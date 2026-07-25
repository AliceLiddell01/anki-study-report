from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"


def load_protocol():
    spec = importlib.util.spec_from_file_location("asr_run_event_controlled_failure", PROTOCOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_controlled_failure_produces_a_valid_final_stream(tmp_path: Path) -> None:
    protocol = load_protocol()
    output = tmp_path / "run-events.jsonl"

    protocol.initialize_stream(output, "docker-e2e", message="mode=standard scope=cards", echo=False)
    protocol.emit(output, "docker-e2e", "browser-smoke-first", "phase", "start", echo=False)
    protocol.emit(
        output,
        "docker-e2e",
        "browser-smoke-first",
        "phase",
        "fail",
        duration_ms=25,
        message="controlled browser fixture failure",
        echo=False,
    )
    protocol.finish_run(output, "docker-e2e", "fail", duration_ms=30, echo=False)

    events = protocol.validate_stream(output, expected_producer="docker-e2e", require_final=True)
    assert [event["status"] for event in events] == ["start", "start", "fail", "fail"]
    assert events[-1]["eventKind"] == "run"
    assert events[-1]["durationMs"] == 30
    assert not protocol.state_path(output).exists()
    assert not protocol.lock_path(output).exists()
