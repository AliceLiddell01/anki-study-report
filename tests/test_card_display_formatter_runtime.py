from __future__ import annotations

from conftest import import_addon_module

runtime = import_addon_module("card_display_formatter_runtime")
store_module = import_addon_module("card_display_formatter_store")


def formatter():
    return {
        "noteTypeId": "123", "noteTypeName": "Japanese", "templateOrdinal": None,
        "templateName": None, "storedState": "enabled", "inputSource": "reviewer_front",
        "textMode": "preserve", "imageMode": "stem", "audioMode": "omit",
        "maxLines": 1, "lineSeparator": " ", "maxCharacters": 240,
        "updatedAt": "2026-07-19T00:00:00Z",
    }


def test_runtime_query_validate_update_and_conflict(tmp_path):
    store = store_module.CardDisplayFormatterStore(tmp_path / "formatters.json")
    query = runtime.run_card_display_formatter_query_sync({"schemaVersion": 1}, store)
    assert query["ok"] is True and query["response"]["status"] == "empty"
    validate = runtime.run_card_display_formatter_validate_sync(
        {"schemaVersion": 1, "formatter": formatter()}, store
    )
    assert validate["ok"] is True and validate["response"]["valid"] is True
    saved = runtime.run_card_display_formatter_update_sync({
        "schemaVersion": 1, "action": "save", "expectedRevision": 0, "formatter": formatter(),
    }, store)
    assert saved["ok"] is True
    conflict = runtime.run_card_display_formatter_update_sync({
        "schemaVersion": 1, "action": "save", "expectedRevision": 0, "formatter": formatter(),
    }, store)
    assert conflict == {
        "ok": False, "error": "card_display_formatter_revision_conflict", "currentRevision": 1,
    }


def test_runtime_rejects_unknown_request_without_persistence(tmp_path):
    path = tmp_path / "formatters.json"
    result = runtime.run_card_display_formatter_validate_sync(
        {"schemaVersion": 1, "formatter": formatter(), "extra": True},
        store_module.CardDisplayFormatterStore(path),
    )
    assert result["ok"] is False
    assert result["error"] == "invalid_card_display_formatter_request"
    assert not path.exists()


def test_validate_has_no_persistence_and_errors_are_bounded(tmp_path):
    path = tmp_path / "formatters.json"
    store = store_module.CardDisplayFormatterStore(path)
    result = runtime.run_card_display_formatter_validate_sync(
        {"schemaVersion": 1, "formatter": formatter()}, store
    )
    assert result["ok"] is True
    assert result["response"]["formatter"] == formatter()
    assert not path.exists()

    invalid = formatter()
    invalid["regex"] = ".*"
    result = runtime.run_card_display_formatter_validate_sync(
        {"schemaVersion": 1, "formatter": invalid}, store
    )
    assert result["ok"] is False
    assert result["error"] == "invalid_card_display_formatter_request"
    assert "formatter.regex" in result["fieldErrors"]
    assert str(path) not in repr(result)
