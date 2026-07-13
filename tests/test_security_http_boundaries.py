from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from conftest import import_addon_module


def _fetch(url: str) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "anki-study-report-security-test"})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def _write_static_dashboard(root: Path) -> None:
    assets = root / "assets"
    assets.mkdir(parents=True)
    (root / "index.html").write_text('<!doctype html><div id="root">dashboard</div>', encoding="utf-8")
    (assets / "app.js").write_text("window.__asrReady = true;", encoding="utf-8")


def test_http_static_boundary_rejects_encoded_and_double_encoded_traversal(monkeypatch, tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    static_dir = tmp_path / "dashboard"
    _write_static_dashboard(static_dir)
    secret = tmp_path / "secret.txt"
    secret.write_text("outside-secret", encoding="utf-8")
    monkeypatch.setattr(dashboard_server, "_find_static_dir", lambda: static_dir)

    manager = dashboard_server.DashboardServerManager()
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    try:
        for request_path in (
            "/%2e%2e/secret.txt",
            "/%252e%252e%252fsecret.txt",
            "/%2f%2fetc/passwd",
            "/C:%2fWindows%2fwin.ini",
            "/%5c%5cserver%5cshare%5cfile",
        ):
            status, body = _fetch(f"{base_url}{request_path}")
            assert status == 404
            assert b"outside-secret" not in body
            assert b'id="root"' not in body
    finally:
        manager.stop()


def test_media_boundary_rejects_legacy_provider_paths(tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    outside = tmp_path / "outside.gif"
    outside.write_bytes(b"GIF89a")

    manager = dashboard_server.DashboardServerManager()
    manager.configure_media_handler(lambda _name: str(outside))
    state = manager.start(port=0, idle_timeout_seconds=0)
    base_url = f"http://127.0.0.1:{state.port}"
    token = parse_qs(urlparse(manager.url()).query)["token"][0]
    try:
        status, body = _fetch(f"{base_url}/api/media?name=outside.gif&token={token}")
        assert status == 404
        assert body != b"GIF89a"
    finally:
        manager.stop()
