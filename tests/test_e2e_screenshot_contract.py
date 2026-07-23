from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SMOKE_BROWSER = ROOT / "docker" / "anki-e2e" / "smoke-browser.mjs"
DOCKER_RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"


def test_manifest_page_counts_follow_real_dashboard_capture_contract() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")
    runner = DOCKER_RUNNER.read_text(encoding="utf-8")
    block = smoke.split("const cases = [", 1)[1].split("];", 1)[0]
    cases = re.findall(r'\["([^"]+)",\s*"([^"]+)"', block)

    assert cases == [
        ("home", "/home"),
        ("cards", "/cards"),
        ("decks", "/decks"),
        ("profile", "/profile"),
        ("settings", "/settings"),
    ]
    assert 'for (const theme of ["light", "dark"])' in smoke
    assert '$pageScreenshots.Count -ne 10' in runner
    assert 'Expected 10 real-dashboard page screenshots' in runner


def test_cards_screenshot_counts_follow_real_deck_anchor_contract() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")
    runner = DOCKER_RUNNER.read_text(encoding="utf-8")

    assert 'const previewAnchorIds = ["words-preview", "grammar-preview", "java-preview"]' in smoke
    assert 'path.join(screenshotsDir, "cards", "real-decks", anchorId, `${theme}.png`)' in smoke
    assert 'path.join(screenshotsDir, "states", "cards", "real-deck-inbox", `${theme}.png`)' in smoke
    assert '$realDeckCards.Count -ne 6' in runner
    assert 'Expected 6 real-deck preview screenshots' in runner
    assert '$syntheticCards.Count -ne 0' in runner
    assert 'Synthetic/legacy APKG screenshots remain' in runner
    assert 'cardsScreenshot("synthetic"' not in smoke
    assert 'cardsScreenshot("apkg"' not in smoke
