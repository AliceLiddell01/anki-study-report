"""Thread-safe bridge between local HTTP requests and Anki QueryOp work."""

from __future__ import annotations

from collections.abc import Callable
import threading
import traceback
from typing import Any

from .search_metadata import execute_search_request, normalize_search_request
from .search_service import (
    SearchEntityNotFoundError,
    SearchValidationError,
    execute_search_inspect,
    normalize_search_inspect_request,
)
from .extension_logging import log_event
from .card_display_formatter_service import CardDisplayFormatterResolver


SEARCH_TIMEOUT_SECONDS = 20.0
_GATE_CREATION_LOCK = threading.Lock()


class _SearchQueryGate:
    """Allow at most one non-cancellable broad native search per Anki session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = False

    def try_start(self) -> bool:
        with self._lock:
            if self._active:
                return False
            self._active = True
            return True

    def finish(self) -> None:
        with self._lock:
            self._active = False


def run_search_query_sync(
    mw: Any,
    payload: object,
    *,
    formatter_store_provider: Callable[[], dict[str, Any]] | None = None,
    timeout_seconds: float = SEARCH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return _run_search_sync(
        mw,
        payload,
        validator=normalize_search_request,
        executor=execute_search_request,
        formatter_store_provider=formatter_store_provider,
        timeout_seconds=timeout_seconds,
        single_flight=True,
    )


def run_search_inspect_sync(
    mw: Any,
    payload: object,
    *,
    formatter_store_provider: Callable[[], dict[str, Any]] | None = None,
    timeout_seconds: float = SEARCH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return _run_search_sync(
        mw,
        payload,
        validator=normalize_search_inspect_request,
        executor=execute_search_inspect,
        formatter_store_provider=formatter_store_provider,
        timeout_seconds=timeout_seconds,
        single_flight=False,
    )


def _run_search_sync(
    mw: Any,
    payload: object,
    *,
    validator: Callable[[object], dict[str, Any]],
    executor: Callable[[Any, object, Any], dict[str, Any]],
    formatter_store_provider: Callable[[], dict[str, Any]] | None,
    timeout_seconds: float,
    single_flight: bool,
) -> dict[str, Any]:
    request_id = payload.get("requestId") if isinstance(payload, dict) else None
    try:
        validator(payload)
    except SearchValidationError as error:
        return _error("invalid_search_request", "Check the search request parameters.", request_id, fieldErrors=error.field_errors)

    formatter_resolver = _read_formatter_resolver(formatter_store_provider)
    if mw is None or getattr(mw, "col", None) is None or not hasattr(mw, "taskman"):
        return _error("search_unavailable", "The Anki collection is unavailable.", request_id)

    gate = _query_gate_for(mw) if single_flight else None
    if gate is not None and not gate.try_start():
        return _error("search_busy", "Another broad search is still running.", request_id)

    event = threading.Event()
    holder: dict[str, Any] = {}

    def finish_gate() -> None:
        if gate is not None:
            gate.finish()

    def success(value: object) -> None:
        holder["response"] = {"ok": True, "response": value}
        finish_gate()
        event.set()

    def failure(error: Exception) -> None:
        if isinstance(error, SearchValidationError):
            holder["response"] = _error(
                "invalid_search_request",
                "Anki rejected the native search query.",
                request_id,
                fieldErrors=error.field_errors,
            )
        elif isinstance(error, SearchEntityNotFoundError):
            holder["response"] = _error("search_entity_not_found", str(error), request_id)
        else:
            _log_safe_failure(error)
            holder["response"] = _error("search_failed", "The search request failed.", request_id)
        finish_gate()
        event.set()

    def start() -> None:
        try:
            QueryOp = _query_op_type()
            operation = QueryOp(
                parent=mw,
                op=lambda col: (
                    executor(col, payload)
                    if formatter_resolver is None
                    else executor(col, payload, formatter_resolver)
                ),
                success=success,
            )
            operation.failure(failure).run_in_background()
        except Exception as error:
            failure(error)

    try:
        mw.taskman.run_on_main(start)
    except Exception:
        finish_gate()
        return _error("search_unavailable", "Could not schedule the search request.", request_id)

    if not event.wait(max(0.001, float(timeout_seconds))):
        return _error("search_timeout", "The search request did not finish in time.", request_id)
    response = holder.get("response")
    return response if isinstance(response, dict) else _error("search_failed", "The search request failed.", request_id)


def _query_gate_for(mw: Any) -> _SearchQueryGate:
    with _GATE_CREATION_LOCK:
        gate = getattr(mw, "_anki_study_report_search_query_gate", None)
        if isinstance(gate, _SearchQueryGate):
            return gate
        gate = _SearchQueryGate()
        setattr(mw, "_anki_study_report_search_query_gate", gate)
        return gate


def _read_formatter_resolver(
    provider: Callable[[], dict[str, Any]] | None,
) -> CardDisplayFormatterResolver | None:
    if provider is None:
        return None
    try:
        snapshot = provider()
        if not isinstance(snapshot, dict):
            raise TypeError("formatter store provider did not return an object")
        return CardDisplayFormatterResolver.from_snapshot(snapshot)
    except Exception as error:
        log_event(
            "search.formatters.error",
            "Card display formatter source failed",
            exception_type=type(error).__name__,
        )
        return CardDisplayFormatterResolver.from_snapshot(
            {"status": "unavailable", "formatters": []}
        )


def _query_op_type() -> Any:
    from aqt.operations import QueryOp
    return QueryOp


def _error(code: str, message: str, request_id: object, **extra: Any) -> dict[str, Any]:
    response: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if isinstance(request_id, str):
        response["requestId"] = request_id
    response.update(extra)
    return response


def _log_safe_failure(error: Exception) -> None:
    frames = traceback.extract_tb(error.__traceback__)[-12:]
    stack = [f"{frame.name}:{frame.lineno}" for frame in frames]
    log_event(
        "search.query.error",
        "Search background operation failed",
        exception_type=type(error).__name__,
        stack=stack,
    )
