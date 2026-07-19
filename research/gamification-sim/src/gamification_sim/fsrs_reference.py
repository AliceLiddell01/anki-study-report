from __future__ import annotations

import importlib.metadata
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .canonical_json import canonical_digest
from .episode_reward import evaluate_episode
from .models import ConfidenceLevel, MemoryContext, Outcome, ReviewEpisodeInput
from .workspace import cargo_environment, cargo_run_command
from .strict_json import load_strict_json, loads_strict


TRAJECTORY_VERSION = "fsrs-trajectories-v0.1"
FSRS_RS_VERSION = "6.6.1"
STATE_TOLERANCE = 1e-4
RETRIEVABILITY_TOLERANCE = 1e-4
INTERVAL_TOLERANCE_DAYS = 1e-6


def _validate_contract(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict) or set(payload) != {
        "trajectory_version", "timezone", "start_datetime", "scheduler", "trajectories"
    }:
        raise ValueError(f"{path}: invalid trajectory contract fields")
    if payload["trajectory_version"] != TRAJECTORY_VERSION or payload["timezone"] != "UTC":
        raise ValueError(f"{path}: unsupported trajectory version or timezone")
    start = datetime.fromisoformat(payload["start_datetime"])
    if start.tzinfo != timezone.utc:
        raise ValueError(f"{path}: start_datetime must be explicit UTC")
    trajectories = payload["trajectories"]
    if not isinstance(trajectories, list) or len(trajectories) != 10:
        raise ValueError(f"{path}: exactly 10 trajectories are required")
    ids = [item["trajectory_id"] for item in trajectories]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: trajectory IDs must be unique")
    for trajectory in trajectories:
        if set(trajectory) != {"trajectory_id", "mode", "desired_retention", "reviews"}:
            raise ValueError(f"{path}: invalid fields in {trajectory.get('trajectory_id')}")
        if trajectory["mode"] not in {"fsrs", "no_fsrs"}:
            raise ValueError(f"{path}: invalid trajectory mode")
        retention = trajectory["desired_retention"]
        if isinstance(retention, bool) or not isinstance(retention, (int, float)) or not 0.7 <= retention <= 0.99:
            raise ValueError(f"{path}: desired_retention must be finite in [0.7, 0.99]")
        previous = -1
        for review in trajectory["reviews"]:
            if set(review) != {"day", "rating"} or type(review["day"]) is not int:
                raise ValueError(f"{path}: invalid review step")
            if review["day"] < previous or review["rating"] not in {"Again", "Hard", "Good", "Easy"}:
                raise ValueError(f"{path}: invalid review ordering or rating")
            previous = review["day"]
        if trajectory["mode"] == "no_fsrs" and trajectory["reviews"]:
            raise ValueError(f"{path}: no_fsrs fallback must not invent FSRS reviews")


def _python_reference(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from fsrs import Card, Rating, Scheduler
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise ValueError("install the research fsrs extra: pip install -e .[fsrs]") from exc
    scheduler_settings = payload["scheduler"]
    start = datetime.fromisoformat(payload["start_datetime"])
    rating_by_name = {
        "Again": Rating.Again,
        "Hard": Rating.Hard,
        "Good": Rating.Good,
        "Easy": Rating.Easy,
    }
    trajectories = []
    for card_index, trajectory in enumerate(payload["trajectories"], 1):
        if trajectory["mode"] == "no_fsrs":
            trajectories.append({"trajectory_id": trajectory["trajectory_id"], "mode": "no_fsrs", "steps": [], "serialized_cards": []})
            continue
        scheduler = Scheduler(
            desired_retention=float(trajectory["desired_retention"]),
            learning_steps=tuple(timedelta(minutes=value) for value in scheduler_settings["learning_steps_minutes"]),
            relearning_steps=tuple(timedelta(minutes=value) for value in scheduler_settings["relearning_steps_minutes"]),
            maximum_interval=scheduler_settings["maximum_interval_days"],
            enable_fuzzing=scheduler_settings["fuzzing"],
        )
        card = Card(card_id=card_index, due=start)
        steps = []
        serialized_cards = [card.to_dict()]
        for review in trajectory["reviews"]:
            review_at = start + timedelta(days=review["day"])
            retrievability = scheduler.get_card_retrievability(card, review_at)
            good_copy = Card.from_dict(card.to_dict())
            good_card, _ = scheduler.review_card(good_copy, Rating.Good, review_at)
            card, log = scheduler.review_card(card, rating_by_name[review["rating"]], review_at)
            interval = (card.due - review_at).total_seconds() / 86400.0
            step = {
                "day": review["day"],
                "rating": review["rating"],
                "retrievability_before": float(retrievability),
                "stability": float(card.stability),
                "difficulty": float(card.difficulty),
                "scheduled_interval_days": interval,
                "counterfactual_good_stability": float(good_card.stability),
                "review_log": log.to_dict(),
            }
            if not all(
                math.isfinite(step[key])
                for key in (
                    "retrievability_before", "stability", "difficulty",
                    "scheduled_interval_days", "counterfactual_good_stability",
                )
            ):
                raise ValueError(f"non-finite py-fsrs state in {trajectory['trajectory_id']}")
            steps.append(step)
            serialized_cards.append(card.to_dict())
        trajectories.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "mode": "fsrs",
                "desired_retention": trajectory["desired_retention"],
                "steps": steps,
                "serialized_cards": serialized_cards,
            }
        )
    return {
        "implementation": "py-fsrs",
        "package_version": importlib.metadata.version("fsrs"),
        "trajectories": trajectories,
    }


def _rust_reference(package_root: Path, contract_path: Path) -> dict[str, Any]:
    command = cargo_run_command(package_root, "fsrs-reference", str(contract_path))
    process = subprocess.run(
        command, cwd=package_root, text=True, capture_output=True, check=False,
        env=cargo_environment(), timeout=120,
    )
    if process.returncode:
        raise ValueError(f"fsrs-rs reference failed ({process.returncode}): {process.stderr.strip()}")
    result = loads_strict(process.stdout, context="fsrs-rs output")
    if result.get("crate_version") != FSRS_RS_VERSION:
        raise ValueError("unexpected fsrs-rs crate version")
    return result


def _compare_references(python: dict[str, Any], rust: dict[str, Any]) -> dict[str, Any]:
    rust_by_id = {item["trajectory_id"]: item for item in rust["trajectories"]}
    comparisons = []
    state_mismatches = []
    known_interval_differences = []
    for trajectory in python["trajectories"]:
        other = rust_by_id[trajectory["trajectory_id"]]
        if trajectory["mode"] == "no_fsrs":
            comparisons.append({"trajectory_id": trajectory["trajectory_id"], "status": "neutral-fallback", "step_count": 0})
            continue
        if len(trajectory["steps"]) != len(other["steps"]):
            state_mismatches.append(f"{trajectory['trajectory_id']}: step count")
            continue
        max_deltas = {"retrievability": 0.0, "stability": 0.0, "difficulty": 0.0, "counterfactual_good_stability": 0.0, "scheduled_interval_days": 0.0}
        for index, (left, right) in enumerate(zip(trajectory["steps"], other["steps"])):
            if left["day"] != right["day"] or left["rating"] != right["rating"]:
                state_mismatches.append(f"{trajectory['trajectory_id']}[{index}]: trajectory signature")
            for output, left_key, right_key, tolerance in (
                ("retrievability", "retrievability_before", "retrievability_before", RETRIEVABILITY_TOLERANCE),
                ("stability", "stability", "stability", STATE_TOLERANCE),
                ("difficulty", "difficulty", "difficulty", STATE_TOLERANCE),
                ("counterfactual_good_stability", "counterfactual_good_stability", "counterfactual_good_stability", STATE_TOLERANCE),
            ):
                left_value = left[left_key]
                right_value = right[right_key]
                if left_value is None and right_value is None:
                    delta = 0.0
                elif left_value is None or right_value is None:
                    delta = math.inf
                else:
                    delta = abs(left_value - right_value)
                max_deltas[output] = max(max_deltas[output], delta)
                if delta > tolerance:
                    state_mismatches.append(f"{trajectory['trajectory_id']}[{index}].{output}: {delta}")
            interval_delta = abs(left["scheduled_interval_days"] - right["scheduled_interval_days"])
            max_deltas["scheduled_interval_days"] = max(max_deltas["scheduled_interval_days"], interval_delta)
            if interval_delta > INTERVAL_TOLERANCE_DAYS:
                known_interval_differences.append(
                    {
                        "trajectory_id": trajectory["trajectory_id"],
                        "step": index,
                        "py_fsrs_days": left["scheduled_interval_days"],
                        "fsrs_rs_days": right["scheduled_interval_days"],
                        "classification": "known-scheduler-layer-difference",
                    }
                )
        comparisons.append({"trajectory_id": trajectory["trajectory_id"], "status": "compared", "step_count": len(trajectory["steps"]), "max_deltas": max_deltas})
    return {
        "comparisons": comparisons,
        "state_mismatches": state_mismatches,
        "known_interval_differences": known_interval_differences,
        "known_differences": [
            "py-fsrs applies learning/relearning step scheduling while fsrs-rs next_states reports model interval",
            "py-fsrs uses Python float while fsrs-rs state inference uses f32",
            "serialized Card/ReviewLog objects are implementation-specific; normalized trajectory signatures and states are compared",
        ],
    }


def _reward_integration() -> dict[str, Any]:
    high = ReviewEpisodeInput(
        "fsrs-high", "fsrs-high", "2026-01-01", Outcome.GOOD,
        memory=MemoryContext(0.80, 0.80, 10.0, 12.0, ConfidenceLevel.HIGH),
    )
    low = ReviewEpisodeInput(
        "fsrs-low", "fsrs-low", "2026-01-01", Outcome.GOOD,
        memory=MemoryContext(0.80, 0.80, 10.0, 12.0, ConfidenceLevel.LOW),
    )
    fallback = ReviewEpisodeInput("fsrs-none", "fsrs-none", "2026-01-01", Outcome.GOOD)
    backlog = ReviewEpisodeInput(
        "fsrs-backlog", "fsrs-backlog", "2026-01-01", Outcome.GOOD,
        memory=MemoryContext(0.30, 0.80, 10.0, 13.0, ConfidenceLevel.HIGH),
    )
    results = {name: evaluate_episode(value) for name, value in (("high_confidence", high), ("low_confidence", low), ("no_fsrs", fallback), ("backlog_natural_due", backlog))}
    baseline = next(iter(results.values())).baseline
    if any(abs(item.baseline - baseline) > 1e-12 for item in results.values()):
        raise ValueError("FSRS adapter uncertainty changed CoreBaseline")
    return {
        "core_baseline": baseline,
        "all_baselines_equal": True,
        "states": {
            name: {
                "context": item.context,
                "total": item.total,
                "challenge_credit": item.challenge_credit,
                "memory_gain_credit": item.memory_gain_credit,
            }
            for name, item in results.items()
        },
    }


def verify_fsrs_reference(contract_path: Path, package_root: Path) -> dict[str, Any]:
    payload = load_strict_json(contract_path)
    _validate_contract(payload, contract_path)
    python = _python_reference(payload)
    rust = _rust_reference(package_root, contract_path)
    comparison = _compare_references(python, rust)
    if comparison["state_mismatches"]:
        raise ValueError(f"FSRS state mismatch: {comparison['state_mismatches'][0]}")
    result = {
        "manifest": {
            "trajectory_version": TRAJECTORY_VERSION,
            "py_fsrs_version": python["package_version"],
            "fsrs_rs_crate_version": rust["crate_version"],
            "scheduler_parameters": "official FSRS-6 defaults",
            "desired_retentions": sorted({item["desired_retention"] for item in payload["trajectories"]}),
            "learning_steps_minutes": payload["scheduler"]["learning_steps_minutes"],
            "relearning_steps_minutes": payload["scheduler"]["relearning_steps_minutes"],
            "timezone_assumption": payload["timezone"],
            "start_datetime": payload["start_datetime"],
            "trajectory_digest": canonical_digest(payload),
            "tolerances": {
                "stability": STATE_TOLERANCE,
                "difficulty": STATE_TOLERANCE,
                "retrievability": RETRIEVABILITY_TOLERANCE,
                "counterfactual_good_stability": STATE_TOLERANCE,
                "scheduled_interval_days": INTERVAL_TOLERANCE_DAYS,
            },
        },
        "python_reference": python,
        "rust_reference": rust,
        "comparison": comparison,
        "reward_integration": _reward_integration(),
    }
    result["manifest"]["output_digest"] = canonical_digest(result)
    return result
