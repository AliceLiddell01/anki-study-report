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


def test_search_selection_builds_mode_specific_query_and_validates_entities():
    browser_actions = fresh_import_addon_module("browser_actions")

    class Entity:
        def __init__(self, entity_id):
            self.id = entity_id

    class Collection:
        def get_card(self, entity_id):
            if entity_id == 999:
                raise KeyError(entity_id)
            return Entity(entity_id)

        def get_note(self, entity_id):
            return Entity(entity_id)

    col = Collection()
    assert browser_actions.build_entity_browser_query(col, "cards", ["1", "2"])[0] == "(cid:1 OR cid:2)"
    assert browser_actions.build_entity_browser_query(col, "notes", ["3"])[0] == "nid:3"
    for mode, ids in [
        ("cards", ["1", "1"]),
        ("cards", [1]),
        ("notes", []),
        ("mixed", ["1"]),
        ("cards", ["999"]),
    ]:
        try:
            browser_actions.build_entity_browser_query(col, mode, ids)
        except browser_actions.BrowserSearchQueryError:
            pass
        else:
            raise AssertionError("Expected invalid explicit selection to fail")


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


def test_sanitize_browser_search_query_accepts_cid_and_nid():
    browser_actions = fresh_import_addon_module("browser_actions")

    assert browser_actions.sanitize_browser_search_query("cid:123") == "cid:123"
    assert browser_actions.sanitize_browser_search_query("nid:456") == "nid:456"


def test_sanitize_browser_search_query_rejects_huge_or_and_unsafe_text():
    browser_actions = fresh_import_addon_module("browser_actions")

    huge = " OR ".join(f"cid:{index}" for index in range(500))
    for query in [huge, "cid:1\ncid:2", "cid:1 token=secret", "deck:\"x\" C:\\Users\\secret", "<b>cid:1</b>"]:
        try:
            browser_actions.sanitize_browser_search_query(query)
        except browser_actions.BrowserSearchQueryError:
            pass
        else:
            raise AssertionError(f"Expected unsafe query to fail: {query[:40]}")


def test_deck_browser_query_includes_descendants_and_direct_only_excludes_them():
    browser_actions = fresh_import_addon_module("browser_actions")

    class Decks:
        def get(self, deck_id, default=False):
            return {"id": deck_id, "name": "Words and Grammar::N3", "dyn": 0}

    col = type("Col", (), {"decks": Decks()})()
    assert browser_actions.build_deck_browser_query(col, 42, "subtree") == 'deck:"Words and Grammar::N3"'
    assert browser_actions.build_deck_browser_query(col, 42, "direct") == (
        'deck:"Words and Grammar::N3" -deck:"Words and Grammar::N3::*"'
    )


def test_deck_browser_query_escapes_quotes_backslashes_wildcards_and_non_latin():
    browser_actions = fresh_import_addon_module("browser_actions")

    class Decks:
        def get(self, deck_id, default=False):
            return {"id": deck_id, "name": '日本語 "OR" \\ *_ <x>', "dyn": 0}

    col = type("Col", (), {"decks": Decks()})()
    query = browser_actions.build_deck_browser_query(col, 7, "subtree")
    assert query == 'deck:"日本語 \\"OR\\" \\\\ \\*\\_ &lt;x&gt;"'
    assert " token=" not in query


def test_deck_browser_query_rejects_unknown_filtered_and_invalid_mode():
    browser_actions = fresh_import_addon_module("browser_actions")

    class Decks:
        def get(self, deck_id, default=False):
            if deck_id == 1:
                return {"id": 1, "name": "Filtered", "dyn": 1}
            return None

    col = type("Col", (), {"decks": Decks()})()
    for deck_id, mode in [(1, "subtree"), (999, "subtree"), (1, "raw-query")]:
        try:
            browser_actions.build_deck_browser_query(col, deck_id, mode)
        except browser_actions.BrowserSearchQueryError:
            pass
        else:
            raise AssertionError("Expected invalid deck Browser request to fail")


def test_deck_browser_query_rejects_query_breaking_control_characters():
    browser_actions = fresh_import_addon_module("browser_actions")

    class Decks:
        def get(self, deck_id, default=False):
            return {"id": deck_id, "name": 'Safe"\nis:suspended', "dyn": 0}

    col = type("Col", (), {"decks": Decks()})()
    try:
        browser_actions.build_deck_browser_query(col, 7, "subtree")
    except browser_actions.BrowserSearchQueryError as error:
        assert "control characters" in str(error)
    else:
        raise AssertionError("Expected control-character deck name to fail")
