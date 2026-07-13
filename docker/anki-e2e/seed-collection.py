#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any


FIELD_SEPARATOR = "\x1f"
GIF_96X96 = base64.b64decode(
    "R0lGODdhYABgAIEAAP///yVj6wAAAAAAACwAAAAAYABgAEAI/wABCBxIsKDBgwgTKlzIsKHDhxAjSpzYMIBFiwQvYhyoMUBGjR8vhtwosONIjxxJTjSZUmRLlSxLgnyJ"
    "UqZLmzBrUowJgKfPmTh1/rzZE2hPiieT0lQalGlRojx3Oh2aE6pRqkKNrsxqtWvVr1zBOpXoNazZqVfTlkWqVuzSt03hPnVLtu1ZuVjRekXKt6/fv4ADC4Z4N67huYUR"
    "61W5dXHivHjt8l0bmfJhyIcjSq5MVzHnxIQ3XxbtefTenaQxl16tmmhdy6xTy7bat/Xszq392oa9u7PUz46DAx9MvLjx48iTK19eEfftx891Rx9uGjdq57ynV9d5Hbt36"
    "LC7g///Lrz67+3lY2d3vXU9eerqUafvPR50+/fo4f+8Pl+7et/31defe0J1NyB+/9n3GoL0pSfegQLqx55DEeZnYYLSEQjhgPJJqKGHjAW4IYjQ8UfiiBcyp+KKLLbo4"
    "oswxijjjDTWaOONOOaYEooYnvhXgz6myJZ/QF4YIoVEJumeiUYqiaBmPBbZY4YMOvnYkB82meVTBgY55ZdRPVTlllJOZmWUWmE55poliuillFQxCeaZ8EH5Jp2ZqVnhnG"
    "TqiSaZanWpJZsOirknnP6ZCeiiAD54J6NZOTroobfJiSikYxH2J6FyKcrppFP5+einXN63KaXhGXrqqj/iyWejboI1Omqksb6KqneWunrpkRSyKmuektrq61HB7norV4I"
    "KO2umSA5rLGDPLqvjtNRWa+212Gb7V0AAOw=="
)
TINY_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00TIT2\x00\x00\x00\x05\x00\x00\x03e2e\x00"
REAL_MEDIA_ALLOWLIST = ("要.gif", "望.gif", "要望.mp3")

JAPANESE_FRONT = (
    '[sound:要望.mp3]<br>'
    '【<span style="color: rgb(170, 170, 127);"><b>を</b></span>】'
    '<img src="要.gif"><img src="望.gif">'
    '（<span style="color: rgb(255, 165, 0);"><b>する</b></span>）'
    '<br><br>（改善を<span class="word-focus">要望する</span>。）'
)

JAPANESE_CSS = """
.card {
  font-family: "Hiragino Kaku Gothic Pro", "Meiryo", "Noto Sans JP", Arial, sans-serif;
  font-size: 20px;
  text-align: center;
  color: #333;
  background-color: #fcfcfc;
  line-height: 1.6;
}
.nightMode .card, .card.nightMode {
  background-color: #2f2f31;
  color: #dcdcdc;
}
.main-word {
  font-size: 36px;
  font-weight: bold;
  color: #000;
  margin-top: 40px;
  margin-bottom: 40px;
}
.nightMode .main-word, .card.nightMode .main-word {
  color: #fff;
}
.word-focus {
  color: rgb(255, 170, 0);
  font-weight: bold;
}
.align-left {
  text-align: left;
  padding: 10px 20px;
  max-width: 800px;
  margin: 0 auto;
}
.meaning-box {
  background-color: #e8f4fd;
  border-left: 5px solid #3498db;
  padding: 15px;
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: 600;
  border-radius: 5px;
  color: #2c3e50;
}
.reading-box {
  background-color: #fff8e1;
  border: 1px solid #ffe082;
  padding: 10px 15px;
  margin-bottom: 20px;
  border-radius: 5px;
}
.section-label {
  font-size: 14px;
  text-transform: uppercase;
  color: #f39c12;
  font-weight: bold;
  margin-bottom: 5px;
}
.reading-content {
  font-family: "Consolas", monospace;
  font-size: 18px;
  display: flex;
  align-items: center;
}
.pos-tag {
  display: inline-block;
  font-size: 14px;
  font-weight: normal;
  color: #555;
  background-color: #e0e0e0;
  padding: 4px 10px;
  border-radius: 15px;
  margin-bottom: 8px;
}
.section-container {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}
.section-title {
  font-size: 16px;
  font-weight: bold;
  color: #7f8c8d;
  margin-bottom: 5px;
}
.text-body {
  font-size: 20px;
  line-height: 1.8;
}
.examples {
  font-style: italic;
  color: #555;
  margin-left: 10px;
  border-left: 2px solid #ddd;
  padding-left: 10px;
}
.similar-box {
  background-color: #f3f3f3;
  border: 1px solid #e0e0e0;
  border-left: 4px solid #9aa0a6;
  border-radius: 5px;
  padding: 12px 14px;
  margin-top: 5px;
}
.similar-item {
  display: inline-block;
  background-color: #ffffff;
  border: 1px solid #dddddd;
  border-radius: 14px;
  padding: 3px 10px;
  margin: 0 6px 8px 0;
  font-size: 20px;
}
.card img {
  max-width: 100%;
  height: auto;
  border-radius: 3px;
}
"""

JAPANESE_QFMT = """
<div class="card-content">
  <div class="main-word">
    {{Слово}}
  </div>
</div>
"""

JAPANESE_AFMT = """
{{FrontSide}}

<hr id="answer">

<div class="card-content align-left">
  {{#Часть речи}}
  <div class="pos-tag">{{Часть речи}}</div>
  {{/Часть речи}}

  {{#Значение}}
  <div class="meaning-box">{{Значение}}</div>
  {{/Значение}}

  {{#Ударение}}
  <div class="reading-box">
    <div class="section-label">Чтение:</div>
    <div class="reading-content">{{Ударение}}</div>
  </div>
  {{/Ударение}}

  {{#Пример}}
  <div class="section-container">
    <div class="section-title">Примеры:</div>
    <div class="text-body examples">{{Пример}}</div>
  </div>
  {{/Пример}}

  {{#Похожие слова}}
  <div class="section-container similar-box">
    <div class="section-title">Похожие:</div>
    <div class="text-body">{{Похожие слова}}</div>
  </div>
  {{/Похожие слова}}
</div>
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
    media_summary = write_media(media_dir)
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
        "media": media_summary,
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
            ["Слово", "Значение", "Пример", "Часть речи", "Ударение", "Похожие слова", "Аудио", "Изображение"],
            JAPANESE_QFMT,
            JAPANESE_AFMT,
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
                "Пример": '<div class="example-item"><div class="jp">改善を<span class="word-focus">要望する</span>。</div><div class="ru">просить улучшения</div></div>',
                "Часть речи": "する-verb",
                "Ударение": "ようぼう",
                "Похожие слова": '<span class="similar-item">要求</span><span class="similar-item">希望</span>',
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
        for index in range(1, 7):
            activity_deck_id = get_deck_id(col, f"E2E Activity::Deck {index:02d}")
            add_note(
                col,
                generic_model,
                {"Front": f"Activity fixture {index}", "Back": "Synthetic activity history"},
                activity_deck_id,
                tags=["e2e", "activity-fixture"],
            )
        deck_hub_fixtures = [
            ("E2E Decks", "DeckHub Parent Direct", "Parent deck has direct cards."),
            ("E2E Decks::Healthy", "DeckHub Healthy", "High-volume healthy child."),
            ("E2E Decks::Danger", "DeckHub Danger", "Danger child under a healthy aggregate."),
            ("E2E Decks::Attention", "DeckHub Attention", "Attention child."),
            ("E2E Decks::Preliminary", "DeckHub Preliminary", "Low-sample child."),
            ("E2E Decks::N3", "DeckHub Duplicate A", "Duplicate short name under first root."),
            ("E2E Grammar::N3", "DeckHub Duplicate B", "Duplicate short name under second root."),
            ("E2E Deep::Level 2::Уровень 3::Level 4::Level 5::Level 6", "DeckHub Deep", "Six-level non-Latin hierarchy."),
        ]
        for deck_name, front, back in deck_hub_fixtures:
            add_note(
                col,
                generic_model,
                {"Front": front, "Back": back},
                get_deck_id(col, deck_name),
                tags=["e2e", "deck-hub"],
            )
        get_filtered_deck_id(col, "E2E Filtered Health Excluded")
        configure_fsrs_fixture(col)
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


def get_filtered_deck_id(col: Any, name: str) -> int:
    method = getattr(col.decks, "id", None)
    if not callable(method):
        raise RuntimeError("Could not create filtered fixture deck")
    return int(method(name, create=True, type=1))


def configure_fsrs_fixture(col: Any) -> None:
    """Enable FSRS and create two deterministic compatible groups."""
    col.set_config("fsrs", True)
    fixture_deck_id = get_deck_id(col, "E2E Fixtures")
    default = col.decks.get_config(1) or col.decks.config_dict_for_deck_id(fixture_deck_id)
    native_defaults = col.decks.get_deck_configs_for_update(fixture_deck_id).defaults.config
    default["fsrsParams6"] = list(native_defaults.fsrs_params_6)
    default["desiredRetention"] = 0.90
    default["new"]["delays"] = [1, 10]
    default["lapse"]["delays"] = [10]
    col.decks.update_config(default)
    second = col.decks.add_config("E2E Science", clone_from=default)
    second["desiredRetention"] = 0.88
    weights = list(second.get("fsrsParams6") or second.get("fsrsWeights") or [])
    if weights:
        weights[0] = round(float(weights[0]) + 0.01, 7)
        second["fsrsParams6" if second.get("fsrsParams6") else "fsrsWeights"] = weights
    second["new"]["delays"] = []
    second["lapse"]["delays"] = []
    col.decks.update_config(second)
    for deck in col.decks.all():
        name = str(deck.get("name") or "")
        if name.startswith("E2E Decks") or name.startswith("E2E Grammar"):
            col.decks.set_config_id_for_deck_dict(deck, second["id"])
        elif name == "E2E Fixtures":
            deck["desiredRetention"] = 0.93
            col.decks.save(deck)


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


def write_media(media_dir: Path) -> dict[str, Any]:
    media_dir.mkdir(parents=True, exist_ok=True)
    for name in ("要.gif", "望.gif"):
        (media_dir / name).write_bytes(GIF_96X96)
    (media_dir / "要望.mp3").write_bytes(TINY_MP3)
    summary = {
        "mode": "synthetic",
        "syntheticFiles": list(REAL_MEDIA_ALLOWLIST),
        "realMediaDir": "",
        "copiedRealMedia": [],
        "missingRealMedia": [],
        "requireRealMedia": os.environ.get("ANKI_E2E_REQUIRE_REAL_MEDIA") == "1",
    }
    real_media_dir = Path(os.environ.get("ANKI_E2E_REAL_MEDIA_DIR") or "/e2e/real-media")
    if real_media_dir.exists():
        summary["mode"] = "real-media"
        summary["realMediaDir"] = str(real_media_dir)
        for name in REAL_MEDIA_ALLOWLIST:
            source = real_media_dir / name
            if source.is_file():
                shutil.copyfile(source, media_dir / name)
                summary["copiedRealMedia"].append(name)
            else:
                summary["missingRealMedia"].append(name)
    elif summary["requireRealMedia"]:
        summary["missingRealMedia"] = list(REAL_MEDIA_ALLOWLIST)

    if summary["requireRealMedia"] and summary["missingRealMedia"]:
        missing = ", ".join(summary["missingRealMedia"])
        raise RuntimeError(f"Required real media files are missing: {missing}")

    print(
        "Media fixture mode: "
        f"{summary['mode']}; copied={summary['copiedRealMedia']}; missing={summary['missingRealMedia']}"
    )
    return summary


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
        grouped: dict[str, list[int]] = {
            "japanese": [],
            "generic": [],
            "customCss": [],
            "unsafe": [],
            "deckHubParent": [],
            "deckHubHealthy": [],
            "deckHubDanger": [],
            "deckHubAttention": [],
            "deckHubPreliminary": [],
            "deckHubOther": [],
        }
        for card_id, fields in cards:
            text = str(fields or "")
            if "DeckHub Parent Direct" in text:
                grouped["deckHubParent"].append(int(card_id))
            elif "DeckHub Healthy" in text:
                grouped["deckHubHealthy"].append(int(card_id))
            elif "DeckHub Danger" in text:
                grouped["deckHubDanger"].append(int(card_id))
            elif "DeckHub Attention" in text:
                grouped["deckHubAttention"].append(int(card_id))
            elif "DeckHub Preliminary" in text:
                grouped["deckHubPreliminary"].append(int(card_id))
            elif "DeckHub " in text:
                grouped["deckHubOther"].append(int(card_id))
            elif "要望" in text:
                grouped["japanese"].append(int(card_id))
            elif "Styled prompt" in text:
                grouped["customCss"].append(int(card_id))
            elif "Unsafe" in text:
                grouped["unsafe"].append(int(card_id))
            else:
                grouped["generic"].append(int(card_id))

        conn.execute("delete from revlog")
        now_ms = int(time.time() * 1000)
        day_counters: dict[int, int] = {}

        def add_reviews(
            card_id: int,
            reviews: list[tuple[int, int]],
            *,
            days_ago: int = 0,
            last_interval: int = 10,
            review_type: int = 1,
        ) -> None:
            for ease, answer_ms in reviews:
                day_counters[days_ago] = day_counters.get(days_ago, 0) + 1
                review_id = now_ms - days_ago * 86_400_000 - 600_000 + day_counters[days_ago] * 1000
                conn.execute(
                    """
                    insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
                    values (?, ?, -1, ?, 1, ?, 2500, ?, ?)
                    """,
                    (review_id, card_id, ease, last_interval, answer_ms, review_type),
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

        for card_id in grouped["deckHubParent"]:
            add_reviews(card_id, [(3, 5_000)] * 10)
        for card_id in grouped["deckHubHealthy"]:
            add_reviews(card_id, [(3, 5_000)] * 80)
        for card_id in grouped["deckHubDanger"]:
            add_reviews(card_id, [(3, 8_000)] * 3 + [(1, 12_000)] * 7)
        for card_id in grouped["deckHubAttention"]:
            add_reviews(card_id, [(3, 8_000)] * 7 + [(1, 11_000)] * 3)
        for card_id in grouped["deckHubPreliminary"]:
            add_reviews(card_id, [(3, 6_000)] * 3)
        for card_id in grouped["deckHubOther"]:
            add_reviews(card_id, [(3, 5_000)] * 10)

        history_cards = [
            card_id
            for key in ("japanese", "generic", "customCss", "unsafe")
            for card_id in grouped[key]
        ]
        active_day_plans = {
            1: 4,
            2: 5,
            5: 7,
            6: 7,
            8: 6,
            10: 6,
            12: 3,
            13: 3,
            15: 3,
            17: 3,
            20: 4,
            21: 4,
            22: 4,
            26: 3,
            28: 3,
            31: 2,
            34: 2,
        }
        for plan_index, (days_ago, review_count) in enumerate(active_day_plans.items()):
            for review_index in range(review_count):
                card_id = history_cards[(plan_index + review_index) % len(history_cards)]
                ease = 1 if review_index % 5 == 0 else 3 if review_index % 3 else 4
                add_reviews(card_id, [(ease, 4_000 + review_index * 350)], days_ago=days_ago)

        # Statistics v1: bounded multi-month/all-time history with both current
        # and previous periods, active gaps, ratings 1-4, young/mature first
        # reviews and real introduced-card events. The first two calls repeat
        # the same card/day so True Retention must count only the first one.
        statistics_day_plans = {
            45: (1, 10),
            60: (2, 21),
            75: (3, 10),
            95: (4, 21),
            125: (3, 10),
            180: (1, 21),
            240: (2, 10),
            330: (3, 21),
            400: (4, 21),
        }
        for index, (days_ago, (ease, last_interval)) in enumerate(statistics_day_plans.items()):
            card_id = history_cards[index % len(history_cards)]
            add_reviews(card_id, [(ease, 5_000 + index * 250)], days_ago=days_ago, last_interval=last_interval)
            if days_ago == 45:
                add_reviews(card_id, [(3, 3_500)], days_ago=days_ago, last_interval=last_interval)
            if index % 3 == 0:
                introduced = history_cards[(index + 1) % len(history_cards)]
                add_reviews(introduced, [(3, 4_500)], days_ago=days_ago, last_interval=0, review_type=0)

        # Manual/reschedule entry: ease=0/factor=0 must be excluded from all
        # answered-review and retention aggregates.
        manual_id = now_ms - 50 * 86_400_000 - 300_000
        conn.execute(
            "insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type) values (?, ?, -1, 0, 30, 30, 0, 1000, 4)",
            (manual_id, history_cards[0]),
        )

        # Current schedule snapshot for overdue and bounded 7/30/90 day due
        # categories. Review due values use scheduler-day numbers; learning
        # queues use Unix seconds.
        collection_created = int(conn.execute("select crt from col limit 1").fetchone()[0])
        scheduler_day = max(0, int(time.time() // 86_400 - collection_created // 86_400))
        schedule_cards = history_cards[:7]
        if len(schedule_cards) >= 7:
            conn.execute("update cards set type=2, queue=2, ivl=30, due=? where id=?", (scheduler_day - 3, schedule_cards[0]))
            conn.execute("update cards set type=2, queue=2, ivl=14, due=? where id=?", (scheduler_day + 7, schedule_cards[1]))
            conn.execute("update cards set type=2, queue=2, ivl=45, due=? where id=?", (scheduler_day + 30, schedule_cards[2]))
            conn.execute("update cards set type=1, queue=1, ivl=0, due=? where id=?", (int(time.time()) + 2 * 86_400, schedule_cards[3]))
            conn.execute("update cards set type=3, queue=3, ivl=5, due=? where id=?", (int(time.time()) + 14 * 86_400, schedule_cards[4]))
            conn.execute("update cards set queue=-1 where id=?", (schedule_cards[5],))
            conn.execute("update cards set queue=-2 where id=?", (schedule_cards[6],))

        for index, (card_id,) in enumerate(conn.execute("select id from cards order by id").fetchall()):
            state = {"s": [0.8, 3.0, 14.0, 60.0, 180.0, 500.0][index % 6], "d": 1.0 + (index % 10), "decay": 0.5}
            conn.execute("update cards set data=? where id=?", (json.dumps(state), card_id))

        conn.commit()
        return grouped
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
