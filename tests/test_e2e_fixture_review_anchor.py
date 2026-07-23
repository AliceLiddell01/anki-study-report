from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_scenario_wrapper():
    path = ROOT / "docker" / "anki-e2e" / "mark-apkg-cards-problematic.py"
    spec = importlib.util.spec_from_file_location("asr_real_deck_scheduler_day", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_collection_db(path: Path, revlog_ids: list[int]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
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
            )
            """
        )
        for index, revlog_id in enumerate(revlog_ids, start=1):
            connection.execute(
                "insert into revlog values (?, ?, -1, 3, 1, 1, 2500, 1000, 1)",
                (revlog_id, index),
            )
        connection.commit()
    finally:
        connection.close()


def test_real_deck_reviews_are_shifted_into_anki_scheduler_days(tmp_path: Path) -> None:
    wrapper = load_scenario_wrapper()
    utc_day_start = int(datetime(2026, 7, 13, tzinfo=timezone.utc).timestamp() * 1000)
    scheduler_cutoff = int(datetime(2026, 7, 13, 4, tzinfo=timezone.utc).timestamp() * 1000)
    scheduler_start = scheduler_cutoff - wrapper.DAY_MS
    original = [utc_day_start + 2 * 60 * 60 * 1000, utc_day_start - wrapper.DAY_MS + 2 * 60 * 60 * 1000]

    collection_path = tmp_path / "collection.anki2"
    create_collection_db(collection_path, original)
    report_path = tmp_path / "scenario-application-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "before": {"revlog": 0},
                "after": {"revlog": 2},
                "scenarios": [{"id": "cards-action-recheck", "revlogIds": original}],
            }
        ),
        encoding="utf-8",
    )

    shifted_count = wrapper.shift_generated_revlog_ids(
        collection_path,
        report_path,
        utc_day_start_ms=utc_day_start,
        scheduler_day_start_ms=scheduler_start,
        scheduler_day_cutoff_ms=scheduler_cutoff,
    )

    connection = sqlite3.connect(collection_path)
    try:
        shifted = [int(row[0]) for row in connection.execute("select id from revlog order by id")]
    finally:
        connection.close()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert shifted_count == 2
    expected = [value + scheduler_start - utc_day_start for value in original]
    assert shifted == sorted(expected)
    assert scheduler_start <= shifted[-1] < scheduler_cutoff
    assert scheduler_start - wrapper.DAY_MS <= shifted[0] < scheduler_start
    assert report["scenarios"][0]["revlogIds"] == expected
    assert report["schedulerDay"]["revlogRowsShifted"] == 2
