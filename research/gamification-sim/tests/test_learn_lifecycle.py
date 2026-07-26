from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from gamification_sim.canonical_json import canonical_digest as shared_canonical_digest
from gamification_sim.learn_lifecycle import (
    LifecycleError,
    LifecycleState,
    TransitionReason,
    evaluate_lifecycle,
)
from gamification_sim.validation import dataclass_to_dict
from gamification_sim.strict_json import load_strict_json, loads_strict


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "contracts" / "learn-xp-lifecycle-model-v1.json"
MODEL_SCHEMA_PATH = ROOT / "schemas" / "learn-xp-lifecycle-model-v1.schema.json"
FIXTURE_SCHEMA_PATH = ROOT / "schemas" / "learn-xp-lifecycle-fixture-v1.schema.json"
FIXTURE_ROOT = ROOT / "fixtures" / "learn-xp-lifecycle-v1"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
SOURCE_CONTRACT_PATH = ROOT / "contracts" / "learn-xp-problem-contract-v1.json"
SOURCE_SCHEMA_PATH = ROOT / "schemas" / "learn-xp-problem-contract-v1.schema.json"

REQUIRED_THREAT_FIXTURES = {
    "FIX-REPETITION-AGAIN-GOOD-LOOP",
    "FIX-CONFIG-STEPS-EQUIVALENCE",
    "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE",
    "FIX-LIFECYCLE-RESET-REIMPORT",
    "FIX-SESSION-DAY-CLOCK-INVARIANCE",
    "FIX-ANSWER-RATING-REVEAL-NEUTRALITY",
}
REQUIRED_INVARIANTS = {
    "INV-SCHEDULER-UNCHANGED",
    "INV-FSRS-UNCHANGED",
    "INV-DUE-DATES-UNCHANGED",
    "INV-BUTTON-DIRECT-REWARD-NEUTRAL",
    "INV-HONEST-AGAIN-NOT-PUNISHED",
    "INV-NO-HARD-MISREPORT-INCENTIVE",
    "INV-NO-STEP-COUNT-GAIN",
    "INV-NO-RESPONSE-TIME-REWARD",
    "INV-SESSION-INVARIANT",
    "INV-CONFIGURATION-INVARIANT",
    "INV-RESET-DOES-NOT-MINT-NEW-ACHIEVEMENT",
    "INV-DUPLICATE-OBJECTS-DO-NOT-MULTIPLY-ACHIEVEMENT",
    "INV-PENDING-BOUNDED",
    "INV-CONFIRMATION-REQUIRES-INDEPENDENT-SIGNAL",
    "INV-DETERMINISTIC-REPLAY",
    "INV-DECOMPOSABLE-EVIDENCE",
    "INV-RESEARCH-ONLY",
    "INV-NO-REAL-USER-DATA",
    "INV-NO-PRODUCTION-APPROVAL",
}
FORBIDDEN_KEYS = {
    "real_card_text",
    "note_fields",
    "media",
    "profile_path",
    "profile_paths",
    "username",
    "usernames",
    "token",
    "tokens",
    "raw_revlog",
    "private_absolute_path",
    "private_absolute_paths",
    "xp_amount",
    "pending_ratio",
    "confirmation_delay_days",
}


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = load_strict_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _fixture_paths() -> list[Path]:
    return sorted(
        path
        for path in FIXTURE_ROOT.rglob("*.json")
        if path.name != "manifest.json"
    )


def _load_fixtures() -> list[dict]:
    return [load_strict_json(path) for path in _fixture_paths()]


def _assert_unique(values: list[str], label: str) -> None:
    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    assert not duplicates, f"duplicate {label}: {duplicates}"


def _validate_semantics(model: dict, fixtures: list[dict], manifest: dict) -> None:
    state_ids = [entry["state_id"] for entry in model["state_definitions"]]
    event_ids = [entry["event_id"] for entry in model["event_definitions"]]
    transition_ids = [entry["transition_id"] for entry in model["transition_definitions"]]
    fixture_ids = [entry["fixture_id"] for entry in fixtures]
    invariant_ids = [entry["invariant_id"] for entry in model["protected_invariant_mapping"]]

    _assert_unique(state_ids, "state ID")
    _assert_unique(event_ids, "event ID")
    _assert_unique(transition_ids, "transition ID")
    _assert_unique(fixture_ids, "fixture ID")
    _assert_unique(invariant_ids, "invariant ID")

    assert set(state_ids) == set(model["namespaces"]["learn_xp_lifecycle_state"])
    assert set(event_ids) == set(model["namespaces"]["learn_xp_event"])
    assert set(invariant_ids) == REQUIRED_INVARIANTS
    assert set(manifest["covered_invariant_ids"]) == REQUIRED_INVARIANTS
    assert set(manifest["fixture_ids"]) == set(fixture_ids)
    assert manifest["fixture_count"] == len(fixtures) == 23
    assert set(manifest["required_threat_fixture_ids"]) == REQUIRED_THREAT_FIXTURES
    assert {entry["fixture_id"] for entry in model["threat_fixture_registry"]} == REQUIRED_THREAT_FIXTURES

    registered = set(fixture_ids)
    for mapping in model["protected_invariant_mapping"]:
        assert set(mapping["fixture_ids"]) <= registered
        if mapping["status"] == "PROVEN_BY_FIXTURE":
            assert mapping["fixture_ids"]

    for transition in model["transition_definitions"]:
        assert set(transition["from_states"]) <= set(state_ids)
        if transition["to_state"] not in {"PRESERVE", "PRESERVE_OR_INVALIDATED"}:
            assert transition["to_state"] in state_ids
        if transition["trigger_event"] != "ANY_REGISTERED_EVENT":
            assert transition["trigger_event"] in event_ids


def _walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def test_source_g2_1_contract_continuity() -> None:
    if not SOURCE_CONTRACT_PATH.exists() or not SOURCE_SCHEMA_PATH.exists():
        pytest.skip("standalone bundle does not include frozen G2.1 sources")
    contract = load_strict_json(SOURCE_CONTRACT_PATH)
    schema = load_strict_json(SOURCE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(contract)
    assert contract["identity"] == {"contract_id": "learn-xp-problem-contract", "version": 1}
    assert contract["status"]["contract_status"] == "FROZEN_PRE_LIFECYCLE_ANALYSIS"
    assert contract["production_flags"] == {
        "candidate_selected": False,
        "reward_amount_selected": False,
        "identity_model_selected": False,
        "confirmation_delay_selected": False,
        "simulation_executed": False,
        "production_approved": False,
        "production_integration": False,
        "g2_2_started": False,
    }


def test_model_and_fixture_schemas_self_check_and_validate() -> None:
    model_validator = _validator(MODEL_SCHEMA_PATH)
    fixture_validator = _validator(FIXTURE_SCHEMA_PATH)
    model = load_strict_json(MODEL_PATH)
    model_validator.validate(model)
    fixtures = _load_fixtures()
    for fixture in fixtures:
        fixture_validator.validate(fixture)
    manifest = load_strict_json(MANIFEST_PATH)
    _validate_semantics(model, fixtures, manifest)


def test_fixture_manifest_digest_and_file_inventory() -> None:
    manifest = load_strict_json(MANIFEST_PATH)
    stored = manifest["manifest_digest"]
    detached = dict(manifest)
    detached["manifest_digest"] = ""
    serialized = json.dumps(
        detached,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    assert hashlib.sha256(serialized.encode("utf-8")).hexdigest() == stored
    actual_files = sorted(path.relative_to(FIXTURE_ROOT).as_posix() for path in _fixture_paths())
    assert actual_files == manifest["files"]


def test_all_frozen_fixtures_match_expected_ledger() -> None:
    for fixture in _load_fixtures():
        results = {}
        for case in fixture["cases"]:
            result = evaluate_lifecycle(case["events"])
            results[case["case_id"]] = result
            expected = case["expected"]
            actual_trace = [
                {
                    "from_state": row.from_state.value,
                    "to_state": row.to_state.value,
                    "reason_code": row.reason_code.value,
                }
                for row in result.transition_ledger
            ]
            assert actual_trace == expected["expected_trace"], (fixture["fixture_id"], case["case_id"])
            assert result.final_state.value == expected["expected_final_state"]
            assert [row.reason_code.value for row in result.transition_ledger] == expected["expected_reason_codes"]
            assert result.canonical_digest == evaluate_lifecycle(case["events"]).canonical_digest

        comparison = fixture["comparison"]
        if comparison is None:
            continue
        left = results[comparison["left_case_id"]]
        right = results[comparison["right_case_id"]]
        assertions = set(comparison["assertions"])
        if "SAME_FINAL_STATE" in assertions or "SAME_LIFECYCLE_ELIGIBILITY" in assertions:
            assert left.final_state == right.final_state
        if "NO_EXTRA_CONFIRMATION" in assertions:
            left_confirm = sum(row.to_state is LifecycleState.CONFIRMED for row in left.transition_ledger)
            right_confirm = sum(row.to_state is LifecycleState.CONFIRMED for row in right.transition_ledger)
            assert right_confirm <= left_confirm
        if "NO_FRESH_ELIGIBILITY" in assertions:
            right_entries = [
                row
                for row in right.transition_ledger
                if row.from_state in {
                    LifecycleState.CONFIRMED,
                    LifecycleState.EXPIRED,
                    LifecycleState.CANCELLED,
                    LifecycleState.INVALIDATED,
                }
                and row.to_state in {LifecycleState.IN_PROGRESS, LifecycleState.PENDING, LifecycleState.CONFIRMED}
            ]
            assert not right_entries
        if "NO_BUTTON_ADVANTAGE" in assertions:
            rank = {
                LifecycleState.NOT_STARTED: 0,
                LifecycleState.IN_PROGRESS: 1,
                LifecycleState.PENDING: 2,
                LifecycleState.CONFIRMED: 3,
                LifecycleState.EXPIRED: 0,
                LifecycleState.CANCELLED: 0,
                LifecycleState.INVALIDATED: 0,
            }
            assert rank[right.final_state] <= rank[left.final_state]


def test_factorized_identity_subjects_and_episode_container() -> None:
    model = load_strict_json(MODEL_PATH)
    assert model["identity_architecture"]["architecture"] == "FACTORIZED"
    assert model["identity_architecture"]["generic_form"] == "LearningEpisode<AchievementSubject>"
    assert {entry["subject_id"] for entry in model["subject_candidates"]} == {
        "CARD",
        "NOTE",
        "SIBLING_GROUP",
    }
    assert all(entry["selected"] is False for entry in model["subject_candidates"])
    assert model["episode_container"] == {
        "container_id": "LEARNING_EPISODE",
        "generic_form": "LearningEpisode<AchievementSubject>",
        "selected_as_subject": False,
        "bounded": True,
    }


def test_honest_again_and_hard_misreport_are_equivalent_without_success_signal() -> None:
    fixture = next(
        item for item in _load_fixtures() if item["fixture_id"] == "FIX-ANSWER-RATING-REVEAL-NEUTRALITY"
    )
    control, attack = fixture["cases"]
    control_result = evaluate_lifecycle(control["events"])
    attack_result = evaluate_lifecycle(attack["events"])
    assert control_result.final_state is LifecycleState.PENDING
    assert attack_result.final_state is LifecycleState.PENDING
    assert TransitionReason.INDEPENDENT_CONFIRMATION not in {
        row.reason_code for row in attack_result.transition_ledger
    }


def test_same_chain_cannot_confirm_and_independent_signal_requires_linkage() -> None:
    same_chain = next(
        item for item in _load_fixtures() if item["fixture_id"] == "FIX-ORD-SAME-CHAIN-NO-CONFIRM"
    )
    assert evaluate_lifecycle(same_chain["cases"][0]["events"]).final_state is LifecycleState.PENDING

    independent = copy.deepcopy(
        next(
            item for item in _load_fixtures() if item["fixture_id"] == "FIX-ORD-INDEPENDENT-SUCCESS-CONFIRM"
        )["cases"][0]["events"]
    )
    independent[-1]["source_event_id"] = None
    with pytest.raises(LifecycleError, match="source_event_id"):
        evaluate_lifecycle(independent)


def test_duplicate_event_id_and_out_of_order_are_rejected() -> None:
    events = [
        {
            "event_id": "EV-1",
            "sequence_index": 1,
            "event_kind": "VALID_INITIAL_ATTEMPT",
            "subject_type": "CARD",
            "subject_id": "card-1",
            "episode_id": "episode-1",
        },
        {
            "event_id": "EV-1",
            "sequence_index": 2,
            "event_kind": "REQUEST_PENDING",
            "subject_type": "CARD",
            "subject_id": "card-1",
            "episode_id": "episode-1",
        },
    ]
    with pytest.raises(LifecycleError, match="duplicate event_id"):
        evaluate_lifecycle(events)
    events[1]["event_id"] = "EV-2"
    events[1]["sequence_index"] = 0
    with pytest.raises(LifecycleError, match="strictly increasing"):
        evaluate_lifecycle(events)


def test_missing_episode_and_conflicting_subject_fail_closed() -> None:
    missing_episode = [
        {
            "event_id": "EV-1",
            "sequence_index": 1,
            "event_kind": "VALID_INITIAL_ATTEMPT",
            "subject_type": "CARD",
            "subject_id": "card-1",
            "episode_id": None,
        }
    ]
    assert evaluate_lifecycle(missing_episode).final_state is LifecycleState.INVALIDATED
    fixture = next(
        item for item in _load_fixtures() if item["fixture_id"] == "FIX-MISSING-CONFLICTING-SUBJECT-INVALIDATE"
    )
    assert evaluate_lifecycle(fixture["cases"][0]["events"]).final_state is LifecycleState.INVALIDATED


def test_confirmed_state_resists_reset_and_reimport_farming() -> None:
    fixture = next(
        item for item in _load_fixtures() if item["fixture_id"] == "FIX-TERM-CONFIRMED-RESET-PRESERVE"
    )
    events = copy.deepcopy(fixture["cases"][0]["events"])
    events.extend(
        [
            {
                **events[-1],
                "event_id": "EV-5",
                "sequence_index": 5,
                "event_kind": "DELETE_REIMPORT",
                "monotonic_time_index": 201,
            },
            {
                **events[-1],
                "event_id": "EV-6",
                "sequence_index": 6,
                "event_kind": "VALID_INITIAL_ATTEMPT",
                "monotonic_time_index": 202,
            },
            {
                **events[-1],
                "event_id": "EV-7",
                "sequence_index": 7,
                "event_kind": "REQUEST_PENDING",
                "monotonic_time_index": 203,
            },
        ]
    )
    result = evaluate_lifecycle(events)
    assert result.final_state is LifecycleState.CONFIRMED
    assert sum(row.reason_code is TransitionReason.INDEPENDENT_CONFIRMATION for row in result.transition_ledger) == 1


def test_schema_negative_samples_and_forbidden_fields() -> None:
    model_validator = _validator(MODEL_SCHEMA_PATH)
    fixture_validator = _validator(FIXTURE_SCHEMA_PATH)
    model = load_strict_json(MODEL_PATH)
    fixture = _load_fixtures()[0]

    mutations = []
    bad = copy.deepcopy(model)
    bad["production_flags"]["production_approved"] = True
    mutations.append((model_validator, bad))
    bad = copy.deepcopy(model)
    bad["production_flags"]["achievement_subject_selected"] = True
    mutations.append((model_validator, bad))
    for key, value in (
        ("xp_amount", 10),
        ("pending_ratio", 0.5),
        ("confirmation_delay_days", 7),
    ):
        bad = copy.deepcopy(model)
        bad[key] = value
        mutations.append((model_validator, bad))

    bad_fixture = copy.deepcopy(fixture)
    bad_fixture["cases"][0]["events"][0]["real_card_text"] = "private"
    mutations.append((fixture_validator, bad_fixture))
    bad_fixture = copy.deepcopy(fixture)
    bad_fixture["cases"][0]["events"][0]["profile_path"] = "/home/user/.local/share/Anki2"
    mutations.append((fixture_validator, bad_fixture))
    bad_fixture = copy.deepcopy(fixture)
    bad_fixture["cases"][0]["events"][0]["raw_revlog"] = []
    mutations.append((fixture_validator, bad_fixture))
    bad_fixture = copy.deepcopy(fixture)
    bad_fixture["cases"][0]["events"][0]["event_kind"] = "UNKNOWN_EVENT"
    mutations.append((fixture_validator, bad_fixture))
    bad_fixture = copy.deepcopy(fixture)
    bad_fixture["cases"][0]["expected"]["expected_trace"][0]["reason_code"] = "UNKNOWN_REASON"
    mutations.append((fixture_validator, bad_fixture))

    for validator, payload in mutations:
        with pytest.raises(ValidationError):
            validator.validate(payload)

    assert not (set(_walk_keys(model)) & FORBIDDEN_KEYS)
    for entry in _load_fixtures():
        assert not (set(_walk_keys(entry)) & FORBIDDEN_KEYS)


def test_strict_json_rejects_duplicate_keys_and_non_finite_numbers() -> None:
    with pytest.raises(Exception, match="duplicate object key"):
        loads_strict('{"a":1,"a":2}')
    with pytest.raises(Exception, match="non-standard JSON number"):
        loads_strict('{"value":NaN}')


def test_semantic_validator_rejects_unregistered_or_missing_coverage() -> None:
    model = load_strict_json(MODEL_PATH)
    fixtures = _load_fixtures()
    manifest = load_strict_json(MANIFEST_PATH)

    bad_manifest = copy.deepcopy(manifest)
    bad_manifest["fixture_ids"].append("FIX-UNREGISTERED")
    with pytest.raises(AssertionError):
        _validate_semantics(model, fixtures, bad_manifest)

    bad_model = copy.deepcopy(model)
    bad_model["protected_invariant_mapping"] = bad_model["protected_invariant_mapping"][:-1]
    with pytest.raises(AssertionError):
        _validate_semantics(bad_model, fixtures, manifest)


def test_no_private_or_production_imports_in_evaluator() -> None:
    source = (ROOT / "src" / "gamification_sim" / "learn_lifecycle.py").read_text(encoding="utf-8")
    forbidden_import_fragments = (
        "anki_study_report",
        "aqt",
        "anki.collection",
        "sqlite3",
        "requests",
        "httpx",
        "os.environ",
        "datetime.now",
        "time.time",
        "random",
    )
    for fragment in forbidden_import_fragments:
        assert fragment not in source


FROZEN_LIFECYCLE_RESULT_SNAPSHOTS = json.loads(
    "{\n  \"FIX-ANSWER-RATING-REVEAL-NEUTRALITY::CASE-ANSWER-ATTACK\": {\n    \"canonical_digest\": \"ad4c9ec2e9ea4a685e4dfd12da14bf36ec2f65a8906b6a006de9325ff12db3f2\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\",\n      \"EV-5\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"NON_REWARDABLE_IGNORED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"RATING_ONLY_NEUTRAL\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-5\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"DELAYED_FAILURE_NO_CONFIRMATION\",\n        \"sequence_index\": 5,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ANSWER-RATING-REVEAL-NEUTRALITY::CASE-ANSWER-CONTROL\": {\n    \"canonical_digest\": \"eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"DELAYED_FAILURE_NO_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-CONFIG-STEPS-EQUIVALENCE::CASE-CONFIG-ATTACK\": {\n    \"canonical_digest\": \"7a88b8b1fcf84de7f4bdd1d33092d46d913f433cc81872dab222321f6adacb5e\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"CONFIGURATION_NEUTRAL\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"CONFIGURATION_NEUTRAL\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-CONFIG-STEPS-EQUIVALENCE::CASE-CONFIG-CONTROL\": {\n    \"canonical_digest\": \"8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ID-CARD-EPISODE::CASE-CARD-EPISODE\": {\n    \"canonical_digest\": \"8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ID-NOTE-EPISODE::CASE-NOTE-EPISODE\": {\n    \"canonical_digest\": \"f668870a4cb06d42e9e013904a783eaa1c10c4326d6e85f81b7b9014c9d0d483\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"NOTE:note-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"NOTE:note-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"NOTE:note-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ID-SIBLING-GROUP-EPISODE::CASE-SIBLING-GROUP-EPISODE\": {\n    \"canonical_digest\": \"02018a4eb4a49b64ff7e98a0f3beb169b4cc5df046428b5d6ec7ff7282118b31\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"SIBLING_GROUP:siblings-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"SIBLING_GROUP:siblings-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"SIBLING_GROUP:siblings-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-INV-CONFIG-PROFILE-EQUIVALENCE::CASE-CONFIG-MANY\": {\n    \"canonical_digest\": \"1228ada88d47d9cfcf7fd26492f2b61b14aa74a47a15ec976b73982bbf1dd090\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"CONFIGURATION_NEUTRAL\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-INV-CONFIG-PROFILE-EQUIVALENCE::CASE-CONFIG-ONE\": {\n    \"canonical_digest\": \"8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-INV-SESSION-REGROUPING::CASE-SESSION-SINGLE\": {\n    \"canonical_digest\": \"8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-INV-SESSION-REGROUPING::CASE-SESSION-SPLIT\": {\n    \"canonical_digest\": \"4fc1bdf40d35331843c3e1350eb0b4150884efa7ee75dd1a03b772bb5b070a50\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"SESSION_TIME_NEUTRAL\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-LIFECYCLE-RESET-REIMPORT::CASE-LIFECYCLE-ATTACK\": {\n    \"canonical_digest\": \"df629fb95d6a128a730de9291379c8c82b529e8c4378a204043cf85c27e427eb\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"INVALIDATED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"RESET_NO_NEW_ACHIEVEMENT\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"CONTINUITY_INVALIDATED\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"INVALIDATED\"\n      }\n    ]\n  },\n  \"FIX-LIFECYCLE-RESET-REIMPORT::CASE-LIFECYCLE-CONTROL\": {\n    \"canonical_digest\": \"8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-MISSING-CONFLICTING-SUBJECT-INVALIDATE::CASE-CONFLICTING-SUBJECT\": {\n    \"canonical_digest\": \"be29cc841653d1cbf84cb3b479fd6f55df40d801940c674dd8a44d963d4ff2b0\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"INVALIDATED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"CONFLICTING_SUBJECT_INVALIDATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"INVALIDATED\"\n      }\n    ]\n  },\n  \"FIX-MISSING-SUBJECT-INVALIDATE::CASE-MISSING-SUBJECT\": {\n    \"canonical_digest\": \"5cddcb90aebc67de281ff64707e5c03630b41ec51a0f312d9347121398a2dfe3\",\n    \"episode_id\": null,\n    \"final_state\": \"INVALIDATED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\"\n    ],\n    \"subject_key\": null,\n    \"transition_ledger\": [\n      {\n        \"episode_id\": null,\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"MISSING_SUBJECT_INVALIDATED\",\n        \"sequence_index\": 1,\n        \"subject_key\": null,\n        \"to_state\": \"INVALIDATED\"\n      }\n    ]\n  },\n  \"FIX-OBJECT-DUPLICATE-REVERSE-CLOZE::CASE-OBJECT-ATTACK\": {\n    \"canonical_digest\": \"e2e9e8c81f1d18ffb824fad3bbc57a05d8deca619bc400d5bb4a12d6f09835da\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"INVALIDATED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-original\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-original\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-original\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"CONFLICTING_SUBJECT_INVALIDATED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-original\",\n        \"to_state\": \"INVALIDATED\"\n      }\n    ]\n  },\n  \"FIX-OBJECT-DUPLICATE-REVERSE-CLOZE::CASE-OBJECT-CONTROL\": {\n    \"canonical_digest\": \"87f8f222b7b9fcac80d9d130936075241b3dbdbd47e73d8cd71618a6040722a7\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-original\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-original\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-original\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ORD-DELAYED-FAILURE-NO-CONFIRM::CASE-DELAYED-FAILURE\": {\n    \"canonical_digest\": \"eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"DELAYED_FAILURE_NO_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ORD-EXPOSURE-NO-START::CASE-EXPOSURE\": {\n    \"canonical_digest\": \"410cb4bc0b6f51ef2f06a5b5ea2c98fc41c6200b100cf3f50ebe586c2e8d9b3b\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"NOT_STARTED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"NON_REWARDABLE_IGNORED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"NOT_STARTED\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"NON_REWARDABLE_IGNORED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"NOT_STARTED\"\n      }\n    ]\n  },\n  \"FIX-ORD-INDEPENDENT-SUCCESS-CONFIRM::CASE-INDEPENDENT-SUCCESS\": {\n    \"canonical_digest\": \"858322d74a912edbe3ef3e486ad63967b64baae58d332ac6d67e60d68d2d2025\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"CONFIRMED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"INDEPENDENT_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CONFIRMED\"\n      }\n    ]\n  },\n  \"FIX-ORD-PENDING-IDEMPOTENT::CASE-PENDING-IDEMPOTENT\": {\n    \"canonical_digest\": \"6db343145c235c3c43f050caf1b1ee9d4985dfe1f8f9a62caafe7af20ec0e222\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"PENDING_ALREADY_EXISTS\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ORD-SAME-CHAIN-NO-CONFIRM::CASE-SAME-CHAIN\": {\n    \"canonical_digest\": \"330feb52d872fe75c47e3b49eba9990c1fafa11b3785337db8d15b550d065ce0\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"SAME_CHAIN_NOT_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-ORD-VALID-ATTEMPT-IN-PROGRESS::CASE-VALID-ATTEMPT\": {\n    \"canonical_digest\": \"c072dc688fa64afa632e7f06f385c86d89e4edfd410901ed71c7991c4c9a6bc4\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"IN_PROGRESS\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      }\n    ]\n  },\n  \"FIX-REPETITION-AGAIN-GOOD-LOOP::CASE-REPETITION-ATTACK\": {\n    \"canonical_digest\": \"681dc7b60070489e16c924834697b73b55701dc4cfcae4e5c7bbd594f9f32d32\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\",\n      \"EV-5\",\n      \"EV-6\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"RATING_ONLY_NEUTRAL\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"SAME_CHAIN_NOT_CONFIRMATION\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-5\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"RATING_ONLY_NEUTRAL\",\n        \"sequence_index\": 5,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-6\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"SAME_CHAIN_NOT_CONFIRMATION\",\n        \"sequence_index\": 6,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-REPETITION-AGAIN-GOOD-LOOP::CASE-REPETITION-CONTROL\": {\n    \"canonical_digest\": \"eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"PENDING\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"DELAYED_FAILURE_NO_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      }\n    ]\n  },\n  \"FIX-SESSION-DAY-CLOCK-INVARIANCE::CASE-SESSION-ATTACK\": {\n    \"canonical_digest\": \"5355c31759876e9a12e44a76d216370234a4b15ff92b922811ccce1d109bb51f\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"CONFIRMED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\",\n      \"EV-5\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"SESSION_TIME_NEUTRAL\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"SESSION_TIME_NEUTRAL\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-5\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"INDEPENDENT_CONFIRMATION\",\n        \"sequence_index\": 5,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CONFIRMED\"\n      }\n    ]\n  },\n  \"FIX-SESSION-DAY-CLOCK-INVARIANCE::CASE-SESSION-CONTROL\": {\n    \"canonical_digest\": \"858322d74a912edbe3ef3e486ad63967b64baae58d332ac6d67e60d68d2d2025\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"CONFIRMED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"INDEPENDENT_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CONFIRMED\"\n      }\n    ]\n  },\n  \"FIX-TERM-CONFIRMED-RESET-PRESERVE::CASE-CONFIRMED-RESET\": {\n    \"canonical_digest\": \"f99b1e6e9c8ceb9bd94dda5d2d8629c4524f289e5bec3689d9964b32d2cd72b4\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"CONFIRMED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\",\n      \"EV-4\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"INDEPENDENT_CONFIRMATION\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CONFIRMED\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-4\",\n        \"from_state\": \"CONFIRMED\",\n        \"reason_code\": \"CONFIRMED_TERMINAL_PRESERVED\",\n        \"sequence_index\": 4,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CONFIRMED\"\n      }\n    ]\n  },\n  \"FIX-TERM-DUPLICATE-REPLAY::CASE-DUPLICATE-REPLAY\": {\n    \"canonical_digest\": \"b4d7b86da61c9a03e5b8b3139c7438fc396cd0bab0dcda0a6b46f7dcef6f903d\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"IN_PROGRESS\",\n    \"ignored_duplicate_source_ids\": [\n      \"EV-1\"\n    ],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"DUPLICATE_REPLAY_IGNORED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      }\n    ]\n  },\n  \"FIX-TERM-EXPIRY::CASE-EXPIRY\": {\n    \"canonical_digest\": \"68a1523411f5dbf9754df86a2b38c8aafa0bde0330772782143a7db047030740\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"EXPIRED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"PENDING_EXPIRED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"EXPIRED\"\n      }\n    ]\n  },\n  \"FIX-TERM-UNDO-CANCEL::CASE-UNDO\": {\n    \"canonical_digest\": \"f9fe835ee8601a241e5013a758b2b0f0c98410ade1b653b49cd0f1b962e5aa6b\",\n    \"episode_id\": \"episode-1\",\n    \"final_state\": \"CANCELLED\",\n    \"ignored_duplicate_source_ids\": [],\n    \"processed_event_ids\": [\n      \"EV-1\",\n      \"EV-2\",\n      \"EV-3\"\n    ],\n    \"subject_key\": \"CARD:card-1\",\n    \"transition_ledger\": [\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-1\",\n        \"from_state\": \"NOT_STARTED\",\n        \"reason_code\": \"VALID_ATTEMPT_STARTED\",\n        \"sequence_index\": 1,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"IN_PROGRESS\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-2\",\n        \"from_state\": \"IN_PROGRESS\",\n        \"reason_code\": \"PENDING_CREATED\",\n        \"sequence_index\": 2,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"PENDING\"\n      },\n      {\n        \"episode_id\": \"episode-1\",\n        \"event_id\": \"EV-3\",\n        \"from_state\": \"PENDING\",\n        \"reason_code\": \"SOURCE_CANCELLED\",\n        \"sequence_index\": 3,\n        \"subject_key\": \"CARD:card-1\",\n        \"to_state\": \"CANCELLED\"\n      }\n    ]\n  }\n}"
)


def test_shared_canonical_digest_preserves_all_frozen_lifecycle_results() -> None:
    actual = {}
    for fixture in _load_fixtures():
        for case in fixture["cases"]:
            result = evaluate_lifecycle(case["events"])
            payload = dataclass_to_dict(result)
            stored = payload.pop("canonical_digest")
            assert shared_canonical_digest(payload) == stored
            actual[f"{fixture['fixture_id']}::{case['case_id']}"] = dataclass_to_dict(result)
    assert actual == FROZEN_LIFECYCLE_RESULT_SNAPSHOTS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sequence_index", "1"),
        ("sequence_index", True),
        ("sequence_index", 1.0),
        ("sequence_index", -1),
        ("answer_revealed", 0),
        ("answer_revealed", 1),
        ("answer_revealed", "false"),
        ("event_id", 123),
        ("subject_id", 123),
        ("episode_id", ""),
        ("monotonic_time_index", "10"),
        ("monotonic_time_index", True),
        ("anki_day_index", True),
        ("scheduler_state_before", "UNKNOWN_STATE"),
        ("rating", "UNKNOWN_RATING"),
        ("event_kind", "UNKNOWN_EVENT"),
        ("unexpected_property", "value"),
    ],
)
def test_direct_event_input_rejects_coercion_and_unknown_values(field, value) -> None:
    payload = {
        "event_id": "EV-STRICT-1",
        "sequence_index": 0,
        "event_kind": "VALID_INITIAL_ATTEMPT",
        "subject_type": "CARD",
        "subject_id": "card-1",
        "episode_id": "episode-1",
        "answer_revealed": False,
        "scheduler_state_before": "ANKI_STATE_NEW",
        "scheduler_state_after": "ANKI_STATE_LEARNING",
        "anki_day_index": 0,
        "monotonic_time_index": 0,
    }
    payload[field] = value
    with pytest.raises(LifecycleError):
        evaluate_lifecycle([payload])
