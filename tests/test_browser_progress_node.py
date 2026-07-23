from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
NODE_TEST = ROOT / "tests" / "browser_progress.test.mjs"
SMOKE = ROOT / "docker" / "anki-e2e" / "smoke-browser.mjs"
PROGRESS = ROOT / "docker" / "anki-e2e" / "browser-progress.mjs"


def test_browser_progress_node_contract() -> None:
    completed = subprocess.run(
        ["node", "--test", str(NODE_TEST)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_browser_progress_and_smoke_modules_have_valid_node_syntax() -> None:
    for path in (SMOKE, PROGRESS):
        completed = subprocess.run(
            ["node", "--check", str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_direct_playwright_and_safe_run_event_adapter_are_preserved() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    progress = PROGRESS.read_text(encoding="utf-8")

    assert 'from "playwright"' in smoke
    assert "@playwright/test" not in smoke
    assert "@playwright/test" not in progress
    assert "retry" not in progress.lower()
    assert 'import { execFile } from "node:child_process"' in progress
    assert '"--phase-id", "browser-smoke-first"' in progress
    assert '"--event-kind", "message"' in progress
    assert '"--status", "info"' in progress
    assert "shell: false" in progress


def test_plan_is_built_and_printed_before_chromium_launch() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")

    plan = smoke.index("const plan = buildBrowserPlan")
    print_plan = smoke.index("progress.printPlan()")
    launch = smoke.index('progress.run("browser.launch"')
    chromium = smoke.index("chromium.launch")
    assert plan < print_plan < launch <= chromium


def test_existing_browser_diagnostics_and_wait_contract_are_preserved() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")

    for token in (
        'page.on("console"',
        'page.on("pageerror"',
        'page.on("requestfailed"',
        'page.on("request"',
        'waitUntil: "networkidle"',
        'consoleEvents.filter((event) => event.type === "error")',
        '!item.url.includes("favicon")',
        "unexpectedExternalRequests",
    ):
        assert token in smoke
