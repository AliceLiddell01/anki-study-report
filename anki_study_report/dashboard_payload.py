"""Payload builders for the web dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .session_tracker import unavailable_tracked_time


def build_dashboard_report_payload(
    metrics: dict,
    metadata: dict,
    *,
    cache_summary: dict | None = None,
) -> dict:
    total_reviews = dashboard_int(metrics.get("total_reviews"))
    new_cards = dashboard_int(metrics.get("new_cards"))
    fail_count = _dashboard_fail_count(metrics)
    pass_count = max(0, dashboard_int(metrics.get("pass_count")) or total_reviews - fail_count)
    pass_rate = dashboard_rate(metrics.get("pass_rate"))
    fail_rate = dashboard_rate(metrics.get("fail_rate"))
    if total_reviews > 0 and fail_rate <= 0:
        fail_rate = round(fail_count / total_reviews, 4)
    total_seconds = dashboard_int(metrics.get("total_seconds"))
    average_answer_seconds = dashboard_float(metrics.get("average_answer_seconds"))
    heatmap = metrics.get("heatmap") if isinstance(metrics.get("heatmap"), dict) else {}
    forecast = metrics.get("forecast") if isinstance(metrics.get("forecast"), dict) else {}
    fsrs = metrics.get("fsrs") if isinstance(metrics.get("fsrs"), dict) else {}
    due_forecast = forecast.get("due_forecast") if isinstance(forecast.get("due_forecast"), dict) else {}
    baseline = forecast.get("baseline") if isinstance(forecast.get("baseline"), dict) else {}
    forecast_recommendation = (
        forecast.get("recommendation")
        if isinstance(forecast.get("recommendation"), dict)
        else {}
    )
    risk = str(forecast_recommendation.get("risk") or "low")
    decks = _dashboard_decks(metrics.get("deck_breakdown"))
    problem_decks = [
        deck for deck in decks if deck["status"] in {"danger", "warning"}
    ]
    hardest_deck = problem_decks[0]["name"] if problem_decks else "проблемные колоды не выделены"
    tomorrow = dashboard_int(due_forecast.get("tomorrow") or metrics.get("due_tomorrow"))
    next_7 = dashboard_int(due_forecast.get("next_7_days_total"))
    next_30 = dashboard_int(due_forecast.get("next_30_days_total"))
    risk_status = _dashboard_risk_status(risk)
    quality_status = _dashboard_quality_status(pass_rate, total_reviews)
    fail_status = "danger" if fail_rate >= 0.22 else "warning" if fail_rate >= 0.15 else "good"

    summary_verdict = _dashboard_summary_verdict(
        pass_rate,
        fail_rate,
        tomorrow,
        hardest_deck,
        risk_status,
    )
    main_action = _dashboard_main_action(problem_decks)
    new_cards_advice = _dashboard_new_cards_advice(pass_rate, risk_status)

    return {
        "metadata": {
            "title": "Anki Study Report",
            "period": str(metadata.get("period") or "Не указан"),
            "periodId": str(metadata.get("period_id") or ""),
            "scope": str(metadata.get("scope") or ""),
            "selectedDecks": _dashboard_selected_decks(metadata.get("selected_decks")),
            "includeChildren": bool(metadata.get("include_child_decks")),
            "answerMode": (
                "pass_fail"
                if str(metrics.get("answer_mode") or metadata.get("requested_answer_mode")) == "pass_fail"
                else "standard"
            ),
            "createdAt": str(metadata.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M")),
            "detailMode": str(metadata.get("detail_level") or "normal"),
            "deletedCardReviews": _dashboard_deleted_reviews(metrics.get("deck_breakdown")),
            "unavailableTrackerNotes": _dashboard_tracker_notes(metrics),
        },
        "summary": {
            "verdict": summary_verdict,
            "riskLevel": "danger" if quality_status == "danger" else risk_status,
            "mainAction": main_action,
            "warning": _dashboard_warning(fail_rate),
            "newCardsAdvice": new_cards_advice,
        },
        "kpis": _dashboard_kpis(
            total_reviews,
            pass_rate,
            fail_rate,
            new_cards,
            total_seconds,
            average_answer_seconds,
            heatmap,
            tomorrow,
            next_7,
            next_30,
            fsrs,
            quality_status,
            fail_status,
        ),
        "answerDistribution": _dashboard_answer_distribution(metrics),
        "activity": _dashboard_activity(heatmap),
        "comparison": _dashboard_comparison(metrics.get("comparison")),
        "decks": decks,
        "forecast": _dashboard_forecast(forecast, tomorrow, next_7, next_30, baseline, risk_status),
        "fsrs": _dashboard_fsrs(fsrs, next_30),
        "recommendations": {
            "mainAction": main_action,
            "why": _dashboard_recommendation_why(problem_decks, tomorrow),
            "avoid": _dashboard_recommendation_avoid(pass_rate, risk_status),
            "checklist": _dashboard_checklist(problem_decks, pass_rate),
        },
        "cache": cache_summary if isinstance(cache_summary, dict) else _dashboard_empty_cache_summary(),
    }


def build_default_dashboard_metadata(
    snapshot: dict,
    today_key: str,
    *,
    display_settings: dict | None = None,
    now: datetime | None = None,
) -> dict:
    display = _normalize_dashboard_display_settings(display_settings)
    deck_rows = _filter_snapshot_deck_rows(_sorted_snapshot_rows(snapshot.get("deckDaily")), display, today_key)
    daily_rows = (
        _daily_rows_from_deck_rows(deck_rows)
        if display.get("selected_deck_ids")
        else _filter_snapshot_daily_rows(_sorted_snapshot_rows(snapshot.get("daily")), display, today_key)
    )
    dates = _snapshot_date_keys(daily_rows)
    start_date = dates[0] if dates else "1970-01-01"
    end_date = dates[-1] if dates else today_key
    current = now or datetime.now()
    selected_deck_names = (
        display.get("selected_deck_names")
        if display.get("selected_deck_ids")
        else []
    )
    selected_decks_label = ", ".join(selected_deck_names) if selected_deck_names else "Все колоды"
    return {
        "period": _dashboard_period_label(display, start_date, end_date),
        "period_id": display["period"],
        "period_human": _dashboard_period_human(display),
        "scope": f"Выбранные колоды ({len(selected_deck_names)})" if selected_deck_names else "Все колоды",
        "selected_decks": selected_decks_label,
        "include_child_decks": bool(display.get("include_child_decks", True)),
        "created_at": current.strftime("%Y-%m-%d %H:%M"),
        "detail_level": "normal",
        "requested_answer_mode": "pass_fail",
        "period_start_ts": 0,
        "period_end_ts": int(current.timestamp()),
        "period_start_date": start_date,
        "period_end_date": end_date,
        "today_date": today_key,
        "force_stats_cache_for_report": True,
        "dashboard_display_deck_filter": bool(display.get("selected_deck_ids")),
    }


def metrics_from_cache_snapshot(snapshot: dict, today_key: str, display_settings: dict | None = None) -> dict:
    display = _normalize_dashboard_display_settings(display_settings)
    deck_rows = _filter_snapshot_deck_rows(_sorted_snapshot_rows(snapshot.get("deckDaily")), display, today_key)
    daily_rows = (
        _daily_rows_from_deck_rows(deck_rows)
        if display.get("selected_deck_ids")
        else _filter_snapshot_daily_rows(_sorted_snapshot_rows(snapshot.get("daily")), display, today_key)
    )
    total_reviews = sum(dashboard_int(row.get("reviews")) for row in daily_rows)
    new_cards = sum(dashboard_int(row.get("new_cards")) for row in daily_rows)
    again = sum(dashboard_int(row.get("again")) for row in daily_rows)
    hard = sum(dashboard_int(row.get("hard")) for row in daily_rows)
    good = sum(dashboard_int(row.get("good")) for row in daily_rows)
    easy = sum(dashboard_int(row.get("easy")) for row in daily_rows)
    pass_count = sum(dashboard_int(row.get("pass_count")) for row in daily_rows)
    fail_count = sum(dashboard_int(row.get("fail_count")) for row in daily_rows)
    total_answer_seconds = sum(dashboard_float(row.get("total_answer_seconds")) for row in daily_rows)
    total_seconds = round(sum(dashboard_float(row.get("study_seconds")) for row in daily_rows))
    if pass_count <= 0 and total_reviews > 0:
        pass_count = max(0, total_reviews - fail_count)
    return {
        "total_reviews": total_reviews,
        "new_cards": new_cards,
        "again_count": fail_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_count / total_reviews, 4) if total_reviews else 0,
        "fail_rate": round(fail_count / total_reviews, 4) if total_reviews else 0,
        "total_seconds": total_seconds,
        "estimated_minutes": round(total_seconds / 60),
        "average_answer_seconds": round(total_answer_seconds / total_reviews, 2) if total_reviews else 0,
        "answer_mode": "pass_fail",
        "answer_distribution": {
            "again": again,
            "hard": hard,
            "good": good,
            "easy": easy,
        },
        "pass_fail": {
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "deck_breakdown": _deck_breakdown_from_cache_rows(deck_rows),
        "heatmap": _heatmap_from_cache_rows(daily_rows, today_key, display["period"]),
        "forecast": _cache_default_forecast(),
        "fsrs": _cache_default_fsrs(),
        "real_study_time": unavailable_tracked_time(
            "cache_default_dashboard",
            "Default dashboard uses the persistent stats cache; live session tracking is not recalculated here.",
        ),
        "due_tomorrow": 0,
    }


def dashboard_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def dashboard_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def dashboard_rate(value) -> float:
    number = dashboard_float(value)
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def _normalize_dashboard_display_settings(settings: dict | None) -> dict:
    source = settings if isinstance(settings, dict) else {}
    period = str(source.get("period") or "all_time")
    if period not in {"all_time", "last_7_days", "last_30_days", "custom"}:
        period = "all_time"
    deck_ids = []
    raw_deck_ids = source.get("selected_deck_ids")
    for value in raw_deck_ids if isinstance(raw_deck_ids, list) else []:
        try:
            deck_id = int(value)
        except (TypeError, ValueError):
            continue
        if deck_id not in deck_ids:
            deck_ids.append(deck_id)
    deck_names = []
    raw_deck_names = source.get("selected_deck_names")
    for value in raw_deck_names if isinstance(raw_deck_names, list) else []:
        text = str(value or "").strip()
        if text and text not in deck_names:
            deck_names.append(text)
    return {
        "period": period,
        "custom_start_date": str(source.get("custom_start_date") or "").strip(),
        "custom_end_date": str(source.get("custom_end_date") or "").strip(),
        "selected_deck_ids": deck_ids,
        "selected_deck_names": deck_names,
        "include_child_decks": bool(source.get("include_child_decks", True)),
    }


def _snapshot_date_keys(rows: object) -> list[str]:
    return [str(row.get("date")) for row in _sorted_snapshot_rows(rows) if str(row.get("date") or "")]


def _sorted_snapshot_rows(rows: object) -> list[dict]:
    if not isinstance(rows, list):
        return []
    clean = [dict(row) for row in rows if isinstance(row, dict)]
    return sorted(clean, key=lambda row: (str(row.get("date") or ""), str(row.get("deck_name") or ""), dashboard_int(row.get("deck_id"))))


def _dashboard_period_bounds(settings: dict, today_key: str) -> tuple[str | None, str | None]:
    period = str(settings.get("period") or "all_time")
    today = _parse_date_key(today_key) or date.today()
    if period == "last_7_days":
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if period == "last_30_days":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    if period == "custom":
        start = _parse_date_key(str(settings.get("custom_start_date") or ""))
        end = _parse_date_key(str(settings.get("custom_end_date") or ""))
        if start is not None and end is not None and end >= start:
            return start.isoformat(), end.isoformat()
    return None, None


def _filter_snapshot_daily_rows(rows: list[dict], settings: dict, today_key: str) -> list[dict]:
    start, end = _dashboard_period_bounds(settings, today_key)
    if start is None or end is None:
        return rows
    return [
        row
        for row in rows
        if start <= str(row.get("date") or "") <= end
    ]


def _filter_snapshot_deck_rows(rows: list[dict], settings: dict, today_key: str) -> list[dict]:
    start, end = _dashboard_period_bounds(settings, today_key)
    deck_ids = set(settings.get("selected_deck_ids") or [])
    filtered = []
    for row in rows:
        row_date = str(row.get("date") or "")
        if start is not None and end is not None and not (start <= row_date <= end):
            continue
        if deck_ids and dashboard_int(row.get("deck_id")) not in deck_ids:
            continue
        filtered.append(row)
    return filtered


def _daily_rows_from_deck_rows(rows: list[dict]) -> list[dict]:
    daily: dict[str, dict] = {}
    for row in rows:
        row_date = str(row.get("date") or "")
        if not row_date:
            continue
        day = daily.setdefault(
            row_date,
            {
                "date": row_date,
                "reviews": 0,
                "new_cards": 0,
                "again": 0,
                "hard": 0,
                "good": 0,
                "easy": 0,
                "pass_count": 0,
                "fail_count": 0,
                "study_seconds": 0,
                "total_answer_seconds": 0.0,
            },
        )
        day["reviews"] += dashboard_int(row.get("reviews"))
        day["new_cards"] += dashboard_int(row.get("new_cards"))
        day["again"] += dashboard_int(row.get("again"))
        day["hard"] += dashboard_int(row.get("hard"))
        day["good"] += dashboard_int(row.get("good"))
        day["easy"] += dashboard_int(row.get("easy"))
        day["pass_count"] += dashboard_int(row.get("pass_count"))
        day["fail_count"] += dashboard_int(row.get("fail_count"))
        day["study_seconds"] += dashboard_int(row.get("study_seconds"))
        day["total_answer_seconds"] += dashboard_float(row.get("total_answer_seconds"))
    return [daily[key] for key in sorted(daily)]


def _deck_names_from_rows(rows: list[dict]) -> list[str]:
    names = []
    for row in rows:
        name = str(row.get("deck_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _dashboard_period_label(settings: dict, start_date: str, end_date: str) -> str:
    period = str(settings.get("period") or "all_time")
    if period == "last_7_days":
        return "Неделя"
    if period == "last_30_days":
        return "Месяц"
    if period == "custom":
        start = str(settings.get("custom_start_date") or start_date)
        end = str(settings.get("custom_end_date") or end_date)
        return f"{start} — {end}" if start and end else "Выбранный период"
    return "Всё время"


def _dashboard_period_human(settings: dict) -> str:
    period = str(settings.get("period") or "all_time")
    if period == "last_7_days":
        return "за неделю"
    if period == "last_30_days":
        return "за месяц"
    if period == "custom":
        return "за выбранный период"
    return "за всё время"


def _deck_breakdown_from_cache_rows(rows: list[dict]) -> list[dict]:
    decks: dict[int, dict] = {}
    for row in rows:
        deck_id = dashboard_int(row.get("deck_id"))
        if deck_id <= 0:
            continue
        deck = decks.setdefault(
            deck_id,
            {
                "deck_id": deck_id,
                "deck_name": str(row.get("deck_name") or f"Deck {deck_id}"),
                "total_reviews": 0,
                "new_cards": 0,
                "again_count": 0,
                "hard_count": 0,
                "good_count": 0,
                "easy_count": 0,
                "pass_count": 0,
                "fail_count": 0,
                "total_seconds": 0,
                "total_answer_seconds": 0.0,
            },
        )
        deck["total_reviews"] += dashboard_int(row.get("reviews"))
        deck["new_cards"] += dashboard_int(row.get("new_cards"))
        deck["again_count"] += dashboard_int(row.get("again"))
        deck["hard_count"] += dashboard_int(row.get("hard"))
        deck["good_count"] += dashboard_int(row.get("good"))
        deck["easy_count"] += dashboard_int(row.get("easy"))
        deck["pass_count"] += dashboard_int(row.get("pass_count"))
        deck["fail_count"] += dashboard_int(row.get("fail_count"))
        deck["total_seconds"] += dashboard_int(row.get("study_seconds"))
        deck["total_answer_seconds"] += dashboard_float(row.get("total_answer_seconds"))

    result = []
    for deck in decks.values():
        total = dashboard_int(deck.get("total_reviews"))
        fail_count = dashboard_int(deck.get("fail_count"))
        if dashboard_int(deck.get("pass_count")) <= 0 and total > 0:
            deck["pass_count"] = max(0, total - fail_count)
        deck["pass_rate"] = round(dashboard_int(deck.get("pass_count")) / total, 4) if total else 0
        deck["fail_rate"] = round(fail_count / total, 4) if total else 0
        deck["average_answer_seconds"] = round(dashboard_float(deck.get("total_answer_seconds")) / total, 2) if total else 0
        result.append(deck)
    return sorted(result, key=lambda deck: dashboard_int(deck.get("total_reviews")), reverse=True)


def _heatmap_from_cache_rows(rows: list[dict], today_key: str, period: str = "all_time") -> dict:
    if not rows:
        return {
            "available": False,
            "active_days": 0,
            "missed_days": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "total_days": 0,
            "best_days": [],
            "weekday_average": {},
            "reviews_by_day": [],
        }

    reviews_by_day = [
        {
            "date": str(row.get("date") or ""),
            "reviews": dashboard_int(row.get("reviews")),
            "new_cards": dashboard_int(row.get("new_cards")),
            "again": dashboard_int(row.get("again")),
            "total_seconds": dashboard_int(row.get("study_seconds")),
        }
        for row in rows
    ]
    active_dates = {
        str(row.get("date"))
        for row in rows
        if str(row.get("date") or "") and dashboard_int(row.get("reviews")) > 0
    }
    first_date = _parse_date_key(str(rows[0].get("date") or ""))
    last_date = _parse_date_key(str(rows[-1].get("date") or ""))
    if first_date is None or last_date is None:
        total_days = len(rows)
    else:
        total_days = max(1, (last_date - first_date).days + 1)

    return {
        "available": True,
        "active_days": len(active_dates),
        "missed_days": max(0, total_days - len(active_dates)),
        "current_streak": _current_streak(active_dates, today_key),
        "longest_streak": _longest_streak(active_dates),
        "total_days": total_days,
        "best_days": sorted(
            reviews_by_day,
            key=lambda row: dashboard_int(row.get("reviews")),
            reverse=True,
        )[:5],
        "weekday_average": _weekday_average_from_cache_rows(rows),
        "reviews_by_day": reviews_by_day,
        "source": {"type": "stats_cache", "period": period},
    }


def _weekday_average_from_cache_rows(rows: list[dict]) -> dict[str, float]:
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    totals = {name: {"reviews": 0, "days": 0} for name in weekday_names}
    for row in rows:
        parsed = _parse_date_key(str(row.get("date") or ""))
        if parsed is None:
            continue
        bucket = totals[weekday_names[parsed.weekday()]]
        bucket["reviews"] += dashboard_int(row.get("reviews"))
        bucket["days"] += 1
    return {
        name: round(values["reviews"] / values["days"], 2) if values["days"] else 0
        for name, values in totals.items()
    }


def _current_streak(active_dates: set[str], today_key: str) -> int:
    current = _parse_date_key(today_key) or date.today()
    streak = 0
    while current.isoformat() in active_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def _longest_streak(active_dates: set[str]) -> int:
    parsed_dates = sorted(
        parsed
        for parsed in (_parse_date_key(value) for value in active_dates)
        if parsed is not None
    )
    longest = 0
    current = 0
    previous: date | None = None
    for parsed in parsed_dates:
        if previous is not None and (parsed - previous).days == 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = parsed
    return longest


def _parse_date_key(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _cache_default_forecast() -> dict:
    return {
        "available": False,
        "baseline": {},
        "due_forecast": {
            "tomorrow": 0,
            "next_7_days_total": 0,
            "next_30_days_total": 0,
            "daily": [],
        },
        "recommendation": {
            "risk": "low",
            "summary": "Прогноз очереди не пересчитывается при cache-first открытии dashboard.",
            "new_cards_advice": "Настройте отображение на сайте; due-прогноз появится в live-режимах отчёта.",
        },
    }


def _cache_default_fsrs() -> dict:
    return {
        "enabled": False,
        "source": {},
        "memory_state": {},
        "future_load": {},
        "deck_settings": [],
        "recommendation": {
            "summary": "FSRS-метрики не пересчитываются при cache-first открытии dashboard.",
        },
    }


def _dashboard_empty_cache_summary() -> dict:
    return {
        "status": "error",
        "updatedAt": 0,
        "cachedDays": 0,
        "cachedDeckDays": 0,
    }


def _dashboard_kpis(
    total_reviews: int,
    pass_rate: float,
    fail_rate: float,
    new_cards: int,
    total_seconds: int,
    average_answer_seconds: float,
    heatmap: dict,
    tomorrow: int,
    next_7: int,
    next_30: int,
    fsrs: dict,
    quality_status: str,
    fail_status: str,
) -> list[dict]:
    fsrs_memory = fsrs.get("memory_state") if isinstance(fsrs.get("memory_state"), dict) else {}
    predicted_recall = _dashboard_optional_rate(fsrs_memory.get("average_recall"))
    return [
        _dashboard_kpi("total_reviews", "Total reviews", _dashboard_format_int(total_reviews), "за выбранный период", "good", "layers"),
        _dashboard_kpi("pass_rate", "Pass rate", _dashboard_format_percent(pass_rate), "качество ответов", quality_status, "check"),
        _dashboard_kpi("fail_rate", "Fail rate", _dashboard_format_percent(fail_rate), "ошибки за период", fail_status, "alert"),
        _dashboard_kpi("new_cards", "New cards", _dashboard_format_int(new_cards), "новые карточки", "warning" if new_cards >= 50 else "neutral", "sparkles"),
        _dashboard_kpi("study_time", "Study time", _dashboard_format_duration(total_seconds), "оценка по revlog", "neutral", "clock"),
        _dashboard_kpi("average_answer_time", "Average answer time", _dashboard_format_seconds(average_answer_seconds), "средний ответ", "good", "timer"),
        _dashboard_kpi("active_days", "Active days", _dashboard_format_int(dashboard_int(heatmap.get("active_days"))), "дни с повторениями", "good", "calendar"),
        _dashboard_kpi("missed_days", "Missed days", _dashboard_format_int(dashboard_int(heatmap.get("missed_days"))), "дни без повторений", "neutral", "pause"),
        _dashboard_kpi("current_streak", "Current streak", f"{dashboard_int(heatmap.get('current_streak'))} дней", "текущая серия", "good", "flame"),
        _dashboard_kpi("best_streak", "Best streak", f"{dashboard_int(heatmap.get('longest_streak'))} дней", "лучшая серия", "good", "trophy"),
        _dashboard_kpi("tomorrow_due", "Tomorrow due", _dashboard_format_int(tomorrow), "очередь на завтра", "warning" if tomorrow >= 100 else "good", "sun"),
        _dashboard_kpi("forecast_7", "7-day forecast", _dashboard_format_int(next_7), "следующие 7 дней", "neutral", "line"),
        _dashboard_kpi("forecast_30", "30-day forecast", _dashboard_format_int(next_30), "следующие 30 дней", "neutral", "bar"),
        _dashboard_kpi("fsrs_predicted_recall", "FSRS predicted recall", _dashboard_format_percent(predicted_recall) if predicted_recall is not None else "Нет данных", "average recall", "warning" if predicted_recall is not None and predicted_recall < 0.9 else "neutral", "brain"),
    ]


def _dashboard_kpi(
    metric_id: str,
    label: str,
    value: str,
    caption: str,
    status: str,
    icon: str,
) -> dict:
    return {
        "id": metric_id,
        "label": label,
        "value": value,
        "caption": caption,
        "status": _dashboard_status(status),
        "icon": icon,
    }


def _dashboard_answer_distribution(metrics: dict) -> list[dict]:
    distribution = (
        metrics.get("answer_distribution")
        if isinstance(metrics.get("answer_distribution"), dict)
        else {}
    )
    pass_fail = (
        metrics.get("pass_fail") if isinstance(metrics.get("pass_fail"), dict) else {}
    )
    return [
        {"label": "Pass", "value": dashboard_int(pass_fail.get("pass_count") or distribution.get("good")), "color": "#67d391"},
        {"label": "Fail", "value": dashboard_int(pass_fail.get("fail_count") or distribution.get("again")), "color": "#ef6f6c"},
        {"label": "Hard", "value": dashboard_int(distribution.get("hard")), "color": "#f6c177"},
        {"label": "Easy", "value": dashboard_int(distribution.get("easy")), "color": "#3db4f2"},
    ]


def _dashboard_activity(heatmap: dict) -> dict:
    days = [
        {
            "date": str(day.get("date") or ""),
            "reviews": dashboard_int(day.get("reviews")),
            "newCards": dashboard_int(day.get("new_cards")),
            "again": dashboard_int(day.get("again")),
            "studySeconds": dashboard_int(day.get("total_seconds")),
        }
        for day in _dashboard_list(heatmap.get("reviews_by_day"))
    ]
    best_days = _dashboard_list(heatmap.get("best_days"))
    best_day = "Нет данных"
    if best_days:
        best = best_days[0]
        best_day = f"{best.get('date')}, {dashboard_int(best.get('reviews'))} reviews"
    weekday_average = heatmap.get("weekday_average")
    if not isinstance(weekday_average, dict):
        weekday_average = {}
    return {
        "available": bool(heatmap.get("available")),
        "activeDays": dashboard_int(heatmap.get("active_days")),
        "missedDays": dashboard_int(heatmap.get("missed_days")),
        "currentStreak": dashboard_int(heatmap.get("current_streak")),
        "bestStreak": dashboard_int(heatmap.get("longest_streak")),
        "bestDay": best_day,
        "weekdayAverage": [
            {
                "day": _dashboard_short_day(day),
                "reviews": dashboard_float(value),
                "activeRate": 0,
            }
            for day, value in weekday_average.items()
        ],
        "days": days,
    }


def _dashboard_comparison(comparison: object) -> dict:
    data = comparison if isinstance(comparison, dict) else {}
    baselines = data.get("baselines") if isinstance(data.get("baselines"), dict) else {}
    comparisons = data.get("comparisons") if isinstance(data.get("comparisons"), dict) else {}
    return {
        "available": bool(data.get("available")),
        "message": str(
            data.get("message")
            or "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы."
        ),
        "today": _dashboard_comparison_stats(data.get("today"), "Сегодня"),
        "baselines": {
            "yesterday": _dashboard_comparison_stats(baselines.get("yesterday"), "Вчера"),
            "avg7": _dashboard_comparison_stats(baselines.get("avg7"), "Последние 7 дней"),
            "avg30": _dashboard_comparison_stats(baselines.get("avg30"), "Последние 30 дней"),
            "sameWeekdayLastWeek": _dashboard_comparison_stats(
                baselines.get("sameWeekdayLastWeek"),
                "Этот день прошлой недели",
            ),
            "currentWeek": _dashboard_comparison_stats(baselines.get("currentWeek"), "Эта неделя"),
            "previousWeek": _dashboard_comparison_stats(baselines.get("previousWeek"), "Прошлая неделя"),
            "currentMonth": _dashboard_comparison_stats(baselines.get("currentMonth"), "Этот месяц"),
            "previousMonth": _dashboard_comparison_stats(baselines.get("previousMonth"), "Прошлый месяц"),
        },
        "comparisons": {
            "yesterday": _dashboard_comparison_delta(comparisons.get("yesterday")),
            "avg7": _dashboard_comparison_delta(comparisons.get("avg7")),
            "avg30": _dashboard_comparison_delta(comparisons.get("avg30")),
            "sameWeekdayLastWeek": _dashboard_comparison_delta(comparisons.get("sameWeekdayLastWeek")),
            "week": _dashboard_comparison_delta(comparisons.get("week")),
            "month": _dashboard_comparison_delta(comparisons.get("month")),
        },
        "insights": _dashboard_comparison_insights(data.get("insights")),
        "source": data.get("source") if isinstance(data.get("source"), dict) else {},
    }


def _dashboard_comparison_stats(value: object, fallback_label: str) -> dict:
    item = value if isinstance(value, dict) else {}
    return {
        "date": str(item.get("date") or ""),
        "label": str(item.get("label") or fallback_label),
        "reviews": dashboard_int(item.get("reviews")),
        "newCards": dashboard_int(item.get("newCards")),
        "pass": dashboard_int(item.get("pass")),
        "fail": dashboard_int(item.get("fail")),
        "hard": dashboard_int(item.get("hard")),
        "easy": dashboard_int(item.get("easy")),
        "studySeconds": dashboard_int(item.get("studySeconds")),
        "studyMinutes": dashboard_int(item.get("studyMinutes")),
        "avgAnswerSeconds": _dashboard_optional_float(item.get("avgAnswerSeconds")),
        "activeDecks": dashboard_int(item.get("activeDecks")),
        "passRate": _dashboard_optional_rate(item.get("passRate")),
        "failRate": _dashboard_optional_rate(item.get("failRate")),
    }


def _dashboard_comparison_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {
        "reviews": _dashboard_metric_delta(data.get("reviews")),
        "newCards": _dashboard_metric_delta(data.get("newCards")),
        "studyMinutes": _dashboard_metric_delta(data.get("studyMinutes")),
        "passRate": _dashboard_rate_delta(data.get("passRate")),
        "failRate": _dashboard_rate_delta(data.get("failRate")),
        "avgAnswerSeconds": _dashboard_metric_delta(data.get("avgAnswerSeconds")),
        "activeDecks": _dashboard_metric_delta(data.get("activeDecks")),
    }


def _dashboard_metric_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {
        "delta": _dashboard_optional_float(data.get("delta")),
        "percentDelta": _dashboard_optional_float(data.get("percentDelta")),
    }


def _dashboard_rate_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {"deltaPp": _dashboard_optional_float(data.get("deltaPp"))}


def _dashboard_comparison_insights(value: object) -> list[dict]:
    insights = []
    for item in _dashboard_list(value):
        severity = str(item.get("severity") or "neutral")
        if severity not in {"positive", "neutral", "warning", "danger"}:
            severity = "neutral"
        insights.append(
            {
                "severity": severity,
                "title": str(item.get("title") or "Сравнение"),
                "text": str(item.get("text") or ""),
                "metric": str(item.get("metric") or ""),
            }
        )
    return insights


def _dashboard_decks(deck_breakdown) -> list[dict]:
    decks = []
    for index, deck in enumerate(_dashboard_list(deck_breakdown), start=1):
        total = dashboard_int(deck.get("total_reviews"))
        fail = dashboard_int(deck.get("fail_count") or deck.get("again_count"))
        pass_count = dashboard_int(deck.get("pass_count")) or max(0, total - fail)
        pass_rate = dashboard_rate(deck.get("pass_rate"))
        average_answer_seconds = dashboard_float(deck.get("average_answer_seconds"))
        status = _dashboard_deck_status(pass_rate, total, fail)
        decks.append(
            {
                "id": dashboard_int(deck.get("deck_id")) or index,
                "name": str(deck.get("deck_name") or f"Колода {index}"),
                "totalReviews": total,
                "newCards": dashboard_int(deck.get("new_cards")),
                "passCount": pass_count,
                "failCount": fail,
                "hardCount": dashboard_int(deck.get("hard_count")),
                "easyCount": dashboard_int(deck.get("easy_count")),
                "passRate": pass_rate,
                "failRate": dashboard_rate(deck.get("fail_rate")),
                "averageAnswerSeconds": average_answer_seconds,
                "studyMinutes": round(dashboard_int(deck.get("total_seconds")) / 60),
                "status": status,
                "explanation": _dashboard_deck_explanation(status, fail, average_answer_seconds),
            }
        )
    return decks


def _dashboard_forecast(
    forecast: dict,
    tomorrow: int,
    next_7: int,
    next_30: int,
    baseline: dict,
    risk_status: str,
) -> dict:
    due_forecast = forecast.get("due_forecast") if isinstance(forecast.get("due_forecast"), dict) else {}
    recommendation = (
        forecast.get("recommendation")
        if isinstance(forecast.get("recommendation"), dict)
        else {}
    )
    daily = []
    for item in _dashboard_list(due_forecast.get("daily")):
        daily.append(
            {
                "offset": dashboard_int(item.get("offset")),
                "date": str(item.get("date") or item.get("offset") or ""),
                "due": dashboard_int(item.get("due")),
                "reviewDue": dashboard_int(item.get("review_due")),
                "learningDue": dashboard_int(item.get("learning_due")),
                "risk": str(item.get("risk") or "low"),
            }
        )
    return {
        "available": bool(forecast.get("available")),
        "tomorrow": tomorrow,
        "next7Days": next_7,
        "next30Days": next_30,
        "activeDayBaseline": dashboard_float(baseline.get("median_reviews_active_day")),
        "overloadRisk": risk_status,
        "daily": daily,
        "recommendation": str(recommendation.get("new_cards_advice") or recommendation.get("summary") or "Прогноз пока недоступен."),
    }


def _dashboard_fsrs(fsrs: dict, fallback_future_load: int) -> dict:
    memory = fsrs.get("memory_state") if isinstance(fsrs.get("memory_state"), dict) else {}
    future = fsrs.get("future_load") if isinstance(fsrs.get("future_load"), dict) else {}
    source = fsrs.get("source") if isinstance(fsrs.get("source"), dict) else {}
    settings = _dashboard_fsrs_settings(fsrs)
    return {
        "predictedRecall": _dashboard_optional_rate(memory.get("average_recall")),
        "cardsBelowTarget": dashboard_int(memory.get("below_90_count")),
        "highForgettingRisk": dashboard_int(memory.get("high_risk_count")),
        "averageDifficulty": _dashboard_optional_float(memory.get("average_difficulty")),
        "futureLoad30Days": dashboard_int(future.get("next_30_days") or fallback_future_load),
        "settings": {
            "enabled": bool(fsrs.get("enabled")),
            "desiredRetention": settings.get("desiredRetention"),
            "helperDetected": bool(source.get("helper_detected")),
            "helperConfigAvailable": bool(source.get("helper_config_available")),
            "rescheduleEnabled": bool(settings.get("rescheduleEnabled")),
            "autoDisperse": bool(settings.get("autoDisperse")),
        },
    }


def _dashboard_fsrs_settings(fsrs: dict) -> dict:
    deck_settings = _dashboard_list(fsrs.get("deck_settings"))
    desired = None
    for item in deck_settings:
        desired = _dashboard_optional_rate(item.get("desired_retention"))
        if desired is not None:
            break
    return {
        "desiredRetention": desired,
        "rescheduleEnabled": False,
        "autoDisperse": False,
    }


def _dashboard_selected_decks(value) -> list[str]:
    text = str(value or "Не указаны")
    if not text:
        return ["Не указаны"]
    return [part.strip() for part in text.split(",") if part.strip()] or [text]


def _dashboard_tracker_notes(metrics: dict) -> list[str]:
    notes = []
    real_time = metrics.get("real_study_time")
    if isinstance(real_time, dict) and not real_time.get("available"):
        notes.append(str(real_time.get("explanation") or "Real study time недоступен."))
    return notes


def _dashboard_deleted_reviews(deck_breakdown) -> int:
    total = 0
    for deck in _dashboard_list(deck_breakdown):
        name = str(deck.get("deck_name") or "").lower()
        if "удал" in name or "deleted" in name:
            total += dashboard_int(deck.get("total_reviews"))
    return total


def _dashboard_summary_verdict(
    pass_rate: float,
    fail_rate: float,
    tomorrow: int,
    hardest_deck: str,
    risk_status: str,
) -> str:
    quality = "хорошее" if pass_rate >= 0.85 else "ошибок много" if fail_rate >= 0.2 else "качество среднее"
    load = "ближайшая очередь лёгкая" if tomorrow < 60 else "нагрузка заметная"
    action = f"Сначала разобрать {hardest_deck}" if hardest_deck != "проблемные колоды не выделены" else "Продолжать обычный темп"
    if risk_status == "danger":
        load = "есть риск перегруза"
    return f"Pass rate {_dashboard_format_percent(pass_rate)}: {quality}, {load}. {action}."


def _dashboard_main_action(problem_decks: list[dict]) -> str:
    if not problem_decks:
        return "Поддержать серию и продолжать обычный темп повторений."
    names = [deck["name"] for deck in problem_decks[:2]]
    return "Разобрать " + " и ".join(names) + "."


def _dashboard_new_cards_advice(pass_rate: float, risk_status: str) -> str:
    if pass_rate < 0.8 or risk_status in {"warning", "danger"}:
        return "Новые карточки лучше временно снизить и вернуть после стабилизации качества."
    return "Новые можно добавлять умеренно, если очередь остаётся комфортной."


def _dashboard_warning(fail_rate: float) -> str:
    if fail_rate >= 0.2:
        return f"Fail rate {_dashboard_format_percent(fail_rate)} выше комфортного уровня."
    return "Критичного fail rate не видно."


def _dashboard_recommendation_why(problem_decks: list[dict], tomorrow: int) -> str:
    if problem_decks:
        return "Эти колоды дают основную часть ошибок; текущая очередь позволяет сначала поднять качество."
    if tomorrow > 0:
        return "Очередь на завтра есть, но явных проблемных колод за период не видно."
    return "На завтра заметной due-нагрузки не видно."


def _dashboard_recommendation_avoid(pass_rate: float, risk_status: str) -> str:
    if pass_rate < 0.8 or risk_status in {"warning", "danger"}:
        return "Пока не повышать лимит новых и не открывать тяжёлые уроки."
    return "Не разгонять новые карточки резко; держать стабильный темп."


def _dashboard_checklist(problem_decks: list[dict], pass_rate: float) -> list[str]:
    items = [f"Разобрать {deck['name']}." for deck in problem_decks[:3]]
    if pass_rate < 0.8:
        items.append("Временно снизить новые карточки.")
        items.append("Вернуть новые после стабилизации pass rate.")
    if not items:
        items.append("Сделать обычную короткую сессию повторений.")
    return items


def _dashboard_deck_status(pass_rate: float, total: int, fail_count: int) -> str:
    if total <= 0:
        return "neutral"
    if pass_rate < 0.7 or fail_count >= 30:
        return "danger"
    if pass_rate < 0.82 or fail_count >= 15:
        return "warning"
    if pass_rate >= 0.88:
        return "good"
    return "neutral"


def _dashboard_deck_explanation(status: str, fail_count: int, average_answer_seconds: float) -> str:
    if status == "danger":
        return "много Fail, лучше разобрать до новых карточек"
    if status == "warning":
        return "ошибки заметны, нагрузку лучше не повышать"
    if average_answer_seconds >= 15:
        return "ответы медленные, стоит проверить сложные карточки"
    if fail_count <= 5:
        return "ошибки редкие, можно продолжать обычный темп"
    return "стабильная колода без явного риска"


def _dashboard_quality_status(pass_rate: float, total_reviews: int) -> str:
    if total_reviews <= 0:
        return "neutral"
    if pass_rate >= 0.88:
        return "good"
    if pass_rate >= 0.8:
        return "warning"
    return "danger"


def _dashboard_risk_status(risk: str) -> str:
    if risk == "high":
        return "danger"
    if risk == "medium":
        return "warning"
    if risk == "low":
        return "good"
    return "neutral"


def _dashboard_status(value: str) -> str:
    return value if value in {"good", "neutral", "warning", "danger"} else "neutral"


def _dashboard_fail_count(metrics: dict) -> int:
    pass_fail = metrics.get("pass_fail") if isinstance(metrics.get("pass_fail"), dict) else {}
    return dashboard_int(metrics.get("fail_count") or pass_fail.get("fail_count") or metrics.get("again_count"))


def _dashboard_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dashboard_short_day(value) -> str:
    return {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }.get(str(value), str(value)[:3])


def _dashboard_optional_rate(value) -> float | None:
    if value is None:
        return None
    return dashboard_rate(value)


def _dashboard_optional_float(value) -> float | None:
    if value is None:
        return None
    return dashboard_float(value)


def _dashboard_format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _dashboard_format_percent(value: float) -> str:
    return f"{round(dashboard_rate(value) * 100)}%"


def _dashboard_format_duration(seconds: int) -> str:
    minutes = round(max(0, seconds) / 60)
    if minutes <= 0:
        return "0 мин"
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} ч {rest} мин"
    if hours:
        return f"{hours} ч"
    return f"{minutes} мин"


def _dashboard_format_seconds(seconds: float) -> str:
    if seconds <= 0:
        return "0 сек"
    if seconds >= 60:
        return _dashboard_format_duration(round(seconds))
    if float(seconds).is_integer():
        return f"{int(seconds)} сек"
    return f"{seconds:.1f} сек"
