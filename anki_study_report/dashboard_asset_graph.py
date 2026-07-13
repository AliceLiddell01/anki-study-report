"""Resolve the complete Vite dashboard asset graph without importing Anki."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import PurePosixPath
import re
from typing import Any


_URI_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", flags=re.IGNORECASE)


class _DashboardHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.refs.append(values["src"] or "")
        if tag == "link" and values.get("href"):
            rel = str(values.get("rel") or "").lower()
            if "stylesheet" in rel or "modulepreload" in rel:
                self.refs.append(values["href"] or "")


def extract_dashboard_html_refs(index_html: str) -> dict[str, list[str]]:
    """Return safe local HTML refs and unsafe refs separately."""

    parser = _DashboardHtmlParser()
    parser.feed(index_html)
    refs: set[str] = set()
    unsafe: set[str] = set()
    for raw_ref in parser.refs:
        normalized, reason = _normalize_ref(raw_ref, allow_root_relative=True)
        if reason:
            unsafe.add(raw_ref)
        elif normalized:
            refs.add(normalized)
    return {"assets": sorted(refs), "unsafe": sorted(unsafe)}


def resolve_dashboard_asset_graph(index_html: str, manifest_json: str) -> dict[str, list[str]]:
    """Resolve every file reachable from the HTML-linked Vite entry.

    The returned asset names are relative to the dashboard static root. Errors
    describe malformed or incomplete manifest edges; unsafe contains path or
    URI references that must never be resolved on disk.
    """

    html = extract_dashboard_html_refs(index_html)
    errors: set[str] = set()
    unsafe: set[str] = set(html["unsafe"])
    reachable_assets: set[str] = set(html["assets"])
    try:
        manifest = json.loads(manifest_json)
    except (TypeError, json.JSONDecodeError) as exc:
        return {"assets": sorted(reachable_assets), "errors": [f"invalid_manifest_json:{exc.msg}"], "unsafe": sorted(unsafe)}
    if not isinstance(manifest, dict):
        return {"assets": sorted(reachable_assets), "errors": ["manifest_root_not_object"], "unsafe": sorted(unsafe)}

    by_file: dict[str, list[str]] = {}
    for key, value in manifest.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            errors.add("manifest_entry_not_object")
            continue
        file_name, reason = _normalize_ref(value.get("file"), allow_root_relative=False)
        if reason:
            unsafe.add(str(value.get("file")))
        elif file_name:
            by_file.setdefault(file_name, []).append(key)

    html_js = [ref for ref in html["assets"] if PurePosixPath(ref).suffix.lower() == ".js"]
    entry_keys: set[str] = set()
    for ref in html_js:
        keys = by_file.get(ref, [])
        if len(keys) != 1:
            errors.add(f"html_entry_not_in_manifest:{ref}")
        else:
            entry_keys.add(keys[0])
    if not entry_keys:
        errors.add("manifest_entry_not_linked_from_html")

    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visited:
            return
        value = manifest.get(key)
        if not isinstance(value, dict):
            errors.add(f"missing_manifest_entry:{key}")
            return
        visited.add(key)
        _collect_manifest_refs(value, "file", reachable_assets, unsafe, errors)
        _collect_manifest_refs(value, "css", reachable_assets, unsafe, errors, many=True)
        _collect_manifest_refs(value, "assets", reachable_assets, unsafe, errors, many=True)
        for edge_name in ("imports", "dynamicImports"):
            edges = value.get(edge_name, [])
            if edges is None:
                continue
            if not isinstance(edges, list):
                errors.add(f"manifest_{edge_name}_not_array:{key}")
                continue
            for dependency in edges:
                if not isinstance(dependency, str) or not dependency:
                    errors.add(f"manifest_{edge_name}_invalid:{key}")
                    continue
                visit(dependency)

    for key in sorted(entry_keys):
        visit(key)
    return {"assets": sorted(reachable_assets), "errors": sorted(errors), "unsafe": sorted(unsafe)}


def _collect_manifest_refs(
    entry: dict[str, Any],
    field: str,
    assets: set[str],
    unsafe: set[str],
    errors: set[str],
    *,
    many: bool = False,
) -> None:
    raw_values = entry.get(field, [] if many else None)
    values = raw_values if many and isinstance(raw_values, list) else [raw_values]
    if many and not isinstance(raw_values, list):
        errors.add(f"manifest_{field}_not_array")
        return
    for raw_ref in values:
        if raw_ref is None:
            if field == "file":
                errors.add("manifest_file_missing")
            continue
        normalized, reason = _normalize_ref(raw_ref, allow_root_relative=False)
        if reason:
            unsafe.add(str(raw_ref))
        elif normalized:
            assets.add(normalized)


def _normalize_ref(raw_ref: Any, *, allow_root_relative: bool) -> tuple[str | None, str | None]:
    if not isinstance(raw_ref, str):
        return None, "not_string"
    ref = raw_ref.split("#", 1)[0].split("?", 1)[0].strip()
    if not ref or _URI_SCHEME.match(ref) or ref.startswith("//") or "\\" in ref:
        return (None, None) if not ref or _URI_SCHEME.match(ref) else (None, "external_or_invalid")
    if ref.startswith("/"):
        if not allow_root_relative:
            return None, "root_relative_manifest_ref"
        ref = ref.lstrip("/")
    if ref.startswith("./"):
        ref = ref[2:]
    path = PurePosixPath(ref)
    if not path.parts or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None, "path_escape"
    return path.as_posix(), None
