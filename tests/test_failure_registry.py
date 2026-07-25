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


def test_registry_is_unique_bounded_and_consistent():
    assert len(protocol.REGISTRY) == len(set(protocol.REGISTRY))
    assert set(protocol.ALLOWED_CATEGORIES) >= {meta.category for meta in protocol.REGISTRY.values()}
    for code, meta in protocol.REGISTRY.items():
        assert re.fullmatch(r"ASR-[A-Z0-9]+(?:-[A-Z0-9]+)+", code)
        assert len(code) <= 80
        assert meta.default_exit_class in protocol.ALLOWED_EXIT_CLASSES
        assert len(meta.default_summary.encode("utf-8")) <= protocol.MAX_SUMMARY_BYTES
        assert all(phase in protocol.ALL_PHASES for phase in meta.allowed_phases)
        protocol.sanitize_summary(meta.default_summary, meta.default_summary)


def test_phase_mapping_covers_current_fast_and_docker_phases():
    assert set(protocol.PHASE_FAILURE_CODES) == protocol.ALL_PHASES
    assert protocol.code_for_phase("docker-e2e", "browser-smoke-first", item_kind="telemetry") == "ASR-E2E-TELEMETRY"
    assert protocol.code_for_phase("docker-e2e", "browser-smoke-first", item_kind="route-capture") == "ASR-E2E-BROWSER-ITEM"
