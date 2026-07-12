from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from typing import Iterable


SCHEMA_VERSION = 2
ALLOWED_MODES = {"standard", "strict-apkg", "perf100"}
ALLOWED_SCOPES = {"full", "global", "stats", "decks", "activity", "cards", "settings"}
ALLOWED_TOP_LEVEL = {
    "artifact-manifest.json",
    "runtime",
    "diagnostics",
    "reports",
    "html",
    "package",
    "screenshots",
}
TEXT_SUFFIXES = {".json", ".jsonl", ".txt", ".log", ".md", ".html", ".htm", ".xml"}
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[ousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:OPENSSH |RSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
)
TOKEN_QUERY = re.compile(
    r"(?:[?&]|&amp;)token=(?:<redacted-token>|\[REDACTED\]|[^&\s\"'<>]+)",
    re.IGNORECASE,
)
WINDOWS_PRIVATE_PATH = re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\\/\s\"'<>]+")
LINUX_PRIVATE_PATH = re.compile(r"/home/(?!e2e(?:/|$))[^/\s\"'<>]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"Unsafe artifact path: {value}")
    return normalized


def manifest_paths(manifest: dict) -> list[str]:
    paths: list[str] = []
    for value in (manifest.get("runtime") or {}).values():
        if isinstance(value, str) and value:
            paths.append(value)
    for values in (manifest.get("artifacts") or {}).values():
        if isinstance(values, list):
            paths.extend(value for value in values if isinstance(value, str) and value)
    for entry in manifest.get("screenshots") or []:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    return paths


def validate_manifest(source: Path, manifest: dict) -> list[str]:
    paths = [safe_relative_path(value) for value in manifest_paths(manifest)]
    if len(paths) != len(set(paths)):
        raise ValueError("Artifact manifest contains duplicate paths")
    for relative in paths:
        if not (source / relative).is_file():
            raise ValueError(f"Artifact manifest references a missing file: {relative}")
    return paths


def redact_text(text: str, *, known_tokens: Iterable[str], private_roots: Iterable[str]) -> str:
    redacted = TOKEN_QUERY.sub("", text)
    for token in known_tokens:
        if token:
            redacted = redacted.replace(token, "[REDACTED]")
    for root in private_roots:
        if not root:
            continue
        variants = {root, root.replace("\\", "/"), root.replace("/", "\\")}
        for variant in variants:
            redacted = redacted.replace(variant, "[WORKSPACE]")
    return redacted


def redact_json(value, *, known_tokens: Iterable[str], private_roots: Iterable[str]):
    if isinstance(value, str):
        return redact_text(value, known_tokens=known_tokens, private_roots=private_roots)
    if isinstance(value, list):
        return [redact_json(item, known_tokens=known_tokens, private_roots=private_roots) for item in value]
    if isinstance(value, dict):
        return {
            key: redact_json(item, known_tokens=known_tokens, private_roots=private_roots)
            for key, item in value.items()
        }
    return value


def assert_safe_text(text: str, relative_path: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Secret-like content remains in {relative_path}")
    if TOKEN_QUERY.search(text):
        raise ValueError(f"Token-bearing URL remains in {relative_path}")
    if WINDOWS_PRIVATE_PATH.search(text) or LINUX_PRIVATE_PATH.search(text):
        raise ValueError(f"Private absolute path remains in {relative_path}")


def read_readiness(source: Path) -> tuple[dict | None, list[str]]:
    path = source / "runtime" / "dashboard-ready.json"
    if not path.is_file():
        return None, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    tokens = [str(payload.get("token") or "")]
    payload.pop("token", None)
    for key, value in list(payload.items()):
        if isinstance(value, str):
            payload[key] = TOKEN_QUERY.sub("", value)
    payload["redacted"] = True
    return payload, tokens


def copy_safe_artifacts(source: Path, destination: Path, private_roots: Iterable[str]) -> tuple[str, list[str]]:
    manifest_status = "missing"
    manifest: dict | None = None
    manifest_path = source / "artifact-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_manifest(source, manifest)
        manifest_status = str(manifest.get("status") or "unknown")

    readiness, known_tokens = read_readiness(source)
    copied: list[str] = []
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            top = relative.split("/", 1)[0]
            if top not in ALLOWED_TOP_LEVEL or relative == "runtime/dashboard-ready.json":
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in TEXT_SUFFIXES or path.name == "artifact-manifest.json":
                text = path.read_text(encoding="utf-8")
                if path.suffix.lower() == ".json" or relative == "artifact-manifest.json":
                    data = json.loads(text)
                    if relative == "artifact-manifest.json":
                        runtime = data.get("runtime") or {}
                        if runtime.get("dashboardReady"):
                            runtime["dashboardReady"] = "runtime/dashboard-ready.redacted.json"
                    data = redact_json(data, known_tokens=known_tokens, private_roots=private_roots)
                    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                else:
                    text = redact_text(text, known_tokens=known_tokens, private_roots=private_roots)
                assert_safe_text(text, relative)
                target.write_text(text, encoding="utf-8")
            else:
                shutil.copyfile(path, target)
            copied.append(f"artifacts/{relative}")

    if readiness is not None:
        relative = "runtime/dashboard-ready.redacted.json"
        text = json.dumps(readiness, ensure_ascii=False, indent=2) + "\n"
        assert_safe_text(text, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        copied.append(f"artifacts/{relative}")
    return manifest_status, copied


def command_version(arguments: list[str]) -> str:
    try:
        result = subprocess.run(arguments, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return (result.stdout or result.stderr).strip().splitlines()[0]


def write_summary(output: Path, *, args: argparse.Namespace, manifest_status: str, artifact_files: list[str]) -> None:
    finished_at = utc_now()
    started_at = args.started_at or finished_at
    try:
        duration = max(0, int((datetime.fromisoformat(finished_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds()))
    except ValueError:
        duration = 0
    success = args.e2e_exit_code == 0
    direct_baseline_comparison = args.mode == "standard" and args.scope == "full"
    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": os.environ.get("GITHUB_REPOSITORY", "AliceLiddell01/anki-study-report"),
        "commitSha": os.environ.get("GITHUB_SHA", args.commit_sha),
        "ref": os.environ.get("GITHUB_REF", args.ref),
        "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "workflow": os.environ.get("GITHUB_WORKFLOW", "Full Docker / Anki E2E"),
        "runId": os.environ.get("GITHUB_RUN_ID", "local"),
        "runAttempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "mode": args.mode,
        "scope": args.scope,
        "screenshotWorkers": args.screenshot_workers,
        "cacheState": args.cache_state,
        "dockerBuildDurationMs": args.build_duration_ms,
        "imageSizeBytes": args.image_size_bytes,
        "runnerOs": os.environ.get("RUNNER_OS", os.name),
        "runnerImage": os.environ.get("ImageOS", "local") + ":" + os.environ.get("ImageVersion", "unknown"),
        "powershellVersion": os.environ.get("CI_E2E_PWSH_VERSION", "unknown"),
        "dockerClientVersion": command_version(["docker", "version", "--format", "{{.Client.Version}}"]),
        "dockerServerVersion": command_version(["docker", "version", "--format", "{{.Server.Version}}"]),
        "dockerComposeVersion": command_version(["docker", "compose", "version", "--short"]),
        "ankiVersion": os.environ.get("ANKI_VERSION", "26.05"),
        "requireApkgFixture": args.mode in {"strict-apkg", "perf100"},
        "perf100": args.mode == "perf100",
        "result": "success" if success else "failure",
        "failureCategory": "none" if success else "unknown",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationSeconds": duration,
        "artifactManifestStatus": manifest_status,
        "artifactFiles": sorted(set(artifact_files + ["ci-e2e-summary.json", "ci-e2e-summary.md", "environment.txt"])),
    }
    phase_path = output / "artifacts" / "reports" / "e2e-phase-timings.json"
    phase_payload = read_json_file(phase_path)
    if phase_payload:
        phase_rows = phase_payload.setdefault("phases", [])
        existing_names = {item.get("name") for item in phase_rows}
        external = [
            ("runner inspection", None, "duration unavailable before summary preparation"),
            ("Buildx setup", None, "duration available from GitHub job metadata, not container telemetry"),
            ("Docker cache restore/build/load", args.build_duration_ms, "measured around docker/build-push-action with load=true"),
            ("artifact upload", None, "measured after upload and reported in GitHub Step Summary"),
            ("total workflow", duration * 1000, "from runner preflight start through public artifact preparation"),
        ]
        for name, duration_ms, notes in external:
            if name not in existing_names:
                phase_rows.append({
                    "name": name,
                    "startedAt": None,
                    "finishedAt": None,
                    "durationMs": duration_ms,
                    "status": "success" if success else "unknown",
                    "scope": args.scope,
                    "mode": args.mode,
                    "cacheState": args.cache_state if "Docker" in name else None,
                    "notes": notes,
                })
        phase_payload["slowest"] = sorted(
            [item for item in phase_rows if isinstance(item.get("durationMs"), (int, float))],
            key=lambda item: item["durationMs"], reverse=True,
        )[:10]
        write_json_file(phase_path, phase_payload)
        (phase_path.with_suffix(".md")).write_text(
            "# E2E phase timings\n\n| Phase | Duration ms | Status | Notes |\n| --- | ---: | --- | --- |\n" +
            "".join(f"| {item['name']} | {item.get('durationMs') if item.get('durationMs') is not None else 'n/a'} | {item.get('status', 'unknown')} | {item.get('notes') or ''} |\n" for item in phase_rows),
            encoding="utf-8",
        )
    performance_path = output / "artifacts" / "reports" / "e2e-performance-summary.json"
    performance = read_json_file(performance_path)
    if performance:
        exported_root = output / "artifacts"
        exported_files = [path for path in exported_root.rglob("*") if path.is_file()]
        file_rows = [
            {"path": path.relative_to(exported_root).as_posix(), "bytes": path.stat().st_size}
            for path in exported_files
        ]
        composition = {
            "fileCount": len(file_rows),
            "totalBytes": sum(item["bytes"] for item in file_rows),
            "pngBytes": sum(item["bytes"] for item in file_rows if item["path"].lower().endswith(".png")),
            "jsonLogBytes": sum(item["bytes"] for item in file_rows if Path(item["path"]).suffix.lower() in {".json", ".jsonl", ".log", ".txt", ".md"}),
            "largestFiles": sorted(file_rows, key=lambda item: item["bytes"], reverse=True)[:20],
            "uploadDurationMs": None,
            "uploadDurationReason": "reported after upload in GitHub Step Summary",
        }
        exported_manifest = read_json_file(exported_root / "artifact-manifest.json")
        screenshot_count = len(exported_manifest.get("screenshots") or [])
        current = performance.setdefault("current", {})
        current.update({
            "runId": summary["runId"],
            "commitSha": summary["commitSha"],
            "mode": args.mode,
            "scope": args.scope,
            "workerCount": args.screenshot_workers,
            "canonicalDurationSeconds": duration,
            "cacheState": args.cache_state,
            "screenshotCount": screenshot_count,
            "artifactFileCount": composition["fileCount"],
            "artifactBytes": composition["totalBytes"],
        })
        cache = performance.setdefault("cache", {})
        cache.update({"backend": "type=gha", "state": args.cache_state, "buildDurationMs": args.build_duration_ms, "imageSizeBytes": args.image_size_bytes})
        baseline_seconds = int((performance.get("baseline") or {}).get("canonicalDurationSeconds") or 183)
        improvement = performance.setdefault("improvement", {})
        if direct_baseline_comparison:
            improvement.update({
                "canonicalSavedSeconds": baseline_seconds - duration,
                "canonicalReductionPercent": (baseline_seconds - duration) * 100 / baseline_seconds,
                "canonicalSpeedupFactor": baseline_seconds / duration if duration else None,
                "comparisonReason": None,
            })
        else:
            improvement.update({
                "canonicalSavedSeconds": None,
                "canonicalReductionPercent": None,
                "canonicalSpeedupFactor": None,
                "comparisonReason": "targeted or non-standard run is not an apples-to-apples comparison with the full standard baseline",
            })
        performance["artifacts"] = composition
        write_json_file(performance_path, performance)
    (output / "ci-e2e-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    saved_display = str(183 - summary["durationSeconds"]) + " seconds" if direct_baseline_comparison else "n/a (targeted/non-standard is not apples-to-apples)"
    markdown = f"""# Full Docker / Anki E2E summary

| Field | Value |
| --- | --- |
| Result | {summary['result']} |
| Failure category | {summary['failureCategory']} |
| Commit | `{summary['commitSha']}` |
| Ref | `{summary['ref']}` |
| Mode | {summary['mode']} |
| Scope | {summary['scope']} |
| Screenshot workers | {summary['screenshotWorkers']} |
| Build cache | {summary['cacheState']} (`type=gha`) |
| Runner | {summary['runnerOs']} / {summary['runnerImage']} |
| Anki | {summary['ankiVersion']} |
| Manifest | {summary['artifactManifestStatus']} |
| Duration | {summary['durationSeconds']} seconds |
| Baseline canonical | 183 seconds (run 29208090406) |
| Saved vs baseline | {saved_display} |
| Docker build/load | {summary['dockerBuildDurationMs']} ms |
| Image size | {summary['imageSizeBytes']} bytes |

Raw dashboard readiness data is not uploaded. The safe export contains
`artifacts/runtime/dashboard-ready.redacted.json` when readiness was available.
Perf100 measurements are diagnostics, not release thresholds.
"""
    (output / "ci-e2e-summary.md").write_text(markdown, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with Path(step_summary).open("a", encoding="utf-8") as handle:
            handle.write(markdown)

    environment = {
        key: summary[key]
        for key in (
            "repository", "commitSha", "ref", "event", "workflow", "runId", "runAttempt",
            "mode", "scope", "screenshotWorkers", "cacheState", "runnerOs", "runnerImage", "powershellVersion", "dockerClientVersion",
            "dockerServerVersion", "dockerComposeVersion", "ankiVersion",
        )
    }
    (output / "environment.txt").write_text("".join(f"{key}={value}\n" for key, value in environment.items()), encoding="utf-8")


def copy_log(source: Path, target: Path, *, private_roots: Iterable[str], known_tokens: Iterable[str]) -> str | None:
    if not source.is_file():
        return None
    text = source.read_text(encoding="utf-8", errors="replace")
    text = redact_text(text, known_tokens=known_tokens, private_roots=private_roots)
    assert_safe_text(text, target.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target.as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("e2e-artifacts"))
    parser.add_argument("--output", type=Path, default=Path("ci-e2e"))
    parser.add_argument("--raw-logs", type=Path, default=Path("ci-e2e-raw"))
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), required=True)
    parser.add_argument("--scope", choices=sorted(ALLOWED_SCOPES), default="full")
    parser.add_argument("--screenshot-workers", type=int, default=3)
    parser.add_argument("--build-duration-ms", type=int, default=0)
    parser.add_argument("--image-size-bytes", type=int, default=0)
    parser.add_argument("--cache-state", default="unknown")
    parser.add_argument("--e2e-exit-code", type=int, required=True)
    parser.add_argument("--started-at", default="")
    parser.add_argument("--commit-sha", default="unknown")
    parser.add_argument("--ref", default="local")
    return parser.parse_args()


def read_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json_file(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "logs").mkdir(parents=True)
    artifact_destination = output / "artifacts"
    artifact_destination.mkdir(parents=True)
    private_roots = [str(Path.cwd().resolve()), os.environ.get("GITHUB_WORKSPACE", "")]
    manifest_status, copied = copy_safe_artifacts(args.source.resolve(), artifact_destination, private_roots)
    _, known_tokens = read_readiness(args.source.resolve())
    log_map = {
        "docker-compose-config.txt": args.raw_logs / "docker-compose-config.txt",
        "docker-build-and-e2e.log": args.raw_logs / "e2e-run.log",
        "docker-system.txt": args.raw_logs / "docker-system.txt",
    }
    for name, source in log_map.items():
        relative = f"logs/{name}"
        if copy_log(source, output / relative, private_roots=private_roots, known_tokens=known_tokens):
            copied.append(relative)
    write_summary(output, args=args, manifest_status=manifest_status, artifact_files=copied)
    for path in output.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            assert_safe_text(path.read_text(encoding="utf-8"), path.relative_to(output).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
