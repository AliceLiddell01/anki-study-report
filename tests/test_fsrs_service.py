from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from conftest import import_addon_module


fsrs = import_addon_module("fsrs_service")


class FakeDecks:
    def all(self):
        return [
            {"id": 1, "name": "Japanese", "conf": 10, "desiredRetention": 0.93},
            {"id": 2, "name": "Japanese::Words", "conf": 10},
            {"id": 3, "name": "Science", "conf": 20},
            {"id": 9, "name": "Filtered", "dyn": 1},
        ]

    def config_dict_for_deck_id(self, deck_id):
        if deck_id in {1, 2}:
            return {"id": 10, "name": "Languages", "desiredRetention": 0.9, "fsrsParams6": [0.1, 0.2, 0.3], "new": {"delays": [1, 10]}, "lapse": {"delays": [10]}, "rev": {"maxIvl": 36500}}
        return {"id": 20, "name": "Science", "desiredRetention": 0.88, "fsrsParams6": [0.4, 0.5, 0.6], "new": {"delays": []}, "lapse": {"delays": []}, "rev": {"maxIvl": 36500}}


class FakeDb:
    def first(self, sql, *args):
        return (100 * len(args), 80 * len(args))

    def scalar(self, sql, *args):
        return 500 * len(args)

    def all(self, sql, *args):
        if "count(*)" in sql and "group by case" in sql and "from cards" in sql:
            return [(deck_id, 100, 80) for deck_id in args]
        if "count(*)" in sql and "join cards" in sql and "group by case" in sql:
            return [(deck_id, 500) for deck_id in args]
        if "json_extract(data,'$.s')" in sql:
            return [
                (1, 50, 10, 2.0, 2.0, 0.5),
                (1, 95, 20, 60.0, 7.0, 0.5),
                (2, 110, 1, 2.0, 9.0, 0.5),
            ]
        if "with ordered" in sql:
            day = 86_400_000
            return [(10 * day, 9 * day, 3, 10.0, 0.5), (11 * day, 10 * day, 1, 10.0, 0.5)]
        return []

    def list(self, sql, *args):
        return [101]


class FakeReview:
    def __init__(self, time, button, stability):
        self.time = time
        self.button_chosen = button
        self.memory_state = SimpleNamespace(stability=stability, difficulty=5.0)
    def HasField(self, field):
        return field == "memory_state"


class FakeBackend:
    def card_stats(self, card_id):
        now = int(__import__("time").time())
        return SimpleNamespace(revlog=[FakeReview(now - 172800, 3, 10.0), FakeReview(now - 86400, 3, 10.0), FakeReview(now, 1, 10.0)])


class FakeSched:
    today = 100


class FakeCollection:
    decks = FakeDecks()
    db = FakeDb()
    sched = FakeSched()
    _backend = FakeBackend()

    def get_config(self, key):
        return key == "fsrs"


def test_configuration_groups_are_stable_typed_and_exclude_filtered_decks():
    groups = fsrs.discover_configuration_groups(FakeCollection())
    assert len(groups) == 2
    languages = groups[0]
    assert languages["presetId"] == 10
    assert languages["deckIds"] == [1, 2]
    assert languages["learningStepsSeconds"] == [60, 600]
    assert languages["deckDesiredRetentionOverrides"] == [{"deckId": 1, "desiredRetention": 0.93}]
    assert languages["parameterFingerprint"] == fsrs.parameter_fingerprint([0.1, 0.2, 0.3])
    assert 9 not in {deck for group in groups for deck in group["deckIds"]}


def test_capability_is_lightweight_and_reports_mixed_configuration():
    capability = fsrs.build_fsrs_capability(FakeCollection())
    assert capability["enabled"] is True
    assert capability["availability"] == "mixed_configuration"
    assert capability["configurationCount"] == 2
    assert fsrs.compact_json_size(capability) < 20_000
    serialized = json.dumps(capability).lower()
    assert "_params" not in serialized
    assert "token" not in serialized


def test_request_is_strict_and_rejects_search_sql_params_and_mixed_simulation():
    groups = fsrs.discover_configuration_groups(FakeCollection())
    for payload, field in [
        ({"operation": "memory", "search": "rated:1"}, "search"),
        ({"operation": "memory", "sql": "select *"}, "sql"),
        ({"operation": "memory", "params": [1, 2]}, "params"),
        ({"operation": "explode"}, "operation"),
        ({"operation": "simulate", "scope": {"kind": "all_collection"}, "simulation": {}}, "scope"),
    ]:
        with pytest.raises(fsrs.FsrsValidationError) as error:
            fsrs.normalize_fsrs_request(payload, groups)
        assert field in error.value.field_errors


def test_simulation_ranges_are_bounded():
    groups = fsrs.discover_configuration_groups(FakeCollection())
    valid = fsrs.normalize_fsrs_request({
        "operation": "simulate",
        "scope": {"kind": "deck", "deckId": 1},
        "simulation": {"desiredRetention": 0.93, "horizonDays": 180, "additionalNewCards": 20, "newCardsPerDay": 10, "maximumReviewsPerDay": 500},
    }, groups)
    assert valid["simulation"]["horizonDays"] == 180
    with pytest.raises(fsrs.FsrsValidationError):
        fsrs.normalize_fsrs_request({
            "operation": "simulate", "scope": {"kind": "deck", "deckId": 1},
            "simulation": {"desiredRetention": 1, "horizonDays": 999, "additionalNewCards": -1, "newCardsPerDay": 1, "maximumReviewsPerDay": 0},
        }, groups)


def test_memory_snapshot_uses_each_decks_own_target_and_never_returns_cards():
    groups = fsrs.discover_configuration_groups(FakeCollection())
    memory = fsrs.build_memory_snapshot(FakeCollection(), [groups[0]], [1, 2])
    assert memory["studiedCards"] == 3
    assert memory["estimatedRemembered"] > 0
    assert memory["cardsBelowOwnTarget"] >= 1
    assert memory["medianStabilityDays"] == 2
    assert sum(row["count"] for row in memory["retrievabilityDistribution"]) == 3
    serialized = json.dumps(memory).lower()
    for forbidden in ("cardid", "front", "back", "note", "revlog", "token", "collection.anki2"):
        assert forbidden not in serialized


def test_calibration_treats_hard_good_easy_as_success_and_marks_sparse_bins():
    group = fsrs.discover_configuration_groups(FakeCollection())[0]
    result = fsrs.build_calibration(FakeCollection(), group, "90d")
    assert result["sampleSize"] == 2
    assert result["sufficiency"] == "insufficient"
    assert result["hardIsRecall"] is True
    populated = next(row for row in result["bins"] if row["sampleSize"])
    assert populated["actual"] == 0.5
    assert populated["sufficiency"] == "insufficient"


def test_steps_mixed_scope_is_explicit_and_has_no_apply_action():
    groups = fsrs.discover_configuration_groups(FakeCollection())
    result = fsrs.build_steps(FakeCollection(), groups, "90d")
    assert result["availability"] == "mixed_configuration"
    assert result["recommendation"] is None
    assert "apply" not in json.dumps(result).lower()
