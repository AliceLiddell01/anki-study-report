from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docker" / "anki-e2e" / "environment-image-spec.json"
LOCK = ROOT / "docker" / "anki-e2e" / "environment-image-lock.json"
BASE_COMPOSE = ROOT / "docker" / "anki-e2e" / "docker-compose.yml"
GHCR_COMPOSE = ROOT / "docker" / "anki-e2e" / "docker-compose.ghcr.yml"
BOOTSTRAP = ROOT / "docker" / "anki-e2e" / "bootstrap-current-harness.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "ci-e2e.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
WRAPPER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"

EXPECTED_DIGEST = "sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475"
EXPECTED_CONTRACT = "sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447"
EXPECTED_REFERENCE = f"ghcr.io/aliceliddell01/anki-study-report-e2e@{EXPECTED_DIGEST}"


def load_consumer_validator():
    scripts = ROOT / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    path = scripts / "validate_e2e_environment_consumer.py"
    spec = importlib.util.spec_from_file_location("validate_e2e_environment_consumer", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_json(validator, value: dict[str, object]) -> str:
    return validator.load_json_object.__globals__["canonical_json"](value)


def test_consumer_lock_is_canonical_exact_and_linked_to_environment_spec() -> None:
    validator = load_consumer_validator()
    raw = LOCK.read_text(encoding="utf-8")
    lock = json.loads(raw)
    spec = validator.read_spec(SPEC)

    assert raw == canonical_json(validator, lock)
    assert validator.read_consumer_lock(LOCK, spec) == lock
    assert validator.exact_reference(lock) == EXPECTED_REFERENCE
    assert lock == {
        "schemaVersion": 1,
        "environmentVersion": "env-v1",
        "imageName": "ghcr.io/aliceliddell01/anki-study-report-e2e",
        "imageDigest": EXPECTED_DIGEST,
        "platform": "linux/amd64",
        "humanTag": "env-v1-anki26.05-pw1.55.1",
        "environmentContractSha256": EXPECTED_CONTRACT,
        "publishedFromCommitSha": "298be46ffe84bffa612dd6322dc0421b1ff0955e",
        "publicationRunId": 29561205765,
        "idempotentVerificationRunId": 29573061110,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schemaVersion", 2),
        ("environmentVersion", "env-v2"),
        ("imageName", "ghcr.io/aliceliddell01/anki-study-report-e2e:latest"),
        ("imageName", "ghcr.io/AliceLiddell01/anki-study-report-e2e"),
        ("imageDigest", "sha256:" + "0" * 64),
        ("platform", "linux/arm64"),
        ("humanTag", "latest"),
        ("environmentContractSha256", "sha256:" + "0" * 64),
        ("publishedFromCommitSha", "0" * 40),
        ("publicationRunId", 0),
        ("idempotentVerificationRunId", 0),
    ],
)
def test_consumer_lock_rejects_identity_drift(tmp_path: Path, field: str, value: object) -> None:
    validator = load_consumer_validator()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    lock[field] = value
    path = tmp_path / "lock.json"
    path.write_text(canonical_json(validator, lock), encoding="utf-8")

    with pytest.raises(validator.EnvironmentImageError):
        validator.read_consumer_lock(path, validator.read_spec(SPEC))


def test_consumer_lock_rejects_unknown_sensitive_or_path_fields(tmp_path: Path) -> None:
    validator = load_consumer_validator()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    lock["token"] = "ghp_example"
    path = tmp_path / "lock.json"
    path.write_text(canonical_json(validator, lock), encoding="utf-8")
    with pytest.raises(validator.EnvironmentImageError):
        validator.read_consumer_lock(path, validator.read_spec(SPEC))

    lock.pop("token")
    lock["localPath"] = "C:/Users/example"
    path.write_text(canonical_json(validator, lock), encoding="utf-8")
    with pytest.raises(validator.EnvironmentImageError):
        validator.read_consumer_lock(path, validator.read_spec(SPEC))


def test_consumer_outputs_are_bounded_and_render_exact_reference() -> None:
    validator = load_consumer_validator()
    outputs = validator.consumer_outputs(
        validator.read_consumer_lock(LOCK, validator.read_spec(SPEC))
    )

    assert outputs == {
        "image_reference": EXPECTED_REFERENCE,
        "image_name": "ghcr.io/aliceliddell01/anki-study-report-e2e",
        "image_digest": EXPECTED_DIGEST,
        "image_platform": "linux/amd64",
        "environment_version": "env-v1",
        "environment_contract_sha256": EXPECTED_CONTRACT,
        "published_from_commit_sha": "298be46ffe84bffa612dd6322dc0421b1ff0955e",
        "human_tag": "env-v1-anki26.05-pw1.55.1",
        "environment_publication_run_id": "29561205765",
        "environment_reuse_verification_run_id": "29573061110",
    }
    assert not any("token" in key.lower() or "path" in key.lower() for key in outputs)


def test_workflow_inputs_permissions_and_concurrency_are_stage_6a_safe() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    permissions = text[text.index("permissions:\n") : text.index("concurrency:\n")]

    assert text.count("environment_image_source:") == 2
    assert text.count("default: buildkit") >= 2
    assert "options:\n          - buildkit\n          - ghcr" in text
    assert "${{ inputs.environment_image_source || 'buildkit' }}" in text
    assert permissions == (
        "permissions:\n"
        "  contents: read\n"
        "  actions: read\n"
        "  packages: read\n\n"
    )
    for forbidden in ("packages: write", "contents: write", "id-token: write", "attestations: write"):
        assert forbidden not in permissions


def test_workflow_rejects_ghcr_source_build_before_registry_login() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    reject = text.index("GHCR environment image source requires a prebuilt")
    login = text.index("- name: Log in to GHCR")

    assert reject < login
    assert "Manual GHCR validation requires fast_ci_run_id" in text
    assert "source.packageSource -eq 'source-build'" in text


def test_workflow_has_disjoint_buildkit_and_ghcr_preparation_contours() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for step in (
        "Enable containerd image store",
        "Set up Docker Buildx",
        "Start Docker build timing",
        "Build and load cached E2E image",
        "Capture Docker build telemetry",
    ):
        index = text.index(f"- name: {step}")
        fragment = text[index : index + 260]
        assert "if: env.ANKI_E2E_IMAGE_SOURCE == 'buildkit'" in fragment

    assert "cache-from: type=gha" in text
    assert "cache-to: type=gha" in text
    assert text.count("- name: Run canonical Docker-only E2E") == 1
    assert "-ImageSource ghcr" not in text
    assert "ANKI_E2E_IMAGE_SOURCE" in text


def test_workflow_uses_pinned_login_exact_digest_and_no_fallback() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    login = text[text.index("- name: Log in to GHCR") : text.index("- name: Pull and verify exact GHCR")]
    pull = text[text.index("- name: Pull and verify exact GHCR") : text.index("- name: Validate resolved Compose contract")]

    assert "docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121 # v4.1.0" in login
    assert "username: ${{ github.actor }}" in login
    assert "password: ${{ github.token }}" in login
    assert "secrets." not in login
    assert "docker pull --platform $env:EXPECTED_PLATFORM $env:EXACT_REFERENCE" in pull
    assert "RepoDigests" in pull
    assert "org.opencontainers.image.source" in pull
    assert "org.opencontainers.image.version" in pull
    assert "io.github.anki-study-report.e2e.environment-contract" in pull
    assert "docker build" not in pull
    assert "latest" not in pull.lower()
    assert "fallback" not in pull.lower()


def test_environment_provenance_is_separate_from_build_duration() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    evidence = text[text.index("- name: Publish sanitized environment image evidence") : text.index("- name: Capture final Docker state")]

    for field in (
        "imageSource",
        "imageReference",
        "imageDigest",
        "imagePlatform",
        "imagePreparationDurationMs",
        "imageSizeBytes",
        "environmentContractSha256",
        "environmentPublicationRunId",
        "environmentReuseVerificationRunId",
        "cacheState",
        "workflowSourceSha",
        "e2eCheckoutSha",
        "packageSource",
        "sourcePackageSha256",
    ):
        assert field in evidence
    assert "environment-image-provenance.json" in evidence
    pull = text[text.index("- name: Pull and verify exact GHCR") : text.index("- name: Validate resolved Compose contract")]
    assert "ANKI_E2E_BUILD_DURATION_MS=$duration" not in pull


def test_bootstrap_stages_only_current_regular_harness_files() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    assert text.startswith("#!/usr/bin/env bash\nset -Eeuo pipefail\n")
    assert 'readonly SOURCE_DIR="/workspace/docker/anki-e2e"' in text
    assert 'readonly DESTINATION_DIR="/e2e/bin"' in text
    assert "-type l" in text
    assert "-type f" in text
    assert "-name '*.sh'" in text
    assert "-name '*.py'" in text
    assert "-name '*.mjs'" in text
    assert "smoke-browser-core.mjs" in text
    assert "smoke-browser-wrapper.mjs" in text
    assert "tr -d '\\r'" in text
    assert "chmod 0755" in text
    assert "install -m 0755" in text
    assert "exec /e2e/bin/entrypoint.sh" in text
    for forbidden in ("curl ", "wget ", "git clone", "pnpm install", "npm install", ".ankiaddon"):
        assert forbidden not in text

    if sys.platform == "win32":
        pytest.skip("bootstrap Bash syntax is validated on Linux runners")
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is unavailable on this platform")
    result = subprocess.run([bash, "-n", str(BOOTSTRAP)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_ghcr_compose_override_preserves_base_security_boundary() -> None:
    base = BASE_COMPOSE.read_text(encoding="utf-8")
    override = GHCR_COMPOSE.read_text(encoding="utf-8")

    assert "../..:/workspace:ro" in base
    assert "./local-input:/e2e/local-input:ro" in base
    assert "${ANKI_E2E_IMAGE:?ANKI_E2E_IMAGE must be an exact digest reference}" in override
    assert "pull_policy: never" in override
    assert "/workspace/docker/anki-e2e/bootstrap-current-harness.sh" in override
    assert "/e2e/bin/run-e2e.sh" in override
    for forbidden in ("privileged:", "network_mode:", "/var/run/docker.sock", "cap_add:", "sha256:"):
        assert forbidden not in override


def test_wrapper_keeps_buildkit_default_and_fails_closed_for_ghcr() -> None:
    text = WRAPPER.read_text(encoding="utf-8")

    assert '[ValidateSet("buildkit", "ghcr")]' in text
    assert '[string]$ImageSource = "buildkit"' in text
    assert "$ComposeFiles = @($BaseComposeFile)" in text
    assert "$ComposeFiles += $GhcrComposeFile" in text
    assert "GHCR image source requires -NoBuild" in text
    assert "GHCR image source does not support -BuildOnly" in text
    assert "requires an exact digest reference in ANKI_E2E_IMAGE" in text
    assert "requires a prebuilt Fast CI or release artifact package" in text
    assert 'Invoke-DockerCompose @("config", "--quiet")' in text
    assert text.count("Invoke-DockerCompose $runArgs") == 1
    assert "Restore-E2EArtifactOwnership -Volume $volume" in text
    assert "docker pull" not in text


def test_release_consumer_remains_implicit_buildkit_with_package_read() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    call = text[text.index("  real-anki-gate:") : text.index("  github-draft:")]

    assert "uses: ./.github/workflows/ci-e2e.yml" in call
    assert "environment_image_source" not in call
    assert (
        "permissions:\n"
        "      contents: read\n"
        "      actions: read\n"
        "      packages: read\n"
    ) in call
    assert "packages: write" not in call
    assert "scope: full" in call
