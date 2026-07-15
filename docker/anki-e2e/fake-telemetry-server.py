#!/usr/bin/env python3
"""Deterministic loopback-only telemetry ingestion fake for real-Anki E2E."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import threading
from urllib.parse import urlparse


PURPOSES = {
    "addon.started": "reliabilityDiagnostics",
    "api_operation.failed": "reliabilityDiagnostics",
    "dashboard_startup.completed": "reliabilityDiagnostics",
    "dashboard.opened": "featureUsage",
    "page.opened": "featureUsage",
    "search.completed": "featureUsage",
    "entity_action.completed": "featureUsage",
}


class State:
    def __init__(self, summary_path: Path) -> None:
        self.lock = threading.RLock()
        self.summary_path = summary_path
        self.offline = False
        self.enrollments = 0
        self.event_batches = 0
        self.event_count = 0
        self.deletions = 0
        self.event_codes: dict[str, int] = {}
        self.event_purposes: dict[str, int] = {purpose: 0 for purpose in sorted(set(PURPOSES.values()))}
        self._persist()

    def public(self) -> dict[str, object]:
        with self.lock:
            return {
                "schemaVersion": 1,
                "offline": self.offline,
                "enrollments": self.enrollments,
                "eventBatches": self.event_batches,
                "eventCount": self.event_count,
                "deletions": self.deletions,
                "eventCodes": dict(sorted(self.event_codes.items())),
                "eventPurposes": dict(sorted(self.event_purposes.items())),
            }

    def _persist(self) -> None:
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.summary_path.with_suffix(self.summary_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.public(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.summary_path)


def handler_factory(state: State):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ASRTelemetryE2E/1"

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_GET(self) -> None:
            if urlparse(self.path).path == "/__e2e/state":
                self._json(HTTPStatus.OK, state.public())
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            body = self._body()
            if body is None:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            if path == "/__e2e/control":
                if set(body) - {"offline"} or not isinstance(body.get("offline"), bool):
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_control"})
                    return
                with state.lock:
                    state.offline = body["offline"]
                    state._persist()
                self._json(HTTPStatus.OK, state.public())
                return
            if state.offline:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "e2e_offline"})
                return
            if path == "/v1/installations":
                with state.lock:
                    state.enrollments += 1
                    state._persist()
                self._json(HTTPStatus.CREATED, {"installationId": "e2e-installation", "writeToken": "e2e-write-token"})
                return
            if path == "/v1/events":
                if self.headers.get("Authorization") != "Bearer e2e-write-token":
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                events = body.get("events")
                batch_id = body.get("batchId")
                if body.get("telemetrySchemaVersion") != 1 or not isinstance(batch_id, str) or not batch_id or not isinstance(events, list) or not events:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_events"})
                    return
                event_ids = []
                with state.lock:
                    for event in events:
                        if not isinstance(event, dict) or not isinstance(event.get("eventId"), str):
                            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_event"})
                            return
                        code = str(event.get("eventCode") or "")
                        purpose = PURPOSES.get(code)
                        if purpose is None:
                            self._json(HTTPStatus.BAD_REQUEST, {"error": "unknown_event"})
                            return
                        event_ids.append(event["eventId"])
                        state.event_codes[code] = state.event_codes.get(code, 0) + 1
                        state.event_purposes[purpose] += 1
                    state.event_batches += 1
                    state.event_count += len(events)
                    state._persist()
                self._json(HTTPStatus.ACCEPTED, {"batchId": batch_id, "acknowledgedEventIds": event_ids})
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_DELETE(self) -> None:
            path = urlparse(self.path).path
            if state.offline:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "e2e_offline"})
                return
            if path != "/v1/installations/current" or self.headers.get("Authorization") != "Bearer e2e-write-token":
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            with state.lock:
                state.deletions += 1
                state._persist()
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def _body(self) -> dict[str, object] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 65536:
                    return None
                value = json.loads(self.rfile.read(length).decode("utf-8"))
                return value if isinstance(value, dict) else None
            except (ValueError, UnicodeError, json.JSONDecodeError):
                return None

        def _json(self, status: HTTPStatus, value: dict[str, object]) -> None:
            encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(State(args.summary)))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
