"""Build human-readable Russian reports from collected study metrics."""

from __future__ import annotations

from datetime import datetime
from html import escape
import re
from typing import Any

from . import templates


def build_report(
    metrics: dict[str, Any],
    template: str = "short",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Render metrics as a useful Russian study report.

    Supported templates:
        short: 3-5 plain-text lines.
        detailed: grouped plain-text blocks.
        markdown: Markdown report for copying.
    """

    meta = _metadata_context(metadata)
    if template == "short":
        return _plain_report(metrics, meta, "compact").strip()
    if template == "detailed":
        return _plain_report(metrics, meta, meta["detail_level"]).strip()
    if template == "markdown":
        return _markdown_report(metrics, metadata).strip()
    raise ValueError(f"Unknown report template: {template}")


def build_markdown_report(
    metrics: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> str:
    return build_report(metrics, "markdown", metadata)


def render_html_report(
    metrics: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Render metrics as local, self-contained HTML for QTextEdit."""

    meta = _metadata_context(context)
    text_context = _context(metrics, meta)
    markdown_context = _markdown_context(metrics, meta)
    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    again_count = _as_int(metrics.get("again_count"))
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
    due_tomorrow = _as_int(metrics.get("due_tomorrow"))
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))
    best_decks = _best_decks(metrics.get("deck_breakdown"))
    hardest_decks = _hardest_decks(metrics.get("deck_breakdown"))
    quality_status = _quality_status(total_reviews, pass_rate)
    tomorrow_status = _tomorrow_status(total_reviews, due_tomorrow)
    problem_status = "bad" if problem_decks else "good"
    main_rows = _main_metrics_rows(markdown_context, metrics)

    blocks = [
        _html_block(
            "Режим ответов",
            _html_actions(markdown_context["answer_mode_block"]),
            "neutral",
        ),
        _html_block(
            "Короткий вывод",
            _html_paragraph(markdown_context["short_conclusion"]),
            quality_status,
        ),
        _html_block(
            "Итоги",
            _html_metrics_table(main_rows),
            quality_status,
        ),
        _html_block(
            "Активность",
            _html_activity(metrics.get("heatmap")),
            _activity_status(metrics.get("heatmap")),
        ),
        _html_block(
            "Распределение ответов",
            _html_metrics_table(_answer_distribution_rows(metrics)),
            "neutral",
        ),
        _html_block(
            "Качество",
            _html_paragraph(markdown_context["quality"]),
            quality_status,
        ),
        _html_block(
            "Таблица по колодам",
            _html_deck_breakdown(metrics),
            "neutral",
        ),
        _html_block(
            "Лучшие колоды",
            _html_ranked_decks(best_decks, pass_fail=_is_pass_fail_metrics(metrics)),
            "good" if best_decks else "neutral",
        ),
        _html_block(
            "Самые тяжёлые колоды",
            _html_ranked_decks(
                hardest_decks,
                hardest=True,
                pass_fail=_is_pass_fail_metrics(metrics),
            ),
            problem_status,
        ),
        _html_block(
            _future_load_title(meta),
            _html_paragraph(markdown_context["tomorrow"]),
            tomorrow_status,
        ),
        _html_block(
            "Прогноз",
            _html_forecast(metrics.get("forecast")),
            _forecast_status(metrics.get("forecast")),
        ),
        _html_block(
            "FSRS и нагрузка",
            _html_fsrs(metrics.get("fsrs")),
            _fsrs_status(metrics.get("fsrs")),
        ),
        _html_block(
            "Следующее действие",
            _html_actions(text_context["next_actions"]),
            _next_action_status(total_reviews, pass_rate, due_tomorrow),
        ),
    ]

    if meta["detail_level"] == "full":
        blocks.extend(
            [
                _html_block(
                    "Топ колод",
                    _html_top_decks(metrics),
                    "neutral",
                ),
                _html_block(
                    "Средние значения",
                    _html_metrics_table(_average_metric_rows(metrics, meta)),
                    "neutral",
                ),
                _html_block(
                    "Пояснение порогов",
                    _html_actions(_thresholds_text().replace(". ", ".\n")),
                    "neutral",
                ),
                _html_block(
                    "Технически",
                    _html_actions(_technical_text(meta, metrics)),
                    "neutral",
                ),
            ]
        )

    return "\n".join(
        [
            "<!doctype html>",
            "<html>",
            "<head>",
            '<meta charset="utf-8">',
            _html_style(),
            "</head>",
            "<body>",
            '<div class="report">',
            "<header>",
            "<h1>Anki Study Report</h1>",
            '<div class="meta">',
            f"<span>Период: {_html(meta['period'])}</span>",
            f"<span>Область: {_html(meta['scope'])}</span>",
            f"<span>Колоды: {_html(meta['selected_decks'])}</span>",
            f"<span>Дочерние: {_html(meta['include_child_decks'])}</span>",
            f"<span>Создано: {_html(meta['created_at'])}</span>",
            "</div>",
            "</header>",
            '<main class="grid">',
            *blocks,
            "</main>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )


def _markdown_report(
    metrics: dict[str, Any],
    metadata: dict[str, Any] | None,
) -> str:
    meta = _metadata_context(metadata)
    context = _markdown_context(metrics, meta)
    lines = _markdown_header(meta, metrics)
    lines.extend(
        [
            _short_conclusion_markdown(metrics, meta),
            "",
        ]
    )

    if meta["detail_level"] == "compact":
        lines.extend(
            [
                "### KPI",
                _main_metrics_table(context, metrics),
                "",
                "### Прогноз нагрузки",
                context["forecast"],
                "",
                "### Что требует внимания",
                _attention_table(metrics, limit=3),
                "",
                "### Следующее действие",
                context["next_actions"],
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "### KPI",
            _main_metrics_table(context, metrics),
            "",
            "### Активность",
            context["activity"],
            "",
            "### Качество",
            context["quality"],
            "",
            "### Прогноз нагрузки",
            context["forecast"],
            "",
            "### FSRS",
            context["fsrs"],
            "",
            "### Лучшие колоды",
            context["best_decks_table"],
            "",
            "### Тяжёлые колоды",
            context["hardest_decks_table"],
            "",
            "### Что требует внимания",
            _attention_table(metrics, limit=5),
            "",
            "### Таблица по колодам",
            _deck_breakdown_table(
                metrics,
                limit=None if meta["detail_level"] == "full" else 25,
                include_deleted=meta["detail_level"] == "full",
            ),
            "",
            "### Распределение ответов",
            context["answer_distribution_table"],
            "",
            "### Следующее действие",
            context["next_actions"],
        ]
    )

    if meta["detail_level"] == "full":
        lines.extend(
            [
                "",
                "### Топ колод",
                context["top_decks_table"],
                "",
                "### Средние значения",
                _averages_markdown(metrics, meta),
                "",
                "### Пояснение порогов",
                _thresholds_markdown(),
                "",
                "### Технические детали",
                _technical_markdown(meta, metrics),
            ]
        )

    return "\n".join(lines)


def _metadata_context(metadata: dict[str, Any] | None) -> dict[str, str]:
    metadata = metadata or {}
    return {
        "period": str(metadata.get("period") or "Не указан"),
        "period_id": str(metadata.get("period_id") or ""),
        "period_human": str(metadata.get("period_human") or "за выбранный период"),
        "scope": str(metadata.get("scope") or "Не указана"),
        "selected_decks": str(metadata.get("selected_decks") or "Не указаны"),
        "include_child_decks": _yes_no(metadata.get("include_child_decks")),
        "created_at": str(metadata.get("created_at") or _created_at()),
        "detail_level": _normalize_detail_level(metadata.get("detail_level")),
        "requested_answer_mode": _normalize_answer_mode(
            metadata.get("requested_answer_mode")
        ),
    }


def _markdown_context(metrics: dict[str, Any], meta: dict[str, str]) -> dict[str, str]:
    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    again_count = _as_int(metrics.get("again_count"))
    fail_count = _fail_count(metrics)
    pass_count = _pass_count(metrics)
    total_seconds = _as_int(metrics.get("total_seconds"))
    estimated_minutes = _as_float(metrics.get("estimated_minutes"))
    average_answer_seconds = _as_float(metrics.get("average_answer_seconds"))
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
    due_tomorrow = _as_int(metrics.get("due_tomorrow"))
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))
    hardest_decks = _hardest_decks(metrics.get("deck_breakdown"))

    return {
        "total_reviews": format_int(total_reviews),
        "new_cards": format_int(new_cards),
        "again_count": format_int(again_count),
        "fail_count": format_int(fail_count),
        "pass_count": format_int(pass_count),
        "pass_rate": format_percent(pass_rate),
        "fail_rate": format_percent(metrics.get("fail_rate")),
        "answer_mode": _answer_mode_label(metrics),
        "answer_mode_block": _answer_mode_markdown(metrics, meta),
        "study_time": _answer_time_text(total_seconds, estimated_minutes),
        "answer_time": _answer_time_text(total_seconds, estimated_minutes),
        "real_study_time": _real_study_time_text(metrics),
        "average_answer_time": format_answer_seconds(average_answer_seconds),
        "short_conclusion": _short_conclusion(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "quality": _markdown_quality(
            total_reviews,
            again_count,
            pass_rate,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "problem_decks_table": _problem_decks_table(
            problem_decks,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "deck_breakdown_table": _deck_breakdown_table(metrics),
        "answer_distribution_table": _answer_distribution_table(metrics),
        "best_decks_table": _ranked_decks_table(
            _best_decks(metrics.get("deck_breakdown")),
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "hardest_decks_table": _ranked_decks_table(
            hardest_decks,
            hardest=True,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "tomorrow": _markdown_tomorrow(total_reviews, due_tomorrow),
        "activity": _activity_markdown(metrics.get("heatmap")),
        "forecast": _forecast_markdown(
            metrics.get("forecast"),
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "fsrs": _fsrs_markdown(metrics.get("fsrs"), metrics),
        "top_decks_table": _top_decks_table(metrics),
        "recommendations": _recommendations(
            total_reviews,
            pass_rate,
            due_tomorrow,
            hardest_decks,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "next_actions": _next_actions(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            problem_decks,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
    }


def _context(metrics: dict[str, Any], meta: dict[str, str]) -> dict[str, Any]:
    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    again_count = _as_int(metrics.get("again_count"))
    fail_count = _fail_count(metrics)
    pass_count = _pass_count(metrics)
    estimated_minutes = _as_float(metrics.get("estimated_minutes"))
    average_answer_seconds = _as_float(metrics.get("average_answer_seconds"))
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
    due_tomorrow = _as_int(metrics.get("due_tomorrow"))

    quality = _quality_text(
        total_reviews,
        pass_rate,
        meta,
        pass_fail=_is_pass_fail_metrics(metrics),
    )
    tomorrow = _tomorrow_text(total_reviews, due_tomorrow)
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))

    return {
        "total_reviews": format_int(total_reviews),
        "new_cards": format_int(new_cards),
        "again_count": format_int(again_count),
        "fail_count": format_int(fail_count),
        "pass_count": format_int(pass_count),
        "estimated_minutes": format_duration_minutes(estimated_minutes),
        "real_study_time": _real_study_time_text(metrics),
        "average_answer_time": format_answer_seconds(average_answer_seconds),
        "pass_rate_percent": format_percent(pass_rate),
        "fail_rate_percent": format_percent(metrics.get("fail_rate")),
        "answer_mode": _answer_mode_label(metrics),
        "answer_mode_block": _answer_mode_text(metrics, meta),
        "due_tomorrow": format_int(due_tomorrow),
        "short_conclusion": _short_conclusion(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "summary": _summary(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "time_summary": _time_summary(metrics),
        "quality": quality,
        "tomorrow": tomorrow,
        "activity": _activity_text(metrics.get("heatmap")),
        "problem_decks": _problem_decks_text(
            problem_decks,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "problem_decks_markdown": _problem_decks_markdown(
            problem_decks,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "deck_breakdown": _deck_breakdown_text(metrics),
        "answer_distribution": _answer_distribution_text(metrics),
        "best_decks": _ranked_decks_text(
            _best_decks(metrics.get("deck_breakdown")),
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "hardest_decks": _ranked_decks_text(
            _hardest_decks(metrics.get("deck_breakdown")),
            hardest=True,
            pass_fail=_is_pass_fail_metrics(metrics),
        ),
        "top_decks": _top_decks_text(metrics),
        "forecast": _forecast_text(metrics.get("forecast")),
        "fsrs": _fsrs_text(metrics.get("fsrs")),
        "recommendations": _recommendations(
            total_reviews,
            pass_rate,
            due_tomorrow,
            _hardest_decks(metrics.get("deck_breakdown")),
            pass_fail=_is_pass_fail_metrics(metrics),
            markdown=False,
        ),
        "next_actions": _next_actions(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            problem_decks,
            meta,
            pass_fail=_is_pass_fail_metrics(metrics),
            markdown=False,
        ),
    }


def _plain_report(
    metrics: dict[str, Any],
    meta: dict[str, str],
    detail_level: str,
) -> str:
    context = _context(metrics, meta)
    lines = [
        "Режим ответов",
        context["answer_mode_block"],
        "",
        "Короткий вывод",
        context["short_conclusion"],
        "",
    ]

    if detail_level == "compact":
        lines.extend(
            [
                "Основные метрики",
                _main_metrics_text(context),
                "",
                "FSRS и нагрузка",
                context["fsrs"],
                "",
                "Прогноз",
                context["forecast"],
                "",
                "Активность",
                context["activity"],
                "",
                "Следующее действие",
                context["next_actions"],
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "Итоги",
            context["summary"],
            context["time_summary"],
            "",
            "Качество",
            context["quality"],
            "",
            "Активность",
            context["activity"],
            "",
            "Проблемные колоды",
            context["problem_decks"],
            "",
            _future_load_title(meta),
            context["tomorrow"],
            "",
            "FSRS и нагрузка",
            context["fsrs"],
            "",
            "Прогноз",
            context["forecast"],
            "",
            "Следующее действие",
            context["next_actions"],
        ]
    )

    if detail_level == "full":
        lines.extend(
            [
                "",
                "Топ колод",
                context["top_decks"],
                "",
                "Распределение ответов",
                context["answer_distribution"],
                "",
                "Таблица по колодам",
                context["deck_breakdown"],
                "",
                "Лучшие колоды",
                context["best_decks"],
                "",
                "Самые тяжёлые колоды",
                context["hardest_decks"],
                "",
                "Осторожные рекомендации",
                context["recommendations"],
                "",
                "Средние значения",
                _averages_text(metrics, meta),
                "",
                "Пояснение порогов",
                _thresholds_text(),
                "",
                "Технически",
                _technical_text(meta, metrics),
            ]
        )

    return "\n".join(lines)


def _markdown_header(meta: dict[str, str], metrics: dict[str, Any]) -> list[str]:
    scope = meta["scope"]
    if (
        meta["selected_decks"]
        and meta["selected_decks"] != "Не указаны"
        and meta["selected_decks"] != meta["scope"]
    ):
        scope = f"{scope}: {meta['selected_decks']}"
    return [
        "# Anki Study Report",
        "",
        f"**Период:** {meta['period']}  ",
        f"**Область:** {scope}  ",
        f"**Режим ответов:** {_answer_mode_label(metrics)}  ",
        f"**Создано:** {meta['created_at']}  ",
        "",
        "---",
        "",
    ]


def _main_metrics_table(
    context: dict[str, str],
    metrics: dict[str, Any] | None = None,
) -> str:
    rows = _main_metrics_rows(context, metrics)
    table = [
        "| Метрика | Значение | Оценка |",
        "|---|---:|---|",
    ]
    table.extend(
        (
            f"| {label} | **{_escape_markdown_table(value)}** | "
            f"{_main_metric_assessment(label, value, metrics)} |"
        )
        for label, value in rows
    )
    note = _real_study_time_note(metrics)
    if note:
        table.extend(["", f"> **Примечание:** {note}"])
    return "\n".join(table)


def _main_metrics_text(context: dict[str, str]) -> str:
    return "\n".join(
        f"{label}: {value}"
        for label, value in _main_metrics_rows(context, plain=True)
    )


def _main_metrics_rows(
    context: dict[str, str],
    metrics: dict[str, Any] | None = None,
    plain: bool = False,
) -> list[tuple[str, str]]:
    pass_fail = _is_pass_fail_metrics(metrics) if metrics is not None else (
        context.get("answer_mode") == "Pass/Fail"
    )
    pass_rate_key = "pass_rate_percent" if plain else "pass_rate"
    time_key = "estimated_minutes" if plain else "answer_time"
    if pass_fail:
        rows = [
            ("Ответов", context["total_reviews"]),
            ("Новых карточек", context["new_cards"]),
        ]
        rows.extend(
            [
                ("Fail", context["fail_count"]),
                ("Pass", context["pass_count"]),
                ("Pass rate", context[pass_rate_key]),
                ("Fail rate", context["fail_rate_percent"] if plain else context["fail_rate"]),
            ]
        )
    else:
        rows = [
            ("Повторений", context["total_reviews"]),
            ("Новых карточек", context["new_cards"]),
        ]
        rows.extend(
            [
                ("Again", context["again_count"]),
                ("Pass rate", context[pass_rate_key]),
            ]
        )
    rows.extend(
        [
            ("Чистое время ответов", context[time_key]),
            ("Реальное время занятий", context["real_study_time"]),
            ("Среднее время ответа", context["average_answer_time"]),
        ]
    )
    return rows


def _main_metric_assessment(
    label: str,
    value: str,
    metrics: dict[str, Any] | None = None,
) -> str:
    if value in {"нет данных", "недоступно"}:
        return "`NO DATA`"
    total_reviews = _as_int(metrics.get("total_reviews")) if isinstance(metrics, dict) else 0
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate")) if isinstance(metrics, dict) else 0
    fail_rate = _normalized_pass_rate(metrics.get("fail_rate")) if isinstance(metrics, dict) else 0
    average_answer_seconds = (
        _as_float(metrics.get("average_answer_seconds")) if isinstance(metrics, dict) else 0
    )

    if label in {"Ответов", "Повторений"}:
        if total_reviews <= 0:
            return "`NO DATA`"
        if total_reviews >= 1000:
            return "`OK` высокий объём"
        if total_reviews >= 100:
            return "`OK` нормально"
        return "`WARNING` мало данных"
    if label == "Pass rate":
        if pass_rate >= templates.PASS_RATE_GOOD:
            return "`OK` хорошо"
        if pass_rate >= templates.PASS_RATE_OK:
            return "`WARNING` нормально"
        return "`RISK` тревожно"
    if label == "Fail rate":
        if fail_rate <= 0.10:
            return "`OK` хорошо"
        if fail_rate <= 0.20:
            return "`WARNING` нормально"
        return "`RISK` высоковато"
    if label in {"Fail", "Again"}:
        return "`RISK` много ошибок" if pass_rate < templates.PASS_RATE_OK else "`OK` нормально"
    if label == "Новых карточек":
        return "`WARNING` умеренно" if pass_rate < templates.PASS_RATE_OK else "`OK` нормально"
    if label == "Среднее время ответа":
        if average_answer_seconds <= 0:
            return "`NO DATA`"
        if average_answer_seconds <= 10:
            return "`OK` нормально"
        if average_answer_seconds <= 20:
            return "`WARNING` медленно"
        return "`RISK` тяжело"
    if label == "Реальное время занятий":
        return "`NO DATA`" if value == "нет данных" else "`OK` есть данные"
    return "`OK` нормально"


def _real_study_time_note(metrics: dict[str, Any] | None) -> str:
    if not isinstance(metrics, dict):
        return ""
    real_time = metrics.get("real_study_time")
    if not isinstance(real_time, dict):
        return "реальное время занятий недоступно."
    if real_time.get("available"):
        return ""
    return str(real_time.get("message") or "реальное время занятий недоступно.")


def _summary(
    total_reviews: int,
    new_cards: int,
    again_count: int,
    pass_rate: float,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    if total_reviews <= 0:
        return f"{_capitalize(meta['period_human'])} повторений нет."

    fail_label = "Fail" if pass_fail else "Again"
    rate_label = "Pass rate" if pass_fail else "успешность"
    return (
        f"{_capitalize(meta['period_human'])}: {format_int(total_reviews)} повторений; "
        f"новые: {format_int(new_cards)}; "
        f"{fail_label}: {format_int(again_count)}; "
        f"{rate_label}: {format_percent(pass_rate)}."
    )


def _answer_time_text(total_seconds: int, estimated_minutes: float) -> str:
    return format_duration_minutes(
        total_seconds / 60 if total_seconds > 0 else estimated_minutes
    )


def _real_study_time_text(metrics: dict[str, Any]) -> str:
    real_time = metrics.get("real_study_time")
    if not isinstance(real_time, dict):
        return "нет данных"

    if not real_time.get("enabled", True):
        return "нет данных"

    if not real_time.get("available"):
        return "нет данных"

    total_seconds = _as_int(real_time.get("total_seconds"))
    value = format_duration_minutes(total_seconds / 60)
    scope = str(real_time.get("scope") or "").strip()
    source = str(real_time.get("source") or "").strip()
    notes = []
    if scope:
        notes.append(scope)
    if source:
        notes.append(source)
    if not notes:
        return value
    return f"{value} ({'; '.join(notes)})"


def _time_summary(metrics: dict[str, Any]) -> str:
    total_seconds = _as_int(metrics.get("total_seconds"))
    estimated_minutes = _as_float(metrics.get("estimated_minutes"))
    return "\n".join(
        [
            f"Чистое время ответов: {_answer_time_text(total_seconds, estimated_minutes)}.",
            f"Реальное время занятий: {_real_study_time_text(metrics)}.",
        ]
    )


def _quality_text(
    total_reviews: int,
    pass_rate: float,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    if total_reviews <= 0:
        return "Оценивать качество пока не по чему."
    if pass_rate >= templates.PASS_RATE_GOOD:
        if pass_fail:
            return f"Pass rate высокий: {format_percent(pass_rate)}."
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} прошёл чисто."
        return f"{_capitalize(meta['period_human'])} качество хорошее."
    if pass_rate >= templates.PASS_RATE_OK:
        if pass_fail:
            return f"Pass rate нормальный: {format_percent(pass_rate)}, но Fail стоит разобрать."
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} нормальный, но ошибки заметны."
        return f"{_capitalize(meta['period_human'])} качество нормальное, но ошибки заметны."
    if pass_fail:
        return f"Pass rate низкий: {format_percent(pass_rate)}. Лучше разобрать Fail и снизить новые."
    if _is_day_period(meta["period_id"]):
        return f"{_day_subject(meta['period_id'])} тяжёлый: лучше снизить новые."
    if meta["period_id"] == "all_time":
        return "Нужен разбор тем с частыми ошибками."
    return f"{_capitalize(meta['period_human'])} качество низкое."


def _tomorrow_text(total_reviews: int, due_tomorrow: int) -> str:
    if due_tomorrow <= 0:
        return "Повторений на завтра нет."
    if total_reviews <= 0:
        return f"{format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    if due_tomorrow >= total_reviews * templates.DUE_TOMORROW_LOAD_RATIO:
        return f"Высокая нагрузка: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    if due_tomorrow <= max(3, total_reviews * 0.10):
        return f"Почти пусто: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    return f"Умеренно: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."


def _activity_status(heatmap: Any) -> str:
    if not isinstance(heatmap, dict) or not heatmap.get("available"):
        return "neutral"
    total_days = _as_int(heatmap.get("total_days"))
    if total_days <= 0:
        return "neutral"
    active_rate = _as_int(heatmap.get("active_days")) / total_days
    if active_rate >= 0.85 and _as_int(heatmap.get("current_streak")) >= 3:
        return "good"
    if active_rate >= 0.60:
        return "warn"
    return "bad"


def _activity_text(heatmap: Any) -> str:
    if not isinstance(heatmap, dict) or not heatmap.get("available"):
        return "Активность за выбранный период пока не рассчитана."

    active_days = _as_int(heatmap.get("active_days"))
    total_days = _as_int(heatmap.get("total_days"))
    missed_days = _as_int(heatmap.get("missed_days"))
    current_streak = _as_int(heatmap.get("current_streak"))
    longest_streak = _as_int(heatmap.get("longest_streak"))
    best_days = _list_of_dicts(heatmap.get("best_days"))
    stability = str(heatmap.get("stability") or "")

    lines = [
        f"Активных дней: {format_int(active_days)} из {format_int(total_days)}.",
        f"Пропущенных дней: {format_int(missed_days)}.",
        (
            f"Текущая серия: {format_int(current_streak)} дней, "
            f"лучшая серия: {format_int(longest_streak)} дней."
        ),
    ]
    if best_days:
        best = best_days[0]
        lines.append(
            "Самый активный день: "
            f"{best.get('date')}, {format_int(best.get('reviews'))} повторений."
        )
    if stability:
        lines.append(f"Вывод: {stability}")

    weekday = _weekday_average_text(heatmap.get("weekday_average"))
    if weekday:
        lines.extend(["", weekday])
    if _activity_limited(heatmap):
        lines.append(
            "Календарь активности ограничен последними "
            f"{format_int(_activity_max_days(heatmap))} днями."
        )
    return "\n".join(lines)


def _activity_markdown(heatmap: Any, compact: bool = False) -> str:
    if not isinstance(heatmap, dict) or not heatmap.get("available"):
        return "Активность за выбранный период пока не рассчитана."

    rows = [
        (
            "Активных дней",
            f"{format_int(heatmap.get('active_days'))} из {format_int(heatmap.get('total_days'))}",
        ),
        ("Пропущенных дней", format_int(heatmap.get("missed_days"))),
        (
            "Текущая серия",
            _days_count_text(_as_int(heatmap.get("current_streak"))),
        ),
        (
            "Лучшая серия",
            _days_count_text(_as_int(heatmap.get("longest_streak"))),
        ),
    ]

    best_days = _list_of_dicts(heatmap.get("best_days"))
    if best_days:
        best = best_days[0]
        rows.append(
            (
                "Самый активный день",
                f"{best.get('date')}, {format_int(best.get('reviews'))} повторений",
            )
        )

    lines = ["| Метрика | Значение |", "|---|---:|"]
    lines.extend(f"| {label} | {value} |" for label, value in rows)

    stability = str(heatmap.get("stability") or "")
    if stability:
        lines.extend(["", f"> **Вывод:** {stability}"])
    if _activity_limited(heatmap):
        lines.extend(
            [
                "",
                (
                    "> **Примечание:** календарь ограничен последними "
                    f"{format_int(_activity_max_days(heatmap))} днями."
                ),
            ]
        )

    if compact:
        return "\n".join(lines)

    table = _weekday_average_markdown(heatmap.get("weekday_average"))
    if table:
        lines.extend(["", "### Средняя нагрузка по дням недели", "", table])
    return "\n".join(lines)


def _html_activity(heatmap: Any) -> str:
    if not isinstance(heatmap, dict) or not heatmap.get("available"):
        return '<p class="empty">Активность за выбранный период пока не рассчитана.</p>'

    rows = [
        ("Активных дней", f"{format_int(heatmap.get('active_days'))} из {format_int(heatmap.get('total_days'))}"),
        ("Пропущенных дней", format_int(heatmap.get("missed_days"))),
        ("Текущая серия", f"{format_int(heatmap.get('current_streak'))} дней"),
        ("Лучшая серия", f"{format_int(heatmap.get('longest_streak'))} дней"),
    ]
    best_days = _list_of_dicts(heatmap.get("best_days"))
    if best_days:
        best = best_days[0]
        rows.append(
            (
                "Самый активный день",
                f"{best.get('date')}, {format_int(best.get('reviews'))} повторений",
            )
        )

    parts = [_html_metrics_table(rows)]
    stability = str(heatmap.get("stability") or "")
    if stability:
        parts.append(_html_paragraph(stability))
    weekday_rows = _weekday_average_rows(heatmap.get("weekday_average"))[:7]
    if weekday_rows:
        parts.append(_html_metrics_table(weekday_rows))
    if _activity_limited(heatmap):
        parts.append(
            _html_paragraph(
                "Календарь активности ограничен последними "
                f"{format_int(_activity_max_days(heatmap))} днями."
            )
        )
    return "".join(parts)


def _weekday_average_text(value: Any) -> str:
    rows = _weekday_average_rows(value)
    if not rows:
        return ""
    return "Средняя нагрузка по дням недели:\n" + "\n".join(
        f"{label}: {reviews}" for label, reviews in rows
    )


def _weekday_average_markdown(value: Any) -> str:
    rows = _weekday_average_rows(value)
    if not rows:
        return ""
    return "\n".join(
        ["| День недели | Повторений в среднем |", "|---|---:|"]
        + [f"| {label} | {reviews} |" for label, reviews in rows]
    )


def _weekday_average_rows(value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, dict):
        return []
    labels = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    rows = []
    for key, label in labels.items():
        if key in value:
            rows.append((label, format_float(value.get(key))))
    return rows


def _activity_limited(heatmap: dict[str, Any]) -> bool:
    source = heatmap.get("source")
    return bool(isinstance(source, dict) and source.get("calendar_limited"))


def _activity_max_days(heatmap: dict[str, Any]) -> int:
    source = heatmap.get("source")
    if not isinstance(source, dict):
        return 366
    return _as_int(source.get("max_days")) or 366


def _forecast_status(forecast: Any) -> str:
    if not isinstance(forecast, dict) or not forecast.get("available"):
        return "neutral"
    risk = _forecast_recommendation(forecast).get("risk")
    if risk == "high":
        return "bad"
    if risk == "medium":
        return "warn"
    return "good"


def _forecast_text(forecast: Any) -> str:
    if not isinstance(forecast, dict) or not forecast.get("available"):
        return "Прогноз пока недоступен: не удалось прочитать планировщик Anki."

    rows = _forecast_summary_rows(forecast)
    lines = [f"{label}: {value}" for label, value in rows]
    recommendation = _forecast_recommendation(forecast)
    pattern = _forecast_pattern(forecast)
    if pattern.get("summary"):
        lines.extend(["", str(pattern["summary"])])
    if recommendation.get("summary"):
        lines.append(str(recommendation["summary"]))
    if recommendation.get("new_cards_advice"):
        lines.append(str(recommendation["new_cards_advice"]))
    if recommendation.get("explanation"):
        lines.append(str(recommendation["explanation"]))
    return "\n".join(lines)


def _forecast_markdown(forecast: Any, pass_fail: bool = False) -> str:
    if not isinstance(forecast, dict) or not forecast.get("available"):
        return "Прогноз пока недоступен: не удалось прочитать планировщик Anki."

    lines = ["| Период | Ожидается |", "|---|---:|"]
    lines.extend(
        f"| {_escape_markdown_table(label)} | {_escape_markdown_table(value)} |"
        for label, value in _forecast_decision_rows(forecast)
    )

    recommendation = _forecast_recommendation(forecast)
    pattern = _forecast_pattern(forecast)
    notes = [
        pattern.get("summary"),
        recommendation.get("summary"),
        recommendation.get("new_cards_advice"),
    ]
    interpretation = " ".join(
        _forecast_note_text(str(note), pass_fail=pass_fail)
        for note in notes
        if note
    )
    if interpretation:
        lines.extend(["", f"> **Интерпретация:** {interpretation}"])
    return "\n".join(lines)


def _forecast_note_text(text: str, pass_fail: bool = False) -> str:
    text = text.strip()
    if pass_fail:
        text = text.replace("Again", "Fail")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentence for sentence in sentences[:2] if sentence)


def _html_forecast(forecast: Any) -> str:
    if not isinstance(forecast, dict) or not forecast.get("available"):
        return '<p class="empty">Прогноз пока недоступен.</p>'

    parts = [_html_metrics_table(_forecast_summary_rows(forecast))]
    recommendation = _forecast_recommendation(forecast)
    pattern = _forecast_pattern(forecast)
    notes = [
        pattern.get("summary"),
        recommendation.get("summary"),
        recommendation.get("new_cards_advice"),
        recommendation.get("explanation"),
    ]
    note_text = "\n".join(str(note) for note in notes if note)
    if note_text:
        parts.append(_html_actions(note_text))

    daily_html = _forecast_daily_html(forecast)
    if daily_html:
        parts.append(daily_html)
    return "".join(parts)


def _forecast_summary_rows(forecast: dict[str, Any]) -> list[tuple[str, str]]:
    baseline = _forecast_baseline(forecast)
    due = _forecast_due(forecast)
    recommendation = _forecast_recommendation(forecast)
    return [
        ("Завтра", _cards_count_text(due.get("tomorrow"))),
        ("Review завтра", _cards_count_text(due.get("tomorrow_reviews"))),
        ("Learning/Relearning завтра", _cards_count_text(due.get("tomorrow_learning"))),
        ("Следующие 7 дней", _cards_count_text(due.get("next_7_days_total"))),
        ("Следующие 30 дней", _cards_count_text(due.get("next_30_days_total"))),
        (
            "Обычный активный день",
            _cards_count_text(baseline.get("median_reviews_active_day")),
        ),
        ("Новых в активный день", _cards_count_text(baseline.get("median_new_active_day"))),
        ("Активных дней", _activity_rate_text(baseline)),
        ("Again rate", format_percent(baseline.get("again_rate"))),
        ("Риск перегруза", str(recommendation.get("risk_label") or "нет данных")),
    ]


def _forecast_decision_rows(forecast: dict[str, Any]) -> list[tuple[str, str]]:
    baseline = _forecast_baseline(forecast)
    due = _forecast_due(forecast)
    return [
        ("Завтра", _cards_count_text(due.get("tomorrow"))),
        ("Следующие 7 дней", _cards_count_text(due.get("next_7_days_total"))),
        ("Следующие 30 дней", _cards_count_text(due.get("next_30_days_total"))),
        (
            "Обычный активный день",
            _cards_count_text(baseline.get("median_reviews_active_day")),
        ),
    ]


def _forecast_daily_html(forecast: dict[str, Any]) -> str:
    daily = _forecast_due(forecast).get("daily")
    if not isinstance(daily, list) or not daily:
        return ""

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Дата</th>"
            '<th class="value">Due</th>'
            '<th class="value">Review</th>'
            '<th class="value">Learning</th>'
            '<th class="value">Риск</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for item in daily[:7]:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{_html(item.get('date') or '')}</td>"
            f'<td class="value">{_html(format_int(item.get("due")))}</td>'
            f'<td class="value">{_html(format_int(item.get("review_due")))}</td>'
            f'<td class="value">{_html(format_int(item.get("learning_due")))}</td>'
            f'<td class="value">{_html(_forecast_risk_label(item.get("risk")))}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _activity_rate_text(baseline: dict[str, Any]) -> str:
    active_days = _as_int(baseline.get("active_days"))
    history_days = _as_int(baseline.get("history_days"))
    rate = format_percent(baseline.get("activity_rate"))
    if history_days <= 0:
        return rate
    return f"{format_int(active_days)} из {format_int(history_days)} ({rate})"


def _forecast_baseline(forecast: dict[str, Any]) -> dict[str, Any]:
    baseline = forecast.get("baseline")
    return baseline if isinstance(baseline, dict) else {}


def _forecast_due(forecast: dict[str, Any]) -> dict[str, Any]:
    due = forecast.get("due_forecast")
    return due if isinstance(due, dict) else {}


def _forecast_pattern(forecast: dict[str, Any]) -> dict[str, Any]:
    pattern = forecast.get("pattern")
    return pattern if isinstance(pattern, dict) else {}


def _forecast_recommendation(forecast: dict[str, Any]) -> dict[str, Any]:
    recommendation = forecast.get("recommendation")
    return recommendation if isinstance(recommendation, dict) else {}


def _forecast_risk_label(risk: Any) -> str:
    return {
        "low": "низкий",
        "medium": "средний",
        "high": "высокий",
        "unknown": "нет данных",
    }.get(str(risk or ""), "нет данных")


def _fsrs_status(fsrs: Any) -> str:
    if not isinstance(fsrs, dict):
        return "neutral"
    recommendation = fsrs.get("recommendation")
    status = recommendation.get("status") if isinstance(recommendation, dict) else ""
    if status == "overloaded":
        return "bad"
    if status == "warning":
        return "warn"
    if _as_int(_fsrs_memory(fsrs).get("cards_with_state")) > 0:
        return "good"
    return "neutral"


def _fsrs_text(fsrs: Any) -> str:
    if not isinstance(fsrs, dict):
        return "FSRS-метрики пока недоступны."

    rows = _fsrs_summary_rows(fsrs)
    lines = [f"{label}: {value}" for label, value in rows]
    top_decks = _fsrs_top_decks_text(fsrs)
    helper = _fsrs_helper_text(fsrs)
    recommendation = _fsrs_recommendation_text(fsrs)
    if top_decks:
        lines.extend(["", top_decks])
    if helper:
        lines.extend(["", helper])
    if recommendation:
        lines.extend(["", recommendation])
    return "\n".join(lines) if lines else "FSRS-метрики пока недоступны."


def _fsrs_markdown(fsrs: Any, metrics: dict[str, Any] | None = None) -> str:
    if not isinstance(fsrs, dict):
        return "FSRS-метрики пока недоступны."

    rows = _fsrs_human_rows(fsrs)
    if not rows:
        return "FSRS-метрики пока недоступны."

    lines = ["| Метрика | Значение | Что это значит |", "|---|---:|---|"]
    lines.extend(
        (
            f"| {_escape_markdown_table(label)} | {_escape_markdown_table(value)} | "
            f"{_escape_markdown_table(meaning)} |"
        )
        for label, value, meaning in rows
    )

    top_decks = _fsrs_top_decks_text(fsrs, markdown=True)
    helper = _fsrs_helper_text(fsrs)
    recommendation = _fsrs_recommendation_text(fsrs, metrics)
    for block in (top_decks, helper, recommendation):
        if block:
            lines.extend(["", block])
    return "\n".join(lines)


def _html_fsrs(fsrs: Any) -> str:
    if not isinstance(fsrs, dict):
        return '<p class="empty">FSRS-метрики пока недоступны.</p>'

    rows = _fsrs_summary_rows(fsrs)
    if not rows:
        return '<p class="empty">FSRS-метрики пока недоступны.</p>'

    parts = [_html_metrics_table(rows)]
    recommendation = _fsrs_recommendation_text(fsrs)
    if recommendation:
        parts.append(_html_paragraph(recommendation.replace("\n", " ")))
    top_decks = _fsrs_top_decks_html(fsrs)
    if top_decks:
        parts.append(top_decks)
    helper = _fsrs_helper_text(fsrs)
    if helper:
        parts.append(_html_paragraph(helper.replace("\n", " ")))
    return "".join(parts)


def _fsrs_summary_rows(fsrs: dict[str, Any]) -> list[tuple[str, str]]:
    memory = _fsrs_memory(fsrs)
    future = _fsrs_future(fsrs)
    settings = _fsrs_settings(fsrs)
    rows = [
        ("FSRS", "включён" if fsrs.get("enabled") else "выключен"),
        ("Desired retention", _fsrs_desired_retention_summary(settings)),
        ("Карточек с FSRS-состоянием", format_int(memory.get("cards_with_state"))),
        ("Средний predicted recall", format_percent(memory.get("average_recall"))),
        ("Recall ниже 90%", format_int(memory.get("below_90_count"))),
        ("Высокий риск забыть", format_int(memory.get("high_risk_count"))),
        ("Средняя сложность", _format_plain_percent(memory.get("average_difficulty"))),
        ("Завтра", _cards_count_text(future.get("tomorrow"))),
        ("Следующие 7 дней", _cards_count_text(future.get("next_7_days"))),
        ("Следующие 30 дней", _cards_count_text(future.get("next_30_days"))),
    ]
    return rows


def _fsrs_human_rows(fsrs: dict[str, Any]) -> list[tuple[str, str, str]]:
    memory = _fsrs_memory(fsrs)
    settings = _fsrs_settings(fsrs)
    return [
        (
            "FSRS",
            "включён" if fsrs.get("enabled") else "выключен",
            "используется новая модель расписания" if fsrs.get("enabled") else "модель не активна",
        ),
        (
            "Desired retention",
            _fsrs_desired_retention_summary(settings),
            "целевое удержание",
        ),
        (
            "Средний predicted recall",
            format_percent(memory.get("average_recall")),
            _fsrs_recall_meaning(memory.get("average_recall")),
        ),
        (
            "Recall ниже 90%",
            format_int(memory.get("below_90_count")),
            "карточки под риском",
        ),
        (
            "Высокий риск забыть",
            format_int(memory.get("high_risk_count")),
            "стоит разбирать постепенно",
        ),
    ]


def _fsrs_recall_meaning(value: Any) -> str:
    if value is None:
        return "нет данных"
    recall = _normalized_pass_rate(value)
    if recall >= 0.90:
        return "на уровне цели"
    if recall >= 0.80:
        return "немного ниже цели"
    return "ниже цели"


def _fsrs_memory(fsrs: dict[str, Any]) -> dict[str, Any]:
    memory = fsrs.get("memory_state")
    return memory if isinstance(memory, dict) else {}


def _fsrs_future(fsrs: dict[str, Any]) -> dict[str, Any]:
    future = fsrs.get("future_load")
    return future if isinstance(future, dict) else {}


def _fsrs_settings(fsrs: dict[str, Any]) -> list[dict[str, Any]]:
    settings = fsrs.get("deck_settings")
    return settings if isinstance(settings, list) else []


def _fsrs_desired_retention_summary(settings: list[dict[str, Any]]) -> str:
    values = sorted(
        {
            round(float(deck["desired_retention"]), 4)
            for deck in settings
            if isinstance(deck, dict) and deck.get("desired_retention") is not None
        }
    )
    if not values:
        return "нет данных"
    if len(values) == 1:
        return format_percent(values[0])
    return f"{format_percent(values[0])} - {format_percent(values[-1])}"


def _format_plain_percent(value: Any) -> str:
    if value is None:
        return "нет данных"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "нет данных"
    return f"{number:.1f}%"


def _cards_count_text(value: Any) -> str:
    count = _as_int(value)
    return f"{format_int(count)} {_card_word(count)}"


def _days_count_text(count: int) -> str:
    return f"{format_int(count)} {_day_word(count)}"


def _fsrs_top_decks_text(fsrs: dict[str, Any], markdown: bool = False) -> str:
    top_decks = _fsrs_future(fsrs).get("top_decks")
    if not isinstance(top_decks, list) or not top_decks:
        return ""
    lines = ["Основная будущая нагрузка:"]
    for deck in top_decks[:5]:
        if not isinstance(deck, dict):
            continue
        prefix = "- " if markdown else "- "
        lines.append(
            f"{prefix}{deck.get('deck_name') or 'Колода'}: "
            f"7 дней {format_int(deck.get('due_7'))}, "
            f"30 дней {format_int(deck.get('due_30'))}."
        )
    return "\n".join(lines)


def _fsrs_top_decks_html(fsrs: dict[str, Any]) -> str:
    top_decks = _fsrs_future(fsrs).get("top_decks")
    if not isinstance(top_decks, list) or not top_decks:
        return ""

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            '<th class="value">7 дней</th>'
            '<th class="value">30 дней</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in top_decks[:5]:
        if not isinstance(deck, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{_html(deck.get('deck_name') or 'Колода')}</td>"
            f'<td class="value">{_html(format_int(deck.get("due_7")))}</td>'
            f'<td class="value">{_html(format_int(deck.get("due_30")))}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _fsrs_helper_text(fsrs: dict[str, Any]) -> str:
    helper = fsrs.get("helper")
    if not isinstance(helper, dict):
        return ""
    config = helper.get("config")
    markers = helper.get("marked_cards")
    pieces = []
    if isinstance(config, dict) and config:
        enabled_flags = [
            key
            for key in (
                "auto_reschedule_after_sync",
                "auto_disperse_after_sync",
                "auto_disperse_when_review",
                "auto_disperse_after_reschedule",
                "display_memory_state",
            )
            if config.get(key)
        ]
        if enabled_flags:
            flags = ", ".join(f"`{flag}`" for flag in enabled_flags)
            pieces.append(f"**FSRS Helper:** {flags}")
    if isinstance(markers, dict) and markers:
        marker_text = ", ".join(
            f"{marker}: {format_int(count)}"
            for marker, count in sorted(markers.items())
        )
        pieces.append(f"Метки Helper на карточках: {marker_text}.")
    return "\n".join(pieces)


def _fsrs_recommendation_text(
    fsrs: dict[str, Any],
    metrics: dict[str, Any] | None = None,
) -> str:
    recommendation = fsrs.get("recommendation")
    if not isinstance(recommendation, dict):
        return ""
    tomorrow = recommendation.get("tomorrow_text")
    new_cards = recommendation.get("new_cards_text")
    if isinstance(metrics, dict):
        pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
        if pass_rate < templates.PASS_RATE_OK:
            new_cards = "Новые лучше ограничить, пока Pass rate не стабилизируется."
    lines = [line for line in (tomorrow, new_cards) if line]
    return "\n".join(str(line) for line in lines)


def _problem_decks(deck_breakdown: Any) -> list[dict[str, Any]]:
    if not isinstance(deck_breakdown, list):
        return []

    problem_decks: list[dict[str, Any]] = []
    for deck in deck_breakdown:
        if not isinstance(deck, dict):
            continue
        if _is_deleted_deck(deck):
            continue

        total_reviews = _as_int(deck.get("total_reviews"))
        pass_rate = _normalized_pass_rate(deck.get("pass_rate"))
        if (
            total_reviews >= templates.PROBLEM_DECK_MIN_REVIEWS
            and pass_rate < templates.PROBLEM_DECK_PASS_RATE
        ):
            problem_decks.append(
                {
                    "deck_name": str(deck.get("deck_name") or deck.get("deck_id") or "Без названия"),
                    "total_reviews": total_reviews,
                    "again_count": _as_int(deck.get("again_count")),
                    "fail_count": _as_int(deck.get("fail_count", deck.get("again_count"))),
                    "pass_count": _as_int(deck.get("pass_count"))
                    or max(0, total_reviews - _as_int(deck.get("fail_count", deck.get("again_count")))),
                    "pass_rate": pass_rate,
                    "comment": _problem_deck_comment(pass_rate),
                }
            )

    problem_decks = _deduplicate_similar_parent_child_decks(problem_decks)
    return sorted(problem_decks, key=lambda deck: (deck["pass_rate"], -deck["again_count"]))


def _problem_decks_text(
    problem_decks: list[dict[str, Any]],
    pass_fail: bool = False,
) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."

    lines = []
    for deck in problem_decks[:5]:
        if pass_fail:
            lines.append(
                "- "
                f"{deck['deck_name']}: Pass rate {format_percent(deck['pass_rate'])}, "
                f"Fail {format_int(deck['fail_count'])}/{format_int(deck['total_reviews'])}. "
                f"{_capitalize(deck['comment'])}."
            )
        else:
            lines.append(
                "- "
                f"{deck['deck_name']}: pass {format_percent(deck['pass_rate'])}, "
                f"Again {format_int(deck['again_count'])}/{format_int(deck['total_reviews'])}. "
                f"{_capitalize(deck['comment'])}."
            )
    return "\n".join(lines)


def _problem_decks_markdown(
    problem_decks: list[dict[str, Any]],
    pass_fail: bool = False,
) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."
    return _problem_decks_text(problem_decks, pass_fail=pass_fail)


def _problem_deck_comment(pass_rate: float) -> str:
    if pass_rate < 0.55:
        return "критическая зона"
    if pass_rate < 0.65:
        return "очень много ошибок"
    if pass_rate < 0.75:
        return "слабая зона"
    return "на грани"


def _deck_status(deck: dict[str, Any]) -> str:
    total_reviews = _as_int(deck.get("total_reviews"))
    if total_reviews <= 0:
        return "NO DATA"
    pass_rate = _normalized_pass_rate(deck.get("pass_rate"))
    fail_count = _as_int(deck.get("fail_count", deck.get("again_count")))
    fail_share = fail_count / total_reviews if total_reviews > 0 else 0
    if pass_rate < 0.55 or fail_share >= 0.35:
        return "CRITICAL"
    if pass_rate < templates.PROBLEM_DECK_PASS_RATE or fail_share >= 0.20:
        return "RISK"
    if pass_rate < templates.PASS_RATE_GOOD:
        return "WARNING"
    return "OK"


def _deduplicate_similar_parent_child_decks(
    problem_decks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sorted_decks = sorted(
        problem_decks,
        key=lambda deck: (
            deck["pass_rate"],
            -deck["again_count"],
            -_deck_depth(deck["deck_name"]),
        ),
    )
    kept: list[dict[str, Any]] = []
    for deck in sorted_decks:
        duplicate_index = _similar_parent_child_index(deck, kept)
        if duplicate_index is None:
            kept.append(deck)
            continue

        existing = kept[duplicate_index]
        if _prefer_problem_deck(deck, existing):
            kept[duplicate_index] = deck

    return kept


def _similar_parent_child_index(
    deck: dict[str, Any],
    kept: list[dict[str, Any]],
) -> int | None:
    for index, existing in enumerate(kept):
        if _is_parent_child_pair(deck["deck_name"], existing["deck_name"]):
            if _problem_stats_almost_same(deck, existing):
                return index
    return None


def _is_parent_child_pair(left: str, right: str) -> bool:
    return left.startswith(right + "::") or right.startswith(left + "::")


def _problem_stats_almost_same(left: dict[str, Any], right: dict[str, Any]) -> bool:
    pass_close = abs(left["pass_rate"] - right["pass_rate"]) <= 0.02
    again_close = _relative_close(left["again_count"], right["again_count"], 0.05)
    reviews_close = _relative_close(left["total_reviews"], right["total_reviews"], 0.05)
    return pass_close and again_close and reviews_close


def _relative_close(left: int, right: int, tolerance: float) -> bool:
    baseline = max(abs(left), abs(right), 1)
    return abs(left - right) / baseline <= tolerance


def _prefer_problem_deck(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    candidate_depth = _deck_depth(candidate["deck_name"])
    existing_depth = _deck_depth(existing["deck_name"])
    if candidate_depth != existing_depth:
        return candidate_depth > existing_depth
    if candidate["pass_rate"] != existing["pass_rate"]:
        return candidate["pass_rate"] < existing["pass_rate"]
    return candidate["again_count"] > existing["again_count"]


def _deck_depth(deck_name: str) -> int:
    return str(deck_name).count("::")


def _short_conclusion(
    total_reviews: int,
    new_cards: int,
    again_count: int,
    pass_rate: float,
    due_tomorrow: int,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    if total_reviews <= 0:
        return "За выбранный период повторений не было."

    sentences = [_short_quality_conclusion(pass_rate, meta, pass_fail=pass_fail)]
    load_sentence = _short_tomorrow_load_sentence(due_tomorrow, total_reviews)
    if load_sentence:
        sentences.append(load_sentence)
    if pass_rate < templates.PASS_RATE_OK and _is_long_period(meta["period_id"]):
        sentences.append(
            "Сначала разбор Fail, потом новые."
            if pass_fail
            else "Сначала разбор ошибок, потом новые."
        )
    return "\n".join(f"- {sentence}" for sentence in sentences[:3])


def _short_conclusion_markdown(
    metrics: dict[str, Any],
    meta: dict[str, str],
) -> str:
    total_reviews = _as_int(metrics.get("total_reviews"))
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
    due_tomorrow = _as_int(metrics.get("due_tomorrow"))
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))
    pass_fail = _is_pass_fail_metrics(metrics)
    if total_reviews <= 0:
        conclusion = "за выбранный период повторений не было."
    else:
        conclusion = _short_quality_conclusion(pass_rate, meta, pass_fail=pass_fail)
        conclusion = conclusion[:1].lower() + conclusion[1:]
        if problem_decks:
            conclusion += f" Главная проблема - {problem_decks[0]['deck_name']}."
    return "\n".join(
        [
            f"> **Короткий вывод:** {conclusion}",
            f"> **Риск:** {_report_risk_label(total_reviews, pass_rate, due_tomorrow, problem_decks)}",
            f"> **Главное действие:** {_main_action_sentence(total_reviews, pass_rate, due_tomorrow, problem_decks, pass_fail)}",
        ]
    )


def _report_risk_label(
    total_reviews: int,
    pass_rate: float,
    due_tomorrow: int,
    problem_decks: list[dict[str, Any]],
) -> str:
    if total_reviews <= 0:
        return "`NO DATA`"
    if pass_rate < 0.65 or len(problem_decks) >= 3:
        return "`CRITICAL`"
    if pass_rate < templates.PASS_RATE_OK or problem_decks:
        return "`RISK`"
    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        return "`WARNING`"
    return "`OK`"


def _main_action_sentence(
    total_reviews: int,
    pass_rate: float,
    due_tomorrow: int,
    problem_decks: list[dict[str, Any]],
    pass_fail: bool,
) -> str:
    if total_reviews <= 0:
        return "сначала сделать короткую сессию повторений."
    if problem_decks:
        names = _problem_deck_names(problem_decks, limit=2)
        return f"разобрать проблемные колоды: {names}."
    if pass_rate < templates.PASS_RATE_OK:
        return "разобрать Fail и временно снизить новые." if pass_fail else "разобрать ошибки и временно снизить новые."
    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        return "сначала закрыть завтрашнюю очередь."
    return "оставить текущий темп."


def _short_quality_conclusion(
    pass_rate: float,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    prefix = _period_context_prefix(meta)
    if pass_fail:
        if pass_rate >= templates.PASS_RATE_GOOD:
            return f"{prefix}Pass rate высокий. Fail мало."
        if pass_rate >= templates.PASS_RATE_OK:
            return f"{prefix}Pass rate нормальный, но Fail заметны."
        if meta["period_id"] == "all_time":
            return "За всё время Pass rate низкий."
        return f"{prefix}Pass rate низкий: лучше снизить новые и разобрать Fail."
    if pass_rate >= templates.PASS_RATE_GOOD:
        return f"{prefix}работа чистая. Ошибок мало."
    if pass_rate >= templates.PASS_RATE_OK:
        return f"{prefix}работа нормальная, но ошибки заметны."
    if meta["period_id"] == "all_time":
        return "За всё время качество низкое."
    return (
        f"{prefix}материал идёт тяжело: "
        "лучше снизить новые и разобрать ошибки."
    )


def _period_context_prefix(meta: dict[str, str]) -> str:
    if meta["period_id"] == "today":
        return "Сегодня "
    if meta["period_id"] == "yesterday":
        return "Вчера "
    if meta["period_id"] == "last_7_days":
        return "За неделю "
    if meta["period_id"] == "last_30_days":
        return "За месяц "
    if meta["period_id"] == "all_time":
        return "За всё время "
    if meta["period_id"] == "custom":
        return "За этот период "
    return f"{_capitalize(meta['period_human'])} "


def _short_tomorrow_load_sentence(due_tomorrow: int, total_reviews: int) -> str:
    if due_tomorrow <= 0:
        return "На завтра нет повторений."
    if total_reviews <= 0:
        return "На завтра есть нагрузка." if due_tomorrow >= 20 else ""
    if due_tomorrow <= max(3, total_reviews * 0.10):
        return "Текущая нагрузка на завтра почти пустая."
    if due_tomorrow >= total_reviews * templates.DUE_TOMORROW_LOAD_RATIO:
        return "Завтра ожидается высокая нагрузка."
    return ""


def _is_long_period(period_id: str) -> bool:
    return period_id in {"last_7_days", "last_30_days", "custom", "all_time"}


def _markdown_quality(
    total_reviews: int,
    again_count: int,
    pass_rate: float,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    if total_reviews <= 0:
        return "Оценивать качество пока не по чему."

    return _quality_sentence(
        total_reviews,
        again_count,
        pass_rate,
        meta,
        pass_fail=pass_fail,
    )


def _quality_sentence(
    total_reviews: int,
    again_count: int,
    pass_rate: float,
    meta: dict[str, str],
    pass_fail: bool = False,
) -> str:
    if total_reviews <= 0:
        return "Повторений нет."
    if pass_rate >= templates.PASS_RATE_GOOD:
        if pass_fail:
            return f"Pass rate высокий: {format_percent(pass_rate)}."
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} хороший: ошибок мало."
        return f"{_capitalize(meta['period_human'])} качество хорошее."
    if pass_rate >= templates.PASS_RATE_OK:
        if pass_fail:
            return f"Pass rate нормальный: {format_percent(pass_rate)}, но Fail стоит разобрать."
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} нормальный, но ошибки стоит разобрать."
        return f"{_capitalize(meta['period_human'])} качество нормальное, но ошибки заметны."
    if pass_fail:
        return f"Pass rate низкий: {format_percent(pass_rate)}. Лучше разобрать Fail и снизить новые."
    if _is_day_period(meta["period_id"]):
        return f"{_day_subject(meta['period_id'])} тяжёлый: новые лучше снизить."
    if meta["period_id"] == "all_time":
        return "Нужен разбор тем с частыми ошибками."
    return f"{_capitalize(meta['period_human'])} качество низкое."


def _problem_decks_table(
    problem_decks: list[dict[str, Any]],
    pass_fail: bool = False,
) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."

    fail_label = "Fail" if pass_fail else "Again"
    rows = [
        f"| Колода | Pass rate | {fail_label} | Повторений | Статус |",
        "|---|---:|---:|---:|---|",
    ]
    for deck in problem_decks[:5]:
        rows.append(
            "| "
            f"{_escape_markdown_table(str(deck['deck_name']))} | "
            f"{format_percent(deck['pass_rate'])} | "
            f"{format_int(deck['fail_count'] if pass_fail else deck['again_count'])} | "
            f"{format_int(deck['total_reviews'])} | "
            f"**{_deck_status(deck)}** |"
        )
    return "\n".join(rows)


def _attention_table(metrics: dict[str, Any], limit: int = 3) -> str:
    pass_fail = _is_pass_fail_metrics(metrics)
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))
    if not problem_decks:
        return "Явных проблемных колод за период не видно."

    fail_label = "Fail" if pass_fail else "Again"
    rows = [
        "| Приоритет | Колода | Почему |",
        "|---:|---|---|",
    ]
    for index, deck in enumerate(problem_decks[:limit], start=1):
        why = (
            f"Pass rate {format_percent(deck['pass_rate'])}, "
            f"{fail_label} {format_int(deck['fail_count'] if pass_fail else deck['again_count'])}"
        )
        rows.append(
            "| "
            f"{index} | "
            f"{_escape_markdown_table(str(deck['deck_name']))} | "
            f"{_escape_markdown_table(why)} |"
        )
    return "\n".join(rows)


def _deck_breakdown_table(
    deck_breakdown: Any,
    limit: int | None = None,
    include_deleted: bool = True,
) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    decks = _normalized_deck_breakdown(_deck_breakdown_value(deck_breakdown))
    if not include_deleted:
        decks = [deck for deck in decks if not deck["is_deleted"]]
    if not decks:
        return "По колодам за период нет данных."

    if pass_fail:
        rows = [
            "| Колода | Ответов | Новых | Fail | Pass | Pass rate | Fail rate | Статус | Время | Ср. ответ |",
            "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        ]
    else:
        rows = [
            "| Колода | Повторений | Новых | Again | Успешность | Статус | Время | Ср. ответ |",
            "|---|---:|---:|---:|---:|---|---:|---:|",
        ]
    visible_decks = decks if limit is None else decks[:limit]
    for deck in visible_decks:
        if pass_fail:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_int(deck['new_cards'])} | "
                f"{format_int(deck['fail_count'])} | "
                f"{format_int(deck['pass_count'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"{format_percent(deck['fail_rate'])} | "
                f"**{_deck_status(deck)}** | "
                f"{format_duration_minutes(deck['total_seconds'] / 60)} | "
                f"{format_answer_seconds(deck['average_answer_seconds'])} |"
            )
        else:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_int(deck['new_cards'])} | "
                f"{format_int(deck['again_count'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"**{_deck_status(deck)}** | "
                f"{format_duration_minutes(deck['total_seconds'] / 60)} | "
                f"{format_answer_seconds(deck['average_answer_seconds'])} |"
            )
    if limit is not None and len(decks) > limit:
        rows.extend(["", f"> Показаны первые {format_int(limit)} колод из {format_int(len(decks))}."])
    return "\n".join(rows)


def _deck_breakdown_text(deck_breakdown: Any) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    decks = _normalized_deck_breakdown(_deck_breakdown_value(deck_breakdown))
    if not decks:
        return "По колодам за период нет данных."

    lines = []
    for deck in decks:
        if pass_fail:
            lines.append(
                "- "
                f"{deck['deck_name']}: "
                f"{format_int(deck['total_reviews'])} ответов, "
                f"новых {format_int(deck['new_cards'])}, "
                f"Fail {format_int(deck['fail_count'])}, "
                f"Pass {format_int(deck['pass_count'])}, "
                f"Pass rate {format_percent(deck['pass_rate'])}, "
                f"Fail rate {format_percent(deck['fail_rate'])}, "
                f"время {format_duration_minutes(deck['total_seconds'] / 60)}, "
                f"ср. ответ {format_answer_seconds(deck['average_answer_seconds'])}."
            )
        else:
            lines.append(
                "- "
                f"{deck['deck_name']}: "
                f"{format_int(deck['total_reviews'])} повторений, "
                f"новых {format_int(deck['new_cards'])}, "
                f"Again {format_int(deck['again_count'])}, "
                f"успешность {format_percent(deck['pass_rate'])}, "
                f"время {format_duration_minutes(deck['total_seconds'] / 60)}, "
                f"ср. ответ {format_answer_seconds(deck['average_answer_seconds'])}."
            )
    return "\n".join(lines)


def _answer_distribution_table(metrics: dict[str, Any]) -> str:
    rows = ["| Ответ | Количество |", "|---|---:|"]
    rows.extend(
        f"| {label} | {format_int(value)} |"
        for label, value in _answer_distribution_rows(metrics)
    )
    return "\n".join(rows)


def _answer_distribution_text(metrics: dict[str, Any]) -> str:
    return "\n".join(
        f"{label}: {format_int(value)}"
        for label, value in _answer_distribution_rows(metrics)
    )


def _answer_distribution_rows(metrics: dict[str, Any]) -> list[tuple[str, int]]:
    distribution = metrics.get("answer_distribution")
    if not isinstance(distribution, dict):
        distribution = {}
    if _is_pass_fail_metrics(metrics):
        rows = [
            ("Fail", _fail_count(metrics)),
            ("Pass", _pass_count(metrics)),
        ]
        hard = _as_int(distribution.get("hard"))
        easy = _as_int(distribution.get("easy"))
        if hard or easy:
            rows.extend(
                [
                    ("Hard (технически)", hard),
                    ("Easy (технически)", easy),
                ]
            )
        return rows
    return [
        ("Again", _as_int(distribution.get("again"))),
        ("Hard", _as_int(distribution.get("hard"))),
        ("Good", _as_int(distribution.get("good"))),
        ("Easy", _as_int(distribution.get("easy"))),
    ]


def _best_decks(deck_breakdown: Any) -> list[dict[str, Any]]:
    decks = [
        deck
        for deck in _normalized_deck_breakdown(deck_breakdown)
        if not deck["is_deleted"]
        and deck["total_reviews"] >= templates.BEST_DECK_MIN_REVIEWS
        and deck["pass_rate"] >= templates.BEST_DECK_PASS_RATE
    ]
    return sorted(
        decks,
        key=lambda deck: (
            -deck["pass_rate"],
            -deck["total_reviews"],
            deck["deck_name"].lower(),
        ),
    )[:5]


def _hardest_decks(deck_breakdown: Any) -> list[dict[str, Any]]:
    decks = [
        deck
        for deck in _normalized_deck_breakdown(deck_breakdown)
        if not deck["is_deleted"]
        and deck["total_reviews"] >= templates.PROBLEM_DECK_MIN_REVIEWS
        and (
            deck["pass_rate"] < templates.PROBLEM_DECK_PASS_RATE
            or deck["again_count"] >= max(3, round(deck["total_reviews"] * 0.20))
        )
    ]
    return sorted(
        decks,
        key=lambda deck: (
            deck["pass_rate"],
            -deck["again_count"],
            -deck["total_reviews"],
            deck["deck_name"].lower(),
        ),
    )[:5]


def _ranked_decks_table(
    decks: list[dict[str, Any]],
    hardest: bool = False,
    pass_fail: bool = False,
) -> str:
    if not decks:
        if hardest:
            return "Явно тяжёлых колод за период не видно."
        return "Лучшие колоды пока не выделены: мало данных или нет подходящих колод."

    if pass_fail:
        rows = [
            "| Колода | Ответов | Pass rate | Fail | Pass | Ср. ответ |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    else:
        rows = [
            "| Колода | Повторений | Успешность | Again | Ср. ответ |",
            "|---|---:|---:|---:|---:|",
        ]
    for deck in decks:
        if pass_fail:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"{format_int(deck['fail_count'])} | "
                f"{format_int(deck['pass_count'])} | "
                f"{format_answer_seconds(deck['average_answer_seconds'])} |"
            )
        else:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"{format_int(deck['again_count'])} | "
                f"{format_answer_seconds(deck['average_answer_seconds'])} |"
            )
    return "\n".join(rows)


def _ranked_decks_text(
    decks: list[dict[str, Any]],
    hardest: bool = False,
    pass_fail: bool = False,
) -> str:
    if not decks:
        if hardest:
            return "Явно тяжёлых колод за период не видно."
        return "Лучшие колоды пока не выделены: мало данных или нет подходящих колод."

    lines = []
    for deck in decks:
        if pass_fail:
            lines.append(
                "- "
                f"{deck['deck_name']}: "
                f"Pass rate {format_percent(deck['pass_rate'])}, "
                f"{format_int(deck['total_reviews'])} ответов, "
                f"Fail {format_int(deck['fail_count'])}, "
                f"Pass {format_int(deck['pass_count'])}, "
                f"ср. ответ {format_answer_seconds(deck['average_answer_seconds'])}."
            )
        else:
            lines.append(
                "- "
                f"{deck['deck_name']}: "
                f"успешность {format_percent(deck['pass_rate'])}, "
                f"{format_int(deck['total_reviews'])} повторений, "
                f"Again {format_int(deck['again_count'])}, "
                f"ср. ответ {format_answer_seconds(deck['average_answer_seconds'])}."
            )
    return "\n".join(lines)


def _recommendations(
    total_reviews: int,
    pass_rate: float,
    due_tomorrow: int,
    hardest_decks: list[dict[str, Any]],
    pass_fail: bool = False,
    markdown: bool = True,
) -> str:
    recommendations: list[str] = []
    tomorrow_high = _tomorrow_load_is_high(due_tomorrow, total_reviews)
    tomorrow_low = _tomorrow_load_is_low(due_tomorrow, total_reviews)

    if tomorrow_high:
        recommendations.append(
            "Завтра ожидается высокая нагрузка, лучше не добавлять много новых карточек."
        )
    if total_reviews > 0 and pass_rate < templates.PASS_RATE_OK:
        if hardest_decks:
            recommendations.append(
                "Материал даётся тяжело, стоит повторить проблемные колоды."
            )
        else:
            recommendations.append(
                "Материал даётся тяжело, стоит осторожно разобрать Fail."
                if pass_fail
                else "Материал даётся тяжело, стоит осторожно разобрать ответы Again."
            )
    if (
        total_reviews > 0
        and pass_rate >= templates.PASS_RATE_GOOD
        and tomorrow_low
    ):
        recommendations.append("Можно добавить новые карточки.")

    if not recommendations:
        recommendations.append(
            "Отдельных сильных сигналов нет, текущий темп можно менять осторожно."
        )

    return _format_actions(_dedupe_actions(recommendations), markdown)


def _tomorrow_load_is_low(due_tomorrow: int, total_reviews: int) -> bool:
    if due_tomorrow <= 0:
        return True
    if total_reviews <= 0:
        return due_tomorrow < 20
    return due_tomorrow <= max(3, total_reviews * 0.10)


def _is_pass_fail_metrics(metrics: Any) -> bool:
    return isinstance(metrics, dict) and str(metrics.get("answer_mode")) == "pass_fail"


def _deck_breakdown_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("deck_breakdown")
    return value


def _fail_count(metrics: dict[str, Any]) -> int:
    if "fail_count" in metrics:
        return _as_int(metrics.get("fail_count"))
    return _as_int(metrics.get("again_count"))


def _pass_count(metrics: dict[str, Any]) -> int:
    if "pass_count" in metrics:
        return _as_int(metrics.get("pass_count"))
    return max(0, _as_int(metrics.get("total_reviews")) - _fail_count(metrics))


def _answer_mode_label(metrics: dict[str, Any]) -> str:
    if _is_pass_fail_metrics(metrics):
        return "Pass/Fail"
    return "Обычный Anki"


def _answer_mode_text(metrics: dict[str, Any], meta: dict[str, str]) -> str:
    lines = [f"Режим: {_answer_mode_label(metrics)}"]
    if _is_pass_fail_metrics(metrics):
        lines.extend(
            [
                f"Pass: {format_int(_pass_count(metrics))}",
                f"Fail: {format_int(_fail_count(metrics))}",
                f"Pass rate: {format_percent(metrics.get('pass_rate'))}",
                f"Fail rate: {format_percent(metrics.get('fail_rate'))}",
            ]
        )
    else:
        lines.extend(
            [
                f"Again: {format_int(metrics.get('again_count'))}",
                f"Pass rate: {format_percent(metrics.get('pass_rate'))}",
            ]
        )

    requested = str(metrics.get("requested_answer_mode") or meta.get("requested_answer_mode") or "")
    reason = str(metrics.get("answer_mode_reason") or "")
    if requested == "auto":
        lines.append(f"Автоопределение: {_answer_mode_reason_text(reason)}")
    return "\n".join(lines)


def _answer_mode_markdown(metrics: dict[str, Any], meta: dict[str, str]) -> str:
    return _format_actions(_answer_mode_text(metrics, meta).splitlines(), markdown=True)


def _answer_mode_reason_text(reason: str) -> str:
    if reason == "auto_hard_easy_under_threshold":
        return "Hard/Easy почти не используются, выбран Pass/Fail."
    if reason == "auto_hard_easy_present":
        return "Hard/Easy заметны в данных, выбран обычный режим Anki."
    if reason == "auto_insufficient_data":
        return "мало данных, безопасный откат к обычному режиму Anki."
    if reason == "configured":
        return "режим задан вручную."
    return "нет дополнительных данных."


def _normalize_answer_mode(value: Any) -> str:
    mode = str(value or "auto").strip().lower()
    if mode in {"auto", "standard", "pass_fail"}:
        return mode
    return "auto"


def _normalized_deck_breakdown(deck_breakdown: Any) -> list[dict[str, Any]]:
    if not isinstance(deck_breakdown, list):
        return []

    decks: list[dict[str, Any]] = []
    for deck in deck_breakdown:
        if not isinstance(deck, dict):
            continue
        total_reviews = _as_int(deck.get("total_reviews"))
        total_seconds = _as_int(deck.get("total_seconds"))
        average_answer_seconds = _as_float(deck.get("average_answer_seconds"))
        fail_count = _as_int(deck.get("fail_count", deck.get("again_count")))
        pass_count = _as_int(deck.get("pass_count"))
        if pass_count <= 0 and total_reviews > 0:
            pass_count = max(0, total_reviews - fail_count)
        if average_answer_seconds <= 0 and total_reviews > 0:
            average_answer_seconds = round(total_seconds / total_reviews, 1)
        decks.append(
            {
                "deck_id": deck.get("deck_id"),
                "deck_name": str(deck.get("deck_name") or deck.get("deck_id") or "Без названия"),
                "total_reviews": total_reviews,
                "new_cards": _as_int(deck.get("new_cards")),
                "again_count": _as_int(deck.get("again_count")),
                "fail_count": fail_count,
                "pass_count": pass_count,
                "pass_rate": _normalized_pass_rate(deck.get("pass_rate")),
                "fail_rate": _normalized_pass_rate(
                    deck.get(
                        "fail_rate",
                        fail_count / total_reviews if total_reviews > 0 else 0,
                    )
                ),
                "total_seconds": total_seconds,
                "average_answer_seconds": average_answer_seconds,
                "is_deleted": _is_deleted_deck(deck),
            }
        )

    return sorted(
        decks,
        key=lambda deck: (-deck["total_reviews"], deck["deck_name"].lower()),
    )


def _markdown_tomorrow(total_reviews: int, due_tomorrow: int) -> str:
    if due_tomorrow <= 0:
        return "Повторений на завтра нет."
    if total_reviews <= 0:
        return f"{format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    if due_tomorrow >= total_reviews * templates.DUE_TOMORROW_LOAD_RATIO:
        return f"Высокая нагрузка: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    if due_tomorrow <= max(3, total_reviews * 0.10):
        return f"Почти пусто: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."
    return f"Умеренно: {format_int(due_tomorrow)} {_card_word(due_tomorrow)}."


def _next_actions(
    total_reviews: int,
    new_cards: int,
    again_count: int,
    pass_rate: float,
    due_tomorrow: int,
    problem_decks: list[dict[str, Any]],
    meta: dict[str, str],
    pass_fail: bool = False,
    markdown: bool = True,
) -> str:
    actions: list[str] = []
    low_pass_rate = pass_rate < templates.PASS_RATE_OK

    if total_reviews <= 0:
        if _tomorrow_load_is_high(due_tomorrow, total_reviews):
            actions.append("Сначала закрыть завтрашнюю нагрузку.")
        else:
            actions.append("За период нет действий по отчёту.")
        return _format_actions(actions, markdown)

    if low_pass_rate:
        if problem_decks:
            worst_decks = _problem_deck_names(problem_decks, limit=2)
            actions.append(
                "Разобрать проблемные колоды"
                + (f": {worst_decks}." if worst_decks else ".")
            )
        else:
            actions.append("Разобрать Fail." if pass_fail else "Разобрать ответы Again.")

    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        actions.append("Сначала закрыть завтрашнюю нагрузку.")

    if new_cards > 0 and low_pass_rate:
        actions.append("Новые временно снизить.")
    elif low_pass_rate:
        actions.append("Не брать много новых.")

    if not actions:
        actions.append("Можно оставить текущий темп.")

    actions = _dedupe_actions(actions)
    if markdown:
        return "\n".join(f"- [ ] {action}" for action in actions)
    return _format_actions(actions, markdown)


def _tomorrow_load_is_high(due_tomorrow: int, total_reviews: int) -> bool:
    if due_tomorrow <= 0:
        return False
    if total_reviews <= 0:
        return due_tomorrow >= 20
    return due_tomorrow >= total_reviews * templates.DUE_TOMORROW_LOAD_RATIO


def _dedupe_actions(actions: list[str]) -> list[str]:
    seen = set()
    result = []
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        result.append(action)
    return result


def _format_actions(actions: list[str], markdown: bool) -> str:
    if markdown:
        return "\n".join(f"- {action}" for action in actions)
    return "\n".join(actions)


def _problem_deck_names(problem_decks: list[dict[str, Any]], limit: int = 2) -> str:
    names = [str(deck.get("deck_name") or "") for deck in problem_decks[:limit]]
    return " и ".join(name for name in names if name)


def _top_decks(deck_breakdown: Any) -> list[dict[str, Any]]:
    decks = [
        deck
        for deck in _normalized_deck_breakdown(_deck_breakdown_value(deck_breakdown))
        if deck["total_reviews"] > 0 and not deck["is_deleted"]
    ]

    return sorted(decks, key=lambda deck: (-deck["total_reviews"], deck["deck_name"].lower()))[:5]


def _deleted_reviews(deck_breakdown: Any) -> int:
    if not isinstance(deck_breakdown, list):
        return 0
    total = 0
    for deck in deck_breakdown:
        if isinstance(deck, dict) and _is_deleted_deck(deck):
            total += _as_int(deck.get("total_reviews"))
    return total


def _is_deleted_deck(deck: dict[str, Any]) -> bool:
    return deck.get("deck_id") is None or str(deck.get("deck_name") or "") == "Удалённые карточки"


def _top_decks_text(deck_breakdown: Any) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return "Топ колод за период не сформирован: нет повторений."

    lines = []
    for deck in top_decks:
        if pass_fail:
            lines.append(
                "- "
                f"{deck['deck_name']}: {format_int(deck['total_reviews'])} ответов, "
                f"Pass rate {format_percent(deck['pass_rate'])}, "
                f"Fail {format_int(deck['fail_count'])}, "
                f"Pass {format_int(deck['pass_count'])}, "
                f"время {format_duration_minutes(deck['total_seconds'] / 60)}."
            )
        else:
            lines.append(
                "- "
                f"{deck['deck_name']}: {format_int(deck['total_reviews'])} повторений, "
                f"pass {format_percent(deck['pass_rate'])}, "
                f"Again {format_int(deck['again_count'])}, "
                f"время {format_duration_minutes(deck['total_seconds'] / 60)}."
            )
    return "\n".join(lines)


def _top_decks_table(deck_breakdown: Any) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return "Топ колод за период не сформирован: нет повторений."

    if pass_fail:
        rows = [
            "| Колода | Ответов | Pass rate | Fail | Pass | Время |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    else:
        rows = [
            "| Колода | Повторений | Pass rate | Again | Время |",
            "|---|---:|---:|---:|---:|",
        ]
    for deck in top_decks:
        if pass_fail:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"{format_int(deck['fail_count'])} | "
                f"{format_int(deck['pass_count'])} | "
                f"{format_duration_minutes(deck['total_seconds'] / 60)} |"
            )
        else:
            rows.append(
                "| "
                f"{_escape_markdown_table(deck['deck_name'])} | "
                f"{format_int(deck['total_reviews'])} | "
                f"{format_percent(deck['pass_rate'])} | "
                f"{format_int(deck['again_count'])} | "
                f"{format_duration_minutes(deck['total_seconds'] / 60)} |"
            )
    return "\n".join(rows)


def _average_metric_rows(metrics: dict[str, Any], meta: dict[str, str]) -> list[tuple[str, str]]:
    days = _period_days(meta)
    if days <= 0:
        return [("Среднее", "нет данных")]

    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    estimated_minutes = _as_float(metrics.get("estimated_minutes"))
    total_seconds = _as_int(metrics.get("total_seconds"))
    average_answer_seconds = _as_float(metrics.get("average_answer_seconds"))
    minutes = total_seconds / 60 if total_seconds > 0 else estimated_minutes
    reviews_label = "Ответов в день" if _is_pass_fail_metrics(metrics) else "Повторений в день"
    return [
        (reviews_label, format_int(round(total_reviews / days))),
        ("Новых в день", format_int(round(new_cards / days))),
        ("Времени в день", format_duration_minutes(minutes / days)),
        ("Среднее время ответа", format_answer_seconds(average_answer_seconds)),
    ]


def _averages_text(metrics: dict[str, Any], meta: dict[str, str]) -> str:
    rows = _average_metric_rows(metrics, meta)
    if rows == [("Среднее", "нет данных")]:
        return "Средние значения для этого периода не рассчитаны."
    return "\n".join(f"{label}: {value}" for label, value in rows)


def _averages_markdown(metrics: dict[str, Any], meta: dict[str, str]) -> str:
    rows = _average_metric_rows(metrics, meta)
    if rows == [("Среднее", "нет данных")]:
        return "Средние значения для этого периода не рассчитаны."
    table = ["| Метрика | Значение |", "|---|---:|"]
    table.extend(f"| {label} | {value} |" for label, value in rows)
    return "\n".join(table)


def _period_days(meta: dict[str, str]) -> int:
    period_id = meta.get("period_id", "")
    if period_id in {"today", "yesterday"}:
        return 1
    if period_id == "last_7_days":
        return 7
    if period_id == "last_30_days":
        return 30
    if period_id == "all_time":
        return 365
    if period_id == "custom":
        return _custom_period_days(meta)
    return 0


def _custom_period_days(meta: dict[str, str]) -> int:
    period_text = f"{meta.get('period', '')} {meta.get('period_human', '')}"
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", period_text)
    if len(dates) < 2:
        return 0
    try:
        start = datetime.strptime(dates[0], "%Y-%m-%d").date()
        end = datetime.strptime(dates[1], "%Y-%m-%d").date()
    except ValueError:
        return 0
    return max((end - start).days, 1)


def _thresholds_text() -> str:
    return (
        "Pass rate >= 90%: чистая работа. 80-89%: нормально, но ошибки заметны. "
        "< 80%: лучше разобрать Fail/Again и не перегружать новые. "
        "Проблемные колоды: pass < 80% и минимум "
        f"{format_int(templates.PROBLEM_DECK_MIN_REVIEWS)} повторений. "
        "Высокая нагрузка на завтра: примерно от 125% текущего объёма."
    )


def _thresholds_markdown() -> str:
    return "\n".join(
        [
            "- Pass rate >= 90%: чистая работа.",
            "- Pass rate 80-89%: нормально, но ошибки заметны.",
            "- Pass rate < 80%: лучше разобрать Fail/Again и не перегружать новые.",
            (
                "- Проблемные колоды: pass < 80% и минимум "
                f"{format_int(templates.PROBLEM_DECK_MIN_REVIEWS)} повторений."
            ),
            "- Высокая нагрузка на завтра: примерно от 125% текущего объёма.",
        ]
    )


def _technical_text(meta: dict[str, str], metrics: dict[str, Any]) -> str:
    lines = [
        f"Период: {meta['period']}",
        f"Область: {meta['scope']}",
        f"Выбранные колоды: {meta['selected_decks']}",
        f"Дочерние колоды: {meta['include_child_decks']}",
        f"Детализация: {meta['detail_level']}",
        f"Режим ответов: {_answer_mode_label(metrics)}",
    ]
    deleted_reviews = _deleted_reviews(metrics.get("deck_breakdown"))
    if deleted_reviews:
        lines.append(
            f"{format_int(deleted_reviews)} повторений относятся к удалённым карточкам."
        )
    return "\n".join(lines)


def _technical_markdown(meta: dict[str, str], metrics: dict[str, Any]) -> str:
    rows = [
        ("Период", meta["period"]),
        ("Область", meta["scope"]),
        ("Выбранные колоды", meta["selected_decks"]),
        ("Дочерние колоды", meta["include_child_decks"]),
        ("Детализация", meta["detail_level"]),
        ("Режим ответов", _answer_mode_label(metrics)),
    ]
    deleted_reviews = _deleted_reviews(metrics.get("deck_breakdown"))
    if deleted_reviews:
        rows.append(("Удалённые карточки", f"{format_int(deleted_reviews)} повторений"))
    table = ["| Параметр | Значение |", "|---|---|"]
    table.extend(
        f"| {_escape_markdown_table(label)} | {_escape_markdown_table(value)} |"
        for label, value in rows
    )
    return "\n".join(table)


def _future_load_title(meta: dict[str, str]) -> str:
    return "Текущая нагрузка на завтра"


def _html_style() -> str:
    return """
<style>
body {
  margin: 0;
  padding: 0;
  background: #202124;
  color: #e8eaed;
  font-family: "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  line-height: 1.45;
}
.report {
  padding: 14px;
}
header {
  margin: 0 0 12px 0;
}
h1 {
  margin: 0 0 8px 0;
  color: #f1f3f4;
  font-size: 20px;
  font-weight: 650;
}
.meta {
  color: #aeb4bc;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.meta span {
  background: #2b2d31;
  border: 1px solid #383b40;
  border-radius: 6px;
  padding: 4px 7px;
}
.grid {
  display: grid;
  gap: 10px;
}
.card {
  background: #27292d;
  border: 1px solid #3a3d42;
  border-left: 4px solid #4b5563;
  border-radius: 8px;
  padding: 10px 12px;
}
.card.good { border-left-color: #3fa66b; }
.card.warn { border-left-color: #d5a93b; }
.card.bad { border-left-color: #b84a5a; }
.card.neutral { border-left-color: #64748b; }
h2 {
  margin: 0 0 7px 0;
  color: #f1f3f4;
  font-size: 15px;
  font-weight: 650;
}
p {
  margin: 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0;
}
th, td {
  border-bottom: 1px solid #3a3d42;
  padding: 6px 7px;
  vertical-align: top;
}
th {
  color: #cfd4dc;
  font-weight: 600;
  text-align: left;
  background: #2d3035;
}
td.value, th.value {
  text-align: right;
  white-space: nowrap;
}
tr:last-child td {
  border-bottom: none;
}
ul {
  margin: 0;
  padding-left: 18px;
}
li {
  margin: 3px 0;
}
.empty {
  color: #aeb4bc;
}
</style>
""".strip()


def _html_block(title: str, body: str, status: str) -> str:
    return (
        f'<section class="card {_html_class(status)}">'
        f"<h2>{_html(title)}</h2>"
        f"{body}"
        "</section>"
    )


def _html_metrics_table(rows: list[tuple[str, str]]) -> str:
    body = [
        "<table>",
        "<thead><tr><th>Метрика</th><th class=\"value\">Значение</th></tr></thead>",
        "<tbody>",
    ]
    for label, value in rows:
        body.append(
            "<tr>"
            f"<td>{_html(label)}</td>"
            f'<td class="value">{_html(value)}</td>'
            "</tr>"
        )
    body.extend(["</tbody>", "</table>"])
    return "".join(body)


def _html_problem_decks(problem_decks: list[dict[str, Any]]) -> str:
    if not problem_decks:
        return '<p class="empty">Явных проблемных колод за период не видно.</p>'

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            '<th class="value">Pass rate</th>'
            '<th class="value">Again</th>'
            '<th class="value">Повторений</th>'
            "<th>Комментарий</th>"
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in problem_decks[:5]:
        rows.append(
            "<tr>"
            f"<td>{_html(deck['deck_name'])}</td>"
            f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
            f'<td class="value">{_html(format_int(deck["again_count"]))}</td>'
            f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
            f"<td>{_html(_capitalize(deck['comment']))}.</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _html_top_decks(deck_breakdown: Any) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return '<p class="empty">Топ колод за период не сформирован: нет повторений.</p>'

    fail_heading = "Fail" if pass_fail else "Again"
    count_heading = "Ответов" if pass_fail else "Повторений"
    extra_heading = '<th class="value">Pass</th>' if pass_fail else ""
    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            f'<th class="value">{count_heading}</th>'
            '<th class="value">Pass rate</th>'
            f'<th class="value">{fail_heading}</th>'
            f"{extra_heading}"
            '<th class="value">Время</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in top_decks:
        pass_cell = (
            f'<td class="value">{_html(format_int(deck["pass_count"]))}</td>'
            if pass_fail
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{_html(deck['deck_name'])}</td>"
            f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
            f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
            f'<td class="value">{_html(format_int(deck["fail_count"] if pass_fail else deck["again_count"]))}</td>'
            f"{pass_cell}"
            f'<td class="value">{_html(format_duration_minutes(deck["total_seconds"] / 60))}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _html_deck_breakdown(deck_breakdown: Any) -> str:
    pass_fail = _is_pass_fail_metrics(deck_breakdown)
    decks = _normalized_deck_breakdown(_deck_breakdown_value(deck_breakdown))
    if not decks:
        return '<p class="empty">По колодам за период нет данных.</p>'

    if pass_fail:
        headings = (
            "<th>Колода</th>"
            '<th class="value">Ответов</th>'
            '<th class="value">Новых</th>'
            '<th class="value">Fail</th>'
            '<th class="value">Pass</th>'
            '<th class="value">Pass rate</th>'
            '<th class="value">Fail rate</th>'
            '<th class="value">Время</th>'
            '<th class="value">Ср. ответ</th>'
        )
    else:
        headings = (
            "<th>Колода</th>"
            '<th class="value">Повторений</th>'
            '<th class="value">Новых</th>'
            '<th class="value">Again</th>'
            '<th class="value">Успешность</th>'
            '<th class="value">Время</th>'
            '<th class="value">Ср. ответ</th>'
        )
    rows = [
        "<table>",
        f"<thead><tr>{headings}</tr></thead>",
        "<tbody>",
    ]
    for deck in decks:
        if pass_fail:
            rows.append(
                "<tr>"
                f"<td>{_html(deck['deck_name'])}</td>"
                f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
                f'<td class="value">{_html(format_int(deck["new_cards"]))}</td>'
                f'<td class="value">{_html(format_int(deck["fail_count"]))}</td>'
                f'<td class="value">{_html(format_int(deck["pass_count"]))}</td>'
                f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
                f'<td class="value">{_html(format_percent(deck["fail_rate"]))}</td>'
                f'<td class="value">{_html(format_duration_minutes(deck["total_seconds"] / 60))}</td>'
                f'<td class="value">{_html(format_answer_seconds(deck["average_answer_seconds"]))}</td>'
                "</tr>"
            )
        else:
            rows.append(
                "<tr>"
                f"<td>{_html(deck['deck_name'])}</td>"
                f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
                f'<td class="value">{_html(format_int(deck["new_cards"]))}</td>'
                f'<td class="value">{_html(format_int(deck["again_count"]))}</td>'
                f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
                f'<td class="value">{_html(format_duration_minutes(deck["total_seconds"] / 60))}</td>'
                f'<td class="value">{_html(format_answer_seconds(deck["average_answer_seconds"]))}</td>'
                "</tr>"
            )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _html_ranked_decks(
    decks: list[dict[str, Any]],
    hardest: bool = False,
    pass_fail: bool = False,
) -> str:
    if not decks:
        if hardest:
            return '<p class="empty">Явно тяжёлых колод за период не видно.</p>'
        return '<p class="empty">Лучшие колоды пока не выделены: мало данных.</p>'

    fail_heading = "Fail" if pass_fail else "Again"
    count_heading = "Ответов" if pass_fail else "Повторений"
    rate_heading = "Pass rate" if pass_fail else "Успешность"
    pass_heading = '<th class="value">Pass</th>' if pass_fail else ""
    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            f'<th class="value">{count_heading}</th>'
            f'<th class="value">{rate_heading}</th>'
            f'<th class="value">{fail_heading}</th>'
            f"{pass_heading}"
            '<th class="value">Ср. ответ</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in decks:
        pass_cell = (
            f'<td class="value">{_html(format_int(deck["pass_count"]))}</td>'
            if pass_fail
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{_html(deck['deck_name'])}</td>"
            f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
            f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
            f'<td class="value">{_html(format_int(deck["fail_count"] if pass_fail else deck["again_count"]))}</td>'
            f"{pass_cell}"
            f'<td class="value">{_html(format_answer_seconds(deck["average_answer_seconds"]))}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _html_actions(text: str) -> str:
    actions = [line.strip("- ").strip() for line in str(text).splitlines() if line.strip()]
    if not actions:
        return '<p class="empty">Нет отдельного действия.</p>'
    return "<ul>" + "".join(f"<li>{_html(action)}</li>" for action in actions) + "</ul>"


def _html_paragraph(text: str) -> str:
    if "\n" in str(text):
        return _html_actions(text)
    return f"<p>{_html(text)}</p>"


def _quality_status(total_reviews: int, pass_rate: float) -> str:
    if total_reviews <= 0:
        return "neutral"
    if pass_rate >= templates.PASS_RATE_GOOD:
        return "good"
    if pass_rate >= templates.PASS_RATE_OK:
        return "warn"
    return "bad"


def _tomorrow_status(total_reviews: int, due_tomorrow: int) -> str:
    if due_tomorrow <= 0:
        return "good"
    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        return "warn"
    return "neutral"


def _next_action_status(total_reviews: int, pass_rate: float, due_tomorrow: int) -> str:
    if total_reviews <= 0:
        return "neutral"
    if pass_rate < templates.PASS_RATE_OK:
        return "bad"
    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        return "warn"
    return "good"


def _html(value: Any) -> str:
    return escape(str(value), quote=True)


def _html_class(value: str) -> str:
    return value if value in {"good", "warn", "bad", "neutral"} else "neutral"


def _new_cards_sentence(
    pass_rate: float,
    due_tomorrow: int,
    total_reviews: int,
    meta: dict[str, str],
) -> str:
    if _should_limit_new_cards(pass_rate, due_tomorrow, total_reviews, meta["period_id"]):
        return "Новые карточки лучше брать осторожно или отложить."
    return "Новые карточки можно брать умеренно, если очередь на завтра остаётся комфортной."


def _should_limit_new_cards(
    pass_rate: float,
    due_tomorrow: int,
    total_reviews: int,
    period_id: str,
) -> bool:
    if pass_rate < templates.PASS_RATE_OK:
        return True
    if total_reviews <= 0:
        return due_tomorrow > 0
    return due_tomorrow >= total_reviews * templates.DUE_TOMORROW_LOAD_RATIO


def _is_day_period(period_id: str) -> bool:
    return period_id in {"today", "yesterday"}


def _day_subject(period_id: str) -> str:
    if period_id == "yesterday":
        return "Вчера день"
    return "Сегодня день"


def _capitalize(value: str) -> str:
    if not value:
        return value
    return value[:1].upper() + value[1:]


def _created_at() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _card_word(count: int) -> str:
    count = abs(int(count))
    if count % 100 in {11, 12, 13, 14}:
        return "карточек"
    if count % 10 == 1:
        return "карточка"
    if count % 10 in {2, 3, 4}:
        return "карточки"
    return "карточек"


def _day_word(count: int) -> str:
    count = abs(int(count))
    if count % 100 in {11, 12, 13, 14}:
        return "дней"
    if count % 10 == 1:
        return "день"
    if count % 10 in {2, 3, 4}:
        return "дня"
    return "дней"


def _normalize_detail_level(value: Any) -> str:
    detail_level = str(value or "normal")
    if detail_level in {"compact", "normal", "full"}:
        return detail_level
    return "normal"


def format_int(value: Any, no_data: str = "нет данных") -> str:
    if value is None:
        return no_data
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return no_data


def format_float(value: Any, no_data: str = "нет данных") -> str:
    if value is None:
        return no_data
    try:
        number = float(value)
    except (TypeError, ValueError):
        return no_data
    if number.is_integer():
        return format_int(number)
    return f"{number:.1f}".replace(".", ",")


def format_percent(value: Any, no_data: str = "нет данных") -> str:
    if value is None:
        return no_data
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return no_data

    if rate > 1:
        rate = rate / 100
    if rate < 0:
        rate = 0.0
    if rate > 1:
        rate = 1.0
    return f"{round(rate * 100)}%"


def format_duration_minutes(value: Any, no_data: str = "нет данных") -> str:
    if value is None:
        return no_data
    try:
        total_minutes = round(float(value))
    except (TypeError, ValueError):
        return no_data

    if total_minutes <= 0:
        return "0 мин"

    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} ч {minutes} мин"
    if hours:
        return f"{hours} ч"
    return f"{minutes} мин"


def format_answer_seconds(value: Any, no_data: str = "нет данных") -> str:
    if value is None:
        return no_data
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return no_data

    if seconds <= 0:
        return "0 сек"
    if seconds >= 60:
        return format_duration_minutes(seconds / 60)
    if seconds.is_integer():
        return f"{int(seconds)} сек"
    return f"{seconds:.1f} сек"


def _format_duration(total_seconds: int) -> str:
    return format_duration_minutes(total_seconds / 60)


def _escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _normalized_pass_rate(value: Any) -> float:
    rate = _as_float(value)
    if rate > 1:
        rate = rate / 100
    if rate < 0:
        return 0.0
    if rate > 1:
        return 1.0
    return rate


def _yes_no(value: Any) -> str:
    return "да" if bool(value) else "нет"


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _format_percent(value: float) -> str:
    formatted = format_percent(value)
    return formatted[:-1] if formatted.endswith("%") else formatted


def _format_minutes(value: float) -> str:
    return format_duration_minutes(value)


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
