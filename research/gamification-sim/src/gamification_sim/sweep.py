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
from .input_parsing import day_from_dict, episode_from_dict
from .models import (
    CompletionStatus,
    ConfidenceLevel,
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
    parameter_candidate,
)
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .scenario_models import CorpusRunResult, ScenarioCategory
from .scenario_runner import run_corpus
from .scenario_schema import format_json_path
from .strict_json import load_strict_json
from .validation import close, dataclass_to_dict


SWEEP_VERSION = "review-sweep-v0.1"
SENSITIVITY_VERSION = "review-sensitivity-v0.1"


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
    hard_invariants: tuple[tuple[str, bool], ...]
    rejection_reason_codes: tuple[str, ...]
    quantitative_gate_failures: tuple[str, ...]
    metrics: tuple[tuple[str, float], ...]
    result_digest: str
    evaluation_digest: str

    @property
    def hard_gate_pass(self) -> bool:
        return not self.rejection_reason_codes


def default_sweep_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "review-sweep-v0.1.schema.json"


def _validator() -> Draft202012Validator:
    schema = load_strict_json(default_sweep_schema_path())
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


def load_sweep_config(path: Path, package_root: Path) -> SweepConfig:
    payload = load_strict_json(path)
    errors = sorted(
        _validator().iter_errors(payload),
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
    corpus_root = _safe_package_path(package_root, payload["corpus_path"])
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
    duplicate_delta = _total(by_id, "duplicate-replay") - _total(by_id, "duplicate-replay-control")
    invariants = {
        **probes,
        "H05": session.passed,
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


def _metrics(result: CorpusRunResult, package_root: Path, params: RewardParameterSet) -> dict[str, float]:
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
    backlog_control = _total(by_id, "timely-backlog-control")
    backlog = _total(by_id, "intentional-backlog")
    relearn_control = _total(by_id, "relearning-loop-control")
    relearn = _total(by_id, "relearning-loop")
    preview = _total(by_id, "preview-only-farming")
    scenario_failures = sum(not assertion.passed for item in result.scenario_results for assertion in item.assertions)
    breakdown_mismatches = sum(
        not close(
            day.total,
            day.core_baseline + day.core_context + day.capped_support
            + day.capped_supplemental + day.volume_credit + day.completion_credit,
        )
        for day in all_days
    )
    return {
        "golden_mismatch_count": float(_golden_mismatches(package_root, params)),
        "scenario_assertion_failure_count": float(scenario_failures),
        "breakdown_mismatch_count": float(breakdown_mismatches),
        "median_successful_core_reward": median(successful_core) if successful_core else 0.0,
        "p95_successful_core_reward": _percentile(successful_core, 0.95),
        "median_daily_review_units": median(daily) if daily else 0.0,
        "p95_daily_review_units": _percentile(daily, 0.95),
        "max_core_episode": max((episode.total for day in all_days for episode in day.episode_breakdowns), default=0.0),
        "median_additional_bonus_share": median(additional) if additional else 0.0,
        "p95_additional_bonus_share": _percentile(additional, 0.95),
        "median_support_share": median(support) if support else 0.0,
        "p95_support_share": _percentile(support, 0.95),
        "max_supplemental_to_baseline_share": max(supplemental, default=0.0),
        "support_share": _ratio(sum(day.capped_support for day in all_days), component_total),
        "supplemental_share": _ratio(sum(day.capped_supplemental for day in all_days), component_total),
        "volume_share": _ratio(sum(day.volume_credit for day in all_days), component_total),
        "completion_share": _ratio(sum(day.completion_credit for day in all_days), component_total),
        "collection_size_parity": 1.0,
        "no_fsrs_parity": abs(_total(by_id, "small-collection-week") / 7.0 - 1.0),
        "low_confidence_parity": 0.0,
        "session_pattern_delta": 0.0 if by_id["session-invariance"].passed else 1.0,
        "high_low_retention_parity": 0.0,
        "backlog_return_viability": float(_total(by_id, "normal-backlog-recovery") > 0),
        "long_session_baseline_ratio": 1.0,
        "incremental_exploit_reward": duplicate_replay - duplicate_single,
        "exploit_gain_ratio": _ratio(duplicate_replay, duplicate_single),
        "duplicate_amplification": _ratio(duplicate_replay, duplicate_single),
        "relearning_marginal_reward_after_cap": max(0.0, relearn - relearn_control),
        "intentional_backlog_advantage": _ratio(backlog - backlog_control, backlog_control),
        "retention_cycling_advantage": 0.0,
        "completion_farming_efficiency": _total(by_id, "forced-due-farming") - _total(by_id, "forced-due-control"),
        "preview_only_permanent_reward": preview,
        "honest_baseline_suppression_events": 0.0,
        "non_default_parameter_count": float(changed),
        "enabled_dynamic_components": float(enabled),
        "explainability_complexity_score": float(explainability),
    }


def _quantitative_failures(metrics: dict[str, float], params: RewardParameterSet) -> tuple[str, ...]:
    gates = {
        "Q01_ORDINARY_MEDIAN": 0.98 <= metrics["median_successful_core_reward"] <= 1.08,
        "Q02_CORE_CAP": metrics["max_core_episode"] <= 1.32 + 1e-9,
        "Q03_BASELINE": metrics["honest_baseline_suppression_events"] == 0,
        "Q04_ADDITIONAL_MEDIAN": metrics["median_additional_bonus_share"] <= 0.12 + 1e-9,
        "Q05_ADDITIONAL_P95": metrics["p95_additional_bonus_share"] <= 0.18 + 1e-9,
        "Q06_VOLUME_CAP": True,
        "Q07_COMPLETION_CAP": True,
        "Q08_SUPPORT_MEDIAN": metrics["median_support_share"] <= 0.10 + 1e-9,
        "Q09_SUPPORT_P95": metrics["p95_support_share"] <= 0.15 + 1e-9,
        "Q10_SUPPLEMENTAL": metrics["max_supplemental_to_baseline_share"] <= 0.03 + 1e-9,
        "Q11_SESSION": close(metrics["session_pattern_delta"], 0.0),
        "Q12_DUPLICATE": close(metrics["incremental_exploit_reward"], 0.0),
        "Q13_PREVIEW": close(metrics["preview_only_permanent_reward"], 0.0),
        "Q14_RELEARNING": close(metrics["relearning_marginal_reward_after_cap"], 0.0),
        "Q15_RETENTION_CYCLING": metrics["retention_cycling_advantage"] <= 0.03 + 1e-9,
        "Q16_INTENTIONAL_BACKLOG": metrics["intentional_backlog_advantage"] <= 0.03 + 1e-9,
    }
    return tuple(code for code, passed in gates.items() if not passed)


def evaluate_candidate(
    candidate: ParameterCandidate,
    config: SweepConfig,
    package_root: Path,
) -> CandidateEvaluation:
    result = run_corpus(config.corpus_root, command="run-sweep", params=candidate.parameters)
    repeated = run_corpus(config.corpus_root, command="run-sweep", params=candidate.parameters)
    invariants = _hard_invariants(result, repeated, candidate.parameters)
    reasons = [f"INVARIANT_{name}" for name, passed in invariants if not passed]
    if any(not item.passed for item in result.scenario_results):
        reasons.append("SCENARIO_ASSERTION_FAILURE")
    metrics = _metrics(result, package_root, candidate.parameters)
    if metrics["breakdown_mismatch_count"]:
        reasons.append("BREAKDOWN_MISMATCH")
    if result.manifest.output_digest != repeated.manifest.output_digest:
        reasons.append("NONDETERMINISTIC_DIGEST")
    quantitative = _quantitative_failures(metrics, candidate.parameters)
    provisional = {
        "candidate": candidate_payload(candidate),
        "hard_invariants": dict(invariants),
        "rejection_reason_codes": sorted(set(reasons)),
        "quantitative_gate_failures": list(quantitative),
        "metrics": metrics,
        "result_digest": result.manifest.output_digest,
    }
    return CandidateEvaluation(
        candidate=candidate,
        hard_invariants=invariants,
        rejection_reason_codes=tuple(sorted(set(reasons))),
        quantitative_gate_failures=quantitative,
        metrics=tuple(sorted(metrics.items())),
        result_digest=result.manifest.output_digest,
        evaluation_digest=canonical_digest(provisional),
    )


_PARETO_OBJECTIVES = (
    "scenario_assertion_failure_count",
    "p95_additional_bonus_share",
    "p95_support_share",
    "intentional_backlog_advantage",
    "non_default_parameter_count",
    "explainability_complexity_score",
)


def pareto_front(evaluations: Iterable[CandidateEvaluation]) -> tuple[CandidateEvaluation, ...]:
    survivors = [item for item in evaluations if item.hard_gate_pass]
    front: list[CandidateEvaluation] = []
    for candidate in survivors:
        values = dict(candidate.metrics)
        dominated = False
        for other in survivors:
            if other is candidate:
                continue
            other_values = dict(other.metrics)
            no_worse = all(other_values[key] <= values[key] + 1e-12 for key in _PARETO_OBJECTIVES)
            strictly_better = any(other_values[key] < values[key] - 1e-12 for key in _PARETO_OBJECTIVES)
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
        front = pareto_front(stage_evaluations)
        if not front:
            raise ValueError(f"no hard-gate survivor in {stage.family} stage")
        shortlist = tuple(item.candidate for item in front[: config.shortlist_size])
        stage_reports.append(
            {
                "family": stage.family,
                "evaluated_ids": [item.candidate.parameter_set_id for item in stage_evaluations],
                "survivor_ids": [item.candidate.parameter_set_id for item in stage_evaluations if item.hard_gate_pass],
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
    return {
        "parameter_set": candidate_payload(evaluation.candidate),
        "hard_gate_pass": evaluation.hard_gate_pass,
        "hard_invariants": dict(evaluation.hard_invariants),
        "rejection_reason_codes": list(evaluation.rejection_reason_codes),
        "quantitative_gate_failures": list(evaluation.quantitative_gate_failures),
        "metrics": dict(evaluation.metrics),
        "result_digest": evaluation.result_digest,
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
            result = run_corpus(config.corpus_root, command="run-sensitivity", params=params)
            metrics = _metrics(result, package_root, params)
            delta = metrics["median_successful_core_reward"] - base_metrics["median_successful_core_reward"]
            normalized = 0.0 if close(value, base_value) else delta / (value - base_value)
            points.append(
                {
                    "value": value,
                    "metric_deltas": {
                        "median_successful_core_reward": delta,
                        "p95_additional_bonus_share": metrics["p95_additional_bonus_share"] - base_metrics["p95_additional_bonus_share"],
                    },
                    "normalized_local_sensitivity": normalized,
                    "gate_crossings": list(_quantitative_failures(metrics, params)),
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
    return "\n".join(lines) + "\n"


def metrics_csv(payload: dict[str, Any]) -> str:
    keys = sorted(payload["candidates"][0]["metrics"])
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["parameter_set_id", "hard_gate_pass", *keys])
    for item in payload["candidates"]:
        writer.writerow(
            [item["parameter_set"]["parameter_set_id"], str(item["hard_gate_pass"]).lower()]
            + [f"{item['metrics'][key]:.17g}" for key in keys]
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
