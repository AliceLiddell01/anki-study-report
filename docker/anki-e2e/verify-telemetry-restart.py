#!/usr/bin/env python3
"""Verify telemetry persistence and deletion after a real Anki restart."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def json_request(url: str, *, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json", "User-Agent": "asr-telemetry-e2e"},
    )
    with urlopen(request, timeout=5) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Expected a JSON object")
    return value


def wait_for(provider, predicate, description: str, *, seconds: float = 20, interval: float = 0.1) -> dict:
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        last = provider()
        if predicate(last):
            return last
        time.sleep(interval)
    raise RuntimeError(f"Timed out waiting for {description}: {last!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready", type=Path, required=True)
    parser.add_argument("--fake-endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ready = json.loads(args.ready.read_text(encoding="utf-8"))
    base_url = str(ready["baseUrl"])
    token = str(ready["token"])

    def dashboard(path: str, payload: dict | None = None) -> dict:
        query = urlencode({"token": token})
        return json_request(f"{base_url}{path}?{query}", payload=payload)

    def fake_state() -> dict:
        return json_request(f"{args.fake_endpoint}/__e2e/state")

    restarted = dashboard("/api/telemetry/status")
    pending_after_restart = int(restarted.get("telemetryClient", {}).get("pendingEventCount", 0))
    if pending_after_restart < 25:
        raise RuntimeError("Persistent telemetry queue was not restored after restart")
    before_delivery = fake_state()
    json_request(f"{args.fake_endpoint}/__e2e/control", payload={"offline": False})
    dashboard("/api/privacy", payload={"purposes": {"reliabilityDiagnostics": False, "featureUsage": True}})
    def trigger_due_delivery() -> dict:
        dashboard("/api/privacy", payload={"purposes": {"reliabilityDiagnostics": False, "featureUsage": True}})
        return dashboard("/api/telemetry/status")

    delivered = wait_for(
        trigger_due_delivery,
        lambda value: value.get("telemetryClient", {}).get("pendingEventCount") == 0,
        "post-restart telemetry delivery",
        seconds=60,
        interval=1,
    )
    after_delivery = fake_state()
    if int(after_delivery.get("eventCount", 0)) <= int(before_delivery.get("eventCount", 0)):
        raise RuntimeError("Fake ingestion did not receive the queue restored after restart")

    json_request(f"{args.fake_endpoint}/__e2e/control", payload={"offline": True})
    pending_delete = dashboard("/api/telemetry/delete", payload={})
    if pending_delete.get("deletionPending") is not True or pending_delete.get("confirmed") is True:
        raise RuntimeError("Offline deletion was not retained as pending")
    pending_status = dashboard("/api/telemetry/status")
    if pending_status.get("telemetryClient", {}).get("deletionPending") is not True:
        raise RuntimeError("Deletion pending state was not visible")

    json_request(f"{args.fake_endpoint}/__e2e/control", payload={"offline": False})
    dashboard("/api/telemetry/delete", payload={})
    confirmed = wait_for(
        lambda: dashboard("/api/telemetry/status"),
        lambda value: value.get("telemetryClient", {}).get("deletionPending") is False
        and value.get("telemetryClient", {}).get("enrollmentState") == "not_enrolled",
        "confirmed remote deletion and credential destruction",
    )
    final_fake = fake_state()
    if int(final_fake.get("deletions", 0)) < 1:
        raise RuntimeError("Fake ingestion did not confirm installation deletion")

    proof = {
        "schemaVersion": 1,
        "ok": True,
        "restartPersistence": True,
        "pendingEventsAfterRestart": pending_after_restart,
        "deliveredAfterRestart": int(after_delivery["eventCount"]) - int(before_delivery["eventCount"]),
        "offlineDeletionPending": True,
        "confirmedDeletion": True,
        "credentialDestroyed": confirmed["telemetryClient"]["enrollmentState"] == "not_enrolled",
        "finalFakeSummary": final_fake,
        "lastDeliveryErrorCode": delivered["telemetryClient"].get("lastDeliveryErrorCode"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
