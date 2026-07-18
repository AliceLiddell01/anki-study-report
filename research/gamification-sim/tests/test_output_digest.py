from __future__ import annotations

import json
from pathlib import Path

import pytest

from gamification_sim.output_digest import compute_output_digest, verify_output_digest
from gamification_sim.reporting import render_json_report, report_payload
from gamification_sim.scenario_runner import run_corpus
from gamification_sim.strict_json import StrictJsonError, loads_strict


ROOT = Path(__file__).parents[1]


def result():
    return run_corpus(ROOT / "scenarios")


def test_stored_output_digest_verifies():
    run = result()
    assert compute_output_digest(run) == run.manifest.output_digest
    assert verify_output_digest(run)


def test_single_numeric_mutation_fails_verification():
    payload = report_payload(result())
    payload["scenario_results"][0]["metrics"][0][1] += 0.001
    assert not verify_output_digest(payload)


def test_manifest_mutation_fails_verification():
    payload = report_payload(result())
    payload["manifest"]["command"] = "mutated-command"
    assert not verify_output_digest(payload)


def test_embedded_digest_is_detached_from_recomputation():
    payload = report_payload(result())
    expected = compute_output_digest(payload)
    payload["manifest"]["output_digest"] = "0" * 64
    assert compute_output_digest(payload) == expected
    assert not verify_output_digest(payload)


def test_report_whitespace_does_not_affect_semantic_verification():
    payload = loads_strict(render_json_report(result()))
    compact = loads_strict(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    assert verify_output_digest(payload)
    assert verify_output_digest(compact)


def test_unknown_digest_contract_is_rejected():
    payload = report_payload(result())
    payload["manifest"]["output_digest_contract"] = "unknown-v9"
    with pytest.raises(ValueError, match="unsupported output digest contract"):
        verify_output_digest(payload)


def test_non_finite_report_value_is_rejected_by_strict_loader():
    with pytest.raises(StrictJsonError, match="non-standard JSON number"):
        loads_strict('{"value":NaN}', context="report")
