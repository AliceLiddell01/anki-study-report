from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"


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
