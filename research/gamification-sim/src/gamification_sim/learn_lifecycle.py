from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence


class LifecycleError(ValueError):
    """Raised when a synthetic lifecycle trace is invalid or ambiguous."""


class LifecycleState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    INVALIDATED = "INVALIDATED"


class SubjectType(str, Enum):
    CARD = "CARD"
    NOTE = "NOTE"
    SIBLING_GROUP = "SIBLING_GROUP"


class EventKind(str, Enum):
    QUESTION_EXPOSURE = "QUESTION_EXPOSURE"
    SHOW_ANSWER = "SHOW_ANSWER"
    PREVIEW = "PREVIEW"
    VALID_INITIAL_ATTEMPT = "VALID_INITIAL_ATTEMPT"
    BOUNDED_PROGRESS = "BOUNDED_PROGRESS"
    REQUEST_PENDING = "REQUEST_PENDING"
    RATING_RECORDED = "RATING_RECORDED"
    INDEPENDENT_RETRIEVAL = "INDEPENDENT_RETRIEVAL"
    UNDO_SOURCE = "UNDO_SOURCE"
    EXPIRE_PENDING = "EXPIRE_PENDING"
    RESET_OR_FORGET = "RESET_OR_FORGET"
    DELETE_REIMPORT = "DELETE_REIMPORT"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    SESSION_BOUNDARY = "SESSION_BOUNDARY"
    CLOCK_SHIFT = "CLOCK_SHIFT"
    MANUAL_RESCHEDULE = "MANUAL_RESCHEDULE"
    FILTERED_DECK_REPETITION = "FILTERED_DECK_REPETITION"
    RELEARNING = "RELEARNING"
    DUPLICATE_REPLAY = "DUPLICATE_REPLAY"
    INVALIDATE_CONTINUITY = "INVALIDATE_CONTINUITY"


class Rating(str, Enum):
    NONE = "NONE"
    AGAIN = "AGAIN"
    HARD = "HARD"
    GOOD = "GOOD"
    EASY = "EASY"


class SignalStatus(str, Enum):
    NONE = "NONE"
    SAME_CHAIN_SUCCESS = "SAME_CHAIN_SUCCESS"
    INDEPENDENT_SUCCESS = "INDEPENDENT_SUCCESS"
    INDEPENDENT_FAILURE = "INDEPENDENT_FAILURE"
    AMBIGUOUS = "AMBIGUOUS"


class ContinuityStatus(str, Enum):
    STABLE = "STABLE"
    EXPLICIT = "EXPLICIT"
    LOST = "LOST"
    AMBIGUOUS = "AMBIGUOUS"


class ProvenanceStatus(str, Enum):
    VALID = "VALID"
    CANCELLED = "CANCELLED"
    CONFLICTING = "CONFLICTING"
    MISSING = "MISSING"


class TransitionReason(str, Enum):
    NON_REWARDABLE_IGNORED = "NON_REWARDABLE_IGNORED"
    VALID_ATTEMPT_STARTED = "VALID_ATTEMPT_STARTED"
    PROGRESS_RECORDED = "PROGRESS_RECORDED"
    PENDING_CREATED = "PENDING_CREATED"
    PENDING_ALREADY_EXISTS = "PENDING_ALREADY_EXISTS"
    SAME_CHAIN_NOT_CONFIRMATION = "SAME_CHAIN_NOT_CONFIRMATION"
    INDEPENDENT_CONFIRMATION = "INDEPENDENT_CONFIRMATION"
    DELAYED_FAILURE_NO_CONFIRMATION = "DELAYED_FAILURE_NO_CONFIRMATION"
    AMBIGUOUS_SIGNAL_PRESERVED = "AMBIGUOUS_SIGNAL_PRESERVED"
    PENDING_EXPIRED = "PENDING_EXPIRED"
    SOURCE_CANCELLED = "SOURCE_CANCELLED"
    CONTINUITY_INVALIDATED = "CONTINUITY_INVALIDATED"
    DUPLICATE_REPLAY_IGNORED = "DUPLICATE_REPLAY_IGNORED"
    RESET_NO_NEW_ACHIEVEMENT = "RESET_NO_NEW_ACHIEVEMENT"
    CONTINUITY_PRESERVED = "CONTINUITY_PRESERVED"
    CONFIRMED_TERMINAL_PRESERVED = "CONFIRMED_TERMINAL_PRESERVED"
    TERMINAL_STATE_PRESERVED = "TERMINAL_STATE_PRESERVED"
    CONFIGURATION_NEUTRAL = "CONFIGURATION_NEUTRAL"
    SESSION_TIME_NEUTRAL = "SESSION_TIME_NEUTRAL"
    RATING_ONLY_NEUTRAL = "RATING_ONLY_NEUTRAL"
    MISSING_SUBJECT_INVALIDATED = "MISSING_SUBJECT_INVALIDATED"
    MISSING_EPISODE_INVALIDATED = "MISSING_EPISODE_INVALIDATED"
    CONFLICTING_SUBJECT_INVALIDATED = "CONFLICTING_SUBJECT_INVALIDATED"


TERMINAL_STATES = frozenset(
    {
        LifecycleState.CONFIRMED,
        LifecycleState.EXPIRED,
        LifecycleState.CANCELLED,
        LifecycleState.INVALIDATED,
    }
)
NON_REWARDABLE_EVENTS = frozenset(
    {
        EventKind.QUESTION_EXPOSURE,
        EventKind.SHOW_ANSWER,
        EventKind.PREVIEW,
        EventKind.MANUAL_RESCHEDULE,
        EventKind.FILTERED_DECK_REPETITION,
        EventKind.RELEARNING,
    }
)
CONFIGURATION_EVENTS = frozenset({EventKind.CONFIGURATION_CHANGE})
SESSION_TIME_EVENTS = frozenset({EventKind.SESSION_BOUNDARY, EventKind.CLOCK_SHIFT})


@dataclass(frozen=True, slots=True)
class LearnEvent:
    event_id: str
    sequence_index: int
    event_kind: EventKind
    subject_type: SubjectType | None
    subject_id: str | None
    episode_id: str | None
    source_event_id: str | None = None
    rating: Rating = Rating.NONE
    signal_status: SignalStatus = SignalStatus.NONE
    continuity_status: ContinuityStatus = ContinuityStatus.STABLE
    provenance_status: ProvenanceStatus = ProvenanceStatus.VALID
    answer_revealed: bool = False
    scheduler_state_before: str | None = None
    scheduler_state_after: str | None = None
    anki_day_index: int | None = None
    monotonic_time_index: int | None = None
    session_id: str | None = None
    preset_id: str | None = None
    learning_step_profile_id: str | None = None


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    event_id: str
    sequence_index: int
    from_state: LifecycleState
    to_state: LifecycleState
    reason_code: TransitionReason
    subject_key: str | None
    episode_id: str | None


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    final_state: LifecycleState
    transition_ledger: tuple[TransitionRecord, ...]
    processed_event_ids: tuple[str, ...]
    ignored_duplicate_source_ids: tuple[str, ...]
    subject_key: str | None
    episode_id: str | None
    canonical_digest: str


def _canonical_payload(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _canonical_payload(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _canonical_payload(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_payload(item) for item in value]
    return value


def canonical_digest(value: Any) -> str:
    serialized = json.dumps(
        _canonical_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def event_from_dict(payload: Mapping[str, Any]) -> LearnEvent:
    allowed = {field.name for field in LearnEvent.__dataclass_fields__.values()}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise LifecycleError(f"unexpected event field(s): {', '.join(unknown)}")
    try:
        return LearnEvent(
            event_id=str(payload["event_id"]),
            sequence_index=int(payload["sequence_index"]),
            event_kind=EventKind(payload["event_kind"]),
            subject_type=SubjectType(payload["subject_type"]) if payload.get("subject_type") is not None else None,
            subject_id=payload.get("subject_id"),
            episode_id=payload.get("episode_id"),
            source_event_id=payload.get("source_event_id"),
            rating=Rating(payload.get("rating", "NONE")),
            signal_status=SignalStatus(payload.get("signal_status", "NONE")),
            continuity_status=ContinuityStatus(payload.get("continuity_status", "STABLE")),
            provenance_status=ProvenanceStatus(payload.get("provenance_status", "VALID")),
            answer_revealed=bool(payload.get("answer_revealed", False)),
            scheduler_state_before=payload.get("scheduler_state_before"),
            scheduler_state_after=payload.get("scheduler_state_after"),
            anki_day_index=payload.get("anki_day_index"),
            monotonic_time_index=payload.get("monotonic_time_index"),
            session_id=payload.get("session_id"),
            preset_id=payload.get("preset_id"),
            learning_step_profile_id=payload.get("learning_step_profile_id"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LifecycleError(f"invalid event payload: {exc}") from exc


def _validate_order(events: Sequence[LearnEvent]) -> None:
    if not events:
        raise LifecycleError("lifecycle trace must contain at least one event")
    event_ids: set[str] = set()
    previous_sequence = -1
    previous_time: int | None = None
    for event in events:
        if not event.event_id:
            raise LifecycleError("event_id must not be empty")
        if event.event_id in event_ids:
            raise LifecycleError(f"duplicate event_id: {event.event_id}")
        event_ids.add(event.event_id)
        if event.sequence_index <= previous_sequence:
            raise LifecycleError("sequence_index must be strictly increasing")
        previous_sequence = event.sequence_index
        if event.monotonic_time_index is not None:
            if previous_time is not None and event.monotonic_time_index < previous_time:
                raise LifecycleError("monotonic_time_index must be non-decreasing")
            previous_time = event.monotonic_time_index


def _subject_key(event: LearnEvent) -> str | None:
    if event.subject_type is None or not event.subject_id:
        return None
    return f"{event.subject_type.value}:{event.subject_id}"


def is_independent_confirmation_signal(event: LearnEvent) -> bool:
    return (
        event.event_kind is EventKind.INDEPENDENT_RETRIEVAL
        and event.signal_status is SignalStatus.INDEPENDENT_SUCCESS
        and event.source_event_id is not None
        and event.provenance_status is ProvenanceStatus.VALID
        and event.continuity_status in {ContinuityStatus.STABLE, ContinuityStatus.EXPLICIT}
    )


def _transition(
    *,
    state: LifecycleState,
    event: LearnEvent,
    expected_subject_key: str | None,
    expected_episode_id: str | None,
    seen_event_ids: set[str],
) -> tuple[LifecycleState, TransitionReason, str | None, str | None]:
    subject_key = _subject_key(event)

    if event.event_kind is EventKind.DUPLICATE_REPLAY:
        if not event.source_event_id or event.source_event_id not in seen_event_ids:
            return LifecycleState.INVALIDATED, TransitionReason.CONTINUITY_INVALIDATED, expected_subject_key, expected_episode_id
        return state, TransitionReason.DUPLICATE_REPLAY_IGNORED, expected_subject_key, expected_episode_id

    if subject_key is None:
        return LifecycleState.INVALIDATED, TransitionReason.MISSING_SUBJECT_INVALIDATED, expected_subject_key, expected_episode_id
    if not event.episode_id:
        return LifecycleState.INVALIDATED, TransitionReason.MISSING_EPISODE_INVALIDATED, expected_subject_key, expected_episode_id
    if expected_subject_key is not None and subject_key != expected_subject_key:
        return LifecycleState.INVALIDATED, TransitionReason.CONFLICTING_SUBJECT_INVALIDATED, expected_subject_key, expected_episode_id
    if expected_episode_id is not None and event.episode_id != expected_episode_id:
        return LifecycleState.INVALIDATED, TransitionReason.CONTINUITY_INVALIDATED, expected_subject_key, expected_episode_id
    expected_subject_key = expected_subject_key or subject_key
    expected_episode_id = expected_episode_id or event.episode_id

    if event.provenance_status in {ProvenanceStatus.CONFLICTING, ProvenanceStatus.MISSING}:
        return LifecycleState.INVALIDATED, TransitionReason.CONTINUITY_INVALIDATED, expected_subject_key, expected_episode_id
    if event.provenance_status is ProvenanceStatus.CANCELLED or event.event_kind is EventKind.UNDO_SOURCE:
        if state is LifecycleState.CONFIRMED:
            return state, TransitionReason.CONFIRMED_TERMINAL_PRESERVED, expected_subject_key, expected_episode_id
        if state in {LifecycleState.IN_PROGRESS, LifecycleState.PENDING}:
            return LifecycleState.CANCELLED, TransitionReason.SOURCE_CANCELLED, expected_subject_key, expected_episode_id
        return state, TransitionReason.TERMINAL_STATE_PRESERVED, expected_subject_key, expected_episode_id

    if state in TERMINAL_STATES:
        if state is LifecycleState.CONFIRMED:
            return state, TransitionReason.CONFIRMED_TERMINAL_PRESERVED, expected_subject_key, expected_episode_id
        return state, TransitionReason.TERMINAL_STATE_PRESERVED, expected_subject_key, expected_episode_id

    if event.event_kind in NON_REWARDABLE_EVENTS:
        return state, TransitionReason.NON_REWARDABLE_IGNORED, expected_subject_key, expected_episode_id
    if event.event_kind in CONFIGURATION_EVENTS:
        return state, TransitionReason.CONFIGURATION_NEUTRAL, expected_subject_key, expected_episode_id
    if event.event_kind in SESSION_TIME_EVENTS:
        return state, TransitionReason.SESSION_TIME_NEUTRAL, expected_subject_key, expected_episode_id
    if event.event_kind is EventKind.RATING_RECORDED:
        return state, TransitionReason.RATING_ONLY_NEUTRAL, expected_subject_key, expected_episode_id

    if event.event_kind in {EventKind.RESET_OR_FORGET, EventKind.DELETE_REIMPORT}:
        if event.continuity_status in {ContinuityStatus.LOST, ContinuityStatus.AMBIGUOUS}:
            return LifecycleState.INVALIDATED, TransitionReason.CONTINUITY_INVALIDATED, expected_subject_key, expected_episode_id
        return state, (
            TransitionReason.RESET_NO_NEW_ACHIEVEMENT
            if event.event_kind is EventKind.RESET_OR_FORGET
            else TransitionReason.CONTINUITY_PRESERVED
        ), expected_subject_key, expected_episode_id

    if event.event_kind is EventKind.INVALIDATE_CONTINUITY:
        return LifecycleState.INVALIDATED, TransitionReason.CONTINUITY_INVALIDATED, expected_subject_key, expected_episode_id

    if state is LifecycleState.NOT_STARTED:
        if event.event_kind is EventKind.VALID_INITIAL_ATTEMPT:
            return LifecycleState.IN_PROGRESS, TransitionReason.VALID_ATTEMPT_STARTED, expected_subject_key, expected_episode_id
        return state, TransitionReason.NON_REWARDABLE_IGNORED, expected_subject_key, expected_episode_id

    if state is LifecycleState.IN_PROGRESS:
        if event.event_kind is EventKind.BOUNDED_PROGRESS:
            return state, TransitionReason.PROGRESS_RECORDED, expected_subject_key, expected_episode_id
        if event.event_kind is EventKind.REQUEST_PENDING:
            return LifecycleState.PENDING, TransitionReason.PENDING_CREATED, expected_subject_key, expected_episode_id
        return state, TransitionReason.NON_REWARDABLE_IGNORED, expected_subject_key, expected_episode_id

    if state is LifecycleState.PENDING:
        if event.event_kind is EventKind.REQUEST_PENDING:
            return state, TransitionReason.PENDING_ALREADY_EXISTS, expected_subject_key, expected_episode_id
        if event.event_kind is EventKind.EXPIRE_PENDING:
            return LifecycleState.EXPIRED, TransitionReason.PENDING_EXPIRED, expected_subject_key, expected_episode_id
        if event.event_kind is EventKind.INDEPENDENT_RETRIEVAL:
            if event.signal_status in {SignalStatus.INDEPENDENT_SUCCESS, SignalStatus.INDEPENDENT_FAILURE}:
                if not event.source_event_id or event.source_event_id not in seen_event_ids:
                    raise LifecycleError("independent retrieval requires a processed source_event_id")
            if is_independent_confirmation_signal(event):
                return LifecycleState.CONFIRMED, TransitionReason.INDEPENDENT_CONFIRMATION, expected_subject_key, expected_episode_id
            if event.signal_status is SignalStatus.INDEPENDENT_FAILURE:
                return state, TransitionReason.DELAYED_FAILURE_NO_CONFIRMATION, expected_subject_key, expected_episode_id
            if event.signal_status is SignalStatus.SAME_CHAIN_SUCCESS:
                return state, TransitionReason.SAME_CHAIN_NOT_CONFIRMATION, expected_subject_key, expected_episode_id
            return state, TransitionReason.AMBIGUOUS_SIGNAL_PRESERVED, expected_subject_key, expected_episode_id
        return state, TransitionReason.NON_REWARDABLE_IGNORED, expected_subject_key, expected_episode_id

    raise LifecycleError(f"unhandled lifecycle state: {state.value}")


def evaluate_lifecycle(events: Iterable[LearnEvent | Mapping[str, Any]]) -> LifecycleResult:
    normalized = tuple(event if isinstance(event, LearnEvent) else event_from_dict(event) for event in events)
    _validate_order(normalized)

    state = LifecycleState.NOT_STARTED
    subject_key: str | None = None
    episode_id: str | None = None
    seen_event_ids: set[str] = set()
    ignored_duplicate_source_ids: list[str] = []
    ledger: list[TransitionRecord] = []

    for event in normalized:
        from_state = state
        state, reason, subject_key, episode_id = _transition(
            state=state,
            event=event,
            expected_subject_key=subject_key,
            expected_episode_id=episode_id,
            seen_event_ids=seen_event_ids,
        )
        if reason is TransitionReason.DUPLICATE_REPLAY_IGNORED and event.source_event_id:
            ignored_duplicate_source_ids.append(event.source_event_id)
        ledger.append(
            TransitionRecord(
                event_id=event.event_id,
                sequence_index=event.sequence_index,
                from_state=from_state,
                to_state=state,
                reason_code=reason,
                subject_key=subject_key,
                episode_id=episode_id,
            )
        )
        seen_event_ids.add(event.event_id)

    detached = {
        "final_state": state.value,
        "transition_ledger": [
            {
                "event_id": row.event_id,
                "sequence_index": row.sequence_index,
                "from_state": row.from_state.value,
                "to_state": row.to_state.value,
                "reason_code": row.reason_code.value,
                "subject_key": row.subject_key,
                "episode_id": row.episode_id,
            }
            for row in ledger
        ],
        "processed_event_ids": [event.event_id for event in normalized],
        "ignored_duplicate_source_ids": ignored_duplicate_source_ids,
        "subject_key": subject_key,
        "episode_id": episode_id,
    }
    return LifecycleResult(
        final_state=state,
        transition_ledger=tuple(ledger),
        processed_event_ids=tuple(event.event_id for event in normalized),
        ignored_duplicate_source_ids=tuple(ignored_duplicate_source_ids),
        subject_key=subject_key,
        episode_id=episode_id,
        canonical_digest=canonical_digest(detached),
    )
