from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical_json import canonical_digest
from .learn_lifecycle import (
    ContinuityStatus,
    EventKind,
    LearnEvent,
    LifecycleResult,
    LifecycleState,
    ProvenanceStatus,
    SignalStatus,
    TransitionReason,
    event_from_dict,
)
from .validation import dataclass_to_dict, require_finite


REFERENCE_FAMILY_ID = "REFERENCE"
REFERENCE_PARAMETERIZATION_ID = "P-NONE"
REFERENCE_DELAY_POLICY_ID = "D-NONE"
REFERENCE_STATUS = "REFERENCE_ONLY"
TERMINAL_NON_CONFIRMED = frozenset(
    {
        LifecycleState.EXPIRED,
        LifecycleState.CANCELLED,
        LifecycleState.INVALIDATED,
    }
)


@dataclass(frozen=True, slots=True)
class SubjectEvaluation:
    subject_strategy_id: str
    derived_key: str | None
    continuity: str
    collision_fragmentation_count: int
    source_subject_keys: tuple[str, ...]
    mapping_rule: str
    private_content_read: bool


@dataclass(frozen=True, slots=True)
class DelayEvaluation:
    delay_policy_id: str
    applicable: bool
    source_event_id: str | None
    confirmation_event_id: str | None
    source_exists_processed: bool
    source_is_pending_creation: bool
    same_achievement_subject: bool
    same_chain_excluded: bool
    minimum_elapsed_reached: bool
    minimum_anki_day_delta_reached: bool
    before_elapsed_expiry: bool
    before_anki_day_expiry: bool
    valid_provenance: bool
    scheduler_review_state_used: bool
    displayed_interval_used: bool
    elapsed_minutes: int | None
    anki_day_delta: int | None
    confirmation_eligible: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AllocationLedgerEntry:
    sequence_index: int
    event_id: str
    action: str
    pending_delta_lru: float
    confirmed_delta_lru: float
    current_pending_lru: float
    settled_total_lru: float


@dataclass(frozen=True, slots=True)
class AllocationResult:
    candidate_or_reference_id: str
    family_id: str
    parameterization_id: str
    subject_strategy_id: str
    delay_policy_id: str
    lifecycle_final_state: str
    pending_created: bool
    pending_creation_count: int
    duplicate_pending_count: int
    provisional_created_lru: float
    pending_lru: float
    confirmed_lru: float
    settled_total_lru: float
    current_total_lru: float
    terminal_disposition: str
    fresh_eligibility: bool
    spendable: bool
    subject: SubjectEvaluation
    delay: DelayEvaluation
    ledger: tuple[AllocationLedgerEntry, ...]
    allocation_digest: str


def normalize_events(events: Sequence[LearnEvent | Mapping[str, Any]]) -> tuple[LearnEvent, ...]:
    return tuple(event if isinstance(event, LearnEvent) else event_from_dict(event) for event in events)


def _source_subject_key(event: LearnEvent) -> str | None:
    if event.subject_type is None or not event.subject_id:
        return None
    return f"{event.subject_type.value}:{event.subject_id}"


def _note_projection(subject_id: str) -> str:
    explicit = {
        "card-original": "note-object-1",
        "card-reverse-cloze-duplicate": "note-object-1",
        "card-collision-a": "note-account-collision",
        "card-collision-b": "note-account-collision",
    }
    if subject_id in explicit:
        return explicit[subject_id]
    if subject_id.startswith("card-"):
        return "note-" + subject_id.removeprefix("card-")
    if subject_id.startswith("note-"):
        return subject_id
    if subject_id.startswith("siblings-"):
        return "note-" + subject_id.removeprefix("siblings-")
    return "note-projection-" + subject_id


def evaluate_subject_strategy(
    events: Sequence[LearnEvent | Mapping[str, Any]],
    subject_strategy_id: str,
) -> SubjectEvaluation:
    normalized = normalize_events(events)
    raw_keys = tuple(
        key
        for key in (_source_subject_key(event) for event in normalized)
        if key is not None
    )
    unique_raw = tuple(sorted(set(raw_keys)))
    if subject_strategy_id == "S-CARD":
        derived = tuple(
            sorted(
                {
                    f"CARD:{event.subject_id}"
                    for event in normalized
                    if event.subject_id is not None
                }
            )
        )
        rule = "SYNTHETIC_CARD_ID"
    elif subject_strategy_id == "S-NOTE-SIBLING":
        derived = tuple(
            sorted(
                {
                    "NOTE-SIBLING:" + _note_projection(event.subject_id)
                    for event in normalized
                    if event.subject_id is not None
                }
            )
        )
        rule = "SYNTHETIC_NOTE_DERIVED_SIBLING_GROUP"
    else:
        raise ValueError(f"unknown subject strategy: {subject_strategy_id}")

    if not derived:
        continuity = "AMBIGUOUS_FAIL_CLOSED"
        derived_key = None
        collision_count = 1
    elif len(derived) == 1:
        continuity = "STABLE"
        derived_key = derived[0]
        collision_count = 0
    else:
        continuity = "FRAGMENTED_FAIL_CLOSED"
        derived_key = None
        collision_count = len(derived) - 1

    return SubjectEvaluation(
        subject_strategy_id=subject_strategy_id,
        derived_key=derived_key,
        continuity=continuity,
        collision_fragmentation_count=collision_count,
        source_subject_keys=unique_raw,
        mapping_rule=rule,
        private_content_read=False,
    )


def _event_by_id(events: Sequence[LearnEvent]) -> dict[str, LearnEvent]:
    return {event.event_id: event for event in events}


def evaluate_delay_policy(
    events: Sequence[LearnEvent | Mapping[str, Any]],
    lifecycle: LifecycleResult,
    delay_policy: Mapping[str, Any] | None,
) -> DelayEvaluation:
    normalized = normalize_events(events)
    if delay_policy is None:
        return DelayEvaluation(
            delay_policy_id=REFERENCE_DELAY_POLICY_ID,
            applicable=False,
            source_event_id=None,
            confirmation_event_id=None,
            source_exists_processed=True,
            source_is_pending_creation=True,
            same_achievement_subject=True,
            same_chain_excluded=True,
            minimum_elapsed_reached=True,
            minimum_anki_day_delta_reached=True,
            before_elapsed_expiry=True,
            before_anki_day_expiry=True,
            valid_provenance=True,
            scheduler_review_state_used=False,
            displayed_interval_used=False,
            elapsed_minutes=None,
            anki_day_delta=None,
            confirmation_eligible=lifecycle.final_state is LifecycleState.CONFIRMED,
            failure_reasons=(),
        )

    policy_id = str(delay_policy["delay_policy_id"])
    processed = set(lifecycle.processed_event_ids)
    by_id = _event_by_id(normalized)
    ledger_by_event = {row.event_id: row for row in lifecycle.transition_ledger}
    confirmation = next(
        (
            event
            for event in normalized
            if event.event_kind is EventKind.INDEPENDENT_RETRIEVAL
            and event.signal_status is SignalStatus.INDEPENDENT_SUCCESS
        ),
        None,
    )
    source = by_id.get(confirmation.source_event_id) if confirmation and confirmation.source_event_id else None
    source_exists = bool(source and source.event_id in processed)
    source_transition = ledger_by_event.get(source.event_id) if source else None
    source_is_pending = bool(
        source
        and source.event_kind is EventKind.REQUEST_PENDING
        and source_transition
        and source_transition.reason_code in {
            TransitionReason.PENDING_CREATED,
            TransitionReason.PENDING_ALREADY_EXISTS,
        }
    )
    same_subject = bool(
        source
        and confirmation
        and source.subject_type == confirmation.subject_type
        and source.subject_id == confirmation.subject_id
        and source.episode_id == confirmation.episode_id
    )
    same_chain_excluded = bool(
        confirmation
        and confirmation.signal_status is SignalStatus.INDEPENDENT_SUCCESS
        and confirmation.event_kind is EventKind.INDEPENDENT_RETRIEVAL
    )
    valid_provenance = bool(
        confirmation
        and confirmation.provenance_status is ProvenanceStatus.VALID
        and confirmation.continuity_status in {ContinuityStatus.STABLE, ContinuityStatus.EXPLICIT}
    )

    elapsed: int | None = None
    day_delta: int | None = None
    if source and confirmation:
        if source.monotonic_time_index is not None and confirmation.monotonic_time_index is not None:
            elapsed = confirmation.monotonic_time_index - source.monotonic_time_index
        if source.anki_day_index is not None and confirmation.anki_day_index is not None:
            day_delta = confirmation.anki_day_index - source.anki_day_index

    min_elapsed = elapsed is not None and elapsed >= int(delay_policy["minimum_elapsed"])
    min_day = day_delta is not None and day_delta >= int(delay_policy["minimum_anki_day_delta"])
    before_elapsed_expiry = elapsed is not None and elapsed < int(delay_policy["expiry_elapsed"])
    before_day_expiry = day_delta is not None and day_delta < int(delay_policy["expiry_anki_day_delta"])

    failures: list[str] = []
    checks = (
        (confirmation is not None, "NO_INDEPENDENT_SUCCESS"),
        (source_exists, "SOURCE_NOT_PROCESSED"),
        (source_is_pending, "SOURCE_NOT_PENDING_CREATION"),
        (same_subject, "SUBJECT_OR_EPISODE_MISMATCH"),
        (same_chain_excluded, "SAME_CHAIN_OR_WRONG_SIGNAL"),
        (valid_provenance, "INVALID_PROVENANCE"),
        (min_elapsed, "MINIMUM_ELAPSED_NOT_REACHED"),
        (min_day, "MINIMUM_ANKI_DAY_DELTA_NOT_REACHED"),
        (before_elapsed_expiry, "ELAPSED_EXPIRY_REACHED"),
        (before_day_expiry, "ANKI_DAY_EXPIRY_REACHED"),
    )
    for passed, reason in checks:
        if not passed:
            failures.append(reason)

    eligible = not failures and lifecycle.final_state is LifecycleState.CONFIRMED
    return DelayEvaluation(
        delay_policy_id=policy_id,
        applicable=True,
        source_event_id=source.event_id if source else None,
        confirmation_event_id=confirmation.event_id if confirmation else None,
        source_exists_processed=source_exists,
        source_is_pending_creation=source_is_pending,
        same_achievement_subject=same_subject,
        same_chain_excluded=same_chain_excluded,
        minimum_elapsed_reached=min_elapsed,
        minimum_anki_day_delta_reached=min_day,
        before_elapsed_expiry=before_elapsed_expiry,
        before_anki_day_expiry=before_day_expiry,
        valid_provenance=valid_provenance,
        scheduler_review_state_used=False,
        displayed_interval_used=False,
        elapsed_minutes=elapsed,
        anki_day_delta=day_delta,
        confirmation_eligible=eligible,
        failure_reasons=tuple(failures),
    )


def _terminal_disposition(state: LifecycleState, confirmed: bool) -> str:
    if confirmed:
        return "CONFIRMED_SETTLED"
    return {
        LifecycleState.EXPIRED: "EXPIRED_VOID",
        LifecycleState.CANCELLED: "CANCELLED_VOID",
        LifecycleState.INVALIDATED: "INVALIDATED_VOID",
        LifecycleState.PENDING: "ACTIVE_PENDING",
        LifecycleState.IN_PROGRESS: "IN_PROGRESS",
        LifecycleState.NOT_STARTED: "NOT_STARTED",
        LifecycleState.CONFIRMED: "CONFIRMATION_REJECTED_BY_DELAY",
    }[state]


def evaluate_allocation(
    *,
    candidate_or_reference_id: str,
    family_id: str,
    parameterization_id: str,
    subject_strategy_id: str,
    delay_policy_id: str,
    pending_share_lru: float,
    confirmation_settlement_lru: float,
    events: Sequence[LearnEvent | Mapping[str, Any]],
    lifecycle: LifecycleResult,
    delay_policy: Mapping[str, Any] | None,
) -> AllocationResult:
    pending_share = require_finite("pending_share_lru", pending_share_lru)
    confirmation_share = require_finite(
        "confirmation_settlement_lru", confirmation_settlement_lru
    )
    if pending_share < 0.0 or confirmation_share < 0.0:
        raise ValueError("negative Learn allocation is forbidden")
    if pending_share + confirmation_share > 1.0:
        raise ValueError("Learn allocation total above 1.0 LRU is forbidden")

    subject = evaluate_subject_strategy(events, subject_strategy_id)
    delay = evaluate_delay_policy(events, lifecycle, delay_policy)
    pending_rows = [
        row
        for row in lifecycle.transition_ledger
        if row.reason_code is TransitionReason.PENDING_CREATED
    ]
    duplicate_rows = [
        row
        for row in lifecycle.transition_ledger
        if row.reason_code is TransitionReason.PENDING_ALREADY_EXISTS
    ]
    if len(pending_rows) > 1:
        raise ValueError("duplicate pending creation is forbidden")

    is_reference = family_id == REFERENCE_FAMILY_ID
    confirmed = (
        lifecycle.final_state is LifecycleState.CONFIRMED
        and delay.confirmation_eligible
        and subject.continuity == "STABLE"
    )
    active_pending = (
        lifecycle.final_state is LifecycleState.PENDING
        and bool(pending_rows)
        and subject.continuity == "STABLE"
    )

    provisional_created = 0.0 if is_reference else (pending_share if pending_rows else 0.0)
    pending_lru = 0.0 if is_reference or not active_pending else pending_share
    confirmed_lru = 0.0 if is_reference or not confirmed else confirmation_share
    settled_total = 0.0 if is_reference or not confirmed else pending_share + confirmation_share
    current_total = settled_total if confirmed else pending_lru

    if lifecycle.final_state in TERMINAL_NON_CONFIRMED:
        pending_lru = 0.0
        confirmed_lru = 0.0
        settled_total = 0.0
        current_total = 0.0
    if current_total < 0.0 or current_total > 1.0:
        raise ValueError("allocation current total outside [0, 1.0]")
    if settled_total < 0.0 or settled_total > 1.0:
        raise ValueError("allocation settled total outside [0, 1.0]")
    if is_reference and any(
        value != 0.0
        for value in (
            provisional_created,
            pending_lru,
            confirmed_lru,
            settled_total,
            current_total,
        )
    ):
        raise ValueError("reference allocation must remain zero")

    ledger: list[AllocationLedgerEntry] = []
    current_pending = 0.0
    current_settled = 0.0
    pending_event_ids = {row.event_id for row in pending_rows}
    confirmation_event_id = delay.confirmation_event_id if confirmed else None
    terminal_event_id = (
        lifecycle.transition_ledger[-1].event_id
        if lifecycle.final_state in TERMINAL_NON_CONFIRMED
        else None
    )
    normalized = normalize_events(events)
    for event in normalized:
        action = "NO_ALLOCATION_CHANGE"
        pending_delta = 0.0
        confirmed_delta = 0.0
        if not is_reference and event.event_id in pending_event_ids:
            action = "CREATE_PROVISIONAL" if pending_share else "PENDING_ACCOUNTING_ONLY"
            pending_delta = pending_share
            current_pending = pending_share
        if not is_reference and event.event_id == confirmation_event_id:
            action = "SETTLE_CONFIRMATION"
            pending_delta = -current_pending
            confirmed_delta = confirmation_share
            current_pending = 0.0
            current_settled = pending_share + confirmation_share
        if not is_reference and event.event_id == terminal_event_id:
            action = "VOID_TERMINAL"
            pending_delta = -current_pending
            current_pending = 0.0
            current_settled = 0.0
        ledger.append(
            AllocationLedgerEntry(
                sequence_index=event.sequence_index,
                event_id=event.event_id,
                action=action,
                pending_delta_lru=pending_delta,
                confirmed_delta_lru=confirmed_delta,
                current_pending_lru=current_pending,
                settled_total_lru=current_settled,
            )
        )

    detached = {
        "candidate_or_reference_id": candidate_or_reference_id,
        "family_id": family_id,
        "parameterization_id": parameterization_id,
        "subject_strategy_id": subject_strategy_id,
        "delay_policy_id": delay_policy_id,
        "lifecycle_final_state": lifecycle.final_state.value,
        "pending_created": bool(pending_rows),
        "pending_creation_count": len(pending_rows),
        "duplicate_pending_count": len(duplicate_rows),
        "provisional_created_lru": provisional_created,
        "pending_lru": pending_lru,
        "confirmed_lru": confirmed_lru,
        "settled_total_lru": settled_total,
        "current_total_lru": current_total,
        "terminal_disposition": _terminal_disposition(lifecycle.final_state, confirmed),
        "fresh_eligibility": lifecycle.final_state not in TERMINAL_NON_CONFIRMED
        and lifecycle.final_state is not LifecycleState.CONFIRMED,
        "spendable": False,
        "subject": dataclass_to_dict(subject),
        "delay": dataclass_to_dict(delay),
        "ledger": dataclass_to_dict(tuple(ledger)),
    }
    return AllocationResult(
        candidate_or_reference_id=candidate_or_reference_id,
        family_id=family_id,
        parameterization_id=parameterization_id,
        subject_strategy_id=subject_strategy_id,
        delay_policy_id=delay_policy_id,
        lifecycle_final_state=lifecycle.final_state.value,
        pending_created=bool(pending_rows),
        pending_creation_count=len(pending_rows),
        duplicate_pending_count=len(duplicate_rows),
        provisional_created_lru=provisional_created,
        pending_lru=pending_lru,
        confirmed_lru=confirmed_lru,
        settled_total_lru=settled_total,
        current_total_lru=current_total,
        terminal_disposition=_terminal_disposition(lifecycle.final_state, confirmed),
        fresh_eligibility=detached["fresh_eligibility"],
        spendable=False,
        subject=subject,
        delay=delay,
        ledger=tuple(ledger),
        allocation_digest=canonical_digest(detached),
    )
