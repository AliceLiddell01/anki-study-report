#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any


FIELD_SEPARATOR = "\x1f"
GIF_1X1 = base64.b64decode(
    "R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=="
)
TINY_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00TIT2\x00\x00\x00\x05\x00\x00\x03e2e\x00"

JAPANESE_FRONT = (
    '[sound:要望.mp3]<br>'
    '【<span style="color: rgb(170, 170, 127);"><b>を</b></span>】'
    '<img src="要.gif"><img src="望.gif">'
    '（<span style="color: rgb(255, 165, 0);"><b>する</b></span>）'
    '<br><br>（改善を<span class="word-focus">要望する</span>。）'
)

JAPANESE_CSS = """
.card {
  font-family: "Noto Sans JP", "Yu Gothic", sans-serif;
  font-size: 32px;
  line-height: 1.45;
  text-align: center;
  color: #1f2937;
  background: #ffffff;
}
.nightMode .card, .card.nightMode {
  color: #f9fafb;
  background: #111827;
}
.word-focus {
  font-weight: 700;
  color: #2563eb;
}
.card img {
  max-height: 96px;
  max-width: 120px;
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Anki Study Report E2E fixture collection.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()

    profile_dir = args.profile_dir
    artifacts_dir = args.artifacts_dir
    profile_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    collection_path = profile_dir / "collection.anki2"
    media_dir = profile_dir / "collection.media"
    reset_collection(collection_path, media_dir)
    create_collection(collection_path)
    write_media(media_dir)
    card_ids = seed_review_history(collection_path)

    fixture_summary = {
        "collection": str(collection_path),
        "mediaDir": str(media_dir),
        "cardIds": card_ids,
        "notes": [
            "Japanese vocabulary fixture with sound/gif/inline style/class CSS",
            "Generic front/back fixture",
            "Custom CSS fixture",
            "Unsafe sanitizer fixture",
        ],
    }
    (artifacts_dir / "fixture-summary.json").write_text(
        json.dumps(fixture_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Seeded E2E fixture collection: {collection_path}")
    return 0


def reset_collection(collection_path: Path, media_dir: Path) -> None:
    for path in (
        collection_path,
        collection_path.with_suffix(".anki2-wal"),
        collection_path.with_suffix(".anki2-shm"),
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    shutil.rmtree(media_dir, ignore_errors=True)
    media_dir.mkdir(parents=True, exist_ok=True)


def create_collection(collection_path: Path) -> None:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        deck_id = get_deck_id(col, "E2E Fixtures")
        japanese_model = create_model(
            col,
            "E2E Japanese Vocabulary",
            ["Слово", "Значение", "Пример", "Часть речи", "Аудио", "Изображение"],
            "{{Слово}}",
            "{{FrontSide}}<hr id=\"answer\">{{Значение}}<br>{{Пример}}",
            JAPANESE_CSS,
        )
        generic_model = create_model(
            col,
            "E2E Generic Basic",
            ["Front", "Back"],
            "{{Front}}",
            "{{FrontSide}}<hr id=\"answer\">{{Back}}",
            ".card { font-family: Arial, sans-serif; color: #111827; background: white; }",
        )
        custom_model = create_model(
            col,
            "E2E Custom CSS",
            ["Prompt", "Answer", "Note"],
            '<div class="custom-card"><span class="keyword">{{Prompt}}</span></div>',
            '{{FrontSide}}<hr id="answer"><div class="answer">{{Answer}}</div><p>{{Note}}</p>',
            ".custom-card { border: 2px solid #2563eb; padding: 12px; } .keyword { color: #b45309; font-weight: 700; } .nightMode .keyword { color: #fbbf24; }",
        )
        unsafe_model = create_model(
            col,
            "E2E Unsafe Sanitizer",
            ["Front", "Back"],
            '{{Front}}<script>window.e2eUnsafe = true</script><img src="file:///tmp/secret.png" onerror="alert(1)">',
            '{{FrontSide}}<hr id="answer">{{Back}}<a href="javascript:alert(1)">bad</a>',
            ".card { color: #111827; } .bad { background-image: url(file:///tmp/secret.png); }",
        )

        add_note(
            col,
            japanese_model,
            {
                "Слово": JAPANESE_FRONT,
                "Значение": "request; demand",
                "Пример": "改善を要望する。",
                "Часть речи": "する-verb",
                "Аудио": "[sound:要望.mp3]",
                "Изображение": '<img src="要.gif"><img src="望.gif">',
            },
            deck_id,
            tags=["e2e", "leech"],
        )
        add_note(
            col,
            generic_model,
            {"Front": "Plain E2E front", "Back": "Plain E2E back"},
            deck_id,
            tags=["e2e"],
        )
        add_note(
            col,
            custom_model,
            {"Prompt": "Styled prompt", "Answer": "Styled answer", "Note": "Uses class-based CSS."},
            deck_id,
            tags=["e2e", "custom-css"],
        )
        add_note(
            col,
            unsafe_model,
            {"Front": 'Unsafe <b>front</b> <img src="要.gif">', "Back": "Unsafe back"},
            deck_id,
            tags=["e2e", "sanitizer"],
        )
        save_collection(col)
    finally:
        close_collection(col)


def create_model(col: Any, name: str, fields: list[str], qfmt: str, afmt: str, css: str) -> Any:
    models = col.models
    model = call(models, ("new", "new_model"), name)
    model["css"] = css
    for field_name in fields:
        field = call(models, ("new_field", "newField"), field_name)
        call(models, ("add_field", "addField"), model, field)
    template = call(models, ("new_template", "newTemplate"), "Card 1")
    template["qfmt"] = qfmt
    template["afmt"] = afmt
    call(models, ("add_template", "addTemplate"), model, template)
    call(models, ("add", "addModel"), model)
    return model


def get_deck_id(col: Any, name: str) -> int:
    decks = col.decks
    for method_name in ("id", "id_for_name"):
        method = getattr(decks, method_name, None)
        if not callable(method):
            continue
        try:
            return int(method(name))
        except TypeError:
            return int(method(name, create=True))
    raise RuntimeError("Could not create fixture deck")


def add_note(col: Any, model: Any, values: dict[str, str], deck_id: int, tags: list[str]) -> None:
    note = col.new_note(model)
    for field_name, value in values.items():
        note[field_name] = value
    try:
        note.tags.extend(tags)
    except Exception:
        pass
    for method_name in ("add_note", "addNote"):
        method = getattr(col, method_name, None)
        if not callable(method):
            continue
        try:
            method(note, deck_id)
            return
        except TypeError:
            method(note, deck_id=deck_id)
            return
    raise RuntimeError("Could not add note to fixture collection")


def call(target: Any, names: tuple[str, ...], *args: Any) -> Any:
    for name in names:
        method = getattr(target, name, None)
        if callable(method):
            return method(*args)
    raise AttributeError(f"Missing method on {target!r}: {names}")


def save_collection(col: Any) -> None:
    method = getattr(col, "save", None)
    if callable(method):
        method()


def close_collection(col: Any) -> None:
    method = getattr(col, "close", None)
    if not callable(method):
        return
    try:
        method(save=True)
    except TypeError:
        method()


def write_media(media_dir: Path) -> None:
    media_dir.mkdir(parents=True, exist_ok=True)
    for name in ("要.gif", "望.gif"):
        (media_dir / name).write_bytes(GIF_1X1)
    (media_dir / "要望.mp3").write_bytes(TINY_MP3)


def seed_review_history(collection_path: Path) -> dict[str, list[int]]:
    conn = sqlite3.connect(collection_path)
    try:
        cards = conn.execute(
            """
            select c.id, n.flds
            from cards c
            join notes n on n.id = c.nid
            order by c.id
            """
        ).fetchall()
        grouped: dict[str, list[int]] = {"japanese": [], "generic": [], "customCss": [], "unsafe": []}
        for card_id, fields in cards:
            text = str(fields or "")
            if "要望" in text:
                grouped["japanese"].append(int(card_id))
            elif "Styled prompt" in text:
                grouped["customCss"].append(int(card_id))
            elif "Unsafe" in text:
                grouped["unsafe"].append(int(card_id))
            else:
                grouped["generic"].append(int(card_id))

        conn.execute("delete from revlog")
        now_ms = int(time.time() * 1000)
        next_id = now_ms - 600_000

        def add_reviews(card_id: int, reviews: list[tuple[int, int]]) -> None:
            nonlocal next_id
            for ease, answer_ms in reviews:
                next_id += 1000
                conn.execute(
                    """
                    insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
                    values (?, ?, -1, ?, 1, 0, 2500, ?, 1)
                    """,
                    (next_id, card_id, ease, answer_ms),
                )

        for card_id in grouped["japanese"]:
            conn.execute("update cards set reps = 4, lapses = 8, type = 2, queue = 2 where id = ?", (card_id,))
            add_reviews(card_id, [(1, 16_000), (1, 14_000), (3, 12_000), (1, 18_000)])
        for card_id in grouped["generic"]:
            conn.execute("update cards set reps = 1, lapses = 0, type = 2, queue = 2 where id = ?", (card_id,))
            add_reviews(card_id, [(3, 3_000)])
        for card_id in grouped["customCss"]:
            conn.execute("update cards set reps = 2, lapses = 0, type = 2, queue = 2 where id = ?", (card_id,))
            add_reviews(card_id, [(3, 4_000), (4, 5_000)])
        for card_id in grouped["unsafe"]:
            conn.execute("update cards set reps = 3, lapses = 2, type = 2, queue = 2 where id = ?", (card_id,))
            add_reviews(card_id, [(1, 13_000), (1, 12_000), (1, 15_000)])

        conn.commit()
        return grouped
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
