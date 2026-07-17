from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import socket
import sys
import urllib.error


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "telemetry_client_smoke.py"
    spec = importlib.util.spec_from_file_location("telemetry_client_smoke_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "_empty_report":
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                report_key_sets.append(
                    {key.value for key in child.value.keys if isinstance(key, ast.Constant)}
                )

    assert report_key_sets == [expected]
    assert "UrlLibTransport()" in source
    assert "requests." not in source
    assert "rawResponse" not in source
    assert "endpoint" not in expected
    assert "exception" not in expected


def test_cloud_smoke_failure_evidence_uses_bounded_codes():
    module = load_module()

    assert module._safe_failure_code(RuntimeError("health_failed_http_503")) == "health_failed_http_503"
    assert module._safe_failure_code(RuntimeError("schema_contract_mismatch")) == "schema_contract_mismatch"
    assert module._safe_failure_code(RuntimeError("secret-bearing unexpected text")) == "unexpected_error"
    assert module._safe_failure_code(
        urllib.error.URLError(socket.gaierror(-2, "name resolution failed"))
    ) == "dns_error"

    stage_error = module.SmokeStageError("health", RuntimeError("health_payload_invalid"))
    assert stage_error.stage == "health"
    assert module._safe_failure_code(stage_error.error) == "health_payload_invalid"


def test_cloud_smoke_success_report_has_no_failure_evidence():
    module = load_module()

    report = module._empty_report("production", "a" * 40)

    assert report["failureStage"] is None
    assert report["failureCode"] is None
    assert report["repositorySha"] == "a" * 40
