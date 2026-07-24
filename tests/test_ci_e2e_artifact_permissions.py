from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "ci-e2e.yml"


def test_linux_artifact_ownership_is_restored_before_host_validation():
    text = RUNNER.read_text(encoding="utf-8")

    run = text.index("$scriptExit = Invoke-DockerComposeRaw -Arguments $runArgs")
    restore = text.index("Restore-E2EArtifactOwnership -Volume $volume", run)
    validate = text.index("Assert-E2EArtifactManifest -ArtifactsRoot $ArtifactsDir", restore)

    assert run < restore < validate
    assert "if ($scriptExit -notin @(130, 143)) {" in text
    assert "if ($scriptExit -eq 0) {" in text
    assert "if (-not $IsLinux)" in text
    restore_block = text.split("function Restore-E2EArtifactOwnership", 1)[1].split(
        "function Assert-E2EArtifactManifest", 1
    )[0]
    assert re.search(r'"run"\s*,\s*"--rm"\s*,\s*"--no-deps"\s*,\s*"-v"\s*,\s*\$Volume', restore_block)
    assert re.search(r'"--entrypoint"\s*,\s*"/bin/chown"', restore_block)
    assert '"$($uid):$($gid)"' in restore_block
    assert '"/e2e/artifacts"' in restore_block

def test_runner_is_valid_powershell_syntax():
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell is unavailable")

    env = os.environ.copy()
    env["ASR_PARSE_TARGET"] = str(RUNNER)
    command = (
        "$tokens = $null; $errors = $null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "$env:ASR_PARSE_TARGET, [ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
    )
    completed = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-Command", command],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

def test_cancelled_workflow_restores_ownership_before_preparing_evidence():
    text = WORKFLOW.read_text(encoding="utf-8")
    cleanup_start = text.index("- name: Clean cancelled Docker E2E state")
    prepare_start = text.index("- name: Prepare bounded cancellation artifact", cleanup_start)
    upload_start = text.index("- name: Upload bounded cancellation evidence", prepare_start)
    preflight_upload = text.index("- name: Upload canonical preflight failure evidence", upload_start)

    cleanup = text[cleanup_start:prepare_start]
    upload = text[upload_start:preflight_upload]

    temp_log = cleanup.index("$hostLog = Join-Path $env:RUNNER_TEMP")
    compose_down = cleanup.index("'down', '-v', '--remove-orphans'")
    ownership = cleanup.index("sudo chown -R -- $owner e2e-artifacts")
    copy_log = cleanup.index(
        "Copy-Item -LiteralPath $hostLog -Destination "
        "e2e-artifacts/diagnostics/cancellation-host.log -Force"
    )

    assert temp_log < compose_down < ownership < copy_log
    assert "Tee-Object -FilePath $hostLog" in cleanup
    assert "Tee-Object -FilePath e2e-artifacts/diagnostics" not in cleanup
    assert "/usr/bin/timeout 10s sudo chown -R --" in cleanup
    assert "if-no-files-found: error" in upload
