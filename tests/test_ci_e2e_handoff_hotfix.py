from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HANDOFF = load_module("verify_fast_ci_e2e_handoff_hotfix", "scripts/verify_fast_ci_e2e_handoff.py")
ARTIFACTS = load_module("prepare_ci_e2e_artifacts_hotfix", "scripts/prepare_ci_e2e_artifacts.py")
HandoffError = HANDOFF.HandoffError
REPO = "AliceLiddell01/anki-study-report"
RUN_ID = 29482887038
SHA = "a" * 40


def run_payload(path: str) -> dict:
    return {
        "id": RUN_ID,
        "name": "Fast CI",
        "path": path,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_sha": SHA,
        "head_branch": "chatgpt/ci-optimization-stage-3-e2e-package-handoff",
        "repository": {"full_name": REPO, "id": 1297299947},
        "head_repository": {"full_name": REPO, "id": 1297299947},
        "pull_requests": [],
    }


def artifacts_payload() -> dict:
    return {
        "total_count": 2,
        "artifacts": [
            {
                "id": 101,
                "name": f"ci-fast-{RUN_ID}-1",
                "digest": "sha256:" + "1" * 64,
                "expired": False,
                "size_in_bytes": 100,
            },
            {
                "id": 102,
                "name": f"ci-package-{SHA}-{RUN_ID}-1",
                "digest": "sha256:" + "2" * 64,
                "expired": False,
                "size_in_bytes": 200,
            },
        ],
    }


@pytest.mark.parametrize(
    "value",
    [
        ".github/workflows/ci-fast.yml",
        ".github/workflows/ci-fast.yml@main",
        ".github/workflows/ci-fast.yml@feature/branch",
        ".github/workflows/ci-fast.yml@refs/tags/example",
        ".github/workflows/ci-fast.yml@" + "f" * 40,
    ],
)
def test_workflow_path_accepts_exact_path_and_opaque_ref_qualifier(value: str):
    canonical, qualifier = HANDOFF.normalize_workflow_run_path(value)
    assert canonical == ".github/workflows/ci-fast.yml"
    assert qualifier is None if "@" not in value else qualifier == value.split("@", 1)[1]


@pytest.mark.parametrize(
    "value",
    [
        ".github/workflows/ci-fast.yml@",
        ".github/workflows/ci-fast.yml.bak@main",
        ".github/workflows/ci-fast.yaml@main",
        ".github/workflows/other.yml@main",
        "subdir/.github/workflows/ci-fast.yml@main",
        "owner/repo/.github/workflows/ci-fast.yml@main",
        " .github/workflows/ci-fast.yml@main",
        ".github/workflows/ci-fast.yml@main\n",
    ],
)
def test_workflow_path_rejects_similar_or_unsafe_values(value: str):
    with pytest.raises(HandoffError):
        HANDOFF.normalize_workflow_run_path(value)


def test_official_ref_qualified_run_shape_normalizes_before_strict_contract():
    resolution = HANDOFF.resolve_source_run(
        run_payload=run_payload(
            ".github/workflows/ci-fast.yml@chatgpt/ci-optimization-stage-3-e2e-package-handoff"
        ),
        artifacts_payload=artifacts_payload(),
        repository=REPO,
        input_run_id=RUN_ID,
    )
    assert resolution["sourceWorkflowPath"] == ".github/workflows/ci-fast.yml"
    assert resolution["sourceRunId"] == RUN_ID


def env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_validate_inputs_writes_normalized_e2e_env_before_handoff(tmp_path: Path, monkeypatch):
    github_env = tmp_path / "github-env.txt"
    github_output = tmp_path / "github-output.txt"
    output = tmp_path / "source.json"
    monkeypatch.setenv("GITHUB_ENV", str(github_env))
    monkeypatch.setenv("E2E_MODE", "standard")
    monkeypatch.setenv("E2E_SCOPE", "settings")
    monkeypatch.setenv("SCREENSHOT_WORKERS_INPUT", "auto")
    monkeypatch.setenv("RESOURCE_TELEMETRY_INPUT", "false")
    monkeypatch.setenv("VERIFY_RESTART_INPUT", "false")
    monkeypatch.setattr(sys, "argv", [
        "verify_fast_ci_e2e_handoff.py", "validate-inputs",
        "--fast-ci-run-id", str(RUN_ID),
        "--output", str(output),
        "--github-output", str(github_output),
    ])

    assert HANDOFF.main() == 0
    values = env_values(github_env)
    assert values["ANKI_E2E_SCOPE"] == "settings"
    assert values["ANKI_E2E_SCREENSHOT_WORKERS"] == "3"
    assert values["ANKI_E2E_RESOURCE_TELEMETRY"] == "0"
    assert values["ANKI_E2E_VERIFY_RESTART"] == "0"
    assert values["ANKI_E2E_PACKAGE_SOURCE"] == "fast-ci-artifact"
    assert values["ANKI_E2E_FAST_CI_RUN_ID"] == str(RUN_ID)


def test_invalid_package_source_keeps_safe_diagnostic_env(tmp_path: Path, monkeypatch):
    github_env = tmp_path / "github-env.txt"
    monkeypatch.setenv("GITHUB_ENV", str(github_env))
    monkeypatch.setenv("E2E_MODE", "standard")
    monkeypatch.setenv("E2E_SCOPE", "settings")
    monkeypatch.setenv("SCREENSHOT_WORKERS_INPUT", "auto")
    monkeypatch.setenv("RESOURCE_TELEMETRY_INPUT", "false")
    monkeypatch.setenv("VERIFY_RESTART_INPUT", "false")
    monkeypatch.setattr(sys, "argv", [
        "verify_fast_ci_e2e_handoff.py", "validate-inputs",
        "--release-artifact-name", "release",
        "--release-artifact-sha256", "a" * 64,
        "--fast-ci-run-id", str(RUN_ID),
        "--output", str(tmp_path / "source.json"),
    ])

    assert HANDOFF.main() == 1
    values = env_values(github_env)
    assert values["ANKI_E2E_SCOPE"] == "settings"
    assert values["ANKI_E2E_SCREENSHOT_WORKERS"] == "3"
    assert values["ANKI_E2E_PACKAGE_SOURCE"] == "source-build"


def test_workflow_preserves_early_failure_and_strict_upload_contract():
    text = (ROOT / ".github" / "workflows" / "ci-e2e.yml").read_text(encoding="utf-8")
    initialize = text.index("Capture workflow source and validate package source inputs")
    resolve = text.index("Resolve exact successful Fast CI run and artifact IDs")
    prepare = text.index("Prepare redacted public E2E artifact")
    upload = text.index("Upload redacted E2E diagnostics")
    assert initialize < resolve < prepare < upload
    assert "CI_E2E_EXIT_CODE=1" in text[initialize:resolve]
    assert "ANKI_E2E_BUILD_DURATION_MS=0" in text[initialize:resolve]
    assert "ANKI_E2E_CACHE_STATE=unavailable" in text[initialize:resolve]
    assert "verify_fast_ci_e2e_handoff.py validate-inputs" in text[initialize:resolve]
    assert "if: always()" in text[prepare:upload]
    upload_block = text[upload:text.index("Report artifact upload telemetry", upload)]
    assert "if: always()" in upload_block
    assert "if-no-files-found: error" in upload_block


def test_early_fast_handoff_failure_creates_safe_public_artifact(tmp_path: Path, monkeypatch):
    source = tmp_path / "missing-e2e-artifacts"
    raw = tmp_path / "ci-e2e-raw"
    raw.mkdir()
    secret = "fixture-dashboard-token-value"
    (raw / "docker-system.txt").write_text(
        f"before failure https://127.0.0.1/?token={secret}\n", encoding="utf-8"
    )
    output = tmp_path / "ci-e2e"
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/chatgpt/ci-optimization-stage-3-e2e-package-handoff")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_WORKFLOW", "Full Docker / Anki E2E")
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(sys, "argv", [
        "prepare_ci_e2e_artifacts.py",
        "--source", str(source),
        "--output", str(output),
        "--raw-logs", str(raw),
        "--mode", "standard",
        "--scope", "settings",
        "--screenshot-workers", "3",
        "--build-duration-ms", "0",
        "--image-size-bytes", "0",
        "--cache-state", "unavailable",
        "--e2e-exit-code", "1",
        "--started-at", "2026-07-16T00:00:00Z",
        "--commit-sha", SHA,
        "--ref", "refs/heads/test",
        "--package-source", "fast-ci-artifact",
        "--source-fast-ci-run-id", str(RUN_ID),
        "--source-fast-ci-tested-sha", "",
        "--source-package-sha256", "",
        "--e2e-checkout-sha", SHA,
    ])

    assert ARTIFACTS.main() == 0
    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    assert summary["result"] == "failure"
    assert summary["failureCategory"] == "fast-ci-handoff"
    assert summary["packageSource"] == "fast-ci-artifact"
    assert summary["sourceFastCiRunId"] == RUN_ID
    assert summary["sourceFastCiTestedSha"] is None
    assert summary["sourcePackageSha256"] is None
    assert summary["e2eCheckoutSha"] == SHA
    assert summary["dockerBuildDurationMs"] == 0
    assert summary["cacheState"] == "unavailable"
    assert summary["screenshotCount"] == 0
    assert all(row["status"] == "absent" for row in summary["productBuildPhases"].values())
    assert (output / "ci-e2e-summary.md").is_file()
    assert (output / "environment.txt").is_file()
    exported = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file() and path.suffix in {".json", ".md", ".txt", ".log"}
    )
    assert secret not in exported
    assert "?token=" not in exported
    assert "fast-ci-run.json" not in exported


def test_validate_package_restores_diagnostics_directory_after_clean_checkout(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolution = tmp_path / "resolution.json"
    diagnostics = tmp_path / "diagnostics.json"
    package_dir = tmp_path / "package"
    output = tmp_path / "handoff.json"
    resolution.write_text("{}", encoding="utf-8")
    diagnostics.write_text("{}", encoding="utf-8")
    package_dir.mkdir()

    monkeypatch.setattr(HANDOFF, "validate_package_handoff", lambda **_: {
        "packageSha256": "e" * 64,
        "packageSizeBytes": 123,
        "sourceTestedCommitSha": SHA,
    })
    monkeypatch.setattr(sys, "argv", [
        "verify_fast_ci_e2e_handoff.py", "validate-package",
        "--resolution", str(resolution),
        "--diagnostics", str(diagnostics),
        "--directory", str(package_dir),
        "--e2e-workflow-source-sha", SHA,
        "--e2e-checkout-sha", SHA,
        "--output", str(output),
    ])

    assert not (tmp_path / "ci-e2e-raw").exists()
    assert HANDOFF.main() == 0
    assert (tmp_path / "ci-e2e-raw").is_dir()
    assert json.loads(output.read_text(encoding="utf-8"))["packageSha256"] == "e" * 64


def test_successful_fast_summary_still_requires_complete_identity(tmp_path: Path):
    output = tmp_path / "output"
    (output / "artifacts").mkdir(parents=True)
    (output / "logs").mkdir()
    args = argparse_namespace(
        e2e_exit_code=0,
        package_source="fast-ci-artifact",
        source_fast_ci_run_id=str(RUN_ID),
        source_fast_ci_tested_sha="",
        source_package_sha256="",
        e2e_checkout_sha=SHA,
    )
    with pytest.raises(ValueError, match="successful fast-ci-artifact"):
        ARTIFACTS.write_summary(output, args=args, manifest_status="missing", artifact_files=[])


def argparse_namespace(**overrides):
    from argparse import Namespace

    values = {
        "started_at": "2026-07-16T00:00:00Z",
        "e2e_exit_code": 1,
        "commit_sha": SHA,
        "ref": "refs/heads/test",
        "mode": "standard",
        "scope": "settings",
        "screenshot_workers": 3,
        "cache_state": "unavailable",
        "build_duration_ms": 0,
        "image_size_bytes": 0,
        "package_source": "source-build",
        "source_fast_ci_run_id": "",
        "source_fast_ci_tested_sha": "",
        "source_package_sha256": "",
        "e2e_checkout_sha": SHA,
    }
    values.update(overrides)
    return Namespace(**values)
