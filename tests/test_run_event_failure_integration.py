from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docker" / "anki-e2e" / "run_event_protocol.py"


def load_protocol(name="asr_run_event_protocol"):
    spec = importlib.util.spec_from_file_location(name, PROTOCOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


protocol = load_protocol()


def event(schema=1, **overrides):
    value = {
        "schemaVersion": schema,
        "timestampUtc": "2026-07-24T00:00:00.000Z",
        "elapsedMs": 123,
        "producer": "fast-ci",
        "phaseId": "frontend-vitest",
        "eventKind": "phase",
        "status": "pass",
        "durationMs": 100,
        "current": None,
        "total": None,
        "message": None,
        "failureCode": None,
    }
    value.update(overrides)
    return value


def worker_append(args):
    output, index = args
    local = load_protocol(f"asr_run_event_protocol_worker_{index}")
    local.emit(Path(output), "fast-ci", "frontend-vitest", "message", "info", message=f"worker={index}", echo=False)
    return index


def test_later_manifest_failure_is_secondary_and_does_not_replace_api_root(tmp_path: Path):
    output = tmp_path / "reports" / "run-events.jsonl"
    protocol.initialize_stream(output, "docker-e2e")
    protocol.emit(output, "docker-e2e", "api-smoke-first", "phase", "start")
    protocol.emit(output, "docker-e2e", "api-smoke-first", "phase", "fail", duration_ms=10, original_exit_code=5)
    protocol.emit(output, "docker-e2e", "artifact-manifest", "phase", "start")
    protocol.emit(output, "docker-e2e", "artifact-manifest", "phase", "fail", duration_ms=2, original_exit_code=1)
    protocol.finish_run(output, "docker-e2e", "fail", original_exit_code=5)
    summary = protocol.failure_protocol.load_document(protocol.failure_summary_path(output))
    assert summary["primary"]["failureCode"] == "ASR-E2E-API-SMOKE"
    assert [item["failureCode"] for item in summary["secondary"]] == ["ASR-E2E-ARTIFACT-MANIFEST"]
    assert protocol.validate_stream(output, expected_producer="docker-e2e")[-1]["failureCode"] == "ASR-E2E-API-SMOKE"


def test_browser_phase_failure_extracts_exact_item_from_partial_report(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    output = reports / "run-events.jsonl"
    protocol.initialize_stream(output, "docker-e2e")
    protocol.emit(output, "docker-e2e", "api-smoke-first", "phase", "start")
    protocol.emit(output, "docker-e2e", "api-smoke-first", "phase", "pass", duration_ms=2)
    (reports / "browser-smoke-first.json").write_text(json.dumps({
        "schemaVersion": 3,
        "progress": {"failedItemId": "route.cards.dark"},
        "items": [
            {"id": "route.cards.light", "kind": "route-capture", "status": "pass", "operationDurationMs": 4},
            {"id": "route.cards.dark", "kind": "route-capture", "status": "fail", "errorType": "TimeoutError", "safeErrorSummary": "route did not become ready", "operationDurationMs": 50},
        ],
    }), encoding="utf-8")
    protocol.emit(output, "docker-e2e", "browser-smoke-first", "phase", "start")
    protocol.emit(output, "docker-e2e", "browser-smoke-first", "phase", "fail", duration_ms=60, original_exit_code=1)
    protocol.finish_run(output, "docker-e2e", "fail", original_exit_code=1)
    summary = protocol.failure_protocol.load_document(protocol.failure_summary_path(output))
    assert summary["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert summary["primary"]["itemId"] == "route.cards.dark"
    assert summary["context"]["lastSuccessfulItemId"] == "route.cards.light"
