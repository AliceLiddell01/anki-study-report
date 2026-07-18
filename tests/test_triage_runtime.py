from __future__ import annotations

from types import SimpleNamespace

from conftest import import_addon_module


runtime = import_addon_module("triage_runtime")


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
            self.failure_callback(RuntimeError("private card IDs token=secret"))
        return self


def payload():
    return {
        "schemaVersion": 3,
        "dataset": "automatic",
        "scope": {"periodStartMs": 1, "periodEndMs": 2, "deckIds": []},
        "limit": 100,
    }


def test_triage_queryop_bridge_schedules_collection_read_and_supplies_signals(monkeypatch):
    taskman = FakeTaskman()
    mw = SimpleNamespace(col=object(), taskman=taskman)
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    calls = []
    monkeypatch.setattr(
        runtime,
        "execute_triage_query",
        lambda col, value, **kwargs: calls.append((col, value, kwargs)) or {"schemaVersion": 3, "items": []},
    )
    FakeQueryOp.behavior = "success"

    result = runtime.run_triage_query_sync(
        mw,
        payload(),
        signal_provider=lambda: [{"code": "card.repeated_again"}],
        profile_store_provider=lambda: {"status": "empty", "revision": 0, "profiles": []},
    )

    assert result == {"ok": True, "response": {"schemaVersion": 3, "items": []}}
    assert taskman.calls == 1
    assert calls[0][2]["signal_rows"] == [{"code": "card.repeated_again"}]
    assert calls[0][2]["signal_source_status"]["status"] == "available"
    assert calls[0][2]["profile_store_snapshot"]["status"] == "empty"


def test_invalid_request_never_reaches_task_manager():
    taskman = FakeTaskman()
    result = runtime.run_triage_query_sync(
        SimpleNamespace(col=object(), taskman=taskman),
        {**payload(), "sql": "select * from cards"},
    )
    assert result["error"] == "invalid_triage_request"
    assert taskman.calls == 0


def test_collection_unavailable_returns_typed_response_and_signal_failure_is_partial(monkeypatch):
    logged = []
    monkeypatch.setattr(runtime, "log_event", lambda *args, **kwargs: logged.append((args, kwargs)))

    result = runtime.run_triage_query_sync(
        None,
        payload(),
        signal_provider=lambda: (_ for _ in ()).throw(RuntimeError("private path token=secret")),
    )

    assert result["ok"] is True
    response = result["response"]
    assert response["schemaVersion"] == 3
    assert response["status"] == "unavailable"
    assert response["sourceStatus"]["attention"]["status"] == "unavailable"
    assert response["sourceStatus"]["signals"]["status"] == "error"
    assert "private" not in repr(result)
    assert "secret" not in repr(result)
    assert "private" not in repr(logged)
    assert "secret" not in repr(logged)


def test_failure_and_timeout_are_generic_and_typed(monkeypatch):
    mw = SimpleNamespace(col=object(), taskman=FakeTaskman())
    monkeypatch.setattr(runtime, "_query_op_type", lambda: FakeQueryOp)
    monkeypatch.setattr(runtime, "log_event", lambda *_args, **_kwargs: None)

    FakeQueryOp.behavior = "failure"
    assert runtime.run_triage_query_sync(mw, payload(), signal_provider=lambda: [])["error"] == "triage_failed"

    FakeQueryOp.behavior = "timeout"
    result = runtime.run_triage_query_sync(mw, payload(), signal_provider=lambda: [], timeout_seconds=0.001)
    assert result == {"ok": False, "error": "triage_timeout", "message": "The triage request did not finish in time."}
