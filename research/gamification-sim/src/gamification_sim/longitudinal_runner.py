from __future__ import annotations

import importlib.metadata
import csv
import io
import json
import math
import statistics
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any
from pathlib import Path

from .canonical_json import canonical_digest
from .day_aggregation import aggregate_day
from .longitudinal_generator import cohort_digest, initial_cohort, latent_draw
from .longitudinal_models import (
    LongitudinalCardState,
    LongitudinalConfig,
    LongitudinalPolicy,
    LongitudinalReview,
)
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    DueRelation,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    SupportEventInput,
    SupportKind,
    WorkloadSnapshot,
)
from .population import resolve_parameter_set
from .validation import close, dataclass_to_dict
from .parameters import RewardParameterSet
from .workspace import ResearchWorkspace, resolve_research_workspace


GENERATOR_VERSION = "longitudinal-review-cards-v0.1"
NEUTRAL_SCHEDULER_VERSION = "neutral-synthetic-v0.1"


def _day_datetime(start_date: str, day: int) -> datetime:
    return datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc) + timedelta(days=day)


def _due_relation(day: int, natural_due_day: int, *, forced: bool = False) -> DueRelation:
    if forced:
        return DueRelation.FORCED_DUE
    if day > natural_due_day:
        return DueRelation.OVERDUE
    if day < natural_due_day:
        return DueRelation.EARLY
    return DueRelation.ON_TIME


def _rating_for_outcome(outcome: Outcome):
    from fsrs import Rating

    return {
        Outcome.AGAIN: Rating.Again,
        Outcome.HARD: Rating.Hard,
        Outcome.GOOD: Rating.Good,
        Outcome.EASY: Rating.Easy,
    }[outcome]


def _choose_outcome(
    *,
    master_seed: int,
    replica: int,
    card: LongitudinalCardState,
    retrievability: float,
) -> Outcome:
    recall = latent_draw(
        master_seed,
        replica,
        card.card_lineage_id,
        card.review_count,
        "recall",
    )
    if recall >= retrievability:
        return Outcome.AGAIN
    grade = latent_draw(
        master_seed,
        replica,
        card.card_lineage_id,
        card.review_count,
        "successful-grade",
    )
    if grade < 0.15:
        return Outcome.HARD
    if grade < 0.90:
        return Outcome.GOOD
    return Outcome.EASY


def _fsrs_transition(
    card: LongitudinalCardState,
    *,
    policy: LongitudinalPolicy,
    start_date: str,
    day: int,
    master_seed: int,
    replica: int,
) -> tuple[LongitudinalCardState, Outcome, MemoryContext, float]:
    from fsrs import Card, Rating, Scheduler

    if card.fsrs_card is None:
        raise ValueError("py-fsrs card state is missing")
    desired_retention = policy.desired_retention(day)
    scheduler = Scheduler(
        desired_retention=desired_retention,
        learning_steps=(timedelta(minutes=10),),
        relearning_steps=(timedelta(minutes=10),),
        maximum_interval=36500,
        enable_fuzzing=False,
    )
    review_at = _day_datetime(start_date, day)
    current = Card.from_dict(dict(card.fsrs_card))
    retrievability = float(scheduler.get_card_retrievability(current, review_at))
    outcome = _choose_outcome(
        master_seed=master_seed,
        replica=replica,
        card=card,
        retrievability=retrievability,
    )
    good_copy = Card.from_dict(current.to_dict())
    good_card, _ = scheduler.review_card(good_copy, Rating.Good, review_at)
    updated, _ = scheduler.review_card(current, _rating_for_outcome(outcome), review_at)
    due_offset = math.ceil((updated.due - _day_datetime(start_date, 0)).total_seconds() / 86400.0)
    next_due_day = max(day + 1, due_offset)
    stability = float(updated.stability or card.stability)
    difficulty = float(updated.difficulty or card.difficulty)
    memory = MemoryContext(
        retrievability_actual=retrievability,
        retrievability_natural_due=float(
            scheduler.get_card_retrievability(
                Card.from_dict(dict(card.fsrs_card)),
                _day_datetime(start_date, card.next_due_day),
            )
        ),
        stability_before=card.stability,
        stability_good_counterfactual=float(good_card.stability or stability),
        confidence=ConfidenceLevel.HIGH,
    )
    new_state = replace(
        card,
        state_kind=updated.state.name.lower(),
        last_review_day=day,
        next_due_day=next_due_day,
        review_count=card.review_count + 1,
        lapse_count=card.lapse_count + int(outcome is Outcome.AGAIN),
        stability=stability,
        difficulty=difficulty,
        retrievability_at_last_update=retrievability,
        scheduled_interval=next_due_day - day,
        desired_retention_policy=policy.policy_id,
        fsrs_card=tuple(sorted(updated.to_dict().items())),
    )
    return new_state, outcome, memory, retrievability


def _neutral_transition(
    card: LongitudinalCardState,
    *,
    policy: LongitudinalPolicy,
    day: int,
    master_seed: int,
    replica: int,
) -> tuple[LongitudinalCardState, Outcome, MemoryContext, float]:
    elapsed = max(1, day - (card.last_review_day if card.last_review_day is not None else -1))
    retrievability = max(0.05, min(0.99, math.exp(-elapsed / max(card.stability, 0.1))))
    outcome = _choose_outcome(
        master_seed=master_seed,
        replica=replica,
        card=card,
        retrievability=retrievability,
    )
    previous = max(1, card.scheduled_interval)
    if outcome is Outcome.AGAIN:
        interval = 1
        stability = max(1.0, card.stability * 0.55)
    elif outcome is Outcome.HARD:
        interval = max(1, round(previous * 1.2))
        stability = card.stability * 1.15
    elif outcome is Outcome.GOOD:
        interval = max(2, round(previous * 2.0))
        stability = card.stability * 1.8
    else:
        interval = max(3, round(previous * 2.5))
        stability = card.stability * 2.1
    new_state = replace(
        card,
        state_kind="neutral-review",
        last_review_day=day,
        next_due_day=day + interval,
        review_count=card.review_count + 1,
        lapse_count=card.lapse_count + int(outcome is Outcome.AGAIN),
        stability=stability,
        difficulty=card.difficulty,
        retrievability_at_last_update=retrievability,
        scheduled_interval=interval,
        desired_retention_policy=policy.policy_id,
        fsrs_card=None,
    )
    return new_state, outcome, MemoryContext(), retrievability


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


def run_policy(
    config: LongitudinalConfig,
    *,
    policy: LongitudinalPolicy,
    parameter_set_id: str,
    master_seed: int,
    mode_id: str,
    replica: int,
    params_override: RewardParameterSet | None = None,
) -> dict[str, Any]:
    mode = config.mode(mode_id)
    if params_override is None:
        normalized_id, params = resolve_parameter_set(parameter_set_id)
    else:
        normalized_id, params = parameter_set_id, params_override
    cards = initial_cohort(
        master_seed=master_seed,
        replica=replica,
        cohort_size=mode.cohort_size,
        start_date=config.start_date,
        policy_id=policy.policy_id,
        scheduler=policy.scheduler,
    )
    initial_digest = cohort_digest(cards)
    states = {item.card_lineage_id: item for item in cards}
    reviews: list[LongitudinalReview] = []
    cumulative = {
        "core_baseline": 0.0,
        "core_context": 0.0,
        "support": 0.0,
        "supplemental": 0.0,
        "volume_credit": 0.0,
        "completion_credit": 0.0,
        "total_review_units": 0.0,
    }
    successful = 0
    again = 0
    overdue_days: list[float] = []
    expected_baseline = 0.0
    suppression_events = 0
    for day in range(mode.horizon_days):
        due = sorted(
            (card for card in states.values() if card.active and card.next_due_day <= day),
            key=lambda card: (card.next_due_day, card.card_lineage_id),
        )
        if not policy.reviews_enabled(day):
            continue
        selected = due[: policy.review_limit]
        episodes: list[ReviewEpisodeInput] = []
        support: list[SupportEventInput] = []
        transitions: dict[str, tuple[LongitudinalCardState, Outcome, float, DueRelation]] = {}
        for card in selected:
            if policy.scheduler == "py-fsrs":
                updated, outcome, memory, retrievability = _fsrs_transition(
                    card,
                    policy=policy,
                    start_date=config.start_date,
                    day=day,
                    master_seed=master_seed,
                    replica=replica,
                )
            else:
                updated, outcome, memory, retrievability = _neutral_transition(
                    card,
                    policy=policy,
                    day=day,
                    master_seed=master_seed,
                    replica=replica,
                )
            relation = _due_relation(day, card.next_due_day)
            key = f"{policy.policy_id}-{replica}-{card.card_lineage_id}-{card.review_count}"
            episodes.append(
                ReviewEpisodeInput(
                    source_event_key=key,
                    card_lineage=card.card_lineage_id,
                    anki_day=_day_datetime(config.start_date, day).date().isoformat(),
                    outcome=outcome,
                    due_relation=relation,
                    memory=memory,
                )
            )
            if outcome is Outcome.AGAIN:
                support.append(SupportEventInput(f"support-{key}", key, SupportKind.FIRST_STEP))
            transitions[key] = (updated, outcome, retrievability, relation)
        status = (
            CompletionStatus.ZERO_DUE
            if not due
            else CompletionStatus.COLLECTION_CLEARED
            if len(selected) == len(due)
            else CompletionStatus.PARTIAL
        )
        day_input = ReviewDayInput(
            anki_day=_day_datetime(config.start_date, day).date().isoformat(),
            episodes=tuple(episodes),
            support_events=tuple(support),
            workload=WorkloadSnapshot(
                status=status,
                natural_due_at_start=len(due),
                due_visible_under_limits=min(len(due), policy.review_limit),
                due_hidden_by_limits=max(0, len(due) - policy.review_limit),
            ),
            session_ids=("longitudinal-daily-session",),
        )
        breakdown = aggregate_day(day_input, params)
        by_key = {item.source_event_key: item for item in breakdown.episode_breakdowns}
        for episode in episodes:
            updated, outcome, retrievability, relation = transitions[episode.source_event_key]
            previous = states[updated.card_lineage_id]
            item = by_key[episode.source_event_key]
            expected = params.attempt_credit + (params.outcome_credit if outcome.passed else 0.0)
            expected_baseline += expected
            suppression_events += int(item.baseline + 1e-9 < expected)
            successful += int(outcome.passed)
            again += int(outcome is Outcome.AGAIN)
            if relation is DueRelation.OVERDUE:
                overdue_days.append(float(day - previous.next_due_day))
            reviews.append(
                LongitudinalReview(
                    updated.card_lineage_id,
                    day,
                    previous.next_due_day,
                    relation.value,
                    outcome.value,
                    retrievability,
                    policy.desired_retention(day),
                    item.baseline,
                    item.context,
                    item.total,
                    updated.next_due_day,
                    updated.stability,
                    updated.difficulty,
                )
            )
            states[updated.card_lineage_id] = updated
        cumulative["core_baseline"] += breakdown.core_baseline
        cumulative["core_context"] += breakdown.core_context
        cumulative["support"] += breakdown.capped_support
        cumulative["supplemental"] += breakdown.capped_supplemental
        cumulative["volume_credit"] += breakdown.volume_credit
        cumulative["completion_credit"] += breakdown.completion_credit
        cumulative["total_review_units"] += breakdown.total
    final_cards = tuple(sorted(states.values(), key=lambda item: item.card_lineage_id))
    review_count = len(reviews)
    final_stabilities = [item.stability for item in final_cards]
    final_backlog = sum(item.next_due_day < mode.horizon_days for item in final_cards)
    lineage_counts: dict[str, int] = {}
    for review in reviews:
        lineage_counts[review.card_lineage_id] = lineage_counts.get(review.card_lineage_id, 0) + 1
    metrics = {
        "card_count": len(final_cards),
        "review_count": review_count,
        "successful_review_count": successful,
        "again_count": again,
        "overdue_review_count": len(overdue_days),
        "mean_days_overdue": statistics.fmean(overdue_days) if overdue_days else 0.0,
        "p50_days_overdue": statistics.median(overdue_days) if overdue_days else 0.0,
        "p95_days_overdue": _percentile(overdue_days, 0.95),
        **cumulative,
        "ru_per_eligible_core_review": cumulative["total_review_units"] / review_count if review_count else 0.0,
        "baseline_preservation_ratio": cumulative["core_baseline"] / expected_baseline if expected_baseline else 1.0,
        "review_workload_per_day": review_count / mode.horizon_days,
        "retention_success_rate": successful / review_count if review_count else 0.0,
        "final_stability_mean": statistics.fmean(final_stabilities),
        "final_stability_p50": statistics.median(final_stabilities),
        "final_stability_p95": _percentile(final_stabilities, 0.95),
        "final_due_backlog": final_backlog,
        "honest_baseline_suppression_events": suppression_events,
        "lineages_with_multiple_reviews": sum(count > 1 for count in lineage_counts.values()),
    }
    events_payload = [dataclass_to_dict(item) for item in reviews]
    return {
        "policy_id": policy.policy_id,
        "scheduler": policy.scheduler,
        "parameter_set_id": normalized_id,
        "replica": replica,
        "horizon_days": mode.horizon_days,
        "initial_cohort_digest": initial_digest,
        "latent_stream_id": canonical_digest(
            {"master_seed": master_seed, "replica": replica, "contract": "card-lineage-review-ordinal-v1"}
        ),
        "trajectory_digest": canonical_digest(events_payload),
        "final_cohort_digest": cohort_digest(final_cards),
        "metrics": metrics,
        "events": events_payload,
        "final_state_summary": {
            "card_count": len(final_cards),
            "active_count": sum(item.active for item in final_cards),
            "state_counts": {
                state: sum(item.state_kind == state for item in final_cards)
                for state in sorted({item.state_kind for item in final_cards})
            },
            "next_due_min": min(item.next_due_day for item in final_cards),
            "next_due_max": max(item.next_due_day for item in final_cards),
        },
    }


def run_longitudinal(
    config: LongitudinalConfig,
    *,
    mode_id: str,
    master_seed: int,
    parameter_set_ids: tuple[str, ...] | None = None,
    policy_ids: tuple[str, ...] | None = None,
    parameter_overrides: dict[str, RewardParameterSet] | None = None,
    workspace: ResearchWorkspace | Path | None = None,
) -> dict[str, Any]:
    if type(master_seed) is not int or master_seed < 0:
        raise ValueError("longitudinal seed must be a non-negative integer")
    from .matched_analysis import validate_policy_pairs

    validate_policy_pairs(config.policies)
    mode = config.mode(mode_id)
    selected_parameters = parameter_set_ids or config.parameter_set_ids
    selected_policy_ids = set(policy_ids or tuple(item.policy_id for item in config.policies))
    selected_policies = tuple(item for item in config.policies if item.policy_id in selected_policy_ids)
    if len(selected_policies) != len(selected_policy_ids):
        raise ValueError("unknown longitudinal policy ID")
    results = []
    for parameter_set_id in selected_parameters:
        for policy in selected_policies:
            for replica in range(mode.replicas):
                results.append(
                    run_policy(
                        config,
                        policy=policy,
                        parameter_set_id=parameter_set_id,
                        master_seed=master_seed,
                        mode_id=mode_id,
                        replica=replica,
                        params_override=(parameter_overrides or {}).get(parameter_set_id),
                    )
                )
    payload = {
        "manifest": {
            "generator_version": GENERATOR_VERSION,
            "config_version": config.version,
            "config_digest": config.digest,
            "mode": mode_id,
            "horizon_days": mode.horizon_days,
            "cohort_size": mode.cohort_size,
            "replicas": mode.replicas,
            "master_seed": master_seed,
            "parameter_set_ids": list(selected_parameters),
            "policy_ids": sorted(selected_policy_ids),
            "py_fsrs_version": importlib.metadata.version("fsrs"),
            "neutral_scheduler_version": NEUTRAL_SCHEDULER_VERSION,
            "result_count": len(results),
        },
        "policy_results": results,
    }
    from .matched_analysis import deterministic_matched_matrices, longitudinal_matrices

    fairness, abuse = longitudinal_matrices(payload)
    deterministic_fairness: list[dict[str, Any]] = []
    deterministic_abuse: list[dict[str, Any]] = []
    for parameter_set_id in selected_parameters:
        fair_items, abuse_items = deterministic_matched_matrices(
            resolve_research_workspace(workspace).root,
            parameter_set_id,
            params_override=(parameter_overrides or {}).get(parameter_set_id),
        )
        deterministic_fairness.extend(fair_items)
        deterministic_abuse.extend(abuse_items)
    fairness["comparisons"].extend(deterministic_fairness)
    abuse["comparisons"].extend(deterministic_abuse)
    payload["fairness"] = fairness
    payload["abuse"] = abuse
    payload["manifest"]["trajectory_digest"] = canonical_digest(
        [item["trajectory_digest"] for item in results]
    )
    payload["manifest"]["final_cohort_digest"] = canonical_digest(
        [item["final_cohort_digest"] for item in results]
    )
    payload["manifest"]["report_digest"] = canonical_digest(payload)
    return payload


def validate_longitudinal_result(payload: dict[str, Any]) -> None:
    if not payload["policy_results"]:
        raise ValueError("longitudinal run has no policy results")
    for result in payload["policy_results"]:
        metrics = result["metrics"]
        if metrics["honest_baseline_suppression_events"]:
            raise ValueError(f"baseline suppression in {result['policy_id']}")
        if not close(metrics["baseline_preservation_ratio"], 1.0):
            raise ValueError(f"baseline preservation ratio failed in {result['policy_id']}")
    if payload["manifest"]["mode"] in {"calibration-90", "calibration-365"}:
        missing = [
            item for item in payload["abuse"]["unsupported"]
            if item["comparison"] in {
                "retention-high-cycle",
                "retention-low-cycle",
                "intentional-backlog",
            }
        ]
        if missing:
            raise ValueError("required matched abuse evidence is unsupported")
        failed = [
            item["comparison"]
            for item in payload["abuse"]["comparisons"]
            if item["status"] == "FAIL"
        ]
        if failed:
            raise ValueError(f"matched abuse gate failure: {', '.join(sorted(set(failed)))}")


def render_longitudinal_summary(payload: dict[str, Any]) -> str:
    manifest = payload["manifest"]
    lines = [
        "# Longitudinal Review XP simulation",
        "",
        f"- Mode: `{manifest['mode']}`",
        f"- Horizon: **{manifest['horizon_days']} days**",
        f"- Cohort per replica: **{manifest['cohort_size']} cards**",
        f"- Replicas: **{manifest['replicas']}**",
        f"- Seed: `{manifest['master_seed']}`",
        f"- py-fsrs: `{manifest['py_fsrs_version']}`",
        f"- Report digest: `{manifest['report_digest']}`",
        "",
        "| Policy | Candidate | Replica | Reviews | Overdue | Baseline | Final backlog |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in payload["policy_results"]:
        metrics = result["metrics"]
        lines.append(
            f"| `{result['policy_id']}` | `{result['parameter_set_id']}` | {result['replica']} | "
            f"{metrics['review_count']} | {metrics['overdue_review_count']} | "
            f"{metrics['baseline_preservation_ratio']:.9g} | {metrics['final_due_backlog']} |"
        )
    return "\n".join(lines) + "\n"


def write_longitudinal_reports(payload: dict[str, Any], output_root: Path) -> Path:
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("longitudinal output root must not be a symlink")
    run_id = payload["manifest"]["report_digest"][:12]
    run_dir = output_root.resolve() / "longitudinal" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("longitudinal run directory must not be a symlink")
    (run_dir / "manifest.json").write_text(
        json.dumps(payload["manifest"], indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    rows = []
    for result in payload["policy_results"]:
        rows.append(
            {
                "policy_id": result["policy_id"],
                "parameter_set_id": result["parameter_set_id"],
                "replica": result["replica"],
                **result["metrics"],
                "initial_cohort_digest": result["initial_cohort_digest"],
                "trajectory_digest": result["trajectory_digest"],
                "final_cohort_digest": result["final_cohort_digest"],
            }
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (run_dir / "policy-metrics.csv").write_text(stream.getvalue(), encoding="utf-8")
    for name, value in (("fairness.json", payload["fairness"]), ("abuse.json", payload["abuse"])):
        (run_dir / name).write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    states = [
        {
            "policy_id": result["policy_id"],
            "parameter_set_id": result["parameter_set_id"],
            "replica": result["replica"],
            **result["final_state_summary"],
        }
        for result in payload["policy_results"]
    ]
    (run_dir / "cohort-state-summary.json").write_text(
        json.dumps(states, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.md").write_text(render_longitudinal_summary(payload), encoding="utf-8")
    return run_dir
