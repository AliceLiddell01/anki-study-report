from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from run_event_contract import *
from run_event_context import summary_primary_code
from run_event_storage import failure_summary_path


def validate_stream(
    output: Path, *, expected_producer: str | None = None, require_final: bool = True
) -> list[dict[str, Any]]:
    try:
        raw = output.read_bytes()
    except FileNotFoundError as exc:
        raise RunEventError(f"run event stream does not exist: {output}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RunEventError("run event stream must be UTF-8 without BOM")
    if not raw or not raw.endswith(b"\n"):
        raise RunEventError("run event stream must be non-empty and newline-terminated")
    events: list[dict[str, Any]] = []
    for index, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line:
            raise RunEventError(f"run event line {index} is empty")
        if len(raw_line) > MAX_LINE_BYTES:
            raise RunEventError(f"run event line {index} exceeds {MAX_LINE_BYTES} bytes")
        try:
            line = raw_line.decode("utf-8")
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunEventError(f"run event line {index} is not valid UTF-8 JSON") from exc
        normalized = validate_event(value, expected_producer=expected_producer)
        if serialize_event(normalized, validate=False) != line:
            raise RunEventError(f"run event line {index} is not deterministically serialized")
        events.append(normalized)
    if not events or events[0]["eventKind"] != "run" or events[0]["status"] != "start":
        raise RunEventError("run event stream must begin with run/start")
    producer = expected_producer or events[0]["producer"]
    if any(event["producer"] != producer for event in events):
        raise RunEventError("run event stream mixes producers")
    versions = {event["schemaVersion"] for event in events}
    if len(versions) != 1:
        raise RunEventError("run event stream mixes schema versions")
    elapsed = [event["elapsedMs"] for event in events]
    if elapsed != sorted(elapsed):
        raise RunEventError("run event elapsedMs values must be non-decreasing")
    final_events = [
        event for event in events
        if event["eventKind"] == "run" and event["status"] in {"pass", "fail", "cancel"}
    ]
    if require_final and (len(final_events) != 1 or events[-1] is not final_events[0]):
        raise RunEventError("finalized stream must end with exactly one run result")
    if not require_final and len(final_events) > 1:
        raise RunEventError("run event stream contains multiple final run results")
    if SCHEMA_VERSION in versions and final_events:
        final = final_events[0]
        if final["status"] == "fail":
            phase_failures = [
                event for event in events if event["eventKind"] == "phase" and event["status"] == "fail"
            ]
            expected = summary_primary_code(output) or (
                phase_failures[0]["failureCode"] if phase_failures else final["failureCode"]
            )
            if final["failureCode"] != expected:
                raise RunEventError("run/fail failureCode differs from primary failure code")
        if final["status"] == "pass" and failure_summary_path(output).exists():
            raise RunEventError("successful run must not contain failure-summary.json")
    return events
