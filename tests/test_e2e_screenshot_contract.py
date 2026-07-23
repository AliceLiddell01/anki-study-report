from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_BROWSER = ROOT / "docker" / "anki-e2e" / "smoke-browser.mjs"
BROWSER_PROGRESS = ROOT / "docker" / "anki-e2e" / "browser-progress.mjs"
DOCKER_RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"


def test_manifest_page_counts_follow_real_dashboard_capture_contract() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")
    progress = BROWSER_PROGRESS.read_text(encoding="utf-8")
    runner = DOCKER_RUNNER.read_text(encoding="utf-8")

    assert 'Object.freeze({ name: "home", route: "/home" })' in progress
    assert 'Object.freeze({ name: "cards", route: "/cards" })' in progress
    assert 'Object.freeze({ name: "decks", route: "/decks" })' in progress
    assert 'Object.freeze({ name: "profile", route: "/profile" })' in progress
    assert 'Object.freeze({ name: "settings", route: "/settings" })' in progress
    assert 'export const THEMES = Object.freeze(["light", "dark"])' in progress
    assert 'candidate.kind === "route-capture"' in smoke
    assert '$pageScreenshots.Count -ne 10' in runner
    assert 'Expected 10 real-dashboard page screenshots' in runner


def test_dashboard_route_capture_uses_structure_and_hash_not_transient_copy() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")

    assert 'page.locator("main").waitFor' in smoke
    assert "window.location.hash === hash" in smoke
    assert "e2eTheme" in smoke
    assert "page.addInitScript" in smoke
    assert "page.reload(" not in smoke
    assert 'getByRole("heading"' not in smoke
    for transient_heading in ("Сегодня", "Карточки", "Колоды"):
        assert transient_heading not in smoke


def test_theme_bootstrap_waits_for_the_document_root() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")

    assert "const root = document.documentElement;" in smoke
    assert "if (!root) return false;" in smoke
    assert 'document.addEventListener("DOMContentLoaded", applyTheme, { once: true });' in smoke
    assert "document.documentElement.dataset.theme = selectedTheme;" not in smoke


def test_cards_screenshot_counts_follow_real_deck_anchor_contract() -> None:
    smoke = SMOKE_BROWSER.read_text(encoding="utf-8")
    progress = BROWSER_PROGRESS.read_text(encoding="utf-8")
    runner = DOCKER_RUNNER.read_text(encoding="utf-8")

    assert 'export const PREVIEW_ANCHOR_IDS = Object.freeze(["words-preview", "grammar-preview", "java-preview"])' in progress
    assert 'expectedScreenshots: 2' in progress
    assert 'path.join(screenshotsDir, "cards", "real-decks", anchorId, `${theme}.png`)' in smoke
    assert 'path.join(screenshotsDir, "states", "cards", "real-deck-inbox", `${theme}.png`)' in smoke
    assert 'expectedScreenshotCount = items.reduce' in progress
    assert '$realDeckCards.Count -ne 6' in runner
    assert 'Expected 6 real-deck preview screenshots' in runner
    assert '$syntheticCards.Count -ne 0' in runner
    assert 'Synthetic/legacy APKG screenshots remain' in runner
    assert 'cardsScreenshot("synthetic"' not in smoke
    assert 'cardsScreenshot("apkg"' not in smoke
