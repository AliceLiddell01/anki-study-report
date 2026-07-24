from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_docker_image_uses_outer_failure_wrapper() -> None:
    dockerfile = text("docker/anki-e2e/Dockerfile")
    wrapper = text("docker/anki-e2e/run-e2e-failure-wrapper.sh")
    assert 'CMD ["/e2e/bin/run-e2e-failure-wrapper.sh"]' in dockerfile
    assert 'core="/e2e/bin/run-e2e.sh"' in wrapper
    assert 'status=$?' in wrapper
    assert "ASR-E2E-UNKNOWN" in wrapper
    assert "ASR-E2E-CANCELLED" in wrapper
    assert 'failure-summary.json' in wrapper
    assert 'run_event_protocol.py validate' in wrapper


def test_cleanup_failure_is_recorded_without_overwriting_primary() -> None:
    source = text("docker/anki-e2e/stop-anki.sh")
    assert 'command="record-primary"' in source
    assert '[ -f "$summary_path" ] && command="record-secondary"' in source
    assert "ASR-E2E-CLEANUP" in source
    assert "set-cleanup-status" in source
    assert "--status failure" in source


def test_public_export_validates_source_and_public_failure_summary() -> None:
    source = text("scripts/prepare_ci_e2e_artifacts.py")
    bridge = text("scripts/failure_artifact_protocol.py")
    assert "ensure_source_contract" in source
    assert "validate_public_contract" in source
    assert "record_sanitization_failure" in source
    assert "publish_minimal_failure" in source
    assert source.count("emit_github_failure") == 2  # success and sanitizer-failure branches, only one executes
    assert '"ASR-E2E-SANITIZATION"' in bridge
    assert 'output.resolve() / "artifacts" / "reports" / "failure-summary.json"' in bridge


def test_browser_subprocess_model_remains_bounded_and_daemon_free() -> None:
    source = text("docker/anki-e2e/browser-progress.mjs")
    assert 'execFile(' in source
    assert 'shell: false' in source
    assert "runEventProducerCalls" in source
    assert "runEventProducerDurationMs" in source
    assert "runEventProducerFailures" in source
    assert "createServer" not in source
    assert "WebSocket" not in source
    assert "daemon" not in source.lower()
    assert "@playwright/test" not in source
    assert "retry" not in source.lower()


def test_no_generated_failure_summary_is_tracked() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "*failure-summary.json", "*run-events.jsonl"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        assert completed.stdout.strip() == ""


def test_shell_and_node_syntax() -> None:
    for relative in (
        "docker/anki-e2e/run-e2e-failure-wrapper.sh",
        "docker/anki-e2e/stop-anki.sh",
    ):
        completed = subprocess.run(["bash", "-n", str(ROOT / relative)], text=True, capture_output=True, check=False)
        assert completed.returncode == 0, completed.stderr
    for relative in (
        "docker/anki-e2e/browser-progress.mjs",
        "docker/anki-e2e/browser-report-contract.mjs",
        "docker/anki-e2e/smoke-browser-wrapper.mjs",
    ):
        completed = subprocess.run(["node", "--check", str(ROOT / relative)], text=True, capture_output=True, check=False)
        assert completed.returncode == 0, completed.stderr
