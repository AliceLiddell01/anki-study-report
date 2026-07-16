from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docker" / "anki-e2e" / "environment-image-spec.json"
DOCKERFILE = ROOT / "docker" / "anki-e2e" / "environment.Dockerfile"
DOCKERIGNORE = ROOT / "docker" / "anki-e2e" / "environment.Dockerfile.dockerignore"
INSTALLER = ROOT / "docker" / "anki-e2e" / "install-anki.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "e2e-environment-image.yml"
CURRENT_E2E_WORKFLOW = ROOT / ".github" / "workflows" / "ci-e2e.yml"
CURRENT_DOCKERFILE = ROOT / "docker" / "anki-e2e" / "Dockerfile"
CURRENT_COMPOSE = ROOT / "docker" / "anki-e2e" / "docker-compose.yml"
BASE_DIGEST = "sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c"


def load_validator():
    path = ROOT / "scripts" / "validate_e2e_environment_image.py"
    spec = importlib.util.spec_from_file_location("validate_e2e_environment_image", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_environment_spec_is_canonical_and_exact() -> None:
    validator = load_validator()
    raw = SPEC.read_text(encoding="utf-8")
    value = json.loads(raw)

    assert raw == validator.canonical_json(value)
    assert validator.read_spec(SPEC) == validator.EXPECTED_SPEC
    assert validator.human_tag(value) == "env-v1-anki26.05-pw1.55.1"
    assert value["imageName"] == value["imageName"].lower()
    assert value["platform"] == "linux/amd64"
    assert value["playwrightBaseDigest"] == BASE_DIGEST


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schemaVersion", 0),
        ("environmentVersion", "env-v0"),
        ("imageName", "ghcr.io/AliceLiddell01/anki-study-report-e2e"),
        ("imageName", "ghcr.io/aliceliddell01/anki-study-report-e2e:latest"),
        ("platform", "linux/arm64"),
        ("playwrightImage", "mcr.microsoft.com/playwright:latest"),
        ("playwrightBaseDigest", "sha256:" + "0" * 64),
        ("playwrightVersion", "1.55.0"),
        ("ankiVersion", "26.04"),
        ("ankiArchiveSha256", "0" * 64),
        ("ankiPythonPackage", "anki==26.4"),
        ("pnpmVersion", "10.0.0"),
    ],
)
def test_environment_spec_rejects_contract_drift(tmp_path: Path, field: str, value: object) -> None:
    validator = load_validator()
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document[field] = value
    path = tmp_path / "spec.json"
    path.write_text(validator.canonical_json(document), encoding="utf-8")

    with pytest.raises(validator.EnvironmentImageError):
        validator.read_spec(path)


def test_environment_spec_rejects_extra_token_or_path_fields(tmp_path: Path) -> None:
    validator = load_validator()
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["token"] = "ghp_example"
    path = tmp_path / "spec.json"
    path.write_text(validator.canonical_json(document), encoding="utf-8")
    with pytest.raises(validator.EnvironmentImageError):
        validator.read_spec(path)

    document.pop("token")
    document["localPath"] = "C:/Users/example"
    path.write_text(validator.canonical_json(document), encoding="utf-8")
    with pytest.raises(validator.EnvironmentImageError):
        validator.read_spec(path)


def test_environment_dockerfile_is_environment_only_and_digest_pinned() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert text.startswith(
        "FROM mcr.microsoft.com/playwright:v1.55.1-noble@" + BASE_DIGEST + "\n"
    )
    assert "ARG ANKI_VERSION=26.05" in text
    assert "ARG ANKI_SHA256=6223d705563f71ab40ce072a5d96a3919c546d5dde1e4c49dc27975e70067274" in text
    assert "ENV ANKI_REQUIRE_SHA256=1" in text
    assert 'ARG ANKI_PYTHON_PACKAGE=anki==26.5' in text
    assert "ARG PNPM_VERSION=9.15.9" in text
    assert "ARG PLAYWRIGHT_VERSION=1.55.1" in text
    assert 'LABEL org.opencontainers.image.source="https://github.com/AliceLiddell01/anki-study-report"' in text
    assert "COPY docker/anki-e2e/install-anki.sh /e2e/bin/install-anki.sh" in text
    assert 'WORKDIR /workspace' in text
    assert 'CMD ["bash"]' in text
    assert "ENTRYPOINT" not in text

    forbidden = (
        "COPY .",
        ".ankiaddon",
        "web-dashboard/package.json",
        "pnpm-lock.yaml",
        "entrypoint.sh",
        "run-e2e.sh",
        "smoke-browser",
        "resource_monitor.py",
        "anki_study_report/",
        "GITHUB_TOKEN",
        "Authorization",
    )
    for value in forbidden:
        assert value not in text
    assert "COPY node_modules" not in text
    assert "web-dashboard/node_modules" not in text


@pytest.mark.parametrize(
    "path",
    [
        "/workspace",
        "/e2e/artifacts",
        "/e2e/anki-data",
        "/e2e/local-input",
        "/e2e/home",
    ],
)
def test_environment_dockerfile_creates_required_runtime_directories(path: str) -> None:
    assert path in DOCKERFILE.read_text(encoding="utf-8")


def test_dedicated_dockerignore_is_default_deny() -> None:
    lines = [line.strip() for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

    assert lines[0] == "**"
    assert lines == [
        "**",
        "!docker/",
        "!docker/anki-e2e/",
        "!docker/anki-e2e/environment.Dockerfile",
        "!docker/anki-e2e/install-anki.sh",
    ]
    serialized = "\n".join(lines).lower()
    assert ".git" not in serialized
    assert ".ankiaddon" not in serialized
    assert "web-dashboard" not in serialized
    assert "screenshots" not in serialized
    assert "cache" not in serialized


def test_contract_hash_is_deterministic_and_sensitive_to_inputs(tmp_path: Path) -> None:
    validator = load_validator()
    first = validator.compute_contract_hash(
        spec_path=SPEC,
        dockerfile_path=DOCKERFILE,
        dockerignore_path=DOCKERIGNORE,
        installer_path=INSTALLER,
    )
    second = validator.compute_contract_hash(
        spec_path=SPEC,
        dockerfile_path=DOCKERFILE,
        dockerignore_path=DOCKERIGNORE,
        installer_path=INSTALLER,
    )
    changed = tmp_path / "install-anki.sh"
    changed.write_bytes(INSTALLER.read_bytes() + b"\n# changed\n")
    third = validator.compute_contract_hash(
        spec_path=SPEC,
        dockerfile_path=DOCKERFILE,
        dockerignore_path=DOCKERIGNORE,
        installer_path=changed,
    )

    assert first == second
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", first)
    assert third != first


def test_producer_workflow_is_manual_only_with_minimal_permissions() -> None:
    text = workflow_text()
    trigger = text[text.index("on:\n") : text.index("permissions:\n")]
    permissions = text[text.index("permissions:\n") : text.index("concurrency:\n")]

    assert text.startswith("name: E2E Environment Image\n")
    assert trigger == "on:\n  workflow_dispatch:\n\n"
    assert "push:" not in trigger
    assert "pull_request:" not in trigger
    assert "schedule:" not in trigger
    assert permissions == (
        "permissions:\n"
        "  contents: read\n"
        "  packages: write\n"
        "  id-token: write\n"
        "  attestations: write\n\n"
    )
    assert "actions: write" not in text
    assert "contents: write" not in text
    assert "artifact-metadata: write" not in text
    assert "secrets." not in text


def test_producer_workflow_actions_are_full_sha_pinned() -> None:
    for line in workflow_text().splitlines():
        if "uses:" not in line:
            continue
        reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
        assert re.search(r"@[0-9a-f]{40}$", reference), line


def test_producer_workflow_uses_ghcr_digest_attestation_and_roundtrip() -> None:
    text = workflow_text()

    assert "runs-on: ubuntu-24.04" in text
    assert "registry: ghcr.io" in text
    assert "username: ${{ github.actor }}" in text
    assert "password: ${{ github.token }}" in text
    assert "platforms: linux/amd64" in text
    assert "push: true" in text
    assert "steps.build.outputs.digest" in text
    assert "subject-name: ${{ steps.spec.outputs.image_name }}" in text
    assert "subject-digest: ${{ steps.image.outputs.image_digest }}" in text
    assert "push-to-registry: true" in text
    assert "create-storage-record: false" in text
    assert "docker pull \"$EXACT_REFERENCE\"" in text
    assert "docker buildx imagetools inspect \"$EXACT_REFERENCE\"" in text
    assert "org.opencontainers.image.source=https://github.com/AliceLiddell01/anki-study-report" in text
    assert "io.github.anki-study-report.e2e.environment-contract=" in text


def test_producer_workflow_has_fail_closed_tag_collision_and_no_mutable_latest() -> None:
    text = workflow_text()

    assert "Check deterministic tag collision" in text
    assert "publish_required=false" in text
    assert "publish_required=true" in text
    assert "Deterministic tag collision" in text
    assert "expected $EXPECTED_CONTRACT" in text
    assert "flavor: latest=false" in text
    assert "type=raw,value=${{ steps.spec.outputs.human_tag }}" in text
    assert ":latest" not in text
    assert "cache-from:" not in text
    assert "cache-to:" not in text
    assert "type=gha" not in text


def test_producer_workflow_smokes_runtime_and_boundary_without_e2e() -> None:
    text = workflow_text()

    for required in (
        "python3 --version",
        'version(\\"anki\\") == \\"26.5\\"',
        "node --version",
        "pnpm --version",
        "playwright/package.json",
        "chromium.launch({ headless: true })",
        "xvfb-run",
        "find /workspace -mindepth 1",
        'find /e2e -type f -name "*.ankiaddon"',
        "type=bind,src=${GITHUB_WORKSPACE},dst=/workspace,readonly",
        "dst=/e2e/local-input/anki_study_report.ankiaddon,readonly",
    ):
        assert required in text
    assert "run_full_check.ps1" not in text
    assert "run_anki_e2e_docker.ps1" not in text
    assert "docker compose" not in text
    assert "release.yml" not in text


def valid_metadata(validator, spec: dict[str, object]) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "repository": "AliceLiddell01/anki-study-report",
        "workflowName": "E2E Environment Image",
        "workflowPath": ".github/workflows/e2e-environment-image.yml",
        "producerJob": "environment-image",
        "sourceCommitSha": "a" * 40,
        "imageRevision": "b" * 40,
        "runId": 123,
        "runAttempt": 1,
        "imageName": spec["imageName"],
        "humanTag": validator.human_tag(spec),
        "imageDigest": "sha256:" + "c" * 64,
        "platform": spec["platform"],
        "environmentVersion": spec["environmentVersion"],
        "environmentContractSha256": "sha256:" + "d" * 64,
        "playwrightBaseDigest": spec["playwrightBaseDigest"],
        "attestationStatus": "created",
        "smokeStatus": "success",
        "createdAt": "2026-07-17T00:00:00Z",
        "environmentSpec": spec,
    }


def test_published_metadata_validation_and_markdown_are_deterministic(tmp_path: Path) -> None:
    validator = load_validator()
    spec = validator.read_spec(SPEC)
    metadata = valid_metadata(validator, spec)
    path = tmp_path / "metadata.json"
    path.write_text(validator.canonical_json(metadata), encoding="utf-8")

    validated = validator.read_published_metadata(path, spec)
    first = validator.render_markdown(validated)
    second = validator.render_markdown(validated)

    assert first == second
    assert f"{spec['imageName']}@{metadata['imageDigest']}" in first
    assert f"{spec['imageName']}:{validator.human_tag(spec)}" in first
    assert "Consumers must use the exact digest reference" in first


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("imageDigest", ""),
        ("imageDigest", "sha256:" + "z" * 64),
        ("platform", "linux/arm64"),
        ("sourceCommitSha", "a" * 39),
        ("playwrightBaseDigest", "sha256:" + "0" * 64),
        ("environmentVersion", "env-v2"),
        ("attestationStatus", "unknown"),
        ("smokeStatus", "not-run"),
    ],
)
def test_published_metadata_rejects_invalid_identity(
    tmp_path: Path, field: str, value: object
) -> None:
    validator = load_validator()
    spec = validator.read_spec(SPEC)
    metadata = valid_metadata(validator, spec)
    metadata[field] = value
    path = tmp_path / "metadata.json"
    path.write_text(validator.canonical_json(metadata), encoding="utf-8")

    with pytest.raises(validator.EnvironmentImageError):
        validator.read_published_metadata(path, spec)


def test_metadata_writes_are_atomic_and_leave_no_temporary_files(tmp_path: Path) -> None:
    validator = load_validator()
    spec = validator.read_spec(SPEC)
    output = tmp_path / "nested" / "metadata.json"
    validator.create_published_metadata(
        spec=spec,
        output=output,
        source_commit_sha="a" * 40,
        image_revision="b" * 40,
        run_id=123,
        run_attempt=1,
        image_digest="sha256:" + "c" * 64,
        environment_contract_sha256="sha256:" + "d" * 64,
        attestation_status="created",
        created_at="2026-07-17T00:00:00Z",
    )

    assert output.is_file()
    assert not output.with_name(f".{output.name}.tmp").exists()
    validator.read_published_metadata(output, spec)


def test_existing_e2e_consumer_and_cache_contract_remain_current() -> None:
    workflow = CURRENT_E2E_WORKFLOW.read_text(encoding="utf-8")
    dockerfile = CURRENT_DOCKERFILE.read_text(encoding="utf-8")
    compose = CURRENT_COMPOSE.read_text(encoding="utf-8")

    assert "name: Full Docker / Anki E2E" in workflow
    assert "file: docker/anki-e2e/Dockerfile" in workflow
    assert "cache-from: type=gha" in workflow
    assert "cache-to: type=gha" in workflow
    assert "ghcr.io" not in workflow.lower()
    assert dockerfile.startswith("FROM mcr.microsoft.com/playwright:v1.55.1-noble\n")
    assert 'ENTRYPOINT ["/e2e/bin/entrypoint.sh"]' in dockerfile
    assert "image: ${ANKI_E2E_IMAGE:-anki-study-report-e2e:local}" in compose
    assert "- ../..:/workspace:ro" in compose
    assert "- ./local-input:/e2e/local-input:ro" in compose
    assert "- ../../e2e-artifacts:/e2e/artifacts" in compose
