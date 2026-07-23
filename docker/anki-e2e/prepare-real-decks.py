#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import time
import traceback
from typing import Any, Iterable

from real_deck_contract import (
    RealDeckContractError,
    load_manifest,
    model_fingerprint,
    model_structure,
    resolve_anchors,
    validate_manifest,
    validate_packages,
    write_json,
)


def log(message: str) -> None:
    print(f"[real-decks] {message}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an empty Anki collection and import all real deck fixtures.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--fixture-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    args.artifacts_dir.mkdir(parents=True, exist_ok=True)
    last_completed_step = "start"
    current_subject = ""
    try:
        log("validating manifest")
        manifest = load_manifest(args.manifest)
        packages = validate_manifest(manifest, args.fixture_dir)
        last_completed_step = "manifest schema validated"

        package_reports = []
        for index, package in enumerate(packages, start=1):
            current_subject = str(package["id"])
            log(f"package {index}/{len(packages)} {current_subject}: validating checksum")
            package_report = validate_packages([package])[0]
            package_reports.append(package_report)
            log(f"package {index}/{len(packages)} {current_subject}: checksum PASS")
        manifest_report = {
            "schemaVersion": 1,
            "status": "PASS",
            "manifestPath": "fixtures/real-decks/manifest.json",
            "packageCount": len(packages),
            "anchorCount": len(manifest.get("anchors") or {}),
            "packages": package_reports,
            "syntheticFallback": False,
        }
        write_json(args.artifacts_dir / "real-deck-manifest-report.json", manifest_report)
        last_completed_step = "all package checksums validated"

        profile_dir = args.profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        collection_path = profile_dir / "collection.anki2"
        media_dir = profile_dir / "collection.media"
        log("creating empty disposable collection")
        reset_collection(collection_path, media_dir)
        create_empty_collection(collection_path)
        last_completed_step = "empty collection created"

        import_report: dict[str, Any] = {
            "schemaVersion": 1,
            "status": "PASS",
            "collection": "collection.anki2",
            "packageOrder": [str(item["id"]) for item in packages],
            "packages": [],
            "runtimeImporter": "official Anki package importer/backend",
            "manualPackageExtraction": False,
            "syntheticFallback": False,
        }
        package_note_ids: dict[str, set[int]] = {}
        package_card_ids: dict[str, set[int]] = {}

        for index, package in enumerate(packages, start=1):
            package_id = str(package["id"])
            current_subject = package_id
            before = collection_snapshot(collection_path)
            before_media = media_inventory(media_dir)
            log(f"importing package {index}/{len(packages)}: {package_id}")
            importer_name = import_package(collection_path, Path(package["fullPath"]))
            after = collection_snapshot(collection_path)
            after_media = media_inventory(media_dir)
            note_ids = after["noteIds"] - before["noteIds"]
            card_ids = after["cardIds"] - before["cardIds"]
            model_ids = model_ids_for_notes(collection_path, note_ids)
            deck_ids = deck_ids_for_cards(collection_path, card_ids)
            media_names = sorted(after_media - before_media)
            expected = package.get("expected") or {}
            assert_expected_count(package_id, "notes", len(note_ids), int(expected.get("notes") or 0))
            assert_expected_count(package_id, "cards", len(card_ids), int(expected.get("cards") or 0))
            assert_expected_count(package_id, "noteTypes", len(model_ids), int(expected.get("noteTypes") or 0))
            assert_expected_count(package_id, "media", len(media_names), int(expected.get("media") or 0))
            package_note_ids[package_id] = note_ids
            package_card_ids[package_id] = card_ids
            item = {
                "id": package_id,
                "path": str(package["path"]),
                "status": "PASS",
                "importer": importer_name,
                "noteCount": len(note_ids),
                "cardCount": len(card_ids),
                "noteTypeCount": len(model_ids),
                "mediaCount": len(media_names),
                "noteIds": sorted(note_ids),
                "cardIds": sorted(card_ids),
                "noteTypeIds": sorted(model_ids),
                "deckIds": sorted(deck_ids),
                "media": summarize_media(media_names),
            }
            import_report["packages"].append(item)
            log(
                f"imported {package_id}: {len(note_ids)} notes, {len(card_ids)} cards, "
                f"{len(model_ids)} note types, {len(media_names)} media"
            )
            last_completed_step = f"package imported: {package_id}"

        current_subject = "collection-metadata"
        log("removing unused empty-collection metadata")
        prune_unused_metadata(collection_path)
        last_completed_step = "unused empty-collection metadata removed"

        models_by_id, deck_names_by_id = read_collection_metadata(collection_path)
        inventory = build_inventory(
            collection_path,
            media_dir,
            models_by_id=models_by_id,
            deck_names_by_id=deck_names_by_id,
            package_note_ids=package_note_ids,
            package_card_ids=package_card_ids,
        )
        assert_collection_content_is_imported_only(inventory, package_note_ids, package_card_ids)
        write_json(args.artifacts_dir / "collection-inventory.json", inventory)
        last_completed_step = "collection inventory written"

        log("resolving anchors")
        current_subject = "anchors"
        conn = sqlite3.connect(collection_path)
        try:
            resolved = resolve_anchors(
                conn,
                manifest,
                package_note_ids=package_note_ids,
                models_by_id=models_by_id,
                deck_names_by_id=deck_names_by_id,
                media_dir=media_dir,
            )
        finally:
            conn.close()
        anchor_report = {
            "schemaVersion": 1,
            "status": "PASS",
            "resolvedCount": len(resolved),
            "anchors": resolved,
        }
        write_json(args.artifacts_dir / "anchor-resolution-report.json", anchor_report)
        import_report["totals"] = {
            "notes": inventory["totals"]["notes"],
            "cards": inventory["totals"]["cards"],
            "noteTypes": inventory["totals"]["noteTypes"],
            "decks": inventory["totals"]["decks"],
            "media": inventory["totals"]["media"],
        }
        write_json(args.artifacts_dir / "real-deck-import-report.json", import_report)
        log(f"resolved {len(resolved)} anchors uniquely")
        log("collection import ready")
        return 0
    except Exception as error:
        stage = getattr(error, "stage", "real-deck-import")
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


def reset_collection(collection_path: Path, media_dir: Path) -> None:
    for path in (
        collection_path,
        collection_path.with_suffix(".anki2-wal"),
        collection_path.with_suffix(".anki2-shm"),
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(media_dir, ignore_errors=True)
    media_dir.mkdir(parents=True, exist_ok=True)


def create_empty_collection(collection_path: Path) -> None:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    close_collection(col)


def import_package(collection_path: Path, package_path: Path) -> str:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    errors: list[str] = []
    try:
        try:
            from anki.importing.apkg import AnkiPackageImporter

            importer = AnkiPackageImporter(col, str(package_path))
            method = getattr(importer, "run", None)
            if not callable(method):
                raise RuntimeError("AnkiPackageImporter.run is unavailable")
            method()
            return "anki.importing.apkg.AnkiPackageImporter.run"
        except Exception as error:
            errors.append(f"AnkiPackageImporter.run: {type(error).__name__}: {error}")

        try:
            from anki import import_export_pb2

            backend = getattr(col, "_backend", None)
            method = getattr(backend, "import_anki_package", None)
            if not callable(method):
                raise RuntimeError("Collection backend import_anki_package is unavailable")
            options = import_export_pb2.ImportAnkiPackageOptions(
                merge_notetypes=True,
                update_notes=import_export_pb2.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                update_notetypes=import_export_pb2.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                with_scheduling=False,
                with_deck_configs=True,
            )
            method(package_path=str(package_path), options=options)
            return "Collection._backend.import_anki_package"
        except Exception as error:
            errors.append(f"Collection._backend.import_anki_package: {type(error).__name__}: {error}")
    finally:
        close_collection(col)
    raise RealDeckContractError(
        "Official Anki package import failed: " + " | ".join(errors),
        stage="package-import",
        subject_id=package_path.name,
    )


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
            "noteIds": {int(row[0]) for row in conn.execute("select id from notes")},
            "cardIds": {int(row[0]) for row in conn.execute("select id from cards")},
        }
    finally:
        conn.close()


def model_ids_for_notes(collection_path: Path, note_ids: Iterable[int]) -> set[int]:
    values = sorted({int(item) for item in note_ids})
    if not values:
        return set()
    conn = sqlite3.connect(collection_path)
    try:
        placeholders = ",".join("?" for _ in values)
        return {int(row[0]) for row in conn.execute(f"select distinct mid from notes where id in ({placeholders})", values)}
    finally:
        conn.close()


def deck_ids_for_cards(collection_path: Path, card_ids: Iterable[int]) -> set[int]:
    values = sorted({int(item) for item in card_ids})
    if not values:
        return set()
    conn = sqlite3.connect(collection_path)
    try:
        placeholders = ",".join("?" for _ in values)
        return {int(row[0]) for row in conn.execute(f"select distinct did from cards where id in ({placeholders})", values)}
    finally:
        conn.close()


def assert_expected_count(package_id: str, key: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise RealDeckContractError(
            f"Package {package_id} {key} mismatch: expected {expected}, got {actual}",
            stage="package-import",
            subject_id=package_id,
        )


def media_inventory(media_dir: Path) -> set[str]:
    if not media_dir.is_dir():
        return set()
    return {path.name for path in media_dir.iterdir() if path.is_file() and not path.name.startswith(".")}


def summarize_media(names: Iterable[str]) -> dict[str, Any]:
    suffix_counts: dict[str, int] = {}
    for name in names:
        suffix = Path(name).suffix.lower() or "<none>"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    return {"count": sum(suffix_counts.values()), "suffixCounts": dict(sorted(suffix_counts.items()))}


def read_collection_metadata(collection_path: Path) -> tuple[dict[int, dict[str, Any]], dict[int, str]]:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        raw_models = col.models.all()
        if isinstance(raw_models, dict):
            raw_models = list(raw_models.values())
        models = {
            int(model.get("id") or model.get("mid")): model
            for model in raw_models or []
            if isinstance(model, dict) and (model.get("id") or model.get("mid")) is not None
        }
        decks = {int(item.id): str(item.name) for item in col.decks.all_names_and_ids()}
        return models, decks
    finally:
        close_collection(col)


def build_inventory(
    collection_path: Path,
    media_dir: Path,
    *,
    models_by_id: dict[int, dict[str, Any]],
    deck_names_by_id: dict[int, str],
    package_note_ids: dict[str, set[int]],
    package_card_ids: dict[str, set[int]],
) -> dict[str, Any]:
    conn = sqlite3.connect(collection_path)
    try:
        note_ids = {int(row[0]) for row in conn.execute("select id from notes")}
        card_ids = {int(row[0]) for row in conn.execute("select id from cards")}
        used_model_ids = {int(row[0]) for row in conn.execute("select distinct mid from notes")}
        used_deck_ids = {int(row[0]) for row in conn.execute("select distinct did from cards")}
        revlog_count = int(conn.execute("select count(*) from revlog").fetchone()[0])
        note_types = []
        for model_id in sorted(used_model_ids):
            model = models_by_id.get(model_id)
            if not model:
                raise RealDeckContractError(
                    f"Used note type {model_id} is absent from Anki model manager.", stage="inventory", subject_id=str(model_id)
                )
            structure = model_structure(model)
            note_types.append(
                {
                    "noteTypeId": model_id,
                    "name": structure["name"],
                    "fingerprint": model_fingerprint(model),
                    "fields": structure["fields"],
                    "templates": structure["templates"],
                    "noteCount": int(conn.execute("select count(*) from notes where mid = ?", (model_id,)).fetchone()[0]),
                }
            )
        decks = [
            {
                "deckId": deck_id,
                "name": deck_names_by_id.get(deck_id, str(deck_id)),
                "cardCount": int(conn.execute("select count(*) from cards where did = ?", (deck_id,)).fetchone()[0]),
            }
            for deck_id in sorted(used_deck_ids)
        ]
        package_inventory = [
            {
                "id": package_id,
                "noteCount": len(package_note_ids[package_id]),
                "cardCount": len(package_card_ids.get(package_id, set())),
                "noteIds": sorted(package_note_ids[package_id]),
                "cardIds": sorted(package_card_ids.get(package_id, set())),
            }
            for package_id in package_note_ids
        ]
        media = sorted(media_inventory(media_dir))
        return {
            "schemaVersion": 1,
            "status": "PASS",
            "totals": {
                "notes": len(note_ids),
                "cards": len(card_ids),
                "noteTypes": len(used_model_ids),
                "decks": len(used_deck_ids),
                "media": len(media),
                "revlogRowsBeforeScenarios": revlog_count,
            },
            "packages": package_inventory,
            "noteTypes": note_types,
            "decks": decks,
            "media": summarize_media(media),
            "contentSource": "committed-real-apkg-only",
            "syntheticNotes": 0,
            "syntheticCards": 0,
            "syntheticMedia": 0,
        }
    finally:
        conn.close()


def assert_collection_content_is_imported_only(
    inventory: dict[str, Any],
    package_note_ids: dict[str, set[int]],
    package_card_ids: dict[str, set[int]],
) -> None:
    imported_notes = set().union(*package_note_ids.values()) if package_note_ids else set()
    imported_cards = set().union(*package_card_ids.values()) if package_card_ids else set()
    if len(imported_notes) != int(inventory["totals"]["notes"]):
        raise RealDeckContractError(
            "Collection contains notes that were not created by the three package imports.", stage="inventory"
        )
    if len(imported_cards) != int(inventory["totals"]["cards"]):
        raise RealDeckContractError(
            "Collection contains cards that were not created by the three package imports.", stage="inventory"
        )
    if int(inventory["totals"]["revlogRowsBeforeScenarios"]) != 0:
        raise RealDeckContractError("Imported collection unexpectedly contains revlog rows.", stage="inventory")


def prune_unused_metadata(collection_path: Path) -> None:
    from anki.collection import Collection

    col = Collection(str(collection_path))
    try:
        used_model_ids = {int(row[0]) for row in col.db.all("select distinct mid from notes")}
        raw_models = col.models.all()
        if isinstance(raw_models, dict):
            raw_models = list(raw_models.values())
        for model in list(raw_models or []):
            if not isinstance(model, dict):
                continue
            model_id = int(model.get("id") or model.get("mid") or 0)
            if model_id and model_id not in used_model_ids:
                call_model_remove(col.models, model_id, model)

        direct_deck_ids = {int(row[0]) for row in col.db.all("select distinct did from cards")}
        names = {int(item.id): str(item.name) for item in col.decks.all_names_and_ids()}
        keep_names = {names[deck_id] for deck_id in direct_deck_ids if deck_id in names}
        for name in list(keep_names):
            parts = name.split("::")
            keep_names.update("::".join(parts[:index]) for index in range(1, len(parts)))
        keep_ids = {deck_id for deck_id, name in names.items() if name in keep_names}
        for deck_id in [deck_id for deck_id in names if deck_id not in keep_ids]:
            call_deck_remove(col.decks, deck_id)
    finally:
        close_collection(col)


def call_model_remove(manager: Any, model_id: int, model: dict[str, Any]) -> None:
    errors = []
    for name in ("remove", "rem"):
        method = getattr(manager, name, None)
        if not callable(method):
            continue
        for argument in (model_id, model):
            try:
                method(argument)
                return
            except Exception as error:
                errors.append(f"{name}({type(argument).__name__}): {error}")
    raise RealDeckContractError(
        f"Could not remove unused bootstrap note type {model_id}: {' | '.join(errors)}",
        stage="metadata-prune",
        subject_id=str(model_id),
    )


def call_deck_remove(manager: Any, deck_id: int) -> None:
    errors = []
    for name in ("remove", "rem"):
        method = getattr(manager, name, None)
        if not callable(method):
            continue
        for positional in (([deck_id],), (deck_id,), (deck_id, False, False)):
            try:
                method(*positional)
                return
            except Exception as error:
                errors.append(f"{name}{positional}: {error}")
    raise RealDeckContractError(
        f"Could not remove unused bootstrap deck {deck_id}: {' | '.join(errors)}",
        stage="metadata-prune",
        subject_id=str(deck_id),
    )


if __name__ == "__main__":
    raise SystemExit(main())
