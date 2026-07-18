"""Strict versioned Inspection Profile contract and profile-local JSON store."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Callable


INSPECTION_PROFILE_SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_PROFILES = 500
MAX_MAPPINGS = 32
MAX_CHECKS = 32
MAX_REFS_PER_CHECK = 16
MAX_FIELDS_PER_MAPPING = 16
MAX_TEMPLATE_ORDINALS = 16
MAX_FIELD_ORDINAL = 63
MAX_TEMPLATE_ORDINAL = 31
MAX_TEXT_LENGTH = 160
MAX_CHECK_ID_LENGTH = 80
MAX_PROFILE_ID_LENGTH = 80

STORED_STATES = {"suggested", "confirmed", "disabled"}
CHECK_KINDS = {
    "non_empty",
    "contains_audio",
    "contains_image",
    "min_text_length",
    "one_of_roles_non_empty",
    "all_roles_non_empty",
}
PRIORITIES = {"high", "medium", "low"}
CHECK_MODES = {"any", "all"}

DECIMAL_ID_RE = re.compile(r"[1-9]\d{0,18}")
PROFILE_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,79}")
ROLE_RE = re.compile(r"[a-z][a-z0-9_]{0,39}")
CHECK_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,79}")
FINGERPRINT_RE = re.compile(r"[a-f0-9]{64}")
RFC3339_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
MAX_SIGNED_ID = 9_223_372_036_854_775_807


class InspectionProfileValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid inspection profile document.")
        self.field_errors = dict(field_errors)


class InspectionProfileConflictError(RuntimeError):
    def __init__(self, current_revision: int) -> None:
        super().__init__("Inspection profile revision is stale.")
        self.current_revision = max(0, int(current_revision))


class UnsupportedInspectionProfileSchemaError(RuntimeError):
    pass


class InspectionProfileStoreUnavailableError(RuntimeError):
    pass


class InspectionProfileStore:
    """Thread-safe atomic store for one profile-local inspection document."""

    def __init__(self, path: Path, *, max_document_bytes: int = MAX_DOCUMENT_BYTES) -> None:
        self.path = Path(path)
        self.max_document_bytes = max(1024, int(max_document_bytes))
        self._lock = threading.RLock()

    def read(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._read_locked())

    def save_profile(self, profile: object, *, expected_revision: object) -> dict[str, Any]:
        normalized = validate_inspection_profile(profile)

        def update(document: dict[str, Any]) -> None:
            profiles = [
                item
                for item in document["profiles"]
                if item["noteTypeId"] != normalized["noteTypeId"]
            ]
            profiles.append(normalized)
            profiles.sort(key=lambda item: int(item["noteTypeId"]))
            document["profiles"] = profiles

        return self._update(expected_revision, update)

    def disable_profile(
        self,
        note_type_id: object,
        *,
        expected_revision: object,
        updated_at: str,
    ) -> dict[str, Any]:
        normalized_id = normalize_decimal_id(note_type_id, "noteTypeId")

        def update(document: dict[str, Any]) -> None:
            for profile in document["profiles"]:
                if profile["noteTypeId"] == normalized_id:
                    profile["storedState"] = "disabled"
                    profile["updatedAt"] = normalize_timestamp(updated_at, "updatedAt", allow_none=False)
                    return
            raise InspectionProfileValidationError({"noteTypeId": "Profile does not exist."})

        return self._update(expected_revision, update)

    def delete_profile(self, note_type_id: object, *, expected_revision: object) -> dict[str, Any]:
        normalized_id = normalize_decimal_id(note_type_id, "noteTypeId")

        def update(document: dict[str, Any]) -> None:
            profiles = [item for item in document["profiles"] if item["noteTypeId"] != normalized_id]
            if len(profiles) == len(document["profiles"]):
                raise InspectionProfileValidationError({"noteTypeId": "Profile does not exist."})
            document["profiles"] = profiles

        return self._update(expected_revision, update)

    def _update(
        self,
        expected_revision: object,
        update: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        revision = normalize_revision(expected_revision, "expectedRevision")
        with self._lock:
            snapshot = self._read_locked()
            status = snapshot["status"]
            if status == "future_schema":
                raise UnsupportedInspectionProfileSchemaError("Future inspection profile schema is preserved.")
            if status == "unavailable":
                raise InspectionProfileStoreUnavailableError("Inspection profile store is unavailable.")
            document = {
                "schemaVersion": INSPECTION_PROFILE_SCHEMA_VERSION,
                "revision": snapshot["revision"],
                "profiles": deepcopy(snapshot["profiles"]),
            }
            if document["revision"] != revision:
                raise InspectionProfileConflictError(document["revision"])
            update(document)
            document["revision"] += 1
            normalized = validate_inspection_profile_document(document)
            self._write_locked(normalized)
            return {
                "status": "available" if normalized["profiles"] else "empty",
                "revision": normalized["revision"],
                "profiles": deepcopy(normalized["profiles"]),
                "errorCode": None,
                "quarantined": False,
            }

    def _read_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return _snapshot("empty")
        try:
            size = self.path.stat().st_size
            if size < 0 or size > self.max_document_bytes:
                raise ValueError("document size is invalid")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("document must be an object")
            version = raw.get("schemaVersion")
            if _is_int(version) and int(version) > INSPECTION_PROFILE_SCHEMA_VERSION:
                return _snapshot("future_schema", error_code="future_schema")
            document = validate_inspection_profile_document(raw)
            return {
                "status": "available" if document["profiles"] else "empty",
                "revision": document["revision"],
                "profiles": deepcopy(document["profiles"]),
                "errorCode": None,
                "quarantined": False,
            }
        except (OSError, UnicodeError):
            return _snapshot("unavailable", error_code="store_unavailable")
        except (json.JSONDecodeError, ValueError, TypeError, InspectionProfileValidationError):
            quarantined = self._quarantine_locked()
            return _snapshot("corrupt", error_code="store_corrupt", quarantined=quarantined)

    def _write_locked(self, document: dict[str, Any]) -> None:
        payload = _serialized_document(document)
        if len(payload) > self.max_document_bytes:
            raise InspectionProfileValidationError({"document": "Document exceeds the size limit."})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise

    def _quarantine_locked(self) -> bool:
        if not self.path.exists():
            return False
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.path.with_name(f"{self.path.name}.corrupt-{timestamp}")
        try:
            os.replace(self.path, target)
            return True
        except OSError:
            return False


def empty_inspection_profile_document() -> dict[str, Any]:
    return {"schemaVersion": INSPECTION_PROFILE_SCHEMA_VERSION, "revision": 0, "profiles": []}


def validate_inspection_profile_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InspectionProfileValidationError({"document": "Expected an object."})
    errors: dict[str, str] = {}
    _reject_unknown(value, {"schemaVersion", "revision", "profiles"}, "", errors)
    if value.get("schemaVersion") != INSPECTION_PROFILE_SCHEMA_VERSION or isinstance(value.get("schemaVersion"), bool):
        errors["schemaVersion"] = "Expected schemaVersion 1."
    revision = _revision(value.get("revision"), "revision", errors)
    raw_profiles = value.get("profiles")
    if not isinstance(raw_profiles, list) or len(raw_profiles) > MAX_PROFILES:
        errors["profiles"] = f"Expected an array with at most {MAX_PROFILES} profiles."
        raw_profiles = []
    profiles: list[dict[str, Any]] = []
    seen_profile_ids: set[str] = set()
    seen_note_type_ids: set[str] = set()
    for index, raw in enumerate(raw_profiles):
        try:
            profile = validate_inspection_profile(raw, field=f"profiles.{index}")
        except InspectionProfileValidationError as error:
            errors.update(error.field_errors)
            continue
        if profile["profileId"] in seen_profile_ids:
            errors[f"profiles.{index}.profileId"] = "Duplicate profileId."
        if profile["noteTypeId"] in seen_note_type_ids:
            errors[f"profiles.{index}.noteTypeId"] = "Only one profile per noteTypeId is allowed."
        seen_profile_ids.add(profile["profileId"])
        seen_note_type_ids.add(profile["noteTypeId"])
        profiles.append(profile)
    if errors:
        raise InspectionProfileValidationError(errors)
    return {"schemaVersion": INSPECTION_PROFILE_SCHEMA_VERSION, "revision": revision, "profiles": profiles}


def validate_inspection_profile(value: object, *, field: str = "profile") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InspectionProfileValidationError({field: "Expected an object."})
    errors: dict[str, str] = {}
    expected = {
        "profileId",
        "noteTypeId",
        "noteTypeName",
        "storedState",
        "displayName",
        "expectedFingerprint",
        "appliesTo",
        "fieldMappings",
        "checks",
        "confirmedAt",
        "updatedAt",
    }
    _reject_unknown(value, expected, field, errors)
    profile_id = _identifier(value.get("profileId"), PROFILE_ID_RE, MAX_PROFILE_ID_LENGTH, f"{field}.profileId", errors)
    note_type_id = _decimal_id(value.get("noteTypeId"), f"{field}.noteTypeId", errors)
    if profile_id and note_type_id and profile_id != f"note-type-{note_type_id}":
        errors[f"{field}.profileId"] = "v1 profileId must be note-type-<noteTypeId>."
    note_type_name = _bounded_text(value.get("noteTypeName"), f"{field}.noteTypeName", errors)
    display_name = _bounded_text(value.get("displayName"), f"{field}.displayName", errors)
    stored_state = value.get("storedState")
    if stored_state not in STORED_STATES:
        errors[f"{field}.storedState"] = "Expected suggested, confirmed, or disabled."
        stored_state = "suggested"
    fingerprint = _fingerprint(value.get("expectedFingerprint"), f"{field}.expectedFingerprint", errors)
    applies_to = _applies_to(value.get("appliesTo"), f"{field}.appliesTo", errors)
    mappings = _field_mappings(value.get("fieldMappings"), f"{field}.fieldMappings", errors)
    checks = _checks(value.get("checks"), f"{field}.checks", errors)
    mapped_roles = {item["role"] for item in mappings}
    for index, check in enumerate(checks):
        missing = [role for role in check["roles"] if role not in mapped_roles]
        if missing:
            errors[f"{field}.checks.{index}.roles"] = "Every targeted role must have a field mapping."
    confirmed_at = _timestamp(value.get("confirmedAt"), f"{field}.confirmedAt", errors, allow_none=True)
    updated_at = _timestamp(value.get("updatedAt"), f"{field}.updatedAt", errors, allow_none=False)
    if stored_state == "confirmed" and confirmed_at is None:
        errors[f"{field}.confirmedAt"] = "Confirmed profiles require confirmedAt."
    if errors:
        raise InspectionProfileValidationError(errors)
    return {
        "profileId": profile_id,
        "noteTypeId": note_type_id,
        "noteTypeName": note_type_name,
        "storedState": stored_state,
        "displayName": display_name,
        "expectedFingerprint": fingerprint,
        "appliesTo": applies_to,
        "fieldMappings": mappings,
        "checks": checks,
        "confirmedAt": confirmed_at,
        "updatedAt": updated_at,
    }


def normalize_decimal_id(value: object, field: str) -> str:
    errors: dict[str, str] = {}
    result = _decimal_id(value, field, errors)
    if errors:
        raise InspectionProfileValidationError(errors)
    return result


def normalize_revision(value: object, field: str) -> int:
    errors: dict[str, str] = {}
    result = _revision(value, field, errors)
    if errors:
        raise InspectionProfileValidationError(errors)
    return result


def normalize_timestamp(value: object, field: str, *, allow_none: bool) -> str | None:
    errors: dict[str, str] = {}
    result = _timestamp(value, field, errors, allow_none=allow_none)
    if errors:
        raise InspectionProfileValidationError(errors)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _field_mappings(value: object, field: str, errors: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_MAPPINGS:
        errors[field] = f"Expected an array with at most {MAX_MAPPINGS} mappings."
        return []
    result: list[dict[str, Any]] = []
    roles: set[str] = set()
    refs_seen: set[tuple[int, str]] = set()
    for index, raw in enumerate(value):
        path = f"{field}.{index}"
        if not isinstance(raw, dict):
            errors[path] = "Expected an object."
            continue
        _reject_unknown(raw, {"role", "fields"}, path, errors)
        role = _identifier(raw.get("role"), ROLE_RE, 40, f"{path}.role", errors)
        if role in roles:
            errors[f"{path}.role"] = "Duplicate role."
        roles.add(role)
        refs = _field_refs(raw.get("fields"), f"{path}.fields", errors)
        for ref in refs:
            key = (ref["ordinal"], ref["name"])
            if key in refs_seen:
                errors[f"{path}.fields"] = "Duplicate field reference."
            refs_seen.add(key)
        result.append({"role": role, "fields": refs})
    return result


def _field_refs(value: object, field: str, errors: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_FIELDS_PER_MAPPING:
        errors[field] = f"Expected 1 to {MAX_FIELDS_PER_MAPPING} field references."
        return []
    result: list[dict[str, Any]] = []
    local_seen: set[tuple[int, str]] = set()
    for index, raw in enumerate(value):
        path = f"{field}.{index}"
        if not isinstance(raw, dict):
            errors[path] = "Expected an object."
            continue
        _reject_unknown(raw, {"ordinal", "name"}, path, errors)
        ordinal = _bounded_int(raw.get("ordinal"), 0, MAX_FIELD_ORDINAL, f"{path}.ordinal", errors)
        name = _bounded_text(raw.get("name"), f"{path}.name", errors)
        key = (ordinal, name)
        if key in local_seen:
            errors[path] = "Duplicate field reference."
        local_seen.add(key)
        result.append({"ordinal": ordinal, "name": name})
    return result


def _checks(value: object, field: str, errors: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_CHECKS:
        errors[field] = f"Expected an array with at most {MAX_CHECKS} checks."
        return []
    result: list[dict[str, Any]] = []
    check_ids: set[str] = set()
    for index, raw in enumerate(value):
        path = f"{field}.{index}"
        if not isinstance(raw, dict):
            errors[path] = "Expected an object."
            continue
        kind = raw.get("kind")
        if kind not in CHECK_KINDS:
            errors[f"{path}.kind"] = "Unsupported check kind."
            continue
        common = {"checkId", "kind", "roles", "priority"}
        expected = common | ({"mode"} if kind in {"non_empty", "contains_audio", "contains_image"} else set())
        if kind == "min_text_length":
            expected |= {"mode", "minLength"}
        _reject_unknown(raw, expected, path, errors)
        check_id = _identifier(raw.get("checkId"), CHECK_ID_RE, MAX_CHECK_ID_LENGTH, f"{path}.checkId", errors)
        if check_id in check_ids:
            errors[f"{path}.checkId"] = "Duplicate checkId."
        check_ids.add(check_id)
        roles = _roles(raw.get("roles"), f"{path}.roles", errors)
        priority = raw.get("priority")
        if priority not in PRIORITIES:
            errors[f"{path}.priority"] = "Expected high, medium, or low."
            priority = "medium"
        check: dict[str, Any] = {"checkId": check_id, "kind": kind, "roles": roles, "priority": priority}
        if "mode" in expected:
            mode = raw.get("mode")
            if mode not in CHECK_MODES:
                errors[f"{path}.mode"] = "Expected any or all."
                mode = "any"
            check["mode"] = mode
        if kind == "min_text_length":
            check["minLength"] = _bounded_int(raw.get("minLength"), 1, 10_000, f"{path}.minLength", errors)
        result.append(check)
    return result


def _roles(value: object, field: str, errors: dict[str, str]) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_REFS_PER_CHECK:
        errors[field] = f"Expected 1 to {MAX_REFS_PER_CHECK} roles."
        return []
    result: list[str] = []
    for index, raw in enumerate(value):
        role = _identifier(raw, ROLE_RE, 40, f"{field}.{index}", errors)
        if role in result:
            errors[f"{field}.{index}"] = "Duplicate role."
        result.append(role)
    return result


def _applies_to(value: object, field: str, errors: dict[str, str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors[field] = "Expected an object."
        return {"templateOrdinals": []}
    _reject_unknown(value, {"templateOrdinals"}, field, errors)
    raw = value.get("templateOrdinals")
    if not isinstance(raw, list) or len(raw) > MAX_TEMPLATE_ORDINALS:
        errors[f"{field}.templateOrdinals"] = f"Expected at most {MAX_TEMPLATE_ORDINALS} ordinals."
        raw = []
    result: list[int] = []
    for index, item in enumerate(raw):
        ordinal = _bounded_int(item, 0, MAX_TEMPLATE_ORDINAL, f"{field}.templateOrdinals.{index}", errors)
        if ordinal in result:
            errors[f"{field}.templateOrdinals.{index}"] = "Duplicate template ordinal."
        result.append(ordinal)
    return {"templateOrdinals": result}


def _fingerprint(value: object, field: str, errors: dict[str, str]) -> dict[str, str]:
    if not isinstance(value, dict):
        errors[field] = "Expected an object."
        return {"algorithm": "sha256", "value": "0" * 64}
    _reject_unknown(value, {"algorithm", "value"}, field, errors)
    if value.get("algorithm") != "sha256":
        errors[f"{field}.algorithm"] = "Expected sha256."
    fingerprint = value.get("value")
    if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
        errors[f"{field}.value"] = "Expected a lowercase SHA-256 value."
        fingerprint = "0" * 64
    return {"algorithm": "sha256", "value": fingerprint}


def _timestamp(value: object, field: str, errors: dict[str, str], *, allow_none: bool) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or len(value) > 40 or not RFC3339_UTC_RE.fullmatch(value):
        errors[field] = "Expected an RFC 3339 UTC timestamp."
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors[field] = "Expected an RFC 3339 UTC timestamp."
        return None
    return value


def _decimal_id(value: object, field: str, errors: dict[str, str]) -> str:
    if not isinstance(value, str) or not DECIMAL_ID_RE.fullmatch(value) or int(value) > MAX_SIGNED_ID:
        errors[field] = "Expected a positive signed-64-bit decimal string."
        return "1"
    return value


def _revision(value: object, field: str, errors: dict[str, str]) -> int:
    if not _is_int(value) or not 0 <= int(value) <= 9_007_199_254_740_991:
        errors[field] = "Expected a non-negative safe integer."
        return 0
    return int(value)


def _bounded_int(value: object, minimum: int, maximum: int, field: str, errors: dict[str, str]) -> int:
    if not _is_int(value) or not minimum <= int(value) <= maximum:
        errors[field] = f"Expected an integer from {minimum} to {maximum}."
        return minimum
    return int(value)


def _bounded_text(value: object, field: str, errors: dict[str, str]) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_LENGTH or _has_control(value):
        errors[field] = f"Expected non-empty text up to {MAX_TEXT_LENGTH} characters."
        return ""
    return value.strip()


def _identifier(
    value: object,
    pattern: re.Pattern[str],
    maximum: int,
    field: str,
    errors: dict[str, str],
) -> str:
    if not isinstance(value, str) or len(value) > maximum or not pattern.fullmatch(value):
        errors[field] = "Expected a bounded lowercase identifier."
        return "invalid"
    return value


def _reject_unknown(value: dict[Any, Any], expected: set[str], field: str, errors: dict[str, str]) -> None:
    for key in value:
        path = f"{field}.{key}" if field else str(key)
        if key not in expected:
            errors[path] = "Unexpected field."
    for key in expected:
        if key not in value:
            path = f"{field}.{key}" if field else key
            errors[path] = "Required field."


def _snapshot(
    status: str,
    *,
    error_code: str | None = None,
    quarantined: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "revision": 0,
        "profiles": [],
        "errorCode": error_code,
        "quarantined": bool(quarantined),
    }


def _serialized_document(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _has_control(value: str) -> bool:
    return any(ord(char) < 32 and char not in {"\t"} for char in value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
