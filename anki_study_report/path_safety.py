"""Small filesystem-boundary helpers for dashboard-controlled paths."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any


class TrustedLeafName:
    """Validated leaf selector that resolves only through a trusted inventory.

    The object intentionally does not implement ``os.PathLike``. When used as
    ``trusted_root / selector``, ``pathlib`` delegates to ``__rtruediv__`` and
    the selector returns a filesystem-discovered target instead of joining the
    request-derived filename into a path expression.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"TrustedLeafName({self._name!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TrustedLeafName):
            return self._name == other._name
        if isinstance(other, str):
            return self._name == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._name)

    def __rtruediv__(self, root: object) -> Path:
        target = trusted_leaf_file_from_directory(Path(root), self._name)
        if target is None:
            raise FileNotFoundError(self._name)
        return target


def _validated_leaf_text(value: Any) -> str | None:
    text = str(value or "")
    if not text or "\x00" in text or text in {".", ".."} or ":" in text:
        return None
    if "/" in text or "\\" in text:
        return None
    leaf = os.path.basename(text)
    if leaf != text:
        return None
    return leaf


def safe_leaf_name(value: Any) -> TrustedLeafName | None:
    """Return a validated selector for one filename component, never a path."""

    text = _validated_leaf_text(value)
    return TrustedLeafName(text) if text is not None else None


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


@lru_cache(maxsize=16)
def _trusted_leaf_inventory(root_text: str, directory_mtime_ns: int) -> dict[str, Path]:
    """Index direct regular files below a trusted directory."""

    del directory_mtime_ns
    root = Path(root_text).resolve()
    inventory: dict[str, Path] = {}
    try:
        candidates = root.iterdir()
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
                relative = resolved.relative_to(root)
                if len(relative.parts) != 1 or not resolved.is_file():
                    continue
            except (OSError, RuntimeError, ValueError):
                continue
            name = candidate.name
            if name and name not in inventory:
                inventory[name] = resolved
    except OSError:
        return {}
    return inventory


def trusted_leaf_file_from_directory(
    root: Path,
    leaf_name: str | TrustedLeafName,
) -> Path | None:
    """Select one direct trusted file without joining request data to a path."""

    safe_name = (
        leaf_name.name
        if isinstance(leaf_name, TrustedLeafName)
        else _validated_leaf_text(leaf_name)
    )
    if safe_name is None:
        return None
    try:
        resolved_root = Path(root).resolve(strict=True)
        directory_mtime_ns = resolved_root.stat().st_mtime_ns
    except (OSError, RuntimeError):
        return None

    target = None
    for trusted_name, trusted_target in _trusted_leaf_inventory(
        str(resolved_root),
        directory_mtime_ns,
    ).items():
        if trusted_name == safe_name:
            target = trusted_target
            break
    if target is None:
        return None

    try:
        current = target.resolve(strict=True)
        current.relative_to(resolved_root)
        if not current.is_file():
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return current
