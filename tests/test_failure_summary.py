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


def test_valid_primary_and_deterministic_serialization(tmp_path: Path):
    output = tmp_path / "reports" / "failure-summary.json"
    document = protocol.record_failure(
        output,
        "docker-e2e",
        failure(),
        primary=True,
        last_successful_phase_id="api-smoke-first",
        last_successful_item_id="route.cards.light",
    )
    assert document["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert protocol.load_document(output) == document
    assert output.read_text(encoding="utf-8") == protocol.serialize_document(document)
    assert not output.read_bytes().startswith(b"\xef\xbb\xbf")


def test_first_primary_wins_and_later_failure_is_secondary(tmp_path: Path):
    output = tmp_path / "failure-summary.json"
    first = failure()
    second_primary = protocol.build_failure(
        code="ASR-E2E-ARTIFACT-MANIFEST",
        phase_id="artifact-manifest",
        summary="manifest failed",
        original_exit_code=1,
    )
    protocol.record_failure(output, "docker-e2e", first, primary=True)
    unchanged = protocol.record_failure(output, "docker-e2e", second_primary, primary=True)
    assert unchanged["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert unchanged["secondary"] == []

    secondary = protocol.build_failure(
        code="ASR-E2E-ARTIFACT-MANIFEST",
        phase_id="artifact-manifest",
        summary="manifest failed",
        original_exit_code=1,
    )
    document = protocol.record_failure(output, "docker-e2e", secondary, primary=False)
    assert document["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert [item["failureCode"] for item in document["secondary"]] == ["ASR-E2E-ARTIFACT-MANIFEST"]


def test_cleanup_failure_does_not_replace_root_cause_and_is_deduplicated(tmp_path: Path):
    output = tmp_path / "failure-summary.json"
    protocol.record_failure(output, "docker-e2e", failure(), primary=True)
    cleanup = protocol.build_failure(code="ASR-E2E-CLEANUP", summary="compose down failed", original_exit_code=1)
    protocol.record_failure(output, "docker-e2e", cleanup, primary=False)
    protocol.record_failure(output, "docker-e2e", cleanup, primary=False)
    protocol.set_cleanup_status(output, "failure")
    document = protocol.load_document(output)
    assert document["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert len(document["secondary"]) == 1
    assert document["cleanup"] == {"status": "failure", "failureCount": 1}


def test_secondary_count_is_bounded(tmp_path: Path):
    output = tmp_path / "failure-summary.json"
    protocol.record_failure(output, "docker-e2e", failure(), primary=True)
    for index in range(protocol.MAX_SECONDARY + 5):
        entry = protocol.build_failure(
            code="ASR-E2E-CLEANUP",
            summary=f"cleanup failure {index}",
            original_exit_code=1,
        )
        protocol.record_failure(output, "docker-e2e", entry, primary=False)
    assert len(protocol.load_document(output)["secondary"]) == protocol.MAX_SECONDARY


def test_atomic_concurrent_secondary_writes(tmp_path: Path):
    output = tmp_path / "reports" / "failure-summary.json"
    protocol.record_failure(output, "docker-e2e", failure(), primary=True)
    work = [(str(PATH), str(output), index) for index in range(8)]
    with ProcessPoolExecutor(max_workers=4) as executor:
        list(executor.map(record_secondary_worker, work))
    document = protocol.load_document(output)
    assert document["primary"]["failureCode"] == "ASR-E2E-BROWSER-ITEM"
    assert len(document["secondary"]) == 8
