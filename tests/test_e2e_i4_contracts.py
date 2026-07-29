from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]

def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

preflight = load(ROOT / "scripts/e2e_preflight.py", "i4_preflight")
cancel = load(ROOT / "docker/anki-e2e/cancellation_protocol.py", "i4_cancel")

def make_repo(tmp_path: Path):
    root = tmp_path / "repo"
    for relative in preflight.REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith("docker-compose.yml"):
            path.write_text("services:\n  anki-e2e:\n    image: ${ANKI_E2E_IMAGE}\n    volumes:\n      - ../..:/workspace:ro\n      - ../../artifacts:/e2e/artifacts\n", encoding="utf-8")
        elif relative.endswith("docker-compose.ghcr.yml"):
            path.write_text("services:\n  anki-e2e:\n    pull_policy: never\n    command: [/e2e/bin/run-e2e-failure-wrapper.sh]\n", encoding="utf-8")
        else:
            path.write_text("fixture\n", encoding="utf-8")
    spec = {"schemaVersion": 1, "environmentVersion": "v1", "imageName": "ghcr.io/example/e2e", "platform": "linux/amd64"}
    lock = {**spec, "imageDigest": "sha256:" + "a" * 64, "environmentContractSha256": "sha256:" + "b" * 64, "publishedFromCommitSha": "c" * 40}
    (root / "docker/anki-e2e/environment-image-spec.json").write_text(json.dumps(spec), encoding="utf-8")
    (root / "docker/anki-e2e/environment-image-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    package = b"exact-package"
    package_path = root / "docker/anki-e2e/local-input/anki_study_report.ankiaddon"
    package_path.parent.mkdir(parents=True); package_path.write_bytes(package)
    env = {
        "GITHUB_ACTIONS": "true", "E2E_MODE": "standard", "ANKI_E2E_SCOPE": "full",
        "ANKI_E2E_SCREENSHOT_WORKERS": "3", "ANKI_E2E_VERIFY_RESTART": "auto",
        "ANKI_E2E_PACKAGE_SOURCE": "fast-ci-artifact", "ANKI_E2E_PREBUILT_ADDON_PATH": "/e2e/local-input/anki_study_report.ankiaddon",
        "ANKI_E2E_IMAGE_SOURCE": "ghcr", "ANKI_E2E_IMAGE": f"{lock['imageName']}@{lock['imageDigest']}",
        "ANKI_E2E_NO_BUILD": "1", "ANKI_E2E_EXPECTED_PACKAGE_SHA256": hashlib.sha256(package).hexdigest(),
        "ANKI_E2E_ARTIFACT_ROOT": str(root / "artifacts"),
    }
    return root, env

class Runner:
    def __init__(self, fail: str | None = None, ports: bool = False): self.calls = []; self.fail = fail; self.ports = ports
    def __call__(self, args, cwd, env):
        command = tuple(args); self.calls.append(command); joined = " ".join(command)
        if self.fail and self.fail in joined: return preflight.CommandResult(1, "", "failed")
        if command == ("docker", "--version"): return preflight.CommandResult(0, "Docker 28")
        if command == ("docker", "compose", "version"): return preflight.CommandResult(0, "Compose 2")
        if "{{json .ServerVersion}}" in command: return preflight.CommandResult(0, '"28"')
        if "{{.OSType}}/{{.Architecture}}" in command: return preflight.CommandResult(0, "linux/amd64\n")
        if command[-2:] == ("config", "--quiet"): return preflight.CommandResult(0)
        if command[-3:] == ("config", "--format", "json"):
            service = {"image": env["ANKI_E2E_IMAGE"], "pull_policy": "never", "volumes": [{"source": str(cwd), "target": "/workspace", "read_only": True}]}
            if self.ports: service["ports"] = [{"published": "8766"}]
            return preflight.CommandResult(0, json.dumps({"services": {"anki-e2e": service}}))
        raise AssertionError(command)

def test_preflight_static_runtime_pass_and_deterministic_order(tmp_path: Path):
    root, env = make_repo(tmp_path); report = root / "artifacts/reports/preflight-report.json"
    preflight.run_preflight(root, report, layer="static", execution_context="github-actions", env=env)
    result = preflight.run_preflight(root, report, layer="runtime", execution_context="github-actions", env=env, command_runner=Runner())
    assert result["status"] == "PASS"
    assert [item["id"] for item in result["checks"]] == list(preflight.ALL_CHECK_IDS)
    assert report.read_bytes() == preflight.serialize_report(preflight.load_report(report)).encode()

@pytest.mark.parametrize(("name", "value", "failed"), [("E2E_MODE", "bad", "inputs.mode-scope"), ("ANKI_E2E_SCREENSHOT_WORKERS", "9", "inputs.workers"), ("ANKI_E2E_PACKAGE_SOURCE", "source-build", "package.source-exclusivity")])
def test_static_validation_fails_before_docker(tmp_path: Path, name: str, value: str, failed: str):
    root, env = make_repo(tmp_path); env[name] = value
    if name == "ANKI_E2E_PACKAGE_SOURCE": env.pop("ANKI_E2E_PREBUILT_ADDON_PATH")
    result = preflight.run_preflight(root, root / "artifacts/reports/preflight-report.json", layer="static", execution_context="github-actions", env=env)
    assert result["failedCheckId"] == failed

def test_runtime_failures_stop_without_pull_build_or_run(tmp_path: Path):
    root, env = make_repo(tmp_path); report = root / "artifacts/reports/preflight-report.json"
    preflight.run_preflight(root, report, layer="static", execution_context="github-actions", env=env)
    (root / "docker/anki-e2e/local-input/anki_study_report.ankiaddon").unlink(); runner = Runner()
    result = preflight.run_preflight(root, report, layer="runtime", execution_context="github-actions", env=env, command_runner=runner)
    assert result["failedCheckId"] == "package.staged-artifact" and runner.calls == []

def test_resolved_compose_rejects_external_ports(tmp_path: Path):
    root, env = make_repo(tmp_path); report = root / "artifacts/reports/preflight-report.json"
    preflight.run_preflight(root, report, layer="static", execution_context="github-actions", env=env)
    result = preflight.run_preflight(root, report, layer="runtime", execution_context="github-actions", env=env, command_runner=Runner(ports=True))
    assert result["failedCheckId"] == "compose.no-external-ports"

@pytest.mark.parametrize(("signal", "code"), [("SIGINT", 130), ("SIGTERM", 143)])
def test_cancellation_summary_is_separate_atomic_and_signal_exact(tmp_path: Path, signal: str, code: int):
    path = tmp_path / "reports/cancellation-summary.json"
    document = cancel.build_document(producer="docker-e2e", elapsed_ms=10, original_exit_code=code, original_signal=signal, cleanup_status="success", cleanup_duration_ms=2, cleanup_attempts=1, artifact_status="partial", evidence_paths=["reports/run-events.jsonl"])
    cancel.write_document(path, document)
    assert cancel.load_document(path) == document
    assert not path.with_name("failure-summary.json").exists()
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))

def test_cancellation_rejects_invalid_signal_path_secret_and_failure_coexistence(tmp_path: Path):
    base = dict(producer="docker-e2e", elapsed_ms=1, original_exit_code=130, original_signal="SIGINT", cleanup_status="partial", cleanup_duration_ms=0, cleanup_attempts=1, artifact_status="unavailable")
    with pytest.raises(cancel.CancellationProtocolError): cancel.build_document(**{**base, "original_signal": "SIGHUP"})
    with pytest.raises(cancel.CancellationProtocolError): cancel.build_document(**base, evidence_paths=["/home/user/private"])
    with pytest.raises(cancel.CancellationProtocolError): cancel.build_document(**base, evidence_paths=["reports/token=secret"])
    path = tmp_path / "reports/cancellation-summary.json"; path.parent.mkdir(); path.with_name("failure-summary.json").write_text("{}\n")
    with pytest.raises(cancel.CancellationProtocolError): cancel.write_document(path, cancel.build_document(**base))


def test_powershell_uses_single_validator_and_run_scoped_resources():
    runner = (ROOT / "scripts/run_anki_e2e_docker.ps1").read_text(encoding="utf-8")
    assert "scripts\\e2e_preflight.py" in runner
    assert "COMPOSE_PROJECT_NAME" in runner
    assert "exit $scriptExit" in runner

def test_workflow_preflight_and_cancellation_conditions_are_bounded():
    e2e = (ROOT / ".github/workflows/ci-e2e.yml").read_text(encoding="utf-8")
    fast = (ROOT / ".github/workflows/ci-fast.yml").read_text(encoding="utf-8")
    assert "if: always()" not in e2e
    assert "if: always()" not in fast
    assert e2e.index("Run canonical static E2E preflight") < e2e.index("Log in to GHCR")
    assert e2e.index("Run canonical runtime E2E preflight") < e2e.index("Pull and verify exact GHCR environment image")
    assert "if: ${{ cancelled() }}" in e2e
    assert "if: ${{ !cancelled() }}" in e2e
    assert "Prepare redacted public E2E artifact\n        if: ${{ !cancelled() }}" in e2e
    assert "Finalize Docker E2E state before artifact preparation\n        if: ${{ !cancelled() }}" in e2e
    assert "Finalize public canonical summary and legacy projections\n        id: final_summary" in e2e
    assert "Upload E2E artifact\n        id: artifact_upload" in e2e
    assert "steps.final_summary.outcome == 'success'" in e2e
    assert "env.CI_E2E_ARTIFACT_EXIT_CODE == '0'" in e2e
    assert "Prepare bounded cancellation artifact" in e2e
    assert "Upload bounded cancellation evidence" in e2e
    assert "Finalize cancelled Fast CI" in fast
    assert "Upload bounded cancelled Fast CI evidence" in fast


def test_inner_runner_and_fast_timing_preserve_cancel_semantics():
    runner = (ROOT / "docker/anki-e2e/run-e2e.sh").read_text(encoding="utf-8")
    timing = (ROOT / "scripts/ci_fast_timing.py").read_text(encoding="utf-8")
    assert "trap 'handle_signal SIGINT 130' INT" in runner
    assert "trap 'handle_signal SIGTERM 143' TERM" in runner
    assert "run_event cancel-run --original-exit-code" in runner
    assert "run_events.cancel_run(" in timing

def test_inner_artifact_reset_preserves_only_canonical_preflight_report():
    runner = (ROOT / "docker/anki-e2e/run-e2e.sh").read_text(encoding="utf-8")
    prepare = runner[
        runner.index('section "Prepare artifacts"'):
        runner.index("run_event initialize", runner.index('section "Prepare artifacts"'))
    ]

    assert (
        'preflight_report="${ANKI_STUDY_REPORT_E2E_REPORTS_DIR}/'
        'preflight-report.json"'
    ) in prepare
    assert '! -path "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"' in prepare
    assert '! -name "preflight-report.json"' in prepare
    assert prepare.index('if [ -f "$preflight_report" ]; then') < prepare.index(
        '! -name "preflight-report.json"'
    )
    assert 'mkdir -p "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"' in prepare
