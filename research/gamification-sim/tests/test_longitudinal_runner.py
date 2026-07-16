from __future__ import annotations

from pathlib import Path

import pytest

from gamification_sim.longitudinal_config import load_longitudinal_config
from gamification_sim.longitudinal_runner import (
    run_longitudinal,
    validate_longitudinal_result,
    write_longitudinal_reports,
)
from gamification_sim.models import Outcome


ROOT = Path(__file__).parents[1]
CONFIG = load_longitudinal_config(ROOT / "configs/review-longitudinal-v0.1.json")


@pytest.fixture(scope="module")
def development():
    return run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=20260716,
        parameter_set_ids=("R-CURRENT",),
    )


@pytest.fixture(scope="module")
def backlog_90():
    return run_longitudinal(
        CONFIG,
        mode_id="calibration-90",
        master_seed=20260716,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("timely-control", "intentional-backlog", "honest-backlog-return"),
    )


def by_policy(payload):
    return {item["policy_id"]: item for item in payload["policy_results"]}


def test_same_card_lineage_reappears_across_days(development):
    stable = by_policy(development)["stable-default"]
    days_by_lineage = {}
    for event in stable["events"]:
        days_by_lineage.setdefault(event["card_lineage_id"], set()).add(event["day"])
    assert any(len(days) > 1 for days in days_by_lineage.values())
    assert stable["metrics"]["lineages_with_multiple_reviews"] > 0


def test_review_updates_state_derived_next_due(development):
    stable = by_policy(development)["stable-default"]
    assert all(event["next_due_day"] > event["day"] for event in stable["events"])
    assert stable["initial_cohort_digest"] != stable["final_cohort_digest"]


def test_missed_due_cards_become_overdue_and_are_caught_up(backlog_90):
    delayed = by_policy(backlog_90)["intentional-backlog"]
    overdue = [event for event in delayed["events"] if event["due_relation"] == "overdue"]
    assert overdue
    assert all(event["card_lineage_id"].startswith("card-") for event in overdue)
    assert delayed["metrics"]["overdue_review_count"] == len(overdue)
    assert delayed["metrics"]["final_due_backlog"] == 0


def test_higher_retention_changes_workload_on_matched_cohort(development):
    results = by_policy(development)
    high = results["stable-high"]
    low = results["stable-low"]
    assert high["initial_cohort_digest"] == low["initial_cohort_digest"]
    assert high["latent_stream_id"] == low["latent_stream_id"]
    assert high["metrics"]["review_count"] > low["metrics"]["review_count"]


def test_same_seed_reproduces_and_different_seed_changes_trajectory(development):
    repeated = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=20260716,
        parameter_set_ids=("R-CURRENT",),
    )
    changed = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=20260717,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-default",),
    )
    assert development["manifest"]["report_digest"] == repeated["manifest"]["report_digest"]
    assert development["manifest"]["trajectory_digest"] != changed["manifest"]["trajectory_digest"]


def test_policy_iteration_order_does_not_change_child_streams():
    first = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=7,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-high", "stable-low"),
    )
    second = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=7,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-low", "stable-high"),
    )
    assert {
        item["policy_id"]: item["trajectory_digest"] for item in first["policy_results"]
    } == {
        item["policy_id"]: item["trajectory_digest"] for item in second["policy_results"]
    }


def test_no_fsrs_mode_uses_neutral_context_and_persistent_identity(development):
    neutral = by_policy(development)["no-fsrs-neutral"]
    successful = [event for event in neutral["events"] if event["outcome"] != "again"]
    assert neutral["scheduler"] == "neutral-synthetic"
    assert successful
    assert all(event["core_context"] == pytest.approx(0.1) for event in successful)
    assert neutral["metrics"]["lineages_with_multiple_reviews"] > 0


def test_failed_recall_is_again_and_other_buttons_are_successful(development):
    outcomes = {event["outcome"] for item in development["policy_results"] for event in item["events"]}
    assert "again" in outcomes
    assert all(Outcome(value).passed for value in outcomes - {"again"})
    assert Outcome.AGAIN.passed is False


def test_baseline_is_preserved_for_fsrs_no_fsrs_and_backlog(development, backlog_90):
    validate_longitudinal_result(development)
    validate_longitudinal_result(backlog_90)
    all_results = development["policy_results"] + backlog_90["policy_results"]
    assert all(item["metrics"]["honest_baseline_suppression_events"] == 0 for item in all_results)
    assert all(item["metrics"]["baseline_preservation_ratio"] == pytest.approx(1.0) for item in all_results)


def test_engine_has_no_production_collection_dependency():
    sources = "\n".join(
        (ROOT / "src/gamification_sim" / name).read_text(encoding="utf-8")
        for name in ("longitudinal_models.py", "longitudinal_generator.py", "longitudinal_runner.py")
    )
    assert "anki_study_report" not in sources
    assert "revlog" not in sources


def test_longitudinal_report_writer_uses_required_artifact_names(tmp_path, development):
    run_dir = write_longitudinal_reports(development, tmp_path)
    assert {item.name for item in run_dir.iterdir()} == {
        "manifest.json",
        "policy-metrics.csv",
        "fairness.json",
        "abuse.json",
        "cohort-state-summary.json",
        "summary.md",
    }
