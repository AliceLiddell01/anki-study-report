from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from gamification_sim.canonical_json import canonical_dumps
from gamification_sim.learn_candidate_protocol import generate_dry_units, matrix_summary
from gamification_sim.strict_json import load_strict_json, loads_strict


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "contracts/learn-xp-candidate-protocol-v1.json"
SCHEMA_PATH = ROOT / "schemas/learn-xp-candidate-protocol-v1.schema.json"
LIFECYCLE_MODEL_PATH = ROOT / "contracts/learn-xp-lifecycle-model-v1.json"
LIFECYCLE_SCHEMA_PATH = ROOT / "schemas/learn-xp-lifecycle-model-v1.schema.json"
FIXTURE_SCHEMA_PATH = ROOT / "schemas/learn-xp-lifecycle-fixture-v1.schema.json"
MANIFEST_PATH = ROOT / "fixtures/learn-xp-lifecycle-v1/manifest.json"
HUMAN_PATH = ROOT.parent.parent / "docs/gamification/learn-xp-candidate-protocol.md"

EXPECTED_FIXTURES = 23
EXPECTED_INVARIANTS = 19
EXPECTED_UNITS = 340


def validator():
    schema = load_strict_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def protocol():
    return load_strict_json(PROTOCOL_PATH)


def semantic_validate(value: dict) -> None:
    families = value["families"]
    assert {item["family_id"] for item in families} == {
        "F-CONFIRMATION-ONLY",
        "F-PENDING-CONFIRMED-SPLIT",
    }
    family_by_id = {item["family_id"]: item for item in families}
    assert family_by_id["F-CONFIRMATION-ONLY"]["pending_share_lru"] == 0.0
    assert family_by_id["F-PENDING-CONFIRMED-SPLIT"]["pending_share_lru"] == 0.25
    for item in families:
        assert item["pending_share_lru"] + item["confirmation_settlement_lru"] == 1.0
        assert 0 <= item["pending_share_lru"] < 0.5

    params = value["parameterizations"]
    assert len(params) == 4
    assert all(
        item["pending_share_lru"] + item["confirmation_settlement_lru"] == 1.0
        for item in params
    )
    assert all(len(item["parameterization_ids"]) == 2 for item in families)

    strategies = value["subject_strategies"]
    assert strategies["note_sibling_relation"] == "OPERATIONALLY_EQUIVALENT"
    assert {item["subject_strategy_id"] for item in strategies["strategies"]} == {
        "S-CARD", "S-NOTE-SIBLING"
    }
    note_sibling = next(
        item for item in strategies["strategies"]
        if item["subject_strategy_id"] == "S-NOTE-SIBLING"
    )
    assert set(note_sibling["conceptual_subject_ids"]) == {"NOTE", "SIBLING_GROUP"}

    delays = {item["delay_policy_id"]: item for item in value["delay_policies"]}
    assert set(delays) == {"D1", "D2"}
    assert (delays["D1"]["minimum_elapsed"], delays["D1"]["minimum_anki_day_delta"]) == (1440, 1)
    assert (delays["D2"]["minimum_elapsed"], delays["D2"]["minimum_anki_day_delta"]) == (4320, 3)
    assert all(item["same_chain_excluded"] for item in delays.values())
    assert all(not item["displayed_interval_used"] for item in delays.values())

    candidates = value["candidate_registry"]
    assert len(candidates) == len({item["candidate_id"] for item in candidates}) == 8
    assert all(item["screening_status"] is None for item in candidates)
    assert all(item["screening_outcome"] is None for item in candidates)
    expected_cross = {
        (param["parameterization_id"], strategy["subject_strategy_id"])
        for param in params
        for strategy in strategies["strategies"]
    }
    assert {
        (item["parameterization_id"], item["subject_strategy_id"])
        for item in candidates
    } == expected_cross

    assert value["reference"]["reference_id"] == "L-NO-LEARN-XP"
    assert all(not item["candidate"] for item in value["reference"]["variants"])
    assert all(item["reward_allocation_lru"] == 0.0 for item in value["reference"]["variants"])

    gate_ids = [item["gate_id"] for item in value["hard_gates"]]
    assert len(gate_ids) == len(set(gate_ids)) == 23
    manifest = load_strict_json(MANIFEST_PATH)
    mapped = {
        invariant
        for gate in value["hard_gates"]
        for invariant in gate["invariant_ids"]
    }
    assert mapped == set(manifest["covered_invariant_ids"])
    assert manifest["fixture_count"] == EXPECTED_FIXTURES
    assert manifest["manifest_digest"] == value["source_contracts"]["g2_2"]["fixture_manifest_digest"]

    assert not value["family_survivor_policy"]["weighted_score_allowed"]
    assert value["family_survivor_policy"]["exact_tie_outcome"] == "FAMILY_INCONCLUSIVE"
    assert not value["matrix_axes"]["adaptive_units_allowed"]
    assert value["matrix_axes"]["seed_axis"] == "ABSENT_DETERMINISTIC"

    units = generate_dry_units(value)
    assert len(units) == EXPECTED_UNITS
    assert len({item["unit_id"] for item in units}) == EXPECTED_UNITS
    assert all(item["seed"] is None for item in units)
    summary = matrix_summary(value)
    assert summary["unit_count"] == summary["unique_unit_ids"] == EXPECTED_UNITS
    assert set(manifest["fixture_ids"]) <= set(summary["scenario_ids"])
    assert set(summary["candidate_or_reference_ids"]) == set(
        value["matrix_axes"]["candidate_or_reference_identity"]
    )
    assert set(summary["subject_strategy_ids"]) == {"S-CARD", "S-NOTE-SIBLING"}
    assert set(summary["delay_policy_ids"]) == {"D1", "D2", "D-NONE"}

    flags = value["production_flags"]
    for key in (
        "screening_implemented", "screening_executed", "candidate_outcome_selected",
        "family_survivor_selected", "final_model_selected", "production_approved",
        "production_integration", "g2_4_started",
    ):
        assert flags[key] is False


def test_schema_self_check_protocol_and_source_continuity() -> None:
    value = protocol()
    validator().validate(value)
    semantic_validate(value)
    lifecycle_schema = load_strict_json(LIFECYCLE_SCHEMA_PATH)
    fixture_schema = load_strict_json(FIXTURE_SCHEMA_PATH)
    Draft202012Validator.check_schema(lifecycle_schema)
    Draft202012Validator.check_schema(fixture_schema)
    Draft202012Validator(lifecycle_schema).validate(load_strict_json(LIFECYCLE_MODEL_PATH))
    assert HUMAN_PATH.exists()


def test_protocol_determinism_and_matrix_identity() -> None:
    value = protocol()
    assert canonical_dumps(value) == canonical_dumps(load_strict_json(PROTOCOL_PATH))
    first = generate_dry_units(value)
    second = generate_dry_units(value)
    assert first == second
    assert [item["unit_id"] for item in first] == [item["unit_id"] for item in second]


def test_strict_json_rejects_duplicate_keys_and_nonfinite() -> None:
    with pytest.raises(Exception, match="duplicate object key"):
        loads_strict('{"a":1,"a":2}')
    with pytest.raises(Exception, match="non-standard JSON number"):
        loads_strict('{"value":NaN}')


def test_negative_samples() -> None:
    base = protocol()
    checks = []

    def invalid_schema(mutator):
        bad = copy.deepcopy(base)
        mutator(bad)
        checks.append(("schema", bad))

    def invalid_semantic(mutator):
        bad = copy.deepcopy(base)
        mutator(bad)
        checks.append(("semantic", bad))

    invalid_schema(lambda p: p["families"].append(copy.deepcopy(p["families"][0])))
    invalid_schema(lambda p: p.__setitem__("families", []))
    invalid_schema(lambda p: p["families"][0]["parameterization_ids"].append("P-EXTRA"))
    invalid_schema(lambda p: p["families"][1].__setitem__("pending_share_lru", 0.0))
    invalid_schema(lambda p: p["families"][1].__setitem__("pending_share_lru", 0.5))
    invalid_schema(lambda p: p["families"][0].__setitem__("pending_share_lru", 0.1))
    invalid_schema(lambda p: p["families"][1].__setitem__("confirmation_settlement_lru", 1.0))
    invalid_schema(lambda p: p["families"][1].__setitem__("pending_share_lru", -0.1))
    invalid_schema(lambda p: p["candidate_registry"][0].__setitem__("subject_strategy_id", "UNKNOWN"))
    invalid_schema(lambda p: p["candidate_registry"][0].__setitem__("delay_policy_id", "D9"))
    invalid_schema(lambda p: p["reference"].__setitem__("candidate", True))
    invalid_semantic(lambda p: p["candidate_registry"][1].__setitem__("candidate_id", p["candidate_registry"][0]["candidate_id"]))
    invalid_schema(lambda p: p.__setitem__("hard_gates", p["hard_gates"][:-1]))
    invalid_schema(lambda p: p["family_survivor_policy"].__setitem__("weighted_score_allowed", True))
    invalid_schema(lambda p: p["matrix_axes"].__setitem__("adaptive_units_allowed", True))
    invalid_schema(lambda p: p.__setitem__("scenario_registry", []))
    invalid_schema(lambda p: p["production_flags"].__setitem__("screening_executed", True))
    invalid_schema(lambda p: p["candidate_registry"][0].__setitem__("screening_status", "SCREENING_ELIGIBLE"))
    invalid_schema(lambda p: p["production_flags"].__setitem__("production_approved", True))
    invalid_schema(lambda p: p.__setitem__("real_card_text", "private"))
    invalid_schema(lambda p: p.__setitem__("profile_path", "/home/user/.local/share/Anki2"))
    invalid_schema(lambda p: p.__setitem__("raw_revlog", []))
    invalid_schema(lambda p: p.__setitem__("protocol_publication_sha", "0" * 40))
    invalid_schema(lambda p: p.__setitem__("unexpected", True))

    v = validator()
    for kind, bad in checks:
        if kind == "schema":
            with pytest.raises(ValidationError):
                v.validate(bad)
        else:
            v.validate(bad)
            with pytest.raises(AssertionError):
                semantic_validate(bad)


def test_no_private_fields_results_or_production_imports() -> None:
    value = protocol()

    def object_keys(node):
        if isinstance(node, dict):
            keys = set(node)
            for child in node.values():
                keys.update(object_keys(child))
            return keys
        if isinstance(node, list):
            keys = set()
            for child in node:
                keys.update(object_keys(child))
            return keys
        return set()

    forbidden_keys = {
        "real_card_text",
        "profile_path",
        "raw_revlog",
        "protocol_publication_sha",
        "screening_result",
        "selected_survivor",
    }
    assert object_keys(value).isdisjoint(forbidden_keys)
    source = (ROOT / "src/gamification_sim/learn_candidate_protocol.py").read_text(encoding="utf-8")
    for fragment in ("anki_study_report", "aqt", "anki.collection", "sqlite3", "requests", "httpx"):
        assert fragment not in source
