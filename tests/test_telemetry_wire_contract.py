from __future__ import annotations

from datetime import datetime, timezone
import json

from conftest import fresh_import_addon_module


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


class CaptureTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.client_module = None

    def request(self, method, url, *, headers, body, timeout):
        call = {
            "method": method,
            "url": url,
            "headers": dict(headers),
            "body": body,
            "timeout": timeout,
        }
        self.calls.append(call)
        if url.endswith("/v1/installations"):
            return self.client_module.HttpResult(
                201,
                {},
                {"installationId": "wire-contract-installation", "writeToken": "wire-contract-token"},
            )
        payload = json.loads(body)
        return self.client_module.HttpResult(
            202,
            {},
            {"batchId": payload["batchId"], "acknowledgedEventIds": [event["eventId"] for event in payload["events"]]},
        )


def test_version_fields_are_envelope_only_on_the_product_wire_payload(tmp_path):
    product = fresh_import_addon_module("product_notices")
    store_module = fresh_import_addon_module("telemetry_store")
    client_module = fresh_import_addon_module("telemetry_client")

    privacy = product.PrivacyStore(tmp_path / "privacy.json")
    privacy.save_choices(
        {"purposes": {"reliabilityDiagnostics": True, "featureUsage": False}},
        now=NOW,
    )
    store = store_module.TelemetryStore(tmp_path / "telemetry.sqlite3")
    transport = CaptureTransport()
    transport.client_module = client_module
    client = client_module.TelemetryClient(
        store,
        privacy,
        lambda: {
            "addonVersion": "1.1.0",
            "ankiVersion": "26.05",
            "osFamily": "other",
            "locale": "unknown",
            "theme": "unknown",
        },
        endpoint="https://telemetry.invalid",
        transport=transport,
        now_provider=lambda: NOW,
        random_provider=lambda: 0.5,
    )

    assert client.queue_semantic_event(
        {"eventCode": "addon.started", "occurredAt": "2026-07-17T12:00:00Z"}
    )["queued"] is True
    assert client.send_once() == {
        "ok": True,
        "code": "telemetry.delivered",
        "acknowledgedCount": 1,
    }

    enrollment = json.loads(transport.calls[0]["body"])
    assert set(enrollment) == {
        "telemetrySchemaVersion",
        "consentSchemaVersion",
        "privacyNoticeVersion",
        "purposes",
    }

    batch = json.loads(transport.calls[1]["body"])
    assert set(batch) == {"telemetrySchemaVersion", "batchId", "events"}
    event = batch["events"][0]
    assert set(event) == {
        "eventId",
        "eventCode",
        "occurredAt",
        "addonVersion",
        "ankiVersion",
        "osFamily",
        "locale",
        "theme",
    }
    assert {
        "telemetrySchemaVersion",
        "consentSchemaVersion",
        "privacyNoticeVersion",
    }.isdisjoint(event)

    client.close()
