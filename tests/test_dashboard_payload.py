from __future__ import annotations

import pytest

from conftest import fresh_import_addon_module, load_dashboard_fixture


TOP_LEVEL_KEYS = {
    "metadata",
    "summary",
    "kpis",
    "answerDistribution",
    "activity",
    "comparison",
    "decks",
    "forecast",
    "fsrs",
    "recommendations",
    "cache",
}


@pytest.mark.parametrize(
    "fixture_name",
    ["minimal_metrics", "empty_collection", "normal_day", "large_collection"],
)
def test_build_dashboard_report_payload_contract_for_demo_fixtures(fixture_name):
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture(fixture_name)

    payload = dashboard_payload.build_dashboard_report_payload(
        fixture["metrics"],
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert_dashboard_contract(payload)
    assert payload["metadata"]["title"] == "Anki Study Report"
    assert payload["metadata"]["period"] == fixture["metadata"]["period"]
    assert payload["cache"]["status"] == fixture["cache"]["status"]


def test_dashboard_payload_normal_day_key_values():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")

    payload = dashboard_payload.build_dashboard_report_payload(
        fixture["metrics"],
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["metadata"]["answerMode"] == "pass_fail"
    assert payload["kpis"][0]["id"] == "total_reviews"
    assert payload["kpis"][0]["value"] == "100"
    assert payload["forecast"]["tomorrow"] == 80
    assert payload["decks"][0]["name"] == "Japanese::Core"


def test_dashboard_payload_cache_snapshot_fixture():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")
    snapshot = fixture["snapshot"]
    today = fixture["today"]

    metrics = dashboard_payload.metrics_from_cache_snapshot(snapshot, today)
    metadata = dashboard_payload.build_default_dashboard_metadata(snapshot, today)
    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        metadata,
        cache_summary=snapshot["status"],
    )

    assert_dashboard_contract(payload)
    assert payload["metadata"]["period"] == "Всё время"
    assert payload["kpis"][0]["value"] == "50"
    assert payload["activity"]["activeDays"] == 2
    assert payload["decks"][0]["totalReviews"] == 50
    assert payload["cache"]["status"] == "ready"


def test_dashboard_payload_imports_without_qt_ui_browser_opening_logic():
    fresh_import_addon_module("dashboard_payload")


def assert_dashboard_contract(payload: dict) -> None:
    assert TOP_LEVEL_KEYS.issubset(payload)
    assert isinstance(payload["metadata"], dict)
    assert isinstance(payload["summary"], dict)
    assert isinstance(payload["kpis"], list)
    assert isinstance(payload["answerDistribution"], list)
    assert isinstance(payload["activity"], dict)
    assert isinstance(payload["comparison"], dict)
    assert isinstance(payload["decks"], list)
    assert isinstance(payload["forecast"], dict)
    assert isinstance(payload["fsrs"], dict)
    assert isinstance(payload["recommendations"], dict)
    assert isinstance(payload["cache"], dict)
