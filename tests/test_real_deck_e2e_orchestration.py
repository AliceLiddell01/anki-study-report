from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "docker" / "anki-e2e"


def test_run_e2e_uses_mandatory_real_deck_stages() -> None:
    source = (E2E / "run-e2e.sh").read_text(encoding="utf-8")
    required_order = [
        "/e2e/bin/seed-collection.py",
        "/e2e/bin/import-apkg-fixture.py",
        "/e2e/bin/mark-apkg-cards-problematic.py",
        "/e2e/bin/install-addon.sh",
        "/e2e/bin/start-anki.sh first",
        "/e2e/bin/smoke-api.py --label first",
        "/e2e/bin/smoke-browser.mjs --label first",
    ]
    positions = [source.index(value) for value in required_order]
    assert positions == sorted(positions)
    assert "real deck checksum import inventory and anchors" in source
    assert "real card scenario preparation" in source


def test_run_e2e_has_no_legacy_apkg_switch_or_fallback() -> None:
    source = (E2E / "run-e2e.sh").read_text(encoding="utf-8")
    forbidden = [
        "ANKI_E2E_REQUIRE_APKG_FIXTURE",
        "ANKI_E2E_APKG_FIXTURE_PATH",
        "strict-apkg",
        "local-input",
        "asr-e2e-render-fixtures.apkg",
    ]
    for value in forbidden:
        assert value not in source


def test_dockerfile_copies_generic_real_deck_scripts() -> None:
    source = (E2E / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY docker/anki-e2e/*.py /e2e/bin/" in source
    assert "COPY docker/anki-e2e/*.mjs /e2e/bin/" in source
    assert "COPY docker/anki-e2e/run-e2e.sh /e2e/bin/run-e2e.sh" in source


def test_browser_and_api_smoke_read_runtime_anchor_report() -> None:
    api = (E2E / "smoke-api.py").read_text(encoding="utf-8")
    browser = (E2E / "smoke-browser.mjs").read_text(encoding="utf-8")
    assert "anchor-resolution-report.json" in api
    assert "anchor-resolution-report.json" in browser
    for fixture_literal in ("要望", "要.gif", "E2E Japanese Vocabulary", "asr-e2e-render-fixtures.apkg"):
        assert fixture_literal not in api
        assert fixture_literal not in browser
