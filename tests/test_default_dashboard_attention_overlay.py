from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace


def import_addon_root(monkeypatch):
    for name in list(sys.modules):
        if name == "anki_study_report" or name.startswith("anki_study_report."):
            sys.modules.pop(name, None)

    aqt = types.ModuleType("aqt")
    aqt.mw = SimpleNamespace(col=SimpleNamespace(db=object()), pm=SimpleNamespace(name="Test"))
    aqt.gui_hooks = SimpleNamespace(main_window_did_init=[])
    aqt.dialogs = SimpleNamespace()
    qt = types.ModuleType("aqt.qt")
    for name in (
        "QAction",
        "QApplication",
        "QCheckBox",
        "QComboBox",
        "QDate",
        "QDateEdit",
        "QDialog",
        "QFileDialog",
        "QHBoxLayout",
        "QLabel",
        "QDesktopServices",
        "QLineEdit",
        "QListWidget",
        "QListWidgetItem",
        "QPushButton",
        "QSpinBox",
        "QSizePolicy",
        "QTabWidget",
        "QTextEdit",
        "Qt",
        "QUrl",
        "QVBoxLayout",
        "QWidget",
    ):
        setattr(qt, name, type(name, (), {}))
    utils = types.ModuleType("aqt.utils")
    utils.showCritical = lambda *args, **kwargs: None
    utils.showInfo = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "aqt", aqt)
    monkeypatch.setitem(sys.modules, "aqt.qt", qt)
    monkeypatch.setitem(sys.modules, "aqt.utils", utils)
    return importlib.import_module("anki_study_report")


def test_prepare_default_dashboard_report_applies_fresh_attention_overlay(monkeypatch):
    addon = import_addon_root(monkeypatch)
    calls = []
    snapshot = {"daily": [], "deckDaily": [], "status": {"status": "ready"}}

    monkeypatch.setattr(addon, "_ensure_default_dashboard_cache_current", lambda: {"ok": True})
    monkeypatch.setattr(addon._STATS_CACHE, "report_snapshot", lambda: snapshot)
    monkeypatch.setattr(addon, "_current_anki_today_date_key", lambda: "2026-07-03")
    monkeypatch.setattr(
        addon,
        "_dashboard_display_settings_for_payload",
        lambda: {"period": "last_7_days", "selected_deck_ids": [10], "selected_deck_names": ["Deck"]},
    )
    monkeypatch.setattr(addon, "build_markdown_report", lambda metrics, metadata: "markdown")

    def fake_collector(col, start_ts, end_ts, deck_ids, max_results):
        calls.append(
            {
                "col": col,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "deck_ids": deck_ids,
                "max_results": max_results,
            }
        )
        return (
            [{"cardId": 1, "deckName": "Deck", "frontPreview": "front", "issues": ["leech"]}],
            {
                "status": "available",
                "scannedCards": 3,
                "candidateCards": 3,
                "revlogRows": 5,
                "returnedCards": 1,
                "collectorRan": True,
                "collectionAvailable": True,
                "source": "fresh",
            },
        )

    monkeypatch.setattr(addon, "collect_attention_cards_with_status", fake_collector)

    result = addon._prepare_default_dashboard_report()

    assert calls
    assert calls[0]["deck_ids"] == [10]
    assert calls[0]["max_results"] == addon.ATTENTION_CARD_LIMIT
    assert calls[0]["start_ts"] > 0
    assert calls[0]["end_ts"] > calls[0]["start_ts"]
    assert result["report"]["attentionCards"][0]["cardId"] == 1
    assert result["report"]["attentionCardsStatus"]["source"] == "fresh"
    assert result["report"]["metadata"]["cardLevelSource"] == "fresh"


def test_default_dashboard_attention_overlay_tolerates_collector_error(monkeypatch):
    addon = import_addon_root(monkeypatch)

    def failing_collector(*_args, **_kwargs):
        raise RuntimeError("boom token=secret C:\\Users\\Name\\collection.anki2")

    monkeypatch.setattr(addon, "collect_attention_cards_with_status", failing_collector)

    metrics = addon._apply_default_dashboard_attention_cards(
        {},
        {"period_start_ts": 1, "period_end_ts": 2},
        {"selected_deck_ids": []},
    )

    assert metrics["attention_cards"] == []
    assert metrics["attention_cards_status"]["status"] == "error"
    assert metrics["attention_cards_status"]["source"] == "fresh"
    assert metrics["attention_cards_status"]["collectorRan"] is True
    assert "token=secret" not in metrics["attention_cards_status"]["reason"]
    assert "C:\\Users" not in metrics["attention_cards_status"]["reason"]
