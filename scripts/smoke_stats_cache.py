from __future__ import annotations

import importlib.util
from contextlib import closing
import json
import sqlite3
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "anki_study_report"


def load_stats_cache_module():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ADDON)]
    sys.modules["anki_study_report"] = package
    for name in ("metrics", "stats_cache"):
        spec = importlib.util.spec_from_file_location(
            f"anki_study_report.{name}",
            ADDON / f"{name}.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"anki_study_report.{name}"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules["anki_study_report.stats_cache"]


def assert_status_json_safe(status: dict) -> None:
    payload = json.dumps(status, ensure_ascii=False, allow_nan=False)
    forbidden = ("Traceback", "NaN", "Infinity", "Invalid Date", "undefined")
    assert not any(item in payload for item in forbidden), payload


def main() -> None:
    stats_cache = load_stats_cache_module()
    manager_cls = stats_cache.StatsCacheManager

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "study_report_cache.sqlite3"
        manager = manager_cls(cache_path)

        empty = manager.status()
        assert empty["status"] == "empty", empty
        assert empty["version"] == 1, empty
        assert empty["cachedDays"] == 0, empty
        assert_status_json_safe(empty)

        assert manager.prepare_rebuild() is True
        assert manager.prepare_refresh() is False
        scheduled = manager.status()
        assert scheduled["status"] == "scheduled", scheduled
        assert scheduled["isBuilding"] is True, scheduled
        assert_status_json_safe(scheduled)

        reloaded = manager_cls(cache_path)
        interrupted = reloaded.status()
        assert interrupted["status"] == "stale", interrupted
        assert "interrupted" in str(interrupted["error"]).lower(), interrupted

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "study_report_cache.sqlite3"
        with closing(sqlite3.connect(cache_path)) as conn:
            conn.execute("create table cache_meta (key text primary key, value text not null)")
            with conn:
                conn.execute("insert into cache_meta values ('version', '999')")
        manager = manager_cls(cache_path)
        stale = manager.status()
        assert stale["status"] == "stale", stale
        assert "outdated" in str(stale["error"]).lower(), stale
        assert_status_json_safe(stale)

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "study_report_cache.sqlite3"
        cache_path.write_text("not a sqlite database", encoding="utf-8")
        manager = manager_cls(cache_path)
        damaged = manager.status()
        assert damaged["status"] == "error", damaged
        assert damaged["error"], damaged
        assert_status_json_safe(damaged)

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "study_report_cache.sqlite3"
        manager = manager_cls(cache_path)
        assert manager.prepare_refresh() is True
        result = manager.refresh_incremental(object(), already_started=True)
        assert result["ok"] is False, result
        assert result["status"] == "stale", result
        assert result.get("rebuildRequired") is True, result
        assert_status_json_safe(manager.status())

    print("STATS_CACHE_SMOKE_OK")


if __name__ == "__main__":
    main()
