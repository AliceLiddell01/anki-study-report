from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "prepare_ci_e2e_artifacts_wrapper_test", SCRIPTS / "prepare_ci_e2e_artifacts.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PACKAGE_SHA = "a" * 40
HARNESS_SHA = "b" * 40


def evidence() -> dict:
    return {
        "schemaVersion": 1,
        "reuseAllowed": True,
        "reuseMode": "harness-only",
        "packageTestedCommitSha": PACKAGE_SHA,
        "e2eHarnessCommitSha": HARNESS_SHA,
        "workflowSourceSha": HARNESS_SHA,
        "changedFileCount": 2,
        "changedPathsSha256": "c" * 64,
        "changedPaths": [
            "docker/anki-e2e/smoke-browser.mjs",
            "scripts/prepare_ci_e2e_artifacts.py",
        ],
    }


def args(tmp_path: Path) -> argparse.Namespace:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "e2e-harness-reuse.json").write_text(json.dumps(evidence()), encoding="utf-8")
    return argparse.Namespace(
        package_source="fast-ci-artifact",
        source_fast_ci_tested_sha=PACKAGE_SHA,
        e2e_checkout_sha=HARNESS_SHA,
        commit_sha=HARNESS_SHA,
        raw_logs=raw,
    )


def fake_legacy_summary(output: Path, *, args: argparse.Namespace, manifest_status: str, artifact_files: list[str]) -> None:
    assert args.e2e_checkout_sha == PACKAGE_SHA
    reports = output / "artifacts" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (output / "ci-e2e-summary.json").write_text(json.dumps({"e2eCheckoutSha": PACKAGE_SHA}), encoding="utf-8")
    (output / "ci-e2e-summary.md").write_text(f"| E2E checkout | `{PACKAGE_SHA}` |\n", encoding="utf-8")
    (output / "environment.txt").write_text(f"e2eCheckoutSha={PACKAGE_SHA}\n", encoding="utf-8")
    (reports / "e2e-performance-summary.json").write_text(json.dumps({"current": {"e2eCheckoutSha": PACKAGE_SHA}}), encoding="utf-8")


def test_harness_only_summary_preserves_package_and_checkout_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = evidence()
    monkeypatch.setattr(MODULE, "validate_package_reuse_boundary", lambda **_: expected)
    monkeypatch.setattr(MODULE, "_ORIGINAL_WRITE_SUMMARY", fake_legacy_summary)
    output = tmp_path / "output"
    output.mkdir()
    files: list[str] = []

    MODULE.write_summary(output, args=args(tmp_path), manifest_status="complete", artifact_files=files)

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    assert summary["e2eCheckoutSha"] == HARNESS_SHA
    assert summary["packageReuseMode"] == "harness-only"
    assert summary["packageReuseChangedFileCount"] == 2
    assert "artifacts/reports/e2e-harness-reuse.json" in files
    assert json.loads((output / "artifacts/reports/e2e-harness-reuse.json").read_text()) == expected
    markdown = (output / "ci-e2e-summary.md").read_text(encoding="utf-8")
    assert f"| E2E checkout | `{HARNESS_SHA}` |" in markdown
    assert f"| Package tested commit | `{PACKAGE_SHA}` |" in markdown
    environment = (output / "environment.txt").read_text(encoding="utf-8")
    assert f"e2eCheckoutSha={HARNESS_SHA}" in environment
    assert "packageReuseMode=harness-only" in environment


def test_mismatched_reuse_evidence_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = evidence()
    monkeypatch.setattr(MODULE, "validate_package_reuse_boundary", lambda **_: expected)
    value = args(tmp_path)
    tampered = dict(expected)
    tampered["changedFileCount"] = 99
    (value.raw_logs / "e2e-harness-reuse.json").write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        MODULE._read_reuse_evidence(value)


def test_exact_tree_path_uses_legacy_summary_without_reuse_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}
    def legacy_call(output: Path, *, args: argparse.Namespace, manifest_status: str, artifact_files: list[str]) -> None:
        called["value"] = True
    monkeypatch.setattr(MODULE, "_ORIGINAL_WRITE_SUMMARY", legacy_call)
    value = argparse.Namespace(
        package_source="fast-ci-artifact",
        source_fast_ci_tested_sha=PACKAGE_SHA,
        e2e_checkout_sha=PACKAGE_SHA,
        commit_sha=PACKAGE_SHA,
        raw_logs=tmp_path / "missing",
    )

    MODULE.write_summary(tmp_path / "output", args=value, manifest_status="complete", artifact_files=[])
    assert called["value"] is True
