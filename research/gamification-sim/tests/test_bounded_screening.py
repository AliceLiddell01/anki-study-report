from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest

from gamification_sim.bounded_screening import (
    CASE_TO_POLICY_PAIR_ID,
    EXPECTED_SCREENING_UNIT_COUNT,
    ScreeningExecutionUnit,
    build_screening_manifest,
    evaluate_screening_gates,
    load_and_validate_screening_protocol,
    validate_bounded_screening_result,
    validate_screening_manifest,
)


ROOT = Path(__file__).parents[1]


def test_protocol_schema_and_semantic_registry_validate():
    protocol, identities = load_and_validate_screening_protocol(ROOT)

    assert protocol["identity"]["protocol_status"] == "FROZEN_PRE_SCREENING"
    assert identities["protocol_sha256"]
    assert identities["schema_sha256"]


def test_manifest_contains_exact_frozen_160_units():
    manifest = build_screening_manifest(ROOT)

    assert manifest["dimension_product"] == 160
    assert manifest["expected_units"] == 160
    assert manifest["actual_units"] == 160
    assert manifest["actual_unique_units"] == 160
    assert manifest["missing_units"] == 0
    assert manifest["extra_units"] == 0
    assert manifest["duplicate_units"] == 0
    assert len(manifest["units"]) == EXPECTED_SCREENING_UNIT_COUNT
    assert len({item["unit_id"] for item in manifest["units"]}) == 160


def test_invariant_checks_are_not_an_execution_axis():
    manifest = build_screening_manifest(ROOT)

    axis_product = 1
    for values in manifest["axes"].values():
        axis_product *= len(values)

    assert axis_product == 160
    assert len(manifest["required_invariant_checks"]) == 10
    assert "required_invariant_checks" not in manifest["axes"]


def test_manifest_order_and_digest_are_deterministic():
    first = build_screening_manifest(ROOT)
    second = build_screening_manifest(ROOT)

    assert first == second
    assert first["units"][0]["candidate_or_reference"] == "R-CURRENT"
    assert first["units"][-1]["candidate_or_reference"] == (
        "P-TAPER-NEUTRAL-RATIO-30D"
    )


def test_execution_unit_identity_is_typed_and_deterministic():
    unit = ScreeningExecutionUnit(
        "P-STEP-ZERO",
        "CASE-RETENTION-HIGH",
        "MATCHED_CONTROL_FROM_CASE",
        90,
        0,
        20260716,
        "CANONICAL_SYNTHETIC_COHORT",
    )

    assert unit.unit_id == unit.unit_id
    assert unit.payload()["parameterization"] == "P-STEP-ZERO"
    assert ScreeningExecutionUnit.__dataclass_params__.frozen is True


def test_manifest_validation_rejects_duplicate_accounting():
    manifest = build_screening_manifest(ROOT)
    drifted = copy.deepcopy(manifest)
    drifted["duplicate_units"] = 1

    with pytest.raises(ValueError, match="accounting"):
        validate_screening_manifest(drifted)


def _synthetic_units(manifest):
    units = []
    for definition in manifest["units"]:
        item = {
            **definition,
            "comparison": {
                "baseline_delta": 0.0,
                "context_delta": 0.0,
                "total_delta": 0.0,
                "unexplained_advantage": 0.0,
                "suppression_events": 0,
            },
        }
        units.append(item)
    return units


def test_gate_evaluator_accepts_complete_neutral_evidence(monkeypatch):
    manifest = build_screening_manifest(ROOT)
    units = _synthetic_units(manifest)

    monkeypatch.setattr(
        "gamification_sim.bounded_screening.evaluate_screening_invariants",
        lambda candidate_id: {
            "ordinary_review_unit": 1.0,
            "again_attempt_credit": 0.25,
            "button_direct_reward_neutral": True,
            "session_invariant": True,
            "response_time_positive_reward_absent": True,
            "response_validity_proportional": True,
            "deterministic_replay": True,
            "research_only_classification": True,
        },
    )

    evidence = evaluate_screening_gates(units, manifest=manifest)

    assert evidence["status"] == "COMPLETE"
    assert len(evidence["parameterizations"]) == 4
    assert {item["status"] for item in evidence["parameterizations"]} == {"PASS"}
    assert set(evidence["eligible_parameterizations_by_family"]) == {
        "F-POST-TRANSITION-MG-STEP",
        "F-POST-TRANSITION-MG-TAPER",
    }


def test_gate_evaluator_rejects_endpoint_cap_failure(monkeypatch):
    manifest = build_screening_manifest(ROOT)
    units = _synthetic_units(manifest)
    target = next(
        item
        for item in units
        if item["candidate_or_reference"] == "P-STEP-ZERO"
        and item["policy_pair"] == "CASE-RETENTION-HIGH"
        and item["horizon"] == 365
    )
    target["comparison"]["unexplained_advantage"] = 0.04

    monkeypatch.setattr(
        "gamification_sim.bounded_screening.evaluate_screening_invariants",
        lambda candidate_id: {
            "ordinary_review_unit": 1.0,
            "again_attempt_credit": 0.25,
            "button_direct_reward_neutral": True,
            "session_invariant": True,
            "response_time_positive_reward_absent": True,
            "response_validity_proportional": True,
            "deterministic_replay": True,
            "research_only_classification": True,
        },
    )

    evidence = evaluate_screening_gates(units, manifest=manifest)
    step_zero = next(
        item
        for item in evidence["parameterizations"]
        if item["parameterization_id"] == "P-STEP-ZERO"
    )

    assert step_zero["status"] == "REJECT"
    assert next(
        gate
        for gate in step_zero["gates"]
        if gate["predicate_id"] == "GATE-ENDPOINT-CAP"
    )["status"] == "FAIL"


def test_gate_evaluator_rejects_missing_unit(monkeypatch):
    manifest = build_screening_manifest(ROOT)
    units = _synthetic_units(manifest)[:-1]

    with pytest.raises(ValueError, match="exactly 160"):
        evaluate_screening_gates(units, manifest=manifest)


def test_result_validation_rejects_missing_digest():
    manifest = build_screening_manifest(ROOT)
    payload = {
        "manifest": manifest,
        "units": _synthetic_units(manifest),
        "gate_evidence": {"status": "COMPLETE"},
    }

    with pytest.raises(ValueError, match="digest"):
        validate_bounded_screening_result(payload)


def test_policy_pair_mapping_is_exact_frozen_order():
    assert tuple(CASE_TO_POLICY_PAIR_ID) == (
        "CASE-RETENTION-HIGH",
        "CASE-RETENTION-LOW",
        "CASE-INTENTIONAL-BACKLOG",
        "CASE-HONEST-BACKLOG-RETURN",
    )


def test_public_api_exposes_required_publication_barrier_symbols():
    from gamification_sim import bounded_screening

    assert inspect.isclass(bounded_screening.ScreeningExecutionUnit)
    assert callable(bounded_screening.build_screening_manifest)
    assert callable(bounded_screening.evaluate_screening_gates)
    assert callable(bounded_screening.run_bounded_screening)
