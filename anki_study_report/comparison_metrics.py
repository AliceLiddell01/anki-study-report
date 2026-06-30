"""Read-only period comparison metrics for the web dashboard."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from .metrics import (
    ANSWER_TIME_CAP_MS,
    EARLIER_REVIEW_FILTER_SQL,
    REVLOG_REVIEW_FILTER_SQL,
    _as_int,
    _deck_filter_sql,
    _expand_deck_ids,
)


SECONDS_IN_DAY = 86_400
DEFAULT_HISTORY_DAYS = 60
MIN_BASELINE_DAYS = 3


def collect_comparison_metrics(
    col: Any,
    deck_ids: Sequence[int] | None = None,
    history_days: int = DEFAULT_HISTORY_DAYS,
) -> dict[str, Any]:
    """Compare today with recent personal baselines using only ``revlog``."""

    history_days = max(31, int(history_days or DEFAULT_HISTORY_DAYS))
    try:
        day_cutoff = int(col.sched.day_cutoff)
    except Exception:
        return _empty_comparison(history_days, "Не удалось прочитать Anki day cutoff.")

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)
    today_start = day_cutoff - SECONDS_IN_DAY
    today_date = date.fromtimestamp(today_start).isoformat()
    start_cutoff = today_start - (history_days - 1) * SECONDS_IN_DAY
    rows = _daily_rows(col, expanded_deck_ids, start_cutoff, day_cutoff)
    by_date = {str(row["date"]): row for row in rows}
    days = [
        _day_with_zeroes((date.fromtimestamp(start_cutoff) + timedelta(days=offset)).isoformat(), by_date)
        for offset in range(history_days)
    ]
    by_date = {str(day["date"]): day for day in days}
    today = _daily_stats(
        by_date.get(today_date),
        active_decks=_active_decks_today(
            col,
            expanded_deck_ids,
            today_start,
            day_cutoff,
        ),
    )
    previous_days = [day for day in days if str(day.get("date")) < today_date]
    active_history_days = [day for day in previous_days if _as_int(day.get("reviews")) > 0]

    yesterday_date = (date.fromisoformat(today_date) - timedelta(days=1)).isoformat()
    same_weekday_date = (date.fromisoformat(today_date) - timedelta(days=7)).isoformat()
    current_week_days, previous_week_days = _week_windows(days, today_date)
    current_month_days, previous_month_days = _month_windows(days, today_date)

    baselines = {
        "yesterday": _daily_stats(by_date.get(yesterday_date)),
        "avg7": _average_daily_stats(previous_days[-7:], "Последние 7 дней"),
        "avg30": _average_daily_stats(previous_days[-30:], "Последние 30 дней"),
        "sameWeekdayLastWeek": _daily_stats(by_date.get(same_weekday_date)),
        "currentWeek": _aggregate_stats(current_week_days, "Эта неделя"),
        "previousWeek": _aggregate_stats(previous_week_days, "Прошлая неделя"),
        "currentMonth": _aggregate_stats(current_month_days, "Этот месяц"),
        "previousMonth": _aggregate_stats(previous_month_days, "Прошлый месяц"),
    }
    available = len(active_history_days) >= MIN_BASELINE_DAYS
    comparisons = _comparison_payloads(today, baselines)
    insights = _insights(today, baselines, available)

    return {
        "available": available,
        "today": today,
        "baselines": baselines,
        "comparisons": comparisons,
        "insights": insights,
        "message": "" if available else "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.",
        "source": {
            "primary": "revlog",
            "history_days": history_days,
            "active_history_days": len(active_history_days),
            "min_baseline_days": MIN_BASELINE_DAYS,
            "anki_day_cutoff": day_cutoff,
            "today_start": today_start,
        },
    }


def _empty_comparison(history_days: int, message: str) -> dict[str, Any]:
    empty = _empty_daily_stats("")
    return {
        "available": False,
        "today": empty,
        "baselines": {},
        "comparisons": {},
        "insights": [],
        "message": message,
        "source": {
            "primary": "unavailable",
            "history_days": history_days,
            "active_history_days": 0,
            "min_baseline_days": MIN_BASELINE_DAYS,
        },
    }


def _daily_rows(
    col: Any,
    deck_ids: Sequence[int] | None,
    start_cutoff: int,
    end_cutoff: int,
) -> list[dict[str, Any]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    start_ms = start_cutoff * 1000
    end_ms = end_cutoff * 1000
    try:
        rows = col.db.all(
            f"""
            select
                cast((r.id / 1000 - ?) / ? as integer) as day_index,
                count(*) as reviews,
                coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as fail,
                coalesce(sum(case when r.ease = 2 then 1 else 0 end), 0) as hard,
                coalesce(sum(case when r.ease = 4 then 1 else 0 end), 0) as easy,
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
                count(distinct c.did) as active_decks,
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
            group by day_index
            order by day_index
            """,
            start_cutoff,
            SECONDS_IN_DAY,
            ANSWER_TIME_CAP_MS,
            ANSWER_TIME_CAP_MS,
            start_ms,
            end_ms,
            *deck_params,
        )
    except Exception:
        rows = []

    start_date = date.fromtimestamp(start_cutoff)
    result = []
    for day_index, reviews, fail, hard, easy, new_cards, active_decks, total_ms in rows:
        index = _as_int(day_index)
        result.append(
            {
                "date": (start_date + timedelta(days=index)).isoformat(),
                "reviews": _as_int(reviews),
                "new_cards": _as_int(new_cards),
                "pass": max(0, _as_int(reviews) - _as_int(fail)),
                "fail": _as_int(fail),
                "hard": _as_int(hard),
                "easy": _as_int(easy),
                "study_seconds": _as_int(round(_as_int(total_ms) / 1000)),
                "active_decks": _as_int(active_decks),
            }
        )
    return result


def _active_decks_today(
    col: Any,
    deck_ids: Sequence[int] | None,
    start_cutoff: int,
    end_cutoff: int,
) -> int:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    try:
        return _as_int(
            col.db.scalar(
                f"""
                select count(distinct c.did)
                from revlog r
                left join cards c on c.id = r.cid
                where r.id >= ?
                  and r.id < ?
                  {REVLOG_REVIEW_FILTER_SQL}
                  {deck_sql}
                """,
                start_cutoff * 1000,
                end_cutoff * 1000,
                *deck_params,
            )
        )
    except Exception:
        return 0


def _day_with_zeroes(date_key: str, by_date: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = by_date.get(date_key)
    if row is None:
        return _empty_daily_stats(date_key)
    return row


def _empty_daily_stats(date_key: str, label: str | None = None) -> dict[str, Any]:
    return {
        "date": date_key,
        "label": label or date_key,
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


def _daily_stats(row: dict[str, Any] | None, active_decks: int | None = None) -> dict[str, Any]:
    if row is None:
        return _empty_daily_stats("")
    reviews = _as_int(row.get("reviews"))
    fail = _as_int(row.get("fail"))
    pass_count = max(0, _as_int(row.get("pass")) or reviews - fail)
    seconds = _as_int(row.get("study_seconds"))
    return {
        "date": str(row.get("date") or ""),
        "label": str(row.get("label") or row.get("date") or ""),
        "reviews": reviews,
        "newCards": _as_int(row.get("new_cards") or row.get("newCards")),
        "pass": pass_count,
        "fail": fail,
        "hard": _as_int(row.get("hard")),
        "easy": _as_int(row.get("easy")),
        "studySeconds": seconds,
        "studyMinutes": round(seconds / 60),
        "avgAnswerSeconds": round(seconds / reviews, 1) if reviews > 0 and seconds > 0 else None,
        "activeDecks": _as_int(active_decks if active_decks is not None else row.get("active_decks")),
        "passRate": round(pass_count / reviews, 4) if reviews > 0 else None,
        "failRate": round(fail / reviews, 4) if reviews > 0 else None,
    }


def _average_daily_stats(days: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not days:
        return _empty_daily_stats("", label)
    count = len(days)
    reviews = sum(_as_int(day.get("reviews")) for day in days)
    fail = sum(_as_int(day.get("fail")) for day in days)
    pass_count = sum(_as_int(day.get("pass")) for day in days)
    seconds = sum(_as_int(day.get("study_seconds")) for day in days)
    new_cards = sum(_as_int(day.get("new_cards")) for day in days)
    active_decks = sum(_as_int(day.get("active_decks")) for day in days)
    return _daily_stats(
        {
            "date": "",
            "label": label,
            "reviews": round(reviews / count),
            "new_cards": round(new_cards / count),
            "pass": round(pass_count / count),
            "fail": round(fail / count),
            "hard": round(sum(_as_int(day.get("hard")) for day in days) / count),
            "easy": round(sum(_as_int(day.get("easy")) for day in days) / count),
            "study_seconds": round(seconds / count),
            "active_decks": round(active_decks / count),
        }
    )


def _aggregate_stats(days: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not days:
        return _empty_daily_stats("", label)
    return _daily_stats(
        {
            "date": "",
            "label": label,
            "reviews": sum(_as_int(day.get("reviews")) for day in days),
            "new_cards": sum(_as_int(day.get("new_cards")) for day in days),
            "pass": sum(_as_int(day.get("pass")) for day in days),
            "fail": sum(_as_int(day.get("fail")) for day in days),
            "hard": sum(_as_int(day.get("hard")) for day in days),
            "easy": sum(_as_int(day.get("easy")) for day in days),
            "study_seconds": sum(_as_int(day.get("study_seconds")) for day in days),
            "active_decks": sum(1 for day in days if _as_int(day.get("reviews")) > 0),
        }
    )


def _week_windows(days: list[dict[str, Any]], today_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    today = date.fromisoformat(today_date)
    week_start = today - timedelta(days=today.weekday())
    previous_start = week_start - timedelta(days=7)
    current = [day for day in days if week_start.isoformat() <= str(day.get("date")) <= today_date]
    previous = [
        day
        for day in days
        if previous_start.isoformat() <= str(day.get("date")) < week_start.isoformat()
    ]
    return current, previous


def _month_windows(days: list[dict[str, Any]], today_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    today = date.fromisoformat(today_date)
    month_start = today.replace(day=1)
    previous_end = month_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    current = [day for day in days if month_start.isoformat() <= str(day.get("date")) <= today_date]
    previous = [
        day
        for day in days
        if previous_start.isoformat() <= str(day.get("date")) <= previous_end.isoformat()
    ]
    return current, previous


def _comparison_payloads(today: dict[str, Any], baselines: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        key: _comparison_payload(today, baseline)
        for key, baseline in baselines.items()
        if key in {"yesterday", "avg7", "avg30", "sameWeekdayLastWeek"}
    } | {
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


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _insights(today: dict[str, Any], baselines: dict[str, dict[str, Any]], available: bool) -> list[dict[str, Any]]:
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
    comparison = _comparison_payload(today, avg7)
    reviews_delta = comparison["reviews"]["percentDelta"]
    new_delta = comparison["newCards"]["percentDelta"]
    pass_delta = comparison["passRate"]["deltaPp"]
    fail_delta = comparison["failRate"]["deltaPp"]
    answer_delta = comparison["avgAnswerSeconds"]["percentDelta"]
    insights: list[dict[str, Any]] = []

    reviews = _as_int(today.get("reviews"))
    avg_reviews = _as_int(avg7.get("reviews"))
    pass_rate = _number_or_none(today.get("passRate"))
    avg_pass_rate = _number_or_none(avg7.get("passRate"))
    fail_rate = _number_or_none(today.get("failRate"))
    avg_fail_rate = _number_or_none(avg7.get("failRate"))

    if (
        avg_reviews > 0
        and reviews >= avg_reviews
        and pass_rate is not None
        and avg_pass_rate is not None
        and pass_rate >= avg_pass_rate - 0.02
        and (fail_delta is None or fail_delta < 3)
    ):
        insights.append(
            {
                "severity": "positive",
                "title": "Продуктивный день",
                "text": "Объём выше нормы, а качество не просело.",
                "metric": "reviews",
            }
        )
    elif (
        reviews_delta is not None
        and reviews_delta >= 50
        and fail_delta is not None
        and fail_delta >= 3
        and answer_delta is not None
        and answer_delta >= 15
    ):
        insights.append(
            {
                "severity": "danger",
                "title": "Похоже на перегруз",
                "text": "Объём вырос, но ошибок и времени на ответ стало заметно больше.",
                "metric": "failRate",
            }
        )
    elif (
        avg_reviews > 0
        and reviews < avg_reviews
        and pass_rate is not None
        and avg_pass_rate is not None
        and pass_rate >= avg_pass_rate - 0.02
    ):
        insights.append(
            {
                "severity": "neutral",
                "title": "Лёгкий стабильный день",
                "text": "Повторений меньше обычного, качество около нормы или выше.",
                "metric": "passRate",
            }
        )

    if new_delta is not None and new_delta >= 50 and fail_rate is not None and avg_fail_rate is not None and fail_rate > avg_fail_rate:
        insights.append(
            {
                "severity": "warning",
                "title": "Новые карточки выше нормы",
                "text": "Сегодня лучше не добавлять новые карточки или добавить меньше обычного.",
                "metric": "newCards",
            }
        )

    week_delta = _comparison_payload(baselines["currentWeek"], baselines["previousWeek"])
    week_reviews_delta = week_delta["reviews"]["percentDelta"]
    if week_reviews_delta is not None and week_reviews_delta >= 10:
        insights.append(
            {
                "severity": "positive",
                "title": "Неделя активнее прошлой",
                "text": "За эту неделю объём повторений выше, чем за прошлую.",
                "metric": "week",
            }
        )

    if pass_delta is not None and pass_delta <= -3 and not any(item["metric"] == "failRate" for item in insights):
        insights.append(
            {
                "severity": "warning",
                "title": "Качество просело",
                "text": "Pass rate ниже 7-дневной нормы на 3+ п.п.; новые лучше давать осторожно.",
                "metric": "passRate",
            }
        )

    if not insights:
        insights.append(
            {
                "severity": "neutral",
                "title": "День около нормы",
                "text": "Сегодняшняя сессия близка к вашему обычному темпу.",
                "metric": "summary",
            }
        )
    return insights[:3]
