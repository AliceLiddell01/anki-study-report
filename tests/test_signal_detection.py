from __future__ import annotations

from datetime import date, timedelta

from conftest import fresh_import_addon_module


TODAY = date(2026, 7, 17)


def daily_rows(count=40, *, reviews=40, retention_pass=36, retention_fail=4):
    start = TODAY - timedelta(days=count - 1)
    return [
        {
            "date": (start + timedelta(days=index)).isoformat(),
            "reviews": reviews,
            "retention_pass_count": retention_pass,
            "retention_fail_count": retention_fail,
        }
        for index in range(count)
    ]


def test_workload_thresholds_and_insufficient_baseline():
    module = fresh_import_addon_module("signal_detection")
    current = {"due": [{"dayOffset": 0, "count": 69}, {"dayOffset": 1, "count": 999}]}
    assert module.detect_review_pressure({"daily": daily_rows(10)}, current, TODAY.isoformat()) == []
    snapshot = {"daily": daily_rows(29, reviews=40)}
    assert module.detect_review_pressure(snapshot, current, TODAY.isoformat()) == []
    current["due"][0]["count"] = 70
    assert module.detect_review_pressure(snapshot, current, TODAY.isoformat())[0]["severity"] == "warning"
    current["due"][0]["count"] = 140
    assert module.detect_review_pressure(snapshot, current, TODAY.isoformat())[0]["severity"] == "critical"


def test_retention_uses_active_day_weighted_samples_and_exact_drop_points():
    module = fresh_import_addon_module("signal_detection")
    rows = daily_rows(35, reviews=40, retention_pass=36, retention_fail=4)
    for row in rows[-7:]:
        row["retention_pass_count"] = 32
        row["retention_fail_count"] = 8
    warning = module.detect_recent_retention_drop({"daily": rows}, {}, TODAY.isoformat())
    assert warning[0]["severity"] == "warning"
    assert warning[0]["evidence"]["dropPoints"] == 10.0
    for row in rows[-7:]:
        row["retention_pass_count"] = 30
        row["retention_fail_count"] = 10
    assert module.detect_recent_retention_drop({"daily": rows}, {}, TODAY.isoformat())[0]["severity"] == "critical"
    for row in rows[-7:]:
        row["retention_pass_count"] = 6
        row["retention_fail_count"] = 1
    assert module.detect_recent_retention_drop({"daily": rows}, {}, TODAY.isoformat()) == []


def test_deck_and_card_detectors_are_canonical_and_bounded():
    module = fresh_import_addon_module("signal_detection")
    deck_hub = {"nodes": {
        "1": {"deckId": 1, "aggregateHealth": "good", "structuralOnly": False, "subtreeMetrics": {"reviews": 20}},
        "2": {"deckId": 2, "aggregateHealth": "warning", "structuralOnly": False, "subtreeMetrics": {"reviews": 20, "passRate": 0.75, "failRate": 0.25, "averageAnswerSeconds": 12}},
        "3": {"deckId": 3, "aggregateHealth": "danger", "structuralOnly": False, "subtreeMetrics": {"reviews": 20, "passRate": 0.6, "failRate": 0.4, "averageAnswerSeconds": 20}},
    }}
    decks = module.detect_deck_health_decline({}, {"deckHub": deck_hub}, TODAY.isoformat())
    assert [item["severity"] for item in decks] == ["critical", "warning"]

    rows = [
        {"cardId": index + 1, "againCount": 5 if index % 2 else 3, "reviewCount": 6, "lastReviewAt": f"2026-07-17T09:{index % 60:02d}:00Z"}
        for index in range(60)
    ]
    cards = module.detect_repeated_again_cards({}, {"repeatedAgainCards": rows}, TODAY.isoformat())
    assert len(cards) == 50
    assert all(item["entityType"] == "card" for item in cards)
    assert cards[0]["severity"] == "critical"


def test_detector_failure_isolation_does_not_resolve_existing_signal(tmp_path, monkeypatch):
    store_module = fresh_import_addon_module("notification_store")
    module = fresh_import_addon_module("signal_detection")
    store = store_module.NotificationStore(tmp_path / "notifications.sqlite3")
    current = {"due": [{"dayOffset": 0, "count": 140}], "deckHub": {"nodes": {}}, "repeatedAgainCards": []}
    snapshot = {"daily": daily_rows(29, reviews=40)}
    evaluator = module.SignalEvaluator(store)
    first = evaluator.evaluate(snapshot, current, TODAY.isoformat(), source_revision="r1", evaluated_at="2026-07-17T10:00:00Z")
    assert first["detectors"]["workload.review_pressure"]["created"] == 1

    def fail(*_args):
        raise RuntimeError("collection content must not leak")

    monkeypatch.setitem(module.DETECTORS, "workload.review_pressure", fail)
    failed = evaluator.evaluate(snapshot, current, TODAY.isoformat(), source_revision="r2", evaluated_at="2026-07-17T11:00:00Z")
    assert failed["detectors"]["workload.review_pressure"]["diagnosticCode"] == "signal_detector_failed"
    assert store.list_notifications(tab="active")["total"] == 1


def test_repeated_again_collection_query_uses_anki_day_cutoff_and_is_bounded():
    module = fresh_import_addon_module("signal_detection")

    class DB:
        def __init__(self):
            self.calls = []

        def all(self, sql, cutoff):
            self.calls.append((sql, cutoff))
            return [(10, 5, 7, 1784282400000)]

    day_cutoff = 2_000_000_000
    db = DB()
    sched = type("Scheduler", (), {"day_cutoff": day_cutoff})()
    col = type("Collection", (), {"db": db, "sched": sched})()
    result = module.collect_repeated_again_cards(col, TODAY.isoformat())
    assert result == [{"cardId": 10, "againCount": 5, "reviewCount": 7, "lastReviewAt": "2026-07-17T10:00:00Z"}]
    assert len(db.calls) == 1
    assert db.calls[0][1] == (day_cutoff - 7 * 86400) * 1000
    assert "LIMIT 50" in db.calls[0][0]
