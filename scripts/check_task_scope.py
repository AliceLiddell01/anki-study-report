"""Validate the current Git change set against a local task contract."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence

DEFAULT_CONTRACT = Path(".agents/task-contract.toml")

BUILTIN_FORBIDDEN = (
    ".venv/**",
    "__pycache__/**",
    "**/__pycache__/**",
    "**/*.pyc",
    ".pytest_cache/**",
    "node_modules/**",
    "**/node_modules/**",
    "web-dashboard/node_modules/**",
    "web-dashboard/dist/**",
    "web-dashboard/screenshots/**",
    "anki_study_report/web_dashboard/**",
    "anki_study_report/user_files/**",
    "e2e-artifacts/**",
    "ci-fast/**",
    "ci-fast-download/**",
    "ci-e2e/**",
    "ci-e2e-raw/**",
    "ci-e2e-download/**",
    "release-artifacts/**",
    ".playwright-auth/**",
    "docker/anki-e2e/local-input/**",
    "*.ankiaddon",
    "*.zip",
)


class Contract(NamedTuple):
    task: str
    base_ref: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]


def normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def matches(path: str, pattern: str) -> bool:
    path = normalize_path(path)
    pattern = normalize_path(pattern)
    if not path or not pattern:
        return False

    # A directory-like pattern without glob characters allows the directory itself
    # and descendants. Explicit glob patterns use fnmatch semantics.
    if not any(char in pattern for char in "*?["):
        return path == pattern or path.startswith(pattern + "/")
    return fnmatch.fnmatchcase(path, pattern)


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


def validate_paths(
    paths: Iterable[str],
    allowed_paths: Sequence[str],
    forbidden_paths: Sequence[str] = (),
) -> tuple[list[str], list[str]]:
    normalized = sorted({normalize_path(path) for path in paths if normalize_path(path)})
    forbidden_patterns = tuple(BUILTIN_FORBIDDEN) + tuple(forbidden_paths)
    forbidden = [path for path in normalized if matches_any(path, forbidden_patterns)]
    unexpected = [
        path
        for path in normalized
        if path not in forbidden and not matches_any(path, allowed_paths)
    ]
    return unexpected, forbidden


def load_contract(path: Path) -> Contract:
    if not path.is_file():
        raise ValueError(
            f"Task contract not found: {path}. "
            "Copy docs/templates/task-contract.toml to .agents/task-contract.toml."
        )

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported or missing schema_version; expected 1.")

    task = str(data.get("task", "")).strip()
    base_ref = str(data.get("base_ref", "")).strip()
    allowed = tuple(str(item).strip() for item in data.get("allowed_paths", ()) if str(item).strip())
    forbidden = tuple(
        str(item).strip() for item in data.get("forbidden_paths", ()) if str(item).strip()
    )

    if not task or task.startswith("REPLACE:"):
        raise ValueError("The task field is not filled in.")
    if not base_ref:
        raise ValueError("The base_ref field is required.")
    if not allowed or any(item == "REPLACE/ME" for item in allowed):
        raise ValueError("allowed_paths must contain task-specific paths.")

    return Contract(
        task=task,
        base_ref=base_ref,
        allowed_paths=allowed,
        forbidden_paths=forbidden,
    )


def run_git(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def changed_paths(base_ref: str, include_untracked: bool = True) -> list[str]:
    paths: set[str] = set()

    # Three-dot comparison covers committed changes from the merge base to HEAD.
    committed = run_git(["diff", "--name-only", "--diff-filter=ACMRTUXB", f"{base_ref}...HEAD"])
    paths.update(committed.splitlines())

    # Include staged and unstaged work that is not in HEAD yet.
    worktree = run_git(["diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"])
    paths.update(worktree.splitlines())

    if include_untracked:
        untracked = run_git(["ls-files", "--others", "--exclude-standard"])
        paths.update(untracked.splitlines())

    return sorted(normalize_path(path) for path in paths if normalize_path(path))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate changed files against .agents/task-contract.toml."
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help=f"Task contract path (default: {DEFAULT_CONTRACT}).",
    )
    parser.add_argument(
        "--base",
        help="Override base_ref from the contract.",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Validate an explicit changed path; repeatable. Skips Git discovery.",
    )
    parser.add_argument(
        "--no-untracked",
        action="store_true",
        help="Do not include untracked files in Git discovery.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract = load_contract(args.contract)
        base_ref = args.base or contract.base_ref
        paths = (
            sorted({normalize_path(path) for path in args.paths if normalize_path(path)})
            if args.paths is not None
            else changed_paths(base_ref, include_untracked=not args.no_untracked)
        )
        unexpected, forbidden = validate_paths(
            paths,
            allowed_paths=contract.allowed_paths,
            forbidden_paths=contract.forbidden_paths,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"task-scope: ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Task: {contract.task}")
    print(f"Base: {base_ref}")
    print(f"Changed paths: {len(paths)}")

    if forbidden:
        print("\nForbidden generated/runtime paths:")
        for path in forbidden:
            print(f"- {path}")

    if unexpected:
        print("\nPaths outside allowed scope:")
        for path in unexpected:
            print(f"- {path}")

    if forbidden or unexpected:
        print(
            "\ntask-scope: FAIL. Update the task contract only when the task genuinely "
            "requires a wider scope, then explain the expansion.",
            file=sys.stderr,
        )
        return 1

    print("task-scope: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
