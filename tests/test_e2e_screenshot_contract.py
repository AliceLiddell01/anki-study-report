from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SMOKE_BROWSER = ROOT / "docker" / "anki-e2e" / "smoke-browser.mjs"
E2E_CONTRACT = ROOT / "docker" / "anki-e2e" / "e2e-contract.mjs"
DOCKER_RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"
ROUTER = ROOT / "web-dashboard" / "src" / "app" / "router.tsx"
RU_LOCALE = ROOT / "web-dashboard" / "src" / "i18n" / "locales" / "ru.ts"


def _page_names() -> list[str]:
    text = SMOKE_BROWSER.read_text(encoding="utf-8")
    block = text.split("const dashboardPageCases = [", 1)[1].split("];", 1)[0]
    return re.findall(r'pageName:\s*"([^"]+)"', block)


def _page_scopes() -> dict[str, str]:
    text = E2E_CONTRACT.read_text(encoding="utf-8")
    block = text.split("const PAGE_SCOPE = Object.freeze({", 1)[1].split("});", 1)[0]
    entries = re.findall(r'^\s*(?:"([^"]+)"|([A-Za-z][\w-]*)):\s*"([^"]+)",?\s*$', block, re.MULTILINE)
    return {(quoted or bare): scope for quoted, bare, scope in entries}


def _runner_expected_pages() -> dict[str, int]:
    text = DOCKER_RUNNER.read_text(encoding="utf-8")
    match = re.search(r'\$expectedPages\s*=\s*@\{([^}]+)\}\[\$scope\]', text)
    assert match, "PowerShell screenshot-count contract was not found"
    return {name: int(value) for name, value in re.findall(r'(\w+)\s*=\s*(\d+)', match.group(1))}


def test_manifest_page_counts_follow_the_capture_contract() -> None:
    page_names = _page_names()
    page_scopes = _page_scopes()
    expected = _runner_expected_pages()

    assert len(page_names) == len(set(page_names)), "dashboard page names must be unique"
    assert set(page_names) == set(page_scopes), "every dashboard page must have exactly one E2E scope"

    calculated = {
        scope: (len(page_names) if scope == "full" else sum(page_scopes[name] == scope for name in page_names)) * 2
        for scope in expected
    }
    assert expected == calculated


def _primary_nav_label_keys() -> list[str]:
    text = ROUTER.read_text(encoding="utf-8")
    block = text.split("export const primaryNavItems", 1)[1].split("];", 1)[0]
    return re.findall(r'labelKey:\s*"primary\.([^"]+)"', block)


def _ru_primary_nav_labels() -> dict[str, str]:
    text = RU_LOCALE.read_text(encoding="utf-8")
    navigation = text.split("navigation: {", 1)[1]
    block = navigation.split("primary: {", 1)[1].split("},", 1)[0]
    return dict(re.findall(r'^\s*(\w+):\s*"([^"]+)"', block, re.MULTILINE))


def _statistics_smoke_nav_labels() -> list[str]:
    text = SMOKE_BROWSER.read_text(encoding="utf-8")
    before_message = text.split("`Statistics primary navigation order is correct:", 1)[0]
    expected = before_message.rsplit("JSON.stringify(", 1)[1].split(")", 1)[0]
    return re.findall(r'"([^"]+)"', expected)


def test_statistics_smoke_navigation_follows_the_router_and_russian_locale() -> None:
    keys = _primary_nav_label_keys()
    labels = _ru_primary_nav_labels()

    assert keys
    assert "search" in keys
    assert all(key in labels for key in keys)
    assert _statistics_smoke_nav_labels() == [labels[key] for key in keys]
