"""Bounded all-collection catalogs used by the Search workspace controls."""

from __future__ import annotations

import re
from typing import Any

from .search_service import (
    MAX_ID,
    REQUEST_ID_PATTERN,
    SearchValidationError,
    execute_search_query,
    normalize_search_query_request,
)

SEARCH_METADATA_SCHEMA_VERSION = 1
SEARCH_METADATA_DECK_LIMIT = 5000
SEARCH_METADATA_NOTE_TYPE_LIMIT = 1000
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def normalize_search_request(raw: object) -> dict[str, Any]:
    """Validate either a normal query request or the strict metadata variant."""

    if not isinstance(raw, dict) or raw.get("kind") != "metadata":
        return normalize_search_query_request(raw)

    errors: dict[str, str] = {}
    allowed = {"kind", "requestId"}
    for key in raw:
        if key not in allowed:
            errors[key] = "Unexpected field."
    if set(raw) - allowed:
        errors["request"] = "Metadata requests accept only kind and requestId."

    request_id = raw.get("requestId")
    if request_id is not None and (
        not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id)
    ):
        errors["requestId"] = "Expected 1-128 non-secret correlation characters."
        request_id = None
    if errors:
        raise SearchValidationError(errors)
    return {"kind": "metadata", "requestId": request_id}


def execute_search_request(
    col: Any,
    raw: object,
    formatter_resolver: Any = None,
) -> dict[str, Any]:
    """Execute metadata or delegate an untouched query to its owning validator."""

    if isinstance(raw, dict) and raw.get("kind") == "metadata":
        return execute_search_metadata(col, normalize_search_request(raw))
    # execute_search_query owns query normalization. Passing its already-normalized
    # result back through the validator would turn decimal-string deck/note-type IDs
    # into integers and then reject them on the second pass.
    return execute_search_query(col, raw, formatter_resolver)


def execute_search_metadata(col: Any, request: dict[str, Any]) -> dict[str, Any]:
    decks = sorted(_deck_catalog(col), key=lambda item: (item["deckName"].casefold(), int(item["deckId"])))
    note_types = sorted(
        _note_type_catalog(col),
        key=lambda item: (item["noteTypeName"].casefold(), int(item["noteTypeId"])),
    )
    response: dict[str, Any] = {
        "schemaVersion": SEARCH_METADATA_SCHEMA_VERSION,
        "kind": "metadata",
        "decks": decks[:SEARCH_METADATA_DECK_LIMIT],
        "noteTypes": note_types[:SEARCH_METADATA_NOTE_TYPE_LIMIT],
        "decksTruncated": len(decks) > SEARCH_METADATA_DECK_LIMIT,
        "noteTypesTruncated": len(note_types) > SEARCH_METADATA_NOTE_TYPE_LIMIT,
    }
    if request.get("requestId") is not None:
        response["requestId"] = request["requestId"]
    return response


def _deck_catalog(col: Any) -> list[dict[str, Any]]:
    manager = getattr(col, "decks", None)
    all_decks = manager.all() if manager is not None and callable(getattr(manager, "all", None)) else []
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for deck in all_decks or []:
        if not isinstance(deck, dict):
            continue
        deck_id = _positive_id(deck.get("id"))
        name = _bounded_name(deck.get("name"))
        if deck_id is None or not name or deck_id in seen:
            continue
        seen.add(deck_id)
        rows.append({
            "deckId": str(deck_id),
            "deckName": name,
            "filtered": bool(deck.get("dyn")),
        })
    return rows


def _note_type_catalog(col: Any) -> list[dict[str, str]]:
    manager = getattr(col, "models", None)
    items = (
        manager.all_names_and_ids()
        if manager is not None and callable(getattr(manager, "all_names_and_ids", None))
        else []
    )
    rows: list[dict[str, str]] = []
    seen: set[int] = set()
    for item in items or []:
        if isinstance(item, dict):
            raw_id = item.get("id")
            raw_name = item.get("name")
        else:
            raw_id = getattr(item, "id", None)
            raw_name = getattr(item, "name", None)
        note_type_id = _positive_id(raw_id)
        name = _bounded_name(raw_name)
        if note_type_id is None or not name or note_type_id in seen:
            continue
        seen.add(note_type_id)
        rows.append({"noteTypeId": str(note_type_id), "noteTypeName": name})
    return rows


def _positive_id(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 0 < parsed <= MAX_ID else None


def _bounded_name(value: object) -> str:
    text = _CONTROL_CHARACTERS.sub("", str(value or "")).strip()
    return text[:500]
