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

        status, content_type, body = fetch(
            f"{base_url}/api/search/query?token={token}",
            method="POST",
            json_body={"mode": "cards", "query": "deck:Japanese"},
        )
        assert status == 200
        assert "application/json" in content_type
        assert json.loads(body) == {"ok": True, "response": {"mode": "cards", "items": []}}

        status, _, body = fetch(
            f"{base_url}/api/search/inspect?token={token}",
            method="POST",
            json_body={"mode": "notes", "noteId": "123"},
        )
        assert status == 404
        assert json.loads(body)["error"] == "search_entity_not_found"
        assert calls == [
            ("query", {"mode": "cards", "query": "deck:Japanese"}),
            ("inspect", {"mode": "notes", "noteId": "123"}),
        ]
    finally:
        manager.stop()


def test_search_endpoint_maps_validation_timeout_and_unavailable_errors():
    dashboard_server = import_addon_module("dashboard_server")
    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        status, _, body = fetch(
            f"{base_url}/api/search/query?token={token}", method="POST", json_body={"mode": "cards"}
        )
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
            status, _, body = fetch(
                f"{base_url}/api/search/query?token={token}", method="POST", json_body={"mode": "cards"}
            )
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
            json_body={"mode": "cards", "query": "", "rawSql": "secret-select"},
        )
        assert status == 400
        assert json.loads(body)["fieldErrors"] == {"rawSql": "Unexpected field."}

        manager.configure_search_handlers(
            query_handler=lambda payload: (_ for _ in ()).throw(RuntimeError("secret-query token=secret-token"))
        )
        status, _, body = fetch(
            f"{base_url}/api/search/query?token={token}", method="POST", json_body={"mode": "cards"}
        )
        assert status == 503
        response_text = body.decode("utf-8")
        assert "secret-query" not in response_text
        assert "secret-token" not in response_text
        assert "secret-query" not in repr(logged)
        assert "secret-token" not in repr(logged)
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
            f"{base_url}/api/actions/open-search-selection?token={token}",
            method="POST",
            json_body=body,
        )
        assert status == 200
        assert json.loads(response)["resultCode"] == "search.browser_opened"
        assert received == [("open-search-selection", body)]
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
            f"{base_url}/api/dashboard/settings?token={token}",
            method="POST",
            json_body=partial,
        )
        assert status == 200
        assert received == [partial]
        assert json.loads(body)["settings"]["data"]["useStatsCacheForReport"] is True

        status, _, _ = fetch(
            f"{base_url}/api/dashboard/settings",
            method="POST",
            json_body=partial,
        )
        assert status == 403

        status, _, body = fetch(
            f"{base_url}/api/dashboard/settings?token={token}",
            method="POST",
            json_body=["invalid"],
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
            f"{base_url}/api/profile?token={token}",
            method="POST",
            json_body={"customStudyStartedOn": "invalid"},
        )
        assert status == 400
        assert "customStudyStartedOn" in json.loads(body)["fieldErrors"]
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
