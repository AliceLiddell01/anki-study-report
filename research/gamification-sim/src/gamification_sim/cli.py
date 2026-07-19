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
from .parameter_catalog import PARAMETER_CANDIDATES, candidate_payload
from .sweep import (
    load_sweep_config,
    render_sweep_summary,
    run_sensitivity,
    run_sweep,
    write_sweep_reports,
)
from .population import (
    load_personas,
    render_population_summary,
    run_population,
    write_population_reports,
)
from .rust_oracle import verify_rust_oracle
from .fsrs_reference import verify_fsrs_reference
from .longitudinal_config import load_longitudinal_config
from .longitudinal_runner import (
    render_longitudinal_summary,
    run_longitudinal,
    validate_longitudinal_result,
    write_longitudinal_reports,
)
from .validation import close
from .workspace import ResearchWorkspace, default_output_root, resolve_research_workspace


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
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-write", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Review XP research simulator")
    parser.add_argument(
        "--research-root",
        type=Path,
        help="validated research/gamification-sim workspace root",
    )
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

    subparsers.add_parser("list-parameter-sets", help="list versioned sweep candidates")

    validate_sweep = subparsers.add_parser("validate-sweep", help="validate a bounded sweep config")
    validate_sweep.add_argument("config", type=Path)

    sweep = subparsers.add_parser("run-sweep", help="run a bounded sequential parameter sweep")
    sweep.add_argument("config", type=Path)
    sweep.add_argument("--output-dir", type=Path)
    sweep.add_argument("--no-write", action="store_true")

    sensitivity = subparsers.add_parser("run-sensitivity", help="run deterministic OAT sensitivity")
    sensitivity.add_argument("config", type=Path)
    sensitivity.add_argument("--parameter-set", required=True)
    sensitivity.add_argument("--output-dir", type=Path)
    sensitivity.add_argument("--no-write", action="store_true")

    personas = subparsers.add_parser("validate-personas", help="validate the synthetic persona catalog")
    personas.add_argument("persona_dir", type=Path)

    population = subparsers.add_parser("run-population", help="run a seeded synthetic population")
    population.add_argument("--mode", choices=("development", "standard", "long"), required=True)
    population.add_argument("--parameter-set", required=True)
    population.add_argument("--seed", type=int, required=True)
    population.add_argument("--persona-dir", type=Path)
    population.add_argument("--output-dir", type=Path)
    population.add_argument("--smoke", action="store_true", help="bounded smoke for long mode")
    population.add_argument("--no-write", action="store_true")

    validate_longitudinal = subparsers.add_parser(
        "validate-longitudinal-config",
        help="validate a bounded persistent-card simulation config",
    )
    validate_longitudinal.add_argument("config", type=Path)

    longitudinal = subparsers.add_parser(
        "run-longitudinal",
        help="run bounded persistent-card policy histories",
    )
    longitudinal.add_argument("config", type=Path)
    longitudinal.add_argument(
        "--mode",
        choices=("development", "calibration-90", "calibration-365"),
        required=True,
    )
    longitudinal.add_argument("--seed", type=int, required=True)
    longitudinal.add_argument("--parameter-set", action="append", dest="parameter_sets")
    longitudinal.add_argument("--policy", action="append", dest="policies")
    longitudinal.add_argument("--output-dir", type=Path)
    longitudinal.add_argument("--no-write", action="store_true")

    rust = subparsers.add_parser("verify-rust-oracle", help="verify Python/Rust deterministic parity")
    rust.add_argument("--parameter-set", required=True)
    rust.add_argument("--corpus", type=Path)
    rust.add_argument("--output-dir", type=Path)
    rust.add_argument("--no-write", action="store_true")

    fsrs = subparsers.add_parser("verify-fsrs-reference", help="compare official Python/Rust FSRS state references")
    fsrs.add_argument("contract", type=Path)
    fsrs.add_argument("--output-dir", type=Path)
    fsrs.add_argument("--no-write", action="store_true")
    return parser


def _scenario_root(path: Path) -> Path:
    resolved = path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        if parent.name == "scenarios":
            return parent
    return resolved.parent


def _apply_workspace_defaults(args, workspace: ResearchWorkspace) -> None:
    if hasattr(args, "output_dir") and args.output_dir is None:
        args.output_dir = default_output_root()
    if args.command == "run-population" and args.persona_dir is None:
        args.persona_dir = workspace.personas
    if args.command == "verify-rust-oracle" and args.corpus is None:
        args.corpus = workspace.scenarios


def _emit_run(result, args) -> int:
    if args.as_json:
        print(render_json_report(result), end="")
    else:
        print(render_markdown_report(result), end="")
    if not args.no_write:
        run_dir = write_reports(result, args.output_dir)
        print(f"reports: {run_dir}", file=sys.stderr)
    return 0 if result.passed else 1


def _run_new_command(args, workspace: ResearchWorkspace) -> int:
    if args.command == "validate-longitudinal-config":
        config = load_longitudinal_config(args.config, workspace=workspace)
        print(
            f"VALID {config.version} {config.config_id} "
            f"{len(config.policies)} policies"
        )
        return 0
    if args.command == "run-longitudinal":
        config = load_longitudinal_config(args.config, workspace=workspace)
        payload = run_longitudinal(
            config,
            mode_id=args.mode,
            master_seed=args.seed,
            parameter_set_ids=tuple(args.parameter_sets) if args.parameter_sets else None,
            policy_ids=tuple(args.policies) if args.policies else None,
            workspace=workspace,
        )
        validate_longitudinal_result(payload)
        print(render_longitudinal_summary(payload), end="")
        if not args.no_write:
            run_dir = write_longitudinal_reports(payload, args.output_dir)
            print(f"reports: {run_dir}", file=sys.stderr)
        return 0
    if args.command == "verify-fsrs-reference":
        payload = verify_fsrs_reference(args.contract, workspace.root)
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        if not args.no_write:
            output_dir = args.output_dir.resolve() / "fsrs-reference"
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{payload['manifest']['output_digest'][:12]}.json"
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            print(f"report: {path}", file=sys.stderr)
        return 0
    if args.command == "verify-rust-oracle":
        if args.corpus.resolve() != workspace.scenarios.resolve():
            raise ValueError("verify-rust-oracle currently requires the committed scenarios corpus")
        payload = verify_rust_oracle(workspace.root, args.parameter_set)
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        if not args.no_write:
            output_dir = args.output_dir.resolve() / "rust-oracle"
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{payload['manifest']['output_digest'][:12]}.json"
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            print(f"report: {path}", file=sys.stderr)
        return 0
    if args.command == "validate-personas":
        personas = load_personas(args.persona_dir, workspace=workspace)
        print(f"VALID {len(personas)} personas {personas[0].version}")
        return 0
    if args.command == "run-population":
        personas = load_personas(args.persona_dir, workspace=workspace)
        payload = run_population(
            personas,
            workspace.root,
            mode=args.mode,
            parameter_set_id=args.parameter_set,
            master_seed=args.seed,
            smoke=args.smoke,
        )
        print(render_population_summary(payload), end="")
        if not args.no_write:
            run_dir = write_population_reports(payload, args.output_dir)
            print(f"reports: {run_dir}", file=sys.stderr)
        return 0
    if args.command == "list-parameter-sets":
        print(json.dumps([candidate_payload(item) for item in PARAMETER_CANDIDATES], indent=2, sort_keys=True, allow_nan=False))
        return 0
    if args.command == "validate-sweep":
        config = load_sweep_config(args.config, workspace)
        print(f"VALID {config.sweep_version} {config.sweep_id}")
        return 0
    if args.command == "run-sweep":
        config = load_sweep_config(args.config, workspace)
        payload = run_sweep(config, workspace.root)
        print(render_sweep_summary(payload), end="")
        if not args.no_write:
            run_dir = write_sweep_reports(payload, args.output_dir)
            print(f"reports: {run_dir}", file=sys.stderr)
        return 0
    if args.command == "run-sensitivity":
        config = load_sweep_config(args.config, workspace)
        payload = run_sensitivity(config, workspace.root, args.parameter_set)
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        if not args.no_write:
            output_root = args.output_dir.resolve() / "sensitivity"
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = output_root / f"{payload['manifest']['output_digest'][:12]}.json"
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            print(f"report: {output_path}", file=sys.stderr)
        return 0
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
        workspace = resolve_research_workspace(args.research_root)
        _apply_workspace_defaults(args, workspace)
        if args.command in {"verify-examples", "evaluate"}:
            fixture = (
                workspace.path("fixtures/golden_cases.json")
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
        return _run_new_command(args, workspace)
    except (StrictJsonError, ScenarioSchemaError, ScenarioDomainError, ValueError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"INTERNAL ERROR: {exc}", file=sys.stderr)
        return 3
