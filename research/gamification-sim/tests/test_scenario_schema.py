from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from gamification_sim.scenario_schema import ScenarioSchemaError, default_schema_path, load_validator, validate_instance
from gamification_sim.strict_json import load_strict_json


def valid_payload():
    return {
        "scenario_version": "review-scenario-v0.1",
        "scenario_id": "schema-smoke",
        "title": "Schema smoke",
        "category": "ordinary",
        "rule_version": "review-v0.1",
        "days": [{"anki_day": "2026-07-16", "sessions": [{"session_id": "main", "episodes": []}]}],
        "assertions": [],
    }


def assert_invalid(payload, text=""):
    with pytest.raises(ScenarioSchemaError, match=text or None):
        validate_instance(payload, source=default_schema_path(), validator=load_validator())


def test_schema_passes_check_schema():
    schema = load_strict_json(default_schema_path())
    Draft202012Validator.check_schema(schema)


def test_missing_required_field():
    payload = valid_payload(); del payload["days"]
    assert_invalid(payload, "days")


def test_unknown_field():
    payload = valid_payload(); payload["code"] = "print(1)"
    assert_invalid(payload, "Additional properties")


@pytest.mark.parametrize(("field", "value"), [("category", "weird"), ("scenario_id", "Bad ID"), ("rule_version", "review-v9")])
def test_invalid_root_values(field, value):
    payload = valid_payload(); payload[field] = value
    assert_invalid(payload)


def test_invalid_integer_and_boolean():
    payload = valid_payload()
    payload["days"][0]["workload"] = {"natural_due_at_start": "1", "snapshot_confident": 1}
    assert_invalid(payload)


def test_invalid_assertion_operator():
    payload = valid_payload()
    payload["assertions"] = [{"type": "eval", "scope": "scenario", "metric": "total_review_units", "expected": 0}]
    assert_invalid(payload)


def test_schema_error_order_is_deterministic():
    payload = valid_payload(); payload["category"] = "x"; payload["scenario_id"] = "X X"
    validator = load_validator()
    errors = []
    for _ in range(2):
        try:
            validate_instance(payload, source=default_schema_path(), validator=validator)
        except ScenarioSchemaError as exc:
            errors.append(str(exc))
    assert errors[0] == errors[1]
