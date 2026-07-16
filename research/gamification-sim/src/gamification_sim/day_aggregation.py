from __future__ import annotations

from collections import defaultdict

from .episode_reward import evaluate_episode
from .models import (
    CompletionStatus,
    ContributionBand,
    EligibilityClass,
    ReasonCode,
    ReviewDayBreakdown,
    ReviewDayInput,
)
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .safeguards import apply_decision, decide_safeguards
from .validation import require_non_negative


def volume_credit(qualified_volume: float, params: RewardParameterSet = CURRENT_PARAMETERS) -> tuple[float, tuple[str, ...]]:
    q = require_non_negative("qualified_volume", qualified_volume)
    total = 0.0
    reasons: list[str] = []
    tier_codes = [
        ReasonCode.VOLUME_TIER_1.value,
        ReasonCode.VOLUME_TIER_2.value,
        ReasonCode.VOLUME_TIER_3.value,
        ReasonCode.VOLUME_TIER_4.value,
    ]
    for index, (start, rate, end) in enumerate(params.volume_tiers):
        amount = max(0.0, q - start)
        if end is not None:
            amount = min(amount, end - start)
        if amount > 0:
            total += rate * amount
            reasons.append(tier_codes[index])
    if total > params.volume_cap:
        total = params.volume_cap
        reasons.append(ReasonCode.VOLUME_CAP_REACHED.value)
    return total, tuple(reasons)


def contribution_band(q: float, status: CompletionStatus) -> ContributionBand:
    if q <= 0:
        return ContributionBand.REVIEW_NONE
    if q >= 25 or (
        q >= 5
        and status
        in {
            CompletionStatus.COLLECTION_CLEARED,
            CompletionStatus.SCOPE_CLEARED,
            CompletionStatus.CONFIGURED_LIMIT_REACHED,
        }
    ):
        return ContributionBand.REVIEW_FULL
    if q >= 10:
        return ContributionBand.REVIEW_SUBSTANTIVE
    return ContributionBand.REVIEW_LIGHT


def aggregate_day(
    day: ReviewDayInput,
    params: RewardParameterSet = CURRENT_PARAMETERS,
) -> ReviewDayBreakdown:
    seen_sources: set[str] = set()
    seen_card_days: set[tuple[str, str]] = set()
    episode_breakdowns = []
    reasons: list[str] = []
    routed_supplemental_raw = 0.0

    for episode in day.episodes:
        if episode.anki_day != day.anki_day:
            raise ValueError("episode anki_day must match day anki_day")
        decision = decide_safeguards(
            episode,
            seen_source_events=frozenset(seen_sources),
            seen_core_card_days=frozenset(seen_card_days),
            undone_source_event_keys=day.undone_source_event_keys,
        )
        reasons.extend(decision.reason_codes)
        seen_sources.add(episode.source_event_key)
        if decision.effective_class is EligibilityClass.SUPPLEMENTAL:
            routed_supplemental_raw += require_non_negative(
                "routed supplemental units", episode.supplemental_units
            )
            continue
        if decision.no_op:
            continue
        effective = apply_decision(episode, decision)
        if effective.eligibility_class is not EligibilityClass.CORE:
            continue
        seen_card_days.add((episode.card_lineage, episode.anki_day))
        episode_breakdowns.append(evaluate_episode(effective, params))

    core_baseline = sum(item.baseline for item in episode_breakdowns)
    core_context = sum(item.context for item in episode_breakdowns)
    qualified_volume = core_baseline

    support_by_parent: dict[str, float] = defaultdict(float)
    support_seen: set[str] = set()
    for event in day.support_events:
        if event.source_event_key in support_seen:
            reasons.append(ReasonCode.DUPLICATE_SOURCE_EVENT.value)
            continue
        support_seen.add(event.source_event_key)
        if event.parent_episode_key in day.undone_source_event_keys:
            reasons.append(ReasonCode.UNDONE.value)
            continue
        units = require_non_negative("support units", event.units)
        support_by_parent[event.parent_episode_key] += units

    raw_support = 0.0
    for units in support_by_parent.values():
        capped = min(units, params.support_episode_cap)
        raw_support += capped
        if units > capped:
            reasons.append(ReasonCode.SUPPORT_EPISODE_CAP.value)
    support_cap = min(
        params.support_day_cap,
        max(params.support_day_floor, params.support_day_rate * core_baseline),
    )
    capped_support = min(raw_support, support_cap)
    applied_caps: list[str] = []
    if raw_support > capped_support:
        applied_caps.append(ReasonCode.SUPPORT_DAY_CAP.value)
        reasons.append(ReasonCode.SUPPORT_DAY_CAP.value)

    supplemental_seen: set[str] = set()
    raw_supplemental = routed_supplemental_raw
    for event in day.supplemental_events:
        if event.source_event_key in supplemental_seen:
            reasons.append(ReasonCode.DUPLICATE_SOURCE_EVENT.value)
            continue
        supplemental_seen.add(event.source_event_key)
        if event.source_event_key in day.undone_source_event_keys or not event.permanent_eligible:
            continue
        raw_supplemental += require_non_negative("supplemental units", event.units)
    supplemental_cap = min(
        params.supplemental_day_cap,
        params.supplemental_day_rate * core_baseline,
    )
    capped_supplemental = min(raw_supplemental, supplemental_cap)
    if raw_supplemental > capped_supplemental:
        applied_caps.append(ReasonCode.SUPPLEMENTAL_DAY_CAP.value)
        reasons.append(ReasonCode.SUPPLEMENTAL_DAY_CAP.value)

    volume, volume_reasons = volume_credit(qualified_volume, params)
    reasons.extend(volume_reasons)
    if ReasonCode.VOLUME_CAP_REACHED.value in volume_reasons:
        applied_caps.append(ReasonCode.VOLUME_CAP_REACHED.value)

    status = day.workload.status
    if not day.workload.snapshot_confident:
        status = CompletionStatus.SNAPSHOT_UNCERTAIN
    factor = params.completion_factor(status)
    completion = factor * min(
        params.completion_cap,
        params.completion_rate * qualified_volume,
    )
    if status is CompletionStatus.COLLECTION_CLEARED:
        reasons.append(ReasonCode.COLLECTION_CLEARED.value)
    elif status is CompletionStatus.SCOPE_CLEARED:
        reasons.append(ReasonCode.SCOPE_CLEARED.value)
    elif status is CompletionStatus.CONFIGURED_LIMIT_REACHED:
        reasons.append(ReasonCode.CONFIGURED_LIMIT_REACHED.value)
    elif status is CompletionStatus.ZERO_DUE:
        reasons.append(ReasonCode.ZERO_DUE.value)
    elif status is CompletionStatus.SNAPSHOT_UNCERTAIN:
        reasons.append(ReasonCode.SNAPSHOT_UNCERTAIN.value)

    total = core_baseline + core_context + capped_support + capped_supplemental + volume + completion
    return ReviewDayBreakdown(
        rule_version=params.rule_version,
        anki_day=day.anki_day,
        core_baseline=core_baseline,
        core_context=core_context,
        raw_support=raw_support,
        capped_support=capped_support,
        support_cap=support_cap,
        raw_supplemental=raw_supplemental,
        capped_supplemental=capped_supplemental,
        supplemental_cap=supplemental_cap,
        qualified_volume=qualified_volume,
        volume_credit=volume,
        completion_credit=completion,
        total=total,
        contribution_band=contribution_band(qualified_volume, status),
        applied_caps=tuple(dict.fromkeys(applied_caps)),
        reason_codes=tuple(dict.fromkeys(reasons)),
        episode_breakdowns=tuple(episode_breakdowns),
    )
