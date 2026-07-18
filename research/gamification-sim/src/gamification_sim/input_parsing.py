from __future__ import annotations

from typing import Any

from .models import (
    CompletionStatus,
    ConfidenceLevel,
    DueRelation,
    EligibilityClass,
    EpisodeRole,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    Source,
    SupplementalInput,
    SupportEventInput,
    SupportKind,
    WorkloadSnapshot,
)
from .validation import require_binary_int, require_non_negative_int


def require_known_fields(data: dict[str, Any], *, allowed: frozenset[str], context: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"{context} contains unsupported field(s): {', '.join(unknown)}")


def memory_from_dict(data: dict[str, Any]) -> MemoryContext:
    return MemoryContext(
        retrievability_actual=data.get("retrievability_actual"),
        retrievability_natural_due=data.get("retrievability_natural_due"),
        stability_before=data.get("stability_before"),
        stability_good_counterfactual=data.get("stability_good_counterfactual"),
        confidence=ConfidenceLevel(data.get("confidence", "unavailable")),
    )


def episode_from_dict(data: dict[str, Any]) -> ReviewEpisodeInput:
    return ReviewEpisodeInput(
        source_event_key=data["source_event_key"],
        card_lineage=data["card_lineage"],
        anki_day=data["anki_day"],
        outcome=Outcome(data["outcome"]),
        eligibility_class=EligibilityClass(data.get("eligibility_class", "core")),
        due_relation=DueRelation(data.get("due_relation", "on_time")),
        source=Source(data.get("source", "normal_queue")),
        role=EpisodeRole(data.get("role", "primary")),
        memory=memory_from_dict(data.get("memory", {})),
        core_eligibility=require_binary_int("core_eligibility", data.get("core_eligibility", 1)),
        bonus_eligibility=data.get("bonus_eligibility", 1.0),
        response_validity=data.get("response_validity", 1.0),
        administrative=data.get("administrative", False),
        preview_without_rescheduling=data.get("preview_without_rescheduling", False),
        forced_due=data.get("forced_due", False),
        supplemental_units=data.get("supplemental_units", 0.0),
    )


def support_event_from_dict(data: dict[str, Any]) -> SupportEventInput:
    require_known_fields(
        data,
        allowed=frozenset({"source_event_key", "parent_episode_key", "kind"}),
        context="support event",
    )
    return SupportEventInput(
        source_event_key=data["source_event_key"],
        parent_episode_key=data["parent_episode_key"],
        kind=SupportKind(data.get("kind", "other")),
    )


def day_from_dict(data: dict[str, Any]) -> ReviewDayInput:
    workload_data = data.get("workload", {})
    episode_items = list(data.get("episodes", []))
    for group in data.get("repeat_episodes", []):
        count = require_non_negative_int("repeat_episodes count", group["count"])
        prefix = group.get("prefix", "generated-")
        template = dict(group.get("template", {}))
        for index in range(count):
            item = dict(template)
            item.setdefault("source_event_key", f"{prefix}{index}")
            item.setdefault("card_lineage", f"{prefix}card-{index}")
            item.setdefault("anki_day", data["anki_day"])
            item.setdefault("outcome", "good")
            episode_items.append(item)
    return ReviewDayInput(
        anki_day=data["anki_day"],
        episodes=tuple(episode_from_dict(item) for item in episode_items),
        support_events=tuple(support_event_from_dict(item) for item in data.get("support_events", [])),
        supplemental_events=tuple(
            SupplementalInput(
                source_event_key=item["source_event_key"],
                units=item["units"],
                permanent_eligible=item.get("permanent_eligible", True),
                reason=item.get("reason", "supplemental_practice"),
            )
            for item in data.get("supplemental_events", [])
        ),
        workload=WorkloadSnapshot(
            status=CompletionStatus(workload_data.get("status", "partial")),
            natural_due_at_start=require_non_negative_int(
                "workload.natural_due_at_start", workload_data.get("natural_due_at_start", 0)
            ),
            due_visible_under_limits=require_non_negative_int(
                "workload.due_visible_under_limits", workload_data.get("due_visible_under_limits", 0)
            ),
            due_hidden_by_limits=require_non_negative_int(
                "workload.due_hidden_by_limits", workload_data.get("due_hidden_by_limits", 0)
            ),
            snapshot_confident=workload_data.get("snapshot_confident", True),
        ),
        undone_source_event_keys=frozenset(data.get("undone_source_event_keys", [])),
        session_ids=tuple(data.get("session_ids", [])),
    )
