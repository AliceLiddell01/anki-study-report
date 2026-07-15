from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
from typing import Any

from fast_ci_e2e_handoff_common import (
    ALLOWED_EVENTS, CANONICAL_FAST_COMMAND, DIAGNOSTIC_REQUIRED, FAST_PRODUCER_JOB,
    FAST_WORKFLOW_NAME, FAST_WORKFLOW_PATH, HANDOFF_PUBLIC_FIELDS, HandoffError,
    PACKAGE_ARTIFACT_RE_TEMPLATE, PACKAGE_METADATA_NAME, PACKAGE_NAME, PACKAGE_SOURCES,
    REPOSITORY_RE, SCHEMA_VERSION, SHA256_RE, _artifact_row, _repository_identity,
    _repository_reference_matches, artifact_digest, exact_sha, load_json, optional_sha,
    package_sha256, positive_integer, safe_text, utc_now,
)

def resolve_source_run(
    *, run_payload: dict[str, Any], artifacts_payload: dict[str, Any], repository: str, input_run_id: int
) -> dict[str, Any]:
    repository = safe_text(repository, "repository", REPOSITORY_RE)
    run_id = positive_integer(run_payload.get("id"), "run.id")
    if run_id != input_run_id:
        raise HandoffError(f"Run ID mismatch: expected {input_run_id}, found {run_id}")
    run_repository, run_repository_id = _repository_identity(run_payload.get("repository"), "run.repository")
    if run_repository != repository:
        raise HandoffError("Fast CI run belongs to a different repository")
    head_repository, head_repository_id = _repository_identity(run_payload.get("head_repository"), "run.head_repository")
    if head_repository != repository or head_repository_id != run_repository_id:
        raise HandoffError("Fork-origin Fast CI runs are not accepted")
    if safe_text(run_payload.get("name"), "run.name") != FAST_WORKFLOW_NAME:
        raise HandoffError("Source run workflow name is not Fast CI")
    if safe_text(run_payload.get("path"), "run.path") != FAST_WORKFLOW_PATH:
        raise HandoffError("Source run workflow path is not .github/workflows/ci-fast.yml")
    if run_payload.get("status") != "completed" or run_payload.get("conclusion") != "success":
        raise HandoffError("Source Fast CI run must be completed successfully")
    event = safe_text(run_payload.get("event"), "run.event")
    if event not in ALLOWED_EVENTS:
        raise HandoffError(f"Source run event is not allowed: {event}")
    attempt = positive_integer(run_payload.get("run_attempt"), "run.run_attempt")
    run_head_sha = exact_sha(run_payload.get("head_sha"), "run.head_sha")
    source_ref = safe_text(run_payload.get("head_branch"), "run.head_branch")

    pulls = run_payload.get("pull_requests") or []
    source_base_sha: str | None
    if event == "pull_request":
        if not isinstance(pulls, list) or len(pulls) != 1 or not isinstance(pulls[0], dict):
            raise HandoffError("Pull-request Fast CI run must expose exactly one unambiguous PR identity")
        pull = pulls[0]
        head = pull.get("head")
        base = pull.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise HandoffError("Pull-request head/base identity is missing")
        try:
            _repository_reference_matches(
                head.get("repo"), repository=repository, repository_id=run_repository_id, label="pull_request.head.repo"
            )
        except HandoffError as exc:
            raise HandoffError("Fork-origin pull-request artifacts are not accepted") from exc
        _repository_reference_matches(
            base.get("repo"), repository=repository, repository_id=run_repository_id, label="pull_request.base.repo"
        )
        source_head_sha = exact_sha(head.get("sha"), "pull_request.head.sha")
        source_base_sha = exact_sha(base.get("sha"), "pull_request.base.sha")
    else:
        if pulls:
            raise HandoffError(f"{event} source run must not carry pull-request identity")
        source_head_sha = run_head_sha
        source_base_sha = None

    rows = artifacts_payload.get("artifacts")
    if not isinstance(rows, list):
        raise HandoffError("Artifacts API response must contain an artifacts array")
    total_count = positive_integer(artifacts_payload.get("total_count"), "artifacts.total_count")
    if total_count != len(rows):
        raise HandoffError("Artifacts API response is incomplete; refusing ambiguous cross-run resolution")
    artifacts = [_artifact_row(row, f"artifact[{index}]") for index, row in enumerate(rows)]
    diagnostics_name = f"ci-fast-{run_id}-{attempt}"
    diagnostics = [row for row in artifacts if row["name"] == diagnostics_name]
    package_re = re.compile(PACKAGE_ARTIFACT_RE_TEMPLATE.format(run_id=run_id, attempt=attempt))
    packages: list[tuple[dict[str, Any], str]] = []
    for row in artifacts:
        match = package_re.fullmatch(row["name"])
        if match:
            packages.append((row, match.group(1)))
    if len(diagnostics) != 1:
        raise HandoffError(f"Expected exactly one diagnostics artifact named {diagnostics_name}")
    if len(packages) != 1:
        raise HandoffError("Expected exactly one package artifact matching the strict Fast CI package pattern")
    package, candidate_tested_sha = packages[0]
    if diagnostics[0]["id"] == package["id"]:
        raise HandoffError("Diagnostics and package artifacts must have distinct IDs")

    resolution = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": repository,
        "sourceRunId": run_id,
        "sourceRunAttempt": attempt,
        "sourceEvent": event,
        "sourceRunHeadSha": run_head_sha,
        "sourceHeadSha": source_head_sha,
        "sourceBaseSha": source_base_sha,
        "sourceBranch": source_ref,
        "diagnosticsArtifact": diagnostics[0],
        "packageArtifact": package,
        "packageCandidateTestedSha": candidate_tested_sha,
    }
    return resolution


def _inventory(directory: Path) -> tuple[list[str], list[Path]]:
    if not directory.is_dir():
        raise HandoffError(f"Artifact directory does not exist: {directory}")
    files: list[Path] = []
    names: list[str] = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise HandoffError(f"Artifact contains a symlink: {path.relative_to(directory)}")
        if path.is_dir():
            continue
        relative = path.relative_to(directory).as_posix()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise HandoffError(f"Artifact contains an unsafe path: {relative}")
        files.append(path)
        names.append(relative)
    return names, files


def validate_diagnostics(*, resolution: dict[str, Any], directory: Path) -> dict[str, Any]:
    names, _ = _inventory(directory)
    name_set = set(names)
    missing = sorted(DIAGNOSTIC_REQUIRED - name_set)
    if missing:
        raise HandoffError(f"Diagnostics artifact is missing required files: {missing}")
    forbidden = [
        name for name in names
        if name == PACKAGE_METADATA_NAME
        or name.endswith(".ankiaddon")
        or name.startswith("package/")
        or name.startswith("ci-package/")
    ]
    if forbidden:
        raise HandoffError(f"Diagnostics artifact contains package data: {forbidden}")

    summary = load_json(directory / "ci-summary.json")
    if summary.get("schemaVersion") != 1:
        raise HandoffError("Diagnostics schemaVersion must be 1")
    if summary.get("repository") != resolution["repository"]:
        raise HandoffError("Diagnostics repository mismatch")
    if summary.get("workflow") != FAST_WORKFLOW_NAME:
        raise HandoffError("Diagnostics workflow mismatch")
    if summary.get("event") != resolution["sourceEvent"]:
        raise HandoffError("Diagnostics event mismatch")
    if positive_integer(summary.get("runId"), "diagnostics.runId") != resolution["sourceRunId"]:
        raise HandoffError("Diagnostics run ID mismatch")
    if positive_integer(summary.get("runAttempt"), "diagnostics.runAttempt") != resolution["sourceRunAttempt"]:
        raise HandoffError("Diagnostics run attempt mismatch")
    if summary.get("result") != "success":
        raise HandoffError("Diagnostics result must be success")
    if summary.get("command") != CANONICAL_FAST_COMMAND:
        raise HandoffError("Diagnostics canonical command mismatch")
    source_ref = safe_text(summary.get("ref"), "diagnostics.ref")
    tested_sha = exact_sha(summary.get("commitSha"), "diagnostics.commitSha")
    if tested_sha != resolution["packageCandidateTestedSha"]:
        raise HandoffError("Diagnostics tested SHA does not match package artifact name")
    if resolution["sourceEvent"] in {"push", "workflow_dispatch"} and tested_sha != resolution["sourceRunHeadSha"]:
        raise HandoffError("Non-PR Fast CI tested SHA must equal the source run head SHA")
    artifact_files = summary.get("artifactFiles")
    if not isinstance(artifact_files, list) or any(not isinstance(item, str) for item in artifact_files):
        raise HandoffError("Diagnostics artifactFiles must be a string array")
    if set(artifact_files) != name_set:
        raise HandoffError("Diagnostics artifactFiles does not match the downloaded diagnostics inventory")
    if any(name.endswith(".ankiaddon") or name == PACKAGE_METADATA_NAME or name.startswith("package/") for name in artifact_files):
        raise HandoffError("Diagnostics artifactFiles contains package data")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": resolution["repository"],
        "sourceRunId": resolution["sourceRunId"],
        "sourceRunAttempt": resolution["sourceRunAttempt"],
        "sourceEvent": resolution["sourceEvent"],
        "sourceRef": source_ref,
        "testedCommitSha": tested_sha,
        "sourceHeadSha": resolution["sourceHeadSha"],
        "sourceBaseSha": resolution["sourceBaseSha"],
        "artifactFiles": sorted(name_set),
    }


def _assert_safe_public_value(value: Any, label: str) -> None:
    if value is None or isinstance(value, (int, bool)):
        return
    if not isinstance(value, str):
        raise HandoffError(f"Public evidence field {label} has an unsupported type")
    lowered = value.lower()
    secret_fragments = ("token=", "author" + "ization:", "bearer ", "github" + "_pat_", "ghp" + "_")
    if any(fragment in lowered for fragment in secret_fragments):
        raise HandoffError(f"Public evidence field {label} contains secret-like content")
    if re.search(r"(?i)[a-z]:[\\/]users[\\/]", value) or re.search(r"/home/(?!e2e(?:/|$))", value):
        raise HandoffError(f"Public evidence field {label} contains a private local path")
    if "\r" in value or "\n" in value:
        raise HandoffError(f"Public evidence field {label} must be single-line")


def validate_package_handoff(
    *,
    resolution: dict[str, Any],
    diagnostics: dict[str, Any],
    directory: Path,
    e2e_workflow_source_sha: str,
    e2e_checkout_sha: str,
) -> dict[str, Any]:
    names, files = _inventory(directory)
    if names != sorted([PACKAGE_METADATA_NAME, PACKAGE_NAME]):
        raise HandoffError(f"Package artifact must contain exactly {PACKAGE_NAME} and {PACKAGE_METADATA_NAME}; found {names}")
    if any(path.is_symlink() for path in files):
        raise HandoffError("Package artifact must not contain symlinks")

    metadata = load_json(directory / PACKAGE_METADATA_NAME)
    package = directory / PACKAGE_NAME
    tested_sha = exact_sha(metadata.get("testedCommitSha"), "metadata.testedCommitSha")
    source_head_sha = exact_sha(metadata.get("sourceHeadSha"), "metadata.sourceHeadSha")
    source_base_sha = optional_sha(metadata.get("sourceBaseSha"), "metadata.sourceBaseSha")
    workflow_source_sha = exact_sha(e2e_workflow_source_sha, "e2eWorkflowSourceSha")
    checkout_sha = exact_sha(e2e_checkout_sha, "e2eCheckoutSha")

    exact_expected = {
        "schemaVersion": 1,
        "repository": resolution["repository"],
        "workflowName": FAST_WORKFLOW_NAME,
        "workflowPath": FAST_WORKFLOW_PATH,
        "producerJob": FAST_PRODUCER_JOB,
        "eventName": resolution["sourceEvent"],
        "ref": diagnostics["sourceRef"],
        "runId": resolution["sourceRunId"],
        "runAttempt": resolution["sourceRunAttempt"],
        "artifactName": resolution["packageArtifact"]["name"],
        "packageName": PACKAGE_NAME,
    }
    for field, expected in exact_expected.items():
        if metadata.get(field) != expected:
            raise HandoffError(f"Package metadata {field} mismatch: expected {expected!r}, found {metadata.get(field)!r}")
    if tested_sha != diagnostics["testedCommitSha"] or tested_sha != checkout_sha:
        raise HandoffError("Package metadata tested SHA must match diagnostics and exact checkout HEAD")
    if source_head_sha != resolution["sourceHeadSha"] or source_head_sha != workflow_source_sha:
        raise HandoffError("Package source head must match source-run identity and initial E2E workflow source SHA")
    if source_base_sha != resolution["sourceBaseSha"]:
        raise HandoffError("Package source base SHA does not match source-run identity")
    if resolution["sourceEvent"] in {"push", "workflow_dispatch"} and source_base_sha is not None:
        raise HandoffError("Push/workflow_dispatch package metadata must use null sourceBaseSha")

    actual_sha = package_sha256(package)
    actual_size = package.stat().st_size
    if not SHA256_RE.fullmatch(str(metadata.get("packageSha256") or "")):
        raise HandoffError("Package metadata packageSha256 must be lowercase 64-hex")
    if metadata.get("packageSha256") != actual_sha:
        raise HandoffError("Package metadata SHA-256 does not match downloaded package bytes")
    if isinstance(metadata.get("packageSizeBytes"), bool) or metadata.get("packageSizeBytes") != actual_size or actual_size <= 0:
        raise HandoffError("Package metadata size does not match downloaded package bytes")

    evidence = {
        "schemaVersion": SCHEMA_VERSION,
        "packageSource": "fast-ci-artifact",
        "repository": resolution["repository"],
        "sourceRunId": resolution["sourceRunId"],
        "sourceRunAttempt": resolution["sourceRunAttempt"],
        "sourceEvent": resolution["sourceEvent"],
        "sourceRef": diagnostics["sourceRef"],
        "sourceTestedCommitSha": tested_sha,
        "sourceHeadSha": source_head_sha,
        "sourceBaseSha": source_base_sha,
        "diagnosticsArtifactId": resolution["diagnosticsArtifact"]["id"],
        "diagnosticsArtifactName": resolution["diagnosticsArtifact"]["name"],
        "diagnosticsArtifactDigest": resolution["diagnosticsArtifact"]["digest"],
        "packageArtifactId": resolution["packageArtifact"]["id"],
        "packageArtifactName": resolution["packageArtifact"]["name"],
        "packageArtifactDigest": resolution["packageArtifact"]["digest"],
        "packageSha256": actual_sha,
        "packageSizeBytes": actual_size,
        "e2eWorkflowSourceSha": workflow_source_sha,
        "e2eCheckoutSha": checkout_sha,
        "validatedAt": utc_now(),
    }
    if set(evidence) != HANDOFF_PUBLIC_FIELDS:
        raise HandoffError("Handoff evidence fields differ from the public allowlist")
    if evidence["packageSource"] not in PACKAGE_SOURCES:
        raise HandoffError("Invalid packageSource in public evidence")
    for key, value in evidence.items():
        _assert_safe_public_value(value, key)
    return evidence

