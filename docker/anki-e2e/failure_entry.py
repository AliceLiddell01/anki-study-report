from __future__ import annotations

from typing import Any

from failure_registry import (
    ALLOWED_EXIT_CLASSES,
    ALLOWED_SIGNALS,
    ALL_PHASES,
    CODE_RE,
    ERROR_TYPE_RE,
    MAX_ERROR_TYPE_BYTES,
    MAX_SUMMARY_BYTES,
    FailureProtocolError,
    definition,
    exit_class_for,
)
from failure_safety import optional_non_negative_int, paths, safe_id, safe_single_line, validate_timestamp

FAILURE_FIELDS = (
    "failureCode",
    "category",
    "domain",
    "phaseId",
    "itemId",
    "itemKind",
    "errorType",
    "summary",
    "occurredAtUtc",
    "elapsedMs",
    "originalExitCode",
    "originalSignal",
    "exitClass",
    "evidencePaths",
    "rawDiagnosticPaths",
)


def validate_failure(value: Any, *, producer: str, secondary: bool) -> dict[str, Any]:
    if not isinstance(value, dict) or tuple(value) != FAILURE_FIELDS:
        raise FailureProtocolError("failure entry differs from schema v1 field order")
    code = safe_single_line(value["failureCode"], "failureCode", max_bytes=80, pattern=CODE_RE)
    assert code is not None
    meta = definition(code)
    expected_domain = "fast" if producer == "fast-ci" else "e2e"
    if meta.domain != expected_domain:
        raise FailureProtocolError("failure code domain differs from producer")
    if value["category"] != meta.category or value["domain"] != meta.domain:
        raise FailureProtocolError("failure metadata differs from registry")
    if secondary and not meta.can_be_secondary:
        raise FailureProtocolError("failure code cannot be secondary")
    phase_id = safe_id(value["phaseId"], "phaseId")
    if phase_id is not None:
        if phase_id not in ALL_PHASES:
            raise FailureProtocolError(f"unknown phaseId: {phase_id}")
        if meta.allowed_phases and phase_id not in meta.allowed_phases:
            raise FailureProtocolError(f"failure code {code} is not allowed for phase {phase_id}")
    item_id = safe_id(value["itemId"], "itemId")
    item_kind = safe_id(value["itemKind"], "itemKind")
    error_type = safe_single_line(
        value["errorType"],
        "errorType",
        max_bytes=MAX_ERROR_TYPE_BYTES,
        fallback="Error",
        pattern=ERROR_TYPE_RE,
    )
    summary = safe_single_line(value["summary"], "summary", max_bytes=MAX_SUMMARY_BYTES, fallback=meta.default_summary)
    timestamp = validate_timestamp(value["occurredAtUtc"])
    elapsed_ms = optional_non_negative_int(value["elapsedMs"], "elapsedMs")
    original_exit = optional_non_negative_int(value["originalExitCode"], "originalExitCode")
    signal = value["originalSignal"]
    if signal not in ALLOWED_SIGNALS:
        raise FailureProtocolError("originalSignal is not allowlisted")
    exit_class = value["exitClass"]
    if isinstance(exit_class, bool) or not isinstance(exit_class, int) or exit_class not in ALLOWED_EXIT_CLASSES:
        raise FailureProtocolError("exitClass is invalid")
    if exit_class != exit_class_for(code, original_exit, signal):
        raise FailureProtocolError("exitClass differs from registry/signal mapping")
    return {
        "failureCode": code,
        "category": meta.category,
        "domain": meta.domain,
        "phaseId": phase_id,
        "itemId": item_id,
        "itemKind": item_kind,
        "errorType": error_type,
        "summary": summary,
        "occurredAtUtc": timestamp,
        "elapsedMs": elapsed_ms,
        "originalExitCode": original_exit,
        "originalSignal": signal,
        "exitClass": exit_class,
        "evidencePaths": paths(value["evidencePaths"], "evidencePaths"),
        "rawDiagnosticPaths": paths(value["rawDiagnosticPaths"], "rawDiagnosticPaths"),
    }
