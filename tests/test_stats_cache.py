from __future__ import annotations

from conftest import import_addon_module


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
