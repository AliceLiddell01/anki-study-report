"""Canonical bounded Cards triage read projection.

The projection is additive and read-only. It composes the existing attention
collector, active card-level Signals, and exact Search card identities without
owning persistence, mutations, rendering, or a second search grammar.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import re
import time
from typing import Any

from .card_display_identity import unavailable_card_display_identity
from .exact_card_authority import reason_requires_profile_authority
from .inspection_profile_service import (
    evaluate_profiles_for_triage,
    load_exact_inspection_candidates,
)
from .metrics import ATTENTION_CARD_LIMIT, expand_deck_ids
from .triage_candidates import (
    collect_exact_learning_triage_candidate_with_status,
    collect_current_content_candidates,
    collect_learning_triage_candidates_with_status,
    content_source_status,
    source_status,
)
from .search_service import resolve_card_rows, safe_plain_text


TRIAGE_SCHEMA_VERSION = 4
TRIAGE_RECHECK_SCHEMA_VERSION = 1
AUTOMATIC_RESULT_LIMIT = ATTENTION_CARD_LIMIT
SEARCH_WORKSET_LIMIT = 200
SIGNAL_RESULT_LIMIT = 50
MAX_REASON_COUNT = 4
MAX_EVIDENCE_PER_REASON = 4
MAX_ID = 9_223_372_036_854_775_807
MAX_TIMESTAMP_MS = 9_007_199_254_740_991
DECIMAL_ID = re.compile(r"[1-9]\d{0,18}")
REASON_ID = re.compile(r"[a-z0-9:._-]{1,200}")

DATASETS = {"automatic", "search_workset"}
SOURCE_ORDER = {"search_workset": 0, "attention": 1, "signals": 2, "profile_checks": 3}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
REASON_ORDER = {
    "learning.leech": 0,
    "learning.repeated_again": 1,
    "learning.low_pass_rate": 2,
    "learning.slow_answer": 3,
    "content.required_text_missing": 10,
    "content.audio_missing": 11,
    "content.image_missing": 12,
    "content.text_too_short": 13,
    "content.required_group_missing": 14,
}
ISSUE_CODES = {
    "leech": "learning.leech",
    "repeated_again": "learning.repeated_again",
    "repeated again": "learning.repeated_again",
    "low_pass_rate": "learning.low_pass_rate",
    "low pass rate": "learning.low_pass_rate",
    "slow_answer": "learning.slow_answer",
    "slow answer": "learning.slow_answer",
}


class TriageValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid triage request.")
        self.field_errors = field_errors


def normalize_triage_query_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TriageValidationError({"request": "Expected a JSON object."})
    dataset = raw.get("dataset")
    allowed = {"schemaVersion", "dataset", "scope", "limit"}
    if dataset == "search_workset":
        allowed.add("cardIds")
    elif dataset == "automatic":
        allowed.add("contentCursor")
    errors = {str(key): "Unexpected field." for key in raw if key not in allowed}

    if raw.get("schemaVersion") != TRIAGE_SCHEMA_VERSION or isinstance(raw.get("schemaVersion"), bool):
        errors["schemaVersion"] = "Expected schemaVersion 4."
    if dataset not in DATASETS:
        errors["dataset"] = "Expected automatic or search_workset."

    scope = _normalize_scope(raw.get("scope"), errors)
    maximum = SEARCH_WORKSET_LIMIT if dataset == "search_workset" else AUTOMATIC_RESULT_LIMIT
    limit = raw.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= maximum:
        errors["limit"] = f"Expected an integer from 1 to {maximum}."
        limit = maximum

    card_ids: list[int] = []
    content_cursor: int | None = None
    if dataset == "search_workset":
        card_ids = _normalize_ids(
            raw.get("cardIds"),
            "cardIds",
            errors,
            maximum=SEARCH_WORKSET_LIMIT,
            allow_empty=False,
        )
        if "contentCursor" in raw:
            errors["contentCursor"] = "contentCursor is not valid for search_workset."
    else:
        if "cardIds" in raw:
            errors["cardIds"] = "cardIds is only valid for search_workset."
        if "contentCursor" not in raw:
            errors["contentCursor"] = "Required field."
        elif raw.get("contentCursor") is not None:
            value = raw.get("contentCursor")
            if not isinstance(value, str) or not DECIMAL_ID.fullmatch(value):
                errors["contentCursor"] = "Expected null or a positive signed-64 decimal string."
            elif int(value) > MAX_ID:
                errors["contentCursor"] = "Expected null or a positive signed-64 decimal string."
            else:
                content_cursor = int(value)

    if errors:
        raise TriageValidationError(errors)
    return {
        "schemaVersion": TRIAGE_SCHEMA_VERSION,
        "dataset": dataset,
        "scope": scope,
        "limit": limit,
        "cardIds": card_ids,
        "contentCursor": content_cursor,
    }


def normalize_triage_recheck_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TriageValidationError({"request": "Expected a JSON object."})
    expected = {"schemaVersion", "cardId", "expectedNoteId", "reasonIds", "scope"}
    errors = {str(key): "Unexpected field." for key in raw if key not in expected}
    for key in expected:
        if key not in raw:
            errors[key] = "Required field."
    if raw.get("schemaVersion") != TRIAGE_RECHECK_SCHEMA_VERSION or isinstance(raw.get("schemaVersion"), bool):
        errors["schemaVersion"] = "Expected schemaVersion 1."
    card_ids = _normalize_ids([raw.get("cardId")], "cardId", errors, maximum=1, allow_empty=False)
    note_ids = _normalize_ids([raw.get("expectedNoteId")], "expectedNoteId", errors, maximum=1, allow_empty=False)
    raw_reason_ids = raw.get("reasonIds")
    reason_ids: list[str] = []
    if not isinstance(raw_reason_ids, list) or not 1 <= len(raw_reason_ids) <= MAX_REASON_COUNT:
        errors["reasonIds"] = f"Expected 1 to {MAX_REASON_COUNT} stable reason IDs."
    else:
        for value in raw_reason_ids:
            if not isinstance(value, str) or not REASON_ID.fullmatch(value) or value in reason_ids:
                errors["reasonIds"] = "Reason IDs must be unique bounded canonical strings."
                continue
            reason_ids.append(value)
    scope = _normalize_scope(raw.get("scope"), errors)
    if errors:
        raise TriageValidationError(errors)
    return {
        "schemaVersion": TRIAGE_RECHECK_SCHEMA_VERSION,
        "cardId": card_ids[0],
        "expectedNoteId": note_ids[0],
        "reasonIds": reason_ids,
        "scope": scope,
    }


def execute_triage_recheck(
    col: Any,
    raw: object,
    *,
    signal_rows: list[dict[str, Any]] | None = None,
    signal_source_status: dict[str, Any] | None = None,
    profile_store_snapshot: dict[str, Any] | None = None,
    formatter_resolver: Any = None,
    generated_at_ms: int | None = None,
) -> dict[str, Any]:
    """Run the canonical Triage evaluators for one exact card only."""

    request = normalize_triage_recheck_request(raw)
    card_id = request["cardId"]
    snapshot = profile_store_snapshot or {
        "status": "unavailable",
        "revision": 0,
        "profiles": [],
        "errorCode": "profile_store_unavailable",
    }
    learning_rows, learning_status = collect_exact_learning_triage_candidate_with_status(
        col,
        card_id,
        request["scope"]["periodStartMs"],
        request["scope"]["periodEndMs"],
        request["scope"]["deckIds"],
    )
    signals = [
        row for row in (signal_rows if isinstance(signal_rows, list) else [])
        if isinstance(row, dict) and _positive_int(row.get("entityId")) == card_id
    ]
    _supported, signal_skipped = _supported_signal_ids(signals)
    signals_status = _signal_source_status(signal_source_status, signals, signal_skipped)

    try:
        resolution = (
            resolve_card_rows(col, [card_id])
            if formatter_resolver is None
            else resolve_card_rows(col, [card_id], formatter_resolver)
        )
        resolved_rows = resolution.get("items") if isinstance(resolution.get("items"), list) else []
        resolver_status = _source_status(
            "available" if resolved_rows else "empty",
            item_count=len(resolved_rows),
            skipped_count=0 if resolved_rows else 1,
            error_code=None if resolved_rows else "card_resolution_missing",
        )
    except Exception:
        resolved_rows = []
        resolver_status = _source_status("error", error_code="card_resolution_failed")

    resolved = resolved_rows[0] if resolved_rows else None
    current_note_id = _positive_int(resolved.get("noteId")) if isinstance(resolved, dict) else 0
    if resolved is None:
        entity_status = "missing"
    elif current_note_id != request["expectedNoteId"]:
        entity_status = "changed"
    else:
        entity_status = "available"

    if entity_status == "available" and request["scope"]["deckIds"]:
        try:
            allowed_decks = set(expand_deck_ids(col, request["scope"]["deckIds"]))
            current_deck_id = _positive_int(resolved.get("deckId")) if isinstance(resolved, dict) else 0
            if current_deck_id not in allowed_decks:
                entity_status = "unavailable"
        except Exception:
            entity_status = "unavailable"

    if entity_status == "available":
        exact_candidates = load_exact_inspection_candidates(col, [card_id])
        profile_result = evaluate_profiles_for_triage(
            col,
            exact_candidates["items"],
            snapshot,
            dataset="search_workset",
            exact_note_type_id=_positive_int(resolved.get("noteTypeId")),
            previous_reason_ids=tuple(request["reasonIds"]),
        )
        content_state = str(profile_result.get("contentChecks", {}).get("status") or "unavailable")
        needs_profile_authority = any(
            reason_requires_profile_authority(reason_id)
            for reason_id in request["reasonIds"]
        )
        if needs_profile_authority and content_state != "available":
            profile_result["sourceStatus"] = _source_status(
                "partial",
                item_count=_non_negative_int(profile_result.get("sourceStatus", {}).get("itemCount")),
                skipped_count=_non_negative_int(profile_result.get("sourceStatus", {}).get("skippedCount")),
                error_code="profile_authority_changed",
            )
    else:
        profile_result = {
            "reasons": [],
            "sourceStatus": _source_status(
                "unavailable" if entity_status == "unavailable" else "not_applicable",
                error_code="card_outside_scope" if entity_status == "unavailable" else None,
            ),
            "contentChecks": {
                "status": "unavailable" if entity_status == "unavailable" else "no_confirmed_profiles",
                "errorCode": "card_outside_scope" if entity_status == "unavailable" else None,
            },
        }

    projection = build_triage_projection(
        {
            "schemaVersion": TRIAGE_SCHEMA_VERSION,
            "dataset": "automatic",
            "scope": request["scope"],
            "limit": 1,
            "cardIds": [],
            "contentCursor": None,
        },
        attention_rows=learning_rows,
        learning_source_status=learning_status,
        content_candidate_source_status=content_source_status("not_applicable"),
        signal_rows=signals,
        signal_source_status=signals_status,
        resolved_card_rows=resolved_rows,
        resolver_source_status=resolver_status,
        profile_reasons=profile_result["reasons"],
        profile_source_status=profile_result["sourceStatus"],
        content_checks=_normalize_content_checks(profile_result["contentChecks"]),
        generated_at_ms=generated_at_ms,
    )
    item = next((value for value in projection["items"] if value["cardId"] == str(card_id)), None)
    if entity_status == "available" and item is None and isinstance(resolved, dict):
        item = _triage_item(
            card_id,
            dataset="automatic",
            resolved=resolved,
            attention=None,
            reason_map={},
        )

    source_statuses = {
        "learningCandidates": _normalize_source_status(learning_status),
        "signals": _normalize_source_status(signals_status),
        "searchResolver": _normalize_source_status(resolver_status),
        "profileChecks": _normalize_source_status(profile_result["sourceStatus"]),
    }
    failing = any(
        value["status"] in {"partial", "unavailable", "error"}
        for value in source_statuses.values()
    )
    status = "unavailable" if source_statuses["searchResolver"]["status"] in {"unavailable", "error"} else "partial" if failing else "available"
    return {
        "schemaVersion": TRIAGE_RECHECK_SCHEMA_VERSION,
        "cardId": str(card_id),
        "expectedNoteId": str(request["expectedNoteId"]),
        "status": status,
        "entityStatus": entity_status,
        "generatedAtMs": _generated_at_ms(generated_at_ms),
        "sourceStatus": source_statuses,
        "contentChecks": _normalize_content_checks(profile_result["contentChecks"]),
        "item": item if entity_status == "available" else None,
    }


def build_unavailable_triage_recheck(
    raw: object,
    *,
    generated_at_ms: int | None = None,
) -> dict[str, Any]:
    request = normalize_triage_recheck_request(raw)
    unavailable = _source_status("unavailable", error_code="collection_unavailable")
    return {
        "schemaVersion": TRIAGE_RECHECK_SCHEMA_VERSION,
        "cardId": str(request["cardId"]),
        "expectedNoteId": str(request["expectedNoteId"]),
        "status": "unavailable",
        "entityStatus": "unavailable",
        "generatedAtMs": _generated_at_ms(generated_at_ms),
        "sourceStatus": {
            "learningCandidates": unavailable,
            "signals": unavailable,
            "searchResolver": unavailable,
            "profileChecks": unavailable,
        },
        "contentChecks": _normalize_content_checks({
            "status": "unavailable",
            "errorCode": "collection_unavailable",
        }),
        "item": None,
    }


def execute_triage_query(
    col: Any,
    raw: object,
    *,
    signal_rows: list[dict[str, Any]] | None = None,
    signal_source_status: dict[str, Any] | None = None,
    profile_store_snapshot: dict[str, Any] | None = None,
    formatter_resolver: Any = None,
    generated_at_ms: int | None = None,
) -> dict[str, Any]:
    """Execute independent bounded source reads and project strict Triage v4."""

    request = normalize_triage_query_request(raw)
    scope = request["scope"]
    snapshot = profile_store_snapshot or {
        "status": "unavailable",
        "revision": 0,
        "profiles": [],
        "errorCode": "profile_store_unavailable",
    }

    if request["dataset"] == "automatic":
        learning_rows, learning_status = collect_learning_triage_candidates_with_status(
            col,
            scope["periodStartMs"],
            scope["periodEndMs"],
            scope["deckIds"],
            max_results=AUTOMATIC_RESULT_LIMIT,
        )
        content_result = collect_current_content_candidates(
            col,
            scope["deckIds"],
            request["contentCursor"],
            snapshot,
        )
        content_status = content_result["sourceStatus"]
        profile_result = {
            "reasons": content_result["reasons"],
            "sourceStatus": content_result["profileSourceStatus"],
            "contentChecks": content_result["contentChecks"],
        }
    else:
        learning_rows = []
        learning_status = source_status("not_applicable")
        content_status = content_source_status("not_applicable")
        profile_candidates = load_exact_inspection_candidates(col, request["cardIds"])["items"]
        profile_result = evaluate_profiles_for_triage(
            col,
            profile_candidates,
            snapshot,
            dataset=request["dataset"],
        )

    signals = signal_rows if isinstance(signal_rows, list) else []
    supported_signal_ids, signal_skipped = _supported_signal_ids(signals)
    signals_status = _signal_source_status(signal_source_status, signals, signal_skipped)

    if request["dataset"] == "search_workset":
        target_ids = list(request["cardIds"])
    else:
        target_ids = _dedupe_ints(
            [_positive_int(row.get("cardId")) for row in learning_rows if isinstance(row, dict)]
            + supported_signal_ids
            + [_positive_int(row.get("cardId")) for row in profile_result["reasons"]]
        )

    try:
        resolution = (
            resolve_card_rows(col, target_ids)
            if formatter_resolver is None
            else resolve_card_rows(col, target_ids, formatter_resolver)
        )
        resolved_rows = resolution.get("items") if isinstance(resolution.get("items"), list) else []
        missing = resolution.get("missingCardIds") if isinstance(resolution.get("missingCardIds"), list) else []
        resolver_status = _source_status(
            "available" if resolved_rows else "empty",
            item_count=len(resolved_rows),
            skipped_count=len(missing),
            error_code="card_resolution_missing" if missing else None,
        )
    except Exception:
        resolved_rows = []
        resolver_status = _source_status("error", error_code="card_resolution_failed")

    return build_triage_projection(
        request,
        attention_rows=learning_rows,
        learning_source_status=learning_status,
        content_candidate_source_status=content_status,
        signal_rows=signals,
        signal_source_status=signals_status,
        resolved_card_rows=resolved_rows,
        resolver_source_status=resolver_status,
        profile_reasons=profile_result["reasons"],
        profile_source_status=profile_result["sourceStatus"],
        content_checks=_normalize_content_checks(profile_result["contentChecks"]),
        generated_at_ms=generated_at_ms,
    )


def build_unavailable_triage_projection(
    raw: object,
    *,
    signal_rows: list[dict[str, Any]] | None = None,
    signal_source_status: dict[str, Any] | None = None,
    profile_store_snapshot: dict[str, Any] | None = None,
    generated_at_ms: int | None = None,
) -> dict[str, Any]:
    request = normalize_triage_query_request(raw)
    signals = signal_rows if isinstance(signal_rows, list) else []
    _ids, skipped = _supported_signal_ids(signals)
    automatic = request["dataset"] == "automatic"
    return build_triage_projection(
        request,
        attention_rows=[],
        learning_source_status=_source_status(
            "unavailable" if automatic else "not_applicable",
            error_code="collection_unavailable" if automatic else None,
        ),
        content_candidate_source_status=content_source_status(
            "unavailable" if automatic else "not_applicable",
            error_code="collection_unavailable" if automatic else None,
        ),
        signal_rows=signals,
        signal_source_status=_signal_source_status(signal_source_status, signals, skipped),
        resolved_card_rows=[],
        resolver_source_status=_source_status("unavailable", error_code="collection_unavailable"),
        profile_reasons=[],
        profile_source_status=_source_status("unavailable", error_code="collection_unavailable"),
        content_checks={
            "status": "unavailable",
            "confirmedProfileCount": 0,
            "needsReviewProfileCount": 0,
            "disabledProfileCount": 0,
            "suggestedProfileCount": 0,
            "scannedNoteCount": 0,
            "evaluatedNoteCount": 0,
            "failedCheckCount": 0,
            "skippedCount": 0,
            "truncated": False,
            "nextCursor": None,
            "errorCode": "collection_unavailable",
        },
        generated_at_ms=generated_at_ms,
    )


def build_triage_projection(
    request: dict[str, Any],
    *,
    attention_rows: list[dict[str, Any]],
    learning_source_status: dict[str, Any],
    content_candidate_source_status: dict[str, Any],
    signal_rows: list[dict[str, Any]],
    signal_source_status: dict[str, Any],
    resolved_card_rows: list[dict[str, Any]],
    resolver_source_status: dict[str, Any],
    profile_reasons: list[dict[str, Any]] | None = None,
    profile_source_status: dict[str, Any] | None = None,
    content_checks: dict[str, Any] | None = None,
    generated_at_ms: int | None = None,
) -> dict[str, Any]:
    reasons_by_card: dict[int, dict[str, dict[str, Any]]] = {}
    attention_by_card: dict[int, dict[str, Any]] = {}

    for row in attention_rows:
        if not isinstance(row, dict):
            continue
        card_id = _positive_int(row.get("cardId"))
        if card_id <= 0:
            continue
        attention_by_card.setdefault(card_id, row)
        for issue in row.get("issues") if isinstance(row.get("issues"), list) else []:
            reason = _attention_reason(issue, row, request["scope"])
            if reason is not None:
                _merge_reason(reasons_by_card, card_id, reason)

    for row in signal_rows:
        reason = _signal_reason(row)
        if reason is None:
            continue
        card_id, value = reason
        _merge_reason(reasons_by_card, card_id, value)

    for row in profile_reasons or []:
        if not isinstance(row, dict) or not isinstance(row.get("reason"), dict):
            continue
        card_id = _positive_int(row.get("cardId"))
        if card_id > 0:
            _merge_reason(reasons_by_card, card_id, row["reason"])

    resolved_by_card = {
        _positive_int(row.get("cardId")): row
        for row in resolved_card_rows
        if isinstance(row, dict) and _positive_int(row.get("cardId")) > 0
    }

    target_ids = list(request["cardIds"]) if request["dataset"] == "search_workset" else sorted(reasons_by_card)
    items = [
        _triage_item(
            card_id,
            dataset=request["dataset"],
            resolved=resolved_by_card.get(card_id),
            attention=attention_by_card.get(card_id),
            reason_map=reasons_by_card.get(card_id, {}),
        )
        for card_id in target_ids
    ]
    if request["dataset"] == "automatic":
        items.sort(key=_automatic_item_sort_key)

    total_count = len(items)
    limit = request["limit"]
    returned = items[:limit]
    source_status = {
        "learningCandidates": _normalize_source_status(learning_source_status),
        "contentCandidates": _normalize_content_source_status(content_candidate_source_status),
        "signals": _normalize_source_status(signal_source_status),
        "searchResolver": _normalize_source_status(resolver_source_status),
        "profileChecks": _normalize_source_status(profile_source_status),
    }
    return {
        "schemaVersion": TRIAGE_SCHEMA_VERSION,
        "dataset": request["dataset"],
        "status": _response_status(request["dataset"], source_status),
        "generatedAtMs": _generated_at_ms(generated_at_ms),
        "totalCount": total_count,
        "returnedCount": len(returned),
        "limit": limit,
        "truncated": total_count > len(returned),
        "sourceStatus": source_status,
        "contentChecks": _normalize_content_checks(content_checks),
        "items": returned,
    }


def _normalize_content_checks(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    truncated = bool(raw.get("truncated"))
    cursor = raw.get("nextCursor") if isinstance(raw.get("nextCursor"), str) else None
    return {
        "status": str(raw.get("status") or "unavailable"),
        "confirmedProfileCount": _non_negative_int(raw.get("confirmedProfileCount")),
        "needsReviewProfileCount": _non_negative_int(raw.get("needsReviewProfileCount")),
        "disabledProfileCount": _non_negative_int(raw.get("disabledProfileCount")),
        "suggestedProfileCount": _non_negative_int(raw.get("suggestedProfileCount")),
        "scannedNoteCount": _non_negative_int(raw.get("scannedNoteCount")),
        "evaluatedNoteCount": _non_negative_int(raw.get("evaluatedNoteCount")),
        "failedCheckCount": _non_negative_int(raw.get("failedCheckCount")),
        "skippedCount": _non_negative_int(raw.get("skippedCount")),
        "truncated": truncated,
        "nextCursor": cursor if truncated else None,
        "errorCode": raw.get("errorCode") if isinstance(raw.get("errorCode"), str) else None,
    }


def _normalize_scope(raw: object, errors: dict[str, str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        errors["scope"] = "Expected an object."
        return {"periodStartMs": 0, "periodEndMs": 1, "deckIds": []}
    expected = {"periodStartMs", "periodEndMs", "deckIds"}
    for key in raw:
        if key not in expected:
            errors[f"scope.{key}"] = "Unexpected field."
    for key in expected:
        if key not in raw:
            errors[f"scope.{key}"] = "Required field."
    start = _timestamp(raw.get("periodStartMs"))
    end = _timestamp(raw.get("periodEndMs"))
    if start is None:
        errors["scope.periodStartMs"] = "Expected a non-negative safe integer timestamp."
        start = 0
    if end is None or end <= 0:
        errors["scope.periodEndMs"] = "Expected a positive safe integer timestamp."
        end = 1
    if end <= start:
        errors["scope.periodEndMs"] = "Expected periodEndMs greater than periodStartMs."
    deck_ids = _normalize_ids(raw.get("deckIds"), "scope.deckIds", errors, maximum=SEARCH_WORKSET_LIMIT, allow_empty=True)
    return {"periodStartMs": start, "periodEndMs": end, "deckIds": deck_ids}


def _normalize_ids(
    raw: object,
    field: str,
    errors: dict[str, str],
    *,
    maximum: int,
    allow_empty: bool,
) -> list[int]:
    if not isinstance(raw, list) or len(raw) > maximum or (not raw and not allow_empty):
        lower = 0 if allow_empty else 1
        errors[field] = f"Expected {lower} to {maximum} decimal ID strings."
        return []
    parsed: list[int] = []
    seen: set[int] = set()
    for item in raw:
        if not isinstance(item, str) or not DECIMAL_ID.fullmatch(item):
            errors[field] = "IDs must be positive decimal strings."
            continue
        value = int(item)
        if value > MAX_ID:
            errors[field] = "IDs must fit signed 64-bit values."
            continue
        if value not in seen:
            seen.add(value)
            parsed.append(value)
    return parsed


def _attention_source_status(raw: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    raw_status = value.get("status")
    if raw_status == "available":
        status = "available" if rows else "empty"
        error_code = None
    elif raw_status == "error":
        status = "error"
        error_code = "attention_source_failed"
    else:
        status = "unavailable"
        error_code = "attention_source_unavailable"
    return _source_status(
        status,
        item_count=len(rows),
        truncated=len(rows) >= AUTOMATIC_RESULT_LIMIT,
        error_code=error_code,
    )


def _signal_source_status(raw: object, rows: list[dict[str, Any]], skipped: int) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    raw_status = value.get("status")
    if raw_status in {"error", "unavailable"}:
        status = str(raw_status)
        error_code = str(value.get("errorCode") or "signal_store_unavailable")
    else:
        status = "available" if rows else "empty"
        error_code = None
    return _source_status(
        status,
        item_count=max(0, len(rows) - skipped),
        skipped_count=skipped,
        truncated=len(rows) >= SIGNAL_RESULT_LIMIT,
        error_code=error_code,
    )


def _source_status(
    status: str,
    *,
    item_count: int = 0,
    skipped_count: int = 0,
    truncated: bool = False,
    error_code: str | None = None,
) -> dict[str, Any]:
    return source_status(
        status,
        item_count=item_count,
        skipped_count=skipped_count,
        truncated=truncated,
        error_code=error_code,
    )


def _normalize_source_status(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return _source_status(
        str(raw.get("status") or "error"),
        item_count=_non_negative_int(raw.get("itemCount")),
        skipped_count=_non_negative_int(raw.get("skippedCount")),
        truncated=bool(raw.get("truncated")),
        error_code=raw.get("errorCode") if isinstance(raw.get("errorCode"), str) else None,
    )


def _normalize_content_source_status(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    truncated = bool(raw.get("truncated"))
    cursor = raw.get("nextCursor") if isinstance(raw.get("nextCursor"), str) else None
    result = _normalize_source_status(raw)
    result["scannedNoteCount"] = _non_negative_int(raw.get("scannedNoteCount"))
    result["nextCursor"] = cursor if truncated else None
    return result


def _supported_signal_ids(rows: list[dict[str, Any]]) -> tuple[list[int], int]:
    supported: list[int] = []
    skipped = 0
    for row in rows:
        reason = _signal_reason(row)
        if reason is None:
            skipped += 1
        else:
            supported.append(reason[0])
    return _dedupe_ints(supported), skipped


def _attention_reason(issue: object, row: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any] | None:
    normalized = str(issue or "").strip().lower().replace("-", "_")
    code = ISSUE_CODES.get(normalized)
    if code is None:
        return None
    priority = {
        "learning.leech": "high",
        "learning.repeated_again": "medium",
        "learning.low_pass_rate": "medium",
        "learning.slow_answer": "low",
    }[code]
    evidence: list[dict[str, Any]] = []
    start, end = scope["periodStartMs"], scope["periodEndMs"]
    if code == "learning.leech":
        lapses = _finite_non_negative(row.get("lapses"))
        if lapses is not None:
            evidence.append({"kind": "leech_state", "lapses": int(lapses)})
    elif code == "learning.repeated_again":
        again = _finite_non_negative(row.get("againCount"))
        if again is not None:
            evidence.append({"kind": "review_counts", "againCount": int(again), "periodStartMs": start, "periodEndMs": end})
    elif code == "learning.low_pass_rate":
        pass_rate = _finite_range(row.get("passRate"), 0.0, 1.0)
        if pass_rate is not None:
            evidence.append({"kind": "pass_rate", "passRate": pass_rate, "periodStartMs": start, "periodEndMs": end})
    elif code == "learning.slow_answer":
        seconds = _finite_non_negative(row.get("averageAnswerSeconds"))
        if seconds is not None:
            evidence.append({"kind": "answer_time", "averageAnswerSeconds": seconds, "periodStartMs": start, "periodEndMs": end})
    return {
        "reasonId": f"learning:{code}",
        "code": code,
        "family": "learning",
        "scope": "card",
        "priority": priority,
        "sources": ["attention"],
        "evidence": evidence,
        "detectedAtMs": _timestamp_from_text(row.get("lastReviewedAt")),
    }


def _signal_reason(row: object) -> tuple[int, dict[str, Any]] | None:
    if not isinstance(row, dict) or row.get("code") != "card.repeated_again" or row.get("entityType") != "card":
        return None
    card_id = _positive_int(row.get("entityId"))
    severity = row.get("severity")
    evidence = row.get("evidence")
    if card_id <= 0 or severity not in {"warning", "critical"} or not isinstance(evidence, dict):
        return None
    again = _finite_non_negative(evidence.get("againCount"))
    reviews = _finite_non_negative(evidence.get("reviewCount"))
    window = _finite_non_negative(evidence.get("windowDays"))
    detector_version = row.get("detectorVersion")
    if again is None or reviews is None or window is None or not isinstance(detector_version, str) or not detector_version:
        return None
    detected_at = max(
        _timestamp_from_text(evidence.get("lastReviewAt")) or 0,
        _timestamp_from_text(row.get("lastSeenAt")) or 0,
    ) or None
    return card_id, {
        "reasonId": "learning:learning.repeated_again",
        "code": "learning.repeated_again",
        "family": "learning",
        "scope": "card",
        "priority": "high" if severity == "critical" else "medium",
        "sources": ["signals"],
        "evidence": [{
            "kind": "signal_evidence",
            "severity": severity,
            "againCount": int(again),
            "reviewCount": int(reviews),
            "windowDays": int(window),
            "detectorVersion": detector_version[:40],
        }],
        "detectedAtMs": detected_at,
    }


def _merge_reason(
    reasons_by_card: dict[int, dict[str, dict[str, Any]]],
    card_id: int,
    candidate: dict[str, Any],
) -> None:
    key = candidate["reasonId"]
    reason_map = reasons_by_card.setdefault(card_id, {})
    current = reason_map.get(key)
    if current is None:
        reason_map[key] = {
            **candidate,
            "sources": _sorted_sources(candidate["sources"]),
            "evidence": _sorted_evidence(candidate["evidence"]),
        }
        return
    current["priority"] = _higher_priority(current["priority"], candidate["priority"])
    current["sources"] = _sorted_sources(current["sources"] + candidate["sources"])
    current["evidence"] = _sorted_evidence(current["evidence"] + candidate["evidence"])
    current["detectedAtMs"] = max(current.get("detectedAtMs") or 0, candidate.get("detectedAtMs") or 0) or None


def _triage_item(
    card_id: int,
    *,
    dataset: str,
    resolved: dict[str, Any] | None,
    attention: dict[str, Any] | None,
    reason_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reasons = sorted(reason_map.values(), key=_reason_sort_key)[:MAX_REASON_COUNT]
    priority = reasons[0]["priority"] if reasons else None
    primary_reason = reasons[0]["code"] if reasons else None
    summary = resolved if isinstance(resolved, dict) else {}
    fallback = attention if isinstance(attention, dict) else {}
    available = bool(summary)

    note_id = _decimal_string(summary.get("noteId")) or _decimal_string(fallback.get("noteId"))
    deck_id = _decimal_string(summary.get("deckId"))
    note_type_id = _decimal_string(summary.get("noteTypeId")) or _decimal_string(fallback.get("noteTypeId"))
    template_ordinal = summary.get("templateOrdinal") if _is_int(summary.get("templateOrdinal")) else None
    state = summary.get("state") if summary.get("state") in {"new", "learning", "review", "due", "suspended", "buried"} else None
    flag = summary.get("flag") if _is_int(summary.get("flag")) and 0 <= int(summary["flag"]) <= 7 else None
    sources = _sorted_sources(
        (["search_workset"] if dataset == "search_workset" else [])
        + [source for reason in reasons for source in reason["sources"]]
    )
    display = _resolved_display_identity(summary)
    return {
        "itemId": f"card:{card_id}",
        "availability": "available" if available else "missing",
        "cardId": str(card_id),
        "noteId": note_id,
        "deck": {
            "deckId": deck_id,
            "name": safe_plain_text(summary.get("deckName") or fallback.get("deckName") or "", max_length=200),
        },
        "noteType": {
            "noteTypeId": note_type_id,
            "name": safe_plain_text(summary.get("noteTypeName") or fallback.get("noteTypeName") or "", max_length=160),
        },
        "template": {
            "ordinal": template_ordinal,
            "name": safe_plain_text(summary.get("templateName") or fallback.get("cardTemplateName") or "", max_length=160),
        },
        **display,
        "priority": priority,
        "primaryReasonCode": primary_reason,
        "reasons": reasons,
        "sources": sources,
        "cardState": {
            "state": state,
            "suspended": state == "suspended" if state is not None else None,
            "buried": state == "buried" if state is not None else None,
            "flag": flag,
        },
        "inspect": {"mode": "cards", "cardId": str(card_id)} if available else None,
    }


def _resolved_display_identity(summary: dict[str, Any]) -> dict[str, object]:
    text = summary.get("displayText")
    source = summary.get("displaySource")
    status = summary.get("displayStatus")
    truncated = summary.get("displayTruncated")
    coherent = (
        isinstance(text, str)
        and len(text) <= 240
        and isinstance(truncated, bool)
        and (
            (status == "available" and source in {"browser_question", "reviewer_front"} and bool(text))
            or (status == "media_only" and source in {"browser_question", "reviewer_front"} and text == "" and truncated is False)
            or (status == "unavailable" and source == "none" and text == "" and truncated is False)
        )
    )
    if coherent:
        return {
            "displayText": text,
            "displaySource": source,
            "displayStatus": status,
            "displayTruncated": truncated,
        }
    return unavailable_card_display_identity().to_wire()


def _response_status(dataset: str, source_status: dict[str, dict[str, Any]]) -> str:
    failing = {
        key for key, value in source_status.items()
        if value["status"] in {"partial", "unavailable", "error"}
    }
    if dataset == "search_workset":
        if source_status["searchResolver"]["status"] in {"unavailable", "error"}:
            return "unavailable"
        return "partial" if failing else "available"

    candidate_keys = ("learningCandidates", "contentCandidates", "signals")
    trustworthy = any(
        source_status[key]["status"] in {"available", "empty", "partial"}
        for key in candidate_keys
    )
    if not trustworthy:
        return "unavailable"
    return "partial" if failing else "available"


def _reason_sort_key(reason: dict[str, Any]) -> tuple[Any, ...]:
    return (
        PRIORITY_ORDER[reason["priority"]],
        REASON_ORDER.get(reason["code"], 99),
        -(reason.get("detectedAtMs") or 0),
        reason["code"],
    )


def _automatic_item_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    reason_code = item.get("primaryReasonCode") or ""
    recency = item["reasons"][0].get("detectedAtMs") if item["reasons"] else None
    return (
        PRIORITY_ORDER.get(item.get("priority"), 99),
        REASON_ORDER.get(reason_code, 99),
        -(recency or 0),
        int(item["cardId"]),
    )


def _sorted_sources(values: list[str]) -> list[str]:
    return sorted({value for value in values if value in SOURCE_ORDER}, key=lambda value: SOURCE_ORDER[value])


def _sorted_evidence(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        key = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        unique.setdefault(key, value)
    kind_order = {"signal_evidence": 0, "leech_state": 1, "review_counts": 2, "pass_rate": 3, "answer_time": 4}
    return sorted(unique.values(), key=lambda value: (kind_order.get(str(value.get("kind")), 99), json.dumps(value, sort_keys=True)))[:MAX_EVIDENCE_PER_REASON]


def _higher_priority(left: str, right: str) -> str:
    return left if PRIORITY_ORDER[left] <= PRIORITY_ORDER[right] else right


def _timestamp(value: object) -> int | None:
    return int(value) if _is_int(value) and 0 <= int(value) <= MAX_TIMESTAMP_MS else None


def _timestamp_from_text(value: object) -> int | None:
    if not isinstance(value, str) or not value or len(value) > 40:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        result = int(moment.timestamp() * 1000)
        return result if 0 <= result <= MAX_TIMESTAMP_MS else None
    except (ValueError, OverflowError):
        return None


def _generated_at_ms(value: int | None) -> int:
    normalized = _timestamp(value)
    return normalized if normalized is not None else int(time.time() * 1000)


def _positive_int(value: object) -> int:
    if isinstance(value, str) and DECIMAL_ID.fullmatch(value):
        parsed = int(value)
    elif _is_int(value):
        parsed = int(value)
    else:
        return 0
    return parsed if 0 < parsed <= MAX_ID else 0


def _decimal_string(value: object) -> str | None:
    parsed = _positive_int(value)
    return str(parsed) if parsed else None


def _non_negative_int(value: object) -> int:
    return int(value) if _is_int(value) and int(value) >= 0 else 0


def _finite_non_negative(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number >= 0 else None


def _finite_range(value: object, minimum: float, maximum: float) -> float | None:
    number = _finite_non_negative(value)
    return number if number is not None and minimum <= number <= maximum else None


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _dedupe_ints(values: list[int]) -> list[int]:
    return list(dict.fromkeys(value for value in values if value > 0))
