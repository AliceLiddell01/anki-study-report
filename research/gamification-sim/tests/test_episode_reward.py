from __future__ import annotations

import math

import pytest

from gamification_sim.episode_reward import (
    adjusted_challenge,
    challenge_curve,
    delay_credit,
    evaluate_episode,
    memory_gain_credit,
)
from gamification_sim.models import ConfidenceLevel, MemoryContext, Outcome, ReviewEpisodeInput
from gamification_sim.review_candidate_mechanisms import RewardExecutionContext
from gamification_sim.validation import close


@pytest.mark.parametrize(
    ("r", "expected"),
    [
        (0.099999, 0.10),
        (0.10, 0.15),
        (0.20, 0.25),
        (0.35, 0.30),
        (0.50, 0.30),
        (0.65, 0.22),
        (0.80, 0.12),
        (0.90, 0.05),
        (0.95, 0.00),
        (0.950001, 0.00),
    ],
)
def test_challenge_curve_boundaries(r, expected):
    assert close(challenge_curve(r), expected)


def test_challenge_curve_interpolates():
    assert close(challenge_curve(0.575), 0.26)


@pytest.mark.parametrize(
    ("drop", "expected"),
    [(0.049999, 1.0), (0.05, 1.0), (0.15, 0.85), (0.30, 0.65), (0.50, 0.45), (0.70, 0.25), (0.9, 0.25)],
)
def test_delay_credit_boundaries(drop, expected):
    assert close(delay_credit(drop), expected)


def test_backlog_protection_matches_documented_heavy_case():
    assert close(adjusted_challenge(0.10, 0.90), 0.075)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0.099999, 0.0), (0.10, 0.0), (0.25, 0.03), (0.50, 0.06), (0.80, 0.09), (1.10, 0.12), (2.0, 0.12)],
)
def test_memory_gain_boundaries(raw, expected):
    assert close(memory_gain_credit(1.0, math.exp(raw)), expected)


def test_ordinary_good_is_one_unit():
    episode = ReviewEpisodeInput(
        source_event_key="good",
        card_lineage="card",
        anki_day="2026-07-16",
        outcome=Outcome.GOOD,
        memory=MemoryContext(
            retrievability_actual=0.90,
            retrievability_natural_due=0.90,
            stability_before=1.0,
            stability_good_counterfactual=math.exp(5 / 12),
            confidence=ConfidenceLevel.HIGH,
        ),
    )
    result = evaluate_episode(episode)
    assert close(result.baseline, 0.90)
    assert close(result.context, 0.10)
    assert close(result.total, 1.00)
    assert close(result.total, result.baseline + result.context)


@pytest.mark.parametrize("outcome", [Outcome.HARD, Outcome.GOOD, Outcome.EASY])
def test_successful_buttons_are_reward_neutral(outcome):
    episode = ReviewEpisodeInput(
        source_event_key=outcome.value,
        card_lineage=outcome.value,
        anki_day="2026-07-16",
        outcome=outcome,
    )
    assert close(evaluate_episode(episode).total, 1.0)


def test_again_gets_attempt_only():
    episode = ReviewEpisodeInput("again", "card", "2026-07-16", Outcome.AGAIN)
    result = evaluate_episode(episode)
    assert close(result.baseline, 0.25)
    assert close(result.context, 0.0)
    assert close(result.total, 0.25)


def test_suspicious_time_suppresses_bonus_not_baseline():
    episode = ReviewEpisodeInput(
        "fast",
        "card",
        "2026-07-16",
        Outcome.GOOD,
        response_validity=0.0,
    )
    result = evaluate_episode(episode)
    assert close(result.baseline, 0.90)
    assert close(result.context, 0.0)
    assert close(result.total, 0.90)


def test_no_fsrs_fallback_is_neutral():
    episode = ReviewEpisodeInput("none", "card", "2026-07-16", Outcome.GOOD)
    assert close(evaluate_episode(episode).total, 1.0)


def test_core_cap_is_never_exceeded():
    episode = ReviewEpisodeInput(
        "cap",
        "card",
        "2026-07-16",
        Outcome.GOOD,
        memory=MemoryContext(
            retrievability_actual=0.50,
            retrievability_natural_due=0.50,
            stability_before=1.0,
            stability_good_counterfactual=math.exp(2.0),
            confidence=ConfidenceLevel.HIGH,
        ),
    )
    result = evaluate_episode(episode)
    assert close(result.total, 1.32)
    assert "core_cap_applied" in result.applied_caps


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_invalid_numeric_values_are_rejected(bad):
    episode = ReviewEpisodeInput(
        "bad",
        "card",
        "2026-07-16",
        Outcome.GOOD,
        bonus_eligibility=bad,
    )
    with pytest.raises(ValueError):
        evaluate_episode(episode)


def test_core_none_outcome_is_rejected():
    episode = ReviewEpisodeInput("none", "card", "2026-07-16", Outcome.NONE)
    with pytest.raises(ValueError):
        evaluate_episode(episode)


def test_invalid_unused_memory_value_is_rejected():
    episode = ReviewEpisodeInput(
        "again-invalid",
        "card",
        "2026-07-16",
        Outcome.AGAIN,
        memory=MemoryContext(retrievability_actual=float("nan")),
    )
    with pytest.raises(ValueError):
        evaluate_episode(episode)


def candidate_memory_episode() -> ReviewEpisodeInput:
    return ReviewEpisodeInput(
        source_event_key="candidate-memory",
        card_lineage="candidate-card",
        anki_day="2026-07-16",
        outcome=Outcome.GOOD,
        memory=MemoryContext(
            retrievability_actual=0.95,
            retrievability_natural_due=0.95,
            stability_before=1.0,
            stability_good_counterfactual=math.exp(2.0),
            confidence=ConfidenceLevel.HIGH,
        ),
    )


def cycling_execution_context(day: int) -> RewardExecutionContext:
    return RewardExecutionContext(
        day=day,
        retention_transition_days=(30, 60),
    )


def test_default_candidate_path_is_bitwise_identity():
    episode = candidate_memory_episode()

    default = evaluate_episode(episode)
    explicit_none = evaluate_episode(
        episode,
        candidate_parameterization_id=None,
    )
    reference = evaluate_episode(
        episode,
        candidate_parameterization_id="R-CURRENT",
    )

    assert explicit_none == default
    assert reference == default


def test_step_candidate_scales_only_memory_gain_on_day_60():
    episode = candidate_memory_episode()

    reference = evaluate_episode(episode)
    candidate = evaluate_episode(
        episode,
        candidate_parameterization_id="P-STEP-ZERO",
        execution_context=cycling_execution_context(60),
    )

    assert close(reference.baseline, candidate.baseline)
    assert close(reference.challenge_credit, candidate.challenge_credit)
    assert close(reference.memory_gain_credit, 0.12)
    assert close(candidate.memory_gain_credit, 0.0)
    assert close(reference.context, 0.12)
    assert close(candidate.context, 0.0)


def test_neutral_ratio_candidate_uses_source_derived_endpoint():
    candidate = evaluate_episode(
        candidate_memory_episode(),
        candidate_parameterization_id="P-STEP-NEUTRAL-RATIO",
        execution_context=cycling_execution_context(60),
    )

    assert close(candidate.memory_gain_credit, 0.10)
    assert close(candidate.context, 0.10)
    assert close(candidate.total, 1.00)


def test_taper_candidate_scales_raw_memory_gain_before_confidence_blend():
    candidate = evaluate_episode(
        candidate_memory_episode(),
        candidate_parameterization_id="P-TAPER-ZERO-30D",
        execution_context=cycling_execution_context(75),
    )

    assert close(candidate.memory_gain_credit, 0.06)
    assert close(candidate.challenge_credit, 0.0)
    assert close(candidate.context, 0.06)
    assert close(candidate.total, 0.96)


def test_candidate_is_identity_for_policy_without_final_day_60_transition():
    episode = candidate_memory_episode()
    reference = evaluate_episode(episode)
    candidate = evaluate_episode(
        episode,
        candidate_parameterization_id="P-STEP-ZERO",
        execution_context=RewardExecutionContext(
            day=365,
            retention_transition_days=(),
        ),
    )

    assert candidate == reference


def test_unknown_candidate_fails_closed_in_episode_evaluation():
    with pytest.raises(
        ValueError,
        match="unknown frozen Review parameterization",
    ):
        evaluate_episode(
            candidate_memory_episode(),
            candidate_parameterization_id="P-UNREGISTERED",
            execution_context=cycling_execution_context(60),
        )


def test_candidate_episode_evaluation_requires_context():
    with pytest.raises(
        ValueError,
        match="requires an execution context",
    ):
        evaluate_episode(
            candidate_memory_episode(),
            candidate_parameterization_id="P-STEP-ZERO",
        )
