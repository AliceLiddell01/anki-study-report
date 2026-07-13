from __future__ import annotations

from datetime import date, timedelta
import json

import pytest

from conftest import import_addon_module


stats = import_addon_module("statistics_service")


CATALOG = [
    {"deck_id": 1, "deck_name": "Languages", "filtered": False},
    {"deck_id": 2, "deck_name": "Languages::Japanese", "filtered": False},
    {"deck_id": 3, "deck_name": "Science", "filtered": False},
    {"deck_id": 9, "deck_name": "Filtered", "filtered": True},
]


def row(day: str, *, deck_id: int | None = None, reviews: int = 10, passed: int = 8, failed: int = 2, seconds: int = 100, new: int = 1) -> dict:
    value = {
        "date": day,
        "reviews": reviews,
        "new_cards": new,
        "learning": new,
        "review": max(0, reviews - new),
        "relearning": 0,
        "cram": 0,
        "again": failed,
        "hard": 1 if passed else 0,
        "good": max(0, passed - 2),
        "easy": 1 if passed else 0,
        "pass_count": passed,
        "fail_count": failed,
        "retention_young_pass": max(0, passed - 4),
        "retention_young_fail": failed,
        "retention_mature_pass": min(4, passed),
        "retention_mature_fail": 0,
        "answer_time_count": reviews,
        "study_seconds": seconds,
        "total_answer_seconds": float(seconds),
    }
    if deck_id is not None:
        value.update({"deck_id": deck_id, "deck_name": next(item["deck_name"] for item in CATALOG if item["deck_id"] == deck_id)})
    return value


def fixture(days: int = 120) -> tuple[dict, dict]:
    end = date(2026, 7, 12)
    daily = []
    deck_daily = []
    for offset in range(days):
        day = (end - timedelta(days=days - offset - 1)).isoformat()
        first = row(day, deck_id=2, reviews=6, passed=5, failed=1, seconds=60)
        second = row(day, deck_id=3, reviews=4, passed=3, failed=1, seconds=40)
        deck_daily.extend([first, second])
        daily.append(row(day))
    snapshot = {"status": {"status": "ready", "updatedAt": 1}, "daily": daily, "deckDaily": deck_daily}
    current = {
        "deckCatalog": CATALOG,
        "states": [
            {"deckId": 2, "state": "mature", "cards": 20, "notes": 18},
            {"deckId": 2, "state": "suspended", "cards": 2, "notes": 2},
            {"deckId": 3, "state": "young", "cards": 10, "notes": 10},
        ],
        "noteCounts": [{"deckId": 2, "notes": 18}, {"deckId": 3, "notes": 10}],
        "due": [
            {"deckId": 2, "dayOffset": -2, "category": "review", "count": 3},
            {"deckId": 2, "dayOffset": 7, "category": "review", "count": 4},
            {"deckId": 3, "dayOffset": 30, "category": "learning", "count": 2},
        ],
        "dailyLoad": [{"deckId": 2, "value": 1.5}, {"deckId": 3, "value": 0.5}],
    }
    return snapshot, current


def build(query: dict | None = None) -> dict:
    snapshot, current = fixture()
    return stats.build_statistics_result(
        snapshot,
        current,
        "2026-07-12",
        query or stats.default_statistics_query(),
        display_settings={"selected_deck_ids": [1, 2, 3], "include_child_decks": True},
    )


def test_metric_aggregation_is_weighted_and_true_retention_is_distinct():
    aggregate = stats._aggregate([
        row("2026-07-01", reviews=10, passed=8, failed=2, seconds=100),
        row("2026-07-02", reviews=2, passed=1, failed=1, seconds=60),
    ])
    assert aggregate["successRate"] == 0.75
    assert aggregate["averageAnswerSeconds"] == pytest.approx(13.333, abs=0.001)
    assert aggregate["ratings"] == {"again": 3, "hard": 2, "good": 6, "easy": 2}
    assert aggregate["trueRetention"] == {
        "overall": 0.75,
        "young": 0.5714,
        "mature": 1.0,
        "youngPass": 4,
        "youngFail": 3,
        "maturePass": 5,
        "matureFail": 0,
        "sampleSize": 12,
    }


def test_missing_answer_time_is_unavailable_not_zero():
    missing = row("2026-07-01", reviews=5, seconds=0)
    missing["answer_time_count"] = 0
    aggregate = stats._aggregate([missing])
    assert aggregate["studySeconds"] is None
    assert aggregate["averageAnswerSeconds"] is None


@pytest.mark.parametrize(
    ("period", "start"),
    [("7d", "2026-07-06"), ("30d", "2026-06-13"), ("90d", "2026-04-14"), ("1y", "2025-07-13")],
)
def test_exact_period_bounds(period, start):
    result = build({"scope": {"kind": "all_collection"}, "period": period, "granularity": "auto", "comparison": True})
    assert result["bounds"]["current"] == {"start": start, "end": "2026-07-12"}


def test_leap_year_month_end_and_all_time_month_granularity():
    assert stats._subtract_year(date(2024, 2, 29)) == date(2023, 2, 28)
    snapshot, current = fixture(500)
    result = stats.build_statistics_result(snapshot, current, "2026-07-12", {"scope": {"kind": "all_collection"}, "period": "all", "granularity": "day", "comparison": True})
    assert result["query"]["resolvedGranularity"] == "month"
    assert result["query"]["comparison"] is False
    assert len(result["overview"]["series"]) <= stats.MAX_BUCKETS


def test_previous_period_reports_partial_coverage_without_zero_filling():
    snapshot, current = fixture(40)
    result = stats.build_statistics_result(snapshot, current, "2026-07-12", {"scope": {"kind": "all_collection"}, "period": "30d", "granularity": "day", "comparison": True})
    assert result["overview"]["comparison"]["status"] == "partial"
    assert result["overview"]["comparison"]["reason"] == "partial_previous_coverage"


def test_scopes_direct_subtree_dashboard_and_filtered_rejection():
    snapshot, current = fixture()
    direct = stats.build_statistics_result(snapshot, current, "2026-07-12", {"scope": {"kind": "single_deck", "deckId": 1, "mode": "direct"}, "period": "7d", "granularity": "day", "comparison": False})
    subtree = stats.build_statistics_result(snapshot, current, "2026-07-12", {"scope": {"kind": "single_deck", "deckId": 1, "mode": "subtree"}, "period": "7d", "granularity": "day", "comparison": False})
    assert direct["overview"]["kpis"]["reviews"] == 0
    assert subtree["overview"]["kpis"]["reviews"] == 42
    assert subtree["scope"]["deckIds"] == [1, 2]
    with pytest.raises(stats.StatisticsValidationError) as error:
        stats.normalize_statistics_query({"scope": {"kind": "single_deck", "deckId": 9}}, CATALOG)
    assert error.value.field_errors["scope.deckId"] == "Filtered decks are not supported."


def test_query_rejects_unknown_fields_arbitrary_search_and_bad_enums():
    for payload, field in [
        ({"search": "rated:1"}, "search"),
        ({"sql": "select * from revlog"}, "sql"),
        ({"period": "forever"}, "period"),
        ({"granularity": "hour"}, "granularity"),
        ({"scope": {"kind": "single_deck", "deckId": 999}}, "scope.deckId"),
    ]:
        with pytest.raises(stats.StatisticsValidationError) as error:
            stats.normalize_statistics_query(payload, CATALOG)
        assert field in error.value.field_errors


def test_current_state_cards_notes_backlog_future_due_and_daily_load():
    result = build({"scope": {"kind": "all_collection"}, "period": "30d", "granularity": "day", "comparison": True})
    progress = result["progress"]
    assert progress["currentStates"]["mature"] == 20
    assert progress["currentStates"]["young"] == 10
    assert progress["currentStates"]["suspended"] == 2
    assert progress["totalCards"] == 32
    assert progress["historicalStateSeriesAvailable"] is False
    assert result["load"]["overdue"] == 3
    assert result["load"]["dailyLoad"] == 2.0
    assert result["load"]["futureDue"] == [
        {"dayOffset": 7, "learning": 0, "review": 4, "relearning": 0, "total": 4},
        {"dayOffset": 30, "learning": 2, "review": 0, "relearning": 0, "total": 2},
    ]


def test_deck_comparison_uses_non_overlapping_roots_and_bounds_payload():
    result = build()
    assert [item["fullName"] for item in result["deckComparison"]["rows"]] == ["Languages", "Science"]
    assert len(result["deckComparison"]["rows"]) <= stats.MAX_DECK_ROWS
    assert stats.compact_json_size(result) < 300_000
    serialized = json.dumps(result)
    assert '"cid"' not in serialized.lower()
    assert "token" not in serialized.lower()
    assert "cardId" not in serialized


def test_statistics_hub_publishes_initial_90d_result_and_capabilities():
    snapshot, current = fixture()
    hub = stats.build_statistics_hub(snapshot, current, "2026-07-12", display_settings={})
    assert set(hub) == {
        "schemaVersion",
        "metricDefinitionsVersion",
        "generatedAt",
        "availability",
        "coverage",
        "defaultQuery",
        "deckOptions",
        "capabilities",
        "initialResult",
        "scope",
        "fsrs",
    }
    assert set(hub["initialResult"]) == {
        "schemaVersion",
        "query",
        "scope",
        "bounds",
        "coverage",
        "confidencePolicy",
        "overview",
        "quality",
        "load",
        "progress",
        "deckComparison",
        "limitations",
        "calculationVersion",
    }
    assert hub["defaultQuery"] == stats.default_statistics_query()
    assert hub["initialResult"]["query"]["period"] == "90d"
    assert hub["capabilities"] == {
        "core": "available",
        "fsrs": "unavailable",
        "advanced": "future_not_exposed",
        "providers": [],
        "nativeStatsAction": True,
    }
    assert hub["fsrs"]["availability"] == "unavailable"
    assert stats.compact_json_size(hub) < 200_000
