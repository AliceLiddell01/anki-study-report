from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .breakdown import to_dict
from .day_aggregation import aggregate_day
from .episode_reward import evaluate_episode
from .input_parsing import day_from_dict, episode_from_dict
from .output_digest import verify_output_digest
from .reporting import render_json_report, render_markdown_report, write_reports
from .scenario_loader import (
    ScenarioDomainError,
    load_corpus,
    load_scenario,
)
from .scenario_models import ScenarioCategory
from .scenario_runner import run_corpus, run_definitions
from .scenario_schema import ScenarioSchemaError
from .strict_json import StrictJsonError, load_strict_json
from .validation import close


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def evaluate_cases(path: Path) -> tuple[int, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    failures = 0
    results: list[dict[str, Any]] = []
    for case in payload["cases"]:
        if case["kind"] == "episode":
            result = evaluate_episode(episode_from_dict(case["input"]))
        elif case["kind"] == "day":
            result = aggregate_day(day_from_dict(case["input"]))
        else:
            raise ValueError(f"unknown case kind: {case['kind']}")
        actual = to_dict(result)
        mismatches: list[str] = []
        for key, expected in case["expected"].items():
            observed = actual[key]
            if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                if not close(float(observed), float(expected)):
                    mismatches.append(f"{key}: expected {expected}, got {observed}")
            elif observed != expected:
                mismatches.append(f"{key}: expected {expected!r}, got {observed!r}")
        if mismatches:
            failures += 1
        results.append({"id": case["id"], "ok": not mismatches, "mismatches": mismatches, "actual": actual})
    return failures, results


def _add_run_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output-dir", type=Path, default=PACKAGE_ROOT / "outputs")
    parser.add_argument("--no-write", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Review XP research simulator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify-examples", help="verify bundled golden cases")
    verify.add_argument("--json", action="store_true", dest="as_json")

    evaluate = subparsers.add_parser("evaluate", help="evaluate a Stage 5B.1 fixture file")
    evaluate.add_argument("fixture", type=Path)
    evaluate.add_argument("--json", action="store_true", dest="as_json")

    verify_report = subparsers.add_parser(
        "verify-report",
        help="verify a detached digest in an existing scenario report",
    )
    verify_report.add_argument("report", type=Path)

    validate = subparsers.add_parser("validate-scenarios", help="validate a scenario corpus")
    validate.add_argument("scenario_dir", type=Path)
    validate.add_argument("--json", action="store_true", dest="as_json")

    single = subparsers.add_parser("run-scenario", help="run one deterministic scenario")
    single.add_argument("scenario", type=Path)
    _add_run_flags(single)

    corpus = subparsers.add_parser("run-scenarios", help="run a deterministic scenario corpus")
    corpus.add_argument("scenario_dir", type=Path)
    _add_run_flags(corpus)

    compare = subparsers.add_parser("compare-scenarios", help="compare a control and dependent scenario")
    compare.add_argument("control", type=Path)
    compare.add_argument("scenario", type=Path)
    _add_run_flags(compare)
    return parser


def _scenario_root(path: Path) -> Path:
    resolved = path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        if parent.name == "scenarios":
            return parent
    return resolved.parent


def _emit_run(result, args) -> int:
    if args.as_json:
        print(render_json_report(result), end="")
    else:
        print(render_markdown_report(result), end="")
    if not args.no_write:
        run_dir = write_reports(result, args.output_dir)
        print(f"reports: {run_dir}", file=sys.stderr)
    return 0 if result.passed else 1


def _run_new_command(args) -> int:
    if args.command == "verify-report":
        payload = load_strict_json(args.report)
        if not isinstance(payload, dict):
            raise ValueError("scenario report must be a JSON object")
        if not verify_output_digest(payload):
            print("MISMATCH: output digest verification failed", file=sys.stderr)
            return 1
        print("VERIFIED detached-corpus-result-v1")
        return 0
    if args.command == "validate-scenarios":
        definitions = load_corpus(args.scenario_dir)
        if args.as_json:
            print(json.dumps({"valid": True, "scenario_ids": sorted(item.scenario_id for item in definitions)}, indent=2, sort_keys=True))
        else:
            print(f"VALID {len(definitions)} scenarios")
        return 0
    if args.command == "run-scenarios":
        return _emit_run(run_corpus(args.scenario_dir, command="run-scenarios"), args)
    if args.command == "run-scenario":
        definition = load_scenario(args.scenario)
        if definition.control_scenario_id:
            corpus = load_corpus(_scenario_root(args.scenario))
            by_id = {item.scenario_id: item for item in corpus}
            definitions = (by_id[definition.control_scenario_id], by_id[definition.scenario_id])
        else:
            definitions = (definition,)
        return _emit_run(run_definitions(definitions, command="run-scenario"), args)
    if args.command == "compare-scenarios":
        control = load_scenario(args.control)
        scenario = load_scenario(args.scenario)
        if control.category is not ScenarioCategory.CONTROL:
            raise ScenarioDomainError("first compare input must have category control")
        if scenario.control_scenario_id != control.scenario_id:
            raise ScenarioDomainError("scenario control_scenario_id does not match the supplied control")
        return _emit_run(
            run_definitions((control, scenario), command="compare-scenarios"),
            args,
        )
    raise RuntimeError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"verify-examples", "evaluate"}:
            fixture = (
                PACKAGE_ROOT / "fixtures" / "golden_cases.json"
                if args.command == "verify-examples"
                else args.fixture
            )
            failures, results = evaluate_cases(fixture)
            if args.as_json:
                print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
            else:
                for result in results:
                    status = "PASS" if result["ok"] else "FAIL"
                    print(f"{status} {result['id']}")
                    for mismatch in result["mismatches"]:
                        print(f"  {mismatch}")
                print(f"{len(results) - failures}/{len(results)} cases passed")
            return 1 if failures else 0
        return _run_new_command(args)
    except (StrictJsonError, ScenarioSchemaError, ScenarioDomainError, ValueError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"INTERNAL ERROR: {exc}", file=sys.stderr)
        return 3
