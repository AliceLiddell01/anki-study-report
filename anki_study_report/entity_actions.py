"""Strict contracts and preflight helpers for explicit entity actions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


ENTITY_ACTION_SCHEMA_VERSION = 1
ENTITY_ACTION_BATCH_LIMIT = 200
ENTITY_ACTION_TAG_LIMIT = 20
ENTITY_ACTION_TAG_TOTAL_LIMIT = 1000
CARD_ACTIONS = {"suspend", "unsuspend", "set_flag", "clear_flag"}
NOTE_ACTIONS = {"add_tags", "remove_tags"}
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_DECIMAL_ID = re.compile(r"[1-9]\d{0,18}")


class EntityActionValidationError(ValueError):
    def __init__(self, message: str, *, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}


class EntityActionStaleError(LookupError):
    pass


@dataclass(frozen=True)
class EntityActionPlan:
    entity_type: str
    action: str
    entity_ids: tuple[int, ...]
    requested_count: int
    affected_count: int
    unchanged_count: int
    request_id: str | None
    args: dict[str, Any]
    native_args: dict[str, Any]


def normalize_card_action_request(payload: object) -> dict[str, Any]:
    data = _object(payload)
    action = data.get("action")
    if action not in CARD_ACTIONS:
        raise _invalid("action", "Choose a supported card action.")
    expected = {"action", "cardIds"}
    if action == "set_flag":
        expected.add("flag")
    _exact_fields(data, expected, optional={"requestId"})
    ids = _entity_ids(data.get("cardIds"), "cardIds")
    request_id = _request_id(data.get("requestId"))
    normalized: dict[str, Any] = {
        "action": action,
        "cardIds": ids,
        "requestId": request_id,
    }
    if action == "set_flag":
        flag = data.get("flag")
        if isinstance(flag, bool) or not isinstance(flag, int) or flag not in range(1, 8):
            raise _invalid("flag", "Choose a flag from 1 to 7.")
        normalized["flag"] = flag
    return normalized


def normalize_note_action_request(payload: object) -> dict[str, Any]:
    data = _object(payload)
    action = data.get("action")
    if action not in NOTE_ACTIONS:
        raise _invalid("action", "Choose a supported note action.")
    _exact_fields(data, {"action", "noteIds", "tags"}, optional={"requestId"})
    ids = _entity_ids(data.get("noteIds"), "noteIds")
    tags = _tags(data.get("tags"))
    return {
        "action": action,
        "noteIds": ids,
        "tags": tags,
        "requestId": _request_id(data.get("requestId")),
    }


def prepare_card_action(col: Any, request: dict[str, Any]) -> EntityActionPlan:
    cards = _resolve(col.get_card, request["cardIds"], "card")
    action = request["action"]
    flag = request.get("flag", 0)
    if action == "suspend":
        affected = sum(int(getattr(card, "queue", 0)) != -1 for card in cards)
    elif action == "unsuspend":
        affected = sum(int(getattr(card, "queue", 0)) == -1 for card in cards)
    elif action == "set_flag":
        affected = sum((int(getattr(card, "flags", 0)) & 7) != flag for card in cards)
    else:
        affected = sum((int(getattr(card, "flags", 0)) & 7) != 0 for card in cards)
    args = {"flag": flag} if action == "set_flag" else {}
    return _plan("cards", request, "cardIds", affected, args, args)


def prepare_note_action(col: Any, request: dict[str, Any]) -> EntityActionPlan:
    notes = _resolve(col.get_note, request["noteIds"], "note")
    native_tags = _dedupe_casefold(col.tags.split(" ".join(request["tags"])))
    if not native_tags:
        raise _invalid("tags", "Provide at least one tag.")
    if len(native_tags) > ENTITY_ACTION_TAG_LIMIT:
        raise _invalid("tags", f"Provide at most {ENTITY_ACTION_TAG_LIMIT} native Anki tags.")
    requested = {tag.casefold() for tag in native_tags}
    if request["action"] == "add_tags":
        affected = sum(not requested.issubset({str(tag).casefold() for tag in note.tags}) for note in notes)
    else:
        affected = sum(bool(requested.intersection({str(tag).casefold() for tag in note.tags})) for note in notes)
    args = {"tagCount": len(native_tags)}
    native_args = {"tags": " ".join(native_tags)}
    return _plan("notes", request, "noteIds", affected, args, native_args)


def action_result(plan: EntityActionPlan, *, undoable: bool) -> dict[str, Any]:
    result_code = {
        "suspend": "cards.suspended",
        "unsuspend": "cards.unsuspended",
        "set_flag": "cards.flag_set",
        "clear_flag": "cards.flag_cleared",
        "add_tags": "notes.tags_added",
        "remove_tags": "notes.tags_removed",
    }[plan.action]
    if plan.affected_count == 0:
        result_code = "action.no_changes"
    response: dict[str, Any] = {
        "schemaVersion": ENTITY_ACTION_SCHEMA_VERSION,
        "entityType": plan.entity_type,
        "action": plan.action,
        "requestedCount": plan.requested_count,
        "affectedCount": plan.affected_count,
        "unchangedCount": plan.unchanged_count,
        "undoable": undoable,
        "resultCode": result_code,
        "args": dict(plan.args),
    }
    if plan.request_id is not None:
        response["requestId"] = plan.request_id
    return response


def _plan(
    entity_type: str,
    request: dict[str, Any],
    id_key: str,
    affected: int,
    args: dict[str, Any],
    native_args: dict[str, Any],
) -> EntityActionPlan:
    ids = tuple(request[id_key])
    return EntityActionPlan(
        entity_type=entity_type,
        action=request["action"],
        entity_ids=ids,
        requested_count=len(ids),
        affected_count=affected,
        unchanged_count=len(ids) - affected,
        request_id=request.get("requestId"),
        args=args,
        native_args=native_args,
    )


def _resolve(getter: Any, ids: list[int], kind: str) -> list[Any]:
    entities: list[Any] = []
    try:
        for entity_id in ids:
            entity = getter(entity_id)
            if int(getattr(entity, "id", 0) or 0) != entity_id:
                raise LookupError
            entities.append(entity)
    except Exception as error:
        raise EntityActionStaleError(
            f"A selected {kind} is unavailable or was deleted."
        ) from error
    return entities


def _object(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EntityActionValidationError("The request body must be an object.")
    return payload


def _exact_fields(data: dict[str, Any], expected: set[str], *, optional: set[str] | None = None) -> None:
    optional = optional or set()
    if not expected.issubset(data) or not set(data).issubset(expected | optional):
        raise EntityActionValidationError(
            "The request fields do not match the selected action.",
            field_errors={"body": "Remove unknown fields and include every required field."},
        )


def _entity_ids(value: object, field: str) -> list[int]:
    if not isinstance(value, list) or not value or len(value) > ENTITY_ACTION_BATCH_LIMIT:
        raise _invalid(field, f"Select between 1 and {ENTITY_ACTION_BATCH_LIMIT} entities.")
    parsed: list[int] = []
    seen: set[int] = set()
    for item in value:
        if not isinstance(item, str) or not _DECIMAL_ID.fullmatch(item):
            raise _invalid(field, "Entity IDs must be positive decimal strings.")
        entity_id = int(item)
        if entity_id > 9_223_372_036_854_775_807 or entity_id in seen:
            raise _invalid(field, "Entity IDs must be unique signed 64-bit values.")
        seen.add(entity_id)
        parsed.append(entity_id)
    return parsed


def _request_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _REQUEST_ID.fullmatch(value):
        raise _invalid("requestId", "Use a short opaque request ID.")
    return value


def _tags(value: object) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > ENTITY_ACTION_TAG_LIMIT:
        raise _invalid("tags", f"Provide between 1 and {ENTITY_ACTION_TAG_LIMIT} tags.")
    tags: list[str] = []
    seen: set[str] = set()
    total = 0
    for item in value:
        if not isinstance(item, str) or not item.strip() or any(ord(char) < 32 or ord(char) == 127 for char in item):
            raise _invalid("tags", "Tags must be non-empty text without control characters.")
        total += len(item)
        if total > ENTITY_ACTION_TAG_TOTAL_LIMIT:
            raise _invalid("tags", f"Tags may contain at most {ENTITY_ACTION_TAG_TOTAL_LIMIT} characters in total.")
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            tags.append(item)
    return tags


def _dedupe_casefold(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _invalid(field: str, message: str) -> EntityActionValidationError:
    return EntityActionValidationError(message, field_errors={field: message})
