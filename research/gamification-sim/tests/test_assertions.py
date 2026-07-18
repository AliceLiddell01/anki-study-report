from __future__ import annotations

import pytest

from gamification_sim.assertions import evaluate_assertion
from gamification_sim.scenario_models import (
    AssertionClass,
    AssertionScope,
    AssertionStatus,
    AssertionType,
    ScenarioAssertion,
    ScenarioMetric,
)


def a(kind, expected, tolerance=1e-9):
    return ScenarioAssertion(
        AssertionClass.INVARIANT,
        kind,
        AssertionScope.SCENARIO,
        ScenarioMetric.TOTAL_REVIEW_UNITS,
        expected,
        tolerance,
        "candidate-independent test invariant",
    )


@pytest.mark.parametrize(
    ("kind", "observed", "expected", "passed"),
    [
        (AssertionType.EQUALS, 1, 1, True),
        (AssertionType.APPROXIMATELY_EQUALS, 1.0000000001, 1, True),
        (AssertionType.LESS_THAN, 0.9, 1, True),
        (AssertionType.LESS_THAN_OR_EQUAL, 1, 1, True),
        (AssertionType.GREATER_THAN, 1.1, 1, True),
        (AssertionType.GREATER_THAN_OR_EQUAL, 1, 1, True),
    ],
)
def test_local_operators(kind, observed, expected, passed):
    assert evaluate_assertion(a(kind, expected), observed=observed).passed is passed


@pytest.mark.parametrize(
    ("kind", "observed", "control", "expected", "passed"),
    [
        (AssertionType.EQUALS_CONTROL, 1, 1, 0, True),
        (AssertionType.DELTA_FROM_CONTROL_LTE, 1.1, 1, 0.1, True),
        (AssertionType.DELTA_FROM_CONTROL_GTE, 0.9, 1, -0.1, True),
        (AssertionType.RATIO_TO_CONTROL_LTE, 1.03, 1, 1.03, True),
        (AssertionType.RATIO_TO_CONTROL_GTE, 0.9, 1, 0.9, True),
    ],
)
def test_control_operators(kind, observed, control, expected, passed):
    assertion = ScenarioAssertion(
        AssertionClass.INVARIANT,
        kind,
        AssertionScope.COMPARISON,
        ScenarioMetric.TOTAL_REVIEW_UNITS,
        expected,
        1e-9,
        "candidate-independent control invariant",
    )
    assert evaluate_assertion(assertion, observed=observed, control_value=control).passed is passed


def test_zero_control_ratio_is_explicit_failure():
    assertion = ScenarioAssertion(
        AssertionClass.INVARIANT,
        AssertionType.RATIO_TO_CONTROL_LTE,
        AssertionScope.COMPARISON,
        ScenarioMetric.TOTAL_REVIEW_UNITS,
        1,
        1e-9,
        "ratio requires a non-zero control",
    )
    result = evaluate_assertion(assertion, observed=0, control_value=0)
    assert not result.passed
    assert "undefined" in result.detail


def test_non_applicable_regression_has_explicit_status():
    result = evaluate_assertion(a(AssertionType.EQUALS, 999), observed=1, applicable=False)
    assert result.status is AssertionStatus.NOT_APPLICABLE
    assert result.passed is False
    assert result.failed is False
