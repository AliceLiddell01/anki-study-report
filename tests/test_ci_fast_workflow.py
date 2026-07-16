from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-fast.yml"
SUMMARY_SCRIPT = ROOT / "scripts" / "write_ci_fast_summary.ps1"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def step(text: str, name: str, next_name: str | None = None) -> str:
    start = text.index(f"      - name: {name}\n")
    end = text.index(f"      - name: {next_name}\n", start) if next_name else len(text)
    return text[start:end]


def verification_step(text: str) -> str:
    return step(text, "Publish verification plan", "Write CI summary")


def test_workflow_identity_triggers_and_canonical_command_are_preserved() -> None:
    text = workflow_text()
    trigger = text[: text.index("permissions:")]

    assert text.startswith("name: Fast CI\n")
    assert "  fast:\n    name: Frontend, Python and package" in text
    assert "push:" in trigger
    assert "      - master" in trigger
    assert "pull_request:" in trigger
    assert "workflow_dispatch:" in trigger
    assert "workflow_run:" not in text
    assert r"& .\scripts\run_full_check.ps1 -SkipDocker" in text
    assert "cache: pip" in text
    assert "cache: pnpm" in text
    assert "cancel-in-progress: true" in text


def test_pull_requests_plan_against_the_complete_base_branch_diff() -> None:
    plan = verification_step(workflow_text())

    assert '$eventName = "${{ github.event_name }}"' in plan
    assert "$eventName -eq 'pull_request'" in plan
    assert '$baseRef = "${{ github.base_ref }}"' in plan
    assert '$base = "origin/$baseBranch"' in plan

    pull_request_branch = plan.index("$eventName -eq 'pull_request'")
    before_lookup = plan.index("git cat-file -e")
    assert pull_request_branch < before_lookup


def test_feature_branch_pushes_plan_the_full_branch_not_only_event_before() -> None:
    plan = verification_step(workflow_text())

    assert "$refName -ne $defaultBranch" in plan
    assert '$base = "origin/$defaultBranch"' in plan
    assert "complete branch risk" in plan


def test_default_branch_push_retains_safe_before_fallback() -> None:
    plan = verification_step(workflow_text())

    assert '$before = "${{ github.event.before }}"' in plan
    assert 'git cat-file -e "${before}^{commit}"' in plan
    assert "if (-not $base) { $base = 'HEAD^' }" in plan


def test_diagnostics_artifact_remains_always_available_and_contains_no_package() -> None:
    text = workflow_text()
    prepare = step(text, "Prepare diagnostics", "Install Python dependencies")
    diagnostics = step(text, "Upload Fast CI diagnostics", "Upload exact Fast CI package")

    assert "ci-fast/logs" in prepare
    assert "ci-fast/package" not in prepare
    assert "if: always()" in diagnostics
    assert "name: ci-fast-${{ github.run_id }}-${{ github.run_attempt }}" in diagnostics
    assert "path: ci-fast/" in diagnostics
    assert "if-no-files-found: error" in diagnostics
    assert "retention-days: 14" in diagnostics
    assert "anki_study_report-ci.ankiaddon" not in text
    assert "Collect non-release package" not in text


def test_exact_package_preparation_preserves_commit_identity_fields() -> None:
    text = workflow_text()
    prepare = step(text, "Prepare exact Fast CI package", "Upload Fast CI diagnostics")

    assert "if: success()" in prepare
    assert "scripts/write_ci_package_metadata.py" in prepare
    assert "--package anki_study_report.ankiaddon" in prepare
    assert "--output-directory ci-package" in prepare
    assert "--output ci-package/anki_study_report.ankiaddon --check-only" in prepare
    assert "--verify-only --output-directory ci-package" in prepare
    assert "TESTED_COMMIT_SHA: ${{ github.sha }}" in prepare
    assert "github.event.pull_request.head.sha || github.sha" in prepare
    assert "github.event.pull_request.base.sha || 'null'" in prepare
    assert "SOURCE_HEAD_SHA" in prepare
    assert "SOURCE_BASE_SHA" in prepare
    assert "ci-e2e.yml" not in prepare
    assert "release.yml" not in prepare


def test_exact_package_upload_is_success_only_and_uses_immutable_unique_name() -> None:
    text = workflow_text()
    upload = step(text, "Upload exact Fast CI package", "Summarize exact Fast CI package")

    assert "id: upload_ci_package" in upload
    assert "if: success()" in upload
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in upload
    assert "name: ci-package-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}" in upload
    assert "path: ci-package/" in upload
    assert "if-no-files-found: error" in upload
    assert "retention-days: 7" in upload
    assert "overwrite:" not in upload
    assert "include-hidden-files:" not in upload
    assert "compression-level:" not in upload


def test_package_summary_distinguishes_inner_and_transport_digests_without_url() -> None:
    summary = step(workflow_text(), "Summarize exact Fast CI package")

    assert "steps.upload_ci_package.outputs.artifact-id" in summary
    assert "steps.upload_ci_package.outputs.artifact-digest" in summary
    assert "packageSha256" in summary
    assert "testedCommitSha" in summary
    assert "sourceHeadSha" in summary
    assert "artifact-url" not in summary
    assert "GITHUB_STEP_SUMMARY" in summary


def test_fast_summary_script_describes_diagnostics_only() -> None:
    text = SUMMARY_SCRIPT.read_text(encoding="utf-8")

    assert 'Join-Path $OutputPath "package"' not in text
    assert "package/`` is a non-release" not in text
    assert "diagnostics artifact contains logs" in text
    assert "published separately" in text
    assert "artifactFiles = $artifactFiles" in text
    assert "schemaVersion = 1" in text


def test_fast_workflow_does_not_invoke_release_or_e2e_workflows() -> None:
    text = workflow_text()

    assert "uses: ./.github/workflows/ci-e2e.yml" not in text
    assert "release_artifact_name" not in text
    assert "workflow_run:" not in text
    assert "repository_dispatch:" not in text
    assert "attest" not in text.lower()


def test_every_external_action_is_pinned_to_a_full_commit() -> None:
    for line in workflow_text().splitlines():
        if "uses:" not in line:
            continue
        reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
        assert re.search(r"@[0-9a-f]{40}$", reference), line
