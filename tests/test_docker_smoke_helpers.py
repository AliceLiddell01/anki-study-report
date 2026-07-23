from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "docker" / "anki-e2e"


def load_e2e_module(file_name: str, module_name: str):
    path = E2E / file_name
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


def load_smoke_api_module():
    return load_e2e_module("smoke-api.py", "anki_study_report_smoke_api")


def test_smoke_api_uses_runtime_real_deck_reports() -> None:
    source = (E2E / "smoke-api.py").read_text(encoding="utf-8")
    for report in (
        "real-deck-manifest-report.json",
        "real-deck-import-report.json",
        "collection-inventory.json",
        "anchor-resolution-report.json",
        "scenario-application-report.json",
    ):
        assert report in source
    assert "committed-real-apkg-only" in source
    assert "syntheticNotes" in source
    assert "syntheticCards" in source


def test_smoke_api_triage_request_uses_current_v4_contract() -> None:
    smoke_api = load_smoke_api_module()
    assert smoke_api.triage_request(["11", "12"]) == {
        "schemaVersion": 4,
        "dataset": "search_workset",
        "cardIds": ["11", "12"],
        "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
        "limit": 2,
    }


def test_smoke_api_confirmed_profile_maps_real_structure_fields() -> None:
    smoke_api = load_smoke_api_module()
    item = {
        "structure": {
            "noteTypeId": "123",
            "name": "Programming",
            "fingerprint": {"algorithm": "sha256", "value": "a" * 64},
            "fields": [
                {"ordinal": 0, "name": "Question"},
                {"ordinal": 1, "name": "Answer"},
            ],
        }
    }
    definition = {
        "displayName": "Programming",
        "mappings": [
            {"role": "question", "field": "Question"},
            {"role": "answer", "field": "Answer"},
        ],
        "checks": [
            {"checkId": "question-required", "kind": "non_empty", "roles": ["question"], "mode": "any", "priority": "high"},
        ],
    }

    profile = smoke_api.confirmed_profile(item, definition)

    assert profile["profileId"] == "note-type-123"
    assert profile["fieldMappings"] == [
        {"role": "question", "fields": [{"ordinal": 0, "name": "Question"}]},
        {"role": "answer", "fields": [{"ordinal": 1, "name": "Answer"}]},
    ]
    assert profile["expectedFingerprint"] == item["structure"]["fingerprint"]
    assert "rawFields" not in json.dumps(profile)


def test_smoke_api_asset_contract_discovers_current_assets(monkeypatch) -> None:
    smoke_api = load_smoke_api_module()

    def fetch_bytes(_base_url, path, _token, _params=None):
        if path == "/":
            return 200, "text/html", b'<link rel="stylesheet" href="/assets/app.css"><script src="/assets/app.js"></script>'
        if path == "/assets/app.css":
            return 200, "text/css", b".cards-inbox-page{}"
        if path == "/assets/app.js":
            return 200, "application/javascript", b"window.ready=true"
        raise AssertionError(path)

    monkeypatch.setattr(smoke_api, "fetch_bytes", fetch_bytes)
    result = smoke_api.assert_dashboard_assets("http://127.0.0.1", "token")
    assert result["assetCount"] == 2
    assert {item["path"] for item in result["assets"]} == {"/assets/app.css", "/assets/app.js"}


def test_browser_smoke_consumes_runtime_anchors_and_avoids_fixture_literals() -> None:
    source = (E2E / "smoke-browser.mjs").read_text(encoding="utf-8")
    progress = (E2E / "browser-progress.mjs").read_text(encoding="utf-8")
    assert "anchor-resolution-report.json" in source
    assert "buildBrowserPlan" in source
    assert 'candidate.kind === "native-preview"' in source
    assert 'Object.freeze(["words-preview", "grammar-preview", "java-preview"])' in progress
    assert "renderSource === \"anki_native\"" in source
    assert "unexpectedExternalRequests" in source
    combined = f"{source}\n{progress}"
    for stale in (
        "要望",
        "要.gif",
        "E2E Japanese Vocabulary",
        "E2E Programming",
        "asr-e2e-render-fixtures.apkg",
        "applyApkgDeckFilter",
        "captureApkg",
    ):
        assert stale not in combined


def test_artifact_paths_create_category_directories(tmp_path: Path) -> None:
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


def test_required_success_artifacts_include_real_deck_evidence() -> None:
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_required_names")
    required = set(manifest_module.REQUIRED_SUCCESS_ARTIFACTS)
    assert {
        "reports/real-deck-manifest-report.json",
        "reports/real-deck-import-report.json",
        "reports/collection-inventory.json",
        "reports/anchor-resolution-report.json",
        "reports/scenario-application-report.json",
    } <= required


def test_artifact_manifest_uses_relative_redacted_real_deck_paths(tmp_path: Path) -> None:
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    create_required_success_artifacts(manifest_module, paths)
    files = [
        paths.diagnostics / "anki-startup-tail.txt",
        paths.html / "cards" / "real-deck-shadow-dom-first.html",
        paths.screenshots / "navigation" / "avatar-menu-light.png",
        paths.screenshots / "pages" / "home" / "light.png",
        paths.screenshots / "pages" / "settings" / "logs" / "dark.png",
        paths.screenshots / "states" / "cards" / "real-deck-inbox" / "light.png",
        paths.screenshots / "zoom-125" / "settings" / "report.png",
        paths.screenshots / "cards" / "real-decks" / "words-preview" / "dark.png",
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
    assert {entry.get("fixture") for entry in manifest["screenshots"] if entry["kind"] == "cards"} == {"real-decks"}
    assert any(entry.get("kind") == "state" and entry.get("state") == "real-deck-inbox" for entry in manifest["screenshots"])
    assert any(entry.get("kind") == "zoom" and entry.get("route") == "#/settings" and entry.get("scale") == 1.25 for entry in manifest["screenshots"])
    assert str(tmp_path) not in serialized
    assert "secret-dashboard-token" not in serialized
    manifest_module.assert_manifest_is_redacted(serialized)
    with pytest.raises(ValueError):
        manifest_module.assert_manifest_is_redacted('{"url":"http://127.0.0.1:8766/?token=secret"}')


def test_artifact_manifest_missing_required_path_fails(tmp_path: Path) -> None:
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_required")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    create_required_success_artifacts(manifest_module, paths)
    (paths.package / "anki_study_report.ankiaddon").unlink()

    with pytest.raises(ValueError, match="Required E2E artifacts are missing"):
        manifest_module.build_manifest(paths, status="success", anki_version="26.05")


def test_artifact_manifest_omits_missing_optional_paths(tmp_path: Path) -> None:
    manifest_module = load_e2e_module("write-artifact-manifest.py", "anki_study_report_artifact_manifest_optional")
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()

    manifest = manifest_module.build_manifest(paths, status="failed", anki_version="26.05")

    assert manifest["runtime"] == {"dashboardReady": None, "events": None}
    assert manifest_module.manifest_indexed_paths(manifest) == []


def test_resource_reports_are_optional_only_when_telemetry_is_disabled(tmp_path: Path, monkeypatch) -> None:
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
def test_artifact_manifest_rejects_invalid_or_missing_indexed_paths(tmp_path: Path, bad_path: str, message: str) -> None:
    manifest_module = load_e2e_module(
        "write-artifact-manifest.py",
        f"anki_study_report_artifact_manifest_bad_{message.replace(' ', '_')}",
    )
    paths = manifest_module.ArtifactPaths.from_root(tmp_path / "artifacts")
    paths.ensure()
    manifest = {"status": "failed", "runtime": {"events": bad_path}, "artifacts": {}, "screenshots": []}

    with pytest.raises(ValueError, match=message):
        manifest_module.validate_manifest(paths, manifest)


def test_artifact_manifest_rejects_duplicate_paths(tmp_path: Path) -> None:
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


def test_artifact_manifest_root_override_and_readiness_token_are_safe(tmp_path: Path) -> None:
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


def test_browser_artifact_resolver_builds_deterministic_nested_paths(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to verify the browser artifact resolver.")
    helper_uri = (E2E / "artifact-paths.mjs").as_uri()
    root = (tmp_path / "artifacts").as_posix()
    script = f"""
      import {{ resolveArtifactPaths, relativeArtifactPath }} from {json.dumps(helper_uri)};
      const paths = resolveArtifactPaths({json.dumps(root)});
      console.log(JSON.stringify([
        relativeArtifactPath(paths, paths.pageScreenshot('settings/server', 'dark')),
        relativeArtifactPath(paths, paths.navigationScreenshot('light')),
        relativeArtifactPath(paths, paths.stateScreenshot('cards', 'real-deck-inbox', 'light')),
        relativeArtifactPath(paths, paths.zoomScreenshot('settings/report')),
        relativeArtifactPath(paths, paths.cardsScreenshot('real-decks', 'words-preview', 'dark')),
      ]));
    """
    result = subprocess.run([node, "--input-type=module", "--eval", script], check=True, capture_output=True, text=True)

    assert json.loads(result.stdout) == [
        "screenshots/pages/settings/server/dark.png",
        "screenshots/navigation/avatar-menu-light.png",
        "screenshots/states/cards/real-deck-inbox/light.png",
        "screenshots/zoom-125/settings/report.png",
        "screenshots/cards/real-decks/words-preview/dark.png",
    ]


def test_restart_verifier_retriggers_only_an_idle_sender_with_pending_events() -> None:
    verifier = load_e2e_module("verify-telemetry-restart.py", "anki_study_report_verify_telemetry_restart")

    assert verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 1, "senderState": "idle"}})
    assert not verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 1, "senderState": "busy"}})
    assert not verifier.delivery_needs_trigger({"telemetryClient": {"pendingEventCount": 0, "senderState": "idle"}})


def test_restart_anki_preserves_imported_note_type_content() -> None:
    source = (E2E / "restart-anki.sh").read_text(encoding="utf-8")

    assert "mutate-inspection-profile-fixture.py" not in source
    assert "without mutating imported note types, fields, templates, or media" in source
    assert not (E2E / "mutate-inspection-profile-fixture.py").exists()
