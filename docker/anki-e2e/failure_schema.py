from __future__ import annotations

import json
from typing import Any, Mapping

from failure_entry import validate_failure
from failure_registry import (
    ALLOWED_PRODUCERS,
    ALL_PHASES,
    MAX_DOCUMENT_BYTES,
    MAX_SECONDARY,
    SCHEMA_VERSION,
    FailureProtocolError,
)
from failure_safety import optional_non_negative_int, safe_id, sanitize_summary

# Backward-compatible private names used by the store and focused tests.
_validate_failure = validate_failure
_optional_non_negative_int = optional_non_negative_int


def validate_document(document: Any) -> dict[str, Any]:
    fields = ("schemaVersion", "result", "producer", "primary", "secondary", "context", "cleanup")
    if not isinstance(document, dict) or tuple(document) != fields:
        raise FailureProtocolError("failure summary differs from schema v1 field order")
    if document["schemaVersion"] != SCHEMA_VERSION or document["result"] != "failure":
        raise FailureProtocolError("failure summary schemaVersion/result is invalid")
    producer = document["producer"]
    if producer not in ALLOWED_PRODUCERS:
        raise FailureProtocolError("failure summary producer is invalid")
    primary = validate_failure(document["primary"], producer=producer, secondary=False)
    secondary_value = document["secondary"]
    if not isinstance(secondary_value, list) or len(secondary_value) > MAX_SECONDARY:
        raise FailureProtocolError(f"secondary must contain at most {MAX_SECONDARY} failures")
    secondary_entries = [validate_failure(item, producer=producer, secondary=True) for item in secondary_value]
    identities = [failure_identity(item) for item in secondary_entries]
    if len(identities) != len(set(identities)):
        raise FailureProtocolError("secondary failures contain duplicates")
    context = document["context"]
    context_fields = ("lastSuccessfulPhaseId", "lastSuccessfulItemId", "activePhaseId", "activeItemId")
    if not isinstance(context, dict) or tuple(context) != context_fields:
        raise FailureProtocolError("context differs from schema v1")
    normalized_context = {key: safe_id(context[key], key) for key in context_fields}
    for key in ("lastSuccessfulPhaseId", "activePhaseId"):
        if normalized_context[key] is not None and normalized_context[key] not in ALL_PHASES:
            raise FailureProtocolError(f"unknown {key}: {normalized_context[key]}")
    cleanup = document["cleanup"]
    if not isinstance(cleanup, dict) or tuple(cleanup) != ("status", "failureCount"):
        raise FailureProtocolError("cleanup differs from schema v1")
    if cleanup["status"] not in {"not_started", "success", "failure", "partial"}:
        raise FailureProtocolError("cleanup.status is invalid")
    failure_count = optional_non_negative_int(cleanup["failureCount"], "cleanup.failureCount")
    assert failure_count is not None
    if failure_count != sum(1 for item in secondary_entries if item["category"] == "cleanup"):
        raise FailureProtocolError("cleanup.failureCount differs from secondary cleanup failures")
    normalized = {
        "schemaVersion": SCHEMA_VERSION,
        "result": "failure",
        "producer": producer,
        "primary": primary,
        "secondary": secondary_entries,
        "context": normalized_context,
        "cleanup": {"status": cleanup["status"], "failureCount": failure_count},
    }
    serialized = serialize_document(normalized, validate=False)
    if len(serialized.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise FailureProtocolError(f"failure summary exceeds {MAX_DOCUMENT_BYTES} UTF-8 bytes")
    return normalized


def serialize_document(document: dict[str, Any], *, validate: bool = True, pretty: bool = True) -> str:
    value = validate_document(document) if validate else document
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n"


def failure_identity(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (entry.get("failureCode"), entry.get("phaseId"), entry.get("itemId"), entry.get("summary"))
