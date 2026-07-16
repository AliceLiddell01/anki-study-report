from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_CHECK = ROOT / "scripts" / "run_full_check.ps1"


def text() -> str:
    return FULL_CHECK.read_text(encoding="utf-8")


def test_default_contract_keeps_timing_optional_and_skip_docker_unchanged() -> None:
    source = text()
    assert '[string]$TimingOutput = ""' in source
    assert "if (-not $TimingOutputPath)" in source
    assert "if (-not $SkipDocker)" in source
    assert "if (-not $DockerOnly)" in source
    assert "Docker E2E" in source


def test_canonical_command_order_is_preserved_and_split_only_for_measurement() -> None:
    source = text()
    ordered = [
        '"changelog-check"',
        '"frontend-typecheck-tests"',
        '"frontend-vitest"',
        '"frontend-typecheck-build"',
        '"frontend-vite-build"',
        '"frontend-bundle-check"',
        '"frontend-addon-assets-copy"',
        '"python-pytest"',
        '"package-build-check"',
        '"package-check-only"',
    ]
    positions = [source.index(value) for value in ordered]
    assert positions == sorted(positions)
    assert '@("run", "typecheck")' in source
    assert '@("run", "test:run")' in source
    assert '@("run", "build:vite")' in source
    assert '@("run", "build:check-bundle")' in source
    assert '@("run", "build:copy-addon")' in source
    assert '@("scripts/run_python.mjs", "-m", "pytest")' in source
    assert '@("scripts/run_python.mjs", "scripts/package_addon.py", "--check")' in source
    assert '@("scripts/run_python.mjs", "scripts/package_addon.py", "--check-only")' in source


def test_failure_preserves_primary_error_and_attempts_timing_finish() -> None:
    source = text()
    assert "$commandError = $_" in source
    assert "if ($exitCode -eq 0)" in source
    assert "Timing finalization failed after the canonical command failure" in source
    assert "if ($commandError) {\n        throw $commandError\n    }" in source


def test_timing_is_initialized_locally_or_validated_when_preinitialized() -> None:
    source = text()
    assert "Initialize-TimingIfNeeded" in source
    assert '"validate", "--output", $TimingOutputPath, "--allow-running"' in source
    assert '"initialize", "--output", $TimingOutputPath' in source
    assert '$runId = if ($env:GITHUB_RUN_ID)' in source


def test_no_docker_timing_or_new_docker_work_is_introduced() -> None:
    source = text()
    docker_section = source[source.index("if (-not $SkipDocker)") :]
    assert "TimingPhase" not in docker_section
    assert "docker compose" in source.lower()
