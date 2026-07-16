from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .input_parsing import day_from_dict, episode_from_dict
from .manifest import SCENARIO_SCHEMA_VERSION
from .parameters import CURRENT_PARAMETERS
from .scenario_models import (
    AssertionScope,
    AssertionType,
    ScenarioAssertion,
    ScenarioCategory,
    ScenarioDay,
    ScenarioDefinition,
    ScenarioMetric,
    ScenarioSession,
)
from .scenario_schema import load_validator, validate_instance
from .strict_json import load_strict_json
from .validation import TOLERANCE, require_non_negative_int


class ScenarioDomainError(ValueError):
    pass


def _expand_session(day_value: str, session: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    items = [dict(item) for item in session.get("episodes", [])]
    for group in session.get("repeat_episodes", []):
        count = require_non_negative_int("repeat_episodes count", group["count"])
        prefix = group["prefix"]
        template = dict(group["template"])
        for index in range(count):
            item = dict(template)
            item.setdefault("source_event_key", f"{prefix}{index}")
            item.setdefault("card_lineage", f"{prefix}card-{index}")
            item.setdefault("anki_day", day_value)
            item.setdefault("outcome", "good")
            items.append(item)
    return tuple(items)


def _parse_assertion(data: dict[str, Any]) -> ScenarioAssertion:
    return ScenarioAssertion(
        type=AssertionType(data["type"]),
        scope=AssertionScope(data["scope"]),
        metric=ScenarioMetric(data["metric"]),
        expected=float(data["expected"]),
        tolerance=float(data.get("tolerance", TOLERANCE)),
        anki_day=data.get("anki_day"),
        control_scenario_id=data.get("control_scenario_id"),
    )


def _parse_definition(data: dict[str, Any]) -> ScenarioDefinition:
    category = ScenarioCategory(data["category"])
    days: list[ScenarioDay] = []
    for raw_day in data["days"]:
        day_value = raw_day["anki_day"]
        sessions: list[ScenarioSession] = []
        all_episodes: list[dict[str, Any]] = []
        session_ids: list[str] = []
        for raw_session in raw_day["sessions"]:
            expanded = _expand_session(day_value, raw_session)
            session_id = raw_session["session_id"]
            sessions.append(
                ScenarioSession(
                    session_id=session_id,
                    episodes=tuple(episode_from_dict(item) for item in expanded),
                )
            )
            session_ids.append(session_id)
            all_episodes.extend(expanded)
        normalized = {
            "anki_day": day_value,
            "episodes": all_episodes,
            "support_events": raw_day.get("support_events", []),
            "supplemental_events": raw_day.get("supplemental_events", []),
            "undone_source_event_keys": raw_day.get("undone_source_event_keys", []),
            "workload": raw_day.get("workload", {}),
            "session_ids": session_ids,
        }
        days.append(
            ScenarioDay(
                anki_day=day_value,
                sessions=tuple(sessions),
                day_input=day_from_dict(normalized),
            )
        )
    return ScenarioDefinition(
        scenario_version=data["scenario_version"],
        scenario_id=data["scenario_id"],
        title=data["title"],
        category=category,
        rule_version=data["rule_version"],
        description=data.get("description", data["title"]),
        tags=tuple(data.get("tags", [])),
        days=tuple(days),
        assertions=tuple(_parse_assertion(item) for item in data["assertions"]),
        control_scenario_id=data.get("control_scenario_id"),
        comparison_basis=data.get("comparison_basis"),
        comparison_note=data.get("comparison_note"),
    )


def validate_definition(definition: ScenarioDefinition) -> None:
    if definition.scenario_version != SCENARIO_SCHEMA_VERSION:
        raise ScenarioDomainError(
            f"{definition.scenario_id}: unsupported scenario_version {definition.scenario_version}"
        )
    if definition.rule_version != CURRENT_PARAMETERS.rule_version:
        raise ScenarioDomainError(
            f"{definition.scenario_id}: rule_version {definition.rule_version} does not match {CURRENT_PARAMETERS.rule_version}"
        )
    if definition.category is ScenarioCategory.ABUSE and not definition.control_scenario_id:
        raise ScenarioDomainError(f"{definition.scenario_id}: abuse scenario requires control_scenario_id")
    if definition.control_scenario_id == definition.scenario_id:
        raise ScenarioDomainError(f"{definition.scenario_id}: control reference cannot point to itself")
    if definition.comparison_basis == "documented-difference" and not definition.comparison_note:
        raise ScenarioDomainError(
            f"{definition.scenario_id}: documented-difference requires comparison_note"
        )

    day_values = [item.anki_day for item in definition.days]
    if len(day_values) != len(set(day_values)):
        raise ScenarioDomainError(f"{definition.scenario_id}: duplicate anki_day")
    parsed_days = [date.fromisoformat(value) for value in day_values]
    if parsed_days != sorted(parsed_days) or any(
        left >= right for left, right in zip(parsed_days, parsed_days[1:])
    ):
        raise ScenarioDomainError(f"{definition.scenario_id}: days must be strictly increasing")

    allow_duplicate_sources = definition.category in {
        ScenarioCategory.ABUSE,
        ScenarioCategory.REGRESSION,
    }
    for day in definition.days:
        session_ids = [item.session_id for item in day.sessions]
        if len(session_ids) != len(set(session_ids)):
            raise ScenarioDomainError(
                f"{definition.scenario_id}/{day.anki_day}: duplicate session_id"
            )
        sources: list[str] = []
        for session in day.sessions:
            for episode in session.episodes:
                if episode.anki_day != day.anki_day:
                    raise ScenarioDomainError(
                        f"{definition.scenario_id}/{day.anki_day}: episode anki_day mismatch"
                    )
                sources.append(episode.source_event_key)
        sources.extend(item.source_event_key for item in day.day_input.support_events)
        sources.extend(item.source_event_key for item in day.day_input.supplemental_events)
        if not allow_duplicate_sources and len(sources) != len(set(sources)):
            raise ScenarioDomainError(
                f"{definition.scenario_id}/{day.anki_day}: duplicate source_event_key in ordinary history"
            )

    known_days = set(day_values)
    for assertion in definition.assertions:
        if assertion.scope is AssertionScope.DAY:
            if assertion.anki_day not in known_days:
                raise ScenarioDomainError(
                    f"{definition.scenario_id}: day assertion requires an existing anki_day"
                )
        elif assertion.anki_day is not None:
            raise ScenarioDomainError(
                f"{definition.scenario_id}: anki_day is only valid for day assertions"
            )
        if assertion.type.requires_control:
            if assertion.scope is not AssertionScope.COMPARISON:
                raise ScenarioDomainError(
                    f"{definition.scenario_id}: control assertion must use comparison scope"
                )
            control_id = assertion.control_scenario_id or definition.control_scenario_id
            if not control_id:
                raise ScenarioDomainError(
                    f"{definition.scenario_id}: control assertion requires a control reference"
                )
            if control_id == definition.scenario_id:
                raise ScenarioDomainError(
                    f"{definition.scenario_id}: assertion control cannot point to itself"
                )
        elif assertion.scope is AssertionScope.COMPARISON:
            raise ScenarioDomainError(
                f"{definition.scenario_id}: comparison scope requires a control assertion type"
            )


def load_scenario(path: Path, *, validator=None) -> ScenarioDefinition:
    instance = load_strict_json(path)
    active_validator = validator or load_validator()
    validate_instance(instance, source=path, validator=active_validator)
    definition = _parse_definition(instance)
    validate_definition(definition)
    return definition


def discover_scenario_paths(root: Path) -> tuple[Path, ...]:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ScenarioDomainError(f"{root}: scenario root must be a directory")
    paths: list[Path] = []
    for path in root.rglob("*.json"):
        if path.is_symlink():
            raise ScenarioDomainError(f"{path}: symlink scenario files are not allowed")
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise ScenarioDomainError(f"{path}: scenario path escapes corpus root") from exc
        paths.append(resolved)
    return tuple(sorted(paths, key=lambda item: item.as_posix()))


def load_corpus(root: Path) -> tuple[ScenarioDefinition, ...]:
    validator = load_validator()
    definitions = tuple(load_scenario(path, validator=validator) for path in discover_scenario_paths(root))
    ids = [item.scenario_id for item in definitions]
    if len(ids) != len(set(ids)):
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        raise ScenarioDomainError(f"duplicate scenario_id: {', '.join(duplicates)}")
    by_id = {item.scenario_id: item for item in definitions}
    for item in definitions:
        if item.control_scenario_id:
            control = by_id.get(item.control_scenario_id)
            if control is None:
                raise ScenarioDomainError(
                    f"{item.scenario_id}: control does not exist: {item.control_scenario_id}"
                )
            if control.category is not ScenarioCategory.CONTROL:
                raise ScenarioDomainError(
                    f"{item.scenario_id}: referenced control has category {control.category.value}"
                )
        for assertion in item.assertions:
            control_id = assertion.control_scenario_id
            if control_id:
                control = by_id.get(control_id)
                if control is None:
                    raise ScenarioDomainError(
                        f"{item.scenario_id}: assertion control does not exist: {control_id}"
                    )
                if control.category is not ScenarioCategory.CONTROL:
                    raise ScenarioDomainError(
                        f"{item.scenario_id}: assertion control has wrong category"
                    )

    def visit(scenario_id: str, active: set[str], complete: set[str]) -> None:
        if scenario_id in complete:
            return
        if scenario_id in active:
            raise ScenarioDomainError(f"cyclic control reference involving {scenario_id}")
        active.add(scenario_id)
        ref = by_id[scenario_id].control_scenario_id
        if ref:
            visit(ref, active, complete)
        active.remove(scenario_id)
        complete.add(scenario_id)

    complete: set[str] = set()
    for scenario_id in sorted(by_id):
        visit(scenario_id, set(), complete)
    return definitions
