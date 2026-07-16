from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import ReviewDayBreakdown, ReviewDayInput, ReviewEpisodeInput


class ScenarioCategory(StrEnum):
    ORDINARY = "ordinary"
    EDGE = "edge"
    CONTROL = "control"
    ABUSE = "abuse"
    REGRESSION = "regression"


class AssertionType(StrEnum):
    EQUALS = "equals"
    APPROXIMATELY_EQUALS = "approximately_equals"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    EQUALS_CONTROL = "equals_control"
    DELTA_FROM_CONTROL_LTE = "delta_from_control_lte"
    DELTA_FROM_CONTROL_GTE = "delta_from_control_gte"
    RATIO_TO_CONTROL_LTE = "ratio_to_control_lte"
    RATIO_TO_CONTROL_GTE = "ratio_to_control_gte"

    @property
    def requires_control(self) -> bool:
        return self in {
            AssertionType.EQUALS_CONTROL,
            AssertionType.DELTA_FROM_CONTROL_LTE,
            AssertionType.DELTA_FROM_CONTROL_GTE,
            AssertionType.RATIO_TO_CONTROL_LTE,
            AssertionType.RATIO_TO_CONTROL_GTE,
        }


class AssertionScope(StrEnum):
    DAY = "day"
    SCENARIO = "scenario"
    COMPARISON = "comparison"


class ScenarioMetric(StrEnum):
    CORE_BASELINE = "core_baseline"
    CORE_CONTEXT = "core_context"
    SUPPORT = "support"
    SUPPLEMENTAL = "supplemental"
    VOLUME_CREDIT = "volume_credit"
    COMPLETION_CREDIT = "completion_credit"
    TOTAL_REVIEW_UNITS = "total_review_units"
    QUALIFIED_VOLUME = "qualified_volume"
    UNIQUE_CORE_EPISODES = "unique_core_episodes"
    SUCCESSFUL_CORE_EPISODES = "successful_core_episodes"
    FAILED_CORE_EPISODES = "failed_core_episodes"
    BONUS_SHARE = "bonus_share"


@dataclass(frozen=True, slots=True)
class ScenarioAssertion:
    type: AssertionType
    scope: AssertionScope
    metric: ScenarioMetric
    expected: float
    tolerance: float
    anki_day: str | None = None
    control_scenario_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioSession:
    session_id: str
    episodes: tuple[ReviewEpisodeInput, ...]


@dataclass(frozen=True, slots=True)
class ScenarioDay:
    anki_day: str
    sessions: tuple[ScenarioSession, ...]
    day_input: ReviewDayInput


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    scenario_version: str
    scenario_id: str
    title: str
    category: ScenarioCategory
    rule_version: str
    description: str
    tags: tuple[str, ...]
    days: tuple[ScenarioDay, ...]
    assertions: tuple[ScenarioAssertion, ...]
    control_scenario_id: str | None = None
    comparison_basis: str | None = None
    comparison_note: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioDayResult:
    anki_day: str
    breakdown: ReviewDayBreakdown
    metrics: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class AssertionResult:
    assertion: ScenarioAssertion
    passed: bool
    observed: float | None
    control_value: float | None
    detail: str


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    scenario_id: str
    control_scenario_id: str
    deltas: tuple[tuple[str, float], ...]
    ratios: tuple[tuple[str, float | None], ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioRunResult:
    scenario_id: str
    category: ScenarioCategory
    rule_version: str
    day_results: tuple[ScenarioDayResult, ...]
    metrics: tuple[tuple[str, float], ...]
    assertions: tuple[AssertionResult, ...]
    comparison: ScenarioComparison | None
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.assertions)


@dataclass(frozen=True, slots=True)
class RunManifest:
    simulator_version: str
    rule_version: str
    scenario_schema_version: str
    python_version: str
    scenario_ids: tuple[str, ...]
    input_digest: str
    output_digest: str
    command: str


@dataclass(frozen=True, slots=True)
class CorpusRunResult:
    manifest: RunManifest
    scenario_results: tuple[ScenarioRunResult, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.scenario_results)
