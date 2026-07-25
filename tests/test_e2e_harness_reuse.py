from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_e2e_harness_reuse.py"
SPEC = importlib.util.spec_from_file_location("validate_e2e_harness_reuse", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PACKAGE = "a" * 40
HARNESS = "b" * 40

E2E_I6_PATHS = [
    ".github/workflows/ci-e2e.yml",
    "docs/e2e-final-summary-history.md",
    "scripts/e2e_final_summary.py",
    "scripts/e2e_final_summary_build.py",
    "scripts/e2e_final_summary_build_core.py",
    "scripts/e2e_final_summary_build_projection.py",
    "scripts/e2e_final_summary_build_validation.py",
    "scripts/e2e_final_summary_common.py",
    "scripts/e2e_final_summary_history.py",
    "scripts/e2e_final_summary_history_core.py",
    "scripts/e2e_final_summary_history_entry.py",
    "scripts/e2e_final_summary_history_report.py",
    "scripts/e2e_history_transport.py",
    "scripts/prepare_ci_e2e_cancellation.py",
    "scripts/validate_e2e_harness_reuse.py",
    "tests/e2e_final_summary_fixtures.py",
    "tests/test_ci_e2e_final_summary_workflow.py",
    "tests/test_e2e_final_summary_artifact_integration.py",
    "tests/test_e2e_final_summary_contract.py",
    "tests/test_e2e_final_summary_history.py",
    "tests/test_e2e_harness_reuse.py",
    "tests/test_e2e_history_transport.py",
]


def test_harness_only_changes_can_reuse_exact_fast_ci_package() -> None:
    changed_paths = [
        ".github/workflows/ci-e2e.yml",
        "docker/anki-e2e/browser-progress.mjs",
        "docker/anki-e2e/smoke-browser.mjs",
        "scripts/failure_artifact_protocol.py",
        "scripts/validate_e2e_harness_reuse.py",
        "scripts/verify_fast_ci_e2e_handoff.py",
        "tests/browser_progress.test.mjs",
        "tests/browser_report_contract.test.mjs",
        "tests/test_browser_progress_node.py",
        "tests/test_e2e_harness_reuse.py",
        "tests/test_e2e_screenshot_contract.py",
        "tests/test_failure_artifact_protocol.py",
        "tests/test_failure_summary.py",
        "tests/test_notification_e2e_fixture.py",
        "tests/test_run_event_schema.py",
    ]
    result = MODULE.validate_harness_reuse(
        package_tested_sha=PACKAGE,
        harness_sha=HARNESS,
        workflow_source_sha=HARNESS,
        changed_paths=changed_paths,
    )

    assert result["reuseAllowed"] is True
    assert result["reuseMode"] == "harness-only"
    assert result["packageTestedCommitSha"] == PACKAGE
    assert result["e2eHarnessCommitSha"] == HARNESS
    assert result["changedFileCount"] == len(changed_paths)
    assert len(result["changedPathsSha256"]) == 64


def test_e2e_i3_complete_harness_diff_is_allowlisted() -> None:
    changed_paths = [
        "docker/anki-e2e/Dockerfile",
        "docker/anki-e2e/browser-plan.mjs",
        "docker/anki-e2e/browser-progress.mjs",
        "docker/anki-e2e/browser-report-contract.mjs",
        "docker/anki-e2e/failure_entry.py",
        "docker/anki-e2e/failure_protocol.py",
        "docker/anki-e2e/failure_registry.py",
        "docker/anki-e2e/failure_safety.py",
        "docker/anki-e2e/failure_schema.py",
        "docker/anki-e2e/failure_store.py",
        "docker/anki-e2e/run-e2e-failure-wrapper.sh",
        "docker/anki-e2e/run_event_context.py",
        "docker/anki-e2e/run_event_contract.py",
        "docker/anki-e2e/run_event_failure.py",
        "docker/anki-e2e/run_event_protocol.py",
        "docker/anki-e2e/run_event_registry.py",
        "docker/anki-e2e/run_event_runtime.py",
        "docker/anki-e2e/run_event_storage.py",
        "docker/anki-e2e/run_event_validate.py",
        "docker/anki-e2e/smoke-browser-wrapper.mjs",
        "docker/anki-e2e/stop-anki.sh",
        "scripts/failure_artifact_protocol.py",
        "scripts/prepare_ci_e2e_artifacts.py",
        "scripts/validate_e2e_harness_reuse.py",
        "tests/browser_progress.test.mjs",
        "tests/browser_report_contract.test.mjs",
        "tests/test_e2e_harness_reuse.py",
        "tests/test_failure_artifact_protocol.py",
        "tests/test_failure_browser.py",
        "tests/test_failure_integration_contract.py",
        "tests/test_failure_registry.py",
        "tests/test_failure_security.py",
        "tests/test_failure_summary.py",
        "tests/test_run_event_concurrency.py",
        "tests/test_run_event_failure_integration.py",
        "tests/test_run_event_schema.py",
    ]
    result = MODULE.validate_harness_reuse(
        package_tested_sha=PACKAGE,
        harness_sha=HARNESS,
        workflow_source_sha=HARNESS,
        changed_paths=changed_paths,
    )
    assert result["reuseMode"] == "harness-only"
    assert result["changedFileCount"] == len(changed_paths)


def test_e2e_i6_complete_harness_diff_is_allowlisted() -> None:
    result = MODULE.validate_harness_reuse(
        package_tested_sha=PACKAGE,
        harness_sha=HARNESS,
        workflow_source_sha=HARNESS,
        changed_paths=E2E_I6_PATHS,
    )

    assert result["reuseAllowed"] is True
    assert result["reuseMode"] == "harness-only"
    assert result["changedFileCount"] == len(E2E_I6_PATHS)
    assert result["changedPaths"] == sorted(E2E_I6_PATHS)


@pytest.mark.parametrize(
    "path",
    [
        "anki_study_report/__init__.py",
        "web-dashboard/src/App.tsx",
        "scripts/package_addon.py",
        "pyproject.toml",
        "README.md",
    ],
)
def test_package_impacting_or_unrelated_changes_fail_closed(path: str) -> None:
    with pytest.raises(MODULE.HarnessReuseError, match="Package reuse is forbidden"):
        MODULE.validate_harness_reuse(
            package_tested_sha=PACKAGE,
            harness_sha=HARNESS,
            workflow_source_sha=HARNESS,
            changed_paths=[path],
        )


def test_exact_tree_reuse_requires_an_empty_diff() -> None:
    result = MODULE.validate_harness_reuse(
        package_tested_sha=PACKAGE,
        harness_sha=PACKAGE,
        workflow_source_sha=PACKAGE,
        changed_paths=[],
    )
    assert result["reuseMode"] == "exact-tree"

    with pytest.raises(MODULE.HarnessReuseError, match="must not report changed paths"):
        MODULE.validate_harness_reuse(
            package_tested_sha=PACKAGE,
            harness_sha=PACKAGE,
            workflow_source_sha=PACKAGE,
            changed_paths=["docker/anki-e2e/smoke-browser.mjs"],
        )


def test_workflow_source_and_harness_identity_must_match() -> None:
    with pytest.raises(MODULE.HarnessReuseError, match="workflow source SHA"):
        MODULE.validate_harness_reuse(
            package_tested_sha=PACKAGE,
            harness_sha=HARNESS,
            workflow_source_sha="c" * 40,
            changed_paths=["docker/anki-e2e/smoke-browser.mjs"],
        )


@pytest.mark.parametrize("path", ["../secret", "/tmp/file", "./docker/anki-e2e/file", "C:\\Users\\x\\file"])
def test_unsafe_changed_paths_are_rejected(path: str) -> None:
    with pytest.raises(MODULE.HarnessReuseError, match="Unsafe changed path"):
        MODULE.validate_harness_reuse(
            package_tested_sha=PACKAGE,
            harness_sha=HARNESS,
            workflow_source_sha=HARNESS,
            changed_paths=[path],
        )
