"""Adapt cached all-time aggregates into dashboard report sections."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
import time
from typing import Any

from .stats_cache import CACHE_SCHEMA_VERSION, DECK_HISTORY_NOTE


SECONDS_IN_DAY = 86_400
MIN_BASELINE_DAYS = 3
COMPARISON_HISTORY_DAYS = 60
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
SHORT_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
COUNT_PARITY_METRICS = {
    "total_reviews",
    "new_cards",
    "again",
    "hard",
    "good",
    "easy",
    "pass",
    "fail",
    "active_days",
}


def merge_cached_report_parts(
    live_report: dict[str, Any],
    cache_parts: dict[str, Any],
) -> dict[str, Any]:
    """Overlay cache-backed sections without erasing live-only report fields."""

    if not isinstance(live_report, dict):
        return {}
    if not isinstance(cache_parts, dict):
        return dict(live_report)

    merged = dict(live_report)
    data_source = str(cache_parts.get("dataSource") or merged.get("dataSource") or "legacy")
    merged["dataSource"] = data_source

    cache_info = cache_parts.get("cache")
    if isinstance(cache_info, dict):
        merged["cache"] = _merge_non_empty_dict(merged.get("cache"), cache_info)

    cache_debug = cache_parts.get("cacheDebug")
    if isinstance(cache_debug, dict):
        merged["cacheDebug"] = _merge_non_empty_dict(merged.get("cacheDebug"), cache_debug)

    performance = cache_parts.get("performance")
    if isinstance(performance, dict):
        merged["performance"] = _merge_non_empty_dict(merged.get("performance"), performance)

    if data_source == "mixed":
        activity = cache_parts.get("activity")
        if isinstance(activity, dict):
            merged["activity"] = _merge_non_empty_dict(merged.get("activity"), activity)

        comparison = cache_parts.get("comparison")
        if isinstance(comparison, dict):
            merged["comparison"] = _merge_non_empty_dict(merged.get("comparison"), comparison)

    return merged


def should_use_cache_for_report(
    config: dict[str, Any],
    cache_status: dict[str, Any],
) -> tuple[bool, str | None]:
    if not bool(config.get("use_stats_cache_for_report", False)):
        return False, "feature_flag_disabled"
    status = str(cache_status.get("status") or "empty")
    if status != "ready":
        return False, f"cache_not_ready:{status}"
    if _as_int(cache_status.get("version")) not in {0, CACHE_SCHEMA_VERSION}:
        return False, "cache_schema_mismatch"
    if _as_int(cache_status.get("cachedDays")) <= 0:
        return False, "cache_empty"
    return True, None


def build_cached_report_parts(
    cache_manager: Any,
    period: str,
    profile_config: dict[str, Any],
    legacy_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    status = _safe_cache_status(cache_manager)
    use_cache, fallback_reason = should_use_cache_for_report(profile_config, status)
    if not use_cache:
        return _fallback_parts(status, fallback_reason, started_at)

    cache_read_started = time.monotonic()
    try:
        snapshot = cache_manager.report_snapshot()
    except Exception as error:
        return _fallback_parts(
            status,
            f"cache_read_error:{_short_error(error)}",
            started_at,
        )
    cache_read_ms = _elapsed_ms(cache_read_started)

    status = snapshot.get("status") if isinstance(snapshot.get("status"), dict) else status
    use_cache, fallback_reason = should_use_cache_for_report(profile_config, status)
    if not use_cache:
        parts = _fallback_parts(status, fallback_reason, started_at)
        parts["performance"]["cacheReadMs"] = cache_read_ms
        return parts

    daily_rows = _clean_daily_rows(snapshot.get("daily"))
    if not daily_rows:
        parts = _fallback_parts(status, "cache_empty", started_at)
        parts["performance"]["cacheReadMs"] = cache_read_ms
        return parts

    deck_daily_rows = _clean_deck_daily_rows(snapshot.get("deckDaily"))
    active_decks_by_date = _active_decks_by_date(deck_daily_rows)
    today_key = _today_key(profile_config)
    selected_rows = _period_rows(daily_rows, period, profile_config, today_key)
    activity = _activity_from_rows(selected_rows, today_key)
    comparison = _comparison_from_rows(daily_rows, active_decks_by_date, today_key)
    period_summary = _summary_from_rows(selected_rows)
    cache_info = _cache_info(
        status,
        data_source="mixed",
        used_for=["activity.days", "activity.summary", "comparison"],
        fallback_reason=None,
    )
    cache_info["periodSummary"] = period_summary
    cache_info["cacheDeckSummary"] = {
        "available": bool(deck_daily_rows),
        "limitation": DECK_HISTORY_NOTE,
    }
    cache_info["performance"] = {
        "cacheReadMs": cache_read_ms,
        "cacheAdaptMs": _elapsed_ms(started_at),
    }
    return {
        "dataSource": "mixed",
        "activity": activity,
        "comparison": comparison,
        "cache": cache_info,
        "cacheDebug": _parity_debug(legacy_report, period_summary),
        "performance": {
            "cacheReadMs": cache_read_ms,
            "reportBuildMs": _elapsed_ms(started_at),
        },
    }


def _safe_cache_status(cache_manager: Any) -> dict[str, Any]:
    try:
        status = cache_manager.status()
        return status if isinstance(status, dict) else {"status": "error"}
    except Exception as error:
        return {"status": "error", "error": _short_error(error)}


def _fallback_parts(
    status: dict[str, Any],
    fallback_reason: str | None,
    started_at: float,
) -> dict[str, Any]:
    return {
        "dataSource": "legacy",
        "cache": _cache_info(
            status,
            data_source="legacy",
            used_for=[],
            fallback_reason=fallback_reason,
        ),
        "cacheDebug": {
            "parityChecked": False,
            "reason": fallback_reason,
            "mismatches": [],
        },
        "performance": {
            "cacheReadMs": 0,
            "reportBuildMs": _elapsed_ms(started_at),
        },
    }


def _cache_info(
    status: dict[str, Any],
    data_source: str,
    used_for: list[str],
    fallback_reason: str | None,
) -> dict[str, Any]:
    return {
        "status": str(status.get("status") or "empty"),
        "dataSource": data_source,
        "usedFor": used_for,
        "version": _as_int(status.get("version")),
        "updatedAt": _as_int(status.get("updatedAt")),
        "cachedDays": _as_int(status.get("cachedDays")),
        "cachedDeckDays": _as_int(status.get("cachedDeckDays")),
        "isBuilding": bool(status.get("isBuilding")),
        "error": _short_error(status.get("error")) if status.get("error") else None,
        "lastError": _short_error(status.get("lastError")) if status.get("lastError") else None,
        "lastRevlogId": _as_int(status.get("lastRevlogId")),
        "fallbackReason": fallback_reason,
        "limitations": list(status.get("limitations") or [DECK_HISTORY_NOTE]),
    }


def _merge_non_empty_dict(live_value: Any, cache_value: dict[str, Any]) -> dict[str, Any]:
    merged = dict(live_value) if isinstance(live_value, dict) else {}
    for key, value in cache_value.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = _merge_non_empty_dict(merged.get(key), value)
            if nested:
                merged[key] = nested
            continue
        if _cache_value_present(value):
            merged[key] = value
    return merged


def _cache_value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _clean_daily_rows(value: Any) -> list[dict[str, Any]]:
    rows = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        date_key = str(row.get("date") or "")
        if not _is_date_key(date_key):
            continue
        reviews = _as_int(row.get("reviews"))
        fail = _as_int(row.get("fail_count") or row.get("again"))
        pass_count = _as_int(row.get("pass_count")) or max(0, reviews - fail)
        total_answer_seconds = _as_float(row.get("total_answer_seconds"))
        study_seconds = _as_int(row.get("study_seconds"))
        rows.append(
            {
                "date": date_key,
                "reviews": reviews,
                "new_cards": _as_int(row.get("new_cards")),
                "learning": _as_int(row.get("learning")),
                "review": _as_int(row.get("review")),
                "relearning": _as_int(row.get("relearning")),
                "cram": _as_int(row.get("cram")),
                "again": fail,
                "hard": _as_int(row.get("hard")),
                "good": _as_int(row.get("good")),
                "easy": _as_int(row.get("easy")),
                "pass": pass_count,
                "fail": fail,
                "study_seconds": study_seconds,
                "total_answer_seconds": total_answer_seconds,
            }
        )
    return sorted(rows, key=lambda item: item["date"])


def _clean_deck_daily_rows(value: Any) -> list[dict[str, Any]]:
    rows = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        date_key = str(row.get("date") or "")
        if not _is_date_key(date_key):
            continue
        rows.append(
            {
                "date": date_key,
                "deck_id": _as_int(row.get("deck_id")),
                "reviews": _as_int(row.get("reviews")),
            }
        )
    return rows


def _period_rows(
    daily_rows: list[dict[str, Any]],
    period: str,
    config: dict[str, Any],
    today_key: str,
) -> list[dict[str, Any]]:
    by_date = {row["date"]: row for row in daily_rows}
    if period == "all_time":
        start_key = daily_rows[0]["date"]
        end_key = max(daily_rows[-1]["date"], today_key)
    else:
        start_key = _date_from_config(config.get("period_start_date")) or daily_rows[0]["date"]
        end_key = _date_from_config(config.get("period_end_date")) or today_key
        if start_key > end_key:
            start_key, end_key = end_key, start_key
    return [_row_with_zeroes(date_key, by_date.get(date_key)) for date_key in _date_range(start_key, end_key)]


def _activity_from_rows(rows: list[dict[str, Any]], today_key: str) -> dict[str, Any]:
    active_days = sum(1 for row in rows if _as_int(row.get("reviews")) > 0)
    total_days = len(rows)
    active_dates = {row["date"] for row in rows if _as_int(row.get("reviews")) > 0}
    best = max(rows, key=lambda row: (_as_int(row.get("reviews")), row["date"]), default=None)
    best_day = "Нет данных"
    if best and _as_int(best.get("reviews")) > 0:
        best_day = f"{best['date']}, {_as_int(best.get('reviews'))} reviews"
    return {
        "available": bool(rows),
        "activeDays": active_days,
        "missedDays": max(0, total_days - active_days),
        "currentStreak": _current_streak(active_dates, today_key),
        "bestStreak": _longest_streak(rows),
        "bestDay": best_day,
        "weekdayAverage": _weekday_average(rows),
        "days": [_activity_day(row) for row in rows],
    }


def _activity_day(row: dict[str, Any]) -> dict[str, Any]:
    reviews = _as_int(row.get("reviews"))
    fail = _as_int(row.get("fail"))
    pass_count = _as_int(row.get("pass")) or max(0, reviews - fail)
    study_seconds = _as_int(row.get("study_seconds"))
    total_answer_seconds = _as_float(row.get("total_answer_seconds"))
    return {
        "date": str(row.get("date") or ""),
        "reviews": reviews,
        "newCards": _as_int(row.get("new_cards")),
        "learning": _as_int(row.get("learning")),
        "review": _as_int(row.get("review")),
        "relearning": _as_int(row.get("relearning")),
        "mature": _as_int(row.get("review")),
        "again": fail,
        "hard": _as_int(row.get("hard")),
        "good": _as_int(row.get("good")),
        "easy": _as_int(row.get("easy")),
        "pass": pass_count,
        "fail": fail,
        "passRate": round(pass_count / reviews, 4) if reviews > 0 else None,
        "failRate": round(fail / reviews, 4) if reviews > 0 else None,
        "studySeconds": study_seconds,
        "avgAnswerSeconds": round(total_answer_seconds / reviews, 1) if reviews > 0 and total_answer_seconds > 0 else None,
    }


def _summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reviews = sum(_as_int(row.get("reviews")) for row in rows)
    fail = sum(_as_int(row.get("fail")) for row in rows)
    pass_count = sum(_as_int(row.get("pass")) for row in rows)
    study_seconds = sum(_as_int(row.get("study_seconds")) for row in rows)
    total_answer_seconds = sum(_as_float(row.get("total_answer_seconds")) for row in rows)
    active_days = sum(1 for row in rows if _as_int(row.get("reviews")) > 0)
    return {
        "total_reviews": reviews,
        "new_cards": sum(_as_int(row.get("new_cards")) for row in rows),
        "again": fail,
        "hard": sum(_as_int(row.get("hard")) for row in rows),
        "good": sum(_as_int(row.get("good")) for row in rows),
        "easy": sum(_as_int(row.get("easy")) for row in rows),
        "pass": pass_count,
        "fail": fail,
        "pass_rate": round(pass_count / reviews, 4) if reviews > 0 else None,
        "fail_rate": round(fail / reviews, 4) if reviews > 0 else None,
        "study_seconds": study_seconds,
        "active_days": active_days,
        "average_reviews_per_active_day": round(reviews / active_days, 1) if active_days > 0 else 0.0,
        "average_study_seconds_per_active_day": round(study_seconds / active_days, 1) if active_days > 0 else 0.0,
        "average_answer_seconds": round(total_answer_seconds / reviews, 1) if reviews > 0 and total_answer_seconds > 0 else None,
    }


def _comparison_from_rows(
    daily_rows: list[dict[str, Any]],
    active_decks_by_date: dict[str, int],
    today_key: str,
) -> dict[str, Any]:
    by_date = {row["date"]: row for row in daily_rows}
    today = _parse_date(today_key)
    start = today - timedelta(days=COMPARISON_HISTORY_DAYS - 1)
    days = [
        _comparison_row(_row_with_zeroes(day.isoformat(), by_date.get(day.isoformat())), active_decks_by_date)
        for day in _date_objects(start, today)
    ]
    by_key = {row["date"]: row for row in days}
    previous_days = [row for row in days if row["date"] < today_key]
    active_history_days = [row for row in previous_days if _as_int(row.get("reviews")) > 0]
    yesterday_key = (today - timedelta(days=1)).isoformat()
    same_weekday_key = (today - timedelta(days=7)).isoformat()
    current_week, previous_week = _week_windows(days, today_key)
    current_month, previous_month = _month_windows(days, today_key)
    baselines = {
        "yesterday": _daily_stats(by_key.get(yesterday_key), "Вчера"),
        "avg7": _average_daily_stats(previous_days[-7:], "Последние 7 дней"),
        "avg30": _average_daily_stats(previous_days[-30:], "Последние 30 дней"),
        "sameWeekdayLastWeek": _daily_stats(by_key.get(same_weekday_key), "Этот день прошлой недели"),
        "currentWeek": _aggregate_stats(current_week, "Эта неделя"),
        "previousWeek": _aggregate_stats(previous_week, "Прошлая неделя"),
        "currentMonth": _aggregate_stats(current_month, "Этот месяц"),
        "previousMonth": _aggregate_stats(previous_month, "Прошлый месяц"),
    }
    today_stats = _daily_stats(by_key.get(today_key), "Сегодня")
    available = len(active_history_days) >= MIN_BASELINE_DAYS
    return {
        "available": available,
        "message": "" if available else "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.",
        "today": today_stats,
        "baselines": baselines,
        "comparisons": _comparison_payloads(today_stats, baselines),
        "insights": _comparison_insights(today_stats, baselines, available),
        "source": {
            "primary": "stats_cache",
            "history_days": COMPARISON_HISTORY_DAYS,
            "active_history_days": len(active_history_days),
            "min_baseline_days": MIN_BASELINE_DAYS,
        },
    }


def _comparison_row(row: dict[str, Any], active_decks_by_date: dict[str, int]) -> dict[str, Any]:
    result = dict(row)
    result["active_decks"] = active_decks_by_date.get(str(row.get("date") or ""), 0)
    return result


def _daily_stats(row: dict[str, Any] | None, label: str) -> dict[str, Any]:
    if row is None:
        return _empty_daily_stats("", label)
    reviews = _as_int(row.get("reviews"))
    fail = _as_int(row.get("fail"))
    pass_count = _as_int(row.get("pass")) or max(0, reviews - fail)
    study_seconds = _as_int(row.get("study_seconds"))
    total_answer_seconds = _as_float(row.get("total_answer_seconds"))
    return {
        "date": str(row.get("date") or ""),
        "label": str(row.get("label") or row.get("date") or label),
        "reviews": reviews,
        "newCards": _as_int(row.get("new_cards")),
        "pass": pass_count,
        "fail": fail,
        "hard": _as_int(row.get("hard")),
        "easy": _as_int(row.get("easy")),
        "studySeconds": study_seconds,
        "studyMinutes": round(study_seconds / 60),
        "avgAnswerSeconds": round(total_answer_seconds / reviews, 1) if reviews > 0 and total_answer_seconds > 0 else None,
        "activeDecks": _as_int(row.get("active_decks")),
        "passRate": round(pass_count / reviews, 4) if reviews > 0 else None,
        "failRate": round(fail / reviews, 4) if reviews > 0 else None,
    }


def _empty_daily_stats(date_key: str, label: str) -> dict[str, Any]:
    return {
        "date": date_key,
        "label": label,
        "reviews": 0,
        "newCards": 0,
        "pass": 0,
        "fail": 0,
        "hard": 0,
        "easy": 0,
        "studySeconds": 0,
        "studyMinutes": 0,
        "avgAnswerSeconds": None,
        "activeDecks": 0,
        "passRate": None,
        "failRate": None,
    }


def _average_daily_stats(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        return _empty_daily_stats("", label)
    count = len(rows)
    aggregate = _aggregate_base(rows)
    aggregate["date"] = ""
    aggregate["label"] = label
    for key in ("reviews", "new_cards", "pass", "fail", "hard", "easy", "study_seconds", "total_answer_seconds", "active_decks"):
        aggregate[key] = round(_as_float(aggregate.get(key)) / count)
    return _daily_stats(aggregate, label)


def _aggregate_stats(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        return _empty_daily_stats("", label)
    aggregate = _aggregate_base(rows)
    aggregate["date"] = ""
    aggregate["label"] = label
    aggregate["active_decks"] = sum(1 for row in rows if _as_int(row.get("reviews")) > 0)
    return _daily_stats(aggregate, label)


def _aggregate_base(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    return {
        "reviews": sum(_as_int(row.get("reviews")) for row in rows),
        "new_cards": sum(_as_int(row.get("new_cards")) for row in rows),
        "pass": sum(_as_int(row.get("pass")) for row in rows),
        "fail": sum(_as_int(row.get("fail")) for row in rows),
        "hard": sum(_as_int(row.get("hard")) for row in rows),
        "easy": sum(_as_int(row.get("easy")) for row in rows),
        "study_seconds": sum(_as_int(row.get("study_seconds")) for row in rows),
        "total_answer_seconds": sum(_as_float(row.get("total_answer_seconds")) for row in rows),
        "active_decks": sum(_as_int(row.get("active_decks")) for row in rows),
    }


def _comparison_payloads(today: dict[str, Any], baselines: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "yesterday": _comparison_payload(today, baselines["yesterday"]),
        "avg7": _comparison_payload(today, baselines["avg7"]),
        "avg30": _comparison_payload(today, baselines["avg30"]),
        "sameWeekdayLastWeek": _comparison_payload(today, baselines["sameWeekdayLastWeek"]),
        "week": _comparison_payload(baselines["currentWeek"], baselines["previousWeek"]),
        "month": _comparison_payload(baselines["currentMonth"], baselines["previousMonth"]),
    }


def _comparison_payload(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "reviews": _metric_delta(current.get("reviews"), baseline.get("reviews")),
        "newCards": _metric_delta(current.get("newCards"), baseline.get("newCards")),
        "studyMinutes": _metric_delta(current.get("studyMinutes"), baseline.get("studyMinutes")),
        "passRate": _rate_delta(current.get("passRate"), baseline.get("passRate")),
        "failRate": _rate_delta(current.get("failRate"), baseline.get("failRate")),
        "avgAnswerSeconds": _metric_delta(current.get("avgAnswerSeconds"), baseline.get("avgAnswerSeconds")),
        "activeDecks": _metric_delta(current.get("activeDecks"), baseline.get("activeDecks")),
    }


def _metric_delta(current: Any, baseline: Any) -> dict[str, Any]:
    current_value = _number_or_none(current)
    baseline_value = _number_or_none(baseline)
    if current_value is None or baseline_value is None:
        return {"delta": None, "percentDelta": None}
    delta = current_value - baseline_value
    percent_delta = (delta / baseline_value * 100) if baseline_value > 0 else None
    return {"delta": round(delta, 1), "percentDelta": round(percent_delta, 1) if percent_delta is not None else None}


def _rate_delta(current: Any, baseline: Any) -> dict[str, Any]:
    current_value = _number_or_none(current)
    baseline_value = _number_or_none(baseline)
    if current_value is None or baseline_value is None:
        return {"deltaPp": None}
    return {"deltaPp": round((current_value - baseline_value) * 100, 1)}


def _comparison_insights(today: dict[str, Any], baselines: dict[str, dict[str, Any]], available: bool) -> list[dict[str, Any]]:
    if not available:
        return [
            {
                "severity": "neutral",
                "title": "История ещё короткая",
                "text": "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.",
                "metric": "history",
            }
        ]
    avg7 = baselines["avg7"]
    reviews = _as_int(today.get("reviews"))
    avg_reviews = _as_int(avg7.get("reviews"))
    pass_rate = _number_or_none(today.get("passRate"))
    avg_pass_rate = _number_or_none(avg7.get("passRate"))
    fail_delta = _rate_delta(today.get("failRate"), avg7.get("failRate")).get("deltaPp")
    if avg_reviews > 0 and reviews >= avg_reviews and pass_rate is not None and avg_pass_rate is not None and pass_rate >= avg_pass_rate - 0.02:
        return [{"severity": "positive", "title": "Продуктивный день", "text": "Объём около нормы или выше, а качество не просело.", "metric": "reviews"}]
    if fail_delta is not None and fail_delta >= 3:
        return [{"severity": "warning", "title": "Качество просело", "text": "Fail rate выше 7-дневной нормы на 3+ п.п.; новые лучше давать осторожно.", "metric": "failRate"}]
    return [{"severity": "neutral", "title": "День около нормы", "text": "Сегодняшняя сессия близка к вашему обычному темпу.", "metric": "summary"}]


def _parity_debug(legacy_report: dict[str, Any] | None, cache_summary: dict[str, Any]) -> dict[str, Any]:
    legacy_summary = _legacy_summary(legacy_report)
    if legacy_summary is None:
        return {"parityChecked": False, "reason": "legacy_metrics_unavailable", "mismatches": []}
    mismatches = []
    for metric, legacy_value in legacy_summary.items():
        cache_value = cache_summary.get(metric)
        if cache_value is None:
            continue
        legacy_number = _as_float(legacy_value)
        cache_number = _as_float(cache_value)
        delta = cache_number - legacy_number
        allowed_drift = 2 if metric == "study_seconds" else 0
        if metric in COUNT_PARITY_METRICS:
            legacy_number = round(legacy_number)
            cache_number = round(cache_number)
            delta = cache_number - legacy_number
        if abs(delta) > allowed_drift:
            mismatches.append(
                {
                    "metric": metric,
                    "legacy": legacy_number,
                    "cache": cache_number,
                    "delta": delta,
                }
            )
    return {"parityChecked": True, "mismatches": mismatches}


def _legacy_summary(legacy_report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(legacy_report, dict):
        return None
    metrics = legacy_report.get("metrics") if isinstance(legacy_report.get("metrics"), dict) else legacy_report
    if not isinstance(metrics, dict):
        return None
    distribution = metrics.get("answer_distribution") if isinstance(metrics.get("answer_distribution"), dict) else {}
    heatmap = metrics.get("heatmap") if isinstance(metrics.get("heatmap"), dict) else {}
    return {
        "total_reviews": _as_int(metrics.get("total_reviews")),
        "new_cards": _as_int(metrics.get("new_cards")),
        "again": _as_int(distribution.get("again") or metrics.get("again_count") or metrics.get("fail_count")),
        "hard": _as_int(distribution.get("hard")),
        "good": _as_int(distribution.get("good")),
        "easy": _as_int(distribution.get("easy")),
        "pass": _as_int(metrics.get("pass_count")),
        "fail": _as_int(metrics.get("fail_count")),
        "study_seconds": _as_int(metrics.get("total_seconds")),
        "active_days": _as_int(heatmap.get("active_days")),
    }


def _active_decks_by_date(rows: list[dict[str, Any]]) -> dict[str, int]:
    buckets: dict[str, set[int]] = {}
    for row in rows:
        if _as_int(row.get("reviews")) <= 0:
            continue
        buckets.setdefault(str(row.get("date") or ""), set()).add(_as_int(row.get("deck_id")))
    return {date_key: len(deck_ids) for date_key, deck_ids in buckets.items()}


def _row_with_zeroes(date_key: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "date": date_key,
            "reviews": 0,
            "new_cards": 0,
            "learning": 0,
            "review": 0,
            "relearning": 0,
            "cram": 0,
            "again": 0,
            "hard": 0,
            "good": 0,
            "easy": 0,
            "pass": 0,
            "fail": 0,
            "study_seconds": 0,
            "total_answer_seconds": 0.0,
        }
    return dict(row)


def _weekday_average(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = {index: [] for index in range(7)}
    for row in rows:
        try:
            weekday = _parse_date(str(row.get("date") or "")).weekday()
        except ValueError:
            continue
        buckets[weekday].append(_as_int(row.get("reviews")))
    return [
        {
            "day": SHORT_WEEKDAY_NAMES[index],
            "reviews": round(sum(values) / len(values), 1) if values else 0.0,
            "activeRate": round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0,
        }
        for index, values in buckets.items()
    ]


def _current_streak(active_dates: set[str], today_key: str) -> int:
    today = _parse_date(today_key)
    if today_key in active_dates:
        cursor = today
    elif (today - timedelta(days=1)).isoformat() in active_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor.isoformat() in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(rows: list[dict[str, Any]]) -> int:
    longest = 0
    current = 0
    for row in rows:
        if _as_int(row.get("reviews")) > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _week_windows(rows: list[dict[str, Any]], today_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    today = _parse_date(today_key)
    week_start = today - timedelta(days=today.weekday())
    previous_start = week_start - timedelta(days=7)
    current = [row for row in rows if week_start.isoformat() <= row["date"] <= today_key]
    previous = [row for row in rows if previous_start.isoformat() <= row["date"] < week_start.isoformat()]
    return current, previous


def _month_windows(rows: list[dict[str, Any]], today_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    today = _parse_date(today_key)
    month_start = today.replace(day=1)
    previous_end = month_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    current = [row for row in rows if month_start.isoformat() <= row["date"] <= today_key]
    previous = [row for row in rows if previous_start.isoformat() <= row["date"] <= previous_end.isoformat()]
    return current, previous


def _date_range(start_key: str, end_key: str) -> list[str]:
    start = _parse_date(start_key)
    end = _parse_date(end_key)
    if end < start:
        return []
    return [day.isoformat() for day in _date_objects(start, end)]


def _date_objects(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _today_key(config: dict[str, Any]) -> str:
    configured = _date_from_config(config.get("today_date"))
    return configured or date.today().isoformat()


def _date_from_config(value: Any) -> str | None:
    text = str(value or "")
    return text if _is_date_key(text) else None


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _is_date_key(value: str) -> bool:
    try:
        _parse_date(value)
    except ValueError:
        return False
    return len(value) == 10


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in {float("inf"), float("-inf")} else None


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _as_float(value: Any) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if number != number or number in {float("inf"), float("-inf")}:
        return 0.0
    return number


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.monotonic() - started_at) * 1000)))


def _short_error(error: Any) -> str:
    message = str(error or "unknown_error").strip().splitlines()[0]
    return message[:120] or "unknown_error"
