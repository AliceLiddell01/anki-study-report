"""Dashboard action handlers for Anki Study Report."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import threading
import traceback

try:
    from aqt import mw
except Exception:
    mw = None

from .browser_actions import (
    BROWSER_ACTION_CARD_LIMIT,
    BrowserSearchQueryError,
    build_deck_browser_query,
    build_entity_browser_query,
    card_ids_search_query,
    collect_browser_action_card_ids,
    open_browser_search,
    sanitize_browser_search_query,
)


MainThreadRunner = Callable[[Callable[[], object], float], dict]


class DashboardActions:
    def __init__(
        self,
        *,
        run_on_main: MainThreadRunner,
        copy_markdown: Callable[[str], None],
        save_markdown: Callable[[str], str | None],
        open_current_dashboard: Callable[[], None],
        open_route: Callable[[str, str], None],
        copy_url: Callable[[], None],
        restart_server: Callable[[], None],
        stop_server: Callable[[], None],
        log_event: Callable[..., None],
        open_native_stats: Callable[[], None] | None = None,
    ) -> None:
        self._run_on_main = run_on_main
        self._copy_markdown = copy_markdown
        self._save_markdown = save_markdown
        self._open_current_dashboard = open_current_dashboard
        self._open_route = open_route
        self._copy_url = copy_url
        self._restart_server = restart_server
        self._stop_server = stop_server
        self._log_event = log_event
        self._open_native_stats = open_native_stats
        self._context: dict[str, object] = {}

    def clear_report_context(self) -> None:
        self._context.clear()

    def publish_report_context(
        self,
        markdown: str,
        metadata: dict,
        deck_ids: list[int] | None,
    ) -> None:
        self._context.clear()
        self._context.update(
            {
                "markdown": markdown,
                "metadata": dict(metadata),
                "start_ts": metadata.get("period_start_ts"),
                "end_ts": metadata.get("period_end_ts"),
                "deck_ids": list(deck_ids) if deck_ids is not None else None,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def request_server_action(self, action: str) -> dict:
        safe_action = str(action or "").strip()
        if safe_action == "open-dashboard":
            return self._request_server_open_route("/home", "server.open_dashboard")
        if safe_action == "copy-url":
            return self._request_server_copy_url()
        if safe_action == "restart":
            return self._request_server_restart()
        if safe_action == "stop":
            return self._request_server_stop()
        return dashboard_action_error(safe_action or "unknown", "Unknown server action.")

    def request_dashboard_action(self, action: str, payload: dict) -> dict:
        safe_action = str(action or "").strip()
        if safe_action == "open-browser":
            kind = str(payload.get("kind") or "problematic-decks")
            return self._request_dashboard_browser_action(kind)
        if safe_action == "open-browser-search":
            return self._request_dashboard_browser_search(payload.get("query"))
        if safe_action == "open-deck-browser":
            return self._request_deck_browser(payload.get("deckId"), payload.get("mode"))
        if safe_action == "open-search-selection":
            return self._request_search_selection(payload)
        if safe_action == "open-problematic":
            return self._request_dashboard_browser_action("problematic-decks")
        if safe_action == "open-again":
            return self._request_dashboard_browser_action("again")
        if safe_action == "open-new":
            return self._request_dashboard_browser_action("new")
        if safe_action == "copy-markdown":
            return self._request_dashboard_copy_markdown()
        if safe_action == "save-markdown":
            return self._request_dashboard_save_markdown()
        if safe_action == "open-dashboard":
            return self._request_dashboard_open_dashboard()
        if safe_action == "open-native-stats":
            return self._request_native_stats(payload)
        if safe_action == "open-deck-options":
            return self._request_deck_options(payload)
        return dashboard_action_error(safe_action or "unknown", "Unknown dashboard action.")

    def _request_native_stats(self, payload: dict) -> dict:
        if payload:
            return dashboard_action_error("open-native-stats", "This action does not accept a body.")
        if self._open_native_stats is None:
            return dashboard_action_error("open-native-stats", "Native Anki statistics is unavailable.")
        result = self._run_on_main(self._open_native_stats)
        if not result["ok"]:
            return dashboard_action_error("open-native-stats", result["error"])
        return dashboard_action_ok("open-native-stats", "Opened Anki statistics.")

    def _request_deck_options(self, payload: dict) -> dict:
        if set(payload) != {"deckId"} or isinstance(payload.get("deckId"), bool):
            return dashboard_action_error("open-deck-options", "A deck ID is required.")
        try:
            deck_id = int(payload["deckId"])
        except (TypeError, ValueError):
            return dashboard_action_error("open-deck-options", "A deck ID is required.")
        def open_options() -> None:
            if mw is None or mw.col is None:
                raise RuntimeError("Anki collection is unavailable.")
            deck = mw.col.decks.get(deck_id)
            if not isinstance(deck, dict) or deck.get("dyn"):
                raise RuntimeError("Normal deck was not found.")
            from aqt.deckoptions import display_options_for_deck_id
            display_options_for_deck_id(deck_id)
        result = self._run_on_main(open_options)
        if not result["ok"]:
            return dashboard_action_error("open-deck-options", result["error"])
        return dashboard_action_ok("open-deck-options", "Opened deck options.")

    def _request_server_open_route(self, route: str, event: str) -> dict:
        result = self._run_on_main(lambda: self._open_route(route, event))
        if not result["ok"]:
            return dashboard_action_error(event, result["error"])
        return dashboard_action_ok(event, "Opened dashboard.")

    def _request_server_copy_url(self) -> dict:
        result = self._run_on_main(self._copy_url)
        if not result["ok"]:
            return dashboard_action_error("copy-url", result["error"])
        return dashboard_action_ok("copy-url", "Copied dashboard URL.")

    def _request_server_restart(self) -> dict:
        result = self._run_on_main(self._restart_server, timeout_seconds=12.0)
        if not result["ok"]:
            return dashboard_action_error("restart", result["error"])
        self._log_event("server.restart", "Dashboard server restarted")
        return dashboard_action_ok("restart", "Dashboard server restarted.")

    def _request_server_stop(self) -> dict:
        result = self._run_on_main(self._stop_server, timeout_seconds=12.0)
        if not result["ok"]:
            return dashboard_action_error("stop", result["error"])
        self._log_event("server.stop_requested", "Dashboard server stop requested")
        return dashboard_action_ok("stop", "Dashboard server stopped.")

    def _request_dashboard_copy_markdown(self) -> dict:
        markdown = self._context_markdown()
        if markdown is None:
            return dashboard_no_report_error("copy-markdown")

        result = self._run_on_main(lambda: self._copy_markdown(markdown))
        if not result["ok"]:
            return dashboard_action_error("copy-markdown", result["error"])
        return dashboard_action_ok("copy-markdown", "Copied Markdown to clipboard.")

    def _request_dashboard_save_markdown(self) -> dict:
        markdown = self._context_markdown()
        if markdown is None:
            return dashboard_no_report_error("save-markdown")

        result = self._run_on_main(
            lambda: self._save_markdown(markdown),
            timeout_seconds=120.0,
        )
        if not result["ok"]:
            return dashboard_action_error("save-markdown", result["error"])
        filename = result.get("value")
        if not filename:
            return dashboard_action_error("save-markdown", "Save cancelled.")
        return dashboard_action_ok("save-markdown", f"Saved report to: {filename}")

    def _request_dashboard_open_dashboard(self) -> dict:
        if not self._context:
            return dashboard_no_report_error("open-dashboard")

        result = self._run_on_main(self._open_current_dashboard)
        if not result["ok"]:
            return dashboard_action_error("open-dashboard", result["error"])
        return dashboard_action_ok("open-dashboard", "Opened current report in dashboard.")

    def _request_dashboard_browser_action(self, kind: str) -> dict:
        action_map = {
            "problematic-decks": (
                "problem_decks",
                "open-browser",
                "No problematic decks found for the selected period.",
            ),
            "again": ("again", "open-again", "No Again answers found for the selected period."),
            "new": ("new", "open-new", "No new cards found for the selected period."),
        }
        if kind not in action_map:
            return dashboard_action_error("open-browser", "Unknown browser action kind.")
        action, response_action, empty_message = action_map[kind]
        if not self._context:
            return dashboard_no_report_error(response_action)
        if mw is None or mw.col is None or not hasattr(mw, "taskman"):
            return dashboard_action_error(response_action, "Anki collection is unavailable.")

        try:
            start_ts = int(self._context["start_ts"])
            end_ts = int(self._context["end_ts"])
            deck_ids = self._context.get("deck_ids")
            deck_ids = deck_ids if isinstance(deck_ids, list) else None
        except Exception:
            return dashboard_action_error(
                response_action,
                "No report is available for the selected period.",
            )

        result = self._collect_browser_action_on_background(start_ts, end_ts, deck_ids, action)
        if not result.get("ok"):
            return dashboard_action_error(
                response_action,
                str(result.get("error") or "Browser action failed."),
            )
        card_ids = result.get("card_ids") if isinstance(result.get("card_ids"), list) else []
        if not card_ids:
            return dashboard_action_ok(response_action, empty_message)

        open_result = self._run_on_main(lambda: open_browser_search(card_ids_search_query(card_ids)))
        if not open_result["ok"]:
            return dashboard_action_error(response_action, open_result["error"])
        message = "Opened Anki Browser."
        if result.get("truncated"):
            message = f"Opened Anki Browser with the first {BROWSER_ACTION_CARD_LIMIT} cards."
        return dashboard_action_ok(response_action, message)

    def _request_dashboard_browser_search(self, query: object) -> dict:
        try:
            safe_query = sanitize_browser_search_query(query)
        except BrowserSearchQueryError as error:
            return dashboard_action_error("open-browser-search", str(error))
        if mw is None:
            return dashboard_action_error("open-browser-search", "Anki collection is unavailable.")
        result = self._run_on_main(lambda: open_browser_search(safe_query))
        if not result["ok"]:
            return dashboard_action_error("open-browser-search", result["error"])
        return dashboard_action_ok("open-browser-search", f"Opened Anki Browser for {safe_query}.")

    def _request_deck_browser(self, deck_id: object, mode: object) -> dict:
        if mw is None or getattr(mw, "col", None) is None:
            return dashboard_action_error("open-deck-browser", "Anki collection is unavailable.")
        try:
            query = build_deck_browser_query(mw.col, deck_id, mode)
        except BrowserSearchQueryError as error:
            return dashboard_action_error("open-deck-browser", str(error))
        result = self._run_on_main(lambda: open_browser_search(query, prevalidated=True))
        if not result["ok"]:
            return dashboard_action_error("open-deck-browser", result["error"])
        return dashboard_action_ok("open-deck-browser", "Opened deck in Anki Browser.")

    def _request_search_selection(self, payload: dict) -> dict:
        if set(payload) != {"mode", "entityIds"}:
            return dashboard_action_error(
                "open-search-selection", "Search selection request is invalid."
            )
        if mw is None or getattr(mw, "col", None) is None:
            return dashboard_action_error(
                "open-search-selection", "Anki collection is unavailable."
            )
        def validate_and_open() -> int:
            query, requested_count = build_entity_browser_query(
                mw.col, payload.get("mode"), payload.get("entityIds")
            )
            open_browser_search(query, prevalidated=True)
            return requested_count

        result = self._run_on_main(validate_and_open)
        if not result["ok"]:
            return dashboard_action_error("open-search-selection", result["error"])
        requested_count = int(result.get("value") or 0)
        return dashboard_action_ok(
            "open-search-selection",
            "Opened selected results in Anki Browser.",
            resultCode="search.browser_opened",
            requestedCount=requested_count,
        )

    def _collect_browser_action_on_background(
        self,
        start_ts: int,
        end_ts: int,
        deck_ids: list[int] | None,
        action: str,
    ) -> dict:
        event = threading.Event()
        holder: dict[str, object] = {}

        def finish(future) -> None:
            try:
                holder["result"] = future.result()
            except Exception:
                traceback.print_exc()
                holder["result"] = {"ok": False, "error": "Browser action failed."}
            finally:
                event.set()

        def start_background() -> None:
            mw.taskman.run_in_background(
                lambda: collect_browser_action_card_ids(
                    mw.col,
                    start_ts,
                    end_ts,
                    deck_ids,
                    action,
                    BROWSER_ACTION_CARD_LIMIT,
                ),
                finish,
            )

        schedule_result = self._run_on_main(start_background)
        if not schedule_result["ok"]:
            return {"ok": False, "error": schedule_result["error"]}

        if not event.wait(30.0):
            return {"ok": False, "error": "Browser action is still running."}
        result = holder.get("result")
        return result if isinstance(result, dict) else {"ok": False, "error": "Browser action failed."}

    def _context_markdown(self) -> str | None:
        markdown = self._context.get("markdown")
        return markdown if isinstance(markdown, str) and markdown.strip() else None


def dashboard_no_report_error(action: str) -> dict:
    return dashboard_action_error(action, "No report is available yet. Build or open a report first.")


def dashboard_action_ok(action: str, message: str, **extra) -> dict:
    return {
        "ok": True,
        "action": action,
        "message": message,
        **extra,
    }


def dashboard_action_error(action: str, error: str) -> dict:
    safe_error = str(error or "Dashboard action failed.")
    if "Traceback" in safe_error:
        safe_error = "Dashboard action failed."
    return {
        "ok": False,
        "action": action,
        "error": safe_error,
    }
