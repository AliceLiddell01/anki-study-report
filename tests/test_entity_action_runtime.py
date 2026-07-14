from __future__ import annotations

import sys
import types
from types import SimpleNamespace

from conftest import import_addon_module


runtime = import_addon_module("entity_action_runtime")


class FakeOperation:
    def __init__(self) -> None:
        self.success_callback = None
        self.failure_callback = None
        self.runs = 0

    def success(self, callback):
        self.success_callback = callback
        return self

    def failure(self, callback):
        self.failure_callback = callback
        return self

    def run_in_background(self):
        self.runs += 1
        self.success_callback(SimpleNamespace(count=1))
        return self


class FakeCollection:
    tags = SimpleNamespace(split=lambda value: value.split())

    def __init__(self) -> None:
        self.cards = {1: SimpleNamespace(id=1, queue=2, flags=0), 2: SimpleNamespace(id=2, queue=-1, flags=3)}
        self.notes = {10: SimpleNamespace(id=10, tags=[]), 11: SimpleNamespace(id=11, tags=["keep"])}

    def get_card(self, entity_id):
        return self.cards[entity_id]

    def get_note(self, entity_id):
        return self.notes[entity_id]


def fake_mw():
    return SimpleNamespace(
        col=FakeCollection(),
        taskman=SimpleNamespace(run_on_main=lambda callback: callback()),
    )


def test_card_runtime_runs_one_native_batch_and_reports_undo() -> None:
    operation = FakeOperation()
    calls = []
    original = runtime._native_operation
    runtime._native_operation = lambda mw, plan: calls.append((mw, plan)) or operation
    try:
        result = runtime.run_card_action_sync(
            fake_mw(),
            {"action": "suspend", "cardIds": ["1", "2"], "requestId": "cards-1"},
        )
    finally:
        runtime._native_operation = original
    assert len(calls) == 1
    assert operation.runs == 1
    assert result["response"] == {
        "schemaVersion": 1,
        "entityType": "cards",
        "action": "suspend",
        "requestedCount": 2,
        "affectedCount": 1,
        "unchangedCount": 1,
        "undoable": True,
        "resultCode": "cards.suspended",
        "args": {},
        "requestId": "cards-1",
    }


def test_note_runtime_runs_one_native_batch() -> None:
    operation = FakeOperation()
    calls = []
    original = runtime._native_operation
    runtime._native_operation = lambda mw, plan: calls.append(plan) or operation
    try:
        result = runtime.run_note_action_sync(
            fake_mw(),
            {"action": "add_tags", "noteIds": ["10", "11"], "tags": ["keep"], "requestId": "notes-1"},
        )
    finally:
        runtime._native_operation = original
    assert len(calls) == 1
    assert result["response"]["resultCode"] == "notes.tags_added"
    assert result["response"]["undoable"] is True


def test_noop_skips_native_operation() -> None:
    original = runtime._native_operation
    runtime._native_operation = lambda *_args: (_ for _ in ()).throw(AssertionError("must not run"))
    try:
        result = runtime.run_card_action_sync(
            fake_mw(),
            {"action": "suspend", "cardIds": ["2"], "requestId": "noop"},
        )
    finally:
        runtime._native_operation = original
    assert result["response"]["resultCode"] == "action.no_changes"
    assert result["response"]["undoable"] is False


def test_stale_batch_fails_before_native_operation() -> None:
    original = runtime._native_operation
    runtime._native_operation = lambda *_args: (_ for _ in ()).throw(AssertionError("must not run"))
    try:
        result = runtime.run_card_action_sync(
            fake_mw(),
            {"action": "suspend", "cardIds": ["1", "999"], "requestId": "stale"},
        )
    finally:
        runtime._native_operation = original
    assert result == {
        "ok": False,
        "error": "entity_action_stale",
        "message": "A selected card is unavailable or was deleted.",
        "requestId": "stale",
    }


def test_invalid_request_and_unavailable_collection_are_typed() -> None:
    invalid = runtime.run_card_action_sync(
        fake_mw(), {"action": "suspend", "cardIds": [1], "requestId": "bad"}
    )
    assert invalid["error"] == "invalid_entity_action"
    unavailable = runtime.run_note_action_sync(
        None, {"action": "add_tags", "noteIds": ["10"], "tags": ["x"], "requestId": "down"}
    )
    assert unavailable["error"] == "entity_action_unavailable"


def test_runtime_failure_log_contains_only_safe_action_metadata() -> None:
    logged = []
    original_operation = runtime._native_operation
    original_log = runtime.log_event
    runtime._native_operation = lambda *_args: (_ for _ in ()).throw(RuntimeError("secret-tag raw-id-999"))
    runtime.log_event = lambda *args, **kwargs: logged.append((args, kwargs))
    try:
        result = runtime.run_note_action_sync(
            fake_mw(),
            {"action": "add_tags", "noteIds": ["10"], "tags": ["secret-tag"], "requestId": "safe-log"},
        )
    finally:
        runtime._native_operation = original_operation
        runtime.log_event = original_log
    assert result["error"] == "entity_action_failed"
    assert logged[0][1]["entity_type"] == "notes"
    assert logged[0][1]["action"] == "add_tags"
    assert logged[0][1]["count"] == 1
    assert "secret-tag" not in repr(logged)
    assert "999" not in repr(logged)


def test_native_bridge_uses_anki_2605_wrapper_signatures(monkeypatch) -> None:
    calls = []
    scheduling = types.ModuleType("aqt.operations.scheduling")
    scheduling.suspend_cards = lambda *, parent, card_ids: calls.append(("suspend", parent, card_ids)) or "suspend-op"
    scheduling.unsuspend_cards = lambda *, parent, card_ids: calls.append(("unsuspend", parent, card_ids)) or "unsuspend-op"
    card = types.ModuleType("aqt.operations.card")
    card.set_card_flag = lambda *, parent, card_ids, flag: calls.append(("flag", parent, card_ids, flag)) or "flag-op"
    tag = types.ModuleType("aqt.operations.tag")
    tag.add_tags_to_notes = lambda *, parent, note_ids, space_separated_tags: calls.append(("add", parent, note_ids, space_separated_tags)) or "add-op"
    tag.remove_tags_from_notes = lambda *, parent, note_ids, space_separated_tags: calls.append(("remove", parent, note_ids, space_separated_tags)) or "remove-op"
    operations = types.ModuleType("aqt.operations")
    monkeypatch.setitem(sys.modules, "aqt.operations", operations)
    monkeypatch.setitem(sys.modules, "aqt.operations.scheduling", scheduling)
    monkeypatch.setitem(sys.modules, "aqt.operations.card", card)
    monkeypatch.setitem(sys.modules, "aqt.operations.tag", tag)
    parent = object()
    plan_type = import_addon_module("entity_actions").EntityActionPlan

    def plan(action, entity_type="cards", native_args=None):
        return plan_type(entity_type, action, (1, 2), 2, 2, 0, None, {}, native_args or {})

    assert runtime._native_operation(parent, plan("suspend")) == "suspend-op"
    assert runtime._native_operation(parent, plan("unsuspend")) == "unsuspend-op"
    assert runtime._native_operation(parent, plan("set_flag", native_args={"flag": 3})) == "flag-op"
    assert runtime._native_operation(parent, plan("clear_flag")) == "flag-op"
    assert runtime._native_operation(parent, plan("add_tags", "notes", {"tags": "a b"})) == "add-op"
    assert runtime._native_operation(parent, plan("remove_tags", "notes", {"tags": "a b"})) == "remove-op"
    assert calls == [
        ("suspend", parent, [1, 2]),
        ("unsuspend", parent, [1, 2]),
        ("flag", parent, [1, 2], 3),
        ("flag", parent, [1, 2], 0),
        ("add", parent, [1, 2], "a b"),
        ("remove", parent, [1, 2], "a b"),
    ]
