"""Declarative formatter resolver and strict local API contract."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .card_display_formatter_store import (
    CARD_DISPLAY_FORMATTER_SCHEMA_VERSION,
    CardDisplayFormatterStore,
    CardDisplayFormatterValidationError,
    formatter_key,
    normalize_decimal_id,
    normalize_revision,
    normalize_template_ordinal,
    validate_card_display_formatter,
)


CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION = 1
STORE_STATUSES = frozenset({"empty", "available", "corrupt", "future_schema", "unavailable"})


@dataclass(frozen=True)
class CardDisplayFormatterResolver:
    """Immutable exact-template/default resolver built from one store snapshot."""

    _entries: Mapping[tuple[str, int | None], Mapping[str, Any]]

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "CardDisplayFormatterResolver":
        if not isinstance(snapshot, dict) or snapshot.get("status") not in {"empty", "available"}:
            return cls(MappingProxyType({}))
        entries: dict[tuple[str, int | None], Mapping[str, Any]] = {}
        raw_formatters = snapshot.get("formatters")
        if not isinstance(raw_formatters, list):
            return cls(MappingProxyType({}))
        try:
            for raw in raw_formatters:
                normalized = validate_card_display_formatter(raw)
                key = formatter_key(normalized)
                if key in entries:
                    return cls(MappingProxyType({}))
                entries[key] = MappingProxyType(deepcopy(normalized))
        except CardDisplayFormatterValidationError:
            return cls(MappingProxyType({}))
        return cls(MappingProxyType(entries))

    def resolve(self, note_type_id: object, template_ordinal: object) -> dict[str, Any] | None:
        try:
            normalized_id = normalize_decimal_id(str(note_type_id), "noteTypeId")
            normalized_ordinal = normalize_template_ordinal(template_ordinal, "templateOrdinal")
        except CardDisplayFormatterValidationError:
            return None
        exact = self._entries.get((normalized_id, normalized_ordinal))
        if exact is not None:
            return dict(exact) if exact["storedState"] == "enabled" else None
        default = self._entries.get((normalized_id, None))
        if default is None or default["storedState"] != "enabled":
            return None
        return dict(default)


def empty_formatter_resolver() -> CardDisplayFormatterResolver:
    return CardDisplayFormatterResolver(MappingProxyType({}))


def normalize_formatter_query_request(raw: object) -> dict[str, Any]:
    value = _strict_request(raw, {"schemaVersion"})
    _schema_version(value)
    return {"schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION}


def normalize_formatter_validate_request(raw: object) -> dict[str, Any]:
    value = _strict_request(raw, {"schemaVersion", "formatter"})
    _schema_version(value)
    formatter = validate_card_display_formatter(value.get("formatter"))
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION,
        "formatter": formatter,
    }


def normalize_formatter_update_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CardDisplayFormatterValidationError({"request": "Expected a JSON object."})
    action = raw.get("action")
    if action == "save":
        expected = {"schemaVersion", "action", "expectedRevision", "formatter"}
    elif action == "delete":
        expected = {
            "schemaVersion",
            "action",
            "expectedRevision",
            "noteTypeId",
            "templateOrdinal",
        }
    else:
        expected = {"schemaVersion", "action", "expectedRevision"}
    value = _strict_request(raw, expected)
    _schema_version(value)
    errors: dict[str, str] = {}
    try:
        expected_revision = normalize_revision(value.get("expectedRevision"), "expectedRevision")
    except CardDisplayFormatterValidationError as error:
        errors.update(error.field_errors)
        expected_revision = 0
    result: dict[str, Any] = {
        "schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION,
        "action": action,
        "expectedRevision": expected_revision,
    }
    if action == "save":
        try:
            result["formatter"] = validate_card_display_formatter(value.get("formatter"))
        except CardDisplayFormatterValidationError as error:
            errors.update(error.field_errors)
    elif action == "delete":
        try:
            result["noteTypeId"] = normalize_decimal_id(value.get("noteTypeId"), "noteTypeId")
        except CardDisplayFormatterValidationError as error:
            errors.update(error.field_errors)
        try:
            result["templateOrdinal"] = normalize_template_ordinal(
                value.get("templateOrdinal"), "templateOrdinal"
            )
        except CardDisplayFormatterValidationError as error:
            errors.update(error.field_errors)
    else:
        errors["action"] = "Expected save or delete."
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return result


def execute_formatter_query(raw: object, snapshot: dict[str, Any]) -> dict[str, Any]:
    normalize_formatter_query_request(raw)
    return public_store_snapshot(snapshot)


def execute_formatter_validate(raw: object) -> dict[str, Any]:
    request = normalize_formatter_validate_request(raw)
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION,
        "valid": True,
        "formatter": deepcopy(request["formatter"]),
        "fieldErrors": {},
    }


def apply_formatter_update(
    store: CardDisplayFormatterStore,
    raw: object,
) -> dict[str, Any]:
    request = normalize_formatter_update_request(raw)
    if request["action"] == "save":
        snapshot = store.save_formatter(
            request["formatter"], expected_revision=request["expectedRevision"]
        )
        key = formatter_key(request["formatter"])
    else:
        snapshot = store.delete_formatter(
            request["noteTypeId"],
            request["templateOrdinal"],
            expected_revision=request["expectedRevision"],
        )
        key = (request["noteTypeId"], request["templateOrdinal"])
    formatter = next(
        (item for item in snapshot["formatters"] if formatter_key(item) == key),
        None,
    )
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION,
        "action": request["action"],
        "store": public_store_snapshot(snapshot),
        "formatter": deepcopy(formatter) if formatter is not None else None,
    }


def public_store_snapshot(snapshot: object) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        snapshot = {}
    status = snapshot.get("status")
    if status not in STORE_STATUSES:
        status = "unavailable"
    revision = snapshot.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        revision = 0
    raw_formatters = snapshot.get("formatters")
    formatters = (
        deepcopy(raw_formatters)
        if status in {"empty", "available"} and isinstance(raw_formatters, list)
        else []
    )
    error_code = snapshot.get("errorCode")
    if error_code is not None and not isinstance(error_code, str):
        error_code = "store_unavailable"
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION,
        "status": status,
        "revision": revision,
        "formatters": formatters,
        "errorCode": error_code,
        "quarantined": bool(snapshot.get("quarantined", False)),
    }


def _strict_request(raw: object, expected: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CardDisplayFormatterValidationError({"request": "Expected a JSON object."})
    errors: dict[str, str] = {}
    for key in raw:
        if key not in expected:
            errors[str(key)] = "Unexpected field."
    for key in expected:
        if key not in raw:
            errors[key] = "Required field."
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return raw


def _schema_version(value: dict[str, Any]) -> None:
    if (
        value.get("schemaVersion") != CARD_DISPLAY_FORMATTER_API_SCHEMA_VERSION
        or isinstance(value.get("schemaVersion"), bool)
    ):
        raise CardDisplayFormatterValidationError(
            {"schemaVersion": "Expected schemaVersion 1."}
        )
