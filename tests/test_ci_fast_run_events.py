from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci_fast_timing.py"
SHA = "a" * 40


def run(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_writes_timing_and_run_events_with_shared_phase_ids(tmp_path: Path) -> None:
    timing = tmp_path / "timing.json"
    events = tmp_path / "run-events.jsonl"
    env = os.environ.copy()
    env["ASR_RUN_EVENTS_PATH"] = str(events)

    result = run(
        "initialize",
        "--output", str(timing),
        "--repository", "AliceLiddell01/anki-study-report",
        "--event-name", "workflow_dispatch",
        "--ref", "refs/heads/example",
        "--tested-commit-sha", SHA,
        "--run-id", "123",
        "--run-attempt", "1",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "[FAST] [run] START" in result.stdout

    assert run("start", "--output", str(timing), "--phase-id", "frontend-vitest", env=env).returncode == 0
    assert run(
        "finish", "--output", str(timing), "--phase-id", "frontend-vitest", "--exit-code", "0", env=env
    ).returncode == 0
    assert run("finalize", "--output", str(timing), "--result", "success", env=env).returncode == 0
    assert run("validate", "--output", str(timing), env=env).returncode == 0

    timing_payload = json.loads(timing.read_text(encoding="utf-8"))
    event_rows = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert timing_payload["result"] == "success"
    assert timing_payload["phases"][0]["id"] == "frontend-vitest"
    assert [row["phaseId"] for row in event_rows] == ["run", "frontend-vitest", "frontend-vitest", "run"]
    assert [row["status"] for row in event_rows] == ["start", "start", "pass", "pass"]


def test_library_surface_remains_compatible_without_event_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ASR_RUN_EVENTS_PATH", raising=False)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import ci_fast_timing

        output = tmp_path / "timing.json"
        ci_fast_timing.initialize(
            output,
            "AliceLiddell01/anki-study-report",
            "local",
            "refs/heads/local",
            SHA,
            1,
            1,
        )
        ci_fast_timing.start_phase(output, "python-pytest")
        ci_fast_timing.finish_phase(output, "python-pytest", 0)
        document = ci_fast_timing.finalize(output, "success")
        assert document["result"] == "success"
        assert ci_fast_timing.validate_document(document)["phases"][0]["id"] == "python-pytest"
    finally:
        sys.path.pop(0)
