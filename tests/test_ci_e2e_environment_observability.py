from __future__ import annotations

import importlib.util
from argparse import Namespace
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
DIGEST = "sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475"
CONTRACT = "sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447"
REFERENCE = f"ghcr.io/aliceliddell01/anki-study-report-e2e@{DIGEST}"
SHA = "a" * 40
PACKAGE_SHA = "b" * 64


def load_module():
    path = ROOT / "scripts" / "prepare_ci_e2e_artifacts.py"
    spec = importlib.util.spec_from_file_location("prepare_ci_e2e_artifacts_environment", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def args(**overrides) -> Namespace:
    values = {
        "started_at": "2026-07-17T00:00:00Z",
        "e2e_exit_code": 0,
        "commit_sha": SHA,
        "ref": "refs/heads/test",
        "mode": "standard",
        "scope": "settings",
        "screenshot_workers": 3,
        "cache_state": "gha-enabled",
        "build_duration_ms": 1200,
        "image_size_bytes": 456,
        "package_source": "source-build",
        "source_fast_ci_run_id": "",
        "source_fast_ci_tested_sha": "",
        "source_package_sha256": "",
        "e2e_checkout_sha": SHA,
    }
    values.update(overrides)
    return Namespace(**values)


def output_root(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    (output / "artifacts" / "reports").mkdir(parents=True)
    (output / "logs").mkdir()
    return output


def write_provenance(output: Path, payload: dict) -> None:
    (output / "artifacts" / "reports" / "environment-image-provenance.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_buildkit_summary_preserves_build_duration_and_gha_backend(tmp_path: Path) -> None:
    module = load_module()
    output = output_root(tmp_path)
    write_provenance(output, {
        "schemaVersion": 1,
        "imageSource": "buildkit",
        "imageReference": "anki-study-report-e2e:ci",
        "imageDigest": None,
        "imagePlatform": "linux/amd64",
        "imagePreparationDurationMs": 1200,
        "imageSizeBytes": 456,
        "environmentContractSha256": None,
        "environmentPublicationRunId": None,
        "environmentReuseVerificationRunId": None,
        "cacheState": "gha-enabled",
    })

    module.write_summary(output, args=args(), manifest_status="success", artifact_files=[])

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    markdown = (output / "ci-e2e-summary.md").read_text(encoding="utf-8")
    assert summary["imageSource"] == "buildkit"
    assert summary["imageDigest"] is None
    assert summary["dockerBuildDurationMs"] == 1200
    assert summary["imagePreparationDurationMs"] == 1200
    assert summary["cacheState"] == "gha-enabled"
    assert "Build cache | gha-enabled (`type=gha`)" in markdown
    assert "Docker build/load | 1200 ms" in markdown


def test_ghcr_summary_records_exact_image_and_never_labels_pull_as_build(tmp_path: Path) -> None:
    module = load_module()
    output = output_root(tmp_path)
    write_provenance(output, {
        "schemaVersion": 1,
        "imageSource": "ghcr",
        "imageReference": REFERENCE,
        "imageDigest": DIGEST,
        "imagePlatform": "linux/amd64",
        "imagePreparationDurationMs": 4321,
        "imageSizeBytes": 987654,
        "environmentContractSha256": CONTRACT,
        "environmentPublicationRunId": 29561205765,
        "environmentReuseVerificationRunId": 29573061110,
        "cacheState": "ghcr-digest",
        "workflowSourceSha": SHA,
        "e2eCheckoutSha": SHA,
        "packageSource": "fast-ci-artifact",
        "sourceFastCiRunId": 123,
        "sourceFastCiTestedSha": SHA,
        "sourcePackageSha256": PACKAGE_SHA,
    })
    summary_args = args(
        build_duration_ms=0,
        image_size_bytes=987654,
        cache_state="ghcr-digest",
        package_source="fast-ci-artifact",
        source_fast_ci_run_id="123",
        source_fast_ci_tested_sha=SHA,
        source_package_sha256=PACKAGE_SHA,
    )

    module.write_summary(output, args=summary_args, manifest_status="success", artifact_files=[])

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    markdown = (output / "ci-e2e-summary.md").read_text(encoding="utf-8")
    environment = (output / "environment.txt").read_text(encoding="utf-8")
    assert summary["imageSource"] == "ghcr"
    assert summary["imageReference"] == REFERENCE
    assert summary["imageDigest"] == DIGEST
    assert summary["imagePreparationDurationMs"] == 4321
    assert summary["dockerBuildDurationMs"] == 0
    assert summary["environmentContractSha256"] == CONTRACT
    assert summary["environmentPublicationRunId"] == 29561205765
    assert summary["environmentReuseVerificationRunId"] == 29573061110
    assert "Build cache | ghcr-digest (`ghcr-digest`)" in markdown
    assert "Docker build/load | n/a (GHCR pull is reported separately)" in markdown
    assert "Image preparation | 4321 ms" in markdown
    assert f"imageDigest={DIGEST}" in environment


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("imageReference", "ghcr.io/aliceliddell01/anki-study-report-e2e:latest", "exact digest image reference"),
        ("imageDigest", "sha256:" + "0" * 64, "reference and digest must agree"),
        ("imagePlatform", "linux/arm64", "Unsupported environment image platform"),
        ("environmentContractSha256", None, "environment contract digest"),
        ("environmentPublicationRunId", None, "publication and reuse run IDs"),
        ("environmentReuseVerificationRunId", None, "publication and reuse run IDs"),
        ("cacheState", "gha-enabled", "cacheState=ghcr-digest"),
    ],
)
def test_successful_ghcr_summary_fails_closed_on_identity_drift(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    module = load_module()
    output = output_root(tmp_path)
    provenance = {
        "imageSource": "ghcr",
        "imageReference": REFERENCE,
        "imageDigest": DIGEST,
        "imagePlatform": "linux/amd64",
        "imagePreparationDurationMs": 100,
        "imageSizeBytes": 1000,
        "environmentContractSha256": CONTRACT,
        "environmentPublicationRunId": 29561205765,
        "environmentReuseVerificationRunId": 29573061110,
        "cacheState": "ghcr-digest",
    }
    provenance[field] = value
    write_provenance(output, provenance)

    with pytest.raises(ValueError, match=message):
        module.write_summary(
            output,
            args=args(
                build_duration_ms=0,
                cache_state="ghcr-digest",
                package_source="fast-ci-artifact",
                source_fast_ci_run_id="123",
                source_fast_ci_tested_sha=SHA,
                source_package_sha256=PACKAGE_SHA,
            ),
            manifest_status="success",
            artifact_files=[],
        )


def test_ghcr_summary_rejects_pull_duration_in_build_field(tmp_path: Path) -> None:
    module = load_module()
    output = output_root(tmp_path)
    write_provenance(output, {
        "imageSource": "ghcr",
        "imageReference": REFERENCE,
        "imageDigest": DIGEST,
        "imagePlatform": "linux/amd64",
        "imagePreparationDurationMs": 100,
        "imageSizeBytes": 1000,
        "environmentContractSha256": CONTRACT,
        "environmentPublicationRunId": 29561205765,
        "environmentReuseVerificationRunId": 29573061110,
        "cacheState": "ghcr-digest",
    })

    with pytest.raises(ValueError, match="must not be reported as Docker build duration"):
        module.write_summary(
            output,
            args=args(
                build_duration_ms=100,
                cache_state="ghcr-digest",
                package_source="fast-ci-artifact",
                source_fast_ci_run_id="123",
                source_fast_ci_tested_sha=SHA,
                source_package_sha256=PACKAGE_SHA,
            ),
            manifest_status="success",
            artifact_files=[],
        )
