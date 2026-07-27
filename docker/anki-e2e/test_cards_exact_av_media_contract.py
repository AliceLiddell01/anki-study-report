from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import py_compile
import subprocess

ROOT = Path(__file__).resolve().parents[2]
E2E = ROOT / "docker" / "anki-e2e"


def read(name: str) -> str:
    return (E2E / name).read_text(encoding="utf-8")


def load_python(name: str):
    path = E2E / name
    spec = importlib.util.spec_from_file_location(
        f"asr_test_{path.stem.replace('-', '_')}",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_scope_is_integrated_into_canonical_contour_without_profiles() -> None:
    run = read("run-e2e.sh")
    api = read("cards-exact-av-media-api.py")
    assert "full|global|stats|decks|activity|cards|cards-exact-av-media|settings|notifications" in run
    assert '/e2e/bin/cards-exact-av-media-scenario.py' in run
    assert '/e2e/bin/cards-exact-av-media-api.py' in run
    assert '/e2e/bin/cards-exact-av-media-browser.mjs' in run
    assert '/e2e/bin/cards-exact-av-media-evidence.py' in run
    assert "/api/inspection-profiles/" not in api


def test_exact_api_counts_complete_class_tokens_without_prefix_collisions() -> None:
    api = load_python("cards-exact-av-media-api.py")
    html = (
        '<span class="asr-card-replay">'
        '<button class="asr-card-replay-button replay-button"></button>'
        '<audio class="asr-card-replay-audio"></audio>'
        '</span>'
    )
    assert api.count_class_token(html, "asr-card-replay") == 1
    assert api.count_class_token(html, "asr-card-replay-button") == 1
    assert api.count_class_token(html, "asr-card-replay-audio") == 1
    assert api.count_class_token(html, "replay-button") == 1


def test_exact_browser_uses_page_clip_and_side_aware_media_contract() -> None:
    source = read("cards-exact-av-media-browser.mjs")
    assert "locator.screenshot" not in source
    assert 'page.screenshot({ path: outputPath, animations: "allow", caret: "hide", clip })' in source
    assert 'if (expectedSide === "front") return !imageNames.includes(config.png)' in source
    assert "return imageNames.includes(config.png)" in source
    assert "browserFramesDiffer" in source
    assert 'canvas.toDataURL("image/png")' in source
    assert "cross-scenario Playwright page.screenshot clip (animations=allow)" in source
    assert "gifScenarioFrames" in source
    assert "comparisonGroups" in source
    assert "same theme and rounded rendered dimensions" in source
    assert "live HTMLImageElement -> CanvasRenderingContext2D.drawImage" not in source
    assert "maxSamples = 60" not in source
    assert 'decoder.decode({ frameIndex: 0, completeFramesOnly: true })' in source
    assert "const proof = window.__asrReplayProof;" in source
    assert "proof?.playCalls >= 2" in source
    assert "second.playEventCurrentTime" in source
    assert "second replay was not reset before play" in source
    assert "first playback did not advance before second replay" in source
    assert "seekableRanges" in source
    assert "second replay pre-seek did not settle" not in source
    assert "rejectedPromiseHandled" in source
    assert "inspectionProfileRequests.length === 0" in source
    assert "externalRequests.length === 0" in source


def test_exact_geometry_targets_the_exact_word_and_side_aware_examples() -> None:
    source = read("cards-exact-av-media-browser.mjs")
    assert 'root.querySelectorAll(".word-focus")' in source
    assert 'normalized(element.textContent) === config.word' in source
    assert 'config: { word: config.word, gif: config.gif.name' in source
    assert 'wordFocusCandidates.length' in source
    assert 'metrics.wordFocus.text === config.word' in source
    assert 'host.dataset.previewSide === "back"' in source
    assert 'metrics.side === "back"' in source
    assert 'front-side example geometry must be absent' in source
    assert "wordFocusRect" in source
    assert "imageToWordFocusGap" in source
    assert "wordFocusToExampleGap" in source
    assert source.count("expectedNatural: { width: 160, height: 120 }") == 1
    assert "aspect ratio was not preserved" in source
    assert "failureScenario = activeScenario || lastScenario" in source
    assert "(する)" not in source
    assert "（する）" not in source
    assert "suruRect" not in source
    assert "imageToSuru" not in source
    assert "metrics.suru" not in source


def test_exact_host_runner_uses_strict_mounts_and_state_guards() -> None:
    source = read("run-cards-exact-av-media-host.sh")
    assert 'EXPECTED_BRANCH="c2-manual-acceptance-remediation"' in source
    assert "git status --porcelain=v1" in source
    assert "validate_e2e_harness_reuse.py" in source
    assert source.count('--mount "type=bind,source=') == 6
    assert 'target=/cleanup' in source
    assert "--entrypoint /bin/sh" in source
    assert "temporary Docker data could not be removed" in source
    assert "docker run -v" not in source
    assert "--volume" not in source
    assert "require_file" in source
    assert "require_dir" in source
    assert "Output path already exists and is not an empty directory" in source
    assert "Do not rerun." in source
    assert "failure_args=(" in source
    assert 'if [ -n "$token" ]; then' in source
    assert 'failure_args+=(--token "$token")' in source
    assert '--token "$token" \\' not in source


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
    assert os.access(
        E2E / "cards-exact-av-media-browser.mjs",
        os.X_OK,
    ), "exact browser harness must remain executable"

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
