from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manual_cloud_smoke_is_dispatch_only_and_production_gated():
    workflow = (ROOT / ".github" / "workflows" / "telemetry-client-smoke.yml").read_text(encoding="utf-8")

    trigger_block = workflow.split("permissions:", 1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "push:" not in trigger_block
    assert "pull_request:" not in trigger_block
    assert "schedule:" not in trigger_block
    assert "default: staging" in workflow
    assert "RUN_PRODUCTION_TELEMETRY_CLIENT_SMOKE" in workflow
    assert "if: inputs.target == 'production'" in workflow


def test_cloud_smoke_report_is_bounded_and_endpoint_free():
    script_path = ROOT / "scripts" / "telemetry_client_smoke.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    expected = {
        "targetKind",
        "schemaAccepted",
        "enrollmentPassed",
        "batchAcknowledged",
        "duplicateAcknowledged",
        "deletionPassed",
        "postDeleteTokenRejected",
        "failureStage",
        "failureCode",
        "repositorySha",
    }
    report_key_sets = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        keys = {key.value for key in node.value.keys if isinstance(key, ast.Constant)}
        if "targetKind" in keys:
            report_key_sets.append(keys)

    assert report_key_sets
    assert all(keys == expected for keys in report_key_sets)
    assert "UrlLibTransport()" in source
    assert "requests." not in source
    assert "rawResponse" not in source
    assert "failureStage" in source
    assert "failureCode" in source
    assert "traceback" not in source
    assert "repr(" not in source
