from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from conftest import ROOT


PACKAGE_SCRIPT = ROOT / "scripts" / "package_addon.py"
REQUIRED_ARCHIVE_FILES = {
    "__init__.py",
    "manifest.json",
    "config.json",
    "web_dashboard/index.html",
}


def load_package_script():
    spec = importlib.util.spec_from_file_location("package_addon", PACKAGE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_archive(path: Path, *, include_js: bool = True, css_payload: str | None = None) -> None:
    css_payload = css_payload if css_payload is not None else "\n".join(
        [
            "[data-theme=light]",
            ".topbar-surface",
            ".shadow-panel",
            ".cards-risk-table",
            ".anki-card-shadow-preview",
        ]
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("__init__.py", "")
        archive.writestr("manifest.json", "{}")
        archive.writestr("config.json", "{}")
        archive.writestr("dashboard_server.py", "")
        archive.writestr(
            "web_dashboard/index.html",
            '<!doctype html><html><head><link rel="stylesheet" href="/assets/app.css"></head>'
            '<body><script type="module" src="/assets/app.js"></script></body></html>',
        )
        archive.writestr("web_dashboard/assets/app.css", css_payload)
        if include_js:
            archive.writestr("web_dashboard/assets/app.js", "console.log('ok');")


def test_package_script_builds_flat_clean_ankiaddon(tmp_path):
    package_addon = load_package_script()
    archive_path = package_addon.build_archive(tmp_path / "anki_study_report.ankiaddon")
    validation = package_addon.validate_archive(archive_path)

    assert archive_path.is_file()
    assert validation.testzip_result is None
    assert validation.missing == []
    assert validation.forbidden == []
    assert validation.has_js_asset is True
    assert validation.has_css_asset is True
    assert REQUIRED_ARCHIVE_FILES.issubset(set(validation.names))
    assert not any(name.startswith("anki_study_report/") for name in validation.names)
    assert not any("__pycache__" in Path(name).parts for name in validation.names)
    assert not any(name.endswith(".pyc") for name in validation.names)
    assert not any("node_modules" in Path(name).parts for name in validation.names)


def test_packaged_manifest_has_required_metadata(tmp_path):
    package_addon = load_package_script()
    archive_path = package_addon.build_archive(tmp_path / "anki_study_report.ankiaddon")

    with ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

    assert manifest["package"] == "anki_study_report"
    assert isinstance(manifest["name"], str) and manifest["name"]
    assert isinstance(manifest["min_point_version"], int)


def test_package_validation_rejects_missing_linked_dashboard_asset(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "missing-linked-asset.ankiaddon"
    write_minimal_archive(archive_path, include_js=False)

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert validation.has_js_asset is False
    assert validation.missing_linked_assets == ["web_dashboard/assets/app.js"]


def test_package_validation_rejects_empty_linked_dashboard_asset(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "empty-linked-asset.ankiaddon"
    write_minimal_archive(archive_path, css_payload="")

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert validation.empty_linked_assets == ["web_dashboard/assets/app.css"]
    assert set(validation.css_markers_missing) == set(package_addon.DASHBOARD_CSS_MARKERS)
