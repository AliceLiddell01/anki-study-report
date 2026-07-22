from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_fast_ci_e2e_handoff", ROOT / "scripts" / "verify_fast_ci_e2e_handoff.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

HandoffError = MODULE.HandoffError
REPO = "AliceLiddell01/anki-study-report"
RUN_ID = 123456789
ATTEMPT = 1
TESTED = "a" * 40
HEAD = "b" * 40
BASE = "c" * 40
DIAGNOSTICS_ID = 101
PACKAGE_ID = 102
DIAGNOSTICS_DIGEST = "sha256:" + "1" * 64
PACKAGE_DIGEST = "sha256:" + "2" * 64

PR_ASSOC = {"head": {"sha": "d" * 40, "repo": {"id": 1297299947}}, "base": {"sha": BASE, "repo": {"id": 1297299947}}}


def run_payload(event: str = "workflow_dispatch") -> dict:
    payload = {
        "id": RUN_ID,
        "name": "Fast CI",
        "path": ".github/workflows/ci-fast.yml",
        "status": "completed",
        "conclusion": "success",
        "event": event,
        "run_attempt": ATTEMPT,
        "head_sha": TESTED if event != "pull_request" else HEAD,
        "head_branch": "chatgpt/ci-optimization-stage-3-e2e-package-handoff",
        "repository": {"full_name": REPO, "id": 1297299947},
        "head_repository": {"full_name": REPO, "id": 1297299947},
        "pull_requests": [],
    }
    if event == "pull_request":
        payload["pull_requests"] = [
            {
                "head": {"sha": HEAD, "repo": {"id": 1297299947}},
                "base": {"sha": BASE, "repo": {"id": 1297299947}},
            }
        ]
    return payload


def artifacts_payload(tested: str = TESTED) -> dict:
    return {
        "total_count": 2,
        "artifacts": [
            {
                "id": DIAGNOSTICS_ID,
                "name": f"ci-fast-{RUN_ID}-{ATTEMPT}",
                "digest": DIAGNOSTICS_DIGEST,
                "expired": False,
                "size_in_bytes": 100,
            },
            {
                "id": PACKAGE_ID,
                "name": f"ci-package-{tested}-{RUN_ID}-{ATTEMPT}",
                "digest": PACKAGE_DIGEST,
                "expired": False,
                "size_in_bytes": 200,
            },
        ],
    }


def resolve(event: str = "workflow_dispatch", *, tested: str = TESTED) -> dict:
    return MODULE.resolve_source_run(
        run_payload=run_payload(event),
        artifacts_payload=artifacts_payload(tested),
        repository=REPO,
        input_run_id=RUN_ID,
    )


def create_diagnostics(root: Path, resolution: dict, *, tested: str = TESTED, result: str = "success") -> dict:
    files = {
        "ci-summary.md": "# Fast CI summary\n",
        "environment.txt": "safe=true\n",
        "logs/fast-check.log": "Full check completed.\n",
        "verification-plan/verification-plan.json": "{}\n",
        "verification-plan/verification-plan.md": "# plan\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    inventory = sorted([*files, "ci-summary.json"])
    summary = {
        "schemaVersion": 1,
        "repository": REPO,
        "commitSha": tested,
        "ref": "refs/pull/33/merge" if resolution["sourceEvent"] == "pull_request" else "refs/heads/feature",
        "event": resolution["sourceEvent"],
        "workflow": "Fast CI",
        "runId": str(RUN_ID),
        "runAttempt": str(ATTEMPT),
        "command": ".\\scripts\\run_full_check.ps1 -SkipDocker",
        "result": result,
        "artifactFiles": inventory,
    }
    (root / "ci-summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return summary


def create_package(root: Path, resolution: dict, diagnostics: dict, *, workflow_source: str | None = None) -> tuple[bytes, dict]:
    payload = b"PK\x03\x04exact package bytes"
    package = root / "anki_study_report.ankiaddon"
    package.parent.mkdir(parents=True, exist_ok=True)
    package.write_bytes(payload)
    source_head = workflow_source or resolution["sourceHeadSha"]
    metadata = {
        "schemaVersion": 1,
        "repository": REPO,
        "workflowName": "Fast CI",
        "workflowPath": ".github/workflows/ci-fast.yml",
        "producerJob": "fast",
        "eventName": resolution["sourceEvent"],
        "ref": diagnostics["sourceRef"],
        "testedCommitSha": diagnostics["testedCommitSha"],
        "sourceHeadSha": source_head,
        "sourceBaseSha": resolution["sourceBaseSha"],
        "runId": RUN_ID,
        "runAttempt": ATTEMPT,
        "artifactName": resolution["packageArtifact"]["name"],
        "packageName": "anki_study_report.ankiaddon",
        "packageSha256": hashlib.sha256(payload).hexdigest(),
        "packageSizeBytes": len(payload),
        "createdAt": "2026-07-16T00:00:00Z",
    }
    (root / "package-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return payload, metadata


def valid_handoff(tmp_path: Path, event: str = "workflow_dispatch"):
    tested = "d" * 40 if event == "pull_request" else TESTED
    resolution = resolve(event, tested=tested)
    diagnostics_dir = tmp_path / "diagnostics"
    create_diagnostics(diagnostics_dir, resolution, tested=tested)
    diagnostics = MODULE.validate_diagnostics(resolution=resolution, directory=diagnostics_dir)
    package_dir = tmp_path / "package"
    create_package(package_dir, resolution, diagnostics)
    evidence = MODULE.validate_package_handoff(
        resolution=resolution,
        diagnostics=diagnostics,
        directory=package_dir,
        e2e_workflow_source_sha=resolution["sourceHeadSha"],
        e2e_checkout_sha=diagnostics["testedCommitSha"],
    )
    return resolution, diagnostics, package_dir, evidence


def test_source_modes_are_mutually_exclusive_and_release_sha_is_strict():
    assert MODULE.validate_source_inputs(release_artifact_name="", release_artifact_sha256="", fast_ci_run_id="") == {
        "packageSource": "source-build",
        "fastCiRunId": None,
    }
    assert MODULE.validate_source_inputs(
        release_artifact_name="release-bundle-1-1", release_artifact_sha256="a" * 64, fast_ci_run_id=""
    )["packageSource"] == "release-artifact"
    assert MODULE.validate_source_inputs(release_artifact_name="", release_artifact_sha256="", fast_ci_run_id="42") == {
        "packageSource": "fast-ci-artifact",
        "fastCiRunId": 42,
    }
    with pytest.raises(HandoffError, match="mutually exclusive"):
        MODULE.validate_source_inputs(release_artifact_name="release", release_artifact_sha256="a" * 64, fast_ci_run_id="42")
    with pytest.raises(HandoffError, match="requires release_artifact_name"):
        MODULE.validate_source_inputs(release_artifact_name="", release_artifact_sha256="a" * 64, fast_ci_run_id="")
    with pytest.raises(HandoffError, match="positive decimal"):
        MODULE.validate_source_inputs(release_artifact_name="", release_artifact_sha256="", fast_ci_run_id="0")


@pytest.mark.parametrize(
    ("event", "pulls"),
    [("workflow_dispatch", []), ("workflow_dispatch", [PR_ASSOC]), ("workflow_dispatch", [PR_ASSOC, PR_ASSOC]), ("push", [PR_ASSOC])],
)
def test_non_pr_source_run_ignores_advisory_pull_request_associations(event: str, pulls: list[dict]):
    payload = run_payload(event)
    payload["pull_requests"] = copy.deepcopy(pulls)
    resolution = MODULE.resolve_source_run(
        run_payload=payload, artifacts_payload=artifacts_payload(), repository=REPO, input_run_id=RUN_ID
    )
    assert (resolution["sourceEvent"], resolution["sourceHeadSha"], resolution["sourceBaseSha"]) == (event, payload["head_sha"], None)
    assert resolution["diagnosticsArtifact"]["id"] == DIAGNOSTICS_ID
    assert resolution["packageArtifact"]["id"] == PACKAGE_ID


def test_valid_same_repository_pr_synthetic_merge_run():
    synthetic = "d" * 40
    resolution = resolve("pull_request", tested=synthetic)
    assert resolution["sourceRunHeadSha"] == HEAD
    assert resolution["sourceHeadSha"] == HEAD
    assert resolution["sourceBaseSha"] == BASE
    assert resolution["packageCandidateTestedSha"] == synthetic


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda p: p.update(status="in_progress"), "completed successfully"),
        (lambda p: p.update(conclusion="failure"), "completed successfully"),
        (lambda p: p.update(name="Other CI"), "workflow name"),
        (lambda p: p.update(path=".github/workflows/other.yml"), "workflow path"),
        (lambda p: p.update(repository={"full_name": "other/repo", "id": 999}), "different repository"),
        (lambda p: p.update(head_repository={"full_name": "fork/repo", "id": 999}), "Fork-origin"),
        (lambda p: p.update(event="workflow_run"), "not allowed"),
    ],
)
def test_source_run_rejections(mutation, message: str):
    payload = run_payload()
    mutation(payload)
    with pytest.raises(HandoffError, match=message):
        MODULE.resolve_source_run(
            run_payload=payload, artifacts_payload=artifacts_payload(), repository=REPO, input_run_id=RUN_ID
        )


def test_pull_request_requires_unambiguous_same_repo_identity():
    payload = run_payload("pull_request")
    payload["pull_requests"] = []
    with pytest.raises(HandoffError, match="exactly one"):
        MODULE.resolve_source_run(run_payload=payload, artifacts_payload=artifacts_payload("d" * 40), repository=REPO, input_run_id=RUN_ID)
    payload = run_payload("pull_request")
    payload["pull_requests"][0]["head"]["repo"]["id"] = 999
    with pytest.raises(HandoffError, match="Fork-origin"):
        MODULE.resolve_source_run(run_payload=payload, artifacts_payload=artifacts_payload("d" * 40), repository=REPO, input_run_id=RUN_ID)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["pull_requests"].append(copy.deepcopy(p["pull_requests"][0])),
        lambda p: p["pull_requests"][0].update(head=None),
        lambda p: p["pull_requests"][0].update(base=None),
    ],
)
def test_pull_request_rejects_ambiguous_or_malformed_identity(mutation):
    payload = run_payload("pull_request")
    mutation(payload)
    with pytest.raises(HandoffError, match="exactly one|head/base identity"):
        MODULE.resolve_source_run(run_payload=payload, artifacts_payload=artifacts_payload("d" * 40), repository=REPO, input_run_id=RUN_ID)


def test_expired_missing_and_duplicate_artifacts_fail():
    expired = artifacts_payload()
    expired["artifacts"][1]["expired"] = True
    with pytest.raises(HandoffError, match="expired"):
        MODULE.resolve_source_run(run_payload=run_payload(), artifacts_payload=expired, repository=REPO, input_run_id=RUN_ID)
    missing = artifacts_payload()
    missing["artifacts"] = missing["artifacts"][1:]
    missing["total_count"] = 1
    with pytest.raises(HandoffError, match="diagnostics"):
        MODULE.resolve_source_run(run_payload=run_payload(), artifacts_payload=missing, repository=REPO, input_run_id=RUN_ID)
    duplicate = artifacts_payload()
    duplicate["artifacts"].append(copy.deepcopy(duplicate["artifacts"][1]))
    duplicate["artifacts"][-1]["id"] = 103
    duplicate["total_count"] = 3
    with pytest.raises(HandoffError, match="exactly one package"):
        MODULE.resolve_source_run(run_payload=run_payload(), artifacts_payload=duplicate, repository=REPO, input_run_id=RUN_ID)


def test_incomplete_artifact_api_page_fails_closed():
    payload = artifacts_payload()
    payload["total_count"] = 3
    with pytest.raises(HandoffError, match="incomplete"):
        MODULE.resolve_source_run(
            run_payload=run_payload(), artifacts_payload=payload, repository=REPO, input_run_id=RUN_ID
        )


def test_invalid_artifact_name_and_transport_digest_fail():
    payload = artifacts_payload()
    payload["artifacts"][1]["name"] = f"ci-package-wrong-{RUN_ID}-{ATTEMPT}"
    with pytest.raises(HandoffError, match="exactly one package"):
        MODULE.resolve_source_run(run_payload=run_payload(), artifacts_payload=payload, repository=REPO, input_run_id=RUN_ID)
    payload = artifacts_payload()
    payload["artifacts"][1]["digest"] = "sha256:bad"
    with pytest.raises(HandoffError, match="transport digest"):
        MODULE.resolve_source_run(run_payload=run_payload(), artifacts_payload=payload, repository=REPO, input_run_id=RUN_ID)


def test_diagnostics_validation_passes_and_rejects_package_content(tmp_path: Path):
    resolution = resolve()
    diagnostics_dir = tmp_path / "diagnostics"
    create_diagnostics(diagnostics_dir, resolution)
    validated = MODULE.validate_diagnostics(resolution=resolution, directory=diagnostics_dir)
    assert validated["testedCommitSha"] == TESTED
    (diagnostics_dir / "package-metadata.json").write_text("{}", encoding="utf-8")
    with pytest.raises(HandoffError, match="package data"):
        MODULE.validate_diagnostics(resolution=resolution, directory=diagnostics_dir)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("result", "failure", "result"),
        ("runId", 999, "run ID"),
        ("runAttempt", 2, "run attempt"),
        ("commitSha", "e" * 40, "package artifact name"),
        ("command", "other", "canonical command"),
    ],
)
def test_diagnostics_identity_mismatches_fail(tmp_path: Path, field: str, value, message: str):
    resolution = resolve()
    diagnostics_dir = tmp_path / "diagnostics"
    summary = create_diagnostics(diagnostics_dir, resolution)
    summary[field] = value
    (diagnostics_dir / "ci-summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(HandoffError, match=message):
        MODULE.validate_diagnostics(resolution=resolution, directory=diagnostics_dir)


def test_non_pr_diagnostics_tested_sha_must_match_run_head(tmp_path: Path):
    resolution = resolve(tested="e" * 40)
    directory = tmp_path / "diagnostics"
    create_diagnostics(directory, resolution, tested="e" * 40)
    with pytest.raises(HandoffError, match="source run head SHA"):
        MODULE.validate_diagnostics(resolution=resolution, directory=directory)


def test_diagnostics_inventory_must_match_summary(tmp_path: Path):
    resolution = resolve()
    directory = tmp_path / "diagnostics"
    summary = create_diagnostics(directory, resolution)
    summary["artifactFiles"] = summary["artifactFiles"][:-1]
    (directory / "ci-summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(HandoffError, match="inventory"):
        MODULE.validate_diagnostics(resolution=resolution, directory=directory)


@pytest.mark.parametrize("event", ["workflow_dispatch", "push", "pull_request"])
def test_complete_handoff_evidence_for_all_allowed_events(tmp_path: Path, event: str):
    _, _, _, evidence = valid_handoff(tmp_path, event)
    assert set(evidence) == MODULE.HANDOFF_PUBLIC_FIELDS
    assert evidence["packageSource"] == "fast-ci-artifact"
    assert evidence["diagnosticsArtifactDigest"] == DIAGNOSTICS_DIGEST
    assert evidence["packageArtifactDigest"] == PACKAGE_DIGEST
    assert evidence["e2eWorkflowSourceSha"] == evidence["sourceHeadSha"]
    if event == "pull_request":
        assert evidence["sourceTestedCommitSha"] != evidence["sourceHeadSha"]
        assert evidence["sourceBaseSha"] == BASE
    else:
        assert evidence["sourceBaseSha"] is None


def test_package_metadata_tested_head_base_and_checkout_mismatches_fail(tmp_path: Path):
    resolution, diagnostics, package_dir, _ = valid_handoff(tmp_path / "valid", "pull_request")
    metadata_path = package_dir / "package-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    metadata["testedCommitSha"] = "e" * 40
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(HandoffError, match="tested SHA"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=HEAD, e2e_checkout_sha=diagnostics["testedCommitSha"]
        )

    create_package(package_dir := tmp_path / "head", resolution, diagnostics)
    metadata_path = package_dir / "package-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["sourceHeadSha"] = "f" * 40
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(HandoffError, match="source head"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=HEAD, e2e_checkout_sha=diagnostics["testedCommitSha"]
        )

    create_package(package_dir := tmp_path / "base", resolution, diagnostics)
    metadata_path = package_dir / "package-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["sourceBaseSha"] = "f" * 40
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(HandoffError, match="source base"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=HEAD, e2e_checkout_sha=diagnostics["testedCommitSha"]
        )

    create_package(package_dir := tmp_path / "checkout", resolution, diagnostics)
    with pytest.raises(HandoffError, match="tested SHA"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=HEAD, e2e_checkout_sha="f" * 40
        )


def test_package_artifact_name_hash_size_and_inventory_are_fail_closed(tmp_path: Path):
    resolution, diagnostics, package_dir, _ = valid_handoff(tmp_path / "valid")
    metadata_path = package_dir / "package-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["artifactName"] = "wrong"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(HandoffError, match="artifactName"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=TESTED, e2e_checkout_sha=TESTED
        )

    resolution, diagnostics, package_dir, _ = valid_handoff(tmp_path / "tamper")
    (package_dir / "anki_study_report.ankiaddon").write_bytes(b"tampered")
    with pytest.raises(HandoffError, match="SHA-256"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=TESTED, e2e_checkout_sha=TESTED
        )

    resolution, diagnostics, package_dir, _ = valid_handoff(tmp_path / "extra")
    (package_dir / "extra.log").write_text("x", encoding="utf-8")
    with pytest.raises(HandoffError, match="exactly"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=TESTED, e2e_checkout_sha=TESTED
        )


def test_symlinks_are_rejected_when_supported(tmp_path: Path):
    resolution, diagnostics, package_dir, _ = valid_handoff(tmp_path / "valid")
    extra = package_dir / "extra"
    try:
        extra.symlink_to(package_dir / "anki_study_report.ankiaddon")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(HandoffError, match="symlink"):
        MODULE.validate_package_handoff(
            resolution=resolution, diagnostics=diagnostics, directory=package_dir,
            e2e_workflow_source_sha=TESTED, e2e_checkout_sha=TESTED
        )


def test_public_evidence_allowlist_contains_no_tokens_paths_or_raw_payload(tmp_path: Path):
    _, _, _, evidence = valid_handoff(tmp_path)
    serialized = json.dumps(evidence)
    assert set(evidence) == MODULE.HANDOFF_PUBLIC_FIELDS
    assert "token" not in serialized.lower()
    assert "archive_download_url" not in serialized
    assert "actor" not in serialized
    assert "C:/Users/" not in serialized
    assert "/home/" not in serialized
    assert "pull_requests" not in serialized
