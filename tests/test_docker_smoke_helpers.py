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


def test_smoke_api_asset_contract_executes_current_cards_inbox_marker(monkeypatch, tmp_path):
    smoke_api = load_smoke_api_module()
    css = " ".join((
        "[data-theme=light]", ".topbar-surface", ".shadow-panel",
        ".cards-inbox-page", ".anki-card-shadow-preview",
    )).encode()

    def fetch_bytes(_base_url, path, _token, _params=None):
        if path == "/":
            return 200, "text/html", b'<link rel="stylesheet" href="/assets/app.css"><script src="/assets/app.js"></script>'
        if path == "/assets/app.css":
            return 200, "text/css", css
        if path == "/assets/app.js":
            return 200, "application/javascript", b"window.ready=true"
        raise AssertionError(path)

    monkeypatch.setattr(smoke_api, "fetch_bytes", fetch_bytes)
    result = smoke_api.assert_dashboard_assets("http://127.0.0.1", "token", tmp_path, "unit")
    assert result["missingCssMarkers"] == []
    assert result["cssAssetCount"] == 1


def test_smoke_api_inspection_profile_requests_execute_current_search_and_triage_schemas(monkeypatch):
    smoke_api = load_smoke_api_module()
    calls = []

    def post_json(base_url, path, token, payload):
        calls.append((base_url, path, token, payload))
        return {"items": [{"cardId": "11"}]}

    monkeypatch.setattr(smoke_api, "post_json", post_json)
    assert smoke_api.search_note_type_cards("http://dashboard", "token", "7", "japanese") == [{"cardId": "11"}]
    search_payload = calls[0][3]
    assert search_payload["schemaVersion"] == 2
    assert search_payload["mode"] == "cards"
    assert search_payload["filters"] == [{"type": "note_type", "noteTypeId": "7"}]

    triage = smoke_api.inspection_triage_request(["11", "12"])
    assert triage["schemaVersion"] == 4
    assert triage["dataset"] == "search_workset"
    assert triage["cardIds"] == ["11", "12"]
    recheck = smoke_api.inspection_recheck_request({
        "cardId": "11",
        "noteId": "21",
        "reasons": [{"reasonId": "learning:learning.leech"}],
    })
    assert recheck == {
        "schemaVersion": 1,
        "cardId": "11",
        "expectedNoteId": "21",
        "reasonIds": ["learning:learning.leech"],
        "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
    }


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        ("cards", True),
        ("full", True),
        ("global", False),
        ("notifications", False),
    ],
)
def test_smoke_api_runs_inspection_profiles_for_cards_and_full(
    scope: str, expected: bool
):
    smoke_api = load_smoke_api_module()

    assert smoke_api.should_run_inspection_profiles(scope) is expected


def test_smoke_browser_inspection_profiles_uses_unconfigured_suggestion_source():
    source = (
        Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / "smoke-browser.mjs"
    ).read_text(encoding="utf-8")
    workspace = source.split("async function assertInspectionProfilesWorkspace", 1)[1].split(
        "async function captureZoomProof", 1
    )[0]

    assert 'name: /E2E Japanese Vocabulary/' in workspace
    assert 'name: /E2E Generic Basic/' in workspace
    assert 'sourceLifecycleText.includes("Не настроен")' in workspace
    assert 'page.locator("#inspection-basic-priority-0")' in workspace
    assert 'initialPriority === "high" ? "medium" : "high"' in workspace
    assert 'name: "Проверить настройку", exact: true' in workspace
    assert 'name: "Проверить профиль", exact: true' not in workspace
    assert 'getByText("Профиль прошёл backend-проверку.", { exact: true })' in workspace
    assert "Проверка и ограниченный пример" not in workspace
    assert "Восстановить предложенную настройку" not in workspace
    assert "Использовать подсказку" not in workspace
    assert 'suggestionSourceName: "E2E Generic Basic"' in workspace

    japanese_state = workspace.index("await japanese.click()")
    unconfigured_source = workspace.index("await suggestionSource.click()")
    apply_suggestion = workspace.index('page.locator("#inspection-basic-priority-0")')
    assert japanese_state < unconfigured_source < apply_suggestion


def test_smoke_browser_search_contract_uses_schema_v2_requests():
    source = (
        Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / "smoke-browser.mjs"
    ).read_text(encoding="utf-8")
    query_contract = source.split("async function assertSearchQueryContract", 1)[1].split(
        "async function assertSafeEntityActions", 1
    )[0]
    action_contract = source.split("async function assertSafeEntityActions", 1)[1].split(
        "async function assertSearchWorkspaceUi", 1
    )[0]

    card_details = source.split("function assertCompleteCardDetails", 1)[1].split(
        "function assertCompleteNoteDetails", 1
    )[0]

    assert 'const cardRequest = {\n    schemaVersion: 2,' in query_contract
    assert 'schemaVersion: 2,\n    mode: "cards",\n    cardId,' in query_contract
    assert 'schemaVersion: 2,\n    mode: "notes",\n    noteId,' in query_contract
    assert '{ schemaVersion: 2, mode: "cards", cardId, requestId }' in action_contract
    assert '{ schemaVersion: 2, mode: "notes", noteId, requestId }' in action_contract
    assert 'schemaVersion: 2, mode: "cards", query: "", filters:' in action_contract
    assert 'postSearchContract("/api/search/inspect", {\n    mode:' not in query_contract
    assert '{ mode: "cards", cardId, requestId }' not in action_contract
    assert '{ mode: "notes", noteId, requestId }' not in action_contract

    for field in ("displayText", "displaySource", "displayStatus", "displayTruncated"):
        assert f'"{field}"' in card_details
    assert '"primaryText"' not in card_details
    assert '"browser_question", "reviewer_front", "none"' in card_details
    assert '"available", "media_only", "unavailable"' in card_details


def test_smoke_browser_cards_workspace_uses_current_attention_inbox_contract():
    source = (
        Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / "smoke-browser.mjs"
    ).read_text(encoding="utf-8")
    workspace = source.split("async function assertCardsV2Workspace", 1)[1].split(
        "async function inspectCardsV2Layout", 1
    )[0]
    layout = source.split("async function inspectCardsV2Layout", 1)[1].split(
        "async function captureApkg", 1
    )[0]
    apkg_filter = source.split("async function applyApkgDeckFilter", 1)[1].split(
        "async function waitForCardsPageReady", 1
    )[0]
    readiness = source.split("async function waitForCardsPageReady", 1)[1].split(
        "async function waitForShadowFixture", 1
    )[0]
    active_contract = workspace + layout + apkg_filter + readiness

    for current in (
        'data-testid="cards-inbox-page"',
        'data-testid="cards-inbox"',
        'data-testid="cards-inbox-item"',
        'data-testid="cards-detail-drawer"',
        'name: "Развернуть ответ"',
        'name: "Перепроверить карточку"',
        "/api/triage/recheck",
        'summaryText.startsWith(`Показано ${expectation.filteredCardCount} из `)',
    ):
        assert current in active_contract

    for stale in (
        'data-testid="cards-triage-table"',
        'data-testid="cards-triage-row"',
        ".cards-v2-row-activate",
        'tr[aria-current="true"]',
        ".cards-v2-queue",
        ".cards-v2-inspector",
        "Развернуть превью",
        ".cards-v2-filter-row",
        "1024 split remains readable",
    ):
        assert stale not in active_contract


def test_smoke_api_selects_rich_media_fixture_when_multiple_japanese_cards_match():
    smoke_api = load_smoke_api_module()
    missing_audio = {
        "renderedPreview": {
            "frontHtml": '<div class="card-content">要望（音声なし）</div>',
            "mediaRefs": [],
        }
    }
    rich_media = {
        "renderedPreview": {
            "frontHtml": '<div class="card-content"><span class="word-focus">要望</span></div>',
            "mediaRefs": [{"name": "要.gif"}],
        }
    }

    assert smoke_api.find_fixture_card([missing_audio, rich_media]) is rich_media


def test_seed_separates_visual_and_inspection_japanese_review_groups():
    seed = load_e2e_module("seed-collection.py", "anki_study_report_seed_collection")

    assert seed.japanese_fixture_group("要望（音声なし）\x1frequest without audio") == "inspectionJapanese"
    assert seed.japanese_fixture_group("改善を要望する。\x1f[sound:要望.mp3]") == "japanese"
    assert seed.japanese_fixture_group("Plain E2E front") is None


def test_inspection_profile_e2e_helpers_build_exact_safe_profile_and_filter_reasons():
    smoke_api = load_smoke_api_module()
    item = {
        "structure": {
            "noteTypeId": "123",
            "name": "E2E Programming",
            "fingerprint": {"algorithm": "sha256", "value": "a" * 64},
            "fields": [
                {"ordinal": 0, "name": "Question"},
                {"ordinal": 1, "name": "Answer"},
            ],
        }
    }
    definition = {
        "displayName": "Programming",
        "mappings": [("question", "Question"), ("answer", "Answer")],
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
    assert "rawFields" not in json.dumps(profile)

    reasons = smoke_api.reasons_for_note_type(
        [
            {"noteType": {"noteTypeId": "123"}, "reasons": [{"code": "learning.leech"}]},
            {"noteType": {"noteTypeId": "456"}, "reasons": [{"code": "content.audio_missing"}]},
        ],
        "123",
    )
    assert reasons == [{"code": "learning.leech"}]


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

def test_restart_anki_mutates_inspection_profile_fixture_for_full_and_cards_scopes():
    source = (
        Path(__file__).resolve().parents[1]
        / "docker"
        / "anki-e2e"
        / "restart-anki.sh"
    ).read_text(encoding="utf-8")

    assert 'case "${ANKI_E2E_SCOPE:-full}" in' in source
    assert "full|cards)" in source
    assert 'if [ "${ANKI_E2E_SCOPE:-full}" = "cards" ]' not in source
    assert source.count("mutate-inspection-profile-fixture.py") == 1
