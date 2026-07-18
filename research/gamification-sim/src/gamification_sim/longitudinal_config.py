from __future__ import annotations

from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest
from .longitudinal_models import (
    LongitudinalConfig,
    LongitudinalMode,
    LongitudinalPolicy,
    RetentionStep,
)
from .parameter_catalog import parameter_candidate
from .scenario_schema import format_json_path
from .strict_json import load_strict_json


CONFIG_VERSION = "review-longitudinal-v0.1"
REQUIRED_POLICY_IDS = frozenset(
    {
        "stable-default",
        "stable-high",
        "stable-low",
        "temporary-high-cycle",
        "temporary-low-cycle",
        "timely-control",
        "intentional-backlog",
        "honest-backlog-return",
        "no-fsrs-neutral",
    }
)


def default_longitudinal_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "review-longitudinal-v0.1.schema.json"


def load_longitudinal_config(path: Path) -> LongitudinalConfig:
    if path.is_symlink():
        raise ValueError("longitudinal config must not be a symlink")
    payload = load_strict_json(path)
    schema = load_strict_json(default_longitudinal_schema_path())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if errors:
        raise ValueError(
            "\n".join(
                f"{path}: {format_json_path(list(error.absolute_path))}: {error.message}"
                for error in errors
            )
        )
    date.fromisoformat(payload["start_date"])
    modes = tuple(
        LongitudinalMode(mode_id, value["horizon_days"], value["cohort_size"], value["replicas"])
        for mode_id, value in sorted(payload["modes"].items())
    )
    policies = []
    for value in payload["policies"]:
        timeline = tuple(
            RetentionStep(item["start_day"], float(item["desired_retention"]))
            for item in value["retention_timeline"]
        )
        starts = [item.start_day for item in timeline]
        if starts[0] != 0 or starts != sorted(set(starts)):
            raise ValueError(f"{value['policy_id']}: retention timeline must start at 0 and increase")
        delay_start = value["delay_start_day"]
        delay_end = value["delay_end_day"]
        if (delay_start is None) != (delay_end is None):
            raise ValueError(f"{value['policy_id']}: delay bounds must both be null or integers")
        if delay_start is not None and delay_end <= delay_start:
            raise ValueError(f"{value['policy_id']}: delay end must be after start")
        policies.append(
            LongitudinalPolicy(
                value["policy_id"],
                value["scheduler"],
                timeline,
                delay_start,
                delay_end,
                min(value["review_limit"], payload["max_reviews_per_day"]),
            )
        )
    ids = [item.policy_id for item in policies]
    if len(ids) != len(set(ids)):
        raise ValueError("longitudinal policy IDs must be unique")
    missing = sorted(REQUIRED_POLICY_IDS - set(ids))
    if missing:
        raise ValueError(f"missing required longitudinal policies: {', '.join(missing)}")
    for parameter_set_id in payload["parameter_set_ids"]:
        for part in parameter_set_id.split("+"):
            parameter_candidate(part)
    return LongitudinalConfig(
        payload["version"],
        payload["config_id"],
        payload["start_date"],
        payload["max_reviews_per_day"],
        modes,
        tuple(sorted(policies, key=lambda item: item.policy_id)),
        tuple(payload["parameter_set_ids"]),
        canonical_digest(payload),
    )
