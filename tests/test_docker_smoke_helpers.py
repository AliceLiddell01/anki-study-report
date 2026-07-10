from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def load_smoke_api_module():
    return load_e2e_module("smoke-api.py", "anki_study_report_smoke_api")


def load_e2e_module(file_name: str, module_name: str):
    path = Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def row(label: str) -> dict[str, str]:
    return {"source": label}


def test_smoke_api_card_rows_prefer_canonical_attention_cards():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report(
        {
            "attentionCards": [row("attentionCards")],
            "cards": [row("cards")],
        }
    ) == [row("attentionCards")]


def test_smoke_api_card_rows_keep_empty_canonical_result():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report(
        {
            "attentionCards": [],
            "cards": [row("cards")],
        }
    ) == []


def test_smoke_api_card_rows_ignore_removed_cards_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"cards": [row("cards")]}) == []


def test_smoke_api_card_rows_ignore_removed_card_issues_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"cardIssues": [row("cardIssues")]}) == []


def test_smoke_api_card_rows_ignore_removed_problem_cards_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"problemCards": [row("problemCards")]}) == []


def test_artifact_paths_create_category_directories(tmp_path: Path):
    artifact_paths = load_e2e_module("artifact_paths.py", "anki_study_report_artifact_paths")

    paths = artifact_paths.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()

    assert paths.runtime.is_dir()
    assert paths.diagnostics.is_dir()
    assert paths.reports.is_dir()
    assert paths.html.is_dir()
    assert paths.screenshots.is_dir()
    assert paths.package.is_dir()
    assert paths.relative(paths.runtime / "dashboard-ready.json") == "runtime/dashboard-ready.json"


def test_artifact_manifest_uses_relative_redacted_paths(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    files = [
        paths.runtime / "dashboard-ready.json",
        paths.runtime / "addon-e2e-events.jsonl",
        paths.diagnostics / "anki-startup-tail.txt",
        paths.reports / "browser-smoke-first.json",
        paths.html / "cards" / "synthetic-shadow-dom-first.html",
        paths.package / "anki_study_report.ankiaddon",
        paths.screenshots / "navigation" / "avatar-menu-light.png",
        paths.screenshots / "pages" / "today" / "light.png",
        paths.screenshots / "pages" / "settings" / "logs" / "dark.png",
        paths.screenshots / "cards" / "synthetic" / "table" / "light.png",
        paths.screenshots / "cards" / "apkg" / "anki-preview" / "dark.png",
    ]
    for file_path in files:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"test")

    manifest = manifest_module.build_manifest(paths, status="success", anki_version="26.05")
    serialized = json.dumps(manifest)

    assert manifest["status"] == "success"
    assert manifest["runtime"] == {
        "dashboardReady": "runtime/dashboard-ready.json",
        "events": "runtime/addon-e2e-events.jsonl",
    }
    assert all(not Path(entry["path"]).is_absolute() for entry in manifest["screenshots"])
    assert {entry.get("route") for entry in manifest["screenshots"]} >= {"#/home", "#/logs", "#/cards"}
    assert {entry.get("fixture") for entry in manifest["screenshots"] if entry["kind"] == "cards"} == {"synthetic", "apkg"}
    assert str(tmp_path) not in serialized
    manifest_module.assert_manifest_is_redacted(serialized)
    with pytest.raises(ValueError):
        manifest_module.assert_manifest_is_redacted('{"url":"http://127.0.0.1:8766/?token=secret"}')


def test_browser_artifact_resolver_builds_deterministic_nested_paths(tmp_path: Path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to verify the browser artifact resolver.")
    helper_uri = (Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / "artifact-paths.mjs").as_uri()
    root = (tmp_path / "artifacts").as_posix()
    script = f"""
      import {{ resolveArtifactPaths, relativeArtifactPath }} from {json.dumps(helper_uri)};
      const paths = resolveArtifactPaths({json.dumps(root)});
      console.log(JSON.stringify([
        relativeArtifactPath(paths, paths.pageScreenshot('settings/server', 'dark')),
        relativeArtifactPath(paths, paths.navigationScreenshot('light')),
        relativeArtifactPath(paths, paths.cardsScreenshot('apkg', 'ankiPreview', 'dark')),
      ]));
    """
    result = subprocess.run(
        [node, "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == [
        "screenshots/pages/settings/server/dark.png",
        "screenshots/navigation/avatar-menu-light.png",
        "screenshots/cards/apkg/anki-preview/dark.png",
    ]
