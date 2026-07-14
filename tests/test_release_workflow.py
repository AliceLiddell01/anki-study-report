from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def job(text: str, name: str, next_name: str | None = None) -> str:
    start = text.index(f"  {name}:\n")
    end = text.index(f"  {next_name}:\n", start) if next_name else len(text)
    return text[start:end]


def test_pr_is_validation_only_and_dispatch_is_explicit() -> None:
    text = workflow_text()
    trigger = text[: text.index("permissions:")]
    assert "pull_request:" in trigger
    assert "workflow_dispatch:" in trigger
    assert "pull_request_target:" not in trigger
    assert "push:" not in trigger
    assert "refs/heads/master" in text
    assert "current origin/master" in text


def test_secrets_exist_only_in_approved_environment_job() -> None:
    text = workflow_text()
    publisher = job(text, "ankiweb-publish", "github-finalize")
    outside = text.replace(publisher, "")
    assert "environment: ankiweb-production" in publisher
    assert "secrets.ANKIWEB_EMAIL" in publisher
    assert "secrets.ANKIWEB_PASSWORD" in publisher
    assert "secrets." not in outside
    assert "contents: write" not in publisher


def test_exact_artifact_crosses_all_release_gates_by_sha256() -> None:
    text = workflow_text()
    assert "scripts/create_release_bundle.py" in text
    assert text.count("needs.build.outputs.artifact_sha256") >= 3
    assert "release_artifact_sha256:" in text
    assert "Get-FileHash -Algorithm SHA256" in text
    assert "subject-path: release-artifacts/anki_study_report.ankiaddon" in text
    assert "--artifact release-artifacts/anki_study_report.ankiaddon" in text


def test_real_anki_and_publication_order_are_gated() -> None:
    text = workflow_text()
    assert text.index("  real-anki-gate:") < text.index("  github-draft:")
    assert text.index("  github-draft:") < text.index("  ankiweb-publish:")
    assert text.index("  ankiweb-publish:") < text.index("  github-finalize:")
    gate = job(text, "real-anki-gate", "github-draft")
    assert "uses: ./.github/workflows/ci-e2e.yml" in gate
    assert "mode: standard" in gate
    assert "scope: full" in gate
    assert "release_artifact_name:" in gate


def test_every_external_action_is_pinned_to_a_full_commit() -> None:
    for line in workflow_text().splitlines():
        if "uses:" not in line or line.strip().endswith("ci-e2e.yml"):
            continue
        reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
        assert re.search(r"@[0-9a-f]{40}$", reference), line


def test_publisher_never_automates_new_branch_control() -> None:
    publisher = (ROOT / "scripts" / "publish_ankiweb.mjs").read_text(encoding="utf-8")
    assert 'name: "Add New Branch"' in publisher
    assert not re.search(r"add[_A-Za-z]*branch[^\n]*\.click\(", publisher, re.IGNORECASE)
    assert "mutationCount = 1" in publisher


def test_real_anki_runner_accepts_and_evidences_prebuilt_package() -> None:
    shell = (ROOT / "docker" / "anki-e2e" / "run-e2e.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci-e2e.yml").read_text(encoding="utf-8")
    assert "ANKI_E2E_PREBUILT_ADDON_PATH" in shell
    assert "package_addon.py" in shell
    assert "e2e-artifacts/package/anki_study_report.ankiaddon" in workflow
    assert "not the exact release artifact" in workflow
