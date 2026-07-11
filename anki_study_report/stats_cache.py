"""Persistent all-time statistics cache for Anki Study Report."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import closing
from datetime import datetime
from pathlib import Path
import json
import re
import sqlite3
import threading
import time
import traceback
from typing import Any

from .metrics import ANSWER_TIME_CAP_MS, REVLOG_REVIEW_FILTER_SQL


CACHE_SCHEMA_VERSION = 3
CACHE_STATUSES = {"ready", "scheduled", "building", "stale", "empty", "error"}
DEFAULT_CACHE_FILE = Path(__file__).resolve().parent / "user_files" / "study_report_cache.sqlite3"
DECK_HISTORY_NOTE = (
    "Deck daily aggregates use the card's current home deck; historical deck "
    "moves and renames are not reconstructed."
)
DATE_KEY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DAILY_COLUMNS = [
    "date",
    "reviews",
    "new_cards",
    "learning",
    "review",
    "relearning",
    "cram",
    "again",
    "hard",
    "good",
    "easy",
    "pass_count",
    "fail_count",
    "retention_young_pass",
    "retention_young_fail",
    "retention_mature_pass",
    "retention_mature_fail",
    "answer_time_count",
    "study_seconds",
    "total_answer_seconds",
]

DECK_DAILY_COLUMNS = [
    "date",
    "deck_id",
    "deck_name",
    "reviews",
    "new_cards",
    "learning",
    "review",
    "relearning",
    "cram",
    "again",
    "hard",
    "good",
    "easy",
    "pass_count",
    "fail_count",
    "retention_young_pass",
    "retention_young_fail",
    "retention_mature_pass",
    "retention_mature_fail",
    "answer_time_count",
    "study_seconds",
    "total_answer_seconds",
]


class StatsCacheManager:
    """Builds and serves all-time revlog aggregates from sqlite plus memory."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = Path(cache_path or DEFAULT_CACHE_FILE)
        self._lock = threading.RLock()
        self._building = False
        self._loaded = False
        self._daily: dict[str, dict[str, Any]] = {}
        self._deck_daily: dict[tuple[str, int], dict[str, Any]] = {}
        self._meta = _empty_meta()

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._load_from_disk_locked()
            return self._status_locked()

    def report_summary(self) -> dict[str, Any]:
        status = self.status()
        return {
            "status": status["status"],
            "updatedAt": status["updatedAt"],
            "cachedDays": status["cachedDays"],
            "cachedDeckDays": status["cachedDeckDays"],
        }

    def report_snapshot(self) -> dict[str, Any]:
        """Return immutable-ish all-time aggregate data for report adapters."""

        with self._lock:
            self._load_from_disk_locked()
            return {
                "status": self._status_locked(),
                "daily": [dict(row) for row in self._daily.values()],
                "deckDaily": [dict(row) for row in self._deck_daily.values()],
            }

    def prepare_rebuild(self) -> bool:
        return self._prepare_build("scheduled")

    def prepare_refresh(self) -> bool:
        return self._prepare_build("scheduled")

    def mark_building(self) -> bool:
        with self._lock:
            self._load_from_disk_locked()
            if not self._building and self._meta.get("status") not in {
                "scheduled",
                "building",
            }:
                return False
            self._building = True
            self._meta["status"] = "building"
            self._meta["error"] = None
            self._meta["updated_at"] = int(time.time())
            self._write_meta_best_effort_locked()
            return True

    def rebuild_all_time_cache(
        self,
        col: Any,
        profile_name: str | None = None,
        already_started: bool = False,
    ) -> dict[str, Any]:
        if not already_started and not self.prepare_rebuild():
            return {"ok": True, "status": "building", "alreadyBuilding": True}

        started_at = time.monotonic()
        try:
            rollover_hours = _anki_rollover_hours(col)
            daily_rows = _daily_rows(col, rollover_hours, min_revlog_id=None)
            deck_rows = _deck_daily_rows(col, rollover_hours, min_revlog_id=None)
            last_revlog_id = _last_revlog_id(col)
            now = int(time.time())
            meta = {
                "version": CACHE_SCHEMA_VERSION,
                "created_at": now,
                "updated_at": now,
                "last_revlog_id": last_revlog_id,
                "collection_scm": _collection_scm(col),
                "profile_name": profile_name,
                "status": "ready",
                "error": None,
                "last_build_duration_ms": _elapsed_ms(started_at),
                "last_refresh_duration_ms": _as_int(self._meta.get("last_refresh_duration_ms")),
                "last_refresh_added_rows": _as_int(self._meta.get("last_refresh_added_rows")),
                "last_error": None,
            }

            with closing(self._connect()) as conn:
                self._init_schema(conn, reset_outdated=True)
                with conn:
                    conn.execute("delete from daily_aggregates")
                    conn.execute("delete from deck_daily_aggregates")
                    _insert_daily_rows(conn, daily_rows)
                    _insert_deck_daily_rows(conn, deck_rows)
                    _write_meta(conn, meta)

            with self._lock:
                self._daily = {row["date"]: row for row in daily_rows}
                self._deck_daily = {
                    (row["date"], int(row["deck_id"])): row for row in deck_rows
                }
                self._meta = meta
                self._loaded = True
                self._building = False
                return {"ok": True, "status": "ready", **self._status_locked()}
        except Exception as error:
            traceback.print_exc()
            self.mark_error(error, build_duration_ms=_elapsed_ms(started_at))
            return {"ok": False, "status": "error", "error": _short_error(error)}

    def refresh_incremental(
        self,
        col: Any,
        profile_name: str | None = None,
        already_started: bool = False,
    ) -> dict[str, Any]:
        if not already_started and not self.prepare_refresh():
            return {"ok": True, "status": "building", "alreadyBuilding": True}

        started_at = time.monotonic()
        try:
            with self._lock:
                self._load_from_disk_locked()
                last_cached = _as_int(self._meta.get("last_revlog_id"))
                current_status = str(self._meta.get("status") or "empty")
                if _as_int(self._meta.get("version")) != CACHE_SCHEMA_VERSION:
                    self._mark_rebuild_required_locked(
                        "Cache schema is outdated. Rebuild required.",
                        refresh_duration_ms=_elapsed_ms(started_at),
                    )
                    return {
                        "ok": False,
                        "status": "stale",
                        "message": "Cache schema is outdated. Rebuild required.",
                        "rebuildRequired": True,
                    }
                if current_status in {"empty", "stale", "error"}:
                    self._mark_rebuild_required_locked(
                        "Cache is not ready. Rebuild required.",
                        refresh_duration_ms=_elapsed_ms(started_at),
                    )
                    return {
                        "ok": False,
                        "status": "stale",
                        "message": "Cache is not ready. Rebuild required.",
                        "rebuildRequired": True,
                    }
                if not self._daily and not self._deck_daily:
                    self._mark_rebuild_required_locked(
                        "Cache is empty. Rebuild required.",
                        refresh_duration_ms=_elapsed_ms(started_at),
                    )
                    return {
                        "ok": False,
                        "status": "stale",
                        "message": "Cache is empty. Rebuild required.",
                        "rebuildRequired": True,
                    }

            new_revlog_count = _revlog_count_after(col, last_cached)
            max_new_id = _max_revlog_id_after(col, last_cached)
            if max_new_id <= last_cached or new_revlog_count <= 0:
                with self._lock:
                    self._meta["status"] = "ready"
                    self._meta["error"] = None
                    self._meta["updated_at"] = int(time.time())
                    self._meta["profile_name"] = profile_name
                    self._meta["collection_scm"] = _collection_scm(col)
                    self._meta["last_refresh_duration_ms"] = _elapsed_ms(started_at)
                    self._meta["last_refresh_added_rows"] = 0
                    self._meta["last_error"] = None
                    self._building = False
                    self._write_meta_best_effort_locked()
                    return {
                        "ok": True,
                        "status": "ready",
                        "addedRows": 0,
                        **self._status_locked(),
                    }

            rollover_hours = _anki_rollover_hours(col)
            daily_rows = _daily_rows(col, rollover_hours, min_revlog_id=last_cached)
            deck_rows = _deck_daily_rows(col, rollover_hours, min_revlog_id=last_cached)

            with closing(self._connect()) as conn:
                self._init_schema(conn)
                with conn:
                    _upsert_daily_deltas(conn, daily_rows)
                    _upsert_deck_daily_deltas(conn, deck_rows)
                    meta = dict(self._meta)
                    meta.update(
                        {
                            "updated_at": int(time.time()),
                            "last_revlog_id": max_new_id,
                            "collection_scm": _collection_scm(col),
                            "profile_name": profile_name,
                            "status": "ready",
                            "error": None,
                            "last_refresh_duration_ms": _elapsed_ms(started_at),
                            "last_refresh_added_rows": new_revlog_count,
                            "last_error": None,
                        }
                    )
                    _write_meta(conn, meta)

            with self._lock:
                self._loaded = False
                self._load_from_disk_locked()
                self._building = False
                return {
                    "ok": True,
                    "status": "ready",
                    "addedRows": new_revlog_count,
                    **self._status_locked(),
                }
        except Exception as error:
            traceback.print_exc()
            self.mark_error(error, refresh_duration_ms=_elapsed_ms(started_at))
            return {"ok": False, "status": "error", "error": _short_error(error)}

    def _prepare_build(self, status: str) -> bool:
        with self._lock:
            self._load_from_disk_locked()
            if self._building or self._meta.get("status") in {"scheduled", "building"}:
                return False
            self._building = True
            self._meta["status"] = status
            self._meta["error"] = None
            self._meta["updated_at"] = int(time.time())
            self._write_meta_best_effort_locked()
            return True

    def _connect(self) -> sqlite3.Connection:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.cache_path), timeout=30)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("pragma journal_mode=wal")
            conn.execute("pragma synchronous=normal")
            return conn
        except Exception:
            conn.close()
            raise

    def _init_schema(self, conn: sqlite3.Connection, *, reset_outdated: bool = False) -> None:
        conn.execute(
            "create table if not exists cache_meta (key text primary key, value text not null)"
        )
        if reset_outdated:
            raw_version = conn.execute(
                "select value from cache_meta where key = 'version'"
            ).fetchone()
            try:
                stored_version = _as_int(json.loads(raw_version[0])) if raw_version else 0
            except Exception:
                stored_version = 0
            if stored_version not in {0, CACHE_SCHEMA_VERSION}:
                conn.execute("drop table if exists daily_aggregates")
                conn.execute("drop table if exists deck_daily_aggregates")
        conn.executescript(
            """
            create table if not exists cache_meta (
              key text primary key,
              value text not null
            );

            create table if not exists daily_aggregates (
              date text primary key,
              reviews integer not null default 0,
              new_cards integer not null default 0,
              learning integer not null default 0,
              review integer not null default 0,
              relearning integer not null default 0,
              cram integer not null default 0,
              again integer not null default 0,
              hard integer not null default 0,
              good integer not null default 0,
              easy integer not null default 0,
              pass_count integer not null default 0,
              fail_count integer not null default 0,
              retention_young_pass integer not null default 0,
              retention_young_fail integer not null default 0,
              retention_mature_pass integer not null default 0,
              retention_mature_fail integer not null default 0,
              answer_time_count integer not null default 0,
              study_seconds integer not null default 0,
              total_answer_seconds real not null default 0
            );

            create table if not exists deck_daily_aggregates (
              date text not null,
              deck_id integer not null,
              deck_name text not null,
              reviews integer not null default 0,
              new_cards integer not null default 0,
              learning integer not null default 0,
              review integer not null default 0,
              relearning integer not null default 0,
              cram integer not null default 0,
              again integer not null default 0,
              hard integer not null default 0,
              good integer not null default 0,
              easy integer not null default 0,
              pass_count integer not null default 0,
              fail_count integer not null default 0,
              retention_young_pass integer not null default 0,
              retention_young_fail integer not null default 0,
              retention_mature_pass integer not null default 0,
              retention_mature_fail integer not null default 0,
              answer_time_count integer not null default 0,
              study_seconds integer not null default 0,
              total_answer_seconds real not null default 0,
              primary key (date, deck_id)
            );

            create index if not exists idx_daily_aggregates_date
            on daily_aggregates(date);

            create index if not exists idx_deck_daily_aggregates_date
            on deck_daily_aggregates(date);

            create index if not exists idx_deck_daily_aggregates_deck_id
            on deck_daily_aggregates(deck_id);
            """
        )

    def _load_from_disk_locked(self) -> None:
        if self._loaded:
            return
        if not self.cache_path.exists():
            self._daily = {}
            self._deck_daily = {}
            self._meta = _empty_meta()
            self._loaded = True
            return
        try:
            with closing(self._connect()) as conn:
                self._init_schema(conn)
                meta = _read_meta(conn)
                daily = {
                    str(row["date"]): dict(row)
                    for row in conn.execute("select * from daily_aggregates order by date")
                }
                deck_daily = {
                    (str(row["date"]), int(row["deck_id"])): dict(row)
                    for row in conn.execute(
                        "select * from deck_daily_aggregates order by date, deck_id"
                    )
                }
            if _as_int(meta.get("version")) != CACHE_SCHEMA_VERSION:
                meta["status"] = "stale"
                meta["error"] = "Cache schema is outdated. Rebuild required."
            elif meta.get("status") in {"scheduled", "building"} and not self._building:
                meta["status"] = "stale"
                meta["error"] = "Previous cache operation was interrupted. Rebuild required."
            elif not daily and not deck_daily and meta.get("status") not in {"building", "scheduled"}:
                meta["status"] = "empty"
            self._daily = daily
            self._deck_daily = deck_daily
            self._meta = _clean_meta(meta)
        except Exception as error:
            print(f"Anki Study Report stats cache load failed: {_short_error(error)}")
            self._daily = {}
            self._deck_daily = {}
            self._meta = _empty_meta()
            self._meta["status"] = "error"
            self._meta["error"] = _short_error(error)
            self._meta["last_error"] = _short_error(error)
        self._loaded = True

    def _write_meta_best_effort_locked(self) -> None:
        try:
            with closing(self._connect()) as conn:
                self._init_schema(conn)
                with conn:
                    _write_meta(conn, self._meta)
        except Exception:
            traceback.print_exc()

    def _status_locked(self) -> dict[str, Any]:
        meta = _clean_meta(self._meta)
        status = str(meta.get("status") or "empty")
        if status not in CACHE_STATUSES:
            status = "error"
        return {
            "status": status,
            "version": _as_int(meta.get("version")),
            "createdAt": _as_int(meta.get("created_at")),
            "updatedAt": _as_int(meta.get("updated_at")),
            "lastRevlogId": _as_int(meta.get("last_revlog_id")),
            "collectionScm": meta.get("collection_scm"),
            "profileName": meta.get("profile_name"),
            "cachedDays": len(self._daily),
            "cachedDeckDays": len(self._deck_daily),
            "isBuilding": bool(self._building or status in {"scheduled", "building"}),
            "error": meta.get("error") if meta.get("error") else None,
            "lastError": meta.get("last_error") if meta.get("last_error") else None,
            "lastBuildDurationMs": _as_int(meta.get("last_build_duration_ms")),
            "lastRefreshDurationMs": _as_int(meta.get("last_refresh_duration_ms")),
            "lastRefreshAddedRows": _as_int(meta.get("last_refresh_added_rows")),
            "limitations": [DECK_HISTORY_NOTE],
            "cachePath": str(self.cache_path),
            "deckHistoryNote": DECK_HISTORY_NOTE,
        }

    def mark_error(
        self,
        message: str,
        build_duration_ms: int | None = None,
        refresh_duration_ms: int | None = None,
    ) -> None:
        with self._lock:
            short = _short_error(message)
            self._meta["status"] = "error"
            self._meta["error"] = short
            self._meta["last_error"] = short
            self._meta["updated_at"] = int(time.time())
            if build_duration_ms is not None:
                self._meta["last_build_duration_ms"] = _as_int(build_duration_ms)
            if refresh_duration_ms is not None:
                self._meta["last_refresh_duration_ms"] = _as_int(refresh_duration_ms)
            self._building = False
            self._write_meta_best_effort_locked()

    def _mark_rebuild_required_locked(
        self,
        message: str,
        refresh_duration_ms: int | None = None,
    ) -> None:
        self._meta["status"] = "stale"
        self._meta["error"] = _short_error(message)
        self._meta["updated_at"] = int(time.time())
        if refresh_duration_ms is not None:
            self._meta["last_refresh_duration_ms"] = _as_int(refresh_duration_ms)
            self._meta["last_refresh_added_rows"] = 0
        self._building = False
        self._write_meta_best_effort_locked()


def _daily_rows(
    col: Any,
    rollover_hours: int,
    min_revlog_id: int | None,
) -> list[dict[str, Any]]:
    where_incremental = ""
    first_retention_review = _first_retention_review_sql(rollover_hours)
    params: list[Any] = [rollover_hours * 3600, ANSWER_TIME_CAP_MS, ANSWER_TIME_CAP_MS]
    if min_revlog_id is not None:
        where_incremental = "and r.id > ?"
        params.append(min_revlog_id)
    rows = col.db.all(
        f"""
        select
            strftime('%Y-%m-%d', r.id / 1000 - ?, 'unixepoch', 'localtime') as day,
            count(*) as reviews,
            count(distinct case
                when r.type = 0
                  and not exists (
                      select 1
                      from revlog earlier
                      where earlier.cid = r.cid
                        and earlier.id < r.id
                        {REVLOG_REVIEW_FILTER_SQL.replace("r.", "earlier.")}
                      limit 1
                  )
                then r.cid
            end) as new_cards,
            coalesce(sum(case when r.type = 0 then 1 else 0 end), 0) as learning,
            coalesce(sum(case when r.type = 1 then 1 else 0 end), 0) as review,
            coalesce(sum(case when r.type = 2 then 1 else 0 end), 0) as relearning,
            coalesce(sum(case when r.type = 3 then 1 else 0 end), 0) as cram,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again,
            coalesce(sum(case when r.ease = 2 then 1 else 0 end), 0) as hard,
            coalesce(sum(case when r.ease = 3 then 1 else 0 end), 0) as good,
            coalesce(sum(case when r.ease = 4 then 1 else 0 end), 0) as easy,
            coalesce(sum(case when r.ease in (2, 3, 4) then 1 else 0 end), 0) as pass_count,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as fail_count,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl > 0 and r.lastIvl < 21
                and r.ease in (2, 3, 4) and {first_retention_review} then 1 else 0 end), 0)
                as retention_young_pass,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl > 0 and r.lastIvl < 21
                and r.ease = 1 and {first_retention_review} then 1 else 0 end), 0)
                as retention_young_fail,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl >= 21
                and r.ease in (2, 3, 4) and {first_retention_review} then 1 else 0 end), 0)
                as retention_mature_pass,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl >= 21
                and r.ease = 1 and {first_retention_review} then 1 else 0 end), 0)
                as retention_mature_fail,
            coalesce(sum(case when r.time is not null and r.time >= 0 then 1 else 0 end), 0)
                as answer_time_count,
            coalesce(sum(
                case
                    when r.time is null or r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms
        from revlog r
        left join cards c on c.id = r.cid
        where 1 = 1
          {REVLOG_REVIEW_FILTER_SQL}
          {where_incremental}
        group by day
        order by day
        """,
        *params,
    )
    return [_clean_daily_row(row) for row in rows if _valid_date_key(row[0])]


def _deck_daily_rows(
    col: Any,
    rollover_hours: int,
    min_revlog_id: int | None,
) -> list[dict[str, Any]]:
    where_incremental = ""
    first_retention_review = _first_retention_review_sql(rollover_hours)
    params: list[Any] = [rollover_hours * 3600, ANSWER_TIME_CAP_MS, ANSWER_TIME_CAP_MS]
    if min_revlog_id is not None:
        where_incremental = "and r.id > ?"
        params.append(min_revlog_id)
    rows = col.db.all(
        f"""
        select
            strftime('%Y-%m-%d', r.id / 1000 - ?, 'unixepoch', 'localtime') as day,
            coalesce(case when c.odid > 0 then c.odid else c.did end, 0) as deck_id,
            count(*) as reviews,
            count(distinct case
                when r.type = 0
                  and not exists (
                      select 1
                      from revlog earlier
                      where earlier.cid = r.cid
                        and earlier.id < r.id
                        {REVLOG_REVIEW_FILTER_SQL.replace("r.", "earlier.")}
                      limit 1
                  )
                then r.cid
            end) as new_cards,
            coalesce(sum(case when r.type = 0 then 1 else 0 end), 0) as learning,
            coalesce(sum(case when r.type = 1 then 1 else 0 end), 0) as review,
            coalesce(sum(case when r.type = 2 then 1 else 0 end), 0) as relearning,
            coalesce(sum(case when r.type = 3 then 1 else 0 end), 0) as cram,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again,
            coalesce(sum(case when r.ease = 2 then 1 else 0 end), 0) as hard,
            coalesce(sum(case when r.ease = 3 then 1 else 0 end), 0) as good,
            coalesce(sum(case when r.ease = 4 then 1 else 0 end), 0) as easy,
            coalesce(sum(case when r.ease in (2, 3, 4) then 1 else 0 end), 0) as pass_count,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as fail_count,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl > 0 and r.lastIvl < 21
                and r.ease in (2, 3, 4) and {first_retention_review} then 1 else 0 end), 0)
                as retention_young_pass,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl > 0 and r.lastIvl < 21
                and r.ease = 1 and {first_retention_review} then 1 else 0 end), 0)
                as retention_young_fail,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl >= 21
                and r.ease in (2, 3, 4) and {first_retention_review} then 1 else 0 end), 0)
                as retention_mature_pass,
            coalesce(sum(case when r.type in (1, 2) and r.lastIvl >= 21
                and r.ease = 1 and {first_retention_review} then 1 else 0 end), 0)
                as retention_mature_fail,
            coalesce(sum(case when r.time is not null and r.time >= 0 then 1 else 0 end), 0)
                as answer_time_count,
            coalesce(sum(
                case
                    when r.time is null or r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms
        from revlog r
        left join cards c on c.id = r.cid
        where 1 = 1
          {REVLOG_REVIEW_FILTER_SQL}
          {where_incremental}
        group by day, deck_id
        order by day, deck_id
        """,
        *params,
    )
    names = _deck_names_by_id(col)
    return [
        _clean_deck_daily_row(row, names)
        for row in rows
        if _valid_date_key(row[0])
    ]


def _insert_daily_rows(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> None:
    placeholders = ", ".join("?" for _ in DAILY_COLUMNS)
    conn.executemany(
        f"insert into daily_aggregates ({', '.join(DAILY_COLUMNS)}) values ({placeholders})",
        ([row[column] for column in DAILY_COLUMNS] for row in rows),
    )


def _insert_deck_daily_rows(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> None:
    placeholders = ", ".join("?" for _ in DECK_DAILY_COLUMNS)
    conn.executemany(
        f"insert into deck_daily_aggregates ({', '.join(DECK_DAILY_COLUMNS)}) values ({placeholders})",
        ([row[column] for column in DECK_DAILY_COLUMNS] for row in rows),
    )


def _upsert_daily_deltas(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> None:
    if not rows:
        return
    update_columns = [column for column in DAILY_COLUMNS if column != "date"]
    assignments = ", ".join(
        f"{column} = {column} + excluded.{column}" for column in update_columns
    )
    placeholders = ", ".join("?" for _ in DAILY_COLUMNS)
    conn.executemany(
        f"""
        insert into daily_aggregates ({', '.join(DAILY_COLUMNS)}) values ({placeholders})
        on conflict(date) do update set {assignments}
        """,
        ([row[column] for column in DAILY_COLUMNS] for row in rows),
    )


def _upsert_deck_daily_deltas(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> None:
    if not rows:
        return
    update_columns = [
        column for column in DECK_DAILY_COLUMNS if column not in {"date", "deck_id", "deck_name"}
    ]
    assignments = ", ".join(
        [f"{column} = {column} + excluded.{column}" for column in update_columns]
        + ["deck_name = excluded.deck_name"]
    )
    placeholders = ", ".join("?" for _ in DECK_DAILY_COLUMNS)
    conn.executemany(
        f"""
        insert into deck_daily_aggregates ({', '.join(DECK_DAILY_COLUMNS)}) values ({placeholders})
        on conflict(date, deck_id) do update set {assignments}
        """,
        ([row[column] for column in DECK_DAILY_COLUMNS] for row in rows),
    )


def _read_meta(conn: sqlite3.Connection) -> dict[str, Any]:
    meta = _empty_meta()
    try:
        rows = conn.execute("select key, value from cache_meta").fetchall()
    except sqlite3.DatabaseError:
        return meta
    for key, raw_value in rows:
        try:
            meta[str(key)] = json.loads(str(raw_value))
        except Exception:
            meta[str(key)] = raw_value
    return _clean_meta(meta)


def _write_meta(conn: sqlite3.Connection, meta: dict[str, Any]) -> None:
    clean = _clean_meta(meta)
    conn.executemany(
        """
        insert into cache_meta(key, value) values (?, ?)
        on conflict(key) do update set value = excluded.value
        """,
        [(key, json.dumps(value, ensure_ascii=False)) for key, value in clean.items()],
    )


def _clean_daily_row(row: Any) -> dict[str, Any]:
    total_ms = _as_int(row[18])
    total_seconds = round(total_ms / 1000)
    return {
        "date": str(row[0]),
        "reviews": _as_int(row[1]),
        "new_cards": _as_int(row[2]),
        "learning": _as_int(row[3]),
        "review": _as_int(row[4]),
        "relearning": _as_int(row[5]),
        "cram": _as_int(row[6]),
        "again": _as_int(row[7]),
        "hard": _as_int(row[8]),
        "good": _as_int(row[9]),
        "easy": _as_int(row[10]),
        "pass_count": _as_int(row[11]),
        "fail_count": _as_int(row[12]),
        "retention_young_pass": _as_int(row[13]),
        "retention_young_fail": _as_int(row[14]),
        "retention_mature_pass": _as_int(row[15]),
        "retention_mature_fail": _as_int(row[16]),
        "answer_time_count": _as_int(row[17]),
        "study_seconds": total_seconds,
        "total_answer_seconds": round(total_ms / 1000, 3),
    }


def _clean_deck_daily_row(row: Any, names: dict[int, str]) -> dict[str, Any]:
    deck_id = _as_int(row[1])
    total_ms = _as_int(row[19])
    total_seconds = round(total_ms / 1000)
    return {
        "date": str(row[0]),
        "deck_id": deck_id,
        "deck_name": _deck_name(deck_id, names),
        "reviews": _as_int(row[2]),
        "new_cards": _as_int(row[3]),
        "learning": _as_int(row[4]),
        "review": _as_int(row[5]),
        "relearning": _as_int(row[6]),
        "cram": _as_int(row[7]),
        "again": _as_int(row[8]),
        "hard": _as_int(row[9]),
        "good": _as_int(row[10]),
        "easy": _as_int(row[11]),
        "pass_count": _as_int(row[12]),
        "fail_count": _as_int(row[13]),
        "retention_young_pass": _as_int(row[14]),
        "retention_young_fail": _as_int(row[15]),
        "retention_mature_pass": _as_int(row[16]),
        "retention_mature_fail": _as_int(row[17]),
        "answer_time_count": _as_int(row[18]),
        "study_seconds": total_seconds,
        "total_answer_seconds": round(total_ms / 1000, 3),
    }


def _empty_meta() -> dict[str, Any]:
    return {
        "version": CACHE_SCHEMA_VERSION,
        "created_at": 0,
        "updated_at": 0,
        "last_revlog_id": 0,
        "collection_scm": None,
        "profile_name": None,
        "status": "empty",
        "error": None,
        "last_build_duration_ms": 0,
        "last_refresh_duration_ms": 0,
        "last_refresh_added_rows": 0,
        "last_error": None,
    }


def _clean_meta(meta: dict[str, Any]) -> dict[str, Any]:
    clean = _empty_meta()
    clean.update(meta)
    clean["version"] = _as_int(clean.get("version"))
    clean["created_at"] = _as_int(clean.get("created_at"))
    clean["updated_at"] = _as_int(clean.get("updated_at"))
    clean["last_revlog_id"] = _as_int(clean.get("last_revlog_id"))
    if clean.get("collection_scm") is not None:
        clean["collection_scm"] = _as_int(clean.get("collection_scm"))
    if clean.get("profile_name") is not None:
        clean["profile_name"] = str(clean.get("profile_name"))
    clean["status"] = str(clean.get("status") or "empty")
    if clean["status"] not in CACHE_STATUSES:
        clean["status"] = "error"
    if clean.get("error"):
        clean["error"] = _short_error(clean.get("error"))
    else:
        clean["error"] = None
    clean["last_build_duration_ms"] = _as_int(clean.get("last_build_duration_ms"))
    clean["last_refresh_duration_ms"] = _as_int(clean.get("last_refresh_duration_ms"))
    clean["last_refresh_added_rows"] = _as_int(clean.get("last_refresh_added_rows"))
    if clean.get("last_error"):
        clean["last_error"] = _short_error(clean.get("last_error"))
    else:
        clean["last_error"] = None
    return clean


def _last_revlog_id(col: Any) -> int:
    return _as_int(col.db.scalar("select coalesce(max(id), 0) from revlog"))


def _max_revlog_id_after(col: Any, last_revlog_id: int) -> int:
    return _as_int(
        col.db.scalar(
            "select coalesce(max(id), 0) from revlog where id > ?",
            _as_int(last_revlog_id),
        )
    )


def _revlog_count_after(col: Any, last_revlog_id: int) -> int:
    return _as_int(
        col.db.scalar(
            "select count(*) from revlog where id > ?",
            _as_int(last_revlog_id),
        )
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.monotonic() - started_at) * 1000)))


def _collection_scm(col: Any) -> int | None:
    try:
        value = getattr(col, "scm")
        if value is not None:
            return _as_int(value)
    except Exception:
        pass
    try:
        return _as_int(col.db.scalar("select scm from col limit 1"))
    except Exception:
        return None


def _anki_rollover_hours(col: Any) -> int:
    rollover_hours = 4
    try:
        rollover_hours = int(col.conf.get("rollover", rollover_hours))
    except Exception:
        try:
            rollover_hours = int(datetime.fromtimestamp(col.crt).hour)
        except Exception:
            pass
    return max(0, min(23, rollover_hours))


def _deck_names_by_id(col: Any) -> dict[int, str]:
    try:
        return {
            _as_int(deck.id): str(deck.name)
            for deck in col.decks.all_names_and_ids()
        }
    except Exception:
        pass

    try:
        decks = col.decks.all()
    except Exception:
        return {}

    names: dict[int, str] = {}
    for deck in decks:
        try:
            names[_as_int(deck["id"])] = str(deck["name"])
        except Exception:
            continue
    return names


def _deck_name(deck_id: int, names: dict[int, str]) -> str:
    if deck_id <= 0:
        return "Deleted cards"
    return names.get(deck_id, f"Deck {deck_id}")


def _valid_date_key(value: Any) -> bool:
    return isinstance(value, str) and bool(DATE_KEY_RE.match(value))


def _first_retention_review_sql(rollover_hours: int) -> str:
    """SQL predicate for Anki-style first qualifying review per card/local day."""

    rollover_seconds = max(0, min(23, _as_int(rollover_hours))) * 3600
    earlier_filter = REVLOG_REVIEW_FILTER_SQL.replace("r.", "earlier.")
    return f"""
        not exists (
            select 1 from revlog earlier
            where earlier.cid = r.cid
              and earlier.id < r.id
              and earlier.type in (1, 2)
              and earlier.lastIvl > 0
              {earlier_filter}
              and strftime('%Y-%m-%d', earlier.id / 1000 - {rollover_seconds},
                    'unixepoch', 'localtime') =
                  strftime('%Y-%m-%d', r.id / 1000 - {rollover_seconds},
                    'unixepoch', 'localtime')
            limit 1
        )
    """


def _short_error(error: Any) -> str:
    message = str(error or "Unknown cache error.").strip().splitlines()[0]
    if not message:
        message = "Unknown cache error."
    return message[:240]


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
