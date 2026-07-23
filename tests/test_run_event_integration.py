from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_protocol():
    path = ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"
    spec = importlib.util.spec_from_file_location("asr_protocol_integration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fast_ci_wrapper_preserves_current_timing_phase_registry() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import ci_fast_timing

        protocol = load_protocol()
        assert set(ci_fast_timing.PHASES) == protocol.FAST_CI_PHASES - {"run"}
    finally:
        sys.path.pop(0)


def test_docker_orchestrator_has_immediate_phase_lifecycle_and_keeps_telemetry() -> None:
    source = (ROOT / "docker" / "anki-e2e" / "run-e2e.sh").read_text(encoding="utf-8")
    protocol = load_protocol()
    for phase_id in protocol.DOCKER_E2E_PHASES - {"run"}:
        assert f'"{phase_id}"' in source
    assert "run_event emit --phase-id" in source
    assert "run_event finish-run" in source
    assert "/e2e/bin/e2e-telemetry.py record-phase" in source
    assert "/e2e/bin/e2e-telemetry.py finalize" in source
    assert 'phase_start "browser-smoke-first"' in source
    assert "[1/18]" not in source


def test_public_export_validates_source_and_copied_stream() -> None:
    source = (ROOT / "scripts" / "prepare_ci_e2e_artifacts.py").read_text(encoding="utf-8")
    assert 'source / "reports" / "run-events.jsonl"' in source
    assert 'output / "artifacts" / "reports" / "run-events.jsonl"' in source
    assert source.count("run_events.validate_stream") == 2
    assert 'status == "success"' in source


def test_compose_ci_mode_is_plain_noninteractive_and_local_gated() -> None:
    source = (ROOT / "scripts" / "run_anki_e2e_docker.ps1").read_text(encoding="utf-8")
    assert '$PlainCompose = ($env:GITHUB_ACTIONS -eq "true" -or $env:CI -eq "true")' in source
    assert '$env:COMPOSE_ANSI = "never"' in source
    assert '$env:COMPOSE_PROGRESS = "plain"' in source
    assert '$env:COMPOSE_MENU = "0"' in source
    assert '$env:COMPOSE_STATUS_STDOUT = "1"' in source
    assert '@("--ansi", "never", "--progress", "plain")' in source
    assert '$runArgs += "--no-TTY"' in source


def test_generated_event_stream_is_not_tracked() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "*run-events.jsonl"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        assert completed.stdout.strip() == ""
