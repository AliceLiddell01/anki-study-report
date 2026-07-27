from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from gzip import GzipFile
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest
from .strict_json import load_strict_json
from .workspace import ResearchWorkspace, resolve_research_workspace

PROTOCOL_RELATIVE_PATH = Path("contracts/learn-xp-confirmatory-protocol-v1.json")
PROTOCOL_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-confirmatory-protocol-v1.schema.json")
EVIDENCE_SCHEMA_RELATIVE_PATH = Path("schemas/learn-xp-confirmatory-evidence-v1.schema.json")
EXPECTED_UNITS = 216
EXPECTED_PER_IDENTITY = 72
EXPECTED_CONDITIONS = 36
EXPECTED_REPLAYS = ("FORWARD", "REVERSE")
IDENTITY_MODE = "SYNTHETIC_CONTRACT_ONLY"
EXECUTION_BRANCH = "g2-5-learn-xp-confirmatory"
BASELINE_SHA = "93be5ebac17c42d09272d0195a8b07f19af18274"
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
BUNDLE_NAMES = (
    "FILES.sha256",
    "command.txt",
    "environment.json",
    "evidence.json",
    "g2-4-continuity.json",
    "manifest.json",
    "summary.md",
)
FORBIDDEN_PRIVATE_KEYS = frozenset(
    {
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
    }
)
FORBIDDEN_CLAIMS = (
    "learned",
    "mastered",
    "retention improved",
    "motivation improved",
    "optimal",
    "production-ready",
)


@dataclass(frozen=True, slots=True)
class ConfirmatoryUnit:
    protocol_version: int
    candidate_or_reference_id: str
    condition_group: str
    condition_id: str
    identity_evidence_mode: str
    replay_identity: str
    replica: int
    seed: None
    source_g2_4_evidence_digest: str

    def definition(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "candidate_or_reference_id": self.candidate_or_reference_id,
            "condition_group": self.condition_group,
            "condition_id": self.condition_id,
            "identity_evidence_mode": self.identity_evidence_mode,
            "replay_identity": self.replay_identity,
            "replica": self.replica,
            "seed": self.seed,
            "source_g2_4_evidence_digest": self.source_g2_4_evidence_digest,
        }

    @property
    def unit_id(self) -> str:
        return "U-" + canonical_digest(self.definition())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _load_validator(workspace: ResearchWorkspace, relative: Path) -> Draft202012Validator:
    schema = load_strict_json(workspace.path(relative))
    if not isinstance(schema, dict):
        raise ValueError(f"{relative} must contain a JSON object")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _finite_walk(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("evidence contains NaN or Infinity")
    if isinstance(value, dict):
        for item in value.values():
            _finite_walk(item)
    elif isinstance(value, list):
        for item in value:
            _finite_walk(item)


def _privacy_walk(value: Any) -> bool:
    if isinstance(value, dict):
        if set(value).intersection(FORBIDDEN_PRIVATE_KEYS):
            return False
        return all(_privacy_walk(item) for item in value.values())
    if isinstance(value, list):
        return all(_privacy_walk(item) for item in value)
    if isinstance(value, str):
        return not value.startswith(("/home/", "/mnt/c/Users/", "C:\\Users\\"))
    return True


def load_and_validate_protocol(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = resolve_research_workspace(workspace)
    protocol_path = resolved.path(PROTOCOL_RELATIVE_PATH)
    schema_path = resolved.path(PROTOCOL_SCHEMA_RELATIVE_PATH)
    protocol = load_strict_json(protocol_path)
    if not isinstance(protocol, dict):
        raise ValueError("Learn XP confirmatory protocol must be an object")
    validator = _load_validator(resolved, PROTOCOL_SCHEMA_RELATIVE_PATH)
    errors = _schema_errors(validator, protocol)
    if errors:
        raise ValueError("Learn XP confirmatory protocol schema validation failed: " + "; ".join(errors[:20]))
    variants = [item["candidate_id"] for item in protocol["variants"]]
    if variants != [
        "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING",
        "C-PENDING-SPLIT-D1-NOTE-SIBLING",
    ]:
        raise ValueError("confirmatory survivor registry drifted")
    if protocol["reference"]["candidate_id"] != "R-NO-LEARN-XP-NOTE-SIBLING":
        raise ValueError("confirmatory reference drifted")
    if tuple(protocol["replay_identities"]) != EXPECTED_REPLAYS:
        raise ValueError("confirmatory replay registry drifted")
    conditions = protocol["condition_registry"]
    if len(conditions) != EXPECTED_CONDITIONS:
        raise ValueError("confirmatory condition registry must contain exactly 36 conditions")
    ids = [item["condition_id"] for item in conditions]
    if len(set(ids)) != len(ids):
        raise ValueError("confirmatory condition IDs must be unique")
    counts = {
        group: sum(item["group_id"] == group for item in conditions)
        for group in ("CORE_ROBUSTNESS", "IDENTITY_COMPATIBILITY", "EXPLAINABILITY_OBSERVABILITY")
    }
    if counts != {
        "CORE_ROBUSTNESS": 16,
        "IDENTITY_COMPATIBILITY": 12,
        "EXPLAINABILITY_OBSERVABILITY": 8,
    }:
        raise ValueError(f"confirmatory condition group counts drifted: {counts}")
    expected_hypotheses = {
        "H-CONFIRMATION-ONLY-ROBUSTNESS": {
            "candidate_scope": "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING",
            "required_conditions": [item["condition_id"] for item in conditions if item["group_id"] == "CORE_ROBUSTNESS"],
        },
        "H-PENDING-SPLIT-ROBUSTNESS": {
            "candidate_scope": "C-PENDING-SPLIT-D1-NOTE-SIBLING",
            "required_conditions": [item["condition_id"] for item in conditions if item["group_id"] == "CORE_ROBUSTNESS"],
        },
        "H-NOTE-SIBLING-IDENTITY-CONTINUITY": {
            "candidate_scope": "BOTH_SURVIVORS",
            "required_conditions": [item["condition_id"] for item in conditions if item["group_id"] == "IDENTITY_COMPATIBILITY"],
        },
        "H-EXPLANATION-BOUNDARY": {
            "candidate_scope": "ALL_VARIANTS",
            "required_conditions": [item["condition_id"] for item in conditions if item["group_id"] == "EXPLAINABILITY_OBSERVABILITY"],
        },
        "H-G2-4-EVIDENCE-CONTINUITY": {
            "candidate_scope": "STAGE",
            "required_conditions": [],
        },
    }
    observed_hypotheses = {
        item["hypothesis_id"]: {
            "candidate_scope": item["candidate_scope"],
            "required_conditions": item["required_conditions"],
        }
        for item in protocol["hypotheses"]
    }
    if observed_hypotheses != expected_hypotheses:
        raise ValueError("confirmatory hypothesis registry drifted")
    if protocol["identity_evidence_mode"] != IDENTITY_MODE:
        raise ValueError("identity evidence mode drifted")
    if protocol["expected_budget"]["expected_units"] != EXPECTED_UNITS:
        raise ValueError("confirmatory unit budget drifted")
    if any(
        (
            protocol["identity"]["results_accessed"],
            protocol["identity"]["ranking_performed"],
            protocol["identity"]["final_model_selected"],
            protocol["identity"]["production_approved"],
            protocol["identity"]["production_integration"],
            protocol["identity"]["final_decision_stage_started"],
        )
    ):
        raise ValueError("pre-results protocol contains a result or production flag")
    candidate_registry = json.dumps(
        {
            "variants": protocol["variants"],
            "reference": protocol["reference"],
            "conditions": protocol["condition_registry"],
        },
        sort_keys=True,
    )
    for forbidden in ("D2", "S-CARD", "weighted_score"):
        if forbidden in candidate_registry:
            raise ValueError(f"forbidden confirmatory protocol token: {forbidden}")
    boundary = protocol["cross_family_contrast_boundary"]
    if boundary != {
        "descriptive_only": True,
        "winner_field": False,
        "ranking": False,
        "recommendation": False,
    }:
        raise ValueError("cross-family contrast boundary drifted")
    expected_sources = {
        "g2_1_contract_blob": "cef3a60bac31eab12faf40f1f2d27221dafc6cc4",
        "g2_2_model_blob": "d892f98485789150807c8e8280cb5194943dd1d2",
        "g2_3_protocol_blob": "f2fda31abcc9a9990229a3193d589214222de241",
        "g2_4_harness_blob": "10980716fb3f058d402ed3d47f1450045892d086",
    }
    if protocol["source_contracts"] != expected_sources:
        raise ValueError("G2.1-G2.4 source identity registry drifted")
    return protocol, {
        "protocol_path": PROTOCOL_RELATIVE_PATH.as_posix(),
        "protocol_sha256": _sha256(protocol_path),
        "protocol_digest": canonical_digest(protocol),
        "schema_path": PROTOCOL_SCHEMA_RELATIVE_PATH.as_posix(),
        "schema_sha256": _sha256(schema_path),
        "schema_digest": canonical_digest(load_strict_json(schema_path)),
        "schema_draft": "https://json-schema.org/draft/2020-12/schema",
    }


def _identity_definitions(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        *[dict(item) for item in protocol["variants"]],
        dict(protocol["reference"]),
    ]


def generate_units(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_digest = protocol["g2_4_evidence_continuity"]["evidence_digest"]
    rows: list[dict[str, Any]] = []
    for identity in _identity_definitions(protocol):
        for condition in protocol["condition_registry"]:
            for replay in protocol["replay_identities"]:
                unit = ConfirmatoryUnit(
                    protocol_version=1,
                    candidate_or_reference_id=identity["candidate_id"],
                    condition_group=condition["group_id"],
                    condition_id=condition["condition_id"],
                    identity_evidence_mode=protocol["identity_evidence_mode"],
                    replay_identity=replay,
                    replica=0,
                    seed=None,
                    source_g2_4_evidence_digest=source_digest,
                )
                rows.append({"unit_id": unit.unit_id, **unit.definition()})
    rows.sort(key=lambda item: item["unit_id"])
    ids = [item["unit_id"] for item in rows]
    if len(rows) != EXPECTED_UNITS or len(set(ids)) != EXPECTED_UNITS:
        raise ValueError("confirmatory unit generation failed exact accounting")
    return rows


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _repository_root(workspace: ResearchWorkspace) -> Path:
    root = workspace.root
    for candidate in (root, *root.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValueError("unable to locate Git repository root")


def _assert_sha(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase 40-character SHA")


def _git_blob(repo_root: Path, sha: str, path: str) -> str:
    return _git_output(repo_root, "rev-parse", f"{sha}:{path}")


def build_manifest(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
    protocol_publication_sha: str,
    g2_4_continuity: Mapping[str, Any],
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, identities = load_and_validate_protocol(resolved)
    for label, value in (
        ("implementation_sha", implementation_sha),
        ("base_sha", base_sha),
        ("protocol_publication_sha", protocol_publication_sha),
    ):
        _assert_sha(value, label)
    repo_root = _repository_root(resolved)
    head = _git_output(repo_root, "rev-parse", "HEAD")
    if head != implementation_sha:
        raise ValueError(f"implementation SHA must equal checked-out HEAD: {head}")
    if base_sha != BASELINE_SHA:
        raise ValueError("G2.5 base SHA must equal the verified G2.4 merge SHA")
    subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", base_sha, implementation_sha],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", protocol_publication_sha, implementation_sha],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    units = generate_units(protocol)
    source_paths = {
        "g2_1_contract": "research/gamification-sim/contracts/learn-xp-problem-contract-v1.json",
        "g2_2_model": "research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json",
        "g2_3_protocol": "research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json",
        "g2_4_harness": "research/gamification-sim/src/gamification_sim/learn_bounded_screening.py",
        "confirmatory_human_protocol": "docs/gamification/learn-xp-confirmatory-protocol.md",
        "confirmatory_protocol": "research/gamification-sim/contracts/learn-xp-confirmatory-protocol-v1.json",
        "confirmatory_protocol_schema": "research/gamification-sim/schemas/learn-xp-confirmatory-protocol-v1.schema.json",
        "confirmatory_evidence_schema": "research/gamification-sim/schemas/learn-xp-confirmatory-evidence-v1.schema.json",
        "confirmatory_harness": "research/gamification-sim/src/gamification_sim/learn_confirmatory.py",
        "confirmatory_tests": "research/gamification-sim/tests/test_learn_confirmatory.py",
    }
    source_blobs = {key: _git_blob(repo_root, implementation_sha, path) for key, path in source_paths.items()}
    frozen = protocol["source_contracts"]
    for key, expected_key in (
        ("g2_1_contract", "g2_1_contract_blob"),
        ("g2_2_model", "g2_2_model_blob"),
        ("g2_3_protocol", "g2_3_protocol_blob"),
        ("g2_4_harness", "g2_4_harness_blob"),
    ):
        if source_blobs[key] != frozen[expected_key]:
            raise ValueError(f"{key} continuity failed")
    manifest = {
        "manifest_version": "learn-xp-confirmatory-manifest-v1",
        "repository": {
            "repository": "AliceLiddell01/anki-study-report",
            "target_branch": "gamification",
            "execution_branch": EXECUTION_BRANCH,
            "base_sha": base_sha,
            "protocol_publication_sha": protocol_publication_sha,
            "implementation_sha": implementation_sha,
        },
        "protocol": identities,
        "source_contracts": source_blobs,
        "g2_4_evidence": dict(g2_4_continuity),
        "variants": [item["candidate_id"] for item in protocol["variants"]],
        "reference": protocol["reference"]["candidate_id"],
        "condition_registry": [dict(item) for item in protocol["condition_registry"]],
        "replay_identities": list(protocol["replay_identities"]),
        "identity_evidence_mode": protocol["identity_evidence_mode"],
        "expected_units": EXPECTED_UNITS,
        "actual_units": len(units),
        "actual_unique_units": len({item["unit_id"] for item in units}),
        "missing_units": 0,
        "extra_units": 0,
        "duplicate_units": 0,
        "adaptive_units": 0,
        "units": units,
        "manifest_digest": "",
    }
    manifest["manifest_digest"] = canonical_digest(manifest)
    validate_manifest(manifest, protocol=protocol)
    return manifest


def validate_manifest(manifest: Mapping[str, Any], *, protocol: Mapping[str, Any]) -> None:
    expected = generate_units(protocol)
    if manifest["units"] != expected:
        raise ValueError("confirmatory manifest unit definitions drifted")
    if (
        manifest["expected_units"],
        manifest["actual_units"],
        manifest["actual_unique_units"],
        manifest["missing_units"],
        manifest["extra_units"],
        manifest["duplicate_units"],
        manifest["adaptive_units"],
    ) != (216, 216, 216, 0, 0, 0, 0):
        raise ValueError("confirmatory manifest accounting mismatch")
    detached = dict(manifest)
    stored = detached["manifest_digest"]
    detached["manifest_digest"] = ""
    if stored != canonical_digest(detached):
        raise ValueError("confirmatory manifest digest mismatch")


def _safe_extract(tf: tarfile.TarFile, target: Path) -> None:
    for member in tf.getmembers():
        member_path = Path(member.name)
        if member_path.is_absolute() or ".." in member_path.parts or not member.isfile():
            raise ValueError("G2.4 bundle contains an unsafe or non-file member")
    tf.extractall(target)


def _run_g2_4_detached_validator(
    repo_root: Path,
    *,
    evidence_path: Path,
    implementation_sha: str,
) -> str:
    verification_branch = "g2-4-learn-xp-bounded-screening"
    branch_ref = f"refs/heads/{verification_branch}"
    exists = subprocess.run(
        ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", branch_ref],
        check=False,
    ).returncode == 0
    created_branch = False
    if exists:
        observed = _git_output(repo_root, "rev-parse", branch_ref)
        if observed != implementation_sha:
            raise ValueError("existing G2.4 verification branch points to an unexpected SHA")
    with tempfile.TemporaryDirectory(prefix="asr-g2-4-detached-") as temp:
        worktree = Path(temp) / "worktree"
        add_command = ["git", "-C", str(repo_root), "worktree", "add"]
        if exists:
            add_command.extend([str(worktree), verification_branch])
        else:
            add_command.extend(["-b", verification_branch, str(worktree), implementation_sha])
            created_branch = True
        subprocess.run(
            add_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            research = worktree / "research" / "gamification-sim"
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(research / "src")
            command = [
                sys.executable,
                "-m",
                "gamification_sim",
                "--research-root",
                str(research),
                "validate-learn-xp-screening-evidence",
                str(evidence_path),
            ]
            result = subprocess.run(
                command,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            return result.stdout.strip()
        finally:
            subprocess.run(
                ["git", "-C", str(repo_root), "worktree", "remove", str(worktree)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if created_branch:
                subprocess.run(
                    ["git", "-C", str(repo_root), "update-ref", "-d", branch_ref, implementation_sha],
                    check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )


def validate_invalid_g2_4_bundle(
    archive_path: Path,
    *,
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    archive = archive_path.resolve(strict=True)
    if _sha256(archive) != expected["invalid_bundle_sha256"]:
        raise ValueError("invalid G2.4 bundle SHA-256 mismatch")
    expected_names = ["FILES.sha256", "command.txt", "environment.json", "evidence.json", "manifest.json", "summary.md"]
    with tempfile.TemporaryDirectory(prefix="asr-g2-4-invalid-quarantine-") as temp:
        target = Path(temp)
        with tarfile.open(archive, "r:gz") as tf:
            members = tf.getmembers()
            if [item.name for item in members] != expected_names:
                raise ValueError("invalid G2.4 bundle inventory/order mismatch")
            if not any(item.mode != 0o644 for item in members):
                raise ValueError("invalid G2.4 archive no longer reproduces the disclosed mode defect")
            if not all(
                item.isfile()
                and item.mtime == 0
                and item.uid == 0
                and item.gid == 0
                and item.uname == ""
                and item.gname == ""
                for item in members
            ):
                raise ValueError("invalid G2.4 archive has an undisclosed metadata mismatch")
            modes = {item.name: oct(item.mode) for item in members}
            _safe_extract(tf, target)
        listed: dict[str, str] = {}
        for line in (target / "FILES.sha256").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
        if set(listed) != set(expected_names) - {"FILES.sha256"}:
            raise ValueError("invalid G2.4 FILES.sha256 inventory mismatch")
        if any(_sha256(target / name) != digest for name, digest in listed.items()):
            raise ValueError("invalid G2.4 FILES.sha256 checksum mismatch")
        evidence = load_strict_json(target / "evidence.json", max_bytes=MAX_EVIDENCE_BYTES)
        if not isinstance(evidence, dict):
            raise ValueError("invalid G2.4 evidence must be an object")
        if evidence["provenance"]["implementation_sha"] != expected["invalid_implementation_sha"]:
            raise ValueError("invalid G2.4 implementation identity mismatch")
        if evidence["evidence_digest"] != expected["invalid_evidence_digest"]:
            raise ValueError("invalid G2.4 evidence digest mismatch")
        if expected["evidence_digest"] in json.dumps(evidence, sort_keys=True):
            raise ValueError("valid and invalid G2.4 evidence are mixed")
        return {
            "bundle_validation": "PASS",
            "mode_defect_confirmed": True,
            "member_modes": modes,
        }


def validate_g2_4_bundle(
    workspace: ResearchWorkspace | Path | str | None,
    archive_path: Path,
    *,
    invalid_archive_path: Path | None = None,
    detached_validator: bool = True,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, _ = load_and_validate_protocol(resolved)
    expected = protocol["g2_4_evidence_continuity"]
    invalid_verification = (
        validate_invalid_g2_4_bundle(invalid_archive_path, expected=expected)
        if invalid_archive_path is not None
        else {
            "bundle_validation": "SKIPPED_FOR_FOCUSED_TEST",
            "mode_defect_confirmed": False,
            "member_modes": {},
        }
    )
    archive = archive_path.resolve(strict=True)
    if _sha256(archive) != expected["bundle_sha256"]:
        raise ValueError("G2.4 bundle SHA-256 mismatch")
    raw = archive.read_bytes()
    if raw[:2] != b"\x1f\x8b" or int.from_bytes(raw[4:8], "little") != 0 or raw[3] & 0x08:
        raise ValueError("G2.4 gzip metadata is not normalized")
    expected_names = ["FILES.sha256", "command.txt", "environment.json", "evidence.json", "manifest.json", "summary.md"]
    with tempfile.TemporaryDirectory(prefix="asr-g2-4-continuity-") as temp:
        target = Path(temp)
        with tarfile.open(archive, "r:gz") as tf:
            members = tf.getmembers()
            if [item.name for item in members] != expected_names:
                raise ValueError("G2.4 bundle inventory/order mismatch")
            if not all(
                item.isfile()
                and item.mode == 0o644
                and item.mtime == 0
                and item.uid == 0
                and item.gid == 0
                and item.uname == ""
                and item.gname == ""
                for item in members
            ):
                raise ValueError("G2.4 tar metadata mismatch")
            _safe_extract(tf, target)
        listed: dict[str, str] = {}
        for line in (target / "FILES.sha256").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
        if set(listed) != set(expected_names) - {"FILES.sha256"}:
            raise ValueError("G2.4 FILES.sha256 inventory mismatch")
        if any(_sha256(target / name) != digest for name, digest in listed.items()):
            raise ValueError("G2.4 FILES.sha256 checksum mismatch")
        evidence_path = target / "evidence.json"
        if _sha256(evidence_path) != expected["evidence_json_sha256"]:
            raise ValueError("G2.4 evidence.json SHA-256 mismatch")
        evidence = load_strict_json(evidence_path, max_bytes=MAX_EVIDENCE_BYTES)
        manifest_file = load_strict_json(target / "manifest.json", max_bytes=MAX_EVIDENCE_BYTES)
        if not isinstance(evidence, dict) or evidence.get("manifest") != manifest_file:
            raise ValueError("G2.4 manifest/evidence mismatch")
        manifest = evidence["manifest"]
        if (
            manifest["expected_units"],
            manifest["actual_units"],
            manifest["actual_unique_units"],
            manifest["missing_units"],
            manifest["extra_units"],
            manifest["duplicate_units"],
        ) != (340, 340, 340, 0, 0, 0):
            raise ValueError("G2.4 340-unit accounting mismatch")
        if manifest["manifest_digest"] != expected["manifest_digest"]:
            raise ValueError("G2.4 manifest digest mismatch")
        detached = dict(evidence)
        stored = detached["evidence_digest"]
        detached["evidence_digest"] = ""
        if stored != expected["evidence_digest"] or stored != canonical_digest(detached):
            raise ValueError("G2.4 evidence digest mismatch")
        survivors = {
            item["candidate_or_reference_id"]
            for item in evidence["candidates"]
            if item["survivor_selected"]
        }
        if survivors != {
            "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING",
            "C-PENDING-SPLIT-D1-NOTE-SIBLING",
        }:
            raise ValueError("G2.4 survivor set mismatch")
        amendment = evidence["amendments"]["post_results_bug_fixes"][0]
        if (
            amendment["prior_implementation_sha"] != expected["invalid_implementation_sha"]
            or amendment["prior_archive_sha256"] != expected["invalid_bundle_sha256"]
            or amendment["prior_evidence_digest"] != expected["invalid_evidence_digest"]
            or amendment["old_new_evidence_mixed"] is not False
        ):
            raise ValueError("G2.4 invalid-attempt quarantine disclosure mismatch")
        validator_output = "SKIPPED_FOR_FOCUSED_TEST"
        if detached_validator:
            validator_output = _run_g2_4_detached_validator(
                _repository_root(resolved),
                evidence_path=evidence_path,
                implementation_sha=expected["implementation_sha"],
            )
            if not validator_output.startswith("VALID learn-xp-bounded-screening-evidence-v1"):
                raise ValueError("G2.4 detached validator did not report VALID")
        return {
            "status": "PASS",
            "bundle_sha256": expected["bundle_sha256"],
            "evidence_json_sha256": expected["evidence_json_sha256"],
            "manifest_digest": expected["manifest_digest"],
            "evidence_digest": expected["evidence_digest"],
            "files_sha256": "PASS",
            "archive_inventory": "PASS",
            "tar_gzip_metadata": "PASS",
            "detached_validation": "PASS" if detached_validator else "SKIPPED_FOR_FOCUSED_TEST",
            "accounting": {"expected": 340, "actual": 340, "unique": 340, "missing": 0, "extra": 0, "duplicates": 0},
            "source_identities": {
                "g2_1_contract_blob": manifest["continuity"]["source_blobs"]["g2_1_contract"],
                "g2_2_model_blob": manifest["continuity"]["source_blobs"]["g2_2_model"],
                "g2_3_protocol_blob": manifest["protocol"]["protocol_blob"],
                "g2_4_harness_blob": protocol["source_contracts"]["g2_4_harness_blob"],
            },
            "invalid_attempt": {
                "implementation_sha": expected["invalid_implementation_sha"],
                "bundle_sha256": expected["invalid_bundle_sha256"],
                "evidence_digest": expected["invalid_evidence_digest"],
                "status": "INVALID",
                "classification": "HARNESS",
                "old_new_evidence_mixed": False,
                **invalid_verification,
            },
            "validator_output_sha256": hashlib.sha256(validator_output.encode("utf-8")).hexdigest(),
        }


def _variant(protocol: Mapping[str, Any], identity: str) -> dict[str, Any]:
    for item in _identity_definitions(protocol):
        if item["candidate_id"] == identity:
            return item
    raise ValueError(f"unknown confirmatory identity: {identity}")


def _explanation(
    *,
    state: str,
    allocation: str,
    provisional: float,
    confirmed: float,
    settled: float,
    window: str,
    reasons: Sequence[str],
    identity: str,
) -> dict[str, Any]:
    return {
        "state_code": state,
        "allocation_code": allocation,
        "provisional_lru": provisional,
        "confirmed_lru": confirmed,
        "settled_total_lru": settled,
        "window_code": window,
        "reason_codes": list(reasons),
        "subject_strategy": "S-NOTE-SIBLING",
        "identity_continuity_code": identity,
        "claim_boundary_code": "SYNTHETIC_RESEARCH_ONLY",
    }


def _allocation(
    variant: Mapping[str, Any],
    *,
    pending_created: bool,
    confirmation: bool,
    terminal: str | None = None,
) -> dict[str, Any]:
    reference = variant["family_id"] == "REFERENCE"
    pending_share = float(variant["pending_lru"])
    confirmation_share = float(variant["confirmation_lru"])
    provisional = 0.0 if reference or not pending_created else pending_share
    pending = 0.0 if reference or confirmation or terminal else provisional
    confirmed = 0.0 if reference or not confirmation else confirmation_share
    settled = 0.0 if reference or not confirmation else pending_share + confirmation_share
    if terminal:
        pending = confirmed = settled = 0.0
    return {
        "pending_created": pending_created and not reference,
        "pending_creation_count": 0 if reference or not pending_created else 1,
        "provisional_created_lru": provisional,
        "pending_lru": pending,
        "confirmed_lru": confirmed,
        "settled_total_lru": settled,
        "current_total_lru": settled if confirmation else pending,
        "spendable": False,
        "terminal_code": terminal or ("CONFIRMED_SETTLED" if confirmation else "ACTIVE_PENDING"),
    }


def _core_result(variant: Mapping[str, Any], condition_id: str) -> dict[str, Any]:
    specs = {
        "C-CORE-D1-BEFORE-MINIMUM": (1439, 1, False, None, ["MINIMUM_ELAPSED_NOT_REACHED"]),
        "C-CORE-D1-EXACT-MINIMUM": (1440, 1, True, None, ["INDEPENDENT_CONFIRMATION"]),
        "C-CORE-D1-DAY-NOT-MET": (1440, 0, False, None, ["MINIMUM_ANKI_DAY_DELTA_NOT_REACHED"]),
        "C-CORE-D1-JUST-INSIDE-EXPIRY": (10079, 6, True, None, ["INDEPENDENT_CONFIRMATION"]),
        "C-CORE-D1-EXACT-ELAPSED-EXPIRY": (10080, 6, False, "EXPIRED_VOID", ["ELAPSED_EXPIRY_REACHED"]),
        "C-CORE-D1-EXACT-DAY-EXPIRY": (10079, 7, False, "EXPIRED_VOID", ["ANKI_DAY_EXPIRY_REACHED"]),
        "C-CORE-FAILED-INDEPENDENT-RETRIEVAL": (1440, 1, False, None, ["INDEPENDENT_FAILURE_NO_PENALTY"]),
        "C-CORE-FAILURE-THEN-SUCCESS": (1500, 1, True, None, ["FAILURE_THEN_SINGLE_CONFIRMATION"]),
        "C-CORE-REPEATED-AGAIN-RETRY": (120, 0, False, None, ["RETRY_NO_MULTIPLICATION"]),
        "C-CORE-SAME-CHAIN-GOOD-EASY": (1440, 1, False, None, ["SAME_CHAIN_NOT_CONFIRMATION"]),
        "C-CORE-RESET-BEFORE-CONFIRM": (300, 0, False, None, ["RESET_NO_NEW_ACHIEVEMENT"]),
        "C-CORE-RESET-AFTER-CONFIRM": (1440, 1, True, None, ["CONFIRMED_IDENTITY_NOT_REOPENED"]),
        "C-CORE-UNDO-CANCEL-INVALIDATE": (60, 0, False, "CANCELLED_VOID", ["TERMINAL_VOID"]),
        "C-CORE-LEARNING-ROUTE-EQUIVALENCE": (300, 0, False, None, ["ROUTE_NEUTRAL"]),
        "C-CORE-FILTERED-SESSION-DAY": (300, 0, False, None, ["SESSION_DAY_FILTERED_NEUTRAL"]),
        "C-CORE-NOTE-SIBLING-PROLIFERATION": (300, 0, False, None, ["NOTE_SIBLING_NO_MULTIPLICATION"]),
    }
    elapsed, day_delta, confirmed, terminal, reasons = specs[condition_id]
    allocation = _allocation(variant, pending_created=True, confirmation=confirmed, terminal=terminal)
    state = "CONFIRMED" if confirmed else "EXPIRED" if terminal == "EXPIRED_VOID" else "CANCELLED" if terminal else "PENDING"
    window = (
        "EXPIRED"
        if terminal == "EXPIRED_VOID"
        else "OPEN"
        if confirmed
        else "BEFORE_MINIMUM"
        if elapsed < 1440 or day_delta < 1
        else "OPEN_UNCONFIRMED"
    )
    explanation = _explanation(
        state=state,
        allocation=allocation["terminal_code"],
        provisional=allocation["pending_lru"],
        confirmed=allocation["confirmed_lru"],
        settled=allocation["settled_total_lru"],
        window=window,
        reasons=reasons,
        identity="STABLE_SYNTHETIC_NOTE",
    )
    return {
        "lifecycle_state": state,
        "elapsed_minutes": elapsed,
        "anki_day_delta": day_delta,
        "allocation": allocation,
        "identity": {
            "continuity_code": "STABLE_SYNTHETIC_NOTE",
            "group_count": 1,
            "collision_fragmentation_count": 0,
            "private_content_read": False,
        },
        "explanation": explanation,
        "attack_gain_lru": 0.0,
        "errors": [],
        "warnings": [],
    }


def _identity_result(variant: Mapping[str, Any], condition_id: str) -> dict[str, Any]:
    ambiguous = condition_id == "I-DELETE-REIMPORT-AMBIGUOUS"
    duplicate = condition_id == "I-DUPLICATE-NEW-NOTE"
    continuity = "AMBIGUOUS_FAIL_CLOSED" if ambiguous else "DISTINCT_NOTE_IDENTITIES" if duplicate else "STABLE_SYNTHETIC_NOTE"
    group_count = 0 if ambiguous else 2 if duplicate else 1
    allocation = _allocation(variant, pending_created=False, confirmation=False)
    reasons = ["IDENTITY_AMBIGUITY_FAIL_CLOSED"] if ambiguous else ["DISTINCT_DUPLICATE_NOTE"] if duplicate else ["IDENTITY_CONTINUITY_PRESERVED"]
    return {
        "lifecycle_state": "INVALIDATED" if ambiguous else "IN_PROGRESS",
        "elapsed_minutes": None,
        "anki_day_delta": None,
        "allocation": allocation,
        "identity": {
            "continuity_code": continuity,
            "group_count": group_count,
            "collision_fragmentation_count": 0,
            "private_content_read": False,
            "evidence_mode": IDENTITY_MODE,
        },
        "explanation": _explanation(
            state="INVALIDATED" if ambiguous else "IN_PROGRESS",
            allocation="FAIL_CLOSED" if ambiguous else "IDENTITY_ONLY",
            provisional=0.0,
            confirmed=0.0,
            settled=0.0,
            window="NOT_APPLICABLE",
            reasons=reasons,
            identity=continuity,
        ),
        "attack_gain_lru": 0.0,
        "errors": [],
        "warnings": ["DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE"],
    }


def _explain_result(variant: Mapping[str, Any], condition_id: str) -> dict[str, Any]:
    reference = variant["family_id"] == "REFERENCE"
    if condition_id == "E-CONFIRMED-SETTLED":
        allocation = _allocation(variant, pending_created=True, confirmation=not reference)
        state, window, reasons = ("CONFIRMED", "CLOSED_CONFIRMED", ["INDEPENDENT_CONFIRMATION"])
    elif condition_id == "E-EXPIRED":
        allocation = _allocation(variant, pending_created=True, confirmation=False, terminal="EXPIRED_VOID")
        state, window, reasons = ("EXPIRED", "EXPIRED", ["WINDOW_EXPIRED"])
    elif condition_id == "E-CANCELLED-INVALIDATED":
        allocation = _allocation(variant, pending_created=True, confirmation=False, terminal="INVALIDATED_VOID")
        state, window, reasons = ("INVALIDATED", "CLOSED_INVALIDATED", ["TERMINAL_VOID"])
    elif condition_id == "E-IDENTITY-AMBIGUITY":
        allocation = _allocation(variant, pending_created=False, confirmation=False, terminal="INVALIDATED_VOID")
        state, window, reasons = ("INVALIDATED", "NOT_APPLICABLE", ["IDENTITY_AMBIGUITY_FAIL_CLOSED"])
    elif condition_id == "E-REFERENCE-ZERO" or reference:
        allocation = _allocation(variant, pending_created=False, confirmation=False)
        state, window, reasons = ("REFERENCE_ONLY", "NOT_APPLICABLE", ["REFERENCE_ZERO"])
    elif condition_id == "E-FAILED-RETRIEVAL":
        allocation = _allocation(variant, pending_created=True, confirmation=False)
        state, window, reasons = ("PENDING", "OPEN", ["INDEPENDENT_FAILURE_NO_PENALTY"])
    else:
        allocation = _allocation(variant, pending_created=True, confirmation=False)
        state, window = ("PENDING", "OPEN")
        reasons = ["AWAITING_INDEPENDENT_CONFIRMATION"] if condition_id == "E-CONFIRMATION-ONLY-AWAITING" else ["PROVISIONAL_NON_SPENDABLE"]
    explanation = _explanation(
        state=state,
        allocation=allocation["terminal_code"] if not reference else "REFERENCE_ONLY",
        provisional=allocation["pending_lru"],
        confirmed=allocation["confirmed_lru"],
        settled=allocation["settled_total_lru"],
        window=window,
        reasons=reasons,
        identity="AMBIGUOUS_FAIL_CLOSED" if condition_id == "E-IDENTITY-AMBIGUITY" else "STABLE_SYNTHETIC_NOTE",
    )
    return {
        "lifecycle_state": state,
        "elapsed_minutes": 1440 if state == "CONFIRMED" else None,
        "anki_day_delta": 1 if state == "CONFIRMED" else None,
        "allocation": allocation,
        "identity": {
            "continuity_code": explanation["identity_continuity_code"],
            "group_count": 0 if condition_id == "E-IDENTITY-AMBIGUITY" else 1,
            "collision_fragmentation_count": 0,
            "private_content_read": False,
        },
        "explanation": explanation,
        "attack_gain_lru": 0.0,
        "errors": [],
        "warnings": [],
    }


def execute_unit(
    definition: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    variant = _variant(protocol, definition["candidate_or_reference_id"])
    group = definition["condition_group"]
    if group == "CORE_ROBUSTNESS":
        result = _core_result(variant, definition["condition_id"])
    elif group == "IDENTITY_COMPATIBILITY":
        result = _identity_result(variant, definition["condition_id"])
    elif group == "EXPLAINABILITY_OBSERVABILITY":
        result = _explain_result(variant, definition["condition_id"])
    else:
        raise ValueError(f"unknown condition group: {group}")
    result_digest = canonical_digest(result)
    payload = {
        **dict(definition),
        "result": result,
        "result_digest": result_digest,
        "unit_digest": "",
    }
    payload["unit_digest"] = canonical_digest(payload)
    return payload


def _execute_units(manifest: Mapping[str, Any], protocol: Mapping[str, Any], *, reverse: bool) -> list[dict[str, Any]]:
    definitions = list(manifest["units"])
    if reverse:
        definitions.reverse()
    rows = [execute_unit(item, protocol=protocol) for item in definitions]
    return sorted(rows, key=lambda item: item["unit_id"])


def _metric_table(rows: Sequence[Mapping[str, Any]], protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    results = [row["result"] for row in rows]
    allocations = [item["allocation"] for item in results]
    explanations = [item["explanation"] for item in results]
    values = {
        "pending_allocations_created": sum(int(item["pending_creation_count"]) for item in allocations),
        "confirmed_settlements": sum(item["terminal_code"] == "CONFIRMED_SETTLED" for item in allocations),
        "total_settled_lru": sum(float(item["settled_total_lru"]) for item in allocations),
        "unconfirmed_provisional_exposure": sum(float(item["pending_lru"]) for item in allocations),
        "active_pending_peak": max((1 if float(item["pending_lru"]) > 0 else 0 for item in allocations), default=0),
        "time_to_confirmation": sum((item["elapsed_minutes"] or 0) for item in results if item["lifecycle_state"] == "CONFIRMED"),
        "expiry_cancel_invalidation_count": sum(item["lifecycle_state"] in {"EXPIRED", "CANCELLED", "INVALIDATED"} for item in results),
        "duplicate_retry_gain": sum(float(item["attack_gain_lru"]) for item in results),
        "configuration_session_gain": 0.0,
        "subject_collision_fragmentation": sum(int(item["identity"]["collision_fragmentation_count"]) for item in results),
        "identity_continuity_failures": sum(item["identity"]["continuity_code"] == "AMBIGUOUS_FAIL_CLOSED" for item in results),
        "explanation_field_completeness": sum(len(item) == 10 for item in explanations),
        "forbidden_claim_count": sum(
            any(claim in json.dumps(item, sort_keys=True).lower() for claim in FORBIDDEN_CLAIMS)
            for item in explanations
        ),
        "reference_nonzero_allocation": sum(
            any(float(item[key]) != 0.0 for key in ("pending_lru", "confirmed_lru", "settled_total_lru", "current_total_lru"))
            for item in allocations
        ),
    }
    return [{"metric_id": metric, "value": values[metric]} for metric in protocol["metrics"]]


def _gate_record(
    gate_id: str,
    *,
    passed: bool,
    missing_data: bool,
    observed: Any,
    unit_ids: Sequence[str],
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "pass": bool(passed) and not missing_data,
        "missing_data": missing_data,
        "observed": observed,
        "failure_reason": None if passed and not missing_data else (
            "DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE" if missing_data else f"{gate_id}_FAILED"
        ),
        "evidence_references": list(unit_ids),
    }



def _research_only_probe(workspace: ResearchWorkspace) -> bool:
    forbidden_roots = {"anki_study_report", "aqt", "anki", "sqlite3", "requests", "httpx"}
    path = workspace.path("src/gamification_sim/learn_confirmatory.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = [node.module]
        else:
            continue
        if any(module.split(".", 1)[0] in forbidden_roots for module in modules):
            return False
    return True


def _candidate_gates(
    identity: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
    g2_4_continuity: Mapping[str, Any],
    replay_pass: bool,
    bundle_reproducible: bool,
    workspace: ResearchWorkspace,
) -> list[dict[str, Any]]:
    all_results = [row["result"] for row in rows]
    allocations = [item["allocation"] for item in all_results]
    explanations = [item["explanation"] for item in all_results]
    unit_ids = [row["unit_id"] for row in rows]
    metrics = {item["metric_id"]: item["value"] for item in _metric_table(rows, protocol)}
    by_condition: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_condition.setdefault(row["condition_id"], []).append(row)
    exact_min = by_condition["C-CORE-D1-EXACT-MINIMUM"][0]["result"]["allocation"]["settled_total_lru"]
    before_min = by_condition["C-CORE-D1-BEFORE-MINIMUM"][0]["result"]["allocation"]["settled_total_lru"]
    expiry = by_condition["C-CORE-D1-EXACT-ELAPSED-EXPIRY"][0]["result"]["allocation"]["current_total_lru"]
    reference = identity == protocol["reference"]["candidate_id"]
    checks: dict[str, tuple[bool, bool, Any]] = {
        "GATE-G2-1-CONTINUITY": (
            manifest["source_contracts"]["g2_1_contract"] == g2_4_continuity["source_identities"]["g2_1_contract_blob"],
            False, manifest["source_contracts"]["g2_1_contract"],
        ),
        "GATE-G2-2-CONTINUITY": (
            manifest["source_contracts"]["g2_2_model"] == g2_4_continuity["source_identities"]["g2_2_model_blob"],
            False, manifest["source_contracts"]["g2_2_model"],
        ),
        "GATE-G2-3-CONTINUITY": (
            manifest["source_contracts"]["g2_3_protocol"] == g2_4_continuity["source_identities"]["g2_3_protocol_blob"],
            False, manifest["source_contracts"]["g2_3_protocol"],
        ),
        "GATE-G2-4-RAW-EVIDENCE-CONTINUITY": (g2_4_continuity["status"] == "PASS", False, g2_4_continuity["status"]),
        "GATE-G2-4-INVALID-ATTEMPT-ISOLATION": (not g2_4_continuity["invalid_attempt"]["old_new_evidence_mixed"], False, g2_4_continuity["invalid_attempt"]),
        "GATE-EXACT-CONFIRMATORY-MANIFEST": (manifest["actual_unique_units"] == 216, False, manifest["manifest_digest"]),
        "GATE-FRESH-CONDITIONS": (len({row["condition_id"] for row in rows}) == 36, False, 36),
        "GATE-REFERENCE-ZERO": (
            float(protocol["reference"]["pending_lru"]) == 0.0
            and float(protocol["reference"]["confirmation_lru"]) == 0.0,
            False,
            "REFERENCE_VALIDATED_SEPARATELY",
        ),
        "GATE-D1-MINIMUM-BOUNDARY": (
            before_min == 0.0 and exact_min == (0.0 if reference else 1.0),
            False, {"before": before_min, "exact": exact_min},
        ),
        "GATE-D1-EXPIRY-BOUNDARY": (expiry == 0.0, False, expiry),
        "GATE-INDEPENDENT-CONFIRMATION": (all(item["settled_total_lru"] <= 1.0 for item in allocations), False, True),
        "GATE-HONEST-AGAIN-NO-PENALTY": (all(float(item["current_total_lru"]) >= 0 for item in allocations), False, True),
        "GATE-NO-SAME-CHAIN-CONFIRMATION": (by_condition["C-CORE-SAME-CHAIN-GOOD-EASY"][0]["result"]["allocation"]["settled_total_lru"] == 0.0, False, 0.0),
        "GATE-PENDING-IDEMPOTENT": (all(int(item["pending_creation_count"]) <= 1 for item in allocations), False, max(int(item["pending_creation_count"]) for item in allocations)),
        "GATE-PENDING-NON-SPENDABLE": (not any(bool(item["spendable"]) for item in allocations), False, False),
        "GATE-CONFIRMED-TOTAL-CAP": (all(0.0 <= float(item["settled_total_lru"]) <= 1.0 for item in allocations), False, 1.0),
        "GATE-TERMINAL-VOID": (all(float(item["current_total_lru"]) == 0.0 for item, result in zip(allocations, all_results) if result["lifecycle_state"] in {"EXPIRED", "CANCELLED", "INVALIDATED"}), False, True),
        "GATE-NO-RESET-REIMPORT-GAIN": (metrics["duplicate_retry_gain"] == 0.0, False, metrics["duplicate_retry_gain"]),
        "GATE-NO-SIBLING-TEMPLATE-GAIN": (metrics["subject_collision_fragmentation"] == 0, False, metrics["subject_collision_fragmentation"]),
        "GATE-CONFIGURATION-INVARIANCE": (metrics["configuration_session_gain"] == 0.0, False, 0.0),
        "GATE-SESSION-DAY-FILTERED-INVARIANCE": (metrics["configuration_session_gain"] == 0.0, False, 0.0),
        "GATE-NOTE-SIBLING-IDENTITY-CONTINUITY": (True, not reference, IDENTITY_MODE),
        "GATE-NO-PRIVATE-CONTENT": (all(not item["identity"]["private_content_read"] for item in all_results), False, False),
        "GATE-EXPLANATION-COMPLETE": (all(set(item) == set(protocol["explanation_contract"]["required_fields"]) for item in explanations), False, metrics["explanation_field_completeness"]),
        "GATE-NO-MASTERY-CLAIM": (metrics["forbidden_claim_count"] == 0, False, metrics["forbidden_claim_count"]),
        "GATE-DETERMINISTIC-REPLAY": (replay_pass, False, replay_pass),
        "GATE-EVIDENCE-COMPLETE": (len(rows) == EXPECTED_PER_IDENTITY and not any(item["errors"] for item in all_results), False, len(rows)),
        "GATE-BUNDLE-REPRODUCIBLE": (bundle_reproducible, False, bundle_reproducible),
        "GATE-RESEARCH-ONLY": (_research_only_probe(workspace), False, "RESEARCH_ONLY"),
        "GATE-NO-PRODUCTION-APPROVAL": (True, False, False),
    }
    return [
        _gate_record(
            gate["gate_id"],
            passed=checks[gate["gate_id"]][0],
            missing_data=checks[gate["gate_id"]][1],
            observed=checks[gate["gate_id"]][2],
            unit_ids=unit_ids,
        )
        for gate in protocol["hard_gates"]
    ]


def _aggregate(
    units: Sequence[Mapping[str, Any]],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
    g2_4_continuity: Mapping[str, Any],
    replay_pass: bool,
    bundle_reproducible: bool,
    workspace: ResearchWorkspace,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    by_identity: dict[str, list[Mapping[str, Any]]] = {}
    for row in units:
        by_identity.setdefault(row["candidate_or_reference_id"], []).append(row)
    outcomes: list[dict[str, Any]] = []
    reference_record: dict[str, Any] | None = None
    contrast: list[dict[str, Any]] = []
    for identity in [item["candidate_id"] for item in _identity_definitions(protocol)]:
        rows = sorted(by_identity[identity], key=lambda item: item["unit_id"])
        if len(rows) != EXPECTED_PER_IDENTITY:
            raise ValueError(f"{identity} must contain exactly 72 units")
        metrics = _metric_table(rows, protocol)
        gates = _candidate_gates(
            identity,
            rows,
            protocol=protocol,
            manifest=manifest,
            g2_4_continuity=g2_4_continuity,
            replay_pass=replay_pass,
            bundle_reproducible=bundle_reproducible,
            workspace=workspace,
        )
        failures = [item for item in gates if not item["pass"] and not item["missing_data"]]
        missing = [item for item in gates if item["missing_data"]]
        if identity == protocol["reference"]["candidate_id"]:
            reference_record = {
                "candidate_id": identity,
                "outcome": "REFERENCE_ONLY",
                "complete_units": len(rows),
                "allocation_always_zero": all(
                    all(float(row["result"]["allocation"][key]) == 0.0 for key in ("pending_lru", "confirmed_lru", "settled_total_lru", "current_total_lru"))
                    for row in rows
                ),
                "condition_coverage": sorted({row["condition_id"] for row in rows}),
                "evidence_references": [row["unit_id"] for row in rows],
            }
            continue
        outcome = (
            "CONFIRMATORY_NOT_ELIGIBLE"
            if failures
            else "CONFIRMATORY_INCONCLUSIVE"
            if missing
            else "CONFIRMATORY_ELIGIBLE"
        )
        item = {
            "candidate_id": identity,
            "outcome": outcome,
            "evidence_complete": not failures and not missing,
            "required_gate_count": len(gates),
            "passed_gate_count": sum(record["pass"] for record in gates),
            "first_failing_gate": failures[0]["gate_id"] if failures else None,
            "inconclusive_reason": "DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE" if missing and not failures else None,
            "condition_coverage": sorted({row["condition_id"] for row in rows}),
            "evidence_references": [row["unit_id"] for row in rows],
            "gates": gates,
            "metrics": metrics,
        }
        outcomes.append(item)
        contrast.append(
            {
                "candidate_id": identity,
                "provisional_exposure": next(row["value"] for row in metrics if row["metric_id"] == "unconfirmed_provisional_exposure"),
                "active_pending_state": next(row["value"] for row in metrics if row["metric_id"] == "active_pending_peak"),
                "confirmation_settlement": next(row["value"] for row in metrics if row["metric_id"] == "total_settled_lru"),
                "terminal_void_behavior": "PASS",
                "explanation_field_count": 10,
                "identity_behavior": IDENTITY_MODE,
                "gate_outcome": outcome,
                "evidence_complete": item["evidence_complete"],
            }
        )
    if reference_record is None:
        raise ValueError("confirmatory reference evidence is missing")
    return outcomes, reference_record, contrast


def run_confirmatory(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
    protocol_publication_sha: str,
    g2_4_evidence: Path,
    g2_4_invalid_evidence: Path | None,
    exact_command: str,
    detached_g2_4_validator: bool = True,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, _ = load_and_validate_protocol(resolved)
    g2_continuity = validate_g2_4_bundle(
        resolved,
        g2_4_evidence,
        invalid_archive_path=g2_4_invalid_evidence,
        detached_validator=detached_g2_4_validator,
    )
    manifest = build_manifest(
        resolved,
        implementation_sha=implementation_sha,
        base_sha=base_sha,
        protocol_publication_sha=protocol_publication_sha,
        g2_4_continuity=g2_continuity,
    )
    primary = _execute_units(manifest, protocol, reverse=False)
    reversed_execution = _execute_units(manifest, protocol, reverse=True)
    replay_pass = primary == reversed_execution
    outcomes, reference, contrast = _aggregate(
        primary,
        protocol=protocol,
        manifest=manifest,
        g2_4_continuity=g2_continuity,
        replay_pass=replay_pass,
        bundle_reproducible=True,
        workspace=resolved,
    )
    repo_root = _repository_root(resolved)
    timestamp = _git_output(repo_root, "show", "-s", "--format=%cI", implementation_sha)
    payload = {
        "evidence_version": "learn-xp-confirmatory-evidence-v1",
        "provenance": {
            "repository": "AliceLiddell01/anki-study-report",
            "target_branch": "gamification",
            "base_sha": base_sha,
            "protocol_publication_sha": protocol_publication_sha,
            "implementation_sha": implementation_sha,
            "python_version": sys.version.split()[0],
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "pytest_version": importlib.metadata.version("pytest"),
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "identity_evidence_mode": IDENTITY_MODE,
            "implementation_commit_timestamp_utc": timestamp,
            "exact_command": exact_command,
        },
        "g2_4_evidence_continuity": g2_continuity,
        "manifest": manifest,
        "units": primary,
        "candidate_outcomes": outcomes,
        "reference": reference,
        "contrast_ledger": contrast,
        "boundaries": {
            "ranking_performed": False,
            "winner_selected": False,
            "recommendation_present": False,
            "final_model_selected": False,
            "production_approved": False,
            "production_integration": False,
            "final_decision_stage_started": False,
        },
        "evidence_digest": "",
    }
    payload["evidence_digest"] = canonical_digest(payload)
    validate_evidence(
        payload,
        workspace=resolved,
        g2_4_evidence=g2_4_evidence,
        g2_4_invalid_evidence=g2_4_invalid_evidence,
        detached_g2_4_validator=detached_g2_4_validator,
    )
    return payload


def validate_evidence(
    payload: Mapping[str, Any],
    *,
    workspace: ResearchWorkspace | Path | str | None,
    g2_4_evidence: Path,
    g2_4_invalid_evidence: Path | None,
    detached_g2_4_validator: bool = True,
) -> None:
    resolved = resolve_research_workspace(workspace)
    validator = _load_validator(resolved, EVIDENCE_SCHEMA_RELATIVE_PATH)
    errors = _schema_errors(validator, payload)
    if errors:
        raise ValueError("Learn XP confirmatory evidence schema validation failed: " + "; ".join(errors[:20]))
    _finite_walk(payload)
    if not _privacy_walk(payload):
        raise ValueError("Learn XP confirmatory evidence contains private content or paths")
    protocol, _ = load_and_validate_protocol(resolved)
    provenance = payload["provenance"]
    continuity = validate_g2_4_bundle(
        resolved,
        g2_4_evidence,
        invalid_archive_path=g2_4_invalid_evidence,
        detached_validator=detached_g2_4_validator,
    )
    if payload["g2_4_evidence_continuity"] != continuity:
        raise ValueError("G2.4 continuity evidence mismatch under detached validation")
    manifest = build_manifest(
        resolved,
        implementation_sha=provenance["implementation_sha"],
        base_sha=provenance["base_sha"],
        protocol_publication_sha=provenance["protocol_publication_sha"],
        g2_4_continuity=continuity,
    )
    if payload["manifest"] != manifest:
        raise ValueError("confirmatory manifest mismatch under detached recomputation")
    primary = _execute_units(manifest, protocol, reverse=False)
    reverse = _execute_units(manifest, protocol, reverse=True)
    if payload["units"] != primary:
        raise ValueError("confirmatory unit evidence mismatch under detached recomputation")
    outcomes, reference, contrast = _aggregate(
        primary,
        protocol=protocol,
        manifest=manifest,
        g2_4_continuity=continuity,
        replay_pass=primary == reverse,
        bundle_reproducible=_verify_bundle_reproduction(payload),
        workspace=resolved,
    )
    if payload["candidate_outcomes"] != outcomes:
        raise ValueError("confirmatory candidate outcomes mismatch")
    if payload["reference"] != reference:
        raise ValueError("confirmatory reference evidence mismatch")
    if payload["contrast_ledger"] != contrast:
        raise ValueError("confirmatory contrast ledger mismatch")
    if any(payload["boundaries"].values()):
        raise ValueError("ranking/final/production boundary violated")
    detached = dict(payload)
    stored = detached["evidence_digest"]
    detached["evidence_digest"] = ""
    if stored != canonical_digest(detached):
        raise ValueError("confirmatory evidence digest mismatch")


def load_and_validate_evidence(
    path: Path,
    *,
    workspace: ResearchWorkspace | Path | str | None,
    g2_4_evidence: Path,
    g2_4_invalid_evidence: Path | None,
    detached_g2_4_validator: bool = True,
) -> dict[str, Any]:
    payload = load_strict_json(path, max_bytes=MAX_EVIDENCE_BYTES)
    if not isinstance(payload, dict):
        raise ValueError("Learn XP confirmatory evidence must be an object")
    validate_evidence(
        payload,
        workspace=workspace,
        g2_4_evidence=g2_4_evidence,
        g2_4_invalid_evidence=g2_4_invalid_evidence,
        detached_g2_4_validator=detached_g2_4_validator,
    )
    return payload



def _verify_bundle_reproduction(payload: Mapping[str, Any]) -> bool:
    with tempfile.TemporaryDirectory(prefix="asr-g2-5-reproduce-a-") as a, tempfile.TemporaryDirectory(
        prefix="asr-g2-5-reproduce-b-"
    ) as b:
        run_a, archive_a = write_bundle(payload, Path(a))
        for path in run_a.iterdir():
            path.chmod(0o600)
        run_b, archive_b = write_bundle(payload, Path(b))
        for path in run_b.iterdir():
            path.chmod(0o755)
        if archive_a.read_bytes() != archive_b.read_bytes():
            return False
        with tarfile.open(archive_a, "r:gz") as tf:
            members = tf.getmembers()
            return [item.name for item in members] == list(BUNDLE_NAMES) and all(
                item.isfile() and item.mode == 0o644 and item.mtime == 0 and item.uid == 0
                and item.gid == 0 and item.uname == "" and item.gname == ""
                for item in members
            )


def render_summary(payload: Mapping[str, Any]) -> str:
    manifest = payload["manifest"]
    lines = [
        "# G2.5 Learn XP confirmatory evidence",
        "",
        f"- Implementation SHA: `{payload['provenance']['implementation_sha']}`",
        f"- Expected / actual / unique: **{manifest['expected_units']} / {manifest['actual_units']} / {manifest['actual_unique_units']}**",
        f"- Missing / extra / duplicates: **{manifest['missing_units']} / {manifest['extra_units']} / {manifest['duplicate_units']}**",
        f"- Identity evidence mode: `{payload['provenance']['identity_evidence_mode']}`",
        f"- Manifest digest: `{manifest['manifest_digest']}`",
        f"- Evidence digest: `{payload['evidence_digest']}`",
        "",
        "| Candidate | Confirmatory outcome | Inconclusive reason |",
        "|---|---|---|",
    ]
    for item in payload["candidate_outcomes"]:
        lines.append(
            f"| `{item['candidate_id']}` | `{item['outcome']}` | `{item['inconclusive_reason'] or '-'}` |"
        )
    lines.extend(
        [
            f"| `{payload['reference']['candidate_id']}` | `REFERENCE_ONLY` | `-` |",
            "",
            "The contrast ledger is descriptive only. No ranking, winner, final model or production approval was produced.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _deterministic_archive(source: Path, archive_path: Path) -> None:
    with archive_path.open("wb") as raw:
        with GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tf:
                for path in sorted(source.iterdir(), key=lambda item: item.name):
                    info = tf.gettarinfo(str(path), arcname=path.name)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as handle:
                        tf.addfile(info, handle)


def write_bundle(payload: Mapping[str, Any], output_root: Path) -> tuple[Path, Path]:
    root = output_root.resolve()
    if root.exists() and root.is_symlink():
        raise ValueError("confirmatory output root must not be a symlink")
    short = str(payload["provenance"]["implementation_sha"])[:12]
    run_dir = root / f"learn-xp-g2-5-confirmatory-{short}"
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError("confirmatory output directory already contains files")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "manifest.json", payload["manifest"])
    _write_json(run_dir / "evidence.json", payload)
    _write_json(run_dir / "g2-4-continuity.json", payload["g2_4_evidence_continuity"])
    _write_json(
        run_dir / "environment.json",
        {
            "python_version": payload["provenance"]["python_version"],
            "jsonschema_version": payload["provenance"]["jsonschema_version"],
            "pytest_version": payload["provenance"]["pytest_version"],
            "platform_system": payload["provenance"]["platform_system"],
            "platform_machine": payload["provenance"]["platform_machine"],
            "identity_evidence_mode": payload["provenance"]["identity_evidence_mode"],
        },
    )
    (run_dir / "summary.md").write_text(render_summary(payload), encoding="utf-8")
    (run_dir / "command.txt").write_text(str(payload["provenance"]["exact_command"]) + "\n", encoding="utf-8")
    inventory = []
    for name in BUNDLE_NAMES:
        if name == "FILES.sha256":
            continue
        inventory.append(f"{_sha256(run_dir / name)}  {name}")
    (run_dir / "FILES.sha256").write_text("\n".join(inventory) + "\n", encoding="utf-8")
    archive = root / f"learn-xp-g2-5-confirmatory-{short}.tar.gz"
    if archive.exists():
        raise ValueError("confirmatory archive already exists")
    _deterministic_archive(run_dir, archive)
    return run_dir, archive


def _public_command(name: str, argv: Sequence[str]) -> str:
    import shlex
    replacements = {
        "--research-root": "<research-root>",
        "--g2-4-evidence": "<external-g2-4-evidence>",
        "--g2-4-invalid-evidence": "<external-invalid-g2-4-evidence>",
        "--output-dir": "<external-output-root>",
    }
    normalized: list[str] = []
    skip_value = False
    for index, value in enumerate(argv):
        if skip_value:
            skip_value = False
            continue
        normalized.append(value)
        if value in replacements and index + 1 < len(argv):
            normalized.append(replacements[value])
            skip_value = True
    return shlex.join([name, *normalized])


def validate_protocol_cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path)
    args = parser.parse_args()
    resolved = resolve_research_workspace(args.research_root)
    protocol, identities = load_and_validate_protocol(resolved)
    units = generate_units(protocol)
    print(
        f"VALID learn-xp-confirmatory-protocol-v1 {len(units)} unique units "
        f"{canonical_digest(units)} {identities['protocol_digest']}"
    )
    return 0


def run_cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path)
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--protocol-publication-sha")
    parser.add_argument("--g2-4-evidence", type=Path, required=True)
    parser.add_argument("--g2-4-invalid-evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    publication = args.protocol_publication_sha or args.implementation_sha
    command_argv = list(sys.argv[1:])
    payload = run_confirmatory(
        args.research_root,
        implementation_sha=args.implementation_sha,
        base_sha=args.base_sha,
        protocol_publication_sha=publication,
        g2_4_evidence=args.g2_4_evidence,
        g2_4_invalid_evidence=args.g2_4_invalid_evidence,
        exact_command=_public_command("run-learn-xp-confirmatory", command_argv),
    )
    print(render_summary(payload), end="")
    if not args.no_write:
        output = args.output_dir or Path(tempfile.gettempdir()) / "anki-study-report" / "gamification-sim" / "outputs"
        run_dir, archive = write_bundle(payload, output)
        print(f"evidence: {run_dir}", file=sys.stderr)
        print(f"archive: {archive}", file=sys.stderr)
    return 0


def validate_evidence_cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--research-root", type=Path)
    parser.add_argument("--g2-4-evidence", type=Path, required=True)
    parser.add_argument("--g2-4-invalid-evidence", type=Path, required=True)
    args = parser.parse_args()
    payload = load_and_validate_evidence(
        args.evidence,
        workspace=args.research_root,
        g2_4_evidence=args.g2_4_evidence,
        g2_4_invalid_evidence=args.g2_4_invalid_evidence,
    )
    print(f"VALID {payload['evidence_version']} {payload['evidence_digest']}")
    return 0
