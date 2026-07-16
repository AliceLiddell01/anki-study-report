from __future__ import annotations

import json
from dataclasses import replace

import pytest

from gamification_sim.parameter_catalog import (
    PARAMETER_CANDIDATES,
    candidate_payload,
    compose_parameter_candidates,
    parameter_candidate,
)
from gamification_sim.parameters import CURRENT_PARAMETERS
from gamification_sim.evidence import CandidateStatus, MetricStatus, measured
from gamification_sim.strict_json import StrictJsonError
from gamification_sim.sweep import (
    SENSITIVITY_GRIDS,
    _metrics,
    _quantitative_failures,
    count_baseline_suppressions,
    evaluate_candidate,
    load_sweep_config,
    run_sensitivity,
    run_sweep,
    pareto_front,
    write_sweep_reports,
)
from gamification_sim.scenario_runner import run_corpus


ROOT = __import__("pathlib").Path(__file__).parents[1]
CONFIG = ROOT / "configs" / "review-sweep-v0.1.json"


def test_candidate_catalog_is_unique_complete_and_does_not_mutate_baseline():
    identifiers = [item.parameter_set_id for item in PARAMETER_CANDIDATES]
    assert len(identifiers) == len(set(identifiers)) == 17
    assert CURRENT_PARAMETERS.rule_version == "review-v0.1"
    for candidate in PARAMETER_CANDIDATES:
        payload = candidate_payload(candidate)
        assert payload["parameter_snapshot"]
        assert len(payload["digest"]) == 64
        assert candidate.digest == candidate_payload(candidate)["digest"]


def test_composite_applies_only_explicit_changed_fields():
    composite = compose_parameter_candidates(
        (parameter_candidate("R-NO-GAIN"), parameter_candidate("V-LOW-CAP"))
    )
    assert composite.parameters.memory_gain_cap == 0
    assert composite.parameters.volume_cap == 10
    assert composite.parameters.completion_cap == CURRENT_PARAMETERS.completion_cap


def test_load_sweep_config_resolves_bounded_local_corpus():
    config = load_sweep_config(CONFIG, ROOT)
    assert config.corpus_root == (ROOT / "scenarios").resolve()
    assert config.max_evaluated_candidates == 48


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda value: value.update(corpus_path="https://example.invalid/scenarios"), "does not match"),
        (lambda value: value.update(corpus_path="../scenarios"), "does not match"),
        (lambda value: value.update(max_evaluated_candidates=16), "less than the minimum"),
        (lambda value: value.update(unexpected=True), "Additional properties"),
    ],
)
def test_sweep_config_rejects_unsafe_or_unbounded_contract(tmp_path, mutation, message):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutation(payload)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_sweep_config(path, ROOT)


def test_sweep_config_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"sweep_version":"review-sweep-v0.1","sweep_version":"other"}', encoding="utf-8")
    with pytest.raises(StrictJsonError, match="duplicate object key"):
        load_sweep_config(path, ROOT)


@pytest.fixture(scope="module")
def sweep_payload():
    return run_sweep(load_sweep_config(CONFIG, ROOT), ROOT)


def test_sequential_sweep_is_bounded_deterministic_and_pareto_only(sweep_payload):
    repeated = run_sweep(load_sweep_config(CONFIG, ROOT), ROOT)
    assert sweep_payload["manifest"]["output_digest"] == repeated["manifest"]["output_digest"]
    assert sweep_payload["manifest"]["evaluated_candidate_count"] <= 48
    assert [stage["family"] for stage in sweep_payload["stages"]] == [
        "reward", "volume", "completion", "support", "supplemental"
    ]
    assert "no aggregate score" in sweep_payload["manifest"]["selection_method"]
    by_id = {item["parameter_set"]["parameter_set_id"]: item for item in sweep_payload["candidates"]}
    assert by_id["R-CURRENT"]["hard_gate_pass"] is True
    assert all(item["status"] == CandidateStatus.PASS.value for item in sweep_payload["candidates"])
    assert all(all(item["hard_invariants"].values()) for item in sweep_payload["candidates"])
    assert all(by_id[item]["hard_gate_pass"] for item in sweep_payload["pareto"]["candidate_ids"])
    assert all(item["rejection_reason_codes"] for item in sweep_payload["candidates"] if not item["hard_gate_pass"])
    pareto_digests = {
        by_id[item]["parameter_set"]["normalized_parameter_digest"]
        for item in sweep_payload["pareto"]["candidate_ids"]
    }
    assert len(pareto_digests) == len(sweep_payload["pareto"]["candidate_ids"])


def test_current_only_regressions_do_not_reject_alternative_candidate():
    config = load_sweep_config(CONFIG, ROOT)
    evaluation = evaluate_candidate(parameter_candidate("R-NO-GAIN"), config, ROOT)
    assert "SCENARIO_ASSERTION_FAILURE" not in evaluation.rejection_reason_codes


def test_valid_sensitivity_boundary_is_rejected_by_expected_quantitative_gate():
    base = parameter_candidate("R-CURRENT")
    params = replace(
        base.parameters,
        attempt_credit=0.15,
        rule_version="review-v0.1+test-rejected-attempt-boundary",
    )
    candidate = replace(
        base,
        parameter_set_id="TEST-REJECTED-ATTEMPT-BOUNDARY",
        rule_version=params.rule_version,
        family="sensitivity-boundary",
        rationale="Prove that a valid parameter contract can fail a measured gate.",
        changed_fields=("attempt_credit",),
        parameters=params,
    )
    evaluation = evaluate_candidate(candidate, load_sweep_config(CONFIG, ROOT), ROOT)
    assert evaluation.status is CandidateStatus.REJECT
    assert evaluation.quantitative_gate_failures == ("Q01_ORDINARY_MEDIAN",)
    assert all(dict(evaluation.hard_invariants).values())


def test_placeholder_metrics_are_replaced_with_typed_evidence():
    evaluation = evaluate_candidate(
        parameter_candidate("R-CURRENT"),
        load_sweep_config(CONFIG, ROOT),
        ROOT,
    )
    metrics = dict(evaluation.metrics)
    assert metrics["collection_size_parity"].status is MetricStatus.DERIVED
    assert metrics["low_confidence_parity"].status is MetricStatus.MEASURED
    assert metrics["high_low_retention_parity"].status is MetricStatus.MEASURED
    assert metrics["long_session_baseline_ratio"].status is MetricStatus.MEASURED
    assert metrics["retention_cycling_advantage"].status is MetricStatus.MEASURED
    assert metrics["honest_baseline_suppression_events"].status is MetricStatus.MEASURED
    assert evaluation.status is CandidateStatus.PASS
    assert not evaluation.incomplete_evidence_reason_codes
    assert all(metric.source_ids for metric in metrics.values())


def test_missing_longitudinal_input_is_explicitly_unavailable():
    candidate = parameter_candidate("R-CURRENT")
    result = run_corpus(
        ROOT / "scenarios",
        command="test-missing-longitudinal",
        params=candidate.parameters,
        parameter_set_id=candidate.parameter_set_id,
    )
    metrics = _metrics(result, ROOT, candidate.parameters)
    assert metrics["high_low_retention_parity"].status is MetricStatus.UNSUPPORTED
    assert metrics["backlog_return_viability"].status is MetricStatus.DEFERRED


def test_measured_volume_and_completion_caps_detect_invalid_observation():
    candidate = parameter_candidate("R-CURRENT")
    evaluation = evaluate_candidate(candidate, load_sweep_config(CONFIG, ROOT), ROOT)
    metrics = dict(evaluation.metrics)
    metrics["max_observed_volume_credit"] = measured(
        "max_observed_volume_credit",
        candidate.parameters.volume_cap + 1,
        unit="Review Units",
        sample_count=1,
        source_ids=("constructed-cap-breach",),
        method="constructed invalid observation",
    )
    metrics["max_observed_completion_credit"] = measured(
        "max_observed_completion_credit",
        candidate.parameters.completion_cap + 1,
        unit="Review Units",
        sample_count=1,
        source_ids=("constructed-cap-breach",),
        method="constructed invalid observation",
    )
    failures = _quantitative_failures(metrics, candidate.parameters)
    assert "Q06_VOLUME_CAP" in failures
    assert "Q07_COMPLETION_CAP" in failures


def test_baseline_suppression_counter_detects_constructed_suppression():
    assert count_baseline_suppressions(((0.9, 0.9), (0.89, 0.9))) == 1


def test_incomplete_candidate_is_not_a_final_pareto_winner():
    evaluation = evaluate_candidate(
        parameter_candidate("R-CURRENT"),
        load_sweep_config(CONFIG, ROOT),
        ROOT,
    )
    incomplete = replace(
        evaluation,
        status=CandidateStatus.INCOMPLETE_EVIDENCE,
        incomplete_evidence_reason_codes=("CONSTRUCTED_MISSING_EVIDENCE",),
    )
    assert pareto_front((incomplete,)) == ()
    assert pareto_front((incomplete,), include_incomplete=True) == (incomplete,)


def test_sweep_writes_complete_gitignored_report_set(tmp_path, sweep_payload):
    run_dir = write_sweep_reports(sweep_payload, tmp_path)
    assert {item.name for item in run_dir.iterdir()} == {
        "manifest.json", "candidates.json", "metrics.csv", "summary.md", "pareto.json"
    }


def test_sensitivity_uses_explicit_grids_and_reports_cliff_triplets():
    payload = run_sensitivity(load_sweep_config(CONFIG, ROOT), ROOT, "R-CURRENT")
    assert len(payload["parameters"]) == len(SENSITIVITY_GRIDS) == 13
    assert payload["reward_cliffs"]
    for probe in payload["reward_cliffs"]:
        assert len(probe["tested_values"]) == 3
        assert probe["tested_values"] == sorted(probe["tested_values"])
    for analysis in payload["parameters"]:
        for point in analysis["points"]:
            assert point["invariant_status"] == "PASS"
            assert point["quantitative_gate_status"] in {"PASS", "FAIL"}
            assert point["reward_cliff_status"] in {"PASS", "BOUNDED_PIECEWISE"}
            assert point["evidence_completeness"] == "COMPLETE"
            assert len(point["longitudinal_metric_deltas"]) == 5
            assert len(point["longitudinal_digest"]) == 64
    assert payload["manifest"]["output_digest"] == run_sensitivity(
        load_sweep_config(CONFIG, ROOT), ROOT, "R-CURRENT"
    )["manifest"]["output_digest"]
