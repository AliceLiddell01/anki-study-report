"""Durable per-profile signal, notification and delivery-preference state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable
import uuid


NOTIFICATION_STORE_SCHEMA_VERSION = 1
NOTIFICATION_HISTORY_DAYS = 180
NOTIFICATION_HISTORY_CAP = 5000
NOTIFICATION_PAGE_LIMIT = 50
MAX_EVIDENCE_BYTES = 2048
MAX_DATABASE_BYTES = 64 * 1024 * 1024

CATEGORIES = {"workload", "retention", "deck_health", "card_problems", "product_updates"}
SIGNAL_CATEGORIES = CATEGORIES - {"product_updates"}
SEVERITIES = {"info", "warning", "critical"}
SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}
STATUSES = {"active", "resolved"}
ENTITY_TYPES = {"all_collection", "deck", "card", "note"}
NOTIFICATION_KINDS = {"signal_created", "signal_reactivated", "severity_escalated", "release", "system"}
TOAST_KINDS = {"signal_created", "signal_reactivated", "severity_escalated", "release"}
ACTIVE_CARD_SIGNAL_LIMIT = 50

DEFAULT_PREFERENCES = {
    "notificationCenterEnabled": True,
    "showUnreadBadge": True,
    "showInAppToasts": True,
    "minimumToastSeverity": "critical",
    "sound": "none",
    "osNotifications": "none",
    "toastCategories": {
        "workload": True,
        "retention": True,
        "deck_health": True,
        "card_problems": True,
        "product_updates": True,
    },
}

EVIDENCE_FIELDS = {
    "workload.review_pressure": {"currentLoad", "baselineMedian", "activeDays", "ratio", "delta"},
    "retention.recent_drop": {"recentAnswers", "baselineAnswers", "recentRetention", "baselineRetention", "dropPoints"},
    "deck.health_decline": {"health", "reviews", "passRate", "failRate", "averageAnswerSeconds"},
    "card.repeated_again": {"againCount", "reviewCount", "windowDays", "lastReviewAt"},
}


class NotificationValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid notification request.")
        self.field_errors = dict(field_errors)


class UnsupportedNotificationSchemaError(sqlite3.DatabaseError):
    """Raised when a newer notification schema must be preserved unchanged."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class NotificationStore:
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
                raise sqlite3.DatabaseError("notification quick_check failed")
            self._migrate()
        except UnsupportedNotificationSchemaError:
            self._close_locked()
            raise
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
        if version > NOTIFICATION_STORE_SCHEMA_VERSION:
            raise UnsupportedNotificationSchemaError(
                f"unsupported future notification schema: {version}"
            )
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    evidence_json TEXT NOT NULL,
                    detector_version TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    resolved_at TEXT,
                    reactivated_at TEXT,
                    status TEXT NOT NULL,
                    missing_evaluation_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    signal_id TEXT REFERENCES signals(signal_id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    template_code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    toast_delivered_at TEXT,
                    toast_attempt_count INTEGER NOT NULL DEFAULT 0,
                    severity_at_creation TEXT NOT NULL,
                    source_revision TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    preferences_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_signals_code_status ON signals(code, status)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_signals_category_status ON signals(category, status)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC, notification_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(read_at, created_at DESC)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_toast ON notifications(toast_delivered_at, created_at)")
            connection.execute(f"PRAGMA user_version={NOTIFICATION_STORE_SCHEMA_VERSION}")
            self._set_metadata_locked("schemaVersion", NOTIFICATION_STORE_SCHEMA_VERSION)
            if connection.execute("SELECT 1 FROM notification_preferences WHERE id = 1").fetchone() is None:
                connection.execute(
                    "INSERT INTO notification_preferences (id, preferences_json, updated_at) VALUES (1, ?, ?)",
                    (_json(DEFAULT_PREFERENCES), utc_now()),
                )

    def reconcile(
        self,
        detector_code: str,
        candidates: Iterable[dict[str, Any]],
        *,
        source_revision: str,
        evaluated_at: str | None = None,
    ) -> dict[str, int]:
        if detector_code not in EVIDENCE_FIELDS:
            raise NotificationValidationError({"detectorCode": "Unknown detector code."})
        moment = evaluated_at or utc_now()
        revision = _bounded_text(source_revision, 160, "sourceRevision")
        normalized = [_validate_candidate(item, expected_code=detector_code) for item in candidates]
        if len(normalized) > 50 and detector_code == "card.repeated_again":
            normalized = normalized[:50]
        if len({item["dedupeKey"] for item in normalized}) != len(normalized):
            raise NotificationValidationError({"dedupeKey": "Duplicate candidate key."})
        counts = {"created": 0, "reactivated": 0, "escalated": 0, "updated": 0, "resolved": 0}
        with self._lock, self._require_connection():
            connection = self._require_connection()
            present = set()
            for candidate in normalized:
                present.add(candidate["dedupeKey"])
                row = connection.execute("SELECT * FROM signals WHERE dedupe_key = ?", (candidate["dedupeKey"],)).fetchone()
                evidence_json = _json(candidate["evidence"])
                if row is None:
                    signal_id = str(uuid.uuid4())
                    connection.execute(
                        """INSERT INTO signals
                        (signal_id, code, category, severity, dedupe_key, entity_type, entity_id, evidence_json,
                         detector_version, first_seen_at, last_seen_at, status, missing_evaluation_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0)""",
                        (signal_id, candidate["code"], candidate["category"], candidate["severity"], candidate["dedupeKey"],
                         candidate["entityType"], candidate["entityId"], evidence_json, candidate["detectorVersion"], moment, moment),
                    )
                    self._insert_notification_locked(signal_id, "signal_created", candidate["code"], candidate["severity"], revision, moment)
                    counts["created"] += 1
                    continue
                old_severity = str(row["severity"])
                was_resolved = row["status"] == "resolved"
                connection.execute(
                    """UPDATE signals SET category = ?, severity = ?, entity_type = ?, entity_id = ?, evidence_json = ?,
                    detector_version = ?, last_seen_at = ?, resolved_at = NULL,
                    reactivated_at = CASE WHEN status = 'resolved' THEN ? ELSE reactivated_at END,
                    status = 'active', missing_evaluation_count = 0 WHERE signal_id = ?""",
                    (candidate["category"], candidate["severity"], candidate["entityType"], candidate["entityId"], evidence_json,
                     candidate["detectorVersion"], moment, moment, row["signal_id"]),
                )
                if was_resolved:
                    self._insert_notification_locked(row["signal_id"], "signal_reactivated", candidate["code"], candidate["severity"], revision, moment)
                    counts["reactivated"] += 1
                elif SEVERITY_ORDER[candidate["severity"]] > SEVERITY_ORDER[old_severity]:
                    self._insert_notification_locked(row["signal_id"], "severity_escalated", candidate["code"], candidate["severity"], revision, moment)
                    counts["escalated"] += 1
                else:
                    counts["updated"] += 1

            active_rows = connection.execute(
                "SELECT signal_id, dedupe_key, missing_evaluation_count FROM signals WHERE code = ? AND status = 'active'",
                (detector_code,),
            ).fetchall()
            for row in active_rows:
                if row["dedupe_key"] in present:
                    continue
                missing = int(row["missing_evaluation_count"]) + 1
                if missing >= 2:
                    connection.execute(
                        "UPDATE signals SET status = 'resolved', resolved_at = ?, missing_evaluation_count = ? WHERE signal_id = ?",
                        (moment, missing, row["signal_id"]),
                    )
                    counts["resolved"] += 1
                else:
                    connection.execute(
                        "UPDATE signals SET missing_evaluation_count = ? WHERE signal_id = ?",
                        (missing, row["signal_id"]),
                    )
            self._set_metadata_locked(f"detectorRevision:{detector_code}", revision)
            self._prune_locked(moment)
        return counts

    def detector_revision(self, detector_code: str) -> str | None:
        with self._lock:
            value = self._get_metadata_locked(f"detectorRevision:{detector_code}")
        return value if isinstance(value, str) else None

    def has_notification_source_revision(self, source_revision: str) -> bool:
        revision = _bounded_text(source_revision, 160, "sourceRevision")
        with self._lock:
            row = self._require_connection().execute(
                "SELECT 1 FROM notifications WHERE source_revision = ? LIMIT 1",
                (revision,),
            ).fetchone()
        return row is not None

    def summary(self, *, limit: int = 8) -> dict[str, Any]:
        bounded = min(8, max(0, int(limit)))
        with self._lock:
            connection = self._require_connection()
            unread = int(connection.execute("SELECT COUNT(*) FROM notifications WHERE read_at IS NULL").fetchone()[0])
            active = int(connection.execute("SELECT COUNT(*) FROM signals WHERE status = 'active'").fetchone()[0])
            rows = connection.execute(_LIST_SQL + " WHERE n.read_at IS NULL OR s.status = 'active' ORDER BY n.created_at DESC, n.notification_id DESC LIMIT ?", (bounded,)).fetchall()
        return {
            "schemaVersion": NOTIFICATION_STORE_SCHEMA_VERSION,
            "unreadCount": unread,
            "activeSignalCount": active,
            "items": [_public_notification(row) for row in rows],
        }

    def list_active_card_signals(self, *, limit: int = ACTIVE_CARD_SIGNAL_LIMIT) -> list[dict[str, Any]]:
        """Return bounded canonical card-level Signals without notification history."""

        bounded = min(ACTIVE_CARD_SIGNAL_LIMIT, max(0, int(limit)))
        with self._lock:
            rows = self._require_connection().execute(
                """
                SELECT code, severity, entity_type, entity_id, evidence_json,
                       detector_version, first_seen_at, last_seen_at
                FROM signals
                WHERE status = 'active' AND entity_type = 'card'
                ORDER BY last_seen_at DESC, code, entity_id
                LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [_public_active_card_signal(row) for row in rows]

    def list_notifications(
        self,
        *,
        page: int = 1,
        page_limit: int = 20,
        tab: str = "all",
        category: str = "all",
    ) -> dict[str, Any]:
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise NotificationValidationError({"page": "Expected a positive integer."})
        if not isinstance(page_limit, int) or isinstance(page_limit, bool) or not 1 <= page_limit <= NOTIFICATION_PAGE_LIMIT:
            raise NotificationValidationError({"pageLimit": "Expected an integer from 1 to 50."})
        if tab not in {"all", "unread", "active"}:
            raise NotificationValidationError({"tab": "Unknown tab."})
        if category != "all" and category not in CATEGORIES:
            raise NotificationValidationError({"category": "Unknown category."})
        clauses, params = [], []
        if tab == "unread":
            clauses.append("n.read_at IS NULL")
        elif tab == "active":
            clauses.append("s.status = 'active'")
        if category != "all":
            clauses.append("COALESCE(s.category, 'product_updates') = ?")
            params.append(category)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            connection = self._require_connection()
            total = int(connection.execute("SELECT COUNT(*) FROM notifications n LEFT JOIN signals s ON s.signal_id = n.signal_id" + where, params).fetchone()[0])
            rows = connection.execute(
                _LIST_SQL + where + " ORDER BY n.created_at DESC, n.notification_id DESC LIMIT ? OFFSET ?",
                (*params, page_limit, (page - 1) * page_limit),
            ).fetchall()
        page_count = (total + page_limit - 1) // page_limit
        return {
            "schemaVersion": NOTIFICATION_STORE_SCHEMA_VERSION,
            "page": page,
            "pageLimit": page_limit,
            "pageCount": page_count,
            "total": total,
            "items": [_public_notification(row) for row in rows],
        }

    def mark_read(self, notification_ids: Iterable[str], *, read_at: str | None = None) -> int:
        ids = tuple(dict.fromkeys(_bounded_id(item) for item in notification_ids))
        if not ids or len(ids) > NOTIFICATION_PAGE_LIMIT:
            raise NotificationValidationError({"notificationIds": "Expected 1 to 50 notification IDs."})
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                f"UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE notification_id IN ({placeholders})",
                (read_at or utc_now(), *ids),
            )
            return int(cursor.rowcount)

    def mark_all_read(self, *, read_at: str | None = None) -> int:
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                "UPDATE notifications SET read_at = ? WHERE read_at IS NULL", (read_at or utc_now(),)
            )
            return int(cursor.rowcount)

    def preferences(self) -> dict[str, Any]:
        return normalize_preferences(self._raw_preferences())

    def _raw_preferences(self) -> dict[str, Any]:
        with self._lock:
            row = self._require_connection().execute("SELECT preferences_json FROM notification_preferences WHERE id = 1").fetchone()
        try:
            source = json.loads(row[0]) if row else {}
        except json.JSONDecodeError:
            source = {}
        return source if isinstance(source, dict) else {}

    def update_preferences(self, patch: dict[str, Any], *, updated_at: str | None = None) -> dict[str, Any]:
        validated = validate_preferences_patch(patch)
        raw = self._raw_preferences()
        current = normalize_preferences(raw)
        merged = {**current, **{key: value for key, value in validated.items() if key != "toastCategories"}}
        if "toastCategories" in validated:
            merged["toastCategories"] = {**current["toastCategories"], **validated["toastCategories"]}
        normalized = normalize_preferences(merged)
        raw_categories = raw.get("toastCategories") if isinstance(raw.get("toastCategories"), dict) else {}
        persisted = {
            **raw,
            **normalized,
            "toastCategories": {**raw_categories, **normalized["toastCategories"]},
        }
        with self._lock, self._require_connection():
            self._require_connection().execute(
                "UPDATE notification_preferences SET preferences_json = ?, updated_at = ? WHERE id = 1",
                (_json(persisted), updated_at or utc_now()),
            )
        return normalized

    def toast_candidates(self, *, session_started_at: str, limit: int = 50) -> list[dict[str, Any]]:
        preferences = self.preferences()
        if not preferences["showInAppToasts"]:
            return []
        minimum = SEVERITY_ORDER[preferences["minimumToastSeverity"]]
        bounded_limit = min(50, max(1, int(limit)))
        with self._lock:
            rows = self._require_connection().execute(
                _LIST_SQL + " WHERE n.toast_delivered_at IS NULL AND n.created_at >= ? ORDER BY n.created_at, n.notification_id LIMIT ?",
                (_bounded_text(session_started_at, 40, "sessionStartedAt"), bounded_limit),
            ).fetchall()
        return [
            item for item in (_public_notification(row) for row in rows)
            if item["kind"] in TOAST_KINDS
            and preferences["toastCategories"].get(item["category"], False)
            and SEVERITY_ORDER[item["severity"]] >= minimum
        ]

    def mark_toast_delivered(self, notification_ids: Iterable[str], *, delivered_at: str | None = None) -> int:
        ids = tuple(dict.fromkeys(_bounded_id(item) for item in notification_ids))
        if not ids or len(ids) > 50:
            raise NotificationValidationError({"notificationIds": "Expected 1 to 50 notification IDs."})
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                f"UPDATE notifications SET toast_delivered_at = COALESCE(toast_delivered_at, ?), toast_attempt_count = toast_attempt_count + 1 WHERE notification_id IN ({placeholders}) AND toast_attempt_count < 2",
                (delivered_at or utc_now(), *ids),
            )
            return int(cursor.rowcount)

    def upsert_release(self, version: str, *, source_revision: str, created_at: str | None = None) -> str:
        release = _bounded_text(version, 64, "version")
        revision = _bounded_text(source_revision, 160, "sourceRevision")
        moment = created_at or utc_now()
        with self._lock, self._require_connection():
            existing = self._require_connection().execute(
                "SELECT notification_id FROM notifications WHERE kind = 'release' AND source_revision = ?", (revision,)
            ).fetchone()
            if existing:
                return str(existing[0])
            notification_id = str(uuid.uuid4())
            self._require_connection().execute(
                """INSERT INTO notifications
                (notification_id, signal_id, kind, template_code, created_at, severity_at_creation, source_revision)
                VALUES (?, NULL, 'release', ?, ?, 'info', ?)""",
                (notification_id, f"release.{release}", moment, revision),
            )
            self._prune_locked(moment)
            return notification_id

    def mark_release_read(self, version: str, *, read_at: str | None = None) -> int:
        code = f"release.{_bounded_text(version, 64, 'version')}"
        with self._lock, self._require_connection():
            cursor = self._require_connection().execute(
                "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE kind = 'release' AND template_code = ?",
                (read_at or utc_now(), code),
            )
            return int(cursor.rowcount)

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _insert_notification_locked(self, signal_id: str, kind: str, code: str, severity: str, revision: str, moment: str) -> None:
        self._require_connection().execute(
            """INSERT INTO notifications
            (notification_id, signal_id, kind, template_code, created_at, severity_at_creation, source_revision)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), signal_id, kind, code, moment, severity, revision),
        )

    def _prune_locked(self, moment: str) -> None:
        cutoff = (datetime.fromisoformat(moment.replace("Z", "+00:00")) - timedelta(days=NOTIFICATION_HISTORY_DAYS)).isoformat().replace("+00:00", "Z")
        connection = self._require_connection()
        connection.execute(
            """DELETE FROM notifications WHERE notification_id IN (
            SELECT n.notification_id FROM notifications n LEFT JOIN signals s ON s.signal_id = n.signal_id
            WHERE n.created_at < ? AND (n.read_at IS NOT NULL OR s.signal_id IS NULL OR s.status = 'resolved'))""",
            (cutoff,),
        )
        connection.execute(
            """DELETE FROM notifications WHERE notification_id IN (
            SELECT n.notification_id FROM notifications n LEFT JOIN signals s ON s.signal_id = n.signal_id
            WHERE n.read_at IS NOT NULL OR s.signal_id IS NULL OR s.status = 'resolved'
            ORDER BY n.created_at, n.notification_id
            LIMIT MAX(0, (SELECT COUNT(*) FROM notifications) - ?))""",
            (NOTIFICATION_HISTORY_CAP,),
        )
        connection.execute(
            """DELETE FROM notifications WHERE notification_id IN (
            SELECT notification_id FROM notifications
            ORDER BY created_at, notification_id
            LIMIT MAX(0, (SELECT COUNT(*) FROM notifications) - ?))""",
            (NOTIFICATION_HISTORY_CAP,),
        )

    def _set_metadata_locked(self, key: str, value: Any) -> None:
        self._require_connection().execute(
            "INSERT OR REPLACE INTO schema_metadata (key, value_json) VALUES (?, ?)", (key, _json(value))
        )

    def _get_metadata_locked(self, key: str) -> Any:
        row = self._require_connection().execute("SELECT value_json FROM schema_metadata WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Notification store is closed")
        return self._connection

    def _close_locked(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _quarantine(self) -> Path | None:
        if not self.path.exists():
            return None
        target = self.path.with_name(f"{self.path.name}.corrupt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}")
        try:
            os.replace(self.path, target)
            return target
        except OSError:
            return None


_LIST_SQL = """SELECT n.*, s.code, s.category, s.severity, s.status, s.entity_type, s.entity_id,
s.evidence_json, s.first_seen_at, s.last_seen_at, s.resolved_at
FROM notifications n LEFT JOIN signals s ON s.signal_id = n.signal_id"""


def _validate_candidate(value: Any, *, expected_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NotificationValidationError({"candidate": "Expected an object."})
    allowed = {"code", "category", "severity", "dedupeKey", "entityType", "entityId", "evidence", "detectorVersion"}
    unknown = set(value) - allowed
    if unknown:
        raise NotificationValidationError({str(key): "Unknown field." for key in sorted(unknown)})
    code = str(value.get("code") or "")
    category = str(value.get("category") or "")
    severity = str(value.get("severity") or "")
    entity_type = str(value.get("entityType") or "")
    if code != expected_code or category not in SIGNAL_CATEGORIES or severity not in SEVERITIES or entity_type not in ENTITY_TYPES:
        raise NotificationValidationError({"candidate": "Invalid signal enum or code."})
    evidence = value.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_FIELDS[code]:
        raise NotificationValidationError({"evidence": "Evidence fields do not match the detector schema."})
    encoded = _json(evidence).encode("utf-8")
    if len(encoded) > MAX_EVIDENCE_BYTES or any(not _bounded_evidence_value(item) for item in evidence.values()):
        raise NotificationValidationError({"evidence": "Evidence is not bounded."})
    entity_id = value.get("entityId")
    if entity_type == "all_collection":
        entity_id = None
    elif not isinstance(entity_id, (str, int)) or isinstance(entity_id, bool) or not str(entity_id) or len(str(entity_id)) > 40:
        raise NotificationValidationError({"entityId": "Expected a bounded local entity ID."})
    return {
        "code": code,
        "category": category,
        "severity": severity,
        "dedupeKey": _bounded_text(value.get("dedupeKey"), 160, "dedupeKey"),
        "entityType": entity_type,
        "entityId": None if entity_id is None else str(entity_id),
        "evidence": evidence,
        "detectorVersion": _bounded_text(value.get("detectorVersion"), 40, "detectorVersion"),
    }


def normalize_preferences(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    categories = source.get("toastCategories") if isinstance(source.get("toastCategories"), dict) else {}
    minimum = source.get("minimumToastSeverity")
    if minimum not in SEVERITIES:
        minimum = DEFAULT_PREFERENCES["minimumToastSeverity"]
    return {
        "notificationCenterEnabled": source.get("notificationCenterEnabled") is not False,
        "showUnreadBadge": source.get("showUnreadBadge") is not False,
        "showInAppToasts": source.get("showInAppToasts") is not False,
        "minimumToastSeverity": minimum,
        "sound": "none",
        "osNotifications": "none",
        "toastCategories": {key: categories.get(key) is not False for key in sorted(CATEGORIES)},
    }


def validate_preferences_patch(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NotificationValidationError({"preferences": "Expected an object."})
    allowed = {"showUnreadBadge", "showInAppToasts", "minimumToastSeverity", "toastCategories"}
    unknown = set(value) - allowed
    errors = {str(key): "Unknown preference." for key in sorted(unknown)}
    result = {}
    for key in ("showUnreadBadge", "showInAppToasts"):
        if key in value:
            if not isinstance(value[key], bool):
                errors[key] = "Expected boolean."
            else:
                result[key] = value[key]
    if "minimumToastSeverity" in value:
        if value["minimumToastSeverity"] not in SEVERITIES:
            errors["minimumToastSeverity"] = "Unknown severity."
        else:
            result["minimumToastSeverity"] = value["minimumToastSeverity"]
    if "toastCategories" in value:
        categories = value["toastCategories"]
        if not isinstance(categories, dict):
            errors["toastCategories"] = "Expected an object."
        else:
            unknown_categories = set(categories) - CATEGORIES
            if unknown_categories:
                errors["toastCategories"] = "Unknown category."
            elif any(not isinstance(item, bool) for item in categories.values()):
                errors["toastCategories"] = "Expected boolean category values."
            else:
                result["toastCategories"] = dict(categories)
    if errors:
        raise NotificationValidationError(errors)
    return result


def _public_notification(row: sqlite3.Row) -> dict[str, Any]:
    try:
        evidence = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
    except json.JSONDecodeError:
        evidence = {}
    release = row["signal_id"] is None
    return {
        "notificationId": str(row["notification_id"]),
        "signalId": str(row["signal_id"]) if row["signal_id"] else None,
        "kind": str(row["kind"]),
        "code": str(row["template_code"] if release else row["code"]),
        "category": "product_updates" if release else str(row["category"]),
        "severity": str(row["severity_at_creation"]),
        "createdAt": str(row["created_at"]),
        "readAt": str(row["read_at"]) if row["read_at"] else None,
        "toastDeliveredAt": str(row["toast_delivered_at"]) if row["toast_delivered_at"] else None,
        "signalStatus": None if release else str(row["status"]),
        "entity": None if release else {"type": str(row["entity_type"]), "id": str(row["entity_id"]) if row["entity_id"] else None},
        "evidence": evidence,
        "sourceRevision": str(row["source_revision"]),
    }


def _public_active_card_signal(row: sqlite3.Row) -> dict[str, Any]:
    try:
        evidence = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
    except (json.JSONDecodeError, TypeError):
        evidence = {}
    return {
        "code": str(row["code"]),
        "severity": str(row["severity"]),
        "entityType": "card",
        "entityId": str(row["entity_id"] or ""),
        "evidence": evidence if isinstance(evidence, dict) else {},
        "detectorVersion": str(row["detector_version"]),
        "firstSeenAt": str(row["first_seen_at"]),
        "lastSeenAt": str(row["last_seen_at"]),
    }


def _bounded_text(value: Any, limit: int, field: str) -> str:
    text = str(value or "")
    if not text or len(text) > limit or "\r" in text or "\n" in text:
        raise NotificationValidationError({field: "Expected bounded single-line text."})
    return text


def _bounded_id(value: Any) -> str:
    return _bounded_text(value, 64, "notificationIds")


def _bounded_evidence_value(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return value is None
    if isinstance(value, (int, float)):
        return abs(float(value)) <= 10**12
    if isinstance(value, str):
        return len(value) <= 40 and "\r" not in value and "\n" not in value
    return False


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
