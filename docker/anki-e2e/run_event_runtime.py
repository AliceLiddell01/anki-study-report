from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any

from run_event_contract import *
from run_event_failure import (
    create_run_level_summary,
    ensure_failure_summary,
    resolve_failure_code,
    summary_primary_code,
)
from run_event_storage import *
from run_event_storage import _atomic_write, _elapsed_ms, _exclusive_lock, _load_state
from run_event_validate import validate_stream


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
    failure_code: str | None = None,
) -> dict[str, Any]:
    state = _load_state(output)
    schema_version = int(state["schemaVersion"])
    resolved_code = (
        resolve_failure_code(output, producer, phase_id, status, failure_code)
        if schema_version == SCHEMA_VERSION
        else None
    )
    return validate_event({
        "schemaVersion": schema_version,
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
        "failureCode": resolved_code,
    })


def initialize_stream(
    output: Path,
    producer: str,
    *,
    message: str | None = None,
    echo: bool = True,
    schema_version: int = SCHEMA_VERSION,
) -> dict[str, Any]:
    if producer not in PRODUCERS:
        raise RunEventError(f"unknown producer: {producer}")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise RunEventError("unsupported run event schemaVersion")
    with _exclusive_lock(output):
        if output.exists() and output.stat().st_size:
            raise RunEventError(f"run event stream already exists: {output}")
        if state_path(output).exists():
            raise RunEventError(f"run event state already exists: {state_path(output)}")
        _atomic_write(
            state_path(output),
            json.dumps(
                {
                    "schemaVersion": schema_version,
                    "producer": producer,
                    "startedEpochMs": int(time.time() * 1000),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ) + "\n",
        )
    event = build_event(
        output=output, producer=producer, phase_id="run", event_kind="run", status="start", message=message
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
    failure_code: str | None = None,
    original_exit_code: int | None = None,
    original_signal: str | None = None,
    echo: bool = True,
) -> dict[str, Any]:
    event = build_event(
        output=output, producer=producer, phase_id=phase_id, event_kind=event_kind, status=status,
        duration_ms=duration_ms, current=current, total=total, message=message, failure_code=failure_code,
    )
    if event["schemaVersion"] == SCHEMA_VERSION and event["failureCode"] and phase_id != "run":
        ensure_failure_summary(
            output, producer, phase_id, event["failureCode"], message=message,
            original_exit_code=original_exit_code, original_signal=original_signal,
        )
    return append_event(output, event, echo=echo)


def finish_run(
    output: Path,
    producer: str,
    status: str,
    *,
    duration_ms: int | None = None,
    message: str | None = None,
    failure_code: str | None = None,
    original_exit_code: int | None = None,
    original_signal: str | None = None,
    echo: bool = True,
) -> dict[str, Any]:
    if status not in {"pass", "fail", "cancel"}:
        raise RunEventError("run final status must be pass, fail, or cancel")
    summary_file = failure_summary_path(output)
    if status == "pass" and summary_file.is_file():
        status = "fail"
    if duration_ms is None:
        duration_ms = _elapsed_ms(output, producer)
    create_run_level_summary(
        output, producer, status, duration_ms=duration_ms, message=message, failure_code=failure_code,
        original_exit_code=original_exit_code, original_signal=original_signal,
    )
    if summary_file.is_file():
        current_summary = failure_protocol.load_document(summary_file)
        if current_summary["cleanup"]["status"] == "not_started":
            failure_protocol.set_cleanup_status(summary_file, "success")
    event = emit(
        output, producer, "run", "run", status, duration_ms=duration_ms, message=message,
        failure_code=failure_code, original_exit_code=original_exit_code, original_signal=original_signal, echo=echo,
    )
    validate_stream(output, expected_producer=producer, require_final=True)
    if status in {"fail", "cancel"} and summary_file.is_file():
        document = failure_protocol.load_document(summary_file)
        emit_github = producer == "fast-ci" or os.environ.get("ASR_EMIT_GITHUB_ANNOTATION") == "1"
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY") if emit_github else None
        if summary_path:
            with Path(summary_path).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n" + failure_protocol.render_markdown(document))
        if emit_github:
            print(failure_protocol.annotation(document), flush=True)
    state_path(output).unlink(missing_ok=True)
    lock_path(output).unlink(missing_ok=True)
    return event
