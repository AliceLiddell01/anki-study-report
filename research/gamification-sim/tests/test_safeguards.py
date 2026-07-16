from __future__ import annotations

from gamification_sim.day_aggregation import aggregate_day
from gamification_sim.models import (
    DueRelation,
    EpisodeRole,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    Source,
    SupplementalInput,
)
from gamification_sim.validation import close


def ep(key, card="card", **kwargs):
    return ReviewEpisodeInput(key, card, "2026-07-16", kwargs.pop("outcome", Outcome.GOOD), **kwargs)


def test_source_event_idempotency():
    day = ReviewDayInput("2026-07-16", episodes=(ep("same"), ep("same")))
    result = aggregate_day(day)
    assert len(result.episode_breakdowns) == 1
    assert close(result.core_baseline, 0.90)
    assert "duplicate_source_event" in result.reason_codes


def test_card_day_core_uniqueness():
    day = ReviewDayInput("2026-07-16", episodes=(ep("one"), ep("two")))
    result = aggregate_day(day)
    assert len(result.episode_breakdowns) == 1
    assert "duplicate_card_day" in result.reason_codes


def test_undo_removes_original_and_related_support():
    day = ReviewDayInput(
        "2026-07-16",
        episodes=(ep("undo"),),
        undone_source_event_keys=frozenset({"undo"}),
    )
    result = aggregate_day(day)
    assert close(result.total, 0.0)
    assert "undone" in result.reason_codes


def test_administrative_manual_event_is_zero():
    day = ReviewDayInput(
        "2026-07-16",
        episodes=(
            ep(
                "admin",
                source=Source.MANUAL_OPERATION,
                role=EpisodeRole.ADMINISTRATIVE,
                administrative=True,
                outcome=Outcome.NONE,
            ),
        ),
    )
    assert close(aggregate_day(day).total, 0.0)


def test_preview_without_rescheduling_is_zero():
    day = ReviewDayInput(
        "2026-07-16",
        episodes=(ep("preview", source=Source.FILTERED_PREVIEW, preview_without_rescheduling=True),),
    )
    assert close(aggregate_day(day).total, 0.0)


def test_forced_due_routes_to_supplemental_channel():
    day = ReviewDayInput(
        "2026-07-16",
        episodes=(
            ep("core", "core-card"),
            ep("forced", "forced-card", due_relation=DueRelation.FORCED_DUE, forced_due=True, supplemental_units=0.2),
        ),
    )
    result = aggregate_day(day)
    assert close(result.raw_supplemental, 0.2)
    assert close(result.capped_supplemental, 0.027)
    assert "forced_due_supplemental" in result.reason_codes


def test_reason_codes_are_not_repeated():
    day = ReviewDayInput(
        "2026-07-16",
        episodes=(ep("same"), ep("same"), ep("same")),
        supplemental_events=(SupplementalInput("p", 5.0),),
    )
    result = aggregate_day(day)
    assert len(result.reason_codes) == len(set(result.reason_codes))
