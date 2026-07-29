#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Mapping, Sequence

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path: sys.path.insert(0, str(_DIR))
from e2e_preflight_contract import *
from e2e_preflight_checks import runtime_checks, static_checks

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def default_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> CommandResult:
    completed = subprocess.run(list(args), cwd=cwd, env=dict(env), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)

def run_preflight(root: Path, report_path: Path, *, layer: str, execution_context: str, env: Mapping[str, str] | None = None, command_runner: CommandRunner | None = None) -> dict[str, object]:
    root = root.resolve(); environment = dict(os.environ if env is None else env)
    if execution_context not in ALLOWED_CONTEXTS or layer not in {"static", "runtime", "all"}: raise PreflightError("unsupported preflight context or layer")
    previous: list[dict[str, object]] = []; started = utc_now(); prior_ms = 0
    if layer == "runtime":
        prior = load_report(report_path)
        if prior["status"] != "PASS" or [c["id"] for c in prior["checks"]] != list(STATIC_CHECK_IDS) or prior["executionContext"] != execution_context: raise PreflightError("runtime preflight requires a successful canonical static report")
        previous = list(prior["checks"]); started = str(prior["startedAtUtc"]); prior_ms = int(prior["durationMs"])
    started_ns = time.monotonic_ns(); checks = list(previous); failed: str | None = None; operations = []
    if layer in {"static", "all"}: operations.extend(static_checks(root, environment))
    if layer in {"runtime", "all"}: operations.extend(runtime_checks(root, environment, command_runner or default_runner))
    for check_id, operation in operations:
        check_started = time.monotonic_ns(); status = "PASS"
        try: summary = operation()
        except PreflightError as exc: status = "FAIL"; summary = str(exc); failed = check_id
        checks.append({"id": check_id, "status": status, "durationMs": max(0, (time.monotonic_ns()-check_started)//1_000_000), "summary": safe_summary(summary)})
        if failed: break
    report = {"schemaVersion": SCHEMA_VERSION, "status": "FAIL" if failed else "PASS", "producer": PRODUCER, "executionContext": execution_context, "startedAtUtc": started, "finishedAtUtc": utc_now(), "durationMs": prior_ms + max(0, (time.monotonic_ns()-started_ns)//1_000_000), "checks": checks, "failedCheckId": failed}
    normalized = validate_report(report); atomic_write(report_path, serialize_report(normalized)); return normalized

def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Docker E2E preflight"); subs = parser.add_subparsers(dest="command", required=True)
    run = subs.add_parser("run"); run.add_argument("--repo-root", type=Path, default=Path.cwd()); run.add_argument("--output", type=Path, required=True); run.add_argument("--layer", choices=("static", "runtime", "all"), required=True); run.add_argument("--execution-context", choices=sorted(ALLOWED_CONTEXTS), required=True)
    validate = subs.add_parser("validate"); validate.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    try:
        report = load_report(args.output) if args.command == "validate" else run_preflight(args.repo_root, args.output, layer=args.layer, execution_context=args.execution_context)
        print(f"[PREFLIGHT] {report['status']} checks={len(report['checks'])} failed={report['failedCheckId'] or 'none'}", flush=True)
        return 0 if report["status"] == "PASS" else 2
    except (PreflightError, OSError) as exc: parser.exit(2, f"preflight error: {exc}\n")

if __name__ == "__main__": raise SystemExit(main())
