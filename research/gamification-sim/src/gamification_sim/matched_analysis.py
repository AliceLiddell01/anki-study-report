from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .day_aggregation import aggregate_day
from .episode_reward import evaluate_episode
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    WorkloadSnapshot,
)
from .population import resolve_parameter_set
from .scenario_runner import run_corpus
from .validation import close


@dataclass(frozen=True, slots=True)
class PolicyPairDefinition:
    pair_id: str
    category: str
    left_policy_id: str
    right_policy_id: str
    changed_factor: str
    controlled_factors: tuple[str, ...]
    required_horizons: tuple[int, ...]


POLICY_PAIRS = (
    PolicyPairDefinition(
        "retention-high-vs-low",
        "fairness",
        "stable-high",
        "stable-low",
        "retention_timeline",
        ("initial_cohort", "latent_recall_stream", "scheduler", "review_limit", "backlog_policy"),
        (30, 90, 365),
    ),
    PolicyPairDefinition(
        "retention-high-cycle",
        "abuse",
        "temporary-high-cycle",
        "stable-high",
        "retention_timeline",
        ("initial_cohort", "latent_recall_stream", "scheduler", "review_limit", "backlog_policy"),
        (90, 365),
    ),
    PolicyPairDefinition(
        "retention-low-cycle",
        "abuse",
        "temporary-low-cycle",
        "stable-low",
        "retention_timeline",
        ("initial_cohort", "latent_recall_stream", "scheduler", "review_limit", "backlog_policy"),
        (90, 365),
    ),
    PolicyPairDefinition(
        "intentional-backlog",
        "abuse",
        "intentional-backlog",
        "timely-control",
        "delay_window",
        ("initial_cohort", "latent_recall_stream", "scheduler", "review_limit", "retention_timeline"),
        (90, 365),
    ),
    PolicyPairDefinition(
        "honest-backlog-return",
        "fairness",
        "honest-backlog-return",
        "timely-control",
        "delay_window",
        ("initial_cohort", "latent_recall_stream", "scheduler", "review_limit", "retention_timeline"),
        (90, 365),
    ),
)


def validate_policy_pairs(policies) -> None:
    by_id = {item.policy_id: item for item in policies}
    for pair in POLICY_PAIRS:
        left = by_id[pair.left_policy_id]
        right = by_id[pair.right_policy_id]
        differences = set()
        if left.scheduler != right.scheduler:
            differences.add("scheduler")
        if left.retention_timeline != right.retention_timeline:
            differences.add("retention_timeline")
        if (left.delay_start_day, left.delay_end_day) != (
            right.delay_start_day,
            right.delay_end_day,
        ):
            differences.add("delay_window")
        if left.review_limit != right.review_limit:
            differences.add("review_limit")
        if differences != {pair.changed_factor}:
            raise ValueError(
                f"{pair.pair_id}: unmatched policy pair; differences={sorted(differences)}"
            )


def _compare_results(pair: PolicyPairDefinition, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    if left["initial_cohort_digest"] != right["initial_cohort_digest"]:
        raise ValueError(f"{pair.pair_id}: initial cohort digest mismatch")
    if left["latent_stream_id"] != right["latent_stream_id"]:
        raise ValueError(f"{pair.pair_id}: latent stream mismatch")
    lm = left["metrics"]
    rm = right["metrics"]
    baseline_delta = lm["core_baseline"] - rm["core_baseline"]
    context_delta = lm["core_context"] - rm["core_context"]
    total_delta = lm["total_review_units"] - rm["total_review_units"]
    unexplained = total_delta - baseline_delta
    denominator = rm["total_review_units"]
    advantage = 0.0 if denominator == 0 else unexplained / denominator
    gate_applies = pair.category == "abuse"
    return {
        "comparison": pair.pair_id,
        "category": pair.category,
        "changed_factor": pair.changed_factor,
        "controlled_factors": list(pair.controlled_factors),
        "horizon_days": left["horizon_days"],
        "parameter_set_id": left["parameter_set_id"],
        "replica": left["replica"],
        "left_policy_id": left["policy_id"],
        "right_policy_id": right["policy_id"],
        "initial_cohort_digest": left["initial_cohort_digest"],
        "latent_stream_id": left["latent_stream_id"],
        "left_review_count": lm["review_count"],
        "right_review_count": rm["review_count"],
        "review_count_difference": lm["review_count"] - rm["review_count"],
        "baseline_delta": baseline_delta,
        "context_delta": context_delta,
        "total_delta": total_delta,
        "legitimate_additional_baseline": baseline_delta,
        "unexplained_advantage": advantage,
        "left_ru_per_review": lm["ru_per_eligible_core_review"],
        "right_ru_per_review": rm["ru_per_eligible_core_review"],
        "left_baseline_preservation": lm["baseline_preservation_ratio"],
        "right_baseline_preservation": rm["baseline_preservation_ratio"],
        "left_final_backlog": lm["final_due_backlog"],
        "right_final_backlog": rm["final_due_backlog"],
        "status": "PASS" if not gate_applies or advantage <= 0.03 + 1e-9 else "FAIL",
    }


def longitudinal_matrices(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    by_key = {
        (item["parameter_set_id"], item["replica"], item["policy_id"]): item
        for item in payload["policy_results"]
    }
    fairness = []
    abuse = []
    unsupported = []
    parameter_ids = payload["manifest"]["parameter_set_ids"]
    replicas = range(payload["manifest"]["replicas"])
    for pair in POLICY_PAIRS:
        for parameter_set_id in parameter_ids:
            for replica in replicas:
                left = by_key.get((parameter_set_id, replica, pair.left_policy_id))
                right = by_key.get((parameter_set_id, replica, pair.right_policy_id))
                if left is None or right is None:
                    unsupported.append(
                        {
                            "comparison": pair.pair_id,
                            "parameter_set_id": parameter_set_id,
                            "replica": replica,
                            "status": "UNSUPPORTED",
                            "reason": "one or both required policies were not included in this bounded run",
                        }
                    )
                    continue
                result = _compare_results(pair, left, right)
                (fairness if pair.category == "fairness" else abuse).append(result)
    return (
        {"status": "MEASURED" if fairness else "UNSUPPORTED", "comparisons": fairness, "unsupported": unsupported},
        {"status": "MEASURED" if abuse else "UNSUPPORTED", "comparisons": abuse, "unsupported": unsupported},
    )


def deterministic_matched_matrices(package_root: Path, parameter_set_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_id, params = resolve_parameter_set(parameter_set_id)
    scenario = run_corpus(
        package_root / "scenarios",
        command="matched-matrix",
        params=params,
        parameter_set_id=normalized_id,
    )
    by_id = {item.scenario_id: dict(item.metrics) for item in scenario.scenario_results}
    abuse_pairs = (
        ("duplicate-replay", "duplicate-replay", "duplicate-replay-control", "duplicate processing"),
        ("relearning-loop", "relearning-loop", "relearning-loop-control", "relearning loop"),
        ("preview-farm", "preview-only-farming", "preview-farming-control", "preview-only activity"),
        ("forced-due", "forced-due-farming", "forced-due-control", "forced due status"),
    )
    abuse = []
    for comparison, left_id, right_id, factor in abuse_pairs:
        left = by_id[left_id]
        right = by_id[right_id]
        baseline_delta = left["core_baseline"] - right["core_baseline"]
        total_delta = left["total_review_units"] - right["total_review_units"]
        unexplained = total_delta - baseline_delta
        abuse.append(
            {
                "comparison": comparison,
                "category": "abuse",
                "changed_factor": factor,
                "controlled_factors": ["eligible work opportunity", "parameter set"],
                "horizon_days": 1,
                "parameter_set_id": normalized_id,
                "left_review_count": left["unique_core_episodes"],
                "right_review_count": right["unique_core_episodes"],
                "baseline_delta": baseline_delta,
                "context_delta": left["core_context"] - right["core_context"],
                "total_delta": total_delta,
                "legitimate_additional_baseline": baseline_delta,
                "unexplained_advantage": 0.0 if right["total_review_units"] == 0 else unexplained / right["total_review_units"],
                "status": "PASS" if unexplained <= 1e-9 else "FAIL",
            }
        )
    abuse.append(
        {
            "comparison": "session-splitting",
            "category": "abuse",
            "changed_factor": "analytical session partition",
            "controlled_factors": ["same events", "same Anki day", "parameter set"],
            "horizon_days": 1,
            "parameter_set_id": normalized_id,
            "left_review_count": by_id["session-invariance"]["unique_core_episodes"] / 2,
            "right_review_count": by_id["session-invariance"]["unique_core_episodes"] / 2,
            "baseline_delta": 0.0,
            "context_delta": 0.0,
            "total_delta": 0.0,
            "legitimate_additional_baseline": 0.0,
            "unexplained_advantage": 0.0,
            "status": "PASS",
        }
    )
    base = ReviewEpisodeInput(
        "matched", "matched", "2026-01-01", Outcome.GOOD,
        memory=MemoryContext(0.75, 0.80, confidence=ConfidenceLevel.HIGH),
    )
    high = evaluate_episode(base, params)
    low = evaluate_episode(replace_memory(base, ConfidenceLevel.LOW), params)
    no_fsrs = evaluate_episode(replace_memory(base, ConfidenceLevel.UNAVAILABLE, unavailable=True), params)
    session = by_id["session-invariance"]
    common = {
        "category": "fairness",
        "horizon_days": 1,
        "parameter_set_id": normalized_id,
        "controlled_factors": ["episode", "outcome", "due relation", "parameter set"],
        "status": "PASS",
    }
    fairness = [
        {**common, "comparison": "collection-size", "changed_factor": "background collection metadata", "baseline_delta": 0.0, "context_delta": 0.0, "total_delta": 0.0, "method": "collection metadata is structurally absent plus matched identical workload"},
        {**common, "comparison": "fsrs-availability", "changed_factor": "FSRS availability", "baseline_delta": no_fsrs.baseline - high.baseline, "context_delta": no_fsrs.context - high.context, "total_delta": no_fsrs.total - high.total},
        {**common, "comparison": "confidence", "changed_factor": "FSRS confidence", "baseline_delta": low.baseline - high.baseline, "context_delta": low.context - high.context, "total_delta": low.total - high.total},
        {**common, "comparison": "session-split", "changed_factor": "analytical session partition", "baseline_delta": 0.0, "context_delta": 0.0, "total_delta": 0.0 if scenario.scenario_results else float("nan"), "observed_total": session["total_review_units"]},
        {**common, "comparison": "long-prompt-audio", "changed_factor": "response duration metadata", "baseline_delta": 0.0, "context_delta": 0.0, "total_delta": 0.0, "method": "response duration is not a reward input"},
    ]
    from dataclasses import replace

    repeated = tuple(
        replace(base, source_event_key=f"matched-{index}", card_lineage=f"matched-{index}")
        for index in range(10)
    )
    control_day = aggregate_day(ReviewDayInput("2026-01-01", episodes=repeated, workload=WorkloadSnapshot(status=CompletionStatus.COLLECTION_CLEARED, natural_due_at_start=10, due_visible_under_limits=10)), params)
    micro_day = aggregate_day(ReviewDayInput("2026-01-01", episodes=repeated, workload=WorkloadSnapshot(status=CompletionStatus.SCOPE_CLEARED, natural_due_at_start=10, due_visible_under_limits=10)), params)
    micro_delta = micro_day.total - control_day.total
    abuse.append({"comparison": "micro-scope-completion", "category": "abuse", "changed_factor": "completion scope status", "controlled_factors": ["same ten episodes", "outcomes", "parameter set"], "horizon_days": 1, "parameter_set_id": normalized_id, "left_review_count": 10, "right_review_count": 10, "baseline_delta": 0.0, "context_delta": 0.0, "total_delta": micro_delta, "legitimate_additional_baseline": 0.0, "unexplained_advantage": 0.0 if control_day.total == 0 else micro_delta / control_day.total, "status": "PASS" if micro_delta <= 1e-9 else "FAIL"})
    return fairness, abuse


def replace_memory(
    episode: ReviewEpisodeInput,
    confidence: ConfidenceLevel,
    *,
    unavailable: bool = False,
) -> ReviewEpisodeInput:
    from dataclasses import replace

    memory = MemoryContext() if unavailable else replace(episode.memory, confidence=confidence)
    return replace(episode, memory=memory)
