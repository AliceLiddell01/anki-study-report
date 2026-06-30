"""Read-only study metrics for Anki Study Report."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import math
from typing import Any


ANSWER_TIME_CAP_MS = 120_000
SECONDS_IN_DAY = 86_400
PROBLEM_DECK_PASS_RATE = 0.80
PROBLEM_DECK_MIN_REVIEWS = 5
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


def _review_summary(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> tuple[int, int, int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
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
            c.did,
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
        group by c.did
        order by total_reviews desc, c.did asc
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
) -> tuple[str, list[int]]:
    if deck_ids is None:
        return "", []

    normalized = [_as_int(deck_id) for deck_id in deck_ids]
    if not normalized:
        return "and 0", []

    column = "did" if table_alias is None else f"{table_alias}.did"
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
