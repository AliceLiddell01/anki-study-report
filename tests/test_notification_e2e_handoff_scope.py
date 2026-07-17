from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_fast_ci_e2e_handoff_notification_scope",
    ROOT / "scripts" / "verify_fast_ci_e2e_handoff.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

ARTIFACT_COMMON_SPEC = importlib.util.spec_from_file_location(
    "ci_e2e_artifact_common_notification_scope",
    ROOT / "scripts" / "ci_e2e_artifact_common.py",
)
assert ARTIFACT_COMMON_SPEC is not None and ARTIFACT_COMMON_SPEC.loader is not None
ARTIFACT_COMMON = importlib.util.module_from_spec(ARTIFACT_COMMON_SPEC)
sys.modules[ARTIFACT_COMMON_SPEC.name] = ARTIFACT_COMMON
ARTIFACT_COMMON_SPEC.loader.exec_module(ARTIFACT_COMMON)


def test_standard_notification_scope_is_preserved_by_fast_ci_handoff():
    normalized = MODULE.normalize_e2e_inputs(
        mode="standard",
        scope="notifications",
        screenshot_workers="auto",
        resource_telemetry="false",
        verify_restart="true",
    )

    assert normalized == {
        "E2E_MODE": "standard",
        "E2E_SCOPE": "notifications",
        "ANKI_E2E_SCOPE": "notifications",
        "ANKI_E2E_SCREENSHOT_WORKERS": "3",
        "ANKI_E2E_RESOURCE_TELEMETRY": "0",
        "ANKI_E2E_VERIFY_RESTART": "1",
    }


def test_notification_scope_is_preserved_by_public_artifact_export():
    assert "notifications" in MODULE._ALLOWED_SCOPES
    assert "notifications" in ARTIFACT_COMMON.ALLOWED_SCOPES


@pytest.mark.parametrize("mode", ["strict-apkg", "perf100"])
def test_special_modes_still_reject_notification_scope(mode: str):
    with pytest.raises(MODULE.HandoffError, match="requires scope=full or scope=cards"):
        MODULE.normalize_e2e_inputs(
            mode=mode,
            scope="notifications",
            screenshot_workers="1",
            resource_telemetry="false",
            verify_restart="false",
        )
