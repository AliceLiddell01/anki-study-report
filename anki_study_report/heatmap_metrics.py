"""Calendar activity and streak metrics for Anki Study Report.

The implementation is intentionally independent from Review Heatmap.  A small
read-only probe records whether the local Review Heatmap controller/config is
available, but all report numbers are calculated from Anki's own ``revlog``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from .metrics import (
    ANSWER_TIME_CAP_MS,
    EARLIER_REVIEW_FILTER_SQL,
    REVLOG_REVIEW_FILTER_SQL,
    _as_int,
    _deck_filter_sql,
    _expand_deck_ids,
    _to_revlog_ms,
)


SECONDS_IN_DAY = 86_400
MAX_ACTIVITY_DAYS = 400
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def collect_heatmap_metrics(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Collect read-only calendar activity metrics from ``revlog``.

    Dates are grouped by Anki day, using the collection's rollover setting when
    available.  Current streak includes today when there is activity today; if
    today is still empty, a streak ending yesterday remains current.
    """

    start_ms = _to_revlog_ms(start_ts)
    end_ms = _to_revlog_ms(end_ts)
    if end_ms <= start_ms:
        return _empty_heatmap_metrics()

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)
    day_context = _anki_day_context(col)
    calendar_start_ms, limited = _limited_calendar_start_ms(start_ms, end_ms)
    rows = _daily_rows(
        col,
        calendar_start_ms,
        end_ms,
        expanded_deck_ids,
        day_context["rollover_hours"],
    )
    reviews_by_date = {str(row["date"]): row for row in rows}
    dates = _calendar_dates(calendar_start_ms, end_ms, day_context["rollover_hours"])
    reviews_by_day = [
        _day_with_zeroes(date_key, reviews_by_date.get(date_key))
        for date_key in dates
    ]

    active_days = sum(1 for day in reviews_by_day if _as_int(day.get("reviews")) > 0)
    total_days = len(reviews_by_day)
    missed_days = max(0, total_days - active_days)
    active_dates = {
        str(day["date"])
        for day in reviews_by_day
        if _as_int(day.get("reviews")) > 0
    }

    current_streak = _current_streak(active_dates, day_context["today_date"])
    longest_streak = _longest_streak(reviews_by_day)
    best_days = _best_days(reviews_by_day)
    weekday_average = _weekday_average(reviews_by_day)

    return {
        "available": True,
        "active_days": active_days,
        "missed_days": missed_days,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_days": total_days,
        "reviews_by_day": reviews_by_day,
        "best_days": best_days,
        "weekday_average": weekday_average,
        "stability": _stability_summary(
            active_days,
            total_days,
            current_streak,
            missed_days,
            weekday_average,
        ),
        "source": {
            "primary": "revlog",
            "calendar_limited": limited,
            "max_days": MAX_ACTIVITY_DAYS,
            "anki_rollover_hour": day_context["rollover_hours"],
            "streak_rule": "today_or_yesterday",
            "review_heatmap": _review_heatmap_probe(),
        },
    }


def diagnose_review_heatmap_personal() -> str:
    """Return a short read-only diagnostic for the optional Review Heatmap add-on."""

    probe = _review_heatmap_probe()
    if not probe.get("detected"):
        return "\n".join(
            [
                "Review Heatmap Personal",
                "Статус: не обнаружен.",
                "Метрики активности будут считаться напрямую из revlog.",
            ]
        )

    controller = "да" if probe.get("controller_available") else "нет"
    config = "да" if probe.get("config_available") else "нет"
    return "\n".join(
        [
            "Review Heatmap Personal",
            "Статус: обнаружен.",
            f"Контроллер mw._review_heatmap: {controller}.",
            f"Конфигурация add-on 1771074083: {config}.",
            "Использование в отчёте: только read-only detection; метрики считаются из revlog.",
        ]
    )


def _empty_heatmap_metrics() -> dict[str, Any]:
    return {
        "available": False,
        "active_days": 0,
        "missed_days": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "total_days": 0,
        "reviews_by_day": [],
        "best_days": [],
        "weekday_average": {name: 0.0 for name in WEEKDAY_NAMES},
        "stability": "Активность за выбранный период пока не найдена.",
        "source": {
            "primary": "revlog",
            "calendar_limited": False,
            "max_days": MAX_ACTIVITY_DAYS,
            "anki_rollover_hour": None,
            "streak_rule": "today_or_yesterday",
            "review_heatmap": {"detected": False},
        },
    }


def _anki_day_context(col: Any) -> dict[str, Any]:
    rollover_hours = 4
    try:
        rollover_hours = int(col.conf.get("rollover", rollover_hours))
    except Exception:
        try:
            rollover_hours = int(datetime.fromtimestamp(col.crt).hour)
        except Exception:
            pass

    now = datetime.now()
    today_date = _date_key_for_timestamp(now.timestamp(), rollover_hours)
    return {
        "rollover_hours": rollover_hours,
        "today_date": today_date,
    }


def _limited_calendar_start_ms(start_ms: int, end_ms: int) -> tuple[int, bool]:
    span_days = max(0, (end_ms - start_ms) // (SECONDS_IN_DAY * 1000))
    if span_days <= MAX_ACTIVITY_DAYS:
        return start_ms, False
    return end_ms - MAX_ACTIVITY_DAYS * SECONDS_IN_DAY * 1000, True


def _daily_rows(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
    rollover_hours: int,
) -> list[dict[str, Any]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select
            strftime('%Y-%m-%d', r.id / 1000 - ?, 'unixepoch', 'localtime') as day,
            count(*) as reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again,
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
            end) as new_cards,
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
        group by day
        order by day
        """,
        rollover_hours * 3600,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )

    return [
        {
            "date": str(day),
            "reviews": _as_int(reviews),
            "new_cards": _as_int(new_cards),
            "again": _as_int(again),
            "total_seconds": _as_int(round(_as_int(total_ms) / 1000)),
        }
        for day, reviews, again, new_cards, total_ms in rows
    ]


def _calendar_dates(start_ms: int, end_ms: int, rollover_hours: int) -> list[str]:
    start_date = datetime.strptime(
        _date_key_for_timestamp(start_ms / 1000, rollover_hours),
        "%Y-%m-%d",
    ).date()
    end_date = datetime.strptime(
        _date_key_for_timestamp((end_ms - 1) / 1000, rollover_hours),
        "%Y-%m-%d",
    ).date()
    if end_date < start_date:
        return []

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def _date_key_for_timestamp(timestamp: float, rollover_hours: int) -> str:
    shifted = datetime.fromtimestamp(timestamp) - timedelta(hours=rollover_hours)
    return shifted.date().isoformat()


def _day_with_zeroes(date_key: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "date": date_key,
            "reviews": 0,
            "new_cards": 0,
            "again": 0,
            "total_seconds": 0,
        }
    return {
        "date": date_key,
        "reviews": _as_int(row.get("reviews")),
        "new_cards": _as_int(row.get("new_cards")),
        "again": _as_int(row.get("again")),
        "total_seconds": _as_int(row.get("total_seconds")),
    }


def _current_streak(active_dates: set[str], today_date: str) -> int:
    today = datetime.strptime(today_date, "%Y-%m-%d").date()
    if today_date in active_dates:
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


def _longest_streak(reviews_by_day: list[dict[str, Any]]) -> int:
    longest = 0
    current = 0
    for day in reviews_by_day:
        if _as_int(day.get("reviews")) > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _best_days(reviews_by_day: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    active = [
        {
            "date": str(day["date"]),
            "reviews": _as_int(day.get("reviews")),
            "new_cards": _as_int(day.get("new_cards")),
            "again": _as_int(day.get("again")),
            "total_seconds": _as_int(day.get("total_seconds")),
        }
        for day in reviews_by_day
        if _as_int(day.get("reviews")) > 0
    ]
    return sorted(active, key=lambda day: (-day["reviews"], day["date"]))[:limit]


def _weekday_average(reviews_by_day: list[dict[str, Any]]) -> dict[str, float]:
    buckets = {name: [] for name in WEEKDAY_NAMES}
    for day in reviews_by_day:
        try:
            weekday = datetime.strptime(str(day["date"]), "%Y-%m-%d").weekday()
        except ValueError:
            continue
        buckets[WEEKDAY_NAMES[weekday]].append(_as_int(day.get("reviews")))

    return {
        name: round(sum(values) / len(values), 1) if values else 0.0
        for name, values in buckets.items()
    }


def _stability_summary(
    active_days: int,
    total_days: int,
    current_streak: int,
    missed_days: int,
    weekday_average: dict[str, float],
) -> str:
    if total_days <= 0:
        return "Активность за выбранный период пока не найдена."

    active_rate = active_days / total_days
    weak_weekdays = [
        name
        for name, average in weekday_average.items()
        if average <= 0 and total_days >= 7
    ]
    if active_rate >= 0.85 and current_streak >= 3:
        return "Занятия идут стабильно; текущая серия поддерживается."
    if active_rate >= 0.60:
        if weak_weekdays:
            return "Занятия в целом регулярные, но есть слабые дни недели."
        return "Занятия достаточно регулярные, хотя пропуски ещё заметны."
    if missed_days > active_days:
        return "Активность рваная: пропущенных дней больше, чем активных."
    return "Стабильность средняя: серию можно укрепить короткими ежедневными сессиями."


def _review_heatmap_probe() -> dict[str, Any]:
    try:
        from aqt import mw as anki_mw  # type: ignore
    except Exception:
        return {"detected": False}

    detected = False
    controller_available = False
    config_available = False
    try:
        controller_available = getattr(anki_mw, "_review_heatmap", None) is not None
        detected = controller_available
    except Exception:
        pass

    try:
        config = anki_mw.addonManager.getConfig("1771074083") if anki_mw else None
        config_available = isinstance(config, dict)
        detected = detected or config_available
    except Exception:
        pass

    return {
        "detected": detected,
        "controller_available": controller_available,
        "config_available": config_available,
        "used_for_metrics": False,
    }
