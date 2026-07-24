from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"


def load_protocol(name="asr_run_event_protocol"):
    spec = importlib.util.spec_from_file_location(name, PROTOCOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


protocol = load_protocol()


def event(schema=1, **overrides):
    value = {
        "schemaVersion": schema,
        "timestampUtc": "2026-07-24T00:00:00.000Z",
        "elapsedMs": 123,
        "producer": "fast-ci",
        "phaseId": "frontend-vitest",
        "eventKind": "phase",
        "status": "pass",
        "durationMs": 100,
        "current": None,
        "total": None,
        "message": None,
        "failureCode": None,
    }
    value.update(overrides)
    return value


def worker_append(args):
    output, index = args
    local = load_protocol(f"asr_run_event_protocol_worker_{index}")
    local.emit(Path(output), "fast-ci", "frontend-vitest", "message", "info", message=f"worker={index}", echo=False)
    return index


def test_concurrent_cross_process_append_has_no_corrupted_lines(tmp_path: Path):
    output = tmp_path / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci", echo=False)
    with ProcessPoolExecutor(max_workers=4) as executor:
        assert sorted(executor.map(worker_append, [(str(output), index) for index in range(12)])) == list(range(12))
    protocol.finish_run(output, "fast-ci", "pass", echo=False)
    events = protocol.validate_stream(output, expected_producer="fast-ci")
    messages = [item["message"] for item in events if item["eventKind"] == "message"]
    assert sorted(messages) == sorted(f"worker={index}" for index in range(12))


def test_security_bounds_and_deterministic_serialization():
    normalized = protocol.validate_event(event(schema=2, message="bounded message"))
    assert protocol.serialize_event(normalized) == json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    for unsafe in (
        "https://127.0.0.1/?token=secret",
        r"C:\\Users\\owner\\secret.txt",
        "/home/owner/private.txt",
        "Authorization: Bearer secret-value",
        "::warning::unsafe",
    ):
        with pytest.raises(protocol.RunEventError):
            protocol.validate_event(event(schema=2, message=unsafe))


def test_unknown_schema_and_partial_stream_are_rejected(tmp_path: Path):
    with pytest.raises(protocol.RunEventError, match="schemaVersion"):
        protocol.validate_event(event(schema=3))
    output = tmp_path / "bad.jsonl"
    output.write_text('{"schemaVersion":2}', encoding="utf-8")
    with pytest.raises(protocol.RunEventError, match="newline-terminated"):
        protocol.validate_stream(output)


def test_phase_registries_match_failure_protocol():
    assert (protocol.FAST_CI_PHASES | protocol.DOCKER_E2E_PHASES) - {"run"} == protocol.failure_protocol.ALL_PHASES
    assert set(protocol.failure_protocol.PHASE_FAILURE_CODES) == protocol.failure_protocol.ALL_PHASES
