import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_CHECK = ROOT / "scripts" / "run_full_check.ps1"
PACKAGE_JSON = ROOT / "web-dashboard" / "package.json"


def text() -> str:
    return FULL_CHECK.read_text(encoding="utf-8")


def test_default_contract_keeps_timing_optional_and_skip_docker_unchanged() -> None:
    source = text()
    assert '[string]$TimingOutput = ""' in source
    assert "if (-not $TimingOutputPath)" in source
    assert "if (-not $SkipDocker)" in source
    assert "if (-not $DockerOnly)" in source
    assert "Docker E2E" in source


def test_canonical_command_order_has_one_typecheck_before_tests_and_build() -> None:
    source = text()
    ordered = [
        '"changelog-check"',
        '"frontend-typecheck-tests"',
        '"frontend-vitest"',
        '"frontend-vite-build"',
        '"frontend-bundle-check"',
        '"frontend-addon-assets-copy"',
        '"python-pytest"',
        '"package-build-check"',
        '"package-check-only"',
    ]
    positions = [source.index(value) for value in ordered]
    assert positions == sorted(positions)
    assert source.count('@("run", "typecheck")') == 1
    assert '"frontend-typecheck-build"' not in source
    assert "Frontend typecheck before build" not in source
    assert '@("run", "test:run")' in source
    assert '@("run", "build:vite")' in source
    assert '@("run", "build:check-bundle")' in source
    assert '@("run", "build:copy-addon")' in source
    assert '@("scripts/run_python.mjs", "-m", "pytest")' in source
    assert '@("scripts/run_python.mjs", "scripts/package_addon.py", "--check")' in source
    assert '@("scripts/run_python.mjs", "scripts/package_addon.py", "--check-only")' in source


def test_standalone_frontend_build_keeps_its_own_typecheck() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    scripts = package["scripts"]
    assert scripts["typecheck"] == "tsc --noEmit"
    assert scripts["build"].split(" && ", 1)[0] == "pnpm run typecheck"
    assert scripts["build:addon"].split(" && ", 1)[0] == "pnpm run build"


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
