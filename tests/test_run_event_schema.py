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


def test_historical_schema_v1_remains_valid():
    normalized = protocol.validate_event(event(schema=1))
    assert normalized["schemaVersion"] == 1
    assert normalized["failureCode"] is None
    with pytest.raises(protocol.RunEventError, match="historical schema v1"):
        protocol.validate_event(event(schema=1, status="fail", failureCode="ASR-FAST-FRONTEND"))


def test_schema_v2_success_event_requires_null_failure_code():
    normalized = protocol.validate_event(event(schema=2))
    assert normalized["schemaVersion"] == 2
    with pytest.raises(protocol.RunEventError, match="failureCode=null"):
        protocol.validate_event(event(schema=2, failureCode="ASR-FAST-FRONTEND"))


def test_schema_v2_failure_requires_known_phase_compatible_code():
    normalized = protocol.validate_event(event(schema=2, status="fail", failureCode="ASR-FAST-FRONTEND"))
    assert normalized["failureCode"] == "ASR-FAST-FRONTEND"
    with pytest.raises(protocol.RunEventError, match="require failureCode"):
        protocol.validate_event(event(schema=2, status="fail", failureCode=None))
    with pytest.raises(protocol.failure_protocol.FailureProtocolError, match="unknown failure code"):
        protocol.validate_event(event(schema=2, status="fail", failureCode="ASR-FAST-NOT-REGISTERED"))
    with pytest.raises(protocol.RunEventError, match="not allowed"):
        protocol.validate_event(event(schema=2, status="fail", failureCode="ASR-FAST-PYTHON"))


def test_schema_v2_success_stream(tmp_path: Path):
    output = tmp_path / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci", message="pipeline=canonical")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "start")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "pass", duration_ms=12)
    protocol.finish_run(output, "fast-ci", "pass")
    events = protocol.validate_stream(output, expected_producer="fast-ci")
    assert {item["schemaVersion"] for item in events} == {2}
    assert all(item["failureCode"] is None for item in events)
    assert not protocol.failure_summary_path(output).exists()


def test_schema_v2_failure_stream_creates_summary_and_code_parity(tmp_path: Path):
    output = tmp_path / "ci-fast" / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "start")
    failed = protocol.emit(
        output,
        "fast-ci",
        "frontend-vitest",
        "phase",
        "fail",
        duration_ms=20,
        message="Frontend tests failed",
        original_exit_code=1,
    )
    final = protocol.finish_run(output, "fast-ci", "fail", original_exit_code=1)
    assert failed["failureCode"] == "ASR-FAST-FRONTEND"
    assert final["failureCode"] == "ASR-FAST-FRONTEND"
    summary = protocol.failure_protocol.load_document(protocol.failure_summary_path(output))
    assert summary["primary"]["failureCode"] == final["failureCode"]
    protocol.validate_stream(output, expected_producer="fast-ci")


def test_run_fail_code_must_equal_primary(tmp_path: Path):
    output = tmp_path / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "start")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "fail", duration_ms=1, original_exit_code=1)
    bad = protocol.build_event(
        output=output,
        producer="fast-ci",
        phase_id="run",
        event_kind="run",
        status="fail",
        duration_ms=2,
        failure_code="ASR-FAST-UNKNOWN",
    )
    protocol.append_event(output, bad, echo=False)
    with pytest.raises(protocol.RunEventError, match="primary failure code"):
        protocol.validate_stream(output, expected_producer="fast-ci")


def test_mixed_schema_stream_is_rejected(tmp_path: Path):
    output = tmp_path / "run-events.jsonl"
    first = event(schema=1, phaseId="run", eventKind="run", status="start", durationMs=None)
    second = event(schema=2)
    output.write_text(protocol.serialize_event(first) + "\n" + protocol.serialize_event(second) + "\n", encoding="utf-8")
    with pytest.raises(protocol.RunEventError, match="mixes schema versions"):
        protocol.validate_stream(output, require_final=False)


def test_cancellation_uses_producer_specific_reserved_code(tmp_path: Path):
    fast = tmp_path / "fast.jsonl"
    protocol.initialize_stream(fast, "fast-ci")
    final = protocol.finish_run(fast, "fast-ci", "cancel", original_exit_code=130)
    assert final["failureCode"] == "ASR-FAST-CANCELLED"
    assert final["message"] == "exit=130 signal=unknown"
    assert not protocol.failure_summary_path(fast).exists()
    fast_summary = protocol.cancellation_protocol.load_document(
        protocol.cancellation_summary_path(fast)
    )
    assert fast_summary["cancellationCode"] == final["failureCode"]
    assert fast_summary["originalExitCode"] == 130
    assert fast_summary["originalSignal"] is None

    e2e = tmp_path / "reports" / "run-events.jsonl"
    protocol.initialize_stream(e2e, "docker-e2e")
    final = protocol.finish_run(
        e2e,
        "docker-e2e",
        "cancel",
        original_exit_code=143,
        original_signal="SIGTERM",
    )
    assert final["failureCode"] == "ASR-E2E-CANCELLED"
    assert final["message"] == "exit=143 signal=SIGTERM"
    assert not protocol.failure_summary_path(e2e).exists()
    e2e_summary = protocol.cancellation_protocol.load_document(
        protocol.cancellation_summary_path(e2e)
    )
    assert e2e_summary["cancellationCode"] == final["failureCode"]
    assert e2e_summary["originalExitCode"] == 143
    assert e2e_summary["originalSignal"] == "SIGTERM"
