from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from conftest import import_addon_module


def fetch(url: str, *, method: str = "GET", json_body=None) -> tuple[int, str, bytes]:
    data = None if json_body is None else json.dumps(json_body).encode("utf-8")
    headers = {"User-Agent": "anki-study-report-test"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def fetch_raw(url: str, body: bytes) -> tuple[int, str, bytes]:
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def write_dashboard_static(root: Path) -> None:
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True)
    (root / "index.html").write_text(
        '<!doctype html><html><head><link rel="stylesheet" href="/assets/app.css"></head>'
        '<body><div id="root"></div><script type="module" src="/assets/app.js"></script></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "app.css").write_text("body { color: black; }", encoding="utf-8")
    (assets_dir / "app.js").write_text("document.body.dataset.ready = '1';", encoding="utf-8")


def test_find_static_dir_prefers_packaged_assets_and_rejects_incomplete_build(monkeypatch, tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    package_dir = tmp_path / "anki_study_report"
    package_dir.mkdir()
    packaged_static = package_dir / "web_dashboard"
    dev_static = tmp_path / "web-dashboard" / "dist"
    write_dashboard_static(packaged_static)
    write_dashboard_static(dev_static)
    monkeypatch.setattr(dashboard_server, "__file__", str(package_dir / "dashboard_server.py"))

    assert dashboard_server._find_static_dir() == packaged_static

    (packaged_static / "assets" / "app.js").unlink()
    assert dashboard_server._find_static_dir() == dev_static

    (dev_static / "assets" / "app.css").write_text("", encoding="utf-8")
    assert dashboard_server._find_static_dir() is None


def test_dashboard_server_smoke_endpoints():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]

    try:
        status, content_type, body = fetch(f"{base_url}/")
        assert status == 200
        assert "text/html" in content_type
        assert b"<html" in body.lower() or b"<!doctype html" in body.lower()

        status, content_type, body = fetch(f"{base_url}/api/status")
        assert status == 200
        assert "application/json" in content_type
        assert json.loads(body)["running"] is True

        status, _, _ = fetch(f"{base_url}/api/health")
        assert status == 403

        manager.configure_health_handler(lambda: {"mode": "e2e", "profile": "E2E"})
        status, content_type, body = fetch(f"{base_url}/api/health?token={token}")
        assert status == 200
        assert "application/json" in content_type
        assert json.loads(body) == {
            "ok": True,
            "addon": "Anki Study Report",
            "mode": "e2e",
            "profile": "E2E",
            "hasReport": False,
        }

        status, _, _ = fetch(f"{base_url}/api/report")
        assert status == 403

        payload = {"ok": True, "summary": {"totalReviews": 10}}
        manager.publish_report(payload)
        status, content_type, body = fetch(f"{base_url}/api/report?token={token}")
        assert status == 200
        assert "application/json" in content_type
        assert json.loads(body) == payload

        status, _, _ = fetch(f"{base_url}/api/logs/recent")
        assert status == 403

        status, _, _ = fetch(f"{base_url}/%2e%2e/config.json")
        assert status == 404

        status, content_type, body = fetch(f"{base_url}/assets/does-not-exist.js")
        assert status == 404
        assert b'id="root"' not in body.lower()
        assert "application/javascript" not in content_type
    finally:
        manager.stop()

    assert manager.state().running is False


def test_search_endpoints_require_token_post_and_preserve_typed_statuses():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    calls = []

    def query_handler(payload):
        calls.append(("query", payload))
        return {"ok": True, "response": {"mode": payload["mode"], "items": []}}

    def inspect_handler(payload):
        calls.append(("inspect", payload))
        return {"ok": False, "error": "search_entity_not_found", "message": "Entity unavailable."}

    manager.configure_search_handlers(query_handler=query_handler, inspect_handler=inspect_handler)
    try:
        status, _, body = fetch(f"{base_url}/api/search/query", method="POST", json_body={"mode": "cards"})
        assert status == 403
        assert json.loads(body)["error"] == "invalid_dashboard_token"

        status, _, body = fetch(f"{base_url}/api/search/query?token={token}")
        assert status == 405
        assert json.loads(body)["error"] == "method_not_allowed"

        query_body = {"schemaVersion": 2, "mode": "cards", "query": "deck:Japanese"}
        status, content_type, body = fetch(
            f"{base_url}/api/search/query?token={token}", method="POST", json_body=query_body
        )
        assert status == 200
        assert "application/json" in content_type
        assert json.loads(body) == {"ok": True, "response": {"mode": "cards", "items": []}}

        inspect_body = {"schemaVersion": 2, "mode": "notes", "noteId": "123"}
        status, _, body = fetch(
            f"{base_url}/api/search/inspect?token={token}", method="POST", json_body=inspect_body
        )
        assert status == 404
        assert json.loads(body)["error"] == "search_entity_not_found"
        assert calls == [("query", query_body), ("inspect", inspect_body)]
    finally:
        manager.stop()


def test_search_endpoint_maps_validation_timeout_and_unavailable_errors():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    request = {"schemaVersion": 2, "mode": "cards"}
    try:
        status, _, body = fetch(f"{base_url}/api/search/query?token={token}", method="POST", json_body=request)
        assert status == 503
        assert json.loads(body)["error"] == "search_unavailable"

        for raw_body in (b"{invalid", b"x" * 8193):
            status, _, body = fetch_raw(f"{base_url}/api/search/query?token={token}", raw_body)
            assert status == 400
            assert json.loads(body)["error"] == "invalid_search_request"

        for code, expected_status in [("invalid_search_request", 400), ("search_timeout", 504), ("search_failed", 503)]:
            manager.configure_search_handlers(
                query_handler=lambda payload, code=code: {"ok": False, "error": code, "message": "Safe failure."}
            )
            status, _, body = fetch(f"{base_url}/api/search/query?token={token}", method="POST", json_body=request)
            assert status == expected_status
            assert json.loads(body)["error"] == code
    finally:
        manager.stop()


def test_search_endpoint_rejects_unknown_fields_and_safely_logs_handler_failure(monkeypatch):
    dashboard_server = import_addon_module("dashboard_server")
    search_runtime = import_addon_module("search_runtime")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    logged = []
    monkeypatch.setattr(dashboard_server, "log_event", lambda *args, **kwargs: logged.append((args, kwargs)))
    try:
        manager.configure_search_handlers(query_handler=lambda payload: search_runtime.run_search_query_sync(None, payload))
        status, _, body = fetch(
            f"{base_url}/api/search/query?token={token}",
            method="POST",
            json_body={"schemaVersion": 2, "mode": "cards", "query": "", "rawSql": "secret-select"},
        )
        assert status == 400
        assert json.loads(body)["fieldErrors"] == {"rawSql": "Unexpected field."}

        manager.configure_search_handlers(
            query_handler=lambda payload: (_ for _ in ()).throw(RuntimeError("secret-query token=secret-token"))
        )
        status, _, body = fetch(
            f"{base_url}/api/search/query?token={token}", method="POST", json_body={"schemaVersion": 2, "mode": "cards"}
        )
        assert status == 503
        response_text = body.decode("utf-8")
        assert "secret-query" not in response_text
        assert "secret-token" not in response_text
        assert "secret-query" not in repr(logged)
        assert "secret-token" not in repr(logged)
    finally:
        manager.stop()


def test_triage_endpoint_is_token_protected_post_json_only_and_strict():
    dashboard_server = import_addon_module("dashboard_server")
    triage_runtime = import_addon_module("triage_runtime")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    payload = {
        "schemaVersion": 3,
        "dataset": "automatic",
        "scope": {"periodStartMs": 1, "periodEndMs": 2, "deckIds": []},
        "limit": 100,
    }
    manager.configure_triage_handler(
        lambda value: triage_runtime.run_triage_query_sync(None, value, signal_provider=lambda: [])
    )
    try:
        status, _, body = fetch(f"{base_url}/api/triage/query", method="POST", json_body=payload)
        assert status == 403
        assert json.loads(body)["error"] == "invalid_dashboard_token"

        status, _, body = fetch(f"{base_url}/api/triage/query?token={token}")
        assert status == 405
        assert json.loads(body)["error"] == "method_not_allowed"

        status, _, body = fetch(f"{base_url}/api/triage/query?token={token}", method="POST")
        assert status == 415
        assert json.loads(body)["error"] == "invalid_triage_request"

        status, content_type, body = fetch(
            f"{base_url}/api/triage/query?token={token}", method="POST", json_body=payload
        )
        assert status == 200
        assert "application/json" in content_type
        response = json.loads(body)
        assert response["ok"] is True
        assert response["response"]["schemaVersion"] == 3
        assert response["response"]["status"] == "partial"

        status, _, body = fetch(
            f"{base_url}/api/triage/query?token={token}",
            method="POST",
            json_body={**payload, "rawSql": "select * from cards"},
        )
        assert status == 400
        assert json.loads(body)["error"] == "invalid_triage_request"

        old = {**payload, "schemaVersion": 2}
        status, _, body = fetch(f"{base_url}/api/triage/query?token={token}", method="POST", json_body=old)
        assert status == 400
        assert json.loads(body)["error"] == "invalid_triage_request"

        status, _, body = fetch_raw(
            f"{base_url}/api/triage/query?token={token}", b'{"padding":"' + b"x" * 9000 + b'"}'
        )
        assert status == 400
        assert json.loads(body)["error"] == "invalid_triage_request"
    finally:
        manager.stop()


def test_triage_endpoint_maps_typed_failures_without_exception_leak(monkeypatch):
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    payload = {
        "schemaVersion": 3,
        "dataset": "automatic",
        "scope": {"periodStartMs": 1, "periodEndMs": 2, "deckIds": []},
        "limit": 100,
    }
    logged = []
    monkeypatch.setattr(dashboard_server, "log_event", lambda *args, **kwargs: logged.append((args, kwargs)))
    try:
        for code, expected in [
            ("invalid_triage_request", 400),
            ("triage_timeout", 504),
            ("triage_unavailable", 503),
            ("triage_failed", 503),
        ]:
            manager.configure_triage_handler(lambda _value, code=code: {"ok": False, "error": code, "message": "Safe failure."})
            status, _, body = fetch(
                f"{base_url}/api/triage/query?token={token}", method="POST", json_body=payload
            )
            assert status == expected
            assert json.loads(body)["error"] == code

        manager.configure_triage_handler(
            lambda _value: (_ for _ in ()).throw(RuntimeError("private-path token=secret-token"))
        )
        status, _, body = fetch(
            f"{base_url}/api/triage/query?token={token}", method="POST", json_body=payload
        )
        assert status == 503
        assert json.loads(body) == {
            "ok": False,
            "error": "triage_failed",
            "message": "The triage request failed.",
        }
        assert "private-path" not in body.decode("utf-8")
        assert "secret-token" not in body.decode("utf-8")
        assert "private-path" not in repr(logged)
        assert "secret-token" not in repr(logged)
    finally:
        manager.stop()


def test_inspection_profile_endpoints_are_token_protected_json_only_bounded_and_typed():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    calls = []
    manager.configure_inspection_profile_handlers(
        query_handler=lambda value: calls.append(("query", value)) or {
            "ok": True, "response": {"schemaVersion": 1, "items": []}
        },
        validate_handler=lambda value: calls.append(("validate", value)) or {
            "ok": False, "error": "invalid_inspection_profile_request", "fieldErrors": {"profile": "invalid"}
        },
        update_handler=lambda value: calls.append(("update", value)) or {
            "ok": False, "error": "inspection_profile_revision_conflict", "currentRevision": 7
        },
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        path = "/api/inspection-profiles/query"
        assert fetch(f"{base_url}{path}", method="POST", json_body={"schemaVersion": 1})[0] == 403
        assert fetch(f"{base_url}{path}?token={token}")[0] == 405
        assert fetch(f"{base_url}{path}?token={token}", method="POST")[0] == 415

        status, _, body = fetch(
            f"{base_url}{path}?token={token}",
            method="POST",
            json_body={"schemaVersion": 1, "noteTypeIds": [], "limit": 500},
        )
        assert status == 200
        assert json.loads(body) == {"ok": True, "response": {"schemaVersion": 1, "items": []}}
        assert calls[-1] == ("query", {"schemaVersion": 1, "noteTypeIds": [], "limit": 500})
        assert token not in body.decode("utf-8")

        status, _, body = fetch(
            f"{base_url}/api/inspection-profiles/validate?token={token}",
            method="POST",
            json_body={"schemaVersion": 1},
        )
        assert status == 400
        assert json.loads(body)["fieldErrors"] == {"profile": "invalid"}

        status, _, body = fetch(
            f"{base_url}/api/inspection-profiles/update?token={token}",
            method="POST",
            json_body={"schemaVersion": 1},
        )
        assert status == 409
        assert json.loads(body)["currentRevision"] == 7

        status, _, body = fetch_raw(
            f"{base_url}{path}?token={token}", b'{"padding":"' + b"x" * 65_536 + b'"}'
        )
        assert status == 400
        assert json.loads(body)["error"] == "invalid_inspection_profile_request"
    finally:
        manager.stop()


def test_search_selection_browser_action_remains_token_protected_and_post_only():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    received = []
    manager.configure_action_handler(
        lambda action, payload: received.append((action, payload)) or {
            "ok": True,
            "action": action,
            "resultCode": "search.browser_opened",
            "requestedCount": len(payload["entityIds"]),
        }
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    body = {"mode": "cards", "entityIds": ["123"]}
    try:
        assert fetch(f"{base_url}/api/actions/open-search-selection", method="POST", json_body=body)[0] == 403
        assert fetch(f"{base_url}/api/actions/open-search-selection?token={token}")[0] == 404
        status, _, response = fetch(
            f"{base_url}/api/actions/open-search-selection?token={token}", method="POST", json_body=body
        )
        assert status == 200
        assert json.loads(response)["resultCode"] == "search.browser_opened"
        assert received == [("open-search-selection", body)]
    finally:
        manager.stop()


def test_entity_action_endpoints_are_separate_post_only_and_typed():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    calls = []

    def card_handler(payload):
        calls.append(("cards", payload))
        return {"ok": True, "response": {"schemaVersion": 1, "entityType": "cards"}}

    def note_handler(payload):
        calls.append(("notes", payload))
        return {"ok": False, "error": "entity_action_stale", "message": "Unavailable."}

    manager.configure_entity_action_handlers(card_handler=card_handler, note_handler=note_handler)
    card_body = {"action": "suspend", "cardIds": ["1"], "requestId": "cards-1"}
    note_body = {"action": "add_tags", "noteIds": ["2"], "tags": ["x"], "requestId": "notes-1"}
    try:
        assert fetch(f"{base_url}/api/entities/cards/actions", method="POST", json_body=card_body)[0] == 403
        status, _, body = fetch(f"{base_url}/api/entities/cards/actions?token={token}")
        assert status == 405
        assert json.loads(body)["error"] == "method_not_allowed"
        status, _, body = fetch(
            f"{base_url}/api/entities/cards/actions?token={token}", method="POST", json_body=card_body
        )
        assert status == 200
        assert json.loads(body)["response"]["entityType"] == "cards"
        status, _, body = fetch(
            f"{base_url}/api/entities/notes/actions?token={token}", method="POST", json_body=note_body
        )
        assert status == 409
        assert json.loads(body)["error"] == "entity_action_stale"
        assert calls == [("cards", card_body), ("notes", note_body)]
    finally:
        manager.stop()


def test_entity_action_endpoint_maps_invalid_timeout_unavailable_and_body_limit():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        status, _, body = fetch(
            f"{base_url}/api/entities/cards/actions?token={token}", method="POST", json_body={"action": "suspend"}
        )
        assert status == 503
        assert json.loads(body)["error"] == "entity_action_unavailable"
        for code, expected in [
            ("invalid_entity_action", 400),
            ("entity_action_timeout", 504),
            ("entity_action_failed", 503),
            ("cards.destination_filtered", 400),
            ("cards.destination_not_found", 409),
            ("cards.filtered_source_unsupported", 409),
        ]:
            manager.configure_entity_action_handlers(
                card_handler=lambda _payload, code=code: {"ok": False, "error": code, "message": "safe"}
            )
            status, _, body = fetch(
                f"{base_url}/api/entities/cards/actions?token={token}", method="POST", json_body={"action": "suspend"}
            )
            assert status == expected
            assert json.loads(body)["error"] == code
        status, _, body = fetch_raw(
            f"{base_url}/api/entities/cards/actions?token={token}", b'{"padding":"' + b"x" * 9000 + b'"}'
        )
        assert status == 400
        assert json.loads(body)["error"] == "invalid_entity_action"
    finally:
        manager.stop()


def test_dashboard_server_reports_static_fallback_without_token_leak(monkeypatch):
    dashboard_server = import_addon_module("dashboard_server")
    monkeypatch.setattr(dashboard_server, "_find_static_dir", lambda: None)
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]

    try:
        status, content_type, body = fetch(f"{base_url}/api/status")
        assert status == 200
        assert "application/json" in content_type
        status_payload = json.loads(body)
        assert status_payload["running"] is True
        assert status_payload["static_available"] is False
        assert status_payload["static_dir"] is None
        assert status_payload["report_available"] is False
        assert status_payload["url"].endswith("?token=...")
        assert token not in body.decode("utf-8")

        status, content_type, body = fetch(f"{base_url}/")
        text = body.decode("utf-8")
        assert status == 200
        assert "text/html" in content_type
        assert "dashboard-static-fallback" in text
        assert "fallback-режиме" in text
        assert "build:addon" in text
        assert token not in text
    finally:
        manager.stop()


def test_runtime_static_check_follows_dynamic_manifest_graph(tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    static_dir = tmp_path / "web_dashboard"
    assets = static_dir / "assets"
    assets.mkdir(parents=True)
    (static_dir / "index.html").write_text(
        '<link rel="stylesheet" href="/assets/app.css"><script type="module" src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (static_dir / "manifest.json").write_text(json.dumps({
        "index.html": {
            "file": "assets/app.js", "isEntry": True,
            "dynamicImports": ["src/pages/FsrsStatisticsPage.tsx"],
            "css": ["assets/app.css"],
        },
        "src/pages/FsrsStatisticsPage.tsx": {
            "file": "assets/fsrs.js", "isDynamicEntry": True,
            "css": ["assets/fsrs.css"],
        },
    }), encoding="utf-8")
    for name in ("app.js", "app.css", "fsrs.js", "fsrs.css"):
        (assets / name).write_text("/* present */", encoding="utf-8")

    assert dashboard_server._static_dir_is_available(static_dir) is True
    (assets / "fsrs.js").unlink()
    assert dashboard_server._static_dir_is_available(static_dir) is False


def test_dashboard_server_serves_token_protected_media(tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    media_file = media_dir / "front.gif"
    media_file.write_bytes(b"GIF89a")

    manager = dashboard_server.DashboardServerManager()
    manager.configure_media_handler(lambda name: ((media_dir / name).read_bytes(), (media_dir / name).suffix))
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]

    try:
        status, content_type, body = fetch(f"{base_url}/api/media?name=front.gif")
        assert status == 403

        status, content_type, body = fetch(f"{base_url}/api/media?name=front.gif&token={token}")
        assert status == 200
        assert content_type == "image/gif"
        assert body == b"GIF89a"

        status, _, _ = fetch(f"{base_url}/api/media?name=..%2Fsecret.txt&token={token}")
        assert status == 400

        status, _, _ = fetch(f"{base_url}/api/media?name=file:///secret.gif&token={token}")
        assert status == 400
    finally:
        manager.stop()


def test_dashboard_settings_endpoint_get_post_validation_and_auth():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    received = []
    manager.configure_display_settings_handlers(
        settings_provider=lambda: {"ok": True, "settings": {"dashboard": {"scope": "all"}}},
        settings_handler=lambda payload: received.append(payload) or {
            "ok": True,
            "settings": {"data": {"useStatsCacheForReport": payload["data"]["useStatsCacheForReport"]}},
        },
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]

    try:
        status, _, _ = fetch(f"{base_url}/api/dashboard/settings")
        assert status == 403

        status, _, body = fetch(f"{base_url}/api/dashboard/settings?token={token}")
        assert status == 200
        assert json.loads(body)["settings"]["dashboard"]["scope"] == "all"

        partial = {"data": {"useStatsCacheForReport": True}}
        status, _, body = fetch(
            f"{base_url}/api/dashboard/settings?token={token}", method="POST", json_body=partial
        )
        assert status == 200
        assert received == [partial]
        assert json.loads(body)["settings"]["data"]["useStatsCacheForReport"] is True

        status, _, _ = fetch(f"{base_url}/api/dashboard/settings", method="POST", json_body=partial)
        assert status == 403

        status, _, body = fetch(
            f"{base_url}/api/dashboard/settings?token={token}", method="POST", json_body=["invalid"]
        )
        assert status == 400
        assert json.loads(body)["ok"] is False
    finally:
        manager.stop()


def test_profile_endpoint_get_post_validation_and_auth():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    received = []
    manager.configure_profile_handlers(
        profile_provider=lambda: {"ok": True, "profile": {"preferences": {"deckOverviewSort": "name"}}},
        profile_handler=lambda payload: received.append(payload) or (
            {"ok": False, "fieldErrors": {"customStudyStartedOn": "invalid"}}
            if payload.get("customStudyStartedOn") == "invalid"
            else {"ok": True, "profile": {"preferences": payload}}
        ),
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        assert fetch(f"{base_url}/api/profile")[0] == 403
        status, _, body = fetch(f"{base_url}/api/profile?token={token}")
        assert status == 200
        assert json.loads(body)["profile"]["preferences"]["deckOverviewSort"] == "name"

        patch = {"deckOverviewSort": "reviews"}
        status, _, body = fetch(f"{base_url}/api/profile?token={token}", method="POST", json_body=patch)
        assert status == 200
        assert received == [patch]
        assert json.loads(body)["profile"]["preferences"] == patch

        assert fetch(f"{base_url}/api/profile", method="POST", json_body=patch)[0] == 403
        status, _, body = fetch(
            f"{base_url}/api/profile?token={token}", method="POST", json_body={"customStudyStartedOn": "invalid"}
        )
        assert status == 400
        assert "customStudyStartedOn" in json.loads(body)["fieldErrors"]
    finally:
        manager.stop()


def test_product_notices_and_privacy_endpoints_are_narrow_token_protected_contracts():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    privacy_calls = []
    seen_calls = []
    manager.configure_product_notice_handlers(
        notices_provider=lambda: {
            "ok": True,
            "currentVersion": "1.1.0",
            "requiresConsent": True,
            "showWhatsNew": True,
        },
        release_seen_handler=lambda: seen_calls.append(True) or {"ok": True, "showWhatsNew": False},
        privacy_provider=lambda: {"ok": True, "privacy": {"telemetry": {"status": "undecided"}}},
        privacy_handler=lambda payload: privacy_calls.append(payload) or (
            {"ok": False, "error": "invalid_privacy_choices", "fieldErrors": {"purposes": "invalid"}}
            if "purposes" not in payload
            else {"ok": True, "privacy": {"telemetry": {"status": "declined"}}}
        ),
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        assert fetch(f"{base_url}/api/product-notices")[0] == 403
        assert fetch(f"{base_url}/api/privacy")[0] == 403
        assert fetch(f"{base_url}/api/product-notices/seen?token={token}")[0] == 405

        status, _, body = fetch(f"{base_url}/api/product-notices?token={token}")
        assert status == 200
        assert json.loads(body)["requiresConsent"] is True

        status, _, body = fetch(f"{base_url}/api/privacy?token={token}")
        assert status == 200
        assert json.loads(body)["privacy"]["telemetry"]["status"] == "undecided"

        status, _, body = fetch(
            f"{base_url}/api/privacy?token={token}",
            method="POST",
            json_body={"purposes": {"reliabilityDiagnostics": False, "featureUsage": False}},
        )
        assert status == 200
        assert json.loads(body)["privacy"]["telemetry"]["status"] == "declined"
        assert privacy_calls == [{"purposes": {"reliabilityDiagnostics": False, "featureUsage": False}}]

        assert fetch(f"{base_url}/api/privacy?token={token}", method="POST", json_body={})[0] == 400
        assert fetch(
            f"{base_url}/api/product-notices/seen?token={token}", method="POST", json_body={"version": "spoofed"}
        )[0] == 400
        status, _, body = fetch(
            f"{base_url}/api/product-notices/seen?token={token}", method="POST", json_body={}
        )
        assert status == 200
        assert json.loads(body)["showWhatsNew"] is False
        assert seen_calls == [True]
    finally:
        manager.stop()


def test_telemetry_endpoints_are_local_token_protected_and_post_only():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    events = []
    deletions = []
    checks = []
    manager.configure_telemetry_handlers(
        status_provider=lambda: {
            "ok": True,
            "pendingEventCount": 2,
            "endpointState": "configured",
        },
        event_handler=lambda payload: events.append(payload) or {
            "ok": True,
            "code": "telemetry.queued",
            "queued": True,
        },
        delete_handler=lambda: deletions.append(True) or {
            "ok": True,
            "deletionPending": True,
            "confirmed": False,
        },
        check_handler=lambda: checks.append(True) or {
            "ok": True,
            "code": "telemetry.manual_send_started",
            "started": True,
        },
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    event = {"eventCode": "dashboard.opened", "occurredAt": "2026-07-15T00:00:00Z"}
    try:
        assert fetch(f"{base_url}/api/telemetry/status")[0] == 403
        assert fetch(f"{base_url}/api/telemetry/events", method="POST", json_body=event)[0] == 403
        assert fetch(f"{base_url}/api/telemetry/delete", method="POST", json_body={})[0] == 403
        assert fetch(f"{base_url}/api/telemetry/check-send", method="POST", json_body={})[0] == 403

        status, _, body = fetch(f"{base_url}/api/telemetry/status?token={token}")
        assert status == 200
        assert json.loads(body)["pendingEventCount"] == 2
        assert token not in body.decode("utf-8")

        status, _, body = fetch(f"{base_url}/api/telemetry/events?token={token}")
        assert status == 405
        assert json.loads(body)["error"] == "method_not_allowed"
        status, _, body = fetch(
            f"{base_url}/api/telemetry/events?token={token}", method="POST", json_body=event
        )
        assert status == 200
        assert json.loads(body)["code"] == "telemetry.queued"
        assert events == [event]
        assert token not in body.decode("utf-8")

        assert fetch(f"{base_url}/api/telemetry/delete?token={token}")[0] == 405
        assert fetch(
            f"{base_url}/api/telemetry/delete?token={token}", method="POST", json_body={"installationId": "spoofed"}
        )[0] == 400
        status, _, body = fetch(
            f"{base_url}/api/telemetry/delete?token={token}", method="POST", json_body={}
        )
        assert status == 200
        assert json.loads(body)["deletionPending"] is True
        assert deletions == [True]
        assert token not in body.decode("utf-8")

        assert fetch(f"{base_url}/api/telemetry/check-send?token={token}")[0] == 405
        assert fetch(
            f"{base_url}/api/telemetry/check-send?token={token}", method="POST", json_body={"force": True}
        )[0] == 400
        status, _, body = fetch(
            f"{base_url}/api/telemetry/check-send?token={token}", method="POST", json_body={}
        )
        assert status == 202
        assert json.loads(body)["code"] == "telemetry.manual_send_started"
        assert checks == [True]
        assert token not in body.decode("utf-8")
    finally:
        manager.stop()


def test_notification_endpoints_are_strict_bounded_and_token_protected():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    calls = []
    summary = {
        "ok": True,
        "schemaVersion": 1,
        "unreadCount": 1,
        "activeSignalCount": 1,
        "items": [],
    }
    manager.configure_notification_handlers(
        summary_provider=lambda: summary,
        list_handler=lambda payload: calls.append(("list", payload)) or {
            "ok": True,
            "schemaVersion": 1,
            "page": payload["page"],
            "pageLimit": payload["pageLimit"],
            "pageCount": 0,
            "total": 0,
            "items": [],
        },
        read_handler=lambda payload: calls.append(("read", payload)) or {**summary, "updated": 1},
        read_all_handler=lambda payload: calls.append(("read-all", payload)) or {**summary, "updated": 1},
        settings_provider=lambda: {
            "ok": True,
            "schemaVersion": 1,
            "preferences": {"showUnreadBadge": True},
        },
        settings_handler=lambda payload: calls.append(("settings", payload)) or {
            "ok": True,
            "schemaVersion": 1,
            "preferences": payload,
        },
        toasts_handler=lambda payload: calls.append(("toasts", payload)) or {
            "ok": True,
            "schemaVersion": 1,
            "items": [],
        },
        toast_delivered_handler=lambda payload: calls.append(("toast-delivered", payload)) or {
            "ok": True,
            "updated": len(payload["notificationIds"]),
        },
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        assert fetch(f"{base_url}/api/notifications/summary")[0] == 403
        status, _, body = fetch(f"{base_url}/api/notifications/summary?token={token}")
        assert status == 200
        assert json.loads(body)["unreadCount"] == 1

        status, _, body = fetch(
            f"{base_url}/api/notifications?token={token}&page=2&pageLimit=50&tab=active&category=workload"
        )
        assert status == 200
        assert json.loads(body)["pageLimit"] == 50
        assert calls[-1] == (
            "list",
            {"page": 2, "pageLimit": 50, "tab": "active", "category": "workload"},
        )
        assert fetch(f"{base_url}/api/notifications?token={token}&pageLimit=51&extra=1")[0] == 400
        assert fetch(f"{base_url}/api/notifications/read?token={token}")[0] == 405

        status, _, _ = fetch(
            f"{base_url}/api/notifications/read?token={token}", method="POST", json_body={"notificationIds": ["n1"]}
        )
        assert status == 200
        assert calls[-1] == ("read", {"notificationIds": ["n1"]})

        assert fetch(
            f"{base_url}/api/settings/notifications?token={token}", method="POST", json_body={}
        )[0] == 405
        status, _, _ = fetch(
            f"{base_url}/api/settings/notifications?token={token}", method="PUT", json_body={"showUnreadBadge": False}
        )
        assert status == 200
        assert calls[-1] == ("settings", {"showUnreadBadge": False})

        status, _, _ = fetch(
            f"{base_url}/api/notifications/toasts?token={token}&sessionStartedAt=2026-07-17T00%3A00%3A00Z"
        )
        assert status == 200
        assert calls[-1] == ("toasts", {"sessionStartedAt": "2026-07-17T00:00:00Z"})
        status, _, _ = fetch(
            f"{base_url}/api/notifications/toast-delivered?token={token}",
            method="POST",
            json_body={"notificationIds": ["n1"]},
        )
        assert status == 200
        assert token not in repr(calls)
    finally:
        manager.stop()


def test_statistics_query_endpoint_is_post_only_typed_bounded_and_token_protected():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    received = []

    def query_handler(payload):
        received.append(payload)
        if "period" not in payload:
            return {"ok": False, "error": "invalid_statistics_query", "fieldErrors": {"period": "required"}}
        return {"ok": True, "result": {"query": payload, "overview": {"reviews": 10}}}

    manager.configure_statistics_handler(query_handler)
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    query = {"scope": {"kind": "dashboard"}, "period": "90d", "granularity": "auto", "comparison": True}
    try:
        assert fetch(f"{base_url}/api/statistics/query", method="POST", json_body=query)[0] == 403
        status, _, body = fetch(f"{base_url}/api/statistics/query?token={token}")
        assert status == 405
        assert json.loads(body)["error"] == "method_not_allowed"

        status, _, body = fetch(f"{base_url}/api/statistics/query?token={token}", method="POST", json_body=query)
        assert status == 200
        assert received == [query]
        response = json.loads(body)
        assert response["result"]["query"] == query
        assert token not in body.decode("utf-8")

        status, _, body = fetch(f"{base_url}/api/statistics/query?token={token}", method="POST", json_body={"sql": "select * from revlog"})
        assert status == 400
        assert json.loads(body)["error"] == "invalid_statistics_query"

        status, _, body = fetch(f"{base_url}/api/statistics/query?token={token}", method="POST", json_body={"period": "90d", "padding": "x" * 9000})
        assert status == 400
        assert json.loads(body)["error"] == "invalid_statistics_query"
    finally:
        manager.stop()


def test_fsrs_query_endpoint_is_post_only_bounded_and_token_protected():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    received = []

    def handler(payload):
        received.append(payload)
        if set(payload) - {"operation", "scope", "period", "simulation"}:
            return {"ok": False, "error": "invalid_fsrs_query", "fieldErrors": {"query": "unexpected"}}
        return {"ok": True, "response": {"operation": payload.get("operation"), "result": {"readOnly": True}}}

    manager.configure_fsrs_handler(handler)
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    query = {"operation": "memory", "scope": {"kind": "all_collection"}, "period": "90d"}
    try:
        assert fetch(f"{base_url}/api/statistics/fsrs/query", method="POST", json_body=query)[0] == 403
        assert fetch(f"{base_url}/api/statistics/fsrs/query?token={token}")[0] == 405
        status, _, body = fetch(f"{base_url}/api/statistics/fsrs/query?token={token}", method="POST", json_body=query)
        assert status == 200
        assert received == [query]
        assert json.loads(body)["response"]["result"]["readOnly"] is True
        assert token not in body.decode("utf-8")
        status, _, body = fetch(f"{base_url}/api/statistics/fsrs/query?token={token}", method="POST", json_body={"operation": "memory", "search": "rated:1"})
        assert status == 400
        assert json.loads(body)["error"] == "invalid_fsrs_query"
        status, _, body = fetch(f"{base_url}/api/statistics/fsrs/query?token={token}", method="POST", json_body={"operation": "memory", "padding": "x" * 9000})
        assert status == 400
    finally:
        manager.stop()


def test_card_display_formatter_endpoints_are_token_protected_json_only_bounded_and_typed():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    calls = []
    manager.configure_card_display_formatter_handlers(
        query_handler=lambda value: calls.append(("query", value)) or {
            "ok": True,
            "response": {
                "schemaVersion": 1,
                "status": "empty",
                "revision": 0,
                "formatters": [],
                "errorCode": None,
                "quarantined": False,
            },
        },
        validate_handler=lambda value: calls.append(("validate", value)) or {
            "ok": False,
            "error": "invalid_card_display_formatter_request",
            "fieldErrors": {"formatter": "invalid"},
        },
        update_handler=lambda value: calls.append(("update", value)) or {
            "ok": False,
            "error": "card_display_formatter_revision_conflict",
            "currentRevision": 7,
        },
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        path = "/api/card-display-formatters/query"
        assert fetch(f"{base_url}{path}", method="POST", json_body={"schemaVersion": 1})[0] == 403
        assert fetch(f"{base_url}{path}?token={token}")[0] == 405
        assert fetch(f"{base_url}{path}?token={token}", method="POST")[0] == 415

        status, _, body = fetch(
            f"{base_url}{path}?token={token}",
            method="POST",
            json_body={"schemaVersion": 1},
        )
        assert status == 200
        assert json.loads(body)["response"]["status"] == "empty"
        assert calls[-1] == ("query", {"schemaVersion": 1})
        assert token not in body.decode("utf-8")

        status, _, body = fetch(
            f"{base_url}/api/card-display-formatters/validate?token={token}",
            method="POST",
            json_body={"schemaVersion": 1},
        )
        assert status == 400
        assert json.loads(body)["fieldErrors"] == {"formatter": "invalid"}

        status, _, body = fetch(
            f"{base_url}/api/card-display-formatters/update?token={token}",
            method="POST",
            json_body={"schemaVersion": 1},
        )
        assert status == 409
        assert json.loads(body)["currentRevision"] == 7

        status, _, body = fetch_raw(
            f"{base_url}{path}?token={token}", b'{"padding":"' + b"x" * 65_536 + b'"}'
        )
        assert status == 400
        assert json.loads(body)["error"] == "invalid_card_display_formatter_request"
    finally:
        manager.stop()
