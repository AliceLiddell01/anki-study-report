from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from ci_e2e_artifact_common import (
    ALLOWED_MODES, ALLOWED_PACKAGE_SOURCES, ALLOWED_SCOPES, PRODUCT_PHASES,
    SCHEMA_VERSION, SHA256_RE, SHA_RE, TEXT_SUFFIXES, _optional_hash,
    _optional_positive, _phase_observations, assert_safe_text, command_version,
    copy_safe_artifacts, read_json_file, read_readiness, utc_now, validate_manifest, write_json_file,
)

def write_summary(output: Path, *, args: argparse.Namespace, manifest_status: str, artifact_files: list[str]) -> None:
    finished_at = utc_now()
    started_at = args.started_at or finished_at
    try:
        duration = max(0, int((datetime.fromisoformat(finished_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds()))
    except ValueError:
        duration = 0
    success = args.e2e_exit_code == 0
    direct_baseline_comparison = args.mode == "standard" and args.scope == "full"
    package_source = args.package_source or "source-build"
    if package_source not in ALLOWED_PACKAGE_SOURCES:
        raise ValueError(f"Unsupported package source: {package_source}")
    source_fast_run_id = _optional_positive(args.source_fast_ci_run_id)
    source_fast_tested_sha = _optional_hash(args.source_fast_ci_tested_sha, SHA_RE, "source-fast-ci-tested-sha")
    source_package_sha256 = _optional_hash(args.source_package_sha256, SHA256_RE, "source-package-sha256")
    e2e_checkout_sha = _optional_hash(args.e2e_checkout_sha, SHA_RE, "e2e-checkout-sha") or args.commit_sha
    if package_source == "fast-ci-artifact":
        if source_fast_run_id is None or source_fast_tested_sha is None or source_package_sha256 is None:
            raise ValueError("fast-ci-artifact summary requires run ID, tested SHA, and package SHA-256")
        if e2e_checkout_sha != source_fast_tested_sha:
            raise ValueError("Fast CI tested SHA must equal E2E checkout SHA")
    else:
        source_fast_run_id = None
        source_fast_tested_sha = None
        source_package_sha256 = None

    phase_path = output / "artifacts" / "reports" / "e2e-phase-timings.json"
    phase_payload = read_json_file(phase_path)
    product_phases = _phase_observations(phase_payload)
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
        "packageSource": package_source,
        "sourceFastCiRunId": source_fast_run_id,
        "sourceFastCiTestedSha": source_fast_tested_sha,
        "sourcePackageSha256": source_package_sha256,
        "e2eCheckoutSha": e2e_checkout_sha,
        "productBuildPhases": product_phases,
        "result": "success" if success else "failure",
        "failureCategory": "none" if success else "unknown",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationSeconds": duration,
        "workflowDurationSeconds": duration,
        "canonicalDurationSeconds": None,
        "artifactManifestStatus": manifest_status,
        "artifactFiles": sorted(set(artifact_files + ["ci-e2e-summary.json", "ci-e2e-summary.md", "environment.txt"])),
    }

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
            "workflowDurationSeconds": duration,
            "cacheState": args.cache_state,
            "screenshotCount": screenshot_count,
            "artifactFileCount": composition["fileCount"],
            "artifactBytes": composition["totalBytes"],
            "packageSource": package_source,
            "sourceFastCiRunId": source_fast_run_id,
            "sourceFastCiTestedSha": source_fast_tested_sha,
            "sourcePackageSha256": source_package_sha256,
            "e2eCheckoutSha": e2e_checkout_sha,
            "productBuildPhases": product_phases,
        })
        cache = performance.setdefault("cache", {})
        cache.update({"backend": "type=gha", "state": args.cache_state, "buildDurationMs": args.build_duration_ms, "imageSizeBytes": args.image_size_bytes})
        baseline_seconds = int((performance.get("baseline") or {}).get("canonicalDurationSeconds") or 183)
        canonical_seconds = current.get("canonicalDurationSeconds")
        improvement = performance.setdefault("improvement", {})
        if direct_baseline_comparison and isinstance(canonical_seconds, (int, float)):
            improvement.update({
                "canonicalSavedSeconds": baseline_seconds - canonical_seconds,
                "canonicalReductionPercent": (baseline_seconds - canonical_seconds) * 100 / baseline_seconds,
                "canonicalSpeedupFactor": baseline_seconds / canonical_seconds if canonical_seconds else None,
                "comparisonReason": None,
            })
        else:
            improvement.update({
                "canonicalSavedSeconds": None,
                "canonicalReductionPercent": None,
                "canonicalSpeedupFactor": None,
                "comparisonReason": (
                    "canonical duration is unavailable"
                    if direct_baseline_comparison
                    else "targeted or non-standard run is not an apples-to-apples comparison with the full standard baseline"
                ),
            })
        summary["canonicalDurationSeconds"] = canonical_seconds
        summary["workflowDurationSeconds"] = duration
        performance["artifacts"] = composition
        write_json_file(performance_path, performance)
    (output / "ci-e2e-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    canonical_duration = summary.get("canonicalDurationSeconds")
    saved_display = (
        f"{183 - canonical_duration:g} seconds"
        if direct_baseline_comparison and isinstance(canonical_duration, (int, float))
        else "n/a"
    )
    markdown = f"""# Full Docker / Anki E2E summary

| Field | Value |
| --- | --- |
| Result | {summary['result']} |
| Failure category | {summary['failureCategory']} |
| Commit | `{summary['commitSha']}` |
| Ref | `{summary['ref']}` |
| E2E checkout | `{summary['e2eCheckoutSha']}` |
| Package source | {summary['packageSource']} |
| Fast CI source run | {summary['sourceFastCiRunId'] if summary['sourceFastCiRunId'] is not None else 'n/a'} |
| Mode | {summary['mode']} |
| Scope | {summary['scope']} |
| Screenshot workers | {summary['screenshotWorkers']} |
| Build cache | {summary['cacheState']} (`type=gha`) |
| Runner | {summary['runnerOs']} / {summary['runnerImage']} |
| Anki | {summary['ankiVersion']} |
| Manifest | {summary['artifactManifestStatus']} |
| Workflow duration | {summary['workflowDurationSeconds']} seconds |
| Canonical E2E duration | {canonical_duration if canonical_duration is not None else 'n/a'} seconds |
| Baseline canonical | 183 seconds (run 29208090406) |
| Saved vs canonical baseline | {saved_display} |
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
            "dockerServerVersion", "dockerComposeVersion", "ankiVersion", "packageSource", "sourceFastCiRunId",
            "sourceFastCiTestedSha", "sourcePackageSha256", "e2eCheckoutSha",
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
    parser.add_argument("--package-source", default="source-build")
    parser.add_argument("--source-fast-ci-run-id", default="")
    parser.add_argument("--source-fast-ci-tested-sha", default="")
    parser.add_argument("--source-package-sha256", default="")
    parser.add_argument("--e2e-checkout-sha", default="")
    return parser.parse_args()


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
