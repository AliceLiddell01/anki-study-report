from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import e2e_final_summary as final
import e2e_final_summary_common as common
from e2e_final_summary_fixtures import build, make_root, write_json


ROOT = Path(__file__).resolve().parents[1]


def load_script(relative: str, module_name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("reports/a.json", "reports"),
        ("artifacts/reports/a.json", "reports"),
        ("screenshots/a.png", "screenshots"),
        ("artifacts/screenshots/a.png", "screenshots"),
        ("package/a.ankiaddon", "package"),
        ("artifacts/package/a.ankiaddon", "package"),
        ("diagnostics/a.log", "diagnostics"),
        ("artifacts/diagnostics/a.log", "diagnostics"),
        ("runtime/a.json", "runtime"),
        ("artifacts/runtime/a.json", "runtime"),
        ("unknown/a.json", "other"),
        ("artifacts-other/reports/a.json", "other"),
        ("artifacts/artifacts/reports/a.json", "other"),
        ("artifact-manifest.json", "other"),
        ("artifacts/artifact-manifest.json", "other"),
    ],
)
def test_footprint_category_normalizes_only_reviewed_public_prefix(path: str, expected: str) -> None:
    assert common._category(path) == expected


@pytest.mark.parametrize("path", ["../secret", "/tmp/file", "./reports/a.json", r"C:\Users\x\file"])
def test_footprint_category_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(final.FinalSummaryError):
        common._category(path)


@pytest.mark.parametrize("public_layout", [False, True])
def test_footprint_category_sums_and_derived_fields_match_inventory(
    tmp_path: Path,
    public_layout: bool,
) -> None:
    root = tmp_path / ("public" if public_layout else "raw")
    prefix = root / "artifacts" if public_layout else root
    files = {
        "reports/a.json": b"report",
        "screenshots/a.png": b"screenshot",
        "diagnostics/a.log": b"diagnostic",
        "package/a.ankiaddon": b"package",
        "runtime/a.json": b"runtime",
        "other.txt": b"other",
    }
    for relative, content in files.items():
        path = prefix / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    summary_relative = (
        "artifacts/reports/final-run-summary.json"
        if public_layout
        else "reports/final-run-summary.json"
    )
    manifest_relative = (
        "artifacts/artifact-manifest.json"
        if public_layout
        else "artifact-manifest.json"
    )
    manifest = root / manifest_relative
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")

    footprint = common._footprint(
        root,
        predicted_summary_bytes=11,
        summary_relative=summary_relative,
        manifest_relative=manifest_relative,
    )

    assert sum(row["fileCount"] for row in footprint["categories"].values()) == footprint["fileCount"]
    assert sum(row["bytes"] for row in footprint["categories"].values()) == footprint["totalUncompressedBytes"]
    for category in ("reports", "screenshots", "diagnostics", "package", "runtime"):
        assert footprint["categories"][category]["fileCount"] == 1
    assert footprint["reportsCount"] == footprint["categories"]["reports"]["fileCount"]
    assert footprint["screenshotCount"] == footprint["categories"]["screenshots"]["fileCount"]
    assert footprint["diagnosticsCount"] == footprint["categories"]["diagnostics"]["fileCount"]
    assert footprint["packageCount"] == footprint["categories"]["package"]["fileCount"]
    assert footprint["runtimeCount"] == footprint["categories"]["runtime"]["fileCount"]
    assert all(not row["path"].startswith("/") for row in footprint["largestFiles"])


def test_workflow_regenerated_manifest_indexes_final_run_summary_without_inner_requirement(tmp_path: Path) -> None:
    manifest = load_script(
        "docker/anki-e2e/write-artifact-manifest.py",
        "e2e_i6_artifact_manifest",
    )
    paths = manifest.ArtifactPaths.from_root(tmp_path / "artifact")
    paths.ensure()
    write_json(paths.reports / "final-run-summary.json", {"schemaVersion": 1})

    document = manifest.build_manifest(paths, status="failed", anki_version="26.05")

    assert "reports/final-run-summary.json" in manifest.manifest_indexed_paths(document)
    assert "reports/final-run-summary.json" not in manifest.REQUIRED_SUCCESS_ARTIFACTS


def test_cancellation_artifact_copies_and_revalidates_bounded_final_summary(tmp_path: Path) -> None:
    cancellation = load_script(
        "scripts/prepare_ci_e2e_cancellation.py",
        "e2e_i6_cancellation_artifact",
    )
    source = make_root(tmp_path / "source", result="cancelled")
    summary = build(
        source,
        result="cancelled",
        purpose="controlled",
        cleanup_status="failure",
    )
    write_json(source / "reports/final-run-summary.json", summary)

    output = tmp_path / "public"
    copied = cancellation.prepare(source, output)

    assert "reports/cancellation-summary.json" in copied
    assert "reports/final-run-summary.json" in copied
    assert final.load_summary(output / "reports/final-run-summary.json") == summary
    artifact = json.loads((output / "cancellation-artifact.json").read_text(encoding="utf-8"))
    assert artifact["policy"] == "best-effort-minimal"
    assert artifact["status"] == "partial"


def test_cancellation_artifact_remains_best_effort_when_final_summary_is_unavailable(tmp_path: Path) -> None:
    cancellation = load_script(
        "scripts/prepare_ci_e2e_cancellation.py",
        "e2e_i6_cancellation_artifact_without_summary",
    )
    source = make_root(tmp_path / "source", result="cancelled")
    output = tmp_path / "public"

    copied = cancellation.prepare(source, output)

    assert "reports/cancellation-summary.json" in copied
    assert "reports/final-run-summary.json" not in copied
