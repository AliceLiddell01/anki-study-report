from __future__ import annotations

from pathlib import Path


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
    assert '"--no-deps"' in text
    assert '"-v",\n        $Volume' in text
    assert '"--entrypoint",\n        "/bin/chown"' in text
    assert '"$($uid):$($gid)"' in text
    assert '"/e2e/artifacts"' in text
