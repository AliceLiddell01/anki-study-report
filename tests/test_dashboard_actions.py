from __future__ import annotations

from types import SimpleNamespace

from conftest import fresh_import_addon_module


def make_actions(module, opened, open_native_stats=None):
    def run_on_main(callback, timeout_seconds=5.0):
        try:
            return {"ok": True, "value": callback()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return module.DashboardActions(
        run_on_main=run_on_main,
        copy_markdown=lambda text: None,
        save_markdown=lambda text: None,
        open_current_dashboard=lambda: None,
        open_route=lambda route, event: None,
        copy_url=lambda: None,
        restart_server=lambda: None,
        stop_server=lambda: None,
        log_event=lambda *args, **kwargs: None,
        open_native_stats=open_native_stats,
    )


def test_dashboard_action_opens_exact_row_search_query(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    opened = []
    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace())
    monkeypatch.setattr(dashboard_actions, "open_browser_search", lambda query: opened.append(query))

    actions = make_actions(dashboard_actions, opened)
    result = actions.request_dashboard_action("open-browser-search", {"query": "cid:123"})

    assert result["ok"] is True
    assert result["action"] == "open-browser-search"
    assert opened == ["cid:123"]


def test_dashboard_action_rejects_unsafe_row_search_query(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    opened = []
    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace())
    monkeypatch.setattr(dashboard_actions, "open_browser_search", lambda query: opened.append(query))

    actions = make_actions(dashboard_actions, opened)
    result = actions.request_dashboard_action("open-browser-search", {"query": "cid:1\ncid:2"})

    assert result["ok"] is False
    assert result["action"] == "open-browser-search"
    assert opened == []


def test_dashboard_action_opens_deck_by_id_and_mode_without_accepting_raw_query(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    opened = []

    class Decks:
        def get(self, deck_id, default=False):
            return {"id": deck_id, "name": "Words::N3", "dyn": 0}

    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace(col=SimpleNamespace(decks=Decks())))
    monkeypatch.setattr(
        dashboard_actions,
        "open_browser_search",
        lambda query, **kwargs: opened.append((query, kwargs)),
    )
    actions = make_actions(dashboard_actions, opened)
    result = actions.request_dashboard_action(
        "open-deck-browser",
        {"deckId": 42, "mode": "direct", "query": "is:suspended"},
    )
    assert result["ok"] is True
    assert result["action"] == "open-deck-browser"
    assert opened == [('deck:"Words::N3" -deck:"Words::N3::*"', {"prevalidated": True})]


def test_dashboard_action_rejects_invalid_deck_browser_mode(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace(col=SimpleNamespace()))
    monkeypatch.setattr(
        dashboard_actions,
        "build_deck_browser_query",
        lambda col, deck_id, mode: (_ for _ in ()).throw(dashboard_actions.BrowserSearchQueryError("Unknown deck Browser mode.")),
    )
    actions = make_actions(dashboard_actions, [])
    result = actions.request_dashboard_action("open-deck-browser", {"deckId": 42, "mode": "query"})
    assert result == {
        "ok": False,
        "action": "open-deck-browser",
        "error": "Unknown deck Browser mode.",
    }


def test_dashboard_action_opens_explicit_search_selection(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    opened = []
    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace(col=object()))
    monkeypatch.setattr(
        dashboard_actions,
        "build_entity_browser_query",
        lambda col, mode, ids: ("(nid:1 OR nid:2)", len(ids)),
    )
    monkeypatch.setattr(
        dashboard_actions,
        "open_browser_search",
        lambda query, **kwargs: opened.append((query, kwargs)),
    )
    actions = make_actions(dashboard_actions, opened)
    result = actions.request_dashboard_action(
        "open-search-selection", {"mode": "notes", "entityIds": ["1", "2"]}
    )
    assert result["ok"] is True
    assert result["resultCode"] == "search.browser_opened"
    assert result["requestedCount"] == 2
    assert opened == [("(nid:1 OR nid:2)", {"prevalidated": True})]


def test_dashboard_action_rejects_ambiguous_search_selection_body(monkeypatch):
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    monkeypatch.setattr(dashboard_actions, "mw", SimpleNamespace(col=object()))
    actions = make_actions(dashboard_actions, [])
    result = actions.request_dashboard_action(
        "open-search-selection",
        {"mode": "cards", "entityIds": ["1"], "query": "cid:2"},
    )
    assert result["ok"] is False
    assert result["action"] == "open-search-selection"


def test_dashboard_action_opens_native_stats_and_rejects_body():
    dashboard_actions = fresh_import_addon_module("dashboard_actions")
    opened = []
    actions = make_actions(dashboard_actions, [], open_native_stats=lambda: opened.append("stats"))
    assert actions.request_dashboard_action("open-native-stats", {}) == {
        "ok": True,
        "action": "open-native-stats",
        "message": "Opened Anki statistics.",
    }
    assert opened == ["stats"]
    rejected = actions.request_dashboard_action("open-native-stats", {"scope": "all"})
    assert rejected["ok"] is False
    assert opened == ["stats"]
