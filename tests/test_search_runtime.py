from __future__ import annotations

from types import SimpleNamespace

from conftest import import_addon_module


runtime = import_addon_module("search_runtime")


class FakeTaskman:
    def __init__(self):
        self.calls = 0

    def run_on_main(self, callback):
        self.calls += 1
        callback()


class FakeQueryOp:
    behavior = "success"

    def __init__(self, *, parent, op, success):
        self.parent = parent
        self.op = op
        self.success = success
        self.failure_callback = None

    def failure(self, callback):
        self.failure_callback = callback
        return self

    def run_in_background(self):
        if self.behavior == "success":
            self.success(self.op(self.parent.col))
        elif self.behavior == "failure":
            self.failure_callback(RuntimeError("native query and token must stay private"))
        return self


def payload():
    return {
        "mode": "cards",
        "query": "deck:private",
        "filters": [],
        "sort": {"key": "entity_id", "direction": "asc"},
        "page": 1,
        "pageSize": 25,
        "requestId": "runtime-1",
    }


def test_queryop_bridge_schedules_on_main_and_returns_success(monkeypatch):
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    monkeypatch.setattr(runtime, "execute_search_request", lambda col, value: {"mode": value["mode"], "items": []})
    FakeQueryOp.behavior = "success"
    result = runtime.run_search_query_sync(mw, payload())
    assert result == {"ok": True, "response": {"mode": "cards", "items": []}}
    assert taskman.calls == 1


def test_metadata_request_uses_the_same_read_only_queryop_bridge(monkeypatch):
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    monkeypatch.setattr(runtime, "execute_search_request", lambda col, value: {"kind": value["kind"], "decks": []})
    FakeQueryOp.behavior = "success"
    result = runtime.run_search_query_sync(mw, {"kind": "metadata", "requestId": "metadata-1"})
    assert result == {"ok": True, "response": {"kind": "metadata", "decks": []}}
    assert taskman.calls == 1


def test_invalid_request_never_reaches_anki_task_manager():
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    result = runtime.run_search_query_sync(mw, {"mode": "cards", "query": "x", "pageSize": 1000})
    assert result["error"] == "invalid_search_request"
    assert taskman.calls == 0


def test_queryop_failure_is_typed_and_does_not_echo_query_or_exception(monkeypatch):
    mw = SimpleNamespace(col=object(), taskman=FakeTaskman())
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    logged = []
    monkeypatch.setattr(runtime, "log_event", lambda *args, **kwargs: logged.append((args, kwargs)))
    FakeQueryOp.behavior = "failure"
    result = runtime.run_search_query_sync(mw, payload())
    assert result == {
        "ok": False,
        "error": "search_failed",
        "message": "The search request failed.",
        "requestId": "runtime-1",
    }
    assert "private" not in repr(result)
    assert "token" not in repr(result)
    assert "private" not in repr(logged)
    assert "token" not in repr(logged)
    assert logged[0][1]["exception_type"] == "RuntimeError"


def test_unavailable_and_timeout_paths_are_typed(monkeypatch):
    assert runtime.run_search_query_sync(None, payload())["error"] == "search_unavailable"
    mw = SimpleNamespace(col=object(), taskman=FakeTaskman())
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    FakeQueryOp.behavior = "timeout"
    result = runtime.run_search_query_sync(mw, payload(), timeout_seconds=0.001)
    assert result["error"] == "search_timeout"
    assert result["requestId"] == "runtime-1"
