from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-fast.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def verification_step(text: str) -> str:
    start = text.index("      - name: Publish verification plan")
    end = text.index("      - name: Collect non-release package", start)
    return text[start:end]


def test_pull_requests_plan_against_the_complete_base_branch_diff() -> None:
    step = verification_step(workflow_text())

    assert '$eventName = "${{ github.event_name }}"' in step
    assert "$eventName -eq 'pull_request'" in step
    assert '$baseRef = "${{ github.base_ref }}"' in step
    assert '$base = "origin/$baseBranch"' in step

    pull_request_branch = step.index("$eventName -eq 'pull_request'")
    before_lookup = step.index("git cat-file -e")
    assert pull_request_branch < before_lookup


def test_feature_branch_pushes_plan_the_full_branch_not_only_event_before() -> None:
    step = verification_step(workflow_text())

    assert "$refName -ne $defaultBranch" in step
    assert '$base = "origin/$defaultBranch"' in step
    assert "complete branch risk" in step


def test_default_branch_push_retains_safe_before_fallback() -> None:
    step = verification_step(workflow_text())

    assert '$before = "${{ github.event.before }}"' in step
    assert 'git cat-file -e "${before}^{commit}"' in step
    assert "if (-not $base) { $base = 'HEAD^' }" in step
