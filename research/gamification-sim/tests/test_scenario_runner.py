from __future__ import annotations

from pathlib import Path

import pytest

import gamification_sim.scenario_runner as runner
from gamification_sim.scenario_loader import load_corpus, load_scenario
from gamification_sim.scenario_runner import run_corpus, run_scenario


ROOT = Path(__file__).parents[1]


def test_one_day_and_multiday_scenarios():
    one = load_scenario(ROOT / "scenarios/ordinary/high-volume-day.json")
    multi = load_scenario(ROOT / "scenarios/ordinary/stable-seven-days.json")
    assert len(run_scenario(one).day_results) == 1
    assert len(run_scenario(multi).day_results) == 7


def test_scenario_total_equals_sum_of_days():
    result = run_scenario(load_scenario(ROOT / "scenarios/ordinary/stable-seven-days.json"))
    assert dict(result.metrics)["total_review_units"] == sum(day.breakdown.total for day in result.day_results)


def test_runner_calls_existing_aggregate_day(monkeypatch):
    original = runner.aggregate_day
    calls = []
    def wrapped(day, params):
        calls.append(day.anki_day)
        return original(day, params)
    monkeypatch.setattr(runner, "aggregate_day", wrapped)
    run_scenario(load_scenario(ROOT / "scenarios/ordinary/stable-seven-days.json"))
    assert len(calls) == 7


def test_session_invariance_corpus_case():
    result = run_scenario(load_scenario(ROOT / "scenarios/edge/session-invariance.json"))
    totals = [day.breakdown.total for day in result.day_results]
    assert totals == [10.0, 10.0]


def test_corpus_all_assertions_pass():
    result = run_corpus(ROOT / "scenarios")
    assert result.passed
    assert len(result.scenario_results) == 26


def test_repeated_run_digest_equality():
    first = run_corpus(ROOT / "scenarios")
    second = run_corpus(ROOT / "scenarios")
    assert first.manifest.input_digest == second.manifest.input_digest
    assert first.manifest.output_digest == second.manifest.output_digest
