#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
import sqlite3
from typing import Any


REFERENCE_NOTE_TYPES = ["Основная", "Грамматика", "Слова", "Копия Грамматика"]
REFERENCE_MEDIA = [
    "要.gif",
    "望.gif",
    "要望.mp3",
    "要望.png",
    "厨.gif",
    "厨.mp3",
    "厨.png",
    "遺.gif",
    "伝.gif",
    "子.gif",
    "型.gif",
    "遺伝子型.mp3",
    "遺伝子型.png",
]
DEFAULT_CANDIDATES = [
    "/e2e/local-input/asr-e2e-render-fixtures.apkg",
    "/workspace/docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg",
    "/e2e/workspace-build/docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg",
    "/e2e/workspace/docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Optionally import an APKG fixture into the E2E collection.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--apkg-path", default="")
    parser.add_argument("--require", action="store_true")
    args = parser.parse_args()

    profile_dir = args.profile_dir
    artifacts_dir = args.artifacts_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifacts_dir / "apkg-import-summary.json"
    require = args.require or os.environ.get("ANKI_E2E_REQUIRE_APKG_FIXTURE") == "1"
    collection_path = profile_dir / "collection.anki2"
    media_dir = profile_dir / "collection.media"
    apkg_path = find_apkg_path(args.apkg_path)

    if apkg_path is None:
        summary = base_summary(False, "")
        summary.update(
            {
                "imported": False,
                "skipped": True,
                "skipReason": "APKG fixture not found; using synthetic fixture only.",
                "candidatePaths": [mask_path(path) for path in candidate_paths(args.apkg_path)],
            }
        )
        write_json(summary_path, summary)
        if require:
            raise RuntimeError(
                "ANKI_E2E_REQUIRE_APKG_FIXTURE=1 but no APKG fixture was found. "
                "Set ANKI_E2E_APKG_FIXTURE or add docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg."
            )
        print("APKG fixture not found; skipping optional APKG mode.")
        return 0

    if not collection_path.is_file():
        raise RuntimeError(f"E2E collection is missing: {collection_path}")

    before = collection_snapshot(collection_path)
    imported = import_with_supported_anki_api(collection_path, apkg_path)
    after = collection_snapshot(collection_path)
    imported_card_ids = sorted(after["cardIds"] - before["cardIds"])
    imported_note_ids = sorted(after["noteIds"] - before["noteIds"])
    imported_deck_ids = sorted(after["deckIds"] - before["deckIds"])
    imported_model_ids = sorted(after["modelIds"] - before["modelIds"])
    deck_names = names_for_decks(collection_path, imported_card_ids)
    note_type_names = names_for_note_types(collection_path, imported_note_ids)
    media_found = sorted([name for name in REFERENCE_MEDIA if (media_dir / name).is_file()])

    summary = base_summary(True, str(apkg_path))
    summary.update(
        {
            "imported": True,
            "importApi": imported,
            "deckIds": imported_deck_ids,
            "deckNames": deck_names,
            "noteTypeIds": imported_model_ids,
            "noteTypeNames": note_type_names,
            "noteCount": len(imported_note_ids),
            "cardCount": len(imported_card_ids),
            "cardIds": imported_card_ids,
            "noteIds": imported_note_ids,
            "mediaFilesExpected": REFERENCE_MEDIA,
            "mediaFilesFound": media_found,
            "warnings": import_warnings(note_type_names, media_found),
        }
    )
    write_json(summary_path, summary)
    print(
        "Imported APKG fixture with "
        f"{summary['noteCount']} notes, {summary['cardCount']} cards via {summary['importApi']}."
    )
    return 0


def candidate_paths(explicit_path: str = "") -> list[Path]:
    paths: list[Path] = []
    for value in (explicit_path, os.environ.get("ANKI_E2E_APKG_FIXTURE_PATH", "")):
        if value:
            paths.append(Path(value))
    paths.extend(Path(value) for value in DEFAULT_CANDIDATES)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def find_apkg_path(explicit_path: str = "") -> Path | None:
    for path in candidate_paths(explicit_path):
        if path.is_file():
            return path
    return None


def base_summary(enabled: bool, path: str) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "apkgPath": mask_path(path),
        "imported": False,
        "deckNames": [],
        "noteTypeNames": [],
        "noteCount": 0,
        "cardCount": 0,
        "mediaFilesExpected": REFERENCE_MEDIA,
        "mediaFilesFound": [],
        "warnings": [],
    }


def import_with_supported_anki_api(collection_path: Path, apkg_path: Path) -> str:
    from anki.collection import Collection

    errors: list[str] = []
    col = Collection(str(collection_path))
    try:
        try:
            from anki.importing.apkg import AnkiPackageImporter

            importer = AnkiPackageImporter(col, str(apkg_path))
            call_importer_method(importer)
            save_collection(col)
            return "anki.importing.apkg.AnkiPackageImporter"
        except Exception as error:
            errors.append(f"anki.importing.apkg.AnkiPackageImporter: {error}")

        try:
            from anki import import_export_pb2

            backend = getattr(col, "_backend", None)
            method = getattr(backend, "import_anki_package", None)
            if callable(method):
                options = import_export_pb2.ImportAnkiPackageOptions(
                    merge_notetypes=True,
                    update_notes=import_export_pb2.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                    update_notetypes=import_export_pb2.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                    with_scheduling=False,
                    with_deck_configs=True,
                )
                method(package_path=str(apkg_path), options=options)
                save_collection(col)
                return "Collection._backend.import_anki_package"
            errors.append("Collection._backend.import_anki_package: method missing")
        except Exception as error:
            errors.append(f"Collection._backend.import_anki_package: {error}")
    finally:
        close_collection(col)

    raise RuntimeError(
        "Could not import APKG through supported Anki APIs. Tried: " + " | ".join(errors)
    )


def call_importer_method(importer: Any) -> Any:
    for name in ("run", "import_file", "import_into_collection"):
        method = getattr(importer, name, None)
        if callable(method):
            return call_with_supported_args(method)
    raise RuntimeError(f"No known import method on {type(importer).__name__}")


def call_with_supported_args(method: Any, *preferred_args: Any) -> Any:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return method(*preferred_args)
    required = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    ]
    args = list(preferred_args[: len(required)])
    if len(args) < len(required):
        args.extend(None for _ in range(len(required) - len(args)))
    return method(*args)


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


def collection_snapshot(collection_path: Path) -> dict[str, set[int]]:
    conn = sqlite3.connect(collection_path)
    try:
        return {
            "cardIds": ids(conn, "select id from cards"),
            "noteIds": ids(conn, "select id from notes"),
            "deckIds": ids(conn, "select distinct did from cards"),
            "modelIds": ids(conn, "select distinct mid from notes"),
        }
    finally:
        conn.close()


def ids(conn: sqlite3.Connection, query: str, *params: Any) -> set[int]:
    return {int(row[0]) for row in conn.execute(query, params).fetchall() if row and row[0] is not None}


def names_for_decks(collection_path: Path, card_ids: list[int]) -> list[str]:
    if not card_ids:
        return []
    deck_ids = values_for_cards(collection_path, card_ids, "did")
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        names_by_id = deck_names_by_id(col)
        names = []
        for deck_id in deck_ids:
            name = names_by_id.get(deck_id, str(deck_id))
            if name not in names:
                names.append(name)
        return names
    finally:
        close_collection(col)


def names_for_note_types(collection_path: Path, note_ids: list[int]) -> list[str]:
    if not note_ids:
        return []
    model_ids = values_for_notes(collection_path, note_ids, "mid")
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        names_by_id = model_names_by_id(col)
        names = []
        for model_id in model_ids:
            name = names_by_id.get(model_id, str(model_id))
            if name not in names:
                names.append(name)
        return names
    finally:
        close_collection(col)


def values_for_cards(collection_path: Path, card_ids: list[int], column: str) -> list[int]:
    conn = sqlite3.connect(collection_path)
    try:
        placeholders = ", ".join("?" for _ in card_ids)
        rows = conn.execute(
            f"select distinct {column} from cards where id in ({placeholders}) order by {column}",
            card_ids,
        ).fetchall()
        return [int(row[0]) for row in rows if row and row[0] is not None]
    finally:
        conn.close()


def values_for_notes(collection_path: Path, note_ids: list[int], column: str) -> list[int]:
    conn = sqlite3.connect(collection_path)
    try:
        placeholders = ", ".join("?" for _ in note_ids)
        rows = conn.execute(
            f"select distinct {column} from notes where id in ({placeholders}) order by {column}",
            note_ids,
        ).fetchall()
        return [int(row[0]) for row in rows if row and row[0] is not None]
    finally:
        conn.close()


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


def import_warnings(note_type_names: list[str], media_found: list[str]) -> list[str]:
    warnings = []
    missing_types = [name for name in REFERENCE_NOTE_TYPES if name not in note_type_names]
    if missing_types:
        warnings.append("Expected reference note types not found: " + ", ".join(missing_types))
    missing_media = [name for name in REFERENCE_MEDIA if name not in media_found]
    if missing_media:
        warnings.append("Expected reference media files not found: " + ", ".join(missing_media))
    return warnings


def mask_path(value: str | Path) -> str:
    text = str(value or "")
    if not text:
        return ""
    path = Path(text)
    if str(path).startswith("/e2e/local-input"):
        return f"/e2e/local-input/{path.name}"
    if str(path).startswith("/workspace"):
        return f"/workspace/.../{path.name}"
    if str(path).startswith("/e2e/workspace"):
        return f"/e2e/workspace/.../{path.name}"
    return path.name


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
