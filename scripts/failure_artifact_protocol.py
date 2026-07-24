from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent


def _load_failure_protocol():
    path = _ROOT / "docker" / "anki-e2e" / "failure_protocol.py"
    spec = importlib.util.spec_from_file_location("asr_failure_protocol_artifacts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load failure protocol from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


failure_protocol = _load_failure_protocol()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    failure_protocol.atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _patch_manifest(source: Path, summary_relative: str) -> None:
    path = source / "artifact-manifest.json"
    manifest = _read_json(path)
    if manifest is None:
        return
    artifacts = manifest.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError("Artifact manifest artifacts section must be an object")
    reports = artifacts.setdefault("reports", [])
    if not isinstance(reports, list):
        raise ValueError("Artifact manifest reports section must be an array")
    if summary_relative not in reports:
        reports.append(summary_relative)
        reports.sort()
    manifest["status"] = "failed"
    _write_json(path, manifest)


def ensure_source_contract(source: Path, *, manifest_status: str, e2e_exit_code: int, package_source: str = "") -> Path | None:
    source = source.resolve()
    summary = source / "reports" / "failure-summary.json"
    failed = e2e_exit_code != 0 or manifest_status == "failed"
    if failed and not summary.is_file():
        package_evidence = source / "reports" / "fast-ci-handoff.json"
        environment_evidence = source / "reports" / "environment-image-provenance.json"
        environment = _read_json(environment_evidence)
        if package_source in {"fast-ci-artifact", "release-artifact"} and not package_evidence.is_file():
            code = "ASR-E2E-PACKAGE-IDENTITY"
            error_type = "PackageIdentityFailure"
            safe_summary = "Exact E2E package identity was not established before execution"
            evidence = []
        elif package_source in {"fast-ci-artifact", "release-artifact"} and (environment is None or not environment.get("imageDigest") or not environment.get("environmentContractSha256")):
            code = "ASR-E2E-ENVIRONMENT-IDENTITY"
            error_type = "EnvironmentIdentityFailure"
            safe_summary = "Exact E2E environment identity was not established before execution"
            evidence = ["reports/environment-image-provenance.json"] if environment_evidence.is_file() else []
        else:
            code = "ASR-E2E-UNKNOWN"
            error_type = "HostWrapperFailure"
            safe_summary = "Cloud E2E failed before a container failure summary was available"
            evidence = ["reports/run-events.jsonl"] if (source / "reports" / "run-events.jsonl").is_file() else []
        entry = failure_protocol.build_failure(
            code=code,
            error_type=error_type,
            summary=safe_summary,
            original_exit_code=max(1, int(e2e_exit_code or 1)),
            evidence_paths=evidence,
            raw_diagnostic_paths=[],
        )
        failure_protocol.record_failure(summary, "docker-e2e", entry, primary=True)
        failure_protocol.set_cleanup_status(summary, "partial")
        _patch_manifest(source, "reports/failure-summary.json")
    elif not failed and summary.exists():
        raise ValueError("Successful E2E source must not contain reports/failure-summary.json")
    if summary.is_file():
        failure_protocol.load_document(summary)
        _patch_manifest(source, "reports/failure-summary.json")
        return summary
    return None


def record_sanitization_failure(source: Path, error: BaseException) -> Path:
    summary = source.resolve() / "reports" / "failure-summary.json"
    entry = failure_protocol.build_failure(
        code="ASR-E2E-SANITIZATION",
        error_type=type(error).__name__,
        summary="Public artifact sanitization failed",
        original_exit_code=6,
        evidence_paths=[],
        raw_diagnostic_paths=[],
    )
    failure_protocol.record_failure(summary, "docker-e2e", entry, primary=not summary.is_file())
    return summary


def publish_minimal_failure(output: Path, source_summary: Path) -> Path:
    document = failure_protocol.load_document(source_summary)
    target = output.resolve() / "artifacts" / "reports" / "failure-summary.json"
    failure_protocol.atomic_write(target, failure_protocol.serialize_document(document))
    markdown = output.resolve() / "failure-summary.md"
    failure_protocol.atomic_write(markdown, failure_protocol.render_markdown(document))
    return target


def validate_public_contract(source_summary: Path | None, output: Path) -> Path | None:
    public = output.resolve() / "artifacts" / "reports" / "failure-summary.json"
    if source_summary is None:
        if public.exists():
            raise ValueError("Public failure summary exists without validated source summary")
        return None
    source_document = failure_protocol.load_document(source_summary)
    public_document = failure_protocol.load_document(public)
    if public_document != source_document:
        raise ValueError("Public failure summary differs from validated source summary")
    return public


def emit_github_failure(summary: Path) -> None:
    document = failure_protocol.load_document(summary)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n" + failure_protocol.render_markdown(document))
    print(failure_protocol.annotation(document), flush=True)
