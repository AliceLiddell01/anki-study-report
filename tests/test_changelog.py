from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest

from conftest import ROOT


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_canonical_changelog_migrates_existing_releases_with_locale_parity():
    changelog = load_script("changelog")

    document = changelog.load_changelog_document()
    versions = [release["version"] for release in document["releases"]]
    version_match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
        changelog.CANONICAL_VERSION_FILE.read_text(encoding="utf-8-sig"),
        re.MULTILINE,
    )

    assert version_match
    assert versions[0] == version_match.group(1)
    assert versions == sorted(versions, key=changelog.semver_key, reverse=True)
    assert {"1.1.0", "1.0.0"}.issubset(versions)
    assert {
        item["id"]
        for release in document["releases"]
        for section in release["sections"]
        for item in section["items"]
    }
    for release in document["releases"]:
        for section in release["sections"]:
            for item in section["items"]:
                assert set(item["text"]) == {"ru", "en"}
                assert all(item["text"][locale].strip() for locale in ("ru", "en"))


def test_structured_changelog_rejects_duplicate_versions_ids_and_bad_order():
    changelog = load_script("changelog")
    document = changelog.load_changelog_document()

    duplicate_version = deepcopy(document)
    duplicate_version["releases"].append(deepcopy(document["releases"][0]))
    with pytest.raises(changelog.ChangelogError, match="Duplicate changelog version"):
        changelog.validate_changelog_document(duplicate_version)

    duplicate_id = deepcopy(document)
    duplicate_id["releases"][1]["sections"][0]["items"][0]["id"] = duplicate_id["releases"][0]["sections"][0]["items"][0]["id"]
    with pytest.raises(changelog.ChangelogError, match="Duplicate changelog item ID"):
        changelog.validate_changelog_document(duplicate_id)

    bad_order = deepcopy(document)
    bad_order["releases"].reverse()
    with pytest.raises(changelog.ChangelogError, match="newest-first"):
        changelog.validate_changelog_document(bad_order)


def test_generated_changelog_outputs_are_deterministic_and_current():
    changelog = load_script("changelog")
    document = changelog.load_changelog_document()

    first = changelog.expected_outputs(document)
    second = changelog.expected_outputs(deepcopy(document))

    assert first == second
    assert first[changelog.MARKDOWN_CHANGELOG_FILE] == changelog.MARKDOWN_CHANGELOG_FILE.read_text(encoding="utf-8")
    assert first[changelog.ADDON_CHANGELOG_FILE] == changelog.ADDON_CHANGELOG_FILE.read_text(encoding="utf-8")
    assert first[changelog.FRONTEND_CHANGELOG_FILE] == changelog.FRONTEND_CHANGELOG_FILE.read_text(encoding="utf-8")
    assert changelog.generate_outputs(check=True) == []


def test_release_preparation_moves_unreleased_items_in_structured_source(monkeypatch, tmp_path: Path):
    changelog = load_script("changelog")
    load_script("release_common")
    prepare_release = load_script("prepare_release")
    document = changelog.load_changelog_document()
    current_version = document["releases"][0]["version"]
    major, minor, _patch = (int(part) for part in current_version.split("."))
    target_version = f"{major}.{minor + 1}.0"
    document["unreleased"] = {
        "sections": [{
            "type": "added",
            "items": [{
                "id": "future_release_fixture",
                "text": {"ru": "Добавлен тестовый пункт.", "en": "Added a fixture item."},
            }],
        }],
    }
    structured_path = tmp_path / "changelog.json"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"mod": 1}\n', encoding="utf-8")
    generated: list[dict] = []
    written_versions: list[str] = []

    monkeypatch.setattr(prepare_release, "read_version", lambda: current_version)
    monkeypatch.setattr(prepare_release, "ensure_new_tag", lambda version: None)
    monkeypatch.setattr(prepare_release, "load_changelog_document", lambda: deepcopy(document))
    monkeypatch.setattr(
        prepare_release,
        "parse_changelog",
        lambda: {
            "Unreleased": object(),
            **{release["version"]: object() for release in document["releases"]},
        },
    )
    monkeypatch.setattr(prepare_release, "write_version", written_versions.append)
    monkeypatch.setattr(prepare_release, "STRUCTURED_CHANGELOG_FILE", structured_path)
    monkeypatch.setattr(prepare_release, "MANIFEST_FILE", manifest_path)
    monkeypatch.setattr(
        prepare_release,
        "generate_outputs",
        lambda: generated.append(json.loads(structured_path.read_text(encoding="utf-8"))),
    )
    monkeypatch.setattr(prepare_release, "prepared_state", lambda version: None)

    changed = prepare_release.prepare(target_version, "2026-07-19", 1_784_419_200, dry_run=False)

    prepared = json.loads(structured_path.read_text(encoding="utf-8"))
    assert prepared["unreleased"] == {"sections": []}
    assert prepared["releases"][0]["version"] == target_version
    assert prepared["releases"][0]["sections"][0]["items"][0]["id"] == "future_release_fixture"
    assert generated == [prepared]
    assert written_versions == [target_version]
    assert "release/changelog.json" in changed
