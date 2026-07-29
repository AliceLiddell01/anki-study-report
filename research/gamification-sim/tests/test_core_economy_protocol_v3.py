from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gamification_sim.core_economy_protocol_v3 import (
    HISTORICAL_SHA256,
    LEARN_LIMITATION,
    ProtocolValidationError,
    _bundle_candidates,
    _expected_gate_outcome,
    _refresh_negative_artifacts,
    _uncertainty_transition_table,
    apply_daily,
    build_all,
    build_negative_corpus,
    build_schemas,
    check_byte_identical,
    evaluate_review_source,
    evaluate_uncertainty_transition,
    generate_rows,
    semantic_validate,
    validate_historical_immutability,
    validate_workspace,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPOSITORY_ROOT / "research" / "gamification-sim"
HUMAN_PATH = REPOSITORY_ROOT / "docs" / "gamification" / "core-economy-candidate-protocol-v3.md"


def test_v3_artifacts_are_strict_schema_valid_and_semantically_valid() -> None:
    artifacts = build_all()
    schemas = build_schemas(artifacts)
    for name, artifact in artifacts.items():
        Draft202012Validator.check_schema(schemas[name])
        Draft202012Validator(schemas[name]).validate(artifact)
    semantic_validate(
        artifacts["protocol"],
        artifacts["pipeline"],
        artifacts["scenarios"],
        artifacts["matrix"],
    )


def test_uncertainty_transition_table_is_total_and_deterministic() -> None:
    table = _uncertainty_transition_table()
    covered = {(row["current_state"], row["signal"]) for row in table}
    assert covered == {
        (state, signal)
        for state in ("NORMAL", "WATCH", "RESTRICTED", "RECOVERING")
        for signal in ("NORMAL", "ISOLATED_ANOMALY", "CONFLICT", "MISSING")
    }
    state = "NORMAL"
    history: list[str] = []
    trace = []
    for signal in ("CONFLICT", "CONFLICT", "NORMAL", "NORMAL"):
        item = evaluate_uncertainty_transition(state, signal, history)
        trace.append(item)
        history.append(signal)
        state = item["next_state"]
    assert [item["next_state"] for item in trace] == [
        "WATCH",
        "RESTRICTED",
        "RECOVERING",
        "NORMAL",
    ]
    assert trace == [
        evaluate_uncertainty_transition(
            ("NORMAL", "WATCH", "RESTRICTED", "RECOVERING")[index],
            signal,
            list(("CONFLICT", "CONFLICT", "NORMAL", "NORMAL")[:index]),
        )
        for index, signal in enumerate(("CONFLICT", "CONFLICT", "NORMAL", "NORMAL"))
    ]


def test_uncertainty_missing_holds_and_invalid_values_fail_closed() -> None:
    held = evaluate_uncertainty_transition("RESTRICTED", None, ["CONFLICT"])
    assert held["next_state"] == "RESTRICTED"
    assert held["applied_multiplier"] == 0.5
    assert held["state_write_timing"] == "NO_WRITE_HOLD"
    with pytest.raises(ProtocolValidationError, match="UNCERTAINTY_UNKNOWN_STATE"):
        evaluate_uncertainty_transition("UNKNOWN", "NORMAL")
    with pytest.raises(ProtocolValidationError, match="UNCERTAINTY_UNKNOWN_SIGNAL"):
        evaluate_uncertainty_transition("NORMAL", "UNKNOWN")


@pytest.mark.parametrize(
    ("day", "step_multiplier", "taper_multiplier"),
    [
        (59, 1.0, 1.0),
        (60, 0.0, 1.0),
        (61, 0.0, 29 / 30),
        (75, 0.0, 0.5),
        (89, 0.0, 1 / 30),
        (90, 0.0, 0.0),
        (91, 0.0, 0.0),
    ],
)
def test_review_source_uses_exact_g1_boundaries(
    day: int,
    step_multiplier: float,
    taper_multiplier: float,
) -> None:
    step = evaluate_review_source(
        "P-STEP-ZERO",
        day=day,
        verified_base=1.0,
        positive_context=0.32,
    )
    taper = evaluate_review_source(
        "P-TAPER-ZERO-30D",
        day=day,
        verified_base=1.0,
        positive_context=0.32,
    )
    assert step["memory_gain_multiplier"] == pytest.approx(step_multiplier)
    assert taper["memory_gain_multiplier"] == pytest.approx(taper_multiplier)
    assert step["verified_base"] == taper["verified_base"] == 1.0


def test_matrix_rows_contain_member_specific_source_traces() -> None:
    artifacts = build_all()
    rows = [
        row
        for row in artifacts["matrix"]["rows"]
        if row["scenario_id"] == "SC-REVIEW-SOURCE-DAY-61"
    ]
    by_member = {
        row["review_member"]: row["review_source_trace"]["source_output"]
        for row in rows
        if row["candidate_bundle_id"] == "B-INTEGRATED-GRACEFUL-MEDIUM"
        and row["replay_direction"] == "FORWARD"
    }
    assert set(by_member) == {"P-STEP-ZERO", "P-TAPER-ZERO-30D"}
    assert by_member["P-STEP-ZERO"] != by_member["P-TAPER-ZERO-30D"]


def test_expected_outcomes_use_candidate_scenario_gate_identity() -> None:
    artifacts = build_all()
    protocol = artifacts["protocol"]
    scenarios = {
        item["scenario_id"]: item
        for item in artifacts["scenarios"]["scenarios"]
    }
    bundles = {
        item["candidate_bundle_id"]: item
        for item in protocol["candidate_bundles"]
    }
    abrupt = bundles["B-INTEGRATED-ABRUPT-CONTROL"]
    max_context = _expected_gate_outcome(
        abrupt,
        scenarios["SC-FP-MAX-CONTEXT-ANOMALY"],
        "HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED",
    )
    zero_context = _expected_gate_outcome(
        abrupt,
        scenarios["SC-FP-ZERO-CONTEXT-DENOMINATOR"],
        "HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED",
    )
    assert max_context["expected_outcome"] == "CONTROL_EXPECTED_FAIL"
    assert zero_context["expected_outcome"] == "PASS"
    assert generate_rows(protocol, artifacts["pipeline"], artifacts["scenarios"]) == artifacts["matrix"]["rows"]


def test_every_declared_metric_and_gate_has_exact_matrix_coverage() -> None:
    artifacts = build_all()
    protocol = artifacts["protocol"]
    rows = artifacts["matrix"]["rows"]
    assert {
        metric
        for row in rows
        for metric in row["metric_set"]
    } == {item["metric_id"] for item in protocol["metrics"]}
    assert {
        outcome["gate_id"]
        for row in rows
        for outcome in row["expected_gate_outcomes"]
    } == {item["gate_id"] for item in protocol["hard_gates"]}
    cumulative_rows = [
        row for row in rows if "M-FALSE-POSITIVE-CUMULATIVE-LOSS" in row["metric_set"]
    ]
    assert {
        row["scenario_id"] for row in cumulative_rows
    } >= {
        "SC-FP-RECOVERY",
        "SC-FP-REPEATED-CONFLICT",
        "SC-FP-MULTIDAY-LEGITIMATE",
    }


def test_daily_medium_candidate_is_mathematically_bounded() -> None:
    for scale in (1_000.0, 10_000.0, 1_000_000.0):
        result = apply_daily(scale, scale, "D-PER-DOMAIN-BOUNDED-MEDIUM")
        assert result["review_bounded"] == 34.0
        assert result["learn_bounded"] == 10.0
        assert all(math.isfinite(value) for value in result.values())
    with pytest.raises(ProtocolValidationError, match="NONFINITE_CONTRIBUTION"):
        apply_daily(math.inf, 1.0, "D-PER-DOMAIN-BOUNDED-MEDIUM")
    with pytest.raises(ProtocolValidationError, match="NEGATIVE_CONTRIBUTION"):
        apply_daily(-1.0, 1.0, "D-PER-DOMAIN-BOUNDED-MEDIUM")


def test_marginality_gate_requires_both_domain_metrics() -> None:
    artifacts = build_all()
    gate = next(
        item
        for item in artifacts["protocol"]["hard_gates"]
        if item["gate_id"] == "HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED"
    )
    assert gate["required_metric_ids"] == [
        "M-REVIEW-MARGINAL-CONTRIBUTION",
        "M-LEARN-MARGINAL-CONTRIBUTION",
    ]


def test_inventory_sets_are_exactly_covered() -> None:
    artifacts = build_all()
    protocol = artifacts["protocol"]
    rows = artifacts["matrix"]["rows"]
    bundles = {
        item["candidate_bundle_id"]: item
        for item in protocol["candidate_bundles"]
    }
    assert {row["candidate_bundle_id"] for row in rows} == set(bundles)
    assert {
        candidate_id
        for row in rows
        for candidate_id in _bundle_candidates(bundles[row["candidate_bundle_id"]]).values()
    } == {item["candidate_id"] for item in protocol["candidate_registry"]}
    assert all(row["learn_limitation"] == LEARN_LIMITATION for row in rows)


def test_no_results_boundary_is_fail_closed() -> None:
    artifacts = build_all()
    assert artifacts["protocol"]["governance"]["results"] == "NOT_AVAILABLE"
    assert artifacts["scenarios"]["results"] == "NOT_AVAILABLE"
    assert artifacts["matrix"]["results"] == "NOT_AVAILABLE"
    assert all(row["result_status"] == "NOT_RUN" for row in artifacts["matrix"]["rows"])
    mutated = copy.deepcopy(artifacts)
    mutated["matrix"]["rows"][0]["result_status"] = "COMPLETE"
    _refresh_negative_artifacts(mutated)
    with pytest.raises(ProtocolValidationError, match="RESULT_STATUS"):
        semantic_validate(
            mutated["protocol"],
            mutated["pipeline"],
            mutated["scenarios"],
            mutated["matrix"],
        )


def test_historical_v1_v2_and_source_identities_are_immutable() -> None:
    assert len(HISTORICAL_SHA256) >= 17
    validate_historical_immutability(RESEARCH_ROOT)


def test_generated_workspace_and_negative_corpus_are_reproducible() -> None:
    assert build_negative_corpus()["identity"]["version"] == 3
    check_byte_identical(RESEARCH_ROOT)
    summary = validate_workspace(RESEARCH_ROOT, repository_root=REPOSITORY_ROOT)
    assert summary["negative_corpus"] == "PASS"
    assert summary["negative_sample_count"] == len(build_negative_corpus()["samples"])
    assert "G4.3 v3: `FROZEN_PRE_SCREENING`" in HUMAN_PATH.read_text(encoding="utf-8")
