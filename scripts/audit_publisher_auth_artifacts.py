from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRECTORY_NAMES = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pnpm",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".yarn",
    "__pycache__",
    "node_modules",
}
EXPLICIT_AUTH_FILENAMES = {
    "ankiweb-auth.json",
    "ankiweb-session.json",
    "ankiweb-storage-state.json",
    "publisher-auth.json",
    "publisher-session.json",
    "storagestate.json",
    "storage-state.json",
    "trace.zip",
}
PROFILE_DIRECTORY_NAMES = {
    ".playwright-profile",
    "ankiweb-profile",
    "playwright-profile",
    "publisher-profile",
}


def normalize_report_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def _safe_relative(root: Path, candidate: Path, label: str) -> str:
    relative = Path(os.path.relpath(candidate, root))
    if relative.parts and relative.parts[0] == "..":
        raise ValueError("audit path escaped its declared root")
    return normalize_report_path(f"{label}/{relative.as_posix()}")


def _is_auth_file(relative_parts: tuple[str, ...], filename: str) -> bool:
    lowered_parts = tuple(part.lower() for part in relative_parts)
    lowered_name = filename.lower()
    if lowered_name in EXPLICIT_AUTH_FILENAMES:
        return True
    if lowered_name.endswith(".json") and ".auth" in lowered_parts:
        return True
    if "playwright" in lowered_parts and ".auth" in lowered_parts:
        return True
    return False


def _workspace_findings(workspace: Path) -> Iterable[str]:
    if not workspace.is_dir():
        return
    for current, directories, files in os.walk(workspace):
        current_path = Path(current)
        kept_directories: list[str] = []
        for directory in directories:
            lowered = directory.lower()
            if lowered in EXCLUDED_DIRECTORY_NAMES or lowered.endswith("_cache"):
                continue
            directory_path = current_path / directory
            if lowered in PROFILE_DIRECTORY_NAMES or lowered.startswith("asr-ankiweb-profile-"):
                yield _safe_relative(workspace, directory_path, "workspace")
                continue
            kept_directories.append(directory)
        directories[:] = kept_directories
        relative_parts = current_path.relative_to(workspace).parts
        for filename in files:
            if _is_auth_file(relative_parts, filename):
                yield _safe_relative(workspace, current_path / filename, "workspace")


def _runner_temp_findings(runner_temp: Path | None) -> Iterable[str]:
    if runner_temp is None or not runner_temp.is_dir():
        return
    for candidate in runner_temp.iterdir():
        if candidate.name.lower().startswith("asr-ankiweb-"):
            yield _safe_relative(runner_temp, candidate, "runner-temp")


def audit_publisher_artifacts(workspace: Path, runner_temp: Path | None = None) -> list[str]:
    findings = set(_workspace_findings(workspace))
    findings.update(_runner_temp_findings(runner_temp))
    return sorted(findings, key=str.casefold)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit publisher-owned locations for persisted browser auth artifacts.")
    parser.add_argument("--workspace", type=Path, default=Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd())))
    runner_temp = os.environ.get("RUNNER_TEMP")
    parser.add_argument("--runner-temp", type=Path, default=Path(runner_temp) if runner_temp else None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings = audit_publisher_artifacts(args.workspace, args.runner_temp)
    if findings:
        print("Publisher left forbidden auth artifacts: " + ", ".join(findings))
        return 1
    print("Publisher auth-artifact audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
