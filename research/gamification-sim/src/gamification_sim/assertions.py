from __future__ import annotations

import math

from .scenario_models import (
    AssertionResult,
    AssertionType,
    ScenarioAssertion,
)
from .validation import close


def evaluate_assertion(
    assertion: ScenarioAssertion,
    *,
    observed: float,
    control_value: float | None = None,
) -> AssertionResult:
    kind = assertion.type
    expected = assertion.expected
    tolerance = assertion.tolerance
    compared: float | None = observed
    detail = ""

    if kind is AssertionType.EQUALS:
        passed = observed == expected
    elif kind is AssertionType.APPROXIMATELY_EQUALS:
        passed = close(observed, expected, tolerance)
    elif kind is AssertionType.LESS_THAN:
        passed = observed < expected
    elif kind is AssertionType.LESS_THAN_OR_EQUAL:
        passed = observed <= expected
    elif kind is AssertionType.GREATER_THAN:
        passed = observed > expected
    elif kind is AssertionType.GREATER_THAN_OR_EQUAL:
        passed = observed >= expected
    else:
        if control_value is None:
            return AssertionResult(assertion, False, None, None, "control value is unavailable")
        if kind is AssertionType.EQUALS_CONTROL:
            compared = observed - control_value
            passed = close(observed, control_value, tolerance)
            detail = f"observed={observed}, control={control_value}"
        elif kind in {
            AssertionType.DELTA_FROM_CONTROL_LTE,
            AssertionType.DELTA_FROM_CONTROL_GTE,
        }:
            compared = observed - control_value
            passed = (compared <= expected or close(compared, expected, tolerance)) if kind is AssertionType.DELTA_FROM_CONTROL_LTE else (compared >= expected or close(compared, expected, tolerance))
            detail = f"delta={compared}"
        else:
            if close(control_value, 0.0):
                return AssertionResult(
                    assertion,
                    False,
                    None,
                    control_value,
                    "ratio is undefined because the control value is zero",
                )
            compared = observed / control_value
            if not math.isfinite(compared):
                return AssertionResult(assertion, False, None, control_value, "ratio is not finite")
            passed = (compared <= expected or close(compared, expected, tolerance)) if kind is AssertionType.RATIO_TO_CONTROL_LTE else (compared >= expected or close(compared, expected, tolerance))
            detail = f"ratio={compared}"

    if not detail:
        detail = f"observed={compared}, expected={expected}"
    return AssertionResult(assertion, passed, compared, control_value, detail)
