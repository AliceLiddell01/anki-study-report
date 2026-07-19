from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from conftest import ROOT, import_addon_module


store_module = import_addon_module("card_display_formatter_store")


def formatter(**updates):
    value = {
        "noteTypeId": "123",
        "noteTypeName": "Japanese Vocabulary",
        "templateOrdinal": None,
        "templateName": None,
        "storedState": "enabled",
        "inputSource": "reviewer_front",
        "textMode": "preserve",
        "imageMode": "stem",
        "audioMode": "omit",
        "maxLines": 1,
        "lineSeparator": " ",
        "maxCharacters": 240,
        "updatedAt": "2026-07-19T00:00:00Z",
    }
    value.update(updates)
    return value


def test_schema_is_independent_strict_draft_2020_12():
    schema = json.loads((ROOT / "schemas" / "card-display-formatter-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert "inspection" not in json.dumps(schema).lower()


def test_missing_round_trip_revision_and_deterministic_serialization(tmp_path):
    path = tmp_path / "card_display_formatters.json"
    store = store_module.CardDisplayFormatterStore(path)
    assert store.read() == {
        "status": "empty", "revision": 0, "formatters": [], "errorCode": None, "quarantined": False,
    }
    first = store.save_formatter(formatter(), expected_revision=0)
    assert first["revision"] == 1
    assert first["formatters"] == [formatter()]
    payload = path.read_bytes()
    assert payload.endswith(b"\n")
    assert payload == store_module.serialized_document(json.loads(payload))
    second = store.save_formatter(formatter(maxLines=2), expected_revision=1)
    assert second["revision"] == 2
    assert len(second["formatters"]) == 1
    assert second["formatters"][0]["maxLines"] == 2


def test_stale_revision_and_exact_delete_are_strict(tmp_path):
    store = store_module.CardDisplayFormatterStore(tmp_path / "formatters.json")
    store.save_formatter(formatter(), expected_revision=0)
    exact = formatter(templateOrdinal=2, templateName="Production")
    store.save_formatter(exact, expected_revision=1)
    with pytest.raises(store_module.CardDisplayFormatterConflictError) as conflict:
        store.delete_formatter("123", 2, expected_revision=1)
    assert conflict.value.current_revision == 2
    result = store.delete_formatter("123", 2, expected_revision=2)
    assert [item["templateOrdinal"] for item in result["formatters"]] == [None]
    with pytest.raises(store_module.CardDisplayFormatterValidationError):
        store.delete_formatter("123", 2, expected_revision=3)


def test_corrupt_is_quarantined_and_future_schema_is_preserved(tmp_path):
    path = tmp_path / "formatters.json"
    path.write_text("{broken", encoding="utf-8")
    corrupt = store_module.CardDisplayFormatterStore(path).read()
    assert corrupt["status"] == "corrupt"
    assert corrupt["quarantined"] is True
    assert not path.exists()
    assert list(tmp_path.glob("formatters.json.corrupt-*"))

    future_bytes = b'{"schemaVersion":2,"revision":7,"formatters":[],"future":"keep"}\n'
    path.write_bytes(future_bytes)
    store = store_module.CardDisplayFormatterStore(path)
    assert store.read()["status"] == "future_schema"
    with pytest.raises(store_module.UnsupportedCardDisplayFormatterSchemaError):
        store.save_formatter(formatter(), expected_revision=0)
    assert path.read_bytes() == future_bytes


def test_document_validation_rejects_unknown_duplicate_boolean_and_incoherent_template():
    base = {"schemaVersion": 1, "revision": 0, "formatters": [formatter()]}
    cases = [
        {**base, "unknown": True},
        {**base, "formatters": [formatter(), formatter()]},
        {**base, "revision": True},
        {**base, "formatters": [formatter(templateOrdinal=0, templateName=None)]},
        {**base, "formatters": [formatter(templateOrdinal=None, templateName="Wrong")]},
        {**base, "formatters": [formatter(lineSeparator="\n")]},
        {**base, "formatters": [formatter(noteTypeId="9223372036854775808")]},
    ]
    for value in cases:
        with pytest.raises(store_module.CardDisplayFormatterValidationError):
            store_module.validate_card_display_formatter_document(value)


def test_caps_size_and_per_note_type_are_enforced(tmp_path):
    entries = [formatter(templateOrdinal=None)] + [
        formatter(templateOrdinal=index, templateName=f"Card {index}") for index in range(32)
    ]
    valid = store_module.validate_card_display_formatter_document(
        {"schemaVersion": 1, "revision": 0, "formatters": entries}
    )
    assert len(valid["formatters"]) == 33
    with pytest.raises(store_module.CardDisplayFormatterValidationError):
        store_module.validate_card_display_formatter_document(
            {"schemaVersion": 1, "revision": 0, "formatters": entries + [formatter(noteTypeId="123", templateOrdinal=0, templateName="Duplicate")]}
        )
    path = tmp_path / "too-large.json"
    path.write_bytes(b"x" * 2049)
    snapshot = store_module.CardDisplayFormatterStore(path, max_document_bytes=2048).read()
    assert snapshot["status"] == "corrupt"


def test_inaccessible_store_returns_unavailable_without_path_leak(tmp_path):
    path = tmp_path / "formatters.json"
    path.mkdir()
    snapshot = store_module.CardDisplayFormatterStore(path).read()
    assert snapshot == {
        "status": "unavailable",
        "revision": 0,
        "formatters": [],
        "errorCode": "store_unavailable",
        "quarantined": False,
    }
    assert str(path) not in repr(snapshot)


def test_timestamp_and_all_nested_unknown_fields_fail_closed():
    invalid_dates = [
        "2026-02-30T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-07-19T24:00:00Z",
    ]
    for updated_at in invalid_dates:
        with pytest.raises(store_module.CardDisplayFormatterValidationError):
            store_module.validate_card_display_formatter(formatter(updatedAt=updated_at))

    with pytest.raises(store_module.CardDisplayFormatterValidationError):
        store_module.validate_card_display_formatter({**formatter(), "callback": "run"})
