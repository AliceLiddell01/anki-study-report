from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import e2e_final_summary as final
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


def test_success_manifest_requires_and_indexes_final_run_summary() -> None:
    manifest = load_script(
        "docker/anki-e2e/write-artifact-manifest.py",
        "e2e_i6_artifact_manifest",
    )
    assert "reports/final-run-summary.json" in manifest.REQUIRED_SUCCESS_ARTIFACTS


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
