"""Durable per-profile product notice and privacy consent state."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Callable


PRODUCT_NOTICE_SCHEMA_VERSION = 1
PRIVACY_SCHEMA_VERSION = 1
CONSENT_SCHEMA_VERSION = 1
PRIVACY_NOTICE_VERSION = "2026-07-15"
TELEMETRY_PURPOSES = ("reliabilityDiagnostics", "featureUsage")

ALLOWED_TELEMETRY_CATEGORIES = (
    "add-on and Anki version buckets",
    "operating-system family",
    "interface locale and theme",
    "allowlisted event, page, feature, action, result and error codes",
    "bounded duration, result-count and collection-size buckets",
    "rounded event time and contract versions",
)

NEVER_COLLECTED_CATEGORIES = (
    "card or note content and field values",
    "deck, note type, template and tag names",
    "search queries and Anki entity identifiers",
    "Anki profile name, user name or email",
    "absolute paths, media filenames and clipboard content",
    "dashboard token, token-bearing URLs and report payloads",
    "raw exception messages, stack traces, free-form text, IP or User-Agent in application storage",
)

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ProductNoticeValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid product notice or privacy request.")
        self.field_errors = dict(field_errors)


class _AtomicJsonStore:
    """Small JSON document with process locking, migration and quarantine."""

    def __init__(
        self,
        path: Path,
        *,
        schema_version: int,
        defaults: Callable[[], dict[str, Any]],
        migrate: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.path = Path(path)
        self.schema_version = int(schema_version)
        self._defaults = defaults
        self._migrate = migrate
        self._lock = threading.RLock()

    def read_document(self) -> dict[str, Any]:
        with self._lock:
            return self._read_locked()

    def update_document(self, update: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock:
            document = self._read_locked()
            stored_schema_version = document.get("schemaVersion")
            update(document)
            document["schemaVersion"] = (
                stored_schema_version
                if isinstance(stored_schema_version, int)
                and not isinstance(stored_schema_version, bool)
                and stored_schema_version > self.schema_version
                else self.schema_version
            )
            self._write_locked(document)
            return deepcopy(document)

    def _read_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._defaults()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("document must be an object")
            version = raw.get("schemaVersion", 0)
            if isinstance(version, bool) or not isinstance(version, int) or version < 0:
                raise ValueError("invalid schemaVersion")
            if version > self.schema_version:
                return raw
            migrated = self._migrate(deepcopy(raw))
            migrated["schemaVersion"] = self.schema_version
            return migrated
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            self._quarantine_locked()
            return self._defaults()

    def _quarantine_locked(self) -> Path | None:
        if not self.path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.path.with_name(f"{self.path.name}.corrupt-{timestamp}")
        try:
            os.replace(self.path, target)
            return target
        except OSError:
            return None

    def _write_locked(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise


def _product_defaults() -> dict[str, Any]:
    return {
        "schemaVersion": PRODUCT_NOTICE_SCHEMA_VERSION,
        "firstObservedVersion": None,
        "lastStartedVersion": None,
        "lastSeenReleaseVersion": None,
    }


def _migrate_product_document(document: dict[str, Any]) -> dict[str, Any]:
    version = int(document.get("schemaVersion", 0) or 0)
    if version == 0:
        aliases = {
            "first_observed_version": "firstObservedVersion",
            "last_started_version": "lastStartedVersion",
            "last_seen_release_version": "lastSeenReleaseVersion",
        }
        for old, new in aliases.items():
            if new not in document and old in document:
                document[new] = document.pop(old)
    for key in ("firstObservedVersion", "lastStartedVersion", "lastSeenReleaseVersion"):
        document[key] = _valid_semver(document.get(key))
    return document


def _privacy_defaults() -> dict[str, Any]:
    return {
        "schemaVersion": PRIVACY_SCHEMA_VERSION,
        "telemetry": {
            "status": "undecided",
            "consentSchemaVersion": CONSENT_SCHEMA_VERSION,
            "privacyNoticeVersion": PRIVACY_NOTICE_VERSION,
            "purposes": {purpose: False for purpose in TELEMETRY_PURPOSES},
            "decidedAt": None,
            "deletionPending": False,
        },
    }


def _migrate_privacy_document(document: dict[str, Any]) -> dict[str, Any]:
    telemetry = document.get("telemetry")
    if not isinstance(telemetry, dict):
        telemetry = {}
        document["telemetry"] = telemetry
    purposes = telemetry.get("purposes") if isinstance(telemetry.get("purposes"), dict) else {}
    normalized_purposes = {purpose: purposes.get(purpose) is True for purpose in TELEMETRY_PURPOSES}
    status = telemetry.get("status")
    if status not in {"undecided", "accepted", "declined"}:
        status = "accepted" if any(normalized_purposes.values()) else "undecided"
    if status == "accepted" and not any(normalized_purposes.values()):
        status = "declined"
    if status != "accepted":
        normalized_purposes = {purpose: False for purpose in TELEMETRY_PURPOSES}
    consent_version = telemetry.get("consentSchemaVersion")
    if isinstance(consent_version, bool) or not isinstance(consent_version, int) or consent_version < 1:
        consent_version = CONSENT_SCHEMA_VERSION
    notice_version = telemetry.get("privacyNoticeVersion")
    if not isinstance(notice_version, str) or not notice_version.strip():
        notice_version = PRIVACY_NOTICE_VERSION
    decided_at = telemetry.get("decidedAt")
    telemetry.update(
        {
            "status": status,
            "consentSchemaVersion": consent_version,
            "privacyNoticeVersion": notice_version,
            "purposes": normalized_purposes,
            "decidedAt": decided_at if isinstance(decided_at, str) else None,
            "deletionPending": telemetry.get("deletionPending") is True,
        }
    )
    return document


class ProductNoticeStore:
    def __init__(self, path: Path) -> None:
        self._store = _AtomicJsonStore(
            path,
            schema_version=PRODUCT_NOTICE_SCHEMA_VERSION,
            defaults=_product_defaults,
            migrate=_migrate_product_document,
        )

    @property
    def path(self) -> Path:
        return self._store.path

    def read(self) -> dict[str, Any]:
        return _public_product_document(self._store.read_document())

    def record_started(self, current_version: str) -> dict[str, Any]:
        version = _require_semver(current_version, "currentVersion")

        def update(document: dict[str, Any]) -> None:
            if _valid_semver(document.get("firstObservedVersion")) is None:
                document["firstObservedVersion"] = version
            document["lastStartedVersion"] = version

        return _public_product_document(self._store.update_document(update))

    def mark_release_seen(self, current_version: str) -> dict[str, Any]:
        version = _require_semver(current_version, "currentVersion")

        def update(document: dict[str, Any]) -> None:
            if _valid_semver(document.get("firstObservedVersion")) is None:
                document["firstObservedVersion"] = version
            document["lastStartedVersion"] = version
            document["lastSeenReleaseVersion"] = version

        return _public_product_document(self._store.update_document(update))


class PrivacyStore:
    def __init__(self, path: Path) -> None:
        self._store = _AtomicJsonStore(
            path,
            schema_version=PRIVACY_SCHEMA_VERSION,
            defaults=_privacy_defaults,
            migrate=_migrate_privacy_document,
        )

    @property
    def path(self) -> Path:
        return self._store.path

    def read(self) -> dict[str, Any]:
        return _public_privacy_document(self._store.read_document())

    def save_choices(self, payload: Any, *, now: datetime | None = None) -> dict[str, Any]:
        purposes = validate_privacy_choices(payload)
        status = "accepted" if any(purposes.values()) else "declined"
        decided_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        def update(document: dict[str, Any]) -> None:
            telemetry = document.setdefault("telemetry", {})
            telemetry.update(
                {
                    "status": status,
                    "consentSchemaVersion": CONSENT_SCHEMA_VERSION,
                    "privacyNoticeVersion": PRIVACY_NOTICE_VERSION,
                    "purposes": purposes,
                    "decidedAt": decided_at,
                    "deletionPending": False,
                }
            )

        return _public_privacy_document(self._store.update_document(update))

    def decline(self, *, now: datetime | None = None) -> dict[str, Any]:
        return self.save_choices(
            {"purposes": {purpose: False for purpose in TELEMETRY_PURPOSES}},
            now=now,
        )


def validate_privacy_choices(payload: Any) -> dict[str, bool]:
    if not isinstance(payload, dict):
        raise ProductNoticeValidationError({"privacy": "Expected an object."})
    unknown = sorted(set(payload) - {"purposes"})
    if unknown:
        raise ProductNoticeValidationError({key: "Unexpected field." for key in unknown})
    purposes = payload.get("purposes")
    if not isinstance(purposes, dict):
        raise ProductNoticeValidationError({"purposes": "Expected an object."})
    purpose_unknown = sorted(set(purposes) - set(TELEMETRY_PURPOSES))
    missing = [purpose for purpose in TELEMETRY_PURPOSES if purpose not in purposes]
    errors = {f"purposes.{key}": "Unexpected purpose." for key in purpose_unknown}
    errors.update({f"purposes.{key}": "A boolean choice is required." for key in missing})
    for purpose in TELEMETRY_PURPOSES:
        if purpose in purposes and not isinstance(purposes[purpose], bool):
            errors[f"purposes.{purpose}"] = "Expected true or false."
    if errors:
        raise ProductNoticeValidationError(errors)
    return {purpose: purposes[purpose] is True for purpose in TELEMETRY_PURPOSES}


def load_bundled_changelog(path: Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schemaVersion") != 1:
        raise ValueError("Unsupported changelog schema")
    releases = raw.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ValueError("Changelog releases are required")
    seen_versions: set[str] = set()
    seen_ids: set[str] = set()
    previous_key: tuple[Any, ...] | None = None
    for release in releases:
        if not isinstance(release, dict):
            raise ValueError("Invalid changelog release")
        version = _require_semver(release.get("version"), "release.version")
        if version in seen_versions:
            raise ValueError(f"Duplicate changelog version: {version}")
        seen_versions.add(version)
        key = _semver_key(version)
        if previous_key is not None and not key < previous_key:
            raise ValueError("Changelog releases must be newest first")
        previous_key = key
        sections = release.get("sections")
        if not isinstance(sections, list) or len(sections) > 10:
            raise ValueError("Invalid changelog sections")
        for section in sections:
            if not isinstance(section, dict) or section.get("type") not in {"added", "changed", "fixed", "safety", "removed"}:
                raise ValueError("Invalid changelog section")
            items = section.get("items")
            if not isinstance(items, list) or len(items) > 100:
                raise ValueError("Invalid changelog items")
            for item in items:
                if not isinstance(item, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,79}", str(item.get("id") or "")):
                    raise ValueError("Invalid changelog item ID")
                item_id = str(item["id"])
                if item_id in seen_ids:
                    raise ValueError(f"Duplicate changelog item ID: {item_id}")
                seen_ids.add(item_id)
                text = item.get("text")
                if not isinstance(text, dict) or set(text) != {"ru", "en"}:
                    raise ValueError("Changelog locale parity is required")
                if any(not isinstance(value, str) or not value.strip() or len(value) > 1000 for value in text.values()):
                    raise ValueError("Invalid changelog item text")
                if any(re.search(r"<[^>]+>|\[[^\]]+\]\([^\)]+\)", value) for value in text.values()):
                    raise ValueError("Changelog text must not contain HTML or executable Markdown")
    return deepcopy(raw)


def product_notices_response(
    current_version: str,
    notice_store: ProductNoticeStore,
    privacy_store: PrivacyStore,
    changelog: dict[str, Any],
) -> dict[str, Any]:
    current = _require_semver(current_version, "currentVersion")
    notice = notice_store.read()
    privacy = privacy_store.read()
    releases = changelog.get("releases", [])
    versions = [str(item.get("version")) for item in releases if isinstance(item, dict)]
    if current not in versions:
        raise ValueError(f"Current version {current} is missing from bundled changelog")
    last_seen = notice.get("lastSeenReleaseVersion")
    unseen = [version for version in versions if last_seen is None or _semver_key(version) > _semver_key(last_seen)]
    show_whats_new = last_seen is None or _semver_key(current) > _semver_key(last_seen)
    return {
        "ok": True,
        "currentVersion": current,
        "notice": notice,
        "privacy": privacy,
        "requiresConsent": privacy["requiresConsent"],
        "showWhatsNew": show_whats_new,
        "unseenReleaseVersions": unseen,
        "changelog": changelog,
    }


def privacy_response(privacy_store: PrivacyStore) -> dict[str, Any]:
    return {
        "ok": True,
        "privacy": privacy_store.read(),
        "allowedDataCategories": list(ALLOWED_TELEMETRY_CATEGORIES),
        "neverCollected": list(NEVER_COLLECTED_CATEGORIES),
        "privacyNotice": {
            "version": PRIVACY_NOTICE_VERSION,
            "consentSchemaVersion": CONSENT_SCHEMA_VERSION,
            "legalReviewStatus": "technical_draft_not_legal_advice",
        },
    }


def _public_product_document(document: dict[str, Any]) -> dict[str, Any]:
    migrated = _migrate_product_document(deepcopy(document))
    return {
        "schemaVersion": PRODUCT_NOTICE_SCHEMA_VERSION,
        "firstObservedVersion": migrated.get("firstObservedVersion"),
        "lastStartedVersion": migrated.get("lastStartedVersion"),
        "lastSeenReleaseVersion": migrated.get("lastSeenReleaseVersion"),
    }


def _public_privacy_document(document: dict[str, Any]) -> dict[str, Any]:
    migrated = _migrate_privacy_document(deepcopy(document))
    telemetry = deepcopy(migrated["telemetry"])
    requires = (
        telemetry["status"] == "undecided"
        or telemetry["consentSchemaVersion"] != CONSENT_SCHEMA_VERSION
        or telemetry["privacyNoticeVersion"] != PRIVACY_NOTICE_VERSION
    )
    effective = telemetry["purposes"] if telemetry["status"] == "accepted" and not requires else {
        purpose: False for purpose in TELEMETRY_PURPOSES
    }
    telemetry["effectivePurposes"] = effective
    telemetry["requiresConsent"] = requires
    return {
        "schemaVersion": PRIVACY_SCHEMA_VERSION,
        "telemetry": telemetry,
        "requiresConsent": requires,
    }


def _require_semver(value: Any, field: str) -> str:
    result = _valid_semver(value)
    if result is None:
        raise ValueError(f"Invalid SemVer in {field}")
    return result


def _valid_semver(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if _SEMVER_RE.fullmatch(text) else None


def _semver_key(value: str) -> tuple[Any, ...]:
    match = _SEMVER_RE.fullmatch(value)
    if not match:
        return (-1, -1, -1, ((-1, ""),))
    prerelease = match.group(4)
    if prerelease is None:
        pre_key: tuple[Any, ...] = ((2, ""),)
    else:
        parts = tuple((0, int(item)) if item.isdigit() else (1, item) for item in prerelease.split("."))
        pre_key = ((1, ""),) + parts
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), pre_key
