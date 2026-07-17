from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-e2e.yml"
RUNNER = ROOT / "scripts" / "run_anki_e2e_docker.ps1"
CONTAINER = ROOT / "docker" / "anki-e2e" / "run-e2e.sh"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def step(text: str, name: str, next_name: str | None = None) -> str:
    start = text.index(f"      - name: {name}\n")
    end = text.index(f"      - name: {next_name}\n", start) if next_name else len(text)
    return text[start:end]


def test_workflow_identity_triggers_inputs_and_job_name_are_ghcr_only() -> None:
    text = workflow_text()
    trigger = text[: text.index("permissions:")]

    assert text.startswith("name: Full Docker / Anki E2E\n")
    assert "workflow_call:" in trigger
    assert "workflow_dispatch:" in trigger
    assert "workflow_run:" not in trigger
    assert "pull_request_target:" not in trigger
    assert trigger.count("fast_ci_run_id:") == 2
    assert "environment_image_source" not in trigger
    assert "Exact successful Fast CI run ID for this branch commit" in trigger
    assert "release_artifact_name:" in trigger
    assert "release_artifact_sha256:" in trigger
    assert "name: Real Anki Desktop (${{ inputs.mode || 'standard' }} / ${{ inputs.scope || 'stats' }})" in text
    concurrency = text[text.index("concurrency:") : text.index("jobs:")]
    assert "environment" not in concurrency.lower()


def test_permissions_are_read_only_and_include_cross_run_and_package_read() -> None:
    text = workflow_text()
    permissions = text[text.index("permissions:") : text.index("concurrency:")]

    assert permissions == "permissions:\n  contents: read\n  actions: read\n  packages: read\n\n"
    assert "contents: write" not in text
    assert "packages: write" not in text
    assert "id-token: write" not in text
    assert "attestations: write" not in text
    assert "secrets." not in text
    assert "github_pat" not in text.lower()
    assert "ghp_" not in text.lower()


def test_package_source_inputs_fail_closed_before_registry_work() -> None:
    text = workflow_text()
    validation = step(
        text,
        "Capture workflow source and validate package source inputs",
        "Resolve exact successful Fast CI run and artifact IDs",
    )

    assert "validate-inputs" in validation
    assert "--release-artifact-name" in validation
    assert "--release-artifact-sha256" in validation
    assert "--fast-ci-run-id" in validation
    assert "E2E_WORKFLOW_SOURCE_SHA=${{ github.sha }}" in validation
    assert "Cloud E2E requires an exact prebuilt Fast CI or release artifact package" in validation
    assert "Manual cloud E2E requires fast_ci_run_id" in validation
    assert "source.packageSource -eq 'source-build'" in validation
    assert text.index("Capture workflow source and validate package source inputs") < text.index("Log in to GHCR")


def test_fast_run_is_resolved_by_api_and_artifacts_are_downloaded_by_id() -> None:
    text = workflow_text()
    resolve = step(text, "Resolve exact successful Fast CI run and artifact IDs", "Download exact Fast CI diagnostics by artifact ID")
    diagnostics = step(text, "Download exact Fast CI diagnostics by artifact ID", "Validate Fast CI diagnostics and derive tested commit")
    package = step(text, "Download exact Fast CI package by artifact ID", "Validate and stage exact Fast CI package")

    assert "GH_TOKEN: ${{ github.token }}" in resolve
    assert "actions/runs/$env:FAST_CI_RUN_ID_INPUT" in resolve
    assert "artifacts?per_page=100" in resolve
    assert "verify_fast_ci_e2e_handoff.py resolve-run" in resolve
    for block, output in ((diagnostics, "diagnostics_artifact_id"), (package, "package_artifact_id")):
        assert f"artifact-ids: ${{{{ steps.resolve_fast_ci.outputs.{output} }}}}" in block
        assert "github-token: ${{ github.token }}" in block
        assert "repository: ${{ github.repository }}" in block
        assert "run-id: ${{ steps.resolve_fast_ci.outputs.source_run_id }}" in block
        assert "merge-multiple: true" in block
        assert "digest-mismatch: error" in block
        assert "name:" not in block.split("with:", 1)[1]


def test_diagnostics_precedes_exact_checkout_and_package_download_follows_it() -> None:
    text = workflow_text()
    diagnostics_download = text.index("Download exact Fast CI diagnostics by artifact ID")
    diagnostics_validation = text.index("Validate Fast CI diagnostics and derive tested commit")
    exact_checkout = text.index("Check out exact Fast CI tested commit")
    checkout_validation = text.index("Verify exact tested commit checkout")
    package_download = text.index("Download exact Fast CI package by artifact ID")
    package_validation = text.index("Validate and stage exact Fast CI package")

    assert diagnostics_download < diagnostics_validation < exact_checkout < checkout_validation < package_download < package_validation
    checkout = step(text, "Check out exact Fast CI tested commit", "Verify exact tested commit checkout")
    assert "ref: ${{ steps.fast_diagnostics.outputs.tested_sha }}" in checkout
    assert "persist-credentials: false" in checkout
    assert "fetch-depth: 0" in checkout
    verify = step(text, "Verify exact tested commit checkout", "Download exact Fast CI package by artifact ID")
    assert "git rev-parse HEAD" in verify
    assert "E2E_CHECKOUT_SHA=$actual" in verify


def test_fast_package_validation_binds_source_head_and_stages_prebuilt_env() -> None:
    text = workflow_text()
    block = step(text, "Validate and stage exact Fast CI package", "Download exact release artifact")

    assert "write_ci_package_metadata.py --verify-only" in block
    assert "verify_fast_ci_e2e_handoff.py validate-package" in block
    assert "--e2e-workflow-source-sha $env:E2E_WORKFLOW_SOURCE_SHA" in block
    assert "--e2e-checkout-sha $checkoutSha" in block
    assert "docker/anki-e2e/local-input/anki_study_report.ankiaddon" in block
    assert "ANKI_E2E_PREBUILT_ADDON_PATH=/e2e/local-input/anki_study_report.ankiaddon" in block
    assert "ANKI_E2E_PACKAGE_SOURCE=fast-ci-artifact" in block
    assert "ANKI_E2E_FAST_CI_RUN_ID" in block
    assert "ANKI_E2E_FAST_CI_TESTED_SHA" in block
    assert "ANKI_E2E_FAST_CI_PACKAGE_SHA256" in block


def test_release_current_run_path_and_local_source_build_remain_separate() -> None:
    text = workflow_text()
    release_download = step(text, "Download exact release artifact", "Stage and verify exact release artifact")
    release_stage = step(text, "Stage and verify exact release artifact", "Capture runner and Docker preflight")

    assert "if: steps.source_mode.outputs.package_source == 'release-artifact'" in release_download
    assert "name: ${{ inputs.release_artifact_name }}" in release_download
    assert "github-token:" not in release_download
    assert "run-id:" not in release_download
    assert "artifact-ids:" not in release_download
    assert "Get-FileHash -Algorithm SHA256" in release_stage
    assert "ANKI_E2E_PACKAGE_SOURCE=release-artifact" in release_stage

    shell = CONTAINER.read_text(encoding="utf-8")
    assert 'case "$ANKI_E2E_PACKAGE_SOURCE" in source-build|fast-ci-artifact|release-artifact)' in shell
    assert 'if [ -z "$ANKI_E2E_PREBUILT_ADDON_PATH" ] && [ "$ANKI_E2E_PACKAGE_SOURCE" != "source-build" ]; then' in shell
    assert 'if [ -n "$ANKI_E2E_PREBUILT_ADDON_PATH" ]; then' in shell
    assert "install --offline --frozen-lockfile" in shell
    assert 'phase_end "frontend build"' in shell
    assert 'phase_end "add-on package"' in shell


def test_prebuilt_wording_and_phase_semantics_are_generic() -> None:
    shell = CONTAINER.read_text(encoding="utf-8")

    assert 'section "Validate exact prebuilt add-on artifact"' in shell
    assert 'phase_end "exact prebuilt add-on validation and extraction"' in shell
    assert "exact prebuilt release artifact" not in shell
    assert "exact release add-on validation and extraction" not in shell


def test_runner_forwards_only_safe_package_and_image_identity_not_github_token() -> None:
    runner = RUNNER.read_text(encoding="utf-8")

    for name in (
        "ANKI_E2E_IMAGE_SOURCE",
        "ANKI_E2E_PREBUILT_ADDON_PATH",
        "ANKI_E2E_PACKAGE_SOURCE",
        "ANKI_E2E_FAST_CI_RUN_ID",
        "ANKI_E2E_FAST_CI_TESTED_SHA",
        "ANKI_E2E_FAST_CI_PACKAGE_SHA256",
    ):
        assert name in runner
    assert "GH_TOKEN" not in runner
    assert "GITHUB_TOKEN" not in runner
    assert "fast-ci-run.json" not in runner
    assert "fast-ci-diagnostics" not in runner


def test_cloud_buildkit_and_gha_cache_contour_is_removed() -> None:
    text = workflow_text()

    for forbidden in (
        "environment_image_source",
        "Enable containerd image store",
        "setup-buildx-action",
        "build-push-action",
        "cache-from",
        "cache-to",
        "type=gha",
        "containerd-snapshotter",
        "anki-study-report-e2e:ci",
        "gha-enabled",
    ):
        assert forbidden not in text
    assert "compression-level: 0" in text
    assert text.count("- name: Run canonical Docker-only E2E") == 1
    assert '"ANKI_E2E_BUILD_DURATION_MS=0"' in text
    assert '"ANKI_E2E_IMAGE_SOURCE=ghcr"' in text
    assert '"ANKI_E2E_CACHE_BACKEND=ghcr-digest"' in text


def test_ghcr_preparation_and_compose_are_unconditional() -> None:
    text = workflow_text()
    lock = step(text, "Validate environment consumer lock", "Expose exact GHCR environment identity")
    identity = step(text, "Expose exact GHCR environment identity", "Log in to GHCR")
    login = step(text, "Log in to GHCR", "Pull and verify exact GHCR environment image")
    pull = step(text, "Pull and verify exact GHCR environment image", "Validate resolved GHCR Compose contract")
    compose = step(text, "Validate resolved GHCR Compose contract", "Run canonical Docker-only E2E")

    for block in (lock, identity, login, pull):
        assert "if: env.ANKI_E2E_IMAGE_SOURCE" not in block
    assert "ANKI_E2E_IMAGE=$env:EXACT_REFERENCE" in identity
    assert "ANKI_E2E_IMAGE_REFERENCE=$env:EXACT_REFERENCE" in identity
    assert "ANKI_E2E_IMAGE_DIGEST=$env:EXPECTED_DIGEST" in identity
    assert "ANKI_E2E_ENVIRONMENT_CONTRACT_SHA256=$env:EXPECTED_CONTRACT" in identity
    assert "docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121 # v4.1.0" in login
    assert "password: ${{ github.token }}" in login
    assert "docker pull --platform $env:EXPECTED_PLATFORM $env:EXACT_REFERENCE" in pull
    assert "RepoDigests" in pull
    assert "docker-compose.yml" in compose
    assert "docker-compose.ghcr.yml" in compose
    assert "if ($env:ANKI_E2E_IMAGE_SOURCE" not in compose


def test_safe_handoff_and_environment_evidence_are_exported_without_raw_api_payloads() -> None:
    text = workflow_text()
    publish = step(text, "Publish sanitized Fast CI handoff evidence", "Publish sanitized environment image evidence")
    environment = step(text, "Publish sanitized environment image evidence", "Capture final Docker state")
    export = step(text, "Prepare redacted public E2E artifact", "Start artifact upload timing")

    assert "fast-ci-handoff.json" in publish
    assert "e2e-artifacts/reports/fast-ci-handoff.json" in publish
    assert "fast-ci-run.json" not in publish
    assert "fast-ci-artifacts.json" not in publish
    assert "environment-image-provenance.json" in environment
    assert "imagePreparationDurationMs" in environment
    assert "sourcePackageSha256" in environment
    assert "token" not in environment.lower()
    assert "--package-source" in export
    assert "--source-fast-ci-run-id" in export
    assert "--source-fast-ci-tested-sha" in export
    assert "--source-package-sha256" in export
    assert "--e2e-checkout-sha" in export


def test_every_external_action_is_pinned_to_a_full_commit() -> None:
    for line in workflow_text().splitlines():
        if "uses:" not in line:
            continue
        reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
        assert re.search(r"@[0-9a-f]{40}$", reference), line
