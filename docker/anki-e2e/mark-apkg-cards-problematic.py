#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from typing import Any

DAY_MS = 86_400_000
ACTION_RECHECK_ANCHOR = "cards-action-recheck"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply generic study-state scenarios to imported real cards.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()

    collection_path = args.profile_dir / "collection.anki2"
    scheduler_day_start_ms, scheduler_day_cutoff_ms = scheduler_day_window(collection_path)
    utc_day_start_ms = (int(time.time() * 1000) // DAY_MS) * DAY_MS

    command = [
        sys.executable,
        "/e2e/bin/apply-real-deck-scenarios.py",
        "--profile-dir",
        str(args.profile_dir),
        "--artifacts-dir",
        str(args.artifacts_dir),
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        return result.returncode

    report_path = args.artifacts_dir / "scenario-application-report.json"
    shifted = shift_generated_revlog_ids(
        collection_path,
        report_path,
        utc_day_start_ms=utc_day_start_ms,
        scheduler_day_start_ms=scheduler_day_start_ms,
        scheduler_day_cutoff_ms=scheduler_day_cutoff_ms,
    )
    print(
        f"[real-decks] scheduler-day normalization PASS: shifted={shifted} "
        f"start={scheduler_day_start_ms} cutoff={scheduler_day_cutoff_ms}",
        flush=True,
    )
    return 0


def scheduler_day_window(collection_path: Path) -> tuple[int, int]:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        cutoff_ms = int(col.sched.day_cutoff) * 1000
    finally:
        close = getattr(col, "close", None)
        if callable(close):
            try:
                close(save=True)
            except TypeError:
                close()
    start_ms = cutoff_ms - DAY_MS
    now_ms = int(time.time() * 1000)
    if not start_ms <= now_ms < cutoff_ms:
        raise RuntimeError(
            "Anki scheduler day window does not contain the current time: "
            f"start={start_ms}, now={now_ms}, cutoff={cutoff_ms}"
        )
    return start_ms, cutoff_ms


def shift_generated_revlog_ids(
    collection_path: Path,
    report_path: Path,
    *,
    utc_day_start_ms: int,
    scheduler_day_start_ms: int,
    scheduler_day_cutoff_ms: int,
) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise RuntimeError("Scenario report is not PASS before scheduler-day normalization.")
    if int((report.get("before") or {}).get("revlog") or 0) != 0:
        raise RuntimeError("Real-deck packages unexpectedly contained scheduling data before scenario preparation.")

    offset_ms = scheduler_day_start_ms - utc_day_start_ms
    connection = sqlite3.connect(collection_path)
    try:
        old_ids = [int(row[0]) for row in connection.execute("select id from revlog order by id")]
        mapping = {value: value + offset_ms for value in old_ids}
        action_old_ids = _scenario_revlog_ids(report, ACTION_RECHECK_ANCHOR)
        action_recent_ids = _recent_unique_ids(
            count=len(action_old_ids),
            reserved={value for key, value in mapping.items() if key not in action_old_ids},
            scheduler_day_start_ms=scheduler_day_start_ms,
            scheduler_day_cutoff_ms=scheduler_day_cutoff_ms,
            now_ms=int(time.time() * 1000),
        )
        for old_id, recent_id in zip(action_old_ids, action_recent_ids, strict=True):
            mapping[old_id] = recent_id

        new_ids = [mapping[value] for value in old_ids]
        if len(new_ids) != len(set(new_ids)) or any(value <= 0 for value in new_ids):
            raise RuntimeError("Scheduler-day revlog normalization would create invalid or duplicate IDs.")

        for index, old_id in enumerate(old_ids, start=1):
            connection.execute("update revlog set id = ? where id = ?", (-index, old_id))
        for index, new_id in enumerate(new_ids, start=1):
            connection.execute("update revlog set id = ? where id = ?", (new_id, -index))
        connection.commit()
    finally:
        connection.close()

    _rewrite_revlog_ids(report, mapping)
    report["schedulerDay"] = {
        "sourceUtcDayStartMs": utc_day_start_ms,
        "startMs": scheduler_day_start_ms,
        "cutoffMs": scheduler_day_cutoff_ms,
        "offsetMs": offset_ms,
        "revlogRowsShifted": len(old_ids),
        "actionRecheckAnchor": ACTION_RECHECK_ANCHOR,
        "actionRecheckRevlogRows": len(action_recent_ids),
        "actionRecheckLastReviewedMs": max(action_recent_ids),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(old_ids)


def _scenario_revlog_ids(report: dict[str, Any], anchor_id: str) -> list[int]:
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list):
        raise RuntimeError("Scenario report has no scenario list.")
    scenario = next(
        (
            item
            for item in scenarios
            if isinstance(item, dict) and str(item.get("id") or item.get("anchorId") or "") == anchor_id
        ),
        None,
    )
    if not isinstance(scenario, dict):
        raise RuntimeError(f"Scenario report is missing required anchor: {anchor_id}")
    values = scenario.get("revlogIds")
    if not isinstance(values, list) or not values:
        raise RuntimeError(f"Scenario {anchor_id} has no generated revlog IDs.")
    ids = [int(value) for value in values]
    if len(ids) != len(set(ids)) or any(value <= 0 for value in ids):
        raise RuntimeError(f"Scenario {anchor_id} has invalid generated revlog IDs.")
    return ids


def _recent_unique_ids(
    *,
    count: int,
    reserved: set[int],
    scheduler_day_start_ms: int,
    scheduler_day_cutoff_ms: int,
    now_ms: int,
) -> list[int]:
    if count <= 0:
        raise RuntimeError("Action/recheck scenario must contain generated revlog rows.")
    latest = min(now_ms - 1, scheduler_day_cutoff_ms - 1)
    if latest <= 0:
        raise RuntimeError("Cannot place action/recheck history before the scheduler cutoff.")
    while True:
        values = list(range(latest - count + 1, latest + 1))
        if values[0] > 0 and not (set(values) & reserved):
            break
        latest -= count
    if values[-1] < scheduler_day_start_ms - DAY_MS:
        raise RuntimeError("Cannot place action/recheck history in the recent scheduler window.")
    return values


def _rewrite_revlog_ids(value: Any, mapping: dict[int, int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "revlogIds" and isinstance(item, list):
                value[key] = [mapping.get(int(entry), int(entry)) for entry in item]
            else:
                _rewrite_revlog_ids(item, mapping)
    elif isinstance(value, list):
        for item in value:
            _rewrite_revlog_ids(item, mapping)


if __name__ == "__main__":
    raise SystemExit(main())
