from __future__ import annotations

from dataclasses import dataclass

from .models import CompletionStatus, ConfidenceLevel, SupportKind


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

    def confidence(self, level: ConfidenceLevel) -> float:
        return dict(self.confidence_values)[level]

    def support_value(self, kind: SupportKind) -> float:
        return dict(self.support_values)[kind]

    def completion_factor(self, status: CompletionStatus) -> float:
        return dict(self.completion_factors)[status]


CURRENT_PARAMETERS = RewardParameterSet()
