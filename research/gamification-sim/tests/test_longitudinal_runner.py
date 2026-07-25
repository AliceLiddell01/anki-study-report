from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path

import pytest

from gamification_sim.longitudinal_config import load_longitudinal_config
import gamification_sim.longitudinal_runner as runner_module
from gamification_sim.longitudinal_models import (
    LongitudinalCardState,
    LongitudinalMode,
)
from gamification_sim.longitudinal_runner import (
    run_longitudinal,
    run_policy,
    validate_longitudinal_result,
    write_longitudinal_reports,
)
from gamification_sim.models import (
    ConfidenceLevel,
    MemoryContext,
    Outcome,
)
from gamification_sim.parameters import CURRENT_PARAMETERS


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


def test_default_r_current_digests_match_pre_wiring_checkpoint(
    development,
):
    manifest = development["manifest"]

    assert manifest["trajectory_digest"] == (
        "14b72f42ce03d7e9a44748c43e273585"
        "4004811b642e5ab9a1773ab5b25d5301"
    )
    assert manifest["final_cohort_digest"] == (
        "34395f2a7eb0683aa30e2a044d1b3ec1"
        "c4f4afee6e86bbc0ad61ec7eec0b29c1"
    )
    assert manifest["report_digest"] == (
        "62788baea6b294663e27713a81645a89f"
        "f3f4dd1f4e9be3842e7df31130ffc0e"
    )
    assert "candidate_parameterization" not in manifest
    assert all(
        "candidate_parameterization" not in result
        for result in development["policy_results"]
    )


def candidate_capability_fixture(monkeypatch):
    mode = LongitudinalMode(
        mode_id="candidate-capability",
        horizon_days=62,
        cohort_size=1,
        replicas=1,
    )
    config = replace(CONFIG, modes=(mode,))

    source_policy = next(
        item
        for item in CONFIG.policies
        if item.policy_id == "temporary-high-cycle"
    )
    policy = replace(
        source_policy,
        scheduler="neutral-synthetic",
        review_limit=1,
    )

    initial_card = LongitudinalCardState(
        card_lineage_id="candidate-card",
        created_day=0,
        state_kind="candidate-fixture",
        last_review_day=None,
        next_due_day=0,
        review_count=0,
        lapse_count=0,
        stability=1.0,
        difficulty=5.0,
        retrievability_at_last_update=1.0,
        scheduled_interval=1,
        desired_retention_policy=policy.policy_id,
        preset_id="candidate-fixture",
        active=True,
        fsrs_card=None,
    )

    def fake_initial_cohort(**_kwargs):
        return (initial_card,)

    def fake_neutral_transition(
        card,
        *,
        policy,
        day,
        master_seed,
        replica,
    ):
        del master_seed, replica
        updated = replace(
            card,
            state_kind="candidate-fixture",
            last_review_day=day,
            next_due_day=day + 1,
            review_count=card.review_count + 1,
            stability=card.stability + 0.5,
            retrievability_at_last_update=0.95,
            scheduled_interval=1,
            desired_retention_policy=policy.policy_id,
        )
        memory = MemoryContext(
            retrievability_actual=0.95,
            retrievability_natural_due=0.95,
            stability_before=1.0,
            stability_good_counterfactual=math.exp(2.0),
            confidence=ConfidenceLevel.HIGH,
        )
        return updated, Outcome.GOOD, memory, 0.95

    monkeypatch.setattr(
        runner_module,
        "initial_cohort",
        fake_initial_cohort,
    )
    monkeypatch.setattr(
        runner_module,
        "_neutral_transition",
        fake_neutral_transition,
    )

    return config, policy


def scheduler_projection(events):
    reward_fields = {
        "core_baseline",
        "core_context",
        "total_review_units",
    }
    return [
        {
            key: value
            for key, value in event.items()
            if key not in reward_fields
        }
        for event in events
    ]


def test_candidate_run_changes_reward_only_and_propagates_identity(
    monkeypatch,
):
    config, policy = candidate_capability_fixture(monkeypatch)

    reference = run_policy(
        config,
        policy=policy,
        parameter_set_id="R-CURRENT",
        master_seed=20260716,
        mode_id="candidate-capability",
        replica=0,
    )
    candidate = run_policy(
        config,
        policy=policy,
        parameter_set_id="R-CURRENT",
        master_seed=20260716,
        mode_id="candidate-capability",
        replica=0,
        candidate_parameterization_id="P-STEP-ZERO",
    )
    repeated = run_policy(
        config,
        policy=policy,
        parameter_set_id="R-CURRENT",
        master_seed=20260716,
        mode_id="candidate-capability",
        replica=0,
        candidate_parameterization_id="P-STEP-ZERO",
    )

    assert candidate == repeated
    assert "candidate_parameterization" not in reference
    assert candidate["parameter_set_id"] == "R-CURRENT"

    trace = candidate["candidate_parameterization"]
    assert trace["protocol_id"] == (
        "review-xp-candidate-protocol"
    )
    assert trace["protocol_version"] == 1
    assert trace["candidate_parameterization_id"] == (
        "P-STEP-ZERO"
    )
    assert trace["family_id"] == (
        "F-POST-TRANSITION-MG-STEP"
    )
    assert trace["mechanism_class"] == (
        "POST_TRANSITION_MEMORY_GAIN_STEP_SCALING"
    )
    assert len(trace["candidate_identity_digest"]) == 64

    assert reference["metrics"]["review_count"] == 62
    assert candidate["metrics"]["review_count"] == 62
    assert (
        reference["metrics"]["core_baseline"]
        == candidate["metrics"]["core_baseline"]
    )
    assert (
        reference["final_cohort_digest"]
        == candidate["final_cohort_digest"]
    )
    assert (
        scheduler_projection(reference["events"])
        == scheduler_projection(candidate["events"])
    )

    reference_by_day = {
        item["day"]: item
        for item in reference["events"]
    }
    candidate_by_day = {
        item["day"]: item
        for item in candidate["events"]
    }

    for day in range(60):
        assert candidate_by_day[day] == reference_by_day[day]

    assert reference_by_day[60]["core_context"] == pytest.approx(
        0.12
    )
    assert candidate_by_day[60]["core_context"] == pytest.approx(
        0.0
    )
    assert reference_by_day[61]["core_context"] == pytest.approx(
        0.12
    )
    assert candidate_by_day[61]["core_context"] == pytest.approx(
        0.0
    )
    assert (
        reference["trajectory_digest"]
        != candidate["trajectory_digest"]
    )


def test_candidate_is_identity_for_policy_without_transition(
    monkeypatch,
):
    config, cycling_policy = candidate_capability_fixture(
        monkeypatch
    )
    stable_policy = replace(
        cycling_policy,
        policy_id="stable-candidate-fixture",
        retention_timeline=(
            cycling_policy.retention_timeline[0],
        ),
    )

    reference = run_policy(
        config,
        policy=stable_policy,
        parameter_set_id="R-CURRENT",
        master_seed=20260716,
        mode_id="candidate-capability",
        replica=0,
    )
    candidate = run_policy(
        config,
        policy=stable_policy,
        parameter_set_id="R-CURRENT",
        master_seed=20260716,
        mode_id="candidate-capability",
        replica=0,
        candidate_parameterization_id="P-STEP-ZERO",
    )

    assert candidate["events"] == reference["events"]
    assert candidate["metrics"] == reference["metrics"]
    assert (
        candidate["trajectory_digest"]
        == reference["trajectory_digest"]
    )
    assert (
        candidate["final_cohort_digest"]
        == reference["final_cohort_digest"]
    )
    assert "candidate_parameterization" in candidate


def test_unknown_candidate_fails_before_cohort_generation(
    monkeypatch,
):
    called = False

    def forbidden_initial_cohort(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("initial cohort must not be generated")

    monkeypatch.setattr(
        runner_module,
        "initial_cohort",
        forbidden_initial_cohort,
    )

    policy = next(
        item
        for item in CONFIG.policies
        if item.policy_id == "temporary-high-cycle"
    )

    with pytest.raises(
        ValueError,
        match="unknown frozen Review parameterization",
    ):
        run_policy(
            CONFIG,
            policy=policy,
            parameter_set_id="R-CURRENT",
            master_seed=20260716,
            mode_id="development",
            replica=0,
            candidate_parameterization_id="P-UNREGISTERED",
        )

    assert called is False


def test_candidate_rejects_non_reference_parameter_set_before_run(
    monkeypatch,
):
    called = False

    def forbidden_initial_cohort(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("initial cohort must not be generated")

    monkeypatch.setattr(
        runner_module,
        "initial_cohort",
        forbidden_initial_cohort,
    )

    policy = next(
        item
        for item in CONFIG.policies
        if item.policy_id == "temporary-high-cycle"
    )

    with pytest.raises(
        ValueError,
        match="require parameter set R-CURRENT",
    ):
        run_policy(
            CONFIG,
            policy=policy,
            parameter_set_id="R-NO-GAIN",
            master_seed=20260716,
            mode_id="development",
            replica=0,
            candidate_parameterization_id="P-STEP-ZERO",
        )

    assert called is False


def test_candidate_rejects_parameter_override_before_run(
    monkeypatch,
):
    called = False

    def forbidden_initial_cohort(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("initial cohort must not be generated")

    monkeypatch.setattr(
        runner_module,
        "initial_cohort",
        forbidden_initial_cohort,
    )

    policy = next(
        item
        for item in CONFIG.policies
        if item.policy_id == "temporary-high-cycle"
    )

    with pytest.raises(
        ValueError,
        match="prohibit parameter overrides",
    ):
        run_policy(
            CONFIG,
            policy=policy,
            parameter_set_id="R-CURRENT",
            master_seed=20260716,
            mode_id="development",
            replica=0,
            params_override=CURRENT_PARAMETERS,
            candidate_parameterization_id="P-STEP-ZERO",
        )

    assert called is False


def test_candidate_policy_iteration_order_is_independent():
    first = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=7,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-high", "stable-low"),
        candidate_parameterization_id="P-STEP-ZERO",
    )
    second = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=7,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-low", "stable-high"),
        candidate_parameterization_id="P-STEP-ZERO",
    )

    assert first == second
    assert first["manifest"]["candidate_parameterization"][
        "candidate_parameterization_id"
    ] == "P-STEP-ZERO"


def test_candidate_longitudinal_run_rejects_mixed_parameter_sets(
    monkeypatch,
):
    called = False

    def forbidden_run_policy(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("policy execution must not begin")

    monkeypatch.setattr(
        runner_module,
        "run_policy",
        forbidden_run_policy,
    )

    with pytest.raises(
        ValueError,
        match="require exactly R-CURRENT",
    ):
        run_longitudinal(
            CONFIG,
            mode_id="development",
            master_seed=20260716,
            parameter_set_ids=("R-CURRENT", "R-NO-GAIN"),
            candidate_parameterization_id="P-STEP-ZERO",
        )

    assert called is False
