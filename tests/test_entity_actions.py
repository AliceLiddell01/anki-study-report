from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import import_addon_module


entity_actions = import_addon_module("entity_actions")
ENTITY_ACTION_BATCH_LIMIT = entity_actions.ENTITY_ACTION_BATCH_LIMIT
EntityActionStaleError = entity_actions.EntityActionStaleError
EntityActionValidationError = entity_actions.EntityActionValidationError
action_result = entity_actions.action_result
normalize_card_action_request = entity_actions.normalize_card_action_request
normalize_note_action_request = entity_actions.normalize_note_action_request
prepare_card_action = entity_actions.prepare_card_action
prepare_note_action = entity_actions.prepare_note_action


class FakeTags:
    @staticmethod
    def split(value: str) -> list[str]:
        return [tag for tag in value.replace("\u3000", " ").split(" ") if tag]


class FakeCollection:
    def __init__(self) -> None:
        self.cards = {
            1: SimpleNamespace(id=1, queue=2, flags=0, did=20, odid=0),
            2: SimpleNamespace(id=2, queue=-1, flags=3, did=30, odid=0),
            3: SimpleNamespace(id=3, queue=-2, flags=0, did=20, odid=0),
            4: SimpleNamespace(id=4, queue=2, flags=0, did=99, odid=20),
        }
        self.notes = {
            10: SimpleNamespace(id=10, tags=["Japanese::Grammar"]),
            11: SimpleNamespace(id=11, tags=["important"]),
        }
        self.tags = FakeTags()
        self.decks = SimpleNamespace(get=lambda deck_id: {
            20: {"id": 20, "name": "Source", "dyn": 0},
            30: {"id": 30, "name": "Target", "dyn": 0},
            99: {"id": 99, "name": "Filtered", "dyn": 1},
        }.get(deck_id))

    def get_card(self, card_id: int):
        return self.cards[card_id]

    def get_note(self, note_id: int):
        return self.notes[note_id]


def test_card_request_is_strict_and_ids_are_decimal_strings() -> None:
    assert normalize_card_action_request(
        {"action": "suspend", "cardIds": ["1", "2"], "requestId": "cards-1"}
    )["cardIds"] == [1, 2]
    for bad_ids in ([1], [True], ["1", "1"], ["0"], ["+1"], ["1"] * (ENTITY_ACTION_BATCH_LIMIT + 1)):
        with pytest.raises(EntityActionValidationError):
            normalize_card_action_request({"action": "suspend", "cardIds": bad_ids, "requestId": None})
    with pytest.raises(EntityActionValidationError):
        normalize_card_action_request({"action": "suspend", "cardIds": ["1"], "flag": 3, "requestId": None})


def test_flag_contract_has_explicit_set_and_clear_shapes() -> None:
    request = normalize_card_action_request(
        {"action": "set_flag", "cardIds": ["1"], "flag": 7, "requestId": "flag-1"}
    )
    assert request["flag"] == 7
    for flag in (0, 8, True, 2.5):
        with pytest.raises(EntityActionValidationError):
            normalize_card_action_request(
                {"action": "set_flag", "cardIds": ["1"], "flag": flag, "requestId": None}
            )
    assert normalize_card_action_request(
        {"action": "clear_flag", "cardIds": ["1"], "requestId": None}
    )["action"] == "clear_flag"


def test_note_tags_are_bounded_deduplicated_and_native_space_parsing_is_preserved() -> None:
    request = normalize_note_action_request(
        {
            "action": "add_tags",
            "noteIds": ["10"],
            "tags": ["Japanese::Grammar", "japanese::grammar", "one two"],
            "requestId": "notes-1",
        }
    )
    assert request["tags"] == ["Japanese::Grammar", "one two"]
    plan = prepare_note_action(FakeCollection(), request)
    assert plan.native_args == {"tags": "Japanese::Grammar one two"}
    assert plan.args == {"tagCount": 3}
    for tags in ([], [""], ["bad\nvalue"], ["x"] * 21, ["x" * 1001]):
        with pytest.raises(EntityActionValidationError):
            normalize_note_action_request(
                {"action": "add_tags", "noteIds": ["10"], "tags": tags, "requestId": None}
            )


def test_preflight_resolves_complete_batch_before_any_operation() -> None:
    col = FakeCollection()
    with pytest.raises(EntityActionStaleError):
        prepare_card_action(
            col,
            normalize_card_action_request(
                {"action": "suspend", "cardIds": ["1", "999"], "requestId": "stale"}
            ),
        )


@pytest.mark.parametrize(
    ("action", "extra", "affected", "code"),
    [
        ("suspend", {}, 1, "cards.suspended"),
        ("unsuspend", {}, 1, "cards.unsuspended"),
        ("set_flag", {"flag": 3}, 1, "cards.flag_set"),
        ("clear_flag", {}, 1, "cards.flag_cleared"),
    ],
)
def test_card_desired_state_counts_are_deterministic(action, extra, affected, code) -> None:
    request = {"action": action, "cardIds": ["1", "2"], "requestId": "batch", **extra}
    plan = prepare_card_action(FakeCollection(), normalize_card_action_request(request))
    assert (plan.affected_count, plan.unchanged_count) == (affected, 2 - affected)
    assert action_result(plan, undoable=True)["resultCode"] == code


@pytest.mark.parametrize(
    ("action", "tags", "affected", "code"),
    [
        ("add_tags", ["important"], 1, "notes.tags_added"),
        ("remove_tags", ["IMPORTANT"], 1, "notes.tags_removed"),
    ],
)
def test_note_desired_state_counts_are_case_insensitive(action, tags, affected, code) -> None:
    plan = prepare_note_action(
        FakeCollection(),
        normalize_note_action_request(
            {"action": action, "noteIds": ["10", "11"], "tags": tags, "requestId": None}
        ),
    )
    assert (plan.affected_count, plan.unchanged_count) == (affected, 1)
    assert action_result(plan, undoable=True)["resultCode"] == code


def test_noop_result_is_typed_and_not_claimed_undoable() -> None:
    plan = prepare_card_action(
        FakeCollection(),
        normalize_card_action_request(
            {"action": "suspend", "cardIds": ["2"], "requestId": "noop"}
        ),
    )
    result = action_result(plan, undoable=False)
    assert result == {
        "schemaVersion": 1,
        "entityType": "cards",
        "action": "suspend",
        "requestedCount": 1,
        "affectedCount": 0,
        "unchangedCount": 1,
        "undoable": False,
        "resultCode": "action.no_changes",
        "args": {},
        "requestId": "noop",
    }


@pytest.mark.parametrize(
    ("action", "affected", "code"),
    [("bury", 1, "cards.buried"), ("unbury", 1, "cards.unburied")],
)
def test_bury_actions_are_explicit_and_do_not_expand_note_siblings(action, affected, code) -> None:
    plan = prepare_card_action(
        FakeCollection(),
        normalize_card_action_request(
            {"action": action, "cardIds": ["1", "3"], "requestId": "bury-1"}
        ),
    )
    assert plan.entity_ids == (1, 3)
    assert plan.affected_count == affected
    assert action_result(plan, undoable=True)["resultCode"] == code


def test_move_resolves_normal_destination_and_reports_noop() -> None:
    col = FakeCollection()
    move = normalize_card_action_request(
        {"action": "move_to_deck", "cardIds": ["1", "2"], "deckId": "30", "requestId": "move-1"}
    )
    plan = prepare_card_action(col, move)
    assert (plan.affected_count, plan.unchanged_count) == (1, 1)
    assert plan.native_args == {"deckId": 30}
    assert action_result(plan, undoable=True)["resultCode"] == "cards.moved"
    noop = prepare_card_action(
        col,
        normalize_card_action_request(
            {"action": "move_to_deck", "cardIds": ["2"], "deckId": "30", "requestId": "move-noop"}
        ),
    )
    assert action_result(noop, undoable=False)["resultCode"] == "action.no_changes"


@pytest.mark.parametrize(
    ("card_ids", "deck_id", "code"),
    [
        (["1"], "99", "cards.destination_filtered"),
        (["1"], "404", "cards.destination_not_found"),
        (["4"], "30", "cards.filtered_source_unsupported"),
    ],
)
def test_move_rejects_filtered_or_stale_destination_and_filtered_source(card_ids, deck_id, code) -> None:
    request = normalize_card_action_request(
        {"action": "move_to_deck", "cardIds": card_ids, "deckId": deck_id, "requestId": "move-bad"}
    )
    with pytest.raises(entity_actions.EntityActionDomainError) as raised:
        prepare_card_action(FakeCollection(), request)
    assert raised.value.code == code
