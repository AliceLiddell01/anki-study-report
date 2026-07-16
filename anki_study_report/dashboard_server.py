"""Local web dashboard server for Anki Study Report.

The server is intentionally local-only. It serves the built Vite dashboard from
disk and shuts itself down after a configurable idle timeout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import threading
import time
import traceback
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .dashboard_asset_graph import extract_dashboard_html_refs, resolve_dashboard_asset_graph
from .path_safety import trusted_file_from_inventory

from .extension_logging import (
    clear_logs,
    log_event,
    log_exception,
    log_status,
    read_recent_logs,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_IDLE_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class DashboardServerState:
    running: bool
    url: str | None
    host: str
    port: int
    requested_port: int
    port_collision: bool
    message: str | None
    static_dir: str | None
    static_available: bool
    started_at: str | None
    last_request_at: str | None
    idle_timeout_seconds: int
    report_available: bool
    report_path: str | None


class DashboardServerManager:
    """Owns the local HTTP server lifecycle."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT
        self._requested_port = DEFAULT_PORT
        self._port_collision = False
        self._message: str | None = None
        self._token: str | None = None
        self._idle_timeout_seconds = DEFAULT_IDLE_TIMEOUT_SECONDS
        self._static_dir: Path | None = None
        self._report_dir: Path | None = None
        self._report_path: Path | None = None
        self._started_at: float | None = None
        self._last_request_at: float | None = None
        self._cache_status_provider = None
        self._cache_rebuild_handler = None
        self._cache_refresh_handler = None
        self._action_handler = None
        self._server_action_handler = None
        self._server_status_provider = None
        self._health_provider = None
        self._display_settings_provider = None
        self._display_settings_handler = None
        self._profile_provider = None
        self._profile_handler = None
        self._product_notices_provider = None
        self._product_notice_seen_handler = None
        self._privacy_provider = None
        self._privacy_handler = None
        self._telemetry_status_provider = None
        self._telemetry_event_handler = None
        self._telemetry_delete_handler = None
        self._telemetry_check_handler = None
        self._statistics_query_handler = None
        self._fsrs_query_handler = None
        self._search_query_handler = None
        self._search_inspect_handler = None
        self._card_action_handler = None
        self._note_action_handler = None
        self._media_file_provider = None

    def start(
        self,
        port: int = DEFAULT_PORT,
        idle_timeout_seconds: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
    ) -> DashboardServerState:
        """Start the server if needed and return its current state."""

        with self._lock:
            if self._server is not None:
                return self.state()

            self._host = DEFAULT_HOST
            self._requested_port = _safe_port(port)
            self._port = self._requested_port
            self._port_collision = False
            self._message = None
            self._token = secrets.token_urlsafe(32)
            self._idle_timeout_seconds = max(0, int(idle_timeout_seconds or 0))
            self._static_dir = _find_static_dir()
            self._report_dir = Path(tempfile.mkdtemp(prefix="anki-study-report-dashboard-"))
            self._report_path = self._report_dir / "report.json"
            self._started_at = time.time()
            self._last_request_at = self._started_at
            self._stop_event.clear()

            handler = partial(_DashboardRequestHandler, manager=self)
            try:
                self._server = ThreadingHTTPServer((self._host, self._port), handler)
            except OSError:
                if self._port == 0:
                    raise
                self._server = ThreadingHTTPServer((self._host, 0), handler)
                self._port_collision = True
            self._port = int(self._server.server_address[1])
            if self._port_collision:
                self._message = (
                    f"Порт {self._requested_port} занят. Dashboard запущен на "
                    f"свободном порту {self._port}."
                )
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                name="AnkiStudyReportDashboardServer",
                daemon=True,
            )
            self._server_thread.start()
            log_event(
                "server.start",
                "Dashboard server started",
                port=self._port,
                requested_port=self._requested_port,
                port_collision=self._port_collision,
            )

            if self._idle_timeout_seconds > 0:
                self._monitor_thread = threading.Thread(
                    target=self._monitor_idle,
                    name="AnkiStudyReportDashboardIdleMonitor",
                    daemon=True,
                )
                self._monitor_thread.start()

            return self.state()

    def stop(self) -> None:
        """Stop the server. Safe to call repeatedly."""

        with self._lock:
            server = self._server
            self._server = None
            self._stop_event.set()
            self._token = None

        if server is not None:
            server.shutdown()
            server.server_close()

        with self._lock:
            self._server_thread = None
            self._monitor_thread = None
            self._started_at = None
            self._last_request_at = None
            self._port_collision = False
            self._message = None
            report_dir = self._report_dir
            self._report_dir = None
            self._report_path = None

        if report_dir is not None:
            shutil.rmtree(report_dir, ignore_errors=True)
        log_event("server.stop", "Dashboard server stopped")

    def publish_report(self, report: dict[str, Any]) -> None:
        """Write the current report JSON into temporary server storage."""

        with self._lock:
            if self._report_dir is None:
                self._report_dir = Path(
                    tempfile.mkdtemp(prefix="anki-study-report-dashboard-")
                )
            self._report_path = self._report_dir / "report.json"
            payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            self._report_path.write_bytes(payload)
            self._last_request_at = time.time()
            log_event("report.publish", "Report published", bytes=len(payload))

    def clear_report(self) -> None:
        with self._lock:
            report_path = self._report_path
            self._report_path = None
        if report_path is not None:
            try:
                report_path.unlink()
            except OSError:
                pass

    def touch(self) -> None:
        with self._lock:
            self._last_request_at = time.time()

    def configure_cache_handlers(
        self,
        status_provider=None,
        rebuild_handler=None,
        refresh_handler=None,
    ) -> None:
        with self._lock:
            self._cache_status_provider = status_provider
            self._cache_rebuild_handler = rebuild_handler
            self._cache_refresh_handler = refresh_handler

    def configure_action_handler(self, action_handler=None) -> None:
        with self._lock:
            self._action_handler = action_handler

    def configure_server_handlers(
        self,
        action_handler=None,
        status_provider=None,
    ) -> None:
        with self._lock:
            self._server_action_handler = action_handler
            self._server_status_provider = status_provider

    def configure_health_handler(self, health_provider=None) -> None:
        with self._lock:
            self._health_provider = health_provider

    def configure_display_settings_handlers(
        self,
        settings_provider=None,
        settings_handler=None,
    ) -> None:
        with self._lock:
            self._display_settings_provider = settings_provider
            self._display_settings_handler = settings_handler

    def configure_profile_handlers(self, profile_provider=None, profile_handler=None) -> None:
        with self._lock:
            self._profile_provider = profile_provider
            self._profile_handler = profile_handler

    def configure_product_notice_handlers(
        self,
        notices_provider=None,
        release_seen_handler=None,
        privacy_provider=None,
        privacy_handler=None,
    ) -> None:
        with self._lock:
            self._product_notices_provider = notices_provider
            self._product_notice_seen_handler = release_seen_handler
            self._privacy_provider = privacy_provider
            self._privacy_handler = privacy_handler

    def configure_telemetry_handlers(
        self,
        status_provider=None,
        event_handler=None,
        delete_handler=None,
        check_handler=None,
    ) -> None:
        with self._lock:
            self._telemetry_status_provider = status_provider
            self._telemetry_event_handler = event_handler
            self._telemetry_delete_handler = delete_handler
            self._telemetry_check_handler = check_handler

    def configure_statistics_handler(self, query_handler=None) -> None:
        with self._lock:
            self._statistics_query_handler = query_handler

    def configure_fsrs_handler(self, query_handler=None) -> None:
        with self._lock:
            self._fsrs_query_handler = query_handler

    def configure_search_handlers(self, query_handler=None, inspect_handler=None) -> None:
        with self._lock:
            self._search_query_handler = query_handler
            self._search_inspect_handler = inspect_handler

    def configure_entity_action_handlers(self, card_handler=None, note_handler=None) -> None:
        with self._lock:
            self._card_action_handler = card_handler
            self._note_action_handler = note_handler

    def configure_media_handler(self, media_file_provider=None) -> None:
        with self._lock:
            self._media_file_provider = media_file_provider

    def cache_status(self) -> dict[str, Any]:
        with self._lock:
            provider = self._cache_status_provider
        if provider is None:
            return {"status": "error", "error": "Statistics cache is not configured."}
        try:
            return provider()
        except Exception:
            traceback.print_exc()
            return {"status": "error", "error": "Statistics cache status failed."}

    def request_cache_rebuild(self) -> dict[str, Any]:
        with self._lock:
            handler = self._cache_rebuild_handler
        if handler is None:
            return {"ok": False, "status": "error", "error": "Statistics cache is not configured."}
        try:
            return handler()
        except Exception:
            traceback.print_exc()
            return {"ok": False, "status": "error", "error": "Statistics cache rebuild failed."}

    def request_cache_refresh(self) -> dict[str, Any]:
        with self._lock:
            handler = self._cache_refresh_handler
        if handler is None:
            return {"ok": False, "status": "error", "error": "Statistics cache is not configured."}
        try:
            return handler()
        except Exception:
            traceback.print_exc()
            return {"ok": False, "status": "error", "error": "Statistics cache refresh failed."}

    def request_action(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            handler = self._action_handler
        if handler is None:
            return _action_error(action, "Dashboard actions are not configured.")
        try:
            return handler(action, payload or {})
        except Exception:
            traceback.print_exc()
            log_exception("action.error", "Dashboard action failed", action=action)
            return _action_error(action, "Dashboard action failed.")

    def request_server_action(self, action: str) -> dict[str, Any]:
        with self._lock:
            handler = self._server_action_handler
        if handler is None:
            return _action_error(action, "Server actions are not configured.")
        try:
            return handler(action)
        except Exception:
            traceback.print_exc()
            log_exception("server.action.error", "Server action failed", action=action)
            return _action_error(action, "Server action failed.")

    def server_status(self) -> dict[str, Any]:
        state = _state_to_dict(self.state())
        with self._lock:
            provider = self._server_status_provider
        if provider is None:
            return state
        try:
            extra = provider()
        except Exception:
            traceback.print_exc()
            log_exception("server.status.error", "Server status failed")
            extra = {"error": "Server status failed."}
        if isinstance(extra, dict):
            state.update(extra)
        return state

    def health(self) -> dict[str, Any]:
        state = self.state()
        payload: dict[str, Any] = {
            "ok": state.running,
            "addon": "Anki Study Report",
            "mode": "normal",
            "profile": None,
            "hasReport": state.report_available,
        }
        with self._lock:
            provider = self._health_provider
        if provider is not None:
            try:
                extra = provider()
            except Exception:
                traceback.print_exc()
                log_exception("server.health.error", "Dashboard health check failed")
                extra = {"ok": False, "error": "Dashboard health check failed."}
            if isinstance(extra, dict):
                payload.update(extra)
        payload["ok"] = bool(payload.get("ok", True)) and state.running
        payload["hasReport"] = bool(payload.get("hasReport", state.report_available))
        return payload

    def display_settings(self) -> dict[str, Any]:
        with self._lock:
            provider = self._display_settings_provider
        if provider is None:
            return {"status": "error", "error": "Dashboard settings are not configured."}
        try:
            return provider()
        except Exception:
            traceback.print_exc()
            return {"status": "error", "error": "Dashboard settings failed."}

    def update_display_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._display_settings_handler
        if handler is None:
            return {"ok": False, "error": "Dashboard settings are not configured."}
        try:
            return handler(payload)
        except Exception:
            traceback.print_exc()
            log_exception("settings.update.error", "Dashboard settings update failed")
            return {"ok": False, "error": "Dashboard settings update failed."}

    def profile(self) -> dict[str, Any]:
        with self._lock:
            provider = self._profile_provider
        if provider is None:
            return {"ok": False, "error": "Profile is not configured."}
        try:
            return provider()
        except Exception:
            traceback.print_exc()
            log_exception("profile.read.error", "Profile read failed")
            return {"ok": False, "error": "Profile read failed."}

    def update_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._profile_handler
        if handler is None:
            return {"ok": False, "error": "Profile is not configured."}
        try:
            return handler(payload)
        except Exception:
            traceback.print_exc()
            log_exception("profile.update.error", "Profile update failed")
            return {"ok": False, "error": "Profile update failed."}

    def product_notices(self) -> dict[str, Any]:
        with self._lock:
            provider = self._product_notices_provider
        if provider is None:
            return {"ok": False, "error": "product_notices_unavailable"}
        try:
            result = provider()
            return result if isinstance(result, dict) else {"ok": False, "error": "product_notices_unavailable"}
        except Exception:
            log_exception("product_notices.read.error", "Product notices read failed")
            return {"ok": False, "error": "product_notices_unavailable"}

    def mark_product_release_seen(self) -> dict[str, Any]:
        with self._lock:
            handler = self._product_notice_seen_handler
        if handler is None:
            return {"ok": False, "error": "product_notices_unavailable"}
        try:
            result = handler()
            return result if isinstance(result, dict) else {"ok": False, "error": "product_notices_unavailable"}
        except Exception:
            log_exception("product_notices.update.error", "Product notice update failed")
            return {"ok": False, "error": "product_notices_unavailable"}

    def privacy(self) -> dict[str, Any]:
        with self._lock:
            provider = self._privacy_provider
        if provider is None:
            return {"ok": False, "error": "privacy_unavailable"}
        try:
            result = provider()
            return result if isinstance(result, dict) else {"ok": False, "error": "privacy_unavailable"}
        except Exception:
            log_exception("privacy.read.error", "Privacy state read failed")
            return {"ok": False, "error": "privacy_unavailable"}

    def update_privacy(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._privacy_handler
        if handler is None:
            return {"ok": False, "error": "privacy_unavailable"}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {"ok": False, "error": "privacy_unavailable"}
        except Exception:
            log_exception("privacy.update.error", "Privacy state update failed")
            return {"ok": False, "error": "privacy_unavailable"}

    def telemetry_status(self) -> dict[str, Any]:
        with self._lock:
            provider = self._telemetry_status_provider
        if provider is None:
            return {"ok": False, "error": "telemetry_unavailable"}
        try:
            result = provider()
            return result if isinstance(result, dict) else {"ok": False, "error": "telemetry_unavailable"}
        except Exception:
            log_exception("telemetry.status.error", "Telemetry status read failed")
            return {"ok": False, "error": "telemetry_unavailable"}

    def queue_telemetry_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._telemetry_event_handler
        if handler is None:
            return {"ok": False, "error": "telemetry_unavailable"}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {"ok": False, "error": "telemetry_unavailable"}
        except Exception:
            log_exception("telemetry.event.error", "Telemetry event validation failed")
            return {"ok": False, "error": "telemetry_unavailable"}

    def delete_telemetry_data(self) -> dict[str, Any]:
        with self._lock:
            handler = self._telemetry_delete_handler
        if handler is None:
            return {"ok": False, "error": "telemetry_unavailable"}
        try:
            result = handler()
            return result if isinstance(result, dict) else {"ok": False, "error": "telemetry_unavailable"}
        except Exception:
            log_exception("telemetry.delete.error", "Telemetry deletion request failed")
            return {"ok": False, "error": "telemetry_unavailable"}

    def check_telemetry_connection(self) -> dict[str, Any]:
        with self._lock:
            handler = self._telemetry_check_handler
        if handler is None:
            return {"ok": False, "error": "telemetry_unavailable"}
        try:
            result = handler()
            return result if isinstance(result, dict) else {"ok": False, "error": "telemetry_unavailable"}
        except Exception:
            log_exception("telemetry.check.error", "Telemetry connection check failed")
            return {"ok": False, "error": "telemetry_unavailable"}

    def query_statistics(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._statistics_query_handler
        if handler is None:
            return {"ok": False, "error": "statistics_unavailable", "message": "Statistics is not configured."}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {"ok": False, "error": "statistics_unavailable"}
        except Exception:
            traceback.print_exc()
            log_exception("statistics.query.error", "Statistics query failed")
            return {"ok": False, "error": "statistics_query_failed", "message": "Statistics query failed."}

    def query_fsrs(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = self._fsrs_query_handler
        if handler is None:
            return {"ok": False, "error": "fsrs_unavailable", "message": "FSRS analytics is not configured."}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {"ok": False, "error": "fsrs_unavailable"}
        except Exception:
            traceback.print_exc()
            log_exception("statistics.fsrs.error", "FSRS query failed")
            return {"ok": False, "error": "fsrs_query_failed", "message": "FSRS query failed."}

    def query_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_search("_search_query_handler", payload)

    def inspect_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_search("_search_inspect_handler", payload)

    def _request_search(self, handler_attribute: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            handler = getattr(self, handler_attribute)
        if handler is None:
            return {"ok": False, "error": "search_unavailable", "message": "Search is not configured."}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {
                "ok": False,
                "error": "search_failed",
                "message": "The search request failed.",
            }
        except Exception as error:
            frames = traceback.extract_tb(error.__traceback__)[-12:]
            log_event(
                "search.request.error",
                "Search request handler failed",
                exception_type=type(error).__name__,
                stack=[f"{frame.name}:{frame.lineno}" for frame in frames],
            )
            return {"ok": False, "error": "search_failed", "message": "The search request failed."}

    def request_entity_action(self, entity_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        attribute = "_card_action_handler" if entity_type == "cards" else "_note_action_handler"
        with self._lock:
            handler = getattr(self, attribute)
        if handler is None:
            return {"ok": False, "error": "entity_action_unavailable", "message": "Entity actions are not configured."}
        try:
            result = handler(payload)
            return result if isinstance(result, dict) else {
                "ok": False,
                "error": "entity_action_failed",
                "message": "The entity action failed.",
            }
        except Exception as error:
            frames = traceback.extract_tb(error.__traceback__)[-12:]
            log_event(
                "entity.action.request.error",
                "Entity action request handler failed",
                entity_type=entity_type,
                exception_type=type(error).__name__,
                stack=[f"{frame.name}:{frame.lineno}" for frame in frames],
            )
            return {"ok": False, "error": "entity_action_failed", "message": "The entity action failed."}

    def media_file(self, name: str) -> tuple[bytes, str] | None:
        with self._lock:
            provider = self._media_file_provider
        if provider is None:
            return None
        try:
            result = provider(name)
        except Exception:
            traceback.print_exc()
            log_exception("media.resolve.error", "Dashboard media lookup failed")
            return None
        if not isinstance(result, tuple) or len(result) != 2:
            return None
        payload, suffix = result
        if not isinstance(payload, (bytes, bytearray)):
            return None
        return bytes(payload), str(suffix or "").lower()

    def state(self) -> DashboardServerState:
        with self._lock:
            running = self._server is not None
            static_available = self._static_dir is not None
            return DashboardServerState(
                running=running,
                url=self.url() if running else None,
                host=self._host,
                port=self._port,
                requested_port=self._requested_port,
                port_collision=self._port_collision,
                message=self._message,
                static_dir=str(self._static_dir) if self._static_dir is not None else None,
                static_available=static_available,
                started_at=_format_ts(self._started_at),
                last_request_at=_format_ts(self._last_request_at),
                idle_timeout_seconds=self._idle_timeout_seconds,
                report_available=(
                    self._report_path is not None and self._report_path.is_file()
                ),
                report_path=str(self._report_path) if self._report_path else None,
            )

    def url(self) -> str:
        return f"http://{self._host}:{self._port}/?token={self._token or ''}"

    def token_is_valid(self, token: str | None) -> bool:
        with self._lock:
            expected = self._token
        return bool(expected and token and secrets.compare_digest(token, expected))

    def _monitor_idle(self) -> None:
        while not self._stop_event.wait(5):
            with self._lock:
                if self._server is None:
                    return
                last_request_at = self._last_request_at or time.time()
                timeout = self._idle_timeout_seconds
            if timeout > 0 and time.time() - last_request_at >= timeout:
                self.stop()
                return


class _DashboardRequestHandler(BaseHTTPRequestHandler):
    manager: DashboardServerManager

    def __init__(self, *args: Any, manager: DashboardServerManager, **kwargs: Any) -> None:
        self.manager = manager
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        self.manager.touch()
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/status":
            self._send_json(_state_to_dict(self.manager.state()))
            return
        if path == "/api/health":
            self._send_health(_query_token(parsed))
            return
        if path == "/api/server/status":
            self._send_server_status(_query_token(parsed))
            return
        if path == "/api/report":
            self._send_report(_query_token(parsed))
            return
        if path == "/api/media":
            self._send_media(_query_token(parsed), parsed)
            return
        if path == "/api/cache/status":
            self._send_cache_status(_query_token(parsed))
            return
        if path == "/api/dashboard/settings":
            self._send_dashboard_settings(_query_token(parsed))
            return
        if path == "/api/profile":
            self._send_profile(_query_token(parsed))
            return
        if path == "/api/product-notices":
            self._send_product_notices(_query_token(parsed))
            return
        if path == "/api/privacy":
            self._send_privacy(_query_token(parsed))
            return
        if path == "/api/telemetry/status":
            self._send_telemetry_status(_query_token(parsed))
            return
        if path in {"/api/telemetry/events", "/api/telemetry/delete", "/api/telemetry/check-send"}:
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json(
                    {"ok": False, "error": "method_not_allowed", "message": "Use POST for telemetry operations."},
                    HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return
        if path == "/api/product-notices/seen":
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json(
                    {"ok": False, "error": "method_not_allowed", "message": "Use POST to mark release notes seen."},
                    HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return
        if path == "/api/statistics/query":
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json(
                    {"ok": False, "error": "method_not_allowed", "message": "Use POST for statistics queries."},
                    HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return
        if path == "/api/statistics/fsrs/query":
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json({"ok": False, "error": "method_not_allowed", "message": "Use POST for FSRS queries."}, HTTPStatus.METHOD_NOT_ALLOWED)
            return
        if path in {"/api/search/query", "/api/search/inspect"}:
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json(
                    {"ok": False, "error": "method_not_allowed", "message": "Use POST for search requests."},
                    HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return
        if path in {"/api/entities/cards/actions", "/api/entities/notes/actions"}:
            if not self.manager.token_is_valid(_query_token(parsed)):
                self._send_forbidden()
            else:
                self._send_json(
                    {"ok": False, "error": "method_not_allowed", "message": "Use POST for entity actions."},
                    HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return
        if path == "/api/logs/status":
            self._send_logs_status(_query_token(parsed))
            return
        if path == "/api/logs/recent":
            self._send_recent_logs(_query_token(parsed), parsed)
            return
        if path == "/api/logs/download":
            self._send_log_download(_query_token(parsed))
            return
        if path == "/api/integrations/status":
            self._send_integrations_status(_query_token(parsed))
            return

        state = self.manager.state()
        if not state.static_available or state.static_dir is None:
            self._send_builtin_dashboard()
            return

        static_dir = Path(state.static_dir)
        target = _safe_static_target(static_dir, path)
        if target is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_file(target)

    def do_POST(self) -> None:
        self.manager.touch()
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/cache/rebuild":
            self._send_cache_action(_query_token(parsed), "rebuild")
            return
        if path == "/api/cache/refresh":
            self._send_cache_action(_query_token(parsed), "refresh")
            return
        if path.startswith("/api/server/"):
            action = path.removeprefix("/api/server/").strip("/")
            self._send_server_action(_query_token(parsed), action)
            return
        if path == "/api/logs/clear":
            self._send_clear_logs(_query_token(parsed))
            return
        if path == "/api/dashboard/settings":
            self._send_dashboard_settings_update(_query_token(parsed))
            return
        if path == "/api/profile":
            self._send_profile_update(_query_token(parsed))
            return
        if path == "/api/product-notices/seen":
            self._send_product_release_seen(_query_token(parsed))
            return
        if path == "/api/privacy":
            self._send_privacy_update(_query_token(parsed))
            return
        if path == "/api/telemetry/events":
            self._send_telemetry_event(_query_token(parsed))
            return
        if path == "/api/telemetry/delete":
            self._send_telemetry_delete(_query_token(parsed))
            return
        if path == "/api/telemetry/check-send":
            self._send_telemetry_check(_query_token(parsed))
            return
        if path == "/api/statistics/query":
            self._send_statistics_query(_query_token(parsed))
            return
        if path == "/api/statistics/fsrs/query":
            self._send_fsrs_query(_query_token(parsed))
            return
        if path == "/api/search/query":
            self._send_search_request(_query_token(parsed), inspect=False)
            return
        if path == "/api/search/inspect":
            self._send_search_request(_query_token(parsed), inspect=True)
            return
        if path == "/api/entities/cards/actions":
            self._send_entity_action(_query_token(parsed), "cards")
            return
        if path == "/api/entities/notes/actions":
            self._send_entity_action(_query_token(parsed), "notes")
            return
        if path.startswith("/api/actions/"):
            action = path.removeprefix("/api/actions/").strip("/")
            self._send_dashboard_action(_query_token(parsed), action)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_forbidden(self) -> None:
        log_event(
            "security.token_failed",
            "Dashboard token validation failed",
            path=urlparse(self.path).path,
        )
        payload = json.dumps(
            {
                "error": "invalid_dashboard_token",
                "ok": False,
                "message": "Недействительная ссылка dashboard. Откройте dashboard из Anki Study Report.",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(HTTPStatus.FORBIDDEN)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_server_status(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        self._send_json(self.manager.server_status())

    def _send_health(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self.manager.health()
        status = HTTPStatus.OK if payload.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE
        self._send_json(payload, status)

    def _send_server_action(self, token: str | None, action: str) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        if action in {"open-dashboard", "copy-url"}:
            result = self.manager.request_server_action(action)
            self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)
            return
        if action in {"restart", "stop"}:
            self._send_json(
                _dashboard_action_ok(action, f"Server {action} scheduled."),
                HTTPStatus.OK,
            )
            self._run_server_action_after_response(action)
            return
        self._send_json(_action_error(action, "Unknown server action."), HTTPStatus.NOT_FOUND)

    def _run_server_action_after_response(self, action: str) -> None:
        def run() -> None:
            time.sleep(0.1)
            self.manager.request_server_action(action)

        threading.Thread(
            target=run,
            name=f"AnkiStudyReportServerAction-{action}",
            daemon=True,
        ).start()

    def _send_logs_status(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        self._send_json(log_status())

    def _send_integrations_status(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        self._send_json(self.manager.server_status().get("integrations", {"items": []}))

    def _send_recent_logs(self, token: str | None, parsed) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        max_bytes = _query_int(parsed, "max_bytes", 200_000)
        text = read_recent_logs(max_bytes=max_bytes)
        self._send_json({"ok": True, "text": text, "status": log_status(max_bytes=max_bytes)})

    def _send_log_download(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        text = read_recent_logs(max_bytes=1_000_000)
        payload = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="anki_study_report.log"')
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_clear_logs(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        clear_logs()
        log_event("logs.clear", "Extension logs cleared")
        self._send_json({"ok": True, "message": "Logs cleared.", "status": log_status()})

    def _send_builtin_dashboard(self) -> None:
        payload = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Anki Study Report Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1624;
      --surface: #151f2e;
      --elevated: #1d2a3d;
      --border: #2b3a50;
      --text: #e8f0ff;
      --muted: #8fa3bf;
      --blue: #3db4f2;
      --purple: #7c5cff;
      --success: #67d391;
      --warning: #f6c177;
      --danger: #ef6f6c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 12% -6%, rgba(61, 180, 242, .14), transparent 34rem),
        radial-gradient(circle at 88% 2%, rgba(124, 92, 255, .12), transparent 30rem),
        var(--bg);
      color: var(--text);
      font-family: "Inter", "Segoe UI", "Noto Sans", "Yu Gothic UI", "Meiryo", ui-sans-serif, system-ui, Arial, sans-serif;
      font-size: 15px;
      line-height: 1.5;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      font-feature-settings: "kern" 1, "liga" 1;
    }
    .shell { width: min(1760px, calc(100% - 32px)); margin: 0 auto; padding: 16px 0 28px; }
    header, section, .card {
      background: rgba(21, 31, 46, .96);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 18px 50px rgba(3, 8, 20, .22);
    }
    header { padding: 18px; margin-bottom: 16px; }
    h1, h2, h3, p { margin: 0; }
    h1, h2, h3 { font-family: "Inter", "Segoe UI", "Noto Sans", "Yu Gothic UI", "Meiryo", ui-sans-serif, system-ui, Arial, sans-serif; }
    h1 { font-size: 24px; }
    h2 { font-size: 18px; margin-bottom: 14px; }
    h3 { font-size: 15px; line-height: 1.45; }
    section { padding: 18px; margin-bottom: 16px; min-width: 0; }
    .meta, .chips, .grid, .hero-grid, .two-col, .cards { display: grid; gap: 12px; }
    .meta { display: flex; flex-wrap: wrap; margin-top: 12px; }
    .chip, .pill {
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(29, 42, 61, .72);
      color: var(--muted);
      padding: 6px 10px;
      font-size: 12px;
    }
    .hero {
      background: linear-gradient(135deg, rgba(21,31,46,.98), rgba(29,42,61,.98));
      border-color: rgba(61, 180, 242, .32);
    }
    .verdict { max-width: 1100px; font-size: clamp(22px, 2vw, 34px); line-height: 1.25; font-weight: 700; }
    .subtle { color: var(--muted); line-height: 1.6; }
    .grid { grid-template-columns: repeat(1, minmax(0, 1fr)); }
    .kpis { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
    .two-col { grid-template-columns: minmax(0, 1fr); }
    .hero-grid { grid-template-columns: minmax(0, 1fr); margin-top: 18px; }
    .card { padding: 14px; min-width: 0; }
    .card-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    .card-value { margin-top: 8px; font-size: 26px; font-weight: 700; }
    .good { border-color: rgba(103, 211, 145, .38); color: var(--success); }
    .neutral { border-color: rgba(61, 180, 242, .28); color: var(--blue); }
    .warning { border-color: rgba(246, 193, 119, .4); color: var(--warning); }
    .danger { border-color: rgba(239, 111, 108, .42); color: var(--danger); }
    .bar-row { display: grid; grid-template-columns: 86px minmax(0, 1fr) 64px; gap: 10px; align-items: center; margin: 10px 0; }
    .bar { height: 11px; background: #111827; border-radius: 999px; overflow: hidden; border: 1px solid var(--border); }
    .bar span { display: block; height: 100%; border-radius: 999px; }
    .deck-list { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    .deck-name { overflow-wrap: anywhere; }
    .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
    table { width: 100%; min-width: 880px; border-collapse: collapse; font-size: 14px; }
    th, td { padding: 11px 12px; border-bottom: 1px solid rgba(43, 58, 80, .75); text-align: left; vertical-align: top; }
    th { color: var(--muted); background: var(--elevated); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    td.num, th.num { text-align: right; white-space: nowrap; }
    .table-details { margin-top: 12px; border: 1px solid var(--border); border-radius: 10px; background: rgba(17, 24, 39, .45); overflow: hidden; }
    .table-details summary { cursor: pointer; padding: 12px; color: var(--blue); font-weight: 700; }
    .table-details .table-wrap { border: 0; border-top: 1px solid var(--border); border-radius: 0; }
    .heatmap { display: grid; grid-template-columns: repeat(auto-fill, minmax(18px, 1fr)); gap: 7px; }
    .day { aspect-ratio: 1; border-radius: 5px; border: 1px solid var(--border); background: #111827; }
    .actions { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .empty { padding: 24px; border: 1px dashed var(--border); border-radius: 10px; color: var(--muted); text-align: center; }
    @media (min-width: 1000px) {
      .two-col { grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr); }
      .hero-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }
    @media (max-width: 520px) {
      .shell { width: min(100% - 24px, 1760px); }
      header, section { padding: 14px; }
      .verdict { font-size: 22px; }
      .bar-row { grid-template-columns: 72px minmax(0, 1fr) 52px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="empty" data-testid="dashboard-static-fallback">
      <h1>Dashboard работает в fallback-режиме</h1>
      <p>Собранные React assets отсутствуют или неполные. Используется встроенная диагностическая страница; для полного dashboard пересоберите assets через build:addon и проверьте package validation.</p>
    </section>
  </div>
  <div class="shell" id="app">
    <section class="empty">Загрузка отчёта...</section>
  </div>
  <script>
    const statusClass = (value) => ["good", "neutral", "warning", "danger"].includes(value) ? value : "neutral";
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[char]));
    const pct = (value) => `${Math.round((Number(value) || 0) * 100)}%`;
    const int = (value) => Number(value) || 0;
    const maxOf = (items, key) => Math.max(1, ...items.map((item) => int(item[key])));
    const colorForStatus = (status) => ({
      good: "var(--success)",
      neutral: "var(--blue)",
      warning: "var(--warning)",
      danger: "var(--danger)"
    }[statusClass(status)]);
    const heatColor = (reviews, max) => {
      const ratio = int(reviews) / Math.max(1, max);
      if (ratio <= 0) return "#111827";
      if (ratio > .75) return "var(--blue)";
      if (ratio > .5) return "#287eaf";
      if (ratio > .25) return "#1d5578";
      return "#17364f";
    };
    let selectedHeatmapYear = null;
    function chip(label, value) {
      return `<span class="chip"><span>${escapeHtml(label)}:&nbsp;</span><strong>${escapeHtml(value)}</strong></span>`;
    }
    function deckScopeSummary(decks) {
      const clean = (Array.isArray(decks) ? decks : []).map((deck) => String(deck || "").trim()).filter(Boolean);
      if (!clean.length || (clean.length === 1 && clean[0].toLowerCase() === "все колоды")) return "Все колоды";
      if (clean.length <= 3) return `${clean.length} ${deckWord(clean.length)}: ${clean.join(", ")}`;
      return `${clean.length} ${deckWord(clean.length)}: ${clean.slice(0, 3).join(", ")} + ещё ${clean.length - 3}`;
    }
    function deckWord(count) {
      const mod10 = count % 10;
      const mod100 = count % 100;
      if (mod10 === 1 && mod100 !== 11) return "колода";
      if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "колоды";
      return "колод";
    }
    function kpi(metric) {
      return `<article class="card ${statusClass(metric.status)}">
        <div class="card-label">${escapeHtml(metric.label)}</div>
        <div class="card-value">${escapeHtml(metric.value)}</div>
        <p class="subtle">${escapeHtml(metric.caption)}</p>
      </article>`;
    }
    function bars(items, totalKey = "value") {
      const max = maxOf(items, totalKey);
      return items.map((item) => `<div class="bar-row">
        <span class="subtle">${escapeHtml(item.label ?? item.day ?? item.offset)}</span>
        <div class="bar"><span style="width:${Math.max(2, int(item[totalKey]) / max * 100)}%;background:${escapeHtml(item.color || "var(--blue)")};"></span></div>
        <strong>${escapeHtml(item[totalKey])}</strong>
      </div>`).join("");
    }
    function deckCard(deck) {
      return `<article class="card ${statusClass(deck.status)}">
        <h3 class="deck-name">${escapeHtml(deck.name)}</h3>
        <div class="hero-grid">
          <div><div class="card-label">Pass</div><strong>${pct(deck.passRate)}</strong></div>
          <div><div class="card-label">Fail</div><strong>${escapeHtml(deck.failCount)}</strong></div>
          <div><div class="card-label">Avg</div><strong>${escapeHtml(deck.averageAnswerSeconds)}s</strong></div>
        </div>
        <p class="subtle" style="margin-top:12px">${escapeHtml(deck.explanation)}</p>
      </article>`;
    }
    function deckRow(deck) {
      return `<tr><td class="deck-name">${escapeHtml(deck.name)}<br><span class="subtle">${escapeHtml(deck.explanation)}</span></td><td class="num">${escapeHtml(deck.totalReviews)}</td><td class="num">${escapeHtml(deck.newCards)}</td><td class="num">${pct(deck.passRate)}</td><td class="num">${escapeHtml(deck.failCount)}</td><td class="num">${escapeHtml(deck.averageAnswerSeconds)}s</td><td><span class="pill ${statusClass(deck.status)}">${escapeHtml(deck.status)}</span></td></tr>`;
    }
    function comparisonDelta(value, suffix = "") {
      if (value == null || !Number.isFinite(Number(value))) return "нет данных";
      const rounded = Math.round(Number(value));
      if (rounded === 0) return `→ 0${suffix}`;
      return `${rounded > 0 ? "↑ +" : "↓ -"}${Math.abs(rounded)}${suffix}`;
    }
    function comparisonPercent(value) {
      if (value == null || !Number.isFinite(Number(value))) return "нет истории";
      const rounded = Math.round(Number(value));
      if (Math.abs(rounded) < 1) return "→ около нормы";
      return `${rounded > 0 ? "↑" : "↓"} ${Math.abs(rounded)}% к норме`;
    }
    function comparisonSection(comparison) {
      const data = comparison || {};
      if (!data.available) {
        return `<section><h2>Сегодня против нормы</h2><div class="empty">${escapeHtml(data.message || "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.")}</div></section>`;
      }
      const today = data.today || {};
      const baseline = data.baselines?.avg7 || {};
      const delta = data.comparisons?.avg7 || {};
      const insightHtml = (data.insights || []).slice(0, 3).map((item) => `<article class="card ${item.severity === "positive" ? "good" : statusClass(item.severity)}"><h3>${escapeHtml(item.title)}</h3><p class="subtle">${escapeHtml(item.text)}</p></article>`).join("");
      return `<section>
        <h2>Сегодня против нормы</h2>
        <p class="subtle">Сегодня против ${escapeHtml(baseline.label || "7-дневной нормы")}</p>
        <div class="grid kpis" style="margin-top:12px">
          ${kpi({label:"Reviews", value: today.reviews || 0, caption:`${comparisonDelta(delta.reviews?.delta)} · ${comparisonPercent(delta.reviews?.percentDelta)}`, status:"neutral"})}
          ${kpi({label:"Study time", value: `${today.studyMinutes || 0} мин`, caption:`${comparisonDelta(delta.studyMinutes?.delta, " мин")} · ${comparisonPercent(delta.studyMinutes?.percentDelta)}`, status:"neutral"})}
          ${kpi({label:"Pass rate", value: today.passRate == null ? "Нет данных" : pct(today.passRate), caption: comparisonDelta(delta.passRate?.deltaPp, " п.п."), status:"good"})}
          ${kpi({label:"New cards", value: today.newCards || 0, caption:`${comparisonDelta(delta.newCards?.delta)} · ${comparisonPercent(delta.newCards?.percentDelta)}`, status:"warning"})}
        </div>
        <div class="cards" style="margin-top:12px">${insightHtml}</div>
      </section>`;
    }
    function render(report) {
      const decks = report.decks || [];
      const deckTableLimit = 12;
      const visibleDecks = decks.slice(0, deckTableLimit);
      const hiddenDecks = decks.slice(deckTableLimit);
      const problemDecks = decks.filter((deck) => ["danger", "warning"].includes(deck.status)).slice(0, 3);
      const bestDecks = [...decks].filter((deck) => deck.status === "good").sort((a, b) => b.passRate - a.passRate).slice(0, 3);
      const activity = report.activity || {};
      const forecast = report.forecast || {};
      const fsrs = report.fsrs || {};
      const comparison = report.comparison || {};
      const days = activity.days || [];
      const years = [...new Set(days.map((day) => String(day.date || "").slice(0, 4)).filter(Boolean))].sort((a, b) => Number(b) - Number(a));
      const currentYear = String(new Date().getFullYear());
      if (!selectedHeatmapYear) selectedHeatmapYear = years.includes(currentYear) ? currentYear : (years[0] || currentYear);
      if (!years.includes(selectedHeatmapYear)) years.unshift(selectedHeatmapYear);
      const visibleDays = days.filter((day) => String(day.date || "").slice(0, 4) === selectedHeatmapYear);
      const dayMax = maxOf(visibleDays, "reviews");
      window.setHeatmapYear = (year) => { selectedHeatmapYear = String(year); render(report); };
      document.getElementById("app").innerHTML = `
        <header>
          <h1>${escapeHtml(report.metadata?.title || "Anki Study Report")}</h1>
          <div class="meta">
            ${chip("Период статистики", report.metadata?.period || "Всё время")}
            ${chip("Статистика по", deckScopeSummary(report.metadata?.selectedDecks))}
          </div>
        </header>
        <section class="hero">
          <span class="pill ${statusClass(report.summary?.riskLevel)}">risk level: ${escapeHtml(report.summary?.riskLevel || "neutral")}</span>
          <p class="verdict" style="margin-top:16px">${escapeHtml(report.summary?.verdict || "Отчёт готов.")}</p>
          <div class="hero-grid">
            <article class="card good"><div class="card-label">Главное действие</div><p>${escapeHtml(report.summary?.mainAction || "")}</p></article>
            <article class="card danger"><div class="card-label">Что тревожит</div><p>${escapeHtml(report.summary?.warning || "")}</p></article>
            <article class="card warning"><div class="card-label">Новые карточки</div><p>${escapeHtml(report.summary?.newCardsAdvice || "")}</p></article>
          </div>
        </section>
        <section><h2>KPI</h2><div class="grid kpis">${(report.kpis || []).map(kpi).join("")}</div></section>
        ${comparisonSection(comparison)}
        <div class="two-col">
          <section><h2>Answer Distribution</h2>${bars(report.answerDistribution || [])}</section>
          <section>
            <h2>Activity</h2>
            <div class="grid kpis">
              ${kpi({label:"Active days", value: activity.activeDays || 0, caption:"дни с повторениями", status:"good"})}
              ${kpi({label:"Missed days", value: activity.missedDays || 0, caption:"дни без повторений", status:"neutral"})}
              ${kpi({label:"Current streak", value:`${activity.currentStreak || 0} дней`, caption:"текущая серия", status:"good"})}
              ${kpi({label:"Best streak", value:`${activity.bestStreak || 0} дней`, caption:"лучшая серия", status:"good"})}
            </div>
            <div class="meta" style="margin-top:14px">
              <button type="button" onclick="window.setHeatmapYear(Number(selectedHeatmapYear)-1)">←</button>
              <select onchange="window.setHeatmapYear(this.value)">${years.map((year) => `<option value="${escapeHtml(year)}" ${year === selectedHeatmapYear ? "selected" : ""}>${escapeHtml(year)}</option>`).join("")}</select>
              <button type="button" onclick="window.setHeatmapYear(Number(selectedHeatmapYear)+1)">→</button>
            </div>
            ${visibleDays.length ? `<div class="heatmap" style="margin-top:14px">${visibleDays.map((day) => `<span class="day" title="${escapeHtml(day.date)}: ${escapeHtml(day.reviews)}" style="background:${heatColor(day.reviews, dayMax)}"></span>`).join("")}</div>` : `<div class="empty" style="margin-top:14px">Нет данных за выбранный год.</div>`}
          </section>
        </div>
        <section><h2>Problem Decks</h2>${problemDecks.length ? `<div class="deck-list">${problemDecks.map(deckCard).join("")}</div>` : `<div class="empty">Явных проблемных колод нет.</div>`}</section>
        <section><h2>Best Decks</h2>${bestDecks.length ? `<div class="deck-list">${bestDecks.map(deckCard).join("")}</div>` : `<div class="empty">Лучшие колоды пока не выделены.</div>`}</section>
        <section>
          <h2>Deck Performance Table</h2>
          <div class="table-wrap"><table>
            <thead><tr><th>Deck</th><th class="num">Reviews</th><th class="num">New</th><th class="num">Pass rate</th><th class="num">Fail</th><th class="num">Avg answer</th><th>Status</th></tr></thead>
            <tbody>${visibleDecks.map(deckRow).join("")}</tbody>
          </table></div>
          ${hiddenDecks.length ? `<details class="table-details"><summary>Показаны первые ${visibleDecks.length} строк, открыть ещё ${hiddenDecks.length}</summary><div class="table-wrap"><table><tbody>${hiddenDecks.map(deckRow).join("")}</tbody></table></div></details>` : ""}
        </section>
        <div class="two-col">
          <section><h2>Forecast</h2>
            <div class="grid kpis">
              ${kpi({label:"Tomorrow", value: forecast.tomorrow || 0, caption:"завтра", status:"good"})}
              ${kpi({label:"Next 7 days", value: forecast.next7Days || 0, caption:"7 дней", status:"neutral"})}
              ${kpi({label:"Next 30 days", value: forecast.next30Days || 0, caption:"30 дней", status:"neutral"})}
            </div>
            <p class="subtle" style="margin-top:14px">${escapeHtml(forecast.recommendation || "")}</p>
          </section>
          <section><h2>FSRS</h2>
            <div class="grid kpis">
              ${kpi({label:"Predicted recall", value: fsrs.predictedRecall == null ? "Нет данных" : pct(fsrs.predictedRecall), caption:"average recall", status:"neutral"})}
              ${kpi({label:"Below target", value: fsrs.cardsBelowTarget || 0, caption:"ниже target", status:"warning"})}
              ${kpi({label:"High forgetting risk", value: fsrs.highForgettingRisk || 0, caption:"риск забывания", status:"danger"})}
              ${kpi({label:"Future load", value: fsrs.futureLoad30Days || 0, caption:"FSRS load", status:"neutral"})}
            </div>
          </section>
        </div>
        <section class="hero">
          <h2>Recommendations / Next Actions</h2>
          <p class="verdict">${escapeHtml(report.recommendations?.mainAction || "")}</p>
          <p class="subtle" style="margin-top:10px">${escapeHtml(report.recommendations?.why || "")}</p>
          <div class="actions" style="margin-top:14px">${(report.recommendations?.checklist || []).map((item) => `<article class="card good">${escapeHtml(item)}</article>`).join("")}</div>
        </section>
        <section><h2>Technical Details</h2>
          <div class="grid kpis">
            ${kpi({label:"period", value: report.metadata?.period || "", caption:"", status:"neutral"})}
            ${kpi({label:"selected decks", value: deckScopeSummary(report.metadata?.selectedDecks), caption:"", status:"neutral"})}
            ${kpi({label:"created at", value: report.metadata?.createdAt || "", caption:"", status:"neutral"})}
            ${kpi({label:"include children", value: report.metadata?.includeChildren ? "yes" : "no", caption:"", status:"neutral"})}
            ${kpi({label:"answer mode", value: report.metadata?.answerMode || "", caption:"", status:"neutral"})}
            ${kpi({label:"deleted reviews", value: report.metadata?.deletedCardReviews || 0, caption:"", status:"neutral"})}
          </div>
        </section>
      `;
    }
    const token = new URLSearchParams(window.location.search).get("token") || "";
    fetch(`/api/report?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (response.status === 403) throw new Error("forbidden");
        if (!response.ok) throw new Error("No report");
        return response.json();
      })
      .then(render)
      .catch((error) => {
        if (error.message === "forbidden") {
          document.getElementById("app").innerHTML = `<section class="empty">
            <h1>Недействительная ссылка dashboard</h1>
            <p>Недействительная ссылка dashboard. Откройте dashboard из Anki Study Report.</p>
          </section>`;
          return;
        }
        document.getElementById("app").innerHTML = `<section class="empty">
          <h1>Отчёт для dashboard ещё не опубликован</h1>
          <p>Откройте основное окно Anki Study Report и нажмите “Открыть этот отчёт в dashboard”.</p>
        </section>`;
      });
  </script>
</body>
</html>
""".encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_report(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return

        state = self.manager.state()
        if state.report_path is None:
            self.send_error(HTTPStatus.NOT_FOUND, "No dashboard report has been published")
            return
        try:
            payload = Path(state.report_path).read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "No dashboard report has been published")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_media(self, token: str | None, parsed) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        name_values = parse_qs(parsed.query).get("name") or []
        name = _safe_media_name(name_values[0] if name_values else "")
        if not name:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid media name")
            return
        media = self.manager.media_file(name)
        if media is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Media not found")
            return
        payload, suffix = media
        self._send_bytes(payload, content_type=_media_content_type(suffix), cache_control="no-store")

    def _send_cache_status(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        self._send_json(self.manager.cache_status())

    def _send_cache_action(self, token: str | None, action: str) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        if action == "rebuild":
            self._send_json(self.manager.request_cache_rebuild())
            return
        if action == "refresh":
            self._send_json(self.manager.request_cache_refresh())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _send_dashboard_settings(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        self._send_json(self.manager.display_settings())

    def _send_dashboard_settings_update(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(_action_error("dashboard-settings", "Invalid JSON request body."), HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.update_display_settings(payload)
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

    def _send_profile(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        result = self.manager.profile()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_profile_update(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(_action_error("profile", "Invalid JSON request body."), HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.update_profile(payload)
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

    def _send_product_notices(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        result = self.manager.product_notices()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_product_release_seen(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None or payload:
            self._send_json(
                {"ok": False, "error": "invalid_product_notice_request", "message": "Expected an empty JSON object."},
                HTTPStatus.BAD_REQUEST,
            )
            return
        result = self.manager.mark_product_release_seen()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_privacy(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        result = self.manager.privacy()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_privacy_update(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(
                {"ok": False, "error": "invalid_privacy_choices", "message": "Invalid JSON request body."},
                HTTPStatus.BAD_REQUEST,
            )
            return
        result = self.manager.update_privacy(payload)
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

    def _send_telemetry_status(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        result = self.manager.telemetry_status()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_telemetry_event(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json({"ok": False, "error": "invalid_telemetry_event"}, HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.queue_telemetry_event(payload)
        status = HTTPStatus.OK if result.get("ok") else (
            HTTPStatus.BAD_REQUEST if result.get("error") == "invalid_telemetry_event" else HTTPStatus.SERVICE_UNAVAILABLE
        )
        self._send_json(result, status)

    def _send_telemetry_delete(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None or payload:
            self._send_json({"ok": False, "error": "invalid_telemetry_delete_request"}, HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.delete_telemetry_data()
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)

    def _send_telemetry_check(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None or payload:
            self._send_json({"ok": False, "error": "invalid_telemetry_check_request"}, HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.check_telemetry_connection()
        status = HTTPStatus.ACCEPTED if result.get("started") else (
            HTTPStatus.CONFLICT if result.get("code") in {"telemetry.sender_busy", "telemetry.deletion_pending"}
            else HTTPStatus.BAD_REQUEST if result.get("code") == "telemetry.manual_send_disabled"
            else HTTPStatus.SERVICE_UNAVAILABLE
        )
        self._send_json(result, status)

    def _send_statistics_query(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(
                {"ok": False, "error": "invalid_statistics_query", "message": "Invalid JSON request body."},
                HTTPStatus.BAD_REQUEST,
            )
            return
        result = self.manager.query_statistics(payload)
        if result.get("ok"):
            status = HTTPStatus.OK
        elif result.get("error") == "invalid_statistics_query":
            status = HTTPStatus.BAD_REQUEST
        elif result.get("error") in {"statistics_unavailable", "statistics_query_failed"}:
            status = HTTPStatus.SERVICE_UNAVAILABLE
        else:
            status = HTTPStatus.BAD_REQUEST
        self._send_json(result, status)

    def _send_fsrs_query(self, token: str | None) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json({"ok": False, "error": "invalid_fsrs_query", "message": "Invalid JSON request body."}, HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.query_fsrs(payload)
        if result.get("ok"):
            status = HTTPStatus.OK
        elif result.get("error") == "invalid_fsrs_query":
            status = HTTPStatus.BAD_REQUEST
        elif result.get("error") in {"fsrs_unavailable", "fsrs_query_failed"}:
            status = HTTPStatus.SERVICE_UNAVAILABLE
        else:
            status = HTTPStatus.BAD_REQUEST
        self._send_json(result, status)

    def _send_search_request(self, token: str | None, *, inspect: bool) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(
                {"ok": False, "error": "invalid_search_request", "message": "Invalid JSON request body."},
                HTTPStatus.BAD_REQUEST,
            )
            return
        result = self.manager.inspect_search(payload) if inspect else self.manager.query_search(payload)
        error = result.get("error")
        if result.get("ok"):
            status = HTTPStatus.OK
        elif error == "invalid_search_request":
            status = HTTPStatus.BAD_REQUEST
        elif error == "search_entity_not_found":
            status = HTTPStatus.NOT_FOUND
        elif error == "search_timeout":
            status = HTTPStatus.GATEWAY_TIMEOUT
        elif error in {"search_unavailable", "search_failed"}:
            status = HTTPStatus.SERVICE_UNAVAILABLE
        else:
            status = HTTPStatus.BAD_REQUEST
        self._send_json(result, status)

    def _send_dashboard_action(self, token: str | None, action: str) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(_action_error(action, "Invalid JSON request body."), HTTPStatus.BAD_REQUEST)
            return
        result = self.manager.request_action(action, payload)
        self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

    def _send_entity_action(self, token: str | None, entity_type: str) -> None:
        if not self.manager.token_is_valid(token):
            self._send_forbidden()
            return
        payload = self._read_json_body()
        if payload is None:
            self._send_json(
                {"ok": False, "error": "invalid_entity_action", "message": "Invalid JSON request body."},
                HTTPStatus.BAD_REQUEST,
            )
            return
        result = self.manager.request_entity_action(entity_type, payload)
        error = result.get("error")
        if result.get("ok"):
            status = HTTPStatus.OK
        elif error == "invalid_entity_action":
            status = HTTPStatus.BAD_REQUEST
        elif error == "entity_action_stale":
            status = HTTPStatus.CONFLICT
        elif error in {"cards.destination_not_found", "cards.filtered_source_unsupported"}:
            status = HTTPStatus.CONFLICT
        elif error == "cards.destination_filtered":
            status = HTTPStatus.BAD_REQUEST
        elif error == "entity_action_timeout":
            status = HTTPStatus.GATEWAY_TIMEOUT
        elif error in {"entity_action_unavailable", "entity_action_failed"}:
            status = HTTPStatus.SERVICE_UNAVAILABLE
        else:
            status = HTTPStatus.BAD_REQUEST
        self._send_json(result, status)

    def _read_json_body(self) -> dict[str, Any] | None:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            return {}
        try:
            length = int(length_header)
        except ValueError:
            return None
        if length < 0 or length > 8192:
            return None
        try:
            raw = self.rfile.read(length)
            if not raw:
                return {}
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def _send_file(self, target: Path, *, content_type: str | None = None, cache_control: str = "no-cache") -> None:
        try:
            payload = target.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_bytes(payload, content_type=content_type or _content_type(target), cache_control=cache_control)

    def _send_bytes(self, payload: bytes, *, content_type: str, cache_control: str = "no-cache") -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(payload)


def _find_static_dir() -> Path | None:
    package_dir = Path(__file__).resolve().parent
    candidates = [
        package_dir / "web_dashboard",
        package_dir.parent / "web-dashboard" / "dist",
    ]
    for candidate in candidates:
        if _static_dir_is_available(candidate):
            return candidate
    return None


def _static_dir_is_available(candidate: Path) -> bool:
    index_path = candidate / "index.html"
    if not index_path.is_file():
        return False
    try:
        index_html = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    manifest_path = candidate / "manifest.json"
    if manifest_path.is_file():
        try:
            graph = resolve_dashboard_asset_graph(index_html, manifest_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return False
        if graph["errors"] or graph["unsafe"]:
            return False
        relative_refs = graph["assets"]
    else:
        direct = extract_dashboard_html_refs(index_html)
        if direct["unsafe"]:
            return False
        relative_refs = direct["assets"]
    root = candidate.resolve()
    for relative_ref in relative_refs:
        target = (candidate / relative_ref).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return False
        try:
            if not target.is_file() or target.stat().st_size <= 0:
                return False
        except OSError:
            return False
    return True


def _safe_static_target(static_dir: Path, path: str) -> Path | None:
    decoded = unquote(str(path or ""))
    if decoded.startswith("//") or decoded.startswith("\\"):
        return None
    relative = decoded.lstrip("/") or "index.html"
    parts = relative.split("/")
    if (
        relative == "api"
        or relative.startswith("api/")
        or "\x00" in relative
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in parts)
        or ":" in parts[0]
    ):
        return None
    target = trusted_file_from_inventory(static_dir, relative)
    if target is not None:
        return target
    if relative.startswith("assets/"):
        return None
    return trusted_file_from_inventory(static_dir, "index.html")


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".png": "image/png",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".svg": "image/svg+xml",
        ".txt": "text/plain; charset=utf-8",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")


def _media_content_type(path: Path | str) -> str:
    suffix = path.suffix.lower() if isinstance(path, Path) else str(path or "").lower()
    return {
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
    }.get(suffix, "application/octet-stream")


def _safe_media_name(value: str) -> str:
    name = unquote(str(value or "").strip())
    if not name:
        return ""
    if "/" in name or "\\" in name or ".." in name or name.startswith("."):
        return ""
    if re.search(r"^[a-z][a-z0-9+.-]*:", name, flags=re.IGNORECASE):
        return ""
    if re.match(r"^[A-Za-z]:", name):
        return ""
    suffix = Path(name).suffix.lower().lstrip(".")
    if suffix not in {"gif", "png", "jpg", "jpeg", "webp", "mp3", "ogg", "wav", "m4a", "flac"}:
        return ""
    return name


def _safe_port(value: int) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    if port == 0:
        return 0
    if 1024 <= port <= 65535:
        return port
    return DEFAULT_PORT


def _query_token(parsed) -> str | None:
    values = parse_qs(parsed.query).get("token")
    if not values:
        return None
    return values[0]


def _query_int(parsed, name: str, fallback: int) -> int:
    values = parse_qs(parsed.query).get(name)
    if not values:
        return fallback
    try:
        return int(values[0])
    except (TypeError, ValueError):
        return fallback


def _action_error(action: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "action": action or "unknown",
        "error": message,
    }


def _dashboard_action_ok(action: str, message: str) -> dict[str, Any]:
    return {
        "ok": True,
        "action": action,
        "message": message,
    }


def _redact_token(url: str | None) -> str | None:
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.query:
        return url
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?token=..."


def _format_ts(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _state_to_dict(state: DashboardServerState) -> dict[str, Any]:
    return {
        "running": state.running,
        "url": _redact_token(state.url),
        "host": state.host,
        "port": state.port,
        "requested_port": state.requested_port,
        "port_collision": state.port_collision,
        "message": state.message,
        "token_required": True,
        "static_dir": _mask_path(state.static_dir),
        "static_available": state.static_available,
        "started_at": state.started_at,
        "last_request_at": state.last_request_at,
        "idle_timeout_seconds": state.idle_timeout_seconds,
        "report_available": state.report_available,
        "report_path": _mask_path(state.report_path),
    }


def _mask_path(value: str | None) -> str | None:
    if not value:
        return value
    try:
        path = Path(value)
        parts = path.resolve().parts
    except OSError:
        return value
    if "Users" in parts:
        index = parts.index("Users")
        if len(parts) > index + 2:
            return str(Path(*parts[: index + 2]) / "..." / Path(*parts[index + 3 :]))
    return str(path)
