from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import gamification_sim.scenario_runner as runner
from gamification_sim.parameter_catalog import PARAMETER_CANDIDATES, parameter_candidate
from gamification_sim.parameters import CURRENT_PARAMETERS
from gamification_sim.scenario_loader import load_corpus, load_scenario
from gamification_sim.scenario_models import AssertionClass, AssertionStatus
from gamification_sim.scenario_runner import run_corpus, run_scenario
from gamification_sim.validation import close


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
    assert all(close(total, 10.0) for total in totals)


def test_corpus_all_assertions_pass():
    result = run_corpus(ROOT / "scenarios")
    assert result.passed
    assert len(result.scenario_results) == 26


def test_all_migrated_assertions_have_explicit_taxonomy_and_rationale():
    assertions = [
        assertion
        for definition in load_corpus(ROOT / "scenarios")
        for assertion in definition.assertions
    ]
    assert len(assertions) == 53
    assert sum(a.assertion_class is AssertionClass.INVARIANT for a in assertions) == 17
    assert sum(a.assertion_class is AssertionClass.REGRESSION for a in assertions) == 36
    assert all(a.rationale for a in assertions)


def test_invariant_assertions_run_for_every_catalog_candidate():
    definition = load_scenario(ROOT / "scenarios/edge/undo-with-support.json")
    for candidate in PARAMETER_CANDIDATES:
        result = run_scenario(
            definition,
            params=candidate.parameters,
            parameter_set_id=candidate.parameter_set_id,
        )
        invariant_results = [
            item for item in result.assertions
            if item.assertion.assertion_class is AssertionClass.INVARIANT
        ]
        assert invariant_results
        assert all(item.status is AssertionStatus.PASSED for item in invariant_results)


def test_regression_assertion_applies_only_to_matching_parameter_set():
    definition = load_scenario(ROOT / "scenarios/regression/core-formula-regression.json")
    current = run_scenario(definition, parameter_set_id="R-CURRENT")
    alternative = parameter_candidate("R-NO-GAIN")
    changed = run_scenario(
        definition,
        params=alternative.parameters,
        parameter_set_id=alternative.parameter_set_id,
    )
    assert all(item.status is AssertionStatus.PASSED for item in current.assertions)
    assert all(item.status is AssertionStatus.NOT_APPLICABLE for item in changed.assertions)
    assert changed.passed


def test_current_regression_catches_changed_current_formula():
    definition = load_scenario(ROOT / "scenarios/regression/core-formula-regression.json")
    changed = replace(CURRENT_PARAMETERS, neutral_context_credit=0.2)
    result = run_scenario(definition, params=changed, parameter_set_id="R-CURRENT")
    assert any(item.status is AssertionStatus.FAILED for item in result.assertions)


def test_repeated_run_digest_equality():
    first = run_corpus(ROOT / "scenarios")
    second = run_corpus(ROOT / "scenarios")
    assert first.manifest.input_digest == second.manifest.input_digest
    assert first.manifest.output_digest == second.manifest.output_digest


def test_control_executes_before_dependent_scenario():
    definitions = load_corpus(ROOT / "scenarios")
    ordered = runner._execution_order(definitions)
    positions = {definition.scenario_id: index for index, definition in enumerate(ordered)}
    for definition in definitions:
        if definition.control_scenario_id:
            assert positions[definition.control_scenario_id] < positions[definition.scenario_id]


def test_all_comparison_assertions_use_the_resolved_top_level_control():
    definitions = load_corpus(ROOT / "scenarios")
    by_id = {definition.scenario_id: definition for definition in definitions}
    results = run_corpus(ROOT / "scenarios")
    for result in results.scenario_results:
        if result.comparison is None:
            continue
        assert result.comparison.control_scenario_id == by_id[result.scenario_id].control_scenario_id


def test_resolved_control_mismatch_cannot_silently_pass():
    definitions = load_corpus(ROOT / "scenarios")
    by_id = {definition.scenario_id: definition for definition in definitions}
    results = run_corpus(ROOT / "scenarios")
    result_by_id = {result.scenario_id: result for result in results.scenario_results}
    with pytest.raises(ValueError, match="does not match top-level"):
        run_scenario(
            by_id["intentional-backlog"],
            control_definition=by_id["duplicate-replay-control"],
            control_result=result_by_id["duplicate-replay-control"],
        )
