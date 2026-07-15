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
    assert paths.addon_log.name == "anki_study_report.log"


def create_required_success_artifacts(manifest_module, paths) -> None:
    for relative_path in (*manifest_module.REQUIRED_SUCCESS_ARTIFACTS, *manifest_module.RESOURCE_ARTIFACTS):
        file_path = paths.root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test", encoding="utf-8")


def test_artifact_manifest_uses_relative_redacted_paths(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    create_required_success_artifacts(manifest_module, paths)
    files = [
        paths.diagnostics / "anki-startup-tail.txt",
        paths.html / "cards" / "synthetic-shadow-dom-first.html",
        paths.screenshots / "navigation" / "avatar-menu-light.png",
        paths.screenshots / "pages" / "today" / "light.png",
        paths.screenshots / "pages" / "settings" / "logs" / "dark.png",
        paths.screenshots / "states" / "decks" / "selected-parent" / "light.png",
        paths.screenshots / "zoom-125" / "settings" / "report.png",
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
    assert {entry.get("route") for entry in manifest["screenshots"]} >= {"#/home", "#/settings/logs", "#/cards"}
    assert {entry.get("fixture") for entry in manifest["screenshots"] if entry["kind"] == "cards"} == {"synthetic", "apkg"}
    assert any(entry.get("kind") == "state" and entry.get("state") == "selected-parent" for entry in manifest["screenshots"])
    assert any(entry.get("kind") == "zoom" and entry.get("route") == "#/settings" and entry.get("scale") == 1.25 for entry in manifest["screenshots"])
    assert str(tmp_path) not in serialized
    assert "secret-dashboard-token" not in serialized
    manifest_module.assert_manifest_is_redacted(serialized)
    with pytest.raises(ValueError):
        manifest_module.assert_manifest_is_redacted('{"url":"http://127.0.0.1:8766/?token=secret"}')


def test_artifact_manifest_missing_required_path_fails(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_required")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    create_required_success_artifacts(manifest_module, paths)
    (paths.package / "anki_study_report.ankiaddon").unlink()

    with pytest.raises(ValueError, match="Required E2E artifacts are missing"):
        manifest_module.build_manifest(paths, status="success", anki_version="26.05")


def test_artifact_manifest_omits_missing_optional_paths(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_optional")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()

    manifest = manifest_module.build_manifest(paths, status="failed", anki_version="26.05")

    assert manifest["runtime"] == {"dashboardReady": None, "events": None}
    assert manifest_module.manifest_indexed_paths(manifest) == []


def test_resource_reports_are_optional_only_when_telemetry_is_disabled(tmp_path: Path, monkeypatch):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_no_resources")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    for relative_path in manifest_module.REQUIRED_SUCCESS_ARTIFACTS:
        file_path = paths.root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test", encoding="utf-8")
    monkeypatch.setenv("ANKI_E2E_RESOURCE_TELEMETRY", "0")

    manifest = manifest_module.build_manifest(paths, status="success", anki_version="26.05")

    assert manifest["execution"]["resourceTelemetry"] is False
    assert not any(path in manifest_module.manifest_indexed_paths(manifest) for path in manifest_module.RESOURCE_ARTIFACTS)


@pytest.mark.parametrize(
    ("bad_path", "message"),
    [
        ("diagnostics/anki-study-report.log", "missing file"),
        ("C:/temp/secret.log", "must be relative"),
        ("../secret.log", "traversal"),
    ],
)
def test_artifact_manifest_rejects_invalid_or_missing_indexed_paths(
    tmp_path: Path,
    bad_path: str,
    message: str,
):
    manifest_module = load_e2e_module(
        "write-artifact-manifest.py",
        f"anki_study_report_artifact_manifest_bad_{message.replace(' ', '_')}",
    )
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    manifest = {
        "status": "failed",
        "runtime": {"events": bad_path},
        "artifacts": {},
        "screenshots": [],
    }

    with pytest.raises(ValueError, match=message):
        manifest_module.validate_manifest(paths, manifest)


def test_artifact_manifest_rejects_duplicate_paths(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_duplicate")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    file_path = paths.reports / "same.json"
    file_path.write_text("{}", encoding="utf-8")
    manifest = {
        "status": "failed",
        "runtime": {},
        "artifacts": {"reports": ["reports/same.json"]},
        "screenshots": [{"path": "reports/same.json"}],
    }

    with pytest.raises(ValueError, match="duplicate paths"):
        manifest_module.validate_manifest(paths, manifest)


def test_artifact_manifest_root_override_and_readiness_token_are_safe(tmp_path: Path):
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_override")
    override_root = tmp_path / "custom-artifacts"
    paths = manifest_module.ArtifactPaths.from_root(override_root)
    paths.ensure()
    create_required_success_artifacts(manifest_module, paths)
    secret = "secret-dashboard-token"
    (paths.runtime / "dashboard-ready.json").write_text(
        json.dumps({"token": secret, "baseUrl": "http://127.0.0.1:8766"}),
        encoding="utf-8",
    )

    manifest = manifest_module.build_manifest(paths, status="success", anki_version="26.05")
    serialized = json.dumps(manifest)

    assert all(not Path(path).is_absolute() for path in manifest_module.manifest_indexed_paths(manifest))
    assert secret not in serialized
    assert str(override_root) not in serialized


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
        relativeArtifactPath(paths, paths.stateScreenshot('decks', 'selected-parent', 'light')),
        relativeArtifactPath(paths, paths.zoomScreenshot('settings/report')),
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
        "screenshots/states/decks/selected-parent/light.png",
        "screenshots/zoom-125/settings/report.png",
        "screenshots/cards/apkg/anki-preview/dark.png",
    ]


def test_restart_verifier_retriggers_only_an_idle_sender_with_pending_events():
    verifier = load_e2e_module("verify-telemetry-restart.py", "anki_study_report_verify_telemetry_restart")

    assert verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 1, "senderState": "idle"}})
    assert not verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 1, "senderState": "busy"}})
    assert not verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 0, "senderState": "idle"}})
