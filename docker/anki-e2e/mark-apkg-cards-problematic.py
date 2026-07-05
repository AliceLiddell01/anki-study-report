#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import time
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark imported APKG fixture cards problematic for E2E.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()

    collection_path = args.profile_dir / "collection.anki2"
    artifacts_dir = args.artifacts_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    import_summary_path = artifacts_dir / "apkg-import-summary.json"
    problem_summary_path = artifacts_dir / "apkg-problematic-summary.json"

    if not import_summary_path.is_file():
        raise RuntimeError(f"APKG import summary is missing: {import_summary_path}")
    import_summary = json.loads(import_summary_path.read_text(encoding="utf-8"))
    if not import_summary.get("enabled"):
        write_json(
            problem_summary_path,
            {
                "enabled": False,
                "cardsMarked": 0,
                "noteTypes": [],
                "cardIds": [],
                "revlogRowsAdded": 0,
                "riskPlan": [],
                "skipped": True,
                "skipReason": import_summary.get("skipReason") or "APKG mode disabled.",
            },
        )
        print("APKG mode disabled; no imported cards marked problematic.")
        return 0
    if not import_summary.get("imported"):
        raise RuntimeError("APKG mode was enabled but the import summary does not report a successful import.")
    if not collection_path.is_file():
        raise RuntimeError(f"E2E collection is missing: {collection_path}")

    imported_card_ids = [int(value) for value in import_summary.get("cardIds", [])]
    if not imported_card_ids:
        imported_card_ids = find_imported_cards(collection_path, import_summary)
    if not imported_card_ids:
        raise RuntimeError("No imported APKG cards were found to mark problematic.")

    result = mark_cards(collection_path, imported_card_ids)
    write_json(
        problem_summary_path,
        {
            "enabled": True,
            "cardsMarked": len(result["cardIds"]),
            "noteTypes": result["noteTypes"],
            "cardIds": result["cardIds"],
            "revlogRowsAdded": result["revlogRowsAdded"],
            "riskPlan": result["riskPlan"],
        },
    )
    print(f"Marked {len(result['cardIds'])} APKG cards problematic with {result['revlogRowsAdded']} revlog rows.")
    return 0


def find_imported_cards(collection_path: Path, import_summary: dict[str, Any]) -> list[int]:
    deck_names = set(str(name) for name in import_summary.get("deckNames", []) if str(name).strip())
    note_type_names = set(str(name) for name in import_summary.get("noteTypeNames", []) if str(name).strip())
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        deck_ids = [
            deck_id
            for deck_id, name in deck_names_by_id(col).items()
            if name in deck_names
        ]
        model_ids = [
            model_id
            for model_id, name in model_names_by_id(col).items()
            if name in note_type_names
        ]
    finally:
        close_collection(col)
    conn = sqlite3.connect(collection_path)
    try:
        clauses = []
        params: list[Any] = []
        if deck_ids:
            clauses.append("c.did in (" + ", ".join("?" for _ in deck_ids) + ")")
            params.extend(deck_ids)
        if model_ids:
            clauses.append("n.mid in (" + ", ".join("?" for _ in model_ids) + ")")
            params.extend(model_ids)
        if not clauses:
            return []
        rows = conn.execute(
            f"""
            select c.id
            from cards c
            join notes n on n.id = c.nid
            where {" or ".join(clauses)}
            order by c.id
            """,
            params,
        ).fetchall()
        return [int(row[0]) for row in rows]
    finally:
        conn.close()


def mark_cards(collection_path: Path, card_ids: list[int]) -> dict[str, Any]:
    model_names = model_names_by_path(collection_path)
    conn = sqlite3.connect(collection_path)
    try:
        rows = conn.execute(
            f"""
            select c.id, c.nid, c.did, n.mid
            from cards c
            join notes n on n.id = c.nid
            where c.id in ({", ".join("?" for _ in card_ids)})
            order by c.id
            """,
            card_ids,
        ).fetchall()
        now_ms = int(time.time() * 1000)
        existing_max = conn.execute("select coalesce(max(id), 0) from revlog").fetchone()[0] or 0
        next_revlog_id = max(now_ms - 3_600_000, int(existing_max) + 1_000)
        risk_plan: list[dict[str, Any]] = []
        revlog_rows_added = 0

        for index, (card_id, note_id, _deck_id, model_id) in enumerate(rows):
            plan = review_plan(index)
            reps = len(plan["reviews"])
            lapses = int(plan["lapses"])
            conn.execute(
                """
                update cards
                set reps = max(reps, ?),
                    lapses = max(lapses, ?),
                    type = 2,
                    queue = 2,
                    due = max(due, 1),
                    factor = 2100,
                    ivl = max(ivl, 1)
                where id = ?
                """,
                (reps, lapses, card_id),
            )
            if plan["leechTag"]:
                add_note_tag(conn, int(note_id), "leech")
            for ease, answer_ms in plan["reviews"]:
                next_revlog_id += 1_000
                conn.execute(
                    """
                    insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
                    values (?, ?, -1, ?, 1, 0, 2100, ?, 1)
                    """,
                    (next_revlog_id, card_id, ease, answer_ms),
                )
                revlog_rows_added += 1
            risk_plan.append(
                {
                    "cardId": int(card_id),
                    "noteId": int(note_id),
                    "noteTypeName": model_names.get(int(model_id), str(model_id)),
                    "againReviews": sum(1 for ease, _answer_ms in plan["reviews"] if ease == 1),
                    "reviewRows": reps,
                    "lapses": lapses,
                    "leechTag": bool(plan["leechTag"]),
                    "maxAnswerMs": max(answer_ms for _ease, answer_ms in plan["reviews"]),
                }
            )

        conn.commit()
        note_types = []
        for item in risk_plan:
            name = str(item["noteTypeName"])
            if name not in note_types:
                note_types.append(name)
        return {
            "cardIds": [int(row[0]) for row in rows],
            "noteTypes": note_types,
            "revlogRowsAdded": revlog_rows_added,
            "riskPlan": risk_plan,
        }
    finally:
        conn.close()


def review_plan(index: int) -> dict[str, Any]:
    plans = [
        {"reviews": [(1, 25_000), (1, 22_000), (1, 18_000), (1, 20_000), (3, 16_000)], "lapses": 9, "leechTag": True},
        {"reviews": [(1, 18_000), (1, 16_000), (3, 12_000), (1, 15_000)], "lapses": 6, "leechTag": False},
        {"reviews": [(1, 14_000), (1, 13_000), (3, 9_000), (3, 8_000)], "lapses": 3, "leechTag": False},
        {"reviews": [(1, 12_000), (1, 11_000), (2, 10_000)], "lapses": 2, "leechTag": False},
    ]
    if index < len(plans):
        return plans[index]
    return {"reviews": [(1, 11_000), (1, 12_000), (3, 10_000)], "lapses": 1, "leechTag": False}


def add_note_tag(conn: sqlite3.Connection, note_id: int, tag: str) -> None:
    row = conn.execute("select tags from notes where id = ?", (note_id,)).fetchone()
    tags = str(row[0] if row else "")
    normalized = {item for item in tags.split() if item}
    normalized.add(tag)
    conn.execute("update notes set tags = ? where id = ?", (" " + " ".join(sorted(normalized)) + " ", note_id))


def model_names_by_path(collection_path: Path) -> dict[int, str]:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        return model_names_by_id(col)
    finally:
        close_collection(col)


def deck_names_by_id(col: Any) -> dict[int, str]:
    try:
        return {int(deck.id): str(deck.name) for deck in col.decks.all_names_and_ids()}
    except Exception:
        return {}


def model_names_by_id(col: Any) -> dict[int, str]:
    try:
        models = col.models.all()
    except Exception:
        models = []
    if isinstance(models, dict):
        models = list(models.values())
    result = {}
    for model in models if isinstance(models, list) else []:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id") or model.get("mid")
        if model_id is None:
            continue
        result[int(model_id)] = str(model.get("name") or model_id)
    return result


def close_collection(col: Any) -> None:
    method = getattr(col, "close", None)
    if not callable(method):
        return
    try:
        method(save=True)
    except TypeError:
        method()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
