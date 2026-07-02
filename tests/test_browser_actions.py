from __future__ import annotations

import sys

from conftest import fresh_import_addon_module


def test_browser_actions_import_without_dashboard_dependencies():
    sys.modules.pop("anki_study_report.dashboard_server", None)
    sys.modules.pop("anki_study_report.dashboard_payload", None)

    browser_actions = fresh_import_addon_module("browser_actions")

    assert browser_actions.BROWSER_ACTION_CARD_LIMIT == 500
    assert "anki_study_report.dashboard_server" not in sys.modules
    assert "anki_study_report.dashboard_payload" not in sys.modules


def test_card_ids_search_query_handles_empty_and_single_card():
    browser_actions = fresh_import_addon_module("browser_actions")

    assert browser_actions.card_ids_search_query([]) == ""
    assert browser_actions.card_ids_search_query([123]) == "cid:123"


def test_card_ids_search_query_for_limit_sized_input():
    browser_actions = fresh_import_addon_module("browser_actions")
    ids = list(range(1, browser_actions.BROWSER_ACTION_CARD_LIMIT + 1))

    query = browser_actions.card_ids_search_query(ids)

    assert query.count("cid:") == browser_actions.BROWSER_ACTION_CARD_LIMIT
    assert f"cid:{browser_actions.BROWSER_ACTION_CARD_LIMIT}" in query
    assert f"cid:{browser_actions.BROWSER_ACTION_CARD_LIMIT + 1}" not in query


def test_balanced_or_search_query_builds_valid_or_expression():
    browser_actions = fresh_import_addon_module("browser_actions")

    query = browser_actions.balanced_or_search_query(["cid:1", "cid:2", "cid:3", "cid:4"])

    assert query.startswith("(")
    assert query.endswith(")")
    assert query.count(" OR ") == 3
    for term in ["cid:1", "cid:2", "cid:3", "cid:4"]:
        assert term in query


def test_collect_browser_action_card_ids_uses_limit_and_reports_truncation(monkeypatch):
    browser_actions = fresh_import_addon_module("browser_actions")
    seen = {}

    def fake_collect(col, start_ts, end_ts, *, deck_ids, action, max_results):
        seen.update(
            {
                "col": col,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "deck_ids": deck_ids,
                "action": action,
                "max_results": max_results,
            }
        )
        return list(range(1, max_results + 1))

    monkeypatch.setattr(browser_actions, "collect_action_card_ids", fake_collect)

    result = browser_actions.collect_browser_action_card_ids(
        col=object(),
        start_ts=10,
        end_ts=20,
        deck_ids=[1, 2],
        action="again",
        limit=3,
    )

    assert result == {"ok": True, "card_ids": [1, 2, 3], "truncated": True}
    assert seen["max_results"] == 4
    assert seen["deck_ids"] == [1, 2]
    assert seen["action"] == "again"
