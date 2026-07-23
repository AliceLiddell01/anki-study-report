from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "docker" / "anki-e2e"
sys.path.insert(0, str(E2E))

from real_deck_contract import (  # noqa: E402
    FINGERPRINT_ALGORITHM,
    RealDeckContractError,
    extract_media_references,
    model_fingerprint,
    resolve_anchors,
    select_distinct_cards,
    validate_manifest,
    validate_packages,
)


def package(package_id: str, path: str, sha256: str = "0" * 64, size: int = 1) -> dict:
    return {
        "id": package_id,
        "path": path,
        "sha256": sha256,
        "sizeBytes": size,
        "purpose": package_id,
        "expected": {"notes": 1, "cards": 1, "noteTypes": 1, "media": 0, "hasSchedulingData": False},
    }


def anchor(package_id: str = "words", guid: str = "guid", ordinal: int = 0) -> dict:
    return {
        "purpose": "test",
        "package": package_id,
        "selector": {"kind": "noteGuidTemplate", "noteGuid": guid, "templateOrdinal": ordinal},
        "expectedNoteType": {
            "name": "Words",
            "fingerprint": model_fingerprint(model()),
            "fieldNames": ["Front", "Back"],
        },
        "requiredMediaCapabilities": [],
        "allowedScenarioMutations": [],
    }


def manifest(packages: list[dict] | None = None, anchors: dict | None = None) -> dict:
    return {
        "schemaVersion": 1,
        "fingerprintAlgorithm": FINGERPRINT_ALGORITHM,
        "packages": packages or [package("words", "words.apkg")],
        "anchors": anchors or {"words-preview": anchor()},
    }


def model() -> dict:
    return {
        "id": 10,
        "name": "Words",
        "flds": [{"ord": 0, "name": "Front"}, {"ord": 1, "name": "Back"}],
        "tmpls": [{"ord": 0, "name": "Card 1"}],
    }


def collection_db(path: Path, *, duplicate: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        create table notes (id integer primary key, guid text, mid integer, flds text);
        create table cards (id integer primary key, nid integer, did integer, ord integer);
        """
    )
    conn.execute("insert into notes values (1, 'guid', 10, 'front\x1fback')")
    conn.execute("insert into cards values (11, 1, 20, 0)")
    if duplicate:
        conn.execute("insert into cards values (12, 1, 20, 0)")
    conn.commit()
    return conn


def test_manifest_rejects_duplicate_package_id(tmp_path: Path) -> None:
    value = manifest([package("words", "words.apkg"), package("words", "grammar.apkg")])
    with pytest.raises(RealDeckContractError, match="Duplicate package id"):
        validate_manifest(value, tmp_path)


def test_manifest_rejects_missing_package(tmp_path: Path) -> None:
    normalized = validate_manifest(manifest(), tmp_path)
    with pytest.raises(RealDeckContractError, match="Package is missing"):
        validate_packages(normalized)


def test_checksum_mismatch_is_hard_failure(tmp_path: Path) -> None:
    fixture = tmp_path / "words.apkg"
    fixture.write_bytes(b"real")
    value = manifest([package("words", "words.apkg", sha256="0" * 64, size=4)])
    normalized = validate_manifest(value, tmp_path)
    with pytest.raises(RealDeckContractError, match="checksum mismatch"):
        validate_packages(normalized)


def test_dynamic_media_extraction_is_content_agnostic() -> None:
    refs = extract_media_references(
        [
            '[sound:any-name.mp3]<img src="picture.gif"><img src="photo.png">',
            '<audio src="clip.ogg"></audio><img src="https://example.invalid/remote.png">',
            '<img src="../escape.png"><img src="file:///tmp/secret.png">',
        ]
    )
    assert refs == [
        {"name": "any-name.mp3", "capability": "audio"},
        {"name": "clip.ogg", "capability": "audio"},
        {"name": "photo.png", "capability": "image"},
        {"name": "picture.gif", "capability": "gif"},
    ]


def test_anchor_resolution_is_unique_and_deterministic(tmp_path: Path) -> None:
    conn = collection_db(tmp_path / "collection.anki2")
    try:
        first = resolve_anchors(
            conn,
            manifest(),
            package_note_ids={"words": {1}},
            models_by_id={10: model()},
            deck_names_by_id={20: "Deck"},
            media_dir=tmp_path,
        )
        second = resolve_anchors(
            conn,
            manifest(),
            package_note_ids={"words": {1}},
            models_by_id={10: model()},
            deck_names_by_id={20: "Deck"},
            media_dir=tmp_path,
        )
    finally:
        conn.close()
    assert first == second
    assert first["words-preview"]["cardId"] == 11


def test_anchor_resolution_fails_when_missing(tmp_path: Path) -> None:
    conn = collection_db(tmp_path / "collection.anki2")
    try:
        value = manifest(anchors={"missing": anchor(guid="absent")})
        with pytest.raises(RealDeckContractError, match="missing"):
            resolve_anchors(
                conn,
                value,
                package_note_ids={"words": {1}},
                models_by_id={10: model()},
                deck_names_by_id={20: "Deck"},
                media_dir=tmp_path,
            )
    finally:
        conn.close()


def test_anchor_resolution_fails_when_ambiguous(tmp_path: Path) -> None:
    conn = collection_db(tmp_path / "collection.anki2", duplicate=True)
    try:
        with pytest.raises(RealDeckContractError, match="ambiguous"):
            resolve_anchors(
                conn,
                manifest(),
                package_note_ids={"words": {1}},
                models_by_id={10: model()},
                deck_names_by_id={20: "Deck"},
                media_dir=tmp_path,
            )
    finally:
        conn.close()


def test_perf100_selects_100_distinct_existing_cards() -> None:
    selected = select_distinct_cards(
        {"words": range(1, 80), "grammar": range(60, 130), "java": range(200, 210)},
        ["words", "grammar", "java"],
        100,
    )
    assert len(selected) == 100
    assert len(set(selected)) == 100
    assert set(selected) <= (set(range(1, 80)) | set(range(60, 130)) | set(range(200, 210)))


def test_perf100_hard_fails_below_target() -> None:
    with pytest.raises(RealDeckContractError, match="distinct imported cards"):
        select_distinct_cards({"words": [1, 2, 2], "grammar": [2, 3]}, ["words", "grammar"], 100)


def test_generic_scripts_have_no_content_creation_or_fixture_hardcoding() -> None:
    scripts = [
        (E2E / "real_deck_contract.py").read_text(encoding="utf-8"),
        (E2E / "prepare-real-decks.py").read_text(encoding="utf-8"),
        (E2E / "apply-real-deck-scenarios.py").read_text(encoding="utf-8"),
    ]
    joined = "\n".join(scripts)
    forbidden_literals = [
        "要望",
        "要.gif",
        "E2E Japanese Vocabulary",
        "E2E Programming",
        "asr-e2e-render-fixtures.apkg",
    ]
    assert not any(value in joined for value in forbidden_literals)
    lowered = joined.lower()
    assert "insert into notes" not in lowered
    assert "insert into cards" not in lowered
    assert "clone_imported_cards" not in lowered
    assert "synthetic fixture" not in lowered
    assert "AnkiPackageImporter" not in joined
    assert "_backend.import_anki_package" not in joined
    assert "Collection.import_anki_package" in joined


def test_entrypoints_have_no_external_apkg_mode() -> None:
    compose = (E2E / "docker-compose.yml").read_text(encoding="utf-8")
    importer = (E2E / "import-apkg-fixture.py").read_text(encoding="utf-8")
    runner = (ROOT / "scripts" / "run_anki_e2e_docker.ps1").read_text(encoding="utf-8")
    full_check = (ROOT / "scripts" / "run_full_check.ps1").read_text(encoding="utf-8")
    joined = "\n".join((compose, importer, runner))
    for legacy in ("ANKI_E2E_APKG_FIXTURE_PATH", "ANKI_E2E_REQUIRE_APKG_FIXTURE", "ApkgFixture"):
        assert legacy not in joined
    assert "fixtures/real-decks" in importer
    assert "[switch]$RequireApkgFixture" in full_check
    assert "Compatibility input RequireApkgFixture accepted" in full_check
    assert "ANKI_E2E_APKG_FIXTURE_PATH" not in full_check
    assert "ANKI_E2E_REQUIRE_APKG_FIXTURE" not in full_check


def test_failure_reports_include_required_diagnostics_contract() -> None:
    source = (E2E / "prepare-real-decks.py").read_text(encoding="utf-8")
    for key in ("stage", "subjectId", "error", "traceback", "lastCompletedStep"):
        assert f'"{key}"' in source
