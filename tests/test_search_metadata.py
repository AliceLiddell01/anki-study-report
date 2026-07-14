from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import import_addon_module


metadata = import_addon_module("search_metadata")


class FakeDeckManager:
    def all(self):
        return [
            {"id": 20, "name": "Filtered", "dyn": 1},
            {"id": 10, "name": "Languages::Japanese", "dyn": 0},
            {"id": 10, "name": "duplicate", "dyn": 0},
            {"id": 0, "name": "invalid", "dyn": 0},
        ]


class FakeModelManager:
    def all_names_and_ids(self):
        return [
            SimpleNamespace(id=7, name="Basic"),
            SimpleNamespace(id=8, name="Cloze"),
            SimpleNamespace(id=7, name="duplicate"),
        ]


class FakeCollection:
    decks = FakeDeckManager()
    models = FakeModelManager()


def test_metadata_request_is_strict_and_keeps_request_id():
    assert metadata.normalize_search_request({"kind": "metadata", "requestId": "metadata-1"}) == {
        "kind": "metadata",
        "requestId": "metadata-1",
    }
    with pytest.raises(metadata.SearchValidationError) as error:
        metadata.normalize_search_request({"kind": "metadata", "query": "deck:private"})
    assert "query" in error.value.field_errors


def test_metadata_returns_sorted_bounded_all_collection_catalogs():
    result = metadata.execute_search_request(
        FakeCollection(),
        {"kind": "metadata", "requestId": "metadata-2"},
    )
    assert result == {
        "schemaVersion": 1,
        "kind": "metadata",
        "decks": [
            {"deckId": "20", "deckName": "Filtered", "filtered": True},
            {"deckId": "10", "deckName": "Languages::Japanese", "filtered": False},
        ],
        "noteTypes": [
            {"noteTypeId": "7", "noteTypeName": "Basic"},
            {"noteTypeId": "8", "noteTypeName": "Cloze"},
        ],
        "decksTruncated": False,
        "noteTypesTruncated": False,
        "requestId": "metadata-2",
    }


def test_normal_query_requests_delegate_raw_contract_without_double_normalization(monkeypatch):
    raw = {
        "mode": "cards",
        "query": "",
        "filters": [
            {"type": "deck", "deckId": "10"},
            {"type": "note_type", "noteTypeId": "7"},
        ],
        "sort": {"key": "entity_id", "direction": "asc"},
        "page": 1,
        "pageSize": 25,
    }
    monkeypatch.setattr(metadata, "execute_search_query", lambda col, request: {"delegated": request})
    assert metadata.execute_search_request(object(), raw) == {"delegated": raw}
