from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "codex-environment-preflight.sh"
REAL_GIT = Path(shutil.which("git") or "/usr/bin/git").resolve()

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Codex preflight targets Linux/WSL")


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@dataclass
class Fixture:
    root: Path
    source: Path
    worktree: Path
    fake_bin: Path
    global_config: Path

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "CODEX_SOURCE_TREE_PATH": str(self.source),
                "CODEX_WORKTREE_PATH": str(self.worktree),
                "GIT_CONFIG_GLOBAL": str(self.global_config),
                "GIT_CONFIG_NOSYSTEM": "1",
                "LC_ALL": "C.UTF-8",
            }
        )
        env.pop("GIT_SSH", None)
        env.pop("GIT_SSH_COMMAND", None)
        return env

    def preflight(self, *args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return run(
            "bash",
            str(SCRIPT),
            *args,
            cwd=cwd or self.worktree,
            env=env or self.env(),
            check=False,
        )


@pytest.fixture
def repo_fixture() -> Fixture:
    root = Path(tempfile.mkdtemp(prefix="codex-preflight-", dir=Path.home()))
    source = root / "source"
    worktree = root / "worktree"
    fake_bin = root / "bin"
    home = root / "home"
    fake_bin.mkdir(parents=True)
    home.mkdir()
    global_config = root / "global.gitconfig"
    global_config.write_text("", encoding="utf-8")

    run(str(REAL_GIT), "init", "-b", "core", str(source))
    run(str(REAL_GIT), "-C", str(source), "config", "user.name", "Preflight Test")
    run(str(REAL_GIT), "-C", str(source), "config", "user.email", "preflight@example.invalid")
    (source / "web-dashboard").mkdir()
    (source / "web-dashboard" / "package.json").write_text(
        '{\n  "engines": {"node": ">=20 <25", "pnpm": "9.x"}\n}\n',
        encoding="utf-8",
    )
    (source / ".python-version").write_text("3.11\n", encoding="utf-8")
    (source / "tracked.txt").write_text("clean\n", encoding="utf-8")
    run(str(REAL_GIT), "-C", str(source), "add", ".")
    run(str(REAL_GIT), "-C", str(source), "commit", "-m", "fixture")
    run(
        str(REAL_GIT),
        "-C",
        str(source),
        "remote",
        "add",
        "origin",
        "https://github.com/AliceLiddell01/anki-study-report.git",
    )
    head = run(str(REAL_GIT), "-C", str(source), "rev-parse", "HEAD").stdout.strip()
    run(str(REAL_GIT), "-C", str(source), "update-ref", "refs/remotes/origin/core", head)
    run(str(REAL_GIT), "-C", str(source), "worktree", "add", "-b", "task", str(worktree), "core")

    write_executable(fake_bin / "node", "#!/usr/bin/env bash\necho v20.20.2\n")
    write_executable(fake_bin / "pnpm", "#!/usr/bin/env bash\necho 9.15.9\n")
    write_executable(fake_bin / "uv", "#!/usr/bin/env bash\necho 'uv 0.8.0'\n")
    write_executable(fake_bin / "docker", "#!/usr/bin/env bash\necho 'Docker version 29.0.0'\n")
    write_executable(fake_bin / "pwsh", "#!/usr/bin/env bash\necho 'PowerShell 7.5.0'\n")
    write_executable(
        fake_bin / "gh",
        "#!/usr/bin/env bash\n"
        "if [[ ${1:-} == auth && ${2:-} == status ]]; then exit 0; fi\n"
        "echo 'gh version 2.0.0'\n",
    )

    fixture = Fixture(root, source, worktree, fake_bin, global_config)
    try:
        yield fixture
    finally:
        subprocess.run([str(REAL_GIT), "-C", str(source), "worktree", "remove", "--force", str(worktree)], check=False)
        shutil.rmtree(root, ignore_errors=True)


def assert_blocked(result: subprocess.CompletedProcess[str], code: int, text: str) -> None:
    assert result.returncode == code, result.stdout
    assert "Codex environment preflight: BLOCKED" in result.stdout
    assert text in result.stdout


def test_pass_offline_clean_linux_environment(repo_fixture: Fixture) -> None:
    result = repo_fixture.preflight("--offline", "--require-clean")
    assert result.returncode == 0, result.stdout
    assert "Codex environment preflight: PASS" in result.stdout
    assert "filesystem: native-linux" in result.stdout
    assert "repository: AliceLiddell01/anki-study-report" in result.stdout
    assert "git_fetch: OFFLINE" in result.stdout
    assert "dirty_state: CLEAN" in result.stdout


@pytest.mark.parametrize("name", ["CODEX_WORKTREE_PATH", "CODEX_SOURCE_TREE_PATH"])
def test_missing_required_path_variable_blocks(repo_fixture: Fixture, name: str) -> None:
    env = repo_fixture.env()
    env.pop(name)
    result = repo_fixture.preflight("--offline", cwd=repo_fixture.worktree, env=env)
    assert_blocked(result, 2, f"{name} is not set")


@pytest.mark.parametrize("name", ["CODEX_WORKTREE_PATH", "CODEX_SOURCE_TREE_PATH"])
def test_mounted_windows_path_blocks_before_repository_access(repo_fixture: Fixture, name: str) -> None:
    env = repo_fixture.env()
    env[name] = "/mnt/c/Users/KykLa/project"
    result = repo_fixture.preflight("--offline", env=env)
    assert_blocked(result, 2, name)


def test_symlink_resolving_into_mounted_windows_path_blocks(repo_fixture: Fixture) -> None:
    link = repo_fixture.root / "mounted-link"
    link.symlink_to("/mnt/c/Users/KykLa/project", target_is_directory=True)
    env = repo_fixture.env()
    env["CODEX_WORKTREE_PATH"] = str(link)
    result = repo_fixture.preflight("--offline", env=env)
    assert_blocked(result, 2, "must resolve under /home")


def test_git_executable_resolving_to_exe_blocks(repo_fixture: Fixture) -> None:
    windows_git = repo_fixture.root / "tools" / "git.exe"
    windows_git.parent.mkdir()
    write_executable(windows_git, "#!/usr/bin/env bash\nexit 0\n")
    (repo_fixture.fake_bin / "git").symlink_to(windows_git)
    result = repo_fixture.preflight("--offline")
    assert_blocked(result, 2, "git resolves to a Windows executable")


def test_pnpm_executable_resolving_to_cmd_blocks(repo_fixture: Fixture) -> None:
    windows_pnpm = repo_fixture.root / "tools" / "pnpm.cmd"
    windows_pnpm.parent.mkdir()
    write_executable(windows_pnpm, "#!/usr/bin/env bash\nexit 0\n")
    (repo_fixture.fake_bin / "pnpm").unlink()
    (repo_fixture.fake_bin / "pnpm").symlink_to(windows_pnpm)
    result = repo_fixture.preflight("--offline")
    assert_blocked(result, 2, "pnpm resolves to a Windows executable")


def test_repository_local_windows_ssh_override_blocks(repo_fixture: Fixture) -> None:
    run(str(REAL_GIT), "-C", str(repo_fixture.worktree), "config", "--local", "core.sshCommand", "C:/Windows/System32/OpenSSH/ssh.exe")
    result = repo_fixture.preflight("--offline")
    assert_blocked(result, 2, "repository-local core.sshCommand")


def test_windows_git_ssh_command_environment_blocks(repo_fixture: Fixture) -> None:
    env = repo_fixture.env()
    env["GIT_SSH_COMMAND"] = "/mnt/c/Windows/System32/OpenSSH/ssh.exe -i key"
    result = repo_fixture.preflight("--offline", env=env)
    assert_blocked(result, 2, "GIT_SSH_COMMAND")


def test_wrong_repository_identity_blocks(repo_fixture: Fixture) -> None:
    run(str(REAL_GIT), "-C", str(repo_fixture.source), "remote", "set-url", "origin", "https://github.com/example/wrong.git")
    result = repo_fixture.preflight("--offline")
    assert_blocked(result, 4, "unexpected repository identity")


def test_current_git_root_must_equal_declared_worktree(repo_fixture: Fixture) -> None:
    result = repo_fixture.preflight("--offline", cwd=repo_fixture.source)
    assert_blocked(result, 4, "current Git root differs")


@pytest.mark.parametrize("untracked", [False, True])
def test_require_clean_blocks_tracked_and_untracked_changes(repo_fixture: Fixture, untracked: bool) -> None:
    target = repo_fixture.worktree / ("new.txt" if untracked else "tracked.txt")
    target.write_text("dirty\n", encoding="utf-8")
    result = repo_fixture.preflight("--offline", "--require-clean")
    assert_blocked(result, 4, "worktree contains tracked or untracked changes")


def test_missing_origin_core_blocks(repo_fixture: Fixture) -> None:
    run(str(REAL_GIT), "-C", str(repo_fixture.source), "update-ref", "-d", "refs/remotes/origin/core")
    result = repo_fixture.preflight("--offline")
    assert_blocked(result, 4, "expected base does not resolve")


def test_failed_fetch_returns_auth_fetch_exit_code(repo_fixture: Fixture) -> None:
    wrapper = repo_fixture.fake_bin / "git"
    write_executable(
        wrapper,
        f"#!/usr/bin/env bash\nfor arg in \"$@\"; do [[ $arg == fetch ]] && exit 1; done\nexec {REAL_GIT} \"$@\"\n",
    )
    result = repo_fixture.preflight("--fetch")
    assert_blocked(result, 3, "git fetch origin --prune failed")


def test_global_windows_ssh_override_warns_for_https(repo_fixture: Fixture) -> None:
    repo_fixture.global_config.write_text('[core]\n\tsshCommand = C:/Windows/System32/OpenSSH/ssh.exe\n', encoding="utf-8")
    result = repo_fixture.preflight("--offline")
    assert result.returncode == 0, result.stdout
    assert "higher-level Windows core.sshCommand is present" in result.stdout


def test_local_core_behind_is_informational_warning(repo_fixture: Fixture) -> None:
    head = run(str(REAL_GIT), "-C", str(repo_fixture.source), "rev-parse", "HEAD").stdout.strip()
    tree = run(str(REAL_GIT), "-C", str(repo_fixture.source), "rev-parse", "HEAD^{tree}").stdout.strip()
    commit = run(
        str(REAL_GIT),
        "-C",
        str(repo_fixture.source),
        "commit-tree",
        tree,
        "-p",
        head,
        env={**repo_fixture.env(), "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid"},
    ).stdout.strip()
    run(str(REAL_GIT), "-C", str(repo_fixture.source), "update-ref", "refs/remotes/origin/core", commit)
    result = repo_fixture.preflight("--offline")
    assert result.returncode == 0, result.stdout
    assert "local_core: ahead=0 behind=1" in result.stdout
    assert "task branches must start from exact" in result.stdout


def test_optional_docker_and_pwsh_unavailable_only_warn(repo_fixture: Fixture) -> None:
    (repo_fixture.fake_bin / "docker").unlink()
    (repo_fixture.fake_bin / "pwsh").unlink()
    result = repo_fixture.preflight("--offline")
    assert result.returncode == 0, result.stdout
    assert "optional tool is unavailable: docker" in result.stdout
    assert "optional tool is unavailable: pwsh" in result.stdout
