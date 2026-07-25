from __future__ import annotations

from types import SimpleNamespace

from conftest import import_addon_module


runtime = import_addon_module("inspection_profile_runtime")
store_module = import_addon_module("inspection_profile_store")


class FakeTaskman:
    def __init__(self):
        self.calls = 0

    def run_on_main(self, callback):
        self.calls += 1
        callback()


class FakeQueryOp:
    def __init__(self, *, parent, op, success):
        self.parent = parent
        self.op = op
        self.success = success
        self.failure_callback = None

    def failure(self, callback):
        self.failure_callback = callback
        return self

    def run_in_background(self):
        try:
            self.success(self.op(self.parent.col))
        except Exception as error:
            self.failure_callback(error)
        return self


def test_query_uses_serialized_queryop_and_store_snapshot(monkeypatch, tmp_path):
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    store = store_module.InspectionProfileStore(tmp_path / "inspection_profiles.json")
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    calls = []
    monkeypatch.setattr(
        runtime,
        "execute_inspection_query",
        lambda col, payload, snapshot: calls.append((col, payload, snapshot)) or {"schemaVersion": 1, "items": []},
    )
    payload = {"schemaVersion": 1, "noteTypeIds": [], "limit": 500}
    result = runtime.run_inspection_profile_query_sync(mw, payload, store)
    assert result == {"ok": True, "response": {"schemaVersion": 1, "items": []}}
    assert taskman.calls == 1
    assert calls[0][2]["status"] == "empty"


def test_invalid_request_and_collection_unavailable_are_typed(tmp_path):
    store = store_module.InspectionProfileStore(tmp_path / "inspection_profiles.json")
    invalid = runtime.run_inspection_profile_query_sync(
        SimpleNamespace(col=object(), taskman=FakeTaskman()),
        {"schemaVersion": 1, "noteTypeIds": [], "limit": 500, "sql": "select * from notes"},
        store,
    )
    assert invalid["error"] == "invalid_inspection_profile_request"
    assert invalid["fieldErrors"] == {"sql": "Unexpected field."}
    assert runtime.run_inspection_profile_query_sync(
        None, {"schemaVersion": 1, "noteTypeIds": [], "limit": 500}, store
    )["error"] == "inspection_profiles_unavailable"


def test_revision_and_future_schema_failures_are_safe(monkeypatch, tmp_path):
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    store = store_module.InspectionProfileStore(tmp_path / "inspection_profiles.json")
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    monkeypatch.setattr(
        runtime,
        "prepare_inspection_update",
        lambda _col, _payload: (_ for _ in ()).throw(store_module.InspectionProfileConflictError(9)),
    )
    payload = {"schemaVersion": 1, "action": "delete", "expectedRevision": 0, "noteTypeId": "123"}
    result = runtime.run_inspection_profile_update_sync(mw, payload, store)
    assert result == {"ok": False, "error": "inspection_profile_revision_conflict", "currentRevision": 9}
    assert "tmp_path" not in repr(result)
