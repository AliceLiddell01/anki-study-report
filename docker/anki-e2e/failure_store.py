from __future__ import annotations

from contextlib import contextmanager
import json
import os
import re
from pathlib import Path
import tempfile
import time
from typing import Any, Iterator, Mapping, Sequence

from failure_registry import *  # noqa: F401,F403
from failure_schema import *  # noqa: F401,F403
from failure_schema import _optional_non_negative_int, _validate_failure
def _sidecar_directory(output: Path) -> Path:
    return output.parent.parent / "runtime" if output.parent.name == "reports" else output.parent


def lock_path(output: Path) -> Path:
    return _sidecar_directory(output) / (output.name + ".lock")


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


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def load_document(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise FailureProtocolError(f"failure summary does not exist: {path}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise FailureProtocolError("failure summary must be UTF-8 without BOM")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FailureProtocolError("failure summary is not valid UTF-8 JSON") from exc
    normalized = validate_document(value)
    if serialize_document(normalized) != raw.decode("utf-8"):
        raise FailureProtocolError("failure summary is not deterministically serialized")
    return normalized


def build_failure(
    *,
    code: str,
    phase_id: str | None = None,
    item_id: str | None = None,
    item_kind: str | None = None,
    error_type: str | None = None,
    summary: str | None = None,
    occurred_at_utc: str | None = None,
    elapsed_ms: int | None = None,
    original_exit_code: int | None = None,
    original_signal: str | None = None,
    evidence_paths: Sequence[str] = (),
    raw_diagnostic_paths: Sequence[str] = (),
) -> dict[str, Any]:
    meta = definition(code)
    safe_summary = sanitize_summary(summary, meta.default_summary)
    safe_error_type = re.sub(r"[^A-Za-z0-9_.-]", "", str(error_type or "Error"))[:MAX_ERROR_TYPE_BYTES] or "Error"
    entry = {
        "failureCode": code,
        "category": meta.category,
        "domain": meta.domain,
        "phaseId": phase_id,
        "itemId": item_id,
        "itemKind": item_kind,
        "errorType": safe_error_type,
        "summary": safe_summary,
        "occurredAtUtc": occurred_at_utc or utc_now(),
        "elapsedMs": elapsed_ms,
        "originalExitCode": original_exit_code,
        "originalSignal": original_signal,
        "exitClass": exit_class_for(code, original_exit_code, original_signal),
        "evidencePaths": list(evidence_paths),
        "rawDiagnosticPaths": list(raw_diagnostic_paths),
    }
    producer = "fast-ci" if meta.domain == "fast" else "docker-e2e"
    return _validate_failure(entry, producer=producer, secondary=False)


def _initial_document(producer: str, primary: dict[str, Any], *, last_successful_phase_id: str | None, last_successful_item_id: str | None, active_phase_id: str | None, active_item_id: str | None) -> dict[str, Any]:
    return validate_document({
        "schemaVersion": SCHEMA_VERSION,
        "result": "failure",
        "producer": producer,
        "primary": primary,
        "secondary": [],
        "context": {
            "lastSuccessfulPhaseId": last_successful_phase_id,
            "lastSuccessfulItemId": last_successful_item_id,
            "activePhaseId": active_phase_id,
            "activeItemId": active_item_id,
        },
        "cleanup": {"status": "not_started", "failureCount": 0},
    })


def record_failure(
    output: Path,
    producer: str,
    failure: dict[str, Any],
    *,
    primary: bool,
    last_successful_phase_id: str | None = None,
    last_successful_item_id: str | None = None,
    active_phase_id: str | None = None,
    active_item_id: str | None = None,
) -> dict[str, Any]:
    with _exclusive_lock(output):
        if output.is_file():
            document = load_document(output)
            if document["producer"] != producer:
                raise FailureProtocolError("failure summary producer mismatch")
            if primary:
                return document
            candidate = _validate_failure(failure, producer=producer, secondary=True)
            if failure_identity(candidate) not in {failure_identity(item) for item in document["secondary"]} and len(document["secondary"]) < MAX_SECONDARY:
                document["secondary"].append(candidate)
            if active_phase_id is not None:
                document["context"]["activePhaseId"] = active_phase_id
            if active_item_id is not None:
                document["context"]["activeItemId"] = active_item_id
            document["cleanup"]["failureCount"] = sum(
                1 for item in document["secondary"] if item["category"] == "cleanup"
            )
            document = validate_document(document)
        else:
            candidate = _validate_failure(failure, producer=producer, secondary=False)
            document = _initial_document(
                producer,
                candidate,
                last_successful_phase_id=last_successful_phase_id,
                last_successful_item_id=last_successful_item_id,
                active_phase_id=active_phase_id or candidate["phaseId"],
                active_item_id=active_item_id or candidate["itemId"],
            )
        atomic_write(output, serialize_document(document))
        return document


def set_cleanup_status(output: Path, status: str) -> dict[str, Any]:
    if status not in {"not_started", "success", "failure", "partial"}:
        raise FailureProtocolError("invalid cleanup status")
    with _exclusive_lock(output):
        document = load_document(output)
        document["cleanup"] = {
            "status": status,
            "failureCount": sum(1 for item in document["secondary"] if item["category"] == "cleanup"),
        }
        document = validate_document(document)
        atomic_write(output, serialize_document(document))
        return document


def update_context(output: Path, *, last_successful_phase_id: str | None = None, last_successful_item_id: str | None = None, active_phase_id: str | None = None, active_item_id: str | None = None) -> dict[str, Any]:
    with _exclusive_lock(output):
        document = load_document(output)
        updates = {
            "lastSuccessfulPhaseId": last_successful_phase_id,
            "lastSuccessfulItemId": last_successful_item_id,
            "activePhaseId": active_phase_id,
            "activeItemId": active_item_id,
        }
        for key, value in updates.items():
            if value is not None:
                document["context"][key] = value
        document = validate_document(document)
        atomic_write(output, serialize_document(document))
        return document


def browser_failure_from_report(report: Path, *, original_exit_code: int | None = 1) -> tuple[dict[str, Any], str | None]:
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FailureProtocolError(f"browser report is unavailable or invalid: {report}") from exc
    if not isinstance(payload, dict):
        raise FailureProtocolError("browser report must be a JSON object")
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    failed_id = progress.get("failedItemId")
    failed = next((item for item in items if isinstance(item, dict) and item.get("id") == failed_id), None)
    if failed is None:
        raise FailureProtocolError("browser report does not identify a failed item")
    item_kind = str(failed.get("kind") or "") or None
    code = code_for_phase("docker-e2e", "browser-smoke-first", item_kind=item_kind)
    passed = [item for item in items if isinstance(item, dict) and item.get("status") == "pass"]
    last_item = passed[-1].get("id") if passed else None
    failure = build_failure(
        code=code,
        phase_id="browser-smoke-first",
        item_id=str(failed.get("id") or "") or None,
        item_kind=item_kind,
        error_type=str(failed.get("errorType") or "Error"),
        summary=str(failed.get("safeErrorSummary") or payload.get("error") or definition(code).default_summary),
        elapsed_ms=_optional_non_negative_int(failed.get("lifecycleDurationMs") or failed.get("operationDurationMs") or failed.get("durationMs"), "browser failure elapsed"),
        original_exit_code=original_exit_code,
        evidence_paths=[report.as_posix()] if not report.is_absolute() else ["reports/" + report.name],
        raw_diagnostic_paths=["diagnostics/anki.log"],
    )
    return failure, str(last_item) if last_item else None
