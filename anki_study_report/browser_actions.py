"""Anki Browser actions for report cards."""

from __future__ import annotations

import traceback

from aqt import dialogs, mw

from .metrics import collect_action_card_ids


BROWSER_ACTION_CARD_LIMIT = 500


def collect_browser_action_card_ids(
    col,
    start_ts: int,
    end_ts: int,
    deck_ids: list[int] | None,
    action: str,
    limit: int = BROWSER_ACTION_CARD_LIMIT,
) -> dict:
    try:
        card_ids = collect_action_card_ids(
            col,
            start_ts,
            end_ts,
            deck_ids=deck_ids,
            action=action,
            max_results=limit + 1,
        )
        truncated = len(card_ids) > limit
        return {
            "ok": True,
            "card_ids": card_ids[:limit],
            "truncated": truncated,
        }
    except Exception:
        return {
            "ok": False,
            "error": traceback.format_exc(),
        }


def card_ids_search_query(card_ids: list[int]) -> str:
    return balanced_or_search_query([f"cid:{int(card_id)}" for card_id in card_ids])


def balanced_or_search_query(terms: list[str]) -> str:
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]

    midpoint = len(terms) // 2
    left = balanced_or_search_query(terms[:midpoint])
    right = balanced_or_search_query(terms[midpoint:])
    return f"({left} OR {right})"


def open_browser_search(search_query: str) -> None:
    if mw is None:
        raise RuntimeError("Главное окно Anki недоступно.")

    browser = dialogs.open("Browser", mw)
    if hasattr(browser, "search_for"):
        browser.search_for(search_query)
        return

    search_edit = getattr(getattr(browser, "form", None), "searchEdit", None)
    if search_edit is not None:
        if hasattr(search_edit, "lineEdit"):
            search_edit.lineEdit().setText(search_query)
        elif hasattr(search_edit, "setText"):
            search_edit.setText(search_query)

    if hasattr(browser, "onSearchActivated"):
        browser.onSearchActivated()
    elif hasattr(browser, "search"):
        browser.search()
    elif hasattr(browser, "onSearch"):
        browser.onSearch()
