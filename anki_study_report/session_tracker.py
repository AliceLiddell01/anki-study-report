"""Reviewer-session time tracking for Anki Study Report.

The tracker measures activity inside Anki's reviewer only. It does not count
background Anki uptime or a merely focused main window.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
import json
from pathlib import Path
import traceback
from typing import Any


TRACKER_FILENAME = "anki_study_report_review_intervals.jsonl"
DEFAULT_IDLE_TIMEOUT_SECONDS = 10 * 60
DEFAULT_GAP_CAP_SECONDS = 2 * 60
MAX_LOG_LINES = 200
_LOG_LINES: list[str] = []
_HOOKS_REGISTERED = False
_LAST_ACTIVITY_TS: int | None = None
_LAST_CARD_ID: int | None = None
_LAST_DECK_ID: int | None = None


def setup_session_tracking(gui_hooks: Any, mw: Any) -> None:
    """Attach reviewer hooks when Anki exposes them."""

    global _HOOKS_REGISTERED
    if _HOOKS_REGISTERED:
        return

    registered: list[str] = []
    for hook_name, callback in (
        ("reviewer_did_show_question", _on_reviewer_activity),
        ("reviewer_did_show_answer", _on_reviewer_activity),
        ("reviewer_did_answer_card", _on_reviewer_answer),
    ):
        hook = getattr(gui_hooks, hook_name, None)
        if hook is None or not hasattr(hook, "append"):
            continue
        try:
            hook.append(
                lambda *args, _event=hook_name, _callback=callback: _callback(
                    mw,
                    _event,
                    *args,
                )
            )
            registered.append(hook_name)
        except Exception:
            _log(f"Не удалось подключить hook {hook_name}.")
            traceback.print_exc()

    state_hook = getattr(gui_hooks, "state_did_change", None)
    if state_hook is not None and hasattr(state_hook, "append"):
        try:
            state_hook.append(lambda *args: _on_state_did_change(*args))
            registered.append("state_did_change")
        except Exception:
            _log("Не удалось подключить hook state_did_change.")
            traceback.print_exc()

    _HOOKS_REGISTERED = True
    if registered:
        _log("Трекер повторений подключён: " + ", ".join(registered))
    else:
        _log("Трекер повторений не нашёл поддерживаемых reviewer hooks.")


def collect_tracked_study_time(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Return measured reviewer time from this add-on's profile-local journal."""

    try:
        start = _to_seconds(start_ts)
        end = _to_seconds(end_ts)
        if end <= start:
            return unavailable_tracked_time("invalid_period")

        journal_path = _tracker_journal_path()
        if journal_path is None or not journal_path.is_file():
            return unavailable_tracked_time(
                "no_journal",
                "Реальное время занятий недоступно: трекер повторений ещё не создал журнал.",
            )

        selected_decks = _normalized_deck_ids(deck_ids)
        total_seconds = 0
        interval_count = 0
        found_records = 0
        for record in _iter_interval_records(journal_path):
            found_records += 1
            started_at = _record_int(record.get("started_at"))
            if started_at < start or started_at >= end:
                continue
            if selected_decks is not None and _record_int(record.get("deck_id")) not in selected_decks:
                continue
            total_seconds += max(0, _record_int(record.get("duration_seconds")))
            interval_count += 1

        if found_records <= 0:
            return unavailable_tracked_time(
                "no_data",
                "Реальное время занятий недоступно: трекер повторений ещё не накопил данных.",
            )

        scope = (
            "с учётом выбранных колод"
            if deck_ids is not None
            else "по всей коллекции"
        )
        return {
            "available": True,
            "enabled": True,
            "status": "ok",
            "total_seconds": total_seconds,
            "estimated_minutes": round(total_seconds / 60, 1) if total_seconds > 0 else 0.0,
            "source": "Anki Study Report: трекер повторений",
            "scope": scope,
            "deck_filtered": deck_ids is not None,
            "message": "",
            "interval_count": interval_count,
        }
    except Exception:
        _log("Ошибка чтения журнала трекера повторений.")
        traceback.print_exc()
        return unavailable_tracked_time(
            "error",
            "Реальное время занятий недоступно: ошибка чтения журнала трекера.",
        )


def unavailable_tracked_time(
    status: str = "unavailable",
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "available": False,
        "enabled": status != "disabled",
        "status": status,
        "total_seconds": 0,
        "estimated_minutes": 0.0,
        "source": "Anki Study Report: трекер повторений",
        "scope": "unknown",
        "deck_filtered": False,
        "message": message or "Реальное время занятий недоступно.",
    }


def diagnose_session_tracker(col: Any | None = None) -> str:
    lines = [
        "Anki Study Report: трекер повторений",
        "Принцип: считаются только интервалы между событиями reviewer.",
        f"Таймаут простоя: {DEFAULT_IDLE_TIMEOUT_SECONDS // 60} мин по умолчанию.",
        f"Максимум одного интервала: {DEFAULT_GAP_CAP_SECONDS // 60} мин по умолчанию.",
    ]
    if col is None:
        lines.append("Коллекция Anki недоступна.")
        return "\n".join(lines)

    try:
        journal_path = _tracker_journal_path()
        if journal_path is None or not journal_path.is_file():
            lines.append("Журнал: ещё не создан.")
            return "\n".join(lines)

        count = 0
        total_seconds = 0
        first_started_at: int | None = None
        last_ended_at: int | None = None
        for record in _iter_interval_records(journal_path):
            count += 1
            total_seconds += max(0, _record_int(record.get("duration_seconds")))
            started_at = _record_int(record.get("started_at"))
            ended_at = _record_int(record.get("ended_at"))
            if started_at:
                first_started_at = (
                    started_at
                    if first_started_at is None
                    else min(first_started_at, started_at)
                )
            if ended_at:
                last_ended_at = (
                    ended_at
                    if last_ended_at is None
                    else max(last_ended_at, ended_at)
                )

        lines.append(f"Журнал: создан, интервалов: {count}.")
        lines.append(f"Всего накоплено: {_format_duration(total_seconds)}.")
        lines.append(f"Файл журнала: {journal_path}.")
        if first_started_at and last_ended_at:
            lines.append(f"Первый интервал: {_format_ts(first_started_at)}.")
            lines.append(f"Последний интервал: {_format_ts(last_ended_at)}.")
    except Exception:
        lines.append("Не удалось прочитать журнал трекера. Подробности в консоли Anki.")
        traceback.print_exc()
    return "\n".join(lines)


def session_tracker_log_text() -> str:
    if not _LOG_LINES:
        return "Лог трекера повторений пока пуст."
    return "\n".join(_LOG_LINES[-MAX_LOG_LINES:])


def _on_reviewer_answer(mw: Any, event_name: str, *args: Any) -> None:
    _on_reviewer_activity(mw, event_name, *args)


def _on_reviewer_activity(mw: Any, event_name: str, *args: Any) -> None:
    global _LAST_ACTIVITY_TS, _LAST_CARD_ID, _LAST_DECK_ID
    try:
        if mw is None or mw.col is None:
            return
        config = _read_config(mw)
        if not bool(config.get("track_reviewer_sessions", False)):
            _reset_activity()
            return

        now = int(datetime.now().timestamp())
        card = _card_from_args(args)
        card_id = _card_id(card)
        deck_id = _deck_id(card)

        if _LAST_ACTIVITY_TS is not None:
            gap = now - _LAST_ACTIVITY_TS
            idle_timeout = _positive_int(
                config.get("session_idle_timeout_seconds"),
                DEFAULT_IDLE_TIMEOUT_SECONDS,
            )
            gap_cap = _positive_int(
                config.get("session_gap_cap_seconds"),
                DEFAULT_GAP_CAP_SECONDS,
            )
            if 0 < gap <= idle_timeout:
                _insert_interval(
                    mw,
                    _LAST_ACTIVITY_TS,
                    now,
                    min(gap, gap_cap),
                    _LAST_DECK_ID,
                    _LAST_CARD_ID,
                    event_name,
                )
            elif gap > idle_timeout:
                _log(f"Сессия повторения разорвана после простоя {gap} сек.")

        _LAST_ACTIVITY_TS = now
        _LAST_CARD_ID = card_id
        _LAST_DECK_ID = deck_id
    except Exception:
        _log("Ошибка записи интервала трекера повторений.")
        traceback.print_exc()


def _on_state_did_change(*args: Any) -> None:
    new_state = str(args[0]) if args else ""
    if new_state != "review":
        _reset_activity()


def _reset_activity() -> None:
    global _LAST_ACTIVITY_TS, _LAST_CARD_ID, _LAST_DECK_ID
    _LAST_ACTIVITY_TS = None
    _LAST_CARD_ID = None
    _LAST_DECK_ID = None


def _insert_interval(
    mw: Any,
    started_at: int,
    ended_at: int,
    duration_seconds: int,
    deck_id: int | None,
    card_id: int | None,
    event_name: str,
) -> None:
    if duration_seconds <= 0:
        return
    journal_path = _tracker_journal_path(mw, create_parent=True)
    if journal_path is None:
        _log("Не удалось найти папку профиля для журнала трекера повторений.")
        return

    record = {
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "deck_id": deck_id,
        "card_id": card_id,
        "event_name": event_name,
        "created_at": int(datetime.now().timestamp()),
    }
    with journal_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        file.write("\n")


def _normalized_deck_ids(deck_ids: Sequence[int] | None) -> set[int] | None:
    if deck_ids is None:
        return None
    normalized = {int(deck_id) for deck_id in deck_ids}
    if not normalized:
        return set()
    return normalized


def _iter_interval_records(journal_path: Path) -> Iterable[dict[str, Any]]:
    try:
        with journal_path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    yield record
    except FileNotFoundError:
        return


def _tracker_journal_path(
    mw: Any | None = None,
    create_parent: bool = False,
) -> Path | None:
    if mw is None:
        try:
            from aqt import mw as anki_mw  # type: ignore
        except Exception:
            anki_mw = None
        mw = anki_mw

    profile_folder = _profile_folder(mw)
    if profile_folder is None:
        return None

    directory = profile_folder / "anki_study_report"
    if create_parent:
        directory.mkdir(parents=True, exist_ok=True)
    return directory / TRACKER_FILENAME


def _profile_folder(mw: Any | None) -> Path | None:
    if mw is None:
        return None

    profile_manager = getattr(mw, "pm", None)
    if profile_manager is None:
        return None

    for attr in ("profileFolder", "profile_folder"):
        value = getattr(profile_manager, attr, None)
        try:
            folder = value() if callable(value) else value
        except Exception:
            continue
        if folder:
            return Path(str(folder))
    return None


def _record_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _card_from_args(args: Iterable[Any]) -> Any | None:
    for value in args:
        if hasattr(value, "id") and hasattr(value, "did"):
            return value
        card = getattr(value, "card", None)
        if card is not None and hasattr(card, "id") and hasattr(card, "did"):
            return card
    return None


def _card_id(card: Any | None) -> int | None:
    try:
        return int(card.id) if card is not None else None
    except Exception:
        return None


def _deck_id(card: Any | None) -> int | None:
    try:
        return int(card.did) if card is not None else None
    except Exception:
        return None


def _read_config(mw: Any) -> dict[str, Any]:
    try:
        config = mw.addonManager.getConfig(__package__)
    except Exception:
        config = None
    return dict(config or {})


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _to_seconds(ts: int | float) -> int:
    value = int(ts)
    if abs(value) > 10_000_000_000:
        return int(value / 1000)
    return value


def _format_duration(total_seconds: int) -> str:
    minutes = round(total_seconds / 60)
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} ч {rest} мин"
    if hours:
        return f"{hours} ч"
    return f"{rest} мин"


def _format_ts(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _LOG_LINES.append(f"[{timestamp}] {message}")
    if len(_LOG_LINES) > MAX_LOG_LINES:
        del _LOG_LINES[:-MAX_LOG_LINES]
