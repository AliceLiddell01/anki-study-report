"""Optional Study Time Stats Personal integration.

This module deliberately reads data files/tables instead of importing the
other add-on. The integration must never be required for Anki Study Report.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import sqlite3
import tempfile
import traceback
from typing import Any
from zipfile import ZipFile


STUDY_TIME_STATS_ADDON_ID = "1247171202"
MAX_LOG_LINES = 200
MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_SQLITE_BYTES = 20 * 1024 * 1024
MAX_ROWS_PER_TABLE = 50_000
MAX_RECORDS_PER_SOURCE = 50_000
SECONDS_IN_DAY = 86_400
ALLOWED_DATA_FILE_NAMES = {
    "study_time_stats.json",
    "study_time_stats.db",
    "study_time_stats.sqlite",
    "study_time_stats.sqlite3",
    "study_sessions.json",
    "study_sessions.db",
    "study_sessions.sqlite",
    "study_sessions.sqlite3",
    "sessions.json",
    "sessions.db",
    "sessions.sqlite",
    "sessions.sqlite3",
}
ALLOWED_DATA_DIRS = {"", "data", "user_files", "meta"}
ALLOWED_TABLE_NAMES = {
    "study_time_stats",
    "study_time_sessions",
    "study_sessions",
    "sessions",
    "review_sessions",
}
TIMESTAMP_KEYS = (
    "date",
    "day",
    "started",
    "started_at",
    "start",
    "start_at",
    "start_time",
    "begin",
    "began",
    "began_at",
    "timestamp",
    "created",
    "created_at",
)
DURATION_KEYS = (
    "duration",
    "duration_s",
    "duration_sec",
    "duration_secs",
    "duration_seconds",
    "duration_ms",
    "elapsed",
    "elapsed_s",
    "elapsed_seconds",
    "study_time",
    "study_seconds",
    "total_time",
    "total_seconds",
    "seconds",
    "session_time",
    "real_time",
    "actual_time",
    "time_spent",
    "minutes",
    "hours",
)
END_KEYS = ("ended", "ended_at", "end", "end_at", "end_time", "stop", "stopped_at")
DECK_ID_KEYS = ("deck_id", "deckid", "did")
DECK_NAME_KEYS = ("deck", "deck_name", "deckname")
_LOG_LINES: list[str] = []
_LIMIT_EXCEEDED = False


@dataclass
class SourceResult:
    seconds: int
    found_records: int
    matched_records: int
    source: str
    deck_filtered: bool
    has_deck_data: bool


def integration_log_text() -> str:
    if not _LOG_LINES:
        return "Лог интеграций пока пуст."
    return "\n".join(_LOG_LINES[-MAX_LOG_LINES:])


def diagnose_study_time_stats(col: Any | None = None) -> str:
    """Return a human-readable diagnostic report for the optional integration."""

    lines = [
        "Study Time Stats Personal",
        f"ID дополнения: {STUDY_TIME_STATS_ADDON_ID}",
    ]
    paths = _candidate_addon_paths()
    existing_paths = [path for path in paths if path.exists()]
    if existing_paths:
        lines.append("Статус: найдено")
        for path in existing_paths:
            kind = "папка" if path.is_dir() else "архив" if path.suffix.lower() == ".zip" else "файл"
            lines.append(f"- {kind}: {path}")
    else:
        lines.append("Статус: не найдено")
        lines.append("Проверенные места:")
        lines.extend(f"- {path}" for path in paths)
        return "\n".join(lines)

    if col is not None:
        table_names = _relevant_collection_table_names(col)
        if table_names:
            lines.append("Таблицы коллекции с похожими данными:")
            lines.extend(f"- {table}" for table in table_names)
        else:
            lines.append("Таблицы коллекции с отдельными сессиями: не найдены")

    file_names = _candidate_data_file_names(existing_paths)
    if file_names:
        lines.append("Файлы-кандидаты с данными:")
        lines.extend(f"- {name}" for name in file_names)
    else:
        lines.append("Файлы JSON/SQLite с отдельными сессиями: не найдены")

    lines.append(
        "Вывод: локальная версия Study Time Stats Personal, которую удалось прочитать, "
        "считает время на лету из revlog.time. Отдельное хранилище реальных сессий не найдено."
    )
    return "\n".join(lines)


def unavailable_study_time(status: str = "unavailable", message: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "enabled": status != "disabled",
        "status": status,
        "total_seconds": 0,
        "estimated_minutes": 0.0,
        "source": "",
        "scope": "unknown",
        "deck_filtered": False,
        "message": message or "Реальное время занятий недоступно.",
    }


def collect_real_study_time(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Return real study time if Study Time Stats Personal data is readable."""

    try:
        global _LIMIT_EXCEEDED
        _LIMIT_EXCEEDED = False
        start = _to_seconds(start_ts)
        end = _to_seconds(end_ts)
        if end <= start:
            return unavailable_study_time("invalid_period")

        deck_context = _deck_context(col, deck_ids)
        results: list[SourceResult] = []
        results.extend(_from_collection_tables(col, start, end, deck_context))
        results.extend(_from_addon_files(start, end, deck_context))

        best = _best_result(results)
        if best is None:
            if _LIMIT_EXCEEDED:
                return unavailable_study_time(
                    "too_large",
                    "Реальное время занятий недоступно: данные Study Time Stats слишком большие для безопасного чтения.",
                )
            if _study_time_stats_is_installed():
                _log("Study Time Stats найден, но отдельные записи учебных сессий не обнаружены.")
                return unavailable_study_time(
                    "revlog_only",
                    "Реальное время занятий недоступно: установленная версия Study Time Stats считает время из revlog.time и не хранит отдельные сессии.",
                )
            return unavailable_study_time(
                "not_found",
                "Реальное время занятий недоступно: данные Study Time Stats не найдены.",
            )

        scope = _scope_text(best, deck_context)
        return {
            "available": True,
            "enabled": True,
            "status": "ok",
            "total_seconds": best.seconds,
            "estimated_minutes": round(best.seconds / 60, 1) if best.seconds > 0 else 0.0,
            "source": best.source,
            "scope": scope,
            "deck_filtered": best.deck_filtered,
            "message": "",
        }
    except Exception:
        _log("Study Time Stats integration failed.")
        print("[Anki Study Report] Study Time Stats integration failed:")
        traceback.print_exc()
        return unavailable_study_time(
            "error",
            "Реальное время занятий недоступно: ошибка чтения Study Time Stats.",
        )


def _best_result(results: list[SourceResult]) -> SourceResult | None:
    if not results:
        return None

    return sorted(
        results,
        key=lambda result: (
            result.deck_filtered,
            result.matched_records > 0,
            result.seconds,
            result.found_records,
        ),
        reverse=True,
    )[0]


def _scope_text(result: SourceResult, deck_context: dict[str, Any]) -> str:
    if deck_context["deck_ids"] is None:
        return "по всей коллекции"
    if result.deck_filtered:
        return "с учётом выбранных колод"
    if result.has_deck_data:
        return "по выбранным колодам; часть записей без колоды пропущена"
    return "по всей коллекции, без фильтра по колодам"


def _from_collection_tables(
    col: Any,
    start: int,
    end: int,
    deck_context: dict[str, Any],
) -> list[SourceResult]:
    try:
        rows = col.db.all(
            "select name from sqlite_master where type = 'table' order by name"
        )
    except Exception:
        return []

    results: list[SourceResult] = []
    for row in rows:
        table = str(row[0]) if row else ""
        if not _source_name_is_allowed(table):
            continue
        result = _source_result_from_collection_table(col, table, start, end, deck_context)
        if result is not None:
            results.append(result)
    return results


def _relevant_collection_table_names(col: Any) -> list[str]:
    try:
        rows = col.db.all(
            "select name from sqlite_master where type = 'table' order by name"
        )
    except Exception:
        return []

    names: list[str] = []
    for row in rows:
        table = str(row[0]) if row else ""
        if not _source_name_is_allowed(table):
            continue
        try:
            columns = [str(info[1]) for info in col.db.all(f'pragma table_info("{table}")')]
        except Exception:
            continue
        if _columns_look_like_time_records(columns):
            names.append(table)
    return names


def _source_result_from_collection_table(
    col: Any,
    table: str,
    start: int,
    end: int,
    deck_context: dict[str, Any],
) -> SourceResult | None:
    try:
        columns = [str(row[1]) for row in col.db.all(f'pragma table_info("{table}")')]
    except Exception:
        return None

    if not _columns_look_like_time_records(columns):
        return None

    column_sql = ", ".join(f'"{column}"' for column in columns)
    try:
        rows = col.db.all(f'select {column_sql} from "{table}" limit {MAX_ROWS_PER_TABLE + 1}')
    except Exception:
        return None
    if len(rows) > MAX_ROWS_PER_TABLE:
        _mark_limit_exceeded(f"Таблица Study Time Stats слишком большая: {table}")
        return None

    records = [dict(zip(columns, row)) for row in rows[:MAX_ROWS_PER_TABLE]]
    return _sum_records(
        records,
        start,
        end,
        deck_context,
        source=f"Study Time Stats: таблица коллекции {table}",
    )


def _from_addon_files(
    start: int,
    end: int,
    deck_context: dict[str, Any],
) -> list[SourceResult]:
    results: list[SourceResult] = []
    for base in _candidate_addon_paths():
        if base.is_dir():
            results.extend(_from_directory(base, start, end, deck_context))
        elif base.is_file() and base.suffix.lower() == ".zip":
            results.extend(_from_zip(base, start, end, deck_context))
    return results


def _study_time_stats_is_installed() -> bool:
    return any(path.exists() for path in _candidate_addon_paths())


def _candidate_addon_paths() -> list[Path]:
    current_addon_dir = Path(__file__).resolve().parent
    home = Path.home()
    candidate_roots = [
        current_addon_dir.parent,
        current_addon_dir.parent.parent,
        home / "AppData" / "Roaming" / "Anki2" / "addons21",
        home / "Library" / "Application Support" / "Anki2" / "addons21",
        home / ".local" / "share" / "Anki2" / "addons21",
    ]
    paths: list[Path] = []
    for root in candidate_roots:
        for candidate in (
            root / STUDY_TIME_STATS_ADDON_ID,
            root / f"{STUDY_TIME_STATS_ADDON_ID}.zip",
        ):
            if candidate not in paths:
                paths.append(candidate)
    return paths


def _from_directory(
    base: Path,
    start: int,
    end: int,
    deck_context: dict[str, Any],
) -> list[SourceResult]:
    results: list[SourceResult] = []
    for file_path in _allowed_data_files(base):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            result = _from_sqlite_path(file_path, start, end, deck_context)
            if result is not None:
                results.append(result)
        elif file_path.suffix.lower() == ".json":
            result = _from_json_bytes(
                _safe_read_bytes(file_path),
                start,
                end,
                deck_context,
                source=f"Study Time Stats: {file_path.name}",
            )
            if result is not None:
                results.append(result)
    return results


def _from_zip(
    zip_path: Path,
    start: int,
    end: int,
    deck_context: dict[str, Any],
) -> list[SourceResult]:
    results: list[SourceResult] = []
    try:
        with ZipFile(zip_path) as archive:
            for info in archive.infolist():
                suffix = Path(info.filename).suffix.lower()
                name = Path(info.filename).name
                if info.is_dir() or not _data_file_name_is_allowed(name):
                    continue
                if suffix == ".json" and info.file_size > MAX_JSON_BYTES:
                    _mark_limit_exceeded(f"JSON Study Time Stats слишком большой: {name}")
                    continue
                if suffix in {".db", ".sqlite", ".sqlite3"} and info.file_size > MAX_SQLITE_BYTES:
                    _mark_limit_exceeded(f"SQLite Study Time Stats слишком большой: {name}")
                    continue
                if suffix == ".json":
                    result = _from_json_bytes(
                        archive.read(info),
                        start,
                        end,
                        deck_context,
                        source=f"Study Time Stats: архив {name}",
                    )
                    if result is not None:
                        results.append(result)
                elif suffix in {".db", ".sqlite", ".sqlite3"}:
                    result = _from_sqlite_bytes(
                        archive.read(info),
                        start,
                        end,
                        deck_context,
                        source=f"Study Time Stats: архив {name}",
                    )
                    if result is not None:
                        results.append(result)
    except Exception:
        _log(f"Не удалось прочитать архив Study Time Stats: {zip_path}")
        print(f"[Anki Study Report] Could not read Study Time Stats archive: {zip_path}")
        traceback.print_exc()
    return results


def _from_json_bytes(
    raw: bytes | None,
    start: int,
    end: int,
    deck_context: dict[str, Any],
    source: str,
) -> SourceResult | None:
    if not raw or len(raw) > MAX_JSON_BYTES:
        return None
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return None
    return _sum_records(_iter_dict_records(data), start, end, deck_context, source)


def _from_sqlite_path(
    file_path: Path,
    start: int,
    end: int,
    deck_context: dict[str, Any],
    source: str | None = None,
) -> SourceResult | None:
    try:
        if file_path.stat().st_size > MAX_SQLITE_BYTES:
            _mark_limit_exceeded(f"SQLite Study Time Stats слишком большой: {file_path.name}")
            return None
        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as db:
            return _from_sqlite_connection(
                db,
                start,
                end,
                deck_context,
                source=source or f"Study Time Stats: {file_path.name}",
            )
    except Exception:
        _log(f"Не удалось прочитать базу Study Time Stats: {file_path}")
        print(f"[Anki Study Report] Could not read Study Time Stats database: {file_path}")
        traceback.print_exc()
        return None


def _from_sqlite_bytes(
    raw: bytes,
    start: int,
    end: int,
    deck_context: dict[str, Any],
    source: str,
) -> SourceResult | None:
    if not raw:
        return None
    if len(raw) > MAX_SQLITE_BYTES:
        _mark_limit_exceeded(f"SQLite Study Time Stats слишком большой: {source}")
        return None
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as temp:
            temp.write(raw)
            temp_path = Path(temp.name)
        return _from_sqlite_path(temp_path, start, end, deck_context, source=source)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


def _from_sqlite_connection(
    db: sqlite3.Connection,
    start: int,
    end: int,
    deck_context: dict[str, Any],
    source: str,
) -> SourceResult | None:
    try:
        tables = [
            row[0]
            for row in db.execute(
                "select name from sqlite_master where type = 'table' order by name"
            )
        ]
    except sqlite3.Error:
        return None

    best: SourceResult | None = None
    for table in tables:
        if not _source_name_is_allowed(str(table)):
            continue
        try:
            columns = [row[1] for row in db.execute(f'pragma table_info("{table}")')]
        except sqlite3.Error:
            continue
        if not _columns_look_like_time_records(columns):
            continue
        column_sql = ", ".join(f'"{column}"' for column in columns)
        try:
            cursor = db.execute(
                f'select {column_sql} from "{table}" limit {MAX_ROWS_PER_TABLE + 1}'
            )
            records = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error:
            continue
        if len(records) > MAX_ROWS_PER_TABLE:
            _mark_limit_exceeded(f"Таблица Study Time Stats слишком большая: {table}")
            continue
        records = records[:MAX_ROWS_PER_TABLE]
        result = _sum_records(records, start, end, deck_context, f"{source}, таблица {table}")
        if result is not None and (
            best is None or (result.seconds, result.found_records) > (best.seconds, best.found_records)
        ):
            best = result
    return best


def _sum_records(
    records: Iterable[dict[str, Any]],
    start: int,
    end: int,
    deck_context: dict[str, Any],
    source: str,
) -> SourceResult | None:
    total_seconds = 0.0
    found_records = 0
    matched_records = 0
    has_deck_data = False
    used_deck_filter = False

    for index, record in enumerate(records, start=1):
        if index > MAX_RECORDS_PER_SOURCE:
            _mark_limit_exceeded(f"Источник Study Time Stats содержит слишком много записей: {source}")
            break
        timestamp = _record_timestamp(record)
        duration = _record_duration_seconds(record)
        if timestamp is None or duration is None:
            continue
        found_records += 1
        if not _timestamp_in_period(timestamp, start, end):
            continue

        deck_match, has_record_deck = _record_matches_decks(record, deck_context)
        has_deck_data = has_deck_data or has_record_deck
        used_deck_filter = used_deck_filter or (deck_context["deck_ids"] is not None and has_record_deck)
        if not deck_match:
            continue

        matched_records += 1
        total_seconds += max(duration, 0.0)

    if found_records <= 0:
        return None
    return SourceResult(
        seconds=int(round(total_seconds)),
        found_records=found_records,
        matched_records=matched_records,
        source=source,
        deck_filtered=used_deck_filter,
        has_deck_data=has_deck_data,
    )


def _record_timestamp(record: dict[str, Any]) -> int | tuple[date, date] | None:
    lowered = _lowered_record(record)
    for key in TIMESTAMP_KEYS:
        if key in lowered:
            parsed = _parse_timestamp(lowered[key])
            if parsed is not None:
                return parsed

    start = _first_parsed_timestamp(lowered, TIMESTAMP_KEYS)
    end = _first_parsed_timestamp(lowered, END_KEYS)
    if start is not None and end is not None:
        return start
    return None


def _record_duration_seconds(record: dict[str, Any]) -> float | None:
    lowered = _lowered_record(record)
    for key in DURATION_KEYS:
        if key in lowered:
            duration = _parse_duration(lowered[key], key)
            if duration is not None:
                return duration

    start = _first_parsed_timestamp(lowered, TIMESTAMP_KEYS)
    end = _first_parsed_timestamp(lowered, END_KEYS)
    if isinstance(start, int) and isinstance(end, int) and end > start:
        return float(end - start)
    return None


def _record_matches_decks(
    record: dict[str, Any],
    deck_context: dict[str, Any],
) -> tuple[bool, bool]:
    selected_ids = deck_context["deck_ids"]
    if selected_ids is None:
        return True, _record_has_deck_data(record)

    lowered = _lowered_record(record)
    for key in DECK_ID_KEYS:
        if key not in lowered:
            continue
        try:
            return int(lowered[key]) in selected_ids, True
        except (TypeError, ValueError):
            continue

    selected_names = deck_context["deck_names"]
    for key in DECK_NAME_KEYS:
        if key not in lowered:
            continue
        name = str(lowered[key] or "").lower()
        if not name:
            continue
        return name in selected_names, True

    return True, False


def _record_has_deck_data(record: dict[str, Any]) -> bool:
    lowered = _lowered_record(record)
    return any(key in lowered for key in (*DECK_ID_KEYS, *DECK_NAME_KEYS))


def _deck_context(col: Any, deck_ids: Sequence[int] | None) -> dict[str, Any]:
    selected = None if deck_ids is None else {int(deck_id) for deck_id in deck_ids}
    names: set[str] = set()
    if selected:
        try:
            for deck in col.decks.all_names_and_ids():
                if int(deck.id) in selected:
                    names.add(str(deck.name).lower())
        except Exception:
            pass
    return {"deck_ids": selected, "deck_names": names}


def _allowed_data_files(base: Path) -> Iterable[Path]:
    for directory in ALLOWED_DATA_DIRS:
        root = base / directory if directory else base
        if not root.is_dir():
            continue
        for name in ALLOWED_DATA_FILE_NAMES:
            yield root / name


def _safe_read_bytes(file_path: Path) -> bytes | None:
    try:
        if file_path.stat().st_size > MAX_JSON_BYTES:
            _mark_limit_exceeded(f"JSON Study Time Stats слишком большой: {file_path.name}")
            return None
        return file_path.read_bytes()
    except Exception:
        _log(f"Не удалось прочитать файл Study Time Stats: {file_path}")
        print(f"[Anki Study Report] Could not read Study Time Stats file: {file_path}")
        traceback.print_exc()
        return None


def _iter_dict_records(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, dict):
        if _columns_look_like_time_records(data.keys()):
            yield data
        for value in data.values():
            yield from _iter_dict_records(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_dict_records(item)


def _columns_look_like_time_records(columns: Iterable[str]) -> bool:
    lowered = {str(column).lower() for column in columns}
    has_time = any(key in lowered for key in TIMESTAMP_KEYS)
    has_duration = any(key in lowered for key in DURATION_KEYS)
    has_end = any(key in lowered for key in END_KEYS)
    return has_time and (has_duration or has_end)


def _source_name_is_allowed(name: str) -> bool:
    return name.lower() in ALLOWED_TABLE_NAMES


def _data_file_name_is_allowed(name: str) -> bool:
    return name.lower() in ALLOWED_DATA_FILE_NAMES


def _mark_limit_exceeded(message: str) -> None:
    global _LIMIT_EXCEEDED
    _LIMIT_EXCEEDED = True
    _log(message)


def _candidate_data_file_names(paths: Iterable[Path]) -> list[str]:
    names: list[str] = []
    for base in paths:
        if base.is_dir():
            for file_path in _allowed_data_files(base):
                if not file_path.is_file():
                    continue
                suffix = file_path.suffix.lower()
                if suffix == ".json" and _json_file_has_time_records(file_path):
                    names.append(str(file_path))
                elif suffix in {".db", ".sqlite", ".sqlite3"} and _sqlite_file_has_time_records(file_path):
                    names.append(str(file_path))
        elif base.is_file() and base.suffix.lower() == ".zip":
            try:
                with ZipFile(base) as archive:
                    for info in archive.infolist():
                        suffix = Path(info.filename).suffix.lower()
                        name = Path(info.filename).name
                        if not _data_file_name_is_allowed(name):
                            continue
                        if suffix == ".json" and info.file_size <= MAX_JSON_BYTES and _json_bytes_have_time_records(archive.read(info)):
                            names.append(f"{base}!{info.filename}")
                        elif suffix in {".db", ".sqlite", ".sqlite3"} and info.file_size <= MAX_SQLITE_BYTES:
                            names.append(f"{base}!{info.filename}")
            except Exception:
                _log(f"Не удалось перечислить архив Study Time Stats: {base}")
    return names[:50]


def _json_file_has_time_records(file_path: Path) -> bool:
    raw = _safe_read_bytes(file_path)
    return _json_bytes_have_time_records(raw)


def _json_bytes_have_time_records(raw: bytes | None) -> bool:
    if not raw or len(raw) > MAX_JSON_BYTES:
        return False
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return False
    return any(True for _record in _iter_dict_records(data))


def _sqlite_file_has_time_records(file_path: Path) -> bool:
    try:
        if file_path.stat().st_size > MAX_SQLITE_BYTES:
            return False
        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as db:
            tables = [
                row[0]
                for row in db.execute(
                    "select name from sqlite_master where type = 'table' order by name"
                )
            ]
            for table in tables:
                if not _source_name_is_allowed(str(table)):
                    continue
                columns = [row[1] for row in db.execute(f'pragma table_info("{table}")')]
                if _columns_look_like_time_records(columns):
                    return True
    except Exception:
        return False
    return False


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _LOG_LINES.append(f"[{timestamp}] {message}")
    if len(_LOG_LINES) > MAX_LOG_LINES:
        del _LOG_LINES[:-MAX_LOG_LINES]


def _lowered_record(record: dict[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in record.items()}


def _first_parsed_timestamp(
    lowered: dict[str, Any],
    keys: Iterable[str],
) -> int | tuple[date, date] | None:
    for key in keys:
        if key in lowered:
            parsed = _parse_timestamp(lowered[key])
            if parsed is not None:
                return parsed
    return None


def _parse_timestamp(value: Any) -> int | tuple[date, date] | None:
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, date):
        return value, value
    if isinstance(value, (int, float)):
        return _parse_numeric_timestamp(float(value))

    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        numeric = float(text)
        if len(text) == 8:
            try:
                parsed_date = datetime.strptime(text, "%Y%m%d").date()
                return parsed_date, parsed_date
            except ValueError:
                pass
        return _parse_numeric_timestamp(numeric)

    normalized = text.replace("Z", "+00:00")
    for parser in (
        lambda: datetime.fromisoformat(normalized),
        lambda: datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S"),
        lambda: datetime.strptime(text[:10], "%Y-%m-%d"),
    ):
        try:
            parsed = parser()
        except ValueError:
            continue
        if isinstance(parsed, datetime):
            if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0 and len(text) <= 10:
                parsed_date = parsed.date()
                return parsed_date, parsed_date
            return int(parsed.timestamp())
    return None


def _parse_numeric_timestamp(value: float) -> int | None:
    if value <= 0:
        return None
    if value > 10_000_000_000_000:
        return int(value / 1_000_000)
    if value > 10_000_000_000:
        return int(value / 1000)
    if value > 100_000_000:
        return int(value)
    return None


def _parse_duration(value: Any, key: str) -> float | None:
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        text = str(value or "").strip()
        if not text:
            return None
        clock = _parse_clock_duration(text)
        if clock is not None:
            return clock
        try:
            numeric = float(text.replace(",", "."))
        except ValueError:
            return None

    lowered_key = key.lower()
    if "hour" in lowered_key:
        return numeric * 3600
    if "minute" in lowered_key or lowered_key in {"min", "mins"}:
        return numeric * 60
    if "ms" in lowered_key or "millis" in lowered_key:
        return numeric / 1000
    if numeric > SECONDS_IN_DAY * 7:
        return numeric / 1000
    return numeric


def _parse_clock_duration(text: str) -> float | None:
    parts = text.split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _timestamp_in_period(
    timestamp: int | tuple[date, date],
    start: int,
    end: int,
) -> bool:
    if isinstance(timestamp, tuple):
        start_date = datetime.fromtimestamp(start).date() if start > 0 else date.min
        end_date = datetime.fromtimestamp(max(end - 1, 0)).date()
        return timestamp[0] <= end_date and timestamp[1] >= start_date
    return start <= timestamp < end


def _to_seconds(ts: int | float) -> int:
    value = int(ts)
    if abs(value) > 10_000_000_000:
        return int(value / 1000)
    return value
