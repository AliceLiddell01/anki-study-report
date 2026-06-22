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


def build_short_report(
    metrics: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> str:
    return build_report(metrics, "short", metadata)


def build_detailed_report(
    metrics: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> str:
    return build_report(metrics, "detailed", metadata)


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

    blocks = [
        _html_block(
            "Короткий вывод",
            _html_paragraph(markdown_context["short_conclusion"]),
            quality_status,
        ),
        _html_block(
            "Итоги",
            _html_metrics_table(
                [
                    ("Повторений", markdown_context["total_reviews"]),
                    ("Новых карточек", markdown_context["new_cards"]),
                    ("Again", markdown_context["again_count"]),
                    ("Pass rate", markdown_context["pass_rate"]),
                    ("Чистое время ответов", markdown_context["answer_time"]),
                    ("Реальное время занятий", markdown_context["real_study_time"]),
                    ("Среднее время ответа", markdown_context["average_answer_time"]),
                ]
            ),
            quality_status,
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
            _html_deck_breakdown(metrics.get("deck_breakdown")),
            "neutral",
        ),
        _html_block(
            "Лучшие колоды",
            _html_ranked_decks(best_decks),
            "good" if best_decks else "neutral",
        ),
        _html_block(
            "Самые тяжёлые колоды",
            _html_ranked_decks(hardest_decks, hardest=True),
            problem_status,
        ),
        _html_block(
            _future_load_title(meta),
            _html_paragraph(markdown_context["tomorrow"]),
            tomorrow_status,
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
                    _html_top_decks(metrics.get("deck_breakdown")),
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
    lines = _markdown_header(meta)
    lines.extend(
        [
            "### Короткий вывод",
            context["short_conclusion"],
            "",
        ]
    )

    if meta["detail_level"] == "compact":
        lines.extend(
            [
                "### Основные метрики",
                _main_metrics_table(context),
                "",
                "### Распределение ответов",
                context["answer_distribution_table"],
                "",
                "### Следующее действие",
                context["next_actions"],
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "### Итоги",
            _main_metrics_table(context),
            "",
            "### Качество",
            context["quality"],
            "",
            "### Распределение ответов",
            context["answer_distribution_table"],
            "",
            "### Таблица по колодам",
            context["deck_breakdown_table"],
            "",
            "### Лучшие колоды",
            context["best_decks_table"],
            "",
            "### Самые тяжёлые колоды",
            context["hardest_decks_table"],
            "",
            f"### {_future_load_title(meta)}",
            context["tomorrow"],
            "",
            "### Осторожные рекомендации",
            context["recommendations"],
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
                "### Распределение ответов",
                context["answer_distribution_table"],
                "",
                "### Таблица по колодам",
                context["deck_breakdown_table"],
                "",
                "### Лучшие колоды",
                context["best_decks_table"],
                "",
                "### Самые тяжёлые колоды",
                context["hardest_decks_table"],
                "",
                "### Осторожные рекомендации",
                context["recommendations"],
                "",
                "### Средние значения",
                _averages_markdown(metrics, meta),
                "",
                "### Пояснение порогов",
                _thresholds_markdown(),
                "",
                "### Технически",
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
    }


def _markdown_context(metrics: dict[str, Any], meta: dict[str, str]) -> dict[str, str]:
    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    again_count = _as_int(metrics.get("again_count"))
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
        "pass_rate": format_percent(pass_rate),
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
        ),
        "quality": _markdown_quality(total_reviews, again_count, pass_rate, meta),
        "problem_decks_table": _problem_decks_table(problem_decks),
        "deck_breakdown_table": _deck_breakdown_table(metrics.get("deck_breakdown")),
        "answer_distribution_table": _answer_distribution_table(metrics),
        "best_decks_table": _ranked_decks_table(_best_decks(metrics.get("deck_breakdown"))),
        "hardest_decks_table": _ranked_decks_table(hardest_decks, hardest=True),
        "tomorrow": _markdown_tomorrow(total_reviews, due_tomorrow),
        "top_decks_table": _top_decks_table(metrics.get("deck_breakdown")),
        "recommendations": _recommendations(
            total_reviews,
            pass_rate,
            due_tomorrow,
            hardest_decks,
        ),
        "next_actions": _next_actions(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            problem_decks,
            meta,
        ),
    }


def _context(metrics: dict[str, Any], meta: dict[str, str]) -> dict[str, Any]:
    total_reviews = _as_int(metrics.get("total_reviews"))
    new_cards = _as_int(metrics.get("new_cards"))
    again_count = _as_int(metrics.get("again_count"))
    estimated_minutes = _as_float(metrics.get("estimated_minutes"))
    average_answer_seconds = _as_float(metrics.get("average_answer_seconds"))
    pass_rate = _normalized_pass_rate(metrics.get("pass_rate"))
    due_tomorrow = _as_int(metrics.get("due_tomorrow"))

    quality = _quality_text(total_reviews, pass_rate, meta)
    tomorrow = _tomorrow_text(total_reviews, due_tomorrow)
    problem_decks = _problem_decks(metrics.get("deck_breakdown"))

    return {
        "total_reviews": format_int(total_reviews),
        "new_cards": format_int(new_cards),
        "again_count": format_int(again_count),
        "estimated_minutes": format_duration_minutes(estimated_minutes),
        "real_study_time": _real_study_time_text(metrics),
        "average_answer_time": format_answer_seconds(average_answer_seconds),
        "pass_rate_percent": format_percent(pass_rate),
        "due_tomorrow": format_int(due_tomorrow),
        "short_conclusion": _short_conclusion(
            total_reviews,
            new_cards,
            again_count,
            pass_rate,
            due_tomorrow,
            meta,
        ),
        "summary": _summary(total_reviews, new_cards, again_count, pass_rate, meta),
        "time_summary": _time_summary(metrics),
        "quality": quality,
        "tomorrow": tomorrow,
        "problem_decks": _problem_decks_text(problem_decks),
        "problem_decks_markdown": _problem_decks_markdown(problem_decks),
        "deck_breakdown": _deck_breakdown_text(metrics.get("deck_breakdown")),
        "answer_distribution": _answer_distribution_text(metrics),
        "best_decks": _ranked_decks_text(_best_decks(metrics.get("deck_breakdown"))),
        "hardest_decks": _ranked_decks_text(
            _hardest_decks(metrics.get("deck_breakdown")),
            hardest=True,
        ),
        "top_decks": _top_decks_text(metrics.get("deck_breakdown")),
        "recommendations": _recommendations(
            total_reviews,
            pass_rate,
            due_tomorrow,
            _hardest_decks(metrics.get("deck_breakdown")),
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
            "Проблемные колоды",
            context["problem_decks"],
            "",
                _future_load_title(meta),
                context["tomorrow"],
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


def _markdown_header(meta: dict[str, str]) -> list[str]:
    return [
        "# Anki Study Report",
        "",
        f"**Период:** {meta['period']}",
        f"**Область:** {meta['scope']}",
        f"**Выбранные колоды:** {meta['selected_decks']}",
        f"**Дочерние колоды:** {meta['include_child_decks']}",
        f"**Создано:** {meta['created_at']}",
        "",
    ]


def _main_metrics_table(context: dict[str, str]) -> str:
    return "\n".join(
        [
            "| Метрика | Значение |",
            "|---|---:|",
            f"| Повторений | {context['total_reviews']} |",
            f"| Новых карточек | {context['new_cards']} |",
            f"| Again | {context['again_count']} |",
            f"| Pass rate | {context['pass_rate']} |",
            f"| Чистое время ответов | {context['answer_time']} |",
            f"| Реальное время занятий | {context['real_study_time']} |",
            f"| Среднее время ответа | {context['average_answer_time']} |",
        ]
    )


def _main_metrics_text(context: dict[str, str]) -> str:
    return "\n".join(
        [
            f"Повторений: {context['total_reviews']}",
            f"Новых карточек: {context['new_cards']}",
            f"Again: {context['again_count']}",
            f"Pass rate: {context['pass_rate_percent']}",
            f"Чистое время ответов: {context['estimated_minutes']}",
            f"Реальное время занятий: {context['real_study_time']}",
            f"Среднее время ответа: {context['average_answer_time']}",
        ]
    )


def _summary(
    total_reviews: int,
    new_cards: int,
    again_count: int,
    pass_rate: float,
    meta: dict[str, str],
) -> str:
    if total_reviews <= 0:
        return f"{_capitalize(meta['period_human'])} повторений нет."

    return (
        f"{_capitalize(meta['period_human'])}: {format_int(total_reviews)} повторений; "
        f"новые: {format_int(new_cards)}; "
        f"Again: {format_int(again_count)}; "
        f"успешность: {format_percent(pass_rate)}."
    )


def _answer_time_text(total_seconds: int, estimated_minutes: float) -> str:
    return format_duration_minutes(
        total_seconds / 60 if total_seconds > 0 else estimated_minutes
    )


def _real_study_time_text(metrics: dict[str, Any]) -> str:
    real_time = metrics.get("real_study_time")
    if not isinstance(real_time, dict):
        return "недоступно"

    if not real_time.get("enabled", True):
        return str(real_time.get("message") or "отключено в настройках")

    if not real_time.get("available"):
        return str(real_time.get("message") or "недоступно")

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


def _quality_text(total_reviews: int, pass_rate: float, meta: dict[str, str]) -> str:
    if total_reviews <= 0:
        return "Оценивать качество пока не по чему."
    if pass_rate >= templates.PASS_RATE_GOOD:
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} прошёл чисто."
        return f"{_capitalize(meta['period_human'])} качество хорошее."
    if pass_rate >= templates.PASS_RATE_OK:
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} нормальный, но ошибки заметны."
        return f"{_capitalize(meta['period_human'])} качество нормальное, но ошибки заметны."
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


def _problem_decks(deck_breakdown: Any) -> list[dict[str, Any]]:
    if not isinstance(deck_breakdown, list):
        return []

    problem_decks: list[dict[str, Any]] = []
    for deck in deck_breakdown:
        if not isinstance(deck, dict):
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
                    "pass_rate": pass_rate,
                    "comment": _problem_deck_comment(pass_rate),
                }
            )

    problem_decks = _deduplicate_similar_parent_child_decks(problem_decks)
    return sorted(problem_decks, key=lambda deck: (deck["pass_rate"], -deck["again_count"]))


def _problem_decks_text(problem_decks: list[dict[str, Any]]) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."

    lines = []
    for deck in problem_decks[:5]:
        lines.append(
            "- "
            f"{deck['deck_name']}: pass {format_percent(deck['pass_rate'])}, "
            f"Again {format_int(deck['again_count'])}/{format_int(deck['total_reviews'])}. "
            f"{_capitalize(deck['comment'])}."
        )
    return "\n".join(lines)


def _problem_decks_markdown(problem_decks: list[dict[str, Any]]) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."
    return _problem_decks_text(problem_decks)


def _problem_deck_comment(pass_rate: float) -> str:
    if pass_rate < 0.55:
        return "критическая зона"
    if pass_rate < 0.65:
        return "очень много ошибок"
    if pass_rate < 0.75:
        return "слабая зона"
    return "на грани"


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
) -> str:
    if total_reviews <= 0:
        return "За выбранный период повторений не было."

    sentences = [_short_quality_conclusion(pass_rate, meta)]
    load_sentence = _short_tomorrow_load_sentence(due_tomorrow, total_reviews)
    if load_sentence:
        sentences.append(load_sentence)
    if pass_rate < templates.PASS_RATE_OK and _is_long_period(meta["period_id"]):
        sentences.append("Сначала разбор ошибок, потом новые.")
    return "\n".join(f"- {sentence}" for sentence in sentences[:3])


def _short_quality_conclusion(pass_rate: float, meta: dict[str, str]) -> str:
    prefix = _period_context_prefix(meta)
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
) -> str:
    if total_reviews <= 0:
        return "Оценивать качество пока не по чему."

    return _quality_sentence(total_reviews, again_count, pass_rate, meta)


def _quality_sentence(
    total_reviews: int,
    again_count: int,
    pass_rate: float,
    meta: dict[str, str],
) -> str:
    if total_reviews <= 0:
        return "Повторений нет."
    if pass_rate >= templates.PASS_RATE_GOOD:
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} хороший: ошибок мало."
        return f"{_capitalize(meta['period_human'])} качество хорошее."
    if pass_rate >= templates.PASS_RATE_OK:
        if _is_day_period(meta["period_id"]):
            return f"{_day_subject(meta['period_id'])} нормальный, но ошибки стоит разобрать."
        return f"{_capitalize(meta['period_human'])} качество нормальное, но ошибки заметны."
    if _is_day_period(meta["period_id"]):
        return f"{_day_subject(meta['period_id'])} тяжёлый: новые лучше снизить."
    if meta["period_id"] == "all_time":
        return "Нужен разбор тем с частыми ошибками."
    return f"{_capitalize(meta['period_human'])} качество низкое."


def _problem_decks_table(problem_decks: list[dict[str, Any]]) -> str:
    if not problem_decks:
        return "Явных проблемных колод за период не видно."

    rows = [
        "| Колода | Pass rate | Again | Повторений | Комментарий |",
        "|---|---:|---:|---:|---|",
    ]
    for deck in problem_decks[:5]:
        rows.append(
            "| "
            f"{_escape_markdown_table(str(deck['deck_name']))} | "
            f"{format_percent(deck['pass_rate'])} | "
            f"{format_int(deck['again_count'])} | "
            f"{format_int(deck['total_reviews'])} | "
            f"{_capitalize(deck['comment'])}. |"
        )
    return "\n".join(rows)


def _deck_breakdown_table(deck_breakdown: Any) -> str:
    decks = _normalized_deck_breakdown(deck_breakdown)
    if not decks:
        return "По колодам за период нет данных."

    rows = [
        "| Колода | Повторений | Новых | Again | Успешность | Время | Ср. ответ |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for deck in decks:
        rows.append(
            "| "
            f"{_escape_markdown_table(deck['deck_name'])} | "
            f"{format_int(deck['total_reviews'])} | "
            f"{format_int(deck['new_cards'])} | "
            f"{format_int(deck['again_count'])} | "
            f"{format_percent(deck['pass_rate'])} | "
            f"{format_duration_minutes(deck['total_seconds'] / 60)} | "
            f"{format_answer_seconds(deck['average_answer_seconds'])} |"
        )
    return "\n".join(rows)


def _deck_breakdown_text(deck_breakdown: Any) -> str:
    decks = _normalized_deck_breakdown(deck_breakdown)
    if not decks:
        return "По колодам за период нет данных."

    lines = []
    for deck in decks:
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


def _ranked_decks_table(decks: list[dict[str, Any]], hardest: bool = False) -> str:
    if not decks:
        if hardest:
            return "Явно тяжёлых колод за период не видно."
        return "Лучшие колоды пока не выделены: мало данных или нет подходящих колод."

    rows = [
        "| Колода | Повторений | Успешность | Again | Ср. ответ |",
        "|---|---:|---:|---:|---:|",
    ]
    for deck in decks:
        rows.append(
            "| "
            f"{_escape_markdown_table(deck['deck_name'])} | "
            f"{format_int(deck['total_reviews'])} | "
            f"{format_percent(deck['pass_rate'])} | "
            f"{format_int(deck['again_count'])} | "
            f"{format_answer_seconds(deck['average_answer_seconds'])} |"
        )
    return "\n".join(rows)


def _ranked_decks_text(decks: list[dict[str, Any]], hardest: bool = False) -> str:
    if not decks:
        if hardest:
            return "Явно тяжёлых колод за период не видно."
        return "Лучшие колоды пока не выделены: мало данных или нет подходящих колод."

    lines = []
    for deck in decks:
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
                "Материал даётся тяжело, стоит осторожно разобрать ответы Again."
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
        if average_answer_seconds <= 0 and total_reviews > 0:
            average_answer_seconds = round(total_seconds / total_reviews, 1)
        decks.append(
            {
                "deck_id": deck.get("deck_id"),
                "deck_name": str(deck.get("deck_name") or deck.get("deck_id") or "Без названия"),
                "total_reviews": total_reviews,
                "new_cards": _as_int(deck.get("new_cards")),
                "again_count": _as_int(deck.get("again_count")),
                "pass_rate": _normalized_pass_rate(deck.get("pass_rate")),
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
            actions.append("Разобрать ответы Again.")

    if _tomorrow_load_is_high(due_tomorrow, total_reviews):
        actions.append("Сначала закрыть завтрашнюю нагрузку.")

    if new_cards > 0 and low_pass_rate:
        actions.append("Новые временно снизить.")
    elif low_pass_rate:
        actions.append("Не брать много новых.")

    if not actions:
        actions.append("Можно оставить текущий темп.")

    actions = _dedupe_actions(actions)
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
    if not isinstance(deck_breakdown, list):
        return []

    decks: list[dict[str, Any]] = []
    for deck in deck_breakdown:
        if not isinstance(deck, dict):
            continue
        total_reviews = _as_int(deck.get("total_reviews"))
        if total_reviews <= 0 or _is_deleted_deck(deck):
            continue
        decks.append(
            {
                "deck_name": str(deck.get("deck_name") or deck.get("deck_id") or "Без названия"),
                "total_reviews": total_reviews,
                "again_count": _as_int(deck.get("again_count")),
                "pass_rate": _normalized_pass_rate(deck.get("pass_rate")),
                "estimated_minutes": _as_float(deck.get("estimated_minutes")),
            }
        )

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
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return "Топ колод за период не сформирован: нет повторений."

    lines = []
    for deck in top_decks:
        lines.append(
            "- "
            f"{deck['deck_name']}: {format_int(deck['total_reviews'])} повторений, "
            f"pass {format_percent(deck['pass_rate'])}, "
            f"Again {format_int(deck['again_count'])}, "
            f"время {format_duration_minutes(deck['estimated_minutes'])}."
        )
    return "\n".join(lines)


def _top_decks_table(deck_breakdown: Any) -> str:
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return "Топ колод за период не сформирован: нет повторений."

    rows = [
        "| Колода | Повторений | Pass rate | Again | Время |",
        "|---|---:|---:|---:|---:|",
    ]
    for deck in top_decks:
        rows.append(
            "| "
            f"{_escape_markdown_table(deck['deck_name'])} | "
            f"{format_int(deck['total_reviews'])} | "
            f"{format_percent(deck['pass_rate'])} | "
            f"{format_int(deck['again_count'])} | "
            f"{format_duration_minutes(deck['estimated_minutes'])} |"
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
    return [
        ("Повторений в день", format_int(round(total_reviews / days))),
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
        "< 80%: лучше разобрать Again и не перегружать новые. "
        "Проблемные колоды: pass < 80% и минимум "
        f"{format_int(templates.PROBLEM_DECK_MIN_REVIEWS)} повторений. "
        "Высокая нагрузка на завтра: примерно от 125% текущего объёма."
    )


def _thresholds_markdown() -> str:
    return "\n".join(
        [
            "- Pass rate >= 90%: чистая работа.",
            "- Pass rate 80-89%: нормально, но ошибки заметны.",
            "- Pass rate < 80%: лучше разобрать Again и не перегружать новые.",
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
    ]
    deleted_reviews = _deleted_reviews(metrics.get("deck_breakdown"))
    if deleted_reviews:
        lines.append(
            f"{format_int(deleted_reviews)} повторений относятся к удалённым карточкам."
        )
    return "\n".join(lines)


def _technical_markdown(meta: dict[str, str], metrics: dict[str, Any]) -> str:
    return _format_actions(_technical_text(meta, metrics).splitlines(), markdown=True)


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
    top_decks = _top_decks(deck_breakdown)
    if not top_decks:
        return '<p class="empty">Топ колод за период не сформирован: нет повторений.</p>'

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            '<th class="value">Повторений</th>'
            '<th class="value">Pass rate</th>'
            '<th class="value">Again</th>'
            '<th class="value">Время</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in top_decks:
        rows.append(
            "<tr>"
            f"<td>{_html(deck['deck_name'])}</td>"
            f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
            f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
            f'<td class="value">{_html(format_int(deck["again_count"]))}</td>'
            f'<td class="value">{_html(format_duration_minutes(deck["estimated_minutes"]))}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "".join(rows)


def _html_deck_breakdown(deck_breakdown: Any) -> str:
    decks = _normalized_deck_breakdown(deck_breakdown)
    if not decks:
        return '<p class="empty">По колодам за период нет данных.</p>'

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            '<th class="value">Повторений</th>'
            '<th class="value">Новых</th>'
            '<th class="value">Again</th>'
            '<th class="value">Успешность</th>'
            '<th class="value">Время</th>'
            '<th class="value">Ср. ответ</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in decks:
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


def _html_ranked_decks(decks: list[dict[str, Any]], hardest: bool = False) -> str:
    if not decks:
        if hardest:
            return '<p class="empty">Явно тяжёлых колод за период не видно.</p>'
        return '<p class="empty">Лучшие колоды пока не выделены: мало данных.</p>'

    rows = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Колода</th>"
            '<th class="value">Повторений</th>'
            '<th class="value">Успешность</th>'
            '<th class="value">Again</th>'
            '<th class="value">Ср. ответ</th>'
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    for deck in decks:
        rows.append(
            "<tr>"
            f"<td>{_html(deck['deck_name'])}</td>"
            f'<td class="value">{_html(format_int(deck["total_reviews"]))}</td>'
            f'<td class="value">{_html(format_percent(deck["pass_rate"]))}</td>'
            f'<td class="value">{_html(format_int(deck["again_count"]))}</td>'
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
