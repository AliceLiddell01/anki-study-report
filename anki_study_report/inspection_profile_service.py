"""Note-type structures, suggestions, lifecycle, and declarative profile checks."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
import hashlib
import json
import re
from typing import Any

from .exact_card_authority import scope_exact_card_profile
from .inspection_profile_store import (
    CHECK_KINDS,
    INSPECTION_PROFILE_SCHEMA_VERSION,
    InspectionProfileStore,
    InspectionProfileValidationError,
    MAX_PROFILES,
    MAX_SIGNED_ID,
    normalize_decimal_id,
    normalize_revision,
    utc_now,
    validate_inspection_profile,
)
from .note_intelligence import analyze_note_type, detect_field_role, safe_plain_text


INSPECTION_API_SCHEMA_VERSION = 1
CATALOG_LIMIT = 500
CATALOG_ID_LIMIT = 200
PREVIEW_CARD_LIMIT = 20
MAX_STRUCTURE_FIELDS = 64
MAX_STRUCTURE_TEMPLATES = 32
MAX_STRUCTURE_REFERENCES = 64
MAX_FAILURES_PER_NOTE = 32
MAX_REASON_EVIDENCE_FIELDS = 16

EFFECTIVE_STATES = {"not_configured", "suggested", "confirmed", "needs_review", "disabled"}
STRUCTURE_KINDS = {"standard", "cloze"}
CONTENT_STATUS_VALUES = {
    "available",
    "no_confirmed_profiles",
    "profiles_need_review",
    "disabled",
    "partial",
    "unavailable",
}
STATE_REASON_CODES = {
    "field_added",
    "field_removed",
    "field_changed",
    "template_field_usage_changed",
    "note_type_missing",
    "fingerprint_mismatch",
    "unsupported_profile",
}

CONTENT_REASON_CODES = {
    "non_empty": "content.required_text_missing",
    "contains_audio": "content.audio_missing",
    "contains_image": "content.image_missing",
    "min_text_length": "content.text_too_short",
    "one_of_roles_non_empty": "content.required_group_missing",
    "all_roles_non_empty": "content.required_group_missing",
}

ROLE_ALIASES = {"partOfSpeech": "part_of_speech", "kanjiGif": "image"}
STANDARD_ROLES = {
    "term",
    "reading",
    "meaning",
    "example",
    "audio",
    "image",
    "part_of_speech",
    "pitch",
    "question",
    "answer",
    "explanation",
    "code",
}

TEMPLATE_FIELD_RE = re.compile(r"{{\s*([#^/]?)(?:[^{}:]+:)*([^{}:]+?)\s*}}")
AUDIO_RE = re.compile(r"\[sound:[^\]\r\n]{1,500}\]", re.IGNORECASE)
IMAGE_RE = re.compile(r"<img\b[^>]{0,2000}\bsrc\s*=", re.IGNORECASE)
SPECIAL_TEMPLATE_FIELDS = {
    "FrontSide",
    "Tags",
    "Type",
    "Deck",
    "Subdeck",
    "CardFlag",
    "Card",
}


def normalize_inspection_query_request(raw: object) -> dict[str, Any]:
    errors: dict[str, str] = {}
    value = _strict_request(raw, {"schemaVersion", "noteTypeIds", "limit"}, errors)
    _schema_version(value, errors)
    note_type_ids = _decimal_id_array(
        value.get("noteTypeIds"),
        "noteTypeIds",
        errors,
        maximum=CATALOG_ID_LIMIT,
        allow_empty=True,
    )
    limit = _bounded_int(value.get("limit"), 1, CATALOG_LIMIT, "limit", errors)
    _raise_request_errors(errors)
    return {"schemaVersion": INSPECTION_API_SCHEMA_VERSION, "noteTypeIds": note_type_ids, "limit": limit}


def normalize_inspection_validate_request(raw: object) -> dict[str, Any]:
    errors: dict[str, str] = {}
    schema_version = raw.get("schemaVersion") if isinstance(raw, dict) else None
    expected = {"schemaVersion", "profile", "cardIds"} if schema_version == 1 else {
        "schemaVersion", "profile", "preview"
    }
    value = _strict_request(raw, expected, errors)
    if schema_version not in {1, 2} or isinstance(schema_version, bool):
        errors["schemaVersion"] = "Expected schemaVersion 1 or 2."
    try:
        profile = validate_inspection_profile(value.get("profile"))
    except InspectionProfileValidationError as error:
        errors.update(error.field_errors)
        profile = None
    card_ids: list[int] = []
    preview_mode = "exact"
    preview_limit = 0
    if schema_version == 1:
        card_ids = _decimal_id_array(
            value.get("cardIds"),
            "cardIds",
            errors,
            maximum=PREVIEW_CARD_LIMIT,
            allow_empty=True,
        )
    else:
        preview = value.get("preview")
        if not isinstance(preview, dict):
            errors["preview"] = "Expected an object."
        else:
            for key in preview:
                if key not in {"mode", "limit"}:
                    errors[f"preview.{key}"] = "Unexpected field."
            if preview.get("mode") != "sample":
                errors["preview.mode"] = "Expected sample."
            preview_limit = _bounded_int(
                preview.get("limit"), 1, PREVIEW_CARD_LIMIT, "preview.limit", errors
            )
            preview_mode = "sample"
    _raise_request_errors(errors)
    return {
        "schemaVersion": schema_version,
        "profile": profile,
        "cardIds": card_ids,
        "previewMode": preview_mode,
        "previewLimit": preview_limit,
    }


def normalize_inspection_update_request(raw: object) -> dict[str, Any]:
    errors: dict[str, str] = {}
    if not isinstance(raw, dict):
        raise InspectionProfileValidationError({"request": "Expected a JSON object."})
    action = raw.get("action")
    if action == "save":
        expected = {"schemaVersion", "action", "expectedRevision", "targetState", "profile"}
    elif action in {"disable", "delete"}:
        expected = {"schemaVersion", "action", "expectedRevision", "noteTypeId"}
    else:
        expected = {"schemaVersion", "action", "expectedRevision"}
        errors["action"] = "Expected save, disable, or delete."
    value = _strict_request(raw, expected, errors)
    _schema_version(value, errors)
    try:
        expected_revision = normalize_revision(value.get("expectedRevision"), "expectedRevision")
    except InspectionProfileValidationError as error:
        errors.update(error.field_errors)
        expected_revision = 0
    result: dict[str, Any] = {
        "schemaVersion": INSPECTION_API_SCHEMA_VERSION,
        "action": action,
        "expectedRevision": expected_revision,
    }
    if action == "save":
        target_state = value.get("targetState")
        if target_state not in {"suggested", "confirmed"}:
            errors["targetState"] = "Expected suggested or confirmed."
        try:
            profile = validate_inspection_profile(value.get("profile"))
            if profile["storedState"] != target_state:
                errors["profile.storedState"] = "storedState must match targetState."
        except InspectionProfileValidationError as error:
            errors.update(error.field_errors)
            profile = None
        result.update({"targetState": target_state, "profile": profile})
    elif action in {"disable", "delete"}:
        try:
            result["noteTypeId"] = normalize_decimal_id(value.get("noteTypeId"), "noteTypeId")
        except InspectionProfileValidationError as error:
            errors.update(error.field_errors)
    _raise_request_errors(errors)
    return result


def execute_inspection_query(
    col: Any,
    raw: object,
    store_snapshot: dict[str, Any],
) -> dict[str, Any]:
    request = normalize_inspection_query_request(raw)
    catalog = read_note_type_structures(col, request["noteTypeIds"], limit=request["limit"])
    profiles = {
        profile["noteTypeId"]: profile
        for profile in store_snapshot.get("profiles", [])
        if isinstance(profile, dict) and isinstance(profile.get("noteTypeId"), str)
    }
    items = []
    for structure in catalog["items"]:
        profile = profiles.get(structure["noteTypeId"])
        lifecycle = effective_profile_state(profile, structure)
        items.append(
            {
                "structure": structure,
                "effectiveState": lifecycle["state"],
                "stateReason": lifecycle["reason"],
                "authoritative": lifecycle["authoritative"],
                "storedProfile": deepcopy(profile) if profile is not None else None,
                "suggestion": suggest_inspection_profile(structure),
            }
        )
    store_status = _public_store_status(store_snapshot)
    response_status = "unavailable" if catalog["status"] == "unavailable" else (
        "partial"
        if catalog["status"] == "partial" or store_status["status"] in {"corrupt", "future_schema", "unavailable"}
        else "available"
    )
    return {
        "schemaVersion": INSPECTION_API_SCHEMA_VERSION,
        "status": response_status,
        "store": store_status,
        "totalCount": catalog["totalCount"],
        "returnedCount": len(items),
        "limit": request["limit"],
        "truncated": catalog["truncated"],
        "skippedCount": catalog["skippedCount"],
        "items": items,
    }


def execute_inspection_validate(col: Any, raw: object) -> dict[str, Any]:
    request = normalize_inspection_validate_request(raw)
    profile = request["profile"]
    structure = structure_for_note_type(col, profile["noteTypeId"])
    lifecycle = effective_profile_state(profile, structure)
    errors = profile_structure_errors(profile, structure, require_checks=profile["storedState"] == "confirmed")
    if request["previewMode"] == "sample":
        candidates = load_sample_inspection_candidates(
            col, int(profile["noteTypeId"]), request["previewLimit"]
        )
    else:
        candidates = load_exact_inspection_candidates(col, request["cardIds"])
    preview_items: list[dict[str, Any]] = []
    if not errors and structure is not None:
        matching = [item for item in candidates["items"] if item["noteTypeId"] == int(profile["noteTypeId"])]
        for candidate in matching:
            failures = evaluate_inspection_profile(
                profile,
                structure,
                candidate,
                profile_revision=0,
            )
            preview_items.append(
                {
                    "cardId": str(candidate["cardId"]),
                    "noteId": str(candidate["noteId"]),
                    "failureCount": len(failures),
                    "failures": failures,
                }
            )
    return {
        "schemaVersion": request["schemaVersion"],
        "valid": not errors,
        "effectiveState": lifecycle["state"],
        "stateReason": lifecycle["reason"],
        "fieldErrors": errors,
        "preview": {
            "status": (
                "available"
                if not errors and (request["previewMode"] == "exact" or candidates["items"])
                else "unavailable"
            ),
            "requestedCount": (
                request["previewLimit"]
                if request["previewMode"] == "sample"
                else len(request["cardIds"])
            ),
            "evaluatedCount": len(preview_items),
            "missingCardIds": [str(value) for value in candidates["missingCardIds"]],
            "failureCount": sum(item["failureCount"] for item in preview_items),
            "truncated": bool(candidates.get("truncated", False)),
            "items": preview_items,
        },
    }


def prepare_inspection_update(col: Any, raw: object) -> dict[str, Any]:
    request = normalize_inspection_update_request(raw)
    if request["action"] != "save":
        return request
    profile = deepcopy(request["profile"])
    structure = structure_for_note_type(col, profile["noteTypeId"])
    errors = profile_structure_errors(
        profile,
        structure,
        require_checks=request["targetState"] == "confirmed",
    )
    if errors:
        raise InspectionProfileValidationError(errors)
    assert structure is not None
    now = utc_now()
    profile["noteTypeName"] = structure["name"]
    profile["storedState"] = request["targetState"]
    profile["updatedAt"] = now
    profile["confirmedAt"] = now if request["targetState"] == "confirmed" else None
    request["profile"] = validate_inspection_profile(profile)
    return request


def apply_inspection_update(store: InspectionProfileStore, prepared: dict[str, Any]) -> dict[str, Any]:
    action = prepared["action"]
    expected = prepared["expectedRevision"]
    if action == "save":
        snapshot = store.save_profile(prepared["profile"], expected_revision=expected)
    elif action == "disable":
        snapshot = store.disable_profile(
            prepared["noteTypeId"],
            expected_revision=expected,
            updated_at=utc_now(),
        )
    else:
        snapshot = store.delete_profile(prepared["noteTypeId"], expected_revision=expected)
    note_type_id = prepared.get("profile", {}).get("noteTypeId") if action == "save" else prepared.get("noteTypeId")
    profile = next((item for item in snapshot["profiles"] if item["noteTypeId"] == note_type_id), None)
    return {
        "schemaVersion": INSPECTION_API_SCHEMA_VERSION,
        "action": action,
        "store": _public_store_status(snapshot),
        "profile": deepcopy(profile) if profile is not None else None,
    }


def read_note_type_structures(
    col: Any,
    note_type_ids: Iterable[int] | None = None,
    *,
    limit: int = CATALOG_LIMIT,
) -> dict[str, Any]:
    if col is None or getattr(col, "models", None) is None:
        return {"status": "unavailable", "items": [], "totalCount": 0, "skippedCount": 0, "truncated": False}
    wanted = {int(value) for value in note_type_ids or [] if 0 < int(value) <= MAX_SIGNED_ID}
    try:
        raw_models = col.models.all()
    except Exception:
        return {"status": "unavailable", "items": [], "totalCount": 0, "skippedCount": 0, "truncated": False}
    if isinstance(raw_models, dict):
        raw_models = list(raw_models.values())
    models = [model for model in raw_models if isinstance(model, dict)] if isinstance(raw_models, list) else []
    if wanted:
        models = [model for model in models if _positive_int(model.get("id") or model.get("mid")) in wanted]
    structures: list[dict[str, Any]] = []
    skipped = 0
    for model in models:
        try:
            structures.append(build_note_type_structure(model))
        except (TypeError, ValueError):
            skipped += 1
    structures.sort(key=lambda item: (item["name"].casefold(), int(item["noteTypeId"])))
    total = len(structures)
    bounded_limit = max(1, min(CATALOG_LIMIT, int(limit)))
    items = structures[:bounded_limit]
    status = "partial" if skipped else "available"
    return {
        "status": status,
        "items": items,
        "totalCount": total,
        "skippedCount": skipped,
        "truncated": total > len(items),
    }


def structure_for_note_type(col: Any, note_type_id: object) -> dict[str, Any] | None:
    target = int(normalize_decimal_id(str(note_type_id), "noteTypeId"))
    catalog = read_note_type_structures(col, [target], limit=1)
    return catalog["items"][0] if catalog["items"] else None


def build_note_type_structure(model: object) -> dict[str, Any]:
    if not isinstance(model, dict):
        raise TypeError("note type must be an object")
    note_type_id = _positive_int(model.get("id") or model.get("mid"))
    name = _bounded_plain_text(model.get("name"), 160)
    raw_fields = model.get("flds")
    raw_templates = model.get("tmpls")
    if note_type_id <= 0 or not name or not isinstance(raw_fields, list) or not isinstance(raw_templates, list):
        raise ValueError("malformed note type")
    if len(raw_fields) > MAX_STRUCTURE_FIELDS or len(raw_templates) > MAX_STRUCTURE_TEMPLATES:
        raise ValueError("note type exceeds structural bounds")
    fields: list[dict[str, Any]] = []
    names: set[str] = set()
    ordinals: set[int] = set()
    for index, raw in enumerate(raw_fields):
        if not isinstance(raw, dict):
            raise ValueError("malformed field")
        ordinal = _ordinal(raw.get("ord"), index, maximum=63)
        field_name = _bounded_plain_text(raw.get("name"), 160)
        if not field_name or field_name in names or ordinal in ordinals:
            raise ValueError("duplicate or invalid field")
        names.add(field_name)
        ordinals.add(ordinal)
        fields.append({"ordinal": ordinal, "name": field_name})
    fields.sort(key=lambda item: item["ordinal"])
    templates: list[dict[str, Any]] = []
    template_ordinals: set[int] = set()
    for index, raw in enumerate(raw_templates):
        if not isinstance(raw, dict):
            raise ValueError("malformed template")
        ordinal = _ordinal(raw.get("ord"), index, maximum=31)
        template_name = _bounded_plain_text(raw.get("name") or f"Card {index + 1}", 160)
        if not template_name or ordinal in template_ordinals:
            raise ValueError("duplicate or invalid template")
        template_ordinals.add(ordinal)
        front_fields = _template_references(raw.get("qfmt"), names)
        back_fields = _template_references(raw.get("afmt"), names)
        templates.append(
            {
                "ordinal": ordinal,
                "name": template_name,
                "frontFields": front_fields,
                "backFields": back_fields,
            }
        )
    templates.sort(key=lambda item: item["ordinal"])
    kind = "cloze" if _is_cloze_model(model) else "standard"
    canonical = {
        "noteTypeId": str(note_type_id),
        "fields": fields,
        "templates": templates,
        "kind": kind,
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "noteTypeId": str(note_type_id),
        "name": name,
        "kind": kind,
        "fields": fields,
        "templates": templates,
        "fingerprint": {"algorithm": "sha256", "value": fingerprint},
    }


def suggest_inspection_profile(structure: dict[str, Any]) -> dict[str, Any]:
    model = {
        "id": int(structure["noteTypeId"]),
        "name": structure["name"],
        "flds": [{"name": item["name"], "ord": item["ordinal"]} for item in structure["fields"]],
        "tmpls": [
            {
                "name": item["name"],
                "ord": item["ordinal"],
                "qfmt": " ".join(f"{{{{{name}}}}}" for name in item["frontFields"]),
                "afmt": " ".join(f"{{{{{name}}}}}" for name in item["backFields"]),
            }
            for item in structure["templates"]
        ],
        "type": 1 if structure["kind"] == "cloze" else 0,
    }
    analysis = analyze_note_type(model, None)
    mappings: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    roles_seen: set[str] = set()
    by_index = {index: item for index, item in enumerate(structure["fields"])}
    for field in analysis.get("fields", []):
        if not isinstance(field, dict):
            continue
        ordinal = int(field.get("index") or 0)
        structural = by_index.get(ordinal)
        if structural is None:
            continue
        raw_role = str(field.get("detectedRole") or "unknown")
        role = ROLE_ALIASES.get(raw_role, raw_role)
        confidence = _bounded_confidence(field.get("confidence"))
        if role == "unknown" or role not in STANDARD_ROLES or role in roles_seen:
            unresolved.append({"ordinal": structural["ordinal"], "name": structural["name"]})
            continue
        roles_seen.add(role)
        mappings.append(
            {
                "role": role,
                "fields": [{"ordinal": structural["ordinal"], "name": structural["name"]}],
                "confidence": confidence,
            }
        )
    kind = str(analysis.get("detectedKind") or "unknown")
    checks = _suggested_checks(kind, {item["role"] for item in mappings})
    warnings: list[str] = []
    if unresolved:
        warnings.append("unresolved_fields")
    if not checks:
        warnings.append("no_checks_suggested")
    return {
        "detectedKind": kind[:40],
        "confidence": _bounded_confidence(analysis.get("confidence")),
        "fieldMappings": mappings,
        "checks": checks,
        "warnings": warnings,
        "unresolvedFields": unresolved,
    }


def effective_profile_state(
    profile: dict[str, Any] | None,
    structure: dict[str, Any] | None,
) -> dict[str, Any]:
    if profile is None:
        return {"state": "not_configured", "reason": None, "authoritative": False}
    stored = profile.get("storedState")
    if stored == "disabled":
        return {"state": "disabled", "reason": None, "authoritative": False}
    if stored == "suggested":
        return {"state": "suggested", "reason": None, "authoritative": False}
    if stored != "confirmed":
        return {"state": "needs_review", "reason": "unsupported_profile", "authoritative": False}
    if structure is None:
        return {"state": "needs_review", "reason": "note_type_missing", "authoritative": False}
    errors = profile_structure_errors(profile, structure, require_checks=True)
    if errors:
        return {
            "state": "needs_review",
            "reason": _structure_reason(profile, structure),
            "authoritative": False,
        }
    return {"state": "confirmed", "reason": None, "authoritative": True}


def profile_structure_errors(
    profile: dict[str, Any],
    structure: dict[str, Any] | None,
    *,
    require_checks: bool,
) -> dict[str, str]:
    if structure is None:
        return {"profile.noteTypeId": "The note type is missing."}
    errors: dict[str, str] = {}
    if profile["noteTypeId"] != structure["noteTypeId"]:
        errors["profile.noteTypeId"] = "The note type ID does not match."
    if profile["noteTypeName"] != structure["name"]:
        errors["profile.noteTypeName"] = "The note type name changed."
    if profile["expectedFingerprint"] != structure["fingerprint"]:
        errors["profile.expectedFingerprint"] = "The note type fingerprint is stale."
    fields = {(item["ordinal"], item["name"]) for item in structure["fields"]}
    for mapping_index, mapping in enumerate(profile["fieldMappings"]):
        for ref_index, ref in enumerate(mapping["fields"]):
            if (ref["ordinal"], ref["name"]) not in fields:
                errors[f"profile.fieldMappings.{mapping_index}.fields.{ref_index}"] = "The exact field reference is unresolved."
    template_ordinals = {item["ordinal"] for item in structure["templates"]}
    for index, ordinal in enumerate(profile["appliesTo"]["templateOrdinals"]):
        if ordinal not in template_ordinals:
            errors[f"profile.appliesTo.templateOrdinals.{index}"] = "The template ordinal is unresolved."
    if require_checks and not profile["checks"]:
        errors["profile.checks"] = "Confirmed profiles require at least one check."
    return errors


def load_exact_inspection_candidates(col: Any, card_ids: list[int]) -> dict[str, Any]:
    ordered = list(dict.fromkeys(int(value) for value in card_ids if 0 < int(value) <= MAX_SIGNED_ID))
    if not ordered or col is None or getattr(col, "db", None) is None:
        return {"items": [], "missingCardIds": ordered}
    placeholders = ",".join("?" for _ in ordered)
    rows = col.db.all(
        f"""
        select c.id, c.nid, n.mid, c.ord, n.flds
        from cards c
        join notes n on n.id = c.nid
        where c.id in ({placeholders})
        """,
        *ordered,
    )
    by_card: dict[int, dict[str, Any]] = {}
    note_ids: list[int] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        card_id, note_id, note_type_id, template_ordinal, raw_fields = row[:5]
        card_int = _positive_int(card_id)
        note_int = _positive_int(note_id)
        model_int = _positive_int(note_type_id)
        if card_int <= 0 or note_int <= 0 or model_int <= 0:
            continue
        by_card[card_int] = {
            "cardId": card_int,
            "noteId": note_int,
            "noteTypeId": model_int,
            "templateOrdinal": _non_negative_int(template_ordinal),
            "rawFields": str(raw_fields or ""),
            "siblingCount": 1,
        }
        note_ids.append(note_int)
    sibling_counts = _sibling_counts(col, note_ids)
    for item in by_card.values():
        item["siblingCount"] = sibling_counts.get(item["noteId"], 1)
    return {
        "items": [by_card[value] for value in ordered if value in by_card],
        "missingCardIds": [value for value in ordered if value not in by_card],
    }


def load_sample_inspection_candidates(
    col: Any,
    note_type_id: int,
    limit: int,
) -> dict[str, Any]:
    """Load a bounded deterministic sample without exposing note values."""
    bounded_limit = max(1, min(PREVIEW_CARD_LIMIT, int(limit)))
    model_id = _positive_int(note_type_id)
    if model_id <= 0 or col is None or getattr(col, "db", None) is None:
        return {"items": [], "missingCardIds": [], "truncated": False}
    try:
        rows = col.db.all(
            """
            select c.id, c.nid, n.mid, c.ord, n.flds
            from cards c
            join notes n on n.id = c.nid
            where n.mid = ?
            order by c.id asc
            limit ?
            """,
            model_id,
            bounded_limit + 1,
        )
    except Exception:
        return {"items": [], "missingCardIds": [], "truncated": False}
    items: list[dict[str, Any]] = []
    for row in rows[:bounded_limit]:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        card_id, note_id, current_model_id, template_ordinal, raw_fields = row[:5]
        card_int = _positive_int(card_id)
        note_int = _positive_int(note_id)
        if card_int <= 0 or note_int <= 0 or _positive_int(current_model_id) != model_id:
            continue
        items.append({
            "cardId": card_int,
            "noteId": note_int,
            "noteTypeId": model_id,
            "templateOrdinal": _non_negative_int(template_ordinal),
            "rawFields": str(raw_fields or ""),
            "siblingCount": 1,
        })
    return {
        "items": attach_sibling_counts(col, items),
        "missingCardIds": [],
        "truncated": len(rows) > bounded_limit,
    }


def attach_sibling_counts(col: Any, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = _sibling_counts(col, [_positive_int(item.get("noteId")) for item in candidates])
    result = []
    for item in candidates:
        copy = dict(item)
        note_id = _positive_int(copy.get("noteId"))
        copy["siblingCount"] = counts.get(note_id, 1)
        result.append(copy)
    return result


def evaluate_inspection_profile(
    profile: dict[str, Any],
    structure: dict[str, Any],
    candidate: dict[str, Any],
    *,
    profile_revision: int,
) -> list[dict[str, Any]]:
    allowed_templates = profile["appliesTo"]["templateOrdinals"]
    template_ordinal = _non_negative_int(candidate.get("templateOrdinal"))
    if allowed_templates and template_ordinal not in allowed_templates:
        return []
    values = str(candidate.get("rawFields") or "").split("\x1f")
    mappings = {item["role"]: item["fields"] for item in profile["fieldMappings"]}
    failures: list[dict[str, Any]] = []
    for check in profile["checks"]:
        mapped = [ref for role in check["roles"] for ref in mappings.get(role, [])]
        role_values = {
            role: [
                (ref, values[ref["ordinal"]] if ref["ordinal"] < len(values) else "")
                for ref in mappings.get(role, [])
            ]
            for role in check["roles"]
        }
        failure = _evaluate_check(check, role_values)
        if failure is None:
            continue
        failures.append(
            {
                "profileId": profile["profileId"],
                "noteTypeId": profile["noteTypeId"],
                "checkId": check["checkId"],
                "checkKind": check["kind"],
                "scope": "note",
                "priority": check["priority"],
                "targetRoles": list(check["roles"]),
                "mappedFields": deepcopy(mapped[:MAX_REASON_EVIDENCE_FIELDS]),
                "evidence": {
                    "expectedCondition": failure["expectedCondition"],
                    "actualTextLength": failure.get("actualTextLength"),
                    "expectedTextLength": failure.get("expectedTextLength"),
                    "marker": failure.get("marker"),
                    "markerPresent": failure.get("markerPresent"),
                },
                "profileRevision": max(0, int(profile_revision)),
                "fingerprint": structure["fingerprint"]["value"],
                "affectedSiblingCount": max(1, _non_negative_int(candidate.get("siblingCount"))),
                "templateOrdinals": list(allowed_templates),
            }
        )
        if len(failures) >= MAX_FAILURES_PER_NOTE:
            break
    return failures


def evaluate_profiles_for_triage(
    col: Any,
    candidates: list[dict[str, Any]],
    store_snapshot: dict[str, Any],
    *,
    dataset: str,
    exact_note_type_id: int | None = None,
    previous_reason_ids: Iterable[str] = (),
) -> dict[str, Any]:
    exact_scope = None
    if exact_note_type_id is not None:
        exact_scope = scope_exact_card_profile(
            store_snapshot,
            note_type_id=exact_note_type_id,
            previous_reason_ids=previous_reason_ids,
        )
        if exact_scope.blocking_error_code is not None:
            return _triage_profile_result(
                "partial",
                "unavailable",
                error_code=exact_scope.blocking_error_code,
            )
        if exact_scope.profile is None:
            return _triage_profile_result("empty", "no_confirmed_profiles")

    store_status = str(store_snapshot.get("status") or "unavailable")
    if store_status in {"future_schema", "unavailable", "corrupt"}:
        source_state = "error" if store_status == "corrupt" else "unavailable"
        return _triage_profile_result(
            source_state,
            "unavailable",
            error_code=str(store_snapshot.get("errorCode") or "profile_store_unavailable"),
        )
    profiles = (
        [exact_scope.profile]
        if exact_scope is not None
        else [item for item in store_snapshot.get("profiles", []) if isinstance(item, dict)]
    )
    model_ids = {int(profile["noteTypeId"]) for profile in profiles}
    catalog = read_note_type_structures(col, model_ids, limit=MAX_PROFILES)
    structures = {item["noteTypeId"]: item for item in catalog["items"]}
    lifecycle = [effective_profile_state(profile, structures.get(profile["noteTypeId"])) for profile in profiles]
    confirmed_profiles = [
        profile
        for profile, state in zip(profiles, lifecycle)
        if state["state"] == "confirmed" and state["authoritative"]
    ]
    needs_review_count = sum(state["state"] == "needs_review" for state in lifecycle)
    disabled_count = sum(state["state"] == "disabled" for state in lifecycle)
    suggested_count = sum(state["state"] == "suggested" for state in lifecycle)
    if not confirmed_profiles:
        if needs_review_count:
            content_status = "profiles_need_review"
        elif profiles and disabled_count == len(profiles):
            content_status = "disabled"
        else:
            content_status = "no_confirmed_profiles"
        fail_closed = bool(
            exact_scope is not None
            and (needs_review_count or exact_scope.requires_profile_authority)
        )
        return _triage_profile_result(
            "partial" if fail_closed else "empty",
            content_status,
            error_code=(
                "profile_authority_changed"
                if exact_scope is not None and exact_scope.requires_profile_authority
                else None
            ),
            confirmed_count=0,
            needs_review_count=needs_review_count,
            disabled_count=disabled_count,
            suggested_count=suggested_count,
        )
    by_profile = {profile["noteTypeId"]: profile for profile in confirmed_profiles}
    candidates_with_counts = attach_sibling_counts(col, candidates)
    grouped: dict[int, list[dict[str, Any]]] = {}
    skipped = 0
    for candidate in candidates_with_counts:
        note_id = _positive_int(candidate.get("noteId"))
        if note_id <= 0:
            skipped += 1
            continue
        grouped.setdefault(note_id, []).append(candidate)
    reasons: list[dict[str, Any]] = []
    evaluated_notes = 0
    revision = _non_negative_int(store_snapshot.get("revision"))
    for note_id, note_candidates in grouped.items():
        profile = by_profile.get(str(_positive_int(note_candidates[0].get("noteTypeId"))))
        if profile is None:
            continue
        structure = structures.get(profile["noteTypeId"])
        if structure is None:
            skipped += 1
            continue
        applicable = [
            item
            for item in note_candidates
            if not profile["appliesTo"]["templateOrdinals"]
            or _non_negative_int(item.get("templateOrdinal")) in profile["appliesTo"]["templateOrdinals"]
        ]
        if not applicable:
            continue
        evaluated_notes += 1
        representative = applicable[0] if dataset == "search_workset" else min(applicable, key=lambda item: _positive_int(item.get("cardId")))
        failures = evaluate_inspection_profile(profile, structure, representative, profile_revision=revision)
        for failure in failures:
            reasons.append(
                {
                    "cardId": _positive_int(representative["cardId"]),
                    "noteId": note_id,
                    "reason": content_reason_from_failure(failure),
                }
            )
    content_status = "partial" if needs_review_count or catalog["status"] == "partial" or skipped else "available"
    source_status = "partial" if content_status == "partial" else ("available" if reasons else "empty")
    return _triage_profile_result(
        source_status,
        content_status,
        reasons=reasons,
        item_count=len(reasons),
        skipped_count=skipped,
        confirmed_count=len(confirmed_profiles),
        needs_review_count=needs_review_count,
        disabled_count=disabled_count,
        suggested_count=suggested_count,
        evaluated_note_count=evaluated_notes,
        failed_check_count=len(reasons),
    )


def content_reason_from_failure(failure: dict[str, Any]) -> dict[str, Any]:
    check_kind = failure["checkKind"]
    return {
        "reasonId": f"profile:{failure['profileId']}:check:{failure['checkId']}",
        "code": CONTENT_REASON_CODES[check_kind],
        "family": "content",
        "scope": "note",
        "priority": failure["priority"],
        "sources": ["profile_checks"],
        "evidence": [
            {
                "kind": "profile_check",
                "profileId": failure["profileId"],
                "checkId": failure["checkId"],
                "checkKind": check_kind,
                "roles": list(failure["targetRoles"]),
                "fields": deepcopy(failure["mappedFields"]),
                "expectedCondition": failure["evidence"]["expectedCondition"],
                "actualTextLength": failure["evidence"]["actualTextLength"],
                "expectedTextLength": failure["evidence"]["expectedTextLength"],
                "marker": failure["evidence"]["marker"],
                "markerPresent": failure["evidence"]["markerPresent"],
                "profileRevision": failure["profileRevision"],
                "fingerprint": failure["fingerprint"],
                "affectedSiblingCount": failure["affectedSiblingCount"],
                "templateOrdinals": list(failure["templateOrdinals"]),
            }
        ],
        "detectedAtMs": None,
    }


def _evaluate_check(
    check: dict[str, Any],
    role_values: dict[str, list[tuple[dict[str, Any], str]]],
) -> dict[str, Any] | None:
    kind = check["kind"]
    field_values = [item for role in check["roles"] for item in role_values.get(role, [])]
    texts = [safe_plain_text(value) for _ref, value in field_values]
    if kind == "non_empty":
        passed = any(texts) if check["mode"] == "any" else bool(texts) and all(texts)
        return None if passed else {
            "expectedCondition": f"{check['mode']}_non_empty",
            "actualTextLength": max((len(value) for value in texts), default=0),
        }
    if kind == "contains_audio":
        markers = [bool(AUDIO_RE.search(value)) for _ref, value in field_values]
        passed = any(markers) if check["mode"] == "any" else bool(markers) and all(markers)
        return None if passed else {
            "expectedCondition": f"{check['mode']}_contains_audio",
            "marker": "audio",
            "markerPresent": False,
        }
    if kind == "contains_image":
        markers = [bool(IMAGE_RE.search(value)) for _ref, value in field_values]
        passed = any(markers) if check["mode"] == "any" else bool(markers) and all(markers)
        return None if passed else {
            "expectedCondition": f"{check['mode']}_contains_image",
            "marker": "image",
            "markerPresent": False,
        }
    if kind == "min_text_length":
        lengths = [len(value) for value in texts]
        passed = any(value >= check["minLength"] for value in lengths) if check["mode"] == "any" else bool(lengths) and all(value >= check["minLength"] for value in lengths)
        return None if passed else {
            "expectedCondition": f"{check['mode']}_min_text_length",
            "actualTextLength": max(lengths, default=0),
            "expectedTextLength": check["minLength"],
        }
    role_has_text = {
        role: any(bool(safe_plain_text(value)) for _ref, value in role_values.get(role, []))
        for role in check["roles"]
    }
    if kind == "one_of_roles_non_empty":
        passed = any(role_has_text.values())
    else:
        passed = bool(role_has_text) and all(role_has_text.values())
    return None if passed else {"expectedCondition": kind}


def _suggested_checks(kind: str, roles: set[str]) -> list[dict[str, Any]]:
    desired: list[tuple[str, str, str]]
    if kind in {"japanese_vocab", "japanese_grammar"}:
        desired = [
            ("meaning", "non_empty", "high"),
            ("audio", "contains_audio", "medium"),
            ("example", "non_empty", "medium"),
            ("part_of_speech", "non_empty", "low"),
            ("image", "contains_image", "low"),
        ]
    elif kind == "programming":
        desired = [("question", "non_empty", "high"), ("answer", "non_empty", "high")]
    else:
        desired = [("question", "non_empty", "high"), ("answer", "non_empty", "high"), ("meaning", "non_empty", "medium")]
    return [
        {
            "checkId": f"{role.replace('_', '-')}-required",
            "kind": check_kind,
            "roles": [role],
            "mode": "any",
            "priority": priority,
        }
        for role, check_kind, priority in desired
        if role in roles
    ]


def _template_references(value: object, field_names: set[str]) -> list[str]:
    if not isinstance(value, str):
        raise ValueError("template source is missing")
    result: list[str] = []
    for match in TEMPLATE_FIELD_RE.finditer(value):
        name = match.group(2).strip()
        if name in SPECIAL_TEMPLATE_FIELDS:
            continue
        if name in field_names and name not in result:
            result.append(name)
        if len(result) > MAX_STRUCTURE_REFERENCES:
            raise ValueError("template references exceed bounds")
    return result


def _is_cloze_model(model: dict[str, Any]) -> bool:
    value = model.get("type")
    if isinstance(value, int) and not isinstance(value, bool):
        return value == 1
    return "cloze" in str(model.get("name") or "").casefold()


def _structure_reason(profile: dict[str, Any], structure: dict[str, Any]) -> str:
    current_by_ordinal = {item["ordinal"]: item["name"] for item in structure["fields"]}
    for mapping in profile["fieldMappings"]:
        for ref in mapping["fields"]:
            if ref["ordinal"] not in current_by_ordinal:
                return "field_removed"
            if current_by_ordinal[ref["ordinal"]] != ref["name"]:
                return "field_changed"
    current_templates = {item["ordinal"] for item in structure["templates"]}
    if any(value not in current_templates for value in profile["appliesTo"]["templateOrdinals"]):
        return "template_field_usage_changed"
    return "fingerprint_mismatch"


def _sibling_counts(col: Any, note_ids: Iterable[int]) -> dict[int, int]:
    ids = list(dict.fromkeys(value for value in note_ids if value > 0))
    if not ids or col is None or getattr(col, "db", None) is None:
        return {}
    placeholders = ",".join("?" for _ in ids)
    try:
        rows = col.db.all(
            f"select nid, count(*) from cards where nid in ({placeholders}) group by nid",
            *ids,
        )
    except Exception:
        return {}
    return {
        _positive_int(row[0]): max(1, _non_negative_int(row[1]))
        for row in rows
        if isinstance(row, (list, tuple)) and len(row) >= 2 and _positive_int(row[0]) > 0
    }


def _triage_profile_result(
    source_status: str,
    content_status: str,
    *,
    reasons: list[dict[str, Any]] | None = None,
    item_count: int = 0,
    skipped_count: int = 0,
    error_code: str | None = None,
    confirmed_count: int = 0,
    needs_review_count: int = 0,
    disabled_count: int = 0,
    suggested_count: int = 0,
    evaluated_note_count: int = 0,
    failed_check_count: int = 0,
) -> dict[str, Any]:
    return {
        "reasons": reasons or [],
        "sourceStatus": {
            "status": source_status,
            "itemCount": max(0, int(item_count)),
            "skippedCount": max(0, int(skipped_count)),
            "truncated": False,
            "errorCode": error_code[:80] if error_code else None,
        },
        "contentChecks": {
            "status": content_status if content_status in CONTENT_STATUS_VALUES else "unavailable",
            "confirmedProfileCount": max(0, int(confirmed_count)),
            "needsReviewProfileCount": max(0, int(needs_review_count)),
            "disabledProfileCount": max(0, int(disabled_count)),
            "suggestedProfileCount": max(0, int(suggested_count)),
            "evaluatedNoteCount": max(0, int(evaluated_note_count)),
            "failedCheckCount": max(0, int(failed_check_count)),
            "skippedCount": max(0, int(skipped_count)),
            "truncated": False,
            "errorCode": error_code[:80] if error_code else None,
        },
    }


def _public_store_status(snapshot: dict[str, Any]) -> dict[str, Any]:
    status = str(snapshot.get("status") or "unavailable")
    if status not in {"empty", "available", "corrupt", "future_schema", "unavailable"}:
        status = "unavailable"
    error_code = snapshot.get("errorCode")
    return {
        "status": status,
        "revision": _non_negative_int(snapshot.get("revision")),
        "profileCount": min(MAX_PROFILES, len(snapshot.get("profiles", [])) if isinstance(snapshot.get("profiles"), list) else 0),
        "errorCode": str(error_code)[:80] if isinstance(error_code, str) and error_code else None,
        "quarantined": bool(snapshot.get("quarantined")),
    }


def _strict_request(raw: object, expected: set[str], errors: dict[str, str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        errors["request"] = "Expected a JSON object."
        return {}
    for key in raw:
        if key not in expected:
            errors[str(key)] = "Unexpected field."
    for key in expected:
        if key not in raw:
            errors[key] = "Required field."
    return raw


def _schema_version(value: dict[str, Any], errors: dict[str, str]) -> None:
    if value.get("schemaVersion") != INSPECTION_API_SCHEMA_VERSION or isinstance(value.get("schemaVersion"), bool):
        errors["schemaVersion"] = "Expected schemaVersion 1."


def _decimal_id_array(
    value: object,
    field: str,
    errors: dict[str, str],
    *,
    maximum: int,
    allow_empty: bool,
) -> list[int]:
    if not isinstance(value, list) or len(value) > maximum or (not value and not allow_empty):
        errors[field] = f"Expected {'0' if allow_empty else '1'} to {maximum} decimal ID strings."
        return []
    result: list[int] = []
    for index, item in enumerate(value):
        try:
            parsed = int(normalize_decimal_id(item, f"{field}.{index}"))
        except InspectionProfileValidationError as error:
            errors.update(error.field_errors)
            continue
        if parsed not in result:
            result.append(parsed)
    return result


def _bounded_int(value: object, minimum: int, maximum: int, field: str, errors: dict[str, str]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        errors[field] = f"Expected an integer from {minimum} to {maximum}."
        return minimum
    return value


def _raise_request_errors(errors: dict[str, str]) -> None:
    if errors:
        raise InspectionProfileValidationError(errors)


def _bounded_plain_text(value: object, limit: int) -> str:
    return safe_plain_text(value, limit=limit).strip()


def _bounded_confidence(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, number)), 4)


def _ordinal(value: object, fallback: int, *, maximum: int) -> int:
    if value is None:
        value = fallback
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError("invalid ordinal")
    return value


def _positive_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if 0 < result <= MAX_SIGNED_ID else 0


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
