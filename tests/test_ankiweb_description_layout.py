from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

import pytest

from conftest import ROOT


def load_modules():
    common_path = ROOT / "scripts" / "release_common.py"
    common_spec = importlib.util.spec_from_file_location("release_common", common_path)
    assert common_spec and common_spec.loader
    common = importlib.util.module_from_spec(common_spec)
    sys.modules[common_spec.name] = common
    common_spec.loader.exec_module(common)

    description_path = ROOT / "scripts" / "ankiweb_description.py"
    description_spec = importlib.util.spec_from_file_location("ankiweb_description", description_path)
    assert description_spec and description_spec.loader
    description = importlib.util.module_from_spec(description_spec)
    sys.modules[description_spec.name] = description
    description_spec.loader.exec_module(description)
    return common, description


def test_rendered_description_uses_product_first_layout_without_duplicate_h1() -> None:
    common, description_module = load_modules()
    version = common.read_version()
    rendered = description_module.render_ankiweb_description(version)
    notes = common.release_notes(version).rstrip()

    assert re.search(r"(?m)^#\s+", rendered) is None
    assert rendered.count(f"## What's new in {version}") == 1
    assert rendered.count("## New: Search your Anki collection") == 1
    assert rendered.count("https://boosty.to/ankistudyreport") == 1
    assert 'src="https://upload.wikimedia.org/wikipedia/commons/9/92/Boosty_logo.svg"' in rendered
    assert 'alt="Support the author on Boosty"' in rendered
    assert 'width="220"' in rendered
    assert "[Unreleased]" not in rendered

    intro = rendered.index("Anki Study Report turns your Anki review data")
    search = rendered.index("## New: Search your Anki collection")
    support = rendered.index("## Support the author")
    features = rendered.index("## Main features")
    privacy = rendered.index("## Privacy and safety")
    compatibility = rendered.index("## Compatibility and limitations")
    links = rendered.index("## Links and contact")
    changelog = rendered.index(f"## What's new in {version}")
    history = rendered.index("[Full release history]")

    assert intro < search < support < features < privacy < compatibility < links < changelog < history
    assert notes in rendered
    assert common.sha256_text(rendered) == common.sha256_text(rendered.replace("\n", "\r\n"))


def test_stable_description_rejects_level_one_headings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    common, description_module = load_modules()
    fixture = tmp_path / "ankiweb-description.md"
    fixture.write_text("# Anki Study Report\n\nProduct copy.\n", encoding="utf-8")
    monkeypatch.setattr(description_module, "ANKIWEB_DESCRIPTION_FILE", fixture)

    with pytest.raises(common.ReleaseError, match="level-one heading"):
        description_module.stable_ankiweb_description()


def test_release_entrypoints_use_the_canonical_description_composer() -> None:
    for relative in (
        "scripts/create_release_bundle.py",
        "scripts/render_ankiweb_description.py",
        "scripts/validate_release.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "from ankiweb_description import render_ankiweb_description" in source
