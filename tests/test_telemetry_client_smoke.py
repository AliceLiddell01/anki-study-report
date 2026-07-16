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
        "repositorySha",
    }
    report_key_sets = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id == "report" for target in node.targets):
            continue
        if isinstance(node.value, ast.Dict):
            report_key_sets.append({key.value for key in node.value.keys if isinstance(key, ast.Constant)})

    assert report_key_sets
    assert all(keys == expected for keys in report_key_sets)
    assert "UrlLibTransport()" in source
    assert "requests." not in source
    assert "rawResponse" not in source
