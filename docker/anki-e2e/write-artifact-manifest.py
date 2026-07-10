#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

from artifact_paths import ArtifactPaths


PAGE_ROUTES = {
    "today": "#/home",
    "calendar": "#/calendar",
    "decks": "#/decks",
    "profile": "#/profile",
    "tools": "#/actions",
    "settings/data": "#/settings",
    "settings/server": "#/settings/server",
    "settings/sources": "#/integrations",
    "settings/logs": "#/logs",
}


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
    (paths.root / "artifact-manifest.json").write_text(serialized + "\n", encoding="utf-8")
    return 0


def build_manifest(paths: ArtifactPaths, *, status: str, anki_version: str) -> dict[str, Any]:
    report_paths = files_under(paths, paths.reports)
    screenshot_paths = files_under(paths, paths.screenshots)
    return {
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


if __name__ == "__main__":
    raise SystemExit(main())
