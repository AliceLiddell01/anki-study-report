from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

import pytest
from jsonschema import Draft202012Validator

from gamification_sim.core_economy_screening_v3 import (
    EXPECTED_DIGESTS,
    ScreeningValidationError,
    _enforce_replay,
    _load_artifacts,
    _source_boundary_proof,
    build_manifest,
    build_manifest_schema,
    build_results_schema,
    check_schema_byte_identical,
    evaluate_row,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPOSITORY_ROOT / "research" / "gamification-sim"


@pytest.fixture(scope="module")
def artifacts() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    return _load_artifacts(RESEARCH_ROOT)


def _matrix_row(
    matrix: Mapping[str, Any],
    *,
    bundle_id: str,
    scenario_id: str,
    review_member: str = "P-STEP-ZERO",
    replay_direction: str = "FORWARD",
) -> Mapping[str, Any]:
    matches = [
        row
        for row in matrix["rows"]
        if row["candidate_bundle_id"] == bundle_id
        and row["scenario_id"] == scenario_id
        and row["review_member"] == review_member
        and row["replay_direction"] == replay_direction
    ]
    assert len(matches) == 1
    return matches[0]


def _gate(result: Mapping[str, Any], gate_id: str) -> Mapping[str, Any]:
    matches = [gate for gate in result["gates"] if gate["gate_id"] == gate_id]
    assert len(matches) == 1
    return matches[0]


def _walk_schema(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
        for child in value.values():
            _walk_schema(child)
    elif isinstance(value, list):
        for child in value:
            _walk_schema(child)


def test_frozen_v3_digests_and_strict_schemas_are_exact(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, pipeline, scenarios, matrix = artifacts
    assert {
        "protocol": protocol["identity"]["artifact_digest"],
        "pipeline": pipeline["identity"]["artifact_digest"],
        "scenarios": scenarios["identity"]["artifact_digest"],
        "matrix": matrix["identity"]["artifact_digest"],
    } == EXPECTED_DIGESTS
    for schema in (build_manifest_schema(), build_results_schema()):
        Draft202012Validator.check_schema(schema)
        _walk_schema(schema)
    check_schema_byte_identical(RESEARCH_ROOT)


def test_abrupt_control_expected_failure_is_identity_specific(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    max_row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-ABRUPT-CONTROL",
        scenario_id="SC-FP-MAX-CONTEXT-ANOMALY",
    )
    zero_row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-ABRUPT-CONTROL",
        scenario_id="SC-FP-ZERO-CONTEXT-DENOMINATOR",
    )
    max_result = evaluate_row(max_row, protocol=protocol, scenarios=scenarios)
    zero_result = evaluate_row(zero_row, protocol=protocol, scenarios=scenarios)
    max_gate = _gate(
        max_result,
        "HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED",
    )
    zero_gate = _gate(
        zero_result,
        "HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED",
    )
    assert max_gate["actual_outcome"] == "CONTROL_EXPECTED_FAIL"
    assert max_gate["expected_match"] is True
    assert zero_gate["actual_outcome"] == "PASS"


def test_review_members_use_different_g1_source_outputs_after_day_60(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    results = {}
    for member in ("P-STEP-ZERO", "P-TAPER-ZERO-30D"):
        row = _matrix_row(
            matrix,
            bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
            scenario_id="SC-REVIEW-SOURCE-DAY-61",
            review_member=member,
        )
        result = evaluate_row(row, protocol=protocol, scenarios=scenarios)
        results[member] = result["review_source_trace"][0]["source_output"]
    assert results["P-STEP-ZERO"] != results["P-TAPER-ZERO-30D"]


def test_combined_cap_control_exposes_both_marginality_failures(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    row = _matrix_row(
        matrix,
        bundle_id=(
            "B-PAIR-XD-X-LEARN-LEANING-0_8-1_2-"
            "D-COMBINED-HARD-6-CONTROL"
        ),
        scenario_id="SC-XDOMAIN-BALANCED",
    )
    result = evaluate_row(row, protocol=protocol, scenarios=scenarios)
    assert _gate(
        result,
        "HG-NO-CROSS-DOMAIN-CROWDOUT",
    )["actual_outcome"] == "CONTROL_EXPECTED_FAIL"
    assert _gate(
        result,
        "HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED",
    )["actual_outcome"] == "CONTROL_EXPECTED_FAIL"


def test_forward_reverse_rows_have_the_same_semantic_digest(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    results = [
        evaluate_row(
            _matrix_row(
                matrix,
                bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
                scenario_id="SC-DETERMINISTIC-REPLAY",
                replay_direction=direction,
            ),
            protocol=protocol,
            scenarios=scenarios,
        )
        for direction in ("FORWARD", "REVERSE")
    ]
    assert results[0]["semantic_result_digest"] == results[1]["semantic_result_digest"]
    _enforce_replay(results)


def test_real_user_data_fails_closed_before_evaluation(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    mutated_scenarios = copy.deepcopy(scenarios)
    target = next(
        item
        for item in mutated_scenarios["scenarios"]
        if item["scenario_id"] == "SC-DETERMINISTIC-REPLAY"
    )
    target["ordered_inputs"][0]["metadata"]["real_user_data"] = True
    row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
        scenario_id="SC-DETERMINISTIC-REPLAY",
    )
    with pytest.raises(ScreeningValidationError, match="real user data"):
        evaluate_row(row, protocol=protocol, scenarios=mutated_scenarios)


def test_evaluator_has_no_production_import_boundary() -> None:
    assert _source_boundary_proof(REPOSITORY_ROOT) == "PASS"


def test_run_manifest_binds_publication_head_and_v3_digests(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    _protocol, _pipeline, _scenarios, matrix = artifacts
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    manifest = build_manifest(
        repository_root=REPOSITORY_ROOT,
        implementation_sha=head,
        matrix=matrix,
    )
    Draft202012Validator(build_manifest_schema()).validate(manifest)
    assert manifest["repository"]["publication_sha"]
    assert manifest["repository"]["implementation_sha"] == head
    assert manifest["artifact_digests"] == EXPECTED_DIGESTS
    assert manifest["proofs"]["production_import_boundary"] == "PASS"


@pytest.mark.parametrize("invalid_value", [-0.01, float("inf"), float("nan")])
def test_invalid_contributions_fail_before_a_result_is_returned(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
    invalid_value: float,
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    mutated_scenarios = copy.deepcopy(scenarios)
    target = next(
        item
        for item in mutated_scenarios["scenarios"]
        if item["scenario_id"] == "SC-DETERMINISTIC-REPLAY"
    )
    target["ordered_inputs"][0]["review_units"] = invalid_value
    row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
        scenario_id="SC-DETERMINISTIC-REPLAY",
    )
    with pytest.raises(
        ScreeningValidationError,
        match="finite and nonnegative",
    ):
        evaluate_row(row, protocol=protocol, scenarios=mutated_scenarios)


def test_unsupported_gate_aborts_the_row_instead_of_emitting_partial_success(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    mutated_protocol = copy.deepcopy(protocol)
    gate = next(
        item
        for item in mutated_protocol["hard_gates"]
        if item["gate_id"] == "HG-DETERMINISTIC-REPLAY"
    )
    gate["predicate_ast"]["op"] = "UNSUPPORTED"
    row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
        scenario_id="SC-DETERMINISTIC-REPLAY",
    )
    with pytest.raises(ScreeningValidationError, match="unsupported gate"):
        evaluate_row(row, protocol=mutated_protocol, scenarios=scenarios)


def test_result_is_complete_and_does_not_copy_scenario_metadata(
    artifacts: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    protocol, _pipeline, scenarios, matrix = artifacts
    row = _matrix_row(
        matrix,
        bundle_id="B-INTEGRATED-GRACEFUL-MEDIUM",
        scenario_id="SC-SOURCE-HONEST-AGAIN-NO-DIRECT-PRICE",
    )
    result = evaluate_row(row, protocol=protocol, scenarios=scenarios)
    assert {item["metric_id"] for item in result["metrics"]} == set(
        row["metric_set"]
    )
    assert {item["gate_id"] for item in result["gates"]} == {
        item["gate_id"] for item in row["expected_gate_outcomes"]
    }
    assert all(item["expected_match"] for item in result["gates"])
    serialized = json.dumps(result, sort_keys=True)
    for metadata_key in (
        "answer_button",
        "response_time_ms",
        "time_spent_seconds",
    ):
        assert metadata_key not in serialized
