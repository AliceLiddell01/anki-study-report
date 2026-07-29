from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-e2e.yml"
IDENTITY_MODULE = ROOT / "scripts" / "non_release_build_identity.py"
CANCELLATION_MODULE = ROOT / "scripts" / "prepare_ci_e2e_cancellation.py"
DOCKER_RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


identity = load_module("non_release_build_identity", IDENTITY_MODULE)
cancellation = load_module("prepare_ci_e2e_cancellation", CANCELLATION_MODULE)


def valid_identity() -> dict:
    sha = "a" * 40
    digest = "sha256:" + "b" * 64
    document = {
        "schemaVersion": 1,
        "kind": "non-release-build",
        "identityDigest": "",
        "identity": {
            "repository": "AliceLiddell01/anki-study-report",
            "package": {
                "source": "fast-ci-artifact",
                "testedCommitSha": sha,
                "sourceRunId": 1,
                "sourceRunAttempt": 1,
                "artifactId": 2,
                "artifactDigest": "sha256:" + "c" * 64,
                "innerSha256": "d" * 64,
                "sizeBytes": 10,
            },
            "harness": {"commitSha": sha, "checkoutSha": sha},
            "workflow": {
                "repository": "AliceLiddell01/anki-study-report",
                "filePath": ".github/workflows/ci-e2e.yml",
                "sourceSha": sha,
            },
            "environment": {
                "imageReference": "ghcr.io/aliceliddell01/anki-study-report-e2e@" + digest,
                "imageDigest": digest,
                "platform": "linux/amd64",
                "contractSha256": "e" * 64,
                "publishedFromCommitSha": "f" * 40,
            },
            "reuse": {
                "mode": "exact-tree",
                "changedFileCount": 0,
                "changedPathsSha256": hashlib.sha256(b"").hexdigest(),
            },
        },
        "execution": {
            "runId": 3,
            "runAttempt": 1,
            "triggerSha": sha,
            "ref": "refs/heads/platform/e2e-i5-non-release-build-identity",
        },
    }
    document["identityDigest"] = identity.compute_identity_digest(document["identity"])
    return document


def test_workflow_uses_job_workflow_identity_not_trigger_sha():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "E2E_WORKFLOW_SOURCE_SHA=${{ job.workflow_sha }}" in text
    assert "E2E_WORKFLOW_SOURCE_REPOSITORY=${{ job.workflow_repository }}" in text
    assert "E2E_WORKFLOW_SOURCE_PATH=${{ job.workflow_file_path }}" in text
    assert "E2E_WORKFLOW_SOURCE_REF=${{ job.workflow_ref }}" in text
    assert "ref: ${{ job.workflow_sha }}" in text
    assert "EXPECTED_HARNESS_SHA: ${{ job.workflow_sha }}" in text
    assert "E2E_WORKFLOW_SOURCE_SHA=${{ github.sha }}" not in text
    assert "--trigger-sha $env:GITHUB_SHA" in text


def test_identity_is_built_before_canonical_e2e_and_release_is_excluded():
    text = WORKFLOW.read_text(encoding="utf-8")
    build = text.index("- name: Build canonical non-release build identity")
    canonical = text.index("- name: Run canonical Docker-only E2E")
    assert build < canonical
    build_block = text[build:canonical]
    assert "if: steps.source_mode.outputs.package_source == 'fast-ci-artifact'" in build_block
    assert "non-release-build-identity.json" in build_block
    assert "release-artifact" not in build_block


def test_identity_survives_inner_reset_by_staging_and_restoration():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "$identityPath = 'ci-e2e-raw/non-release-build-identity.json'" in text
    assert "Copy-Item -LiteralPath $identityPath -Destination e2e-artifacts/reports/non-release-build-identity.json -Force" in text
    restore = text.index("- name: Restore canonical non-release build identity evidence")
    canonical = text.index("- name: Run canonical Docker-only E2E")
    public = text.index("- name: Prepare redacted public E2E artifact")
    assert canonical < restore < public
    assert "Remove-Item -LiteralPath ci-e2e-raw/non-release-build-identity.json" in text
    assert "Remove-Item -LiteralPath e2e-artifacts/reports/non-release-build-identity.json" in text
    restore_block = text[restore:public]
    assert "write-artifact-manifest.py" in restore_block
    assert "Identity-aware artifact manifest regeneration failed." in restore_block


def test_docker_runner_preserves_artifact_backed_identity_across_inner_reset():
    text = DOCKER_RUNNER.read_text(encoding="utf-8")
    assert '$PreservedReportEvidence = @{}' in text
    assert '"non-release-build-identity.json"' in text
    assert '"release-build-identity.json"' in text
    assert "[IO.File]::ReadAllBytes" in text
    assert "[IO.File]::WriteAllBytes" in text
    save = text.index("Save-E2EReportEvidence -ArtifactsRoot $ArtifactsDir")
    canonical = text.index("$scriptExit = Invoke-DockerComposeRaw -Arguments $runArgs")
    restore = text.index("Restore-E2EReportEvidence -ArtifactsRoot $ArtifactsDir")
    assert save < canonical < restore


def test_cancellation_restores_staged_identity_before_minimal_export():
    text = WORKFLOW.read_text(encoding="utf-8")
    cleanup = text.index("- name: Clean cancelled Docker E2E state")
    prepare = text.index("- name: Prepare bounded cancellation artifact")
    block = text[cleanup:prepare]
    assert "ci-e2e-raw/non-release-build-identity.json" in block
    assert "e2e-artifacts/reports/non-release-build-identity.json" in block


def test_public_raw_pair_is_revalidated_and_release_copy_is_rejected():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "non_release_build_identity.py validate-pair" in text
    assert "--raw e2e-artifacts/reports/non-release-build-identity.json" in text
    assert "--public ci-e2e/artifacts/reports/non-release-build-identity.json" in text
    assert "Release E2E must not emit non-release build identity evidence." in text


def test_no_supply_chain_or_retry_scope_creep():
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    for forbidden in ("attest", "sigstore", "slsa", "sbom", "cosign", "retry", "continue-on-error: false"):
        assert forbidden not in text
    assert "permissions:\n  contents: read\n  actions: read\n  packages: read" in text


def test_cancellation_artifact_preserves_valid_identity_when_available(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    reports = source / "reports"
    reports.mkdir(parents=True)
    (reports / "cancellation-summary.json").write_text(
        json.dumps({"schemaVersion": 1, "status": "partial"}) + "\n", encoding="utf-8"
    )
    identity.atomic_write(reports / identity.CANONICAL_FILENAME, valid_identity())
    copied = cancellation.prepare(source, output)
    relative = f"reports/{identity.CANONICAL_FILENAME}"
    assert relative in copied
    assert identity.load_document(output / relative) == valid_identity()


def test_cancellation_before_material_resolution_allows_identity_absence(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    reports = source / "reports"
    reports.mkdir(parents=True)
    (reports / "cancellation-summary.json").write_text(
        json.dumps({"schemaVersion": 1, "status": "partial"}) + "\n", encoding="utf-8"
    )
    copied = cancellation.prepare(source, output)
    assert f"reports/{identity.CANONICAL_FILENAME}" not in copied


def test_invalid_cancellation_identity_fails_closed(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    reports = source / "reports"
    reports.mkdir(parents=True)
    (reports / "cancellation-summary.json").write_text("{}\n", encoding="utf-8")
    (reports / identity.CANONICAL_FILENAME).write_text("{}\n", encoding="utf-8")
    with pytest.raises(identity.BuildIdentityError):
        cancellation.prepare(source, output)


def test_manifest_and_public_exporter_keep_report_files_generic():
    manifest_path = ROOT / "docker" / "anki-e2e" / "write-artifact-manifest.py"
    exporter_path = ROOT / "scripts" / "ci_e2e_artifact_common.py"
    if not manifest_path.is_file() or not exporter_path.is_file():
        pytest.skip("repository integration files are not present in the isolated focused fixture")
    manifest = manifest_path.read_text(encoding="utf-8")
    exporter = exporter_path.read_text(encoding="utf-8")
    assert "report_paths = files_under(paths, paths.reports)" in manifest
    assert '"reports": report_paths' in manifest
    assert "for path in sorted(source.rglob(\"*\"))" in exporter
    assert "top not in ALLOWED_TOP_LEVEL" in exporter


def test_workflow_retains_browser_contract_and_no_source_build_fallback():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Cloud E2E requires an exact prebuilt Fast CI or release artifact package." in text
    assert "source-build" in text
    assert "-NoDockerBuild" in text
    assert "perf100" in text  # existing mode remains available, but E2E-I5 does not invoke it automatically
