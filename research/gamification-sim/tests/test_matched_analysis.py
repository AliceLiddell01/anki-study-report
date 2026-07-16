from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gamification_sim.longitudinal_config import load_longitudinal_config
from gamification_sim.longitudinal_runner import run_longitudinal
from gamification_sim.matched_analysis import (
    POLICY_PAIRS,
    compare_abuse_horizons,
    validate_policy_pairs,
)


ROOT = Path(__file__).parents[1]
CONFIG = load_longitudinal_config(ROOT / "configs/review-longitudinal-v0.1.json")


@pytest.fixture(scope="module")
def calibration_90():
    return run_longitudinal(
        CONFIG,
        mode_id="calibration-90",
        master_seed=20260716,
        parameter_set_ids=("R-CURRENT",),
    )


@pytest.fixture(scope="module")
def calibration_365():
    return run_longitudinal(
        CONFIG,
        mode_id="calibration-365",
        master_seed=20260716,
        parameter_set_ids=("R-CURRENT",),
    )


def test_each_policy_pair_changes_only_the_declared_factor():
    validate_policy_pairs(CONFIG.policies)
    assert {pair.changed_factor for pair in POLICY_PAIRS} == {
        "retention_timeline",
        "delay_window",
    }


def test_unmatched_policy_pair_is_rejected():
    policies = list(CONFIG.policies)
    index = next(i for i, item in enumerate(policies) if item.policy_id == "stable-high")
    policies[index] = replace(policies[index], review_limit=policies[index].review_limit - 1)
    with pytest.raises(ValueError, match="unmatched policy pair"):
        validate_policy_pairs(tuple(policies))


def test_longitudinal_pairs_share_initial_cohort_and_latent_stream(calibration_90):
    comparisons = calibration_90["fairness"]["comparisons"] + calibration_90["abuse"]["comparisons"]
    longitudinal = [item for item in comparisons if item.get("replica") is not None]
    assert longitudinal
    by_key = {
        (item["parameter_set_id"], item["replica"], item["policy_id"]): item
        for item in calibration_90["policy_results"]
    }
    for comparison in longitudinal:
        left = by_key[(comparison["parameter_set_id"], comparison["replica"], comparison["left_policy_id"])]
        right = by_key[(comparison["parameter_set_id"], comparison["replica"], comparison["right_policy_id"])]
        assert left["initial_cohort_digest"] == right["initial_cohort_digest"]
        assert left["latent_stream_id"] == right["latent_stream_id"]


def test_retention_comparison_reports_workload_and_normalized_reward(calibration_90):
    comparisons = [
        item for item in calibration_90["fairness"]["comparisons"]
        if item["comparison"] == "retention-high-vs-low"
    ]
    assert len(comparisons) == 2
    assert all(item["review_count_difference"] != 0 for item in comparisons)
    assert all(item["left_ru_per_review"] > 0 and item["right_ru_per_review"] > 0 for item in comparisons)
    assert all(item["left_baseline_preservation"] == pytest.approx(1.0) for item in comparisons)


def test_abuse_advantage_subtracts_legitimate_additional_baseline(calibration_90):
    comparisons = [
        item for item in calibration_90["abuse"]["comparisons"]
        if item.get("replica") is not None
    ]
    assert comparisons
    for item in comparisons:
        unexplained_units = item["total_delta"] - item["legitimate_additional_baseline"]
        control = next(
            result for result in calibration_90["policy_results"]
            if result["parameter_set_id"] == item["parameter_set_id"]
            and result["replica"] == item["replica"]
            and result["policy_id"] == item["right_policy_id"]
        )
        assert item["unexplained_advantage"] == pytest.approx(
            unexplained_units / control["metrics"]["total_review_units"]
        )


def test_backlog_horizon_includes_catchup_and_stabilization(calibration_90):
    delayed = [
        item for item in calibration_90["policy_results"]
        if item["policy_id"] == "intentional-backlog"
    ]
    assert all(any(event["day"] >= 45 and event["due_relation"] == "overdue" for event in item["events"]) for item in delayed)
    assert all(item["metrics"]["final_due_backlog"] == 0 for item in delayed)
    comparisons = [
        item for item in calibration_90["abuse"]["comparisons"]
        if item["comparison"] == "intentional-backlog"
    ]
    assert all(item["status"] == "PASS" for item in comparisons)


def test_retention_cycling_gate_is_measured_not_placeholder(calibration_90):
    cycling = [
        item for item in calibration_90["abuse"]["comparisons"]
        if item["comparison"] in {"retention-high-cycle", "retention-low-cycle"}
    ]
    assert len(cycling) == 4
    assert all(isinstance(item["unexplained_advantage"], float) for item in cycling)
    assert all(item["unexplained_advantage"] <= 0.03 + 1e-9 for item in cycling)
    assert all(item["status"] == "PASS" for item in cycling)


def test_long_horizon_comparison_exposes_systematic_cycling_growth(calibration_90, calibration_365):
    comparison = compare_abuse_horizons(calibration_90, calibration_365)
    assert comparison["status"] == "FAIL"
    assert all(item["long_horizon_gate_pass"] for item in comparison["cells"])
    failed = [item for item in comparison["groups"] if item["status"] == "FAIL"]
    assert {item["comparison"] for item in failed} == {
        "retention-high-cycle",
        "retention-low-cycle",
    }
    assert all(item["systematic_growth"] for item in failed)


def test_horizon_comparison_rejects_unmatched_seed(calibration_90, calibration_365):
    changed = {
        **calibration_365,
        "manifest": {**calibration_365["manifest"], "master_seed": 20260717},
    }
    with pytest.raises(ValueError, match="unmatched master_seed"):
        compare_abuse_horizons(calibration_90, changed)


def test_missing_policy_evidence_remains_explicit():
    partial = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=1,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-default",),
    )
    unsupported = partial["fairness"]["unsupported"]
    assert unsupported
    assert all(item["status"] == "UNSUPPORTED" and item["reason"] for item in unsupported)


def test_deterministic_matrix_contains_all_required_abuse_controls(calibration_90):
    ids = {item["comparison"] for item in calibration_90["abuse"]["comparisons"]}
    assert {
        "duplicate-replay",
        "session-splitting",
        "relearning-loop",
        "preview-farm",
        "forced-due",
        "micro-scope-completion",
    } <= ids
