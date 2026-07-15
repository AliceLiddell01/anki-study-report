from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3

from conftest import fresh_import_addon_module


def modules():
    contract = fresh_import_addon_module("telemetry_contract")
    store = fresh_import_addon_module("telemetry_store")
    return contract, store


def event(index: int, purpose: str = "featureUsage") -> tuple[str, dict]:
    payload = {
        "eventId": f"00000000-0000-4000-8000-{index:012d}",
        "eventCode": "dashboard.opened",
        "occurredAt": "2026-07-15T12:00:00Z",
        "addonVersion": "1.1.0",
        "ankiVersion": "26.05",
        "osFamily": "windows",
        "locale": "unknown",
        "theme": "unknown",
        "telemetrySchemaVersion": 1,
        "consentSchemaVersion": 1,
        "privacyNoticeVersion": "2026-07-15",
    }
    return purpose, payload


def test_queue_cap_ttl_batch_ack_and_persistence(monkeypatch, tmp_path):
    contract, module = modules()
    monkeypatch.setitem(contract.CONTRACT["limits"], "queueMaxEvents", 3)
    path = tmp_path / "telemetry.sqlite3"
    store = module.TelemetryStore(path)
    for index in range(4):
        purpose, payload = event(index)
        assert store.enqueue(purpose, payload, now=f"2026-07-15T12:00:0{index}Z")
    assert store.queue_count() == 3
    batch = store.due_batch(now="2026-07-15T12:01:00Z")
    assert [item.event_id for item in batch] == [event(index)[1]["eventId"] for index in (1, 2, 3)]
    assert store.acknowledge([batch[0].event_id], delivered_at="2026-07-15T12:02:00Z") == 1
    store.close()

    reopened = module.TelemetryStore(path)
    assert reopened.queue_count() == 2
    assert reopened.public_status()["lastSuccessfulDeliveryAt"] == "2026-07-15T12:02:00Z"
    reopened.due_batch(now="2026-07-23T12:00:00Z")
    assert reopened.queue_count() == 0
    reopened.close()


def test_batch_respects_event_count_and_request_bytes(monkeypatch, tmp_path):
    contract, module = modules()
    monkeypatch.setitem(contract.CONTRACT["limits"], "batchMaxEvents", 2)
    store = module.TelemetryStore(tmp_path / "telemetry.sqlite3")
    for index in range(3):
        purpose, payload = event(index)
        store.enqueue(purpose, payload, now="2026-07-15T12:00:00Z")
    batch = store.due_batch(now="2026-07-15T12:00:01Z")
    body = {"telemetrySchemaVersion": 1, "events": [item.payload for item in batch]}
    assert len(batch) == 2
    assert len(json.dumps(body, separators=(",", ":")).encode()) <= contract.CONTRACT["limits"]["requestBodyMaxBytes"]


def test_credentials_are_secret_and_purpose_withdrawal_is_selective(tmp_path):
    _, module = modules()
    store = module.TelemetryStore(tmp_path / "telemetry.sqlite3")
    store.save_credentials("installation-one", "super-secret-token", created_at="2026-07-15T12:00:00Z")
    assert "super-secret-token" not in repr(store.credentials())
    assert "installation-one" not in json.dumps(store.public_status())
    assert "super-secret-token" not in json.dumps(store.public_status())
    store.enqueue(*event(1, "featureUsage"), now="2026-07-15T12:00:00Z")
    purpose, payload = event(2, "reliabilityDiagnostics")
    payload["eventCode"] = "addon.started"
    store.enqueue(purpose, payload, now="2026-07-15T12:00:00Z")
    assert store.delete_purposes(["featureUsage"]) == 1
    assert store.purpose_counts() == {"reliabilityDiagnostics": 1, "featureUsage": 0}


def test_schema_migration_and_corrupt_database_quarantine(tmp_path):
    _, module = modules()
    legacy = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(legacy)
    connection.executescript(
        """
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE installation_credentials (id INTEGER PRIMARY KEY, installation_id TEXT NOT NULL, write_token TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE queued_events (
          event_id TEXT PRIMARY KEY, purpose TEXT NOT NULL, event_code TEXT NOT NULL,
          occurred_at TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        PRAGMA user_version=0;
        """
    )
    connection.execute("INSERT INTO installation_credentials VALUES (1, 'kept-id', 'kept-token', '2026-07-15T00:00:00Z')")
    connection.commit()
    connection.close()
    migrated = module.TelemetryStore(legacy)
    assert migrated.credentials().installation_id == "kept-id"
    columns = {row[1] for row in migrated._require_connection().execute("PRAGMA table_info(queued_events)")}
    assert {"next_attempt_at", "retry_count"} <= columns
    migrated.close()

    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")
    recovered = module.TelemetryStore(corrupt)
    assert recovered.queue_count() == 0
    assert len(list(tmp_path.glob("corrupt.sqlite3.corrupt-*"))) == 1
