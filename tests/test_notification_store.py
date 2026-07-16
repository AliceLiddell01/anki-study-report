from __future__ import annotations

import json

import pytest

from conftest import fresh_import_addon_module


NOW = "2026-07-17T10:00:00Z"


def candidate(severity="warning", *, load=80):
    return {
        "code": "workload.review_pressure",
        "category": "workload",
        "severity": severity,
        "dedupeKey": "workload.review_pressure:all",
        "entityType": "all_collection",
        "entityId": None,
        "evidence": {
            "currentLoad": load,
            "baselineMedian": 30.0,
            "activeDays": 20,
            "ratio": round(load / 30, 3),
            "delta": load - 30.0,
        },
        "detectorVersion": "signals-v1.0",
    }


def test_signal_lifecycle_keeps_read_and_resolution_independent(tmp_path):
    module = fresh_import_addon_module("notification_store")
    store = module.NotificationStore(tmp_path / "notifications.sqlite3")

    created = store.reconcile("workload.review_pressure", [candidate()], source_revision="r1", evaluated_at=NOW)
    assert created["created"] == 1
    first = store.summary()["items"][0]
    assert first["kind"] == "signal_created"
    assert first["signalStatus"] == "active"
    assert store.summary()["unreadCount"] == 1

    same = store.reconcile("workload.review_pressure", [candidate(load=85)], source_revision="r2", evaluated_at="2026-07-17T11:00:00Z")
    assert same["updated"] == 1
    assert store.summary()["unreadCount"] == 1

    escalated = store.reconcile("workload.review_pressure", [candidate("critical", load=150)], source_revision="r3", evaluated_at="2026-07-17T12:00:00Z")
    assert escalated["escalated"] == 1
    assert store.summary()["unreadCount"] == 2
    newest = store.summary()["items"][0]
    store.mark_read([newest["notificationId"]], read_at="2026-07-17T12:01:00Z")
    assert store.list_notifications(tab="active")["total"] == 2

    decreased = store.reconcile("workload.review_pressure", [candidate("warning")], source_revision="r4", evaluated_at="2026-07-17T13:00:00Z")
    assert decreased["escalated"] == 0
    assert store.reconcile("workload.review_pressure", [], source_revision="r5", evaluated_at="2026-07-17T14:00:00Z")["resolved"] == 0
    assert store.list_notifications(tab="active")["total"] == 2
    assert store.reconcile("workload.review_pressure", [], source_revision="r6", evaluated_at="2026-07-17T15:00:00Z")["resolved"] == 1
    assert store.list_notifications(tab="active")["total"] == 0
    assert store.list_notifications()["total"] == 2

    reactivated = store.reconcile("workload.review_pressure", [candidate()], source_revision="r7", evaluated_at="2026-07-17T16:00:00Z")
    assert reactivated["reactivated"] == 1
    history = store.list_notifications()
    assert history["total"] == 3
    assert history["items"][0]["kind"] == "signal_reactivated"


def test_preferences_toast_delivery_and_profile_isolation(tmp_path):
    module = fresh_import_addon_module("notification_store")
    first = module.NotificationStore(tmp_path / "profile-a" / "notifications.sqlite3")
    second = module.NotificationStore(tmp_path / "profile-b" / "notifications.sqlite3")
    assert first.preferences() == module.DEFAULT_PREFERENCES
    assert first.summary()["unreadCount"] == second.summary()["unreadCount"] == 0

    first.reconcile("workload.review_pressure", [candidate("critical", load=150)], source_revision="r1", evaluated_at=NOW)
    assert first.summary()["unreadCount"] == 1
    assert second.summary()["unreadCount"] == 0
    toast = first.toast_candidates(session_started_at=NOW)
    assert len(toast) == 1
    assert first.mark_toast_delivered([toast[0]["notificationId"]]) == 1
    assert first.toast_candidates(session_started_at=NOW) == []

    updated = first.update_preferences({
        "showUnreadBadge": False,
        "showInAppToasts": False,
        "minimumToastSeverity": "warning",
        "toastCategories": {"workload": False},
    })
    assert updated["showUnreadBadge"] is False
    assert updated["showInAppToasts"] is False
    assert updated["toastCategories"]["workload"] is False
    reopened = module.NotificationStore(first.path)
    assert reopened.preferences() == updated


def test_strict_pagination_preferences_and_evidence_validation(tmp_path):
    module = fresh_import_addon_module("notification_store")
    store = module.NotificationStore(tmp_path / "notifications.sqlite3")
    with pytest.raises(module.NotificationValidationError):
        store.list_notifications(page_limit=51)
    with pytest.raises(module.NotificationValidationError):
        store.update_preferences({"unknown": True})
    invalid = candidate()
    invalid["evidence"]["raw"] = "not allowed"
    with pytest.raises(module.NotificationValidationError):
        store.reconcile("workload.review_pressure", [invalid], source_revision="r1")


def test_corrupt_database_is_quarantined_and_recreated(tmp_path):
    module = fresh_import_addon_module("notification_store")
    path = tmp_path / "notifications.sqlite3"
    path.write_bytes(b"not sqlite")
    store = module.NotificationStore(path)
    assert store.summary()["unreadCount"] == 0
    assert list(tmp_path.glob("notifications.sqlite3.corrupt-*"))
    assert json.loads(store._require_connection().execute("SELECT value_json FROM schema_metadata WHERE key = 'schemaVersion'").fetchone()[0]) == 1


def test_preferences_update_preserves_unknown_future_fields(tmp_path):
    module = fresh_import_addon_module("notification_store")
    store = module.NotificationStore(tmp_path / "notifications.sqlite3")
    raw = {
        **module.DEFAULT_PREFERENCES,
        "futureDeliveryMode": "reserved",
        "toastCategories": {**module.DEFAULT_PREFERENCES["toastCategories"], "future_category": False},
    }
    store._require_connection().execute(
        "UPDATE notification_preferences SET preferences_json = ? WHERE id = 1",
        (json.dumps(raw),),
    )
    public = store.update_preferences({"showUnreadBadge": False})
    persisted = json.loads(store._require_connection().execute(
        "SELECT preferences_json FROM notification_preferences WHERE id = 1"
    ).fetchone()[0])
    assert public["showUnreadBadge"] is False
    assert "futureDeliveryMode" not in public
    assert persisted["futureDeliveryMode"] == "reserved"
    assert persisted["toastCategories"]["future_category"] is False


def test_toast_preferences_and_history_pruning_are_bounded(tmp_path, monkeypatch):
    module = fresh_import_addon_module("notification_store")
    monkeypatch.setattr(module, "NOTIFICATION_HISTORY_CAP", 3)
    store = module.NotificationStore(tmp_path / "notifications.sqlite3")
    store.reconcile("workload.review_pressure", [candidate("warning")], source_revision="r1", evaluated_at=NOW)
    assert store.toast_candidates(session_started_at=NOW) == []
    store.update_preferences({"minimumToastSeverity": "warning"})
    assert len(store.toast_candidates(session_started_at=NOW)) == 1
    store.update_preferences({"toastCategories": {"workload": False}})
    assert store.toast_candidates(session_started_at=NOW) == []

    store.mark_all_read(read_at="2026-07-17T10:01:00Z")
    for index in range(5):
        store.upsert_release(
            f"1.1.{index}",
            source_revision=f"release:{index}",
            created_at=f"2026-07-17T11:0{index}:00Z",
        )
        store.mark_release_read(f"1.1.{index}", read_at=f"2026-07-17T11:1{index}:00Z")
    store.reconcile("workload.review_pressure", [candidate("warning", load=90)], source_revision="r2", evaluated_at="2026-07-17T12:00:00Z")
    assert store.list_notifications(page_limit=50)["total"] <= 3
    assert store.summary()["activeSignalCount"] == 1
