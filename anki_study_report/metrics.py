"""Read-only study metrics for Anki Study Report."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import unescape
import math
import re
import time
from typing import Any

from .deck_hub import collect_deck_catalog
from .note_intelligence import (
    analyze_note_type,
    build_note_preview,
    build_rendered_preview_native_first,
    missing_fields_for_profile,
)


ANSWER_TIME_CAP_MS = 120_000
SECONDS_IN_DAY = 86_400
PROBLEM_DECK_PASS_RATE = 0.80
PROBLEM_DECK_MIN_REVIEWS = 5
ATTENTION_CARD_LIMIT = 100
ATTENTION_CARD_SLOW_SECONDS = 10.0
ATTENTION_CARD_LOW_PASS_RATE = 0.60
ATTENTION_CARD_LOW_PASS_MIN_REVIEWS = 3
ATTENTION_CARD_REPEATED_AGAIN_MIN = 2
ATTENTION_CARD_LEECH_LAPSE_THRESHOLD = 8
ATTENTION_CARD_STATUS_VERSION = 2
FSRS_FORECAST_DAYS = 30
FSRS_LOW_RECALL_THRESHOLD = 0.90
FSRS_MEDIUM_RECALL_THRESHOLD = 0.80
FSRS_HIGH_RISK_THRESHOLD = 0.65
FSRS_DEFAULT_DECAY = 0.5
ANSWER_MODE_STANDARD = "standard"
ANSWER_MODE_PASS_FAIL = "pass_fail"
ANSWER_MODE_AUTO = "auto"
ANSWER_MODE_AUTO_MIN_REVIEWS = 20
ANSWER_MODE_AUTO_HARD_EASY_THRESHOLD = 0.05
REVLOG_REVIEW_FILTER_SQL = "and r.ease between 1 and 4 and (r.type < 3 or r.factor != 0)"
EARLIER_REVIEW_FILTER_SQL = (
    "and earlier.ease between 1 and 4 and (earlier.type < 3 or earlier.factor != 0)"
)


def collect_metrics(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
    answer_mode: str = ANSWER_MODE_AUTO,
) -> dict[str, Any]:
    """Collect read-only study metrics from an Anki collection.

    Args:
        col: Anki collection object.
        start_ts: Inclusive period start as Unix seconds or milliseconds.
        end_ts: Exclusive period end as Unix seconds or milliseconds.
        deck_ids: Optional deck ids. When provided, descendants are included
            when the current Anki deck API exposes enough information.

    Returns:
        A dictionary with safe zero values when no matching data exists.
    """

    start_ms = _to_revlog_ms(start_ts)
    end_ms = _to_revlog_ms(end_ts)
    if end_ms <= start_ms:
        return _empty_metrics()

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)

    requested_answer_mode = _normalize_answer_mode(answer_mode)
    total_reviews, again_count, total_seconds = _review_summary(
        col,
        start_ms,
        end_ms,
        expanded_deck_ids,
    )
    new_cards = _new_cards(col, start_ms, end_ms, expanded_deck_ids)
    answer_distribution = _answer_distribution(col, start_ms, end_ms, expanded_deck_ids)
    resolved_answer_mode, answer_mode_reason = _resolve_answer_mode(
        requested_answer_mode,
        answer_distribution,
    )
    pass_fail = _pass_fail_metrics(total_reviews, again_count, answer_distribution)
    deck_breakdown = _deck_breakdown(col, start_ms, end_ms, expanded_deck_ids)
    attention_cards, attention_cards_status = collect_attention_cards_with_status(
        col,
        start_ms,
        end_ms,
        expanded_deck_ids,
        max_results=ATTENTION_CARD_LIMIT,
    )
    due_tomorrow = _due_tomorrow(col, expanded_deck_ids)
    from .forecast_metrics import collect_forecast_metrics

    forecast = collect_forecast_metrics(col, expanded_deck_ids)
    fsrs = _fsrs_metrics(col, expanded_deck_ids)
    from .heatmap_metrics import collect_heatmap_metrics

    heatmap = collect_heatmap_metrics(col, start_ms, end_ms, expanded_deck_ids)
    from .comparison_metrics import collect_comparison_metrics

    comparison = collect_comparison_metrics(col, expanded_deck_ids)

    return {
        "total_reviews": total_reviews,
        "new_cards": new_cards,
        "again_count": again_count,
        "fail_count": pass_fail["fail_count"],
        "pass_count": pass_fail["pass_count"],
        "pass_rate": _pass_rate(total_reviews, again_count),
        "fail_rate": pass_fail["fail_rate"],
        "total_seconds": total_seconds,
        "average_answer_seconds": _average_seconds(total_seconds, total_reviews),
        "estimated_minutes": _minutes(total_seconds),
        "answer_mode": resolved_answer_mode,
        "requested_answer_mode": requested_answer_mode,
        "answer_mode_reason": answer_mode_reason,
        "pass_fail": pass_fail,
        "answer_distribution": answer_distribution,
        "deck_breakdown": deck_breakdown,
        "deck_catalog": collect_deck_catalog(col),
        "deck_scope_ids": list(expanded_deck_ids) if expanded_deck_ids is not None else None,
        "deck_active_dates_available": False,
        "attention_cards": attention_cards,
        "attention_cards_status": attention_cards_status,
        "note_type_catalog": attention_cards_status.get("noteTypeCatalog", []),
        "due_tomorrow": due_tomorrow,
        "forecast": forecast,
        "fsrs": fsrs,
        "heatmap": heatmap,
        "comparison": comparison,
    }


def expand_deck_ids(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> list[int] | None:
    """Return selected deck ids plus descendants when Anki exposes them."""

    return _expand_deck_ids(col, deck_ids)


def collect_attention_cards(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
    max_results: int = ATTENTION_CARD_LIMIT,
    include_rendered_preview: bool = True,
) -> list[dict[str, Any]]:
    """Return read-only card-level attention rows for the dashboard.

    The payload is intentionally small: no full revlog history and no raw HTML.
    Any collection/model incompatibility falls back to an empty list so report
    generation can keep using the deck-level fallback.
    """

    cards, _status = collect_attention_cards_with_status(
        col,
        start_ts,
        end_ts,
        deck_ids,
        max_results=max_results,
        include_rendered_preview=include_rendered_preview,
    )
    return cards


def collect_attention_cards_with_status(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
    max_results: int = ATTENTION_CARD_LIMIT,
    include_rendered_preview: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return card-level attention rows plus collector status metadata."""

    start_ms, start_normalized, start_reason = _ensure_epoch_ms(start_ts, name="periodStartRaw", default=0)
    end_ms, end_normalized, end_reason = _ensure_epoch_ms(end_ts, name="periodEndRaw", default=_now_ms())
    time_unit_normalized = start_normalized or end_normalized
    if end_ms <= start_ms:
        return [], _attention_cards_status(
            "skipped",
            scanned_cards=0,
            returned_cards=0,
            reason=start_reason or end_reason or "Invalid report period.",
            collector_ran=True,
            collection_available=_collection_available(col),
            source="fresh",
            period_start_raw=start_ts,
            period_end_raw=end_ts,
            period_start_ms=start_ms,
            period_end_ms=end_ms,
            time_unit_normalized=time_unit_normalized,
        )

    if not _collection_available(col):
        return [], _attention_cards_status(
            "unavailable",
            scanned_cards=0,
            returned_cards=0,
            reason="collection unavailable",
            collector_ran=True,
            collection_available=False,
            source="fresh",
            period_start_raw=start_ts,
            period_end_raw=end_ts,
            period_start_ms=start_ms,
            period_end_ms=end_ms,
            time_unit_normalized=time_unit_normalized,
        )

    try:
        raw_selected_deck_ids = _normalized_deck_ids(deck_ids or [])
        expanded_deck_ids = _expand_deck_ids(col, deck_ids) if raw_selected_deck_ids else None
        probe = _attention_collection_probe(col, start_ms, end_ms, expanded_deck_ids)
        if start_ms == 0 and probe.get("revlogMaxId") is not None:
            end_ms = max(end_ms, _as_int(probe.get("revlogMaxId")) + 1)
            probe = _attention_collection_probe(col, start_ms, end_ms, expanded_deck_ids)
        if not probe.get("collectionAvailable"):
            return [], _attention_cards_status(
                "unavailable",
                scanned_cards=0,
                returned_cards=0,
                reason="collection unavailable",
                collector_ran=True,
                collection_available=False,
                source="fresh",
                period_start_raw=start_ts,
                period_end_raw=end_ts,
                period_start_ms=start_ms,
                period_end_ms=end_ms,
                time_unit_normalized=time_unit_normalized,
                selected_deck_ids_count=len(raw_selected_deck_ids),
                deck_filter_applied=bool(raw_selected_deck_ids),
                **probe,
            )
        rows = _attention_card_rows(col, start_ms, end_ms, expanded_deck_ids)
        deck_names = _deck_names_by_id(col)
        attention_cards = [
            _attention_card_payload(
                col,
                row,
                deck_names,
                include_rendered_preview=include_rendered_preview,
            )
            for row in rows
        ]
        attention_cards = [card for card in attention_cards if card is not None]
        attention_cards.sort(
            key=lambda card: (
                -_as_int(card.get("riskScore")),
                -_as_int(card.get("againCount")),
                -_as_int(card.get("lapses")),
                _as_int(card.get("cardId")),
            )
        )
        used_note_type_ids = {
            _as_int(card.get("noteTypeId"))
            for card in attention_cards
            if _as_int(card.get("noteTypeId")) > 0
        }
        note_type_catalog = _note_type_catalog(col, used_note_type_ids)
        issue_counts = _attention_issue_counts(attention_cards)
        note_profile_diagnostics = _attention_note_profile_diagnostics(attention_cards)
        limit = max(0, _as_int(max_results))
        limited_cards = attention_cards[:limit]
        reason = None
        if _as_int(probe.get("revlogTotalRows")) == 0:
            reason = "revlog table is empty"
        elif _as_int(probe.get("revlogRowsInPeriod")) == 0:
            reason = "no revlog rows in selected period"
        elif bool(raw_selected_deck_ids) and _as_int(probe.get("revlogRowsAfterDeckFilter")) == 0:
            reason = "deck filter removed all revlog rows"
        elif _as_int(probe.get("candidateCards")) == 0:
            reason = "no candidate cards after revlog lookup"
        elif not rows:
            reason = "no candidate cards after revlog lookup"
        elif not limited_cards:
            reason = "no attention issues found"
        diagnostic_warning = None
        if (
            start_ms == 0
            and _as_int(probe.get("revlogTotalRows")) > 0
            and _as_int(probe.get("revlogRowsInPeriod")) == 0
        ):
            diagnostic_warning = "all-time revlog period returned zero rows despite non-empty revlog"
        return limited_cards, _attention_cards_status(
            "available",
            scanned_cards=len(rows),
            returned_cards=len(limited_cards),
            reason=reason,
            collector_ran=True,
            collection_available=True,
            source="fresh",
            candidate_cards=probe.get("candidateCards"),
            revlog_rows=probe.get("revlogRowsAfterDeckFilter"),
            notes_loaded=sum(1 for row in rows if _attention_row_raw_fields(row) is not None),
            field_scan_cards=len(rows),
            issue_counts=issue_counts,
            max_results=limit,
            period_start_raw=start_ts,
            period_end_raw=end_ts,
            period_start_ms=start_ms,
            period_end_ms=end_ms,
            time_unit_normalized=time_unit_normalized,
            selected_deck_ids_count=len(raw_selected_deck_ids),
            deck_filter_applied=bool(raw_selected_deck_ids),
            diagnostic_warning=diagnostic_warning,
            **note_profile_diagnostics,
            noteTypeCatalog=note_type_catalog,
            noteTypeCatalogCount=len(note_type_catalog),
            **probe,
        )
    except Exception:
        return [], _attention_cards_status(
            "error",
            scanned_cards=0,
            returned_cards=0,
            reason="Card-level collector failed.",
            collector_ran=True,
            collection_available=_collection_available(col),
            source="fresh",
            period_start_raw=start_ts,
            period_end_raw=end_ts,
            period_start_ms=start_ms,
            period_end_ms=end_ms,
            time_unit_normalized=time_unit_normalized,
        )


def collect_action_card_ids(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
    action: str = "again",
    max_results: int | None = None,
) -> list[int]:
    """Return card ids for Browser actions without modifying the collection."""

    start_ms = _to_revlog_ms(start_ts)
    end_ms = _to_revlog_ms(end_ts)
    if end_ms <= start_ms:
        return []

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)
    if action == "again":
        return _review_card_ids(
            col,
            start_ms,
            end_ms,
            expanded_deck_ids,
            extra_where="and r.ease = 1",
            max_results=max_results,
        )
    if action == "new":
        return _new_card_ids(col, start_ms, end_ms, expanded_deck_ids, max_results)
    if action == "problem_decks":
        return _problem_deck_card_ids(
            col,
            start_ms,
            end_ms,
            expanded_deck_ids,
            max_results,
        )
    raise ValueError(f"Unknown Browser action: {action}")


def _empty_metrics() -> dict[str, Any]:
    return {
        "total_reviews": 0,
        "new_cards": 0,
        "again_count": 0,
        "fail_count": 0,
        "pass_count": 0,
        "pass_rate": 0.0,
        "fail_rate": 0.0,
        "total_seconds": 0,
        "average_answer_seconds": 0.0,
        "estimated_minutes": 0.0,
        "answer_mode": ANSWER_MODE_STANDARD,
        "requested_answer_mode": ANSWER_MODE_AUTO,
        "answer_mode_reason": "no_reviews",
        "pass_fail": _empty_pass_fail_metrics(),
        "answer_distribution": _empty_answer_distribution(),
        "deck_breakdown": [],
        "attention_cards": [],
        "attention_cards_status": {
            "status": "skipped",
            "scannedCards": 0,
            "returnedCards": 0,
            "reason": "No reviews in the selected period.",
            "collectorRan": False,
            "collectionAvailable": False,
            "source": "fresh",
        },
        "due_tomorrow": 0,
        "forecast": {
            "available": False,
            "baseline": {
                "history_days": 60,
                "active_days": 0,
                "activity_rate": 0.0,
                "median_reviews_active_day": 0,
                "avg_reviews_active_day": 0.0,
                "median_new_active_day": 0,
                "avg_new_active_day": 0.0,
                "again_rate": 0.0,
                "estimated_minutes_active_day": 0.0,
                "weekday_activity": {},
            },
            "due_forecast": {
                "tomorrow": 0,
                "tomorrow_reviews": 0,
                "tomorrow_learning": 0,
                "next_7_days_total": 0,
                "next_30_days_total": 0,
                "daily": [],
            },
            "pattern": {
                "summary": "Для прогноза пока не хватает данных.",
                "active_weekdays": [],
                "weak_weekdays": [],
                "regularity": "unknown",
            },
            "recommendation": {
                "risk": "unknown",
                "risk_label": "нет данных",
                "new_cards_advice": "Рекомендация по новым карточкам пока недоступна.",
                "explanation": "Нет данных для прогноза.",
                "summary": "Прогноз пока недоступен.",
            },
        },
        "fsrs": _empty_fsrs_metrics(),
        "heatmap": {
            "available": False,
            "active_days": 0,
            "missed_days": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "total_days": 0,
            "reviews_by_day": [],
            "best_days": [],
            "weekday_average": {},
            "stability": "Активность за выбранный период пока не найдена.",
            "source": {"primary": "revlog"},
        },
        "comparison": {
            "available": False,
            "today": {},
            "baselines": {},
            "comparisons": {},
            "insights": [],
            "message": "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.",
            "source": {"primary": "unavailable"},
        },
    }


def _to_revlog_ms(ts: int | float) -> int:
    value = int(ts)
    if abs(value) < 10_000_000_000:
        return value * 1000
    return value


def _ensure_epoch_ms(value: Any, *, name: str, default: int = 0) -> tuple[int, bool, str | None]:
    if value is None:
        return default, False, None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default, False, f"{name} is not a valid timestamp"
    if number == 0:
        return 0, False, None
    absolute = abs(number)
    if 1_000_000_000 <= absolute < 100_000_000_000:
        return number * 1000, True, None
    if absolute >= 100_000_000_000:
        return number, False, None
    return max(0, number), False, f"{name} is outside expected epoch timestamp range"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _review_summary(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> tuple[int, int, int]:
    home_deck_sql = "case when c.odid > 0 then c.odid else c.did end"
    deck_sql, deck_params = _deck_filter_sql(deck_ids, column=home_deck_sql)
    row = col.db.first(
        f"""
        select
            count(*) as total_reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
            coalesce(sum(
                case
                    when r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {deck_sql}
        """,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )
    if not row:
        return 0, 0, 0

    total_reviews = _as_int(row[0])
    again_count = _as_int(row[1])
    total_seconds = _as_int(round(_as_int(row[2]) / 1000))
    return total_reviews, again_count, total_seconds


def _new_cards(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> int:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    return _as_int(
        col.db.scalar(
            f"""
            select count(distinct r.cid)
            from revlog r
            left join cards c on c.id = r.cid
            where r.id >= ?
              and r.id < ?
              and r.type = 0
              {REVLOG_REVIEW_FILTER_SQL}
              and not exists (
                  select 1
                  from revlog earlier
                  where earlier.cid = r.cid
                    and earlier.id < r.id
                    {EARLIER_REVIEW_FILTER_SQL}
                  limit 1
              )
              {deck_sql}
            """,
            start_ms,
            end_ms,
            *deck_params,
        )
    )


def _answer_distribution(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> dict[str, int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select r.ease, count(*)
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {deck_sql}
        group by r.ease
        """,
        start_ms,
        end_ms,
        *deck_params,
    )

    distribution = _empty_answer_distribution()
    for ease, count in rows:
        key = _ease_key(ease)
        if key:
            distribution[key] += _as_int(count)
    return distribution


def _empty_answer_distribution() -> dict[str, int]:
    return {
        "again": 0,
        "hard": 0,
        "good": 0,
        "easy": 0,
    }


def _empty_pass_fail_metrics() -> dict[str, Any]:
    return {
        "total_reviews": 0,
        "fail_count": 0,
        "pass_count": 0,
        "pass_rate": 0.0,
        "fail_rate": 0.0,
        "hard_count": 0,
        "easy_count": 0,
        "hard_easy_rate": 0.0,
    }


def _pass_fail_metrics(
    total_reviews: int,
    again_count: int,
    answer_distribution: dict[str, int],
) -> dict[str, Any]:
    pass_count = max(0, total_reviews - again_count)
    fail_rate = _fail_rate(total_reviews, again_count)
    hard_count = _as_int(answer_distribution.get("hard"))
    easy_count = _as_int(answer_distribution.get("easy"))
    hard_easy = hard_count + easy_count
    return {
        "total_reviews": total_reviews,
        "fail_count": again_count,
        "pass_count": pass_count,
        "pass_rate": _pass_rate(total_reviews, again_count),
        "fail_rate": fail_rate,
        "hard_count": hard_count,
        "easy_count": easy_count,
        "hard_easy_rate": round(hard_easy / total_reviews, 4) if total_reviews > 0 else 0.0,
    }


def _normalize_answer_mode(value: Any) -> str:
    mode = str(value or ANSWER_MODE_AUTO).strip().lower()
    if mode in {ANSWER_MODE_STANDARD, ANSWER_MODE_PASS_FAIL, ANSWER_MODE_AUTO}:
        return mode
    return ANSWER_MODE_AUTO


def _resolve_answer_mode(
    requested_answer_mode: str,
    answer_distribution: dict[str, int],
) -> tuple[str, str]:
    if requested_answer_mode in {ANSWER_MODE_STANDARD, ANSWER_MODE_PASS_FAIL}:
        return requested_answer_mode, "configured"

    total_reviews = sum(_as_int(value) for value in answer_distribution.values())
    if total_reviews < ANSWER_MODE_AUTO_MIN_REVIEWS:
        return ANSWER_MODE_STANDARD, "auto_insufficient_data"

    hard_easy = (
        _as_int(answer_distribution.get("hard"))
        + _as_int(answer_distribution.get("easy"))
    )
    hard_easy_rate = hard_easy / total_reviews if total_reviews > 0 else 1
    if hard_easy_rate < ANSWER_MODE_AUTO_HARD_EASY_THRESHOLD:
        return ANSWER_MODE_PASS_FAIL, "auto_hard_easy_under_threshold"
    return ANSWER_MODE_STANDARD, "auto_hard_easy_present"


def _ease_key(ease: Any) -> str | None:
    try:
        ease_int = _as_int(ease)
    except (TypeError, ValueError):
        return None
    return {
        1: "again",
        2: "hard",
        3: "good",
        4: "easy",
    }.get(ease_int)


def _review_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
    extra_where: str = "",
    max_results: int | None = None,
) -> list[int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    limit_sql, limit_params = _limit_sql(max_results)
    rows = col.db.all(
        f"""
        select distinct r.cid
        from revlog r
        join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {extra_where}
          {deck_sql}
        order by r.cid
        {limit_sql}
        """,
        start_ms,
        end_ms,
        *deck_params,
        *limit_params,
    )
    return [_as_int(row[0]) for row in rows if row and row[0] is not None]


def _new_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
    max_results: int | None = None,
) -> list[int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    limit_sql, limit_params = _limit_sql(max_results)
    rows = col.db.all(
        f"""
        select distinct r.cid
        from revlog r
        join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          and r.type = 0
          {REVLOG_REVIEW_FILTER_SQL}
          and not exists (
              select 1
              from revlog earlier
              where earlier.cid = r.cid
                and earlier.id < r.id
                {EARLIER_REVIEW_FILTER_SQL}
              limit 1
          )
          {deck_sql}
        order by r.cid
        {limit_sql}
        """,
        start_ms,
        end_ms,
        *deck_params,
        *limit_params,
    )
    return [_as_int(row[0]) for row in rows if row and row[0] is not None]


def _problem_deck_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
    max_results: int | None = None,
) -> list[int]:
    problem_deck_ids = [
        _as_int(deck["deck_id"])
        for deck in _deck_breakdown(col, start_ms, end_ms, deck_ids)
        if deck.get("deck_id") is not None
        and _as_int(deck.get("total_reviews")) >= PROBLEM_DECK_MIN_REVIEWS
        and float(deck.get("pass_rate") or 0) < PROBLEM_DECK_PASS_RATE
    ]
    if not problem_deck_ids:
        return []

    return _review_card_ids(
        col,
        start_ms,
        end_ms,
        problem_deck_ids,
        max_results=max_results,
    )


def _attention_card_rows(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> list[tuple[Any, ...]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    return col.db.all(
        f"""
        select
            c.id as card_id,
            c.nid as note_id,
            c.did as deck_id,
            c.lapses as lapses,
            n.mid as model_id,
            c.ord as card_ord,
            n.tags as tags,
            n.flds as fields,
            count(*) as total_reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
            coalesce(sum(
                case
                    when r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms,
            max(r.id) as last_reviewed_ms
        from revlog r
        join cards c on c.id = r.cid
        left join notes n on n.id = c.nid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {deck_sql}
        group by c.id, c.nid, c.did, c.lapses, n.mid, c.ord, n.tags, n.flds
        """,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )


def _attention_card_payload(
    col: Any,
    row: tuple[Any, ...],
    deck_names: dict[int, str],
    *,
    include_rendered_preview: bool = True,
) -> dict[str, Any] | None:
    if len(row) >= 12:
        (
            card_id,
            note_id,
            deck_id,
            lapses,
            model_id,
            card_ord,
            tags,
            raw_fields,
            total_reviews,
            again_count,
            total_ms,
            last_reviewed_ms,
        ) = row[:12]
    else:
        (
            card_id,
            note_id,
            deck_id,
            lapses,
            model_id,
            tags,
            raw_fields,
            total_reviews,
            again_count,
            total_ms,
            last_reviewed_ms,
        ) = row[:11]
        card_ord = 0
    total_reviews_int = _as_int(total_reviews)
    if total_reviews_int <= 0:
        return None

    card_id_int = _as_int(card_id)
    note_id_int = _as_int(note_id) if note_id is not None else None
    deck_id_int = _as_int(deck_id) if deck_id is not None else None
    deck_name = _deck_name_for_breakdown(deck_id_int, deck_names)
    lapses_int = _as_int(lapses)
    again_count_int = _as_int(again_count)
    total_seconds = _as_int(round(_as_int(total_ms) / 1000))
    average_answer_seconds = _average_seconds(total_seconds, total_reviews_int)
    pass_rate = _pass_rate(total_reviews_int, again_count_int)
    tag_list = _attention_tags(tags)
    fields = _note_fields_by_name(col, model_id, raw_fields)
    model = _model_by_id(col, model_id)
    profile = analyze_note_type(model, raw_fields)
    preview = build_note_preview(model, raw_fields, card_ord)
    missing_fields = _attention_missing_fields(fields, profile, raw_fields)
    issues = _attention_issues(
        tags=tag_list,
        lapses=lapses_int,
        again_count=again_count_int,
        total_reviews=total_reviews_int,
        average_answer_seconds=average_answer_seconds,
        pass_rate=pass_rate,
        missing_fields=missing_fields,
    )
    if not issues:
        return None

    front_preview = preview.get("primary") or _front_preview(fields)
    payload = {
        "cardId": card_id_int,
        "noteId": note_id_int,
        "noteTypeId": _as_int(model_id),
        "deckName": deck_name,
        "frontPreview": front_preview,
        "preview": preview,
        "issues": issues,
        "riskScore": _attention_risk_score(issues, lapses_int),
        "againCount": again_count_int,
        "lapses": lapses_int,
        "averageAnswerSeconds": average_answer_seconds,
        "passRate": pass_rate,
        "lastReviewedAt": _revlog_ms_to_iso(last_reviewed_ms),
        "searchQuery": _attention_search_query(card_id_int, note_id_int, deck_name, front_preview),
        "missingFields": missing_fields,
        "noteTypeName": preview.get("noteTypeName") or profile.get("noteTypeName") or "",
        "cardTemplateName": preview.get("cardTemplateName") or "",
        "detectedKind": preview.get("detectedKind") or profile.get("detectedKind") or "unknown",
    }
    if include_rendered_preview:
        payload["renderedPreview"] = build_rendered_preview_native_first(
            col,
            card_id_int,
            model,
            raw_fields,
            card_ord,
        )
    return payload


def _rendered_preview_fallback() -> dict[str, Any]:
    return {
        "renderStatus": "unavailable",
        "reason": "Anki rendered preview is unavailable in this read-only dashboard path; structured preview is used.",
        "mediaRefs": [],
    }


def _attention_cards_status(
    status: str,
    *,
    scanned_cards: int,
    returned_cards: int,
    reason: str | None = None,
    collector_ran: bool,
    collection_available: bool,
    revlog_rows: Any = None,
    candidate_cards: Any = None,
    notes_loaded: Any = None,
    field_scan_cards: Any = None,
    source: str = "unknown",
    issue_counts: dict[str, Any] | None = None,
    max_results: Any = None,
    period_start_raw: Any = None,
    period_end_raw: Any = None,
    period_start_ms: Any = None,
    period_end_ms: Any = None,
    time_unit_normalized: bool = False,
    selected_deck_ids_count: Any = None,
    deck_filter_applied: Any = None,
    diagnostic_warning: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status if status in {"available", "unavailable", "skipped", "error"} else "unavailable",
        "scannedCards": max(0, _as_int(scanned_cards)),
        "returnedCards": max(0, _as_int(returned_cards)),
        "collectorRan": bool(collector_ran),
        "collectionAvailable": bool(collection_available),
        "source": source if source in {"fresh", "cache", "mock", "unknown"} else "unknown",
        "issueCounts": _attention_issue_counts_payload(issue_counts),
        "thresholds": _attention_thresholds(max_results),
        "periodStartRaw": _safe_timestamp_value(period_start_raw),
        "periodEndRaw": _safe_timestamp_value(period_end_raw),
        "periodStartMs": max(0, _as_int(period_start_ms)),
        "periodEndMs": max(0, _as_int(period_end_ms)),
        "timeUnitNormalized": bool(time_unit_normalized),
        "selectedDeckIdsCount": max(0, _as_int(selected_deck_ids_count)),
        "deckFilterApplied": bool(deck_filter_applied),
    }
    if reason:
        payload["reason"] = _attention_status_reason(reason)
    if diagnostic_warning:
        payload["diagnosticWarning"] = _attention_status_reason(diagnostic_warning)
    for key, value in (
        ("revlogRows", revlog_rows if revlog_rows is not None else extra.get("revlogRows")),
        ("candidateCards", candidate_cards if candidate_cards is not None else extra.get("candidateCards")),
        ("notesLoaded", notes_loaded if notes_loaded is not None else extra.get("notesLoaded")),
        ("fieldScanCards", field_scan_cards if field_scan_cards is not None else extra.get("fieldScanCards")),
        ("cardsTotal", extra.get("cardsTotal")),
        ("notesTotal", extra.get("notesTotal")),
        ("revlogTotalRows", extra.get("revlogTotalRows")),
        ("revlogMinId", extra.get("revlogMinId")),
        ("revlogMaxId", extra.get("revlogMaxId")),
        ("revlogRowsInPeriod", extra.get("revlogRowsInPeriod")),
        ("revlogRowsAfterDeckFilter", extra.get("revlogRowsAfterDeckFilter")),
        ("noteTypeProfilesCount", extra.get("noteTypeProfilesCount")),
        ("unknownNoteTypesCount", extra.get("unknownNoteTypesCount")),
        ("noteTypeCatalogCount", extra.get("noteTypeCatalogCount")),
    ):
        if value is not None:
            payload[key] = max(0, _as_int(value))
    detected_kinds = extra.get("detectedKinds")
    if isinstance(detected_kinds, dict):
        payload["detectedKinds"] = {
            str(key): max(0, _as_int(value))
            for key, value in detected_kinds.items()
            if str(key).strip()
        }
    if extra.get("previewStrategy"):
        payload["previewStrategy"] = _attention_status_reason(extra.get("previewStrategy"))
    if extra.get("missingFieldRoleSource"):
        payload["missingFieldRoleSource"] = _attention_status_reason(extra.get("missingFieldRoleSource"))
    note_type_catalog = extra.get("noteTypeCatalog")
    if isinstance(note_type_catalog, list):
        payload["noteTypeCatalog"] = [item for item in note_type_catalog if isinstance(item, dict)]
    return payload


def _safe_timestamp_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _attention_issue_counts(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts = _empty_attention_issue_counts()
    for card in cards:
        issues = card.get("issues")
        if not isinstance(issues, list):
            continue
        for issue in issues:
            key = _attention_issue_count_key(issue)
            if key in counts:
                counts[key] += 1
    return counts


def _attention_issue_counts_payload(value: dict[str, Any] | None = None) -> dict[str, int]:
    counts = _empty_attention_issue_counts()
    if isinstance(value, dict):
        for key in counts:
            counts[key] = max(0, _as_int(value.get(key)))
    return counts


def _empty_attention_issue_counts() -> dict[str, int]:
    return {
        "leech": 0,
        "repeatedAgain": 0,
        "slowAnswer": 0,
        "lowPassRate": 0,
        "missingAudio": 0,
        "missingExample": 0,
        "missingPitch": 0,
        "missingImage": 0,
        "missingMeaning": 0,
        "missingPartOfSpeech": 0,
    }


def _attention_issue_count_key(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "leech": "leech",
        "repeated_again": "repeatedAgain",
        "slow_answer": "slowAnswer",
        "low_pass_rate": "lowPassRate",
        "missing_audio": "missingAudio",
        "missing_example": "missingExample",
        "missing_pitch": "missingPitch",
        "missing_image": "missingImage",
        "missing_meaning": "missingMeaning",
        "missing_part_of_speech": "missingPartOfSpeech",
    }.get(normalized, "")


def _attention_thresholds(max_results: Any = None) -> dict[str, Any]:
    limit = _as_int(max_results)
    if limit <= 0:
        limit = ATTENTION_CARD_LIMIT
    return {
        "repeatedAgainThreshold": ATTENTION_CARD_REPEATED_AGAIN_MIN,
        "slowAnswerSeconds": ATTENTION_CARD_SLOW_SECONDS,
        "lowPassRateThreshold": ATTENTION_CARD_LOW_PASS_RATE,
        "leechLapsesFallback": ATTENTION_CARD_LEECH_LAPSE_THRESHOLD,
        "maxResults": limit,
    }


def _collection_available(col: Any) -> bool:
    return bool(col is not None and getattr(col, "db", None) is not None)


def _attention_collection_probe(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> dict[str, Any]:
    if not _collection_available(col):
        return {
            "collectionAvailable": False,
            "revlogRows": 0,
            "candidateCards": 0,
            "revlogTotalRows": 0,
            "revlogRowsInPeriod": 0,
            "revlogRowsAfterDeckFilter": 0,
        }
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    deck_filter_applied = bool(deck_sql.strip())
    revlog_total_rows = _safe_db_scalar(col, "select count(*) from revlog")
    revlog_min_id = _safe_db_scalar(col, "select min(id) from revlog")
    revlog_max_id = _safe_db_scalar(col, "select max(id) from revlog")
    revlog_rows_in_period = _safe_db_scalar(
        col,
        """
        select count(*)
        from revlog r
        where r.id >= ?
          and r.id < ?
        """,
        start_ms,
        end_ms,
    )
    revlog_rows_after_deck_filter = _safe_db_scalar(
        col,
        f"""
        select count(*)
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {deck_sql}
        """,
        start_ms,
        end_ms,
        *deck_params,
    )
    candidate_cards = _safe_db_scalar(
        col,
        f"""
        select count(distinct r.cid)
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {deck_sql}
        """,
        start_ms,
        end_ms,
        *deck_params,
    )
    return {
        "collectionAvailable": True,
        "cardsTotal": _safe_db_scalar(col, "select count(*) from cards"),
        "notesTotal": _safe_db_scalar(col, "select count(*) from notes"),
        "revlogTotalRows": revlog_total_rows,
        "revlogMinId": revlog_min_id,
        "revlogMaxId": revlog_max_id,
        "revlogRowsInPeriod": revlog_rows_in_period,
        "revlogRowsAfterDeckFilter": revlog_rows_after_deck_filter,
        "revlogRows": revlog_rows_after_deck_filter,
        "candidateCards": candidate_cards,
        "deckFilterApplied": deck_filter_applied,
    }


def _safe_db_scalar(col: Any, query: str, *params: Any) -> int:
    try:
        return max(0, _as_int(col.db.scalar(query, *params)))
    except Exception:
        return 0


def _attention_status_reason(value: Any) -> str:
    text = _plain_text(value)
    text = re.sub(r"\b[A-Za-z]:\\[^\s]+", "", text)
    text = re.sub(r"token=[^\s&]+", "token=[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return _truncate_text(text, 160) or "Card-level collector unavailable."


def _attention_search_query(
    card_id: Any,
    note_id: Any,
    deck_name: str,
    front_preview: str,
) -> str:
    card_id_int = _as_int(card_id)
    if card_id_int > 0:
        return f"cid:{card_id_int}"
    note_id_int = _as_int(note_id)
    if note_id_int > 0:
        return f"nid:{note_id_int}"
    deck_query = f'deck:{_quote_anki_search_value(deck_name)}'
    front_query = _attention_search_text(front_preview)
    return f"{deck_query} {front_query}".strip()


def _attention_search_text(value: Any, limit: int = 40) -> str:
    text = _plain_text(value)
    text = re.sub(r'["\\]', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _truncate_text(text, limit)


def _quote_anki_search_value(value: Any) -> str:
    text = str(value or "").strip() or "Default"
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _attention_tags(raw_tags: Any) -> list[str]:
    return [
        tag.strip().lower()
        for tag in str(raw_tags or "").split()
        if tag.strip()
    ]


def _note_fields_by_name(
    col: Any,
    model_id: Any,
    raw_fields: Any,
) -> dict[str, str]:
    values = str(raw_fields or "").split("\x1f")
    names = _model_field_names(col, model_id)
    if not names:
        return {f"field_{index + 1}": value for index, value in enumerate(values)}
    return {
        name: values[index] if index < len(values) else ""
        for index, name in enumerate(names)
    }


def _model_field_names(col: Any, model_id: Any) -> list[str]:
    model = _model_by_id(col, model_id)
    if not isinstance(model, dict):
        return []
    fields = model.get("flds")
    if not isinstance(fields, list):
        return []
    names: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            name = str(field.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _model_by_id(col: Any, model_id: Any) -> dict[str, Any] | None:
    try:
        model = col.models.get(_as_int(model_id))
    except Exception:
        model = None
    return model if isinstance(model, dict) else None


def _note_type_catalog(col: Any, used_note_type_ids: set[int] | None = None) -> list[dict[str, Any]]:
    used_ids = used_note_type_ids or set()
    models = _all_models(col)
    catalog = []
    for model in models:
        model_id = _as_int(model.get("id") or model.get("mid"))
        fields = [
            str(field.get("name") or "").strip()
            for field in model.get("flds", [])
            if isinstance(field, dict) and str(field.get("name") or "").strip()
        ]
        templates = []
        for index, template in enumerate(model.get("tmpls", []) if isinstance(model.get("tmpls"), list) else []):
            if not isinstance(template, dict):
                continue
            templates.append(
                {
                    "ord": _as_int(template.get("ord")) if template.get("ord") is not None else index,
                    "name": str(template.get("name") or f"Card {index + 1}").strip(),
                    "qfmtAvailable": bool(str(template.get("qfmt") or "").strip()),
                    "afmtAvailable": bool(str(template.get("afmt") or "").strip()),
                }
            )
        catalog.append(
            {
                "noteTypeId": model_id,
                "name": str(model.get("name") or f"Note type {model_id}").strip(),
                "noteCount": _note_count_for_model(col, model_id),
                "cardTemplateCount": len(templates),
                "fields": fields,
                "templates": templates,
                "cssAvailable": bool(str(model.get("css") or "").strip()),
                "usedInCurrentCards": model_id in used_ids,
            }
        )
    return sorted(catalog, key=lambda item: (str(item.get("name") or "").lower(), _as_int(item.get("noteTypeId"))))


def _all_models(col: Any) -> list[dict[str, Any]]:
    models = getattr(col, "models", None)
    if models is None:
        return []
    try:
        raw_models = models.all()
    except Exception:
        raw_models = []
    if isinstance(raw_models, dict):
        raw_models = list(raw_models.values())
    if not isinstance(raw_models, list):
        return []
    return [model for model in raw_models if isinstance(model, dict)]


def _note_count_for_model(col: Any, model_id: int) -> int:
    if model_id <= 0 or getattr(col, "db", None) is None:
        return 0
    try:
        return max(0, _as_int(col.db.scalar("select count(*) from notes where mid = ?", model_id)))
    except Exception:
        return 0


def _attention_row_raw_fields(row: tuple[Any, ...]) -> Any:
    if len(row) >= 12:
        return row[7]
    if len(row) >= 7:
        return row[6]
    return None


def _attention_missing_fields(
    fields: dict[str, str],
    profile: dict[str, Any] | None = None,
    raw_fields: Any = None,
) -> list[str]:
    if isinstance(profile, dict):
        missing = missing_fields_for_profile(profile, raw_fields)
        missing = [issue for issue in missing if issue != "missing_pitch"]
        if missing or profile.get("fields"):
            return missing
    missing: list[str] = []
    for issue, aliases in _attention_field_aliases().items():
        matches = _matching_field_values(fields, aliases)
        if not matches:
            continue
        if issue == "missing_audio":
            if all("[sound:" not in value.lower() for value in matches):
                missing.append(issue)
        elif issue == "missing_image":
            if all("<img" not in value.lower() for value in matches):
                missing.append(issue)
        elif all(not _plain_text(value) for value in matches):
            missing.append(issue)
    return missing


def _attention_note_profile_diagnostics(cards: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = set()
    detected_kinds: dict[str, int] = {}
    unknown_count = 0
    for card in cards:
        note_type_name = str(card.get("noteTypeName") or "").strip()
        template_name = str(card.get("cardTemplateName") or "").strip()
        kind = str(card.get("detectedKind") or "unknown").strip() or "unknown"
        if note_type_name or template_name:
            profiles.add((note_type_name, template_name))
        detected_kinds[kind] = detected_kinds.get(kind, 0) + 1
        if kind == "unknown":
            unknown_count += 1
    return {
        "noteTypeProfilesCount": len(profiles),
        "unknownNoteTypesCount": unknown_count,
        "detectedKinds": detected_kinds,
        "previewStrategy": "role-based-note-intelligence",
        "missingFieldRoleSource": "detected_roles",
    }


def _attention_field_aliases() -> dict[str, set[str]]:
    return {
        "missing_audio": {"audio", "sound", "аудио", "звук"},
        "missing_example": {"example", "examples", "sentence", "context", "пример", "предложение"},
        "missing_image": {"image", "picture", "photo", "img", "картинка", "изображение"},
        "missing_meaning": {"meaning", "translation", "definition", "gloss", "перевод", "значение"},
        "missing_part_of_speech": {"part of speech", "part_of_speech", "pos", "speech", "часть речи"},
    }


def _matching_field_values(fields: dict[str, str], aliases: set[str]) -> list[str]:
    values: list[str] = []
    for name, value in fields.items():
        normalized = _normalize_field_name(name)
        if any(alias in normalized for alias in aliases):
            values.append(str(value or ""))
    return values


def _attention_issues(
    *,
    tags: list[str],
    lapses: int,
    again_count: int,
    total_reviews: int,
    average_answer_seconds: float,
    pass_rate: float,
    missing_fields: list[str],
) -> list[str]:
    issues: list[str] = []
    tag_set = set(tags)
    if "leech" in tag_set or lapses >= ATTENTION_CARD_LEECH_LAPSE_THRESHOLD:
        issues.append("leech")
    if again_count >= ATTENTION_CARD_REPEATED_AGAIN_MIN:
        issues.append("repeated again")
    if average_answer_seconds >= ATTENTION_CARD_SLOW_SECONDS:
        issues.append("slow answer")
    if (
        total_reviews >= ATTENTION_CARD_LOW_PASS_MIN_REVIEWS
        and pass_rate < ATTENTION_CARD_LOW_PASS_RATE
    ):
        issues.append("low pass rate")
    issues.extend(missing_fields)
    return issues


def _attention_risk_score(issues: list[str], lapses: int) -> int:
    score = 0
    if "leech" in issues:
        score += 30
    if "repeated again" in issues:
        score += 20
    if "slow answer" in issues:
        score += 15
    if "low pass rate" in issues:
        score += 15
    if lapses >= 3:
        score += 10
    if any(issue.startswith("missing_") for issue in issues):
        score += 10
    return min(100, score)


def _front_preview(fields: dict[str, str], limit: int = 100) -> str:
    preferred_aliases = {
        "front",
        "word",
        "expression",
        "term",
        "question",
        "слово",
        "выражение",
        "вопрос",
    }
    for name, value in fields.items():
        normalized = _normalize_field_name(name)
        if any(alias in normalized for alias in preferred_aliases):
            text = _plain_text(value)
            if text:
                return _truncate_text(text, limit)
    for value in fields.values():
        text = _plain_text(value)
        if text:
            return _truncate_text(text, limit)
    return "Карточка без front preview"


def _plain_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\[sound:[^\]]+\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b[A-Za-z]:\\[^\s<>\"']+", " ", text)
    text = re.sub(r"file://[^\s<>\"']+", " ", text, flags=re.IGNORECASE)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[_\-\s]+", " ", str(value or "").strip().lower())


def _revlog_ms_to_iso(value: Any) -> str | None:
    milliseconds = _as_int(value)
    if milliseconds <= 0:
        return None
    try:
        return datetime_from_revlog_ms(milliseconds)
    except Exception:
        return None


def datetime_from_revlog_ms(milliseconds: int) -> str:
    return datetime_from_timestamp_ms(milliseconds).strftime("%Y-%m-%d")


def datetime_from_timestamp_ms(milliseconds: int):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)


def _deck_breakdown(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> list[dict[str, Any]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select
            {home_deck_sql} as home_did,
            count(*) as total_reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
            coalesce(sum(case when r.ease = 2 then 1 else 0 end), 0) as hard_count,
            coalesce(sum(case when r.ease = 3 then 1 else 0 end), 0) as good_count,
            coalesce(sum(case when r.ease = 4 then 1 else 0 end), 0) as easy_count,
            coalesce(sum(
                case
                    when r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms,
            count(distinct case
                when r.type = 0
                  and not exists (
                      select 1
                      from revlog earlier
                      where earlier.cid = r.cid
                        and earlier.id < r.id
                        {EARLIER_REVIEW_FILTER_SQL}
                      limit 1
                  )
                then r.cid
            end) as new_cards
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {REVLOG_REVIEW_FILTER_SQL}
          {deck_sql}
        group by home_did
        order by total_reviews desc, home_did asc
        """,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )

    names = _deck_names_by_id(col)
    breakdown: list[dict[str, Any]] = []
    for did, total_reviews, again_count, hard_count, good_count, easy_count, total_ms, new_cards in rows:
        deck_id = _as_int(did) if did is not None else None
        total_reviews_int = _as_int(total_reviews)
        again_count_int = _as_int(again_count)
        pass_count_int = max(0, total_reviews_int - again_count_int)
        total_seconds = _as_int(round(_as_int(total_ms) / 1000))
        breakdown.append(
            {
                "deck_id": deck_id,
                "deck_name": _deck_name_for_breakdown(deck_id, names),
                "total_reviews": total_reviews_int,
                "new_cards": _as_int(new_cards),
                "again_count": again_count_int,
                "fail_count": again_count_int,
                "pass_count": pass_count_int,
                "hard_count": _as_int(hard_count),
                "good_count": _as_int(good_count),
                "easy_count": _as_int(easy_count),
                "pass_rate": _pass_rate(total_reviews_int, again_count_int),
                "fail_rate": _fail_rate(total_reviews_int, again_count_int),
                "total_seconds": total_seconds,
                "average_answer_seconds": _average_seconds(
                    total_seconds,
                    total_reviews_int,
                ),
                "estimated_minutes": _minutes(total_seconds),
            }
        )
    return breakdown


def _deck_name_for_breakdown(deck_id: int | None, names: dict[int, str]) -> str:
    if deck_id is None:
        return "Удалённые карточки"
    return names.get(deck_id, f"Колода {deck_id}")


def _due_tomorrow(col: Any, deck_ids: Sequence[int] | None) -> int:
    try:
        today = int(col.sched.today)
        day_cutoff = int(col.sched.day_cutoff)
    except Exception:
        return 0

    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    tomorrow = today + 1
    tomorrow_start = day_cutoff
    tomorrow_end = day_cutoff + SECONDS_IN_DAY

    return _as_int(
        col.db.scalar(
            f"""
            select count(*)
            from cards
            where (
                (queue in (2, 3) and due = ?)
                or (queue = 1 and due >= ? and due < ?)
            )
            {deck_sql}
            """,
            tomorrow,
            tomorrow_start,
            tomorrow_end,
            *deck_params,
        )
    )


def _empty_fsrs_metrics() -> dict[str, Any]:
    return {
        "enabled": False,
        "source": {
            "memory_state": "unavailable",
            "helper_detected": False,
            "helper_config_available": False,
        },
        "deck_settings": [],
        "memory_state": {
            "cards_with_state": 0,
            "average_recall": None,
            "below_90_count": 0,
            "below_80_count": 0,
            "high_risk_count": 0,
            "average_difficulty": None,
            "difficulty_buckets": _empty_fsrs_difficulty_buckets(),
            "stability_buckets": _empty_fsrs_stability_buckets(),
            "overdue_risk_count": 0,
        },
        "future_load": {
            "tomorrow": 0,
            "next_7_days": 0,
            "next_30_days": 0,
            "daily": [],
            "top_decks": [],
            "heavy_days": [],
            "light_days": [],
        },
        "helper": {
            "config": {},
            "marked_cards": {},
        },
        "recommendation": {
            "status": "unknown",
            "tomorrow_text": "FSRS-данные недоступны.",
            "new_cards_text": "Рекомендация по новым карточкам недоступна.",
        },
    }


def _fsrs_metrics(col: Any, deck_ids: Sequence[int] | None) -> dict[str, Any]:
    enabled = _fsrs_enabled(col)
    deck_settings = _fsrs_deck_settings(col, deck_ids)
    memory_rows = _fsrs_memory_rows(col, deck_ids)
    memory_state = _fsrs_memory_state(memory_rows)
    future_load = _fsrs_future_load(col, deck_ids, memory_rows)
    helper_config = _fsrs_helper_config()
    marked_cards = _fsrs_helper_marked_cards(col, deck_ids)
    helper_detected = bool(helper_config) or bool(marked_cards)

    return {
        "enabled": enabled,
        "source": {
            "memory_state": "cards.data",
            "helper_detected": helper_detected,
            "helper_config_available": bool(helper_config),
        },
        "deck_settings": deck_settings,
        "memory_state": memory_state,
        "future_load": future_load,
        "helper": {
            "config": helper_config,
            "marked_cards": marked_cards,
        },
        "recommendation": _fsrs_recommendation(memory_state, future_load),
    }


def _fsrs_enabled(col: Any) -> bool:
    try:
        return bool(col.get_config("fsrs"))
    except Exception:
        return False


def _fsrs_deck_settings(col: Any, deck_ids: Sequence[int] | None) -> list[dict[str, Any]]:
    decks = _deck_dicts(col)
    if not decks:
        return []

    selected = set(_normalized_deck_ids(deck_ids)) if deck_ids is not None else None
    names = _deck_names_by_id(col)
    settings: list[dict[str, Any]] = []
    for deck in decks:
        deck_id = _deck_id_from_dict(deck)
        if deck_id is None:
            continue
        if selected is not None and deck_id not in selected:
            continue
        if deck.get("dyn"):
            continue

        config = _deck_config_for_deck_id(col, deck_id, deck)
        params_key, params_count = _fsrs_params_summary(config)
        settings.append(
            {
                "deck_id": deck_id,
                "deck_name": names.get(deck_id, str(deck.get("name") or deck_id)),
                "desired_retention": _desired_retention(deck, config),
                "fsrs_params_version": params_key,
                "fsrs_params_count": params_count,
                "max_interval": _nested_int(config, "rev", "maxIvl"),
                "easy_days_percentages": _list_or_empty(config.get("easyDaysPercentages")),
            }
        )

    return sorted(settings, key=lambda item: item["deck_name"].lower())


def _deck_dicts(col: Any) -> list[dict[str, Any]]:
    try:
        decks = col.decks.all()
    except Exception:
        return []
    return [deck for deck in decks if isinstance(deck, dict)]


def _deck_id_from_dict(deck: dict[str, Any]) -> int | None:
    try:
        return _as_int(deck.get("id"))
    except (TypeError, ValueError):
        return None


def _deck_config_for_deck_id(
    col: Any,
    deck_id: int,
    deck: dict[str, Any],
) -> dict[str, Any]:
    try:
        config = col.decks.config_dict_for_deck_id(deck_id)
        if isinstance(config, dict):
            return config
    except Exception:
        pass

    conf_id = deck.get("conf")
    if conf_id is not None:
        try:
            config = col.decks.get_config(conf_id)
            if isinstance(config, dict):
                return config
        except Exception:
            pass
    return {}


def _desired_retention(deck: dict[str, Any], config: dict[str, Any]) -> float | None:
    value = deck.get("desiredRetention")
    if value is None:
        value = config.get("desiredRetention")
    if value is None:
        return None

    try:
        retention = float(value)
    except (TypeError, ValueError):
        return None
    if retention > 1:
        retention /= 100
    return round(retention, 4)


def _fsrs_params_summary(config: dict[str, Any]) -> tuple[str | None, int]:
    for key in ("fsrsParams6", "fsrsParams5", "fsrsWeights"):
        params = config.get(key)
        if isinstance(params, list) and params:
            return key, len(params)
    return None, 0


def _nested_int(data: dict[str, Any], key: str, child_key: str) -> int | None:
    child = data.get(key)
    if not isinstance(child, dict):
        return None
    value = child.get(child_key)
    if value is None:
        return None
    try:
        return _as_int(value)
    except (TypeError, ValueError):
        return None


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _fsrs_memory_rows(col: Any, deck_ids: Sequence[int] | None) -> list[dict[str, Any]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    try:
        today = int(col.sched.today)
    except Exception:
        return []

    try:
        rows = col.db.all(
            f"""
            select
                id,
                did,
                case when odid = 0 then due else odue end as true_due,
                ivl,
                json_extract(data, '$.s') as stability,
                json_extract(data, '$.d') as difficulty,
                coalesce(json_extract(data, '$.decay'), ?) as decay
            from cards
            where queue not in (0, -1)
              and data != ''
              and json_extract(data, '$.s') is not null
              {deck_sql}
            """,
            FSRS_DEFAULT_DECAY,
            *deck_params,
        )
    except Exception:
        return []

    memory_rows: list[dict[str, Any]] = []
    for cid, did, due, ivl, stability, difficulty, decay in rows:
        stability_float = _safe_float(stability)
        if stability_float is None or stability_float <= 0:
            continue

        due_int = _as_int(due)
        interval = _as_int(ivl)
        elapsed_days = max(0, today - (due_int - interval))
        decay_float = _safe_float(decay)
        recall = _fsrs_retrievability(
            elapsed_days,
            stability_float,
            decay_float if decay_float is not None else FSRS_DEFAULT_DECAY,
        )

        difficulty_float = _safe_float(difficulty)
        difficulty_percent = (
            _difficulty_percent(difficulty_float)
            if difficulty_float is not None
            else None
        )
        memory_rows.append(
            {
                "card_id": _as_int(cid),
                "deck_id": _as_int(did),
                "due": due_int,
                "elapsed_days": elapsed_days,
                "stability": stability_float,
                "difficulty": difficulty_float,
                "difficulty_percent": difficulty_percent,
                "recall": recall,
                "forgetting_risk": 1 - recall,
                "overdue": due_int < today,
            }
        )
    return memory_rows


def _fsrs_retrievability(elapsed_days: int, stability: float, decay: float) -> float:
    if stability <= 0:
        return 0.0
    decay_value = -abs(decay or FSRS_DEFAULT_DECAY)
    try:
        factor = 0.9 ** (1 / decay_value) - 1
        recall = (1 + factor * max(elapsed_days, 0) / stability) ** decay_value
    except Exception:
        return 0.0
    return max(0.0, min(1.0, recall))


def _difficulty_percent(difficulty: float) -> float:
    return max(0.0, min(100.0, ((difficulty - 1) / 9) * 100))


def _fsrs_memory_state(memory_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not memory_rows:
        return _empty_fsrs_metrics()["memory_state"]

    recalls = [row["recall"] for row in memory_rows]
    difficulty_values = [
        row["difficulty_percent"]
        for row in memory_rows
        if row.get("difficulty_percent") is not None
    ]
    return {
        "cards_with_state": len(memory_rows),
        "average_recall": round(sum(recalls) / len(recalls), 4),
        "below_90_count": sum(1 for recall in recalls if recall < FSRS_LOW_RECALL_THRESHOLD),
        "below_80_count": sum(1 for recall in recalls if recall < FSRS_MEDIUM_RECALL_THRESHOLD),
        "high_risk_count": sum(1 for recall in recalls if recall < FSRS_HIGH_RISK_THRESHOLD),
        "average_difficulty": (
            round(sum(difficulty_values) / len(difficulty_values), 1)
            if difficulty_values
            else None
        ),
        "difficulty_buckets": _fsrs_difficulty_buckets(memory_rows),
        "stability_buckets": _fsrs_stability_buckets(memory_rows),
        "overdue_risk_count": sum(
            1
            for row in memory_rows
            if row["overdue"] and row["recall"] < FSRS_LOW_RECALL_THRESHOLD
        ),
    }


def _empty_fsrs_difficulty_buckets() -> dict[str, int]:
    return {
        "easy": 0,
        "medium": 0,
        "hard": 0,
        "very_hard": 0,
        "unknown": 0,
    }


def _fsrs_difficulty_buckets(memory_rows: list[dict[str, Any]]) -> dict[str, int]:
    buckets = _empty_fsrs_difficulty_buckets()
    for row in memory_rows:
        value = row.get("difficulty_percent")
        if value is None:
            buckets["unknown"] += 1
        elif value >= 80:
            buckets["very_hard"] += 1
        elif value >= 60:
            buckets["hard"] += 1
        elif value >= 35:
            buckets["medium"] += 1
        else:
            buckets["easy"] += 1
    return buckets


def _empty_fsrs_stability_buckets() -> dict[str, int]:
    return {
        "fresh": 0,
        "weak": 0,
        "medium": 0,
        "strong": 0,
        "very_strong": 0,
    }


def _fsrs_stability_buckets(memory_rows: list[dict[str, Any]]) -> dict[str, int]:
    buckets = _empty_fsrs_stability_buckets()
    for row in memory_rows:
        stability = _safe_float(row.get("stability")) or 0
        if stability >= 90:
            buckets["very_strong"] += 1
        elif stability >= 30:
            buckets["strong"] += 1
        elif stability >= 7:
            buckets["medium"] += 1
        elif stability >= 2:
            buckets["weak"] += 1
        else:
            buckets["fresh"] += 1
    return buckets


def _fsrs_future_load(
    col: Any,
    deck_ids: Sequence[int] | None,
    memory_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        today = int(col.sched.today)
        day_cutoff = int(col.sched.day_cutoff)
    except Exception:
        return _empty_fsrs_metrics()["future_load"]

    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    names = _deck_names_by_id(col)
    daily_counts = {day: 0 for day in range(1, FSRS_FORECAST_DAYS + 1)}
    deck_counts: dict[int, dict[str, Any]] = {}

    try:
        rows = col.db.all(
            f"""
            select
                did,
                case when odid = 0 then due else odue end as true_due,
                count(*)
            from cards
            where queue in (2, 3)
              and (case when odid = 0 then due else odue end) > ?
              and (case when odid = 0 then due else odue end) <= ?
              {deck_sql}
            group by did, case when odid = 0 then due else odue end
            """,
            today,
            today + FSRS_FORECAST_DAYS,
            *deck_params,
        )
    except Exception:
        rows = []

    for did, due, count in rows:
        offset = _as_int(due) - today
        if offset < 1 or offset > FSRS_FORECAST_DAYS:
            continue
        count_int = _as_int(count)
        deck_id = _as_int(did)
        daily_counts[offset] += count_int
        entry = deck_counts.setdefault(
            deck_id,
            {
                "deck_id": deck_id,
                "deck_name": names.get(deck_id, f"Колода {deck_id}"),
                "due_7": 0,
                "due_30": 0,
            },
        )
        if offset <= 7:
            entry["due_7"] += count_int
        entry["due_30"] += count_int

    _add_learning_due_to_forecast(
        col,
        deck_ids,
        day_cutoff,
        names,
        daily_counts,
        deck_counts,
    )

    risk_by_day = {day: 0 for day in range(1, FSRS_FORECAST_DAYS + 1)}
    for row in memory_rows:
        offset = _as_int(row["due"]) - today
        if 1 <= offset <= FSRS_FORECAST_DAYS and row["recall"] < FSRS_LOW_RECALL_THRESHOLD:
            risk_by_day[offset] += 1

    daily = [
        {
            "offset": offset,
            "due": daily_counts[offset],
            "risk_due": risk_by_day[offset],
        }
        for offset in range(1, FSRS_FORECAST_DAYS + 1)
    ]
    next_30 = sum(daily_counts.values())
    next_7 = sum(daily_counts[offset] for offset in range(1, 8))
    heavy_days, light_days = _fsrs_load_extremes(daily)
    top_decks = sorted(
        deck_counts.values(),
        key=lambda deck: (-deck["due_30"], -deck["due_7"], deck["deck_name"].lower()),
    )[:5]

    return {
        "tomorrow": daily_counts[1],
        "next_7_days": next_7,
        "next_30_days": next_30,
        "daily": daily,
        "top_decks": top_decks,
        "heavy_days": heavy_days,
        "light_days": light_days,
    }


def _add_learning_due_to_forecast(
    col: Any,
    deck_ids: Sequence[int] | None,
    day_cutoff: int,
    names: dict[int, str],
    daily_counts: dict[int, int],
    deck_counts: dict[int, dict[str, Any]],
) -> None:
    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    try:
        rows = col.db.all(
            f"""
            select did, count(*)
            from cards
            where queue = 1
              and due >= ?
              and due < ?
              {deck_sql}
            group by did
            """,
            day_cutoff,
            day_cutoff + SECONDS_IN_DAY,
            *deck_params,
        )
    except Exception:
        return

    for did, count in rows:
        count_int = _as_int(count)
        deck_id = _as_int(did)
        daily_counts[1] += count_int
        entry = deck_counts.setdefault(
            deck_id,
            {
                "deck_id": deck_id,
                "deck_name": names.get(deck_id, f"Колода {deck_id}"),
                "due_7": 0,
                "due_30": 0,
            },
        )
        entry["due_7"] += count_int
        entry["due_30"] += count_int


def _fsrs_load_extremes(
    daily: list[dict[str, int]],
) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    nonzero = [item["due"] for item in daily if item["due"] > 0]
    if not nonzero:
        return [], []

    average = sum(nonzero) / len(nonzero)
    heavy_threshold = max(20, math.ceil(average * 1.5))
    light_threshold = max(1, math.floor(average * 0.5))
    heavy = [item for item in daily if item["due"] >= heavy_threshold]
    light = [item for item in daily if 0 < item["due"] <= light_threshold]
    return (
        sorted(heavy, key=lambda item: (-item["due"], item["offset"]))[:5],
        sorted(light, key=lambda item: (item["due"], item["offset"]))[:5],
    )


def _fsrs_helper_config() -> dict[str, Any]:
    try:
        from aqt import mw as anki_mw  # type: ignore
    except Exception:
        return {}

    try:
        config = anki_mw.addonManager.getConfig("759844606")
    except Exception:
        return {}
    return config if isinstance(config, dict) else {}


def _fsrs_helper_marked_cards(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> dict[str, int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    try:
        rows = col.db.all(
            f"""
            select json_extract(data, '$.v'), count(*)
            from cards
            where data != ''
              and json_extract(data, '$.v') is not null
              {deck_sql}
            group by json_extract(data, '$.v')
            """,
            *deck_params,
        )
    except Exception:
        return {}

    markers: dict[str, int] = {}
    for marker, count in rows:
        if marker is None:
            continue
        markers[str(marker)] = _as_int(count)
    return markers


def _fsrs_recommendation(
    memory_state: dict[str, Any],
    future_load: dict[str, Any],
) -> dict[str, str]:
    tomorrow = _as_int(future_load.get("tomorrow"))
    next_7 = _as_int(future_load.get("next_7_days"))
    high_risk = _as_int(memory_state.get("high_risk_count"))
    below_90 = _as_int(memory_state.get("below_90_count"))
    overdue_risk = _as_int(memory_state.get("overdue_risk_count"))
    average_recall = _safe_float(memory_state.get("average_recall"))

    if tomorrow <= 0 and next_7 <= 10:
        status = "empty"
    elif tomorrow >= 100 or overdue_risk >= 50:
        status = "overloaded"
    elif tomorrow >= 50 or overdue_risk >= 20 or (tomorrow > 0 and high_risk >= 50):
        status = "warning"
    elif tomorrow > 0 or next_7 > 0:
        status = "ok"
    else:
        status = "empty"

    if tomorrow <= 0:
        tomorrow_text = "На завтра явной FSRS-нагрузки нет."
    elif status == "overloaded":
        tomorrow_text = (
            f"Завтра высокая нагрузка: {tomorrow} карточек; сначала закрыть "
            f"карточки с recall ниже 90%."
        )
    elif status == "warning":
        tomorrow_text = (
            f"Завтра заметная нагрузка: {tomorrow} карточек. Новые лучше давать осторожно."
        )
    else:
        tomorrow_text = f"Завтра умеренная FSRS-нагрузка: {tomorrow} карточек."

    if tomorrow <= 0 and next_7 <= 10:
        new_cards_text = "Можно добавить немного новых карточек, если есть время."
    elif status in {"overloaded", "warning"}:
        new_cards_text = "Новые карточки завтра лучше ограничить или отложить."
    elif average_recall is not None and average_recall >= 0.9 and tomorrow < 30:
        new_cards_text = "Можно добавить немного новых карточек, если есть время."
    else:
        new_cards_text = "Новые карточки лучше держать в обычном лимите."

    return {
        "status": status,
        "tomorrow_text": tomorrow_text,
        "new_cards_text": new_cards_text,
    }


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _expand_deck_ids(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> list[int] | None:
    if deck_ids is None:
        return None

    selected = _normalized_deck_ids(deck_ids)
    if not selected:
        return []

    names = _deck_names_by_id(col)
    if names:
        selected = {deck_id for deck_id in selected if deck_id in names}
        if not selected:
            return []

    expanded_via_api = _expand_deck_ids_via_children(col, selected)
    if expanded_via_api is not None:
        if names:
            expanded_via_api = {
                deck_id for deck_id in expanded_via_api if deck_id in names
            }
        return sorted(expanded_via_api)

    if names:
        return sorted(_expand_deck_ids_by_names(names, selected))

    return sorted(selected)


def _normalized_deck_ids(deck_ids: Sequence[int]) -> set[int]:
    normalized: set[int] = set()
    for deck_id in deck_ids:
        try:
            normalized.add(_as_int(deck_id))
        except (TypeError, ValueError):
            continue
    return normalized


def _expand_deck_ids_via_children(col: Any, selected: set[int]) -> set[int] | None:
    try:
        children_method = col.decks.children
    except Exception:
        return None

    if not callable(children_method):
        return None

    expanded = set(selected)
    pending = list(selected)

    while pending:
        deck_id = pending.pop()
        try:
            children = children_method(deck_id)
        except Exception:
            return None

        for child in _iter_child_deck_ids(children):
            if child not in expanded:
                expanded.add(child)
                pending.append(child)

    return expanded


def _iter_child_deck_ids(children: Iterable[Any]) -> Iterable[int]:
    for child in children:
        child_id = None
        if isinstance(child, int):
            child_id = child
        elif hasattr(child, "id"):
            child_id = child.id
        elif isinstance(child, dict):
            child_id = child.get("id")
        elif isinstance(child, (tuple, list)) and child:
            child_id = _child_id_from_sequence(child)

        if child_id is not None:
            try:
                yield _as_int(child_id)
            except (TypeError, ValueError):
                continue


def _child_id_from_sequence(child: Sequence[Any]) -> Any:
    for value in reversed(child):
        try:
            return _as_int(value)
        except (TypeError, ValueError):
            continue
    return None


def _expand_deck_ids_by_names(names: dict[int, str], selected: set[int]) -> set[int]:
    selected_names = {names[deck_id] for deck_id in selected if deck_id in names}
    if not selected_names:
        return set(selected)

    expanded = set(selected)
    for deck_id, name in names.items():
        if any(name == parent or name.startswith(parent + "::") for parent in selected_names):
            expanded.add(deck_id)
    return expanded


def _deck_names_by_id(col: Any) -> dict[int, str]:
    try:
        return {
            _as_int(deck.id): str(deck.name)
            for deck in col.decks.all_names_and_ids()
        }
    except Exception:
        pass

    try:
        decks = col.decks.all()
    except Exception:
        return {}

    names: dict[int, str] = {}
    for deck in decks:
        try:
            names[_as_int(deck["id"])] = str(deck["name"])
        except Exception:
            continue
    return names


def _deck_filter_sql(
    deck_ids: Sequence[int] | None,
    table_alias: str | None = "c",
    column: str | None = None,
) -> tuple[str, list[int]]:
    if deck_ids is None:
        return "", []

    normalized = [_as_int(deck_id) for deck_id in deck_ids]
    if not normalized:
        return "and 0", []

    column = column or ("did" if table_alias is None else f"{table_alias}.did")
    placeholders = ", ".join("?" for _ in normalized)
    return f"and {column} in ({placeholders})", normalized


def _limit_sql(max_results: int | None) -> tuple[str, list[int]]:
    if max_results is None:
        return "", []
    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        return "", []
    if limit <= 0:
        return "", []
    return "limit ?", [limit]


def _pass_rate(total_reviews: int, again_count: int) -> float:
    if total_reviews <= 0:
        return 0.0
    return round((total_reviews - again_count) / total_reviews, 4)


def _fail_rate(total_reviews: int, again_count: int) -> float:
    if total_reviews <= 0:
        return 0.0
    return round(again_count / total_reviews, 4)


def _minutes(total_seconds: int) -> float:
    if total_seconds <= 0:
        return 0.0
    return round(total_seconds / 60, 1)


def _average_seconds(total_seconds: int, total_reviews: int) -> float:
    if total_reviews <= 0 or total_seconds <= 0:
        return 0.0
    return round(total_seconds / total_reviews, 1)


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)
