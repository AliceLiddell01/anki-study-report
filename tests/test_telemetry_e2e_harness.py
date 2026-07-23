from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_real_deck_browser_smoke_prepares_persistent_telemetry_before_restart() -> None:
    source = (ROOT / "docker" / "anki-e2e" / "smoke-browser.mjs").read_text(encoding="utf-8")
    progress = (ROOT / "docker" / "anki-e2e" / "browser-progress.mjs").read_text(encoding="utf-8")

    assert "ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT" in source
    assert "createTelemetryHarness" in source
    assert "await controlFake(true)" in source
    assert "pendingEventCount >= 25" in source
    assert "pendingBeforeRestart" in source
    assert 'eventCode: "api_operation.failed"' in source
    assert 'eventCode: "page.opened"' in source
    for item_id in (
        "telemetry.declined",
        "telemetry.reliability",
        "telemetry.feature",
        "telemetry.offline",
    ):
        assert item_id in progress


def test_restart_verifier_remains_strict() -> None:
    source = (ROOT / "docker" / "anki-e2e" / "verify-telemetry-restart.py").read_text(encoding="utf-8")

    assert "Persistent telemetry queue was not restored after restart" in source
    assert "pendingEventCount" in source
    assert "pending_after_restart < 25" in source
