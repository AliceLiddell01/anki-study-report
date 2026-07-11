"""Bounded, cache-backed Statistics v1 query model.

The public model intentionally contains aggregates only. Revlog/card rows and
collection paths never cross this module's public boundary.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
import json
from typing import Any, Iterable

from .deck_hub import collect_deck_catalog


STATISTICS_SCHEMA_VERSION = 1
METRIC_DEFINITIONS_VERSION = "statistics-v1.0"
CALCULATION_VERSION = "statistics-v1.0"
MAX_BUCKETS = 400
MAX_DECK_ROWS = 12
MAX_DUE_DAYS = 90
PERIODS = {"7d", "30d", "90d", "1y", "all"}
GRANULARITIES = {"auto", "day", "week", "month"}
SCOPE_KINDS = {"dashboard", "all_collection", "single_deck"}
SCOPE_MODES = {"subtree", "direct"}
AGGREGATE_FIELDS = (
    "reviews", "new_cards", "learning", "review", "relearning", "cram",
    "again", "hard", "good", "easy", "pass_count", "fail_count",
    "retention_young_pass", "retention_young_fail",
    "retention_mature_pass", "retention_mature_fail",
    "answer_time_count",
    "study_seconds", "total_answer_seconds",
)

METRIC_REGISTRY = (
    {"id": "reviews", "category": "overview", "source": "cache.daily", "unit": "answers", "aggregation": "sum", "availability": "core", "costClass": "cheap", "supportsScope": True, "supportsComparison": True, "minimumSample": 1, "limitations": [], "calculationVersion": CALCULATION_VERSION},
    {"id": "success_rate", "category": "quality", "source": "cache.daily", "unit": "ratio", "aggregation": "weighted", "availability": "core", "costClass": "cheap", "supportsScope": True, "supportsComparison": True, "minimumSample": 1, "limitations": [], "calculationVersion": CALCULATION_VERSION},
    {"id": "true_retention", "category": "quality", "source": "cache.daily.first_review", "unit": "ratio", "aggregation": "weighted", "availability": "core", "costClass": "moderate", "supportsScope": True, "supportsComparison": True, "minimumSample": 30, "limitations": ["first_review_per_card_local_day"], "calculationVersion": CALCULATION_VERSION},
    {"id": "study_time", "category": "overview", "source": "revlog_estimate", "unit": "seconds", "aggregation": "sum", "availability": "core", "costClass": "cheap", "supportsScope": True, "supportsComparison": True, "minimumSample": 1, "limitations": ["capped_answer_time_estimate"], "calculationVersion": CALCULATION_VERSION},
    {"id": "introduced_cards", "category": "progress", "source": "cache.first_qualifying_review", "unit": "cards", "aggregation": "sum", "availability": "core", "costClass": "moderate", "supportsScope": True, "supportsComparison": True, "minimumSample": 1, "limitations": [], "calculationVersion": CALCULATION_VERSION},
    {"id": "current_card_states", "category": "progress", "source": "collection.current_snapshot", "unit": "cards", "aggregation": "snapshot", "availability": "core", "costClass": "moderate", "supportsScope": True, "supportsComparison": False, "minimumSample": 1, "limitations": ["not_historical"], "calculationVersion": CALCULATION_VERSION},
    {"id": "future_due", "category": "load", "source": "collection.current_schedule", "unit": "cards", "aggregation": "snapshot", "availability": "core", "costClass": "moderate", "supportsScope": True, "supportsComparison": False, "minimumSample": 1, "limitations": ["assumes_no_new_cards_or_future_failures"], "calculationVersion": CALCULATION_VERSION},
)


class StatisticsValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid statistics query.")
        self.field_errors = field_errors


def default_statistics_query() -> dict[str, Any]:
    return {
        "scope": {"kind": "dashboard"},
        "period": "90d",
        "granularity": "auto",
        "comparison": True,
    }


def normalize_statistics_query(
    raw: object,
    deck_catalog: object,
    *,
    display_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StatisticsValidationError({"query": "Expected a JSON object."})
    allowed = {"scope", "period", "granularity", "comparison"}
    errors: dict[str, str] = {}
    for key in raw:
        if key not in allowed:
            errors[key] = "Unexpected field."

    period = raw.get("period", "90d")
    granularity = raw.get("granularity", "auto")
    comparison = raw.get("comparison", True)
    if period not in PERIODS:
        errors["period"] = "Unsupported period."
    if granularity not in GRANULARITIES:
        errors["granularity"] = "Unsupported granularity."
    if not isinstance(comparison, bool):
        errors["comparison"] = "Expected boolean."

    scope_raw = raw.get("scope", {"kind": "dashboard"})
    scope: dict[str, Any] = {"kind": "dashboard"}
    catalog = _catalog_rows(deck_catalog)
    catalog_by_id = {row["deckId"]: row for row in catalog}
    if not isinstance(scope_raw, dict):
        errors["scope"] = "Expected an object."
    else:
        for key in scope_raw:
            if key not in {"kind", "deckId", "mode"}:
                errors[f"scope.{key}"] = "Unexpected field."
        kind = scope_raw.get("kind", "dashboard")
        if kind not in SCOPE_KINDS:
            errors["scope.kind"] = "Unsupported scope."
        elif kind == "single_deck":
            deck_id = _strict_positive_int(scope_raw.get("deckId"))
            mode = scope_raw.get("mode", "subtree")
            if deck_id is None:
                errors["scope.deckId"] = "A positive deck ID is required."
            elif deck_id not in catalog_by_id:
                errors["scope.deckId"] = "Deck was not found."
            elif catalog_by_id[deck_id]["filtered"]:
                errors["scope.deckId"] = "Filtered decks are not supported."
            if mode not in SCOPE_MODES:
                errors["scope.mode"] = "Unsupported deck mode."
            if deck_id is not None:
                scope = {"kind": kind, "deckId": deck_id, "mode": mode}
        else:
            if "deckId" in scope_raw or "mode" in scope_raw:
                errors["scope"] = "deckId and mode are only valid for single_deck."
            scope = {"kind": kind}

    if errors:
        raise StatisticsValidationError(errors)
    if period == "all":
        comparison = False
    return {
        "scope": scope,
        "period": period,
        "granularity": granularity,
        "comparison": comparison,
        "resolvedGranularity": _resolve_granularity(period, granularity),
        "dashboardScope": _dashboard_scope_metadata(display_settings),
    }


def build_statistics_hub(
    snapshot: object,
    current_snapshot: object,
    today_key: str,
    *,
    display_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = current_snapshot if isinstance(current_snapshot, dict) else {}
    catalog = current.get("deckCatalog") if isinstance(current.get("deckCatalog"), list) else []
    public_catalog = _catalog_rows(catalog)
    query = normalize_statistics_query(default_statistics_query(), catalog, display_settings=display_settings)
    result = build_statistics_result(snapshot, current, today_key, query, display_settings=display_settings)
    status = snapshot.get("status") if isinstance(snapshot, dict) and isinstance(snapshot.get("status"), dict) else {}
    return {
        "schemaVersion": STATISTICS_SCHEMA_VERSION,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "availability": _availability(status, snapshot),
        "coverage": result["coverage"],
        "capabilities": {
            "core": "available",
            "fsrs": "future_not_exposed",
            "advanced": "future_not_exposed",
            "providers": [],
            "nativeStatsAction": True,
        },
        "metricDefinitionsVersion": METRIC_DEFINITIONS_VERSION,
        "defaultQuery": default_statistics_query(),
        "initialResult": result,
        "scope": result["scope"],
        "deckOptions": [
            {"deckId": row["deckId"], "fullName": row["fullName"], "parentId": row["parentId"]}
            for row in public_catalog if not row["filtered"]
        ],
    }


def build_statistics_result(
    snapshot: object,
    current_snapshot: object,
    today_key: str,
    query: object,
    *,
    display_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snap = snapshot if isinstance(snapshot, dict) else {}
    current = current_snapshot if isinstance(current_snapshot, dict) else {}
    catalog = current.get("deckCatalog") if isinstance(current.get("deckCatalog"), list) else []
    normalized = (
        dict(query)
        if isinstance(query, dict) and "resolvedGranularity" in query
        else normalize_statistics_query(query, catalog, display_settings=display_settings)
    )
    today = _parse_date(today_key) or date.today()
    all_daily = _rows(snap.get("daily"))
    all_deck_daily = _rows(snap.get("deckDaily"))
    scope_ids, scope_metadata = _scope_ids(normalized["scope"], catalog, display_settings)
    scoped_daily = _scope_daily_rows(all_daily, all_deck_daily, scope_ids)
    requested_start, requested_end = _period_bounds(normalized["period"], today, scoped_daily)
    current_rows = _between(scoped_daily, requested_start, requested_end)
    previous_rows: list[dict[str, Any]] = []
    previous_bounds: tuple[date, date] | None = None
    if normalized["comparison"] and requested_start is not None:
        days = (requested_end - requested_start).days + 1
        previous_end = requested_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        previous_bounds = (previous_start, previous_end)
        previous_rows = _between(scoped_daily, previous_start, previous_end)

    totals = _aggregate(current_rows)
    previous_totals = _aggregate(previous_rows) if previous_bounds else None
    buckets = _bucket_rows(current_rows, normalized["resolvedGranularity"])
    coverage = _coverage(scoped_daily, requested_start, requested_end, totals)
    current_slice = _current_scope_snapshot(current, scope_ids)
    deck_rows = _deck_comparison_rows(all_deck_daily, catalog, requested_start, requested_end, scope_ids, previous_bounds)

    public_query = {
        "scope": normalized["scope"],
        "period": normalized["period"],
        "granularity": normalized["granularity"],
        "resolvedGranularity": normalized["resolvedGranularity"],
        "comparison": normalized["comparison"],
    }
    overview = _overview(totals, previous_totals, buckets)
    if previous_bounds and previous_rows:
        previous_dates = [value for value in (_parse_date(row.get("date")) for row in previous_rows) if value]
        if previous_dates and min(previous_dates) > previous_bounds[0]:
            overview["comparison"]["status"] = "partial"
            overview["comparison"]["reason"] = "partial_previous_coverage"
    return {
        "schemaVersion": STATISTICS_SCHEMA_VERSION,
        "query": public_query,
        "scope": scope_metadata,
        "coverage": coverage,
        "confidencePolicy": {
            "insufficientBelow": 30,
            "preliminaryBelow": 100,
            "deckRowMinimum": 10,
            "trendMinimumActiveDays": 3,
        },
        "overview": overview,
        "quality": _quality(totals, buckets),
        "load": _load(totals, buckets, current_slice),
        "progress": _progress(totals, buckets, current_slice),
        "deckComparison": {
            "mode": "non_overlapping_roots",
            "limit": MAX_DECK_ROWS,
            "rows": deck_rows,
        },
        "limitations": [
            "historical_deck_moves_not_reconstructed",
            "current_states_are_snapshot_only",
            "future_due_assumes_no_new_cards_or_future_failures",
            "study_time_is_capped_revlog_estimate",
        ],
        "calculationVersion": CALCULATION_VERSION,
        "bounds": {
            "current": _bounds_json(requested_start, requested_end),
            "previous": _bounds_json(*previous_bounds) if previous_bounds else None,
        },
    }


def collect_statistics_current_snapshot(col: Any, today_key: str) -> dict[str, Any]:
    """Collect grouped current state/due data in a bounded number of SQL calls."""

    catalog = collect_deck_catalog(col)
    today = _parse_date(today_key) or date.today()
    scheduler_day = _scheduler_day(col)
    states: list[dict[str, Any]] = []
    try:
        rows = col.db.all(
            """
            select case when odid > 0 then odid else did end as deck_id,
              case
                when queue = -1 then 'suspended'
                when queue in (-2, -3) then 'buried'
                when type = 0 then 'unseen'
                when type in (1, 3) then 'learning'
                when type = 2 and ivl >= 21 then 'mature'
                when type = 2 then 'young'
                else 'learning'
              end as state,
              count(*) as cards,
              count(distinct nid) as notes
            from cards
            group by deck_id, state
            """
        )
        states = [
            {"deckId": _as_int(row[0]), "state": str(row[1]), "cards": _as_int(row[2]), "notes": _as_int(row[3])}
            for row in rows
        ]
    except Exception:
        states = []

    note_counts: list[dict[str, Any]] = []
    try:
        rows = col.db.all(
            """
            select case when odid > 0 then odid else did end as deck_id,
              count(distinct nid)
            from cards
            group by deck_id
            """
        )
        note_counts = [{"deckId": _as_int(row[0]), "notes": _as_int(row[1])} for row in rows]
    except Exception:
        note_counts = []

    due: list[dict[str, Any]] = []
    try:
        rows = col.db.all(
            """
            select case when odid > 0 then odid else did end as deck_id,
              type, queue, due, count(*)
            from cards
            where queue in (1, 2, 3)
            group by deck_id, type, queue, due
            """
        )
        for deck_id, card_type, queue, raw_due, count in rows:
            offset = _due_offset(_as_int(queue), _as_int(raw_due), scheduler_day, today)
            if offset is None or offset > MAX_DUE_DAYS:
                continue
            due.append({
                "deckId": _as_int(deck_id),
                "dayOffset": offset,
                "category": _due_category(_as_int(card_type)),
                "count": _as_int(count),
            })
    except Exception:
        due = []

    daily_load: list[dict[str, Any]] = []
    try:
        rows = col.db.all(
            """
            select case when odid > 0 then odid else did end as deck_id,
              coalesce(sum(1.0 / case when ivl < 1 then 1 else ivl end), 0)
            from cards
            where type = 2 and queue >= 0
            group by deck_id
            """
        )
        daily_load = [{"deckId": _as_int(row[0]), "value": round(float(row[1] or 0), 3)} for row in rows]
    except Exception:
        daily_load = []

    return {
        "deckCatalog": catalog,
        "states": states,
        "noteCounts": note_counts,
        "due": due,
        "dailyLoad": daily_load,
        "today": today.isoformat(),
    }


def compact_json_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _overview(totals: dict[str, Any], previous: dict[str, Any] | None, buckets: list[dict[str, Any]]) -> dict[str, Any]:
    comparison = _comparison(totals, previous)
    insights: list[dict[str, Any]] = []
    if previous and totals["reviews"] >= 30 and previous["reviews"] >= 30:
        for key, insight_type, unit in (
            ("reviews", "reviews_changed", "percent"),
            ("successRate", "success_rate_changed", "percentage_points"),
            ("averageAnswerSeconds", "answer_time_changed", "seconds"),
        ):
            change = comparison.get(key)
            if isinstance(change, dict) and change.get("delta") not in (None, 0):
                insights.append({"type": insight_type, "direction": change["direction"], "value": change["delta"], "unit": unit})
    return {
        "kpis": {
            "reviews": totals["reviews"],
            "studySeconds": totals["studySeconds"],
            "successRate": totals["successRate"],
            "introducedCards": totals["newCards"],
            "activeDays": totals["activeDays"],
            "averageAnswerSeconds": totals["averageAnswerSeconds"],
        },
        "comparison": comparison,
        "series": buckets,
        "insights": insights[:3],
        "confidence": _confidence(totals["reviews"]),
    }


def _quality(totals: dict[str, Any], buckets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "series": [{
            "key": row["key"], "label": row["label"], "reviews": row["reviews"],
            "successRate": row["successRate"], "pass": row["pass"], "fail": row["fail"],
            "averageAnswerSeconds": row["averageAnswerSeconds"],
            "trueRetention": row["trueRetention"],
        } for row in buckets],
        "ratings": totals["ratings"],
        "pass": totals["pass"],
        "fail": totals["fail"],
        "successRate": totals["successRate"],
        "trueRetention": totals["trueRetention"],
        "confidence": _confidence(totals["reviews"]),
    }


def _load(totals: dict[str, Any], buckets: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "past": [{"key": row["key"], "label": row["label"], "reviews": row["reviews"], "studySeconds": row["studySeconds"], "introducedCards": row["introducedCards"]} for row in buckets],
        "averageActiveDayReviews": round(totals["reviews"] / totals["activeDays"], 2) if totals["activeDays"] else None,
        "dailyLoad": current["dailyLoad"],
        "overdue": current["overdue"],
        "futureDue": current["futureDue"],
        "assumptionCode": "current_schedule_no_future_new_or_failures",
    }


def _progress(totals: dict[str, Any], buckets: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "currentStates": current["states"],
        "totalCards": current["totalCards"],
        "totalNotes": current["totalNotes"],
        "introducedSeries": [{"key": row["key"], "label": row["label"], "introducedCards": row["introducedCards"], "reviews": row["reviews"]} for row in buckets],
        "introducedCards": totals["newCards"],
        "historicalStateSeriesAvailable": False,
    }


def _aggregate(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = {field: 0.0 if field in {"study_seconds", "total_answer_seconds"} else 0 for field in AGGREGATE_FIELDS}
    active_days = 0
    for row in rows:
        reviews = _as_int(row.get("reviews"))
        if reviews > 0:
            active_days += 1
        for field in AGGREGATE_FIELDS:
            if field in {"study_seconds", "total_answer_seconds"}:
                values[field] += _as_float(row.get(field))
            else:
                values[field] += _as_int(row.get(field))
    reviews = int(values["reviews"])
    passed = int(values["pass_count"])
    failed = int(values["fail_count"])
    answered = passed + failed
    young_pass = int(values["retention_young_pass"])
    young_fail = int(values["retention_young_fail"])
    mature_pass = int(values["retention_mature_pass"])
    mature_fail = int(values["retention_mature_fail"])
    return {
        "reviews": reviews,
        "newCards": int(values["new_cards"]),
        "activeDays": active_days,
        "studySeconds": round(float(values["study_seconds"])) if int(values["answer_time_count"]) else None,
        "averageAnswerSeconds": round(float(values["total_answer_seconds"]) / int(values["answer_time_count"]), 3) if int(values["answer_time_count"]) else None,
        "pass": passed,
        "fail": failed,
        "successRate": round(passed / answered, 4) if answered else None,
        "ratings": {"again": int(values["again"]), "hard": int(values["hard"]), "good": int(values["good"]), "easy": int(values["easy"])},
        "reviewTypes": {"learning": int(values["learning"]), "review": int(values["review"]), "relearning": int(values["relearning"]), "cram": int(values["cram"])},
        "trueRetention": {
            "overall": _ratio(young_pass + mature_pass, young_pass + young_fail + mature_pass + mature_fail),
            "young": _ratio(young_pass, young_pass + young_fail),
            "mature": _ratio(mature_pass, mature_pass + mature_fail),
            "youngPass": young_pass, "youngFail": young_fail,
            "maturePass": mature_pass, "matureFail": mature_fail,
            "sampleSize": young_pass + young_fail + mature_pass + mature_fail,
        },
    }


def _bucket_rows(rows: list[dict[str, Any]], granularity: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        parsed = _parse_date(row.get("date"))
        if parsed:
            grouped[_bucket_key(parsed, granularity)].append(row)
    result = []
    for key in sorted(grouped):
        aggregate = _aggregate(grouped[key])
        result.append({
            "key": key, "label": _bucket_label(key, granularity),
            "reviews": aggregate["reviews"], "studySeconds": aggregate["studySeconds"],
            "introducedCards": aggregate["newCards"], "activeDays": aggregate["activeDays"],
            "successRate": aggregate["successRate"], "averageAnswerSeconds": aggregate["averageAnswerSeconds"],
            "pass": aggregate["pass"], "fail": aggregate["fail"],
            "ratings": aggregate["ratings"], "trueRetention": aggregate["trueRetention"],
        })
    if len(result) > MAX_BUCKETS:
        return result[-MAX_BUCKETS:]
    return result


def _comparison(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if previous is None:
        return {"status": "unavailable", "reason": "comparison_disabled"}
    status = "available" if previous["reviews"] else "unavailable"
    return {
        "status": status,
        "reason": None if status == "available" else "no_previous_data",
        "reviews": _change(current["reviews"], previous["reviews"], relative=True),
        "studySeconds": _change(current["studySeconds"], previous["studySeconds"], relative=True),
        "successRate": _change(current["successRate"], previous["successRate"], relative=False, scale=100),
        "introducedCards": _change(current["newCards"], previous["newCards"], relative=True),
        "activeDays": _change(current["activeDays"], previous["activeDays"], relative=True),
        "averageAnswerSeconds": _change(current["averageAnswerSeconds"], previous["averageAnswerSeconds"], relative=False),
        "previousSampleSize": previous["reviews"],
    }


def _change(current: Any, previous: Any, *, relative: bool, scale: float = 1.0) -> dict[str, Any]:
    if current is None or previous is None or (relative and previous == 0):
        return {"current": current, "previous": previous, "delta": None, "direction": "unavailable"}
    delta = ((current - previous) / previous * 100) if relative else ((current - previous) * scale)
    rounded = round(delta, 2)
    return {"current": current, "previous": previous, "delta": rounded, "direction": "increase" if rounded > 0 else "decrease" if rounded < 0 else "same"}


def _deck_comparison_rows(
    deck_daily: list[dict[str, Any]], catalog: object, start: date | None, end: date,
    scope_ids: set[int] | None,
    previous_bounds: tuple[date, date] | None,
) -> list[dict[str, Any]]:
    catalog_rows = [row for row in _catalog_rows(catalog) if not row["filtered"]]
    roots = [row for row in catalog_rows if row["parentId"] is None]
    if scope_ids is not None:
        roots = [row for row in roots if _descendant_ids(row["deckId"], catalog_rows) & scope_ids]
    rows: list[dict[str, Any]] = []
    for root in roots:
        ids = _descendant_ids(root["deckId"], catalog_rows)
        if scope_ids is not None:
            ids &= scope_ids
        aggregate = _aggregate(_between([row for row in deck_daily if _as_int(row.get("deck_id")) in ids], start, end))
        previous = _aggregate(_between([row for row in deck_daily if _as_int(row.get("deck_id")) in ids], previous_bounds[0], previous_bounds[1])) if previous_bounds else None
        rows.append({
            "deckId": root["deckId"], "fullName": root["fullName"], "mode": "subtree",
            "reviews": aggregate["reviews"], "successRate": aggregate["successRate"],
            "averageAnswerSeconds": aggregate["averageAnswerSeconds"], "studySeconds": aggregate["studySeconds"],
            "introducedCards": aggregate["newCards"], "confidence": _deck_confidence(aggregate["reviews"]),
            "periodDelta": {
                "reviews": _change(aggregate["reviews"], previous["reviews"], relative=True),
                "successRate": _change(aggregate["successRate"], previous["successRate"], relative=False, scale=100),
            } if previous else None,
        })
    rows.sort(key=lambda row: (-row["reviews"], row["fullName"].casefold(), row["deckId"]))
    return rows[:MAX_DECK_ROWS]


def _current_scope_snapshot(current: dict[str, Any], scope_ids: set[int] | None) -> dict[str, Any]:
    state_counts: dict[str, int] = defaultdict(int)
    total_cards = 0
    for row in _rows(current.get("states")):
        deck_id = _as_int(row.get("deckId"))
        if scope_ids is not None and deck_id not in scope_ids:
            continue
        count = _as_int(row.get("cards"))
        state_counts[str(row.get("state") or "unknown")] += count
        total_cards += count
    total_notes = sum(
        _as_int(row.get("notes"))
        for row in _rows(current.get("noteCounts"))
        if scope_ids is None or _as_int(row.get("deckId")) in scope_ids
    )
    overdue = 0
    future: dict[int, dict[str, int]] = defaultdict(lambda: {"learning": 0, "review": 0, "relearning": 0})
    for row in _rows(current.get("due")):
        deck_id = _as_int(row.get("deckId"))
        if scope_ids is not None and deck_id not in scope_ids:
            continue
        offset = _as_int(row.get("dayOffset"))
        count = _as_int(row.get("count"))
        if offset < 0:
            overdue += count
        elif offset <= MAX_DUE_DAYS:
            category = str(row.get("category") or "review")
            if category in future[offset]:
                future[offset][category] += count
    daily_load = sum(_as_float(row.get("value")) for row in _rows(current.get("dailyLoad")) if scope_ids is None or _as_int(row.get("deckId")) in scope_ids)
    return {
        "states": {key: state_counts.get(key, 0) for key in ("unseen", "learning", "young", "mature", "suspended", "buried")},
        "totalCards": total_cards,
        "totalNotes": total_notes,
        "overdue": overdue,
        "dailyLoad": round(daily_load, 2),
        "futureDue": [
            {"dayOffset": offset, **future[offset], "total": sum(future[offset].values())}
            for offset in sorted(future)
        ],
    }


def _scope_ids(scope: dict[str, Any], catalog: object, display: dict[str, Any] | None) -> tuple[set[int] | None, dict[str, Any]]:
    rows = _catalog_rows(catalog)
    normal = {row["deckId"] for row in rows if not row["filtered"]}
    kind = scope["kind"]
    if kind == "all_collection":
        return None, {"kind": kind, "deckIds": sorted(normal), "label": "Вся коллекция"}
    if kind == "dashboard":
        selected = {_as_int(value) for value in (display or {}).get("selected_deck_ids", []) if _as_int(value) > 0}
        ids = normal & selected if selected else None
        return ids, {"kind": kind, "deckIds": sorted(ids if ids is not None else normal), "label": "Текущая область dashboard"}
    deck_id = _as_int(scope.get("deckId"))
    ids = {deck_id} if scope.get("mode") == "direct" else _descendant_ids(deck_id, rows)
    ids &= normal
    name = next((row["fullName"] for row in rows if row["deckId"] == deck_id), f"Deck {deck_id}")
    return ids, {"kind": kind, "deckId": deck_id, "mode": scope.get("mode"), "deckIds": sorted(ids), "label": name}


def _scope_daily_rows(daily: list[dict[str, Any]], deck_daily: list[dict[str, Any]], ids: set[int] | None) -> list[dict[str, Any]]:
    if ids is None:
        return daily
    grouped: dict[str, dict[str, Any]] = {}
    for row in deck_daily:
        if _as_int(row.get("deck_id")) not in ids:
            continue
        key = str(row.get("date") or "")
        target = grouped.setdefault(key, {"date": key, **{field: 0 for field in AGGREGATE_FIELDS}})
        for field in AGGREGATE_FIELDS:
            target[field] += _as_float(row.get(field)) if field in {"study_seconds", "total_answer_seconds"} else _as_int(row.get(field))
    return [grouped[key] for key in sorted(grouped)]


def _period_bounds(period: str, today: date, rows: list[dict[str, Any]]) -> tuple[date | None, date]:
    if period == "all":
        dates = [_parse_date(row.get("date")) for row in rows]
        dates = [value for value in dates if value]
        return (min(dates) if dates else None), today
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period)
    if days:
        return today - timedelta(days=days - 1), today
    return _subtract_year(today) + timedelta(days=1), today


def _coverage(rows: list[dict[str, Any]], start: date | None, end: date, totals: dict[str, Any]) -> dict[str, Any]:
    dates = sorted(value for value in (_parse_date(row.get("date")) for row in rows) if value)
    data_from = dates[0] if dates else None
    data_to = dates[-1] if dates else None
    if data_from is None:
        status = "unavailable"
    elif start is None or data_from <= start:
        status = "full"
    else:
        status = "partial"
    return {
        "dataFrom": data_from.isoformat() if data_from else None,
        "dataTo": data_to.isoformat() if data_to else None,
        "requestedFrom": start.isoformat() if start else None,
        "requestedTo": end.isoformat(),
        "coverage": status,
        "sampleSize": totals["reviews"],
        "activeDays": totals["activeDays"],
        "studyTimeSource": "revlog_estimate" if dates else None,
        "limitations": ["historical_deck_moves_not_reconstructed"],
        "calculationVersion": CALCULATION_VERSION,
    }


def _catalog_rows(value: object) -> list[dict[str, Any]]:
    raw = value if isinstance(value, list) else []
    basic = []
    name_to_id: dict[str, int] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        deck_id = _strict_positive_int(item.get("deck_id", item.get("deckId")))
        name = str(item.get("deck_name", item.get("fullName", ""))).strip()
        if deck_id and name:
            row = {"deckId": deck_id, "fullName": name, "filtered": bool(item.get("filtered"))}
            basic.append(row)
            name_to_id[name] = deck_id
    for row in basic:
        parent_name = row["fullName"].rsplit("::", 1)[0] if "::" in row["fullName"] else ""
        row["parentId"] = name_to_id.get(parent_name)
    return basic


def _descendant_ids(deck_id: int, catalog: list[dict[str, Any]]) -> set[int]:
    target = next((row for row in catalog if row["deckId"] == deck_id), None)
    if not target:
        return set()
    prefix = target["fullName"] + "::"
    return {row["deckId"] for row in catalog if row["deckId"] == deck_id or row["fullName"].startswith(prefix)}


def _between(rows: list[dict[str, Any]], start: date | None, end: date) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        parsed = _parse_date(row.get("date"))
        if parsed and parsed <= end and (start is None or parsed >= start):
            result.append(row)
    return result


def _rows(value: object) -> list[dict[str, Any]]:
    return [dict(row) for row in value] if isinstance(value, list) else []


def _resolve_granularity(period: str, granularity: str) -> str:
    if period == "all":
        return "month"
    if granularity != "auto":
        if period == "1y" and granularity == "day":
            return "week"
        return granularity
    return "day" if period in {"7d", "30d"} else "week" if period == "90d" else "month"


def _bucket_key(value: date, granularity: str) -> str:
    if granularity == "month":
        return value.strftime("%Y-%m")
    if granularity == "week":
        return (value - timedelta(days=value.weekday())).isoformat()
    return value.isoformat()


def _bucket_label(key: str, granularity: str) -> str:
    return key if granularity != "week" else f"Неделя {key}"


def _subtract_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _scheduler_day(col: Any) -> int:
    try:
        return _as_int(col.sched.today)
    except Exception:
        return 0


def _due_offset(queue: int, raw_due: int, scheduler_day: int, today: date) -> int | None:
    if queue == 2:
        return raw_due - scheduler_day
    if queue in {1, 3}:
        try:
            due_date = datetime.fromtimestamp(raw_due).date()
        except (OSError, OverflowError, ValueError):
            return None
        return (due_date - today).days
    return None


def _due_category(card_type: int) -> str:
    return "learning" if card_type == 1 else "relearning" if card_type == 3 else "review"


def _confidence(sample: int) -> str:
    return "insufficient" if sample < 30 else "preliminary" if sample < 100 else "sufficient"


def _deck_confidence(sample: int) -> str:
    return "insufficient" if sample < 10 else "preliminary" if sample < 100 else "sufficient"


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _bounds_json(start: date | None, end: date) -> dict[str, str | None]:
    return {"start": start.isoformat() if start else None, "end": end.isoformat()}


def _dashboard_scope_metadata(display: dict[str, Any] | None) -> dict[str, Any]:
    selected = [_as_int(value) for value in (display or {}).get("selected_deck_ids", []) if _as_int(value) > 0]
    return {"selectedDeckIds": selected, "includeChildDecks": bool((display or {}).get("include_child_decks", True))}


def _availability(status: dict[str, Any], snapshot: object) -> str:
    if status.get("isBuilding"):
        return "building"
    if status.get("status") in {"stale", "error"}:
        return "partial"
    return "available" if isinstance(snapshot, dict) and snapshot.get("daily") else "unavailable"


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 and str(value).strip() == str(parsed) else None


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
