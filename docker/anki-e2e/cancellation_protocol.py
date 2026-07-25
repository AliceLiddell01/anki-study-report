#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterator, Sequence

SCHEMA_VERSION = 1
RESULT = "cancelled"
PRODUCERS = {"docker-e2e", "fast-ci"}
CODES = {"docker-e2e": "ASR-E2E-CANCELLED", "fast-ci": "ASR-FAST-CANCELLED"}
ALLOWED_SIGNALS = {None, "SIGINT", "SIGTERM"}
SIGNAL_EXIT = {"SIGINT": 130, "SIGTERM": 143}
ALLOWED_EXIT_CODES = {130, 143}
ALLOWED_CLEANUP_STATUS = {"success", "failure", "partial"}
ALLOWED_ARTIFACT_STATUS = {"complete", "partial", "unavailable"}
ARTIFACT_POLICY = "best-effort-minimal"
MAX_DOCUMENT_BYTES = 16 * 1024
MAX_PATHS = 16
MAX_PATH_BYTES = 240
ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
TOKEN_RE = re.compile(
    r"(?i)(?:(?:[?&]|\b)(?:access_)?token=|authorization\s*:\s*bearer|"
    r"github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|sk-[a-z0-9_-]{20,})"
)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class CancellationProtocolError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _non_negative(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CancellationProtocolError(f"{label} must be a non-negative integer")
    return value


def _optional_id(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise CancellationProtocolError(f"{label} has an invalid format")
    return value


def _safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CancellationProtocolError("evidence path must be a non-empty trimmed string")
    if len(value.encode("utf-8")) > MAX_PATH_BYTES or CONTROL_RE.search(value) or TOKEN_RE.search(value):
        raise CancellationProtocolError("evidence path is unsafe")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or "." in path.parts or ":" in path.parts[0]:
        raise CancellationProtocolError("evidence path must be a safe relative path")
    return path.as_posix()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if not lock_path.exists():
        lock_path.write_bytes(b"0")
    with lock_path.open("r+b") as handle:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    import time
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
    lock_path.unlink(missing_ok=True)


def validate_document(document: dict[str, Any]) -> dict[str, Any]:
    expected_fields = (
        "schemaVersion",
        "result",
        "producer",
        "cancellationCode",
        "observedAtUtc",
        "elapsedMs",
        "originalExitCode",
        "originalSignal",
        "context",
        "cleanup",
        "artifact",
        "evidencePaths",
    )
    if not isinstance(document, dict) or tuple(document) != expected_fields:
        raise CancellationProtocolError("cancellation summary differs from the supported field order")
    if document["schemaVersion"] != SCHEMA_VERSION:
        raise CancellationProtocolError("unsupported cancellation schemaVersion")
    producer = document["producer"]
    if document["result"] != RESULT or producer not in PRODUCERS or document["cancellationCode"] != CODES[producer]:
        raise CancellationProtocolError("cancellation summary identity is invalid")
    observed = document["observedAtUtc"]
    if not isinstance(observed, str) or not UTC_RE.fullmatch(observed):
        raise CancellationProtocolError("observedAtUtc must use UTC millisecond precision")
    elapsed = _non_negative(document["elapsedMs"], "elapsedMs")
    exit_code = document["originalExitCode"]
    signal = document["originalSignal"]
    if exit_code not in ALLOWED_EXIT_CODES:
        raise CancellationProtocolError("originalExitCode must be 130 or 143")
    if signal not in ALLOWED_SIGNALS:
        raise CancellationProtocolError("originalSignal must be SIGINT, SIGTERM, or null")
    if signal is not None and SIGNAL_EXIT[signal] != exit_code:
        raise CancellationProtocolError("original signal and exit code differ")

    context = document["context"]
    context_fields = (
        "lastSuccessfulPhaseId",
        "lastSuccessfulItemId",
        "activePhaseId",
        "activeItemId",
    )
    if not isinstance(context, dict) or tuple(context) != context_fields:
        raise CancellationProtocolError("cancellation context differs from the supported field order")
    normalized_context = {
        "lastSuccessfulPhaseId": _optional_id(context["lastSuccessfulPhaseId"], "lastSuccessfulPhaseId"),
        "lastSuccessfulItemId": _optional_id(context["lastSuccessfulItemId"], "lastSuccessfulItemId"),
        "activePhaseId": _optional_id(context["activePhaseId"], "activePhaseId"),
        "activeItemId": _optional_id(context["activeItemId"], "activeItemId"),
    }

    cleanup = document["cleanup"]
    if not isinstance(cleanup, dict) or tuple(cleanup) != ("status", "durationMs", "attempts"):
        raise CancellationProtocolError("cleanup differs from the supported field order")
    if cleanup["status"] not in ALLOWED_CLEANUP_STATUS:
        raise CancellationProtocolError("cleanup status is unsupported")
    normalized_cleanup = {
        "status": cleanup["status"],
        "durationMs": _non_negative(cleanup["durationMs"], "cleanup durationMs"),
        "attempts": _non_negative(cleanup["attempts"], "cleanup attempts"),
    }
    if normalized_cleanup["attempts"] < 1:
        raise CancellationProtocolError("cleanup attempts must be at least one")

    artifact = document["artifact"]
    if not isinstance(artifact, dict) or tuple(artifact) != ("policy", "status"):
        raise CancellationProtocolError("artifact differs from the supported field order")
    if artifact["policy"] != ARTIFACT_POLICY or artifact["status"] not in ALLOWED_ARTIFACT_STATUS:
        raise CancellationProtocolError("cancelled artifact policy is invalid")

    paths = document["evidencePaths"]
    if not isinstance(paths, list) or len(paths) > MAX_PATHS:
        raise CancellationProtocolError("evidencePaths must be a bounded list")
    normalized_paths: list[str] = []
    for item in paths:
        path = _safe_path(item)
        if path in normalized_paths:
            raise CancellationProtocolError("evidencePaths must not contain duplicates")
        normalized_paths.append(path)

    normalized = {
        "schemaVersion": SCHEMA_VERSION,
        "result": RESULT,
        "producer": producer,
        "cancellationCode": CODES.get(producer),
        "observedAtUtc": observed,
        "elapsedMs": elapsed,
        "originalExitCode": exit_code,
        "originalSignal": signal,
        "context": normalized_context,
        "cleanup": normalized_cleanup,
        "artifact": {
            "policy": ARTIFACT_POLICY,
            "status": artifact["status"],
        },
        "evidencePaths": normalized_paths,
    }
    serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(serialized.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise CancellationProtocolError("cancellation summary exceeds the bounded document size")
    return normalized


def serialize_document(document: dict[str, Any]) -> str:
    return json.dumps(validate_document(document), ensure_ascii=False, separators=(",", ":")) + "\n"


def load_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or not raw.endswith(b"\n"):
        raise CancellationProtocolError("cancellation summary must be UTF-8 without BOM and newline-terminated")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CancellationProtocolError("cancellation summary is not valid UTF-8 JSON") from exc
    normalized = validate_document(value)
    if serialize_document(normalized).encode("utf-8") != raw:
        raise CancellationProtocolError("cancellation summary is not deterministically serialized")
    return normalized


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def discover_context(run_events: Path | None, browser_report: Path | None) -> dict[str, str | None]:
    last_successful_phase: str | None = None
    active_phase: str | None = None
    if run_events and run_events.is_file():
        try:
            lines = run_events.read_text(encoding="utf-8").splitlines()
            for line in lines:
                event = json.loads(line)
                if not isinstance(event, dict):
                    continue
                phase_id = event.get("phaseId")
                kind = event.get("eventKind")
                status = event.get("status")
                if kind == "phase" and isinstance(phase_id, str):
                    if status == "start":
                        active_phase = phase_id
                    elif status == "pass":
                        last_successful_phase = phase_id
                        if active_phase == phase_id:
                            active_phase = None
                    elif status in {"fail", "cancel", "skip"} and active_phase == phase_id:
                        active_phase = None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass

    last_item: str | None = None
    active_item: str | None = None
    if browser_report:
        report = _read_json(browser_report)
        if report:
            progress = report.get("progress")
            if isinstance(progress, dict):
                active_value = progress.get("activeItemId")
                if isinstance(active_value, str) and ID_RE.fullmatch(active_value):
                    active_item = active_value
            items = report.get("items")
            if isinstance(items, list):
                passed = [
                    item for item in items
                    if isinstance(item, dict)
                    and item.get("status") == "PASS"
                    and isinstance(item.get("id"), str)
                    and ID_RE.fullmatch(item["id"])
                ]
                if passed:
                    passed.sort(key=lambda item: int(item.get("order", 0)))
                    last_item = passed[-1]["id"]
    return {
        "lastSuccessfulPhaseId": last_successful_phase,
        "lastSuccessfulItemId": last_item,
        "activePhaseId": active_phase,
        "activeItemId": active_item,
    }


def build_document(
    *,
    producer: str = "docker-e2e",
    elapsed_ms: int,
    original_exit_code: int,
    original_signal: str | None,
    cleanup_status: str,
    cleanup_duration_ms: int,
    cleanup_attempts: int,
    artifact_status: str,
    context: dict[str, str | None] | None = None,
    evidence_paths: Sequence[str] = (),
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    value = {
        "schemaVersion": SCHEMA_VERSION,
        "result": RESULT,
        "producer": producer,
        "cancellationCode": CODES.get(producer),
        "observedAtUtc": observed_at_utc or utc_now(),
        "elapsedMs": elapsed_ms,
        "originalExitCode": original_exit_code,
        "originalSignal": original_signal,
        "context": context or {
            "lastSuccessfulPhaseId": None,
            "lastSuccessfulItemId": None,
            "activePhaseId": None,
            "activeItemId": None,
        },
        "cleanup": {
            "status": cleanup_status,
            "durationMs": cleanup_duration_ms,
            "attempts": cleanup_attempts,
        },
        "artifact": {
            "policy": ARTIFACT_POLICY,
            "status": artifact_status,
        },
        "evidencePaths": list(evidence_paths),
    }
    return validate_document(value)


def write_document(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_document(document)
    with _lock(path):
        if path.is_file():
            existing = load_document(path)
            if existing != normalized:
                raise CancellationProtocolError("cancellation summary is immutable once written")
            return existing
        failure_path = path.with_name("failure-summary.json")
        if failure_path.exists():
            raise CancellationProtocolError("cancellation summary cannot coexist with failure-summary.json")
        _atomic_write(path, serialize_document(normalized))
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical Docker E2E cancellation summary protocol")
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--output", type=Path, required=True)
    record.add_argument("--producer", choices=sorted(PRODUCERS), default="docker-e2e")
    record.add_argument("--elapsed-ms", type=int, required=True)
    record.add_argument("--original-exit-code", type=int, choices=sorted(ALLOWED_EXIT_CODES), required=True)
    record.add_argument("--original-signal", choices=("SIGINT", "SIGTERM"))
    record.add_argument("--cleanup-status", choices=sorted(ALLOWED_CLEANUP_STATUS), required=True)
    record.add_argument("--cleanup-duration-ms", type=int, required=True)
    record.add_argument("--cleanup-attempts", type=int, default=1)
    record.add_argument("--artifact-status", choices=sorted(ALLOWED_ARTIFACT_STATUS), required=True)
    record.add_argument("--run-events", type=Path)
    record.add_argument("--browser-report", type=Path)
    record.add_argument("--evidence-path", action="append", default=[])
    validate = subparsers.add_parser("validate")
    validate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            document = load_document(args.output)
        else:
            context = discover_context(args.run_events, args.browser_report)
            document = build_document(
                producer=args.producer,
                elapsed_ms=args.elapsed_ms,
                original_exit_code=args.original_exit_code,
                original_signal=args.original_signal,
                cleanup_status=args.cleanup_status,
                cleanup_duration_ms=args.cleanup_duration_ms,
                cleanup_attempts=args.cleanup_attempts,
                artifact_status=args.artifact_status,
                context=context,
                evidence_paths=args.evidence_path,
            )
            write_document(args.output, document)
        print(
            f"[CANCEL] exit={document['originalExitCode']} signal={document['originalSignal'] or 'unknown'} "
            f"cleanup={document['cleanup']['status']} artifact={document['artifact']['status']}",
            flush=True,
        )
        return 0
    except (CancellationProtocolError, OSError) as exc:
        parser.exit(2, f"cancellation protocol error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
