"""Serialized QueryOp bridge for the Inspection Profiles runtime API."""

from __future__ import annotations

import threading
from typing import Any, Callable

from .extension_logging import log_event
from .inspection_profile_service import (
    apply_inspection_update,
    execute_inspection_query,
    execute_inspection_validate,
    normalize_inspection_query_request,
    normalize_inspection_update_request,
    normalize_inspection_validate_request,
    prepare_inspection_update,
)
from .inspection_profile_store import (
    InspectionProfileConflictError,
    InspectionProfileStore,
    InspectionProfileStoreUnavailableError,
    InspectionProfileValidationError,
    UnsupportedInspectionProfileSchemaError,
)


INSPECTION_PROFILE_TIMEOUT_SECONDS = 20.0


def run_inspection_profile_query_sync(
    mw: Any,
    payload: object,
    store: InspectionProfileStore,
    *,
    timeout_seconds: float = INSPECTION_PROFILE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return _run(
        mw,
        payload,
        validate=normalize_inspection_query_request,
        operation=lambda col: execute_inspection_query(col, payload, store.read()),
        timeout_seconds=timeout_seconds,
    )


def run_inspection_profile_validate_sync(
    mw: Any,
    payload: object,
    _store: InspectionProfileStore,
    *,
    timeout_seconds: float = INSPECTION_PROFILE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return _run(
        mw,
        payload,
        validate=normalize_inspection_validate_request,
        operation=lambda col: execute_inspection_validate(col, payload),
        timeout_seconds=timeout_seconds,
    )


def run_inspection_profile_update_sync(
    mw: Any,
    payload: object,
    store: InspectionProfileStore,
    *,
    timeout_seconds: float = INSPECTION_PROFILE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return _run(
        mw,
        payload,
        validate=normalize_inspection_update_request,
        operation=lambda col: apply_inspection_update(store, prepare_inspection_update(col, payload)),
        timeout_seconds=timeout_seconds,
    )


def _run(
    mw: Any,
    payload: object,
    *,
    validate: Callable[[object], dict[str, Any]],
    operation: Callable[[Any], dict[str, Any]],
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        validate(payload)
    except InspectionProfileValidationError as error:
        return _error("invalid_inspection_profile_request", fieldErrors=error.field_errors)
    if mw is None or getattr(mw, "col", None) is None or not hasattr(mw, "taskman"):
        return _error("inspection_profiles_unavailable")

    event = threading.Event()
    holder: dict[str, Any] = {}

    def success(value: object) -> None:
        holder["response"] = {"ok": True, "response": value}
        event.set()

    def failure(error: Exception) -> None:
        if isinstance(error, InspectionProfileValidationError):
            holder["response"] = _error(
                "invalid_inspection_profile_request", fieldErrors=error.field_errors
            )
        elif isinstance(error, InspectionProfileConflictError):
            holder["response"] = _error(
                "inspection_profile_revision_conflict", currentRevision=error.current_revision
            )
        elif isinstance(error, UnsupportedInspectionProfileSchemaError):
            holder["response"] = _error("inspection_profile_future_schema")
        elif isinstance(error, InspectionProfileStoreUnavailableError):
            holder["response"] = _error("inspection_profiles_unavailable")
        else:
            log_event(
                "inspection_profiles.api.error",
                "Inspection Profile operation failed",
                exception_type=type(error).__name__,
            )
            holder["response"] = _error("inspection_profiles_failed")
        event.set()

    def start() -> None:
        try:
            query_op = _query_op_type()(parent=mw, op=operation, success=success)
            query_op.failure(failure).run_in_background()
        except Exception as error:
            failure(error)

    try:
        mw.taskman.run_on_main(start)
    except Exception:
        return _error("inspection_profiles_unavailable")
    if not event.wait(max(0.001, float(timeout_seconds))):
        return _error("inspection_profiles_timeout")
    response = holder.get("response")
    return response if isinstance(response, dict) else _error("inspection_profiles_failed")


def _query_op_type() -> Any:
    from aqt.operations import QueryOp

    return QueryOp


def _error(code: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, **extra}
