from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "failure_artifact_protocol.py"


def load_module():
    spec = importlib.util.spec_from_file_location("asr_failure_artifact_protocol", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge = load_module()


def write_manifest(root: Path, status: str) -> None:
    (root / "artifact-manifest.json").write_text(json.dumps({
        "artifactSchemaVersion": 2,
        "status": status,
        "runtime": {},
        "artifacts": {"reports": [], "diagnostics": [], "html": [], "package": []},
        "screenshots": [],
    }), encoding="utf-8")


def create_api_primary(root: Path) -> Path:
    path = root / "reports" / "failure-summary.json"
    entry = bridge.failure_protocol.build_failure(
        code="ASR-E2E-API-SMOKE",
        phase_id="api-smoke-first",
        summary="API response was invalid",
        original_exit_code=5,
        evidence_paths=["reports/api-smoke-first.json"],
    )
    bridge.failure_protocol.record_failure(path, "docker-e2e", entry, primary=True)
    return path


def test_failed_host_run_gets_bounded_fallback_and_manifest_index(tmp_path: Path):
    source = tmp_path / "source"
    (source / "reports").mkdir(parents=True)
    write_manifest(source, "failed")
    summary = bridge.ensure_source_contract(source, manifest_status="failed", e2e_exit_code=1)
    assert summary is not None
    document = bridge.failure_protocol.load_document(summary)
    assert document["primary"]["failureCode"] == "ASR-E2E-UNKNOWN"
    assert document["cleanup"]["status"] == "partial"
    manifest = json.loads((source / "artifact-manifest.json").read_text(encoding="utf-8"))
    assert "reports/failure-summary.json" in manifest["artifacts"]["reports"]
    assert manifest["status"] == "failed"


def test_success_source_rejects_failure_summary(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    create_api_primary(source)
    with pytest.raises(ValueError, match="Successful E2E source"):
        bridge.ensure_source_contract(source, manifest_status="success", e2e_exit_code=0)


def test_sanitization_failure_is_secondary_and_preserves_primary(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    summary = create_api_primary(source)
    bridge.record_sanitization_failure(source, RuntimeError("private /home/owner detail"))
    document = bridge.failure_protocol.load_document(summary)
    assert document["primary"]["failureCode"] == "ASR-E2E-API-SMOKE"
    assert [item["failureCode"] for item in document["secondary"]] == ["ASR-E2E-SANITIZATION"]
    assert "/home/" not in json.dumps(document)


def test_minimal_public_copy_is_identical_and_validated(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "public"
    source.mkdir()
    summary = create_api_primary(source)
    public = bridge.publish_minimal_failure(output, summary)
    assert bridge.validate_public_contract(summary, output) == public
    assert bridge.failure_protocol.load_document(public) == bridge.failure_protocol.load_document(summary)
    assert (output / "failure-summary.md").is_file()


def test_public_copy_mismatch_fails_closed(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "public"
    source.mkdir()
    summary = create_api_primary(source)
    public = bridge.publish_minimal_failure(output, summary)
    payload = json.loads(public.read_text(encoding="utf-8"))
    payload["primary"]["summary"] = "changed"
    public.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs"):
        bridge.validate_public_contract(summary, output)


def test_host_failure_infers_package_identity_before_container(tmp_path: Path):
    source = tmp_path / "source"
    (source / "reports").mkdir(parents=True)
    summary = bridge.ensure_source_contract(
        source,
        manifest_status="missing",
        e2e_exit_code=1,
        package_source="fast-ci-artifact",
    )
    assert summary is not None
    document = bridge.failure_protocol.load_document(summary)
    assert document["primary"]["failureCode"] == "ASR-E2E-PACKAGE-IDENTITY"


def test_host_failure_infers_environment_identity_after_package_handoff(tmp_path: Path):
    source = tmp_path / "source"
    reports = source / "reports"
    reports.mkdir(parents=True)
    (reports / "fast-ci-handoff.json").write_text("{}\n", encoding="utf-8")
    (reports / "environment-image-provenance.json").write_text(
        json.dumps({"imageDigest": None, "environmentContractSha256": None}) + "\n",
        encoding="utf-8",
    )
    summary = bridge.ensure_source_contract(
        source,
        manifest_status="missing",
        e2e_exit_code=1,
        package_source="fast-ci-artifact",
    )
    assert summary is not None
    document = bridge.failure_protocol.load_document(summary)
    assert document["primary"]["failureCode"] == "ASR-E2E-ENVIRONMENT-IDENTITY"
