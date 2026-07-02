from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = ROOT / "anki_study_report"

sys.dont_write_bytecode = True


def install_fake_aqt_modules(mw=None, dialogs=None) -> None:
    """Provide the tiny aqt surface needed by pure unit tests outside Anki."""

    if "aqt" not in sys.modules:
        aqt = types.ModuleType("aqt")
        sys.modules["aqt"] = aqt
    else:
        aqt = sys.modules["aqt"]
    aqt.mw = mw
    aqt.dialogs = dialogs or types.SimpleNamespace()


def import_addon_module(module_name: str):
    """Import an add-on submodule without executing the Anki/Qt-heavy __init__."""

    install_fake_aqt_modules()
    package = sys.modules.get("anki_study_report")
    if package is None:
        package = types.ModuleType("anki_study_report")
        package.__path__ = [str(ADDON_DIR)]
        package.__file__ = str(ADDON_DIR / "__init__.py")
        sys.modules["anki_study_report"] = package
    return importlib.import_module(f"anki_study_report.{module_name}")


def fresh_import_addon_module(module_name: str):
    sys.modules.pop(f"anki_study_report.{module_name}", None)
    return import_addon_module(module_name)


def load_dashboard_fixture(name: str) -> dict:
    path = ROOT / "tests" / "fixtures" / "dashboard" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))
