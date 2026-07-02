from __future__ import annotations

import importlib.util
import sys

import pytest

from conftest import ROOT


ARCHIVE = ROOT / "anki_study_report.ankiaddon"
PACKAGE_SCRIPT = ROOT / "scripts" / "package_addon.py"


def load_package_script():
    spec = importlib.util.spec_from_file_location("package_addon", PACKAGE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_built_ankiaddon_archive_is_flat_and_clean():
    if not ARCHIVE.is_file():
        pytest.skip("anki_study_report.ankiaddon has not been built yet")

    package_addon = load_package_script()
    validation = package_addon.validate_archive(ARCHIVE)

    assert validation.testzip_result is None
    assert validation.missing == []
    assert validation.has_js_asset is True
    assert validation.has_css_asset is True
    assert validation.forbidden == []
    assert "anki_study_report/__init__.py" not in validation.names
