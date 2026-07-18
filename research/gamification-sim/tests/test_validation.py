from __future__ import annotations

import math

import pytest

from gamification_sim.episode_reward import evaluate_episode
from gamification_sim.models import Outcome, ReviewEpisodeInput
from gamification_sim.validation import require_non_negative_int


DAY = "2026-07-16"


@pytest.mark.parametrize("value", [0, 1, 30])
def test_require_non_negative_int_accepts_real_integers(value):
    assert require_non_negative_int("count", value) == value


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        -1,
        0.0,
        1.0,
        1.7,
        "1",
        "30",
        None,
        math.nan,
        math.inf,
    ],
)
def test_require_non_negative_int_rejects_coercible_or_invalid_values(value):
    with pytest.raises(ValueError, match="count"):
        require_non_negative_int("count", value)


@pytest.mark.parametrize("value", [0, 1])
def test_evaluate_episode_accepts_binary_integer_eligibility(value):
    episode = ReviewEpisodeInput(
        "eligibility",
        "card",
        DAY,
        Outcome.GOOD,
        core_eligibility=value,
    )
    result = evaluate_episode(episode)
    assert result.core_eligibility == value


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        -1,
        2,
        30,
        0.0,
        1.0,
        1.7,
        "1",
        "30",
        None,
        math.nan,
        math.inf,
    ],
)
def test_evaluate_episode_rejects_non_binary_or_coercible_eligibility(value):
    episode = ReviewEpisodeInput(
        "eligibility",
        "card",
        DAY,
        Outcome.GOOD,
        core_eligibility=value,
    )
    with pytest.raises(ValueError, match="core_eligibility"):
        evaluate_episode(episode)

@pytest.mark.parametrize(
    "field",
    [
        "natural_due_at_start",
        "due_visible_under_limits",
        "due_hidden_by_limits",
    ],
)
@pytest.mark.parametrize(
    "value",
    [True, False, -1, 0.0, 1.0, 1.7, "1", "30", None, float("nan"), float("inf")],
)
def test_aggregate_day_rejects_invalid_workload_integer_fields(field, value):
    from gamification_sim.day_aggregation import aggregate_day
    from gamification_sim.models import ReviewDayInput, WorkloadSnapshot

    workload_values = {
        "natural_due_at_start": 0,
        "due_visible_under_limits": 0,
        "due_hidden_by_limits": 0,
    }
    workload_values[field] = value
    day = ReviewDayInput(
        "2026-07-16",
        workload=WorkloadSnapshot(**workload_values),
    )

    with pytest.raises(ValueError, match=field):
        aggregate_day(day)
