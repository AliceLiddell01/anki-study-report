from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "anki_study_report"


def load_report_from_cache_module():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ADDON)]
    sys.modules["anki_study_report"] = package
    for name in ("metrics", "stats_cache", "report_from_cache"):
        spec = importlib.util.spec_from_file_location(
            f"anki_study_report.{name}",
            ADDON / f"{name}.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"anki_study_report.{name}"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules["anki_study_report.report_from_cache"]


def main() -> None:
    adapter = load_report_from_cache_module()

    live_report = {
        "dataSource": "legacy",
        "activity": {
            "available": True,
            "activeDays": 2,
            "missedDays": 1,
            "days": [{"date": "2026-06-29", "reviews": 12}],
            "liveOnly": "kept",
        },
        "comparison": {
            "available": True,
            "message": "live message",
            "today": {"date": "2026-06-30", "reviews": 10, "passRate": 0.8},
            "baselines": {
                "avg7": {"label": "Последние 7 дней", "reviews": 7, "passRate": 0.7},
                "currentWeek": {"label": "Эта неделя", "reviews": 20},
            },
            "comparisons": {
                "avg7": {"reviews": {"delta": 3, "percentDelta": 42.9}},
                "week": {"reviews": {"delta": 5, "percentDelta": 25}},
            },
            "liveOnly": {"nested": True},
        },
        "cache": {"status": "ready", "usedFor": ["legacy"]},
    }
    cache_parts = {
        "dataSource": "mixed",
        "activity": {
            "activeDays": 5,
            "missedDays": None,
            "days": [],
            "cacheOnly": "kept",
        },
        "comparison": {
            "message": "",
            "today": {"reviews": 11, "passRate": None},
            "baselines": {"avg7": {"reviews": 8, "passRate": None}},
            "comparisons": {"avg7": {"reviews": {"delta": 3.0, "percentDelta": None}}},
            "cacheOnly": {"nested": True},
        },
        "cache": {"status": "ready", "usedFor": ["activity.days", "comparison"]},
        "performance": {"reportBuildMs": 4, "cacheReadMs": 1},
    }

    merged = adapter.merge_cached_report_parts(live_report, cache_parts)

    assert merged["dataSource"] == "mixed", merged
    assert merged["activity"]["activeDays"] == 5, merged["activity"]
    assert merged["activity"]["missedDays"] == 1, merged["activity"]
    assert merged["activity"]["days"] == live_report["activity"]["days"], merged["activity"]
    assert merged["activity"]["liveOnly"] == "kept", merged["activity"]
    assert merged["activity"]["cacheOnly"] == "kept", merged["activity"]

    comparison = merged["comparison"]
    assert comparison["message"] == "live message", comparison
    assert comparison["today"]["reviews"] == 11, comparison["today"]
    assert comparison["today"]["passRate"] == 0.8, comparison["today"]
    assert comparison["baselines"]["avg7"]["reviews"] == 8, comparison["baselines"]
    assert comparison["baselines"]["avg7"]["passRate"] == 0.7, comparison["baselines"]
    assert comparison["comparisons"]["week"]["reviews"]["delta"] == 5, comparison["comparisons"]
    assert comparison["liveOnly"] == {"nested": True}, comparison
    assert comparison["cacheOnly"] == {"nested": True}, comparison
    assert merged["cache"]["usedFor"] == ["activity.days", "comparison"], merged["cache"]
    assert merged["performance"]["cacheReadMs"] == 1, merged["performance"]

    print("REPORT_CACHE_MERGE_SMOKE_OK")


if __name__ == "__main__":
    main()
