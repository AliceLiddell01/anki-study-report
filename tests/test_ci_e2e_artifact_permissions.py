from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"


def test_linux_artifact_ownership_is_restored_before_host_validation():
    text = RUNNER.read_text(encoding="utf-8")

    run = text.index("Invoke-DockerCompose $runArgs")
    restore = text.index("Restore-E2EArtifactOwnership -Volume $volume", run)
    validate = text.index("Assert-E2EArtifactManifest -ArtifactsRoot $ArtifactsDir", restore)

    assert run < restore < validate
    assert "try {\n        Invoke-DockerCompose $runArgs\n    } finally {" in text
    assert "if (-not $IsLinux)" in text
    restore_block = text.split("function Restore-E2EArtifactOwnership", 1)[1].split(
        "function Assert-E2EArtifactManifest", 1
    )[0]
    assert re.search(r'"run"\s*,\s*"--rm"\s*,\s*"--no-deps"\s*,\s*"-v"\s*,\s*\$Volume', restore_block)
    assert re.search(r'"--entrypoint"\s*,\s*"/bin/chown"', restore_block)
    assert '"$($uid):$($gid)"' in restore_block
    assert '"/e2e/artifacts"' in restore_block
