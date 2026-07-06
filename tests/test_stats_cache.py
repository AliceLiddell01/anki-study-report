from __future__ import annotations

from conftest import import_addon_module


class StaticCacheManager:
    def __init__(self, status: dict[str, object], snapshot: dict[str, object] | None = None):
        self._status = status
        self._snapshot = snapshot if snapshot is not None else {"status": status, "daily": [], "deckDaily": []}

    def status(self) -> dict[str, object]:
        return dict(self._status)

    def report_snapshot(self) -> dict[str, object]:
        return dict(self._snapshot)


def daily_row(date: str = "2026-07-01") -> dict[str, object]:
    return {
        "date": date,
        "reviews": 10,
        "new_cards": 2,
        "learning": 2,
        "review": 8,
        "relearning": 0,
        "cram": 0,
        "again": 1,
        "hard": 1,
        "good": 7,
        "easy": 1,
        "pass_count": 9,
        "fail_count": 1,
        "study_seconds": 120,
        "total_answer_seconds": 120.0,
    }


def deck_daily_row(date: str = "2026-07-01") -> dict[str, object]:
    row = daily_row(date)
    row.update({"deck_id": 100, "deck_name": "Core"})
    return row


def test_empty_stats_cache_is_safe(tmp_path):
    stats_cache = import_addon_module("stats_cache")
    manager = stats_cache.StatsCacheManager(tmp_path / "study_report_cache.sqlite3")

    status = manager.status()
    snapshot = manager.report_snapshot()

    assert status["status"] == "empty"
    assert status["cachedDays"] == 0
    assert status["cachedDeckDays"] == 0
    assert snapshot["daily"] == []
    assert snapshot["deckDaily"] == []


def test_fake_rebuild_initializes_schema_and_cached_report_shape(tmp_path, monkeypatch):
    stats_cache = import_addon_module("stats_cache")
    report_from_cache = import_addon_module("report_from_cache")
    manager = stats_cache.StatsCacheManager(tmp_path / "study_report_cache.sqlite3")

    monkeypatch.setattr(stats_cache, "_anki_rollover_hours", lambda col: 4)
    monkeypatch.setattr(stats_cache, "_daily_rows", lambda col, rollover_hours, min_revlog_id: [daily_row()])
    monkeypatch.setattr(stats_cache, "_deck_daily_rows", lambda col, rollover_hours, min_revlog_id: [deck_daily_row()])
    monkeypatch.setattr(stats_cache, "_last_revlog_id", lambda col: 123)
    monkeypatch.setattr(stats_cache, "_collection_scm", lambda col: 456)

    first = manager.rebuild_all_time_cache(object(), profile_name="pytest")
    second = manager.rebuild_all_time_cache(object(), profile_name="pytest")
    snapshot = manager.report_snapshot()
    status = manager.status()

    assert first["ok"] is True
    assert second["ok"] is True
    assert manager.cache_path.is_file()
    assert status["status"] == "ready"
    assert status["cachedDays"] == 1
    assert status["cachedDeckDays"] == 1
    assert len(snapshot["daily"]) == 1
    assert len(snapshot["deckDaily"]) == 1

    parts = report_from_cache.build_cached_report_parts(
        manager,
        "today",
        {
            "use_stats_cache_for_report": True,
            "today_date": "2026-07-01",
            "period_start_date": "2026-07-01",
            "period_end_date": "2026-07-01",
        },
        legacy_report={"summary": {"totalReviews": 10}},
    )

    assert parts["dataSource"] == "mixed"
    assert "activity" in parts
    assert "comparison" in parts
    assert "cache" in parts
    assert "performance" in parts
    assert parts["cache"]["periodSummary"]["total_reviews"] == 10


def test_cached_report_parts_characterizes_unavailable_cache_fallback():
    report_from_cache = import_addon_module("report_from_cache")
    manager = StaticCacheManager({
        "status": "empty",
        "version": 1,
        "updatedAt": 0,
        "cachedDays": 0,
        "cachedDeckDays": 0,
        "isBuilding": False,
        "lastRevlogId": 0,
    })

    parts = report_from_cache.build_cached_report_parts(
        manager,
        "today",
        {"use_stats_cache_for_report": True, "today_date": "2026-07-01"},
        legacy_report={"total_reviews": 10},
    )

    assert parts["dataSource"] == "legacy"
    assert parts["cache"]["dataSource"] == "legacy"
    assert parts["cache"]["usedFor"] == []
    assert parts["cache"]["version"] == 1
    assert parts["cache"]["isBuilding"] is False
    assert parts["cache"]["error"] is None
    assert parts["cache"]["lastError"] is None
    assert parts["cache"]["fallbackReason"] == "cache_not_ready:empty"
    assert parts["cache"]["cachedDays"] == 0
    assert parts["cacheDebug"] == {
        "parityChecked": False,
        "reason": "cache_not_ready:empty",
        "mismatches": [],
    }
    assert parts["performance"]["cacheReadMs"] == 0
    assert "activity" not in parts
    assert "comparison" not in parts


def test_cached_report_fallback_preserves_cache_status_diagnostics():
    report_from_cache = import_addon_module("report_from_cache")
    manager = StaticCacheManager({
        "status": "stale",
        "version": 99,
        "updatedAt": 1_782_925_200,
        "cachedDays": 12,
        "cachedDeckDays": 5,
        "isBuilding": True,
        "error": "schema mismatch\nsecond line",
        "lastError": "previous rebuild failed",
        "lastRevlogId": 456,
    })

    parts = report_from_cache.build_cached_report_parts(
        manager,
        "today",
        {"use_stats_cache_for_report": True, "today_date": "2026-07-01"},
    )

    assert parts["dataSource"] == "legacy"
    assert parts["cache"]["dataSource"] == "legacy"
    assert parts["cache"]["usedFor"] == []
    assert parts["cache"]["fallbackReason"] == "cache_not_ready:stale"
    assert parts["cache"]["version"] == 99
    assert parts["cache"]["isBuilding"] is True
    assert parts["cache"]["error"] == "schema mismatch"
    assert parts["cache"]["lastError"] == "previous rebuild failed"
    assert parts["cache"]["cachedDays"] == 12
    assert parts["cache"]["cachedDeckDays"] == 5
    assert parts["cache"]["lastRevlogId"] == 456
    assert parts["cacheDebug"]["reason"] == "cache_not_ready:stale"


def test_cached_report_parts_characterizes_mixed_cache_shape_and_merge():
    report_from_cache = import_addon_module("report_from_cache")
    status = {
        "status": "ready",
        "version": 1,
        "updatedAt": 1_782_925_200,
        "cachedDays": 2,
        "cachedDeckDays": 2,
        "isBuilding": False,
        "lastRevlogId": 123,
    }
    manager = StaticCacheManager(
        status,
        {
            "status": status,
            "daily": [daily_row("2026-07-01"), daily_row("2026-07-02")],
            "deckDaily": [deck_daily_row("2026-07-01"), deck_daily_row("2026-07-02")],
        },
    )

    parts = report_from_cache.build_cached_report_parts(
        manager,
        "today",
        {
            "use_stats_cache_for_report": True,
            "today_date": "2026-07-02",
            "period_start_date": "2026-07-01",
            "period_end_date": "2026-07-02",
        },
        legacy_report={
            "total_reviews": 20,
            "new_cards": 4,
            "answer_distribution": {"again": 2, "hard": 2, "good": 14, "easy": 2},
            "pass_count": 18,
            "fail_count": 2,
            "total_seconds": 240,
            "heatmap": {"active_days": 2},
        },
    )

    assert parts["dataSource"] == "mixed"
    assert parts["cache"]["dataSource"] == "mixed"
    assert parts["cache"]["usedFor"] == ["activity.days", "activity.summary", "comparison"]
    assert parts["cache"]["version"] == 1
    assert parts["cache"]["isBuilding"] is False
    assert parts["cache"]["error"] is None
    assert parts["cache"]["lastError"] is None
    assert parts["cache"]["fallbackReason"] is None
    assert parts["cache"]["periodSummary"] == {
        "total_reviews": 20,
        "new_cards": 4,
        "again": 2,
        "hard": 2,
        "good": 14,
        "easy": 2,
        "pass": 18,
        "fail": 2,
        "pass_rate": 0.9,
        "fail_rate": 0.1,
        "study_seconds": 240,
        "active_days": 2,
        "average_reviews_per_active_day": 10.0,
        "average_study_seconds_per_active_day": 120.0,
        "average_answer_seconds": 12.0,
    }
    assert parts["cache"]["cacheDeckSummary"]["available"] is True
    assert parts["cacheDebug"] == {"parityChecked": True, "mismatches": []}
    assert parts["activity"]["available"] is True
    assert len(parts["activity"]["days"]) == 2
    assert parts["comparison"]["source"]["primary"] == "stats_cache"

    live_report = {
        "dataSource": "legacy",
        "activity": {"available": False, "days": []},
        "comparison": {"available": False},
        "attentionCards": [],
        "attentionCardsStatus": {"status": "unavailable", "source": "cache"},
        "forecast": {"available": False},
        "decks": [],
    }
    merged = report_from_cache.merge_cached_report_parts(live_report, parts)

    assert merged["dataSource"] == "mixed"
    assert merged["activity"]["available"] is True
    assert merged["comparison"]["source"]["primary"] == "stats_cache"
    assert merged["attentionCards"] == []
    assert merged["attentionCardsStatus"] == {"status": "unavailable", "source": "cache"}
    assert merged["forecast"] == {"available": False}


def test_cached_report_merge_preserves_live_only_contract_and_ignores_removed_aliases():
    report_from_cache = import_addon_module("report_from_cache")
    live_report = {
        "dataSource": "legacy",
        "metadata": {"period": "today"},
        "activity": {"available": False, "days": [], "liveOnly": "kept"},
        "comparison": {"available": False, "liveOnly": {"nested": True}},
        "attentionCards": [{"cardId": 1}],
        "attentionCardsStatus": {"status": "available", "source": "fresh"},
        "noteTypeCatalog": [{"noteTypeId": 10}],
        "forecast": {"available": True, "tomorrow": 20},
        "recommendations": [{"id": "keep"}],
        "cache": {"status": "ready", "liveOnly": "kept"},
    }
    cache_parts = {
        "dataSource": "mixed",
        "activity": {"available": True, "cacheOnly": "added"},
        "comparison": {"cacheOnly": {"nested": True}},
        "cache": {"usedFor": ["activity.days"], "fallbackReason": None},
        "cacheDebug": {"parityChecked": True, "mismatches": []},
        "performance": {"cacheReadMs": 1},
        "metadata": {"period": "Cache"},
        "attentionCards": [{"cardId": 999}],
        "attentionCardsStatus": {"status": "unavailable", "source": "cache"},
        "noteTypeCatalog": [],
        "forecast": {"available": False},
        "recommendations": [],
        "cards": [{"cardId": 999}],
        "cardIssues": [{"cardId": 999}],
        "problemCards": [{"cardId": 999}],
    }

    merged = report_from_cache.merge_cached_report_parts(live_report, cache_parts)

    assert merged["dataSource"] == "mixed"
    assert merged["activity"] == {"available": True, "days": [], "liveOnly": "kept", "cacheOnly": "added"}
    assert merged["comparison"] == {"available": False, "liveOnly": {"nested": True}, "cacheOnly": {"nested": True}}
    assert merged["cache"] == {"status": "ready", "liveOnly": "kept", "usedFor": ["activity.days"]}
    assert merged["cacheDebug"] == {"parityChecked": True}
    assert merged["performance"] == {"cacheReadMs": 1}
    assert merged["metadata"] == {"period": "today"}
    assert merged["attentionCards"] == [{"cardId": 1}]
    assert merged["attentionCardsStatus"] == {"status": "available", "source": "fresh"}
    assert merged["noteTypeCatalog"] == [{"noteTypeId": 10}]
    assert merged["forecast"] == {"available": True, "tomorrow": 20}
    assert merged["recommendations"] == [{"id": "keep"}]
    assert "cards" not in merged
    assert "cardIssues" not in merged
    assert "problemCards" not in merged
