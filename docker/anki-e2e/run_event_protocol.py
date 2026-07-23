#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Iterator

SCHEMA_VERSION = 1
MAX_MESSAGE_BYTES = 512
MAX_LINE_BYTES = 2048
PRODUCERS = {"fast-ci", "docker-e2e"}
EVENT_KINDS = {"run", "phase", "message"}
STATUSES = {"start", "pass", "fail", "skip", "cancel", "info"}
RUN_STATUSES = {"start", "pass", "fail", "cancel"}
PHASE_STATUSES = {"start", "pass", "fail", "skip", "cancel"}
MESSAGE_STATUSES = {"info"}

FAST_CI_PHASES = {
    "run",
    "install-python-dependencies",
    "install-frontend-dependencies",
    "changelog-check",
    "frontend-typecheck-tests",
    "frontend-vitest",
    "frontend-typecheck-build",
    "frontend-vite-build",
    "frontend-bundle-check",
    "frontend-addon-assets-copy",
    "python-pytest",
    "package-build-check",
    "package-check-only",
    "verification-planner",
    "ci-summary",
    "package-metadata-write",
    "package-staged-validation",
    "package-metadata-verify",
}

DOCKER_E2E_PHASES = {
    "run",
    "workspace-copy",
    "exact-package-validation",
    "frontend-dependency-install",
    "frontend-build",
    "addon-package",
    "profile-bootstrap",
    "collection-bootstrap",
    "real-deck-import",
    "scenario-preparation",
    "addon-install",
    "anki-start-first",
    "dashboard-ready-first",
    "api-smoke-first",
    "browser-smoke-first",
    "anki-restart",
    "dashboard-ready-restart",
    "api-smoke-restart",
    "telemetry-restart",
    "artifact-manifest",
}

PHASE_REGISTRY = {
    "fast-ci": FAST_CI_PHASES,
    "docker-e2e": DOCKER_E2E_PHASES,
}

EVENT_FIELDS = (
    "schemaVersion",
    "timestampUtc",
    "elapsedMs",
    "producer",
    "phaseId",
    "eventKind",
    "status",
    "durationMs",
    "current",
    "total",
    "message",
    "failureCode",
)

UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
PHASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOKEN_URL_RE = re.compile(r"(?:https?://[^\s]+@|[?&](?:access_)?token=)", re.IGNORECASE)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:^|[\s'\"(])(?:[A-Z]:[\\/]|\\\\[^\\/\s]+[\\/])")
LINUX_ABSOLUTE_RE = re.compile(r"(?:^|[\s'\"(])/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:/|\b)")
SECRET_RE = re.compile(
    r"(?:authorization\s*:\s*bearer\s+\S+|-----BEGIN (?:OPENSSH |RSA )?PRIVATE KEY-----|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)


class RunEventError(ValueError):
    pass


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
    if TOKEN_URL_RE.search(value):
        raise RunEventError("message contains a token-bearing URL")
    if WINDOWS_ABSOLUTE_RE.search(value) or LINUX_ABSOLUTE_RE.search(value):
        raise RunEventError("message contains an absolute private path")
    if SECRET_RE.search(value):
        raise RunEventError("message contains secret-like data")
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
        raise RunEventError("run event differs from schema v1 field order")
    if event["schemaVersion"] != SCHEMA_VERSION:
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
    allowed_statuses = {
        "run": RUN_STATUSES,
        "phase": PHASE_STATUSES,
        "message": MESSAGE_STATUSES,
    }[event_kind]
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
    if event["failureCode"] is not None:
        raise RunEventError("failureCode is reserved for E2E-I3 and must be null in schema v1")

    normalized = {
        "schemaVersion": SCHEMA_VERSION,
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
        "failureCode": None,
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
    if hours:
        elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    else:
        elapsed_text = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    domain = "FAST" if normalized["producer"] == "fast-ci" else "E2E"
    parts = [f"[{elapsed_text}]", f"[{domain}]", f"[{normalized['phaseId']}]", normalized["status"].upper()]
    if normalized["current"] is not None:
        parts.append(f"[{normalized['current']}/{normalized['total']}]")
    if normalized["durationMs"] is not None:
        parts.append(f"duration={normalized['durationMs']}ms")
    if normalized["message"] is not None:
        parts.append(normalized["message"])
    return " ".join(parts)


def _sidecar_directory(output: Path) -> Path:
    if output.parent.name == "reports":
        return output.parent.parent / "runtime"
    return output.parent


def state_path(output: Path) -> Path:
    return _sidecar_directory(output) / (output.name + ".state.json")


def lock_path(output: Path) -> Path:
    return _sidecar_directory(output) / (output.name + ".lock")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def _exclusive_lock(output: Path) -> Iterator[None]:
    path = lock_path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_bytes(b"0")
    with path.open("r+b") as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.01)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load_state(output: Path) -> dict[str, Any]:
    path = state_path(output)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunEventError(f"run event state does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunEventError("run event state is not valid JSON") from exc
    if set(state) != {"schemaVersion", "producer", "startedEpochMs"}:
        raise RunEventError("run event state has an invalid shape")
    if state["schemaVersion"] != SCHEMA_VERSION or state["producer"] not in PRODUCERS:
        raise RunEventError("run event state identity is invalid")
    _require_non_negative_int(state["startedEpochMs"], "startedEpochMs")
    return state


def _elapsed_ms(output: Path, producer: str) -> int:
    state = _load_state(output)
    if state["producer"] != producer:
        raise RunEventError("run event producer differs from state")
    return max(0, int(time.time() * 1000) - state["startedEpochMs"])


def _last_elapsed_ms(output: Path) -> int:
    if not output.is_file() or output.stat().st_size == 0:
        return 0
    lines = output.read_bytes().splitlines()
    if not lines:
        return 0
    try:
        value = json.loads(lines[-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunEventError("existing run event stream ends with an invalid line") from exc
    elapsed = value.get("elapsedMs") if isinstance(value, dict) else None
    return int(_require_non_negative_int(elapsed, "existing elapsedMs"))


def append_event(output: Path, event: dict[str, Any], *, echo: bool = True) -> dict[str, Any]:
    normalized = validate_event(event)
    output.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_lock(output):
        last_elapsed = _last_elapsed_ms(output)
        if normalized["elapsedMs"] < last_elapsed:
            normalized = dict(normalized)
            normalized["elapsedMs"] = last_elapsed
            normalized = validate_event(normalized)
        encoded = (serialize_event(normalized, validate=False) + "\n").encode("utf-8")
        if len(encoded) > MAX_LINE_BYTES + 1:
            raise RunEventError(f"serialized event exceeds {MAX_LINE_BYTES} UTF-8 bytes")
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(output, flags, 0o644)
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise RunEventError("run event append was incomplete")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    if echo:
        print(format_console(normalized), flush=True)
    return normalized


def build_event(
    *,
    output: Path,
    producer: str,
    phase_id: str,
    event_kind: str,
    status: str,
    duration_ms: int | None = None,
    current: int | None = None,
    total: int | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    return validate_event(
        {
            "schemaVersion": SCHEMA_VERSION,
            "timestampUtc": utc_now(),
            "elapsedMs": _elapsed_ms(output, producer),
            "producer": producer,
            "phaseId": phase_id,
            "eventKind": event_kind,
            "status": status,
            "durationMs": duration_ms,
            "current": current,
            "total": total,
            "message": message,
            "failureCode": None,
        }
    )


def initialize_stream(output: Path, producer: str, *, message: str | None = None, echo: bool = True) -> dict[str, Any]:
    if producer not in PRODUCERS:
        raise RunEventError(f"unknown producer: {producer}")
    with _exclusive_lock(output):
        if output.exists() and output.stat().st_size:
            raise RunEventError(f"run event stream already exists: {output}")
        if state_path(output).exists():
            raise RunEventError(f"run event state already exists: {state_path(output)}")
        started_epoch_ms = int(time.time() * 1000)
        _atomic_write(
            state_path(output),
            json.dumps(
                {"schemaVersion": SCHEMA_VERSION, "producer": producer, "startedEpochMs": started_epoch_ms},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n",
        )
    event = build_event(
        output=output,
        producer=producer,
        phase_id="run",
        event_kind="run",
        status="start",
        message=message,
    )
    return append_event(output, event, echo=echo)


def emit(
    output: Path,
    producer: str,
    phase_id: str,
    event_kind: str,
    status: str,
    *,
    duration_ms: int | None = None,
    current: int | None = None,
    total: int | None = None,
    message: str | None = None,
    echo: bool = True,
) -> dict[str, Any]:
    event = build_event(
        output=output,
        producer=producer,
        phase_id=phase_id,
        event_kind=event_kind,
        status=status,
        duration_ms=duration_ms,
        current=current,
        total=total,
        message=message,
    )
    return append_event(output, event, echo=echo)


def finish_run(
    output: Path,
    producer: str,
    status: str,
    *,
    duration_ms: int | None = None,
    message: str | None = None,
    echo: bool = True,
) -> dict[str, Any]:
    if status not in {"pass", "fail", "cancel"}:
        raise RunEventError("run final status must be pass, fail, or cancel")
    if duration_ms is None:
        duration_ms = _elapsed_ms(output, producer)
    event = emit(
        output,
        producer,
        "run",
        "run",
        status,
        duration_ms=duration_ms,
        message=message,
        echo=echo,
    )
    validate_stream(output, expected_producer=producer, require_final=True)
    state_path(output).unlink(missing_ok=True)
    lock_path(output).unlink(missing_ok=True)
    return event


def validate_stream(
    output: Path,
    *,
    expected_producer: str | None = None,
    require_final: bool = True,
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
        except UnicodeDecodeError as exc:
            raise RunEventError(f"run event line {index} is not UTF-8") from exc
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RunEventError(f"run event line {index} is not valid JSON") from exc
        normalized = validate_event(value, expected_producer=expected_producer)
        if serialize_event(normalized, validate=False) != line:
            raise RunEventError(f"run event line {index} is not deterministically serialized")
        events.append(normalized)

    if not events or events[0]["eventKind"] != "run" or events[0]["status"] != "start":
        raise RunEventError("run event stream must begin with run/start")
    producer = expected_producer or events[0]["producer"]
    if any(event["producer"] != producer for event in events):
        raise RunEventError("run event stream mixes producers")
    elapsed = [event["elapsedMs"] for event in events]
    if elapsed != sorted(elapsed):
        raise RunEventError("run event elapsedMs values must be non-decreasing")
    final_events = [event for event in events if event["eventKind"] == "run" and event["status"] in {"pass", "fail", "cancel"}]
    if require_final and (len(final_events) != 1 or events[-1] is not final_events[0]):
        raise RunEventError("finalized stream must end with exactly one run result")
    if not require_final and len(final_events) > 1:
        raise RunEventError("run event stream contains multiple final run results")
    return events


def _main() -> int:
    parser = argparse.ArgumentParser(description="Schema-validated live run event protocol")
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("initialize")
    initialize.add_argument("--output", required=True, type=Path)
    initialize.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    initialize.add_argument("--message")

    emit_parser = commands.add_parser("emit")
    emit_parser.add_argument("--output", required=True, type=Path)
    emit_parser.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    emit_parser.add_argument("--phase-id", required=True)
    emit_parser.add_argument("--event-kind", required=True, choices=sorted(EVENT_KINDS))
    emit_parser.add_argument("--status", required=True, choices=sorted(STATUSES))
    emit_parser.add_argument("--duration-ms", type=int)
    emit_parser.add_argument("--current", type=int)
    emit_parser.add_argument("--total", type=int)
    emit_parser.add_argument("--message")

    finish = commands.add_parser("finish-run")
    finish.add_argument("--output", required=True, type=Path)
    finish.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    finish.add_argument("--status", required=True, choices=("pass", "fail", "cancel"))
    finish.add_argument("--duration-ms", type=int)
    finish.add_argument("--message")

    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--output", required=True, type=Path)
    validate_parser.add_argument("--producer", choices=sorted(PRODUCERS))
    validate_parser.add_argument("--allow-running", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "initialize":
            initialize_stream(args.output, args.producer, message=args.message)
        elif args.command == "emit":
            emit(
                args.output,
                args.producer,
                args.phase_id,
                args.event_kind,
                args.status,
                duration_ms=args.duration_ms,
                current=args.current,
                total=args.total,
                message=args.message,
            )
        elif args.command == "finish-run":
            finish_run(
                args.output,
                args.producer,
                args.status,
                duration_ms=args.duration_ms,
                message=args.message,
            )
        else:
            validate_stream(
                args.output,
                expected_producer=args.producer,
                require_final=not args.allow_running,
            )
        return 0
    except RunEventError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(_main())
