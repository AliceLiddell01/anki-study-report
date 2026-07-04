from __future__ import annotations

import json
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
