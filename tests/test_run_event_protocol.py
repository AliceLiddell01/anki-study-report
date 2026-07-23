from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"


def load_protocol():
    spec = importlib.util.spec_from_file_location("asr_run_event_protocol", PROTOCOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


protocol = load_protocol()


def event(**overrides):
    value = {
        "schemaVersion": 1,
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
    local = load_protocol()
    local.emit(
        Path(output),
        "fast-ci",
        "frontend-vitest",
        "message",
        "info",
        message=f"worker={index}",
        echo=False,
    )


def test_valid_schema_v1_event_and_deterministic_serialization() -> None:
    normalized = protocol.validate_event(event())
    serialized = protocol.serialize_event(normalized)
    assert list(normalized) == list(protocol.EVENT_FIELDS)
    assert serialized == json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    assert " " not in serialized


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schemaVersion", 2, "schemaVersion"),
        ("status", "success", "unknown status"),
        ("eventKind", "step", "unknown eventKind"),
        ("phaseId", "not-registered", "unknown phaseId"),
    ],
)
def test_unknown_schema_status_kind_and_phase_are_rejected(field: str, value, message: str) -> None:
    with pytest.raises(protocol.RunEventError, match=message):
        protocol.validate_event(event(**{field: value}))


def test_utc_timestamp_elapsed_and_duration_are_validated() -> None:
    protocol.validate_event(event(timestampUtc="2026-07-24T00:00:00.000Z", elapsedMs=0, durationMs=0))
    with pytest.raises(protocol.RunEventError, match="timestampUtc"):
        protocol.validate_event(event(timestampUtc="2026-07-24T00:00:00+02:00"))
    with pytest.raises(protocol.RunEventError, match="non-negative"):
        protocol.validate_event(event(elapsedMs=-1))
    with pytest.raises(protocol.RunEventError, match="non-negative"):
        protocol.validate_event(event(durationMs=-1))


def test_message_and_line_bounds_are_enforced() -> None:
    protocol.validate_event(event(message="x" * protocol.MAX_MESSAGE_BYTES))
    with pytest.raises(protocol.RunEventError, match="exceeds"):
        protocol.validate_event(event(message="я" * protocol.MAX_MESSAGE_BYTES))


def test_token_urls_absolute_paths_and_secrets_are_rejected() -> None:
    unsafe = [
        "https://127.0.0.1/?token=secret",
        r"C:\\Users\\owner\\secret.txt",
        "/home/owner/private.txt",
        "Authorization: Bearer secret-value",
        "::warning::unsafe workflow command",
    ]
    for value in unsafe:
        with pytest.raises(protocol.RunEventError):
            protocol.validate_event(event(message=value))


def test_control_characters_newlines_and_nul_are_rejected() -> None:
    for value in ("line\nbreak", "line\rbreak", "nul\0byte", "tab\tvalue"):
        with pytest.raises(protocol.RunEventError, match="control"):
            protocol.validate_event(event(message=value))


def test_progress_fields_are_bounded_and_paired() -> None:
    protocol.validate_event(event(current=1, total=2))
    with pytest.raises(protocol.RunEventError, match="both"):
        protocol.validate_event(event(current=1, total=None))
    with pytest.raises(protocol.RunEventError, match="current <= total"):
        protocol.validate_event(event(current=3, total=2))


def test_jsonl_append_stream_validation_and_console_format(tmp_path: Path, capsys) -> None:
    output = tmp_path / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci", message="scope=canonical")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "start")
    protocol.emit(output, "fast-ci", "frontend-vitest", "phase", "pass", duration_ms=12)
    protocol.finish_run(output, "fast-ci", "pass")

    events = protocol.validate_stream(output, expected_producer="fast-ci")
    assert [item["status"] for item in events] == ["start", "start", "pass", "pass"]
    assert output.read_bytes().endswith(b"\n")
    assert not output.read_bytes().startswith(b"\xef\xbb\xbf")
    console = capsys.readouterr().out
    assert "[FAST] [frontend-vitest] START" in console
    assert "[FAST] [frontend-vitest] PASS duration=12ms" in console
    assert not protocol.state_path(output).exists()


def test_concurrent_cross_process_append_has_no_corrupted_lines(tmp_path: Path) -> None:
    output = tmp_path / "run-events.jsonl"
    protocol.initialize_stream(output, "fast-ci", echo=False)
    items = [(str(output), index) for index in range(24)]
    with ProcessPoolExecutor(max_workers=6) as executor:
        list(executor.map(worker_append, items))
    protocol.finish_run(output, "fast-ci", "pass", echo=False)

    events = protocol.validate_stream(output, expected_producer="fast-ci")
    messages = [item["message"] for item in events if item["eventKind"] == "message"]
    assert sorted(messages) == sorted(f"worker={index}" for index in range(24))
    assert len(output.read_text(encoding="utf-8").splitlines()) == 26


def test_stream_rejects_partial_nondeterministic_and_mixed_lines(tmp_path: Path) -> None:
    output = tmp_path / "bad.jsonl"
    output.write_text('{"schemaVersion":1}', encoding="utf-8")
    with pytest.raises(protocol.RunEventError, match="newline-terminated"):
        protocol.validate_stream(output)

    output.write_text(json.dumps(event()) + "\n", encoding="utf-8")
    with pytest.raises(protocol.RunEventError, match="deterministically serialized"):
        protocol.validate_stream(output, require_final=False)


def test_failure_code_is_reserved_for_e2e_i3() -> None:
    with pytest.raises(protocol.RunEventError, match="reserved"):
        protocol.validate_event(event(failureCode="ASR-E2E-EXAMPLE"))


def test_phase_registries_are_shell_independent_and_stable() -> None:
    assert "frontend-vitest" in protocol.FAST_CI_PHASES
    assert "browser-smoke-first" in protocol.DOCKER_E2E_PHASES
    assert all(" " not in phase_id for phases in protocol.PHASE_REGISTRY.values() for phase_id in phases)
    assert protocol.PRODUCERS == {"fast-ci", "docker-e2e"}
