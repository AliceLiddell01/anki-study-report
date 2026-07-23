from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ci_e2e_artifact_common.py"


def load_artifact_common():
    spec = importlib.util.spec_from_file_location("ci_e2e_artifact_common_private_paths", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_browser_diagnostics_private_paths_are_redacted_before_validation() -> None:
    module = load_artifact_common()
    payload = {
        "consoleEvents": [
            {
                "type": "log",
                "location": {
                    "url": "file:///home/runner/work/anki-study-report/web-dashboard/src/App.tsx",
                    "lineNumber": 12,
                    "columnNumber": 4,
                },
            },
            {
                "type": "warning",
                "location": {
                    "url": r"C:\Users\alice\anki-study-report\web-dashboard\src\App.tsx",
                    "lineNumber": 7,
                    "columnNumber": 2,
                },
            },
        ]
    }

    redacted = module.redact_json(payload, known_tokens=[], private_roots=[])
    serialized = json.dumps(redacted)

    assert "/home/" not in serialized
    assert "C:\\Users\\" not in serialized
    assert serialized.count("[PRIVATE_PATH]") == 2
    module.assert_safe_text(serialized, "artifacts/reports/browser-smoke-first.json")


def test_private_path_guard_remains_strict_without_redaction() -> None:
    module = load_artifact_common()

    with pytest.raises(ValueError, match="Private absolute path remains"):
        module.assert_safe_text(
            '{"url":"file:///home/runner/work/anki-study-report/src/App.tsx"}',
            "artifacts/reports/browser-smoke-first.json",
        )
