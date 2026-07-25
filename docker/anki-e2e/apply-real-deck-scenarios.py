#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
import traceback
from typing import Any, Iterable

from real_deck_contract import RealDeckContractError, select_distinct_cards, write_json

DAY_MS = 86_400_000


def log(message: str) -> None:
    print(f"[real-decks] {message}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply deterministic E2E study state to imported real cards.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()
    args.artifacts_dir.mkdir(parents=True, exist_ok=True)

    last_completed_step = "start"
    current_subject = ""
    try:
        log("applying scenarios")
        collection_path = args.profile_dir / "collection.anki2"
        if not collection_path.is_file():
            raise RealDeckContractError(f"Collection is missing: {collection_path}", stage="scenario")
        import_report = read_object(args.artifacts_dir / "real-deck-import-report.json")
        anchor_report = read_object(args.artifacts_dir / "anchor-resolution-report.json")
        package_order = [str(item) for item in import_report.get("packageOrder") or []]
        package_cards = {
            str(item["id"]): [int(value) for value in item.get("cardIds") or []]
            for item in import_report.get("packages") or []
            if isinstance(item, dict) and item.get("id")
        }
        imported_cards = {
            card_id
            for package_id in package_order
            for card_id in package_cards.get(package_id, [])
        }
        if not imported_cards:
            raise RealDeckContractError("No imported cards are available for scenarios.", stage="scenario")
        anchors = anchor_report.get("anchors")
        if not isinstance(anchors, dict):
            raise RealDeckContractError("Anchor report is invalid.", stage="scenario")

        conn = sqlite3.connect(collection_path)
        conn.row_factory = sqlite3.Row
        try:
            before = collection_counts(conn)
            verify_cards_exist(conn, imported_cards)
            now_ms = int(time.time() * 1000)
            day_start_ms = (now_ms // DAY_MS) * DAY_MS
            next_revlog_id = max(
                day_start_ms - 180 * DAY_MS,
                int(conn.execute("select coalesce(max(id), 0) + 1000 from revlog").fetchone()[0] or 1),
            )
            results: list[dict[str, Any]] = []

            plans = {
                "words-preview": {
                    "mutations": {"scheduling", "revlog"}, "queue": 2, "type": 2, "ivl": 5,
                    "factor": 2000, "reviews": [1, 3, 2, 3], "lapses": 1,
                },
                "grammar-preview": {
                    "mutations": {"scheduling", "revlog"}, "queue": 2, "type": 2, "ivl": 3,
                    "factor": 1950, "reviews": [1, 1, 3, 2], "lapses": 2,
                },
                "java-preview": {
                    "mutations": {"scheduling", "revlog"}, "queue": 2, "type": 2, "ivl": 7,
                    "factor": 2150, "reviews": [1, 3, 2, 3], "lapses": 1,
                },
                "cards-action-recheck": {
                    "mutations": {"scheduling", "revlog"},
                    "queue": 2,
                    "type": 2,
                    "ivl": 4,
                    "factor": 1800,
                    "reviews": [1, 1, 3, 1, 2, 3],
                    "lapses": 3,
                },
                "cards-low-success": {
                    "mutations": {"scheduling", "revlog"},
                    "queue": 2,
                    "type": 2,
                    "ivl": 2,
                    "factor": 1700,
                    "reviews": [1, 1, 1, 3, 1, 1, 2, 1, 3, 1],
                    "lapses": 7,
                },
                "cards-suspended": {
                    "mutations": {"scheduling", "suspended"},
                    "queue": -1,
                    "type": 2,
                    "ivl": 12,
                    "factor": 2100,
                    "reviews": [],
                    "lapses": 1,
                },
                "cards-buried": {
                    "mutations": {"scheduling", "buried"},
                    "queue": -2,
                    "type": 2,
                    "ivl": 7,
                    "factor": 2050,
                    "reviews": [],
                    "lapses": 1,
                },
                "inspection-japanese": {
                    "mutations": {"scheduling", "revlog"},
                    "queue": 2,
                    "type": 2,
                    "ivl": 6,
                    "factor": 2000,
                    "reviews": [1, 3, 2, 3],
                    "lapses": 1,
                },
                "inspection-programming": {
                    "mutations": {"scheduling", "revlog"},
                    "queue": 2,
                    "type": 2,
                    "ivl": 8,
                    "factor": 2200,
                    "reviews": [3, 2, 3, 4],
                    "lapses": 0,
                },
            }
            scenario_card_ids: set[int] = set()
            for offset, (anchor_id, plan) in enumerate(plans.items()):
                current_subject = anchor_id
                anchor = anchors.get(anchor_id)
                if not isinstance(anchor, dict):
                    raise RealDeckContractError(
                        f"Required scenario anchor is missing: {anchor_id}", stage="scenario", subject_id=anchor_id
                    )
                card_id = int(anchor.get("cardId") or 0)
                if card_id not in imported_cards:
                    raise RealDeckContractError(
                        f"Scenario anchor {anchor_id} targets a non-imported card.", stage="scenario", subject_id=anchor_id
                    )
                allowed = {str(item) for item in anchor.get("allowedScenarioMutations") or []}
                required = set(plan["mutations"])
                if not required.issubset(allowed):
                    raise RealDeckContractError(
                        f"Scenario {anchor_id} requires undeclared mutations: {sorted(required - allowed)}",
                        stage="scenario",
                        subject_id=anchor_id,
                    )
                before_state = card_state(conn, card_id)
                next_revlog_id, revlog_ids = apply_card_plan(
                    conn,
                    card_id,
                    plan,
                    next_revlog_id=next_revlog_id,
                    first_review_ms=day_start_ms - (30 + offset) * DAY_MS + 3_600_000,
                )
                results.append(
                    {
                        "id": anchor_id,
                        "anchorId": anchor_id,
                        "cardId": card_id,
                        "noteId": int(anchor.get("noteId") or 0),
                        "allowedMutations": sorted(allowed),
                        "appliedMutations": sorted(required),
                        "before": before_state,
                        "after": card_state(conn, card_id),
                        "revlogIds": revlog_ids,
                    }
                )
                scenario_card_ids.add(card_id)

            current_subject = "study-history"
            history_candidates = [
                card_id
                for package_id in package_order
                for card_id in package_cards.get(package_id, [])
                if card_id not in scenario_card_ids
            ]
            history_target = min(180, len(history_candidates))
            history_cards = history_candidates[:history_target]
            history_revlog_ids: list[int] = []
            for index, card_id in enumerate(history_cards):
                ease = 1 if index % 7 == 0 else 2 if index % 5 == 0 else 3 if index % 3 else 4
                review_ms = day_start_ms - (index % 120) * DAY_MS + 7_200_000 + (index // 120) * 1000
                plan = {
                    "queue": 2,
                    "type": 2,
                    "ivl": 1 + (index % 45),
                    "factor": 1900 + (index % 5) * 100,
                    "reviews": [ease],
                    "lapses": 1 if ease == 1 else 0,
                }
                next_revlog_id, revlog_ids = apply_card_plan(
                    conn,
                    card_id,
                    plan,
                    next_revlog_id=next_revlog_id,
                    first_review_ms=review_ms,
                )
                history_revlog_ids.extend(revlog_ids)

            perf100_enabled = os.environ.get("ANKI_E2E_PERF100") == "1"
            perf100_cards: list[int] = []
            if perf100_enabled:
                current_subject = "perf100"
                perf100_cards = select_distinct_cards(package_cards, package_order, 100)
                for index, card_id in enumerate(perf100_cards):
                    plan = {
                        "queue": 2,
                        "type": 2,
                        "ivl": 1 + (index % 20),
                        "factor": 1800 + (index % 4) * 100,
                        "reviews": [1, 3] if index % 4 == 0 else [2, 3],
                        "lapses": 1 if index % 4 == 0 else 0,
                    }
                    next_revlog_id, _ = apply_card_plan(
                        conn,
                        card_id,
                        plan,
                        next_revlog_id=next_revlog_id,
                        first_review_ms=day_start_ms - (index % 45) * DAY_MS + 10_800_000,
                    )

            conn.commit()
            after = collection_counts(conn)
            if after["notes"] != before["notes"] or after["cards"] != before["cards"]:
                raise RealDeckContractError(
                    "Scenario applicator changed note/card counts; content cloning is forbidden.", stage="scenario"
                )
            if not set(perf100_cards).issubset(imported_cards) or len(perf100_cards) != len(set(perf100_cards)):
                raise RealDeckContractError("perf100 selection is not distinct imported cards.", stage="scenario", subject_id="perf100")
        finally:
            conn.close()

        report = {
            "schemaVersion": 1,
            "status": "PASS",
            "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contentMutation": {
                "notesCreated": 0,
                "cardsCreated": 0,
                "templatesChanged": 0,
                "fieldsChanged": 0,
                "mediaChanged": 0,
            },
            "before": before,
            "after": after,
            "scenarios": results,
            "studyHistory": {
                "cardCount": len(history_cards),
                "revlogRowsAdded": len(history_revlog_ids),
                "cardIds": history_cards,
            },
            "perf100": {
                "enabled": perf100_enabled,
                "targetCardCount": 100,
                "selectedCardCount": len(perf100_cards),
                "distinctCardCount": len(set(perf100_cards)),
                "cardIds": perf100_cards,
                "notesOrCardsCloned": 0,
            },
        }
        write_json(args.artifacts_dir / "scenario-application-report.json", report)
        last_completed_step = "scenario report written"
        log(
            f"scenarios applied to {len(results)} anchors; history cards={len(history_cards)}; "
            f"perf100={'PASS' if perf100_enabled else 'disabled'}"
        )
        log("collection ready")
        return 0
    except Exception as error:
        stage = getattr(error, "stage", "scenario")
        subject = getattr(error, "subject_id", "") or current_subject
        failure = {
            "schemaVersion": 1,
            "status": "FAIL",
            "stage": stage,
            "subjectId": subject,
            "errorType": type(error).__name__,
            "error": str(error),
            "lastCompletedStep": last_completed_step,
            "traceback": traceback.format_exc(),
        }
        write_json(args.artifacts_dir / "real-deck-failure.json", failure)
        log(f"FAIL stage={stage} subject={subject or '-'}: {error}")
        return 1


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RealDeckContractError(f"Required report is missing: {path.name}", stage="scenario") from error
    if not isinstance(value, dict) or value.get("status") != "PASS":
        raise RealDeckContractError(f"Required report is invalid: {path.name}", stage="scenario")
    return value


def collection_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "notes": int(conn.execute("select count(*) from notes").fetchone()[0]),
        "cards": int(conn.execute("select count(*) from cards").fetchone()[0]),
        "revlog": int(conn.execute("select count(*) from revlog").fetchone()[0]),
    }


def verify_cards_exist(conn: sqlite3.Connection, card_ids: set[int]) -> None:
    placeholders = ",".join("?" for _ in card_ids)
    found = {int(row[0]) for row in conn.execute(f"select id from cards where id in ({placeholders})", sorted(card_ids))}
    missing = sorted(card_ids - found)
    if missing:
        raise RealDeckContractError(
            f"Imported card IDs are missing from collection: {missing[:5]}", stage="scenario"
        )


def card_state(conn: sqlite3.Connection, card_id: int) -> dict[str, int]:
    row = conn.execute(
        "select queue, type, due, ivl, factor, reps, lapses from cards where id = ?", (card_id,)
    ).fetchone()
    if row is None:
        raise RealDeckContractError(f"Card is missing: {card_id}", stage="scenario", subject_id=str(card_id))
    return {
        "queue": int(row[0]),
        "type": int(row[1]),
        "due": int(row[2]),
        "interval": int(row[3]),
        "factor": int(row[4]),
        "reps": int(row[5]),
        "lapses": int(row[6]),
    }


def apply_card_plan(
    conn: sqlite3.Connection,
    card_id: int,
    plan: dict[str, Any],
    *,
    next_revlog_id: int,
    first_review_ms: int,
) -> tuple[int, list[int]]:
    reviews = [int(value) for value in plan.get("reviews") or []]
    conn.execute(
        """
        update cards
        set queue = ?, type = ?, due = ?, ivl = ?, factor = ?,
            reps = ?, lapses = ?, left = 0, odue = 0, odid = 0,
            mod = ?, usn = -1
        where id = ?
        """,
        (
            int(plan.get("queue", 2)),
            int(plan.get("type", 2)),
            1 + (card_id % 5000),
            int(plan.get("ivl", 1)),
            int(plan.get("factor", 2100)),
            len(reviews),
            int(plan.get("lapses", 0)),
            int(time.time()),
            card_id,
        ),
    )
    revlog_ids: list[int] = []
    for index, ease in enumerate(reviews):
        candidate = first_review_ms + index * 1000
        next_revlog_id = max(next_revlog_id + 1, candidate)
        answer_ms = 8_000 + ((card_id + index) % 15) * 1_000
        conn.execute(
            """
            insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
            values (?, ?, -1, ?, ?, ?, ?, ?, 1)
            """,
            (
                next_revlog_id,
                card_id,
                ease,
                int(plan.get("ivl", 1)),
                max(0, int(plan.get("ivl", 1)) - 1),
                int(plan.get("factor", 2100)),
                answer_ms,
            ),
        )
        revlog_ids.append(next_revlog_id)
    return next_revlog_id, revlog_ids


if __name__ == "__main__":
    raise SystemExit(main())
