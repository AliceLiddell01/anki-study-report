from __future__ import annotations

from .scenario_models import ScenarioComparison, ScenarioDefinition, ScenarioRunResult
from .validation import close

COMPARISON_METRICS = (
    "total_review_units",
    "core_baseline",
    "core_context",
    "support",
    "supplemental",
    "volume_credit",
    "completion_credit",
)


def metric_map(result: ScenarioRunResult) -> dict[str, float]:
    return dict(result.metrics)


def compare_results(
    scenario: ScenarioDefinition,
    result: ScenarioRunResult,
    control: ScenarioDefinition,
    control_result: ScenarioRunResult,
) -> ScenarioComparison:
    warnings: list[str] = []
    if scenario.rule_version != control.rule_version:
        warnings.append("rule versions differ")
    if len(scenario.days) != len(control.days):
        warnings.append("scenario horizons differ")
    scenario_cards = {episode.card_lineage for day in scenario.days for episode in day.day_input.episodes}
    control_cards = {episode.card_lineage for day in control.days for episode in day.day_input.episodes}
    if len(scenario_cards) != len(control_cards):
        warnings.append("unique card counts differ")
    scenario_opportunities = {
        (episode.card_lineage, episode.anki_day)
        for day in scenario.days
        for episode in day.day_input.episodes
    }
    control_opportunities = {
        (episode.card_lineage, episode.anki_day)
        for day in control.days
        for episode in day.day_input.episodes
    }
    if len(scenario_opportunities) != len(control_opportunities):
        warnings.append("core opportunity counts differ")

    def initial_memory(definition: ScenarioDefinition) -> tuple[tuple[str, str, object], ...]:
        first_by_opportunity: dict[tuple[str, str], object] = {}
        for day in definition.days:
            for episode in day.day_input.episodes:
                key = (episode.card_lineage, episode.anki_day)
                first_by_opportunity.setdefault(key, episode.memory)
        return tuple(
            (card, anki_day, memory)
            for (card, anki_day), memory in sorted(first_by_opportunity.items())
        )

    if initial_memory(scenario) != initial_memory(control):
        warnings.append("initial memory states differ")
    if warnings and scenario.comparison_basis == "documented-difference" and scenario.comparison_note:
        warnings.append(f"documented difference: {scenario.comparison_note}")

    values = metric_map(result)
    controls = metric_map(control_result)
    deltas = tuple((name, values[name] - controls[name]) for name in COMPARISON_METRICS)
    ratios = tuple(
        (name, None if close(controls[name], 0.0) else values[name] / controls[name])
        for name in COMPARISON_METRICS
    )
    return ScenarioComparison(
        scenario_id=scenario.scenario_id,
        control_scenario_id=control.scenario_id,
        deltas=deltas,
        ratios=ratios,
        warnings=tuple(warnings),
    )
