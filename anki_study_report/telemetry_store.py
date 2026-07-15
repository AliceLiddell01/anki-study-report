"""Bounded per-profile SQLite queue for opt-in telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable

from .telemetry_contract import CONTRACT, utc_now


TELEMETRY_STORE_SCHEMA_VERSION = 1
MAX_DATABASE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, repr=False)
class InstallationCredentials:
    installation_id: str
    write_token: str
    created_at: str

    def __repr__(self) -> str:
        return f"InstallationCredentials(installation_id={self.installation_id!r}, write_token=<redacted>, created_at={self.created_at!r})"


@dataclass(frozen=True)
class QueuedEvent:
    event_id: str
    purpose: str
    payload: dict[str, Any]
    retry_count: int


class TelemetryStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._open_or_recover()

    def _open_or_recover(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = self._connect()
            result = self._connection.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError("telemetry quick_check failed")
            self._migrate()
        except (sqlite3.DatabaseError, OSError):
            self._close_locked()
            self._quarantine()
            self._connection = self._connect()
            self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA max_page_count={MAX_DATABASE_BYTES // 4096}")
            return connection
        except Exception:
            connection.close()
            raise

    def _migrate(self) -> None:
        connection = self._require_connection()
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > TELEMETRY_STORE_SCHEMA_VERSION:
            raise sqlite3.DatabaseError("unsupported future telemetry schema")
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS installation_credentials (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    installation_id TEXT NOT NULL,
                    write_token TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queued_events (
                    event_id TEXT PRIMARY KEY,
                    purpose TEXT NOT NULL,
                    event_code TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    next_attempt_at TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(queued_events)")}
            additions = {
                "next_attempt_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z'",
                "retry_count": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, declaration in additions.items():
                if column not in columns:
                    connection.execute(f"ALTER TABLE queued_events ADD COLUMN {column} {declaration}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_queued_due ON queued_events(next_attempt_at, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_queued_purpose ON queued_events(purpose)")
            connection.execute(f"PRAGMA user_version={TELEMETRY_STORE_SCHEMA_VERSION}")
            self._set_metadata_locked("telemetrySchemaVersion", 1)
            if self._get_metadata_locked("deletionPending") is None:
                self._set_metadata_locked("deletionPending", False)

    def enqueue(self, purpose: str, payload: dict[str, Any], *, now: str | None = None) -> bool:
        event_id = str(payload.get("eventId") or "")
        event_code = str(payload.get("eventCode") or "")
        occurred_at = str(payload.get("occurredAt") or "")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if purpose not in CONTRACT["purposes"] or not event_id or not event_code or len(encoded.encode("utf-8")) > CONTRACT["limits"]["eventBodyMaxBytes"] * 2:
            return False
        created_at = now or utc_now()
        with self._lock, self._require_connection():
            self._prune_locked(created_at)
            self._require_connection().execute(
                """
                INSERT OR IGNORE INTO queued_events
                    (event_id, purpose, event_code, occurred_at, payload_json, created_at, next_attempt_at, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (event_id, purpose, event_code, occurred_at, encoded, created_at, created_at),
            )
            self._evict_over_cap_locked()
            return self._require_connection().execute(
                "SELECT 1 FROM queued_events WHERE event_id = ?", (event_id,)
            ).fetchone() is not None

    def due_batch(self, *, now: str | None = None) -> list[QueuedEvent]:
        moment = now or utc_now()
        with self._lock, self._require_connection():
            self._prune_locked(moment)
            rows = self._require_connection().execute(
                """
                SELECT event_id, purpose, payload_json, retry_count
                FROM queued_events
                WHERE next_attempt_at <= ?
                ORDER BY created_at, event_id
                LIMIT ?
                """,
                (moment, int(CONTRACT["limits"]["batchMaxEvents"])),
            ).fetchall()
        selected: list[QueuedEvent] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                self.acknowledge([row["event_id"]])
                continue
            candidate = selected + [QueuedEvent(row["event_id"], row["purpose"], payload, int(row["retry_count"]))]
            body = {"telemetrySchemaVersion": 1, "events": [item.payload for item in candidate]}
            if len(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > int(CONTRACT["limits"]["requestBodyMaxBytes"]):
                break
            selected = candidate
        return selected

    def acknowledge(self, event_ids: Iterable[str], *, delivered_at: str | None = None) -> int:
        ids = tuple(dict.fromkeys(str(item) for item in event_ids if item))
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                f"DELETE FROM queued_events WHERE event_id IN ({placeholders})", ids
            )
            if delivered_at is not None:
                self._set_metadata_locked("lastSuccessfulDeliveryAt", delivered_at)
            return int(cursor.rowcount)

    def defer(self, event_ids: Iterable[str], next_attempt_at: str) -> None:
        ids = tuple(dict.fromkeys(str(item) for item in event_ids if item))
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._require_connection():
            self._require_connection().execute(
                f"UPDATE queued_events SET retry_count = retry_count + 1, next_attempt_at = ? WHERE event_id IN ({placeholders})",
                (next_attempt_at, *ids),
            )

    def delete_purposes(self, purposes: Iterable[str]) -> int:
        values = tuple(dict.fromkeys(str(item) for item in purposes if item in CONTRACT["purposes"]))
        if not values:
            return 0
        placeholders = ",".join("?" for _ in values)
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                f"DELETE FROM queued_events WHERE purpose IN ({placeholders})", values
            )
            return int(cursor.rowcount)

    def clear_queue(self) -> int:
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute("DELETE FROM queued_events")
            return int(cursor.rowcount)

    def queue_count(self) -> int:
        with self._lock:
            return int(self._require_connection().execute("SELECT COUNT(*) FROM queued_events").fetchone()[0])

    def purpose_counts(self) -> dict[str, int]:
        result = {purpose: 0 for purpose in CONTRACT["purposes"]}
        with self._lock:
            for row in self._require_connection().execute("SELECT purpose, COUNT(*) AS count FROM queued_events GROUP BY purpose"):
                if row["purpose"] in result:
                    result[row["purpose"]] = int(row["count"])
        return result

    def credentials(self) -> InstallationCredentials | None:
        with self._lock:
            row = self._require_connection().execute(
                "SELECT installation_id, write_token, created_at FROM installation_credentials WHERE id = 1"
            ).fetchone()
        return InstallationCredentials(row[0], row[1], row[2]) if row else None

    def save_credentials(self, installation_id: str, write_token: str, *, created_at: str | None = None) -> None:
        if not installation_id or len(installation_id) > 128 or not write_token or len(write_token) > 512:
            raise ValueError("Invalid installation credentials")
        with self._lock, self._require_connection():
            self._require_connection().execute(
                "INSERT OR REPLACE INTO installation_credentials (id, installation_id, write_token, created_at) VALUES (1, ?, ?, ?)",
                (installation_id, write_token, created_at or utc_now()),
            )

    def clear_credentials(self) -> None:
        with self._lock, self._require_connection():
            self._require_connection().execute("DELETE FROM installation_credentials")

    def set_deletion_state(self, pending: bool, *, error_code: str | None = None, next_attempt_at: str | None = None) -> None:
        with self._lock, self._require_connection():
            self._set_metadata_locked("deletionPending", bool(pending))
            self._set_metadata_locked("deletionErrorCode", error_code)
            self._set_metadata_locked("deletionNextAttemptAt", next_attempt_at)

    def set_delivery_state(self, *, attempt_at: str, error_code: str | None = None) -> None:
        with self._lock, self._require_connection():
            self._set_metadata_locked("lastDeliveryAttemptAt", attempt_at)
            self._set_metadata_locked("lastDeliveryErrorCode", error_code)

    def public_status(self) -> dict[str, Any]:
        with self._lock:
            credentials = self._require_connection().execute("SELECT 1 FROM installation_credentials WHERE id = 1").fetchone()
            return {
                "storeSchemaVersion": TELEMETRY_STORE_SCHEMA_VERSION,
                "enrollmentState": "enrolled" if credentials else "not_enrolled",
                "pendingEventCount": self.queue_count(),
                "pendingByPurpose": self.purpose_counts(),
                "lastSuccessfulDeliveryAt": self._get_metadata_locked("lastSuccessfulDeliveryAt"),
                "lastDeliveryAttemptAt": self._get_metadata_locked("lastDeliveryAttemptAt"),
                "lastDeliveryErrorCode": self._get_metadata_locked("lastDeliveryErrorCode"),
                "deletionPending": self._get_metadata_locked("deletionPending") is True,
                "deletionErrorCode": self._get_metadata_locked("deletionErrorCode"),
                "deletionNextAttemptAt": self._get_metadata_locked("deletionNextAttemptAt"),
            }

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _prune_locked(self, now: str) -> None:
        try:
            moment = datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            moment = datetime.now(timezone.utc)
        cutoff = (moment - timedelta(days=int(CONTRACT["limits"]["queueMaxAgeDays"]))).isoformat().replace("+00:00", "Z")
        self._require_connection().execute("DELETE FROM queued_events WHERE created_at < ?", (cutoff,))

    def _evict_over_cap_locked(self) -> None:
        cap = int(CONTRACT["limits"]["queueMaxEvents"])
        self._require_connection().execute(
            """
            DELETE FROM queued_events WHERE event_id IN (
                SELECT event_id FROM queued_events ORDER BY created_at, event_id
                LIMIT MAX(0, (SELECT COUNT(*) FROM queued_events) - ?)
            )
            """,
            (cap,),
        )

    def _set_metadata_locked(self, key: str, value: Any) -> None:
        self._require_connection().execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False, separators=(",", ":"))),
        )

    def _get_metadata_locked(self, key: str) -> Any:
        row = self._require_connection().execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Telemetry store is closed")
        return self._connection

    def _close_locked(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _quarantine(self) -> Path | None:
        if not self.path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.path.with_name(f"{self.path.name}.corrupt-{timestamp}")
        try:
            os.replace(self.path, target)
            return target
        except OSError:
            return None
