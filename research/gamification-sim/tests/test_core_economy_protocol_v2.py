from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gamification_sim.core_economy_protocol_v2 import (
    MATRIX_PATH,
    PIPELINE_PATH,
    PROTOCOL_PATH,
    SCENARIOS_PATH,
    apply_cross_domain,
    apply_daily,
    artifact_digest,
    build_all,
    build_schemas,
    check_byte_identical,
    evaluate_false_positive,
    generate_rows,
    nonlinear_aggregate_first_prohibited,
    nonlinear_componentwise_selected,
    run_negative_corpus,
    semantic_validate,
    validate_workspace,
)
from gamification_sim.strict_json import load_strict_json, loads_strict

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
HUMAN_PATH = REPOSITORY_ROOT / "docs/gamification/core-economy-candidate-protocol-v2.md"


def artifacts() -> tuple[dict, dict, dict, dict]:
    return (
        load_strict_json(ROOT / PROTOCOL_PATH, max_bytes=16 * 1024 * 1024),
        load_strict_json(ROOT / PIPELINE_PATH, max_bytes=16 * 1024 * 1024),
        load_strict_json(ROOT / SCENARIOS_PATH, max_bytes=32 * 1024 * 1024),
        load_strict_json(ROOT / MATRIX_PATH, max_bytes=64 * 1024 * 1024),
    )


def test_valid_canonical_v2_artifacts_and_human_parity() -> None:
    summary = validate_workspace(ROOT, repository_root=REPOSITORY_ROOT)
    assert summary == {
        "protocol_digest": "3db6a7399d8e0d95e1625585c0c191eb4e298ea5427be7f52bcaa5f27bbde001",
        "pipeline_digest": "c00a51aafa0fd6a092677cbbf25475a6e722062ab848509c977b0759121f231a",
        "scenario_digest": "857503cf63e8a700f774e9e4b40bcc9b90b3abfda716c682be7efd97416c78be",
        "matrix_digest": "41e68fdfad8590d7fb9a9d763039573f903741b21292caa75e98c359170ea55e",
        "candidate_count": 19,
        "bundle_count": 21,
        "hypothesis_count": 20,
        "gate_count": 29,
        "metric_count": 22,
        "scenario_count": 32,
        "row_count": 720,
        "negative_sample_count": 40,
        "negative_samples": 40,
        "negative_corpus": "PASS",
    }


def test_schema_self_check_and_exact_inventory_bounds() -> None:
    generated = build_all()
    schemas = build_schemas(generated)
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(generated[name])
    assert schemas["protocol"]["properties"]["candidate_registry"]["minItems"] == 19
    assert schemas["protocol"]["properties"]["candidate_registry"]["maxItems"] == 19
    assert schemas["scenarios"]["properties"]["scenarios"]["minItems"] == 32
    assert schemas["matrix"]["properties"]["rows"]["maxItems"] == 720


def test_deterministic_byte_identical_regeneration_and_digests() -> None:
    first = build_all()
    second = build_all()
    assert first == second
    for value in first.values():
        assert value["identity"]["artifact_digest"] == artifact_digest(value)
    check_byte_identical(ROOT)


def test_false_positive_context_metric_differentiates_control() -> None:
    abrupt = evaluate_false_positive(0.32, 1.32, 0.0)
    stepped = evaluate_false_positive(0.32, 1.32, 0.75)
    assert abrupt == {
        "lost_positive_context": 0.32,
        "context_loss_ratio": 1.0,
        "total_immediate_loss_ratio": pytest.approx(0.242424242424),
    }
    assert stepped["context_loss_ratio"] == 0.25
    assert stepped["total_immediate_loss_ratio"] == pytest.approx(0.060606060606)
    zero_context = evaluate_false_positive(0.0, 1.0, 0.0)
    assert zero_context["context_loss_ratio"] == 0.0


def test_candidate_specific_gate_profile_is_matrix_source_of_truth() -> None:
    protocol, pipeline, scenarios, matrix = artifacts()
    scenario = next(item for item in scenarios["scenarios"] if item["scenario_id"] == "SC-FP-MAX-CONTEXT-ANOMALY")
    assert "expected_hard_gate_outcomes" not in scenario
    abrupt_row = next(
        row for row in matrix["rows"]
        if row["scenario_id"] == scenario["scenario_id"]
        and row["candidate_bundle_id"] == "B-INTEGRATED-ABRUPT-CONTROL"
        and row["review_member"] == "P-STEP-ZERO"
        and row["replay_direction"] == "FORWARD"
    )
    graceful_row = next(
        row for row in matrix["rows"]
        if row["scenario_id"] == scenario["scenario_id"]
        and row["candidate_bundle_id"] == "B-INTEGRATED-GRACEFUL-MEDIUM"
        and row["review_member"] == "P-STEP-ZERO"
        and row["replay_direction"] == "FORWARD"
    )
    abrupt_outcome = {item["gate_id"]: item["expected_outcome"] for item in abrupt_row["expected_gate_outcomes"]}
    graceful_outcome = {item["gate_id"]: item["expected_outcome"] for item in graceful_row["expected_gate_outcomes"]}
    assert abrupt_outcome["HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED"] == "CONTROL_EXPECTED_FAIL"
    assert graceful_outcome["HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED"] == "PASS"
    assert generate_rows(protocol, pipeline, scenarios) == matrix["rows"]


def test_cross_domain_marginality_decomposition_and_control_crowdout() -> None:
    protocol, _, _, _ = artifacts()
    candidates = {item["candidate_id"]: item for item in protocol["candidate_registry"]}
    conversion = candidates["X-EQUALIZED-1_0-1_0"]
    medium = apply_daily(5.0, 1.0, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    base = apply_cross_domain(medium["review_bounded"], 0.0, conversion, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    plus_learn = apply_cross_domain(medium["review_bounded"], medium["learn_bounded"], conversion, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    assert plus_learn["total_npu"] > base["total_npu"]
    assert plus_learn["review_component"] == 5.0
    assert plus_learn["learn_component"] == 1.0
    control = apply_daily(100.0, 0.0, "D-COMBINED-HARD-6-CONTROL")
    saturated = apply_cross_domain(control["review_bounded"], control["learn_bounded"], conversion, "D-COMBINED-HARD-6-CONTROL")
    with_added_learn = apply_cross_domain(control["review_bounded"], 1.0, conversion, "D-COMBINED-HARD-6-CONTROL")
    assert saturated["total_npu"] == 6.0
    assert with_added_learn["total_npu"] == 6.0
    assert with_added_learn["learn_component"] > 0
    assert with_added_learn["review_component"] < saturated["review_component"]


def test_per_domain_cap_scale_and_session_neutral_inputs() -> None:
    low = apply_daily(5.0, 1.0, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    normal = apply_daily(10.0, 5.0, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    intensive = apply_daily(100.0, 30.0, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    extreme = apply_daily(300.0, 30.0, "D-PER-DOMAIN-PIECEWISE-MEDIUM")
    assert low["review_bounded"] == 5.0
    assert low["learn_bounded"] == 1.0
    assert normal["review_bounded"] < intensive["review_bounded"] < extreme["review_bounded"]
    assert intensive["review_bounded"] > 0
    assert extreme["review_bounded"] < 300.0
    high = apply_daily(300.0, 30.0, "D-PER-DOMAIN-SQRT-HIGH")
    assert 30.0 < high["review_bounded"] <= 60.0
    assert 5.0 < high["learn_bounded"] <= 20.0


def test_operator_order_is_typed_deterministic_and_distinct() -> None:
    _, pipeline, _, _ = artifacts()
    assert [step["ordinal"] for step in pipeline["steps"]] == list(range(1, 18))
    assert pipeline["operator_order_resolution"]["selected"] == "NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY"
    selected = nonlinear_componentwise_selected(1.0, 0.32, 0.75)
    prohibited = nonlinear_aggregate_first_prohibited(1.0, 0.32, 0.75)
    assert selected != prohibited
    assert selected > prohibited


def test_matrix_exactness_review_pair_and_no_results() -> None:
    protocol, pipeline, scenarios, matrix = artifacts()
    assert matrix["row_count"] == len(matrix["rows"]) == 720
    assert len({row["row_id"] for row in matrix["rows"]}) == 720
    assert matrix["coverage"]["missing"] == matrix["coverage"]["extra"] == matrix["coverage"]["duplicates"] == 0
    scenario_map = {item["scenario_id"]: item for item in scenarios["scenarios"]}
    for row in matrix["rows"]:
        assert row["result_status"] == "NOT_RUN"
        assert row["result"] == "NOT_AVAILABLE"
        required = scenario_map[row["scenario_id"]]["axis_mapping"]["review_pair_required"]
        assert (row["review_member"] in {"P-STEP-ZERO", "P-TAPER-ZERO-30D"}) if required else (row["review_member"] == "NOT_APPLICABLE")
    semantic_validate(protocol, pipeline, scenarios, matrix, human_text=HUMAN_PATH.read_text(encoding="utf-8"))


def test_strict_json_duplicate_key_and_nonfinite_rejection() -> None:
    with pytest.raises(Exception, match="duplicate object key"):
        loads_strict('{"a":1,"a":2}')
    with pytest.raises(Exception, match="non-standard JSON number"):
        loads_strict('{"value":NaN}')


def test_versioned_negative_corpus_executes_all_40_samples() -> None:
    assert run_negative_corpus(ROOT, REPOSITORY_ROOT) == {
        "negative_samples": 40,
        "negative_corpus": "PASS",
    }


def test_research_only_module_has_no_production_or_remote_imports() -> None:
    source = (ROOT / "src/gamification_sim/core_economy_protocol_v2.py").read_text(encoding="utf-8")
    for fragment in (
        "anki_study_report",
        "aqt",
        "anki.collection",
        "sqlite3",
        "requests",
        "httpx",
        "socket",
        "subprocess",
    ):
        assert fragment not in source
    protocol, pipeline, scenarios, matrix = artifacts()
    assert protocol["production_flags"]["g4_4_started"] is False
    assert pipeline["production_flags"]["g4_4_started"] is False
    assert scenarios["g4_4_started"] is False
    assert matrix["g4_4_started"] is False
