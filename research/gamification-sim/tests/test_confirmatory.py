from __future__ import annotations

from copy import deepcopy


from gamification_sim.canonical_json import canonical_digest
from gamification_sim.confirmatory import (
    EXPECTED_GATE_IDS,
    EXPECTED_TOTAL_UNITS,
    build_confirmatory_manifest,
    evaluate_confirmatory_gates,
    load_and_validate_confirmatory_protocol,
    validate_confirmatory_manifest,
)
from gamification_sim.workspace import resolve_research_workspace


def _passing_result(item: dict) -> dict:
    component = item["component"]
    if component == "CORE_LONGITUDINAL":
        payload = {
            "component": component,
            "variant_id": item["variant_id"],
            "policy_pair": item["policy_pair"],
            "horizon": item["horizon"],
            "replica": item["replica"],
            "seed": item["seed"],
            "model_condition": item["model_condition"],
            "cohort_size": 20,
            "pair_definition": {},
            "left": {},
            "right": {},
            "comparison": {
                "baseline_delta": 0.0,
                "context_delta": 0.0,
                "total_delta": 0.0,
                "unexplained_advantage": 0.0,
                "suppression_events": 0,
                "left_baseline_preservation": 1.0,
                "right_baseline_preservation": 1.0,
            },
        }
    elif component == "PERSONA_SAFETY":
        payload = {
            "component": component,
            "variant_id": item["variant_id"],
            "persona_id": item["persona_id"],
            "seed": item["seed"],
            "derived_seed": 1,
            "window_start_day": 60,
            "window_end_day": 89,
            "day_count": 30,
            "mean_total_review_units": 1.0,
            "min_total_review_units": 0.0,
            "max_total_review_units": 2.0,
            "baseline_preservation_ratio": 1.0,
            "suppression_events": 0,
            "gate_failures": [],
            "history_digest": "0" * 64,
        }
    else:
        observed = True
        if item["probe_id"] == "INV-ORDINARY-UNIT":
            observed = 1.0
        elif item["probe_id"] == "INV-AGAIN-CREDIT":
            observed = 0.25
        payload = {
            "component": component,
            "variant_id": item["variant_id"],
            "probe_id": item["probe_id"],
            "passed": True,
            "observed": observed,
        }
    return {
        "unit_id": item["unit_id"],
        **{key: item[key] for key in (
            "component",
            "variant_id",
            "parameterization",
            "replay_id",
            "policy_pair",
            "horizon",
            "replica",
            "seed",
            "model_condition",
            "persona_id",
            "probe_id",
        )},
        "result_payload": payload,
        "result_digest": canonical_digest(payload),
    }


def test_confirmatory_protocol_and_manifest_are_exact():
    workspace = resolve_research_workspace()
    protocol, identities = load_and_validate_confirmatory_protocol(workspace)
    manifest = build_confirmatory_manifest(workspace)
    validate_confirmatory_manifest(manifest)

    assert protocol["protocol_status"] == "FROZEN_PRE_RESULTS"
    assert protocol["eligible_variants"] == [
        "R-CURRENT",
        "P-STEP-ZERO",
        "P-TAPER-ZERO-30D",
    ]
    assert not set(protocol["eligible_variants"]) & set(
        protocol["rejected_variants"]
    )
    assert identities["schema_draft"] == (
        "https://json-schema.org/draft/2020-12/schema"
    )
    assert manifest["expected_units"] == EXPECTED_TOTAL_UNITS
    assert manifest["actual_unique_units"] == EXPECTED_TOTAL_UNITS
    assert manifest["component_counts"] == {
        "CORE_LONGITUDINAL": 576,
        "PERSONA_SAFETY": 192,
        "INVARIANT_ABUSE_PROBE": 72,
    }
    assert len({item["unit_id"] for item in manifest["units"]}) == 840


def test_confirmatory_gate_evaluator_uses_only_allowed_outcomes():
    workspace = resolve_research_workspace()
    manifest = build_confirmatory_manifest(workspace)
    results = [_passing_result(item) for item in manifest["units"]]

    evidence = evaluate_confirmatory_gates(results, manifest=manifest)

    assert evidence["ranking_performed"] is False
    assert evidence["final_candidate_selected"] is False
    assert [item["outcome"] for item in evidence["outcomes"]] == [
        "CONFIRMATORY_ELIGIBLE",
        "CONFIRMATORY_ELIGIBLE",
    ]
    assert all(
        tuple(gate["predicate_id"] for gate in item["gates"])
        == EXPECTED_GATE_IDS
        for item in evidence["outcomes"]
    )


def test_confirmatory_gate_evaluator_rejects_positive_growth():
    workspace = resolve_research_workspace()
    manifest = build_confirmatory_manifest(workspace)
    results = [_passing_result(item) for item in manifest["units"]]

    target = next(
        item
        for item in results
        if item["variant_id"] == "P-STEP-ZERO"
        and item["component"] == "CORE_LONGITUDINAL"
        and item["replay_id"] == "PRIMARY"
        and item["policy_pair"] == "retention-high-cycle"
        and item["horizon"] == 365
        and item["replica"] == 0
        and item["seed"] == 5978107021558220631
        and item["model_condition"] == "MODEL-NATIVE-COHORT"
    )
    target["result_payload"]["comparison"]["unexplained_advantage"] = 0.1
    target["result_digest"] = canonical_digest(target["result_payload"])
    replay = next(
        item
        for item in results
        if item["variant_id"] == target["variant_id"]
        and item["component"] == target["component"]
        and item["replay_id"] == "SAME_INPUT_REPLAY"
        and item["policy_pair"] == target["policy_pair"]
        and item["horizon"] == target["horizon"]
        and item["replica"] == target["replica"]
        and item["seed"] == target["seed"]
        and item["model_condition"] == target["model_condition"]
    )
    replay["result_payload"] = deepcopy(target["result_payload"])
    replay["result_digest"] = target["result_digest"]

    evidence = evaluate_confirmatory_gates(results, manifest=manifest)
    step = next(
        item
        for item in evidence["outcomes"]
        if item["parameterization_id"] == "P-STEP-ZERO"
    )
    assert step["outcome"] == "CONFIRMATORY_NOT_ELIGIBLE"
    assert next(
        gate
        for gate in step["gates"]
        if gate["predicate_id"] == "GATE-ENDPOINT-CAP"
    )["status"] == "FAIL"




def test_confirmatory_manifest_is_deterministic():
    workspace = resolve_research_workspace()
    first = build_confirmatory_manifest(workspace)
    second = build_confirmatory_manifest(workspace)
    assert first == second
    assert first["manifest_digest"] == second["manifest_digest"]


def test_confirmatory_replay_mismatch_is_not_eligible():
    workspace = resolve_research_workspace()
    manifest = build_confirmatory_manifest(workspace)
    results = [_passing_result(item) for item in manifest["units"]]
    replay = next(
        item
        for item in results
        if item["variant_id"] == "P-TAPER-ZERO-30D"
        and item["component"] == "PERSONA_SAFETY"
        and item["replay_id"] == "SAME_INPUT_REPLAY"
    )
    replay["result_payload"]["mean_total_review_units"] = 2.0
    replay["result_digest"] = canonical_digest(replay["result_payload"])

    evidence = evaluate_confirmatory_gates(results, manifest=manifest)
    taper = next(
        item
        for item in evidence["outcomes"]
        if item["parameterization_id"] == "P-TAPER-ZERO-30D"
    )
    assert taper["outcome"] == "CONFIRMATORY_NOT_ELIGIBLE"
    assert next(
        gate
        for gate in taper["gates"]
        if gate["predicate_id"] == "GATE-DETERMINISTIC-REPLAY"
    )["status"] == "FAIL"
