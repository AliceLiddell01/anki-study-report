from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_CHECK = ROOT / "scripts" / "run_full_check.ps1"


def test_full_check_preserves_explicit_e2e_runtime_options() -> None:
    text = FULL_CHECK.read_text(encoding="utf-8")

    assert "ANKI_E2E_RESOURCE_TELEMETRY = $env:ANKI_E2E_RESOURCE_TELEMETRY" in text
    assert "elseif ($previous.ANKI_E2E_RESOURCE_TELEMETRY)" in text
    assert "$previous.ANKI_E2E_RESOURCE_TELEMETRY } else { \"1\"" in text

    assert "ANKI_E2E_VERIFY_RESTART = $env:ANKI_E2E_VERIFY_RESTART" in text
    assert "$previousRestart = $previous.ANKI_E2E_VERIFY_RESTART" in text
    assert '$PSBoundParameters.ContainsKey("VerifyRestart")' in text
    assert "elseif ($previousRestart)" in text
    assert "$previousRestart\n    } else {\n        \"auto\"" in text


def test_full_check_explicit_switches_still_override_environment() -> None:
    text = FULL_CHECK.read_text(encoding="utf-8")

    assert "$env:ANKI_E2E_RESOURCE_TELEMETRY = if ($DisableResourceTelemetry)" in text
    assert 'switch ($VerifyRestart) { "true" { "1" }; "false" { "0" }; default { "auto" } }' in text
