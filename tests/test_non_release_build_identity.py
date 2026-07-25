from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "non_release_build_identity.py"
spec = importlib.util.spec_from_file_location("non_release_build_identity", MODULE_PATH)
assert spec and spec.loader
identity = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = identity
spec.loader.exec_module(identity)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
HASH_A = "1" * 64
HASH_B = "2" * 64
DIGEST_A = "sha256:" + "3" * 64
IMAGE_DIGEST = "sha256:" + "4" * 64
EMPTY_PATHS_HASH = hashlib.sha256(b"").hexdigest()


def sample_document(*, run_id: int = 101, run_attempt: int = 1) -> dict:
    value = {
        "schemaVersion": 1,
        "kind": "non-release-build",
        "identityDigest": "",
        "identity": {
            "repository": "AliceLiddell01/anki-study-report",
            "package": {
                "source": "fast-ci-artifact",
                "testedCommitSha": SHA_A,
                "sourceRunId": 10,
                "sourceRunAttempt": 1,
                "artifactId": 20,
                "artifactDigest": DIGEST_A,
                "innerSha256": HASH_A,
                "sizeBytes": 123,
            },
            "harness": {"commitSha": SHA_A, "checkoutSha": SHA_A},
            "workflow": {
                "repository": "AliceLiddell01/anki-study-report",
                "filePath": ".github/workflows/ci-e2e.yml",
                "sourceSha": SHA_A,
            },
            "environment": {
                "imageReference": "ghcr.io/aliceliddell01/anki-study-report-e2e@" + IMAGE_DIGEST,
                "imageDigest": IMAGE_DIGEST,
                "platform": "linux/amd64",
                "contractSha256": HASH_B,
                "publishedFromCommitSha": SHA_C,
            },
            "reuse": {
                "mode": "exact-tree",
                "changedFileCount": 0,
                "changedPathsSha256": EMPTY_PATHS_HASH,
            },
        },
        "execution": {
            "runId": run_id,
            "runAttempt": run_attempt,
            "triggerSha": SHA_A,
            "ref": "refs/heads/platform/e2e-i5-non-release-build-identity",
        },
    }
    value["identityDigest"] = identity.compute_identity_digest(value["identity"])
    return value


def sample_cross_evidence(tmp_path: Path):
    package_path = tmp_path / "anki_study_report.ankiaddon"
    package_path.write_bytes(b"exact package bytes")
    inner_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    handoff = {
        "packageSource": "fast-ci-artifact",
        "repository": "AliceLiddell01/anki-study-report",
        "sourceTestedCommitSha": SHA_A,
        "sourceRunId": 10,
        "sourceRunAttempt": 2,
        "packageArtifactId": 20,
        "packageArtifactDigest": DIGEST_A,
        "packageSha256": inner_hash,
        "packageSizeBytes": package_path.stat().st_size,
        "e2eWorkflowSourceSha": SHA_A,
        "e2eCheckoutSha": SHA_A,
    }
    reuse = {
        "schemaVersion": 1,
        "reuseAllowed": True,
        "reuseMode": "exact-tree",
        "packageTestedCommitSha": SHA_A,
        "e2eHarnessCommitSha": SHA_A,
        "workflowSourceSha": SHA_A,
        "changedFileCount": 0,
        "changedPathsSha256": EMPTY_PATHS_HASH,
        "changedPaths": [],
    }
    lock = {
        "schemaVersion": 1,
        "environmentVersion": "env-v1",
        "imageName": "ghcr.io/aliceliddell01/anki-study-report-e2e",
        "imageDigest": IMAGE_DIGEST,
        "platform": "linux/amd64",
        "humanTag": "ignored",
        "environmentContractSha256": "sha256:" + HASH_B,
        "publishedFromCommitSha": SHA_C,
        "publicationRunId": 30,
        "idempotentVerificationRunId": 31,
    }
    document = identity.build_document(
        handoff=handoff,
        reuse=reuse,
        environment_lock=lock,
        package_path=package_path,
        repository="AliceLiddell01/anki-study-report",
        harness_sha=SHA_A,
        checkout_sha=SHA_A,
        workflow_repository="AliceLiddell01/anki-study-report",
        workflow_path=".github/workflows/ci-e2e.yml",
        workflow_source_sha=SHA_A,
        image_reference=lock["imageName"] + "@" + IMAGE_DIGEST,
        image_digest=IMAGE_DIGEST,
        image_platform="linux/amd64",
        run_id=100,
        run_attempt=3,
        trigger_sha=SHA_A,
        ref="refs/heads/platform/e2e-i5-non-release-build-identity",
    )
    return document, handoff, reuse, lock, package_path


def test_valid_schema_and_deterministic_digest():
    value = sample_document()
    assert identity.validate_document(value) == value
    reordered = json.loads(json.dumps(value, sort_keys=True))
    assert identity.compute_identity_digest(reordered["identity"]) == value["identityDigest"]


def test_execution_identity_does_not_change_build_digest():
    first = sample_document(run_id=101, run_attempt=1)
    second = sample_document(run_id=202, run_attempt=7)
    assert first["identityDigest"] == second["identityDigest"]


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("repository",), "Other/repository"),
        (("package", "testedCommitSha"), SHA_B),
        (("package", "sourceRunId"), 11),
        (("package", "sourceRunAttempt"), 2),
        (("package", "artifactId"), 21),
        (("package", "artifactDigest"), "sha256:" + "5" * 64),
        (("package", "innerSha256"), "6" * 64),
        (("package", "sizeBytes"), 124),
        (("harness", "commitSha"), SHA_B),
        (("harness", "checkoutSha"), SHA_B),
        (("workflow", "repository"), "Other/repository"),
        (("workflow", "filePath"), ".github/workflows/other.yml"),
        (("workflow", "sourceSha"), SHA_B),
        (("environment", "imageReference"), "ghcr.io/example/e2e@sha256:" + "5" * 64),
        (("environment", "imageDigest"), "sha256:" + "5" * 64),
        (("environment", "platform"), "linux/arm64"),
        (("environment", "contractSha256"), "7" * 64),
        (("environment", "publishedFromCommitSha"), SHA_B),
        (("reuse", "mode"), "harness-only"),
        (("reuse", "changedFileCount"), 1),
        (("reuse", "changedPathsSha256"), "8" * 64),
    ],
)
def test_each_identity_field_is_hashed(path, replacement):
    value = sample_document()
    target = value["identity"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    assert identity.compute_identity_digest(value["identity"]) != value["identityDigest"]


def test_unknown_missing_and_wrong_types_are_rejected():
    value = sample_document()
    value["unexpected"] = True
    with pytest.raises(identity.BuildIdentityError, match="fields differ"):
        identity.validate_document(value)

    value = sample_document()
    del value["identity"]["package"]["artifactId"]
    with pytest.raises(identity.BuildIdentityError, match="fields differ"):
        identity.validate_document(value)

    value = sample_document()
    value["identity"]["package"]["sourceRunId"] = "10"
    value["identityDigest"] = identity.compute_identity_digest(value["identity"])
    with pytest.raises(identity.BuildIdentityError, match="positive integer"):
        identity.validate_document(value)


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda value: value["identity"]["package"].__setitem__("testedCommitSha", "A" * 40), "lowercase"),
        (lambda value: value["identity"]["package"].__setitem__("artifactDigest", "3" * 64), "sha256"),
        (lambda value: value["identity"]["environment"].__setitem__("imageReference", "ghcr.io/example:e2e"), "immutable"),
        (lambda value: value["execution"].__setitem__("ref", "platform/branch"), "Git ref"),
    ],
)
def test_invalid_formats_are_rejected(mutator, match):
    value = sample_document()
    mutator(value)
    value["identityDigest"] = identity.compute_identity_digest(value["identity"])
    with pytest.raises(identity.BuildIdentityError, match=match):
        identity.validate_document(value)


def test_human_labels_are_not_schema_fields():
    value = sample_document()
    value["identity"]["package"]["artifactName"] = "renamed-human-label"
    value["identityDigest"] = identity.compute_identity_digest(value["identity"])
    with pytest.raises(identity.BuildIdentityError, match="unknown=artifactName"):
        identity.validate_document(value)


def test_cross_evidence_build_and_validation(tmp_path: Path):
    document, handoff, reuse, lock, package_path = sample_cross_evidence(tmp_path)
    identity.validate_cross_evidence(
        document=document,
        handoff=handoff,
        reuse=reuse,
        environment_lock=lock,
        package_path=package_path,
    )
    assert document["identity"]["package"]["artifactDigest"] != "sha256:" + document["identity"]["package"]["innerSha256"]


def test_package_hash_and_size_mismatch_fail_closed(tmp_path: Path):
    document, handoff, reuse, lock, package_path = sample_cross_evidence(tmp_path)
    package_path.write_bytes(b"mutated")
    with pytest.raises(identity.BuildIdentityError, match="package bytes"):
        identity.validate_cross_evidence(
            document=document,
            handoff=handoff,
            reuse=reuse,
            environment_lock=lock,
            package_path=package_path,
        )


def test_handoff_artifact_id_and_tested_commit_mismatch_fail(tmp_path: Path):
    document, handoff, reuse, lock, package_path = sample_cross_evidence(tmp_path)
    handoff = dict(handoff, packageArtifactId=999)
    with pytest.raises(identity.BuildIdentityError, match="packageArtifactId"):
        identity.validate_cross_evidence(
            document=document,
            handoff=handoff,
            reuse=reuse,
            environment_lock=lock,
            package_path=package_path,
        )

    handoff = dict(handoff, packageArtifactId=20, sourceTestedCommitSha=SHA_B)
    with pytest.raises(identity.BuildIdentityError, match="sourceTestedCommitSha"):
        identity.validate_cross_evidence(
            document=document,
            handoff=handoff,
            reuse=reuse,
            environment_lock=lock,
            package_path=package_path,
        )


def test_harness_only_boundary_is_valid_and_changes_digest():
    exact = sample_document()
    harness_only = copy.deepcopy(exact)
    harness_only["identity"]["harness"] = {"commitSha": SHA_B, "checkoutSha": SHA_B}
    harness_only["identity"]["workflow"]["sourceSha"] = SHA_B
    harness_only["identity"]["reuse"] = {
        "mode": "harness-only",
        "changedFileCount": 1,
        "changedPathsSha256": hashlib.sha256(b"docker/anki-e2e/run-e2e.sh\n").hexdigest(),
    }
    harness_only["identityDigest"] = identity.compute_identity_digest(harness_only["identity"])
    identity.validate_document(harness_only)
    assert harness_only["identityDigest"] != exact["identityDigest"]


def test_document_size_bom_and_atomic_write(tmp_path: Path):
    path = tmp_path / "identity.json"
    value = sample_document()
    identity.atomic_write(path, value)
    assert identity.load_document(path) == value
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert not list(tmp_path.glob(".identity.json.*"))

    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(value).encode())
    with pytest.raises(identity.BuildIdentityError, match="BOM"):
        identity.load_document(path)

    oversized = sample_document()
    oversized["execution"]["ref"] = "refs/heads/" + "x" * identity.MAX_DOCUMENT_BYTES
    oversized["identityDigest"] = identity.compute_identity_digest(oversized["identity"])
    path.write_text(json.dumps(oversized), encoding="utf-8")
    with pytest.raises(identity.BuildIdentityError, match="exceeds"):
        identity.load_document(path)


def test_public_reformatting_preserves_semantic_identity(tmp_path: Path):
    value = sample_document()
    raw = tmp_path / "raw.json"
    public = tmp_path / "public.json"
    identity.atomic_write(raw, value)
    public.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    assert identity.load_document(raw) == identity.load_document(public)


def test_summary_is_bounded_and_uses_immutable_values():
    summary = identity.render_summary(sample_document())
    assert "Non-release build identity" in summary
    assert DIGEST_A in summary
    assert "artifactName" not in summary
    assert len(summary.encode("utf-8")) < 4096
