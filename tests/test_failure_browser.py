from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docker" / "anki-e2e" / "failure_protocol.py"


def load_protocol():
    spec = importlib.util.spec_from_file_location("asr_failure_protocol", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


protocol = load_protocol()


def failure(code="ASR-E2E-BROWSER-ITEM", **overrides):
    values = dict(
        code=code,
        phase_id="browser-smoke-first",
        item_id="route.cards.dark",
        item_kind="route-capture",
        error_type="TimeoutError",
        summary="Dashboard route did not become ready",
        occurred_at_utc="2026-07-24T00:00:00.000Z",
        elapsed_ms=12345,
        original_exit_code=1,
        evidence_paths=["reports/browser-smoke-first.json"],
        raw_diagnostic_paths=["diagnostics/anki.log"],
    )
    values.update(overrides)
    return protocol.build_failure(**values)


def record_secondary_worker(args):
    module_path, output, index = args
    spec = importlib.util.spec_from_file_location(f"asr_failure_protocol_{index}", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    entry = module.build_failure(
        code="ASR-E2E-CLEANUP",
        error_type="CleanupError",
        summary=f"cleanup helper {index} failed",
        original_exit_code=1,
    )
    module.record_failure(Path(output), "docker-e2e", entry, primary=False)


def test_browser_report_maps_route_and_telemetry_failures(tmp_path: Path):
    report = tmp_path / "browser-smoke-first.json"
    report.write_text(json.dumps({
        "progress": {"failedItemId": "telemetry.offline"},
        "items": [
            {"id": "route.cards.light", "kind": "route-capture", "status": "pass"},
            {"id": "telemetry.offline", "kind": "telemetry", "status": "fail", "errorType": "TimeoutError", "safeErrorSummary": "queue did not persist", "operationDurationMs": 100},
        ],
    }), encoding="utf-8")
    entry, last_item = protocol.browser_failure_from_report(report)
    assert entry["failureCode"] == "ASR-E2E-TELEMETRY"
    assert entry["itemId"] == "telemetry.offline"
    assert last_item == "route.cards.light"


def test_render_and_annotation_are_compact_and_safe(tmp_path: Path):
    output = tmp_path / "failure-summary.json"
    protocol.record_failure(output, "docker-e2e", failure(), primary=True)
    document = protocol.load_document(output)
    rendered = protocol.render_markdown(document)
    annotation = protocol.annotation(document)
    assert "ASR-E2E-BROWSER-ITEM" in rendered
    assert annotation.startswith("::error title=ASR-E2E-BROWSER-ITEM::")
    assert "\n" not in annotation
