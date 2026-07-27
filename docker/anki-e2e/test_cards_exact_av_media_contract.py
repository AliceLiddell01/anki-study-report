from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess

ROOT = Path(__file__).resolve().parents[2]
E2E = ROOT / "docker" / "anki-e2e"


def read(name: str) -> str:
    return (E2E / name).read_text(encoding="utf-8")


def test_exact_scope_is_integrated_into_canonical_contour_without_profiles() -> None:
    run = read("run-e2e.sh")
    api = read("cards-exact-av-media-api.py")
    assert "full|global|stats|decks|activity|cards|cards-exact-av-media|settings|notifications" in run
    assert '/e2e/bin/cards-exact-av-media-scenario.py' in run
    assert '/e2e/bin/cards-exact-av-media-api.py' in run
    assert '/e2e/bin/cards-exact-av-media-browser.mjs' in run
    assert '/e2e/bin/cards-exact-av-media-evidence.py' in run
    assert "/api/inspection-profiles/" not in api


def test_exact_browser_uses_page_clip_and_side_aware_media_contract() -> None:
    source = read("cards-exact-av-media-browser.mjs")
    assert "locator.screenshot" not in source
    assert 'page.screenshot({ path: outputPath, animations: "allow", caret: "hide", clip })' in source
    assert 'if (expectedSide === "front") return !imageNames.includes(config.png)' in source
    assert "return imageNames.includes(config.png)" in source
    assert "browserFramesDiffer" in source
    assert 'decoder.decode({ frameIndex: 0, completeFramesOnly: true })' in source
    assert 'window.__asrReplayProof?.playCalls >= 2' in source
    assert "rejectedPromiseHandled" in source
    assert "inspectionProfileRequests.length === 0" in source
    assert "externalRequests.length === 0" in source


def test_exact_host_runner_uses_strict_mounts_and_state_guards() -> None:
    source = read("run-cards-exact-av-media-host.sh")
    assert 'EXPECTED_BRANCH="c2-manual-acceptance-remediation"' in source
    assert "git status --porcelain=v1" in source
    assert "validate_e2e_harness_reuse.py" in source
    assert source.count('--mount "type=bind,source=') == 5
    assert "docker run -v" not in source
    assert "--volume" not in source
    assert "require_file" in source
    assert "require_dir" in source
    assert "Output path already exists and is not an empty directory" in source
    assert "Do not rerun." in source


def test_final_evidence_contract_is_self_verifying() -> None:
    source = read("cards-exact-av-media-evidence.py")
    for required in (
        "exact-scenario.json",
        "exact-api.json",
        "exact-browser.json",
        "targeted-run-summary.json",
        "environment.json",
        "page-console-summary.json",
        "request-ledger.json",
        "geometry-metrics.json",
        "manifest.json",
        "SHA256SUMS",
        "contact-sheet.png",
    ):
        assert required in source
    assert "missing" in source
    assert "unexpected" in source
    assert "mismatches" in source
    assert "archive.extractall(extraction)" in source
    assert 'FINAL_NAME = "cards-final-av-media-fidelity-evidence.zip"' in source


def test_new_harness_files_parse() -> None:
    for name in (
        "cards-exact-av-media-scenario.py",
        "cards-exact-av-media-api.py",
        "cards-exact-av-media-evidence.py",
        "cards-exact-av-media-failure.py",
    ):
        py_compile.compile(str(E2E / name), doraise=True)

    for name in (
        "cards-exact-av-media-browser.mjs",
    ):
        completed = subprocess.run(
            ["node", "--check", str(E2E / name)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout

    for name in (
        "cards-exact-av-media-entrypoint.sh",
        "run-cards-exact-av-media-host.sh",
        "run-e2e.sh",
    ):
        completed = subprocess.run(
            ["bash", "-n", str(E2E / name)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout
