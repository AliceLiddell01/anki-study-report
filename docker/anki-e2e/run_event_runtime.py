from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any

import cancellation_protocol
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
        if failure_summary_path(output).exists() or cancellation_summary_path(output).exists():
            raise RunEventError("run event evidence from an earlier lifecycle already exists")
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
    if (
        event["schemaVersion"] == SCHEMA_VERSION
        and event["failureCode"]
        and phase_id != "run"
        and status == "fail"
    ):
        ensure_failure_summary(
            output, producer, phase_id, event["failureCode"], message=message,
            original_exit_code=original_exit_code, original_signal=original_signal,
        )
    return append_event(output, event, echo=echo)


def _ensure_cancellation_summary(
    output: Path,
    producer: str,
    duration_ms: int,
    original_exit_code: int | None,
    original_signal: str | None,
) -> None:
    if failure_summary_path(output).exists():
        raise RunEventError("cancelled run must not contain failure-summary.json")
    summary_path = cancellation_summary_path(output)
    if summary_path.exists():
        document = cancellation_protocol.load_document(summary_path)
        expected_code = cancellation_protocol.CODES[producer]
        if document["producer"] != producer or document["cancellationCode"] != expected_code:
            raise RunEventError("cancellation summary producer differs from the run")
        if original_exit_code is not None and document["originalExitCode"] != original_exit_code:
            raise RunEventError("cancellation summary exit code differs from run/cancel")
        if original_signal is not None and document["originalSignal"] != original_signal:
            raise RunEventError("cancellation summary signal differs from run/cancel")
        return
    if original_exit_code not in cancellation_protocol.ALLOWED_EXIT_CODES:
        raise RunEventError("cancelled run requires original exit 130 or 143")
    context = cancellation_protocol.discover_context(
        output,
        output.parent / "browser-smoke-first.json",
    )
    evidence = [
        output.relative_to(output.parent.parent).as_posix()
        if output.parent.name == "reports"
        else output.name
    ]
    document = cancellation_protocol.build_document(
        producer=producer,
        elapsed_ms=duration_ms,
        original_exit_code=original_exit_code,
        original_signal=original_signal,
        cleanup_status="partial",
        cleanup_duration_ms=0,
        cleanup_attempts=1,
        artifact_status="unavailable",
        context=context,
        evidence_paths=evidence,
    )
    cancellation_protocol.write_document(summary_path, document)


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
    failure_file = failure_summary_path(output)
    cancellation_file = cancellation_summary_path(output)
    if status == "pass" and failure_file.is_file():
        status = "fail"
    if status == "pass" and cancellation_file.is_file():
        raise RunEventError("successful run must not contain cancellation-summary.json")
    if status == "fail" and cancellation_file.is_file():
        raise RunEventError("failed run must not contain cancellation-summary.json")
    if duration_ms is None:
        duration_ms = _elapsed_ms(output, producer)
    if status == "cancel":
        _ensure_cancellation_summary(
            output,
            producer,
            duration_ms,
            original_exit_code,
            original_signal,
        )
    else:
        create_run_level_summary(
            output, producer, status, duration_ms=duration_ms, message=message, failure_code=failure_code,
            original_exit_code=original_exit_code, original_signal=original_signal,
        )
    if failure_file.is_file():
        current_summary = failure_protocol.load_document(failure_file)
        if current_summary["cleanup"]["status"] == "not_started":
            failure_protocol.set_cleanup_status(failure_file, "success")
    event = emit(
        output, producer, "run", "run", status, duration_ms=duration_ms, message=message,
        failure_code=failure_code, original_exit_code=original_exit_code, original_signal=original_signal, echo=echo,
    )
    validate_stream(output, expected_producer=producer, require_final=True)
    if status == "fail" and failure_file.is_file():
        document = failure_protocol.load_document(failure_file)
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

def cancel_run(
    output: Path,
    producer: str,
    *,
    original_exit_code: int,
    original_signal: str | None = None,
    duration_ms: int | None = None,
    echo: bool = True,
) -> dict[str, Any]:
    events = validate_stream(output, expected_producer=producer, require_final=False)
    terminal = [
        event for event in events
        if event["eventKind"] == "run" and event["status"] in {"pass", "fail", "cancel"}
    ]
    if terminal:
        if terminal[0]["status"] != "cancel":
            raise RunEventError("cannot convert an already finalized run into cancellation")
        return terminal[0]
    if duration_ms is None:
        duration_ms = _elapsed_ms(output, producer)
    active_phase: dict[str, Any] | None = None
    for event in events:
        if event["eventKind"] != "phase":
            continue
        if event["status"] == "start":
            active_phase = event
        elif active_phase and event["phaseId"] == active_phase["phaseId"] and event["status"] in {
            "pass", "fail", "skip", "cancel"
        }:
            active_phase = None
    _ensure_cancellation_summary(
        output,
        producer,
        duration_ms,
        original_exit_code,
        original_signal,
    )
    signal_text = original_signal or "unknown"
    message = f"exit={original_exit_code} signal={signal_text}"
    if active_phase is not None:
        phase_duration = max(0, duration_ms - int(active_phase["elapsedMs"]))
        emit(
            output,
            producer,
            active_phase["phaseId"],
            "phase",
            "cancel",
            duration_ms=phase_duration,
            message=message,
            original_exit_code=original_exit_code,
            original_signal=original_signal,
            echo=echo,
        )
    return finish_run(
        output,
        producer,
        "cancel",
        duration_ms=duration_ms,
        message=message,
        original_exit_code=original_exit_code,
        original_signal=original_signal,
        echo=echo,
    )

