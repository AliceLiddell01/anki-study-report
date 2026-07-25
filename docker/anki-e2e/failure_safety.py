from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
import re
from typing import Any

from failure_registry import (
    ERROR_TYPE_RE,
    ID_RE,
    LINUX_ABSOLUTE_RE,
    MAX_PATHS,
    MAX_PATH_BYTES,
    MAX_SUMMARY_BYTES,
    SECRET_RE,
    TOKEN_URL_RE,
    UTC_RE,
    WINDOWS_ABSOLUTE_RE,
    FailureProtocolError,
)


def validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise FailureProtocolError("occurredAtUtc must be UTC ISO-8601 with millisecond precision")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FailureProtocolError("occurredAtUtc is invalid") from exc
    return value


def safe_single_line(
    value: Any,
    label: str,
    *,
    max_bytes: int,
    fallback: str | None = None,
    pattern: re.Pattern[str] | None = None,
) -> str | None:
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise FailureProtocolError(f"{label} must be a string or null")
    normalized = " ".join(value.strip().split())
    if not normalized:
        if fallback is not None:
            return fallback
        raise FailureProtocolError(f"{label} must be non-empty")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise FailureProtocolError(f"{label} contains control characters")
    if normalized.startswith("::"):
        raise FailureProtocolError(f"{label} must not begin with a workflow command marker")
    if len(normalized.encode("utf-8")) > max_bytes:
        encoded = normalized.encode("utf-8")[:max_bytes]
        normalized = encoded.decode("utf-8", errors="ignore").rstrip()
    if (
        TOKEN_URL_RE.search(normalized)
        or WINDOWS_ABSOLUTE_RE.search(normalized)
        or LINUX_ABSOLUTE_RE.search(normalized)
        or SECRET_RE.search(normalized)
    ):
        raise FailureProtocolError(f"{label} contains private or secret-like data")
    if pattern is not None and not pattern.fullmatch(normalized):
        raise FailureProtocolError(f"{label} has an invalid format")
    return normalized


def sanitize_summary(value: Any, fallback: str) -> str:
    raw = str(value or fallback)
    raw = raw.replace("\r", " ").replace("\n", " ").replace("\t", " ").replace("\0", " ")
    raw = re.sub(r"https?://\S+", "[URL]", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/])\S*", "[PRIVATE_PATH]", raw)
    raw = re.sub(r"/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:/\S*)?", "[PRIVATE_PATH]", raw)
    raw = re.sub(r"([?&](?:access_)?token=)[^&\s]+", r"\1[REDACTED]", raw, flags=re.IGNORECASE)
    raw = SECRET_RE.sub("[REDACTED]", raw)
    raw = " ".join(raw.split()) or fallback
    if raw.startswith("::"):
        raw = raw.lstrip(":")
    encoded = raw.encode("utf-8")
    if len(encoded) > MAX_SUMMARY_BYTES:
        raw = encoded[:MAX_SUMMARY_BYTES].decode("utf-8", errors="ignore").rstrip()
    return safe_single_line(raw, "summary", max_bytes=MAX_SUMMARY_BYTES, fallback=fallback) or fallback


def safe_id(value: Any, label: str, *, allow_none: bool = True) -> str | None:
    if value is None and allow_none:
        return None
    return safe_single_line(value, label, max_bytes=120, pattern=ID_RE)


def safe_path(value: Any, label: str) -> str:
    normalized = safe_single_line(value, label, max_bytes=MAX_PATH_BYTES)
    assert normalized is not None
    if "\\" in normalized:
        raise FailureProtocolError(f"{label} must use POSIX separators")
    path = PurePosixPath(normalized)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", normalized) or any(part in {"", ".", ".."} for part in path.parts):
        raise FailureProtocolError(f"{label} must be a normalized safe relative path")
    return path.as_posix()


def paths(values: Any, label: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > MAX_PATHS:
        raise FailureProtocolError(f"{label} must be an array with at most {MAX_PATHS} items")
    result: list[str] = []
    for index, value in enumerate(values):
        path = safe_path(value, f"{label}[{index}]")
        if path not in result:
            result.append(path)
    return result


def optional_non_negative_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FailureProtocolError(f"{label} must be a non-negative integer or null")
    return value
