from __future__ import annotations

import json
import py_compile

from conftest import ADDON_DIR, import_addon_module


REQUIRED_FILES = [
    "__init__.py",
    "manifest.json",
    "config.json",
    "telemetry_contract.json",
    "dashboard_server.py",
    "config_service.py",
    "browser_actions.py",
    "dashboard_actions.py",
    "dashboard_payload.py",
    "metrics.py",
    "report_builder.py",
    "stats_cache.py",
]

IMPORTABLE_MODULES = [
    "dashboard_server",
    "report_builder",
    "stats_cache",
    "forecast_metrics",
    "heatmap_metrics",
    "extension_logging",
    "report_from_cache",
    "config_service",
    "browser_actions",
    "dashboard_actions",
    "dashboard_payload",
    "telemetry_contract",
    "telemetry_store",
    "telemetry_client",
]


def test_required_addon_files_exist():
    missing = [name for name in REQUIRED_FILES if not (ADDON_DIR / name).is_file()]
    assert missing == []


def test_manifest_config_and_telemetry_contract_are_valid_json():
    for name in ["manifest.json", "config.json", "telemetry_contract.json"]:
        data = json.loads((ADDON_DIR / name).read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert data


def test_built_dashboard_assets_are_present():
    dashboard_dir = ADDON_DIR / "web_dashboard"
    assets_dir = dashboard_dir / "assets"
    assert (dashboard_dir / "index.html").is_file()
    assert any(path.suffix == ".js" for path in assets_dir.glob("*.js"))
    assert any(path.suffix == ".css" for path in assets_dir.glob("*.css"))


def test_addon_directory_has_no_generated_junk():
    forbidden = {"__pycache__", ".pytest_cache", "node_modules"}
    found = [
        path.relative_to(ADDON_DIR).as_posix()
        for path in ADDON_DIR.rglob("*")
        if path.name in forbidden
    ]
    assert found == []


def test_all_addon_python_files_compile(tmp_path):
    for source in sorted(ADDON_DIR.rglob("*.py")):
        relative = source.relative_to(ADDON_DIR)
        compiled = tmp_path / (relative.as_posix().replace("/", "__") + ".pyc")
        py_compile.compile(str(source), cfile=str(compiled), doraise=True)


def test_clean_modules_import_without_anki():
    imported = []
    for module_name in IMPORTABLE_MODULES:
        if not (ADDON_DIR / f"{module_name}.py").is_file():
            continue
        imported.append(import_addon_module(module_name).__name__)
    assert "anki_study_report.dashboard_server" in imported
    assert "anki_study_report.report_builder" in imported
    assert "anki_study_report.stats_cache" in imported
