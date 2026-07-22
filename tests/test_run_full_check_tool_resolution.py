from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_full_check.ps1"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_linux_does_not_prepend_bundled_windows_codex_runtime() -> None:
    text = source()
    function = text.split("function Add-BundledNodeToPath", 1)[1].split("function Invoke-DockerCompose", 1)[0]
    assert "if ($IsLinux)" in function
    assert function.index("if ($IsLinux)") < function.index("$env:USERPROFILE")
    assert "return" in function.split("$env:USERPROFILE", 1)[0]


def test_linux_candidates_exclude_windows_executable_names() -> None:
    text = source()
    assert '$gitNames = if ($IsLinux) { @("git") } else { @("git.exe", "git") }' in text
    assert '$nodeNames = if ($IsLinux) { @("node") } else { @("node.exe", "node") }' in text
    assert '$pnpmNames = if ($IsLinux) { @("pnpm") } else { @("pnpm.cmd", "pnpm") }' in text
    assert 'Find-CommandPath @("git.exe", "git")' not in text
    assert 'Find-CommandPath @("node.exe", "node")' not in text
    assert 'Find-CommandPath @("pnpm.cmd", "pnpm")' not in text


def test_linux_command_resolution_rejects_mounted_and_windows_paths() -> None:
    text = source()
    function = text.split("function Find-CommandPath", 1)[1].split("function Add-BundledNodeToPath", 1)[0]
    assert "$IsLinux" in function
    assert "^/mnt/[A-Za-z]/" in function
    assert "\\.(exe|cmd|bat)$" in function
    assert "^[A-Za-z]:[\\\\/]" in function


def test_timing_metadata_reuses_resolved_native_git() -> None:
    text = source()
    assert "$ResolvedGit = $null" in text
    assert "$script:ResolvedGit = $git" in text
    timing = text.split("function Initialize-TimingIfNeeded", 1)[1].split("Set-Location $Root", 1)[0]
    assert "& $ResolvedGit branch --show-current" in timing
    assert "& $ResolvedGit rev-parse HEAD" in timing
    assert "& git branch --show-current" not in timing
    assert "& git rev-parse HEAD" not in timing
