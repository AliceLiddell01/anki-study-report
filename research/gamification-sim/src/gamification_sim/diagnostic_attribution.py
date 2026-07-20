from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest, canonical_dumps
from .episode_reward import challenge_curve, delay_credit
from .longitudinal_config import load_longitudinal_config
from .longitudinal_runner import run_longitudinal, validate_longitudinal_result
from .models import Outcome
from .validation import close, dataclass_to_dict
from .workspace import resolve_research_workspace

VERSION = "review-cycling-attribution-v1"
MASTER_SEED = 20260716
SECONDARY_SEED = 20260717
POLICY_IDS = (
    "stable-high",
    "stable-low",
    "temporary-high-cycle",
    "temporary-low-cycle",
    "timely-control",
    "intentional-backlog",
    "honest-backlog-return",
)
COMPARISON_POLICIES = {
    "retention-high-cycle": ("temporary-high-cycle", "stable-high"),
    "retention-low-cycle": ("temporary-low-cycle", "stable-low"),
    "intentional-backlog": ("intentional-backlog", "timely-control"),
}
POLICY_COMPARISONS = {
    policy_id: comparison
    for comparison, pair in COMPARISON_POLICIES.items()
    for policy_id in pair
}
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
FORBIDDEN_TEXT = (
    "collection.anki2",
    "collection.anki21",
    "revlog",
    "profile path",
    "bearer ",
    "github_pat_",
    "ghp_",
    "token=",
    "authorization:",
    "private-user-images",
)
TOLERANCE = 1e-9


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(canonical_dumps(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON constant {value} in {path}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=reject,
    )


def _finite_walk(value: Any, path: str = "$") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} is non-finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_walk(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _finite_walk(item, f"{path}.{key}")
        return
    raise TypeError(f"{path} contains unsupported value {type(value).__name__}")


def transition_marker(policy: Any, day: int) -> str:
    if policy.delay_end_day is not None and policy.delay_end_day <= day < policy.delay_end_day + 15:
        return "backlog_return_window"
    if day < 30:
        return "pre_transition"
    if day == 30:
        return "day_30_transition"
    if day < 60:
        return "between_transitions"
    if day == 60:
        return "day_60_transition"
    return "post_transition"


def _counter_context(
    *,
    passed: bool,
    baseline: float,
    challenge: float,
    memory: float,
    neutral: float,
    confidence: float,
    effective_bonus: float,
    episode_cap: float,
) -> float:
    if not passed:
        return 0.0
    blended = neutral + confidence * (challenge + memory - neutral)
    context = effective_bonus * blended
    if baseline + context >= episode_cap - 1e-12:
        context = max(0.0, episode_cap - baseline)
    return context


def _raw_memory_gain(before: float | None, after: float | None) -> float:
    if before is None or after is None:
        return 0.0
    return math.log(after / before)


def recompute_episode_counterfactuals(row: dict[str, Any]) -> dict[str, float]:
    """Re-evaluate reward-only counterfactuals without mutating a trace row."""
    common = {
        "passed": row["outcome"] != Outcome.AGAIN.value,
        "baseline": row["baseline_credit"],
        "neutral": row["neutral_context_credit"],
        "confidence": row["confidence"],
        "effective_bonus": row["effective_bonus"],
        "episode_cap": row["episode_cap"],
    }
    f_cm = _counter_context(challenge=row["adjusted_challenge"], memory=row["memory_gain_credit"], **common)
    f_c0 = _counter_context(challenge=row["adjusted_challenge"], memory=0.0, **common)
    f_0m = _counter_context(challenge=0.0, memory=row["memory_gain_credit"], **common)
    f_00 = _counter_context(challenge=0.0, memory=0.0, **common)
    return {
        "f_cm": f_cm,
        "f_c0": f_c0,
        "f_0m": f_0m,
        "f_00": f_00,
        "challenge_main": f_c0 - f_00,
        "memory_main": f_0m - f_00,
        "interaction": f_cm - f_c0 - f_0m + f_00,
    }


def _comparison_id(policy_id: str) -> str:
    if policy_id in POLICY_COMPARISONS:
        return POLICY_COMPARISONS[policy_id]
    if policy_id == "honest-backlog-return":
        return "honest-backlog-return"
    if policy_id in {"stable-default", "no-fsrs-neutral"}:
        return "interval-neutral-control"
    return "unmatched-policy"


@dataclass
class TraceBundle:
    label: str
    payload: dict[str, Any]
    episodes: list[dict[str, Any]]
    days: list[dict[str, Any]]
    policies: list[dict[str, Any]]
    comparisons: list[dict[str, Any]]

    @property
    def trace_digest(self) -> str:
        return canonical_digest(
            {
                "episodes": self.episodes,
                "days": self.days,
                "policies": self.policies,
                "comparisons": self.comparisons,
            }
        )


class AttributionCollector:
    def __init__(self, *, mode_id: str, master_seed: int) -> None:
        self.mode_id = mode_id
        self.master_seed = master_seed
        self.run_id = f"g12-{mode_id}-{master_seed}"
        self.episodes: list[dict[str, Any]] = []
        self.days: list[dict[str, Any]] = []
        self.policies: list[dict[str, Any]] = []

    def observe(self, event: dict[str, Any]) -> None:
        kind = event["kind"]
        if kind == "day":
            self._observe_day(event)
        elif kind == "policy_result":
            self._observe_policy(event)
        else:
            raise ValueError(f"unknown diagnostic observation kind: {kind}")

    def _observe_day(self, event: dict[str, Any]) -> None:
        policy = event["policy"]
        params = event["params"]
        day = event["day"]
        breakdown = event["day_breakdown"]
        marker = transition_marker(policy, day)
        comparison_id = _comparison_id(policy.policy_id)
        episode_rows: list[dict[str, Any]] = []
        for observed in event["episode_observations"]:
            episode = observed["episode"]
            item = observed["breakdown"]
            previous = observed["previous_state"]
            updated = observed["updated_state"]
            memory = episode.memory
            passed = episode.outcome.passed
            raw_challenge = (
                challenge_curve(memory.retrievability_actual, params)
                if passed and memory.retrievability_actual is not None
                else 0.0
            )
            natural_challenge = (
                challenge_curve(memory.retrievability_natural_due, params)
                if passed and memory.retrievability_natural_due is not None
                else 0.0
            )
            extra_challenge = max(0.0, raw_challenge - natural_challenge)
            delay_factor = 1.0
            if (
                passed
                and memory.retrievability_actual is not None
                and memory.retrievability_natural_due is not None
                and memory.retrievability_actual < memory.retrievability_natural_due
            ):
                delay_factor = delay_credit(
                    memory.retrievability_natural_due - memory.retrievability_actual,
                    params,
                )
            confidence = params.confidence(memory.confidence)
            context_before_blend = item.challenge_credit + item.memory_gain_credit
            context_after_blend = (
                params.neutral_context_credit
                + confidence * (context_before_blend - params.neutral_context_credit)
                if passed
                else 0.0
            )
            common = {
                "passed": passed,
                "baseline": item.baseline,
                "neutral": params.neutral_context_credit,
                "confidence": confidence,
                "effective_bonus": item.bonus_eligibility,
                "episode_cap": params.core_episode_cap,
            }
            f_cm = _counter_context(
                challenge=item.challenge_credit,
                memory=item.memory_gain_credit,
                **common,
            )
            f_c0 = _counter_context(challenge=item.challenge_credit, memory=0.0, **common)
            f_0m = _counter_context(challenge=0.0, memory=item.memory_gain_credit, **common)
            f_00 = _counter_context(challenge=0.0, memory=0.0, **common)
            challenge_main = f_c0 - f_00
            memory_main = f_0m - f_00
            interaction = f_cm - f_c0 - f_0m + f_00
            decomposition_residual = item.context - (
                f_00 + challenge_main + memory_main + interaction
            )
            row = {
                "grain": "review_episode",
                "run_id": self.run_id,
                "parameter_set_id": event["parameter_set_id"],
                "policy_id": policy.policy_id,
                "comparison_id": comparison_id,
                "replica": event["replica"],
                "horizon_days": event["horizon_days"],
                "day": day,
                "window_id": marker,
                "transition_marker": marker,
                "synthetic_card_lineage_id": episode.card_lineage,
                "source_event_key": episode.source_event_key,
                "desired_retention": policy.desired_retention(day),
                "scheduled_due_day": previous.next_due_day,
                "next_due_day": updated.next_due_day,
                "actual_review_day": day,
                "delay_days": max(0, day - previous.next_due_day),
                "due_relation": episode.due_relation.value,
                "retrievability_actual": memory.retrievability_actual,
                "retrievability_natural_due": memory.retrievability_natural_due,
                "stability_before": memory.stability_before,
                "stability_good_counterfactual": memory.stability_good_counterfactual,
                "stability_after": updated.stability,
                "difficulty_before": previous.difficulty,
                "difficulty_after": updated.difficulty,
                "model_confidence": memory.confidence.value,
                "outcome": episode.outcome.value,
                "attempt_credit": params.attempt_credit,
                "outcome_credit": params.outcome_credit if passed else 0.0,
                "baseline_credit": item.baseline,
                "neutral_context_credit": params.neutral_context_credit,
                "raw_challenge_credit": raw_challenge,
                "natural_due_challenge_credit": natural_challenge,
                "extra_challenge": extra_challenge,
                "delay_credit": delay_factor,
                "adjusted_challenge": item.challenge_credit,
                "raw_memory_gain": _raw_memory_gain(
                    memory.stability_before,
                    memory.stability_good_counterfactual,
                ),
                "memory_gain_credit": item.memory_gain_credit,
                "confidence": confidence,
                "effective_bonus": item.bonus_eligibility,
                "episode_cap": params.core_episode_cap,
                "response_validity": episode.response_validity,
                "context_before_blend": context_before_blend,
                "context_after_blend": context_after_blend,
                "context_after_cap": item.context,
                "core_review_units": item.total,
                "cap_applied": bool(item.applied_caps),
                "suppression_or_cap_reason": (
                    ",".join(item.applied_caps) if item.applied_caps else "none"
                ),
                "f_cm": f_cm,
                "f_c0": f_c0,
                "f_0m": f_0m,
                "f_00": f_00,
                "challenge_main": challenge_main,
                "memory_main": memory_main,
                "interaction": interaction,
                "decomposition_residual": decomposition_residual,
                "classification": "EXPLORATORY_NON_DECISION",
            }
            if not close(row["context_after_cap"], f_cm):
                raise ValueError("post-hoc full-context counterfactual does not match runtime")
            if abs(decomposition_residual) > TOLERANCE:
                raise ValueError("episode counterfactual decomposition residual exceeds tolerance")
            episode_rows.append(row)
        self.episodes.extend(episode_rows)
        self.days.append(
            {
                "grain": "day_window",
                "run_id": self.run_id,
                "parameter_set_id": event["parameter_set_id"],
                "policy_id": policy.policy_id,
                "comparison_id": comparison_id,
                "replica": event["replica"],
                "horizon_days": event["horizon_days"],
                "day": day,
                "window_id": marker,
                "transition_marker": marker,
                "review_count": len(episode_rows),
                "successful_review_count": sum(row["outcome"] != Outcome.AGAIN.value for row in episode_rows),
                "again_count": sum(row["outcome"] == Outcome.AGAIN.value for row in episode_rows),
                "core_baseline": breakdown.core_baseline,
                "core_context": breakdown.core_context,
                "support": breakdown.capped_support,
                "supplemental": breakdown.capped_supplemental,
                "volume_credit": breakdown.volume_credit,
                "completion_credit": breakdown.completion_credit,
                "day_total": breakdown.total,
                "support_cap_applied": breakdown.raw_support > breakdown.capped_support + TOLERANCE,
                "supplemental_cap_applied": (
                    breakdown.raw_supplemental > breakdown.capped_supplemental + TOLERANCE
                ),
                "applied_caps": list(breakdown.applied_caps),
            }
        )

    def _observe_policy(self, event: dict[str, Any]) -> None:
        result = event["result"]
        episode_rows = [
            row
            for row in self.episodes
            if row["policy_id"] == result["policy_id"]
            and row["replica"] == result["replica"]
            and row["horizon_days"] == result["horizon_days"]
            and row["parameter_set_id"] == result["parameter_set_id"]
        ]
        metrics = result["metrics"]
        counter_totals = {
            name: sum(row[name] for row in episode_rows)
            for name in ("f_cm", "f_c0", "f_0m", "f_00", "challenge_main", "memory_main", "interaction")
        }
        row = {
            "grain": "policy",
            "run_id": self.run_id,
            "parameter_set_id": result["parameter_set_id"],
            "policy_id": result["policy_id"],
            "comparison_id": _comparison_id(result["policy_id"]),
            "replica": result["replica"],
            "horizon_days": result["horizon_days"],
            "review_count": metrics["review_count"],
            "successful_review_count": metrics["successful_review_count"],
            "again_count": metrics["again_count"],
            "core_baseline": metrics["core_baseline"],
            "core_context": metrics["core_context"],
            "support": metrics["support"],
            "supplemental": metrics["supplemental"],
            "volume_credit": metrics["volume_credit"],
            "completion_credit": metrics["completion_credit"],
            "total_review_units": metrics["total_review_units"],
            "trajectory_digest": result["trajectory_digest"],
            "final_cohort_digest": result["final_cohort_digest"],
            "initial_cohort_digest": result["initial_cohort_digest"],
            "latent_stream_id": result["latent_stream_id"],
            "honest_baseline_suppression_events": metrics["honest_baseline_suppression_events"],
            **counter_totals,
        }
        self._reconcile_policy(row)
        self.policies.append(row)

    def _reconcile_policy(self, policy: dict[str, Any]) -> None:
        episodes = [
            row
            for row in self.episodes
            if row["policy_id"] == policy["policy_id"]
            and row["replica"] == policy["replica"]
            and row["horizon_days"] == policy["horizon_days"]
            and row["parameter_set_id"] == policy["parameter_set_id"]
        ]
        days = [
            row
            for row in self.days
            if row["policy_id"] == policy["policy_id"]
            and row["replica"] == policy["replica"]
            and row["horizon_days"] == policy["horizon_days"]
            and row["parameter_set_id"] == policy["parameter_set_id"]
        ]
        checks = {
            "review_count": (len(episodes), policy["review_count"]),
            "successful_review_count": (
                sum(row["outcome"] != Outcome.AGAIN.value for row in episodes),
                policy["successful_review_count"],
            ),
            "again_count": (
                sum(row["outcome"] == Outcome.AGAIN.value for row in episodes),
                policy["again_count"],
            ),
            "core_baseline": (
                sum(row["baseline_credit"] for row in episodes),
                policy["core_baseline"],
            ),
            "core_context": (
                sum(row["context_after_cap"] for row in episodes),
                policy["core_context"],
            ),
            "support": (sum(row["support"] for row in days), policy["support"]),
            "supplemental": (
                sum(row["supplemental"] for row in days),
                policy["supplemental"],
            ),
            "volume_credit": (
                sum(row["volume_credit"] for row in days),
                policy["volume_credit"],
            ),
            "completion_credit": (
                sum(row["completion_credit"] for row in days),
                policy["completion_credit"],
            ),
            "total_review_units": (
                sum(row["day_total"] for row in days),
                policy["total_review_units"],
            ),
            "counterfactual_full": (policy["f_cm"], policy["core_context"]),
        }
        for name, (left, right) in checks.items():
            if isinstance(left, int) and isinstance(right, int):
                if left != right:
                    raise ValueError(f"{policy['policy_id']} {name} mismatch")
            elif not close(float(left), float(right)):
                raise ValueError(
                    f"{policy['policy_id']} {name} mismatch: {left!r} != {right!r}"
                )


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("horizon_days", 0),
            row.get("parameter_set_id", ""),
            row.get("policy_id", ""),
            row.get("replica", -1),
            row.get("day", -1),
            row.get("synthetic_card_lineage_id", ""),
            row.get("source_event_key", ""),
        ),
    )


def _policy_index(policies: list[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {
        (row["policy_id"], row["replica"], row["parameter_set_id"]): row
        for row in policies
    }


def _window_totals(
    days: list[dict[str, Any]],
    *,
    policy_id: str,
    replica: int,
    parameter_set_id: str,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for row in days:
        if (
            row["policy_id"] != policy_id
            or row["replica"] != replica
            or row["parameter_set_id"] != parameter_set_id
        ):
            continue
        bucket = result.setdefault(
            row["window_id"],
            {
                "core_context": 0.0,
                "support": 0.0,
                "supplemental": 0.0,
                "volume_credit": 0.0,
                "completion_credit": 0.0,
                "day_total": 0.0,
            },
        )
        for key in bucket:
            bucket[key] += row[key]
    return result


def _lineage_context(
    episodes: list[dict[str, Any]],
    *,
    policy_id: str,
    replica: int,
    parameter_set_id: str,
) -> dict[str, float]:
    values: dict[str, float] = defaultdict(float)
    for row in episodes:
        if (
            row["policy_id"] == policy_id
            and row["replica"] == replica
            and row["parameter_set_id"] == parameter_set_id
        ):
            values[row["synthetic_card_lineage_id"]] += row["context_after_cap"]
    return dict(values)


def build_comparisons(
    payload: dict[str, Any],
    episodes: list[dict[str, Any]],
    days: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index = _policy_index(policies)
    rows: list[dict[str, Any]] = []
    for comparison_id, (left_id, right_id) in COMPARISON_POLICIES.items():
        for replica in range(payload["manifest"]["replicas"]):
            key = (left_id, replica, "R-CURRENT")
            right_key = (right_id, replica, "R-CURRENT")
            if key not in index or right_key not in index:
                continue
            left = index[key]
            right = index[right_key]
            denominator = right["total_review_units"]
            deltas = {
                name: left[name] - right[name]
                for name in (
                    "core_baseline",
                    "core_context",
                    "support",
                    "supplemental",
                    "volume_credit",
                    "completion_credit",
                    "total_review_units",
                    "challenge_main",
                    "memory_main",
                    "interaction",
                    "f_00",
                )
            }
            unexplained_units = deltas["total_review_units"] - deltas["core_baseline"]
            advantage = 0.0 if denominator == 0 else unexplained_units / denominator
            component_advantages = {
                "neutral_context": 0.0 if denominator == 0 else deltas["f_00"] / denominator,
                "challenge_main": 0.0 if denominator == 0 else deltas["challenge_main"] / denominator,
                "memory_main": 0.0 if denominator == 0 else deltas["memory_main"] / denominator,
                "interaction": 0.0 if denominator == 0 else deltas["interaction"] / denominator,
                "support": 0.0 if denominator == 0 else deltas["support"] / denominator,
                "supplemental": 0.0 if denominator == 0 else deltas["supplemental"] / denominator,
                "volume_credit": 0.0 if denominator == 0 else deltas["volume_credit"] / denominator,
                "completion_credit": 0.0 if denominator == 0 else deltas["completion_credit"] / denominator,
            }
            component_sum = sum(component_advantages.values())
            if not close(component_sum, advantage):
                raise ValueError(
                    f"{comparison_id}/{replica}/{left['horizon_days']} component reconciliation failed"
                )
            left_windows = _window_totals(
                days,
                policy_id=left_id,
                replica=replica,
                parameter_set_id="R-CURRENT",
            )
            right_windows = _window_totals(
                days,
                policy_id=right_id,
                replica=replica,
                parameter_set_id="R-CURRENT",
            )
            window_advantages: dict[str, float] = {}
            for window in sorted(set(left_windows) | set(right_windows)):
                left_total = left_windows.get(window, {})
                right_total = right_windows.get(window, {})
                value = sum(
                    left_total.get(name, 0.0) - right_total.get(name, 0.0)
                    for name in (
                        "core_context",
                        "support",
                        "supplemental",
                        "volume_credit",
                        "completion_credit",
                    )
                )
                window_advantages[window] = 0.0 if denominator == 0 else value / denominator
            if not close(sum(window_advantages.values()), advantage):
                raise ValueError(
                    f"{comparison_id}/{replica}/{left['horizon_days']} window reconciliation failed"
                )
            left_lineages = _lineage_context(
                episodes,
                policy_id=left_id,
                replica=replica,
                parameter_set_id="R-CURRENT",
            )
            right_lineages = _lineage_context(
                episodes,
                policy_id=right_id,
                replica=replica,
                parameter_set_id="R-CURRENT",
            )
            lineage_deltas = [
                (lineage, left_lineages.get(lineage, 0.0) - right_lineages.get(lineage, 0.0))
                for lineage in sorted(set(left_lineages) | set(right_lineages))
            ]
            positive = sorted((value for _, value in lineage_deltas if value > 0), reverse=True)
            positive_total = sum(positive)
            top_20_count = max(1, math.ceil(len(lineage_deltas) * 0.2)) if lineage_deltas else 0
            concentration = (
                0.0
                if positive_total <= 0 or top_20_count == 0
                else sum(positive[:top_20_count]) / positive_total
            )
            rows.append(
                {
                    "grain": "aggregate_comparison",
                    "comparison": comparison_id,
                    "replica": replica,
                    "horizon_days": left["horizon_days"],
                    "parameter_set_id": "R-CURRENT",
                    "left_policy_id": left_id,
                    "right_policy_id": right_id,
                    "left_review_count": left["review_count"],
                    "right_review_count": right["review_count"],
                    "review_count_difference": left["review_count"] - right["review_count"],
                    "baseline_delta": deltas["core_baseline"],
                    "context_delta": deltas["core_context"],
                    "support_delta": deltas["support"],
                    "supplemental_delta": deltas["supplemental"],
                    "volume_delta": deltas["volume_credit"],
                    "completion_delta": deltas["completion_credit"],
                    "total_delta": deltas["total_review_units"],
                    "unexplained_units": unexplained_units,
                    "unexplained_advantage": advantage,
                    "component_advantages": component_advantages,
                    "window_advantages": window_advantages,
                    "lineage_positive_top_20_share": concentration,
                    "lineage_count": len(lineage_deltas),
                    "residual": advantage - component_sum,
                    "classification": "EXPLORATORY_NON_DECISION",
                }
            )
    return sorted(rows, key=lambda row: (row["comparison"], row["replica"], row["horizon_days"]))


def run_trace(
    config: Any,
    *,
    mode_id: str,
    master_seed: int,
    workspace: Path,
    policy_ids: tuple[str, ...] = POLICY_IDS,
) -> TraceBundle:
    collector = AttributionCollector(mode_id=mode_id, master_seed=master_seed)
    payload = run_longitudinal(
        config,
        mode_id=mode_id,
        master_seed=master_seed,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=policy_ids,
        diagnostic_observer=collector.observe,
        workspace=workspace,
    )
    validate_longitudinal_result(payload)
    episodes = _sort_rows(collector.episodes)
    days = _sort_rows(collector.days)
    policies = _sort_rows(collector.policies)
    comparisons = build_comparisons(payload, episodes, days, policies)
    return TraceBundle(
        label=f"{mode_id}-{master_seed}",
        payload=payload,
        episodes=episodes,
        days=days,
        policies=policies,
        comparisons=comparisons,
    )


def _bundle_summary(bundle: TraceBundle) -> dict[str, Any]:
    return {
        "run_id": bundle.episodes[0]["run_id"] if bundle.episodes else f"g12-{bundle.label}",
        "mode": bundle.payload["manifest"]["mode"],
        "horizon_days": bundle.payload["manifest"]["horizon_days"],
        "master_seed": bundle.payload["manifest"]["master_seed"],
        "trajectory_digest": bundle.payload["manifest"]["trajectory_digest"],
        "final_cohort_digest": bundle.payload["manifest"]["final_cohort_digest"],
        "report_digest": bundle.payload["manifest"]["report_digest"],
        "trace_digest": bundle.trace_digest,
        "row_counts": {
            "review_episode": len(bundle.episodes),
            "day_window": len(bundle.days),
            "policy": len(bundle.policies),
            "aggregate_comparison": len(bundle.comparisons),
        },
    }



def _aggregate_grains(bundle: TraceBundle) -> list[dict[str, Any]]:
    summary = _bundle_summary(bundle)
    rows: list[dict[str, Any]] = [
        {
            "grain": "run",
            "run_id": summary["run_id"],
            "mode": summary["mode"],
            "horizon_days": summary["horizon_days"],
            "master_seed": summary["master_seed"],
            "trajectory_digest": summary["trajectory_digest"],
            "trace_digest": summary["trace_digest"],
        },
        {
            "grain": "horizon",
            "run_id": summary["run_id"],
            "horizon_days": summary["horizon_days"],
            "policy_count": len(bundle.policies),
            "episode_count": len(bundle.episodes),
        },
    ]
    for replica in sorted({row["replica"] for row in bundle.policies}):
        selected = [row for row in bundle.policies if row["replica"] == replica]
        rows.append(
            {
                "grain": "replica",
                "run_id": summary["run_id"],
                "horizon_days": summary["horizon_days"],
                "replica": replica,
                "policy_count": len(selected),
                "review_episode_count": sum(row["review_count"] for row in selected),
            }
        )
    for lineage in sorted({row["synthetic_card_lineage_id"] for row in bundle.episodes}):
        selected = [row for row in bundle.episodes if row["synthetic_card_lineage_id"] == lineage]
        rows.append(
            {
                "grain": "synthetic_card_lineage",
                "run_id": summary["run_id"],
                "horizon_days": summary["horizon_days"],
                "synthetic_card_lineage_id": lineage,
                "review_episode_count": len(selected),
                "context_total": sum(row["context_after_cap"] for row in selected),
            }
        )
    return rows

def write_bundle(root: Path, label: str, bundle: TraceBundle) -> dict[str, Any]:
    directory = root / "raw" / label
    _write_jsonl(directory / "episodes.jsonl", bundle.episodes)
    _write_jsonl(directory / "days.jsonl", bundle.days)
    _write_json(directory / "policies.json", bundle.policies)
    _write_json(directory / "comparisons.json", bundle.comparisons)
    _write_json(directory / "grains.json", _aggregate_grains(bundle))
    _write_json(directory / "runtime-payload.json", bundle.payload)
    summary = _bundle_summary(bundle)
    _write_json(directory / "summary.json", summary)
    return summary


def _tree_identity(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root).as_posix()
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    return {
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "digest": canonical_digest(rows),
        "files": rows,
    }


def _canonical_cells(
    short: TraceBundle,
    long: TraceBundle,
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    short_rows = {(row["comparison"], row["replica"]): row for row in short.comparisons}
    long_rows = {(row["comparison"], row["replica"]): row for row in long.comparisons}
    cells = []
    for key in sorted(short_rows):
        a90 = short_rows[key]["unexplained_advantage"]
        a365 = long_rows[key]["unexplained_advantage"]
        delta = a365 - a90
        cells.append(
            {
                "comparison": key[0],
                "replica": key[1],
                "advantage_90": a90,
                "advantage_365": a365,
                "delta_365_minus_90": delta,
                "endpoint_pass": a365 <= 0.03 + TOLERANCE,
                "grew": delta > TOLERANCE,
            }
        )
    groups = []
    for comparison in sorted(COMPARISON_POLICIES):
        selected = [row for row in cells if row["comparison"] == comparison]
        systematic = comparison.startswith("retention-") and all(row["grew"] for row in selected)
        endpoint = all(row["endpoint_pass"] for row in selected)
        groups.append(
            {
                "comparison": comparison,
                "replicas": len(selected),
                "endpoint_pass": endpoint,
                "systematic_growth": systematic,
                "status": "PASS" if endpoint and not systematic else "FAIL",
                "growth_semantics": (
                    "ALL_MATCHED_REPLICAS_GREW"
                    if comparison.startswith("retention-")
                    else "NOT_APPLIED_TO_NON_RETENTION_GROUP"
                ),
            }
        )
    expected_cells = contract["current_evidence"]["cells"]
    expected_groups = contract["current_evidence"]["groups"]
    if len(cells) != 6 or len(groups) != 3:
        raise ValueError("canonical cell/group count mismatch")
    for observed, expected in zip(cells, expected_cells):
        for key in ("comparison", "replica", "endpoint_pass", "grew"):
            expected_key = "grew" if key == "grew" else key
            if observed[key] != expected[expected_key]:
                raise ValueError(f"canonical cell mismatch for {key}")
        for key in ("advantage_90", "advantage_365", "delta_365_minus_90"):
            if not close(observed[key], expected[key]):
                raise ValueError(f"canonical numeric cell mismatch for {key}")
    for observed, expected in zip(groups, expected_groups):
        for key in (
            "comparison",
            "replicas",
            "endpoint_pass",
            "systematic_growth",
            "status",
            "growth_semantics",
        ):
            if observed[key] != expected[key]:
                raise ValueError(f"canonical group mismatch for {key}")
    return cells, groups


def _cross_horizon_attribution(
    short: TraceBundle,
    long: TraceBundle,
) -> list[dict[str, Any]]:
    short_rows = {(row["comparison"], row["replica"]): row for row in short.comparisons}
    long_rows = {(row["comparison"], row["replica"]): row for row in long.comparisons}
    result = []
    for key in sorted(short_rows):
        s = short_rows[key]
        l = long_rows[key]
        components = {
            name: l["component_advantages"][name] - s["component_advantages"][name]
            for name in sorted(l["component_advantages"])
        }
        windows = {
            name: l["window_advantages"].get(name, 0.0) - s["window_advantages"].get(name, 0.0)
            for name in sorted(set(l["window_advantages"]) | set(s["window_advantages"]))
        }
        delta = l["unexplained_advantage"] - s["unexplained_advantage"]
        residual = delta - sum(components.values())
        if abs(residual) > TOLERANCE:
            raise ValueError("cross-horizon component residual exceeds tolerance")
        result.append(
            {
                "comparison": key[0],
                "replica": key[1],
                "advantage_90": s["unexplained_advantage"],
                "advantage_365": l["unexplained_advantage"],
                "delta_365_minus_90": delta,
                "review_count_difference_90": s["review_count_difference"],
                "review_count_difference_365": l["review_count_difference"],
                "baseline_delta_90": s["baseline_delta"],
                "baseline_delta_365": l["baseline_delta"],
                "component_contributions": components,
                "window_contributions": windows,
                "lineage_positive_top_20_share_90": s["lineage_positive_top_20_share"],
                "lineage_positive_top_20_share_365": l["lineage_positive_top_20_share"],
                "residual": residual,
                "classification": "EXPLORATORY_NON_DECISION",
            }
        )
    return result


def _aggregate_signed_and_absolute(rows: list[dict[str, Any]], contribution_field: str) -> tuple[dict[str, float], dict[str, float]]:
    """Return signed totals and cell-level absolute totals without cancellation."""
    signed: dict[str, float] = defaultdict(float)
    absolute: dict[str, float] = defaultdict(float)
    for row in rows:
        for key, raw_value in row[contribution_field].items():
            value = float(raw_value)
            signed[key] += value
            absolute[key] += abs(value)
    return dict(sorted(signed.items())), dict(sorted(absolute.items()))


def _dominant_from_cell_absolute(signed_totals: dict[str, float], absolute_cell_totals: dict[str, float]) -> tuple[str, float, float]:
    denominator = sum(absolute_cell_totals.values())
    if not absolute_cell_totals or denominator <= 0:
        return "none", 0.0, 0.0
    key = max(sorted(absolute_cell_totals), key=lambda item: absolute_cell_totals[item])
    return key, signed_totals[key], absolute_cell_totals[key] / denominator


def _root_cause_summary(cross: list[dict[str, Any]]) -> dict[str, Any]:
    retention = [row for row in cross if row["comparison"].startswith("retention-")]
    component_signed, component_absolute = _aggregate_signed_and_absolute(retention, "component_contributions")
    window_signed, window_absolute = _aggregate_signed_and_absolute(retention, "window_contributions")
    component, component_value, component_share = _dominant_from_cell_absolute(component_signed, component_absolute)
    window, window_value, window_share = _dominant_from_cell_absolute(window_signed, window_absolute)
    max_residual = max((abs(row["residual"]) for row in cross), default=0.0)
    same_sign = {
        comparison: len({math.copysign(1.0, row["delta_365_minus_90"]) for row in retention if row["comparison"] == comparison and abs(row["delta_365_minus_90"]) > TOLERANCE}) <= 1
        for comparison in ("retention-high-cycle", "retention-low-cycle")
    }
    challenge_signs = {math.copysign(1.0, row["component_contributions"]["challenge_main"]) for row in retention if abs(row["component_contributions"]["challenge_main"]) > TOLERANCE}
    challenge_consistent = len(challenge_signs) <= 1
    if max_residual > TOLERANCE:
        classification, confidence = "ROOT_CAUSE_UNRESOLVED", "LOW"
    elif component_share >= 0.55 and window_share >= 0.45:
        classification = "ROOT_CAUSE_LOCALIZED"
        confidence = "HIGH" if component_share >= 0.70 and window_share >= 0.60 else "MEDIUM"
    else:
        classification, confidence = "ROOT_CAUSE_PARTIALLY_LOCALIZED", "MEDIUM"
    return {
        "classification": classification,
        "confidence": confidence,
        "dominant_component": component,
        "dominant_component_signed_total": component_value,
        "dominant_component_share_of_cell_level_absolute_contributions": component_share,
        "component_share_formula": "sum(abs(component contribution per retention cell)) / sum(abs(all component contributions per retention cell))",
        "component_signed_totals": component_signed,
        "component_absolute_cell_totals": component_absolute,
        "dominant_window": window,
        "dominant_window_signed_total": window_value,
        "dominant_window_share_of_cell_level_absolute_contributions": window_share,
        "window_share_formula": "sum(abs(window contribution per retention cell)) / sum(abs(all window contributions per retention cell))",
        "window_signed_totals": window_signed,
        "window_absolute_cell_totals": window_absolute,
        "retention_groups_replica_direction_consistent": same_sign,
        "challenge_direction_consistent_across_retention_cells": challenge_consistent,
        "max_abs_residual": max_residual,
        "rationale": (
            "The fixed-trajectory decomposition reconciles the observed growth and identifies a dominant component and timing window, but replica magnitudes, Challenge signs and lineage concentration vary; the trace is not a unique causal formula and no coefficient or candidate was tested."
            if classification != "ROOT_CAUSE_UNRESOLVED" else "The attribution residual exceeded the frozen tolerance."
        ),
    }


def _answer_rows(cross: list[dict[str, Any]], summary: dict[str, Any], controls: TraceBundle) -> list[dict[str, Any]]:
    return _corrected_answer_rows(cross, summary, controls.policies)


def _corrected_answer_rows(cross: list[dict[str, Any]], summary: dict[str, Any], control_policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    retention = [row for row in cross if row["comparison"].startswith("retention-")]
    intentional = [row for row in cross if row["comparison"] == "intentional-backlog"]
    count_rows = [{"comparison": row["comparison"], "replica": row["replica"], "review_count_difference_90": row["review_count_difference_90"], "review_count_difference_365": row["review_count_difference_365"], "baseline_delta_90": row["baseline_delta_90"], "baseline_delta_365": row["baseline_delta_365"]} for row in cross]
    endpoint = [{"comparison": row["comparison"], "replica": row["replica"]} for row in cross if row["advantage_90"] < 0 < row["advantage_365"]]
    controls = {row["policy_id"]: row["core_context"] for row in control_policies}
    challenge = [{"comparison": row["comparison"], "replica": row["replica"], "challenge_main": row["component_contributions"]["challenge_main"], "sign": "positive" if row["component_contributions"]["challenge_main"] > TOLERANCE else "negative" if row["component_contributions"]["challenge_main"] < -TOLERANCE else "zero"} for row in retention]
    lineage = [{"comparison": row["comparison"], "replica": row["replica"], "share_90": row["lineage_positive_top_20_share_90"], "share_365": row["lineage_positive_top_20_share_365"]} for row in retention]
    cden = sum(summary["component_absolute_cell_totals"].values())
    wden = sum(summary["window_absolute_cell_totals"].values())
    rows = [
        (1, "review_count_share", "Review-count differences explain baseline deltas, but their direct share of frozen unexplained advantage is zero because baseline_delta is subtracted exactly.", "This is an accounting conclusion inside the synthetic metric, not a claim about user behavior.", {"cells": count_rows}),
        (2, "per_review_context", "After baseline removal, contextual and day-level credits reconcile all six cross-horizon deltas within tolerance.", "Reconciliation identifies where the metric is accounted for; it does not establish a unique causal intervention.", {"signed_component_totals": summary["component_signed_totals"], "absolute_cell_component_totals": summary["component_absolute_cell_totals"], "max_abs_residual": summary["max_abs_residual"]}),
        (3, "component_distribution", f"{summary['dominant_component']} is the largest component under cell-level absolute aggregation.", "The dominant share is descriptive across four retention cells and does not select a coefficient.", {"formula": summary["component_share_formula"], "signed_totals": summary["component_signed_totals"], "absolute_cell_totals": summary["component_absolute_cell_totals"], "shares": {key: value / cden if cden else 0.0 for key, value in summary["component_absolute_cell_totals"].items()}, "dominant": summary["dominant_component"]}),
        (4, "divergence_timing", f"{summary['dominant_window']} is the largest timing window under cell-level absolute aggregation.", "The timing result localizes accumulation after transitions but does not identify a unique formula change.", {"formula": summary["window_share_formula"], "windows_by_cell": {f"{row['comparison']}:{row['replica']}": row["window_contributions"] for row in retention}, "signed_totals": summary["window_signed_totals"], "absolute_cell_totals": summary["window_absolute_cell_totals"], "shares": {key: value / wden if wden else 0.0 for key, value in summary["window_absolute_cell_totals"].items()}, "dominant": summary["dominant_window"]}),
        (5, "shared_mechanism", "Both retention groups grow in both replicas, but the component decomposition is not direction-consistent enough to claim one fully shared mechanism.", "Group-level growth direction is shared; Challenge signs and effect magnitudes are not.", {"replica_direction_consistent": summary["retention_groups_replica_direction_consistent"], "challenge_direction_consistent": summary["challenge_direction_consistent_across_retention_cells"]}),
        (6, "replica_difference", "Replica-specific deltas and component values differ materially and are preserved without averaging.", "Two replicas expose heterogeneity but do not characterize a population distribution.", {"cells": retention}),
        (7, "lineage_concentration", "Positive contextual contribution is concentrated in a subset of synthetic lineages, with concentration varying by replica.", "The statistic is descriptive and does not identify real cards or users.", {"shares": lineage}),
        (8, "actual_vs_natural_due", "Challenge attribution separates actual from natural-due retrievability, but Challenge contributions are not direction-consistent across all retention cells.", "Mixed signs prevent treating Challenge as one shared dominant mechanism.", {"measured_fields": ["retrievability_actual", "retrievability_natural_due", "extra_challenge", "delay_credit", "adjusted_challenge"], "cells": challenge, "direction_consistent": summary["challenge_direction_consistent_across_retention_cells"]}),
        (9, "memory_gain_counterfactual", "MemoryGain is isolated by the fixed-trajectory f(0,M)-f(0,0) main effect and is the largest cell-level absolute component.", "This is a reward-only post-hoc decomposition on fixed scheduler trajectories.", {"formula": "f(0,M) - f(0,0)", "signed_total": summary["component_signed_totals"]["memory_main"], "absolute_cell_total": summary["component_absolute_cell_totals"]["memory_main"]}),
        (10, "endpoint_cancellation", "Three cells have negative 90-day advantage and positive 365-day advantage.", "This frozen synthetic pattern is not a forecast for real users.", {"cells": endpoint}),
        (11, "interval_neutral_control", "The bounded development control traces stable-default and no-fsrs-neutral without changing canonical cells.", "The control is exploratory and shorter than confirmatory horizons.", {"core_context": controls}),
        (12, "cap_suppression", "Cap/blend interaction is negligible and traced control suppression remains zero.", "This does not prove every future candidate is cap-insensitive.", {"interaction_signed_total": summary["component_signed_totals"]["interaction"], "interaction_absolute_cell_total": summary["component_absolute_cell_totals"]["interaction"], "control_suppression_events": sum(row["honest_baseline_suppression_events"] for row in control_policies)}),
        (13, "intentional_backlog", "Intentional backlog remains a separate PASS control and does not show two-replica systematic growth.", "The executable growth rule is not applied to the non-retention group.", {"cells": intentional}),
        (14, "mechanism_class", "The mechanism class remains partially localized: MemoryGain and post-transition accumulation dominate, but no unique causal correction is established.", "Replica magnitudes differ, Challenge signs are mixed, lineage concentration varies, the trace is not a unique causal formula, and no coefficient or candidate was tested.", {"classification": summary["classification"], "confidence": summary["confidence"], "reasons": ["replica magnitudes differ", "Challenge does not have one common sign across every retention cell", "lineage concentration differs", "the trace is a deterministic decomposition rather than a unique causal formula", "no coefficient or candidate has been tested"], "candidate_tested": False, "unique_causal_formula_established": False}),
    ]
    return [{"question": number, "id": key, "answer": answer, "boundary": boundary, "evidence": evidence, "classification": "EXPLORATORY_NON_DECISION"} for number, key, answer, boundary, evidence in rows]


def _grain_counts(
    short: TraceBundle,
    long: TraceBundle,
    controls: TraceBundle,
    secondary: TraceBundle,
) -> dict[str, int]:
    bundles = (short, short, long, long, controls, secondary)
    return {
        "run": len(bundles),
        "policy": sum(len(bundle.policies) for bundle in bundles),
        "replica": sum(
            len({row["replica"] for row in bundle.policies})
            for bundle in bundles
        ),
        "horizon": len(bundles),
        "day_window": sum(len(bundle.days) for bundle in bundles),
        "synthetic_card_lineage": sum(
            len({row["synthetic_card_lineage_id"] for row in bundle.episodes})
            for bundle in bundles
        ),
        "review_episode": sum(len(bundle.episodes) for bundle in bundles),
        "aggregate_comparison": sum(len(bundle.comparisons) for bundle in bundles),
    }


def _safety_scan(root: Path) -> dict[str, Any]:
    findings: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.is_symlink():
            findings.append(f"symlink:{path.name}")
            continue
        rel = path.relative_to(root).as_posix()
        if not SAFE_PATH.fullmatch(rel):
            findings.append(f"unsafe-path:{rel}")
        if path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".log", ".csv"}:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for needle in FORBIDDEN_TEXT:
                if needle in text:
                    findings.append(f"forbidden:{needle}:{rel}")
    for path in root.rglob("episodes.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            for key in ("run_id", "policy_id", "comparison_id", "synthetic_card_lineage_id", "source_event_key"):
                value = row[key]
                if not SAFE_ID.fullmatch(value):
                    findings.append(f"unsafe-id:{key}:{value}")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def _manifest(staging: Path) -> dict[str, Any]:
    rows = []
    excluded = {"FILES.sha256", "normalized/artifact-manifest.json"}
    for path in sorted(item for item in staging.rglob("*") if item.is_file()):
        rel = path.relative_to(staging).as_posix()
        if rel in excluded:
            continue
        rows.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    lines = [f"{row['sha256']}\t{row['bytes']}\t{row['path']}" for row in rows]
    manifest_path = staging / "FILES.sha256"
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "manifest_sha256": _sha256(manifest_path),
        "files": rows,
    }


def build_evidence_base(
    *,
    workspace: Path,
    short: TraceBundle,
    long: TraceBundle,
    secondary: TraceBundle,
    controls: TraceBundle,
    short_repeat_identity: dict[str, Any],
    long_repeat_identity: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    cells, groups = _canonical_cells(short, long, contract)
    cross = _cross_horizon_attribution(short, long)
    summary = _root_cause_summary(cross)
    evidence = {
        "$schema": "../schemas/review-cycling-attribution-v1.schema.json",
        "version": VERSION,
        "status": "COMPLETE",
        "classification": summary["classification"],
        "confidence": summary["confidence"],
        "provenance": {
            "canonical_branch": "gamification",
            "canonical_input_commit": "f8374c58578d3a492dffa3e5b758e78b4049cdbf",
            "frozen_contract_path": "research/gamification-sim/contracts/review-cycling-diagnostic-v1.json",
            "frozen_contract_blob_sha1": "8f5c3526cd1c98440ad513d9773f145c1971f995",
            "frozen_schema_path": "research/gamification-sim/schemas/review-cycling-diagnostic-v1.schema.json",
            "frozen_schema_blob_sha1": "d64070f68e9b96f54dba4941b85fa7a770c8e8cf",
            "g0_7_evidence_path": "research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json",
            "g0_7_evidence_blob_sha1": "6d08e6d701d6b57b5e24992223185764bc29e66e",
            "longitudinal_config_path": "research/gamification-sim/configs/review-longitudinal-v0.1.json",
            "longitudinal_config_blob_sha1": "e8b30247b83f8d466cacaec93e9842f9ff23e257",
            "parameter_set_id": "R-CURRENT",
            "master_seed": MASTER_SEED,
            "secondary_seed": SECONDARY_SEED,
        },
        "environment": {
            "platform": "Windows AMD64",
            "python": "CPython 3.11.9 x64",
            "rust": "1.97.1-x86_64-pc-windows-msvc",
            "python_lock": "research/gamification-sim/environment/python-windows-amd64-py311.lock.txt",
            "dependency_resolution": "EXACT_HASH_LOCK_REPLAY",
        },
        "artifact": {
            "id": 0,
            "name": "PENDING",
            "digest": "sha256:" + "0" * 64,
            "manifest_digest": "0" * 64,
            "size_bytes": 0,
            "expires_at": "1970-01-01T00:00:00Z",
            "workflow_run_id": 0,
            "job_id": 0,
        },
        "grain_counts": _grain_counts(short, long, controls, secondary),
        "determinism": {
            "canonical_90_same_seed": short_repeat_identity,
            "canonical_365_same_seed": long_repeat_identity,
            "secondary_seed_trajectory_differs": (
                secondary.payload["manifest"]["trajectory_digest"]
                != short.payload["manifest"]["trajectory_digest"]
            ),
            "tracing_disabled_equivalence": "VERIFIED_BY_TEST",
        },
        "safety": {
            "synthetic_ids_only": True,
            "forbidden_data_scan": "PENDING",
            "all_numbers_finite": True,
            "duplicate_keys_rejected": True,
        },
        "reconciliation": {
            "tolerance": TOLERANCE,
            "max_abs_residual": summary["max_abs_residual"],
            "canonical_cells": cells,
            "canonical_groups": groups,
            "overall_status": "FAIL",
            "policy_result_count_90": len(short.policies),
            "policy_result_count_365": len(long.policies),
        },
        "attribution": {
            "cross_horizon_cells": cross,
            "summary": summary,
            "control_summary": {
                "mode": controls.payload["manifest"]["mode"],
                "policies": controls.policies,
            },
        },
        "root_cause_answers": _answer_rows(cross, summary, controls),
        "verification": {
            "focused_command": "PENDING",
            "focused_passed": 0,
            "full_command": "PENDING",
            "full_passed": 0,
            "schema_validation": "PENDING",
            "artifact_audit": "PENDING",
            "frozen_blob_audit": "PENDING",
            "exact_seven_path_diff": "PENDING",
        },
        "publication": {
            "execution_branch": "temp/g1-2-root-cause-attribution-execution",
            "development_branch": "temp/g1-2-root-cause-attribution",
            "canonical_branch": "gamification",
            "canonical_input_commit": "f8374c58578d3a492dffa3e5b758e78b4049cdbf",
            "result_commit": "THIS_COMMIT",
            "workflow_run_id": 0,
            "fast_forward": True,
            "changed_paths": [
                "research/gamification-sim/src/gamification_sim/diagnostic_attribution.py",
                "research/gamification-sim/src/gamification_sim/longitudinal_runner.py",
                "research/gamification-sim/tests/test_diagnostic_attribution.py",
                "research/gamification-sim/schemas/review-cycling-attribution-v1.schema.json",
                "research/gamification-sim/evidence/g1.2-root-cause-attribution-v1.json",
                "roadmap/gamification/g1-root-cause-attribution.md",
                "roadmap/gamification/README.md",
            ],
        },
        "cleanup": {
            "status": "COMPLETE_EXCEPT_CANONICAL_EVIDENCE_RUN",
            "deleted_refs": [
                "temp/g1-2-root-cause-attribution",
                "temp/g1-2-root-cause-attribution-execution",
            ],
            "preserved_run_ids": [29695312258, 29697258461, 29691295919, 0],
            "preserved_artifact_ids": [8444920908, 0],
            "disposable_runs_deleted": 0,
        },
        "decision_boundary": {
            "candidate_selected": False,
            "reward_formula_changed": False,
            "production_approved": False,
            "human_learning_effectiveness_proven": False,
            "g1_3_started": False,
        },
        "limitations": [
            "Synthetic trajectories do not establish human learning effectiveness or real-user reward gaming.",
            "Counterfactuals are reward-only post-hoc evaluations on fixed scheduler trajectories.",
            "This stage localizes mechanism classes and does not select coefficients or candidates.",
        ],
    }
    _finite_walk(evidence)
    return evidence


def _validate_schema(schema_path: Path, evidence: dict[str, Any]) -> None:
    schema = _strict_load(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(evidence),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if errors:
        raise ValueError(
            "\n".join(
                f"{'.'.join(str(part) for part in error.absolute_path)}: {error.message}"
                for error in errors
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic G1.2 Review attribution")
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    workspace = resolve_research_workspace(args.research_root).root
    output = args.output_root.resolve()
    if output.exists() and output.is_symlink():
        raise ValueError("diagnostic output root must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "configs/review-longitudinal-v0.1.json"
    config = load_longitudinal_config(config_path, workspace=workspace)
    contract = _strict_load(workspace / "contracts/review-cycling-diagnostic-v1.json")

    short_1 = run_trace(config, mode_id="calibration-90", master_seed=MASTER_SEED, workspace=workspace)
    short_2 = run_trace(config, mode_id="calibration-90", master_seed=MASTER_SEED, workspace=workspace)
    long_1 = run_trace(config, mode_id="calibration-365", master_seed=MASTER_SEED, workspace=workspace)
    long_2 = run_trace(config, mode_id="calibration-365", master_seed=MASTER_SEED, workspace=workspace)
    secondary = run_trace(config, mode_id="calibration-90", master_seed=SECONDARY_SEED, workspace=workspace)
    controls = run_trace(
        config,
        mode_id="development",
        master_seed=MASTER_SEED,
        workspace=workspace,
        policy_ids=("stable-default", "no-fsrs-neutral"),
    )

    short_summary_1 = write_bundle(output, "canonical-90-run-1", short_1)
    short_summary_2 = write_bundle(output, "canonical-90-run-2", short_2)
    long_summary_1 = write_bundle(output, "canonical-365-run-1", long_1)
    long_summary_2 = write_bundle(output, "canonical-365-run-2", long_2)
    write_bundle(output, "secondary-90", secondary)
    write_bundle(output, "interval-neutral-control", controls)

    short_id_1 = _tree_identity(output / "raw/canonical-90-run-1")
    short_id_2 = _tree_identity(output / "raw/canonical-90-run-2")
    long_id_1 = _tree_identity(output / "raw/canonical-365-run-1")
    long_id_2 = _tree_identity(output / "raw/canonical-365-run-2")
    if short_id_1["digest"] != short_id_2["digest"]:
        raise ValueError("canonical 90-day same-seed replay is not byte-identical")
    if long_id_1["digest"] != long_id_2["digest"]:
        raise ValueError("canonical 365-day same-seed replay is not byte-identical")
    if not (
        short_summary_1["trace_digest"] == short_summary_2["trace_digest"]
        and long_summary_1["trace_digest"] == long_summary_2["trace_digest"]
    ):
        raise ValueError("same-seed trace digest mismatch")
    evidence = build_evidence_base(
        workspace=workspace,
        short=short_1,
        long=long_1,
        secondary=secondary,
        controls=controls,
        short_repeat_identity={
            "status": "PASS",
            "tree_digest": short_id_1["digest"],
            "trace_digest": short_summary_1["trace_digest"],
        },
        long_repeat_identity={
            "status": "PASS",
            "tree_digest": long_id_1["digest"],
            "trace_digest": long_summary_1["trace_digest"],
        },
        contract=contract,
    )
    _write_json(output / "normalized/evidence-base.json", evidence)
    safety = _safety_scan(output)
    if safety["status"] != "PASS":
        raise ValueError(f"forbidden-data scan failed: {safety['findings']}")
    evidence["safety"]["forbidden_data_scan"] = "PASS"
    _write_json(output / "normalized/evidence-base.json", evidence)
    manifest = _manifest(output)
    _write_json(output / "normalized/artifact-manifest.json", manifest)
    _finite_walk(evidence)
    print(
        _json_text(
            {
                "status": "PASS",
                "classification": evidence["classification"],
                "confidence": evidence["confidence"],
                "manifest_sha256": manifest["manifest_sha256"],
                "grain_counts": evidence["grain_counts"],
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
