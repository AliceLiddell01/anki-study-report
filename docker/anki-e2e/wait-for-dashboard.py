#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from artifact_paths import ArtifactPaths


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for Anki Study Report dashboard readiness.")
    parser.add_argument("--label", default="run")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    paths = ArtifactPaths.from_env()
    paths.ensure()
    ready_file = Path(os.environ.get("ANKI_STUDY_REPORT_E2E_READY_FILE", str(paths.runtime / "dashboard-ready.json")))
    pid_file = paths.runtime / "anki.pid"
    deadline = time.monotonic() + args.timeout
    last_error = ""

    while time.monotonic() < deadline:
        if pid_file.is_file() and not process_alive(pid_file):
            print("Anki process exited before dashboard became ready.", file=sys.stderr)
            write_failure_artifacts(paths, args.label)
            print_readiness_diagnostics(paths, ready_file, args.label)
            print_log_tails(paths, args.label)
            return 1

        if ready_file.is_file():
            try:
                ready = json.loads(ready_file.read_text(encoding="utf-8"))
                health = fetch_json(
                    f"{ready['baseUrl']}/api/health?{urlencode({'token': ready['token']})}"
                )
                if health.get("ok") and health.get("hasReport"):
                    (paths.reports / f"api-health-{args.label}.json").write_text(
                        json.dumps(health, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    if has_traceback(paths, args.label):
                        print("Traceback found in Anki logs after readiness.", file=sys.stderr)
                        print_log_tails(paths, args.label)
                        return 1
                    print(f"Dashboard ready: {ready['baseUrl']}")
                    return 0
                last_error = f"health not ready: {health}"
            except Exception as exc:
                last_error = str(exc)
        time.sleep(1)

    print(f"Timed out waiting for dashboard readiness. Last error: {last_error}", file=sys.stderr)
    write_failure_artifacts(paths, args.label)
    print_readiness_diagnostics(paths, ready_file, args.label)
    print_log_tails(paths, args.label)
    return 1


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "anki-study-report-e2e"})
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def process_alive(pid_file: Path) -> bool:
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        return True
    return Path(f"/proc/{pid}").exists()


def has_traceback(paths: ArtifactPaths, label: str) -> bool:
    candidates = [
        paths.diagnostics / f"anki-stderr-{label}.log",
        paths.diagnostics / f"anki-stdout-{label}.log",
        paths.diagnostics / "anki_study_report.log",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Traceback (most recent call last)" in text:
            return True
    return False


def write_failure_artifacts(paths: ArtifactPaths, label: str) -> None:
    anki_base = Path(os.environ.get("ANKI_BASE", "/e2e/anki-data"))
    anki_profile = os.environ.get("ANKI_PROFILE", "E2E")
    profile_dir = Path(os.environ.get("ANKI_PROFILE_DIR", str(anki_base / anki_profile)))

    write_command_output(
        paths.diagnostics / "anki-data-tree.txt",
        f"find {shell_quote(anki_base)} -maxdepth 4 -print | sort",
    )
    write_command_output(
        paths.diagnostics / "addons-tree.txt",
        f"find {shell_quote(anki_base / 'addons21')} -maxdepth 4 -print | sort",
    )

    startup_paths = [
        paths.diagnostics / "prefs21-summary.txt",
        paths.runtime / "addon-e2e-events.jsonl",
        paths.diagnostics / f"anki-stdout-{label}.log",
        paths.diagnostics / f"anki-stderr-{label}.log",
        paths.diagnostics / "anki-study-report.log",
        paths.diagnostics / "anki_study_report.log",
        paths.diagnostics / "xvfb.log",
    ]
    lines = [
        f"ANKI_BASE={anki_base}",
        f"ANKI_PROFILE_DIR={profile_dir}",
        "",
    ]
    for path in startup_paths:
        if not path.is_file():
            continue
        lines.append(f"--- tail {path} ---")
        lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:])
        lines.append("")
    (paths.diagnostics / "anki-startup-tail.txt").write_text("\n".join(lines), encoding="utf-8")


def write_command_output(path: Path, command: str) -> None:
    result = subprocess.run(
        ["bash", "-lc", command],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    path.write_text(result.stdout, encoding="utf-8")


def shell_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


def print_readiness_diagnostics(paths: ArtifactPaths, ready_file: Path, label: str) -> None:
    print("\n--- readiness diagnostics ---", file=sys.stderr)
    print(f"dashboard-ready.json exists: {ready_file.is_file()} ({ready_file})", file=sys.stderr)

    events_file = paths.runtime / "addon-e2e-events.jsonl"
    print(f"addon-e2e-events.jsonl exists: {events_file.is_file()} ({events_file})", file=sys.stderr)
    if events_file.is_file():
        last_event = read_last_event(events_file)
        if last_event:
            print(
                f"last addon e2e stage: {last_event.get('stage')} "
                f"where={last_event.get('where', '')}",
                file=sys.stderr,
            )
        print(f"add-on import_start occurred: {event_stage_exists(events_file, 'import_start')}", file=sys.stderr)
        print(f"last 30 addon-e2e-events.jsonl lines:", file=sys.stderr)
        print_tail(events_file, 30)
    else:
        print("add-on import_start occurred: False", file=sys.stderr)

    for path in (
        paths.diagnostics / "prefs21-summary.txt",
        paths.diagnostics / "anki-study-report.log",
        paths.diagnostics / "anki_study_report.log",
        paths.diagnostics / f"anki-stdout-{label}.log",
        paths.diagnostics / f"anki-stderr-{label}.log",
    ):
        print(f"{path.name} exists: {path.is_file()} ({path})", file=sys.stderr)

    for path in (paths.diagnostics / "addons-tree.txt", paths.diagnostics / "anki-data-tree.txt"):
        if not path.is_file():
            continue
        print(f"\n--- head {path} ---", file=sys.stderr)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n".join(lines[:80]), file=sys.stderr)


def print_tail(path: Path, lines_count: int) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[-lines_count:]), file=sys.stderr)


def read_last_event(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return {"stage": "<invalid-jsonl>", "line": line[:200]}
        return value if isinstance(value, dict) else {"stage": "<non-object-jsonl>"}
    return {}


def event_stage_exists(path: Path, stage: str) -> bool:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("stage") == stage:
            return True
    return False


def print_log_tails(paths: ArtifactPaths, label: str) -> None:
    for path in (
        paths.diagnostics / "prefs21-summary.txt",
        paths.diagnostics / f"anki-stdout-{label}.log",
        paths.diagnostics / f"anki-stderr-{label}.log",
        paths.runtime / "addon-e2e-events.jsonl",
        paths.diagnostics / "anki-study-report.log",
        paths.diagnostics / "anki_study_report.log",
        paths.diagnostics / "xvfb.log",
    ):
        if not path.is_file():
            continue
        print(f"\n--- tail {path} ---", file=sys.stderr)
        print_tail(path, 80)


if __name__ == "__main__":
    raise SystemExit(main())
