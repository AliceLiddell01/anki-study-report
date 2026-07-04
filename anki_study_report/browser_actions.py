"""Anki Browser actions for report cards."""

from __future__ import annotations

import traceback
import re

from aqt import dialogs, mw

from .metrics import collect_action_card_ids


BROWSER_ACTION_CARD_LIMIT = 500
BROWSER_SEARCH_DIRECT_MAX_LENGTH = 1800


class BrowserSearchQueryError(ValueError):
    """Raised when a dashboard browser search query is unsafe."""


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
    search_query = sanitize_browser_search_query(search_query)
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


def sanitize_browser_search_query(search_query: object, *, max_length: int = BROWSER_SEARCH_DIRECT_MAX_LENGTH) -> str:
    query = str(search_query or "").strip()
    if not query:
        raise BrowserSearchQueryError("Search query is empty.")
    if len(query) > max_length:
        raise BrowserSearchQueryError("Search query is too long for direct Browser open.")
    if re.search(r"[\r\n\t<>]", query):
        raise BrowserSearchQueryError("Search query contains unsafe characters.")
    if re.search(r"\b[A-Za-z]:\\|file://|https?://|token=", query, flags=re.IGNORECASE):
        raise BrowserSearchQueryError("Search query contains unsafe path, URL, or token text.")
    if not _browser_search_query_allowed(query):
        raise BrowserSearchQueryError("Search query is not allowed for dashboard Browser open.")
    return query


def _browser_search_query_allowed(query: str) -> bool:
    if re.fullmatch(r"cid:\d+", query):
        return True
    if re.fullmatch(r"nid:\d+", query):
        return True
    if re.fullmatch(r'deck:"[^"\r\n<>]{1,180}"(?:\s+[\w-]+:"?[^"\r\n<>]{1,120}"?)*', query):
        return True
    if re.fullmatch(r"(tag|rated|is):[A-Za-z0-9_:\-]+", query):
        return True
    if " OR " in query:
        terms = [
            term.strip("() ")
            for term in query.split(" OR ")
            if term.strip("() ")
        ]
        return bool(terms) and all(re.fullmatch(r"cid:\d+|nid:\d+", term) for term in terms)
    return False
