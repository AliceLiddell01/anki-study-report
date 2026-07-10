"""Bounded scoped Activity Hub and deterministic derived feed builders."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any


ACTIVITY_SCHEMA_VERSION = 1
ACTIVITY_MAX_DECKS_PER_DAY = 100
STREAK_MILESTONES = {3, 7, 14, 30, 60, 100, 180, 365}
PERIODS = {
    "30d": "Последние 30 дней",
    "90d": "Последние 90 дней",
    "6m": "Последние 6 месяцев",
    "1y": "Последний год",
}


def activity_period_bounds(today_key: str) -> dict[str, dict[str, str]]:
    today = _parse_date(today_key) or date.today()
    starts = {
        "30d": today - timedelta(days=29),
        "90d": today - timedelta(days=89),
        "6m": _subtract_months(today, 6) + timedelta(days=1),
        "1y": _subtract_year(today) + timedelta(days=1),
    }
    return {
        key: {"start": starts[key].isoformat(), "end": today.isoformat(), "label": label}
        for key, label in PERIODS.items()
    }


def build_activity_hub_payload(
    snapshot: dict[str, Any],
    today_key: str,
    *,
    display_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe one-year view from canonical daily/deck-day aggregates."""

    today = _parse_date(today_key) or date.today()
    today_key = today.isoformat()
    settings = _normalize_display_settings(display_settings)
    all_daily = _clean_rows(snapshot.get("daily"), today_key)
    all_deck_rows = _clean_deck_rows(snapshot.get("deckDaily"), today_key)
    available_from = str(all_daily[0]["date"]) if all_daily else None
    scoped_deck_rows = _filter_decks(all_deck_rows, settings["selectedDeckIds"])
    scoped_daily = (
        _daily_from_decks(scoped_deck_rows)
        if settings["selectedDeckIds"]
        else [dict(row) for row in all_daily]
    )
    scoped_by_date = {str(row["date"]): row for row in scoped_daily}
    decks_by_date = _decks_by_date(scoped_deck_rows)
    periods = activity_period_bounds(today_key)
    public_start = periods["1y"]["start"]
    public_days: list[dict[str, Any]] = []

    if available_from is not None:
        for current in _date_range(public_start, today_key):
            row = scoped_by_date.get(current)
            availability = "unavailable" if current < available_from else "active" if _is_active(row) else "inactive"
            public_days.append(
                _public_day(
                    current,
                    availability,
                    row,
                    decks_by_date.get(current, []),
                )
            )

    all_active_rows = [row for row in scoped_daily if _is_active(row)]
    feed_days = _build_feed_days(all_active_rows, available_from)
    feed_days = [entry for entry in feed_days if entry["date"] >= public_start]
    weeks = _build_weekly_summaries(scoped_daily, available_from, today)
    weeks = [week for week in weeks if week["weekEnd"] >= public_start]
    active_dates = {str(row["date"]) for row in all_active_rows}

    return {
        "schemaVersion": ACTIVITY_SCHEMA_VERSION,
        "today": today_key,
        "scope": {
            "kind": "selected" if settings["selectedDeckIds"] else "all",
            "selectedDeckIds": settings["selectedDeckIds"],
            "includeChildDecks": settings["includeChildDecks"],
        },
        "bounds": {
            "start": public_start,
            "end": today_key,
            "availableFrom": available_from,
            "maxDays": len(_date_range(public_start, today_key)),
        },
        "periods": periods,
        "metrics": {"studyTimeSource": "revlog_estimate"},
        "overview": {
            "currentStreak": _current_streak(active_dates, today),
            "bestStreak": _best_streak(active_dates),
        },
        "days": public_days,
        "feed": {
            "days": feed_days,
            "weeks": weeks,
            "pageSize": 14,
        },
    }


def _normalize_display_settings(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    raw_ids = source.get("selected_deck_ids")
    ids: list[int] = []
    for value in raw_ids if isinstance(raw_ids, list) else []:
        deck_id = _int(value)
        if deck_id > 0 and deck_id not in ids:
            ids.append(deck_id)
    return {
        "selectedDeckIds": ids,
        "includeChildDecks": bool(source.get("include_child_decks", True)),
    }


def _clean_rows(value: Any, today_key: str) -> list[dict[str, Any]]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        day = _valid_date(item.get("date"))
        if day and day <= today_key:
            result.append(dict(item, date=day))
    return sorted(result, key=lambda row: row["date"])


def _clean_deck_rows(value: Any, today_key: str) -> list[dict[str, Any]]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        day = _valid_date(item.get("date"))
        deck_id = _int(item.get("deck_id"))
        if day and day <= today_key and deck_id > 0:
            result.append(dict(item, date=day, deck_id=deck_id))
    return sorted(result, key=lambda row: (row["date"], _int(row.get("deck_id"))))


def _filter_decks(rows: list[dict[str, Any]], selected_ids: list[int]) -> list[dict[str, Any]]:
    if not selected_ids:
        return rows
    allowed = set(selected_ids)
    return [row for row in rows if _int(row.get("deck_id")) in allowed]


def _daily_from_decks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = str(row["date"])
        target = grouped.setdefault(day, _empty_daily(day))
        _add_daily(target, row)
    return [grouped[key] for key in sorted(grouped)]


def _empty_daily(day: str) -> dict[str, Any]:
    return {
        "date": day,
        "reviews": 0,
        "new_cards": 0,
        "pass_count": 0,
        "fail_count": 0,
        "study_seconds": 0,
    }


def _add_daily(target: dict[str, Any], row: dict[str, Any]) -> None:
    for key in ("reviews", "new_cards", "pass_count", "fail_count", "study_seconds"):
        target[key] = _int(target.get(key)) + _int(row.get(key))


def _decks_by_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = {}
    for row in rows:
        day = str(row["date"])
        deck_id = _int(row.get("deck_id"))
        target = grouped.setdefault(day, {}).setdefault(
            deck_id,
            {
                "id": deck_id,
                "name": str(row.get("deck_name") or f"Колода {deck_id}"),
                "reviews": 0,
                "pass": 0,
                "fail": 0,
            },
        )
        target["name"] = str(row.get("deck_name") or target["name"])
        target["reviews"] += _int(row.get("reviews"))
        target["pass"] += _int(row.get("pass_count"))
        target["fail"] += _int(row.get("fail_count"))
    result: dict[str, list[dict[str, Any]]] = {}
    for day, decks in grouped.items():
        rows_for_day = []
        for deck in decks.values():
            denominator = deck["pass"] + deck["fail"]
            rows_for_day.append(
                {
                    **deck,
                    "successRate": round(deck["pass"] / denominator, 4) if denominator > 0 else None,
                }
            )
        result[day] = sorted(
            rows_for_day,
            key=lambda row: (-row["reviews"], row["name"].casefold(), row["id"]),
        )[:ACTIVITY_MAX_DECKS_PER_DAY]
    return result


def _public_day(
    day: str,
    availability: str,
    row: dict[str, Any] | None,
    decks: list[dict[str, Any]],
) -> dict[str, Any]:
    if availability != "active":
        return {"date": day, "availability": availability}
    source = row if isinstance(row, dict) else {}
    reviews = _int(source.get("reviews"))
    passed = _int(source.get("pass_count"))
    failed = _int(source.get("fail_count"))
    denominator = passed + failed
    seconds = _int(source.get("study_seconds"))
    return {
        "date": day,
        "availability": availability,
        "reviews": reviews,
        "newCards": _int(source.get("new_cards")),
        "pass": passed,
        "fail": failed,
        "successRate": round(passed / denominator, 4) if denominator > 0 else None,
        "studySeconds": seconds if seconds > 0 else None,
        "activeDeckCount": len(decks),
        "decks": decks,
    }


def _build_feed_days(rows: list[dict[str, Any]], available_from: str | None) -> list[dict[str, Any]]:
    active_dates = {str(row["date"]) for row in rows}
    prior_max: int | None = None
    entries: list[dict[str, Any]] = []
    previous_active: date | None = None
    for row in rows:
        day = str(row["date"])
        parsed = _parse_date(day)
        if parsed is None:
            continue
        highlights: list[dict[str, Any]] = []
        if previous_active is not None:
            gap_days = (parsed - previous_active).days - 1
            gap_start = previous_active + timedelta(days=1)
            if gap_days >= 2 and available_from and gap_start.isoformat() >= available_from:
                highlights.append(
                    {
                        "id": f"{day}:return:{gap_days}",
                        "type": "return_after_break",
                        "inactiveDays": gap_days,
                    }
                )
        streak = _streak_ending(active_dates, parsed)
        if streak in STREAK_MILESTONES:
            highlights.append(
                {
                    "id": f"{day}:streak:{streak}",
                    "type": "streak_milestone",
                    "days": streak,
                }
            )
        reviews = _int(row.get("reviews"))
        if prior_max is not None and reviews > prior_max:
            highlights.append(
                {
                    "id": f"{day}:record:{reviews}",
                    "type": "new_activity_record",
                    "reviews": reviews,
                    "previousMax": prior_max,
                }
            )
        prior_max = reviews if prior_max is None else max(prior_max, reviews)
        entries.append(
            {
                "id": f"{day}:daily-summary",
                "type": "daily_summary",
                "date": day,
                "highlights": highlights,
            }
        )
        previous_active = parsed
    return list(reversed(entries))


def _build_weekly_summaries(
    rows: list[dict[str, Any]],
    available_from: str | None,
    today: date,
) -> list[dict[str, Any]]:
    by_week: dict[date, list[dict[str, Any]]] = {}
    for row in rows:
        parsed = _parse_date(str(row.get("date") or ""))
        if parsed is None:
            continue
        monday = parsed - timedelta(days=parsed.weekday())
        by_week.setdefault(monday, []).append(row)
    if available_from:
        available = _parse_date(available_from)
    else:
        available = None
    complete: dict[date, dict[str, Any]] = {}
    for monday, week_rows in by_week.items():
        sunday = monday + timedelta(days=6)
        if sunday >= today or available is None or available > monday:
            continue
        active_rows = [row for row in week_rows if _is_active(row)]
        reviews = sum(_int(row.get("reviews")) for row in active_rows)
        passed = sum(_int(row.get("pass_count")) for row in active_rows)
        failed = sum(_int(row.get("fail_count")) for row in active_rows)
        denominator = passed + failed
        seconds_values = [_int(row.get("study_seconds")) for row in active_rows]
        seconds = sum(seconds_values)
        iso_year, iso_week, _ = monday.isocalendar()
        complete[monday] = {
            "id": f"{iso_year}-W{iso_week:02d}:weekly-summary",
            "type": "weekly_summary",
            "weekStart": monday.isoformat(),
            "weekEnd": sunday.isoformat(),
            "activeDays": len(active_rows),
            "reviews": reviews,
            "studySeconds": seconds if any(value > 0 for value in seconds_values) else None,
            "successRate": round(passed / denominator, 4) if denominator > 0 else None,
            "comparison": None,
        }
    for monday, current in complete.items():
        previous = complete.get(monday - timedelta(days=7))
        if (
            previous
            and current["activeDays"] >= 2
            and previous["activeDays"] >= 2
            and current["reviews"] >= 20
            and previous["reviews"] >= 20
        ):
            change = round((current["reviews"] - previous["reviews"]) / previous["reviews"] * 100)
            current["comparison"] = {
                "reviewsPercentChange": change,
                "direction": "more" if change > 0 else "less" if change < 0 else "same",
            }
    return [complete[key] for key in sorted(complete, reverse=True)]


def _is_active(row: dict[str, Any] | None) -> bool:
    return isinstance(row, dict) and _int(row.get("reviews")) > 0


def _current_streak(active_dates: set[str], today: date) -> int:
    cursor = today if today.isoformat() in active_dates else today - timedelta(days=1)
    return _streak_ending(active_dates, cursor) if cursor.isoformat() in active_dates else 0


def _streak_ending(active_dates: set[str], end: date) -> int:
    result = 0
    cursor = end
    while cursor.isoformat() in active_dates:
        result += 1
        cursor -= timedelta(days=1)
    return result


def _best_streak(active_dates: set[str]) -> int:
    best = current = 0
    previous: date | None = None
    for day in sorted(filter(None, (_parse_date(value) for value in active_dates))):
        current = current + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, current)
        previous = day
    return best


def _date_range(start_key: str, end_key: str) -> list[str]:
    start = _parse_date(start_key)
    end = _parse_date(end_key)
    if start is None or end is None or end < start:
        return []
    return [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]


def _subtract_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _subtract_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _valid_date(value: Any) -> str | None:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed is not None else None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
