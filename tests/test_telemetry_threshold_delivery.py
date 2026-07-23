from __future__ import annotations

from datetime import datetime, timezone
import json
import time

from conftest import fresh_import_addon_module


NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, client_module):
        self.client_module = client_module
        self.calls: list[dict] = []

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
                {"installationId": "installation", "writeToken": "write-token"},
            )
        payload = json.loads(body)
        return self.client_module.HttpResult(
            202,
            {},
            {"acknowledgedEventIds": [event["eventId"] for event in payload["events"]]},
        )


def common_dimensions() -> dict[str, str]:
    return {
        "addonVersion": "1.1.0",
        "ankiVersion": "26.05",
        "osFamily": "linux",
        "locale": "unknown",
        "theme": "unknown",
    }


def wait_for_idle_empty_queue(store, client) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if store.queue_count() == 0 and client.public_status()["senderState"] == "idle":
            return
        time.sleep(0.01)
    raise AssertionError(
        f"Telemetry sender did not drain: queue={store.queue_count()} status={client.public_status()}"
    )


def test_threshold_send_survives_empty_consent_transition_and_recent_periodic_send(tmp_path, monkeypatch) -> None:
    product = fresh_import_addon_module("product_notices")
    store_module = fresh_import_addon_module("telemetry_store")
    client_module = fresh_import_addon_module("telemetry_client")

    reliability_only = {"reliabilityDiagnostics": True, "featureUsage": False}
    feature_only = {"reliabilityDiagnostics": False, "featureUsage": True}
    privacy = product.PrivacyStore(tmp_path / "privacy.json")
    privacy.save_choices({"purposes": reliability_only}, now=NOW)
    store = store_module.TelemetryStore(tmp_path / "telemetry.sqlite3")
    transport = FakeTransport(client_module)
    client = client_module.TelemetryClient(
        store,
        privacy,
        common_dimensions,
        endpoint="https://telemetry.invalid",
        transport=transport,
        now_provider=lambda: NOW,
        random_provider=lambda: 0.5,
    )

    try:
        for _ in range(25):
            queued = client.queue_semantic_event({
                "eventCode": "api_operation.failed",
                "featureCode": "dashboard_start",
                "errorCode": "internal_error",
                "occurredAt": "2026-07-24T12:00:00Z",
            })
            assert queued["queued"] is True
        wait_for_idle_empty_queue(store, client)

        original_request_send = client.request_send
        requests: list[dict] = []

        def recorded_request_send(**kwargs):
            requests.append(dict(kwargs))
            return original_request_send(**kwargs)

        monkeypatch.setattr(client, "request_send", recorded_request_send)
        privacy.save_choices({"purposes": feature_only}, now=NOW)
        result = client.apply_privacy_choices(feature_only)

        assert result == {
            "ok": True,
            "code": "telemetry.choices_applied",
            "deletionPending": False,
        }
        assert requests == []

        for _ in range(25):
            queued = client.queue_semantic_event({
                "eventCode": "page.opened",
                "pageCode": "settings_privacy",
                "occurredAt": "2026-07-24T12:00:00Z",
            })
            assert queued["queued"] is True
        wait_for_idle_empty_queue(store, client)

        assert requests == [{"force": True}]
        event_calls = [call for call in transport.calls if call["url"].endswith("/v1/events")]
        assert [len(json.loads(call["body"])["events"]) for call in event_calls] == [25, 25]
    finally:
        client.close()
