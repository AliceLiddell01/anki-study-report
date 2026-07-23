from __future__ import annotations

from argparse import Namespace
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_ci_e2e_artifacts.py"


def load_wrapper(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def summary_args() -> Namespace:
    return Namespace(
        started_at="2026-07-13T00:00:00Z",
        e2e_exit_code=0,
        commit_sha="a" * 40,
        ref="refs/heads/test",
        mode="standard",
        scope="full",
        screenshot_workers=3,
        cache_state="gha-enabled",
        build_duration_ms=1200,
        image_size_bytes=456,
        package_source="source-build",
        source_fast_ci_run_id="",
        source_fast_ci_tested_sha="",
        source_package_sha256="",
        e2e_checkout_sha="a" * 40,
    )


def test_repeated_wrapper_imports_do_not_capture_previous_wrapper_clock(tmp_path: Path) -> None:
    load_wrapper("prepare_ci_e2e_artifacts_reimport_first")
    module = load_wrapper("prepare_ci_e2e_artifacts_reimport_second")

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

    module.utc_now = lambda: "2026-07-13T00:03:30Z"
    module.write_summary(output, args=summary_args(), manifest_status="success", artifact_files=[])

    summary = json.loads((output / "ci-e2e-summary.json").read_text(encoding="utf-8"))
    assert summary["workflowDurationSeconds"] == 210
    assert summary["canonicalDurationSeconds"] == 150
