"""Lightweight read-only forecast metrics for Anki Study Report."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from statistics import median
from typing import Any


ANSWER_TIME_CAP_MS = 120_000
SECONDS_IN_DAY = 86_400
DEFAULT_HISTORY_DAYS = 60
DEFAULT_FORECAST_DAYS = 30
REVLOG_REVIEW_FILTER_SQL = "and r.ease between 1 and 4 and (r.type < 3 or r.factor != 0)"
EARLIER_REVIEW_FILTER_SQL = (
    "and earlier.ease between 1 and 4 and (earlier.type < 3 or earlier.factor != 0)"
)


def collect_forecast_metrics(
    col: Any,
    deck_ids: Sequence[int] | None = None,
    history_days: int = DEFAULT_HISTORY_DAYS,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
) -> dict[str, Any]:
    """Return a compact practical forecast without simulating Anki scheduling."""

    history_days = max(1, int(history_days or DEFAULT_HISTORY_DAYS))
    forecast_days = max(1, int(forecast_days or DEFAULT_FORECAST_DAYS))
    try:
        today = int(col.sched.today)
        day_cutoff = int(col.sched.day_cutoff)
    except Exception:
        return _empty_forecast(history_days, forecast_days)

    deck_ids = _expand_deck_ids(col, deck_ids)
    baseline = _baseline(col, deck_ids, day_cutoff, history_days)
    due_forecast = _due_forecast(col, deck_ids, today, day_cutoff, forecast_days, baseline)
    pattern = _pattern_summary(baseline)
    recommendation = _recommendation(baseline, due_forecast, pattern)

    return {
        "available": True,
        "baseline": baseline,
        "due_forecast": due_forecast,
        "pattern": pattern,
        "recommendation": recommendation,
        "source": {
            "primary": "cards.due + revlog",
            "anki_simulator": "not_required",
            "history_days": history_days,
            "forecast_days": forecast_days,
        },
    }


def _empty_forecast(history_days: int, forecast_days: int) -> dict[str, Any]:
    return {
        "available": False,
        "baseline": _empty_baseline(history_days),
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
            "explanation": "Не удалось прочитать планировщик Anki.",
            "summary": "Прогноз пока недоступен.",
        },
        "source": {
            "primary": "unavailable",
            "anki_simulator": "not_required",
            "history_days": history_days,
            "forecast_days": forecast_days,
        },
    }


def _baseline(
    col: Any,
    deck_ids: Sequence[int] | None,
    day_cutoff: int,
    history_days: int,
) -> dict[str, Any]:
    start_ms = (day_cutoff - history_days * SECONDS_IN_DAY) * 1000
    end_ms = day_cutoff * 1000
    rows = _history_rows(col, deck_ids, start_ms, end_ms)
    if not rows:
        return _empty_baseline(history_days)

    by_day = {
        index: {
            "reviews": 0,
            "again": 0,
            "new_cards": 0,
            "seconds": 0,
            "weekday": _weekday_name(date.today() - timedelta(days=history_days - index)),
        }
        for index in range(history_days)
    }

    for day_index, weekday, reviews, again, new_cards, total_ms in rows:
        if day_index not in by_day:
            continue
        by_day[day_index] = {
            "reviews": _as_int(reviews),
            "again": _as_int(again),
            "new_cards": _as_int(new_cards),
            "seconds": round(_as_int(total_ms) / 1000),
            "weekday": _weekday_name_by_index(_as_int(weekday)),
        }

    active_days = [item for item in by_day.values() if item["reviews"] > 0]
    if not active_days:
        return _empty_baseline(history_days)

    review_counts = [item["reviews"] for item in active_days]
    new_counts = [item["new_cards"] for item in active_days]
    seconds_counts = [item["seconds"] for item in active_days]
    total_reviews = sum(review_counts)
    total_again = sum(item["again"] for item in active_days)

    weekday_stats = _weekday_activity(active_days, history_days)
    return {
        "history_days": history_days,
        "active_days": len(active_days),
        "activity_rate": round(len(active_days) / history_days, 4),
        "median_reviews_active_day": round(median(review_counts), 1),
        "avg_reviews_active_day": round(_trimmed_average(review_counts), 1),
        "median_new_active_day": round(median(new_counts), 1),
        "avg_new_active_day": round(_trimmed_average(new_counts), 1),
        "again_rate": round(total_again / total_reviews, 4) if total_reviews > 0 else 0.0,
        "estimated_minutes_active_day": round(_trimmed_average(seconds_counts) / 60, 1),
        "weekday_activity": weekday_stats,
    }


def _empty_baseline(history_days: int) -> dict[str, Any]:
    return {
        "history_days": history_days,
        "active_days": 0,
        "activity_rate": 0.0,
        "median_reviews_active_day": 0,
        "avg_reviews_active_day": 0.0,
        "median_new_active_day": 0,
        "avg_new_active_day": 0.0,
        "again_rate": 0.0,
        "estimated_minutes_active_day": 0.0,
        "weekday_activity": {},
    }


def _history_rows(
    col: Any,
    deck_ids: Sequence[int] | None,
    start_ms: int,
    end_ms: int,
) -> list[tuple[Any, ...]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    try:
        return col.db.all(
            f"""
            select
                cast((r.id - ?) / ? as integer) as day_index,
                cast(strftime('%w', r.id / 1000, 'unixepoch', 'localtime') as integer) as weekday,
                count(*) as reviews,
                coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
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
            group by day_index, weekday
            order by day_index
            """,
            start_ms,
            SECONDS_IN_DAY * 1000,
            ANSWER_TIME_CAP_MS,
            ANSWER_TIME_CAP_MS,
            start_ms,
            end_ms,
            *deck_params,
        )
    except Exception:
        return []


def _due_forecast(
    col: Any,
    deck_ids: Sequence[int] | None,
    today: int,
    day_cutoff: int,
    forecast_days: int,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    reviews = {offset: 0 for offset in range(1, forecast_days + 1)}
    learning = {offset: 0 for offset in range(1, forecast_days + 1)}
    _fill_review_due(col, deck_ids, today, forecast_days, reviews)
    _fill_learning_due(col, deck_ids, day_cutoff, forecast_days, learning)

    daily = []
    for offset in range(1, forecast_days + 1):
        due = reviews[offset] + learning[offset]
        daily.append(
            {
                "offset": offset,
                "date": str(date.today() + timedelta(days=offset)),
                "due": due,
                "review_due": reviews[offset],
                "learning_due": learning[offset],
                "risk": _risk_for_due(due, baseline),
            }
        )

    return {
        "tomorrow": daily[0]["due"] if daily else 0,
        "tomorrow_reviews": daily[0]["review_due"] if daily else 0,
        "tomorrow_learning": daily[0]["learning_due"] if daily else 0,
        "next_7_days_total": sum(item["due"] for item in daily[:7]),
        "next_30_days_total": sum(item["due"] for item in daily[:30]),
        "daily": daily,
    }


def _fill_review_due(
    col: Any,
    deck_ids: Sequence[int] | None,
    today: int,
    forecast_days: int,
    daily_counts: dict[int, int],
) -> None:
    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    try:
        rows = col.db.all(
            f"""
            select case when odid = 0 then due else odue end as true_due, count(*)
            from cards
            where queue in (2, 3)
              and (case when odid = 0 then due else odue end) > ?
              and (case when odid = 0 then due else odue end) <= ?
              {deck_sql}
            group by case when odid = 0 then due else odue end
            """,
            today,
            today + forecast_days,
            *deck_params,
        )
    except Exception:
        rows = []

    for due, count in rows:
        offset = _as_int(due) - today
        if 1 <= offset <= forecast_days:
            daily_counts[offset] += _as_int(count)


def _fill_learning_due(
    col: Any,
    deck_ids: Sequence[int] | None,
    day_cutoff: int,
    forecast_days: int,
    daily_counts: dict[int, int],
) -> None:
    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    try:
        rows = col.db.all(
            f"""
            select cast((due - ?) / ? as integer) + 1 as offset, count(*)
            from cards
            where queue = 1
              and due >= ?
              and due < ?
              {deck_sql}
            group by offset
            """,
            day_cutoff,
            SECONDS_IN_DAY,
            day_cutoff,
            day_cutoff + forecast_days * SECONDS_IN_DAY,
            *deck_params,
        )
    except Exception:
        rows = []

    for offset, count in rows:
        offset_int = _as_int(offset)
        if 1 <= offset_int <= forecast_days:
            daily_counts[offset_int] += _as_int(count)


def _risk_for_due(due: int, baseline: dict[str, Any]) -> str:
    median_reviews = float(baseline.get("median_reviews_active_day") or 0)
    again_rate = float(baseline.get("again_rate") or 0)
    if due <= 0:
        return "low"
    if median_reviews <= 0:
        return "medium" if due >= 50 else "low"
    if due >= median_reviews * 1.8 or (due >= median_reviews * 1.4 and again_rate >= 0.2):
        return "high"
    if due >= median_reviews * 1.15 or again_rate >= 0.25:
        return "medium"
    return "low"


def _recommendation(
    baseline: dict[str, Any],
    due_forecast: dict[str, Any],
    pattern: dict[str, Any],
) -> dict[str, Any]:
    tomorrow = _as_int(due_forecast.get("tomorrow"))
    median_reviews = float(baseline.get("median_reviews_active_day") or 0)
    median_new = float(baseline.get("median_new_active_day") or 0)
    activity_rate = float(baseline.get("activity_rate") or 0)
    again_rate = float(baseline.get("again_rate") or 0)
    tomorrow_risk = _risk_for_due(tomorrow, baseline)
    risk = tomorrow_risk

    if activity_rate < 0.45 and risk == "low" and tomorrow > 0:
        risk = "medium"
    if again_rate >= 0.25:
        if risk == "medium":
            risk = "high"
        elif risk == "low":
            risk = "medium"

    if risk == "high":
        advice = "Новые карточки завтра лучше отложить и сначала закрыть повторения."
    elif again_rate >= 0.25:
        advice = (
            "Новые завтра лучше ограничить: due-очередь небольшая, "
            "но доля Again высокая."
        )
    elif risk == "medium":
        advice = "Новые можно добавлять осторожно, лучше не выше обычного темпа."
    elif median_new <= 0:
        advice = "Можно добавить немного новых карточек, если есть время и очередь комфортная."
    else:
        advice = "Новые можно добавлять как обычно, если завтра не появится дополнительная очередь."

    if median_reviews > 0:
        explanation = (
            f"Завтра ожидается {tomorrow} повторений при обычной медиане "
            f"около {round(median_reviews)}."
        )
    elif tomorrow > 0:
        explanation = (
            f"Завтра ожидается {tomorrow} повторений, но личный baseline пока слабый."
        )
    else:
        explanation = "На завтра заметной due-нагрузки не видно."

    if again_rate >= 0.2:
        explanation += f" Again rate за историю около {round(again_rate * 100)}%."

    new_week = round(median_new * min(7, max(1, activity_rate * 7)))
    summary = _summary_text(risk, tomorrow, due_forecast, pattern, new_week, again_rate)
    return {
        "risk": risk,
        "risk_label": _risk_label(risk),
        "new_cards_advice": advice,
        "explanation": explanation,
        "expected_new_cards_7_days": new_week,
        "summary": summary,
    }


def _summary_text(
    risk: str,
    tomorrow: int,
    due_forecast: dict[str, Any],
    pattern: dict[str, Any],
    new_week: int,
    again_rate: float,
) -> str:
    next_7 = _as_int(due_forecast.get("next_7_days_total"))
    if again_rate >= 0.25 and tomorrow == 0 and next_7 <= 10:
        load = "легкими по очереди, но осторожными по качеству ответов"
    elif risk == "high":
        load = "тяжелыми"
    elif risk == "medium":
        load = "заметными, но управляемыми"
    else:
        load = "легкими или нормальными"

    text = (
        f"Если продолжать заниматься примерно как обычно, ближайшие 7 дней выглядят "
        f"{load}: завтра {tomorrow}, за 7 дней около {next_7} повторений."
    )
    if new_week > 0:
        text += f" При привычном темпе новых может добавиться около {new_week} карточек за неделю."
    if pattern.get("regularity") == "irregular":
        text += " Из-за нерегулярного графика прогноз стоит читать осторожно."
    return text


def _pattern_summary(baseline: dict[str, Any]) -> dict[str, Any]:
    activity_rate = float(baseline.get("activity_rate") or 0)
    median_new = float(baseline.get("median_new_active_day") or 0)
    again_rate = float(baseline.get("again_rate") or 0)
    weekday_activity = baseline.get("weekday_activity")
    weekday_activity = weekday_activity if isinstance(weekday_activity, dict) else {}
    active_weekdays = [
        day
        for day, stats in weekday_activity.items()
        if isinstance(stats, dict) and float(stats.get("activity_rate") or 0) >= 0.5
    ]
    weak_weekdays = [
        day
        for day, stats in weekday_activity.items()
        if isinstance(stats, dict) and float(stats.get("activity_rate") or 0) <= 0.25
    ]

    if activity_rate >= 0.8:
        regularity = "regular"
        summary = "Пользователь занимается почти каждый день."
    elif activity_rate >= 0.45:
        regularity = "mixed"
        summary = "Пользователь занимается регулярно, но с заметными пропусками."
    elif activity_rate > 0:
        regularity = "irregular"
        summary = "Пользователь занимается нерегулярно, поэтому прогноз осторожный."
    else:
        regularity = "unknown"
        summary = "Для определения паттерна пока не хватает истории."

    if median_new >= 20 and again_rate >= 0.18:
        summary += " Видно много новых карточек на фоне заметных Again."
    elif median_new >= 10:
        summary += " Темп новых карточек заметный."
    elif median_new > 0:
        summary += " Темп новых карточек умеренный."
    if again_rate >= 0.25:
        summary += " Доля Again высокая."

    return {
        "summary": summary,
        "active_weekdays": active_weekdays,
        "weak_weekdays": weak_weekdays,
        "regularity": regularity,
    }


def _weekday_activity(
    active_days: list[dict[str, Any]],
    history_days: int,
) -> dict[str, dict[str, Any]]:
    stats = {day: {"active_days": 0, "avg_reviews": 0.0} for day in _weekday_order()}
    review_values: dict[str, list[int]] = {day: [] for day in _weekday_order()}
    for item in active_days:
        day = str(item.get("weekday") or "")
        if day not in stats:
            continue
        stats[day]["active_days"] += 1
        review_values[day].append(_as_int(item.get("reviews")))

    total_weeks = max(1, round(history_days / 7))
    for day, values in review_values.items():
        stats[day]["activity_rate"] = round(min(1.0, len(values) / total_weeks), 4)
        stats[day]["avg_reviews"] = round(_trimmed_average(values), 1) if values else 0.0
    return stats


def _trimmed_average(values: Sequence[int | float]) -> float:
    numbers = sorted(float(value) for value in values)
    if not numbers:
        return 0.0
    if len(numbers) < 5:
        return sum(numbers) / len(numbers)
    cut = max(1, int(len(numbers) * 0.1))
    trimmed = numbers[cut:-cut] or numbers
    return sum(trimmed) / len(trimmed)


def _risk_label(risk: str) -> str:
    return {
        "low": "низкий",
        "medium": "средний",
        "high": "высокий",
        "unknown": "нет данных",
    }.get(risk, "нет данных")


def _weekday_order() -> list[str]:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _weekday_name(value: date) -> str:
    return _weekday_order()[value.weekday()]


def _weekday_name_by_index(index: int) -> str:
    # SQLite strftime('%w') uses Sunday=0.
    return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][
        index % 7
    ]


def _expand_deck_ids(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> list[int] | None:
    if deck_ids is None:
        return None
    try:
        from .metrics import expand_deck_ids

        return expand_deck_ids(col, deck_ids)
    except Exception:
        return [_as_int(deck_id) for deck_id in deck_ids]


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


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)
