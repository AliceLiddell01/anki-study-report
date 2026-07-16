from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MAX_BYTES = 1_048_576


class StrictJsonError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise StrictJsonError(f"non-standard JSON number is not allowed: {value}")


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate object key: {key}")
        result[key] = value
    return result


def loads_strict(text: str, *, context: str = "JSON document") -> Any:
    if not text.strip():
        raise StrictJsonError(f"{context}: document is empty")
    if text.startswith("\ufeff"):
        raise StrictJsonError(f"{context}: UTF-8 BOM is not allowed")
    try:
        return json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except StrictJsonError as exc:
        raise StrictJsonError(f"{context}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise StrictJsonError(
            f"{context}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def load_strict_json(path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StrictJsonError(f"{path}: unable to read JSON: {exc}") from exc
    if len(raw) > max_bytes:
        raise StrictJsonError(f"{path}: JSON file exceeds {max_bytes} bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"{path}: UTF-8 BOM is not allowed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"{path}: invalid UTF-8 at byte {exc.start}") from exc
    return loads_strict(text, context=str(path))
