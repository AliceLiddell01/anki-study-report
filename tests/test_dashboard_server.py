from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from conftest import import_addon_module


def fetch(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "anki-study-report-test"})
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


def test_dashboard_server_serves_token_protected_media(tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    media_file = media_dir / "front.gif"
    media_file.write_bytes(b"GIF89a")

    manager = dashboard_server.DashboardServerManager()
    manager.configure_media_handler(lambda name: str(media_dir / name))
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
