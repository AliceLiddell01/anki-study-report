from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import re
import subprocess

from jsonschema import Draft202012Validator, FormatChecker
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "gamification-contract-v1"
CONTRACT_PATH = ROOT / "docs" / "gamification" / "study-rhythm-mvp-contract-v1.md"

SCHEMA_PATHS = {
    "settings": SCHEMA_DIR / "gamification-settings-v1.schema.json",
    "request": SCHEMA_DIR / "gamification-settings-request-v1.schema.json",
    "model": SCHEMA_DIR / "gamification-model-v1.schema.json",
    "error": SCHEMA_DIR / "gamification-error-v1.schema.json",
}

FIXTURE_SCHEMAS = {
    "settings-default-disabled.json": "settings",
    "settings-replace-enabled.json": "request",
    "settings-reset-request.json": "request",
    "model-disabled.json": "model",
    "model-enabled-in-progress.json": "model",
    "model-planned-rest-today.json": "model",
    "model-active-on-rest-day.json": "model",
    "model-completed-week.json": "model",
    "model-partial-coverage.json": "model",
    "model-unavailable-source.json": "model",
    "error-revision-conflict.json": "error",
    "error-store-unavailable.json": "error",
}

HUMAN_EXAMPLE_FIXTURES = {
    "settings-default-disabled.json",
    "settings-replace-enabled.json",
    "model-active-on-rest-day.json",
    "error-revision-conflict.json",
    "error-store-unavailable.json",
}


class DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def _schemas() -> dict[str, dict]:
    return {name: _load_json(path) for name, path in SCHEMA_PATHS.items()}


def _schema_errors(schema: dict, value) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    ]


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _settings_semantic_errors(settings: dict, *, require_sorted: bool) -> list[str]:
    errors = []
    target = settings.get("weeklyTargetDays")
    rest = settings.get("plannedRestWeekdays")
    if isinstance(target, int) and isinstance(rest, list):
        if target + len(rest) > 7:
            errors.append("weeklyTargetDays plus plannedRestWeekdays must not exceed seven")
        if require_sorted and rest != sorted(rest):
            errors.append("public and persisted plannedRestWeekdays must be ascending")
    return errors


def _request_semantic_errors(request: dict) -> list[str]:
    if request.get("operation") != "replace":
        return []
    settings = request.get("settings")
    return _settings_semantic_errors(settings, require_sorted=False) if isinstance(settings, dict) else []


def _day_count_value(activity: str):
    return {
        "active": True,
        "inactive": False,
        "unavailable": None,
        "future": None,
    }[activity]


def _model_semantic_errors(model: dict) -> list[str]:
    errors = []
    settings = model.get("settings")
    coverage = model.get("coverage")
    if not isinstance(settings, dict) or not isinstance(coverage, dict):
        return errors
    errors.extend(_settings_semantic_errors(settings, require_sorted=True))

    try:
        today_date = _parse_date(coverage["today"])
        week_start = _parse_date(coverage["weekStart"])
        week_end = _parse_date(coverage["weekEnd"])
    except (KeyError, TypeError, ValueError):
        return errors

    if week_start.isoweekday() != 1:
        errors.append("coverage weekStart must be Monday")
    if week_end != week_start + timedelta(days=6):
        errors.append("coverage weekEnd must be Sunday")
    if not week_start <= today_date <= week_end:
        errors.append("coverage today must belong to the current week")

    elapsed_dates = [week_start + timedelta(days=index) for index in range((today_date - week_start).days + 1)]
    unavailable_dates = coverage.get("unavailableElapsedDates", [])
    if unavailable_dates != sorted(unavailable_dates):
        errors.append("unavailableElapsedDates must be ascending")
    try:
        unavailable_as_dates = [_parse_date(value) for value in unavailable_dates]
    except (TypeError, ValueError):
        unavailable_as_dates = []
    if any(value not in elapsed_dates for value in unavailable_as_dates):
        errors.append("unavailableElapsedDates must contain only elapsed current-week dates")
    if coverage.get("knownElapsedDays", 0) + len(unavailable_dates) != len(elapsed_dates):
        errors.append("known and unavailable elapsed coverage must partition Monday through today")

    coverage_status = coverage.get("status")
    if coverage_status == "full":
        if unavailable_dates or coverage.get("knownElapsedDays") != len(elapsed_dates):
            errors.append("full coverage must know every elapsed day")
        if model.get("availability") != "available":
            errors.append("full coverage must expose available model status")
    elif coverage_status == "partial":
        if not unavailable_dates or not 0 < coverage.get("knownElapsedDays", 0) < len(elapsed_dates):
            errors.append("partial coverage must mix known and unavailable elapsed days")
        if model.get("availability") != "partial":
            errors.append("partial coverage must expose partial model status")
        if "current_week_partial_coverage" not in model.get("limitations", []):
            errors.append("partial coverage must report its limitation")
    elif coverage_status == "unavailable":
        if coverage.get("knownElapsedDays") != 0 or len(unavailable_dates) != len(elapsed_dates):
            errors.append("unavailable coverage must have no trustworthy elapsed day")
        if model.get("availability") != "unavailable":
            errors.append("unavailable coverage must expose unavailable model status")

    if coverage.get("availableFrom") is not None:
        try:
            if _parse_date(coverage["availableFrom"]) > today_date:
                errors.append("availableFrom must not be after today")
        except (TypeError, ValueError):
            pass

    today = model.get("today")
    week = model.get("week")
    if not settings.get("enabled"):
        if today is not None or week is not None:
            errors.append("disabled settings must suppress today and week")
    elif coverage_status == "unavailable":
        if today is not None or week is not None:
            errors.append("unavailable source must suppress today and week")
    elif not isinstance(today, dict) or not isinstance(week, dict):
        errors.append("enabled available or partial model must include today and week")

    rest_weekdays = set(settings.get("plannedRestWeekdays", []))
    if isinstance(today, dict):
        if today.get("date") != coverage.get("today"):
            errors.append("today date must match coverage today")
        if today.get("isoWeekday") != today_date.isoweekday():
            errors.append("today isoWeekday must match its date")
        expected_plan = "rest" if today_date.isoweekday() in rest_weekdays else "open"
        if today.get("plan") != expected_plan:
            errors.append("today plan must derive from plannedRestWeekdays")
        if today.get("activity") in {"active", "inactive", "unavailable"}:
            if today.get("countsTowardTarget") is not _day_count_value(today["activity"]):
                errors.append("today count must derive only from activity availability")

    if isinstance(week, dict):
        if week.get("weekStart") != coverage.get("weekStart") or week.get("weekEnd") != coverage.get("weekEnd"):
            errors.append("week bounds must match coverage")
        days = week.get("days", [])
        expected_dates = [week_start + timedelta(days=index) for index in range(7)]
        actual_dates = []
        for index, item in enumerate(days):
            try:
                item_date = _parse_date(item["date"])
            except (KeyError, TypeError, ValueError):
                continue
            actual_dates.append(item_date)
            expected_relation = "past" if item_date < today_date else "today" if item_date == today_date else "future"
            expected_plan = "rest" if item_date.isoweekday() in rest_weekdays else "open"
            if item.get("isoWeekday") != index + 1 or item_date.isoweekday() != index + 1:
                errors.append("week days must be ISO weekday ordered")
            if item.get("relation") != expected_relation:
                errors.append("day relation must derive from coverage today")
            if item.get("plan") != expected_plan:
                errors.append("day plan must derive from plannedRestWeekdays")
            activity = item.get("activity")
            if expected_relation == "future" and activity != "future":
                errors.append("future day must use future activity")
            if expected_relation != "future" and activity == "future":
                errors.append("elapsed day must not use future activity")
            if activity in {"active", "inactive", "unavailable", "future"}:
                if item.get("countsTowardTarget") is not _day_count_value(activity):
                    errors.append("day count must derive only from activity availability")
        if actual_dates != expected_dates:
            errors.append("week days must be exactly Monday through Sunday")

        progress = week.get("progress", {})
        completed_days = sum(item.get("countsTowardTarget") is True for item in days)
        target_days = settings.get("weeklyTargetDays")
        remaining_days = max(0, target_days - completed_days)
        lower_bound = any(item.get("activity") == "unavailable" for item in days if item.get("relation") != "future")
        if progress.get("completedDays") != completed_days:
            errors.append("completedDays must count every known active day, including rest")
        if progress.get("targetDays") != target_days:
            errors.append("targetDays must match current settings")
        if progress.get("remainingDays") != remaining_days:
            errors.append("remainingDays must be max(target minus completed, zero)")
        if progress.get("isLowerBound") is not lower_bound:
            errors.append("isLowerBound must reflect unavailable elapsed days")

        expected_open_dates = [
            item["date"]
            for item in days
            if item.get("relation") in {"today", "future"}
            and item.get("plan") == "open"
            and item.get("countsTowardTarget") is not True
        ]
        if week.get("remainingOpenDays") != expected_open_dates:
            errors.append("remainingOpenDays must be ordered current/future non-rest opportunities")
        if completed_days >= target_days:
            expected_completion = "complete"
        elif coverage_status != "full":
            expected_completion = "unknown"
        elif len(expected_open_dates) >= remaining_days:
            expected_completion = "possible"
        else:
            expected_completion = "not_possible_without_plan_change"
        if week.get("completionState") != expected_completion:
            errors.append("completionState must follow the frozen decision order")

    history = model.get("historySummary", {}).get("completedWeeks", [])
    history_starts = []
    for item in history:
        try:
            item_start = _parse_date(item["weekStart"])
            item_end = _parse_date(item["weekEnd"])
        except (KeyError, TypeError, ValueError):
            continue
        history_starts.append(item_start)
        if item_start.isoweekday() != 1 or item_end != item_start + timedelta(days=6):
            errors.append("history weeks must use Monday through Sunday bounds")
        if item_end >= week_start:
            errors.append("historySummary may include only completed weeks")
    if history_starts != sorted(history_starts, reverse=True):
        errors.append("historySummary must be newest first")

    streak = model.get("existingStreakContext", {})
    if streak.get("available") and streak.get("bestStreak", 0) < streak.get("currentStreak", 0):
        errors.append("bestStreak must not be smaller than currentStreak")
    if not streak.get("available") and "profile_missing_for_streak_context" not in model.get("limitations", []):
        errors.append("unavailable streak context must report its limitation")
    if settings.get("source") == "recovered_default" and "settings_corrupt_recovered" not in model.get("limitations", []):
        errors.append("recovered defaults must report corrupt settings recovery")
    return errors


def _semantic_errors(schema_name: str, value) -> list[str]:
    if not isinstance(value, dict):
        return []
    if schema_name == "settings":
        return _settings_semantic_errors(value, require_sorted=True)
    if schema_name == "request":
        return _request_semantic_errors(value)
    if schema_name == "model":
        return _model_semantic_errors(value)
    return []


def _contract_errors(schema_name: str, value) -> list[str]:
    schema_errors = _schema_errors(_schemas()[schema_name], value)
    return schema_errors + _semantic_errors(schema_name, value)


def _walk_schema(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_schema(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_schema(nested)


def _git_lines(*arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def test_machine_schemas_are_duplicate_safe_strict_local_and_draft_2020_12():
    schemas = _schemas()
    assert len({schema["$id"] for schema in schemas.values()}) == len(schemas)
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://anki-study-report.local/schemas/{SCHEMA_PATHS[name].name}"
        for node in _walk_schema(schema):
            reference = node.get("$ref")
            if reference is not None:
                assert reference.startswith("#/"), reference
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, node
                assert "required" in node or node.get("minProperties") == 1
            if node.get("type") == "array":
                assert "maxItems" in node, node


def test_valid_fixtures_are_complete_and_pass_schema_plus_semantics():
    actual_names = {path.name for path in FIXTURE_DIR.glob("*.json")}
    assert actual_names == set(FIXTURE_SCHEMAS)
    for fixture_name, schema_name in FIXTURE_SCHEMAS.items():
        value = _load_json(FIXTURE_DIR / fixture_name)
        assert _contract_errors(schema_name, value) == [], fixture_name


def _invalid_contract_cases():
    default_settings = _load_json(FIXTURE_DIR / "settings-default-disabled.json")
    enabled_model = _load_json(FIXTURE_DIR / "model-enabled-in-progress.json")
    conflict = _load_json(FIXTURE_DIR / "error-revision-conflict.json")

    unknown_key = deepcopy(default_settings)
    unknown_key["unexpected"] = True

    wrong_schema_version = deepcopy(default_settings)
    wrong_schema_version["schemaVersion"] = 2

    unsafe_revision = deepcopy(default_settings)
    unsafe_revision["revision"] = 9007199254740992

    duplicate_weekdays = deepcopy(default_settings)
    duplicate_weekdays["plannedRestWeekdays"] = [6, 6]

    invalid_weekday = deepcopy(default_settings)
    invalid_weekday["plannedRestWeekdays"] = [0]

    impossible_plan = deepcopy(default_settings)
    impossible_plan["weeklyTargetDays"] = 4
    impossible_plan["plannedRestWeekdays"] = [1, 5, 6, 7]

    invalid_date = deepcopy(enabled_model)
    invalid_date["today"]["date"] = "2026-02-30"

    invalid_timestamp = deepcopy(enabled_model)
    invalid_timestamp["generatedAt"] = "2026-07-29T12:00:00+00:00"

    wrong_day_order = deepcopy(enabled_model)
    wrong_day_order["week"]["days"][0], wrong_day_order["week"]["days"][1] = (
        wrong_day_order["week"]["days"][1],
        wrong_day_order["week"]["days"][0],
    )

    wrong_week_length = deepcopy(enabled_model)
    wrong_week_length["week"]["days"].pop()

    invalid_completion_state = deepcopy(enabled_model)
    invalid_completion_state["week"]["completionState"] = "almost"

    conflict_without_current_revision = deepcopy(conflict)
    conflict_without_current_revision.pop("currentRevision")

    return [
        ("unknown-key", "settings", unknown_key),
        ("wrong-schema-version", "settings", wrong_schema_version),
        ("unsafe-revision", "settings", unsafe_revision),
        ("duplicate-weekdays", "settings", duplicate_weekdays),
        ("invalid-weekday", "settings", invalid_weekday),
        ("impossible-target-rest-plan", "settings", impossible_plan),
        ("invalid-date", "model", invalid_date),
        ("invalid-timestamp", "model", invalid_timestamp),
        ("wrong-day-order", "model", wrong_day_order),
        ("wrong-week-length", "model", wrong_week_length),
        ("invalid-completion-state", "model", invalid_completion_state),
        ("conflict-without-current-revision", "error", conflict_without_current_revision),
    ]


@pytest.mark.parametrize(
    ("case_name", "schema_name", "value"),
    _invalid_contract_cases(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_required_invalid_cases_are_rejected(case_name: str, schema_name: str, value):
    assert _contract_errors(schema_name, value), case_name


def test_human_json_examples_equal_named_fixtures_and_validate():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    matches = re.findall(
        r"<!-- contract-example:([a-z0-9-]+\.json) -->\s*```json\s*(.*?)\s*```",
        text,
        flags=re.DOTALL,
    )
    assert {name for name, _payload in matches} == HUMAN_EXAMPLE_FIXTURES
    for fixture_name, payload in matches:
        example = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
        fixture = _load_json(FIXTURE_DIR / fixture_name)
        assert example == fixture
        assert _contract_errors(FIXTURE_SCHEMAS[fixture_name], example) == []

    for exact_mapping in (
        "| JSON | Python | TypeScript |",
        "| `null` | `None` | `null` |",
        "| `boolean` | `bool` | `boolean` |",
        "| safe integer | `int` | `number` |",
        "| string | `str` | `string` |",
        "| array | `list` | `Array` |",
        "| object | `dict` | object/interface |",
    ):
        assert exact_mapping in text


def test_machine_contract_has_no_g6_to_g8_fields_or_labels():
    forbidden = re.compile(
        r"^(?:xp|experiencepoints?|levels?|skillmastery|achievements?|quests?|"
        r"currenc(?:y|ies)|rewards?|leaderboards?)$",
        flags=re.IGNORECASE,
    )
    values = []
    for schema in _schemas().values():
        for node in _walk_schema(schema):
            values.extend(node.keys())
            for key in ("const", "enum"):
                item = node.get(key)
                values.extend(item if isinstance(item, list) else [item])
    for fixture_path in FIXTURE_DIR.glob("*.json"):
        for node in _walk_schema(_load_json(fixture_path)):
            values.extend(node.keys())
    assert not [value for value in values if isinstance(value, str) and forbidden.fullmatch(value)]


def test_candidate_diff_has_no_live_api_route_frontend_package_or_runtime_change():
    changed = set(_git_lines("diff", "--name-only", "origin/gamification", "--"))
    changed.update(_git_lines("ls-files", "--others", "--exclude-standard"))
    forbidden_prefixes = (
        "anki_study_report/",
        "web-dashboard/src/",
        ".github/",
        "docker/",
    )
    assert not sorted(path for path in changed if path.startswith(forbidden_prefixes))
    assert "scripts/package_addon.py" not in changed
    assert "requirements.txt" not in changed
    assert "requirements-dev.txt" not in changed
    assert "docs/dashboard-api.md" not in changed
