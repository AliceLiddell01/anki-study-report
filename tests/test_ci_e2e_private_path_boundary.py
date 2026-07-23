from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ci_e2e_artifact_common.py"


def load_artifact_common():
    spec = importlib.util.spec_from_file_location("ci_e2e_artifact_common_private_path_boundary", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_relative_home_route_paths_are_not_treated_as_private_paths() -> None:
    module = load_artifact_common()
    values = (
        "screenshots/pages/home/dark.png",
        "screenshots/pages/home/light.png",
        "artifacts/screenshots/pages/home/dark.png",
    )

    for value in values:
        assert module.redact_text(value, known_tokens=[], private_roots=[]) == value
        module.assert_safe_text(value, "ci-e2e-summary.json")
