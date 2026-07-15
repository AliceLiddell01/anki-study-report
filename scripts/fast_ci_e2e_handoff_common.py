from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable


SCHEMA_VERSION = 1
FAST_WORKFLOW_NAME = "Fast CI"
FAST_WORKFLOW_PATH = ".github/workflows/ci-fast.yml"
FAST_PRODUCER_JOB = "fast"
PACKAGE_NAME = "anki_study_report.ankiaddon"
PACKAGE_METADATA_NAME = "package-metadata.json"
CANONICAL_FAST_COMMAND = ".\\scripts\\run_full_check.ps1 -SkipDocker"
ALLOWED_EVENTS = {"workflow_dispatch", "push", "pull_request"}
PACKAGE_SOURCES = {"source-build", "release-artifact", "fast-ci-artifact"}
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
POSITIVE_INTEGER_RE = re.compile(r"^[1-9][0-9]*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PACKAGE_ARTIFACT_RE_TEMPLATE = r"^ci-package-([0-9a-f]{{40}})-{run_id}-{attempt}$"
DIAGNOSTIC_REQUIRED = {
    "ci-summary.json",
    "ci-summary.md",
    "environment.txt",
    "logs/fast-check.log",
    "verification-plan/verification-plan.json",
    "verification-plan/verification-plan.md",
}
HANDOFF_PUBLIC_FIELDS = {
    "schemaVersion",
    "packageSource",
    "repository",
    "sourceRunId",
    "sourceRunAttempt",
    "sourceEvent",
    "sourceRef",
    "sourceTestedCommitSha",
    "sourceHeadSha",
    "sourceBaseSha",
    "diagnosticsArtifactId",
    "diagnosticsArtifactName",
    "diagnosticsArtifactDigest",
    "packageArtifactId",
    "packageArtifactName",
    "packageArtifactDigest",
    "packageSha256",
    "packageSizeBytes",
    "e2eWorkflowSourceSha",
    "e2eCheckoutSha",
    "validatedAt",
}


class HandoffError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"Could not read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_outputs(path: Path | None, values: dict[str, Any]) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            if value is None:
                rendered = ""
            elif isinstance(value, bool):
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            if "\n" in rendered or "\r" in rendered:
                raise HandoffError(f"Output {key} must be single-line")
            handle.write(f"{key}={rendered}\n")


def exact_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise HandoffError(f"{label} must be an exact 40-character hexadecimal SHA")
    return value.lower()


def optional_sha(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "null", "none"}:
        return None
    return exact_sha(value, label)


def positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise HandoffError(f"{label} must be a positive integer")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and POSITIVE_INTEGER_RE.fullmatch(value):
        return int(value)
    raise HandoffError(f"{label} must be a positive decimal integer")


def safe_text(value: Any, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(c in value for c in "\r\n\0"):
        raise HandoffError(f"{label} must be a non-empty single-line string")
    if pattern is not None and not pattern.fullmatch(value):
        raise HandoffError(f"{label} has an invalid format")
    return value


def artifact_digest(value: Any, label: str) -> str:
    value = safe_text(value, label)
    if not ARTIFACT_DIGEST_RE.fullmatch(value):
        raise HandoffError(f"{label} must be a sha256 transport digest")
    return value


def package_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_source_inputs(
    *, release_artifact_name: str, release_artifact_sha256: str, fast_ci_run_id: str
) -> dict[str, Any]:
    release_name = release_artifact_name.strip()
    release_sha = release_artifact_sha256.strip()
    fast_input = fast_ci_run_id.strip()

    if release_name and fast_input:
        raise HandoffError("release_artifact_name and fast_ci_run_id are mutually exclusive")
    if release_sha and not release_name:
        raise HandoffError("release_artifact_sha256 requires release_artifact_name")
    if release_name:
        safe_text(release_name, "release_artifact_name")
        if not SHA256_RE.fullmatch(release_sha):
            raise HandoffError("release_artifact_name requires a lowercase 64-character release_artifact_sha256")
        return {"packageSource": "release-artifact", "fastCiRunId": None}
    if fast_input:
        run_id = positive_integer(fast_input, "fast_ci_run_id")
        return {"packageSource": "fast-ci-artifact", "fastCiRunId": run_id}
    return {"packageSource": "source-build", "fastCiRunId": None}


def _repository_identity(value: Any, label: str) -> tuple[str, int]:
    if not isinstance(value, dict):
        raise HandoffError(f"{label} must be an object")
    full_name = safe_text(value.get("full_name"), f"{label}.full_name", REPOSITORY_RE)
    repository_id = positive_integer(value.get("id"), f"{label}.id")
    return full_name, repository_id


def _repository_reference_matches(value: Any, *, repository: str, repository_id: int, label: str) -> None:
    if not isinstance(value, dict):
        raise HandoffError(f"{label} must be an object")
    full_name = value.get("full_name")
    if full_name is not None:
        if safe_text(full_name, f"{label}.full_name", REPOSITORY_RE) != repository:
            raise HandoffError(f"{label} belongs to a different repository")
        return
    reference_id = value.get("id")
    if reference_id is None or positive_integer(reference_id, f"{label}.id") != repository_id:
        raise HandoffError(f"{label} repository identity is missing or mismatched")


def _artifact_row(row: Any, label: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise HandoffError(f"{label} must be an object")
    artifact_id = positive_integer(row.get("id"), f"{label}.id")
    name = safe_text(row.get("name"), f"{label}.name")
    digest = artifact_digest(row.get("digest"), f"{label}.digest")
    if row.get("expired") is not False:
        raise HandoffError(f"{label} is expired or has ambiguous expiry state")
    size = positive_integer(row.get("size_in_bytes"), f"{label}.size_in_bytes")
    return {"id": artifact_id, "name": name, "digest": digest, "sizeInBytes": size, "expired": False}

