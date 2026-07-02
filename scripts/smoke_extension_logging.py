from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "anki_study_report"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_dashboard_server_module():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ADDON)]
    sys.modules["anki_study_report"] = package
    load_module("anki_study_report.extension_logging", ADDON / "extension_logging.py")
    return load_module("anki_study_report.dashboard_server", ADDON / "dashboard_server.py")


def get_json(url: str) -> tuple[int, dict]:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def post_json(url: str) -> tuple[int, dict]:
    request = Request(url, data=b"{}", method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main() -> None:
    dashboard_server = load_dashboard_server_module()
    logging_module = sys.modules["anki_study_report.extension_logging"]
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        logging_module.configure_log_dir(log_dir)
        logging_module.log_event("smoke.lock", "Lock check")
        log_file = log_dir / "anki_study_report.log"
        renamed = log_dir / "anki_study_report.log.renamed"
        log_file.rename(renamed)
        assert renamed.is_file(), "log file should be renamable while logger exists"
        renamed.rename(log_file)

    manager = dashboard_server.DashboardServerManager()
    manager.configure_server_handlers(
        action_handler=lambda action: {"ok": True, "action": action, "message": "OK"},
        status_provider=lambda: {"extra": "ok"},
    )
    state = manager.start(port=0, idle_timeout_seconds=0)
    try:
        token = parse_qs(urlparse(state.url).query)["token"][0]
        base = f"http://{state.host}:{state.port}"
        logging_module.log_event(
            "smoke.token",
            "Token redaction check",
            url=f"{base}/?token={token}#/logs",
        )

        status, data = get_json(f"{base}/api/logs/status")
        assert status == 403, (status, data)

        status, data = get_json(f"{base}/api/logs/status?token={token}")
        assert status == 200, (status, data)
        assert "anki_study_report.log" in data["fileName"], data

        status, data = get_json(f"{base}/api/logs/recent?token={token}&max_bytes=200000")
        assert status == 200, (status, data)
        assert "token=<hidden>" in data["text"], data["text"]
        assert token not in data["text"], data["text"]

        status, data = get_json(f"{base}/api/server/status?token={token}")
        assert status == 200, (status, data)
        assert data["url"].endswith("token=..."), data

        status, data = post_json(f"{base}/api/logs/clear?token=bad")
        assert status == 403, (status, data)

        status, data = post_json(f"{base}/api/logs/clear?token={token}")
        assert status == 200, (status, data)
        assert data["ok"] is True, data
    finally:
        manager.stop()

    print("EXTENSION_LOGGING_SMOKE_OK")


if __name__ == "__main__":
    main()
