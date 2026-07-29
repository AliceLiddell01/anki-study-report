#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

DAY_MS = 86_400_000
EASES = [1, 1, 1, 3, 1, 1, 2, 1, 3, 1]


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the exact Cards AV/media real-card scenario.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    card_id = int(required_env("ANKI_E2E_EXACT_CARD_ID"))
    gif_name = required_env("ANKI_E2E_EXACT_GIF_NAME")
    mp3_name = required_env("ANKI_E2E_EXACT_MP3_NAME")
    png_name = required_env("ANKI_E2E_EXACT_PNG_NAME")
    apkg_path = Path(required_env("ANKI_E2E_EXACT_APKG_PATH"))
    apkg_sha = required_env("ANKI_E2E_EXACT_APKG_SHA256")

    if not apkg_path.is_file():
        raise RuntimeError(f"Exact APKG is missing or not a file: {apkg_path}")
    actual_apkg_sha = sha256_file(apkg_path)
    if actual_apkg_sha != apkg_sha:
        raise RuntimeError(f"Exact APKG SHA mismatch: expected={apkg_sha} actual={actual_apkg_sha}")

    collection = args.profile_dir / "collection.anki2"
    if not collection.is_file():
        raise RuntimeError(f"Collection is missing: {collection}")

    conn = sqlite3.connect(collection)
    conn.row_factory = sqlite3.Row
    try:
        before_counts = {
            "notes": int(conn.execute("select count(*) from notes").fetchone()[0]),
            "cards": int(conn.execute("select count(*) from cards").fetchone()[0]),
            "revlog": int(conn.execute("select count(*) from revlog").fetchone()[0]),
        }
        row = conn.execute(
            """
            select c.id as card_id, c.nid as note_id, c.did as deck_id,
                   c.queue, c.type, c.ivl, c.factor, c.reps, c.lapses,
                   n.flds
            from cards c join notes n on n.id = c.nid
            where c.id = ?
            """,
            (card_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Exact oracle card is missing: {card_id}")

        fields = str(row["flds"]).split("\x1f")
        joined = "\n".join(fields)
        for marker in (f"[sound:{mp3_name}]", gif_name, png_name):
            if marker not in joined:
                raise RuntimeError(f"Exact oracle field marker is missing: {marker}")

        before_state = {
            key: int(row[key])
            for key in ("queue", "type", "ivl", "factor", "reps", "lapses")
        }

        conn.execute("delete from revlog where cid = ?", (card_id,))
        now_ms = int(time.time() * 1000)
        first_ms = now_ms - 72 * 60 * 60 * 1000
        revlog_ids: list[int] = []
        for index, ease in enumerate(EASES):
            revlog_id = first_ms + index * 6 * 60 * 60 * 1000
            answer_ms = 9_000 + index * 750
            conn.execute(
                """
                insert into revlog
                  (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
                values (?, ?, -1, ?, 2, 1, 1700, ?, 1)
                """,
                (revlog_id, card_id, ease, answer_ms),
            )
            revlog_ids.append(revlog_id)

        conn.execute(
            """
            update cards
            set queue = 2, type = 2, due = ?, ivl = 2, factor = 1700,
                reps = ?, lapses = 7, left = 0, odue = 0, odid = 0,
                mod = ?, usn = -1
            where id = ?
            """,
            (1 + card_id % 5000, len(EASES), int(time.time()), card_id),
        )
        conn.commit()

        after_row = conn.execute(
            "select queue, type, ivl, factor, reps, lapses from cards where id = ?",
            (card_id,),
        ).fetchone()
        after_counts = {
            "notes": int(conn.execute("select count(*) from notes").fetchone()[0]),
            "cards": int(conn.execute("select count(*) from cards").fetchone()[0]),
            "revlog": int(conn.execute("select count(*) from revlog").fetchone()[0]),
        }
        if before_counts["notes"] != after_counts["notes"] or before_counts["cards"] != after_counts["cards"]:
            raise RuntimeError("Exact scenario changed note/card counts")

        payload = {
            "schemaVersion": 1,
            "status": "PASS",
            "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cardId": card_id,
            "noteId": int(row["note_id"]),
            "deckId": int(row["deck_id"]),
            "apkg": {"path": apkg_path.name, "sha256": actual_apkg_sha},
            "fieldContentSha256": sha256_text(joined),
            "requiredMediaMarkers": [mp3_name, gif_name, png_name],
            "beforeCounts": before_counts,
            "afterCounts": after_counts,
            "beforeState": before_state,
            "afterState": {
                key: int(after_row[key])
                for key in ("queue", "type", "ivl", "factor", "reps", "lapses")
            },
            "revlogIds": revlog_ids,
            "easeSequence": EASES,
            "contentMutation": {
                "notesCreated": 0,
                "cardsCreated": 0,
                "fieldsChanged": 0,
                "templatesChanged": 0,
                "mediaChanged": 0,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"[cards-exact] scenario PASS card={card_id} revlog={len(revlog_ids)} fields/media unchanged",
            flush=True,
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
