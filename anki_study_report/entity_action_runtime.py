"""Synchronous HTTP bridge to official undoable Anki entity operations."""

from __future__ import annotations

import threading
import traceback
from collections.abc import Callable
from typing import Any

from .entity_actions import (
    EntityActionPlan,
    EntityActionDomainError,
    EntityActionStaleError,
    EntityActionValidationError,
    action_result,
    normalize_card_action_request,
    normalize_note_action_request,
    prepare_card_action,
    prepare_note_action,
)
from .extension_logging import log_event


ENTITY_ACTION_TIMEOUT_SECONDS = 20.0


def run_card_action_sync(mw: Any, payload: object, *, timeout_seconds: float = ENTITY_ACTION_TIMEOUT_SECONDS) -> dict[str, Any]:
    return _run_action_sync(
        mw,
        payload,
        entity_type="cards",
        validator=normalize_card_action_request,
        planner=prepare_card_action,
        timeout_seconds=timeout_seconds,
    )


def run_note_action_sync(mw: Any, payload: object, *, timeout_seconds: float = ENTITY_ACTION_TIMEOUT_SECONDS) -> dict[str, Any]:
    return _run_action_sync(
        mw,
        payload,
        entity_type="notes",
        validator=normalize_note_action_request,
        planner=prepare_note_action,
        timeout_seconds=timeout_seconds,
    )


def _run_action_sync(
    mw: Any,
    payload: object,
    *,
    entity_type: str,
    validator: Callable[[object], dict[str, Any]],
    planner: Callable[[Any, dict[str, Any]], EntityActionPlan],
    timeout_seconds: float,
) -> dict[str, Any]:
    request_id = payload.get("requestId") if isinstance(payload, dict) else None
    try:
        request = validator(payload)
    except EntityActionValidationError as error:
        return _error("invalid_entity_action", "Check the action request parameters.", request_id, fieldErrors=error.field_errors)
    if mw is None or getattr(mw, "col", None) is None or not hasattr(mw, "taskman"):
        return _error("entity_action_unavailable", "The Anki collection is unavailable.", request_id)

    event = threading.Event()
    holder: dict[str, Any] = {}

    def finish(response: dict[str, Any]) -> None:
        holder["response"] = response
        event.set()

    def failure(error: Exception) -> None:
        if isinstance(error, EntityActionValidationError):
            finish(_error("invalid_entity_action", "Check the action request parameters.", request_id, fieldErrors=error.field_errors))
        elif isinstance(error, EntityActionStaleError):
            finish(_error("entity_action_stale", str(error), request_id))
        elif isinstance(error, EntityActionDomainError):
            finish(_error(error.code, str(error), request_id))
        else:
            _log_safe_failure(error, entity_type=entity_type, action=request["action"], count=len(request[f"{entity_type[:-1]}Ids"]))
            finish(_error("entity_action_failed", "The Anki action failed.", request_id))

    def start() -> None:
        try:
            plan = planner(mw.col, request)
            if plan.affected_count == 0:
                finish({"ok": True, "response": action_result(plan, undoable=False)})
                return
            operation = _native_operation(mw, plan)
            operation.success(
                lambda _changes: finish({"ok": True, "response": action_result(plan, undoable=True)})
            ).failure(failure).run_in_background()
        except Exception as error:
            failure(error)

    try:
        mw.taskman.run_on_main(start)
    except Exception:
        return _error("entity_action_unavailable", "Could not schedule the Anki action.", request_id)
    if not event.wait(max(0.001, float(timeout_seconds))):
        return _error("entity_action_timeout", "The Anki action did not finish in time.", request_id)
    response = holder.get("response")
    return response if isinstance(response, dict) else _error("entity_action_failed", "The Anki action failed.", request_id)


def _native_operation(mw: Any, plan: EntityActionPlan) -> Any:
    ids = list(plan.entity_ids)
    if plan.action == "suspend":
        from aqt.operations.scheduling import suspend_cards
        return suspend_cards(parent=mw, card_ids=ids)
    if plan.action == "unsuspend":
        from aqt.operations.scheduling import unsuspend_cards
        return unsuspend_cards(parent=mw, card_ids=ids)
    if plan.action == "bury":
        from aqt.operations.scheduling import bury_cards
        return bury_cards(parent=mw, card_ids=ids)
    if plan.action == "unbury":
        from aqt.operations.scheduling import unbury_cards
        return unbury_cards(parent=mw, card_ids=ids)
    if plan.action in {"set_flag", "clear_flag"}:
        from aqt.operations.card import set_card_flag
        return set_card_flag(parent=mw, card_ids=ids, flag=int(plan.native_args.get("flag", 0)))
    if plan.action == "add_tags":
        from aqt.operations.tag import add_tags_to_notes
        return add_tags_to_notes(parent=mw, note_ids=ids, space_separated_tags=str(plan.native_args["tags"]))
    if plan.action == "remove_tags":
        from aqt.operations.tag import remove_tags_from_notes
        return remove_tags_from_notes(parent=mw, note_ids=ids, space_separated_tags=str(plan.native_args["tags"]))
    if plan.action == "move_to_deck":
        from aqt.operations.card import set_card_deck
        return set_card_deck(parent=mw, card_ids=ids, deck_id=int(plan.native_args["deckId"]))
    raise EntityActionValidationError("Unsupported entity action.")


def _error(code: str, message: str, request_id: object, **extra: Any) -> dict[str, Any]:
    response: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if isinstance(request_id, str):
        response["requestId"] = request_id
    response.update(extra)
    return response


def _log_safe_failure(error: Exception, *, entity_type: str, action: str, count: int) -> None:
    frames = traceback.extract_tb(error.__traceback__)[-12:]
    log_event(
        "entity.action.error",
        "Entity batch action failed",
        entity_type=entity_type,
        action=action,
        count=count,
        exception_type=type(error).__name__,
        stack=[f"{frame.name}:{frame.lineno}" for frame in frames],
    )
