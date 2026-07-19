from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from conftest import ROOT


PACKAGE_SCRIPT = ROOT / "scripts" / "package_addon.py"
REQUIRED_ARCHIVE_FILES = {
    "__init__.py",
    "version.py",
    "manifest.json",
    "config.json",
    "changelog.json",
    "telemetry_contract.json",
    "card_display_formatter_store.py",
    "card_display_formatter_service.py",
    "card_display_formatter_runtime.py",
    "schemas/card-display-formatter-v1.schema.json",
    "web_dashboard/index.html",
}


def load_package_script():
    spec = importlib.util.spec_from_file_location("package_addon", PACKAGE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_archive(
    path: Path,
    *,
    include_js: bool = True,
    css_payload: str | None = None,
    version_source: str = '__version__ = "1.0.0"\n',
) -> None:
    css_payload = css_payload if css_payload is not None else "\n".join(
        [
            "[data-theme=light]",
            ".topbar-surface",
            ".shadow-panel",
            ".cards-v2-table",
            ".anki-card-shadow-preview",
        ]
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("__init__.py", "")
        archive.writestr("version.py", version_source)
        archive.writestr("manifest.json", "{}")
        archive.writestr("config.json", "{}")
        archive.writestr("changelog.json", '{"schemaVersion":1,"unreleased":{"sections":[]},"releases":[]}')
        archive.writestr("telemetry_contract.json", '{"telemetrySchemaVersion":1}')
        archive.writestr("dashboard_server.py", "")
        archive.writestr("card_display_formatter_store.py", "")
        archive.writestr("card_display_formatter_service.py", "")
        archive.writestr("card_display_formatter_runtime.py", "")
        archive.writestr("schemas/card-display-formatter-v1.schema.json", "{}")
        archive.writestr(
            "web_dashboard/index.html",
            '<!doctype html><html><head><link rel="stylesheet" href="/assets/app.css"></head>'
            '<body><script type="module" src="/assets/app.js"></script></body></html>',
        )
        archive.writestr(
            "web_dashboard/manifest.json",
            json.dumps({
                "index.html": {
                    "file": "assets/app.js",
                    "src": "index.html",
                    "isEntry": True,
                    "css": ["assets/app.css"],
                }
            }),
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


def write_split_archive(
    path: Path,
    *,
    omitted: set[str] | None = None,
    empty: set[str] | None = None,
    stale: set[str] | None = None,
    unsafe_lazy_path: str | None = None,
) -> None:
    omitted = omitted or set()
    empty = empty or set()
    stale = stale or set()
    css_payload = "\n".join([
        "[data-theme=light]", ".topbar-surface", ".shadow-panel",
        ".cards-v2-table", ".anki-card-shadow-preview",
    ])
    lazy_file = unsafe_lazy_path or "assets/fsrs-lazy.js"
    manifest = {
        "index.html": {
            "file": "assets/app.js", "src": "index.html", "isEntry": True,
            "dynamicImports": ["src/pages/FsrsStatisticsPage.tsx"],
            "css": ["assets/app.css"],
        },
        "src/pages/FsrsStatisticsPage.tsx": {
            "file": lazy_file, "src": "src/pages/FsrsStatisticsPage.tsx",
            "isDynamicEntry": True, "css": ["assets/fsrs-lazy.css"],
        },
    }
    files = {
        "web_dashboard/assets/app.js": "import('./fsrs-lazy.js')",
        "web_dashboard/assets/app.css": css_payload,
        "web_dashboard/assets/fsrs-lazy.js": "export default {}",
        "web_dashboard/assets/fsrs-lazy.css": ".fsrs-shell{display:grid}",
    }
    with ZipFile(path, "w") as archive:
        archive.writestr("__init__.py", "")
        archive.writestr("version.py", '__version__ = "1.0.0"\n')
        archive.writestr("manifest.json", "{}")
        archive.writestr("config.json", "{}")
        archive.writestr("changelog.json", '{"schemaVersion":1,"unreleased":{"sections":[]},"releases":[]}')
        archive.writestr("telemetry_contract.json", '{"telemetrySchemaVersion":1}')
        archive.writestr("dashboard_server.py", "")
        archive.writestr("card_display_formatter_store.py", "")
        archive.writestr("card_display_formatter_service.py", "")
        archive.writestr("card_display_formatter_runtime.py", "")
        archive.writestr("schemas/card-display-formatter-v1.schema.json", "{}")
        archive.writestr(
            "web_dashboard/index.html",
            '<!doctype html><link rel="stylesheet" href="/assets/app.css">'
            '<script type="module" src="/assets/app.js"></script>',
        )
        archive.writestr("web_dashboard/manifest.json", json.dumps(manifest))
        for name, payload in files.items():
            if name not in omitted:
                archive.writestr(name, "" if name in empty else payload)
        for name in stale:
            archive.writestr(name, "/* stale */")


def test_package_validation_accepts_split_dashboard_graph(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "split-valid.ankiaddon"
    write_split_archive(archive_path)

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is True
    assert validation.asset_graph_errors == []
    assert validation.unsafe_dashboard_asset_refs == []
    assert "web_dashboard/assets/fsrs-lazy.js" in validation.linked_assets
    assert "web_dashboard/assets/fsrs-lazy.css" in validation.linked_assets


def test_package_validation_rejects_missing_or_empty_dynamic_js(tmp_path):
    package_addon = load_package_script()
    missing = tmp_path / "split-missing-js.ankiaddon"
    empty = tmp_path / "split-empty-js.ankiaddon"
    write_split_archive(missing, omitted={"web_dashboard/assets/fsrs-lazy.js"})
    write_split_archive(empty, empty={"web_dashboard/assets/fsrs-lazy.js"})

    missing_validation = package_addon.validate_archive(missing)
    empty_validation = package_addon.validate_archive(empty)

    assert missing_validation.ok is False
    assert missing_validation.missing_linked_assets == ["web_dashboard/assets/fsrs-lazy.js"]
    assert empty_validation.ok is False
    assert empty_validation.empty_linked_assets == ["web_dashboard/assets/fsrs-lazy.js"]


def test_package_validation_rejects_missing_async_css(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "split-missing-css.ankiaddon"
    write_split_archive(archive_path, omitted={"web_dashboard/assets/fsrs-lazy.css"})

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert validation.missing_linked_assets == ["web_dashboard/assets/fsrs-lazy.css"]


def test_package_validation_rejects_stale_unreachable_js_and_css(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "split-stale.ankiaddon"
    stale = {"web_dashboard/assets/old-route.js", "web_dashboard/assets/old-route.css"}
    write_split_archive(archive_path, stale=stale)

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert set(validation.unreferenced_dashboard_assets) == stale


def test_package_validation_rejects_manifest_path_escape(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "split-unsafe.ankiaddon"
    write_split_archive(archive_path, unsafe_lazy_path="../outside.js")

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert validation.unsafe_dashboard_asset_refs == ["../outside.js"]


def test_package_validation_requires_literal_semver_version_source(tmp_path):
    package_addon = load_package_script()
    archive_path = tmp_path / "invalid-version.ankiaddon"
    write_minimal_archive(archive_path, version_source='__version__ = "01.0.0"\n')

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert validation.canonical_version is None
    assert "valid SemVer" in validation.version_error


@pytest.mark.parametrize("unsafe_name", ["../escape.py", "/absolute.py", "C:/private.py"])
def test_package_validation_rejects_unsafe_archive_paths(tmp_path, unsafe_name):
    package_addon = load_package_script()
    archive_path = tmp_path / "unsafe-path.ankiaddon"
    write_minimal_archive(archive_path)
    with ZipFile(archive_path, "a") as archive:
        archive.writestr(unsafe_name, "unsafe")

    validation = package_addon.validate_archive(archive_path)

    assert validation.ok is False
    assert unsafe_name in validation.forbidden
