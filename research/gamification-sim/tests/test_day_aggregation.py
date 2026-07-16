from __future__ import annotations

from dataclasses import replace

import pytest

from gamification_sim.day_aggregation import aggregate_day, contribution_band, volume_credit
from gamification_sim.models import (
    CompletionStatus,
    ContributionBand,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    SupplementalInput,
    SupportEventInput,
    SupportKind,
    WorkloadSnapshot,
)
from gamification_sim.parameters import CURRENT_PARAMETERS
from gamification_sim.validation import close


DAY = "2026-07-16"


def successes(count: int, prefix: str = "e"):
    return tuple(ReviewEpisodeInput(f"{prefix}{i}", f"{prefix}-card-{i}", DAY, Outcome.GOOD) for i in range(count))


@pytest.mark.parametrize(
    ("q", "expected"),
    [(9.99, 0.0), (10.0, 0.0), (10.01, 0.0005), (25.0, 0.75), (50.0, 2.75), (100.0, 7.75), (180.0, 15.0), (300.0, 15.0)],
)
def test_volume_boundaries(q, expected):
    assert close(volume_credit(q)[0], expected)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (SupportKind.FIRST_STEP, 0.05),
        (SupportKind.SECOND_STEP, 0.04),
        (SupportKind.COMPLETION, 0.03),
        (SupportKind.INTERDAY_RECOVERY, 0.12),
        (SupportKind.OTHER, 0.00),
    ],
)
def test_support_kind_values_are_parameterized(kind, expected):
    event = SupportEventInput("support", "parent", kind)
    result = aggregate_day(ReviewDayInput(DAY, support_events=(event,)))
    assert close(result.raw_support, expected)


def test_support_reward_uses_supplied_parameter_set():
    custom_values = tuple(
        (kind, 0.07 if kind is SupportKind.FIRST_STEP else value)
        for kind, value in CURRENT_PARAMETERS.support_values
    )
    params = replace(
        CURRENT_PARAMETERS,
        rule_version="review-custom",
        support_values=custom_values,
    )
    event = SupportEventInput("support", "parent", SupportKind.FIRST_STEP)

    default_result = aggregate_day(ReviewDayInput(DAY, support_events=(event,)))
    custom_result = aggregate_day(
        ReviewDayInput(DAY, support_events=(event,)),
        params,
    )

    assert close(default_result.raw_support, 0.05)
    assert close(custom_result.raw_support, 0.07)
    assert custom_result.rule_version == "review-custom"


def test_support_episode_and_day_caps():
    kinds = (
        SupportKind.FIRST_STEP,
        SupportKind.SECOND_STEP,
        SupportKind.COMPLETION,
    )
    events = tuple(
        SupportEventInput(f"s{i}", "parent", kinds[i % len(kinds)])
        for i in range(12)
    )
    day = ReviewDayInput(DAY, episodes=successes(30), support_events=events)
    result = aggregate_day(day)
    assert close(result.raw_support, 0.12)
    assert result.capped_support <= result.support_cap
    assert "support_episode_cap" in result.reason_codes


def test_daily_support_cap_allows_and_caps_interday_relearning_only():
    events = tuple(
        SupportEventInput(
            f"s{i}",
            f"parent-{i}",
            SupportKind.INTERDAY_RECOVERY,
        )
        for i in range(5)
    )
    result = aggregate_day(ReviewDayInput(DAY, support_events=events))
    assert close(result.raw_support, 0.60)
    assert close(result.support_cap, 0.50)
    assert close(result.capped_support, 0.50)
    assert "support_day_cap" in result.applied_caps


def test_daily_supplemental_cap():
    supplemental = tuple(SupplementalInput(f"p{i}", 1.0) for i in range(5))
    result = aggregate_day(ReviewDayInput(DAY, episodes=successes(100), supplemental_events=supplemental))
    assert close(result.supplemental_cap, 2.0)
    assert close(result.capped_supplemental, 2.0)
    assert "supplemental_day_cap" in result.applied_caps


def test_supplemental_without_core_has_zero_permanent_reward():
    result = aggregate_day(
        ReviewDayInput(DAY, supplemental_events=(SupplementalInput("p", 1.0),))
    )
    assert close(result.raw_supplemental, 1.0)
    assert close(result.capped_supplemental, 0.0)


@pytest.mark.parametrize(
    ("status", "factor"),
    [
        (CompletionStatus.COLLECTION_CLEARED, 1.0),
        (CompletionStatus.SCOPE_CLEARED, 0.8),
        (CompletionStatus.CONFIGURED_LIMIT_REACHED, 0.5),
        (CompletionStatus.PARTIAL, 0.0),
        (CompletionStatus.ZERO_DUE, 0.0),
        (CompletionStatus.SNAPSHOT_UNCERTAIN, 0.0),
    ],
)
def test_completion_factors_and_cap(status, factor):
    result = aggregate_day(
        ReviewDayInput(DAY, episodes=successes(300), workload=WorkloadSnapshot(status=status))
    )
    assert close(result.completion_credit, 3.0 * factor)
    assert result.completion_credit <= 3.0


def test_zero_due_is_neutral():
    result = aggregate_day(
        ReviewDayInput(DAY, workload=WorkloadSnapshot(status=CompletionStatus.ZERO_DUE))
    )
    assert close(result.total, 0.0)
    assert close(result.completion_credit, 0.0)
    assert result.contribution_band is ContributionBand.REVIEW_NONE


def test_contribution_bands():
    assert contribution_band(0, CompletionStatus.PARTIAL) is ContributionBand.REVIEW_NONE
    assert contribution_band(9.9, CompletionStatus.PARTIAL) is ContributionBand.REVIEW_LIGHT
    assert contribution_band(10, CompletionStatus.PARTIAL) is ContributionBand.REVIEW_SUBSTANTIVE
    assert contribution_band(25, CompletionStatus.PARTIAL) is ContributionBand.REVIEW_FULL
    assert contribution_band(5, CompletionStatus.COLLECTION_CLEARED) is ContributionBand.REVIEW_FULL


def test_session_invariance():
    episodes = successes(100)
    one = aggregate_day(ReviewDayInput(DAY, episodes=episodes, session_ids=("one",)))
    split = aggregate_day(ReviewDayInput(DAY, episodes=episodes, session_ids=("a", "b", "c")))
    assert one == split


def test_late_recomputation_is_derived_not_mutated():
    initial = aggregate_day(ReviewDayInput(DAY, episodes=successes(10, "initial")))
    expanded = aggregate_day(ReviewDayInput(DAY, episodes=successes(31, "late")))
    repeated = aggregate_day(ReviewDayInput(DAY, episodes=successes(31, "late")))
    assert expanded == repeated
    assert expanded.total > initial.total


def test_full_breakdown_equality():
    result = aggregate_day(
        ReviewDayInput(
            DAY,
            episodes=successes(100),
            support_events=(
                SupportEventInput(
                    "s",
                    "p",
                    SupportKind.INTERDAY_RECOVERY,
                ),
            ),
            supplemental_events=(SupplementalInput("p", 5.0),),
            workload=WorkloadSnapshot(status=CompletionStatus.COLLECTION_CLEARED),
        )
    )
    expected = (
        result.core_baseline
        + result.core_context
        + result.capped_support
        + result.capped_supplemental
        + result.volume_credit
        + result.completion_credit
    )
    assert close(result.total, expected)
    assert result.total >= 0
