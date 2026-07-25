"""Strict versioned local store for declarative card display formatters."""

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


CARD_DISPLAY_FORMATTER_SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_FORMATTERS = 1000
MAX_ENTRIES_PER_NOTE_TYPE = 33
MAX_TEXT_LENGTH = 160
MAX_LINE_SEPARATOR_LENGTH = 8
MAX_TEMPLATE_ORDINAL = 31
MAX_DISPLAY_CHARACTERS = 240
MAX_SIGNED_ID = 9_223_372_036_854_775_807
MAX_SAFE_REVISION = 9_007_199_254_740_991

STORED_STATES = frozenset({"enabled", "disabled"})
INPUT_SOURCES = frozenset({"browser_question", "reviewer_front"})
TEXT_MODES = frozenset({"preserve", "omit"})
MEDIA_MODES = frozenset({"omit", "filename", "stem", "marker"})

_DECIMAL_ID_RE = re.compile(r"[1-9]\d{0,18}")
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")


class CardDisplayFormatterValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid card display formatter document.")
        self.field_errors = dict(field_errors)


class CardDisplayFormatterConflictError(RuntimeError):
    def __init__(self, current_revision: int) -> None:
        super().__init__("Card display formatter revision is stale.")
        self.current_revision = max(0, int(current_revision))


class UnsupportedCardDisplayFormatterSchemaError(RuntimeError):
    pass


class CardDisplayFormatterStoreUnavailableError(RuntimeError):
    pass


class CardDisplayFormatterStore:
    """Thread-safe atomic store for one profile-local formatter document."""

    def __init__(self, path: Path, *, max_document_bytes: int = MAX_DOCUMENT_BYTES) -> None:
        self.path = Path(path)
        self.max_document_bytes = max(1024, int(max_document_bytes))
        self._lock = threading.RLock()

    def read(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._read_locked())

    def save_formatter(self, formatter: object, *, expected_revision: object) -> dict[str, Any]:
        normalized = validate_card_display_formatter(formatter)
        key = formatter_key(normalized)

        def update(document: dict[str, Any]) -> None:
            formatters = [item for item in document["formatters"] if formatter_key(item) != key]
            formatters.append(normalized)
            formatters.sort(key=_formatter_sort_key)
            document["formatters"] = formatters

        return self._update(expected_revision, update)

    def delete_formatter(
        self,
        note_type_id: object,
        template_ordinal: object,
        *,
        expected_revision: object,
    ) -> dict[str, Any]:
        normalized_id = normalize_decimal_id(note_type_id, "noteTypeId")
        normalized_ordinal = normalize_template_ordinal(template_ordinal, "templateOrdinal")
        key = (normalized_id, normalized_ordinal)

        def update(document: dict[str, Any]) -> None:
            remaining = [item for item in document["formatters"] if formatter_key(item) != key]
            if len(remaining) == len(document["formatters"]):
                raise CardDisplayFormatterValidationError({"formatter": "Formatter does not exist."})
            document["formatters"] = remaining

        return self._update(expected_revision, update)

    def _update(
        self,
        expected_revision: object,
        update: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        revision = normalize_revision(expected_revision, "expectedRevision")
        with self._lock:
            snapshot = self._read_locked()
            if snapshot["status"] == "future_schema":
                raise UnsupportedCardDisplayFormatterSchemaError(
                    "Future card display formatter schema is preserved."
                )
            if snapshot["status"] == "unavailable":
                raise CardDisplayFormatterStoreUnavailableError(
                    "Card display formatter store is unavailable."
                )
            document = {
                "schemaVersion": CARD_DISPLAY_FORMATTER_SCHEMA_VERSION,
                "revision": snapshot["revision"],
                "formatters": deepcopy(snapshot["formatters"]),
            }
            if document["revision"] != revision:
                raise CardDisplayFormatterConflictError(document["revision"])
            update(document)
            document["revision"] += 1
            normalized = validate_card_display_formatter_document(document)
            self._write_locked(normalized)
            return _snapshot_from_document(normalized)

    def _read_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return _snapshot("empty")
        try:
            size = self.path.stat().st_size
            if size < 0 or size > self.max_document_bytes:
                raise ValueError("document size is invalid")
            raw_bytes = self.path.read_bytes()
            if len(raw_bytes) > self.max_document_bytes:
                raise ValueError("document size is invalid")
            raw = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("document must be an object")
            version = raw.get("schemaVersion")
            if _is_int(version) and int(version) > CARD_DISPLAY_FORMATTER_SCHEMA_VERSION:
                return _snapshot("future_schema", error_code="future_schema")
            document = validate_card_display_formatter_document(raw)
            return _snapshot_from_document(document)
        except (OSError, UnicodeError):
            return _snapshot("unavailable", error_code="store_unavailable")
        except (
            json.JSONDecodeError,
            ValueError,
            TypeError,
            CardDisplayFormatterValidationError,
        ):
            quarantined = self._quarantine_locked()
            return _snapshot("corrupt", error_code="store_corrupt", quarantined=quarantined)

    def _write_locked(self, document: dict[str, Any]) -> None:
        payload = serialized_document(document)
        if len(payload) > self.max_document_bytes:
            raise CardDisplayFormatterValidationError(
                {"document": "Document exceeds the size limit."}
            )
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


def empty_card_display_formatter_document() -> dict[str, Any]:
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_SCHEMA_VERSION,
        "revision": 0,
        "formatters": [],
    }


def validate_card_display_formatter_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CardDisplayFormatterValidationError({"document": "Expected an object."})
    errors: dict[str, str] = {}
    _reject_unknown(value, {"schemaVersion", "revision", "formatters"}, "", errors)
    if (
        value.get("schemaVersion") != CARD_DISPLAY_FORMATTER_SCHEMA_VERSION
        or isinstance(value.get("schemaVersion"), bool)
    ):
        errors["schemaVersion"] = "Expected schemaVersion 1."
    revision = _revision(value.get("revision"), "revision", errors)
    raw_formatters = value.get("formatters")
    if not isinstance(raw_formatters, list) or len(raw_formatters) > MAX_FORMATTERS:
        errors["formatters"] = f"Expected an array with at most {MAX_FORMATTERS} formatters."
        raw_formatters = []

    formatters: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()
    per_note_type: dict[str, int] = {}
    for index, raw in enumerate(raw_formatters):
        try:
            formatter = validate_card_display_formatter(raw, field=f"formatters.{index}")
        except CardDisplayFormatterValidationError as error:
            errors.update(error.field_errors)
            continue
        key = formatter_key(formatter)
        if key in seen:
            errors[f"formatters.{index}"] = "Duplicate formatter key."
        seen.add(key)
        note_type_id = formatter["noteTypeId"]
        per_note_type[note_type_id] = per_note_type.get(note_type_id, 0) + 1
        if per_note_type[note_type_id] > MAX_ENTRIES_PER_NOTE_TYPE:
            errors[f"formatters.{index}.noteTypeId"] = (
                f"At most {MAX_ENTRIES_PER_NOTE_TYPE} entries per note type are allowed."
            )
        formatters.append(formatter)
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return {
        "schemaVersion": CARD_DISPLAY_FORMATTER_SCHEMA_VERSION,
        "revision": revision,
        "formatters": formatters,
    }


def validate_card_display_formatter(
    value: object,
    *,
    field: str = "formatter",
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CardDisplayFormatterValidationError({field: "Expected an object."})
    errors: dict[str, str] = {}
    expected = {
        "noteTypeId",
        "noteTypeName",
        "templateOrdinal",
        "templateName",
        "storedState",
        "inputSource",
        "textMode",
        "imageMode",
        "audioMode",
        "maxLines",
        "lineSeparator",
        "maxCharacters",
        "updatedAt",
    }
    _reject_unknown(value, expected, field, errors)
    note_type_id = _decimal_id(value.get("noteTypeId"), f"{field}.noteTypeId", errors)
    note_type_name = _bounded_text(value.get("noteTypeName"), f"{field}.noteTypeName", errors)
    template_ordinal = _template_ordinal(
        value.get("templateOrdinal"), f"{field}.templateOrdinal", errors
    )
    template_name = _nullable_bounded_text(
        value.get("templateName"), f"{field}.templateName", errors
    )
    if template_ordinal is None and template_name is not None:
        errors[f"{field}.templateName"] = "Note-type defaults require templateName null."
    if template_ordinal is not None and template_name is None:
        errors[f"{field}.templateName"] = "Exact template formatters require a name snapshot."

    stored_state = _enum(
        value.get("storedState"), STORED_STATES, f"{field}.storedState", errors
    )
    input_source = _enum(
        value.get("inputSource"), INPUT_SOURCES, f"{field}.inputSource", errors
    )
    text_mode = _enum(value.get("textMode"), TEXT_MODES, f"{field}.textMode", errors)
    image_mode = _enum(value.get("imageMode"), MEDIA_MODES, f"{field}.imageMode", errors)
    audio_mode = _enum(value.get("audioMode"), MEDIA_MODES, f"{field}.audioMode", errors)
    max_lines = _bounded_int(value.get("maxLines"), 1, 4, f"{field}.maxLines", errors)
    line_separator = _line_separator(value.get("lineSeparator"), f"{field}.lineSeparator", errors)
    max_characters = _bounded_int(
        value.get("maxCharacters"), 1, MAX_DISPLAY_CHARACTERS, f"{field}.maxCharacters", errors
    )
    updated_at = _timestamp(value.get("updatedAt"), f"{field}.updatedAt", errors)
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return {
        "noteTypeId": note_type_id,
        "noteTypeName": note_type_name,
        "templateOrdinal": template_ordinal,
        "templateName": template_name,
        "storedState": stored_state,
        "inputSource": input_source,
        "textMode": text_mode,
        "imageMode": image_mode,
        "audioMode": audio_mode,
        "maxLines": max_lines,
        "lineSeparator": line_separator,
        "maxCharacters": max_characters,
        "updatedAt": updated_at,
    }


def formatter_key(formatter: dict[str, Any]) -> tuple[str, int | None]:
    return (formatter["noteTypeId"], formatter["templateOrdinal"])


def normalize_decimal_id(value: object, field: str) -> str:
    errors: dict[str, str] = {}
    result = _decimal_id(value, field, errors)
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return result


def normalize_template_ordinal(value: object, field: str) -> int | None:
    errors: dict[str, str] = {}
    result = _template_ordinal(value, field, errors)
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return result


def normalize_revision(value: object, field: str) -> int:
    errors: dict[str, str] = {}
    result = _revision(value, field, errors)
    if errors:
        raise CardDisplayFormatterValidationError(errors)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def serialized_document(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _snapshot_from_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "available" if document["formatters"] else "empty",
        "revision": document["revision"],
        "formatters": deepcopy(document["formatters"]),
        "errorCode": None,
        "quarantined": False,
    }


def _snapshot(
    status: str,
    *,
    error_code: str | None = None,
    quarantined: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "revision": 0,
        "formatters": [],
        "errorCode": error_code,
        "quarantined": bool(quarantined),
    }


def _formatter_sort_key(value: dict[str, Any]) -> tuple[int, int]:
    ordinal = value["templateOrdinal"]
    return (int(value["noteTypeId"]), -1 if ordinal is None else int(ordinal))


def _reject_unknown(
    value: dict[Any, Any],
    expected: set[str],
    field: str,
    errors: dict[str, str],
) -> None:
    for key in value:
        path = f"{field}.{key}" if field else str(key)
        if key not in expected:
            errors[path] = "Unexpected field."
    for key in expected:
        if key not in value:
            path = f"{field}.{key}" if field else key
            errors[path] = "Required field."


def _decimal_id(value: object, field: str, errors: dict[str, str]) -> str:
    if (
        not isinstance(value, str)
        or not _DECIMAL_ID_RE.fullmatch(value)
        or int(value) > MAX_SIGNED_ID
    ):
        errors[field] = "Expected a positive signed-64-bit decimal string."
        return "1"
    return value


def _revision(value: object, field: str, errors: dict[str, str]) -> int:
    if not _is_int(value) or not 0 <= int(value) <= MAX_SAFE_REVISION:
        errors[field] = "Expected a non-negative safe integer."
        return 0
    return int(value)


def _template_ordinal(
    value: object,
    field: str,
    errors: dict[str, str],
) -> int | None:
    if value is None:
        return None
    if not _is_int(value) or not 0 <= int(value) <= MAX_TEMPLATE_ORDINAL:
        errors[field] = f"Expected null or an integer from 0 to {MAX_TEMPLATE_ORDINAL}."
        return None
    return int(value)


def _bounded_int(
    value: object,
    minimum: int,
    maximum: int,
    field: str,
    errors: dict[str, str],
) -> int:
    if not _is_int(value) or not minimum <= int(value) <= maximum:
        errors[field] = f"Expected an integer from {minimum} to {maximum}."
        return minimum
    return int(value)


def _bounded_text(value: object, field: str, errors: dict[str, str]) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_TEXT_LENGTH
        or _has_control(value)
    ):
        errors[field] = f"Expected non-empty text up to {MAX_TEXT_LENGTH} characters."
        return ""
    return value.strip()


def _nullable_bounded_text(
    value: object,
    field: str,
    errors: dict[str, str],
) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field, errors)


def _line_separator(value: object, field: str, errors: dict[str, str]) -> str:
    if (
        not isinstance(value, str)
        or len(value) > MAX_LINE_SEPARATOR_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        errors[field] = (
            f"Expected text up to {MAX_LINE_SEPARATOR_LENGTH} characters without controls."
        )
        return " "
    return value


def _timestamp(value: object, field: str, errors: dict[str, str]) -> str:
    if not isinstance(value, str) or len(value) > 40 or not _TIMESTAMP_RE.fullmatch(value):
        errors[field] = "Expected an RFC 3339 UTC timestamp."
        return "1970-01-01T00:00:00Z"
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors[field] = "Expected an RFC 3339 UTC timestamp."
        return "1970-01-01T00:00:00Z"
    return value


def _enum(
    value: object,
    allowed: frozenset[str],
    field: str,
    errors: dict[str, str],
) -> str:
    if not isinstance(value, str) or value not in allowed:
        errors[field] = f"Expected one of {sorted(allowed)}."
        return sorted(allowed)[0]
    return value


def _has_control(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
