#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping

FIELD_SEPARATOR = "\x1f"
MANIFEST_SCHEMA_VERSION = 1
FINGERPRINT_ALGORITHM = "asr-note-type-structure-v1"
ALLOWED_MUTATIONS = {"scheduling", "revlog", "suspended", "buried"}
REMOTE_OR_UNSAFE_PREFIXES = ("http://", "https://", "data:", "file://", "javascript:")
AUDIO_SUFFIXES = {".mp3", ".ogg", ".oga", ".wav", ".m4a", ".aac", ".flac"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".avif"}

_SOUND_RE = re.compile(r"\[sound:([^\]\r\n]+)\]", flags=re.IGNORECASE)
_SRC_RE = re.compile(
    r"<(?:img|audio|source|video)\b[^>]*?\bsrc\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))",
    flags=re.IGNORECASE,
)
_CLASS_RE = re.compile(r"\bclass\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", flags=re.IGNORECASE)


class RealDeckContractError(RuntimeError):
    def __init__(self, message: str, *, stage: str, subject_id: str = "") -> None:
        super().__init__(message)
        self.stage = stage
        self.subject_id = subject_id


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RealDeckContractError(f"Manifest is missing: {path}", stage="manifest") from error
    except json.JSONDecodeError as error:
        raise RealDeckContractError(f"Manifest JSON is invalid: {error}", stage="manifest") from error
    if not isinstance(value, dict):
        raise RealDeckContractError("Manifest root must be an object.", stage="manifest")
    return value


def validate_manifest(manifest: Mapping[str, Any], fixture_dir: Path) -> list[dict[str, Any]]:
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise RealDeckContractError(
            f"Unsupported manifest schemaVersion: {manifest.get('schemaVersion')!r}",
            stage="manifest",
        )
    algorithm = str(manifest.get("fingerprintAlgorithm") or "")
    if algorithm != FINGERPRINT_ALGORITHM:
        raise RealDeckContractError(
            f"Unsupported fingerprintAlgorithm: {algorithm!r}",
            stage="manifest",
        )

    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        raise RealDeckContractError("Manifest packages must be a non-empty array.", stage="manifest")

    normalized: list[dict[str, Any]] = []
    package_ids: set[str] = set()
    package_paths: set[str] = set()
    for index, raw in enumerate(packages):
        if not isinstance(raw, dict):
            raise RealDeckContractError(f"Package #{index + 1} must be an object.", stage="manifest")
        package_id = str(raw.get("id") or "").strip()
        relative_path = str(raw.get("path") or "").strip()
        sha256 = str(raw.get("sha256") or "").strip().lower()
        if not package_id:
            raise RealDeckContractError(f"Package #{index + 1} has no id.", stage="manifest")
        if package_id in package_ids:
            raise RealDeckContractError(f"Duplicate package id: {package_id}", stage="manifest", subject_id=package_id)
        if not relative_path:
            raise RealDeckContractError(f"Package {package_id} has no path.", stage="manifest", subject_id=package_id)
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.suffix.lower() != ".apkg":
            raise RealDeckContractError(
                f"Package {package_id} path must be a safe relative .apkg path: {relative_path}",
                stage="manifest",
                subject_id=package_id,
            )
        normalized_path = candidate.as_posix()
        if normalized_path in package_paths:
            raise RealDeckContractError(
                f"Duplicate package path: {normalized_path}", stage="manifest", subject_id=package_id
            )
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise RealDeckContractError(
                f"Package {package_id} has an invalid SHA-256.", stage="manifest", subject_id=package_id
            )
        expected = raw.get("expected")
        if not isinstance(expected, dict):
            raise RealDeckContractError(
                f"Package {package_id} has no expected inventory.", stage="manifest", subject_id=package_id
            )
        full_path = (fixture_dir / candidate).resolve()
        try:
            full_path.relative_to(fixture_dir.resolve())
        except ValueError as error:
            raise RealDeckContractError(
                f"Package {package_id} escapes fixture directory.", stage="manifest", subject_id=package_id
            ) from error
        normalized.append({**raw, "id": package_id, "path": normalized_path, "sha256": sha256, "fullPath": full_path})
        package_ids.add(package_id)
        package_paths.add(normalized_path)

    anchors = manifest.get("anchors")
    if not isinstance(anchors, dict) or not anchors:
        raise RealDeckContractError("Manifest anchors must be a non-empty object.", stage="manifest")
    for anchor_id, raw in anchors.items():
        if not isinstance(raw, dict):
            raise RealDeckContractError(f"Anchor {anchor_id} must be an object.", stage="manifest", subject_id=str(anchor_id))
        package_id = str(raw.get("package") or "")
        if package_id not in package_ids:
            raise RealDeckContractError(
                f"Anchor {anchor_id} references unknown package {package_id!r}.",
                stage="manifest",
                subject_id=str(anchor_id),
            )
        selector = raw.get("selector")
        if not isinstance(selector, dict) or selector.get("kind") != "noteGuidTemplate":
            raise RealDeckContractError(
                f"Anchor {anchor_id} must use noteGuidTemplate selector.", stage="manifest", subject_id=str(anchor_id)
            )
        if not str(selector.get("noteGuid") or ""):
            raise RealDeckContractError(f"Anchor {anchor_id} has no noteGuid.", stage="manifest", subject_id=str(anchor_id))
        ordinal = selector.get("templateOrdinal")
        if not isinstance(ordinal, int) or ordinal < 0:
            raise RealDeckContractError(
                f"Anchor {anchor_id} has invalid templateOrdinal.", stage="manifest", subject_id=str(anchor_id)
            )
        mutations = raw.get("allowedScenarioMutations") or []
        if not isinstance(mutations, list) or any(str(item) not in ALLOWED_MUTATIONS for item in mutations):
            raise RealDeckContractError(
                f"Anchor {anchor_id} declares unsupported scenario mutations.",
                stage="manifest",
                subject_id=str(anchor_id),
            )
    return normalized


def validate_packages(packages: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for package in packages:
        package_id = str(package["id"])
        path = Path(package["fullPath"])
        if not path.is_file():
            raise RealDeckContractError(f"Package is missing: {path.name}", stage="checksum", subject_id=package_id)
        actual_size = path.stat().st_size
        expected_size = int(package.get("sizeBytes") or 0)
        if expected_size and actual_size != expected_size:
            raise RealDeckContractError(
                f"Package {package_id} size mismatch: expected {expected_size}, got {actual_size}",
                stage="checksum",
                subject_id=package_id,
            )
        actual_sha = sha256_file(path)
        if actual_sha != package["sha256"]:
            raise RealDeckContractError(
                f"Package {package_id} checksum mismatch: expected {package['sha256']}, got {actual_sha}",
                stage="checksum",
                subject_id=package_id,
            )
        reports.append(
            {
                "id": package_id,
                "path": package["path"],
                "sizeBytes": actual_size,
                "sha256": actual_sha,
                "status": "PASS",
            }
        )
    return reports


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_structure(model: Mapping[str, Any]) -> dict[str, Any]:
    fields = sorted(
        (
            {"ord": int(field.get("ord", index)), "name": str(field.get("name") or "")}
            for index, field in enumerate(model.get("flds") or [])
            if isinstance(field, dict)
        ),
        key=lambda item: (item["ord"], item["name"]),
    )
    templates = sorted(
        (
            {"ord": int(template.get("ord", index)), "name": str(template.get("name") or "")}
            for index, template in enumerate(model.get("tmpls") or [])
            if isinstance(template, dict)
        ),
        key=lambda item: (item["ord"], item["name"]),
    )
    return {
        "schemaVersion": 1,
        "name": str(model.get("name") or ""),
        "fields": fields,
        "templates": templates,
    }


def model_fingerprint(model: Mapping[str, Any]) -> str:
    payload = json.dumps(
        model_structure(model), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def extract_media_references(values: Iterable[str]) -> list[dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for value in values:
        text = str(value or "")
        for match in _SOUND_RE.finditer(text):
            add_media_reference(result, match.group(1), "audio")
        for match in _SRC_RE.finditer(text):
            raw = next((group for group in match.groups() if group), "")
            add_media_reference(result, raw, classify_media(raw))
    return [result[name] for name in sorted(result)]


def add_media_reference(target: dict[str, dict[str, str]], raw_name: str, hinted: str) -> None:
    name = str(raw_name or "").strip().replace("&amp;", "&")
    lowered = name.lower()
    if not name or lowered.startswith(REMOTE_OR_UNSAFE_PREFIXES):
        return
    if name.startswith("/") or "\\" in name or ".." in Path(name).parts:
        return
    name = name.split("?", 1)[0].split("#", 1)[0]
    if not name:
        return
    target[name] = {"name": name, "capability": hinted or classify_media(name)}


def classify_media(name: str) -> str:
    suffix = Path(str(name)).suffix.lower()
    if suffix == ".gif":
        return "gif"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "other"


def html_classes(values: Iterable[str]) -> set[str]:
    classes: set[str] = set()
    for value in values:
        for match in _CLASS_RE.finditer(str(value or "")):
            raw = match.group(1) or match.group(2) or ""
            classes.update(item for item in raw.split() if item)
    return classes


def resolve_anchors(
    conn: sqlite3.Connection,
    manifest: Mapping[str, Any],
    *,
    package_note_ids: Mapping[str, set[int]],
    models_by_id: Mapping[int, Mapping[str, Any]],
    deck_names_by_id: Mapping[int, str],
    media_dir: Path,
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    anchors = manifest.get("anchors") or {}
    for anchor_id in sorted(anchors):
        raw = anchors[anchor_id]
        selector = raw["selector"]
        rows = conn.execute(
            """
            select c.id, c.nid, c.did, c.ord, n.guid, n.mid, n.flds
            from cards c
            join notes n on n.id = c.nid
            where n.guid = ? and c.ord = ?
            order by c.id
            """,
            (selector["noteGuid"], int(selector["templateOrdinal"])),
        ).fetchall()
        if len(rows) != 1:
            reason = "missing" if not rows else "ambiguous"
            raise RealDeckContractError(
                f"Anchor {anchor_id} is {reason}: resolved {len(rows)} cards.",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        card_id, note_id, deck_id, ordinal, note_guid, model_id, fields_blob = rows[0]
        package_id = str(raw["package"])
        if int(note_id) not in package_note_ids.get(package_id, set()):
            raise RealDeckContractError(
                f"Anchor {anchor_id} resolved outside package {package_id}.",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        model = models_by_id.get(int(model_id))
        if not model:
            raise RealDeckContractError(
                f"Anchor {anchor_id} note type {model_id} is missing.",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        structure = model_structure(model)
        actual_fingerprint = model_fingerprint(model)
        expected_type = raw.get("expectedNoteType") if isinstance(raw.get("expectedNoteType"), dict) else {}
        expected_name = str(expected_type.get("name") or "")
        expected_fingerprint = str(
            expected_type.get("fingerprint") or raw.get("expectedNoteTypeFingerprint") or ""
        )
        expected_fields = [str(item) for item in expected_type.get("fieldNames") or []]
        actual_fields = [item["name"] for item in structure["fields"]]
        if expected_name and structure["name"] != expected_name:
            raise RealDeckContractError(
                f"Anchor {anchor_id} note type name mismatch.", stage="anchor-resolution", subject_id=str(anchor_id)
            )
        if expected_fingerprint and actual_fingerprint != expected_fingerprint:
            raise RealDeckContractError(
                f"Anchor {anchor_id} note type fingerprint mismatch.",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        if expected_fields and actual_fields != expected_fields:
            raise RealDeckContractError(
                f"Anchor {anchor_id} field list mismatch.", stage="anchor-resolution", subject_id=str(anchor_id)
            )
        template_ordinals = {item["ord"] for item in structure["templates"]}
        if int(ordinal) not in template_ordinals:
            raise RealDeckContractError(
                f"Anchor {anchor_id} template ordinal {ordinal} is not present.",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        fields = str(fields_blob or "").split(FIELD_SEPARATOR)
        media_refs = extract_media_references(fields)
        missing_media = [item["name"] for item in media_refs if not (media_dir / item["name"]).is_file()]
        if missing_media:
            raise RealDeckContractError(
                f"Anchor {anchor_id} references missing media: {', '.join(missing_media[:5])}",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        capabilities = {item["capability"] for item in media_refs}
        required_capabilities = {str(item) for item in raw.get("requiredMediaCapabilities") or []}
        if not required_capabilities.issubset(capabilities):
            missing = sorted(required_capabilities - capabilities)
            raise RealDeckContractError(
                f"Anchor {anchor_id} lacks media capabilities: {', '.join(missing)}",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        required_classes = {str(item) for item in raw.get("requiredHtmlClasses") or []}
        actual_classes = html_classes(fields)
        if not required_classes.issubset(actual_classes):
            missing = sorted(required_classes - actual_classes)
            raise RealDeckContractError(
                f"Anchor {anchor_id} lacks HTML classes: {', '.join(missing)}",
                stage="anchor-resolution",
                subject_id=str(anchor_id),
            )
        resolved[str(anchor_id)] = {
            "status": "PASS",
            "package": package_id,
            "purpose": str(raw.get("purpose") or ""),
            "selector": {"kind": "noteGuidTemplate", "noteGuid": str(note_guid), "templateOrdinal": int(ordinal)},
            "cardId": int(card_id),
            "noteId": int(note_id),
            "deckId": int(deck_id),
            "deckName": str(deck_names_by_id.get(int(deck_id), deck_id)),
            "noteTypeId": int(model_id),
            "noteTypeName": structure["name"],
            "noteTypeFingerprint": actual_fingerprint,
            "fieldNames": actual_fields,
            "templateName": next(
                (item["name"] for item in structure["templates"] if item["ord"] == int(ordinal)), ""
            ),
            "mediaReferences": media_refs,
            "htmlClasses": sorted(required_classes),
            "allowedScenarioMutations": [str(item) for item in raw.get("allowedScenarioMutations") or []],
        }
    return resolved


def select_distinct_cards(package_cards: Mapping[str, Iterable[int]], package_order: Iterable[str], count: int) -> list[int]:
    if count <= 0:
        raise RealDeckContractError("Requested card count must be positive.", stage="scenario")
    selected: list[int] = []
    seen: set[int] = set()
    for package_id in package_order:
        for raw in package_cards.get(package_id, []):
            card_id = int(raw)
            if card_id in seen:
                continue
            selected.append(card_id)
            seen.add(card_id)
            if len(selected) == count:
                return selected
    raise RealDeckContractError(
        f"Only {len(selected)} distinct imported cards are available; {count} required.", stage="scenario", subject_id="perf100"
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
