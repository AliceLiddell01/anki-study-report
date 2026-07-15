from __future__ import annotations

import json

import pytest

from conftest import fresh_import_addon_module


@pytest.fixture
def contract_module():
    return fresh_import_addon_module("telemetry_contract")


def test_contract_has_exact_version_purposes_and_bounded_events(contract_module):
    contract = contract_module.load_telemetry_contract()

    assert contract["telemetrySchemaVersion"] == 1
    assert contract["purposes"] == ["reliabilityDiagnostics", "featureUsage"]
    assert set(contract["events"]) == {
        "addon.started", "dashboard.opened", "page.opened", "search.completed",
        "entity_action.completed", "api_operation.failed", "dashboard_startup.completed",
    }
    assert contract["limits"] == {
        "queueMaxEvents": 5000,
        "queueMaxAgeDays": 7,
        "batchMaxEvents": 50,
        "requestBodyMaxBytes": 65536,
        "eventBodyMaxBytes": 4096,
    }


def test_semantic_validation_rejects_unknown_spoofed_and_prohibited_fields(contract_module):
    base = {"eventCode": "page.opened", "pageCode": "search", "occurredAt": "2026-07-15T12:34:56Z"}
    purpose, normalized = contract_module.validate_semantic_event(base)
    assert purpose == "featureUsage"
    assert normalized["occurredAt"] == "2026-07-15T12:34:00Z"

    for field, value in [
        ("addonVersion", "9.9.9"),
        ("writeToken", "secret"),
        ("query", "deck:private"),
        ("profileName", "Alice"),
        ("stackTrace", "private content"),
        ("cardId", "123"),
    ]:
        with pytest.raises(contract_module.TelemetryValidationError) as error:
            contract_module.validate_semantic_event({**base, field: value})
        assert error.value.field_errors[field] == "Unexpected field."


def test_every_enum_is_exact_and_common_dimensions_are_backend_only(contract_module):
    with pytest.raises(contract_module.TelemetryValidationError) as error:
        contract_module.validate_semantic_event({
            "eventCode": "search.completed",
            "resultCode": "SUCCESS",
            "durationBucket": "123_ms",
            "resultCountBucket": "11",
            "occurredAt": "2026-07-15T12:00:00Z",
        })
    assert set(error.value.field_errors) == {"resultCode", "durationBucket", "resultCountBucket"}

    common = {
        "addonVersion": "1.1.0",
        "ankiVersion": "26.05",
        "osFamily": "windows",
        "locale": "unknown",
        "theme": "unknown",
    }
    purpose, queued = contract_module.build_queued_event(
        {"eventCode": "dashboard.opened", "occurredAt": "2026-07-15T12:00:00Z"},
        common,
    )
    assert purpose == "featureUsage"
    assert queued["telemetrySchemaVersion"] == 1
    assert queued["addonVersion"] == "1.1.0"
    assert len(queued["eventId"]) == 36
    assert "writeToken" not in json.dumps(queued)

