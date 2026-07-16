from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .strict_json import load_strict_json


class ScenarioSchemaError(ValueError):
    pass


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "review-scenario-v0.1.schema.json"


def format_json_path(parts: list[Any]) -> str:
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def load_validator(schema_path: Path | None = None) -> Draft202012Validator:
    path = schema_path or default_schema_path()
    schema = load_strict_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_instance(instance: Any, *, source: Path, validator: Draft202012Validator) -> None:
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if not errors:
        return
    lines = [
        f"{source}: {format_json_path(list(error.absolute_path))}: {error.message}"
        for error in errors
    ]
    raise ScenarioSchemaError("\n".join(lines))
