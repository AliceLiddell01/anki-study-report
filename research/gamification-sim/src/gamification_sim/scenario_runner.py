from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .assertions import evaluate_assertion
from .canonical_json import canonical_digest
from .comparisons import compare_results
from .manifest import (
    OUTPUT_DIGEST_CONTRACT,
    SCENARIO_SCHEMA_VERSION,
    SIMULATOR_VERSION,
    python_major_minor,
)
from .models import Outcome, ReviewDayBreakdown
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .scenario_loader import load_corpus
from .scenario_models import (
    AssertionClass,
    AssertionScope,
    CorpusRunResult,
    RunManifest,
    ScenarioDay,
    ScenarioDayResult,
    ScenarioDefinition,
    ScenarioMetric,
    ScenarioRunResult,
)
from .day_aggregation import aggregate_day
from .output_digest import compute_output_digest


def _day_metrics(day: ScenarioDay, breakdown: ReviewDayBreakdown) -> dict[str, float]:
    accepted_keys = {item.source_event_key for item in breakdown.episode_breakdowns}
    by_source = {}
    for episode in day.day_input.episodes:
        by_source.setdefault(episode.source_event_key, episode)
    successful = sum(
        1
        for key in accepted_keys
        if key in by_source and by_source[key].outcome.passed
    )
    failed = sum(
        1
        for key in accepted_keys
        if key in by_source and by_source[key].outcome is Outcome.AGAIN
    )
    bonus = (
        breakdown.core_context
        + breakdown.capped_support
        + breakdown.capped_supplemental
        + breakdown.volume_credit
        + breakdown.completion_credit
    )
    return {
        ScenarioMetric.CORE_BASELINE.value: breakdown.core_baseline,
        ScenarioMetric.CORE_CONTEXT.value: breakdown.core_context,
        ScenarioMetric.SUPPORT.value: breakdown.capped_support,
        ScenarioMetric.SUPPLEMENTAL.value: breakdown.capped_supplemental,
        ScenarioMetric.VOLUME_CREDIT.value: breakdown.volume_credit,
        ScenarioMetric.COMPLETION_CREDIT.value: breakdown.completion_credit,
        ScenarioMetric.TOTAL_REVIEW_UNITS.value: breakdown.total,
        ScenarioMetric.QUALIFIED_VOLUME.value: breakdown.qualified_volume,
        ScenarioMetric.UNIQUE_CORE_EPISODES.value: float(len(breakdown.episode_breakdowns)),
        ScenarioMetric.SUCCESSFUL_CORE_EPISODES.value: float(successful),
        ScenarioMetric.FAILED_CORE_EPISODES.value: float(failed),
        ScenarioMetric.BONUS_SHARE.value: 0.0 if breakdown.total == 0 else bonus / breakdown.total,
    }


def _scenario_metrics(day_results: tuple[ScenarioDayResult, ...]) -> dict[str, float]:
    names = [item.value for item in ScenarioMetric if item is not ScenarioMetric.BONUS_SHARE]
    totals = {
        name: sum(dict(day.metrics)[name] for day in day_results)
        for name in names
    }
    bonus = (
        totals[ScenarioMetric.CORE_CONTEXT.value]
        + totals[ScenarioMetric.SUPPORT.value]
        + totals[ScenarioMetric.SUPPLEMENTAL.value]
        + totals[ScenarioMetric.VOLUME_CREDIT.value]
        + totals[ScenarioMetric.COMPLETION_CREDIT.value]
    )
    total = totals[ScenarioMetric.TOTAL_REVIEW_UNITS.value]
    totals[ScenarioMetric.BONUS_SHARE.value] = 0.0 if total == 0 else bonus / total
    return totals


def _value_for_assertion(
    definition: ScenarioDefinition,
    day_results: tuple[ScenarioDayResult, ...],
    scenario_metrics: dict[str, float],
    assertion,
) -> float:
    if assertion.scope is AssertionScope.SCENARIO or assertion.scope is AssertionScope.COMPARISON:
        return scenario_metrics[assertion.metric.value]
    for day in day_results:
        if day.anki_day == assertion.anki_day:
            return dict(day.metrics)[assertion.metric.value]
    raise ValueError(f"{definition.scenario_id}: assertion day not found: {assertion.anki_day}")


def run_scenario(
    definition: ScenarioDefinition,
    *,
    params: RewardParameterSet = CURRENT_PARAMETERS,
    parameter_set_id: str = "R-CURRENT",
    control_definition: ScenarioDefinition | None = None,
    control_result: ScenarioRunResult | None = None,
) -> ScenarioRunResult:
    requires_control = any(assertion.type.requires_control for assertion in definition.assertions)
    if definition.control_scenario_id:
        if control_definition is None or control_result is None:
            if requires_control:
                raise ValueError(
                    f"{definition.scenario_id}: resolved top-level control is required"
                )
        elif (
            control_definition.scenario_id != definition.control_scenario_id
            or control_result.scenario_id != definition.control_scenario_id
        ):
            raise ValueError(
                f"{definition.scenario_id}: resolved control does not match top-level control_scenario_id"
            )
    elif control_definition is not None or control_result is not None:
        raise ValueError(f"{definition.scenario_id}: unexpected resolved control")

    day_results: list[ScenarioDayResult] = []
    for day in definition.days:
        breakdown = aggregate_day(day.day_input, params)
        metrics = _day_metrics(day, breakdown)
        day_results.append(
            ScenarioDayResult(
                anki_day=day.anki_day,
                breakdown=breakdown,
                metrics=tuple(sorted(metrics.items())),
            )
        )
    frozen_days = tuple(day_results)
    scenario_metrics = _scenario_metrics(frozen_days)

    assertion_results = []
    for assertion in definition.assertions:
        if assertion.type.requires_control:
            continue
        applicable = (
            assertion.assertion_class is AssertionClass.INVARIANT
            or parameter_set_id in assertion.applies_to_parameter_set_ids
        )
        if not applicable:
            assertion_results.append(evaluate_assertion(assertion, observed=0.0, applicable=False))
            continue
        observed = _value_for_assertion(definition, frozen_days, scenario_metrics, assertion)
        assertion_results.append(evaluate_assertion(assertion, observed=observed))

    provisional = ScenarioRunResult(
        scenario_id=definition.scenario_id,
        category=definition.category,
        rule_version=params.rule_version,
        day_results=frozen_days,
        metrics=tuple(sorted(scenario_metrics.items())),
        assertions=tuple(assertion_results),
        comparison=None,
        warnings=(),
    )

    comparison = None
    warnings: tuple[str, ...] = ()
    if control_definition is not None and control_result is not None:
        comparison = compare_results(
            definition,
            provisional,
            control_definition,
            control_result,
        )
        warnings = comparison.warnings
        control_metrics = dict(control_result.metrics)
        for assertion in definition.assertions:
            if not assertion.type.requires_control:
                continue
            applicable = (
                assertion.assertion_class is AssertionClass.INVARIANT
                or parameter_set_id in assertion.applies_to_parameter_set_ids
            )
            if not applicable:
                assertion_results.append(evaluate_assertion(assertion, observed=0.0, applicable=False))
                continue
            observed = _value_for_assertion(definition, frozen_days, scenario_metrics, assertion)
            assertion_results.append(
                evaluate_assertion(
                    assertion,
                    observed=observed,
                    control_value=control_metrics[assertion.metric.value],
                )
            )

    return replace(
        provisional,
        assertions=tuple(assertion_results),
        comparison=comparison,
        warnings=warnings,
    )


def _execution_order(definitions: tuple[ScenarioDefinition, ...]) -> tuple[ScenarioDefinition, ...]:
    by_id = {item.scenario_id: item for item in definitions}
    ordered: list[ScenarioDefinition] = []
    visited: set[str] = set()

    def visit(item: ScenarioDefinition) -> None:
        if item.scenario_id in visited:
            return
        if item.control_scenario_id:
            visit(by_id[item.control_scenario_id])
        visited.add(item.scenario_id)
        ordered.append(item)

    for item in sorted(definitions, key=lambda value: value.scenario_id):
        visit(item)
    return tuple(ordered)


def run_definitions(
    definitions: tuple[ScenarioDefinition, ...],
    *,
    command: str,
    params: RewardParameterSet = CURRENT_PARAMETERS,
    parameter_set_id: str = "R-CURRENT",
) -> CorpusRunResult:
    by_id = {item.scenario_id: item for item in definitions}
    input_digest = canonical_digest(
        {
            "definitions": tuple(sorted(definitions, key=lambda item: item.scenario_id)),
            "parameters": params,
        }
    )
    results: dict[str, ScenarioRunResult] = {}
    warnings: list[str] = []
    for definition in _execution_order(definitions):
        control_definition = None
        control_result = None
        if definition.control_scenario_id:
            control_definition = by_id[definition.control_scenario_id]
            control_result = results[definition.control_scenario_id]
        result = run_scenario(
            definition,
            params=params,
            parameter_set_id=parameter_set_id,
            control_definition=control_definition,
            control_result=control_result,
        )
        results[definition.scenario_id] = result
        warnings.extend(result.warnings)

    ordered_results = tuple(results[key] for key in sorted(results))
    manifest = RunManifest(
        simulator_version=SIMULATOR_VERSION,
        rule_version=params.rule_version,
        parameter_set_id=parameter_set_id,
        scenario_schema_version=SCENARIO_SCHEMA_VERSION,
        python_version=python_major_minor(),
        scenario_ids=tuple(item.scenario_id for item in ordered_results),
        input_digest=input_digest,
        output_digest="",
        output_digest_contract=OUTPUT_DIGEST_CONTRACT,
        command=command,
    )
    provisional = CorpusRunResult(manifest, ordered_results, tuple(sorted(set(warnings))))
    digest = compute_output_digest(provisional)
    return replace(provisional, manifest=replace(manifest, output_digest=digest))


def run_corpus(
    root: Path,
    *,
    command: str = "run-scenarios",
    params: RewardParameterSet = CURRENT_PARAMETERS,
    parameter_set_id: str = "R-CURRENT",
) -> CorpusRunResult:
    return run_definitions(
        load_corpus(root),
        command=command,
        params=params,
        parameter_set_id=parameter_set_id,
    )
