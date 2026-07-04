from __future__ import annotations

from types import SimpleNamespace

from conftest import fresh_import_addon_module


def make_actions(module, opened):
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
