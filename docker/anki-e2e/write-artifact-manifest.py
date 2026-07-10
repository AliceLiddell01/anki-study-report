#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

from artifact_paths import ArtifactPaths, CANONICAL_ADDON_LOG_NAME


PAGE_ROUTES = {
    "today": "#/home",
    "calendar": "#/calendar",
    "decks": "#/decks",
    "profile": "#/profile",
    "tools": "#/actions",
    "settings/report": "#/settings",
    "settings/data": "#/settings/data",
    "settings/server": "#/settings/server",
    "settings/sources": "#/settings/sources",
    "settings/logs": "#/settings/logs",
}

REQUIRED_SUCCESS_ARTIFACTS = (
    "runtime/dashboard-ready.json",
    "runtime/addon-e2e-events.jsonl",
    f"diagnostics/{CANONICAL_ADDON_LOG_NAME}",
    "reports/api-health-first.json",
    "reports/api-smoke-first.json",
    "reports/browser-smoke-first.json",
    "package/anki_study_report.ankiaddon",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a redacted E2E artifact index.")
    parser.add_argument("--root", default=os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS", "/e2e/artifacts"))
    parser.add_argument("--status", choices=("success", "failed"), required=True)
    parser.add_argument("--anki-version", default=os.environ.get("ANKI_VERSION", "unknown"))
    args = parser.parse_args()

    paths = ArtifactPaths.from_root(args.root)
    paths.root.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(paths, status=args.status, anki_version=args.anki_version)
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2)
    assert_manifest_is_redacted(serialized)
    validate_manifest(paths, manifest)
    (paths.root / "artifact-manifest.json").write_text(serialized + "\n", encoding="utf-8")
    return 0


def build_manifest(paths: ArtifactPaths, *, status: str, anki_version: str) -> dict[str, Any]:
    report_paths = files_under(paths, paths.reports)
    screenshot_paths = files_under(paths, paths.screenshots)
    manifest = {
        "artifactSchemaVersion": 1,
        "status": status,
        "ankiVersion": str(anki_version),
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime": {
            "dashboardReady": relative_if_exists(paths, paths.runtime / "dashboard-ready.json"),
            "events": relative_if_exists(paths, paths.runtime / "addon-e2e-events.jsonl"),
        },
        "artifacts": {
            "reports": report_paths,
            "diagnostics": files_under(paths, paths.diagnostics),
            "html": files_under(paths, paths.html),
            "package": files_under(paths, paths.package),
        },
        "screenshots": [describe_screenshot(relative_path) for relative_path in screenshot_paths],
    }
    validate_manifest(paths, manifest)
    return manifest


def files_under(paths: ArtifactPaths, directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(paths.relative(path) for path in directory.rglob("*") if path.is_file())


def relative_if_exists(paths: ArtifactPaths, path: Path) -> str | None:
    return paths.relative(path) if path.is_file() else None


def describe_screenshot(relative_path: str) -> dict[str, Any]:
    parts = Path(relative_path).parts
    result: dict[str, Any] = {"path": relative_path}
    if len(parts) >= 4 and parts[:2] == ("screenshots", "pages"):
        page_name = "/".join(parts[2:-1])
        result.update(
            {
                "kind": "page",
                "route": PAGE_ROUTES.get(page_name),
                "theme": Path(parts[-1]).stem,
            }
        )
    elif len(parts) >= 3 and parts[:2] == ("screenshots", "navigation"):
        match = re.fullmatch(r"avatar-menu-(light|dark)", Path(parts[-1]).stem)
        result.update(
            {
                "kind": "navigation",
                "route": "#/home",
                "theme": match.group(1) if match else None,
            }
        )
    elif len(parts) >= 5 and parts[:2] == ("screenshots", "cards"):
        result.update(
            {
                "kind": "cards",
                "route": "#/cards",
                "fixture": parts[2],
                "cardsMode": "ankiPreview" if parts[3] == "anki-preview" else parts[3],
                "theme": Path(parts[-1]).stem,
            }
        )
    else:
        result["kind"] = "failure" if "failures" in parts else "other"
    return result


def assert_manifest_is_redacted(serialized: str) -> None:
    lowered = serialized.lower()
    if "token=" in lowered or "?token" in lowered:
        raise ValueError("Artifact manifest contains a token-bearing URL.")
    if re.search(r"https?://127\.0\.0\.1:\d+/.{0,200}token", serialized, flags=re.IGNORECASE):
        raise ValueError("Artifact manifest contains a local dashboard token reference.")


def validate_manifest(paths: ArtifactPaths, manifest: dict[str, Any]) -> None:
    indexed = manifest_indexed_paths(manifest)
    duplicates = sorted(path for path in set(indexed) if indexed.count(path) > 1)
    if duplicates:
        raise ValueError(f"Artifact manifest contains duplicate paths: {', '.join(duplicates)}")

    root = paths.root.resolve()
    for relative_path in indexed:
        normalized = _validated_relative_path(relative_path)
        target = (root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Artifact path escapes artifact root: {relative_path}") from error
        if not target.is_file():
            raise ValueError(f"Artifact manifest references a missing file: {relative_path}")

    if str(manifest.get("status") or "") == "success":
        missing = [path for path in REQUIRED_SUCCESS_ARTIFACTS if path not in indexed]
        if missing:
            raise ValueError(f"Required E2E artifacts are missing: {', '.join(missing)}")


def manifest_indexed_paths(manifest: dict[str, Any]) -> list[str]:
    indexed: list[str] = []
    runtime = manifest.get("runtime")
    if isinstance(runtime, dict):
        indexed.extend(value for value in runtime.values() if isinstance(value, str) and value)
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for entries in artifacts.values():
            if isinstance(entries, list):
                indexed.extend(value for value in entries if isinstance(value, str) and value)
    screenshots = manifest.get("screenshots")
    if isinstance(screenshots, list):
        for entry in screenshots:
            if isinstance(entry, dict) and isinstance(entry.get("path"), str) and entry["path"]:
                indexed.append(entry["path"])
    return indexed


def _validated_relative_path(value: str) -> str:
    raw = str(value or "")
    if not raw:
        raise ValueError("Artifact manifest contains an empty path.")
    if "\\" in raw:
        raise ValueError(f"Artifact path must use POSIX separators: {raw}")
    candidate = Path(raw)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", raw):
        raise ValueError(f"Artifact path must be relative: {raw}")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"Artifact path contains traversal or invalid segments: {raw}")
    return candidate.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
