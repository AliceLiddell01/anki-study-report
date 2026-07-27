from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gamification_sim.canonical_json import canonical_digest
from gamification_sim.learn_bounded_screening import (
    EXPECTED_BLOBS,
    EXPECTED_GATES,
    EXPECTED_METRICS,
    EXPECTED_UNITS,
    FROZEN_LIFECYCLE_RESULT_DIGESTS,
    LearnScreeningUnit,
    _accounting_trace,
    _candidate_definition,
    _load_fixture_registry,
    aggregate_learn_screening,
    build_learn_screening_manifest,
    load_and_validate_learn_screening_protocol,
    run_learn_screening_unit,
    run_learn_xp_screening,
    validate_learn_screening_manifest,
    validate_learn_xp_screening_evidence,
    write_learn_xp_screening_bundle,
)
from gamification_sim.learn_candidate_protocol import generate_dry_units
from gamification_sim.learn_lifecycle import evaluate_lifecycle
from gamification_sim.learn_reward_allocation import (
    evaluate_allocation,
    evaluate_delay_policy,
    evaluate_subject_strategy,
)
from gamification_sim.strict_json import load_strict_json
from gamification_sim.workspace import ResearchWorkspace


ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "933325f8d2647d52cbc0d6859ff44ded0b6686c4"
IMPL_SHA = "a" * 40


@pytest.fixture
def workspace() -> ResearchWorkspace:
    return ResearchWorkspace(ROOT)


@pytest.fixture
def protocol() -> dict:
    return load_strict_json(ROOT / "contracts/learn-xp-candidate-protocol-v1.json")


@pytest.fixture
def stub_git(monkeypatch, protocol):
    source = protocol["source_contracts"]
    by_path = {
        "contracts/learn-xp-candidate-protocol-v1.json": EXPECTED_BLOBS["protocol"],
        "schemas/learn-xp-candidate-protocol-v1.schema.json": EXPECTED_BLOBS["protocol_schema"],
        "src/gamification_sim/learn_candidate_protocol.py": EXPECTED_BLOBS["dry_generator"],
        "fixtures/learn-xp-lifecycle-v1/manifest.json": EXPECTED_BLOBS["fixture_manifest"],
        "contracts/learn-xp-problem-contract-v1.json": source["g2_1"]["contract_blob_sha"],
        "schemas/learn-xp-problem-contract-v1.schema.json": source["g2_1"]["schema_blob_sha"],
        "contracts/learn-xp-lifecycle-model-v1.json": source["g2_2"]["model_blob_sha"],
        "schemas/learn-xp-lifecycle-model-v1.schema.json": source["g2_2"]["model_schema_blob_sha"],
        "schemas/learn-xp-lifecycle-fixture-v1.schema.json": source["g2_2"]["fixture_schema_blob_sha"],
    }
    monkeypatch.setattr(
        "gamification_sim.learn_bounded_screening._git_blob",
        lambda workspace, path: by_path[path.as_posix()],
    )
    monkeypatch.setattr(
        "gamification_sim.learn_bounded_screening._git_repository_blob",
        lambda workspace, path: EXPECTED_BLOBS["human_protocol"],
    )
    monkeypatch.setattr(
        "gamification_sim.learn_bounded_screening._validate_git_identity",
        lambda workspace, implementation_sha, base_sha: {
            "repository": "AliceLiddell01/anki-study-report",
            "target_branch": "gamification",
            "execution_branch": "g2-4-learn-xp-bounded-screening",
            "base_sha": base_sha,
            "implementation_sha": implementation_sha,
            "protocol_publication_sha": "41313c9369c76d331d489a9aa4b44da2497b3132",
            "publication_ancestry": "PASS",
        },
    )
    monkeypatch.setattr(
        "gamification_sim.learn_bounded_screening._git_output",
        lambda workspace, *args: "2026-07-27T12:00:00+00:00",
    )


def test_protocol_and_exact_manifest(workspace, protocol, stub_git):
    loaded, identities = load_and_validate_learn_screening_protocol(workspace)
    assert loaded == protocol
    assert identities["human_protocol_blob"] == EXPECTED_BLOBS["human_protocol"]
    assert identities["protocol_blob"] == EXPECTED_BLOBS["protocol"]
    manifest = build_learn_screening_manifest(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
    )
    validate_learn_screening_manifest(manifest, protocol=protocol)
    assert manifest["expected_units"] == EXPECTED_UNITS
    assert manifest["actual_units"] == EXPECTED_UNITS
    assert manifest["actual_unique_units"] == EXPECTED_UNITS
    assert len({item["unit_id"] for item in manifest["units"]}) == EXPECTED_UNITS
    assert manifest["units"] == [dict(item) for item in generate_dry_units(protocol)]
    assert manifest["missing_units"] == manifest["extra_units"] == manifest["duplicate_units"] == 0


def test_frozen_lifecycle_digest_registry_is_exact(workspace):
    fixtures = _load_fixture_registry(workspace)
    observed = {}
    for fixture in fixtures.values():
        for case in fixture["cases"]:
            observed[f"{fixture['fixture_id']}::{case['case_id']}"] = evaluate_lifecycle(case["events"]).canonical_digest
    assert observed == FROZEN_LIFECYCLE_RESULT_DIGESTS
    assert len(observed) == 31


def test_delay_boundaries_are_inclusive_minimum_exclusive_expiry(protocol):
    delay = {item["delay_policy_id"]: item for item in protocol["delay_policies"]}
    unit = LearnScreeningUnit.from_mapping(
        next(
            item for item in generate_dry_units(protocol)
            if item["candidate_or_reference_id"] == "C-CONFIRMATION-ONLY-D1-CARD"
            and item["scenario_id"] == "SCN-ACCOUNT-CONFIRM-SETTLEMENT"
        )
    )
    candidate = _candidate_definition(protocol, unit)
    events = list(_accounting_trace(unit, candidate["delay_policy"]))
    lifecycle = evaluate_lifecycle(events)
    assert evaluate_delay_policy(events, lifecycle, delay["D1"]).confirmation_eligible

    events[2]["monotonic_time_index"] -= 1
    lifecycle = evaluate_lifecycle(events)
    result = evaluate_delay_policy(events, lifecycle, delay["D1"])
    assert not result.confirmation_eligible
    assert "MINIMUM_ELAPSED_NOT_REACHED" in result.failure_reasons

    events = list(_accounting_trace(unit, candidate["delay_policy"]))
    events[2]["anki_day_index"] = 0
    lifecycle = evaluate_lifecycle(events)
    result = evaluate_delay_policy(events, lifecycle, delay["D1"])
    assert not result.confirmation_eligible
    assert "MINIMUM_ANKI_DAY_DELTA_NOT_REACHED" in result.failure_reasons

    events = list(_accounting_trace(unit, candidate["delay_policy"]))
    events[2]["monotonic_time_index"] = 1 + delay["D1"]["expiry_elapsed"]
    lifecycle = evaluate_lifecycle(events)
    result = evaluate_delay_policy(events, lifecycle, delay["D1"])
    assert not result.confirmation_eligible
    assert "ELAPSED_EXPIRY_REACHED" in result.failure_reasons

    events = list(_accounting_trace(unit, candidate["delay_policy"]))
    events[2]["anki_day_index"] = delay["D1"]["expiry_anki_day_delta"]
    lifecycle = evaluate_lifecycle(events)
    result = evaluate_delay_policy(events, lifecycle, delay["D1"])
    assert not result.confirmation_eligible
    assert "ANKI_DAY_EXPIRY_REACHED" in result.failure_reasons


@pytest.mark.parametrize(
    "policy_id,min_elapsed,min_day,expiry_elapsed,expiry_day",
    [("D1", 1440, 1, 10080, 7), ("D2", 4320, 3, 20160, 14)],
)
def test_delay_exact_numeric_boundaries(protocol, policy_id, min_elapsed, min_day, expiry_elapsed, expiry_day):
    policy = next(item for item in protocol["delay_policies"] if item["delay_policy_id"] == policy_id)
    assert policy["minimum_elapsed"] == min_elapsed
    assert policy["minimum_anki_day_delta"] == min_day
    assert policy["expiry_elapsed"] == expiry_elapsed
    assert policy["expiry_anki_day_delta"] == expiry_day


def test_subject_strategies_are_namespaced_and_fail_closed():
    events = [
        {
            "event_id": "E1", "sequence_index": 1, "event_kind": "VALID_INITIAL_ATTEMPT",
            "subject_type": "CARD", "subject_id": "card-collision-a", "episode_id": "ep",
        },
        {
            "event_id": "E2", "sequence_index": 2, "event_kind": "VALID_INITIAL_ATTEMPT",
            "subject_type": "CARD", "subject_id": "card-collision-b", "episode_id": "ep",
        },
    ]
    card = evaluate_subject_strategy(events, "S-CARD")
    group = evaluate_subject_strategy(events, "S-NOTE-SIBLING")
    assert card.derived_key is None
    assert card.continuity == "FRAGMENTED_FAIL_CLOSED"
    assert card.collision_fragmentation_count == 1
    assert group.derived_key == "NOTE-SIBLING:note-account-collision"
    assert group.continuity == "STABLE"
    assert not group.private_content_read


def test_allocation_confirmation_only_and_split(protocol):
    fixtures = _load_fixture_registry(ResearchWorkspace(ROOT))
    units = generate_dry_units(protocol)
    confirm_only = LearnScreeningUnit.from_mapping(next(
        item for item in units
        if item["candidate_or_reference_id"] == "C-CONFIRMATION-ONLY-D1-CARD"
        and item["scenario_id"] == "SCN-ACCOUNT-CONFIRM-SETTLEMENT"
    ))
    split = LearnScreeningUnit.from_mapping(next(
        item for item in units
        if item["candidate_or_reference_id"] == "C-PENDING-SPLIT-D1-CARD"
        and item["scenario_id"] == "SCN-ACCOUNT-CONFIRM-SETTLEMENT"
    ))
    first = run_learn_screening_unit(confirm_only, protocol=protocol, fixtures=fixtures)["case_evidence"][0]["allocation"]
    second = run_learn_screening_unit(split, protocol=protocol, fixtures=fixtures)["case_evidence"][0]["allocation"]
    assert first["provisional_created_lru"] == 0.0
    assert first["confirmed_lru"] == 1.0
    assert first["settled_total_lru"] == 1.0
    assert second["provisional_created_lru"] == 0.25
    assert second["confirmed_lru"] == 0.75
    assert second["settled_total_lru"] == 1.0
    assert second["current_total_lru"] != 1.25


def test_terminal_paths_void_split_allocation(protocol):
    fixtures = _load_fixture_registry(ResearchWorkspace(ROOT))
    for scenario in (
        "SCN-ACCOUNT-EXPIRE-VOID",
        "SCN-ACCOUNT-CANCEL-VOID",
        "SCN-ACCOUNT-INVALIDATE-VOID",
    ):
        unit = LearnScreeningUnit.from_mapping(next(
            item for item in generate_dry_units(protocol)
            if item["candidate_or_reference_id"] == "C-PENDING-SPLIT-D1-CARD"
            and item["scenario_id"] == scenario
        ))
        allocation = run_learn_screening_unit(unit, protocol=protocol, fixtures=fixtures)["case_evidence"][0]["allocation"]
        assert allocation["pending_lru"] == 0.0
        assert allocation["confirmed_lru"] == 0.0
        assert allocation["settled_total_lru"] == 0.0
        assert allocation["current_total_lru"] == 0.0
        assert not allocation["fresh_eligibility"]


def test_pending_is_idempotent(protocol):
    fixture = load_strict_json(ROOT / "fixtures/learn-xp-lifecycle-v1/ordinary/fix-ord-pending-idempotent.json")
    lifecycle = evaluate_lifecycle(fixture["cases"][0]["events"])
    candidate = next(item for item in protocol["candidate_registry"] if item["candidate_id"] == "C-PENDING-SPLIT-D1-CARD")
    param = next(item for item in protocol["parameterizations"] if item["parameterization_id"] == candidate["parameterization_id"])
    delay = next(item for item in protocol["delay_policies"] if item["delay_policy_id"] == "D1")
    allocation = evaluate_allocation(
        candidate_or_reference_id=candidate["candidate_id"], family_id=candidate["family_id"],
        parameterization_id=candidate["parameterization_id"], subject_strategy_id=candidate["subject_strategy_id"],
        delay_policy_id="D1", pending_share_lru=param["pending_share_lru"],
        confirmation_settlement_lru=param["confirmation_settlement_lru"], events=fixture["cases"][0]["events"],
        lifecycle=lifecycle, delay_policy=delay,
    )
    assert allocation.pending_creation_count == 1
    assert allocation.duplicate_pending_count == 1
    assert allocation.pending_lru == 0.25


def test_reference_allocates_zero_on_all_accounting_paths(protocol):
    fixtures = _load_fixture_registry(ResearchWorkspace(ROOT))
    definitions = [
        item for item in generate_dry_units(protocol)
        if item["candidate_or_reference_id"] == "R-NO-LEARN-XP-CARD"
        and item["scenario_id"] in {
            "SCN-ACCOUNT-PENDING-ALLOCATION", "SCN-ACCOUNT-CONFIRM-SETTLEMENT",
            "SCN-ACCOUNT-EXPIRE-VOID", "SCN-ACCOUNT-CANCEL-VOID",
            "SCN-ACCOUNT-INVALIDATE-VOID", "SCN-ACCOUNT-REFERENCE-ZERO",
        }
    ]
    for definition in definitions:
        result = run_learn_screening_unit(LearnScreeningUnit.from_mapping(definition), protocol=protocol, fixtures=fixtures)
        for case in result["case_evidence"]:
            allocation = case["allocation"]
            assert allocation["provisional_created_lru"] == 0.0
            assert allocation["pending_lru"] == 0.0
            assert allocation["confirmed_lru"] == 0.0
            assert allocation["current_total_lru"] == 0.0


def test_full_evidence_is_deterministic_complete_and_schema_valid(workspace, protocol, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="python -m gamification_sim run-learn-xp-screening --implementation-sha <sha> --base-sha <sha>",
    )
    validate_learn_xp_screening_evidence(payload, workspace=workspace)
    assert len(payload["units"]) == 340
    assert len(payload["candidates"]) == 8
    assert len(payload["references"]) == 2
    assert len(payload["families"]) == 2
    assert payload["shared_evidence"]["replay"]["pass"]
    assert all(len(item["gates"]) == EXPECTED_GATES for item in payload["candidates"])
    assert all(len(item["metrics"]) == EXPECTED_METRICS for item in payload["candidates"])
    assert {gate["scope"] for item in payload["candidates"] for gate in item["gates"]} == {
        "REPOSITORY_PROTOCOL_CONTINUITY",
        "UNIT_SCENARIO",
        "CANDIDATE_AGGREGATE",
        "FAMILY_SELECTION_PREREQUISITE",
    }
    assert all(item["screening_status"] == "REFERENCE_ONLY" for item in payload["references"])
    assert all(item["complete_units"] == 34 for item in payload["candidates"] + payload["references"])
    assert all(sum(1 for item in payload["candidates"] if item["family_id"] == family["family_id"] and item["survivor_selected"]) <= 1 for family in payload["families"])


def test_detached_validator_rejects_fake_pass(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    bad = copy.deepcopy(payload)
    bad["candidates"][0]["gates"][0]["pass"] = not bad["candidates"][0]["gates"][0]["pass"]
    bad["evidence_digest"] = ""
    bad["evidence_digest"] = canonical_digest(bad)
    with pytest.raises(ValueError, match="candidate aggregates mismatch"):
        validate_learn_xp_screening_evidence(bad, workspace=workspace)


def test_detached_validator_rejects_modified_unit_id(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    bad = copy.deepcopy(payload)
    bad["units"][0]["unit_id"] = "U-" + "0" * 64
    bad["evidence_digest"] = ""
    bad["evidence_digest"] = canonical_digest(bad)
    with pytest.raises(ValueError):
        validate_learn_xp_screening_evidence(bad, workspace=workspace)


def test_weighted_score_and_private_fields_are_absent(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    text = json.dumps(payload, sort_keys=True)
    assert "weighted_score" not in text
    assert "real_card_text" not in text
    assert "raw_revlog" not in text
    assert "/home/" not in text
    assert payload["boundaries"] == {
        "adaptive_units": 0,
        "rescue_sweep": False,
        "cross_family_ranking": False,
        "final_model_selected": False,
        "production_approved": False,
        "production_integration": False,
        "g2_5_started": False,
    }


def test_detached_validator_rejects_fake_shared_pass(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    bad = copy.deepcopy(payload)
    bad["shared_evidence"]["strict_event_types"] = "FAIL"
    bad["evidence_digest"] = ""
    bad["evidence_digest"] = canonical_digest(bad)
    with pytest.raises(ValueError, match="strict_event_types|shared gate evidence mismatch"):
        validate_learn_xp_screening_evidence(bad, workspace=workspace)


def test_detached_validator_rejects_reference_survivor(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    bad = copy.deepcopy(payload)
    bad["references"][0]["survivor_selected"] = True
    bad["evidence_digest"] = ""
    bad["evidence_digest"] = canonical_digest(bad)
    with pytest.raises(ValueError):
        validate_learn_xp_screening_evidence(bad, workspace=workspace)


def test_detached_validator_rejects_private_absolute_command(workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    bad = copy.deepcopy(payload)
    bad["provenance"]["exact_command"] = "/home/owner/run-screening"
    bad["evidence_digest"] = ""
    bad["evidence_digest"] = canonical_digest(bad)
    with pytest.raises(ValueError, match="private"):
        validate_learn_xp_screening_evidence(bad, workspace=workspace)


def test_external_bundle_is_deterministic(tmp_path, workspace, stub_git):
    payload = run_learn_xp_screening(
        workspace,
        implementation_sha=IMPL_SHA,
        base_sha=BASE_SHA,
        exact_command="safe command",
    )
    first_dir, first_archive = write_learn_xp_screening_bundle(payload, tmp_path / "first")
    second_dir, second_archive = write_learn_xp_screening_bundle(payload, tmp_path / "second")
    assert first_archive.read_bytes() == second_archive.read_bytes()
    assert (first_dir / "FILES.sha256").read_text() == (second_dir / "FILES.sha256").read_text()
    assert "/home/" not in (first_dir / "command.txt").read_text()
