from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from .breakdown import to_dict
from .canonical_json import canonical_digest, canonical_dumps
from .day_aggregation import aggregate_day
from .episode_reward import evaluate_episode
from .input_parsing import day_from_dict, episode_from_dict
from .models import ConfidenceLevel, MemoryContext, Outcome, ReviewDayInput, ReviewEpisodeInput
from .parameter_catalog import candidate_payload, compose_parameter_candidates, parameter_candidate
from .scenario_loader import load_corpus
from .strict_json import loads_strict, load_strict_json
from .validation import close, dataclass_to_dict


ORACLE_CONTRACT_VERSION = "rust-oracle-jsonl-v0.1"
TOLERANCE = 1e-9


def _case(
    case_id: str,
    kind: str,
    input_value: Any,
    params,
    *,
    source: str,
    expected_error: bool = False,
) -> dict[str, Any]:
    normalized = dataclass_to_dict(input_value) if not isinstance(input_value, dict) else input_value
    expected = None
    if not expected_error:
        result = (
            evaluate_episode(input_value, params.parameters)
            if kind == "episode"
            else aggregate_day(input_value, params.parameters)
        )
        expected = to_dict(result)
    return {
        "case_id": case_id,
        "kind": kind,
        "input": normalized,
        "parameters": candidate_payload(params)["parameter_snapshot"],
        "expected": expected,
        "expected_error": expected_error,
        "source": source,
    }


def build_differential_cases(package_root: Path, parameter_set_id: str) -> list[dict[str, Any]]:
    parts = tuple(parameter_candidate(item) for item in parameter_set_id.split("+"))
    selected = parts[0] if len(parts) == 1 else compose_parameter_candidates(parts)
    cases: list[dict[str, Any]] = []
    golden = load_strict_json(package_root / "fixtures" / "golden_cases.json")
    for item in golden["cases"]:
        input_value = episode_from_dict(item["input"]) if item["kind"] == "episode" else day_from_dict(item["input"])
        cases.append(_case(f"golden:{item['id']}", item["kind"], input_value, selected, source="golden"))
    for definition in load_corpus(package_root / "scenarios"):
        for day in definition.days:
            cases.append(
                _case(
                    f"scenario:{definition.scenario_id}:{day.anki_day}",
                    "day",
                    day.day_input,
                    selected,
                    source="scenario",
                )
            )
    epsilon = 1e-6
    thresholds = sorted(
        set(point for point, _ in selected.parameters.challenge_anchors)
        | {0.10, 0.95}
    )
    for threshold in thresholds:
        for label, value in (
            ("minus", max(0.0, threshold - epsilon)),
            ("exact", threshold),
            ("plus", min(1.0, threshold + epsilon)),
        ):
            episode = ReviewEpisodeInput(
                source_event_key=f"threshold-{threshold:g}-{label}",
                card_lineage=f"threshold-{threshold:g}-{label}",
                anki_day="2026-01-01",
                outcome=Outcome.GOOD,
                memory=MemoryContext(
                    retrievability_actual=value,
                    retrievability_natural_due=value,
                    confidence=ConfidenceLevel.HIGH,
                ),
            )
            cases.append(_case(f"threshold:challenge:{threshold:g}:{label}", "episode", episode, selected, source="threshold"))
    for threshold in (5, 10, 25, 50, 100, 300):
        for delta in (-1, 0, 1):
            count = max(0, threshold + delta)
            day = ReviewDayInput(
                "2026-01-01",
                tuple(
                    ReviewEpisodeInput(f"volume-{count}-{index}", f"card-{index}", "2026-01-01", Outcome.GOOD)
                    for index in range(count)
                ),
            )
            cases.append(_case(f"threshold:volume:{count}", "day", day, selected, source="threshold"))
    survivor_ids = (
        "R-CURRENT",
        "R-CURRENT+V-CURRENT",
        "R-CURRENT+V-CURRENT+C-CURRENT",
        "R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT",
        "R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT+P-CURRENT",
    )
    edge_episode = ReviewEpisodeInput("survivor", "survivor", "2026-01-01", Outcome.GOOD)
    for survivor_id in survivor_ids:
        survivor_parts = tuple(parameter_candidate(item) for item in survivor_id.split("+"))
        survivor = survivor_parts[0] if len(survivor_parts) == 1 else compose_parameter_candidates(survivor_parts)
        cases.append(_case(f"survivor:{survivor_id}", "episode", edge_episode, survivor, source="survivor"))
    for index, episode in enumerate(
        (
            ReviewEpisodeInput("edge-again", "edge-again", "2026-01-01", Outcome.AGAIN),
            ReviewEpisodeInput("edge-zero-bonus", "edge-zero-bonus", "2026-01-01", Outcome.GOOD, bonus_eligibility=0.0),
            ReviewEpisodeInput("edge-cap", "edge-cap", "2026-01-01", Outcome.GOOD, memory=MemoryContext(0.1, 0.1, 1.0, 10.0, ConfidenceLevel.HIGH)),
        )
    ):
        cases.append(_case(f"property-edge:{index}", "episode", episode, selected, source="property-edge"))
    invalid = dataclass_to_dict(edge_episode)
    invalid["outcome"] = "invalid-outcome"
    cases.append(_case("invalid:unknown-outcome", "episode", invalid, selected, source="invalid", expected_error=True))
    invalid_binary = dataclass_to_dict(edge_episode)
    invalid_binary["core_eligibility"] = True
    cases.append(_case("invalid:bool-core", "episode", invalid_binary, selected, source="invalid", expected_error=True))
    return cases


def _cargo_command(package_root: Path) -> list[str]:
    cargo = Path.home() / ".cargo" / "bin" / "cargo.exe"
    executable = str(cargo if cargo.is_file() else "cargo")
    return [
        executable,
        "+stable-x86_64-pc-windows-gnu",
        "run",
        "--quiet",
        "--manifest-path",
        str(package_root / "rust-oracle" / "Cargo.toml"),
        "--",
        "evaluate-jsonl",
    ]


def cargo_environment() -> dict[str, str]:
    environment = os.environ.copy()
    mingw = Path("C:/msys64/mingw64/bin")
    if mingw.is_dir():
        environment["PATH"] = str(mingw) + os.pathsep + environment.get("PATH", "")
    return environment


def _compare(expected: Any, actual: Any, path: str = "$") -> tuple[str, list[str]]:
    if type(expected) is not type(actual) and not (
        isinstance(expected, (int, float)) and isinstance(actual, (int, float))
        and not isinstance(expected, bool) and not isinstance(actual, bool)
    ):
        return "semantic_mismatch", [f"{path}: type mismatch"]
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return "semantic_mismatch", [f"{path}: key mismatch"]
        classifications = [_compare(expected[key], actual[key], f"{path}.{key}") for key in sorted(expected)]
        failures = [message for _, messages in classifications for message in messages]
        if failures:
            return "semantic_mismatch", failures
        return ("within_tolerance" if any(name == "within_tolerance" for name, _ in classifications) else "exact_match", [])
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return "semantic_mismatch", [f"{path}: length mismatch"]
        classifications = [_compare(left, right, f"{path}[{index}]") for index, (left, right) in enumerate(zip(expected, actual))]
        failures = [message for _, messages in classifications for message in messages]
        if failures:
            return "semantic_mismatch", failures
        return ("within_tolerance" if any(name == "within_tolerance" for name, _ in classifications) else "exact_match", [])
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if expected == actual:
            return "exact_match", []
        if close(float(expected), float(actual), TOLERANCE):
            return "within_tolerance", []
        return "semantic_mismatch", [f"{path}: expected {expected!r}, got {actual!r}"]
    if expected != actual:
        return "semantic_mismatch", [f"{path}: expected {expected!r}, got {actual!r}"]
    return "exact_match", []


def verify_rust_oracle(package_root: Path, parameter_set_id: str) -> dict[str, Any]:
    cases = build_differential_cases(package_root, parameter_set_id)
    with tempfile.TemporaryDirectory(prefix="gamification-rust-oracle-") as temporary:
        valid_contract = Path(temporary) / "differential-inputs.jsonl"
        invalid_contract = Path(temporary) / "invalid-inputs.jsonl"
        serialize = lambda selected: "".join(
            canonical_dumps({key: value for key, value in case.items() if key not in {"expected", "expected_error", "source"}}) + "\n"
            for case in selected
        )
        valid_contract.write_text(serialize(case for case in cases if not case["expected_error"]), encoding="utf-8")
        invalid_contract.write_text(serialize(case for case in cases if case["expected_error"]), encoding="utf-8")
        command = [*_cargo_command(package_root), str(valid_contract)]
        process = subprocess.run(
            command, cwd=package_root, text=True, capture_output=True, check=False,
            env=cargo_environment(), timeout=120,
        )
        invalid_command = [*_cargo_command(package_root), str(invalid_contract)]
        invalid_process = subprocess.run(
            invalid_command, cwd=package_root, text=True, capture_output=True, check=False,
            env=cargo_environment(), timeout=120,
        )
    if process.returncode != 0:
        raise ValueError(f"Rust oracle failed ({process.returncode}): {process.stderr.strip()}")
    if invalid_process.returncode == 0:
        raise ValueError("Rust oracle accepted invalid-input batch with exit code 0")
    lines = [
        loads_strict(line, context="Rust oracle JSONL")
        for line in (process.stdout + invalid_process.stdout).splitlines()
        if line.strip()
    ]
    if len(lines) != len(cases):
        raise ValueError(f"Rust oracle returned {len(lines)} rows for {len(cases)} cases")
    outputs = {line["case_id"]: line for line in lines}
    classifications = []
    for case in cases:
        output = outputs.get(case["case_id"])
        if output is None:
            classifications.append({"case_id": case["case_id"], "classification": "semantic_mismatch", "details": ["missing output"]})
            continue
        if case["expected_error"]:
            classification = "exact_match" if output["ok"] is False else "semantic_mismatch"
            details = [] if output["ok"] is False else ["Rust accepted invalid input"]
        elif output["ok"] is False:
            classification, details = "semantic_mismatch", [output.get("error", "Rust rejected valid input")]
        else:
            classification, details = _compare(case["expected"], output["result"])
        classifications.append(
            {
                "case_id": case["case_id"],
                "source": case["source"],
                "classification": classification,
                "details": details,
            }
        )
    counts = {
        name: sum(item["classification"] == name for item in classifications)
        for name in ("exact_match", "within_tolerance", "semantic_mismatch", "unsupported_case")
    }
    payload = {
        "manifest": {
            "contract_version": ORACLE_CONTRACT_VERSION,
            "parameter_set_id": parameter_set_id,
            "tolerance": TOLERANCE,
            "case_count": len(cases),
            "source_counts": {
                source: sum(case["source"] == source for case in cases)
                for source in sorted({case["source"] for case in cases})
            },
            "cargo_command": command[:-1] + ["<temporary-jsonl>"],
        },
        "counts": counts,
        "cases": classifications,
    }
    payload["manifest"]["output_digest"] = canonical_digest(payload)
    if counts["semantic_mismatch"]:
        first = next(item for item in classifications if item["classification"] == "semantic_mismatch")
        raise ValueError(f"Rust oracle semantic mismatch: {first}")
    return payload
