"""Synchronous local bridge for the formatter store API."""

from __future__ import annotations

from typing import Any, Callable

from .extension_logging import log_event
from .card_display_formatter_service import (
    apply_formatter_update,
    execute_formatter_query,
    execute_formatter_validate,
    normalize_formatter_query_request,
    normalize_formatter_update_request,
    normalize_formatter_validate_request,
)
from .card_display_formatter_store import (
    CardDisplayFormatterConflictError,
    CardDisplayFormatterStore,
    CardDisplayFormatterStoreUnavailableError,
    CardDisplayFormatterValidationError,
    UnsupportedCardDisplayFormatterSchemaError,
)


def run_card_display_formatter_query_sync(
    payload: object,
    store: CardDisplayFormatterStore,
) -> dict[str, Any]:
    return _run(
        payload,
        validate=normalize_formatter_query_request,
        operation=lambda: execute_formatter_query(payload, store.read()),
    )


def run_card_display_formatter_validate_sync(
    payload: object,
    _store: CardDisplayFormatterStore,
) -> dict[str, Any]:
    return _run(
        payload,
        validate=normalize_formatter_validate_request,
        operation=lambda: execute_formatter_validate(payload),
    )


def run_card_display_formatter_update_sync(
    payload: object,
    store: CardDisplayFormatterStore,
) -> dict[str, Any]:
    return _run(
        payload,
        validate=normalize_formatter_update_request,
        operation=lambda: apply_formatter_update(store, payload),
    )


def _run(
    payload: object,
    *,
    validate: Callable[[object], dict[str, Any]],
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        validate(payload)
        return {"ok": True, "response": operation()}
    except CardDisplayFormatterValidationError as error:
        return _error(
            "invalid_card_display_formatter_request",
            fieldErrors=error.field_errors,
        )
    except CardDisplayFormatterConflictError as error:
        return _error(
            "card_display_formatter_revision_conflict",
            currentRevision=error.current_revision,
        )
    except UnsupportedCardDisplayFormatterSchemaError:
        return _error("card_display_formatter_future_schema")
    except CardDisplayFormatterStoreUnavailableError:
        return _error("card_display_formatters_unavailable")
    except Exception as error:
        log_event(
            "card_display_formatters.api.error",
            "Card display formatter operation failed",
            exception_type=type(error).__name__,
        )
        return _error("card_display_formatters_failed")


def _error(code: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, **extra}
