"""Rotating local logs for Anki Study Report."""

from __future__ import annotations

from logging import Filter, Formatter, Handler, LogRecord, getLogger
import logging
from pathlib import Path
import re
from typing import Any


LOG_DIR = Path(__file__).resolve().parent / "user_files" / "logs"
LOG_FILE = LOG_DIR / "anki_study_report.log"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 5
RECENT_LOG_BYTES = 200_000
_LOGGER_NAME = "anki_study_report"
_TOKEN_RE = re.compile(r"([?&]token=)([^&#\s]+)", re.IGNORECASE)
_SECRET_KEY_RE = re.compile(r"(token|secret|password|api[_-]?key)", re.IGNORECASE)


class _EventDefaults(Filter):
    def filter(self, record: LogRecord) -> bool:
        if not hasattr(record, "event"):
            record.event = "general"
        if not hasattr(record, "field_text"):
            record.field_text = ""
        return True


class _PerWriteRotatingFileHandler(Handler):
    """Write one record per short-lived file handle to avoid Windows update locks."""

    def __init__(self) -> None:
        super().__init__()
        self.addFilter(_EventDefaults())

    def emit(self, record: LogRecord) -> None:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            message = self.format(record)
            _rotate_logs_if_needed(len(message.encode("utf-8")) + 1)
            with LOG_FILE.open("a", encoding="utf-8") as file:
                file.write(message)
                file.write("\n")
        except Exception:
            self.handleError(record)


def get_logger() -> logging.Logger:
    logger = getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    handler = _PerWriteRotatingFileHandler()
    handler.setFormatter(
        Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)s | %(event)s | "
            "%(message)s%(field_text)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def configure_log_dir(log_dir: Path) -> None:
    """Move future log writes to a profile data directory."""

    global LOG_DIR, LOG_FILE
    logger = getLogger(_LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    LOG_DIR = Path(log_dir)
    LOG_FILE = LOG_DIR / "anki_study_report.log"


def log_event(event: str, message: str, **fields: Any) -> None:
    logger = get_logger()
    logger.info(
        _safe_text(message),
        extra={
            "event": _safe_text(event) or "general",
            "field_text": _format_fields(fields),
        },
    )


def log_exception(event: str, message: str, **fields: Any) -> None:
    logger = get_logger()
    logger.exception(
        _safe_text(message),
        extra={
            "event": _safe_text(event) or "general",
            "field_text": _format_fields(fields),
        },
    )


def get_log_file_paths() -> list[Path]:
    paths = [LOG_FILE]
    paths.extend(LOG_DIR / f"anki_study_report.log.{index}" for index in range(1, BACKUP_COUNT + 1))
    return paths


def read_recent_logs(max_bytes: int = RECENT_LOG_BYTES) -> str:
    path = LOG_FILE
    if not path.is_file():
        return ""
    limit = max(1, min(int(max_bytes or RECENT_LOG_BYTES), 1_000_000))
    size = path.stat().st_size
    with path.open("rb") as file:
        if size > limit:
            file.seek(size - limit)
        data = file.read(limit)
    return data.decode("utf-8", errors="replace")


def log_status(max_bytes: int = RECENT_LOG_BYTES) -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_FILE
    stat = path.stat() if path.is_file() else None
    return {
        "path": _mask_user_path(path),
        "fileName": path.name,
        "exists": path.is_file(),
        "size": stat.st_size if stat else 0,
        "modified": stat.st_mtime if stat else None,
        "maxBytes": MAX_BYTES,
        "backupCount": BACKUP_COUNT,
        "recentBytes": max_bytes,
    }


def clear_logs() -> None:
    logger = get_logger()
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for path in get_log_file_paths():
        try:
            if path == LOG_FILE:
                path.write_text("", encoding="utf-8")
            elif path.is_file():
                path.unlink()
        except OSError:
            pass
    get_logger()


def _rotate_logs_if_needed(incoming_bytes: int) -> None:
    try:
        current_size = LOG_FILE.stat().st_size if LOG_FILE.is_file() else 0
    except OSError:
        current_size = 0
    if current_size + max(0, incoming_bytes) <= MAX_BYTES:
        return

    oldest = LOG_DIR / f"anki_study_report.log.{BACKUP_COUNT}"
    try:
        if oldest.exists():
            oldest.unlink()
    except OSError:
        pass

    for index in range(BACKUP_COUNT - 1, 0, -1):
        source = LOG_DIR / f"anki_study_report.log.{index}"
        target = LOG_DIR / f"anki_study_report.log.{index + 1}"
        if not source.exists():
            continue
        try:
            source.rename(target)
        except OSError:
            pass

    if LOG_FILE.exists():
        try:
            LOG_FILE.rename(LOG_DIR / "anki_study_report.log.1")
        except OSError:
            pass


def redact(value: Any) -> str:
    text = str(value)
    text = _TOKEN_RE.sub(r"\1<hidden>", text)
    return text


def _format_fields(fields: dict[str, Any]) -> str:
    safe_fields = []
    for key, value in sorted(fields.items()):
        safe_key = _safe_text(key)
        if not safe_key:
            continue
        if _SECRET_KEY_RE.search(safe_key):
            safe_value = "<hidden>"
        else:
            safe_value = redact(value)
        safe_fields.append(f"{safe_key}={safe_value}")
    return f" | {' '.join(safe_fields)}" if safe_fields else ""


def _safe_text(value: Any) -> str:
    text = redact(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:1000]


def _mask_user_path(path: Path) -> str:
    parts = path.resolve().parts
    if "Users" in parts:
        index = parts.index("Users")
        if len(parts) > index + 2:
            return str(Path(*parts[: index + 2]) / "..." / Path(*parts[index + 3 :]))
    return str(path)
