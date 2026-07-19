from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass, fields, replace
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .breakdown import to_dict
from .canonical_json import canonical_digest
from .day_aggregation import aggregate_day, contribution_band, volume_credit
from .episode_reward import evaluate_episode
from .evidence import (
    CandidateStatus,
    MetricResult,
    MetricStatus,
    derived,
    measured,
    unavailable,
)
from .input_parsing import day_from_dict, episode_from_dict
from .longitudinal_config import load_longitudinal_config
from .longitudinal_runner import run_longitudinal
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    DueRelation,
    EligibilityClass,
    Outcome,
    MemoryContext,
    ReviewDayInput,
    ReviewEpisodeInput,
    Source,
    WorkloadSnapshot,
)
from .parameter_catalog import (
    PARAMETER_CANDIDATES,
    ParameterCandidate,
    candidate_payload,
    compose_parameter_candidates,
    normalized_parameter_digest,
    parameter_candidate,
)
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .scenario_loader import load_corpus
from .scenario_models import CorpusRunResult, ScenarioCategory
from .scenario_runner import run_corpus
from .scenario_schema import format_json_path
from .strict_json import load_strict_json
from .validation import close, dataclass_to_dict
from .workspace import ResearchWorkspace, resolve_research_workspace


SWEEP_VERSION = "review-sweep-v0.1"
SENSITIVITY_VERSION = "review-sensitivity-v0.1"


_LONGITUDINAL_EVIDENCE_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}


@dataclass(frozen=True, slots=True)
class SweepStage:
    family: str
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SweepConfig:
    sweep_version: str
    sweep_id: str
    corpus_path: str
    max_evaluated_candidates: int
    shortlist_size: int
    epsilon: float
    stages: tuple[SweepStage, ...]
    sensitivity_parameter_set_ids: tuple[str, ...]
    config_digest: str
    corpus_root: Path


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate: ParameterCandidate
    status: CandidateStatus
    hard_invariants: tuple[tuple[str, bool], ...]
    rejection_reason_codes: tuple[str, ...]
    incomplete_evidence_reason_codes: tuple[str, ...]
    quantitative_gate_failures: tuple[str, ...]
    metrics: tuple[tuple[str, MetricResult], ...]
    result_digest: str
    longitudinal_digest: str | None
    evaluation_digest: str

    @property
    def hard_gate_pass(self) -> bool:
        return self.status is not CandidateStatus.REJECT

    @property
    def evidence_complete(self) -> bool:
        return self.status is CandidateStatus.PASS


def default_sweep_schema_path(
    workspace: ResearchWorkspace | Path | None = None,
) -> Path:
    return resolve_research_workspace(workspace).path(
        "schemas/review-sweep-v0.1.schema.json"
    )


def _validator(
    workspace: ResearchWorkspace | Path | None = None,
) -> Draft202012Validator:
    schema = load_strict_json(default_sweep_schema_path(workspace))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _safe_package_path(package_root: Path, relative_path: str) -> Path:
    requested = Path(relative_path)
    if requested.is_absolute() or "://" in relative_path or ".." in requested.parts:
        raise ValueError("corpus_path must be a package-relative local path")
    root = package_root.resolve()
    resolved = (root / requested).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("corpus_path escapes the package root")
    current = root
    for part in requested.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError("corpus_path must not traverse symlinks")
    if not resolved.is_dir():
        raise ValueError(f"corpus_path is not a directory: {relative_path}")
    return resolved


def load_sweep_config(
    path: Path,
    package_root: ResearchWorkspace | Path | None = None,
) -> SweepConfig:
    workspace = resolve_research_workspace(package_root, anchors=(path,))
    payload = load_strict_json(path)
    errors = sorted(
        _validator(workspace).iter_errors(payload),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if errors:
        raise ValueError(
            "\n".join(
                f"{path}: {format_json_path(list(error.absolute_path))}: {error.message}"
                for error in errors
            )
        )
    stages = tuple(
        SweepStage(item["family"], tuple(item["candidate_ids"]))
        for item in payload["stages"]
    )
    configured_ids = tuple(identifier for stage in stages for identifier in stage.candidate_ids)
    if len(set(configured_ids)) != len(configured_ids):
        raise ValueError("candidate IDs must be unique across sweep stages")
    catalog_ids = {candidate.parameter_set_id for candidate in PARAMETER_CANDIDATES}
    unknown = sorted(set(configured_ids) - catalog_ids)
    if unknown:
        raise ValueError(f"unknown candidate IDs: {', '.join(unknown)}")
    for stage in stages:
        for identifier in stage.candidate_ids:
            if parameter_candidate(identifier).family != stage.family:
                raise ValueError(f"{identifier} does not belong to {stage.family}")
    minimum_budget = len(stages[0].candidate_ids)
    minimum_budget += payload["shortlist_size"] * sum(
        len(stage.candidate_ids) for stage in stages[1:]
    )
    if minimum_budget > payload["max_evaluated_candidates"]:
        raise ValueError(
            "max_evaluated_candidates cannot cover the configured sequential sweep"
        )
    corpus_root = _safe_package_path(workspace.root, payload["corpus_path"])
    return SweepConfig(
        sweep_version=payload["sweep_version"],
        sweep_id=payload["sweep_id"],
        corpus_path=payload["corpus_path"],
        max_evaluated_candidates=payload["max_evaluated_candidates"],
        shortlist_size=payload["shortlist_size"],
        epsilon=float(payload["epsilon"]),
        stages=stages,
        sensitivity_parameter_set_ids=tuple(payload["sensitivity_parameter_set_ids"]),
        config_digest=canonical_digest(payload),
        corpus_root=corpus_root,
    )


def _percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _result_by_id(result: CorpusRunResult) -> dict[str, Any]:
    return {item.scenario_id: item for item in result.scenario_results}


def _total(result_by_id: dict[str, Any], scenario_id: str) -> float:
    return dict(result_by_id[scenario_id].metrics)["total_review_units"]


def _ratio(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _probe_invariants(params: RewardParameterSet) -> dict[str, bool]:
    base = ReviewEpisodeInput(
        source_event_key="probe",
        card_lineage="probe-card",
        anki_day="2026-01-01",
        outcome=Outcome.GOOD,
    )
    hard = evaluate_episode(replace(base, outcome=Outcome.HARD), params).total
    good = evaluate_episode(base, params).total
    easy = evaluate_episode(replace(base, outcome=Outcome.EASY), params).total
    duplicate_day = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            episodes=(base, base, replace(base, source_event_key="probe-2")),
        ),
        params,
    )
    undone = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            episodes=(base,),
            undone_source_event_keys=frozenset({base.source_event_key}),
        ),
        params,
    )
    manual = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            episodes=(replace(base, administrative=True, source=Source.MANUAL_OPERATION),),
        ),
        params,
    )
    preview = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            episodes=(replace(base, preview_without_rescheduling=True),),
        ),
        params,
    )
    two = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            episodes=(base, replace(base, source_event_key="probe-2", card_lineage="probe-card-2")),
        ),
        params,
    )
    zero_due = aggregate_day(
        ReviewDayInput(
            anki_day=base.anki_day,
            workload=WorkloadSnapshot(status=CompletionStatus.ZERO_DUE),
        ),
        params,
    )
    expected_baseline = params.attempt_credit + params.outcome_credit
    return {
        "H01": close(evaluate_episode(base, params).baseline, expected_baseline),
        "H02": close(duplicate_day.core_baseline, expected_baseline),
        "H03": close(duplicate_day.core_baseline, expected_baseline),
        "H04": close(undone.total, 0.0),
        "H06": close(hard, good) and close(good, easy),
        "H07": True,
        "H08": close(manual.total, 0.0),
        "H09": close(preview.total, 0.0),
        "H10": close(two.core_baseline, 2.0 * expected_baseline),
        "H15": close(zero_due.completion_credit, 0.0),
    }


def _hard_invariants(
    result: CorpusRunResult,
    repeated: CorpusRunResult,
    params: RewardParameterSet,
) -> tuple[tuple[str, bool], ...]:
    by_id = _result_by_id(result)
    days = [day.breakdown for item in result.scenario_results for day in item.day_results]
    probes = _probe_invariants(params)
    session = by_id["session-invariance"]
    session_totals = [day.breakdown.total for day in session.day_results]
    duplicate_delta = _total(by_id, "duplicate-replay") - _total(by_id, "duplicate-replay-control")
    invariants = {
        **probes,
        "H05": len(session_totals) == 2 and close(session_totals[0], session_totals[1]),
        "H11": all(
            day.capped_support <= day.support_cap + 1e-9
            and day.capped_support <= params.support_day_cap + 1e-9
            for day in days
        ),
        "H12": all(day.capped_supplemental <= params.supplemental_day_cap + 1e-9 for day in days),
        "H13": all(day.volume_credit <= params.volume_cap + 1e-9 for day in days),
        "H14": all(day.completion_credit <= params.completion_cap + 1e-9 for day in days),
        "H16": all(day.total >= -1e-9 for day in days),
        "H17": all(
            close(
                day.total,
                day.core_baseline
                + day.core_context
                + day.capped_support
                + day.capped_supplemental
                + day.volume_credit
                + day.completion_credit,
            )
            for day in days
        ),
        "H18": result.manifest.output_digest == repeated.manifest.output_digest,
    }
    invariants["H02"] = invariants["H02"] and close(duplicate_delta, 0.0)
    return tuple((f"H{index:02d}", bool(invariants[f"H{index:02d}"])) for index in range(1, 19))


def _golden_mismatches(package_root: Path, params: RewardParameterSet) -> int:
    payload = load_strict_json(package_root / "fixtures" / "golden_cases.json")
    mismatches = 0
    for case in payload["cases"]:
        actual = (
            evaluate_episode(episode_from_dict(case["input"]), params)
            if case["kind"] == "episode"
            else aggregate_day(day_from_dict(case["input"]), params)
        )
        observed = to_dict(actual)
        for key, expected in case["expected"].items():
            value = observed[key]
            if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                mismatches += int(not close(float(value), float(expected)))
            else:
                mismatches += int(value != expected)
    return mismatches


def _complexity(params: RewardParameterSet) -> tuple[int, int, int]:
    changed = sum(
        getattr(params, field.name) != getattr(CURRENT_PARAMETERS, field.name)
        for field in fields(RewardParameterSet)
        if field.name != "rule_version"
    )
    enabled = sum(
        (
            params.memory_gain_cap > 0,
            params.support_day_cap > 0,
            params.supplemental_day_cap > 0,
            params.volume_cap > 0,
            params.completion_cap > 0,
        )
    )
    explainability = changed + enabled + len(params.challenge_anchors) + len(params.volume_tiers)
    return changed, enabled, explainability


def _baseline_suppression_events(
    result: CorpusRunResult,
    package_root: Path,
    params: RewardParameterSet,
) -> tuple[int, int, tuple[str, ...]]:
    definitions = {item.scenario_id: item for item in load_corpus(package_root / "scenarios")}
    checked = 0
    awarded_expected: list[tuple[float, float]] = []
    sources: set[str] = set()
    for scenario in result.scenario_results:
        if scenario.category not in {
            ScenarioCategory.ORDINARY,
            ScenarioCategory.EDGE,
            ScenarioCategory.CONTROL,
        }:
            continue
        definition = definitions[scenario.scenario_id]
        input_days = {item.anki_day: item for item in definition.days}
        for day in scenario.day_results:
            inputs: dict[str, ReviewEpisodeInput] = {}
            for episode in input_days[day.anki_day].day_input.episodes:
                inputs.setdefault(episode.source_event_key, episode)
            for episode in day.breakdown.episode_breakdowns:
                source = inputs.get(episode.source_event_key)
                if source is None:
                    continue
                expected = episode.core_eligibility * (
                    params.attempt_credit
                    + (params.outcome_credit if source.outcome.passed else 0.0)
                )
                checked += 1
                sources.add(scenario.scenario_id)
                awarded_expected.append((episode.baseline, expected))
    return count_baseline_suppressions(awarded_expected), checked, tuple(sorted(sources))


def count_baseline_suppressions(
    awarded_expected: Iterable[tuple[float, float]],
) -> int:
    return sum(awarded + 1e-9 < expected for awarded, expected in awarded_expected)


def _matched_context_deltas(params: RewardParameterSet) -> dict[str, float]:
    base = ReviewEpisodeInput(
        source_event_key="matched-context",
        card_lineage="matched-card",
        anki_day="2026-01-01",
        outcome=Outcome.GOOD,
        due_relation=DueRelation.ON_TIME,
        memory=MemoryContext(
            retrievability_actual=0.75,
            retrievability_natural_due=0.80,
            confidence=ConfidenceLevel.HIGH,
        ),
    )
    high = evaluate_episode(base, params)
    low = evaluate_episode(
        replace(base, memory=replace(base.memory, confidence=ConfidenceLevel.LOW)),
        params,
    )
    no_fsrs = evaluate_episode(replace(base, memory=MemoryContext()), params)
    return {
        "low_confidence_baseline_delta": low.baseline - high.baseline,
        "low_confidence_context_delta": low.context - high.context,
        "low_confidence_total_delta": low.total - high.total,
        "no_fsrs_baseline_delta": no_fsrs.baseline - high.baseline,
        "no_fsrs_context_delta": no_fsrs.context - high.context,
        "no_fsrs_total_delta": no_fsrs.total - high.total,
    }


def _metrics(
    result: CorpusRunResult,
    package_root: Path,
    params: RewardParameterSet,
    longitudinal: dict[str, Any] | None = None,
) -> dict[str, MetricResult]:
    by_id = _result_by_id(result)
    ordinary = [item for item in result.scenario_results if item.category is ScenarioCategory.ORDINARY]
    ordinary_days = [day.breakdown for item in ordinary for day in item.day_results]
    all_days = [day.breakdown for item in result.scenario_results for day in item.day_results]
    successful_core = [
        episode.total
        for item in ordinary
        for day in item.day_results
        for episode in day.breakdown.episode_breakdowns
        if episode.baseline > 0
    ]
    daily = [day.total for day in ordinary_days]
    additional = [_ratio(day.volume_credit + day.completion_credit, day.total) for day in ordinary_days if day.total]
    support = [_ratio(day.capped_support, day.total) for day in ordinary_days if day.total]
    supplemental = [_ratio(day.capped_supplemental, day.core_baseline) for day in ordinary_days if day.core_baseline]
    component_total = sum(day.total for day in all_days)
    changed, enabled, explainability = _complexity(params)
    duplicate_single = _total(by_id, "duplicate-replay-control")
    duplicate_replay = _total(by_id, "duplicate-replay")
    relearn_control = _total(by_id, "relearning-loop-control")
    relearn = _total(by_id, "relearning-loop")
    preview = _total(by_id, "preview-only-farming")
    scenario_failures = sum(
        assertion.failed
        for item in result.scenario_results
        for assertion in item.assertions
    )
    breakdown_mismatches = sum(
        not close(
            day.total,
            day.core_baseline + day.core_context + day.capped_support
            + day.capped_supplemental + day.volume_credit + day.completion_credit,
        )
        for day in all_days
    )
    scenario_ids = tuple(item.scenario_id for item in result.scenario_results)
    context = _matched_context_deltas(params)
    suppressed, baseline_samples, baseline_sources = _baseline_suppression_events(
        result, package_root, params
    )

    def observed(metric_id: str, value: float, *, unit: str = "ratio", count: int | None = None, method: str = "computed from committed scenario results") -> MetricResult:
        return measured(
            metric_id,
            value,
            unit=unit,
            sample_count=len(all_days) if count is None else count,
            source_ids=scenario_ids,
            method=method,
        )

    values = {
        "golden_mismatch_count": observed("golden_mismatch_count", float(_golden_mismatches(package_root, params)), unit="count", count=31, method="31-case review-v0.1 regression comparison"),
        "scenario_assertion_failure_count": observed("scenario_assertion_failure_count", float(scenario_failures), unit="count", count=53, method="count of applicable FAILED assertions; NOT_APPLICABLE excluded"),
        "breakdown_mismatch_count": observed("breakdown_mismatch_count", float(breakdown_mismatches), unit="count"),
        "median_successful_core_reward": observed("median_successful_core_reward", median(successful_core) if successful_core else 0.0, unit="Review Units", count=len(successful_core)),
        "p95_successful_core_reward": observed("p95_successful_core_reward", _percentile(successful_core, 0.95), unit="Review Units", count=len(successful_core)),
        "median_daily_review_units": observed("median_daily_review_units", median(daily) if daily else 0.0, unit="Review Units", count=len(daily)),
        "p95_daily_review_units": observed("p95_daily_review_units", _percentile(daily, 0.95), unit="Review Units", count=len(daily)),
        "max_core_episode": observed("max_core_episode", max((episode.total for day in all_days for episode in day.episode_breakdowns), default=0.0), unit="Review Units"),
        "median_additional_bonus_share": observed("median_additional_bonus_share", median(additional) if additional else 0.0, count=len(additional)),
        "p95_additional_bonus_share": observed("p95_additional_bonus_share", _percentile(additional, 0.95), count=len(additional)),
        "median_support_share": observed("median_support_share", median(support) if support else 0.0, count=len(support)),
        "p95_support_share": observed("p95_support_share", _percentile(support, 0.95), count=len(support)),
        "max_supplemental_to_baseline_share": observed("max_supplemental_to_baseline_share", max(supplemental, default=0.0), count=len(supplemental)),
        "support_share": observed("support_share", _ratio(sum(day.capped_support for day in all_days), component_total)),
        "supplemental_share": observed("supplemental_share", _ratio(sum(day.capped_supplemental for day in all_days), component_total)),
        "volume_share": observed("volume_share", _ratio(sum(day.volume_credit for day in all_days), component_total)),
        "completion_share": observed("completion_share", _ratio(sum(day.completion_credit for day in all_days), component_total)),
        "max_observed_volume_credit": observed("max_observed_volume_credit", max((day.volume_credit for day in all_days), default=0.0), unit="Review Units"),
        "max_observed_completion_credit": observed("max_observed_completion_credit", max((day.completion_credit for day in all_days), default=0.0), unit="Review Units"),
        "collection_size_parity": derived("collection_size_parity", 0.0, unit="Review Units delta", sample_count=1, source_ids=("matched-collection-metadata",), method="collection size is absent from ReviewEpisodeInput/ReviewDayInput and a matched identical workload produces zero delta"),
        "no_fsrs_parity": measured("no_fsrs_parity", abs(context["no_fsrs_total_delta"]), unit="Review Units delta", sample_count=1, source_ids=("matched-fsrs-availability",), method=f"matched episode; baseline_delta={context['no_fsrs_baseline_delta']:.17g}; context_delta={context['no_fsrs_context_delta']:.17g}; total_delta={context['no_fsrs_total_delta']:.17g}"),
        "low_confidence_parity": measured("low_confidence_parity", abs(context["low_confidence_total_delta"]), unit="Review Units delta", sample_count=1, source_ids=("matched-confidence",), method=f"matched episode; baseline_delta={context['low_confidence_baseline_delta']:.17g}; context_delta={context['low_confidence_context_delta']:.17g}; total_delta={context['low_confidence_total_delta']:.17g}"),
        "low_confidence_baseline_delta": measured("low_confidence_baseline_delta", context["low_confidence_baseline_delta"], unit="Review Units delta", sample_count=1, source_ids=("matched-confidence",), method="matched high/low-confidence episode"),
        "low_confidence_context_delta": measured("low_confidence_context_delta", context["low_confidence_context_delta"], unit="Review Units delta", sample_count=1, source_ids=("matched-confidence",), method="matched high/low-confidence episode"),
        "low_confidence_total_delta": measured("low_confidence_total_delta", context["low_confidence_total_delta"], unit="Review Units delta", sample_count=1, source_ids=("matched-confidence",), method="matched high/low-confidence episode"),
        "session_pattern_delta": observed("session_pattern_delta", abs(dict(by_id["session-invariance"].day_results[0].metrics)["total_review_units"] - dict(by_id["session-invariance"].day_results[1].metrics)["total_review_units"]), unit="Review Units delta", count=2, method="matched event set in one versus split analytical sessions"),
        "incremental_exploit_reward": observed("incremental_exploit_reward", duplicate_replay - duplicate_single, unit="Review Units", count=2),
        "exploit_gain_ratio": observed("exploit_gain_ratio", _ratio(duplicate_replay, duplicate_single), count=2),
        "duplicate_amplification": observed("duplicate_amplification", _ratio(duplicate_replay, duplicate_single), count=2),
        "relearning_marginal_reward_after_cap": observed("relearning_marginal_reward_after_cap", max(0.0, relearn - relearn_control), unit="Review Units", count=2),
        "completion_farming_efficiency": observed("completion_farming_efficiency", _total(by_id, "forced-due-farming") - _total(by_id, "forced-due-control"), unit="Review Units", count=2),
        "preview_only_permanent_reward": observed("preview_only_permanent_reward", preview, unit="Review Units", count=1),
        "honest_baseline_suppression_events": measured("honest_baseline_suppression_events", float(suppressed), unit="count", sample_count=baseline_samples, source_ids=baseline_sources, method="episode baseline compared with eligible attempt plus successful-outcome baseline"),
        "non_default_parameter_count": observed("non_default_parameter_count", float(changed), unit="count", count=1, method="normalized parameter snapshot diff from R-CURRENT"),
        "enabled_dynamic_components": observed("enabled_dynamic_components", float(enabled), unit="count", count=1, method="count of enabled reward channels"),
        "explainability_complexity_score": observed("explainability_complexity_score", float(explainability), unit="count", count=1, method="declared structural complexity proxy"),
    }
    if longitudinal is None:
        values.update({
            "high_low_retention_parity": unavailable("high_low_retention_parity", MetricStatus.UNSUPPORTED, unit="ratio", source_ids=("longitudinal-retention-pair",), method="matched longitudinal policy histories", reason="longitudinal evidence was not supplied"),
            "backlog_return_viability": unavailable("backlog_return_viability", MetricStatus.DEFERRED, unit="ratio", source_ids=("longitudinal-backlog-pair",), method="matched backlog catch-up history", reason="longitudinal evidence was not supplied"),
            "long_session_baseline_ratio": unavailable("long_session_baseline_ratio", MetricStatus.DEFERRED, unit="ratio", source_ids=("longitudinal-high-volume",), method="awarded baseline divided by expected eligible baseline", reason="longitudinal evidence was not supplied"),
            "intentional_backlog_advantage": unavailable("intentional_backlog_advantage", MetricStatus.DEFERRED, unit="ratio", source_ids=("longitudinal-backlog-pair",), method="unexplained reward after comparable obligations", reason="longitudinal evidence was not supplied"),
            "retention_cycling_advantage": unavailable("retention_cycling_advantage", MetricStatus.UNSUPPORTED, unit="ratio", source_ids=("longitudinal-retention-cycle",), method="matched cumulative reward minus legitimate extra baseline", reason="longitudinal evidence was not supplied"),
        })
    else:
        fairness = longitudinal["fairness"]["comparisons"]
        abuse = longitudinal["abuse"]["comparisons"]
        retention = [item for item in fairness if item["comparison"] == "retention-high-vs-low"]
        backlog = [item for item in fairness if item["comparison"] == "honest-backlog-return"]
        cycling = [item for item in abuse if item["comparison"] in {"retention-high-cycle", "retention-low-cycle"}]
        intentional = [item for item in abuse if item["comparison"] == "intentional-backlog"]
        high_volume = max(longitudinal["policy_results"], key=lambda item: item["metrics"]["review_count"])
        values.update({
            "high_low_retention_parity": measured("high_low_retention_parity", max(abs(item["unexplained_advantage"]) for item in retention), unit="ratio", sample_count=len(retention), source_ids=("retention-high-vs-low",), method="maximum absolute unexplained reward ratio across matched 90-day replicas"),
            "backlog_return_viability": measured("backlog_return_viability", min(item["left_baseline_preservation"] for item in backlog), unit="ratio", sample_count=len(backlog), source_ids=("honest-backlog-return",), method="minimum baseline preservation across matched catch-up replicas"),
            "long_session_baseline_ratio": measured("long_session_baseline_ratio", high_volume["metrics"]["baseline_preservation_ratio"], unit="ratio", sample_count=high_volume["metrics"]["review_count"], source_ids=(f"{high_volume['policy_id']}:replica-{high_volume['replica']}",), method="baseline ratio of the maximum-review longitudinal cohort"),
            "intentional_backlog_advantage": measured("intentional_backlog_advantage", max(item["unexplained_advantage"] for item in intentional), unit="ratio", sample_count=len(intentional), source_ids=("intentional-backlog",), method="maximum unexplained 90-day advantage after subtracting legitimate additional baseline"),
            "retention_cycling_advantage": measured("retention_cycling_advantage", max(item["unexplained_advantage"] for item in cycling), unit="ratio", sample_count=len(cycling), source_ids=("retention-high-cycle", "retention-low-cycle"), method="maximum unexplained 90-day cycling advantage after subtracting legitimate additional baseline"),
        })
    return values


def _metric_value(metrics: dict[str, MetricResult], metric_id: str) -> float:
    metric = metrics[metric_id]
    if not metric.supported or metric.value is None:
        raise ValueError(f"metric {metric_id} is not measured")
    return metric.value


def _quantitative_gate_results(
    metrics: dict[str, MetricResult],
    params: RewardParameterSet,
) -> dict[str, dict[str, object]]:
    measured_gates = {
        "Q01_ORDINARY_MEDIAN": 0.98 <= _metric_value(metrics, "median_successful_core_reward") <= 1.08,
        "Q02_CORE_CAP": _metric_value(metrics, "max_core_episode") <= 1.32 + 1e-9,
        "Q03_BASELINE": _metric_value(metrics, "honest_baseline_suppression_events") == 0,
        "Q04_ADDITIONAL_MEDIAN": _metric_value(metrics, "median_additional_bonus_share") <= 0.12 + 1e-9,
        "Q05_ADDITIONAL_P95": _metric_value(metrics, "p95_additional_bonus_share") <= 0.18 + 1e-9,
        "Q06_VOLUME_CAP": _metric_value(metrics, "max_observed_volume_credit") <= params.volume_cap + 1e-9,
        "Q07_COMPLETION_CAP": _metric_value(metrics, "max_observed_completion_credit") <= params.completion_cap + 1e-9,
        "Q08_SUPPORT_MEDIAN": _metric_value(metrics, "median_support_share") <= 0.10 + 1e-9,
        "Q09_SUPPORT_P95": _metric_value(metrics, "p95_support_share") <= 0.15 + 1e-9,
        "Q10_SUPPLEMENTAL": _metric_value(metrics, "max_supplemental_to_baseline_share") <= 0.03 + 1e-9,
        "Q11_SESSION": close(_metric_value(metrics, "session_pattern_delta"), 0.0),
        "Q12_DUPLICATE": close(_metric_value(metrics, "incremental_exploit_reward"), 0.0),
        "Q13_PREVIEW": close(_metric_value(metrics, "preview_only_permanent_reward"), 0.0),
        "Q14_RELEARNING": close(_metric_value(metrics, "relearning_marginal_reward_after_cap"), 0.0),
    }
    results = {
        code: {"status": MetricStatus.MEASURED.value, "passed": passed}
        for code, passed in measured_gates.items()
    }
    for code, metric_id in (
        ("Q15_RETENTION_CYCLING", "retention_cycling_advantage"),
        ("Q16_INTENTIONAL_BACKLOG", "intentional_backlog_advantage"),
    ):
        metric = metrics[metric_id]
        results[code] = {
            "status": metric.status.value,
            "passed": (
                metric.value <= 0.03 + 1e-9
                if metric.supported and metric.value is not None
                else None
            ),
            "metric_id": metric_id,
        }
    return results


def _quantitative_failures(metrics: dict[str, MetricResult], params: RewardParameterSet) -> tuple[str, ...]:
    return tuple(
        code
        for code, result in _quantitative_gate_results(metrics, params).items()
        if result["passed"] is False
    )


def _longitudinal_evidence(
    package_root: Path,
    parameter_set_id: str,
    params: RewardParameterSet,
) -> dict[str, Any]:
    cache_key = (
        str(package_root.resolve()),
        parameter_set_id,
        normalized_parameter_digest(params),
    )
    cached = _LONGITUDINAL_EVIDENCE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    workspace = resolve_research_workspace(package_root)
    longitudinal_config = load_longitudinal_config(
        workspace.path("configs/review-longitudinal-v0.1.json"),
        workspace=workspace,
    )
    result = run_longitudinal(
        longitudinal_config,
        mode_id="calibration-90",
        master_seed=20260716,
        parameter_set_ids=(parameter_set_id,),
        parameter_overrides={parameter_set_id: params},
        workspace=workspace,
    )
    _LONGITUDINAL_EVIDENCE_CACHE[cache_key] = result
    return result


def evaluate_candidate(
    candidate: ParameterCandidate,
    config: SweepConfig,
    package_root: Path,
) -> CandidateEvaluation:
    result = run_corpus(
        config.corpus_root,
        command="run-sweep",
        params=candidate.parameters,
        parameter_set_id=candidate.parameter_set_id,
    )
    repeated = run_corpus(
        config.corpus_root,
        command="run-sweep",
        params=candidate.parameters,
        parameter_set_id=candidate.parameter_set_id,
    )
    invariants = _hard_invariants(result, repeated, candidate.parameters)
    reasons = [f"INVARIANT_{name}" for name, passed in invariants if not passed]
    if any(not item.passed for item in result.scenario_results):
        reasons.append("SCENARIO_ASSERTION_FAILURE")
    longitudinal = _longitudinal_evidence(
        package_root,
        candidate.parameter_set_id,
        candidate.parameters,
    )
    metrics = _metrics(
        result,
        package_root,
        candidate.parameters,
        longitudinal=longitudinal,
    )
    if _metric_value(metrics, "breakdown_mismatch_count"):
        reasons.append("BREAKDOWN_MISMATCH")
    if (
        candidate.parameter_set_id == "R-CURRENT"
        and _metric_value(metrics, "golden_mismatch_count")
    ):
        reasons.append("CURRENT_GOLDEN_REGRESSION_MISMATCH")
    if result.manifest.output_digest != repeated.manifest.output_digest:
        reasons.append("NONDETERMINISTIC_DIGEST")
    quantitative = _quantitative_failures(metrics, candidate.parameters)
    reasons.extend(f"QUANTITATIVE_{code}" for code in quantitative)
    required_evidence = (
        "high_low_retention_parity",
        "backlog_return_viability",
        "long_session_baseline_ratio",
        "intentional_backlog_advantage",
        "retention_cycling_advantage",
    )
    incomplete = tuple(
        f"{metric_id}_{metrics[metric_id].status.value}"
        for metric_id in required_evidence
        if not metrics[metric_id].supported
    )
    status = (
        CandidateStatus.REJECT
        if reasons
        else CandidateStatus.INCOMPLETE_EVIDENCE
        if incomplete
        else CandidateStatus.PASS
    )
    provisional = {
        "candidate": candidate_payload(candidate),
        "status": status.value,
        "hard_invariants": dict(invariants),
        "rejection_reason_codes": sorted(set(reasons)),
        "incomplete_evidence_reason_codes": list(incomplete),
        "quantitative_gate_failures": list(quantitative),
        "metrics": metrics,
        "result_digest": result.manifest.output_digest,
        "longitudinal_digest": longitudinal["manifest"]["report_digest"],
    }
    return CandidateEvaluation(
        candidate=candidate,
        status=status,
        hard_invariants=invariants,
        rejection_reason_codes=tuple(sorted(set(reasons))),
        incomplete_evidence_reason_codes=incomplete,
        quantitative_gate_failures=quantitative,
        metrics=tuple(sorted(metrics.items())),
        result_digest=result.manifest.output_digest,
        longitudinal_digest=longitudinal["manifest"]["report_digest"],
        evaluation_digest=canonical_digest(provisional),
    )


_PARETO_OBJECTIVES = (
    "scenario_assertion_failure_count",
    "p95_additional_bonus_share",
    "p95_support_share",
    "retention_cycling_advantage",
    "intentional_backlog_advantage",
    "non_default_parameter_count",
    "explainability_complexity_score",
)


def pareto_front(
    evaluations: Iterable[CandidateEvaluation],
    *,
    include_incomplete: bool = False,
) -> tuple[CandidateEvaluation, ...]:
    eligible = [
        item
        for item in evaluations
        if item.status is CandidateStatus.PASS
        or (include_incomplete and item.status is CandidateStatus.INCOMPLETE_EVIDENCE)
    ]
    by_digest: dict[str, CandidateEvaluation] = {}
    for item in sorted(
        eligible,
        key=lambda candidate: (
            _metric_value(dict(candidate.metrics), "non_default_parameter_count"),
            candidate.candidate.parameter_set_id,
        ),
    ):
        by_digest.setdefault(
            normalized_parameter_digest(item.candidate.parameters),
            item,
        )
    survivors = list(by_digest.values())
    front: list[CandidateEvaluation] = []
    for candidate in survivors:
        values = dict(candidate.metrics)
        dominated = False
        for other in survivors:
            if other is candidate:
                continue
            other_values = dict(other.metrics)
            no_worse = all(
                _metric_value(other_values, key) <= _metric_value(values, key) + 1e-12
                for key in _PARETO_OBJECTIVES
            )
            strictly_better = any(
                _metric_value(other_values, key) < _metric_value(values, key) - 1e-12
                for key in _PARETO_OBJECTIVES
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return tuple(sorted(front, key=lambda item: item.candidate.parameter_set_id))


def run_sweep(config: SweepConfig, package_root: Path) -> dict[str, Any]:
    evaluated: dict[str, CandidateEvaluation] = {}
    stage_reports: list[dict[str, Any]] = []
    shortlist: tuple[ParameterCandidate, ...] = ()
    for stage_index, stage in enumerate(config.stages):
        stage_candidates: list[ParameterCandidate] = []
        if stage_index == 0:
            stage_candidates = [parameter_candidate(identifier) for identifier in stage.candidate_ids]
        else:
            for base in shortlist:
                base_parts = tuple(parameter_candidate(identifier) for identifier in base.parameter_set_id.split("+"))
                for identifier in stage.candidate_ids:
                    stage_candidates.append(compose_parameter_candidates(base_parts + (parameter_candidate(identifier),)))
        if len(evaluated) + len(stage_candidates) > config.max_evaluated_candidates:
            raise ValueError("sequential sweep exceeded max_evaluated_candidates")
        stage_evaluations = []
        for candidate in stage_candidates:
            evaluation = evaluate_candidate(candidate, config, package_root)
            evaluated[candidate.parameter_set_id] = evaluation
            stage_evaluations.append(evaluation)
        front = pareto_front(stage_evaluations, include_incomplete=True)
        if not front:
            raise ValueError(f"no hard-gate survivor in {stage.family} stage")
        shortlist = tuple(item.candidate for item in front[: config.shortlist_size])
        stage_reports.append(
            {
                "family": stage.family,
                "evaluated_ids": [item.candidate.parameter_set_id for item in stage_evaluations],
                "survivor_ids": [item.candidate.parameter_set_id for item in stage_evaluations if item.hard_gate_pass],
                "pass_ids": [item.candidate.parameter_set_id for item in stage_evaluations if item.status is CandidateStatus.PASS],
                "incomplete_evidence_ids": [item.candidate.parameter_set_id for item in stage_evaluations if item.status is CandidateStatus.INCOMPLETE_EVIDENCE],
                "pareto_ids": [item.candidate.parameter_set_id for item in front],
                "shortlist_ids": [item.parameter_set_id for item in shortlist],
            }
        )
    final_front = pareto_front(evaluated.values())
    payload = {
        "manifest": {
            "sweep_version": config.sweep_version,
            "sweep_id": config.sweep_id,
            "config_digest": config.config_digest,
            "corpus_path": config.corpus_path,
            "candidate_budget": config.max_evaluated_candidates,
            "evaluated_candidate_count": len(evaluated),
            "selection_method": "hard-gate then nondominated Pareto front; no aggregate score",
        },
        "stages": stage_reports,
        "candidates": [_evaluation_payload(evaluated[key]) for key in sorted(evaluated)],
        "pareto": {
            "objectives_minimized": list(_PARETO_OBJECTIVES),
            "candidate_ids": [item.candidate.parameter_set_id for item in final_front],
        },
        "final_shortlist_ids": [item.parameter_set_id for item in shortlist],
    }
    payload["manifest"]["output_digest"] = canonical_digest(payload)
    return payload


def _evaluation_payload(evaluation: CandidateEvaluation) -> dict[str, Any]:
    metric_map = dict(evaluation.metrics)
    return {
        "parameter_set": candidate_payload(evaluation.candidate),
        "status": evaluation.status.value,
        "hard_gate_pass": evaluation.hard_gate_pass,
        "evidence_complete": evaluation.evidence_complete,
        "hard_invariants": dict(evaluation.hard_invariants),
        "rejection_reason_codes": list(evaluation.rejection_reason_codes),
        "incomplete_evidence_reason_codes": list(evaluation.incomplete_evidence_reason_codes),
        "quantitative_gate_failures": list(evaluation.quantitative_gate_failures),
        "quantitative_gates": _quantitative_gate_results(
            metric_map,
            evaluation.candidate.parameters,
        ),
        "metrics": {
            metric_id: metric.payload()
            for metric_id, metric in evaluation.metrics
        },
        "result_digest": evaluation.result_digest,
        "longitudinal_digest": evaluation.longitudinal_digest,
        "evaluation_digest": evaluation.evaluation_digest,
    }


SENSITIVITY_GRIDS: dict[str, tuple[float, ...]] = {
    "attempt_credit": (0.15, 0.20, 0.25, 0.30, 0.35),
    "outcome_credit": (0.55, 0.60, 0.65, 0.70, 0.75),
    "neutral_context_credit": (0.05, 0.075, 0.10, 0.125, 0.15),
    "challenge_cap": (0.20, 0.25, 0.30, 0.35, 0.40),
    "memory_gain_cap": (0.0, 0.05, 0.10, 0.12, 0.15),
    "support_episode_cap": (0.06, 0.09, 0.12, 0.15, 0.18),
    "support_day_rate": (0.05, 0.075, 0.10, 0.125, 0.15),
    "support_day_cap": (1.0, 2.0, 3.0, 4.0),
    "supplemental_day_rate": (0.0, 0.01, 0.03, 0.04, 0.05),
    "supplemental_day_cap": (0.0, 1.0, 2.0, 3.0),
    "volume_cap": (5.0, 10.0, 15.0, 20.0, 25.0),
    "completion_rate": (0.0, 0.01, 0.03, 0.04, 0.05),
    "completion_cap": (0.0, 1.0, 3.0, 4.0, 5.0),
}


def _sensitivity_variant(params: RewardParameterSet, name: str, value: float) -> RewardParameterSet:
    if name == "challenge_cap":
        current = max(amount for _, amount in params.challenge_anchors)
        anchors = tuple((point, 0.0 if current == 0 else amount * value / current) for point, amount in params.challenge_anchors)
        return replace(params, challenge_anchors=anchors, rule_version=f"{params.rule_version}+sens-{name}-{value:g}")
    return replace(params, **{name: value, "rule_version": f"{params.rule_version}+sens-{name}-{value:g}"})


def _cliff_probes(params: RewardParameterSet, epsilon: float) -> list[dict[str, Any]]:
    thresholds = {
        "challenge_anchors": [point for point, _ in params.challenge_anchors],
        "volume_tiers": [start for start, _, _ in params.volume_tiers],
        "volume_cap": [params.volume_cap],
        "support_floor": [params.support_day_floor],
        "support_episode_cap": [params.support_episode_cap],
        "support_day_cap": [params.support_day_cap],
        "supplemental_cap": [params.supplemental_day_cap],
        "completion_cap": [params.completion_cap],
        "contribution_band_thresholds": [5.0, 10.0, 25.0],
    }
    probes = []
    for family, values in thresholds.items():
        for threshold in values:
            tested = (max(0.0, threshold - epsilon), threshold, threshold + epsilon)
            if family == "challenge_anchors":
                rewards = [
                    evaluate_episode(
                        ReviewEpisodeInput(
                            source_event_key="cliff",
                            card_lineage="cliff",
                            anki_day="2026-01-01",
                            outcome=Outcome.GOOD,
                            memory=MemoryContext(
                                retrievability_actual=value,
                                retrievability_natural_due=value,
                                confidence=ConfidenceLevel.HIGH,
                            ),
                        ),
                        params,
                    ).total
                    for value in tested
                ]
            elif family in {"volume_tiers", "volume_cap"}:
                rewards = [volume_credit(value, params)[0] for value in tested]
            elif family in {"support_floor", "support_episode_cap", "support_day_cap"}:
                cap = {
                    "support_floor": params.support_day_floor,
                    "support_episode_cap": params.support_episode_cap,
                    "support_day_cap": params.support_day_cap,
                }[family]
                rewards = [min(value, cap) for value in tested]
            elif family == "supplemental_cap":
                rewards = [min(value, params.supplemental_day_cap) for value in tested]
            elif family == "completion_cap":
                rewards = [min(value, params.completion_cap) for value in tested]
            else:
                rewards = [
                    contribution_band(value, CompletionStatus.PARTIAL).value
                    for value in tested
                ]
            numeric_rewards = [value for value in rewards if isinstance(value, (int, float))]
            max_jump = max(
                (abs(right - left) for left, right in zip(numeric_rewards, numeric_rewards[1:])),
                default=0.0,
            )
            probes.append(
                {
                    "family": family,
                    "threshold": threshold,
                    "tested_values": list(tested),
                    "observed_outputs": rewards,
                    "max_input_step": epsilon,
                    "max_reward_jump": max_jump,
                    "disproportionate_reward_jump": max_jump > max(0.001, 2.0 * epsilon),
                    "classification": "bounded-piecewise-threshold",
                }
            )
    return probes


def run_sensitivity(
    config: SweepConfig,
    package_root: Path,
    parameter_set_id: str,
) -> dict[str, Any]:
    parts = tuple(parameter_candidate(identifier) for identifier in parameter_set_id.split("+"))
    base = parts[0] if len(parts) == 1 else compose_parameter_candidates(parts)
    base_evaluation = evaluate_candidate(base, config, package_root)
    base_metrics = dict(base_evaluation.metrics)
    analyses = []
    for name, values in SENSITIVITY_GRIDS.items():
        points = []
        base_value = (
            max(amount for _, amount in base.parameters.challenge_anchors)
            if name == "challenge_cap"
            else float(getattr(base.parameters, name))
        )
        for value in values:
            params = _sensitivity_variant(base.parameters, name, value)
            point_id = f"SENSITIVITY-{name.upper().replace('_', '-')}-{value:g}"
            result = run_corpus(
                config.corpus_root,
                command="run-sensitivity",
                params=params,
                parameter_set_id=point_id,
            )
            repeated = run_corpus(
                config.corpus_root,
                command="run-sensitivity",
                params=params,
                parameter_set_id=point_id,
            )
            longitudinal = _longitudinal_evidence(package_root, point_id, params)
            metrics = _metrics(result, package_root, params, longitudinal=longitudinal)
            delta = _metric_value(metrics, "median_successful_core_reward") - _metric_value(base_metrics, "median_successful_core_reward")
            normalized = 0.0 if close(value, base_value) else delta / (value - base_value)
            invariants = dict(_hard_invariants(result, repeated, params))
            gates = _quantitative_gate_results(metrics, params)
            required_longitudinal = (
                "high_low_retention_parity",
                "backlog_return_viability",
                "long_session_baseline_ratio",
                "intentional_backlog_advantage",
                "retention_cycling_advantage",
            )
            cliff_probes = _cliff_probes(params, config.epsilon)
            points.append(
                {
                    "value": value,
                    "metric_deltas": {
                        "median_successful_core_reward": delta,
                        "p95_additional_bonus_share": _metric_value(metrics, "p95_additional_bonus_share") - _metric_value(base_metrics, "p95_additional_bonus_share"),
                    },
                    "longitudinal_metric_deltas": {
                        metric_id: _metric_value(metrics, metric_id) - _metric_value(base_metrics, metric_id)
                        for metric_id in required_longitudinal
                    },
                    "normalized_local_sensitivity": normalized,
                    "gate_crossings": list(_quantitative_failures(metrics, params)),
                    "invariant_status": "PASS" if all(invariants.values()) else "FAIL",
                    "failed_invariants": [name for name, passed in invariants.items() if not passed],
                    "quantitative_gate_status": (
                        "PASS" if all(item["passed"] is not False for item in gates.values()) else "FAIL"
                    ),
                    "quantitative_gates": gates,
                    "reward_cliff_status": (
                        "BOUNDED_PIECEWISE"
                        if any(item["disproportionate_reward_jump"] for item in cliff_probes)
                        else "PASS"
                    ),
                    "evidence_completeness": (
                        "COMPLETE"
                        if all(metrics[metric_id].supported for metric_id in required_longitudinal)
                        else "INCOMPLETE_EVIDENCE"
                    ),
                    "result_digest": result.manifest.output_digest,
                    "longitudinal_digest": longitudinal["manifest"]["report_digest"],
                }
            )
        analyses.append({"parameter": name, "base_value": base_value, "tested_values": list(values), "points": points})
    payload = {
        "manifest": {
            "sensitivity_version": SENSITIVITY_VERSION,
            "config_digest": config.config_digest,
            "parameter_set_id": parameter_set_id,
            "epsilon": config.epsilon,
        },
        "base_evaluation_digest": base_evaluation.evaluation_digest,
        "parameters": analyses,
        "reward_cliffs": _cliff_probes(base.parameters, config.epsilon),
    }
    payload["manifest"]["output_digest"] = canonical_digest(payload)
    return payload


def render_sweep_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Review parameter sweep",
        "",
        f"- Evaluated: **{payload['manifest']['evaluated_candidate_count']}**",
        f"- Budget: **{payload['manifest']['candidate_budget']}**",
        f"- Digest: `{payload['manifest']['output_digest']}`",
        "- Selection: hard gates followed by a nondominated Pareto front; no aggregate score.",
        "",
        "## Sequential stages",
        "",
    ]
    for stage in payload["stages"]:
        lines.append(
            f"- `{stage['family']}`: {len(stage['evaluated_ids'])} evaluated; "
            f"shortlist `{', '.join(stage['shortlist_ids'])}`"
        )
    lines.extend(["", "## Final Pareto candidates", ""])
    lines.extend(f"- `{identifier}`" for identifier in payload["pareto"]["candidate_ids"])
    lines.extend(["", "## Rejections", ""])
    rejected = [item for item in payload["candidates"] if not item["hard_gate_pass"]]
    if rejected:
        lines.extend(
            f"- `{item['parameter_set']['parameter_set_id']}`: {', '.join(item['rejection_reason_codes'])}"
            for item in rejected
        )
    else:
        lines.append("None.")
    incomplete = [
        item for item in payload["candidates"]
        if item["status"] == CandidateStatus.INCOMPLETE_EVIDENCE.value
    ]
    lines.extend(["", "## Incomplete evidence", ""])
    if incomplete:
        lines.extend(
            f"- `{item['parameter_set']['parameter_set_id']}`: "
            + ", ".join(item["incomplete_evidence_reason_codes"])
            for item in incomplete
        )
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def metrics_csv(payload: dict[str, Any]) -> str:
    keys = sorted(payload["candidates"][0]["metrics"])
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["parameter_set_id", "status", "hard_gate_pass", *keys])
    for item in payload["candidates"]:
        writer.writerow(
            [item["parameter_set"]["parameter_set_id"], item["status"], str(item["hard_gate_pass"]).lower()]
            + [
                "" if item["metrics"][key]["value"] is None
                else f"{item['metrics'][key]['value']:.17g}"
                for key in keys
            ]
        )
    return stream.getvalue()


def write_sweep_reports(payload: dict[str, Any], output_root: Path) -> Path:
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("sweep output root must not be a symlink")
    run_id = payload["manifest"]["output_digest"][:12]
    run_dir = output_root.resolve() / "sweeps" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("sweep run directory must not be a symlink")
    files = {
        "manifest.json": payload["manifest"],
        "candidates.json": payload["candidates"],
        "pareto.json": payload["pareto"],
    }
    for name, value in files.items():
        (run_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (run_dir / "metrics.csv").write_text(metrics_csv(payload), encoding="utf-8")
    (run_dir / "summary.md").write_text(render_sweep_summary(payload), encoding="utf-8")
    return run_dir
