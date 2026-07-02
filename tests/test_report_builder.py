from __future__ import annotations

from conftest import import_addon_module


def test_report_builder_handles_zero_reviews_without_division_errors():
    report_builder = import_addon_module("report_builder")
    metrics = {
        "total_reviews": 0,
        "new_cards": 0,
        "again_count": 0,
        "pass_rate": 0,
        "fail_rate": 0,
        "due_tomorrow": 0,
        "deck_breakdown": [],
    }
    metadata = {"period": "today", "period_human": "сегодня", "detail_level": "normal"}

    markdown = report_builder.build_markdown_report(metrics, metadata)
    html = report_builder.render_html_report(metrics, metadata)

    assert "### KPI" in markdown
    assert "### Следующее действие" in markdown
    assert "нет повторений" in markdown.lower() or "0" in markdown
    assert "Anki Study Report" in html
    assert "Traceback" not in markdown
    assert "ZeroDivisionError" not in html


def test_report_builder_renders_expected_pass_fail_percentages():
    report_builder = import_addon_module("report_builder")
    metrics = {
        "answer_mode": "pass_fail",
        "total_reviews": 10,
        "new_cards": 2,
        "again_count": 1,
        "fail_count": 1,
        "pass_count": 9,
        "pass_rate": 0.9,
        "fail_rate": 0.1,
        "total_seconds": 120,
        "estimated_minutes": 2,
        "average_answer_seconds": 12,
        "due_tomorrow": 3,
        "deck_breakdown": [
            {
                "deck_name": "Core",
                "total_reviews": 10,
                "new_cards": 2,
                "fail_count": 1,
                "pass_count": 9,
                "pass_rate": 0.9,
                "fail_rate": 0.1,
                "total_seconds": 120,
                "average_answer_seconds": 12,
            }
        ],
    }
    metadata = {"period": "today", "period_human": "сегодня", "detail_level": "normal"}

    markdown = report_builder.build_markdown_report(metrics, metadata)
    html = report_builder.render_html_report(metrics, metadata)

    for expected in ["90%", "10%", "### KPI", "### Таблица по колодам"]:
        assert expected in markdown
    assert "90%" in html
    assert "10%" in html
