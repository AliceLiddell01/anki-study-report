from __future__ import annotations

import math

from .models import EpisodeRewardBreakdown, ReasonCode, ReviewEpisodeInput
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .validation import require_positive, require_range


def _interpolate(value: float, anchors: tuple[tuple[float, float], ...]) -> float:
    if value <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if value <= x1:
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return anchors[-1][1]


def challenge_curve(retrievability: float, params: RewardParameterSet = CURRENT_PARAMETERS) -> float:
    r = require_range("retrievability", retrievability, 0.0, 1.0)
    if r < 0.10:
        return params.low_retrievability_credit
    if r >= 0.95:
        return 0.0
    return _interpolate(r, params.challenge_anchors)


def delay_credit(delay_drop: float, params: RewardParameterSet = CURRENT_PARAMETERS) -> float:
    drop = require_range("delay_drop", delay_drop, 0.0, 1.0)
    if drop <= 0.05:
        return 1.0
    if drop >= 0.70:
        return 0.25
    return _interpolate(drop, params.delay_credit_anchors)


def adjusted_challenge(
    retrievability_actual: float | None,
    retrievability_natural_due: float | None,
    params: RewardParameterSet = CURRENT_PARAMETERS,
) -> float:
    if retrievability_actual is None:
        return 0.0
    actual = challenge_curve(retrievability_actual, params)
    if retrievability_natural_due is None:
        return actual
    due_r = require_range("retrievability_natural_due", retrievability_natural_due, 0.0, 1.0)
    actual_r = require_range("retrievability_actual", retrievability_actual, 0.0, 1.0)
    if actual_r >= due_r:
        return actual
    due = challenge_curve(due_r, params)
    extra = max(0.0, actual - due)
    return due + extra * delay_credit(max(0.0, due_r - actual_r), params)


def memory_gain_credit(
    stability_before: float | None,
    stability_good_counterfactual: float | None,
    params: RewardParameterSet = CURRENT_PARAMETERS,
) -> float:
    if stability_before is None or stability_good_counterfactual is None:
        return 0.0
    before = require_positive("stability_before", stability_before)
    after = require_positive("stability_good_counterfactual", stability_good_counterfactual)
    raw = math.log(after / before)
    if raw <= 0.10:
        return 0.0
    if raw >= 1.10:
        return params.memory_gain_cap
    return min(params.memory_gain_cap, _interpolate(raw, params.memory_gain_anchors))


def evaluate_episode(
    episode: ReviewEpisodeInput,
    params: RewardParameterSet = CURRENT_PARAMETERS,
) -> EpisodeRewardBreakdown:
    core_eligibility = int(episode.core_eligibility)
    if core_eligibility not in {0, 1}:
        raise ValueError("core_eligibility must be 0 or 1")
    bonus_eligibility = require_range("bonus_eligibility", episode.bonus_eligibility, 0.0, 1.0)
    response_validity = require_range("response_validity", episode.response_validity, 0.0, 1.0)
    effective_bonus = min(bonus_eligibility, response_validity)
    passed = episode.outcome.passed

    baseline = core_eligibility * (
        params.attempt_credit + (params.outcome_credit if passed else 0.0)
    )
    challenge = adjusted_challenge(
        episode.memory.retrievability_actual,
        episode.memory.retrievability_natural_due,
        params,
    ) if passed else 0.0
    gain = memory_gain_credit(
        episode.memory.stability_before,
        episode.memory.stability_good_counterfactual,
        params,
    ) if passed else 0.0
    confidence = params.confidence(episode.memory.confidence)
    context_credit = 0.0
    reasons: list[str] = []
    if passed and core_eligibility:
        context_credit = params.neutral_context_credit + confidence * (
            challenge + gain - params.neutral_context_credit
        )
        reasons.append(
            ReasonCode.NEUTRAL_CONTEXT.value if confidence == 0 else ReasonCode.MODEL_CONTEXT.value
        )
    context = effective_bonus * context_credit
    if effective_bonus < 1.0 and passed and core_eligibility:
        reasons.append(ReasonCode.BONUS_SUPPRESSED.value)
    reasons.append(
        ReasonCode.CORE_ELIGIBLE.value if core_eligibility else ReasonCode.CORE_INELIGIBLE.value
    )

    total = baseline + context
    caps: list[str] = []
    if total >= params.core_episode_cap - 1e-12:
        context = max(0.0, params.core_episode_cap - baseline)
        total = baseline + context
        caps.append(ReasonCode.CORE_CAP_APPLIED.value)
        reasons.append(ReasonCode.CORE_CAP_APPLIED.value)

    return EpisodeRewardBreakdown(
        rule_version=params.rule_version,
        source_event_key=episode.source_event_key,
        baseline=baseline,
        context=context,
        total=total,
        challenge_credit=challenge,
        memory_gain_credit=gain,
        core_eligibility=core_eligibility,
        bonus_eligibility=effective_bonus,
        applied_caps=tuple(caps),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
