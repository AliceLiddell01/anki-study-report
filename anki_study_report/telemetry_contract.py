"""Strict content-free telemetry event contract shared with the service."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


CONTRACT_PATH = Path(__file__).resolve().with_name("telemetry_contract.json")
TELEMETRY_SCHEMA_VERSION = 1
CONSENT_SCHEMA_VERSION = 1
PRIVACY_NOTICE_VERSION = "2026-07-15-production"
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$")


class TelemetryValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid telemetry event.")
        self.field_errors = dict(field_errors)


def load_telemetry_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("telemetrySchemaVersion") != TELEMETRY_SCHEMA_VERSION:
        raise ValueError("Unsupported telemetry contract")
    if set(raw) != {"telemetrySchemaVersion", "purposes", "events", "commonDimensions", "limits"}:
        raise ValueError("Telemetry contract root keys mismatch")
    if raw.get("purposes") != ["reliabilityDiagnostics", "featureUsage"]:
        raise ValueError("Telemetry purposes mismatch")
    events = raw.get("events")
    if not isinstance(events, dict) or not events or len(events) > 32:
        raise ValueError("Invalid telemetry events contract")
    for event_code, definition in events.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", str(event_code)):
            raise ValueError("Invalid telemetry event code")
        if not isinstance(definition, dict) or set(definition) != {"purpose", "fields"}:
            raise ValueError(f"Invalid contract for {event_code}")
        if definition["purpose"] not in raw["purposes"] or not isinstance(definition["fields"], dict):
            raise ValueError(f"Invalid purpose or fields for {event_code}")
        for field, allowed in definition["fields"].items():
            if not re.fullmatch(r"[a-z][A-Za-z0-9]{0,39}", str(field)):
                raise ValueError(f"Invalid field in {event_code}")
            if not isinstance(allowed, list) or not allowed or len(allowed) > 64:
                raise ValueError(f"Invalid enum in {event_code}.{field}")
            if len(set(allowed)) != len(allowed) or any(not isinstance(item, str) or not item or len(item) > 64 for item in allowed):
                raise ValueError(f"Invalid enum values in {event_code}.{field}")
    limits = raw.get("limits")
    if not isinstance(limits, dict) or set(limits) != {
        "queueMaxEvents", "queueMaxAgeDays", "batchMaxEvents", "requestBodyMaxBytes", "eventBodyMaxBytes"
    }:
        raise ValueError("Telemetry limits mismatch")
    return deepcopy(raw)


CONTRACT = load_telemetry_contract()


def validate_semantic_event(value: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise TelemetryValidationError({"event": "Expected an object."})
    event_code = value.get("eventCode")
    definition = CONTRACT["events"].get(event_code)
    if definition is None:
        raise TelemetryValidationError({"eventCode": "Unknown event code."})
    expected = {"eventCode", "occurredAt", *definition["fields"]}
    errors = {field: "Unexpected field." for field in sorted(set(value) - expected)}
    errors.update({field: "Required field." for field in sorted(expected - set(value))})
    occurred_at = _rounded_utc(value.get("occurredAt"))
    if occurred_at is None and "occurredAt" in value:
        errors["occurredAt"] = "Expected an ISO UTC timestamp."
    for field, allowed in definition["fields"].items():
        if field in value and value[field] not in allowed:
            errors[field] = "Unknown enum value."
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > int(CONTRACT["limits"]["eventBodyMaxBytes"]):
        errors["event"] = "Event exceeds the size limit."
    if errors:
        raise TelemetryValidationError(errors)
    normalized = {"eventCode": event_code, "occurredAt": occurred_at}
    normalized.update({field: value[field] for field in definition["fields"]})
    return str(definition["purpose"]), normalized


def build_queued_event(value: Any, common_dimensions: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    purpose, event = validate_semantic_event(value)
    common = validate_common_dimensions(common_dimensions)
    payload = {
        "eventId": str(uuid4()),
        **event,
        **common,
        "telemetrySchemaVersion": TELEMETRY_SCHEMA_VERSION,
        "consentSchemaVersion": CONSENT_SCHEMA_VERSION,
        "privacyNoticeVersion": PRIVACY_NOTICE_VERSION,
    }
    return purpose, payload


def validate_common_dimensions(value: Any) -> dict[str, Any]:
    expected = {"addonVersion", "ankiVersion", "osFamily", "locale", "theme"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Trusted telemetry dimensions mismatch")
    for field in ("addonVersion", "ankiVersion"):
        if not isinstance(value[field], str) or not _VERSION_RE.fullmatch(value[field]):
            raise ValueError(f"Invalid trusted {field}")
    for field in ("osFamily", "locale", "theme"):
        if value[field] not in CONTRACT["commonDimensions"][field]:
            raise ValueError(f"Invalid trusted {field}")
    return dict(value)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rounded_utc(value: Any) -> str | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")
