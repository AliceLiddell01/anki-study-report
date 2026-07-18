from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LongitudinalMode:
    mode_id: str
    horizon_days: int
    cohort_size: int
    replicas: int


@dataclass(frozen=True, slots=True)
class RetentionStep:
    start_day: int
    desired_retention: float


@dataclass(frozen=True, slots=True)
class LongitudinalPolicy:
    policy_id: str
    scheduler: str
    retention_timeline: tuple[RetentionStep, ...]
    delay_start_day: int | None
    delay_end_day: int | None
    review_limit: int

    def desired_retention(self, day: int) -> float:
        active = [step for step in self.retention_timeline if step.start_day <= day]
        return active[-1].desired_retention

    def reviews_enabled(self, day: int) -> bool:
        if self.delay_start_day is None or self.delay_end_day is None:
            return True
        return not self.delay_start_day <= day < self.delay_end_day


@dataclass(frozen=True, slots=True)
class LongitudinalConfig:
    version: str
    config_id: str
    start_date: str
    max_reviews_per_day: int
    modes: tuple[LongitudinalMode, ...]
    policies: tuple[LongitudinalPolicy, ...]
    parameter_set_ids: tuple[str, ...]
    digest: str

    def mode(self, mode_id: str) -> LongitudinalMode:
        for mode in self.modes:
            if mode.mode_id == mode_id:
                return mode
        raise ValueError(f"unknown longitudinal mode: {mode_id}")


@dataclass(frozen=True, slots=True)
class LongitudinalCardState:
    card_lineage_id: str
    created_day: int
    state_kind: str
    last_review_day: int | None
    next_due_day: int
    review_count: int
    lapse_count: int
    stability: float
    difficulty: float
    retrievability_at_last_update: float
    scheduled_interval: int
    desired_retention_policy: str
    preset_id: str
    active: bool
    fsrs_card: tuple[tuple[str, object], ...] | None


@dataclass(frozen=True, slots=True)
class LongitudinalReview:
    card_lineage_id: str
    day: int
    natural_due_day: int
    due_relation: str
    outcome: str
    retrievability: float
    desired_retention: float
    core_baseline: float
    core_context: float
    total_review_units: float
    next_due_day: int
    stability: float
    difficulty: float
