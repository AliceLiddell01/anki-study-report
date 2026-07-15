from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from conftest import ROOT


SCRIPT = ROOT / "docker" / "anki-e2e" / "fake-telemetry-server.py"


def load_fake_module():
    spec = importlib.util.spec_from_file_location("asr_fake_telemetry", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def request(base_url: str, path: str, *, method: str = "GET", payload=None, token: str | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(base_url + path, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=3) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def test_fake_ingestion_is_deterministic_and_persists_only_safe_summary(tmp_path: Path):
    module = load_fake_module()
    summary = tmp_path / "summary.json"
    state = module.State(summary)
    server = module.ThreadingHTTPServer(("127.0.0.1", 0), module.handler_factory(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        status, enrolled = request(base_url, "/v1/installations", method="POST", payload={"purposes": ["featureUsage"]})
        assert status == 201
        event = {"eventId": "event-secret-id", "eventCode": "dashboard.opened"}
        status, ack = request(
            base_url,
            "/v1/events",
            method="POST",
            payload={"telemetrySchemaVersion": 1, "batchId": "batch-secret-id", "events": [event]},
            token=enrolled["writeToken"],
        )
        assert status == 202
        assert ack == {"batchId": "batch-secret-id", "acknowledgedEventIds": ["event-secret-id"]}
        persisted = summary.read_text(encoding="utf-8")
        assert "dashboard.opened" in persisted
        assert "event-secret-id" not in persisted
        assert enrolled["writeToken"] not in persisted
        assert enrolled["installationId"] not in persisted

        assert request(base_url, "/__e2e/control", method="POST", payload={"offline": True})[0] == 200
        assert request(
            base_url,
            "/v1/events",
            method="POST",
            payload={"telemetrySchemaVersion": 1, "batchId": "batch-secret-id-2", "events": [event]},
            token=enrolled["writeToken"],
        )[0] == 503
        assert json.loads(summary.read_text(encoding="utf-8"))["eventCount"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
