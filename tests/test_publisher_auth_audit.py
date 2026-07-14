from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts.audit_publisher_auth_artifacts import (
    audit_publisher_artifacts,
    normalize_report_path,
)

from conftest import ROOT


def touch(path: Path, content: str = "safe") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_dependency_cookie_sources_and_sanitized_outputs_are_allowed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    touch(workspace / "web-dashboard/node_modules/jsdom/NavigatorCookies-impl.js")
    touch(workspace / "web-dashboard/node_modules/playwright-core/cookieStore.js")
    touch(workspace / "src/cookie_policy.py")
    touch(workspace / "tests/test_cookies.py")
    touch(workspace / "release-artifacts/ankiweb-publish-report.json")
    touch(workspace / "release-artifacts/anki_study_report.ankiaddon")

    assert audit_publisher_artifacts(workspace) == []


def test_real_auth_state_traces_and_profiles_are_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runner_temp = tmp_path / "runner-temp"
    forbidden = [
        workspace / "playwright/.auth/user.json",
        workspace / "storageState.json",
        workspace / "nested/storage-state.json",
        workspace / ".auth/session.json",
        workspace / "diagnostics/trace.zip",
        workspace / "publisher-auth.json",
    ]
    for path in forbidden:
        touch(path, "SECRET-CONTENT-MUST-NOT-LEAK")
    touch(workspace / "playwright-profile/Default/Cookies", "SECRET-PROFILE")
    touch(runner_temp / "asr-ankiweb-survivor/download.ankiaddon")

    findings = audit_publisher_artifacts(workspace, runner_temp)

    assert len(findings) == 8
    assert "workspace/playwright/.auth/user.json" in findings
    assert "workspace/storageState.json" in findings
    assert "workspace/nested/storage-state.json" in findings
    assert "workspace/.auth/session.json" in findings
    assert "workspace/diagnostics/trace.zip" in findings
    assert "workspace/publisher-auth.json" in findings
    assert "workspace/playwright-profile" in findings
    assert "runner-temp/asr-ankiweb-survivor" in findings
    assert all(not Path(item).is_absolute() for item in findings)
    assert "SECRET" not in " ".join(findings)


def test_cli_reports_only_safe_relative_paths_and_never_file_contents(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    secret = "COOKIE-VALUE-DO-NOT-PRINT"
    touch(workspace / ".auth/session.json", secret)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "audit_publisher_auth_artifacts.py"),
            "--workspace",
            str(workspace),
            "--runner-temp",
            str(tmp_path / "missing-runner-temp"),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 1
    assert "workspace/.auth/session.json" in result.stdout
    assert str(workspace) not in result.stdout
    assert secret not in result.stdout


def test_missing_workspace_and_runner_temp_are_safe(tmp_path: Path) -> None:
    assert audit_publisher_artifacts(tmp_path / "missing-workspace", tmp_path / "missing-temp") == []


def test_report_path_normalization_handles_windows_and_posix_separators() -> None:
    assert normalize_report_path(r".\playwright\.auth\user.json") == "playwright/.auth/user.json"
    assert normalize_report_path("./playwright//.auth/user.json") == "playwright/.auth/user.json"
