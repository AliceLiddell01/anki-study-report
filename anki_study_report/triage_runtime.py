"""Serialized QueryOp bridge for the canonical triage read API."""

from __future__ import annotations

from collections.abc import Callable
import threading
import traceback
from typing import Any

from .extension_logging import log_event
from .card_display_formatter_service import CardDisplayFormatterResolver
from .triage_service import (
    TriageValidationError,
    build_unavailable_triage_projection,
    execute_triage_query,
    normalize_triage_query_request,
)


TRIAGE_TIMEOUT_SECONDS = 20.0


def run_triage_query_sync(
    mw: Any,
    payload: object,
    *,
    signal_provider: Callable[[], list[dict[str, Any]]] | None = None,
    profile_store_provider: Callable[[], dict[str, Any]] | None = None,
    formatter_store_provider: Callable[[], dict[str, Any]] | None = None,
    timeout_seconds: float = TRIAGE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        normalize_triage_query_request(payload)
    except TriageValidationError as error:
        return _error("invalid_triage_request", "Check the triage request parameters.", fieldErrors=error.field_errors)

    signal_rows, signal_status = _read_signals(signal_provider)
    profile_snapshot = _read_profile_store(profile_store_provider)
    formatter_resolver = _read_formatter_resolver(formatter_store_provider)
    if mw is None or getattr(mw, "col", None) is None or not hasattr(mw, "taskman"):
        return {
            "ok": True,
            "response": build_unavailable_triage_projection(
                payload,
                signal_rows=signal_rows,
                signal_source_status=signal_status,
                profile_store_snapshot=profile_snapshot,
            ),
        }

    event = threading.Event()
    holder: dict[str, Any] = {}

    def success(value: object) -> None:
        holder["response"] = {"ok": True, "response": value}
        event.set()

    def failure(error: Exception) -> None:
        if isinstance(error, TriageValidationError):
            holder["response"] = _error(
                "invalid_triage_request",
                "Check the triage request parameters.",
                fieldErrors=error.field_errors,
            )
        else:
            _log_safe_failure(error)
            holder["response"] = _error("triage_failed", "The triage request failed.")
        event.set()

    def start() -> None:
        try:
            operation = _query_op_type()(
                parent=mw,
                op=lambda col: execute_triage_query(
                    col,
                    payload,
                    signal_rows=signal_rows,
                    signal_source_status=signal_status,
                    profile_store_snapshot=profile_snapshot,
                    formatter_resolver=formatter_resolver,
                ),
                success=success,
            )
            operation.failure(failure).run_in_background()
        except Exception as error:
            failure(error)

    try:
        mw.taskman.run_on_main(start)
    except Exception:
        return _error("triage_unavailable", "Could not schedule the triage request.")

    if not event.wait(max(0.001, float(timeout_seconds))):
        return _error("triage_timeout", "The triage request did not finish in time.")
    response = holder.get("response")
    return response if isinstance(response, dict) else _error("triage_failed", "The triage request failed.")


def _read_signals(
    provider: Callable[[], list[dict[str, Any]]] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if provider is None:
        return [], {"status": "unavailable", "errorCode": "signal_store_unavailable"}
    try:
        value = provider()
        if not isinstance(value, list):
            raise TypeError("signal provider did not return a list")
        return value, {"status": "available" if value else "empty", "errorCode": None}
    except Exception as error:
        _log_safe_signal_failure(error)
        return [], {"status": "error", "errorCode": "signal_store_failed"}


def _read_profile_store(
    provider: Callable[[], dict[str, Any]] | None,
) -> dict[str, Any]:
    if provider is None:
        return {
            "status": "unavailable",
            "revision": 0,
            "profiles": [],
            "errorCode": "profile_store_unavailable",
        }
    try:
        value = provider()
        if not isinstance(value, dict):
            raise TypeError("profile store provider did not return an object")
        return value
    except Exception as error:
        log_event(
            "triage.profiles.error",
            "Inspection Profile source failed",
            exception_type=type(error).__name__,
        )
        return {
            "status": "unavailable",
            "revision": 0,
            "profiles": [],
            "errorCode": "profile_store_unavailable",
        }


def _read_formatter_resolver(
    provider: Callable[[], dict[str, Any]] | None,
) -> CardDisplayFormatterResolver:
    if provider is None:
        return CardDisplayFormatterResolver.from_snapshot({"status": "empty", "formatters": []})
    try:
        value = provider()
        if not isinstance(value, dict):
            raise TypeError("formatter store provider did not return an object")
        return CardDisplayFormatterResolver.from_snapshot(value)
    except Exception as error:
        log_event(
            "triage.formatters.error",
            "Card display formatter source failed",
            exception_type=type(error).__name__,
        )
        return CardDisplayFormatterResolver.from_snapshot(
            {"status": "unavailable", "formatters": []}
        )


def _query_op_type() -> Any:
    from aqt.operations import QueryOp

    return QueryOp


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message, **extra}


def _log_safe_failure(error: Exception) -> None:
    frames = traceback.extract_tb(error.__traceback__)[-12:]
    log_event(
        "triage.query.error",
        "Triage background operation failed",
        exception_type=type(error).__name__,
        stack=[f"{frame.name}:{frame.lineno}" for frame in frames],
    )


def _log_safe_signal_failure(error: Exception) -> None:
    log_event(
        "triage.signals.error",
        "Triage Signal source failed",
        exception_type=type(error).__name__,
    )
