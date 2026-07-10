"""Per-Anki-profile preferences and public Profile MVP payload builders."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any


PROFILE_SCHEMA_VERSION = 1
PROFILE_DECK_SORTS = {"name", "reviews", "active_days"}
PROFILE_DECK_LIMIT = 8
PROFILE_RECENT_DAYS_LIMIT = 7
PROFILE_HEATMAP_DAYS = 182


class ProfileValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid profile preferences.")
        self.field_errors = dict(field_errors)


class ProfilePreferencesStore:
    """Reads and atomically writes the small profile-local JSON document."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def read(self) -> dict[str, Any]:
        with self._lock:
            document = self._read_document_locked()
            return normalize_profile_preferences(document)

    def update(self, patch: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
        validated = validate_profile_preferences_patch(patch, today=today)
        with self._lock:
            document = self._read_document_locked(preserve_unknown=True)
            preferences = normalize_profile_preferences(document)
            preferences.update(validated)
            document.update(preferences)
            document["schemaVersion"] = PROFILE_SCHEMA_VERSION
            self._write_document_locked(document)
            return normalize_profile_preferences(document)

    def _read_document_locked(self, *, preserve_unknown: bool = False) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return dict(raw) if preserve_unknown else raw

    def _write_document_locked(self, document: dict[str, Any]) -> None:
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


def normalize_profile_preferences(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    custom_started_on = _valid_date_key(source.get("customStudyStartedOn"))
    deck_sort = str(source.get("deckOverviewSort") or "name")
    if deck_sort not in PROFILE_DECK_SORTS:
        deck_sort = "name"
    return {
        "customStudyStartedOn": custom_started_on,
        "deckOverviewSort": deck_sort,
    }


def validate_profile_preferences_patch(
    patch: Any,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ProfileValidationError({"profile": "Ожидался объект настроек."})
    unknown = sorted(set(patch) - {"customStudyStartedOn", "deckOverviewSort"})
    if unknown:
        raise ProfileValidationError(
            {key: "Поле нельзя изменять." for key in unknown}
        )
    errors: dict[str, str] = {}
    result: dict[str, Any] = {}
    if "customStudyStartedOn" in patch:
        value = patch.get("customStudyStartedOn")
        if value is None or value == "":
            result["customStudyStartedOn"] = None
        else:
            parsed = _parse_date_key(value)
            if parsed is None:
                errors["customStudyStartedOn"] = "Укажите корректную дату в формате ГГГГ-ММ-ДД."
            elif parsed > (today or date.today()):
                errors["customStudyStartedOn"] = "Дата начала не может быть в будущем."
            else:
                result["customStudyStartedOn"] = parsed.isoformat()
    if "deckOverviewSort" in patch:
        value = patch.get("deckOverviewSort")
        if value not in PROFILE_DECK_SORTS:
            errors["deckOverviewSort"] = "Выберите доступный порядок сортировки."
        else:
            result["deckOverviewSort"] = str(value)
    if errors:
        raise ProfileValidationError(errors)
    return result


def build_profile_payload(
    snapshot: dict[str, Any],
    today_key: str,
    *,
    anki_profile_name: str | None,
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact all-collection profile model before dashboard filters."""

    normalized_preferences = normalize_profile_preferences(preferences)
    daily_rows = _daily_rows(snapshot.get("daily"), today_key)
    deck_rows = _deck_rows(snapshot.get("deckDaily"), today_key)
    active_rows = [row for row in daily_rows if _int(row.get("reviews")) > 0]
    active_dates = {str(row["date"]) for row in active_rows}
    detected_started_on = active_rows[0]["date"] if active_rows else None
    custom_started_on = normalized_preferences["customStudyStartedOn"]
    displayed_started_on = custom_started_on or detected_started_on
    total_reviews = sum(_int(row.get("reviews")) for row in active_rows)
    pass_count = sum(_int(row.get("pass_count")) for row in active_rows)
    fail_count = sum(_int(row.get("fail_count")) for row in active_rows)
    answered = pass_count + fail_count
    study_seconds = sum(_int(row.get("study_seconds")) for row in active_rows)
    profile_name = str(anki_profile_name or "").strip()
    display_name = profile_name or "Пользователь Anki"
    activity_days = _profile_activity_days(active_rows, today_key)
    recent_days = [_public_activity_day(row) for row in reversed(active_rows[-PROFILE_RECENT_DAYS_LIMIT:])]
    decks = _profile_decks(deck_rows)
    decks = _sort_profile_decks(decks, normalized_preferences["deckOverviewSort"])

    return {
        "identity": {
            "ankiProfileName": profile_name or None,
            "displayName": display_name,
            "initials": _initials(display_name),
            "label": "Локальный профиль",
        },
        "studyHistory": {
            "detectedStartedOn": detected_started_on,
            "customStartedOn": custom_started_on,
            "displayedStartedOn": displayed_started_on,
            "statsAvailableFrom": detected_started_on,
            "totalReviews": total_reviews,
            "activeDays": len(active_dates),
            "currentStreak": _current_streak(active_dates, today_key),
            "bestStreak": _best_streak(active_dates),
            "studyTimeSeconds": study_seconds if study_seconds > 0 else None,
            "studyTimeSource": "revlog_estimate" if study_seconds > 0 else None,
            "averagePassRate": round(pass_count / answered, 4) if answered > 0 else None,
        },
        "activity": {
            "days": activity_days,
            "recentActiveDays": recent_days,
            "rangeStart": activity_days[0]["date"] if activity_days else None,
            "rangeEnd": activity_days[-1]["date"] if activity_days else None,
        },
        "decks": {
            "overview": decks[:PROFILE_DECK_LIMIT],
            "total": len(decks),
            "limit": PROFILE_DECK_LIMIT,
            "aggregation": "canonical_current_deck",
        },
        "preferences": normalized_preferences,
    }


def _daily_rows(value: Any, today_key: str) -> list[dict[str, Any]]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        day = _valid_date_key(item.get("date"))
        if day and day <= today_key:
            result.append(dict(item, date=day))
    return sorted(result, key=lambda item: item["date"])


def _deck_rows(value: Any, today_key: str) -> list[dict[str, Any]]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        day = _valid_date_key(item.get("date"))
        deck_id = _int(item.get("deck_id"))
        if day and day <= today_key and deck_id > 0:
            result.append(dict(item, date=day, deck_id=deck_id))
    return result


def _profile_activity_days(rows: list[dict[str, Any]], today_key: str) -> list[dict[str, Any]]:
    today = _parse_date_key(today_key) or date.today()
    cutoff = (today - timedelta(days=PROFILE_HEATMAP_DAYS - 1)).isoformat()
    visible = [row for row in rows if str(row["date"]) >= cutoff]
    return [_public_activity_day(row) for row in visible]


def _public_activity_day(row: dict[str, Any]) -> dict[str, Any]:
    reviews = _int(row.get("reviews"))
    passed = _int(row.get("pass_count"))
    failed = _int(row.get("fail_count"))
    answered = passed + failed
    seconds = _int(row.get("study_seconds"))
    return {
        "date": str(row.get("date") or ""),
        "reviews": reviews,
        "studySeconds": seconds if seconds > 0 else None,
        "passRate": round(passed / answered, 4) if answered > 0 else None,
    }


def _profile_decks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        deck_id = _int(row.get("deck_id"))
        deck = grouped.setdefault(
            deck_id,
            {
                "id": deck_id,
                "name": str(row.get("deck_name") or f"Колода {deck_id}"),
                "reviews": 0,
                "activeDays": set(),
            },
        )
        deck["name"] = str(row.get("deck_name") or deck["name"])
        reviews = _int(row.get("reviews"))
        deck["reviews"] += reviews
        if reviews > 0:
            deck["activeDays"].add(str(row.get("date")))
    return [
        {
            "id": deck["id"],
            "name": deck["name"],
            "totalReviews": deck["reviews"],
            "activeDays": len(deck["activeDays"]),
        }
        for deck in grouped.values()
    ]


def _sort_profile_decks(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    name_key = lambda row: (str(row.get("name") or "").casefold(), _int(row.get("id")))
    if sort == "reviews":
        return sorted(rows, key=lambda row: (-_int(row.get("totalReviews")), *name_key(row)))
    if sort == "active_days":
        return sorted(rows, key=lambda row: (-_int(row.get("activeDays")), *name_key(row)))
    return sorted(rows, key=name_key)


def _current_streak(active_dates: set[str], today_key: str) -> int:
    today = _parse_date_key(today_key) or date.today()
    cursor = today if today.isoformat() in active_dates else today - timedelta(days=1)
    if cursor.isoformat() not in active_dates:
        return 0
    result = 0
    while cursor.isoformat() in active_dates:
        result += 1
        cursor -= timedelta(days=1)
    return result


def _best_streak(active_dates: set[str]) -> int:
    result = current = 0
    previous: date | None = None
    for day in sorted(filter(None, (_parse_date_key(value) for value in active_dates))):
        current = current + 1 if previous and day - previous == timedelta(days=1) else 1
        result = max(result, current)
        previous = day
    return result


def _initials(value: str) -> str:
    parts = [part for part in value.strip().split() if part]
    if not parts:
        return "A"
    return "".join(part[0] for part in parts[:2]).upper()


def _valid_date_key(value: Any) -> str | None:
    parsed = _parse_date_key(value)
    return parsed.isoformat() if parsed is not None else None


def _parse_date_key(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
