from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Outcome(StrEnum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"
    NONE = "none"

    @property
    def passed(self) -> bool:
        return self in {Outcome.HARD, Outcome.GOOD, Outcome.EASY}


class EligibilityClass(StrEnum):
    CORE = "core"
    SUPPORT = "support"
    SUPPLEMENTAL = "supplemental"
    NONE = "none"
    ROUTE_TO_LEARN = "route_to_learn"
    DEFERRED = "deferred"


class DueRelation(StrEnum):
    ON_TIME = "on_time"
    OVERDUE = "overdue"
    EARLY = "early"
    FORCED_DUE = "forced_due"
    UNKNOWN = "unknown"


class Source(StrEnum):
    NORMAL_QUEUE = "normal_queue"
    FILTERED_RESCHEDULING = "filtered_rescheduling"
    FILTERED_PREVIEW = "filtered_preview"
    REVIEW_AHEAD = "review_ahead"
    MANUAL_OPERATION = "manual_operation"
    IMPORTED_HISTORY = "imported_history"
    CUSTOM_SCHEDULER = "custom_scheduler"
    UNKNOWN = "unknown"


class EpisodeRole(StrEnum):
    PRIMARY = "primary"
    RECOVERY = "recovery"
    SUPPLEMENTAL = "supplemental"
    DUPLICATE = "duplicate"
    ADMINISTRATIVE = "administrative"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class SupportKind(StrEnum):
    FIRST_STEP = "first_step"
    SECOND_STEP = "second_step"
    COMPLETION = "completion"
    OTHER = "other"


class CompletionStatus(StrEnum):
    COLLECTION_CLEARED = "collection_cleared"
    SCOPE_CLEARED = "scope_cleared"
    CONFIGURED_LIMIT_REACHED = "configured_limit_reached"
    PARTIAL = "partial"
    ZERO_DUE = "zero_due"
    SNAPSHOT_UNCERTAIN = "snapshot_uncertain"


class ContributionBand(StrEnum):
    REVIEW_NONE = "review_none"
    REVIEW_LIGHT = "review_light"
    REVIEW_SUBSTANTIVE = "review_substantive"
    REVIEW_FULL = "review_full"


class ReasonCode(StrEnum):
    CORE_ELIGIBLE = "core_eligible"
    CORE_INELIGIBLE = "core_ineligible"
    NEUTRAL_CONTEXT = "neutral_context"
    MODEL_CONTEXT = "model_context"
    BONUS_SUPPRESSED = "bonus_suppressed"
    CORE_CAP_APPLIED = "core_cap_applied"
    DUPLICATE_SOURCE_EVENT = "duplicate_source_event"
    DUPLICATE_CARD_DAY = "duplicate_card_day"
    UNDONE = "undone"
    ADMINISTRATIVE_ZERO = "administrative_zero"
    PREVIEW_ZERO = "preview_zero"
    FORCED_DUE_SUPPLEMENTAL = "forced_due_supplemental"
    ROUTED_TO_LEARN = "routed_to_learn"
    SUPPORT_EPISODE_CAP = "support_episode_cap"
    SUPPORT_DAY_CAP = "support_day_cap"
    SUPPLEMENTAL_DAY_CAP = "supplemental_day_cap"
    VOLUME_TIER_1 = "volume_tier_1"
    VOLUME_TIER_2 = "volume_tier_2"
    VOLUME_TIER_3 = "volume_tier_3"
    VOLUME_TIER_4 = "volume_tier_4"
    VOLUME_CAP_REACHED = "volume_cap_reached"
    COLLECTION_CLEARED = "collection_cleared"
    SCOPE_CLEARED = "scope_cleared"
    CONFIGURED_LIMIT_REACHED = "configured_limit_reached"
    ZERO_DUE = "zero_due"
    SNAPSHOT_UNCERTAIN = "snapshot_uncertain"


@dataclass(frozen=True, slots=True)
class MemoryContext:
    retrievability_actual: float | None = None
    retrievability_natural_due: float | None = None
    stability_before: float | None = None
    stability_good_counterfactual: float | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNAVAILABLE


@dataclass(frozen=True, slots=True)
class ReviewEpisodeInput:
    source_event_key: str
    card_lineage: str
    anki_day: str
    outcome: Outcome
    eligibility_class: EligibilityClass = EligibilityClass.CORE
    due_relation: DueRelation = DueRelation.ON_TIME
    source: Source = Source.NORMAL_QUEUE
    role: EpisodeRole = EpisodeRole.PRIMARY
    memory: MemoryContext = field(default_factory=MemoryContext)
    core_eligibility: int = 1
    bonus_eligibility: float = 1.0
    response_validity: float = 1.0
    administrative: bool = False
    preview_without_rescheduling: bool = False
    forced_due: bool = False
    supplemental_units: float = 0.0


@dataclass(frozen=True, slots=True)
class SupportEventInput:
    source_event_key: str
    parent_episode_key: str
    units: float
    kind: SupportKind = SupportKind.OTHER


@dataclass(frozen=True, slots=True)
class SupplementalInput:
    source_event_key: str
    units: float
    permanent_eligible: bool = True
    reason: str = "supplemental_practice"


@dataclass(frozen=True, slots=True)
class WorkloadSnapshot:
    status: CompletionStatus = CompletionStatus.PARTIAL
    natural_due_at_start: int = 0
    due_visible_under_limits: int = 0
    due_hidden_by_limits: int = 0
    snapshot_confident: bool = True


@dataclass(frozen=True, slots=True)
class ReviewDayInput:
    anki_day: str
    episodes: tuple[ReviewEpisodeInput, ...] = ()
    support_events: tuple[SupportEventInput, ...] = ()
    supplemental_events: tuple[SupplementalInput, ...] = ()
    workload: WorkloadSnapshot = field(default_factory=WorkloadSnapshot)
    undone_source_event_keys: frozenset[str] = frozenset()
    session_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EpisodeRewardBreakdown:
    rule_version: str
    source_event_key: str
    baseline: float
    context: float
    total: float
    challenge_credit: float
    memory_gain_credit: float
    core_eligibility: int
    bonus_eligibility: float
    applied_caps: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SafeguardDecision:
    effective_class: EligibilityClass
    core_eligibility: int
    bonus_eligibility: float
    no_op: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewDayBreakdown:
    rule_version: str
    anki_day: str
    core_baseline: float
    core_context: float
    raw_support: float
    capped_support: float
    support_cap: float
    raw_supplemental: float
    capped_supplemental: float
    supplemental_cap: float
    qualified_volume: float
    volume_credit: float
    completion_credit: float
    total: float
    contribution_band: ContributionBand
    applied_caps: tuple[str, ...]
    reason_codes: tuple[str, ...]
    episode_breakdowns: tuple[EpisodeRewardBreakdown, ...]


def enum_value(value: Any) -> Any:
    return value.value if isinstance(value, StrEnum) else value
