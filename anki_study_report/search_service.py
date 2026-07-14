"""Bounded read-only search/query projections for the dashboard.

Native Anki owns query parsing and structured search construction. This module
only validates the public request shape, asks the collection to execute the
search, and projects compact plain-text rows/details.
"""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import math
import re
from typing import Any


SEARCH_SCHEMA_VERSION = 1
MAX_QUERY_LENGTH = 4096
MAX_FILTERS = 12
ALLOWED_PAGE_SIZES = (25, 50, 100)
DEFAULT_PAGE_SIZE = 50
RESULT_CAP = 2000
MAX_PRIMARY_TEXT_LENGTH = 240
MAX_FIELD_VALUE_LENGTH = 2000
MAX_FIELDS = 64
MAX_TAGS = 50
MAX_CARD_REFERENCES = 100
MAX_DECK_SUMMARY = 20
MAX_ID = 9_223_372_036_854_775_807
MODES = {"cards", "notes"}
SORT_DIRECTIONS = {"asc", "desc"}
SORT_KEYS = {"entity_id"}
CARD_STATES = {"new", "learning", "review", "due", "suspended", "buried"}
FLAG_VALUES = set(range(8))
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
MEDIA_MARKER_PATTERN = re.compile(r"\[sound:[^\]\r\n]{1,500}\]", re.IGNORECASE)
CLOZE_PATTERN = re.compile(r"\{\{c\d+::(.*?)(?:::[^{}]*?)?\}\}", re.IGNORECASE)
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class SearchValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str], message: str = "Invalid search request.") -> None:
        super().__init__(message)
        self.field_errors = field_errors


class SearchEntityNotFoundError(LookupError):
    def __init__(self, mode: str) -> None:
        super().__init__(f"The selected {mode[:-1]} is unavailable or was deleted.")
        self.mode = mode


def normalize_search_query_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SearchValidationError({"request": "Expected a JSON object."})
    allowed = {"mode", "query", "filters", "sort", "page", "pageSize", "requestId"}
    errors = {key: "Unexpected field." for key in raw if key not in allowed}

    mode = raw.get("mode")
    if mode not in MODES:
        errors["mode"] = "Expected cards or notes."

    query = raw.get("query", "")
    if not isinstance(query, str):
        errors["query"] = "Expected a string."
        query = ""
    elif len(query) > MAX_QUERY_LENGTH:
        errors["query"] = f"Query exceeds {MAX_QUERY_LENGTH} characters."
    elif CONTROL_PATTERN.search(query):
        errors["query"] = "Query contains unsupported control characters."

    filters = _normalize_filters(raw.get("filters", []), mode, errors)
    sort = _normalize_sort(raw.get("sort", {"key": "entity_id", "direction": "asc"}), errors)
    page = _strict_int(raw.get("page", 1))
    page_size = _strict_int(raw.get("pageSize", DEFAULT_PAGE_SIZE))
    if page is None or page <= 0:
        errors["page"] = "Expected a positive integer."
        page = 1
    if page_size not in ALLOWED_PAGE_SIZES:
        errors["pageSize"] = f"Expected one of {list(ALLOWED_PAGE_SIZES)}."
        page_size = DEFAULT_PAGE_SIZE
    max_page = math.ceil(RESULT_CAP / page_size)
    if page > max_page:
        errors["page"] = f"Page exceeds the maximum {max_page} for this page size."

    request_id = raw.get("requestId")
    if request_id is not None and (not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id)):
        errors["requestId"] = "Expected 1-128 non-secret correlation characters."
        request_id = None

    if errors:
        raise SearchValidationError(errors)
    return {
        "mode": mode,
        "query": query,
        "filters": filters,
        "sort": sort,
        "page": page,
        "pageSize": page_size,
        "requestId": request_id,
    }


def normalize_search_inspect_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SearchValidationError({"request": "Expected a JSON object."})
    allowed = {"mode", "cardId", "noteId", "requestId"}
    errors = {key: "Unexpected field." for key in raw if key not in allowed}
    mode = raw.get("mode")
    if mode not in MODES:
        errors["mode"] = "Expected cards or notes."
    expected_key = "cardId" if mode == "cards" else "noteId"
    unexpected_key = "noteId" if mode == "cards" else "cardId"
    entity_id = _strict_id(raw.get(expected_key)) if mode in MODES else None
    if entity_id is None:
        errors[expected_key] = "Expected a positive decimal ID string."
    if unexpected_key in raw:
        errors[unexpected_key] = f"Not valid in {mode or 'this'} mode."
    request_id = raw.get("requestId")
    if request_id is not None and (not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id)):
        errors["requestId"] = "Expected 1-128 non-secret correlation characters."
        request_id = None
    if errors:
        raise SearchValidationError(errors)
    return {"mode": mode, expected_key: entity_id, "requestId": request_id}


def execute_search_query(col: Any, raw: object) -> dict[str, Any]:
    # Always revalidate at the collection boundary. This keeps the public
    # helpers safe even when they are called outside the HTTP bridge.
    request = normalize_search_query_request(raw)
    native_query = build_native_query(col, request)
    found = col.find_cards(native_query, order=False) if request["mode"] == "cards" else col.find_notes(native_query, order=False)

    ids = sorted({_coerce_entity_id(value) for value in found}, reverse=request["sort"]["direction"] == "desc")
    truncated = len(ids) > RESULT_CAP
    bounded_ids = ids[:RESULT_CAP]
    page = request["page"]
    page_size = request["pageSize"]
    offset = (page - 1) * page_size
    page_ids = bounded_ids[offset:offset + page_size]
    if request["mode"] == "cards":
        items = [project_card_row(col, col.get_card(card_id)) for card_id in page_ids]
    else:
        items = [project_note_row(col, col.get_note(note_id)) for note_id in page_ids]
    response: dict[str, Any] = {
        "schemaVersion": SEARCH_SCHEMA_VERSION,
        "mode": request["mode"],
        "items": items,
        "page": page,
        "pageSize": page_size,
        "maxPage": math.ceil(RESULT_CAP / page_size),
        "returnedCount": len(items),
        "boundedTotal": len(bounded_ids),
        "hasNext": offset + len(items) < len(bounded_ids),
        "truncated": truncated,
        "sort": dict(request["sort"]),
    }
    if request.get("requestId") is not None:
        response["requestId"] = request["requestId"]
    return response


def execute_search_inspect(col: Any, raw: object) -> dict[str, Any]:
    request = normalize_search_inspect_request(raw)
    mode = request["mode"]
    try:
        if mode == "cards":
            details = project_card_details(col, col.get_card(request["cardId"]))
        else:
            details = project_note_details(col, col.get_note(request["noteId"]))
    except SearchEntityNotFoundError:
        raise
    except Exception as error:
        raise SearchEntityNotFoundError(mode) from error
    response = {"schemaVersion": SEARCH_SCHEMA_VERSION, "mode": mode, "details": details}
    if request.get("requestId") is not None:
        response["requestId"] = request["requestId"]
    return response


def build_native_query(col: Any, request: dict[str, Any]) -> str:
    nodes: list[Any] = []
    if request["query"]:
        nodes.append(request["query"])
    for item in request["filters"]:
        nodes.append(_filter_node(col, item))
    try:
        return col.build_search_string(*(nodes or [""]))
    except Exception as error:
        raise SearchValidationError({"query": "Anki rejected the native search query."}) from error


def safe_plain_text(value: object, *, max_length: int = MAX_PRIMARY_TEXT_LENGTH) -> str:
    text = str(value or "")
    text = MEDIA_MARKER_PATTERN.sub(" ", text)
    for _ in range(4):
        replaced = CLOZE_PATTERN.sub(r"\1", text)
        if replaced == text:
            break
        text = replaced
    parser = _PlainTextParser()
    try:
        parser.feed(text)
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]*>", " ", text)
    text = " ".join(unescape(text).replace("\xa0", " ").split())
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 1)].rstrip() + "…"


def project_card_row(col: Any, card: Any) -> dict[str, Any]:
    note = card.note() if callable(getattr(card, "note", None)) else col.get_note(card.nid)
    note_type = _note_type(note)
    deck_id = _card_deck_id(card)
    return {
        "cardId": str(_coerce_entity_id(card.id)),
        "noteId": str(_coerce_entity_id(card.nid)),
        "deckId": str(deck_id),
        "deckName": _deck_name(col, deck_id),
        "noteTypeId": str(_coerce_entity_id(getattr(note, "mid", note_type.get("id", 0)))),
        "noteTypeName": str(note_type.get("name") or ""),
        "templateOrdinal": int(getattr(card, "ord", 0)),
        "templateName": _template_name(card, note_type),
        "primaryText": _primary_text(note, note_type),
        "state": _card_state(card),
        "due": int(getattr(card, "due", 0)),
        "interval": int(getattr(card, "ivl", 0)),
        "repetitions": int(getattr(card, "reps", 0)),
        "lapses": int(getattr(card, "lapses", 0)),
        "flag": int(getattr(card, "flags", 0)) & 7,
        "tagSummary": _tags(note, limit=8),
    }


def project_note_row(col: Any, note: Any) -> dict[str, Any]:
    note_type = _note_type(note)
    cards = _note_cards(note)
    decks = _deck_summary(col, cards, MAX_DECK_SUMMARY)
    return {
        "noteId": str(_coerce_entity_id(note.id)),
        "noteTypeId": str(_coerce_entity_id(getattr(note, "mid", note_type.get("id", 0)))),
        "noteTypeName": str(note_type.get("name") or ""),
        "primaryText": _primary_text(note, note_type),
        "tagSummary": _tags(note, limit=8),
        "cardCount": len(cards),
        "deckSummary": decks,
    }


def project_card_details(col: Any, card: Any) -> dict[str, Any]:
    row = project_card_row(col, card)
    note = card.note() if callable(getattr(card, "note", None)) else col.get_note(card.nid)
    return {
        **row,
        "deck": {"deckId": row["deckId"], "deckName": row["deckName"]},
        "noteType": {"noteTypeId": row["noteTypeId"], "noteTypeName": row["noteTypeName"]},
        "template": {"ordinal": row["templateOrdinal"], "name": row["templateName"]},
        "queue": int(getattr(card, "queue", 0)),
        "tags": _tags(note, limit=MAX_TAGS),
    }


def project_note_details(col: Any, note: Any) -> dict[str, Any]:
    row = project_note_row(col, note)
    cards = _note_cards(note)
    card_refs = [
        {"cardId": str(_coerce_entity_id(card.id)), "deckId": str(_card_deck_id(card)), "templateOrdinal": int(getattr(card, "ord", 0))}
        for card in cards[:MAX_CARD_REFERENCES]
    ]
    field_items = _note_items(note)[:MAX_FIELDS]
    return {
        **row,
        "noteType": {"noteTypeId": row["noteTypeId"], "noteTypeName": row["noteTypeName"]},
        "fields": [
            {"name": safe_plain_text(name, max_length=100), "value": safe_plain_text(value, max_length=MAX_FIELD_VALUE_LENGTH)}
            for name, value in field_items
        ],
        "tags": _tags(note, limit=MAX_TAGS),
        "cardReferences": card_refs,
        "cardsTruncated": len(cards) > MAX_CARD_REFERENCES,
        "fieldsTruncated": len(_note_items(note)) > MAX_FIELDS,
        "deckSummaries": _deck_summary(col, cards, MAX_DECK_SUMMARY),
    }


def _normalize_filters(raw: object, mode: object, errors: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        errors["filters"] = "Expected an array."
        return []
    if len(raw) > MAX_FILTERS:
        errors["filters"] = f"At most {MAX_FILTERS} filters are allowed."
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw[:MAX_FILTERS]):
        prefix = f"filters.{index}"
        if not isinstance(item, dict):
            errors[prefix] = "Expected an object."
            continue
        kind = item.get("type")
        schemas = {
            "deck": {"type", "deckId"},
            "note_type": {"type", "noteTypeId"},
            "tag": {"type", "tag"},
            "state": {"type", "state"},
            "flag": {"type", "flag"},
        }
        if kind not in schemas:
            errors[f"{prefix}.type"] = "Unsupported filter type."
            continue
        for key in item:
            if key not in schemas[kind]:
                errors[f"{prefix}.{key}"] = "Unexpected field."
        if set(item) != schemas[kind]:
            for key in schemas[kind] - set(item):
                errors[f"{prefix}.{key}"] = "Required field."
        if kind == "deck":
            value = _strict_id(item.get("deckId"))
            if value is None:
                errors[f"{prefix}.deckId"] = "Expected a positive decimal ID string."
            else:
                result.append({"type": kind, "deckId": value})
        elif kind == "note_type":
            value = _strict_id(item.get("noteTypeId"))
            if value is None:
                errors[f"{prefix}.noteTypeId"] = "Expected a positive decimal ID string."
            else:
                result.append({"type": kind, "noteTypeId": value})
        elif kind == "tag":
            value = item.get("tag")
            if not isinstance(value, str) or not value.strip() or len(value) > 100 or CONTROL_PATTERN.search(value):
                errors[f"{prefix}.tag"] = "Expected a non-empty tag up to 100 characters."
            else:
                result.append({"type": kind, "tag": value})
        elif kind == "state":
            if mode != "cards":
                errors[prefix] = "Card state is only valid in cards mode."
            elif item.get("state") not in CARD_STATES:
                errors[f"{prefix}.state"] = "Unsupported card state."
            else:
                result.append({"type": kind, "state": item["state"]})
        elif kind == "flag":
            flag = _strict_int(item.get("flag"))
            if mode != "cards":
                errors[prefix] = "Flag is only valid in cards mode."
            elif flag not in FLAG_VALUES:
                errors[f"{prefix}.flag"] = "Expected a flag from 0 to 7."
            else:
                result.append({"type": kind, "flag": flag})
    return result


def _normalize_sort(raw: object, errors: dict[str, str]) -> dict[str, str]:
    if not isinstance(raw, dict):
        errors["sort"] = "Expected an object."
        return {"key": "entity_id", "direction": "asc"}
    for key in raw:
        if key not in {"key", "direction"}:
            errors[f"sort.{key}"] = "Unexpected field."
    key = raw.get("key", "entity_id")
    direction = raw.get("direction", "asc")
    if key not in SORT_KEYS:
        errors["sort.key"] = "Unsupported sort key."
    if direction not in SORT_DIRECTIONS:
        errors["sort.direction"] = "Expected asc or desc."
    return {"key": "entity_id" if key not in SORT_KEYS else key, "direction": "asc" if direction not in SORT_DIRECTIONS else direction}


def _filter_node(col: Any, item: dict[str, Any]) -> Any:
    SearchNode = _search_node_type()
    kind = item["type"]
    if kind == "deck":
        deck = _manager_get(getattr(col, "decks", None), item["deckId"])
        if not isinstance(deck, dict) or not str(deck.get("name") or "").strip():
            raise SearchValidationError({"filters": "Deck is unavailable or was deleted."})
        return SearchNode(deck=str(deck["name"]))
    if kind == "note_type":
        model = _manager_get(getattr(col, "models", None), item["noteTypeId"])
        if not isinstance(model, dict) or not str(model.get("name") or "").strip():
            raise SearchValidationError({"filters": "Note type is unavailable or was deleted."})
        return SearchNode(note=str(model["name"]))
    if kind == "tag":
        return SearchNode(tag=item["tag"])
    if kind == "state":
        state_name = {
            "new": "CARD_STATE_NEW", "learning": "CARD_STATE_LEARN", "review": "CARD_STATE_REVIEW",
            "due": "CARD_STATE_DUE", "suspended": "CARD_STATE_SUSPENDED", "buried": "CARD_STATE_BURIED",
        }[item["state"]]
        return SearchNode(card_state=getattr(SearchNode.CardState, state_name))
    flag_name = ["FLAG_NONE", "FLAG_RED", "FLAG_ORANGE", "FLAG_GREEN", "FLAG_BLUE", "FLAG_PINK", "FLAG_TURQUOISE", "FLAG_PURPLE"][item["flag"]]
    return SearchNode(flag=getattr(SearchNode.Flag, flag_name))


def _search_node_type() -> Any:
    from anki.collection import SearchNode
    return SearchNode


def _manager_get(manager: Any, entity_id: int) -> Any:
    if manager is None:
        return None
    try:
        return manager.get(entity_id, default=False)
    except TypeError:
        return manager.get(entity_id)


def _note_type(note: Any) -> dict[str, Any]:
    value = note.note_type() if callable(getattr(note, "note_type", None)) else getattr(note, "_note_type", None)
    return value if isinstance(value, dict) else {}


def _note_items(note: Any) -> list[tuple[str, str]]:
    if callable(getattr(note, "items", None)):
        return [(str(name), str(value or "")) for name, value in note.items()]
    fields = list(getattr(note, "fields", []) or [])
    return [(str(index), str(value or "")) for index, value in enumerate(fields)]


def _primary_text(note: Any, note_type: dict[str, Any]) -> str:
    fields = list(getattr(note, "fields", []) or [])
    sort_index = note_type.get("sortf", 0)
    if isinstance(sort_index, bool) or not isinstance(sort_index, int) or sort_index < 0:
        sort_index = 0
    candidates = ([fields[sort_index]] if sort_index < len(fields) else []) + [value for index, value in enumerate(fields) if index != sort_index]
    for value in candidates:
        text = safe_plain_text(value)
        if text:
            return text
    return ""


def _note_cards(note: Any) -> list[Any]:
    if callable(getattr(note, "cards", None)):
        return list(note.cards())
    return []


def _tags(note: Any, *, limit: int) -> list[str]:
    values = [safe_plain_text(value, max_length=100) for value in list(getattr(note, "tags", []) or [])]
    return [value for value in values if value][:limit]


def _card_deck_id(card: Any) -> int:
    original = int(getattr(card, "odid", 0) or 0)
    return _coerce_entity_id(original or getattr(card, "did", 0))


def _deck_name(col: Any, deck_id: int) -> str:
    manager = getattr(col, "decks", None)
    if manager is not None and callable(getattr(manager, "name", None)):
        try:
            return str(manager.name(deck_id) or "")
        except Exception:
            pass
    deck = _manager_get(manager, deck_id)
    return str(deck.get("name") or "") if isinstance(deck, dict) else ""


def _deck_summary(col: Any, cards: list[Any], limit: int) -> list[dict[str, str]]:
    ids = sorted({_card_deck_id(card) for card in cards})
    return [{"deckId": str(deck_id), "deckName": _deck_name(col, deck_id)} for deck_id in ids[:limit]]


def _template_name(card: Any, note_type: dict[str, Any]) -> str:
    try:
        if callable(getattr(card, "template", None)):
            template = card.template()
        else:
            templates = note_type.get("tmpls") or []
            template = templates[int(getattr(card, "ord", 0))] if templates else {}
        return str(template.get("name") or "") if isinstance(template, dict) else ""
    except Exception:
        return ""


def _card_state(card: Any) -> str:
    queue = int(getattr(card, "queue", 0))
    card_type = int(getattr(card, "type", 0))
    if queue == -1:
        return "suspended"
    if queue in {-2, -3}:
        return "buried"
    if card_type == 0:
        return "new"
    if card_type in {1, 3}:
        return "learning"
    return "review"


def _strict_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _strict_id(value: object) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"[1-9]\d{0,18}", value):
        return None
    parsed = int(value)
    return parsed if parsed <= MAX_ID else None


def _coerce_entity_id(value: object) -> int:
    parsed = int(value)
    if parsed <= 0 or parsed > MAX_ID:
        raise RuntimeError("Anki returned an invalid entity ID.")
    return parsed


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "iframe", "object", "embed", "svg", "math"}:
            self._blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "iframe", "object", "embed", "svg", "math"} and self._blocked_depth:
            self._blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._blocked_depth:
            self.parts.append(data)
