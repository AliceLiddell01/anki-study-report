"""Small filesystem-boundary helpers for dashboard-controlled paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def safe_leaf_name(value: Any) -> str | None:
    """Return one platform-safe filename component, never a path."""

    text = str(value or "")
    if not text or "\x00" in text or text in {".", ".."} or ":" in text:
        return None
    if "/" in text or "\\" in text:
        return None
    leaf = os.path.basename(text)
    if leaf != text:
        return None
    return leaf


def _trusted_file_inventory(root_text: str) -> dict[str, Path]:
    """Index existing regular files whose resolved targets remain under root."""

    root = Path(root_text).resolve()
    inventory: dict[str, Path] = {}
    try:
        candidates = root.rglob("*")
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
                relative = resolved.relative_to(root)
                if not resolved.is_file():
                    continue
            except (OSError, RuntimeError, ValueError):
                continue
            key = relative.as_posix()
            if key and key not in inventory:
                inventory[key] = resolved
    except OSError:
        return {}
    return inventory


def trusted_file_from_inventory(root: Path, relative_path: str) -> Path | None:
    """Select a trusted existing file without constructing a path from request data."""

    if not isinstance(relative_path, str) or not relative_path or "\x00" in relative_path:
        return None
    if relative_path.startswith(("/", "\\")) or "\\" in relative_path:
        return None
    parts = relative_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    if ":" in parts[0]:
        return None

    try:
        resolved_root = Path(root).resolve()
    except (OSError, RuntimeError):
        return None
    target = None
    for trusted_relative, trusted_target in _trusted_file_inventory(str(resolved_root)).items():
        if trusted_relative == relative_path:
            target = trusted_target
            break
    if target is None:
        return None
    try:
        target.relative_to(resolved_root)
    except ValueError:
        return None
    return target
