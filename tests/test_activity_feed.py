from __future__ import annotations

import json

import pytest

from conftest import fresh_import_addon_module


@pytest.fixture
def activity():
    return fresh_import_addon_module("activity_service")


def daily(day, reviews, *, new=0, passed=None, failed=0, seconds=0):
    passed = max(0, reviews - failed) if passed is None else passed
    return {
        "date": day,
        "reviews": reviews,
        "new_cards": new,
        "pass_count": passed,
        "fail_count": failed,
        "study_seconds": seconds,
    }


def deck(day, deck_id, name, reviews, *, passed=None, failed=0, seconds=0):
    return {
        **daily(day, reviews, passed=passed, failed=failed, seconds=seconds),
        "deck_id": deck_id,
        "deck_name": name,
    }


def snapshot(days, decks=None):
    return {"daily": days, "deckDaily": decks or []}


def test_period_bounds_are_inclusive_and_calendar_safe(activity):
    bounds = activity.activity_period_bounds("2026-07-11")
    assert bounds["30d"]["start"] == "2026-06-12"
    assert bounds["90d"]["start"] == "2026-04-13"
    assert bounds["6m"]["start"] == "2026-01-12"
    assert bounds["1y"]["start"] == "2025-07-12"

    leap = activity.activity_period_bounds("2024-02-29")
    assert leap["1y"] == {"start": "2023-03-01", "end": "2024-02-29", "label": "Последний год"}
    month_end = activity.activity_period_bounds("2026-08-31")
    assert month_end["6m"]["start"] == "2026-03-01"


def test_activity_days_distinguish_unavailable_inactive_and_active(activity):
    payload = activity.build_activity_hub_payload(
        snapshot([
            daily("2026-07-01", 3),
            daily("2026-07-03", 5, passed=0, failed=0, seconds=0),
        ]),
        "2026-07-04",
    )
    by_date = {day["date"]: day for day in payload["days"]}
    assert by_date["2026-06-30"]["availability"] == "unavailable"
    assert by_date["2026-07-02"]["availability"] == "inactive"
    assert by_date["2026-07-03"]["availability"] == "active"
    assert by_date["2026-07-03"]["successRate"] is None
    assert by_date["2026-07-03"]["studySeconds"] is None
    assert by_date["2026-07-04"]["availability"] == "inactive"


def test_activity_scope_uses_selected_deck_rows_and_preserves_all_collection_source(activity):
    source = snapshot(
        [daily("2026-07-10", 30, failed=3)],
        [
            deck("2026-07-10", 1, "Alpha", 10, failed=1),
            deck("2026-07-10", 2, "Beta", 20, failed=2),
        ],
    )
    all_payload = activity.build_activity_hub_payload(source, "2026-07-11")
    selected = activity.build_activity_hub_payload(
        source,
        "2026-07-11",
        display_settings={"selected_deck_ids": [1], "include_child_decks": False},
    )
    all_day = next(day for day in all_payload["days"] if day["date"] == "2026-07-10")
    selected_day = next(day for day in selected["days"] if day["date"] == "2026-07-10")
    assert all_day["reviews"] == 30
    assert selected_day["reviews"] == 10
    assert selected_day["decks"] == [{"id": 1, "name": "Alpha", "reviews": 10, "pass": 9, "fail": 1, "successRate": 0.9}]
    assert selected["scope"] == {"kind": "selected", "selectedDeckIds": [1], "includeChildDecks": False}
    assert source["daily"][0]["reviews"] == 30


def test_day_decks_are_sorted_and_all_more_than_five_are_recoverable(activity):
    decks = [deck("2026-07-10", index, f"Колода {index}", index) for index in range(1, 8)]
    payload = activity.build_activity_hub_payload(snapshot([daily("2026-07-10", 28)], decks), "2026-07-11")
    day = next(day for day in payload["days"] if day["date"] == "2026-07-10")
    assert day["activeDeckCount"] == 7
    assert [item["reviews"] for item in day["decks"]] == [7, 6, 5, 4, 3, 2, 1]


def test_every_active_day_has_newest_first_deterministic_daily_entry(activity):
    payload = activity.build_activity_hub_payload(
        snapshot([daily("2026-07-01", 5), daily("2026-07-03", 7)]),
        "2026-07-04",
    )
    assert [(entry["id"], entry["date"]) for entry in payload["feed"]["days"]] == [
        ("2026-07-03:daily-summary", "2026-07-03"),
        ("2026-07-01:daily-summary", "2026-07-01"),
    ]
    assert payload["feed"]["pageSize"] == 14


def test_return_requires_two_known_inactive_days_and_never_crosses_unavailable(activity):
    payload = activity.build_activity_hub_payload(
        snapshot([daily("2026-07-01", 5), daily("2026-07-04", 6)]),
        "2026-07-05",
    )
    latest = payload["feed"]["days"][0]
    assert {item["type"]: item for item in latest["highlights"]}["return_after_break"] == {
        "id": "2026-07-04:return:2",
        "type": "return_after_break",
        "inactiveDays": 2,
    }

    first_known = activity.build_activity_hub_payload(snapshot([daily("2026-07-04", 6)]), "2026-07-05")
    assert first_known["feed"]["days"][0]["highlights"] == []


def test_milestones_keep_pre_window_context(activity):
    start = activity.date(2025, 7, 5)
    rows = [daily((start + activity.timedelta(days=index)).isoformat(), 5) for index in range(14)]
    payload = activity.build_activity_hub_payload(snapshot(rows), "2026-07-11")
    milestone = next(entry for entry in payload["feed"]["days"] if entry["date"] == "2025-07-18")
    assert {item["type"]: item for item in milestone["highlights"]}["streak_milestone"]["days"] == 14


def test_record_is_strict_uses_prior_history_and_skips_first_day(activity):
    payload = activity.build_activity_hub_payload(
        snapshot([
            daily("2024-01-01", 100),
            daily("2026-07-09", 90),
            daily("2026-07-10", 100),
            daily("2026-07-11", 101),
        ]),
        "2026-07-11",
    )
    entries = {entry["date"]: entry for entry in payload["feed"]["days"]}
    assert not any(item["type"] == "new_activity_record" for item in entries["2026-07-09"]["highlights"])
    assert not any(item["type"] == "new_activity_record" for item in entries["2026-07-10"]["highlights"])
    record = next(item for item in entries["2026-07-11"]["highlights"] if item["type"] == "new_activity_record")
    assert record == {"id": "2026-07-11:record:101", "type": "new_activity_record", "reviews": 101, "previousMax": 100}


def test_weekly_summary_is_completed_weighted_and_compares_eligible_weeks(activity):
    rows = [
        daily("2026-06-29", 10, passed=9, failed=1, seconds=100),
        daily("2026-07-01", 10, passed=1, failed=9, seconds=0),
        daily("2026-07-06", 20, passed=18, failed=2, seconds=200),
        daily("2026-07-08", 10, passed=8, failed=2, seconds=100),
        daily("2026-07-20", 50),
    ]
    payload = activity.build_activity_hub_payload(snapshot(rows), "2026-07-20")
    weeks = {week["weekStart"]: week for week in payload["feed"]["weeks"]}
    current = weeks["2026-07-06"]
    assert current["weekEnd"] == "2026-07-12"
    assert current["activeDays"] == 2
    assert current["reviews"] == 30
    assert current["studySeconds"] == 300
    assert current["successRate"] == 0.8667
    assert current["comparison"] == {"reviewsPercentChange": 50, "direction": "more"}
    assert "2026-07-20" not in weeks


def test_weekly_comparison_handles_threshold_zero_and_partial_coverage(activity):
    insufficient = activity.build_activity_hub_payload(
        snapshot([daily("2026-07-08", 10), daily("2026-07-13", 10), daily("2026-07-14", 10)]),
        "2026-07-20",
    )
    assert all(week["comparison"] is None for week in insufficient["feed"]["weeks"])
    assert all(week["weekStart"] != "2026-07-06" for week in insufficient["feed"]["weeks"])


def test_activity_payload_is_bounded_json_safe_and_contains_no_private_data(activity):
    payload = activity.build_activity_hub_payload(
        snapshot([daily("2020-01-01", 1), daily("2026-07-11", 2)]),
        "2026-07-11",
    )
    assert len(payload["days"]) == 365
    assert payload["bounds"]["start"] == "2025-07-12"
    encoded = json.dumps(payload, ensure_ascii=False)
    assert len(encoded.encode("utf-8")) < 100_000
    for forbidden in ("token", "collection.anki2", "addon_data", "card content", "rawrevlog"):
        assert forbidden not in encoded.lower()
