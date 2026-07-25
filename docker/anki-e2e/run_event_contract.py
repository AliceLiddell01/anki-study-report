from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))
import failure_protocol
from run_event_registry import *


class RunEventError(ValueError):
    pass


if (FAST_CI_PHASES | DOCKER_E2E_PHASES) - {"run"} != failure_protocol.ALL_PHASES:
    raise RuntimeError("run-event and failure phase registries differ")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _require_non_negative_int(value: Any, label: str, *, allow_none: bool = False) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RunEventError(f"{label} must be a non-negative integer")
    return value


def _safe_message(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RunEventError("message must be a string or null")
    if value != value.strip() or not value:
        raise RunEventError("message must be non-empty and trimmed")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise RunEventError("message contains control characters")
    if value.startswith("::"):
        raise RunEventError("message must not begin with a GitHub workflow command marker")
    if len(value.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise RunEventError(f"message exceeds {MAX_MESSAGE_BYTES} UTF-8 bytes")
    if TOKEN_URL_RE.search(value) or WINDOWS_ABSOLUTE_RE.search(value) or LINUX_ABSOLUTE_RE.search(value) or SECRET_RE.search(value):
        raise RunEventError("message contains private or secret-like data")
    return value


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise RunEventError("timestampUtc must be UTC ISO-8601 with millisecond precision")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RunEventError("timestampUtc is not a valid UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RunEventError("timestampUtc must use UTC")
    return value


def validate_event(event: dict[str, Any], *, expected_producer: str | None = None) -> dict[str, Any]:
    if not isinstance(event, dict) or tuple(event.keys()) != EVENT_FIELDS:
        raise RunEventError("run event differs from the supported field order")
    schema_version = event["schemaVersion"]
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise RunEventError("unsupported run event schemaVersion")
    producer = event["producer"]
    if producer not in PRODUCERS:
        raise RunEventError(f"unknown producer: {producer}")
    if expected_producer is not None and producer != expected_producer:
        raise RunEventError(f"producer mismatch: expected {expected_producer}, got {producer}")
    phase_id = event["phaseId"]
    if not isinstance(phase_id, str) or not PHASE_ID_RE.fullmatch(phase_id):
        raise RunEventError("phaseId has an invalid format")
    if phase_id not in PHASE_REGISTRY[producer]:
        raise RunEventError(f"unknown phaseId for {producer}: {phase_id}")
    event_kind = event["eventKind"]
    status = event["status"]
    if event_kind not in EVENT_KINDS:
        raise RunEventError(f"unknown eventKind: {event_kind}")
    if status not in STATUSES:
        raise RunEventError(f"unknown status: {status}")
    allowed_statuses = {"run": RUN_STATUSES, "phase": PHASE_STATUSES, "message": MESSAGE_STATUSES}[event_kind]
    if status not in allowed_statuses:
        raise RunEventError(f"status {status} is invalid for eventKind {event_kind}")
    if event_kind == "run" and phase_id != "run":
        raise RunEventError("run lifecycle events must use phaseId=run")
    if event_kind != "run" and phase_id == "run":
        raise RunEventError("phaseId=run is reserved for run lifecycle events")
    timestamp = _validate_timestamp(event["timestampUtc"])
    elapsed_ms = _require_non_negative_int(event["elapsedMs"], "elapsedMs")
    duration_ms = _require_non_negative_int(event["durationMs"], "durationMs", allow_none=True)
    current = _require_non_negative_int(event["current"], "current", allow_none=True)
    total = _require_non_negative_int(event["total"], "total", allow_none=True)
    if (current is None) != (total is None):
        raise RunEventError("current and total must either both be null or both be integers")
    if current is not None and (total == 0 or current > total):
        raise RunEventError("progress counters must satisfy 0 <= current <= total and total > 0")
    if status == "start" and duration_ms is not None:
        raise RunEventError("start events must not include durationMs")
    if event_kind == "message" and duration_ms is not None:
        raise RunEventError("message events must not include durationMs")
    message = _safe_message(event["message"])
    failure_code = event["failureCode"]
    terminal_failure = event_kind in {"run", "phase"} and status in {"fail", "cancel"}
    if schema_version == LEGACY_SCHEMA_VERSION:
        if failure_code is not None:
            raise RunEventError("failureCode must be null in historical schema v1")
    elif terminal_failure:
        if not isinstance(failure_code, str):
            raise RunEventError("schema v2 failure/cancel events require failureCode")
        meta = failure_protocol.definition(failure_code)
        expected_domain = "fast" if producer == "fast-ci" else "e2e"
        if meta.domain != expected_domain:
            raise RunEventError("failureCode domain differs from producer")
        if event_kind == "phase" and meta.allowed_phases and phase_id not in meta.allowed_phases:
            raise RunEventError("failureCode is not allowed for phaseId")
        reserved_cancel = "ASR-FAST-CANCELLED" if producer == "fast-ci" else "ASR-E2E-CANCELLED"
        if status == "cancel" and failure_code != reserved_cancel:
            raise RunEventError("cancel events require the reserved producer cancellation code")
    elif failure_code is not None:
        raise RunEventError("non-failure schema v2 events require failureCode=null")
    normalized = {
        "schemaVersion": schema_version,
        "timestampUtc": timestamp,
        "elapsedMs": elapsed_ms,
        "producer": producer,
        "phaseId": phase_id,
        "eventKind": event_kind,
        "status": status,
        "durationMs": duration_ms,
        "current": current,
        "total": total,
        "message": message,
        "failureCode": failure_code,
    }
    serialized = serialize_event(normalized, validate=False)
    if len(serialized.encode("utf-8")) > MAX_LINE_BYTES:
        raise RunEventError(f"serialized event exceeds {MAX_LINE_BYTES} UTF-8 bytes")
    return normalized


def serialize_event(event: dict[str, Any], *, validate: bool = True) -> str:
    normalized = validate_event(event) if validate else event
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def format_console(event: dict[str, Any]) -> str:
    normalized = validate_event(event)
    elapsed = normalized["elapsedMs"]
    hours, remainder = divmod(elapsed, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}" if hours else f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    domain = "FAST" if normalized["producer"] == "fast-ci" else "E2E"
    parts = [f"[{elapsed_text}]", f"[{domain}]", f"[{normalized['phaseId']}]", normalized["status"].upper()]
    if normalized["failureCode"]:
        parts.append(f"code={normalized['failureCode']}")
    if normalized["current"] is not None:
        parts.append(f"[{normalized['current']}/{normalized['total']}]")
    if normalized["durationMs"] is not None:
        parts.append(f"duration={normalized['durationMs']}ms")
    if normalized["message"] is not None:
        parts.append(normalized["message"])
    return " ".join(parts)
