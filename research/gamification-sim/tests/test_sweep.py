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
from gamification_sim.strict_json import StrictJsonError
from gamification_sim.sweep import (
    SENSITIVITY_GRIDS,
    evaluate_candidate,
    load_sweep_config,
    run_sensitivity,
    run_sweep,
    write_sweep_reports,
)


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
    assert all(by_id[item]["hard_gate_pass"] for item in sweep_payload["pareto"]["candidate_ids"])
    assert all(item["rejection_reason_codes"] for item in sweep_payload["candidates"] if not item["hard_gate_pass"])


def test_current_only_regressions_do_not_reject_alternative_candidate():
    config = load_sweep_config(CONFIG, ROOT)
    evaluation = evaluate_candidate(parameter_candidate("R-NO-GAIN"), config, ROOT)
    assert "SCENARIO_ASSERTION_FAILURE" not in evaluation.rejection_reason_codes


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
    assert payload["manifest"]["output_digest"] == run_sensitivity(
        load_sweep_config(CONFIG, ROOT), ROOT, "R-CURRENT"
    )["manifest"]["output_digest"]
