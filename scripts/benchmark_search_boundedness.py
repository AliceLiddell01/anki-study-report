#!/usr/bin/env python3
"""Characterize add-on-side Search selection latency and peak memory."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
import time
import tracemalloc
import types


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NATIVE_RESULT_COUNT = 100_000


def load_search_service():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ROOT / "anki_study_report")]
    package.__file__ = str(ROOT / "anki_study_report" / "__init__.py")
    sys.modules.setdefault("anki_study_report", package)
    return importlib.import_module("anki_study_report.search_service")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-result-count", type=int, default=DEFAULT_NATIVE_RESULT_COUNT)
    args = parser.parse_args()
    count = max(1, int(args.native_result_count))
    search = load_search_service()

    tracemalloc.start()
    started = time.perf_counter()
    selected, truncated = search._bounded_sorted_entity_ids(
        range(count, 0, -1),
        limit=search.RESULT_CAP,
        reverse=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({
        "nativeResultCount": count,
        "resultCap": search.RESULT_CAP,
        "selectedCount": len(selected),
        "truncated": truncated,
        "elapsedMs": round(elapsed_ms, 3),
        "peakAddonBytes": peak_bytes,
        "memoryBudgetBytes": 2 * 1024 * 1024,
        "latencyBudgetMs": 500,
        "upstreamNativeSequenceMaterialized": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
