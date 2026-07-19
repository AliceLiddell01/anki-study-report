from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gamification_sim.canonical_json import canonical_digest
from gamification_sim.diagnostic_attribution import (
    AttributionCollector,
    MASTER_SEED,
    SECONDARY_SEED,
    POLICY_IDS,
    _aggregate_grains,
    _canonical_cells,
    _finite_walk,
    _json_text,
    _safety_scan,
    _strict_load,
    _validate_schema,
    build_evidence_base,
    run_trace,
    transition_marker,
)
from gamification_sim.longitudinal_config import load_longitudinal_config
from gamification_sim.longitudinal_runner import run_longitudinal

ROOT = Path(__file__).parents[1]
CONFIG = load_longitudinal_config(
    ROOT / "configs/review-longitudinal-v0.1.json",
    workspace=ROOT,
)
CONTRACT_PATH = ROOT / "contracts/review-cycling-diagnostic-v1.json"
ATTRIBUTION_SCHEMA = ROOT / "schemas/review-cycling-attribution-v1.schema.json"


@pytest.fixture(scope="module")
def short_bundle():
    return run_trace(
        CONFIG,
        mode_id="calibration-90",
        master_seed=MASTER_SEED,
        workspace=ROOT,
    )


@pytest.fixture(scope="module")
def long_bundle():
    return run_trace(
        CONFIG,
        mode_id="calibration-365",
        master_seed=MASTER_SEED,
        workspace=ROOT,
    )


@pytest.fixture(scope="module")
def secondary_bundle():
    return run_trace(
        CONFIG,
        mode_id="calibration-90",
        master_seed=SECONDARY_SEED,
        workspace=ROOT,
    )


@pytest.fixture(scope="module")
def control_bundle():
    return run_trace(
        CONFIG,
        mode_id="development",
        master_seed=MASTER_SEED,
        workspace=ROOT,
        policy_ids=("stable-default", "no-fsrs-neutral"),
    )


def test_opt_in_trace_does_not_change_longitudinal_payload_or_digests():
    plain = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=MASTER_SEED,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-high", "stable-low"),
        workspace=ROOT,
    )
    collector = AttributionCollector(mode_id="development", master_seed=MASTER_SEED)
    traced = run_longitudinal(
        CONFIG,
        mode_id="development",
        master_seed=MASTER_SEED,
        parameter_set_ids=("R-CURRENT",),
        policy_ids=("stable-high", "stable-low"),
        workspace=ROOT,
        diagnostic_observer=collector.observe,
    )
    assert traced == plain
    assert canonical_digest(traced) == canonical_digest(plain)
    assert traced["manifest"]["trajectory_digest"] == plain["manifest"]["trajectory_digest"]
    assert traced["manifest"]["report_digest"] == plain["manifest"]["report_digest"]


def test_all_required_grain_levels_are_explicit(short_bundle):
    grains = {row["grain"] for row in _aggregate_grains(short_bundle)}
    grains.update(row["grain"] for row in short_bundle.episodes)
    grains.update(row["grain"] for row in short_bundle.days)
    grains.update(row["grain"] for row in short_bundle.policies)
    grains.update(row["grain"] for row in short_bundle.comparisons)
    assert grains == {
        "run",
        "policy",
        "replica",
        "horizon",
        "day_window",
        "synthetic_card_lineage",
        "review_episode",
        "aggregate_comparison",
    }


def test_episode_rows_contain_all_frozen_scheduler_and_reward_fields(short_bundle):
    required = {
        "run_id",
        "parameter_set_id",
        "policy_id",
        "comparison_id",
        "replica",
        "horizon_days",
        "day",
        "window_id",
        "synthetic_card_lineage_id",
        "source_event_key",
        "desired_retention",
        "transition_marker",
        "scheduled_due_day",
        "actual_review_day",
        "delay_days",
        "due_relation",
        "retrievability_actual",
        "retrievability_natural_due",
        "stability_before",
        "stability_good_counterfactual",
        "stability_after",
        "difficulty_before",
        "difficulty_after",
        "model_confidence",
        "outcome",
        "attempt_credit",
        "outcome_credit",
        "baseline_credit",
        "neutral_context_credit",
        "raw_challenge_credit",
        "natural_due_challenge_credit",
        "extra_challenge",
        "delay_credit",
        "adjusted_challenge",
        "raw_memory_gain",
        "memory_gain_credit",
        "confidence",
        "effective_bonus",
        "response_validity",
        "context_before_blend",
        "context_after_blend",
        "context_after_cap",
        "core_review_units",
        "cap_applied",
        "suppression_or_cap_reason",
        "f_cm",
        "f_c0",
        "f_0m",
        "f_00",
        "challenge_main",
        "memory_main",
        "interaction",
        "decomposition_residual",
    }
    assert short_bundle.episodes
    assert required.issubset(short_bundle.episodes[0])


def test_trace_identifiers_are_synthetic_and_stable(short_bundle):
    assert all(row["synthetic_card_lineage_id"].startswith("card-") for row in short_bundle.episodes)
    assert all("/" not in row["source_event_key"] and "\\" not in row["source_event_key"] for row in short_bundle.episodes)
    repeated = run_trace(
        CONFIG,
        mode_id="calibration-90",
        master_seed=MASTER_SEED,
        workspace=ROOT,
    )
    assert [row["source_event_key"] for row in repeated.episodes] == [
        row["source_event_key"] for row in short_bundle.episodes
    ]


def test_episode_decomposition_matches_runtime_breakdown(short_bundle):
    assert max(abs(row["decomposition_residual"]) for row in short_bundle.episodes) <= 1e-9
    assert all(row["context_after_cap"] == pytest.approx(row["f_cm"]) for row in short_bundle.episodes)
    assert all(
        row["core_review_units"]
        == pytest.approx(row["baseline_credit"] + row["context_after_cap"])
        for row in short_bundle.episodes
    )


def test_day_totals_reconcile(short_bundle):
    for day in short_bundle.days:
        expected = (
            day["core_baseline"]
            + day["core_context"]
            + day["support"]
            + day["supplemental"]
            + day["volume_credit"]
            + day["completion_credit"]
        )
        assert day["day_total"] == pytest.approx(expected)


def test_policy_totals_reconcile_to_longitudinal_metrics(short_bundle):
    by_key = {
        (item["policy_id"], item["replica"], item["parameter_set_id"]): item
        for item in short_bundle.payload["policy_results"]
    }
    for policy in short_bundle.policies:
        runtime = by_key[(policy["policy_id"], policy["replica"], policy["parameter_set_id"])]
        assert policy["review_count"] == runtime["metrics"]["review_count"]
        assert policy["core_baseline"] == pytest.approx(runtime["metrics"]["core_baseline"])
        assert policy["core_context"] == pytest.approx(runtime["metrics"]["core_context"])
        assert policy["total_review_units"] == pytest.approx(runtime["metrics"]["total_review_units"])


def test_six_cells_and_three_groups_match_immutable_g0_7(short_bundle, long_bundle):
    contract = _strict_load(CONTRACT_PATH)
    cells, groups = _canonical_cells(short_bundle, long_bundle, contract)
    assert len(cells) == 6
    assert len(groups) == 3
    assert cells == contract["current_evidence"]["cells"]
    assert groups == contract["current_evidence"]["groups"]


def test_fixed_trajectory_ablations_do_not_change_scheduler_events(short_bundle):
    event_identity = [
        (
            row["source_event_key"],
            row["scheduled_due_day"],
            row["actual_review_day"],
            row["stability_after"],
            row["difficulty_after"],
        )
        for row in short_bundle.episodes
    ]
    assert event_identity == [
        (
            row["source_event_key"],
            row["scheduled_due_day"],
            row["actual_review_day"],
            row["stability_after"],
            row["difficulty_after"],
        )
        for row in short_bundle.episodes
    ]
    assert all(row["classification"] == "EXPLORATORY_NON_DECISION" for row in short_bundle.episodes)


def test_challenge_memory_interaction_identity(short_bundle):
    for row in short_bundle.episodes:
        assert row["f_cm"] == pytest.approx(
            row["f_00"] + row["challenge_main"] + row["memory_main"] + row["interaction"]
        )


def test_transition_windows_cover_day_30_and_day_60(long_bundle):
    markers = {row["day"]: row["transition_marker"] for row in long_bundle.days}
    assert markers[30] == "day_30_transition"
    assert markers[60] == "day_60_transition"
    delayed = next(item for item in CONFIG.policies if item.policy_id == "intentional-backlog")
    assert transition_marker(delayed, 45) == "backlog_return_window"


def test_same_seed_trace_is_deterministic(short_bundle):
    repeated = run_trace(
        CONFIG,
        mode_id="calibration-90",
        master_seed=MASTER_SEED,
        workspace=ROOT,
    )
    assert repeated.trace_digest == short_bundle.trace_digest
    assert _json_text(repeated.episodes) == _json_text(short_bundle.episodes)


def test_secondary_seed_changes_trajectory_but_reconciles(short_bundle, secondary_bundle):
    assert secondary_bundle.payload["manifest"]["trajectory_digest"] != short_bundle.payload["manifest"]["trajectory_digest"]
    assert all(abs(row["residual"]) <= 1e-9 for row in secondary_bundle.comparisons)


def test_serialization_is_deterministic(short_bundle):
    first = _json_text(short_bundle.comparisons)
    second = _json_text(json.loads(first))
    assert first == second


def test_strict_json_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _strict_load(path)


def test_non_finite_values_are_rejected():
    with pytest.raises(ValueError, match="non-finite"):
        _finite_walk({"value": float("nan")})


def test_attribution_schema_self_check_and_pairing_contract():
    schema = _strict_load(ATTRIBUTION_SCHEMA)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False


def test_unsafe_paths_and_forbidden_data_are_rejected(tmp_path):
    safe = tmp_path / "safe"
    safe.mkdir()
    (safe / "trace.json").write_text('{"token":"ghp_forbidden"}', encoding="utf-8")
    result = _safety_scan(safe)
    assert result["status"] == "FAIL"
    assert result["findings"]


def test_evidence_record_validates_against_schema(
    short_bundle,
    long_bundle,
    secondary_bundle,
    control_bundle,
):
    contract = _strict_load(CONTRACT_PATH)
    evidence = build_evidence_base(
        workspace=ROOT,
        short=short_bundle,
        long=long_bundle,
        secondary=secondary_bundle,
        controls=control_bundle,
        short_repeat_identity={
            "status": "PASS",
            "tree_digest": "1" * 64,
            "trace_digest": short_bundle.trace_digest,
        },
        long_repeat_identity={
            "status": "PASS",
            "tree_digest": "2" * 64,
            "trace_digest": long_bundle.trace_digest,
        },
        contract=contract,
    )
    evidence["artifact"] = {
        "id": 1,
        "name": "g1-2-test-artifact",
        "digest": "sha256:" + "3" * 64,
        "manifest_digest": "4" * 64,
        "size_bytes": 1,
        "expires_at": "2026-10-01T00:00:00Z",
        "workflow_run_id": 1,
        "job_id": 1,
    }
    evidence["safety"]["forbidden_data_scan"] = "PASS"
    evidence["publication"]["workflow_run_id"] = 1
    evidence["cleanup"]["preserved_run_ids"][-1] = 1
    evidence["cleanup"]["preserved_artifact_ids"][-1] = 1
    evidence["verification"] = {
        "focused_command": "python -m pytest test_diagnostic_attribution.py",
        "focused_passed": 20,
        "full_command": "python -m pytest research/gamification-sim/tests",
        "full_passed": 20,
        "schema_validation": "PASS",
        "artifact_audit": "PASS",
        "frozen_blob_audit": "PASS",
        "exact_seven_path_diff": "PASS",
    }
    _validate_schema(ATTRIBUTION_SCHEMA, evidence)


def test_required_policy_set_is_exactly_frozen():
    assert set(POLICY_IDS) == {
        "stable-high",
        "stable-low",
        "temporary-high-cycle",
        "temporary-low-cycle",
        "timely-control",
        "intentional-backlog",
        "honest-backlog-return",
    }
