from __future__ import annotations

from dataclasses import dataclass

from .models import CompletionStatus, ConfidenceLevel, SupportKind
from .validation import require_non_negative, require_range


@dataclass(frozen=True, slots=True)
class RewardParameterSet:
    rule_version: str = "review-v0.1"
    attempt_credit: float = 0.25
    outcome_credit: float = 0.65
    neutral_context_credit: float = 0.10
    core_episode_cap: float = 1.32
    challenge_anchors: tuple[tuple[float, float], ...] = (
        (0.10, 0.15),
        (0.20, 0.25),
        (0.35, 0.30),
        (0.50, 0.30),
        (0.65, 0.22),
        (0.80, 0.12),
        (0.90, 0.05),
        (0.95, 0.00),
    )
    low_retrievability_credit: float = 0.10
    delay_credit_anchors: tuple[tuple[float, float], ...] = (
        (0.05, 1.00),
        (0.15, 0.85),
        (0.30, 0.65),
        (0.50, 0.45),
        (0.70, 0.25),
    )
    memory_gain_anchors: tuple[tuple[float, float], ...] = (
        (0.10, 0.00),
        (0.25, 0.03),
        (0.50, 0.06),
        (0.80, 0.09),
        (1.10, 0.12),
    )
    memory_gain_cap: float = 0.12
    confidence_values: tuple[tuple[ConfidenceLevel, float], ...] = (
        (ConfidenceLevel.HIGH, 1.00),
        (ConfidenceLevel.MEDIUM, 0.60),
        (ConfidenceLevel.LOW, 0.25),
        (ConfidenceLevel.UNAVAILABLE, 0.00),
    )
    support_values: tuple[tuple[SupportKind, float], ...] = (
        (SupportKind.FIRST_STEP, 0.05),
        (SupportKind.SECOND_STEP, 0.04),
        (SupportKind.COMPLETION, 0.03),
        (SupportKind.INTERDAY_RECOVERY, 0.12),
        (SupportKind.OTHER, 0.00),
    )
    support_episode_cap: float = 0.12
    support_day_floor: float = 0.50
    support_day_rate: float = 0.10
    support_day_cap: float = 3.00
    supplemental_day_rate: float = 0.03
    supplemental_day_cap: float = 2.00
    volume_tiers: tuple[tuple[float, float, float | None], ...] = (
        (10.0, 0.05, 25.0),
        (25.0, 0.08, 50.0),
        (50.0, 0.10, 100.0),
        (100.0, 0.12, None),
    )
    volume_cap: float = 15.0
    completion_rate: float = 0.03
    completion_cap: float = 3.0
    completion_factors: tuple[tuple[CompletionStatus, float], ...] = (
        (CompletionStatus.COLLECTION_CLEARED, 1.00),
        (CompletionStatus.SCOPE_CLEARED, 0.80),
        (CompletionStatus.CONFIGURED_LIMIT_REACHED, 0.50),
        (CompletionStatus.PARTIAL, 0.00),
        (CompletionStatus.ZERO_DUE, 0.00),
        (CompletionStatus.SNAPSHOT_UNCERTAIN, 0.00),
    )

    def __post_init__(self) -> None:
        if not isinstance(self.rule_version, str) or not self.rule_version.strip():
            raise ValueError("rule_version must be a non-empty string")
        for name in (
            "attempt_credit", "outcome_credit", "neutral_context_credit",
            "core_episode_cap", "low_retrievability_credit", "memory_gain_cap",
            "support_episode_cap", "support_day_floor", "support_day_rate",
            "support_day_cap", "supplemental_day_rate", "supplemental_day_cap",
            "volume_cap", "completion_rate", "completion_cap",
        ):
            require_non_negative(name, getattr(self, name))
        if self.core_episode_cap < self.attempt_credit + self.outcome_credit:
            raise ValueError("core_episode_cap must preserve the successful core baseline")
        self._validate_anchors("challenge_anchors", self.challenge_anchors, x_maximum=1.0)
        self._validate_anchors("delay_credit_anchors", self.delay_credit_anchors, x_maximum=1.0)
        self._validate_anchors("memory_gain_anchors", self.memory_gain_anchors)
        self._validate_enum_values("confidence_values", self.confidence_values, ConfidenceLevel, bounded=True)
        self._validate_enum_values("support_values", self.support_values, SupportKind)
        self._validate_enum_values("completion_factors", self.completion_factors, CompletionStatus, bounded=True)
        if not self.volume_tiers:
            raise ValueError("volume_tiers must not be empty")
        previous_start = -1.0
        for index, (start, rate, end) in enumerate(self.volume_tiers):
            require_non_negative(f"volume_tiers[{index}].start", start)
            require_non_negative(f"volume_tiers[{index}].rate", rate)
            if start <= previous_start:
                raise ValueError("volume_tiers starts must be strictly increasing")
            if end is not None and end <= start:
                raise ValueError("volume_tiers end must be greater than start")
            if index < len(self.volume_tiers) - 1 and end != self.volume_tiers[index + 1][0]:
                raise ValueError("volume_tiers must be contiguous")
            if index == len(self.volume_tiers) - 1 and end is not None:
                raise ValueError("final volume tier must be open-ended")
            previous_start = start

    @staticmethod
    def _validate_anchors(
        name: str,
        anchors: tuple[tuple[float, float], ...],
        *,
        x_maximum: float | None = None,
    ) -> None:
        if not anchors:
            raise ValueError(f"{name} must not be empty")
        previous = -1.0
        for index, (point, value) in enumerate(anchors):
            require_non_negative(f"{name}[{index}].point", point)
            require_non_negative(f"{name}[{index}].value", value)
            if x_maximum is not None:
                require_range(f"{name}[{index}].point", point, 0.0, x_maximum)
            if point <= previous:
                raise ValueError(f"{name} points must be strictly increasing")
            previous = point

    @staticmethod
    def _validate_enum_values(name, values, enum_type, *, bounded: bool = False) -> None:
        keys = [key for key, _ in values]
        if set(keys) != set(enum_type) or len(keys) != len(set(keys)):
            raise ValueError(f"{name} must contain every {enum_type.__name__} exactly once")
        for index, (_, value) in enumerate(values):
            if bounded:
                require_range(f"{name}[{index}]", value, 0.0, 1.0)
            else:
                require_non_negative(f"{name}[{index}]", value)

    def confidence(self, level: ConfidenceLevel) -> float:
        return dict(self.confidence_values)[level]

    def support_value(self, kind: SupportKind) -> float:
        return dict(self.support_values)[kind]

    def completion_factor(self, status: CompletionStatus) -> float:
        return dict(self.completion_factors)[status]


CURRENT_PARAMETERS = RewardParameterSet()
