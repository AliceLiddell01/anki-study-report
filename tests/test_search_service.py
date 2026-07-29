from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import import_addon_module


search = import_addon_module("search_service")


class FakeManager:
    def __init__(self, values: dict[int, dict]):
        self.values = values

    def get(self, entity_id: int, default=False):
        return self.values.get(entity_id, default)

    def name(self, entity_id: int) -> str:
        value = self.values.get(entity_id, {})
        return value.get("name", "")


class FakeNote:
    def __init__(self, note_id: int, *, text: str = "Front", tags=None):
        self.id = note_id
        self.mid = 7
        self.fields = [text, "Back"]
        self.tags = list(tags or ["tag-one"])
        self._cards = []

    def note_type(self):
        return {"id": 7, "name": "Basic", "sortf": 0, "tmpls": [{"name": "Card 1"}]}

    def items(self):
        return [("Front", self.fields[0]), ("Back", self.fields[1])]

    def cards(self):
        return list(self._cards)


class FakeCard:
    def __init__(self, card_id: int, note: FakeNote):
        self.id = card_id
        self.nid = note.id
        self.did = 3
        self.odid = 0
        self.ord = 0
        self.queue = 2
        self.type = 2
        self.due = 12
        self.ivl = 10
        self.reps = 5
        self.lapses = 1
        self.flags = 2
        self._note = note
        self.browser_html = ""
        self.reviewer_html = note.fields[0]
        self.question_calls = []
        note._cards.append(self)

    def note(self):
        return self._note

    def template(self):
        return {"name": "Card 1"}

    def question(self, reload=False, browser=False):
        self.question_calls.append((reload, browser))
        return self.browser_html if browser else self.reviewer_html


class FakeCollection:
    def __init__(self, ids=range(1, 4)):
        self.decks = FakeManager({3: {"id": 3, "name": "Languages::Japanese"}})
        self.models = FakeManager({7: {"id": 7, "name": "Basic"}})
        self.notes = {value: FakeNote(value) for value in ids}
        self.cards = {value: FakeCard(value, self.notes[value]) for value in ids}
        self.card_ids = list(ids)
        self.note_ids = list(ids)
        self.loaded_cards = []
        self.loaded_notes = []
        self.built_nodes = None

    def build_search_string(self, *nodes):
        self.built_nodes = nodes
        return "native-query"

    def find_cards(self, query, order=False):
        assert query == "native-query"
        assert order is False
        return list(self.card_ids)

    def find_notes(self, query, order=False):
        assert query == "native-query"
        assert order is False
        return list(self.note_ids)

    def get_card(self, card_id):
        self.loaded_cards.append(card_id)
        return self.cards[card_id]

    def get_note(self, note_id):
        self.loaded_notes.append(note_id)
        return self.notes[note_id]


class FakeSearchNode:
    CardState = SimpleNamespace(
        CARD_STATE_NEW=0,
        CARD_STATE_LEARN=1,
        CARD_STATE_REVIEW=2,
        CARD_STATE_DUE=3,
        CARD_STATE_SUSPENDED=4,
        CARD_STATE_BURIED=5,
    )
    Flag = SimpleNamespace(
        FLAG_NONE=0,
        FLAG_RED=2,
        FLAG_ORANGE=3,
        FLAG_GREEN=4,
        FLAG_BLUE=5,
        FLAG_PINK=6,
        FLAG_TURQUOISE=7,
        FLAG_PURPLE=8,
    )

    def __init__(self, **value):
        self.value = value


def query(**overrides):
    value = {
        "schemaVersion": 2,
        "mode": "cards",
        "query": "deck:Japanese",
        "filters": [],
        "sort": {"key": "entity_id", "direction": "asc"},
        "page": 1,
        "pageSize": 25,
        "requestId": "request-1",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"mode": "cards"}, "schemaVersion"),
        ({"schemaVersion": 1, "mode": "cards"}, "schemaVersion"),
        ({"schemaVersion": 2, "mode": "invalid"}, "mode"),
        ({"schemaVersion": 2, "mode": "cards", "sql": "select 1"}, "sql"),
        ({"schemaVersion": 2, "mode": "cards", "query": "x\x00y"}, "query"),
        ({"schemaVersion": 2, "mode": "cards", "query": "x" * (search.MAX_QUERY_LENGTH + 1)}, "query"),
        ({"schemaVersion": 2, "mode": "cards", "page": True}, "page"),
        ({"schemaVersion": 2, "mode": "cards", "pageSize": 200}, "pageSize"),
        ({"schemaVersion": 2, "mode": "cards", "sort": {"key": "due", "direction": "asc"}}, "sort.key"),
        ({"schemaVersion": 2, "mode": "notes", "filters": [{"type": "state", "state": "due"}]}, "filters.0"),
        ({"schemaVersion": 2, "mode": "cards", "filters": [{"type": "deck", "deckId": "01"}]}, "filters.0.deckId"),
        ({"schemaVersion": 2, "mode": "cards", "filters": [{}]}, "filters.0.type"),
    ],
)
def test_query_validation_rejects_unbounded_or_ambiguous_inputs(payload, field):
    with pytest.raises(search.SearchValidationError) as error:
        search.normalize_search_query_request(payload)
    assert field in error.value.field_errors


def test_inspect_validation_keeps_card_and_note_modes_distinct_and_versioned():
    assert search.normalize_search_inspect_request({"schemaVersion": 2, "mode": "cards", "cardId": "123"})["cardId"] == 123
    assert search.normalize_search_inspect_request({"schemaVersion": 2, "mode": "notes", "noteId": "456"})["noteId"] == 456
    with pytest.raises(search.SearchValidationError) as error:
        search.normalize_search_inspect_request({"schemaVersion": 2, "mode": "cards", "noteId": "456"})
    assert {"cardId", "noteId"} <= set(error.value.field_errors)
    with pytest.raises(search.SearchValidationError) as error:
        search.normalize_search_inspect_request({"mode": "cards", "cardId": "123"})
    assert "schemaVersion" in error.value.field_errors


def test_native_query_combines_parsable_text_with_structured_filters(monkeypatch):
    monkeypatch.setattr(search, "_search_node_type", lambda: FakeSearchNode)
    col = FakeCollection()
    request = search.normalize_search_query_request(query(filters=[
        {"type": "deck", "deckId": "3"},
        {"type": "note_type", "noteTypeId": "7"},
        {"type": "tag", "tag": "marked"},
        {"type": "state", "state": "due"},
        {"type": "flag", "flag": 1},
    ]))
    assert search.build_native_query(col, request) == "native-query"
    assert col.built_nodes[0] == "deck:Japanese"
    assert [node.value for node in col.built_nodes[1:]] == [
        {"deck": "Languages::Japanese"},
        {"note": "Basic"},
        {"tag": "marked"},
        {"card_state": 3},
        {"flag": 2},
    ]


def test_empty_query_is_normalized_by_anki_builder():
    col = FakeCollection([1])
    request = search.normalize_search_query_request(query(query=""))
    assert search.build_native_query(col, request) == "native-query"
    assert col.built_nodes == ("",)


def test_malformed_native_query_is_a_typed_validation_error():
    col = FakeCollection([1])
    col.build_search_string = lambda *nodes: (_ for _ in ()).throw(RuntimeError("parser details"))
    with pytest.raises(search.SearchValidationError) as error:
        search.execute_search_query(col, query(query='deck:"unterminated'))
    assert error.value.field_errors == {"query": "Anki rejected the native search query."}
    assert "unterminated" not in str(error.value)


def test_query_caps_results_paginates_and_loads_only_the_requested_page():
    col = FakeCollection(range(1, 2052))
    result = search.execute_search_query(col, query(page=2, pageSize=25))
    assert result["schemaVersion"] == 2
    assert result["boundedTotal"] == search.RESULT_CAP
    assert result["pageCount"] == 80
    assert result["pageLimit"] == 80
    assert "maxPage" not in result
    assert result["truncated"] is True
    assert result["returnedCount"] == 25
    assert result["hasNext"] is True
    assert [item["cardId"] for item in result["items"]] == [str(value) for value in range(26, 51)]
    assert col.loaded_cards == list(range(26, 51))
    assert col.loaded_notes == []
    assert all(isinstance(item["cardId"], str) and isinstance(item["noteId"], str) for item in result["items"])


def test_result_selection_streams_once_and_keeps_only_the_bounded_ordered_ids():
    class OneShotIds:
        iterations = 0

        def __iter__(self):
            self.iterations += 1
            if self.iterations > 1:
                raise AssertionError("native results must not be iterated twice")
            yield from range(100_000, 0, -1)

        def __len__(self):
            raise AssertionError("selection must not require a materialized Python length")

    found = OneShotIds()
    ids, truncated = search._bounded_sorted_entity_ids(found, limit=search.RESULT_CAP, reverse=False)
    assert found.iterations == 1
    assert truncated is True
    assert len(ids) == search.RESULT_CAP
    assert ids[:3] == [1, 2, 3]
    assert ids[-1] == search.RESULT_CAP


def test_sort_is_deterministic_deduplicated_and_supports_descending():
    col = FakeCollection(range(1, 5))
    col.card_ids = [2, 4, 2, 1, 3]
    result = search.execute_search_query(col, query(sort={"key": "entity_id", "direction": "desc"}))
    assert [item["cardId"] for item in result["items"]] == ["4", "3", "2", "1"]


@pytest.mark.parametrize("page_size", search.ALLOWED_PAGE_SIZES)
def test_allowed_page_sizes_and_page_limit_are_explicit(page_size):
    normalized = search.normalize_search_query_request(query(pageSize=page_size, page=search.RESULT_CAP // page_size))
    assert normalized["pageSize"] == page_size
    with pytest.raises(search.SearchValidationError) as error:
        search.normalize_search_query_request(query(pageSize=page_size, page=search.RESULT_CAP // page_size + 1))
    assert "page" in error.value.field_errors


def test_page_count_reflects_results_and_valid_pages_beyond_it_are_empty():
    col = FakeCollection(range(1, 5))
    first = search.execute_search_query(col, query(page=1, pageSize=25))
    beyond = search.execute_search_query(col, query(page=2, pageSize=25))
    assert first["pageCount"] == 1
    assert first["pageLimit"] == 80
    assert beyond["page"] == 2
    assert beyond["items"] == []
    assert beyond["returnedCount"] == 0
    assert beyond["pageCount"] == 1
    assert beyond["hasNext"] is False


def test_empty_result_uses_page_one_with_zero_page_count():
    result = search.execute_search_query(FakeCollection([]), query(page=1, pageSize=50))
    assert result["page"] == 1
    assert result["pageCount"] == 0
    assert result["pageLimit"] == 40
    assert result["boundedTotal"] == 0
    assert result["items"] == []


def test_notes_mode_has_a_distinct_bounded_projection_and_keeps_primary_text():
    col = FakeCollection(range(1, 3))
    result = search.execute_search_query(col, query(mode="notes", query="tag:one", requestId=None))
    assert result["mode"] == "notes"
    assert "requestId" not in result
    assert col.loaded_notes == [1, 2]
    assert col.loaded_cards == []
    assert set(result["items"][0]) == {
        "noteId", "noteTypeId", "noteTypeName", "primaryText", "tagSummary", "cardCount", "deckSummary"
    }


def test_card_projection_uses_exact_display_identity_without_primary_text_alias(monkeypatch):
    col = FakeCollection([1])
    card = col.cards[1]
    card.browser_html = "<b>Browser identity</b>"
    projected = {"displayText": "Browser identity", "displaySource": "browser_question", "displayStatus": "available", "displayTruncated": False}
    row = search.project_card_row(col, card)
    resolution = search.resolve_card_rows(col, [1])
    monkeypatch.setattr(search, "build_rendered_preview_native_first", lambda *_args: {"renderStatus": "sanitized", "mediaRefs": []})
    details = search.execute_search_inspect(col, {"schemaVersion": 2, "mode": "cards", "cardId": "1"})["details"]
    assert {key: row[key] for key in projected} == projected
    assert {key: resolution["items"][0][key] for key in projected} == projected
    assert {key: details[key] for key in projected} == projected
    assert "primaryText" not in row
    assert "primaryText" not in details


def test_plain_text_projection_removes_active_markup_media_and_cloze():
    value = '<script>alert(1)</script><b>Hello</b> [sound:secret.mp3] {{c1::world::hint}} &amp; ok'
    assert search.safe_plain_text(value) == "Hello world & ok"
    col = FakeCollection([1])
    col.notes[1].fields[0] = value
    result = search.execute_search_inspect(col, {"schemaVersion": 2, "mode": "notes", "noteId": "1"})
    assert result["details"]["primaryText"] == "Hello world & ok"
    assert result["details"]["fields"][0]["value"] == "Hello world & ok"


def test_card_and_note_inspect_return_separate_bounded_models(monkeypatch):
    col = FakeCollection([1])
    preview_calls = []
    monkeypatch.setattr(search, "build_rendered_preview_native_first", lambda collection, card_id, model, fields, card_ord: preview_calls.append((collection, card_id, model["name"], fields, card_ord)) or {"renderStatus": "sanitized", "frontHtml": "<b>safe</b>", "mediaRefs": []})
    card = search.execute_search_inspect(col, {"schemaVersion": 2, "mode": "cards", "cardId": "1"})
    note = search.execute_search_inspect(col, {"schemaVersion": 2, "mode": "notes", "noteId": "1"})
    assert card["mode"] == "cards"
    assert card["details"]["cardId"] == "1"
    assert card["details"]["deck"] == {"deckId": "3", "deckName": "Languages::Japanese"}
    assert card["details"]["renderedPreview"] == {"renderStatus": "sanitized", "frontHtml": "<b>safe</b>", "mediaRefs": []}
    assert preview_calls == [(col, 1, "Basic", ["Front", "Back"], 0)]
    assert "fields" not in card["details"]
    assert note["mode"] == "notes"
    assert note["details"]["noteId"] == "1"
    assert note["details"]["fields"] == [{"name": "Front", "value": "Front"}, {"name": "Back", "value": "Back"}]
    assert note["details"]["cardReferences"] == [{"cardId": "1", "deckId": "3", "templateOrdinal": 0}]
    assert "cardId" not in note["details"]


def test_inspect_returns_typed_not_found_without_leaking_backend_errors():
    col = FakeCollection([1])
    with pytest.raises(search.SearchEntityNotFoundError) as error:
        search.execute_search_inspect(col, {"schemaVersion": 2, "mode": "cards", "cardId": "999"})
    assert error.value.mode == "cards"
    assert "999" not in str(error.value)


def test_execute_revalidates_even_payloads_with_the_complete_key_set():
    col = FakeCollection([1])
    payload = query()
    payload["filters"] = [{"type": "deck", "deckId": 3}]
    with pytest.raises(search.SearchValidationError):
        search.execute_search_query(col, payload)


def test_formatter_resolver_changes_card_row_and_inspect_identity_without_wire_keys():
    formatter_service = import_addon_module("card_display_formatter_service")
    col = FakeCollection(ids=[1])
    card = col.cards[1]
    card.reviewer_html = '【<b>に</b>】<img src="感.gif"><img src="謝.gif">（<b>する</b>）'
    formatter = {
        "noteTypeId": "7", "noteTypeName": "Basic", "templateOrdinal": None,
        "templateName": None, "storedState": "enabled", "inputSource": "reviewer_front",
        "textMode": "preserve", "imageMode": "stem", "audioMode": "omit",
        "maxLines": 1, "lineSeparator": " ", "maxCharacters": 240,
        "updatedAt": "2026-07-19T00:00:00Z",
    }
    resolver = formatter_service.CardDisplayFormatterResolver.from_snapshot(
        {"status": "available", "revision": 1, "formatters": [formatter]}
    )
    row = search.project_card_row(col, card, resolver)
    details = search.project_card_details(col, card, resolver)
    assert row["displayText"] == "【に】感謝（する）"
    assert details["displayText"] == row["displayText"]
    assert row["displaySource"] == "reviewer_front"
    assert "formatterApplied" not in row
    assert "formatterId" not in row
    assert "primaryText" not in row


def test_exact_disabled_formatter_preserves_canonical_identity():
    formatter_service = import_addon_module("card_display_formatter_service")
    col = FakeCollection(ids=[1])
    card = col.cards[1]
    card.reviewer_html = '【<b>に</b>】<img src="感.gif">（<b>する</b>）'
    default = {
        "noteTypeId": "7", "noteTypeName": "Basic", "templateOrdinal": None,
        "templateName": None, "storedState": "enabled", "inputSource": "reviewer_front",
        "textMode": "preserve", "imageMode": "stem", "audioMode": "omit",
        "maxLines": 1, "lineSeparator": " ", "maxCharacters": 240,
        "updatedAt": "2026-07-19T00:00:00Z",
    }
    disabled = {**default, "templateOrdinal": 0, "templateName": "Card 1", "storedState": "disabled"}
    resolver = formatter_service.CardDisplayFormatterResolver.from_snapshot(
        {"status": "available", "revision": 1, "formatters": [default, disabled]}
    )
    row = search.project_card_row(col, card, resolver)
    assert row["displayText"] == "【に】（する）"
