from __future__ import annotations

from dataclasses import replace

from .models import (
    DueRelation,
    EligibilityClass,
    EpisodeRole,
    ReasonCode,
    ReviewEpisodeInput,
    SafeguardDecision,
    Source,
)


def decide_safeguards(
    episode: ReviewEpisodeInput,
    *,
    seen_source_events: frozenset[str] = frozenset(),
    seen_core_card_days: frozenset[tuple[str, str]] = frozenset(),
    undone_source_event_keys: frozenset[str] = frozenset(),
) -> SafeguardDecision:
    reasons: list[str] = []
    effective_class = episode.eligibility_class
    core_eligibility = episode.core_eligibility
    bonus_eligibility = episode.bonus_eligibility
    no_op = False

    if episode.source_event_key in undone_source_event_keys:
        return SafeguardDecision(
            EligibilityClass.NONE, 0, 0.0, True, (ReasonCode.UNDONE.value,)
        )
    if episode.source_event_key in seen_source_events:
        return SafeguardDecision(
            EligibilityClass.NONE, 0, 0.0, True, (ReasonCode.DUPLICATE_SOURCE_EVENT.value,)
        )
    if (
        episode.administrative
        or episode.role is EpisodeRole.ADMINISTRATIVE
        or episode.source is Source.MANUAL_OPERATION
    ):
        return SafeguardDecision(
            EligibilityClass.NONE, 0, 0.0, True, (ReasonCode.ADMINISTRATIVE_ZERO.value,)
        )
    if episode.preview_without_rescheduling or episode.source is Source.FILTERED_PREVIEW:
        return SafeguardDecision(
            EligibilityClass.NONE, 0, 0.0, True, (ReasonCode.PREVIEW_ZERO.value,)
        )
    if episode.forced_due or episode.due_relation is DueRelation.FORCED_DUE:
        return SafeguardDecision(
            EligibilityClass.SUPPLEMENTAL,
            0,
            0.0,
            True,
            (ReasonCode.FORCED_DUE_SUPPLEMENTAL.value,),
        )
    if episode.eligibility_class is EligibilityClass.ROUTE_TO_LEARN:
        return SafeguardDecision(
            EligibilityClass.ROUTE_TO_LEARN,
            0,
            0.0,
            True,
            (ReasonCode.ROUTED_TO_LEARN.value,),
        )
    if episode.eligibility_class is not EligibilityClass.CORE:
        return SafeguardDecision(effective_class, 0, 0.0, True, (ReasonCode.CORE_INELIGIBLE.value,))
    card_day = (episode.card_lineage, episode.anki_day)
    if card_day in seen_core_card_days:
        return SafeguardDecision(
            EligibilityClass.NONE, 0, 0.0, True, (ReasonCode.DUPLICATE_CARD_DAY.value,)
        )
    return SafeguardDecision(
        EligibilityClass.CORE,
        core_eligibility,
        bonus_eligibility,
        no_op,
        (ReasonCode.CORE_ELIGIBLE.value,),
    )


def apply_decision(episode: ReviewEpisodeInput, decision: SafeguardDecision) -> ReviewEpisodeInput:
    return replace(
        episode,
        eligibility_class=decision.effective_class,
        core_eligibility=decision.core_eligibility,
        bonus_eligibility=decision.bonus_eligibility,
    )
