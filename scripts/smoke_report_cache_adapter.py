from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any


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


def assert_json_safe(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    forbidden = ("Traceback", "NaN", "Infinity", "Invalid Date", "undefined")
    assert not any(item in encoded for item in forbidden), encoded


class FakeCacheManager:
    def __init__(
        self,
        status: dict[str, Any],
        daily: list[dict[str, Any]] | None = None,
        deck_daily: list[dict[str, Any]] | None = None,
    ) -> None:
        self._status = status
        self._daily = daily or []
        self._deck_daily = deck_daily or []

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def report_snapshot(self) -> dict[str, Any]:
        return {
            "status": dict(self._status),
            "daily": [dict(row) for row in self._daily],
            "deckDaily": [dict(row) for row in self._deck_daily],
        }


def daily_rows() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-06-24",
            "reviews": 5,
            "new_cards": 1,
            "learning": 1,
            "review": 4,
            "relearning": 0,
            "cram": 0,
            "again": 1,
            "hard": 1,
            "good": 2,
            "easy": 1,
            "pass_count": 4,
            "fail_count": 1,
            "study_seconds": 20,
            "total_answer_seconds": 18.5,
        },
        {
            "date": "2026-06-26",
            "reviews": 7,
            "new_cards": 2,
            "learning": 2,
            "review": 5,
            "relearning": 0,
            "cram": 0,
            "again": 1,
            "hard": 2,
            "good": 3,
            "easy": 1,
            "pass_count": 6,
            "fail_count": 1,
            "study_seconds": 28,
            "total_answer_seconds": 21.0,
        },
        {
            "date": "2026-06-30",
            "reviews": 10,
            "new_cards": 3,
            "learning": 3,
            "review": 7,
            "relearning": 0,
            "cram": 0,
            "again": 1,
            "hard": 3,
            "good": 4,
            "easy": 2,
            "pass_count": 9,
            "fail_count": 1,
            "study_seconds": 50,
            "total_answer_seconds": 42.2,
        },
    ]


def ready_status(adapter: Any, cached_days: int = 3) -> dict[str, Any]:
    return {
        "status": "ready",
        "version": adapter.CACHE_SCHEMA_VERSION,
        "updatedAt": 1_781_000_000,
        "cachedDays": cached_days,
        "cachedDeckDays": 2,
        "lastRevlogId": 1_782_751_206_906,
        "limitations": [adapter.DECK_HISTORY_NOTE],
    }


def main() -> None:
    adapter = load_report_from_cache_module()
    rows = daily_rows()
    manager = FakeCacheManager(
        ready_status(adapter),
        rows,
        [
            {"date": "2026-06-24", "deck_id": 1, "reviews": 5},
            {"date": "2026-06-30", "deck_id": 2, "reviews": 10},
        ],
    )
    config = {
        "use_stats_cache_for_report": True,
        "period_start_date": "2026-06-24",
        "period_end_date": "2026-06-30",
        "today_date": "2026-06-30",
    }
    legacy_report = {
        "metrics": {
            "total_reviews": 22,
            "new_cards": 6,
            "pass_count": 19,
            "fail_count": 3,
            "total_seconds": 98,
            "answer_distribution": {"again": 3, "hard": 6, "good": 9, "easy": 4},
            "heatmap": {"active_days": 3},
        }
    }

    mixed = adapter.build_cached_report_parts(manager, "last_7_days", config, legacy_report=legacy_report)
    assert mixed["dataSource"] == "mixed", mixed
    assert mixed["cache"]["usedFor"] == ["activity.days", "activity.summary", "comparison"], mixed["cache"]
    assert mixed["activity"]["days"][0]["date"] == "2026-06-24", mixed["activity"]["days"]
    assert mixed["activity"]["days"][1]["date"] == "2026-06-25", mixed["activity"]["days"]
    assert mixed["activity"]["days"][1]["reviews"] == 0, mixed["activity"]["days"][1]
    assert mixed["activity"]["days"][0]["avgAnswerSeconds"] == 3.7, mixed["activity"]["days"][0]
    assert mixed["cache"]["periodSummary"]["average_answer_seconds"] == 3.7, mixed["cache"]["periodSummary"]
    assert mixed["comparison"]["today"]["date"] == "2026-06-30", mixed["comparison"]["today"]
    assert mixed["comparison"]["today"]["avgAnswerSeconds"] == 4.2, mixed["comparison"]["today"]
    assert mixed["cacheDebug"]["parityChecked"] is True, mixed["cacheDebug"]
    assert mixed["cacheDebug"]["mismatches"] == [], mixed["cacheDebug"]
    assert_json_safe(mixed)

    off = adapter.build_cached_report_parts(manager, "last_7_days", {**config, "use_stats_cache_for_report": False})
    assert off["dataSource"] == "legacy", off
    assert off["cache"]["fallbackReason"] == "feature_flag_disabled", off["cache"]
    assert off["cache"]["usedFor"] == [], off["cache"]
    assert_json_safe(off)

    empty = adapter.build_cached_report_parts(
        FakeCacheManager(ready_status(adapter, cached_days=0), []),
        "last_7_days",
        config,
    )
    assert empty["dataSource"] == "legacy", empty
    assert empty["cache"]["fallbackReason"] == "cache_empty", empty["cache"]
    assert_json_safe(empty)

    errored = adapter.build_cached_report_parts(
        FakeCacheManager({"status": "error", "cachedDays": 3, "cachedDeckDays": 0}),
        "last_7_days",
        config,
    )
    assert errored["dataSource"] == "legacy", errored
    assert errored["cache"]["fallbackReason"] == "cache_not_ready:error", errored["cache"]
    assert_json_safe(errored)

    all_time = adapter.build_cached_report_parts(manager, "all_time", config)
    assert all_time["dataSource"] == "mixed", all_time
    assert all_time["activity"]["days"][0]["date"] == "2026-06-24", all_time["activity"]["days"]
    assert all_time["activity"]["days"][-1]["date"] == "2026-06-30", all_time["activity"]["days"]
    assert_json_safe(all_time)

    print("REPORT_CACHE_ADAPTER_SMOKE_OK")


if __name__ == "__main__":
    main()
