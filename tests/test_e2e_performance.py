from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_telemetry():
    path = ROOT / "docker" / "anki-e2e" / "e2e-telemetry.py"
    spec = importlib.util.spec_from_file_location("asr_e2e_telemetry", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_contract(script: str) -> object:
    module_uri = (ROOT / "docker" / "anki-e2e" / "e2e-contract.mjs").as_uri()
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", f'import * as contract from {json.dumps(module_uri)};\n{script}'],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_scope_resolution_and_page_filtering():
    result = run_contract(
        """
        const cases = [
          {route:'/home', pageName:'today', heading:'Today'},
          {route:'/stats', pageName:'stats-overview', heading:'Stats'},
          {route:'/settings', pageName:'settings/report', heading:'Settings'},
        ];
        console.log(JSON.stringify({
          full: contract.buildPageCaptureTasks(cases, 'full').map(x => x.id),
          stats: contract.buildPageCaptureTasks(cases, 'stats').map(x => x.id),
          restart: {full: contract.shouldRunScope('full', 'cards'), stats: contract.shouldRunScope('stats', 'cards')},
        }));
        """
    )
    assert len(result["full"]) == 6
    assert result["stats"] == ["page:stats-overview:light", "page:stats-overview:dark"]
    assert result["restart"] == {"full": True, "stats": False}


def test_scope_and_worker_validation_rejects_invalid_values():
    result = run_contract(
        """
        const errors = [];
        for (const action of [() => contract.resolveScope('other'), () => contract.resolveWorkerCount('5')]) {
          try { action(); } catch (error) { errors.push(String(error.message)); }
        }
        console.log(JSON.stringify(errors));
        """
    )
    assert result == ["Unsupported E2E scope: other", "Screenshot workers must be auto or an integer from 1 to 4: 5"]


def test_bounded_queue_aggregates_failures_and_closes_workers():
    result = run_contract(
        """
        const closed = [];
        try {
          await contract.runBoundedTaskQueue(
            [{id:'a', artifactPath:'a'}, {id:'b', artifactPath:'b'}], 2,
            async id => ({id, close: async () => closed.push(id)}),
            async (_worker, task) => { if (task.id === 'b') throw new Error('boom'); return task.id; },
          );
        } catch (error) {
          console.log(JSON.stringify({message:error.message, results:error.taskResults.map(x => x.result), closed:closed.sort()}));
        }
        """
    )
    assert result == {"message": "Parallel capture failed for b", "results": ["success", "failed"], "closed": [1, 2]}


def test_capture_aggregation_handles_percentiles_and_zero_wall():
    result = run_contract(
        """
        const summary = contract.summarizeCapturePerformance({
          startedAt: 1000, finishedAt: 2000, workerCount: 2,
          tasks: [
            {id:'a', workerId:1, durationMs:600, result:'success', retryCount:0},
            {id:'b', workerId:2, durationMs:800, result:'success', retryCount:1},
          ],
        });
        console.log(JSON.stringify(summary));
        """
    )
    assert result["medianTaskMs"] == 600
    assert result["p90TaskMs"] == 800
    assert result["parallelSpeedup"] == pytest.approx(1.4)
    assert result["parallelEfficiency"] == pytest.approx(0.7)
    assert result["workerUtilization"] == {"1": 0.6, "2": 0.8}


def test_resource_summary_accepts_cpu_above_100_and_missing_network(tmp_path: Path):
    module = load_telemetry()
    reports = tmp_path / "reports"
    reports.mkdir()
    samples = [
        {"cpuPercent": 125.0, "memoryUsageBytes": 100, "memoryLimitBytes": 1000, "pids": 3, "diskFreeBytes": 900, "blockReadBytes": 10, "blockWriteBytes": 20},
        {"cpuPercent": 320.0, "memoryUsageBytes": 300, "memoryLimitBytes": 1000, "pids": 8, "diskFreeBytes": 700, "blockReadBytes": 30, "blockWriteBytes": 80},
    ]
    (reports / "resource-samples.jsonl").write_text("".join(json.dumps(item) + "\n" for item in samples), encoding="utf-8")

    summary = module.summarize_resources(tmp_path, 1.0)

    assert summary["averageCpuPercent"] == pytest.approx(222.5)
    assert summary["p95CpuPercent"] == 320
    assert summary["peakMemoryBytes"] == 300
    assert summary["memoryHeadroomBytes"] == 700
    assert summary["networkRxBytes"] is None
    assert summary["diskUsedDeltaBytes"] == 200


def test_docker_cache_and_layering_contract_is_structural():
    dockerfile = (ROOT / "docker" / "anki-e2e" / "Dockerfile").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci-e2e.yml").read_text(encoding="utf-8")
    assert dockerfile.index("COPY docker/anki-e2e/install-anki.sh") < dockerfile.index("docker/anki-e2e/*.mjs")
    assert dockerfile.index("web-dashboard/pnpm-lock.yaml") < dockerfile.index("docker/anki-e2e/*.mjs")
    assert "fetch --frozen-lockfile" in dockerfile
    assert "PNPM_STORE_DIR=/e2e/pnpm-store" in dockerfile
    assert '--store-dir "$PNPM_STORE_DIR"' in dockerfile
    assert "install --offline --frozen-lockfile" in (ROOT / "docker" / "anki-e2e" / "run-e2e.sh").read_text(encoding="utf-8")
    assert "cache-from: type=gha" in workflow
    assert "cache-to: type=gha" in workflow
    assert "compression=zstd" in workflow
    assert "containerd-snapshotter" in workflow
    assert "driver: docker" in workflow
    assert "compression-level: 0" in workflow
    assert "docker/setup-buildx-action@d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5 # v4.1.0" in workflow
    assert "docker/build-push-action@f9f3042f7e2789586610d6e8b85c8f03e5195baf # v7.2.0" in workflow
