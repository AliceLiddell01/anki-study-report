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


@pytest.mark.parametrize(
    "value",
    [
        "https://127.0.0.1/?token=secret",
        r"C:\\Users\\owner\\secret.txt",
        "/home/owner/private.txt",
        "Authorization: Bearer secret-value",
        "line\nworkflow",
    ],
)
def test_private_summary_is_sanitized(value: str):
    entry = failure(summary=value)
    serialized = json.dumps(entry, ensure_ascii=False)
    assert "secret" not in serialized
    assert "/home/" not in serialized
    assert "C:\\" not in serialized
    assert "\n" not in entry["summary"]


@pytest.mark.parametrize(
    "path",
    ["/tmp/failure.json", "C:/Users/owner/failure.json", "../failure.json", "reports/../secret.json", "reports\\bad.json"],
)
def test_unsafe_evidence_paths_are_rejected(path: str):
    with pytest.raises(protocol.FailureProtocolError):
        failure(evidence_paths=[path])


def test_unknown_code_and_invalid_signal_are_rejected():
    with pytest.raises(protocol.FailureProtocolError, match="unknown failure code"):
        protocol.build_failure(code="ASR-E2E-NOT-REGISTERED")
    with pytest.raises(protocol.FailureProtocolError, match="allowlisted"):
        failure(original_signal="SIGUSR1")


def test_full_stack_is_not_stored():
    entry = failure(summary="TimeoutError: ready failed\n  at /tmp/browser.mjs:10:2")
    assert "\n" not in entry["summary"]
    assert "/tmp/" not in entry["summary"]
    assert "stack" not in entry


def test_document_size_is_bounded(tmp_path: Path):
    output = tmp_path / "failure-summary.json"
    protocol.record_failure(output, "docker-e2e", failure(summary="x" * 5000), primary=True)
    assert output.stat().st_size <= protocol.MAX_DOCUMENT_BYTES
    assert len(protocol.load_document(output)["primary"]["summary"].encode("utf-8")) <= protocol.MAX_SUMMARY_BYTES


def test_success_document_is_rejected():
    document = {
        "schemaVersion": 1,
        "result": "success",
        "producer": "docker-e2e",
        "primary": failure(),
        "secondary": [],
        "context": {"lastSuccessfulPhaseId": None, "lastSuccessfulItemId": None, "activePhaseId": None, "activeItemId": None},
        "cleanup": {"status": "success", "failureCount": 0},
    }
    with pytest.raises(protocol.FailureProtocolError, match="schemaVersion/result"):
        protocol.validate_document(document)
