import importlib.util
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_task_scope.py"
SPEC = importlib.util.spec_from_file_location("check_task_scope", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def test_exact_path_and_directory_rules():
    assert guard.matches("AGENTS.md", "AGENTS.md")
    assert guard.matches("docs/ai-handoff.md", "docs")
    assert guard.matches("docs/templates/task.toml", "docs/**")
    assert not guard.matches("README.md", "docs/**")


def test_forbidden_runtime_output_overrides_allowed_scope():
    unexpected, forbidden = guard.validate_paths(
        ["web-dashboard/dist/index.html", "docs/ai-handoff.md"],
        allowed_paths=["web-dashboard/**", "docs/**"],
    )
    assert unexpected == []
    assert forbidden == ["web-dashboard/dist/index.html"]


def test_unexpected_path_is_reported():
    unexpected, forbidden = guard.validate_paths(
        ["scripts/check_task_scope.py", "anki_study_report/dashboard_server.py"],
        allowed_paths=["scripts/check_task_scope.py"],
    )
    assert forbidden == []
    assert unexpected == ["anki_study_report/dashboard_server.py"]


def test_contract_requires_real_task_and_allowed_paths(tmp_path):
    contract = tmp_path / "task.toml"
    contract.write_text(
        """
schema_version = 1
task = "REPLACE: task"
mode = "codex"
track = "core"
branch = "agent/test"
base_ref = "origin/core"
allowed_paths = ["REPLACE/ME"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        guard.load_contract(contract)


def test_contract_loads_task_specific_values(tmp_path):
    contract = tmp_path / "task.toml"
    contract.write_text(
        """
schema_version = 1
task = "Add AI workflow guardrails"
mode = "codex"
track = "core"
branch = "agent/ai-workflow-guardrails"
base_ref = "origin/core"
allowed_paths = ["AGENTS.md", "docs/**"]
forbidden_paths = ["docs/private/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    loaded = guard.load_contract(contract)
    assert loaded.task == "Add AI workflow guardrails"
    assert loaded.mode == "codex"
    assert loaded.track == "core"
    assert loaded.branch == "agent/ai-workflow-guardrails"
    assert loaded.base_ref == "origin/core"
    assert loaded.allowed_paths == ("AGENTS.md", "docs/**")
    assert loaded.forbidden_paths == ("docs/private/**",)


def test_changed_paths_includes_committed_worktree_and_untracked(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    git("config", "user.email", "scope-guard@example.invalid")
    git("config", "user.name", "Scope Guard Test")
    (repository / "base.txt").write_text("base\n", encoding="utf-8")
    git("add", "base.txt")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")

    (repository / "committed.txt").write_text("committed\n", encoding="utf-8")
    git("add", "committed.txt")
    git("commit", "-m", "committed")

    (repository / "base.txt").write_text("worktree\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    monkeypatch.chdir(repository)
    assert guard.changed_paths(base) == [
        "base.txt",
        "committed.txt",
        "untracked.txt",
    ]


def test_changed_paths_includes_deleted_file(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    git("config", "user.email", "scope-guard@example.invalid")
    git("config", "user.name", "Scope Guard Test")
    deleted = repository / "deleted.txt"
    deleted.write_text("tracked\n", encoding="utf-8")
    git("add", "deleted.txt")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")

    deleted.unlink()
    git("add", "-u")
    git("commit", "-m", "delete")

    monkeypatch.chdir(repository)
    assert guard.changed_paths(base) == ["deleted.txt"]


def test_cli_rejects_wrong_current_branch(tmp_path, monkeypatch, capsys):
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    git("config", "user.email", "scope-guard@example.invalid")
    git("config", "user.name", "Scope Guard Test")
    (repository / "base.txt").write_text("base\n", encoding="utf-8")
    git("add", "base.txt")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")

    contract = repository / "task.toml"
    contract.write_text(
        f"""
schema_version = 1
task = "Reject a wrong branch"
mode = "codex"
track = "core"
branch = "different-branch"
base_ref = "{base}"
allowed_paths = ["base.txt"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(repository)
    assert guard.main(["--contract", str(contract)]) == 2
    assert "does not match contract branch" in capsys.readouterr().err


def test_cli_explicit_paths_pass_and_fail(tmp_path, capsys):
    contract = tmp_path / "task.toml"
    contract.write_text(
        """
schema_version = 1
task = "Guard a bounded change"
mode = "chatgpt"
track = "core"
branch = "agent/test"
base_ref = "origin/core"
allowed_paths = ["docs/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert guard.main(["--contract", str(contract), "--path", "docs/README.md"]) == 0
    assert "task-scope: PASS" in capsys.readouterr().out

    assert guard.main(["--contract", str(contract), "--path", "README.md"]) == 1
    captured = capsys.readouterr()
    assert "README.md" in captured.out
    assert "task-scope: FAIL" in captured.err
