from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "anki_study_report"


def load_dashboard_server_module():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ADDON)]
    sys.modules["anki_study_report"] = package
    spec = importlib.util.spec_from_file_location(
        "anki_study_report.dashboard_server",
        ADDON / "dashboard_server.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["anki_study_report.dashboard_server"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def post_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def assert_json_safe(payload: dict) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    forbidden = ("Traceback", "NaN", "Infinity", "Invalid Date", "undefined")
    assert not any(item in encoded for item in forbidden), encoded


def main() -> None:
    dashboard_server = load_dashboard_server_module()
    manager = dashboard_server.DashboardServerManager()
    calls: list[tuple[str, dict]] = []

    def action_handler(action: str, payload: dict) -> dict:
        calls.append((action, payload))
        if action == "unknown-action":
            return {"ok": False, "action": action, "error": "Unknown dashboard action."}
        if action == "copy-markdown":
            return {
                "ok": False,
                "action": action,
                "error": "No report is available yet. Build or open a report first.",
            }
        if action == "save-markdown":
            assert "path" not in payload or payload["path"] == "ignored-by-server"
            return {"ok": True, "action": action, "message": "Save dialog opened."}
        if action == "open-browser":
            assert payload.get("kind") in {"problematic-decks", "again", "new"}
            assert "query" not in payload
            return {"ok": True, "action": action, "message": "Opened Anki Browser."}
        return {"ok": True, "action": action, "message": "OK"}

    manager.configure_action_handler(action_handler)
    state = manager.start(port=0, idle_timeout_seconds=0)
    try:
        parsed = urlparse(state.url)
        token = parse_qs(parsed.query)["token"][0]
        base = f"http://{state.host}:{state.port}"

        status, data = post_json(f"{base}/api/actions/copy-markdown")
        assert status == 403, (status, data)
        assert data["ok"] is False, data
        assert_json_safe(data)

        status, data = post_json(f"{base}/api/actions/copy-markdown?token=bad")
        assert status == 403, (status, data)
        assert data["ok"] is False, data
        assert_json_safe(data)

        status, data = post_json(f"{base}/api/actions/unknown-action?token={token}")
        assert status == 400, (status, data)
        assert data["ok"] is False, data
        assert data["error"] == "Unknown dashboard action.", data
        assert_json_safe(data)

        status, data = post_json(f"{base}/api/actions/copy-markdown?token={token}")
        assert status == 400, (status, data)
        assert data["ok"] is False, data
        assert "No report" in data["error"], data
        assert_json_safe(data)

        status, data = post_json(
            f"{base}/api/actions/save-markdown?token={token}",
            {"path": "ignored-by-server"},
        )
        assert status == 200, (status, data)
        assert data["ok"] is True, data
        assert_json_safe(data)

        status, data = post_json(
            f"{base}/api/actions/open-browser?token={token}",
            {"kind": "problematic-decks"},
        )
        assert status == 200, (status, data)
        assert data["ok"] is True, data
        assert_json_safe(data)
    finally:
        manager.stop()

    assert ("save-markdown", {"path": "ignored-by-server"}) in calls
    print("DASHBOARD_ACTIONS_SMOKE_OK")


if __name__ == "__main__":
    main()
