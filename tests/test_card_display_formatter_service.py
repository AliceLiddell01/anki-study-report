from __future__ import annotations

import pytest

from conftest import import_addon_module

service = import_addon_module("card_display_formatter_service")
store_module = import_addon_module("card_display_formatter_store")


def formatter(note="123", ordinal=None, state="enabled", **updates):
    value = {
        "noteTypeId": note,
        "noteTypeName": "Japanese Vocabulary" if note == "123" else "Programming",
        "templateOrdinal": ordinal,
        "templateName": None if ordinal is None else f"Card {ordinal}",
        "storedState": state,
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


def resolver(*entries):
    return service.CardDisplayFormatterResolver.from_snapshot(
        {"status": "available", "revision": 1, "formatters": list(entries)}
    )


def test_exact_precedence_default_and_exact_disabled_opt_out():
    default = formatter(imageMode="stem")
    exact = formatter(ordinal=1, imageMode="marker")
    disabled = formatter(ordinal=2, state="disabled")
    value = resolver(default, exact, disabled)
    assert value.resolve("123", 0)["imageMode"] == "stem"
    assert value.resolve("123", 1)["imageMode"] == "marker"
    assert value.resolve("123", 2) is None
    assert value.resolve("999", 0) is None


def test_bad_store_status_fails_to_empty_resolver():
    for status in ("corrupt", "future_schema", "unavailable", "invalid"):
        assert service.CardDisplayFormatterResolver.from_snapshot(
            {"status": status, "formatters": [formatter()]}
        ).resolve("123", 0) is None


def test_strict_query_validate_and_update_requests(tmp_path):
    assert service.normalize_formatter_query_request({"schemaVersion": 1}) == {"schemaVersion": 1}
    with pytest.raises(store_module.CardDisplayFormatterValidationError):
        service.normalize_formatter_query_request({"schemaVersion": 1, "extra": True})
    validated = service.execute_formatter_validate({"schemaVersion": 1, "formatter": formatter()})
    assert validated["valid"] is True
    assert validated["formatter"]["imageMode"] == "stem"

    store = store_module.CardDisplayFormatterStore(tmp_path / "formatters.json")
    saved = service.apply_formatter_update(store, {
        "schemaVersion": 1, "action": "save", "expectedRevision": 0, "formatter": formatter(),
    })
    assert saved["store"]["revision"] == 1
    deleted = service.apply_formatter_update(store, {
        "schemaVersion": 1, "action": "delete", "expectedRevision": 1,
        "noteTypeId": "123", "templateOrdinal": None,
    })
    assert deleted["store"]["status"] == "empty"
    assert deleted["formatter"] is None


def test_no_implicit_alias_or_executable_fields():
    for key in ("regex", "javascript", "expression", "path", "url", "selector"):
        value = formatter()
        value[key] = "x"
        with pytest.raises(store_module.CardDisplayFormatterValidationError):
            service.normalize_formatter_validate_request({"schemaVersion": 1, "formatter": value})


def test_duplicate_or_invalid_snapshot_fails_closed_in_immutable_resolver():
    duplicate = service.CardDisplayFormatterResolver.from_snapshot(
        {"status": "available", "revision": 1, "formatters": [formatter(), formatter()]}
    )
    assert duplicate.resolve("123", 0) is None

    value = resolver(formatter())
    resolved = value.resolve("123", 0)
    assert resolved is not None
    resolved["imageMode"] = "marker"
    assert value.resolve("123", 0)["imageMode"] == "stem"
