from __future__ import annotations

import argparse
import importlib.util
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import time
import sys
from typing import Any

SCHEMA_VERSION = 1
WORKFLOW_NAME = "Fast CI"
PRODUCER_JOB = "fast"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
EVENT_RE = re.compile(r"^[A-Za-z0-9_]+$")
ABSOLUTE_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")
TOKEN_URL_RE = re.compile(r"(?:https?://[^\s]+@|[?&](?:access_)?token=)", re.I)
FINAL_RESULTS = {"success", "failure", "cancelled"}
PHASE_STATUSES = {"success", "failure", "skipped"}
PHASES: dict[str, tuple[str, str]] = {
    "install-python-dependencies": ("Install Python dependencies", "dependency"),
    "install-frontend-dependencies": ("Install frontend dependencies", "dependency"),
    "changelog-check": ("Structured changelog generated outputs", "python"),
    "frontend-typecheck-tests": ("Frontend typecheck before tests", "frontend"),
    "frontend-vitest": ("Frontend Vitest", "frontend"),
    "frontend-typecheck-build": ("Frontend typecheck before build", "frontend"),
    "frontend-vite-build": ("Vite production build", "frontend"),
    "frontend-bundle-check": ("Frontend bundle validation", "frontend"),
    "frontend-addon-assets-copy": ("Dashboard asset synchronization", "frontend"),
    "python-pytest": ("Python pytest", "python"),
    "package-build-check": ("Build and validate package archive", "package"),
    "package-check-only": ("Verify package archive", "package"),
    "verification-planner": ("Verification planner", "ci-finalization"),
    "ci-summary": ("Fast CI summary preparation", "ci-finalization"),
    "package-metadata-write": ("Exact package metadata preparation", "ci-finalization"),
    "package-staged-validation": ("Staged exact package validation", "ci-finalization"),
    "package-metadata-verify": ("Exact package metadata verification", "ci-finalization"),
}
DOC_FIELDS = {
    "schemaVersion", "repository", "workflowName", "producerJob", "eventName", "ref",
    "testedCommitSha", "runId", "runAttempt", "startedAt", "completedAt", "result",
    "durationMs", "phases",
}
PHASE_FIELDS = {
    "id", "label", "category", "status", "startedAt", "completedAt", "durationMs", "exitCode",
}


class TimingError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise TimingError(f"{label} must be a UTC ISO-8601 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TimingError(f"{label} must be valid UTC ISO-8601") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise TimingError(f"{label} must use UTC")
    return value


def require_int(value: Any, label: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < (1 if positive else 0):
        adjective = "positive" if positive else "non-negative"
        raise TimingError(f"{label} must be a {adjective} integer")
    return value


def safe_text(value: Any, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(c in value for c in "\r\n\0"):
        raise TimingError(f"{label} must be a non-empty single-line string")
    if pattern and not pattern.fullmatch(value):
        raise TimingError(f"{label} has an invalid format")
    if ABSOLUTE_PATH_RE.match(value) or TOKEN_URL_RE.search(value):
        raise TimingError(f"{label} contains unsafe path or URL data")
    return value


def normalize_sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise TimingError("testedCommitSha must be an exact 40-character hexadecimal SHA")
    return value.lower()


def state_path(output: Path) -> Path:
    return output.with_name(output.name + ".state")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TimingError(f"Timing file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TimingError(f"Timing file is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise TimingError("Timing document must be a JSON object")
    return value


def scan_safe(value: Any, location: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in ("token", "authorization", "environment", "commandline", "actoremail")):
                raise TimingError(f"Unsafe field name at {location}.{key}")
            scan_safe(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            scan_safe(nested, f"{location}[{index}]")
    elif isinstance(value, str) and (ABSOLUTE_PATH_RE.match(value) or TOKEN_URL_RE.search(value)):
        raise TimingError(f"Unsafe path or token-bearing URL at {location}")


def validate(document: dict[str, Any], *, allow_running: bool = False) -> dict[str, Any]:
    if set(document) != DOC_FIELDS or document["schemaVersion"] != SCHEMA_VERSION:
        raise TimingError("Timing document differs from schema v1")
    repository = safe_text(document["repository"], "repository", REPOSITORY_RE)
    if document["workflowName"] != WORKFLOW_NAME or document["producerJob"] != PRODUCER_JOB:
        raise TimingError("Workflow identity mismatch")
    event_name = safe_text(document["eventName"], "eventName", EVENT_RE)
    ref = safe_text(document["ref"], "ref")
    tested_sha = normalize_sha(document["testedCommitSha"])
    run_id = require_int(document["runId"], "runId", positive=True)
    run_attempt = require_int(document["runAttempt"], "runAttempt", positive=True)
    started_at = parse_utc(document["startedAt"], "startedAt")
    result = document["result"]
    completed_at = document["completedAt"]
    if result == "running":
        if not allow_running or completed_at is not None:
            raise TimingError("Running timing document has invalid finalization data")
    elif result in FINAL_RESULTS:
        parse_utc(completed_at, "completedAt")
    else:
        raise TimingError("result has an invalid value")
    duration_ms = require_int(document["durationMs"], "durationMs")
    if not isinstance(document["phases"], list):
        raise TimingError("phases must be an array")
    phases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for phase in document["phases"]:
        if not isinstance(phase, dict) or set(phase) != PHASE_FIELDS:
            raise TimingError("Phase differs from schema v1")
        phase_id = phase["id"]
        if phase_id not in PHASES or phase_id in seen:
            raise TimingError(f"Unknown or duplicate phase id: {phase_id}")
        seen.add(phase_id)
        label, category = PHASES[phase_id]
        if phase["label"] != label or phase["category"] != category:
            raise TimingError(f"Phase metadata mismatch: {phase_id}")
        status = phase["status"]
        if status == "running":
            if not allow_running or phase["completedAt"] is not None or phase["exitCode"] is not None:
                raise TimingError(f"Running phase is invalid: {phase_id}")
        elif status in PHASE_STATUSES:
            parse_utc(phase["completedAt"], f"{phase_id}.completedAt")
            require_int(phase["exitCode"], f"{phase_id}.exitCode")
        else:
            raise TimingError(f"Invalid phase status: {status}")
        parse_utc(phase["startedAt"], f"{phase_id}.startedAt")
        require_int(phase["durationMs"], f"{phase_id}.durationMs")
        phases.append(dict(phase))
    normalized = {
        "schemaVersion": SCHEMA_VERSION, "repository": repository, "workflowName": WORKFLOW_NAME,
        "producerJob": PRODUCER_JOB, "eventName": event_name, "ref": ref,
        "testedCommitSha": tested_sha, "runId": run_id, "runAttempt": run_attempt,
        "startedAt": started_at, "completedAt": completed_at, "result": result,
        "durationMs": duration_ms, "phases": phases,
    }
    scan_safe(normalized)
    return normalized


def load_state(output: Path) -> dict[str, Any]:
    state = load_json(state_path(output))
    if set(state) != {"startedMonotonicNs", "activePhases"} or not isinstance(state["activePhases"], dict):
        raise TimingError("Timing state has an invalid shape")
    require_int(state["startedMonotonicNs"], "startedMonotonicNs")
    return state


def initialize(output: Path, repository: str, event_name: str, ref: str, tested_commit_sha: str, run_id: int, run_attempt: int) -> dict[str, Any]:
    if output.exists() or state_path(output).exists():
        raise TimingError("Timing output already exists")
    document = validate({
        "schemaVersion": 1, "repository": repository, "workflowName": WORKFLOW_NAME,
        "producerJob": PRODUCER_JOB, "eventName": event_name, "ref": ref,
        "testedCommitSha": tested_commit_sha, "runId": run_id, "runAttempt": run_attempt,
        "startedAt": utc_now(), "completedAt": None, "result": "running",
        "durationMs": 0, "phases": [],
    }, allow_running=True)
    write_json(output, document)
    write_json(state_path(output), {"startedMonotonicNs": time.monotonic_ns(), "activePhases": {}})
    return document


def start_phase(output: Path, phase_id: str) -> None:
    document = validate(load_json(output), allow_running=True)
    state = load_state(output)
    if phase_id not in PHASES:
        raise TimingError(f"Unknown phase id: {phase_id}")
    if document["result"] != "running":
        raise TimingError("Cannot start a phase after finalization")
    if phase_id in state["activePhases"] or any(p["id"] == phase_id for p in document["phases"]):
        raise TimingError(f"Duplicate phase id: {phase_id}")
    label, category = PHASES[phase_id]
    document["phases"].append({
        "id": phase_id, "label": label, "category": category, "status": "running",
        "startedAt": utc_now(), "completedAt": None, "durationMs": 0, "exitCode": None,
    })
    state["activePhases"][phase_id] = time.monotonic_ns()
    write_json(output, validate(document, allow_running=True))
    write_json(state_path(output), state)


def finish_phase(output: Path, phase_id: str, exit_code: int, status: str | None = None) -> None:
    exit_code = require_int(exit_code, "exitCode")
    document = validate(load_json(output), allow_running=True)
    state = load_state(output)
    if phase_id not in state["activePhases"]:
        raise TimingError(f"Phase is not active: {phase_id}")
    phase = next((p for p in document["phases"] if p["id"] == phase_id), None)
    if phase is None or phase["status"] != "running":
        raise TimingError(f"Phase is not running: {phase_id}")
    resolved = status or ("success" if exit_code == 0 else "failure")
    if resolved not in PHASE_STATUSES or (resolved == "success") != (exit_code == 0):
        raise TimingError("Phase status and exitCode disagree")
    started_ns = state["activePhases"].pop(phase_id)
    phase.update(status=resolved, completedAt=utc_now(), durationMs=max(0, (time.monotonic_ns() - started_ns) // 1_000_000), exitCode=exit_code)
    write_json(output, validate(document, allow_running=True))
    write_json(state_path(output), state)


def record_phase_for_test(
    output: Path, *, phase_id: str, status: str, started_at: str, completed_at: str, duration_ms: int, exit_code: int
) -> dict[str, Any]:
    document = validate(load_json(output), allow_running=True)
    state = load_state(output)
    if phase_id not in PHASES:
        raise TimingError(f"Unknown phase id: {phase_id}")
    if any(phase["id"] == phase_id for phase in document["phases"]):
        raise TimingError(f"Duplicate phase id: {phase_id}")
    if status not in PHASE_STATUSES:
        raise TimingError(f"Invalid phase status: {status}")
    duration_ms = require_int(duration_ms, "durationMs")
    exit_code = require_int(exit_code, "exitCode")
    if (status == "success") != (exit_code == 0):
        raise TimingError("Phase status and exitCode disagree")
    label, category = PHASES[phase_id]
    document["phases"].append({
        "id": phase_id, "label": label, "category": category, "status": status,
        "startedAt": parse_utc(started_at, "startedAt"),
        "completedAt": parse_utc(completed_at, "completedAt"),
        "durationMs": duration_ms, "exitCode": exit_code,
    })
    write_json(output, validate(document, allow_running=True))
    write_json(state_path(output), state)
    return document


def finalize(output: Path, result: str, markdown_output: Path | None = None, summary_output: Path | None = None) -> dict[str, Any]:
    if result not in FINAL_RESULTS:
        raise TimingError("Invalid final result")
    document = validate(load_json(output), allow_running=True)
    state = load_state(output)
    now_ns, now_utc = time.monotonic_ns(), utc_now()
    for phase in document["phases"]:
        if phase["status"] == "running":
            started_ns = state["activePhases"].pop(phase["id"], now_ns)
            phase.update(status="failure", completedAt=now_utc, durationMs=max(0, (now_ns - started_ns) // 1_000_000), exitCode=1)
            if result == "success":
                result = "failure"
    document.update(completedAt=now_utc, result=result, durationMs=max(0, (now_ns - state["startedMonotonicNs"]) // 1_000_000))
    document = validate(document)
    write_json(output, document)
    state_path(output).unlink(missing_ok=True)
    rendered = render_markdown(document)
    if markdown_output:
        atomic_write(markdown_output, rendered)
    if summary_output:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        with summary_output.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n" + rendered)
    return document


def render_markdown(document: dict[str, Any]) -> str:
    document = validate(document)
    phases = document["phases"]
    top = sorted(phases, key=lambda p: (-p["durationMs"], p["id"]))[:5]
    lines = [
        "# Fast CI timing", "", "| Field | Value |", "| --- | --- |",
        f"| Result | {document['result']} |", f"| Tested commit | `{document['testedCommitSha']}` |",
        f"| Internal timed total | {sum(p['durationMs'] for p in phases)} ms |",
        f"| Timing document duration | {document['durationMs']} ms |", "", "## Top phases", "",
        "| Phase | Category | Status | Duration |", "| --- | --- | --- | ---: |",
    ]
    lines.extend(f"| {p['label']} | {p['category']} | {p['status']} | {p['durationMs']} ms |" for p in top)
    if not top:
        lines.append("| No internal phases recorded | n/a | n/a | 0 ms |")
    lines += ["", "## TypeScript typechecks", "", "| Phase | Duration |", "| --- | ---: |"]
    for phase_id in ("frontend-typecheck-tests", "frontend-typecheck-build"):
        phase = next((p for p in phases if p["id"] == phase_id), None)
        lines.append(f"| {PHASES[phase_id][0]} | {phase['durationMs']} ms |" if phase else f"| {PHASES[phase_id][0]} | not recorded |")
    lines += ["", "GitHub action setup, artifact upload, and post-job cache durations are external step timings and must be analyzed through the GitHub Jobs API.", ""]
    return "\n".join(lines)


validate_document = validate


_SCRIPT_DIR = Path(__file__).resolve().parent
_REPOSITORY_ROOT = _SCRIPT_DIR.parent


def _load_run_event_protocol():
    path = _REPOSITORY_ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"
    spec = importlib.util.spec_from_file_location("asr_run_event_protocol", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load run event protocol from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_events = _load_run_event_protocol()
if set(PHASES) != run_events.FAST_CI_PHASES - {"run"}:
    missing_from_protocol = sorted(set(PHASES) - run_events.FAST_CI_PHASES)
    missing_from_timing = sorted((run_events.FAST_CI_PHASES - {"run"}) - set(PHASES))
    raise RuntimeError(
        "Fast CI timing and run-event phase registries differ: "
        f"missingFromProtocol={missing_from_protocol} missingFromTiming={missing_from_timing}"
    )


def _events_path(explicit: Path | None, timing_output: Path) -> Path:
    if explicit is not None:
        return explicit
    value = str(os.environ.get("ASR_RUN_EVENTS_PATH") or "").strip()
    if value:
        return Path(value)
    parent = timing_output.parent
    root = parent.parent if parent.name == "timing" else parent
    return root / "run-events.jsonl"


def _phase_from_document(output: Path, phase_id: str) -> dict[str, Any]:
    document = load_json(output)
    phase = next((item for item in document.get("phases", []) if item.get("id") == phase_id), None)
    if not isinstance(phase, dict):
        raise TimingError(f"Phase is missing after timing update: {phase_id}")
    return phase


def main() -> int:
    parser = argparse.ArgumentParser(description="Structured Fast CI timing and unified live run events")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("initialize")
    for name in ("output", "repository", "event-name", "ref", "tested-commit-sha", "run-id", "run-attempt"):
        init.add_argument(
            f"--{name}",
            required=True,
            type=Path if name == "output" else int if name in {"run-id", "run-attempt"} else str,
        )
    init.add_argument("--events-output", type=Path)
    for command in ("start", "finish"):
        sub = commands.add_parser(command)
        sub.add_argument("--output", required=True, type=Path)
        sub.add_argument("--events-output", type=Path)
        sub.add_argument("--phase-id", required=True, choices=sorted(PHASES))
        if command == "finish":
            sub.add_argument("--exit-code", required=True, type=int)
            sub.add_argument("--status", choices=sorted(PHASE_STATUSES))
    final = commands.add_parser("finalize")
    final.add_argument("--output", required=True, type=Path)
    final.add_argument("--events-output", type=Path)
    final.add_argument("--result", required=True, choices=sorted(FINAL_RESULTS))
    final.add_argument("--markdown-output", type=Path)
    final.add_argument("--summary-output", type=Path)
    check = commands.add_parser("validate")
    check.add_argument("--output", required=True, type=Path)
    check.add_argument("--events-output", type=Path)
    check.add_argument("--allow-running", action="store_true")
    render = commands.add_parser("render")
    render.add_argument("--output", required=True, type=Path)
    render.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    events = _events_path(getattr(args, "events_output", None), args.output)
    try:
        if args.command == "initialize":
            initialize(args.output, args.repository, args.event_name, args.ref, args.tested_commit_sha, args.run_id, args.run_attempt)
            run_events.initialize_stream(events, "fast-ci", message="pipeline=canonical")
        elif args.command == "start":
            start_phase(args.output, args.phase_id)
            run_events.emit(events, "fast-ci", args.phase_id, "phase", "start")
        elif args.command == "finish":
            finish_phase(args.output, args.phase_id, args.exit_code, args.status)
            phase = _phase_from_document(args.output, args.phase_id)
            status = {"success": "pass", "failure": "fail", "skipped": "skip"}[phase["status"]]
            run_events.emit(events, "fast-ci", args.phase_id, "phase", status, duration_ms=int(phase["durationMs"]))
        elif args.command == "finalize":
            before = validate(load_json(args.output), allow_running=True)
            running = {item["id"] for item in before["phases"] if item["status"] == "running"}
            document = finalize(args.output, args.result, args.markdown_output, args.summary_output)
            for phase in document["phases"]:
                if phase["id"] in running:
                    run_events.emit(
                        events,
                        "fast-ci",
                        phase["id"],
                        "phase",
                        "fail",
                        duration_ms=int(phase["durationMs"]),
                        message="phase ended during finalization",
                    )
            status = {"success": "pass", "failure": "fail", "cancelled": "cancel"}[document["result"]]
            run_events.finish_run(events, "fast-ci", status, duration_ms=int(document["durationMs"]))
        elif args.command == "validate":
            validate(load_json(args.output), allow_running=args.allow_running)
            run_events.validate_stream(events, expected_producer="fast-ci", require_final=not args.allow_running)
        else:
            atomic_write(args.markdown_output, render_markdown(load_json(args.output)))
        return 0
    except (TimingError, run_events.RunEventError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
