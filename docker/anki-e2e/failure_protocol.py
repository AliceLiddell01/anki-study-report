#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from failure_registry import *  # noqa: F401,F403
from failure_schema import *  # noqa: F401,F403
from failure_store import *  # noqa: F401,F403

def render_markdown(document: dict[str, Any]) -> str:
    value = validate_document(document)
    primary = value["primary"]
    context = value["context"]
    evidence = ", ".join(f"`{item}`" for item in primary["evidencePaths"]) or "n/a"
    original = primary["originalSignal"] or (str(primary["originalExitCode"]) if primary["originalExitCode"] is not None else "n/a")
    return "\n".join([
        "## Failure diagnostics",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Result | FAILURE |",
        f"| Code | `{primary['failureCode']}` |",
        f"| Category | `{primary['category']}` |",
        f"| Phase | `{primary['phaseId'] or 'n/a'}` |",
        f"| Item | `{primary['itemId'] or 'n/a'}` |",
        f"| Summary | {primary['summary']} |",
        f"| Original exit/signal | `{original}` |",
        f"| Last successful phase | `{context['lastSuccessfulPhaseId'] or 'n/a'}` |",
        f"| Last successful item | `{context['lastSuccessfulItemId'] or 'n/a'}` |",
        f"| Secondary failures | {len(value['secondary'])} |",
        f"| Cleanup | `{value['cleanup']['status']}` |",
        f"| Evidence | {evidence} |",
        "",
    ])


def annotation(document: dict[str, Any]) -> str:
    value = validate_document(document)
    primary = value["primary"]
    message = sanitize_summary(
        f"{primary['summary']}; phase={primary['phaseId'] or 'n/a'}; item={primary['itemId'] or 'n/a'}",
        primary["summary"],
    )
    return f"::error title={primary['failureCode']}::{message}"


def _parse_paths(values: Sequence[str] | None) -> list[str]:
    return list(values or [])


def _record_from_args(args: argparse.Namespace, *, primary: bool) -> dict[str, Any]:
    code = args.failure_code or code_for_phase(args.producer, args.phase_id, item_kind=args.item_kind)
    failure = build_failure(
        code=code,
        phase_id=args.phase_id,
        item_id=args.item_id,
        item_kind=args.item_kind,
        error_type=args.error_type,
        summary=args.summary,
        elapsed_ms=args.elapsed_ms,
        original_exit_code=args.original_exit_code,
        original_signal=args.original_signal,
        evidence_paths=_parse_paths(args.evidence_path),
        raw_diagnostic_paths=_parse_paths(args.raw_diagnostic_path),
    )
    return record_failure(
        args.output,
        args.producer,
        failure,
        primary=primary,
        last_successful_phase_id=args.last_successful_phase_id,
        last_successful_item_id=args.last_successful_item_id,
        active_phase_id=args.active_phase_id or args.phase_id,
        active_item_id=args.active_item_id or args.item_id,
    )


def _add_record_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--producer", required=True, choices=sorted(ALLOWED_PRODUCERS))
    parser.add_argument("--failure-code", choices=sorted(REGISTRY))
    parser.add_argument("--phase-id")
    parser.add_argument("--item-id")
    parser.add_argument("--item-kind")
    parser.add_argument("--error-type", default="Error")
    parser.add_argument("--summary")
    parser.add_argument("--elapsed-ms", type=int)
    parser.add_argument("--original-exit-code", type=int)
    parser.add_argument("--original-signal", choices=sorted(item for item in ALLOWED_SIGNALS if item))
    parser.add_argument("--evidence-path", action="append")
    parser.add_argument("--raw-diagnostic-path", action="append")
    parser.add_argument("--last-successful-phase-id")
    parser.add_argument("--last-successful-item-id")
    parser.add_argument("--active-phase-id")
    parser.add_argument("--active-item-id")


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical stable CI/E2E failure diagnostics protocol")
    commands = parser.add_subparsers(dest="command", required=True)
    primary = commands.add_parser("record-primary")
    _add_record_arguments(primary)
    secondary = commands.add_parser("record-secondary")
    _add_record_arguments(secondary)
    browser = commands.add_parser("record-browser-primary")
    browser.add_argument("--output", required=True, type=Path)
    browser.add_argument("--report", required=True, type=Path)
    browser.add_argument("--original-exit-code", type=int, default=1)
    cleanup = commands.add_parser("set-cleanup-status")
    cleanup.add_argument("--output", required=True, type=Path)
    cleanup.add_argument("--status", required=True, choices=("not_started", "success", "failure", "partial"))
    validate = commands.add_parser("validate")
    validate.add_argument("--output", required=True, type=Path)
    render = commands.add_parser("render")
    render.add_argument("--output", required=True, type=Path)
    render.add_argument("--markdown-output", type=Path)
    annotation_parser = commands.add_parser("annotation")
    annotation_parser.add_argument("--output", required=True, type=Path)
    primary_code = commands.add_parser("primary-code")
    primary_code.add_argument("--output", required=True, type=Path)
    registry = commands.add_parser("registry")
    registry.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "record-primary":
            _record_from_args(args, primary=True)
        elif args.command == "record-secondary":
            _record_from_args(args, primary=False)
        elif args.command == "record-browser-primary":
            failure, last_item = browser_failure_from_report(args.report, original_exit_code=args.original_exit_code)
            record_failure(
                args.output,
                "docker-e2e",
                failure,
                primary=True,
                last_successful_phase_id="api-smoke-first",
                last_successful_item_id=last_item,
                active_phase_id="browser-smoke-first",
                active_item_id=failure["itemId"],
            )
        elif args.command == "set-cleanup-status":
            set_cleanup_status(args.output, args.status)
        elif args.command == "validate":
            load_document(args.output)
        elif args.command == "render":
            rendered = render_markdown(load_document(args.output))
            if args.markdown_output:
                atomic_write(args.markdown_output, rendered)
            else:
                print(rendered, end="")
        elif args.command == "annotation":
            print(annotation(load_document(args.output)))
        elif args.command == "primary-code":
            print(load_document(args.output)["primary"]["failureCode"])
        else:
            payload = {
                code: {
                    "category": meta.category,
                    "domain": meta.domain,
                    "defaultSummary": meta.default_summary,
                    "defaultExitClass": meta.default_exit_class,
                    "allowedPhases": sorted(meta.allowed_phases),
                    "canBeSecondary": meta.can_be_secondary,
                }
                for code, meta in sorted(REGISTRY.items())
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                for code in payload:
                    print(code)
        return 0
    except (FailureProtocolError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
