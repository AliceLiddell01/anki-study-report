from __future__ import annotations

import ast
import importlib.util
from argparse import Namespace
import json
from pathlib import Path
import sys

import pytest


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "prepare_ci_e2e_artifacts.py"
    spec = importlib.util.spec_from_file_location("prepare_ci_e2e_artifacts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_e2e_fixture_sources_forbid_collection_save_but_allow_manager_save():
    root = Path(__file__).resolve().parents[1] / "docker" / "anki-e2e"
    seed = (root / "seed-collection.py").read_text(encoding="utf-8")
    fixture_import = (root / "import-apkg-fixture.py").read_text(encoding="utf-8")
    trees = [ast.parse(seed), ast.parse(fixture_import)]
    direct_collection_saves = []
    dynamic_collection_saves = []
    manager_saves = []
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "save":
                target = node.func.value
                if isinstance(target, ast.Name) and target.id == "col":
                    direct_collection_saves.append(node)
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "col":
                    manager_saves.append(node)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr":
                if len(node.args) >= 2 and isinstance(node.args[0], ast.Name) and node.args[0].id == "col":
                    if isinstance(node.args[1], ast.Constant) and node.args[1].value == "save":
                        dynamic_collection_saves.append(node)

    assert direct_collection_saves == []
    assert dynamic_collection_saves == []
    assert len(manager_saves) == 1
    assert "col.decks.save(deck)" in seed


def create_source(root: Path) -> str:
    token = "fixture-dashboard-token-value"
    files = {
        "runtime/dashboard-ready.json": json.dumps(
            {"token": token, "baseUrl": f"http://127.0.0.1:8766/?token={token}", "reportAvailable": True}
        ),
        "runtime/addon-e2e-events.jsonl": json.dumps({"stage": "readiness_write_done"}),
        "reports/browser-smoke-first.json": json.dumps(
            {
                "requestFailures": [],
                "consoleErrors": [],
                "alreadyRedacted": "http://127.0.0.1/api?name=test&amp;token=<redacted-token>",
            }
        ),
        "diagnostics/anki-startup-tail.txt": f"ready token={token}",
        "html/cards.html": f'<a href="http://127.0.0.1/?token={token}">safe</a>',
    }
    binary = {
        "screenshots/pages/today/light.png": b"png",
        "package/anki_study_report.ankiaddon": b"zip",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for relative, content in binary.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {
        "status": "success",
        "runtime": {
            "dashboardReady": "runtime/dashboard-ready.json",
            "events": "runtime/addon-e2e-events.jsonl",
        },
        "artifacts": {
            "reports": ["reports/browser-smoke-first.json"],
            "diagnostics": ["diagnostics/anki-startup-tail.txt"],
            "html": ["html/cards.html"],
            "package": ["package/anki_study_report.ankiaddon"],
        },
        "screenshots": [{"path": "screenshots/pages/today/light.png", "kind": "page"}],
    }
    (root / "artifact-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return token


def test_export_redacts_readiness_token_and_preserves_safe_evidence(tmp_path: Path):
    module = load_module()
    source = tmp_path / "source"
    destination = tmp_path / "output" / "artifacts"
    token = create_source(source)

    status, copied = module.copy_safe_artifacts(source, destination, [str(tmp_path)])

    assert status == "success"
    assert not (destination / "runtime/dashboard-ready.json").exists()
    readiness = json.loads((destination / "runtime/dashboard-ready.redacted.json").read_text(encoding="utf-8"))
    assert "token" not in readiness
    assert readiness["redacted"] is True
    exported_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in destination.rglob("*")
        if path.is_file() and path.suffix in module.TEXT_SUFFIXES
    )
    assert token not in exported_text
    assert "?token=" not in exported_text
    assert "artifacts/screenshots/pages/today/light.png" in copied
    assert (destination / "package/anki_study_report.ankiaddon").read_bytes() == b"zip"
    manifest = json.loads((destination / "artifact-manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtime"]["dashboardReady"] == "runtime/dashboard-ready.redacted.json"
    browser = json.loads((destination / "reports/browser-smoke-first.json").read_text(encoding="utf-8"))
    assert browser["alreadyRedacted"] == "http://127.0.0.1/api?name=test"


def test_export_supports_missing_manifest_and_empty_optional_directories(tmp_path: Path):
    module = load_module()
    source = tmp_path / "source"
    (source / "reports").mkdir(parents=True)

    status, copied = module.copy_safe_artifacts(source, tmp_path / "output", [str(tmp_path)])

    assert status == "missing"
    assert copied == []


@pytest.mark.parametrize("bad_path", ["../secret.txt", "/tmp/secret.txt", "C:/secret.txt"])
def test_manifest_rejects_absolute_and_traversal_paths(tmp_path: Path, bad_path: str):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    manifest = {"runtime": {"events": bad_path}, "artifacts": {}, "screenshots": []}

    with pytest.raises(ValueError, match="Unsafe artifact path"):
        module.validate_manifest(source, manifest)


def test_export_rejects_secret_like_text(tmp_path: Path):
    module = load_module()
    source = tmp_path / "source"
    create_source(source)
    (source / "reports/browser-smoke-first.json").write_text(
        json.dumps({"credential": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Secret-like content"):
        module.copy_safe_artifacts(source, tmp_path / "output", [str(tmp_path)])


def test_export_rejects_unredacted_private_path(tmp_path: Path):
    module = load_module()

    with pytest.raises(ValueError, match="Private absolute path"):
        module.assert_safe_text("path=C:/Users/Alice/private.txt", "report.txt")


def test_summary_v2_keeps_targeted_comparison_honest(tmp_path: Path, monkeypatch):
    module = load_module()
    output = tmp_path / "output"
    reports = output / "artifacts" / "reports"
    reports.mkdir(parents=True)
    (output / "logs").mkdir()
    performance = {"baseline": {"canonicalDurationSeconds": 183}, "current": {}, "improvement": {}}
    (reports / "e2e-performance-summary.json").write_text(json.dumps(performance), encoding="utf-8")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    args = Namespace(
        started_at="2026-07-13T00:00:00Z",
        e2e_exit_code=0,
        commit_sha="abc123",
        ref="refs/heads/test",
        mode="standard",
        scope="stats",
        screenshot_workers=3,
        cache_state="gha-enabled",
        build_duration_ms=1200,
        image_size_bytes=456,
    )

    module.write_summary(output, args=args, manifest_status="success", artifact_files=[])

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    exported_performance = json.loads((reports / "e2e-performance-summary.json").read_text(encoding="utf-8"))
    assert summary["schemaVersion"] == 2
    assert summary["scope"] == "stats"
    assert summary["screenshotWorkers"] == 3
    assert exported_performance["improvement"]["canonicalSavedSeconds"] is None
    assert "not an apples-to-apples" in exported_performance["improvement"]["comparisonReason"]


def test_summary_compares_canonical_duration_with_canonical_baseline(tmp_path: Path, monkeypatch):
    module = load_module()
    output = tmp_path / "output"
    reports = output / "artifacts" / "reports"
    reports.mkdir(parents=True)
    (output / "logs").mkdir()
    performance = {
        "baseline": {"canonicalDurationSeconds": 183},
        "current": {"canonicalDurationSeconds": 150},
        "improvement": {},
    }
    (reports / "e2e-performance-summary.json").write_text(json.dumps(performance), encoding="utf-8")
    monkeypatch.setattr(module, "utc_now", lambda: "2026-07-13T00:03:30Z")
    args = Namespace(
        started_at="2026-07-13T00:00:00Z",
        e2e_exit_code=0,
        commit_sha="abc123",
        ref="refs/heads/test",
        mode="standard",
        scope="full",
        screenshot_workers=3,
        cache_state="gha-enabled",
        build_duration_ms=1200,
        image_size_bytes=456,
    )

    module.write_summary(output, args=args, manifest_status="success", artifact_files=[])

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    exported_performance = json.loads((reports / "e2e-performance-summary.json").read_text(encoding="utf-8"))
    markdown = (output / "ci-e2e-summary.md").read_text(encoding="utf-8")
    assert summary["workflowDurationSeconds"] == 210
    assert summary["canonicalDurationSeconds"] == 150
    assert exported_performance["improvement"]["canonicalSavedSeconds"] == 33
    assert "Saved vs canonical baseline | 33 seconds" in markdown
    assert "Workflow duration | 210 seconds" in markdown
