from __future__ import annotations

import json
from pathlib import Path

from gamification_sim.reporting import render_json_report, render_markdown_report, write_reports
from gamification_sim.scenario_runner import run_corpus

ROOT = Path(__file__).parents[1]


def result():
    return run_corpus(ROOT / "scenarios")


def test_json_report_is_valid_and_contains_digests():
    payload = json.loads(render_json_report(result()))
    assert payload["manifest"]["input_digest"]
    assert payload["manifest"]["output_digest"]
    assert payload["manifest"]["output_digest_contract"] == "detached-corpus-result-v1"
    assert payload["corpus_summary"] == {"scenario_count": 26, "passed": 26, "failed": 0}
    assert payload["failures"] == []


def test_markdown_is_deterministic_and_contains_comparisons():
    first = render_markdown_report(result())
    second = render_markdown_report(result())
    assert first == second
    assert "Abuse and control comparisons" in first
    assert "Failed assertions" in first


def test_write_reports_uses_deterministic_run_directory(tmp_path):
    run = result()
    first = write_reports(run, tmp_path)
    second = write_reports(run, tmp_path)
    assert first == second
    assert (first / "results.json").is_file()
    assert (first / "summary.md").is_file()


def test_no_committed_outputs():
    output = ROOT / "outputs"
    assert not output.exists() or not any(path.is_file() for path in output.rglob("*"))


def test_failed_assertion_is_rendered():
    from dataclasses import replace
    from gamification_sim.scenario_loader import load_scenario
    from gamification_sim.scenario_runner import run_definitions

    definition = load_scenario(ROOT / "scenarios/ordinary/high-volume-day.json")
    broken_assertion = replace(definition.assertions[0], expected=999.0)
    broken = replace(definition, scenario_id="report-failure", assertions=(broken_assertion,))
    run = run_definitions((broken,), command="test")
    report = render_markdown_report(run)
    payload = json.loads(render_json_report(run))
    assert "`report-failure`" in report
    assert "observed=" in report
    assert payload["corpus_summary"]["failed"] == 1
    assert payload["failures"][0]["scenario_id"] == "report-failure"
