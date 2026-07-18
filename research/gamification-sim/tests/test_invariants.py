from __future__ import annotations

from gamification_sim.day_aggregation import aggregate_day
from gamification_sim.episode_reward import evaluate_episode
from gamification_sim.models import Outcome, ReviewDayInput, ReviewEpisodeInput
from gamification_sim.validation import close


DAY = "2026-07-16"


def test_h01_and_h10_all_eligible_baseline_is_preserved_at_high_volume():
    episodes = tuple(ReviewEpisodeInput(f"e{i}", f"c{i}", DAY, Outcome.GOOD) for i in range(300))
    result = aggregate_day(ReviewDayInput(DAY, episodes=episodes))
    assert close(result.core_baseline, 270.0)


def test_h06_h07_button_and_time_neutrality():
    totals = [evaluate_episode(ReviewEpisodeInput(o.value, o.value, DAY, o)).total for o in (Outcome.HARD, Outcome.GOOD, Outcome.EASY)]
    assert all(close(total, totals[0]) for total in totals)
    slow = evaluate_episode(ReviewEpisodeInput("slow", "slow", DAY, Outcome.GOOD, response_validity=1.0))
    suspicious = evaluate_episode(ReviewEpisodeInput("fast", "fast", DAY, Outcome.GOOD, response_validity=0.5))
    assert suspicious.total <= slow.total
    assert close(suspicious.baseline, slow.baseline)


def test_h13_volume_cap_and_h16_non_negative():
    episodes = tuple(ReviewEpisodeInput(f"e{i}", f"c{i}", DAY, Outcome.GOOD) for i in range(1000))
    result = aggregate_day(ReviewDayInput(DAY, episodes=episodes))
    assert result.volume_credit <= 15.0
    assert result.total >= 0.0


def test_h18_determinism():
    day = ReviewDayInput(DAY, episodes=(ReviewEpisodeInput("e", "c", DAY, Outcome.GOOD),))
    assert aggregate_day(day) == aggregate_day(day)
