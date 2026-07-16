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
