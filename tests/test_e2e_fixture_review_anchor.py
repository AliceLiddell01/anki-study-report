from __future__ import annotations

from datetime import date, datetime
import importlib.util
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_apkg_marker():
    path = ROOT / "docker" / "anki-e2e" / "mark-apkg-cards-problematic.py"
    spec = importlib.util.spec_from_file_location("asr_apkg_marker_review_anchor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_collection_db(path: Path, existing_revlog_id: int) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            create table notes(id integer primary key, mid integer not null, tags text not null);
            create table cards(
                id integer primary key,
                nid integer not null,
                did integer not null,
                reps integer not null default 0,
                lapses integer not null default 0,
                type integer not null default 0,
                queue integer not null default 0,
                due integer not null default 0,
                factor integer not null default 0,
                ivl integer not null default 0
            );
            create table revlog(
                id integer primary key,
                cid integer not null,
                usn integer not null,
                ease integer not null,
                ivl integer not null,
                lastIvl integer not null,
                factor integer not null,
                time integer not null,
                type integer not null
            );
            insert into notes(id, mid, tags) values (10, 20, '');
            insert into cards(id, nid, did) values (30, 10, 40);
            """
        )
        connection.execute(
            "insert into revlog values (?, 30, -1, 3, 1, 1, 2500, 1000, 1)",
            (existing_revlog_id,),
        )
        connection.commit()
    finally:
        connection.close()


def test_apkg_reviews_use_scheduler_day_when_wall_clock_is_next_date(tmp_path: Path, monkeypatch) -> None:
    marker = load_apkg_marker()
    scheduler_day_cutoff = datetime(2026, 7, 13, 4, 0)
    scheduler_day_cutoff_ms = int(scheduler_day_cutoff.timestamp() * 1000)
    review_anchor_ms = scheduler_day_cutoff_ms - 12 * 60 * 60 * 1000
    scheduler_today = date.fromtimestamp(scheduler_day_cutoff.timestamp() - 86_400).isoformat()
    wall_clock = datetime(2026, 7, 13, 1, 0)
    assert wall_clock.date().isoformat() > scheduler_today

    collection_path = tmp_path / "collection.anki2"
    create_collection_db(collection_path, review_anchor_ms - 2 * 60 * 60 * 1000)
    monkeypatch.setattr(marker.time, "time", wall_clock.timestamp)
    monkeypatch.setattr(marker, "model_names_by_path", lambda _path: {20: "APKG fixture"})

    result = marker.mark_cards(
        collection_path,
        [30],
        review_anchor_ms=review_anchor_ms,
        scheduler_day_cutoff_ms=scheduler_day_cutoff_ms,
    )

    connection = sqlite3.connect(collection_path)
    try:
        review_ids = [
            int(row[0])
            for row in connection.execute("select id from revlog where id > ? order by id", (review_anchor_ms - 2 * 60 * 60 * 1000,))
        ]
    finally:
        connection.close()

    assert result["revlogRowsAdded"] == 5
    assert len(review_ids) == 5
    assert review_ids == sorted(set(review_ids))
    assert all(scheduler_day_cutoff_ms - 86_400_000 <= review_id < scheduler_day_cutoff_ms for review_id in review_ids)
    assert {date.fromtimestamp(review_id / 1000).isoformat() for review_id in review_ids} == {scheduler_today}
    assert max(review_ids) < int(wall_clock.timestamp() * 1000)
