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


def create_collection_db(path: Path, rows: list[tuple[int, int]]) -> None:
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
        for revlog_id, card_id in rows:
            connection.execute(
                "insert into revlog values (?, ?, -1, 3, 1, 1, 2500, 1000, 1)",
                (revlog_id, card_id),
            )
        connection.commit()
    finally:
        connection.close()


def test_real_deck_reviews_are_shifted_and_action_anchor_stays_recent(tmp_path: Path, monkeypatch) -> None:
    wrapper = load_scenario_wrapper()
    utc_day_start = int(datetime(2026, 7, 13, tzinfo=timezone.utc).timestamp() * 1000)
    scheduler_cutoff = int(datetime(2026, 7, 14, 4, tzinfo=timezone.utc).timestamp() * 1000)
    scheduler_start = scheduler_cutoff - wrapper.DAY_MS
    now_ms = scheduler_start + 12 * 60 * 60 * 1000
    monkeypatch.setattr(wrapper.time, "time", lambda: now_ms / 1000)

    action_original = [
        utc_day_start - 33 * wrapper.DAY_MS + 1000,
        utc_day_start - 33 * wrapper.DAY_MS + 2000,
    ]
    ordinary_original = [utc_day_start - wrapper.DAY_MS + 3000]
    collection_path = tmp_path / "collection.anki2"
    create_collection_db(
        collection_path,
        [(value, 10) for value in action_original] + [(value, 20) for value in ordinary_original],
    )
    report_path = tmp_path / "scenario-application-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "before": {"revlog": 0},
                "after": {"revlog": 3},
                "scenarios": [
                    {"id": "cards-action-recheck", "revlogIds": action_original},
                    {"id": "words-preview", "revlogIds": ordinary_original},
                ],
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
        rows = connection.execute("select id, cid from revlog order by id").fetchall()
    finally:
        connection.close()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    action = next(item for item in report["scenarios"] if item["id"] == "cards-action-recheck")
    ordinary = next(item for item in report["scenarios"] if item["id"] == "words-preview")
    action_ids = sorted(int(row[0]) for row in rows if int(row[1]) == 10)
    ordinary_ids = sorted(int(row[0]) for row in rows if int(row[1]) == 20)
    expected_ordinary = [value + scheduler_start - utc_day_start for value in ordinary_original]

    assert shifted_count == 3
    assert action_ids == [now_ms - 2, now_ms - 1]
    assert ordinary_ids == expected_ordinary
    assert action["revlogIds"] == action_ids
    assert ordinary["revlogIds"] == expected_ordinary
    assert len({int(row[0]) for row in rows}) == 3
    assert scheduler_start <= action_ids[0] < scheduler_cutoff
    assert report["schedulerDay"]["revlogRowsShifted"] == 3
    assert report["schedulerDay"]["actionRecheckAnchor"] == "cards-action-recheck"
    assert report["schedulerDay"]["actionRecheckRevlogRows"] == 2
    assert report["schedulerDay"]["actionRecheckLastReviewedMs"] == now_ms - 1
