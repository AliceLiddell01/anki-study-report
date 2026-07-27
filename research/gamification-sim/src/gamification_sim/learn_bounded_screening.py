from __future__ import annotations

import hashlib
import importlib.metadata
import ast
import json
import platform
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from gzip import GzipFile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest
from .learn_candidate_protocol import generate_dry_units, matrix_summary
from .learn_lifecycle import (
    EventKind,
    LifecycleResult,
    LifecycleState,
    evaluate_lifecycle,
)
from .learn_reward_allocation import (
    REFERENCE_FAMILY_ID,
    REFERENCE_PARAMETERIZATION_ID,
    evaluate_allocation,
)
from .strict_json import load_strict_json
from .validation import dataclass_to_dict
from .workspace import ResearchWorkspace, resolve_research_workspace


PROTOCOL_RELATIVE_PATH = Path("contracts/learn-xp-candidate-protocol-v1.json")
HUMAN_PROTOCOL_REPOSITORY_PATH = Path("docs/gamification/learn-xp-candidate-protocol.md")
PROTOCOL_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-candidate-protocol-v1.schema.json")
EVIDENCE_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-bounded-screening-evidence-v1.schema.json")
G2_1_CONTRACT_RELATIVE_PATH = Path("contracts/learn-xp-problem-contract-v1.json")
G2_1_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-problem-contract-v1.schema.json")
G2_2_MODEL_RELATIVE_PATH = Path("contracts/learn-xp-lifecycle-model-v1.json")
G2_2_MODEL_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-lifecycle-model-v1.schema.json")
G2_2_FIXTURE_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-lifecycle-fixture-v1.schema.json")
FIXTURE_ROOT_RELATIVE_PATH = Path("fixtures/learn-xp-lifecycle-v1")
FIXTURE_MANIFEST_RELATIVE_PATH = FIXTURE_ROOT_RELATIVE_PATH / "manifest.json"
DRY_GENERATOR_RELATIVE_PATH = Path("src/gamification_sim/learn_candidate_protocol.py")
PUBLICATION_SHA = "41313c9369c76d331d489a9aa4b44da2497b3132"
STARTING_GAMIFICATION_SHA = "933325f8d2647d52cbc0d6859ff44ded0b6686c4"
EXPECTED_UNITS = 340
EXPECTED_CANDIDATES = 8
EXPECTED_REFERENCES = 2
EXPECTED_GATES = 23
EXPECTED_METRICS = 14
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024

EXPECTED_BLOBS = {
    "human_protocol": "e738514a08f5f25a006914dbf5fe257518f1ed95",
    "protocol": "f2fda31abcc9a9990229a3193d589214222de241",
    "protocol_schema": "110ce870ee1aaa92f2703237deda59ce8dab4f93",
    "dry_generator": "e5a096985bc544545334edc58f4a55b5f4ef5bcd",
    "fixture_manifest": "f8e60cc8b0ebd3ff20fd66f602543f9aa75c2167",
}

FROZEN_LIFECYCLE_RESULT_DIGESTS = {
    "FIX-ANSWER-RATING-REVEAL-NEUTRALITY::CASE-ANSWER-ATTACK": "ad4c9ec2e9ea4a685e4dfd12da14bf36ec2f65a8906b6a006de9325ff12db3f2",
    "FIX-ANSWER-RATING-REVEAL-NEUTRALITY::CASE-ANSWER-CONTROL": "eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded",
    "FIX-CONFIG-STEPS-EQUIVALENCE::CASE-CONFIG-ATTACK": "7a88b8b1fcf84de7f4bdd1d33092d46d913f433cc81872dab222321f6adacb5e",
    "FIX-CONFIG-STEPS-EQUIVALENCE::CASE-CONFIG-CONTROL": "8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3",
    "FIX-ID-CARD-EPISODE::CASE-CARD-EPISODE": "8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3",
    "FIX-ID-NOTE-EPISODE::CASE-NOTE-EPISODE": "f668870a4cb06d42e9e013904a783eaa1c10c4326d6e85f81b7b9014c9d0d483",
    "FIX-ID-SIBLING-GROUP-EPISODE::CASE-SIBLING-GROUP-EPISODE": "02018a4eb4a49b64ff7e98a0f3beb169b4cc5df046428b5d6ec7ff7282118b31",
    "FIX-INV-CONFIG-PROFILE-EQUIVALENCE::CASE-CONFIG-MANY": "1228ada88d47d9cfcf7fd26492f2b61b14aa74a47a15ec976b73982bbf1dd090",
    "FIX-INV-CONFIG-PROFILE-EQUIVALENCE::CASE-CONFIG-ONE": "8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3",
    "FIX-INV-SESSION-REGROUPING::CASE-SESSION-SINGLE": "8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3",
    "FIX-INV-SESSION-REGROUPING::CASE-SESSION-SPLIT": "4fc1bdf40d35331843c3e1350eb0b4150884efa7ee75dd1a03b772bb5b070a50",
    "FIX-LIFECYCLE-RESET-REIMPORT::CASE-LIFECYCLE-ATTACK": "df629fb95d6a128a730de9291379c8c82b529e8c4378a204043cf85c27e427eb",
    "FIX-LIFECYCLE-RESET-REIMPORT::CASE-LIFECYCLE-CONTROL": "8ae08169159b151726585d0844709067f6b85c5f01e0547b8115e35683353eb3",
    "FIX-MISSING-CONFLICTING-SUBJECT-INVALIDATE::CASE-CONFLICTING-SUBJECT": "be29cc841653d1cbf84cb3b479fd6f55df40d801940c674dd8a44d963d4ff2b0",
    "FIX-MISSING-SUBJECT-INVALIDATE::CASE-MISSING-SUBJECT": "5cddcb90aebc67de281ff64707e5c03630b41ec51a0f312d9347121398a2dfe3",
    "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE::CASE-OBJECT-ATTACK": "e2e9e8c81f1d18ffb824fad3bbc57a05d8deca619bc400d5bb4a12d6f09835da",
    "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE::CASE-OBJECT-CONTROL": "87f8f222b7b9fcac80d9d130936075241b3dbdbd47e73d8cd71618a6040722a7",
    "FIX-ORD-DELAYED-FAILURE-NO-CONFIRM::CASE-DELAYED-FAILURE": "eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded",
    "FIX-ORD-EXPOSURE-NO-START::CASE-EXPOSURE": "410cb4bc0b6f51ef2f06a5b5ea2c98fc41c6200b100cf3f50ebe586c2e8d9b3b",
    "FIX-ORD-INDEPENDENT-SUCCESS-CONFIRM::CASE-INDEPENDENT-SUCCESS": "858322d74a912edbe3ef3e486ad63967b64baae58d332ac6d67e60d68d2d2025",
    "FIX-ORD-PENDING-IDEMPOTENT::CASE-PENDING-IDEMPOTENT": "6db343145c235c3c43f050caf1b1ee9d4985dfe1f8f9a62caafe7af20ec0e222",
    "FIX-ORD-SAME-CHAIN-NO-CONFIRM::CASE-SAME-CHAIN": "330feb52d872fe75c47e3b49eba9990c1fafa11b3785337db8d15b550d065ce0",
    "FIX-ORD-VALID-ATTEMPT-IN-PROGRESS::CASE-VALID-ATTEMPT": "c072dc688fa64afa632e7f06f385c86d89e4edfd410901ed71c7991c4c9a6bc4",
    "FIX-REPETITION-AGAIN-GOOD-LOOP::CASE-REPETITION-ATTACK": "681dc7b60070489e16c924834697b73b55701dc4cfcae4e5c7bbd594f9f32d32",
    "FIX-REPETITION-AGAIN-GOOD-LOOP::CASE-REPETITION-CONTROL": "eed66ae425d507839b634383e128e84ec1835f44feb90ff14b4015243dd3cded",
    "FIX-SESSION-DAY-CLOCK-INVARIANCE::CASE-SESSION-ATTACK": "5355c31759876e9a12e44a76d216370234a4b15ff92b922811ccce1d109bb51f",
    "FIX-SESSION-DAY-CLOCK-INVARIANCE::CASE-SESSION-CONTROL": "858322d74a912edbe3ef3e486ad63967b64baae58d332ac6d67e60d68d2d2025",
    "FIX-TERM-CONFIRMED-RESET-PRESERVE::CASE-CONFIRMED-RESET": "f99b1e6e9c8ceb9bd94dda5d2d8629c4524f289e5bec3689d9964b32d2cd72b4",
    "FIX-TERM-DUPLICATE-REPLAY::CASE-DUPLICATE-REPLAY": "b4d7b86da61c9a03e5b8b3139c7438fc396cd0bab0dcda0a6b46f7dcef6f903d",
    "FIX-TERM-EXPIRY::CASE-EXPIRY": "68a1523411f5dbf9754df86a2b38c8aafa0bde0330772782143a7db047030740",
    "FIX-TERM-UNDO-CANCEL::CASE-UNDO": "f9fe835ee8601a241e5013a758b2b0f0c98410ade1b653b49cd0f1b962e5aa6b",
}

ACCOUNTING_SCENARIOS = frozenset(
    {
        "SCN-ACCOUNT-PENDING-ALLOCATION",
        "SCN-ACCOUNT-CONFIRM-SETTLEMENT",
        "SCN-ACCOUNT-EXPIRE-VOID",
        "SCN-ACCOUNT-CANCEL-VOID",
        "SCN-ACCOUNT-INVALIDATE-VOID",
        "SCN-ACCOUNT-SUBJECT-COLLISION",
        "SCN-ACCOUNT-REFERENCE-ZERO",
    }
)


@dataclass(frozen=True, slots=True)
class LearnScreeningUnit:
    unit_id: str
    protocol_version: int
    candidate_or_reference_id: str
    family_id: str
    parameterization_id: str
    subject_strategy_id: str
    delay_policy_id: str
    scenario_id: str
    configuration_profile_id: str
    session_time_arrangement_id: str
    replica: int
    seed: None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LearnScreeningUnit":
        return cls(**{name: value[name] for name in cls.__dataclass_fields__})

    def payload(self) -> dict[str, Any]:
        return dataclass_to_dict(self)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(workspace: ResearchWorkspace, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(workspace.root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _git_blob(workspace: ResearchWorkspace, path: Path) -> str:
    prefix = _git_output(workspace, "rev-parse", "--show-prefix")
    return _git_output(workspace, "rev-parse", f"HEAD:{prefix}{path.as_posix()}")


def _git_repository_blob(workspace: ResearchWorkspace, path: Path) -> str:
    return _git_output(workspace, "rev-parse", f"HEAD:{path.as_posix()}")


def _assert_sha(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be lowercase 40-character hexadecimal")


def _schema_errors(validator: Draft202012Validator, instance: Any) -> list[str]:
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda item: (
            tuple(str(part) for part in item.absolute_path),
            item.message,
        ),
    )
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in errors
    ]


def _validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def load_and_validate_learn_screening_protocol(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = resolve_research_workspace(workspace)
    protocol_path = resolved.path(PROTOCOL_RELATIVE_PATH)
    schema_path = resolved.path(PROTOCOL_SCHEMA_RELATIVE_PATH)
    protocol = load_strict_json(protocol_path)
    schema = load_strict_json(schema_path)
    if not isinstance(protocol, dict) or not isinstance(schema, dict):
        raise ValueError("Learn screening protocol and schema must be objects")
    errors = _schema_errors(_validator(schema), protocol)
    if errors:
        raise ValueError("Learn candidate protocol validation failed: " + "; ".join(errors))
    if protocol["status"]["protocol_status"] != "FROZEN_PRE_SCREENING_IMPLEMENTATION":
        raise ValueError("Learn candidate protocol status drifted")
    if len(protocol["hard_gates"]) != EXPECTED_GATES:
        raise ValueError("Learn hard-gate registry drifted")
    if len(protocol["descriptive_metrics"]) != EXPECTED_METRICS:
        raise ValueError("Learn metric registry drifted")
    summary = matrix_summary(protocol)
    if summary["unit_count"] != EXPECTED_UNITS or summary["unique_unit_ids"] != EXPECTED_UNITS:
        raise ValueError("Learn dry matrix is not exact 340/340")
    human_protocol_blob = _git_repository_blob(resolved, HUMAN_PROTOCOL_REPOSITORY_PATH)
    if human_protocol_blob != EXPECTED_BLOBS["human_protocol"]:
        raise ValueError("frozen Learn human protocol Git blob drifted")
    return protocol, {
        "human_protocol_path": HUMAN_PROTOCOL_REPOSITORY_PATH.as_posix(),
        "human_protocol_blob": human_protocol_blob,
        "protocol_path": PROTOCOL_RELATIVE_PATH.as_posix(),
        "protocol_blob": _git_blob(resolved, PROTOCOL_RELATIVE_PATH),
        "protocol_sha256": _sha256(protocol_path),
        "protocol_digest": canonical_digest(protocol),
        "schema_path": PROTOCOL_SCHEMA_RELATIVE_PATH.as_posix(),
        "schema_blob": _git_blob(resolved, PROTOCOL_SCHEMA_RELATIVE_PATH),
        "schema_sha256": _sha256(schema_path),
        "schema_digest": canonical_digest(schema),
        "schema_draft": schema["$schema"],
    }


def _load_fixture_registry(workspace: ResearchWorkspace) -> dict[str, dict[str, Any]]:
    root = workspace.path(FIXTURE_ROOT_RELATIVE_PATH)
    fixtures: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        payload = load_strict_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"fixture must be an object: {path}")
        fixture_id = payload["fixture_id"]
        if fixture_id in fixtures:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        fixtures[fixture_id] = payload
    if len(fixtures) != 23:
        raise ValueError("frozen Learn fixture inventory must contain 23 fixtures")
    return fixtures


def _validate_source_continuity(
    workspace: ResearchWorkspace,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    paths = {
        "g2_1_contract": G2_1_CONTRACT_RELATIVE_PATH,
        "g2_1_schema": G2_1_SCHEMA_RELATIVE_PATH,
        "g2_2_model": G2_2_MODEL_RELATIVE_PATH,
        "g2_2_model_schema": G2_2_MODEL_SCHEMA_RELATIVE_PATH,
        "g2_2_fixture_schema": G2_2_FIXTURE_SCHEMA_RELATIVE_PATH,
        "fixture_manifest": FIXTURE_MANIFEST_RELATIVE_PATH,
        "dry_generator": DRY_GENERATOR_RELATIVE_PATH,
    }
    blobs = {name: _git_blob(workspace, path) for name, path in paths.items()}
    source = protocol["source_contracts"]
    required = {
        "g2_1_contract": source["g2_1"]["contract_blob_sha"],
        "g2_1_schema": source["g2_1"]["schema_blob_sha"],
        "g2_2_model": source["g2_2"]["model_blob_sha"],
        "g2_2_model_schema": source["g2_2"]["model_schema_blob_sha"],
        "g2_2_fixture_schema": source["g2_2"]["fixture_schema_blob_sha"],
        "fixture_manifest": source["g2_2"]["fixture_manifest_blob_sha"],
        "dry_generator": EXPECTED_BLOBS["dry_generator"],
    }
    mismatches = {
        name: {"expected": required[name], "observed": blobs[name]}
        for name in required
        if blobs[name] != required[name]
    }
    if mismatches:
        raise ValueError(f"G2.1/G2.2 source continuity failed: {mismatches}")

    for schema_path, instance_path in (
        (G2_1_SCHEMA_RELATIVE_PATH, G2_1_CONTRACT_RELATIVE_PATH),
        (G2_2_MODEL_SCHEMA_RELATIVE_PATH, G2_2_MODEL_RELATIVE_PATH),
    ):
        schema = load_strict_json(workspace.path(schema_path))
        instance = load_strict_json(workspace.path(instance_path))
        errors = _schema_errors(_validator(schema), instance)
        if errors:
            raise ValueError(f"continuity schema validation failed for {instance_path}: {errors}")

    fixture_schema = load_strict_json(workspace.path(G2_2_FIXTURE_SCHEMA_RELATIVE_PATH))
    fixture_validator = _validator(fixture_schema)
    fixtures = _load_fixture_registry(workspace)
    for fixture_id, fixture in fixtures.items():
        errors = _schema_errors(fixture_validator, fixture)
        if errors:
            raise ValueError(f"fixture schema validation failed for {fixture_id}: {errors}")

    fixture_manifest = load_strict_json(workspace.path(FIXTURE_MANIFEST_RELATIVE_PATH))
    stored_digest = fixture_manifest["manifest_digest"]
    detached = dict(fixture_manifest)
    detached["manifest_digest"] = ""
    computed_digest = canonical_digest(detached)
    if computed_digest != stored_digest:
        raise ValueError("fixture manifest detached digest mismatch")
    if stored_digest != source["g2_2"]["fixture_manifest_digest"]:
        raise ValueError("fixture manifest digest drifted from G2.3 protocol")

    return {
        "g2_1": "PASS",
        "g2_2": "PASS",
        "g2_3": "PASS",
        "source_blobs": blobs,
        "fixture_manifest_digest": stored_digest,
        "fixture_count": len(fixtures),
        "frozen_case_count": len(FROZEN_LIFECYCLE_RESULT_DIGESTS),
    }


def _validate_git_identity(
    workspace: ResearchWorkspace,
    *,
    implementation_sha: str,
    base_sha: str,
) -> dict[str, Any]:
    _assert_sha(implementation_sha, "implementation SHA")
    _assert_sha(base_sha, "base SHA")
    head = _git_output(workspace, "rev-parse", "HEAD")
    if head != implementation_sha:
        raise ValueError("implementation SHA does not match current HEAD")
    if base_sha != STARTING_GAMIFICATION_SHA:
        raise ValueError("G2.4 base SHA must be the frozen starting gamification HEAD")
    subprocess.run(
        ["git", "-C", str(workspace.root), "merge-base", "--is-ancestor", base_sha, implementation_sha],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "-C", str(workspace.root), "merge-base", "--is-ancestor", PUBLICATION_SHA, implementation_sha],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "repository": "AliceLiddell01/anki-study-report",
        "target_branch": "gamification",
        "execution_branch": _git_output(workspace, "branch", "--show-current"),
        "base_sha": base_sha,
        "implementation_sha": implementation_sha,
        "protocol_publication_sha": PUBLICATION_SHA,
        "publication_ancestry": "PASS",
    }


def build_learn_screening_manifest(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    repository = _validate_git_identity(
        resolved,
        implementation_sha=implementation_sha,
        base_sha=base_sha,
    )
    protocol, identities = load_and_validate_learn_screening_protocol(resolved)
    if identities["protocol_blob"] != EXPECTED_BLOBS["protocol"]:
        raise ValueError("frozen Learn protocol Git blob drifted")
    if identities["schema_blob"] != EXPECTED_BLOBS["protocol_schema"]:
        raise ValueError("frozen Learn protocol schema Git blob drifted")
    continuity = _validate_source_continuity(resolved, protocol)
    dry_units = [dict(item) for item in generate_dry_units(protocol)]
    expected_ids = [item["unit_id"] for item in dry_units]
    unique_ids = set(expected_ids)
    if len(dry_units) != EXPECTED_UNITS or len(unique_ids) != EXPECTED_UNITS:
        raise ValueError("frozen Learn manifest is not exact 340/340")
    manifest = {
        "manifest_version": "learn-xp-bounded-screening-manifest-v1",
        "repository": repository,
        "protocol": identities,
        "continuity": continuity,
        "dry_generator_blob": _git_blob(resolved, DRY_GENERATOR_RELATIVE_PATH),
        "axes": protocol["matrix_axes"],
        "scenario_registry": protocol["scenario_registry"],
        "expected_units": EXPECTED_UNITS,
        "actual_units": len(dry_units),
        "actual_unique_units": len(unique_ids),
        "missing_units": 0,
        "extra_units": 0,
        "duplicate_units": 0,
        "units": dry_units,
        "manifest_digest": "",
    }
    manifest["manifest_digest"] = canonical_digest(manifest)
    validate_learn_screening_manifest(manifest, protocol=protocol)
    return manifest


def validate_learn_screening_manifest(
    manifest: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
) -> None:
    for name, expected in (
        ("expected_units", EXPECTED_UNITS),
        ("actual_units", EXPECTED_UNITS),
        ("actual_unique_units", EXPECTED_UNITS),
    ):
        if manifest.get(name) != expected:
            raise ValueError(f"Learn manifest {name} drifted")
    if any(manifest.get(name) != 0 for name in ("missing_units", "extra_units", "duplicate_units")):
        raise ValueError("Learn manifest accounting is incomplete")
    units = manifest.get("units")
    if not isinstance(units, list) or len(units) != EXPECTED_UNITS:
        raise ValueError("Learn manifest unit list is invalid")
    expected = [dict(item) for item in generate_dry_units(protocol)]
    if units != expected:
        raise ValueError("Learn manifest units differ from generate_dry_units(protocol)")
    if len({item["unit_id"] for item in units}) != EXPECTED_UNITS:
        raise ValueError("Learn manifest unit IDs are not unique")
    detached = dict(manifest)
    stored = detached["manifest_digest"]
    detached["manifest_digest"] = ""
    if stored != canonical_digest(detached):
        raise ValueError("Learn manifest digest mismatch")


def _event(
    event_id: str,
    sequence_index: int,
    event_kind: str,
    *,
    subject_type: str,
    subject_id: str,
    episode_id: str,
    source_event_id: str | None = None,
    signal_status: str = "NONE",
    continuity_status: str = "STABLE",
    provenance_status: str = "VALID",
    rating: str = "NONE",
    anki_day_index: int = 0,
    monotonic_time_index: int = 0,
    configuration_profile_id: str = "CFG-ONE-STEP",
    session_id: str = "session-account-1",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "sequence_index": sequence_index,
        "event_kind": event_kind,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "episode_id": episode_id,
        "source_event_id": source_event_id,
        "rating": rating,
        "signal_status": signal_status,
        "continuity_status": continuity_status,
        "provenance_status": provenance_status,
        "answer_revealed": False,
        "scheduler_state_before": "NEW",
        "scheduler_state_after": "LEARNING",
        "anki_day_index": anki_day_index,
        "monotonic_time_index": monotonic_time_index,
        "session_id": session_id,
        "preset_id": "preset-account-a",
        "learning_step_profile_id": configuration_profile_id,
    }


def _accounting_trace(
    unit: LearnScreeningUnit,
    delay_policy: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    subject_type = "CARD" if unit.subject_strategy_id == "S-CARD" else "NOTE"
    subject_id = "card-account-1" if subject_type == "CARD" else "note-account-1"
    episode_id = "episode-account-1"
    start = _event(
        "EV-A1",
        1,
        "VALID_INITIAL_ATTEMPT",
        subject_type=subject_type,
        subject_id=subject_id,
        episode_id=episode_id,
        monotonic_time_index=0,
        configuration_profile_id=unit.configuration_profile_id,
    )
    pending = _event(
        "EV-A2",
        2,
        "REQUEST_PENDING",
        subject_type=subject_type,
        subject_id=subject_id,
        episode_id=episode_id,
        monotonic_time_index=1,
        configuration_profile_id=unit.configuration_profile_id,
    )
    scenario = unit.scenario_id
    if scenario == "SCN-ACCOUNT-PENDING-ALLOCATION":
        return (start, pending)
    if scenario in {"SCN-ACCOUNT-CONFIRM-SETTLEMENT", "SCN-ACCOUNT-REFERENCE-ZERO"}:
        minimum_elapsed = int(delay_policy["minimum_elapsed"]) if delay_policy else 1440
        minimum_day = int(delay_policy["minimum_anki_day_delta"]) if delay_policy else 1
        confirm = _event(
            "EV-A3",
            3,
            "INDEPENDENT_RETRIEVAL",
            subject_type=subject_type,
            subject_id=subject_id,
            episode_id=episode_id,
            source_event_id="EV-A2",
            signal_status="INDEPENDENT_SUCCESS",
            rating="GOOD",
            anki_day_index=minimum_day,
            monotonic_time_index=1 + minimum_elapsed,
            configuration_profile_id=unit.configuration_profile_id,
            session_id="session-account-2",
        )
        return (start, pending, confirm)
    if scenario == "SCN-ACCOUNT-EXPIRE-VOID":
        expiry_elapsed = int(delay_policy["expiry_elapsed"]) if delay_policy else 10080
        expiry_day = int(delay_policy["expiry_anki_day_delta"]) if delay_policy else 7
        expire = _event(
            "EV-A3",
            3,
            "EXPIRE_PENDING",
            subject_type=subject_type,
            subject_id=subject_id,
            episode_id=episode_id,
            anki_day_index=expiry_day,
            monotonic_time_index=1 + expiry_elapsed,
            configuration_profile_id=unit.configuration_profile_id,
        )
        return (start, pending, expire)
    if scenario == "SCN-ACCOUNT-CANCEL-VOID":
        cancel = _event(
            "EV-A3",
            3,
            "UNDO_SOURCE",
            subject_type=subject_type,
            subject_id=subject_id,
            episode_id=episode_id,
            source_event_id="EV-A1",
            provenance_status="CANCELLED",
            monotonic_time_index=2,
            configuration_profile_id=unit.configuration_profile_id,
        )
        return (start, pending, cancel)
    if scenario == "SCN-ACCOUNT-INVALIDATE-VOID":
        invalid = _event(
            "EV-A3",
            3,
            "INVALIDATE_CONTINUITY",
            subject_type=subject_type,
            subject_id=subject_id,
            episode_id=episode_id,
            continuity_status="LOST",
            monotonic_time_index=2,
            configuration_profile_id=unit.configuration_profile_id,
        )
        return (start, pending, invalid)
    if scenario == "SCN-ACCOUNT-SUBJECT-COLLISION":
        first_id = "card-collision-a" if unit.subject_strategy_id == "S-CARD" else "card-collision-a"
        second_id = "card-collision-b"
        collision_start = _event(
            "EV-A1",
            1,
            "VALID_INITIAL_ATTEMPT",
            subject_type="CARD",
            subject_id=first_id,
            episode_id=episode_id,
            monotonic_time_index=0,
            configuration_profile_id=unit.configuration_profile_id,
        )
        collision_pending = _event(
            "EV-A2",
            2,
            "REQUEST_PENDING",
            subject_type="CARD",
            subject_id=first_id,
            episode_id=episode_id,
            monotonic_time_index=1,
            configuration_profile_id=unit.configuration_profile_id,
        )
        collision = _event(
            "EV-A3",
            3,
            "VALID_INITIAL_ATTEMPT",
            subject_type="CARD",
            subject_id=second_id,
            episode_id=episode_id,
            monotonic_time_index=2,
            configuration_profile_id=unit.configuration_profile_id,
        )
        return (collision_start, collision_pending, collision)
    raise ValueError(f"unknown accounting scenario: {scenario}")


def _lifecycle_payload(result: LifecycleResult) -> dict[str, Any]:
    return {
        "final_state": result.final_state.value,
        "transition_ledger": [
            {
                "event_id": row.event_id,
                "sequence_index": row.sequence_index,
                "from_state": row.from_state.value,
                "to_state": row.to_state.value,
                "reason_code": row.reason_code.value,
                "subject_key": row.subject_key,
                "episode_id": row.episode_id,
            }
            for row in result.transition_ledger
        ],
        "processed_event_ids": list(result.processed_event_ids),
        "ignored_duplicate_source_ids": list(result.ignored_duplicate_source_ids),
        "subject_key": result.subject_key,
        "episode_id": result.episode_id,
        "canonical_digest": result.canonical_digest,
    }


def _candidate_definition(protocol: Mapping[str, Any], unit: LearnScreeningUnit) -> dict[str, Any]:
    if unit.family_id == REFERENCE_FAMILY_ID:
        return {
            "candidate_or_reference_id": unit.candidate_or_reference_id,
            "family_id": REFERENCE_FAMILY_ID,
            "parameterization_id": REFERENCE_PARAMETERIZATION_ID,
            "subject_strategy_id": unit.subject_strategy_id,
            "delay_policy_id": "D-NONE",
            "pending_share_lru": 0.0,
            "confirmation_settlement_lru": 0.0,
            "delay_policy": None,
        }
    candidate = next(
        item for item in protocol["candidate_registry"]
        if item["candidate_id"] == unit.candidate_or_reference_id
    )
    parameterization = next(
        item for item in protocol["parameterizations"]
        if item["parameterization_id"] == candidate["parameterization_id"]
    )
    delay = next(
        item for item in protocol["delay_policies"]
        if item["delay_policy_id"] == candidate["delay_policy_id"]
    )
    return {
        "candidate_or_reference_id": candidate["candidate_id"],
        "family_id": candidate["family_id"],
        "parameterization_id": candidate["parameterization_id"],
        "subject_strategy_id": candidate["subject_strategy_id"],
        "delay_policy_id": candidate["delay_policy_id"],
        "pending_share_lru": parameterization["pending_share_lru"],
        "confirmation_settlement_lru": parameterization["confirmation_settlement_lru"],
        "delay_policy": delay,
    }


def _case_evidence(
    *,
    unit: LearnScreeningUnit,
    case_id: str,
    role: str,
    events: Sequence[Mapping[str, Any]],
    expected: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
    frozen_fixture: bool,
) -> dict[str, Any]:
    lifecycle = evaluate_lifecycle(events)
    expected_digest = (
        FROZEN_LIFECYCLE_RESULT_DIGESTS.get(f"{unit.scenario_id}::{case_id}")
        if frozen_fixture
        else None
    )
    if frozen_fixture:
        if expected_digest is None or lifecycle.canonical_digest != expected_digest:
            raise ValueError(f"frozen lifecycle digest drift: {unit.scenario_id}::{case_id}")
        if expected is None:
            raise ValueError("frozen fixture expected evidence is missing")
        observed_trace = [
            {
                "from_state": row.from_state.value,
                "to_state": row.to_state.value,
                "reason_code": row.reason_code.value,
            }
            for row in lifecycle.transition_ledger
        ]
        if observed_trace != expected["expected_trace"]:
            raise ValueError(f"frozen lifecycle trace drift: {unit.scenario_id}::{case_id}")
        if lifecycle.final_state.value != expected["expected_final_state"]:
            raise ValueError(f"frozen lifecycle final-state drift: {unit.scenario_id}::{case_id}")

    allocation = evaluate_allocation(
        candidate_or_reference_id=candidate["candidate_or_reference_id"],
        family_id=candidate["family_id"],
        parameterization_id=candidate["parameterization_id"],
        subject_strategy_id=candidate["subject_strategy_id"],
        delay_policy_id=candidate["delay_policy_id"],
        pending_share_lru=candidate["pending_share_lru"],
        confirmation_settlement_lru=candidate["confirmation_settlement_lru"],
        events=events,
        lifecycle=lifecycle,
        delay_policy=candidate["delay_policy"],
    )
    allocation_payload = dataclass_to_dict(allocation)
    result = {
        "case_id": case_id,
        "role": role,
        "events": [dict(event) for event in events],
        "expected_lifecycle_digest": expected_digest,
        "lifecycle": _lifecycle_payload(lifecycle),
        "allocation": allocation_payload,
        "case_digest": "",
    }
    result["case_digest"] = canonical_digest(result)
    return result


def _exposure(case: Mapping[str, Any]) -> float:
    allocation = case["allocation"]
    provisional = float(allocation["provisional_created_lru"])
    if provisional == 0.0:
        return 0.0
    events = case["events"]
    pending_event_ids = {
        row["event_id"]
        for row in case["lifecycle"]["transition_ledger"]
        if row["reason_code"] == "PENDING_CREATED"
    }
    pending = next((event for event in events if event["event_id"] in pending_event_ids), None)
    if pending is None or pending["monotonic_time_index"] is None:
        return 0.0
    end = events[-1]["monotonic_time_index"]
    if end is None:
        return 0.0
    return provisional * max(0, end - pending["monotonic_time_index"])


def _comparison_gain(cases: Sequence[Mapping[str, Any]]) -> float:
    control = next((item for item in cases if item["role"] == "CONTROL"), None)
    attack = next((item for item in cases if item["role"] == "ATTACK"), None)
    if control is None or attack is None:
        return 0.0
    return max(
        0.0,
        float(attack["allocation"]["current_total_lru"])
        - float(control["allocation"]["current_total_lru"]),
    )


def _unit_metric_contributions(
    unit: LearnScreeningUnit,
    cases: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    provisional = sum(float(case["allocation"]["provisional_created_lru"]) for case in cases)
    confirmed = sum(float(case["allocation"]["settled_total_lru"]) for case in cases)
    confirmed_cases = [
        case for case in cases
        if case["allocation"]["terminal_disposition"] == "CONFIRMED_SETTLED"
    ]
    terminal_cases = [
        case for case in cases
        if case["lifecycle"]["final_state"] in {"CONFIRMED", "EXPIRED", "CANCELLED", "INVALIDATED"}
    ]
    confirmation_times = [
        case["allocation"]["delay"]["elapsed_minutes"]
        for case in confirmed_cases
        if case["allocation"]["delay"]["elapsed_minutes"] is not None
    ]
    scenario_gain = _comparison_gain(cases)
    duplicate_gain = scenario_gain if unit.scenario_id in {
        "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE",
        "FIX-TERM-DUPLICATE-REPLAY",
        "FIX-REPETITION-AGAIN-GOOD-LOOP",
    } else 0.0
    step_gain = scenario_gain if unit.scenario_id in {
        "FIX-CONFIG-STEPS-EQUIVALENCE",
        "FIX-INV-CONFIG-PROFILE-EQUIVALENCE",
    } else 0.0
    reset_gain = scenario_gain if unit.scenario_id == "FIX-LIFECYCLE-RESET-REIMPORT" else 0.0
    session_gain = scenario_gain if unit.scenario_id in {
        "FIX-INV-SESSION-REGROUPING",
        "FIX-SESSION-DAY-CLOCK-INVARIANCE",
        "FIX-CONFIG-STEPS-EQUIVALENCE",
        "FIX-INV-CONFIG-PROFILE-EQUIVALENCE",
    } else 0.0
    subject_collision = 0.0
    if unit.scenario_id in {
        "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE",
        "SCN-ACCOUNT-SUBJECT-COLLISION",
    }:
        subject_collision = float(
            max(
                (case["allocation"]["subject"]["collision_fragmentation_count"] for case in cases),
                default=0,
            )
        )
    active_peak = max(
        (1 if float(case["allocation"]["pending_lru"]) > 0.0 else 0 for case in cases),
        default=0,
    )
    invalid_retained = sum(
        float(case["allocation"]["current_total_lru"])
        for case in cases
        if case["lifecycle"]["final_state"] in {"EXPIRED", "CANCELLED", "INVALIDATED"}
    )
    return {
        "M-PROVISIONAL-ALLOCATION": provisional,
        "M-CONFIRMED-ALLOCATION": confirmed,
        "M-UNCONFIRMED-PROVISIONAL-EXPOSURE": sum(_exposure(case) for case in cases),
        "M-CONFIRMATION-RATE": float(len(confirmed_cases)),
        "M-TERMINAL-RATE": float(len(terminal_cases)),
        "M-TIME-TO-CONFIRMATION": float(sum(confirmation_times)),
        "M-DUPLICATE-GAIN": duplicate_gain,
        "M-STEP-COUNT-GAIN": step_gain,
        "M-RESET-REIMPORT-GAIN": reset_gain,
        "M-SESSION-CONFIG-GAIN": session_gain,
        "M-SUBJECT-COLLISION-FRAGMENTATION": subject_collision,
        "M-ACTIVE-PENDING-PEAK": float(active_peak),
        "M-INVALID-TERMINAL-RETAINED-LRU": invalid_retained,
        "M-EXPLANATION-COMPLEXITY-FIELDS": 0.0,
    }


def run_learn_screening_unit(
    unit: LearnScreeningUnit,
    *,
    protocol: Mapping[str, Any],
    fixtures: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate = _candidate_definition(protocol, unit)
    scenario = next(
        item for item in protocol["scenario_registry"]
        if item["scenario_id"] == unit.scenario_id
    )
    cases: list[dict[str, Any]] = []
    if scenario["scenario_kind"] == "FROZEN_LIFECYCLE_FIXTURE":
        fixture = fixtures[scenario["source_fixture_id"]]
        for case in fixture["cases"]:
            cases.append(
                _case_evidence(
                    unit=unit,
                    case_id=case["case_id"],
                    role=case["role"],
                    events=case["events"],
                    expected=case["expected"],
                    candidate=candidate,
                    frozen_fixture=True,
                )
            )
        mapping = "EXACT_FROZEN_FIXTURE_UNMODIFIED"
    elif scenario["scenario_kind"] == "CANDIDATE_ACCOUNTING":
        events = _accounting_trace(unit, candidate["delay_policy"])
        cases.append(
            _case_evidence(
                unit=unit,
                case_id=unit.scenario_id + "-CASE",
                role="ORDINARY",
                events=events,
                expected=None,
                candidate=candidate,
                frozen_fixture=False,
            )
        )
        mapping = "EXPLICIT_PRE_RESULTS_ACCOUNTING_TRACE_V1"
    else:
        raise ValueError(f"unknown Learn scenario kind: {scenario['scenario_kind']}")

    payload = {
        **unit.payload(),
        "scenario_kind": scenario["scenario_kind"],
        "execution_mapping": mapping,
        "case_evidence": cases,
        "metric_contributions": _unit_metric_contributions(unit, cases),
        "errors": [],
        "warnings": [],
        "unit_digest": "",
    }
    payload["unit_digest"] = canonical_digest(payload)
    return payload


def _complexity(candidate: Mapping[str, Any]) -> float:
    value = 4.0
    if candidate["family_id"] == "F-PENDING-CONFIRMED-SPLIT":
        value += 2.0
    if candidate["subject_strategy_id"] == "S-NOTE-SIBLING":
        value += 1.0
    return value


def _aggregate_metrics(
    candidate: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    metric_registry: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sums = {item["metric_id"]: 0.0 for item in metric_registry}
    confirmation_numerator = 0.0
    terminal_numerator = 0.0
    case_count = 0
    for row in rows:
        contributions = row["metric_contributions"]
        for metric_id in sums:
            if metric_id in {
                "M-CONFIRMATION-RATE",
                "M-TERMINAL-RATE",
                "M-TIME-TO-CONFIRMATION",
                "M-ACTIVE-PENDING-PEAK",
                "M-EXPLANATION-COMPLEXITY-FIELDS",
            }:
                continue
            sums[metric_id] += float(contributions[metric_id])
        confirmation_numerator += float(contributions["M-CONFIRMATION-RATE"])
        terminal_numerator += float(contributions["M-TERMINAL-RATE"])
        case_count += len(row["case_evidence"])
        if float(contributions["M-TIME-TO-CONFIRMATION"]) > 0.0:
            sums["M-TIME-TO-CONFIRMATION"] += float(contributions["M-TIME-TO-CONFIRMATION"])
        sums["M-ACTIVE-PENDING-PEAK"] = max(
            sums["M-ACTIVE-PENDING-PEAK"],
            float(contributions["M-ACTIVE-PENDING-PEAK"]),
        )
    sums["M-CONFIRMATION-RATE"] = 0.0 if case_count == 0 else confirmation_numerator / case_count
    sums["M-TERMINAL-RATE"] = 0.0 if case_count == 0 else terminal_numerator / case_count
    sums["M-TIME-TO-CONFIRMATION"] = (
        0.0
        if confirmation_numerator == 0.0
        else sums["M-TIME-TO-CONFIRMATION"] / confirmation_numerator
    )
    sums["M-EXPLANATION-COMPLEXITY-FIELDS"] = _complexity(candidate)
    return [
        {
            "metric_id": item["metric_id"],
            "selection_role": item["selection_role"],
            "unit": item["unit"],
            "value": sums[item["metric_id"]],
        }
        for item in metric_registry
    ]


def _all_cases(rows: Sequence[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for row in rows:
        yield from row["case_evidence"]


def _scenario_rows(rows: Sequence[Mapping[str, Any]], scenario_id: str) -> list[Mapping[str, Any]]:
    return [row for row in rows if row["scenario_id"] == scenario_id]


def _scenario_gain(rows: Sequence[Mapping[str, Any]], scenario_id: str) -> float:
    return max(
        (_comparison_gain(row["case_evidence"]) for row in _scenario_rows(rows, scenario_id)),
        default=0.0,
    )


def _gate(
    gate: Mapping[str, Any],
    passed: bool,
    observed: Any,
    evidence_references: Sequence[str],
    *,
    scope: str,
    missing_data: bool = False,
) -> dict[str, Any]:
    return {
        "gate_id": gate["gate_id"],
        "scope": scope,
        "predicate_inputs": observed,
        "operator": "FROZEN_BOOLEAN_PREDICATE",
        "pass": bool(passed) and not missing_data,
        "missing_data": missing_data,
        "failure_reason": None if passed and not missing_data else gate["claim"],
        "evidence_references": list(evidence_references),
    }


def _candidate_gates(
    candidate: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    metrics: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
    shared: Mapping[str, Any],
) -> list[dict[str, Any]]:
    metric = {item["metric_id"]: item["value"] for item in metrics}
    cases = list(_all_cases(rows))
    max_total = max((float(case["allocation"]["current_total_lru"]) for case in cases), default=2.0)
    min_total = min((float(case["allocation"]["current_total_lru"]) for case in cases), default=-1.0)
    pending_creation_max = max((int(case["allocation"]["pending_creation_count"]) for case in cases), default=2)
    spendable_any = any(bool(case["allocation"]["spendable"]) for case in cases)
    terminal_retained = metric["M-INVALID-TERMINAL-RETAINED-LRU"]
    deterministic = all(
        row["unit_digest"] == canonical_digest({**row, "unit_digest": ""})
        for row in rows
    )
    independent = all(
        not (
            case["allocation"]["terminal_disposition"] == "CONFIRMED_SETTLED"
            and not case["allocation"]["delay"]["confirmation_eligible"]
        )
        for case in cases
    )
    reference_by_gate = {
        "GATE-G2-1-CONTINUITY": (shared["continuity"]["g2_1"] == "PASS", shared["continuity"]),
        "GATE-G2-2-CONTINUITY": (shared["continuity"]["g2_2"] == "PASS", shared["continuity"]),
        "GATE-LIFECYCLE-DIGEST-PARITY": (shared["lifecycle_digest_parity"] == "PASS", shared["lifecycle_digest_parity"]),
        "GATE-STRICT-EVENT-TYPES": (shared["strict_event_types"] == "PASS", shared["strict_event_types"]),
        "GATE-NO-STEP-COUNT-GAIN": (metric["M-STEP-COUNT-GAIN"] == 0.0, metric["M-STEP-COUNT-GAIN"]),
        "GATE-NO-AGAIN-FARMING": (_scenario_gain(rows, "FIX-REPETITION-AGAIN-GOOD-LOOP") == 0.0, _scenario_gain(rows, "FIX-REPETITION-AGAIN-GOOD-LOOP")),
        "GATE-NO-HARD-MISREPORT-ADVANTAGE": (_scenario_gain(rows, "FIX-ANSWER-RATING-REVEAL-NEUTRALITY") == 0.0, _scenario_gain(rows, "FIX-ANSWER-RATING-REVEAL-NEUTRALITY")),
        "GATE-NO-RESET-FARMING": (_scenario_gain(rows, "FIX-LIFECYCLE-RESET-REIMPORT") == 0.0, _scenario_gain(rows, "FIX-LIFECYCLE-RESET-REIMPORT")),
        "GATE-NO-REIMPORT-FARMING": (_scenario_gain(rows, "FIX-LIFECYCLE-RESET-REIMPORT") == 0.0, _scenario_gain(rows, "FIX-LIFECYCLE-RESET-REIMPORT")),
        "GATE-NO-DUPLICATE-OBJECT-GAIN": (metric["M-DUPLICATE-GAIN"] == 0.0, metric["M-DUPLICATE-GAIN"]),
        "GATE-NO-SIBLING-TEMPLATE-GAIN": (_scenario_gain(rows, "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE") == 0.0, _scenario_gain(rows, "FIX-OBJECT-DUPLICATE-REVERSE-CLOZE")),
        "GATE-SESSION-TIME-INVARIANCE": (_scenario_gain(rows, "FIX-SESSION-DAY-CLOCK-INVARIANCE") == 0.0 and _scenario_gain(rows, "FIX-INV-SESSION-REGROUPING") == 0.0, metric["M-SESSION-CONFIG-GAIN"]),
        "GATE-CONFIGURATION-INVARIANCE": (metric["M-STEP-COUNT-GAIN"] == 0.0, metric["M-STEP-COUNT-GAIN"]),
        "GATE-INDEPENDENT-CONFIRMATION": (independent, independent),
        "GATE-PENDING-IDEMPOTENT": (pending_creation_max <= 1, pending_creation_max),
        "GATE-PENDING-NON-SPENDABLE": (not spendable_any, spendable_any),
        "GATE-TOTAL-REWARD-CAP": (min_total >= 0.0 and max_total <= 1.0, {"minimum": min_total, "maximum": max_total}),
        "GATE-TERMINAL-DISPOSITION": (terminal_retained == 0.0, terminal_retained),
        "GATE-DETERMINISTIC-REPLAY": (deterministic and shared["replay"]["pass"], shared["replay"]),
        "GATE-EVIDENCE-COMPLETENESS": (len(rows) == 34 and not any(row["errors"] for row in rows), {"units": len(rows)}),
        "GATE-RESEARCH-ONLY": (shared["research_only"] == "PASS", shared["research_only"]),
        "GATE-NO-REAL-USER-DATA": (shared["privacy"] == "PASS", shared["privacy"]),
        "GATE-NO-PRODUCTION-APPROVAL": (shared["production_boundary"] == "PASS", shared["production_boundary"]),
    }
    repository_scope = {
        "GATE-G2-1-CONTINUITY",
        "GATE-G2-2-CONTINUITY",
        "GATE-LIFECYCLE-DIGEST-PARITY",
        "GATE-STRICT-EVENT-TYPES",
        "GATE-RESEARCH-ONLY",
        "GATE-NO-REAL-USER-DATA",
        "GATE-NO-PRODUCTION-APPROVAL",
    }
    scenario_scope = {
        "GATE-NO-STEP-COUNT-GAIN",
        "GATE-NO-AGAIN-FARMING",
        "GATE-NO-HARD-MISREPORT-ADVANTAGE",
        "GATE-NO-RESET-FARMING",
        "GATE-NO-REIMPORT-FARMING",
        "GATE-NO-DUPLICATE-OBJECT-GAIN",
        "GATE-NO-SIBLING-TEMPLATE-GAIN",
        "GATE-SESSION-TIME-INVARIANCE",
        "GATE-CONFIGURATION-INVARIANCE",
        "GATE-INDEPENDENT-CONFIRMATION",
    }
    family_prerequisite_scope = {
        "GATE-DETERMINISTIC-REPLAY",
        "GATE-EVIDENCE-COMPLETENESS",
    }
    result = []
    for gate in protocol["hard_gates"]:
        gate_id = gate["gate_id"]
        passed, observed = reference_by_gate[gate_id]
        scope = (
            "REPOSITORY_PROTOCOL_CONTINUITY"
            if gate_id in repository_scope
            else "UNIT_SCENARIO"
            if gate_id in scenario_scope
            else "FAMILY_SELECTION_PREREQUISITE"
            if gate_id in family_prerequisite_scope
            else "CANDIDATE_AGGREGATE"
        )
        result.append(
            _gate(
                gate,
                passed,
                observed,
                [row["unit_id"] for row in rows],
                scope=scope,
            )
        )
    return result


def _lexicographic_vector(
    metrics: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    values = {item["metric_id"]: item["value"] for item in metrics}
    return [
        {"metric_id": metric_id, "value": values[metric_id]}
        for metric_id in protocol["family_survivor_policy"]["lexicographic_metric_ids"]
    ]


def aggregate_learn_screening(
    units: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any],
    protocol: Mapping[str, Any],
    shared: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if len(units) != EXPECTED_UNITS:
        raise ValueError("Learn evidence must contain exactly 340 units")
    by_identity: dict[str, list[Mapping[str, Any]]] = {}
    for row in units:
        by_identity.setdefault(row["candidate_or_reference_id"], []).append(row)
    expected_identities = protocol["matrix_axes"]["candidate_or_reference_identity"]
    if set(by_identity) != set(expected_identities):
        raise ValueError("Learn candidate/reference evidence coverage is incomplete")

    candidates: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for identity in expected_identities:
        rows = sorted(by_identity[identity], key=lambda item: item["unit_id"])
        if len(rows) != 34:
            raise ValueError(f"identity {identity} must have exactly 34 units")
        candidate = _candidate_definition(protocol, LearnScreeningUnit.from_mapping(rows[0]))
        metrics = _aggregate_metrics(candidate, rows, protocol["descriptive_metrics"])
        gates = _candidate_gates(candidate, rows, metrics, protocol, shared)
        all_pass = all(item["pass"] for item in gates)
        first_failure = next((item["gate_id"] for item in gates if not item["pass"]), None)
        item = {
            "candidate_or_reference_id": identity,
            "family_id": candidate["family_id"],
            "parameterization_id": candidate["parameterization_id"],
            "subject_strategy_id": candidate["subject_strategy_id"],
            "delay_policy_id": candidate["delay_policy_id"],
            "complete_units": len(rows),
            "gates": gates,
            "metrics": metrics,
            "first_failing_gate": first_failure,
            "screening_status": "REFERENCE_ONLY" if candidate["family_id"] == REFERENCE_FAMILY_ID else ("SCREENING_ELIGIBLE" if all_pass else "SCREENING_NOT_ELIGIBLE"),
            "eligibility_reason": "REFERENCE_EXCLUDED" if candidate["family_id"] == REFERENCE_FAMILY_ID else ("ALL_HARD_GATES_PASS" if all_pass else f"FAILED_{first_failure}"),
            "lexicographic_vector": [] if candidate["family_id"] == REFERENCE_FAMILY_ID else _lexicographic_vector(metrics, protocol),
            "survivor_selected": False,
        }
        if candidate["family_id"] == REFERENCE_FAMILY_ID:
            if any(
                float(case["allocation"]["current_total_lru"]) != 0.0
                for row in rows for case in row["case_evidence"]
            ):
                raise ValueError("reference allocation drifted from zero")
            references.append(item)
        else:
            candidates.append(item)

    families: list[dict[str, Any]] = []
    for family in protocol["families"]:
        family_candidates = [item for item in candidates if item["family_id"] == family["family_id"]]
        eligible = [item for item in family_candidates if item["screening_status"] == "SCREENING_ELIGIBLE"]
        survivor: str | None = None
        outcome = "NO_SURVIVOR"
        comparison: list[dict[str, Any]] = []
        if len(eligible) == 1:
            survivor = eligible[0]["candidate_or_reference_id"]
            outcome = "SURVIVOR_SELECTED"
        elif len(eligible) > 1:
            vectors = {
                item["candidate_or_reference_id"]: tuple(row["value"] for row in item["lexicographic_vector"])
                for item in eligible
            }
            minimum = min(vectors.values())
            winners = sorted(identity for identity, vector in vectors.items() if vector == minimum)
            comparison = [
                {"candidate_id": identity, "vector": list(vectors[identity])}
                for identity in sorted(vectors)
            ]
            if len(winners) == 1:
                survivor = winners[0]
                outcome = "SURVIVOR_SELECTED"
            else:
                outcome = "FAMILY_INCONCLUSIVE"
                for item in candidates:
                    if item["candidate_or_reference_id"] in winners:
                        item["screening_status"] = "SCREENING_INCONCLUSIVE"
                        item["eligibility_reason"] = "EXACT_LEXICOGRAPHIC_TIE"
        if survivor is not None:
            next(item for item in candidates if item["candidate_or_reference_id"] == survivor)["survivor_selected"] = True
        families.append(
            {
                "family_id": family["family_id"],
                "eligible_candidates": sorted(item["candidate_or_reference_id"] for item in eligible),
                "lexicographic_comparison": comparison,
                "survivor": survivor,
                "family_outcome": outcome,
                "tie": outcome == "FAMILY_INCONCLUSIVE",
            }
        )
    if any(sum(1 for item in candidates if item["family_id"] == family["family_id"] and item["survivor_selected"]) > 1 for family in protocol["families"]):
        raise ValueError("more than one survivor selected in a Learn family")
    return candidates, references, families


def _strict_event_type_probe() -> str:
    bad = {
        "event_id": "EV-X",
        "sequence_index": "1",
        "event_kind": "VALID_INITIAL_ATTEMPT",
        "subject_type": "CARD",
        "subject_id": "card-x",
        "episode_id": "episode-x",
    }
    try:
        evaluate_lifecycle([bad])
    except Exception:
        return "PASS"
    return "FAIL"


def _research_only_probe(workspace: ResearchWorkspace) -> str:
    forbidden_roots = {"anki_study_report", "aqt", "anki", "sqlite3", "requests", "httpx"}
    for path in (
        Path("src/gamification_sim/learn_bounded_screening.py"),
        Path("src/gamification_sim/learn_reward_allocation.py"),
    ):
        tree = ast.parse(workspace.path(path).read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            modules: tuple[str, ...]
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = (node.module,)
            else:
                continue
            if any(module.split(".", 1)[0] in forbidden_roots for module in modules):
                return "FAIL"
    return "PASS"


def _privacy_probe(value: Any) -> str:
    forbidden_keys = {
        "real_card_text", "note_fields", "media", "profile_path", "profile_paths",
        "username", "usernames", "token", "tokens", "raw_revlog", "private_absolute_path",
    }
    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            if set(node).intersection(forbidden_keys):
                return False
            return all(walk(item) for item in node.values())
        if isinstance(node, list):
            return all(walk(item) for item in node)
        if isinstance(node, str):
            return not node.startswith(("/home/", "/mnt/c/Users/", "C:\\Users\\"))
        return True
    return "PASS" if walk(value) else "FAIL"


def _execute_units(
    manifest: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    fixtures: Mapping[str, Mapping[str, Any]],
    reverse: bool = False,
) -> list[dict[str, Any]]:
    definitions = list(manifest["units"])
    if reverse:
        definitions.reverse()
    rows = [
        run_learn_screening_unit(
            LearnScreeningUnit.from_mapping(item),
            protocol=protocol,
            fixtures=fixtures,
        )
        for item in definitions
    ]
    return sorted(rows, key=lambda item: item["unit_id"])


def _build_shared_evidence(
    workspace: ResearchWorkspace,
    *,
    manifest: Mapping[str, Any],
    units: Sequence[Mapping[str, Any]],
    replay_units: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    primary_digest = canonical_digest(units)
    replay_digest = canonical_digest(replay_units)
    shared = {
        "continuity": manifest["continuity"],
        "lifecycle_digest_parity": "PASS",
        "strict_event_types": _strict_event_type_probe(),
        "replay": {
            "primary_digest": primary_digest,
            "replay_digest": replay_digest,
            "pass": units == replay_units and primary_digest == replay_digest,
            "execution_order_independent": True,
        },
        "research_only": _research_only_probe(workspace),
        "privacy": "PENDING",
        "production_boundary": "PASS",
    }
    shared["privacy"] = _privacy_probe({"manifest": manifest, "units": units})
    return shared


def run_learn_xp_screening(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
    exact_command: str,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, _ = load_and_validate_learn_screening_protocol(resolved)
    manifest = build_learn_screening_manifest(
        resolved,
        implementation_sha=implementation_sha,
        base_sha=base_sha,
    )
    fixtures = _load_fixture_registry(resolved)
    units = _execute_units(manifest, protocol=protocol, fixtures=fixtures)
    replay_units = _execute_units(manifest, protocol=protocol, fixtures=fixtures, reverse=True)
    shared = _build_shared_evidence(
        resolved,
        manifest=manifest,
        units=units,
        replay_units=replay_units,
    )
    candidates, references, families = aggregate_learn_screening(
        units,
        manifest=manifest,
        protocol=protocol,
        shared=shared,
    )
    commit_timestamp = _git_output(resolved, "show", "-s", "--format=%cI", implementation_sha)
    payload = {
        "evidence_version": "learn-xp-bounded-screening-evidence-v1",
        "provenance": {
            "repository": "AliceLiddell01/anki-study-report",
            "target_branch": "gamification",
            "base_sha": base_sha,
            "implementation_sha": implementation_sha,
            "protocol_publication_sha": PUBLICATION_SHA,
            "execution_branch": manifest["repository"]["execution_branch"],
            "python_version": sys.version.split()[0],
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "implementation_commit_timestamp_utc": commit_timestamp,
            "exact_command": exact_command,
        },
        "manifest": manifest,
        "shared_evidence": shared,
        "units": units,
        "candidates": candidates,
        "references": references,
        "families": families,
        "amendments": {
            "results_viewed_before_implementation_publication": False,
            "substantive_amendments": [],
            "execution_mapping": "EXPLICIT_PRE_RESULTS_ACCOUNTING_TRACE_V1",
        },
        "boundaries": {
            "adaptive_units": 0,
            "rescue_sweep": False,
            "cross_family_ranking": False,
            "final_model_selected": False,
            "production_approved": False,
            "production_integration": False,
            "g2_5_started": False,
        },
        "evidence_digest": "",
    }
    payload["evidence_digest"] = canonical_digest(payload)
    validate_learn_xp_screening_evidence(payload, workspace=resolved)
    return payload


def _finite_walk(value: Any) -> None:
    if isinstance(value, float) and not (value == value and value not in {float("inf"), float("-inf")}):
        raise ValueError("evidence contains NaN or Infinity")
    if isinstance(value, dict):
        for item in value.values():
            _finite_walk(item)
    elif isinstance(value, list):
        for item in value:
            _finite_walk(item)


def validate_learn_xp_screening_evidence(
    payload: Mapping[str, Any],
    *,
    workspace: ResearchWorkspace | Path | str | None,
) -> None:
    resolved = resolve_research_workspace(workspace)
    schema = load_strict_json(resolved.path(EVIDENCE_SCHEMA_RELATIVE_PATH))
    errors = _schema_errors(_validator(schema), payload)
    if errors:
        raise ValueError("Learn screening evidence schema validation failed: " + "; ".join(errors[:20]))
    _finite_walk(payload)
    protocol, _ = load_and_validate_learn_screening_protocol(resolved)
    provenance = payload["provenance"]
    recomputed_manifest = build_learn_screening_manifest(
        resolved,
        implementation_sha=provenance["implementation_sha"],
        base_sha=provenance["base_sha"],
    )
    if payload["manifest"] != recomputed_manifest:
        raise ValueError("Learn screening manifest mismatch under detached recomputation")
    expected_units = sorted(
        (dict(item) for item in generate_dry_units(protocol)),
        key=lambda item: item["unit_id"],
    )
    stored_definitions = [
        {key: item[key] for key in expected_units[0]}
        for item in payload["units"]
    ]
    if stored_definitions != expected_units:
        raise ValueError("stored Learn evidence unit definitions drifted")
    fixtures = _load_fixture_registry(resolved)
    recomputed_units = [
        run_learn_screening_unit(
            LearnScreeningUnit.from_mapping(item),
            protocol=protocol,
            fixtures=fixtures,
        )
        for item in payload["manifest"]["units"]
    ]
    recomputed_units.sort(key=lambda item: item["unit_id"])
    if payload["units"] != recomputed_units:
        raise ValueError("Learn unit evidence mismatch under detached recomputation")
    replay_units = _execute_units(
        recomputed_manifest,
        protocol=protocol,
        fixtures=fixtures,
        reverse=True,
    )
    recomputed_shared = _build_shared_evidence(
        resolved,
        manifest=recomputed_manifest,
        units=recomputed_units,
        replay_units=replay_units,
    )
    if payload["shared_evidence"] != recomputed_shared:
        raise ValueError("Learn shared gate evidence mismatch under detached recomputation")
    candidates, references, families = aggregate_learn_screening(
        recomputed_units,
        manifest=recomputed_manifest,
        protocol=protocol,
        shared=recomputed_shared,
    )
    if payload["candidates"] != candidates:
        raise ValueError("Learn candidate aggregates mismatch")
    if payload["references"] != references:
        raise ValueError("Learn reference aggregates mismatch")
    if payload["families"] != families:
        raise ValueError("Learn family outcomes mismatch")
    detached = dict(payload)
    stored = detached["evidence_digest"]
    detached["evidence_digest"] = ""
    if stored != canonical_digest(detached):
        raise ValueError("Learn evidence digest mismatch")
    if _privacy_probe(payload) != "PASS":
        raise ValueError("Learn evidence contains private or forbidden fields")


def load_and_validate_learn_xp_screening_evidence(
    path: Path,
    *,
    workspace: ResearchWorkspace | Path | str | None,
) -> dict[str, Any]:
    payload = load_strict_json(path, max_bytes=MAX_EVIDENCE_BYTES)
    if not isinstance(payload, dict):
        raise ValueError("Learn screening evidence must be an object")
    validate_learn_xp_screening_evidence(payload, workspace=workspace)
    return payload


def render_learn_xp_screening_summary(payload: Mapping[str, Any]) -> str:
    manifest = payload["manifest"]
    lines = [
        "# G2.4 Learn XP bounded screening",
        "",
        f"- Implementation SHA: `{payload['provenance']['implementation_sha']}`",
        f"- Expected / actual / unique: **{manifest['expected_units']} / {manifest['actual_units']} / {manifest['actual_unique_units']}**",
        f"- Missing / extra / duplicates: **{manifest['missing_units']} / {manifest['extra_units']} / {manifest['duplicate_units']}**",
        f"- Manifest digest: `{manifest['manifest_digest']}`",
        f"- Evidence digest: `{payload['evidence_digest']}`",
        "",
        "| Candidate | Status | First failing gate | Survivor |",
        "|---|---|---|---|",
    ]
    for item in payload["candidates"]:
        lines.append(
            f"| `{item['candidate_or_reference_id']}` | `{item['screening_status']}` | "
            f"`{item['first_failing_gate'] or '-'}` | `{'YES' if item['survivor_selected'] else 'NO'}` |"
        )
    lines.extend(["", "| Family | Outcome | Survivor |", "|---|---|---|"])
    for item in payload["families"]:
        lines.append(
            f"| `{item['family_id']}` | `{item['family_outcome']}` | `{item['survivor'] or 'NONE'}` |"
        )
    lines.extend(
        [
            "",
            "No cross-family ranking was performed. No final model or production integration was approved.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _deterministic_tar_gz(source_dir: Path, archive_path: Path) -> None:
    with archive_path.open("wb") as raw:
        with GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for path in sorted(source_dir.iterdir(), key=lambda item: item.name):
                    info = archive.gettarinfo(str(path), arcname=path.name)
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)


def write_learn_xp_screening_bundle(
    payload: Mapping[str, Any],
    output_root: Path,
) -> tuple[Path, Path]:
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("Learn screening output root must not be a symlink")
    implementation_short = str(payload["provenance"]["implementation_sha"])[:12]
    run_dir = output_root.resolve() / f"learn-xp-g2-4-evidence-{implementation_short}"
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError("Learn screening output directory already contains files")
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("Learn screening output directory must not be a symlink")
    _write_json(run_dir / "manifest.json", payload["manifest"])
    _write_json(run_dir / "evidence.json", payload)
    (run_dir / "summary.md").write_text(render_learn_xp_screening_summary(payload), encoding="utf-8")
    environment = {
        "python_version": payload["provenance"]["python_version"],
        "jsonschema_version": payload["provenance"]["jsonschema_version"],
        "platform_system": payload["provenance"]["platform_system"],
        "platform_machine": payload["provenance"]["platform_machine"],
        "written_at_utc": payload["provenance"]["implementation_commit_timestamp_utc"],
    }
    _write_json(run_dir / "environment.json", environment)
    (run_dir / "command.txt").write_text(str(payload["provenance"]["exact_command"]) + "\n", encoding="utf-8")
    inventory = []
    for name in ("command.txt", "environment.json", "evidence.json", "manifest.json", "summary.md"):
        path = run_dir / name
        inventory.append(f"{_file_sha(path)}  {name}")
    (run_dir / "FILES.sha256").write_text("\n".join(inventory) + "\n", encoding="utf-8")
    archive_path = output_root.resolve() / f"learn-xp-g2-4-evidence-{implementation_short}.tar.gz"
    if archive_path.exists():
        raise ValueError("Learn screening archive already exists")
    _deterministic_tar_gz(run_dir, archive_path)
    return run_dir, archive_path
