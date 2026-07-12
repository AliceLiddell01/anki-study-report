#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import time
from typing import Any


BASELINE = {
    "runId": "29208090406",
    "commitSha": "cd68c2ca827023477422575d8421074d960fd4a7",
    "canonicalDurationSeconds": 183,
    "workflowUiDurationApproxSeconds": 202,
    "source": "existing Stage 6.5 artifact",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * p / 100) - 1)]


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_phase(args: argparse.Namespace) -> None:
    path = args.root / "reports" / "e2e-phase-timings.json"
    payload = read_json(path, {"schemaVersion": 1, "phases": []})
    payload["phases"].append({
        "name": args.name,
        "startedAt": args.started_at,
        "finishedAt": args.finished_at,
        "durationMs": args.duration_ms,
        "status": args.status,
        "scope": args.scope,
        "mode": args.mode,
        "cacheState": args.cache_state or None,
        "notes": args.notes or None,
    })
    write_json(path, payload)


def _read_int(path: str) -> int | None:
    try:
        return int(Path(path).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _memory() -> tuple[int | None, int | None]:
    current = _read_int("/sys/fs/cgroup/memory.current")
    limit_text = ""
    try:
        limit_text = Path("/sys/fs/cgroup/memory.max").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    limit = int(limit_text) if limit_text.isdigit() else _meminfo().get("MemTotal")
    return current, limit


def _meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            value = raw.strip().split()[0]
            result[key] = int(value) * 1024
    except (OSError, ValueError, IndexError):
        return {}
    return result


def _network_bytes() -> tuple[int | None, int | None]:
    rx = tx = 0
    found = False
    try:
        for line in Path("/proc/net/dev").read_text(encoding="utf-8").splitlines()[2:]:
            interface, counters = line.split(":", 1)
            if interface.strip() == "lo":
                continue
            values = counters.split()
            rx += int(values[0])
            tx += int(values[8])
            found = True
    except (OSError, ValueError, IndexError):
        return None, None
    return (rx, tx) if found else (None, None)


def _cpu_usage_usec() -> int | None:
    try:
        for line in Path("/sys/fs/cgroup/cpu.stat").read_text(encoding="utf-8").splitlines():
            if line.startswith("usage_usec "):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def _io_bytes() -> tuple[int | None, int | None]:
    read_bytes = write_bytes = 0
    found = False
    try:
        for line in Path("/sys/fs/cgroup/io.stat").read_text(encoding="utf-8").splitlines():
            fields = dict(item.split("=", 1) for item in line.split()[1:] if "=" in item)
            read_bytes += int(fields.get("rbytes", 0))
            write_bytes += int(fields.get("wbytes", 0))
            found = True
    except (OSError, ValueError):
        return None, None
    return (read_bytes, write_bytes) if found else (None, None)


def sample_resources(args: argparse.Namespace) -> None:
    output = args.root / "reports" / "resource-samples.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    previous_cpu = None
    previous_time = time.monotonic()
    with output.open("w", encoding="utf-8") as handle:
        while not args.stop_file.exists():
            now = time.monotonic()
            cpu = _cpu_usage_usec()
            elapsed = now - previous_time
            cpu_percent = None if cpu is None or previous_cpu is None or elapsed <= 0 else (cpu - previous_cpu) / (elapsed * 10_000)
            memory, memory_limit = _memory()
            meminfo = _meminfo()
            block_read, block_write = _io_bytes()
            network_rx, network_tx = _network_bytes()
            disk = shutil.disk_usage(args.root)
            try:
                load_average = os.getloadavg()
            except OSError:
                load_average = (None, None, None)
            sample = {
                "timestamp": utc_now(),
                "container": os.environ.get("HOSTNAME", "anki-e2e"),
                "cpuPercent": cpu_percent,
                "memoryUsageBytes": memory,
                "memoryLimitBytes": memory_limit,
                "memoryPercent": None if memory is None or not memory_limit else memory * 100 / memory_limit,
                "pids": _read_int("/sys/fs/cgroup/pids.current"),
                "blockReadBytes": block_read,
                "blockWriteBytes": block_write,
                "networkRxBytes": network_rx,
                "networkTxBytes": network_tx,
                "hostLoadAverage": list(load_average),
                "hostMemoryTotalBytes": meminfo.get("MemTotal"),
                "hostMemoryAvailableBytes": meminfo.get("MemAvailable"),
                "hostMemoryUsedBytes": None if not meminfo.get("MemTotal") or meminfo.get("MemAvailable") is None else meminfo["MemTotal"] - meminfo["MemAvailable"],
                "diskFreeBytes": disk.free,
            }
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            handle.flush()
            previous_cpu, previous_time = cpu, now
            time.sleep(max(0.2, args.interval))


def summarize_resources(root: Path, interval: float) -> dict[str, Any]:
    samples_path = root / "reports" / "resource-samples.jsonl"
    samples = []
    if samples_path.is_file():
        for line in samples_path.read_text(encoding="utf-8").splitlines():
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    cpus = [float(item["cpuPercent"]) for item in samples if item.get("cpuPercent") is not None]
    memory = [int(item["memoryUsageBytes"]) for item in samples if item.get("memoryUsageBytes") is not None]
    pids = [int(item["pids"]) for item in samples if item.get("pids") is not None]
    disk = [int(item["diskFreeBytes"]) for item in samples if item.get("diskFreeBytes") is not None]
    block_read = [int(item["blockReadBytes"]) for item in samples if item.get("blockReadBytes") is not None]
    block_write = [int(item["blockWriteBytes"]) for item in samples if item.get("blockWriteBytes") is not None]
    network_rx = [int(item["networkRxBytes"]) for item in samples if item.get("networkRxBytes") is not None]
    network_tx = [int(item["networkTxBytes"]) for item in samples if item.get("networkTxBytes") is not None]
    host_available = [int(item["hostMemoryAvailableBytes"]) for item in samples if item.get("hostMemoryAvailableBytes") is not None]
    limit = next((int(item["memoryLimitBytes"]) for item in reversed(samples) if item.get("memoryLimitBytes")), None)
    peak_memory = max(memory) if memory else None
    phases = read_json(root / "reports" / "e2e-phase-timings.json", {}).get("phases", [])
    by_phase = {}
    for phase in phases:
        start = str(phase.get("startedAt") or "")
        finish = str(phase.get("finishedAt") or "")
        selected = [item for item in samples if start and finish and start <= str(item.get("timestamp") or "") <= finish]
        phase_cpu = [float(item["cpuPercent"]) for item in selected if item.get("cpuPercent") is not None]
        phase_memory = [int(item["memoryUsageBytes"]) for item in selected if item.get("memoryUsageBytes") is not None]
        by_phase[str(phase.get("name"))] = {
            "sampleCount": len(selected),
            "averageCpuPercent": statistics.fmean(phase_cpu) if phase_cpu else None,
            "peakCpuPercent": max(phase_cpu) if phase_cpu else None,
            "averageMemoryBytes": statistics.fmean(phase_memory) if phase_memory else None,
            "peakMemoryBytes": max(phase_memory) if phase_memory else None,
        }
    summary = {
        "schemaVersion": 1,
        "sampleIntervalSeconds": interval,
        "sampleCount": len(samples),
        "averageCpuPercent": statistics.fmean(cpus) if cpus else None,
        "medianCpuPercent": statistics.median(cpus) if cpus else None,
        "p95CpuPercent": percentile(cpus, 95),
        "peakCpuPercent": max(cpus) if cpus else None,
        "averageMemoryBytes": statistics.fmean(memory) if memory else None,
        "p95MemoryBytes": percentile(memory, 95),
        "peakMemoryBytes": peak_memory,
        "memoryLimitBytes": limit,
        "memoryHeadroomBytes": min(host_available) if host_available else (None if limit is None or peak_memory is None else limit - peak_memory),
        "peakPids": max(pids) if pids else None,
        "diskUsedDeltaBytes": None if len(disk) < 2 else disk[0] - disk[-1],
        "blockReadDeltaBytes": None if len(block_read) < 2 else block_read[-1] - block_read[0],
        "blockWriteDeltaBytes": None if len(block_write) < 2 else block_write[-1] - block_write[0],
        "networkRxBytes": None if len(network_rx) < 2 else network_rx[-1] - network_rx[0],
        "networkRxReason": None if len(network_rx) >= 2 else "network counters are unavailable in the lightweight sampler",
        "networkTxBytes": None if len(network_tx) < 2 else network_tx[-1] - network_tx[0],
        "networkTxReason": None if len(network_tx) >= 2 else "network counters are unavailable in the lightweight sampler",
        "cpuSaturationSampleCount": sum(1 for value in cpus if value >= 390),
        "byPhase": by_phase,
        "cpuInterpretation": "Docker/container CPU may exceed 100%; 400% approximately saturates a 4-vCPU runner.",
    }
    write_json(root / "reports" / "resource-summary.json", summary)
    return summary


def artifact_composition(root: Path) -> dict[str, Any]:
    files = [path for path in root.rglob("*") if path.is_file()]
    rows = [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size} for path in files]
    return {
        "fileCount": len(rows),
        "totalBytes": sum(row["bytes"] for row in rows),
        "pngBytes": sum(row["bytes"] for row in rows if row["path"].lower().endswith(".png")),
        "jsonLogBytes": sum(row["bytes"] for row in rows if Path(row["path"]).suffix.lower() in {".json", ".jsonl", ".log", ".txt", ".md"}),
        "largestFiles": sorted(rows, key=lambda row: row["bytes"], reverse=True)[:20],
        "uploadDurationMs": None,
        "uploadDurationReason": "available only from GitHub Actions step metadata after artifact creation",
    }


def markdown_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def finalize(args: argparse.Namespace) -> None:
    reports = args.root / "reports"
    phases = read_json(reports / "e2e-phase-timings.json", {"schemaVersion": 1, "phases": []})
    phase_rows = phases.get("phases", [])
    phase_rows.sort(key=lambda item: item.get("startedAt", ""))
    phases["slowest"] = sorted(phase_rows, key=lambda item: item.get("durationMs", 0), reverse=True)[:10]
    phases["totalRecordedMs"] = sum(item.get("durationMs", 0) for item in phase_rows)
    write_json(reports / "e2e-phase-timings.json", phases)
    (reports / "e2e-phase-timings.md").write_text(
        "# E2E phase timings\n\n| Phase | Duration ms | Status |\n| --- | ---: | --- |\n" +
        "".join(f"| {item['name']} | {item['durationMs']} | {item['status']} |\n" for item in phase_rows), encoding="utf-8")

    resources = summarize_resources(args.root, args.interval) if args.resource_telemetry else None
    if resources is not None:
        (reports / "resource-summary.md").write_text(
            "# E2E resource summary\n\n| Metric | Value |\n| --- | ---: |\n" +
            "".join(f"| {key} | {markdown_value(value)} |\n" for key, value in resources.items() if not isinstance(value, (dict, list))), encoding="utf-8")

    screenshot = read_json(reports / "screenshot-performance.json", {})
    artifacts = artifact_composition(args.root)
    canonical_ms = sum(item.get("durationMs", 0) for item in phase_rows if item.get("name") == "total canonical E2E") or None
    current_seconds = None if canonical_ms is None else canonical_ms / 1000
    direct_comparison = args.mode == "standard" and args.scope == "full"
    saved = None if current_seconds is None or not direct_comparison else BASELINE["canonicalDurationSeconds"] - current_seconds
    performance = {
        "schemaVersion": 1,
        "baseline": BASELINE,
        "current": {
            "runId": os.environ.get("GITHUB_RUN_ID", "local"),
            "commitSha": os.environ.get("GITHUB_SHA", "local"),
            "mode": args.mode,
            "scope": args.scope,
            "workerCount": args.workers,
            "canonicalDurationSeconds": current_seconds,
            "workflowDurationSeconds": None,
            "workflowDurationReason": "computed by GitHub Actions outside the container",
            "cacheState": os.environ.get("ANKI_E2E_CACHE_STATE", "unknown"),
            "screenshotCount": screenshot.get("successfulTasks"),
            "artifactFileCount": artifacts["fileCount"],
            "artifactBytes": artifacts["totalBytes"],
        },
        "improvement": {
            "canonicalSavedSeconds": saved,
            "canonicalReductionPercent": None if saved is None else saved * 100 / BASELINE["canonicalDurationSeconds"],
            "canonicalSpeedupFactor": None if current_seconds in {None, 0} else BASELINE["canonicalDurationSeconds"] / current_seconds,
            "workflowSavedSeconds": None,
            "workflowReductionPercent": None,
            "workflowReason": "workflow duration is added from GitHub run metadata",
            "comparisonReason": None if direct_comparison else "targeted/non-standard run is not apples-to-apples with the full standard baseline",
        },
        "phases": {"slowest": phases.get("slowest", []), "criticalPath": [item["name"] for item in phase_rows]},
        "parallel": screenshot or None,
        "resources": resources,
        "cache": {"backend": os.environ.get("ANKI_E2E_CACHE_BACKEND", "local"), "state": os.environ.get("ANKI_E2E_CACHE_STATE", "unknown"), "buildDurationMs": None, "imageSizeBytes": None},
        "artifacts": artifacts,
    }
    write_json(reports / "e2e-performance-summary.json", performance)
    (reports / "e2e-performance-summary.md").write_text(
        "# E2E performance summary\n\n"
        f"Baseline: {BASELINE['canonicalDurationSeconds']} s from run {BASELINE['runId']}.\n\n"
        f"Mode/scope: `{args.mode}` / `{args.scope}`; workers: {args.workers}.\n\n"
        f"Canonical duration: {markdown_value(current_seconds)} s; saved: {markdown_value(saved)} s.\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    phase = sub.add_parser("record-phase")
    phase.add_argument("--root", type=Path, required=True)
    phase.add_argument("--name", required=True)
    phase.add_argument("--started-at", required=True)
    phase.add_argument("--finished-at", required=True)
    phase.add_argument("--duration-ms", type=int, required=True)
    phase.add_argument("--status", default="success")
    phase.add_argument("--scope", required=True)
    phase.add_argument("--mode", required=True)
    phase.add_argument("--cache-state", default="")
    phase.add_argument("--notes", default="")
    sampler = sub.add_parser("sample-resources")
    sampler.add_argument("--root", type=Path, required=True)
    sampler.add_argument("--stop-file", type=Path, required=True)
    sampler.add_argument("--interval", type=float, default=1.0)
    finish = sub.add_parser("finalize")
    finish.add_argument("--root", type=Path, required=True)
    finish.add_argument("--scope", required=True)
    finish.add_argument("--mode", required=True)
    finish.add_argument("--workers", type=int, required=True)
    finish.add_argument("--interval", type=float, default=1.0)
    finish.add_argument("--resource-telemetry", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "record-phase":
        record_phase(args)
    elif args.command == "sample-resources":
        sample_resources(args)
    else:
        finalize(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
