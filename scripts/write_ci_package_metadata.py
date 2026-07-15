from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


SCHEMA_VERSION = 1
WORKFLOW_NAME = "Fast CI"
WORKFLOW_PATH = ".github/workflows/ci-fast.yml"
PRODUCER_JOB = "fast"
PACKAGE_NAME = "anki_study_report.ankiaddon"
METADATA_NAME = "package-metadata.json"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
EVENT_RE = re.compile(r"^[A-Za-z0-9_]+$")
PACKAGE_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PUBLIC_FIELDS = {
    "schemaVersion",
    "repository",
    "workflowName",
    "workflowPath",
    "producerJob",
    "eventName",
    "ref",
    "testedCommitSha",
    "sourceHeadSha",
    "sourceBaseSha",
    "runId",
    "runAttempt",
    "artifactName",
    "packageName",
    "packageSha256",
    "packageSizeBytes",
    "createdAt",
}


class MetadataError(ValueError):
    pass


def normalize_sha(value: str, label: str) -> str:
    if not SHA_RE.fullmatch(value or ""):
        raise MetadataError(f"{label} must be an exact 40-character hexadecimal SHA")
    return value.lower()


def normalize_optional_sha(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MetadataError(f"{label} must be a SHA string or null")
    if value.strip().lower() in {"", "null", "none"}:
        return None
    return normalize_sha(value.strip(), label)


def require_positive(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MetadataError(f"{label} must be a positive integer")
    return value


def require_safe_text(value: str, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if not value or value != value.strip() or any(char in value for char in "\r\n\0"):
        raise MetadataError(f"{label} must be a non-empty single-line value")
    if pattern is not None and not pattern.fullmatch(value):
        raise MetadataError(f"{label} has an invalid format")
    return value


def package_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_timestamp(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not value.endswith("Z"):
        raise MetadataError("createdAt must be a UTC ISO-8601 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MetadataError("createdAt must be a valid UTC ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MetadataError("createdAt must use UTC")
    return value


def expected_artifact_name(tested_sha: str, run_id: int, run_attempt: int) -> str:
    return f"ci-package-{tested_sha}-{run_id}-{run_attempt}"


def validate_inventory(directory: Path) -> tuple[Path, Path]:
    if not directory.is_dir():
        raise MetadataError(f"Package artifact directory does not exist: {directory}")
    children = list(directory.iterdir())
    if any(child.is_dir() or child.is_symlink() for child in children):
        raise MetadataError("Package artifact directory must not contain directories or symlinks")
    names = {child.name for child in children}
    expected = {PACKAGE_NAME, METADATA_NAME}
    if names != expected:
        raise MetadataError(
            f"Package artifact directory must contain exactly {sorted(expected)}; found {sorted(names)}"
        )
    return directory / PACKAGE_NAME, directory / METADATA_NAME


def validate_metadata(metadata: dict[str, Any], package_path: Path) -> dict[str, Any]:
    if set(metadata) != PUBLIC_FIELDS:
        raise MetadataError(
            f"Metadata fields differ from schema v1: expected {sorted(PUBLIC_FIELDS)}, found {sorted(metadata)}"
        )
    if metadata["schemaVersion"] != SCHEMA_VERSION:
        raise MetadataError("schemaVersion must be 1")
    if metadata["workflowName"] != WORKFLOW_NAME:
        raise MetadataError("workflowName mismatch")
    if metadata["workflowPath"] != WORKFLOW_PATH:
        raise MetadataError("workflowPath mismatch")
    if metadata["producerJob"] != PRODUCER_JOB:
        raise MetadataError("producerJob mismatch")
    if metadata["packageName"] != PACKAGE_NAME:
        raise MetadataError("packageName mismatch")

    repository = require_safe_text(str(metadata["repository"]), "repository", REPOSITORY_RE)
    event_name = require_safe_text(str(metadata["eventName"]), "eventName", EVENT_RE)
    ref = require_safe_text(str(metadata["ref"]), "ref")
    tested_sha = normalize_sha(str(metadata["testedCommitSha"]), "testedCommitSha")
    source_head_sha = normalize_sha(str(metadata["sourceHeadSha"]), "sourceHeadSha")
    source_base_sha = normalize_optional_sha(metadata["sourceBaseSha"], "sourceBaseSha")
    run_id = require_positive(metadata["runId"], "runId")
    run_attempt = require_positive(metadata["runAttempt"], "runAttempt")
    artifact_name = require_safe_text(str(metadata["artifactName"]), "artifactName")
    expected_name = expected_artifact_name(tested_sha, run_id, run_attempt)
    if artifact_name != expected_name:
        raise MetadataError(f"artifactName must be {expected_name}")
    created_at = utc_timestamp(str(metadata["createdAt"]))

    if not package_path.is_file() or package_path.name != PACKAGE_NAME:
        raise MetadataError(f"Expected staged package {PACKAGE_NAME}")
    actual_sha = package_sha256(package_path)
    actual_size = package_path.stat().st_size
    if not PACKAGE_SHA_RE.fullmatch(str(metadata["packageSha256"])):
        raise MetadataError("packageSha256 must be a lowercase 64-character hexadecimal SHA-256")
    if metadata["packageSha256"] != actual_sha:
        raise MetadataError("packageSha256 does not match staged package bytes")
    if isinstance(metadata["packageSizeBytes"], bool) or metadata["packageSizeBytes"] != actual_size:
        raise MetadataError("packageSizeBytes does not match staged package bytes")

    metadata.update(
        repository=repository,
        eventName=event_name,
        ref=ref,
        testedCommitSha=tested_sha,
        sourceHeadSha=source_head_sha,
        sourceBaseSha=source_base_sha,
        runId=run_id,
        runAttempt=run_attempt,
        artifactName=artifact_name,
        createdAt=created_at,
    )
    return metadata


def create_package_artifact(
    *,
    package: Path,
    output_directory: Path,
    repository: str,
    event_name: str,
    ref: str,
    tested_commit_sha: str,
    source_head_sha: str,
    source_base_sha: str | None,
    run_id: int,
    run_attempt: int,
    artifact_name: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    if package.is_symlink():
        raise MetadataError("Package source must not be a symlink")
    package = package.resolve()
    output_directory = output_directory.resolve()
    if not package.is_file():
        raise MetadataError(f"Package does not exist: {package}")
    if package.name != PACKAGE_NAME:
        raise MetadataError(f"Package filename must be {PACKAGE_NAME}")

    repository = require_safe_text(repository, "repository", REPOSITORY_RE)
    event_name = require_safe_text(event_name, "eventName", EVENT_RE)
    ref = require_safe_text(ref, "ref")
    tested_sha = normalize_sha(tested_commit_sha, "testedCommitSha")
    source_head = normalize_sha(source_head_sha, "sourceHeadSha")
    source_base = normalize_optional_sha(source_base_sha, "sourceBaseSha")
    run_id = require_positive(run_id, "runId")
    run_attempt = require_positive(run_attempt, "runAttempt")
    artifact_name = require_safe_text(artifact_name, "artifactName")
    expected_name = expected_artifact_name(tested_sha, run_id, run_attempt)
    if artifact_name != expected_name:
        raise MetadataError(f"artifactName must be {expected_name}")

    if output_directory.exists():
        if not output_directory.is_dir() or any(output_directory.iterdir()):
            raise MetadataError("Output directory must be absent or empty")
    else:
        output_directory.mkdir(parents=True, exist_ok=False)

    source_sha = package_sha256(package)
    source_size = package.stat().st_size
    staged_package = output_directory / PACKAGE_NAME
    shutil.copyfile(package, staged_package)
    if package_sha256(staged_package) != source_sha or staged_package.stat().st_size != source_size:
        raise MetadataError("Staged package bytes differ from source package")

    metadata: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": repository,
        "workflowName": WORKFLOW_NAME,
        "workflowPath": WORKFLOW_PATH,
        "producerJob": PRODUCER_JOB,
        "eventName": event_name,
        "ref": ref,
        "testedCommitSha": tested_sha,
        "sourceHeadSha": source_head,
        "sourceBaseSha": source_base,
        "runId": run_id,
        "runAttempt": run_attempt,
        "artifactName": artifact_name,
        "packageName": PACKAGE_NAME,
        "packageSha256": source_sha,
        "packageSizeBytes": source_size,
        "createdAt": utc_timestamp(created_at),
    }
    metadata_path = output_directory / METADATA_NAME
    temporary = output_directory / f".{METADATA_NAME}.tmp"
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(metadata_path)

    verified = verify_package_artifact(output_directory)
    if package_sha256(package) != source_sha or package.stat().st_size != source_size:
        raise MetadataError("Source package bytes changed while preparing the artifact")
    return verified


def verify_package_artifact(output_directory: Path) -> dict[str, Any]:
    package_path, metadata_path = validate_inventory(output_directory.resolve())
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataError(f"Could not read package metadata: {exc}") from exc
    if not isinstance(metadata, dict):
        raise MetadataError("Package metadata must be a JSON object")
    return validate_metadata(metadata, package_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or verify the exact Fast CI package artifact and package-metadata.json."
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--package", type=Path)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--repository")
    parser.add_argument("--event-name")
    parser.add_argument("--ref")
    parser.add_argument("--tested-commit-sha")
    parser.add_argument("--source-head-sha")
    parser.add_argument("--source-base-sha")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--run-attempt", type=int)
    parser.add_argument("--artifact-name")
    parser.add_argument("--created-at", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.verify_only:
            metadata = verify_package_artifact(args.output_directory)
            print(
                f"Verified {metadata['artifactName']} "
                f"(package sha256={metadata['packageSha256']}, size={metadata['packageSizeBytes']})."
            )
            return 0

        required = {
            "package": args.package,
            "repository": args.repository,
            "event-name": args.event_name,
            "ref": args.ref,
            "tested-commit-sha": args.tested_commit_sha,
            "source-head-sha": args.source_head_sha,
            "run-id": args.run_id,
            "run-attempt": args.run_attempt,
            "artifact-name": args.artifact_name,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error(f"creation mode requires: {', '.join(missing)}")
        metadata = create_package_artifact(
            package=args.package,
            output_directory=args.output_directory,
            repository=args.repository,
            event_name=args.event_name,
            ref=args.ref,
            tested_commit_sha=args.tested_commit_sha,
            source_head_sha=args.source_head_sha,
            source_base_sha=args.source_base_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            artifact_name=args.artifact_name,
            created_at=args.created_at,
        )
        print(
            f"Created {metadata['artifactName']} "
            f"(package sha256={metadata['packageSha256']}, size={metadata['packageSizeBytes']})."
        )
        return 0
    except (MetadataError, OSError, shutil.Error) as exc:
        print(f"Fast CI package metadata error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
