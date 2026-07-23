from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_EXACT_PATHS = {
    ".github/workflows/ci-e2e.yml",
    "scripts/ci_e2e_artifact_common.py",
    "scripts/prepare_ci_e2e_artifacts.py",
    "scripts/prepare_ci_e2e_artifacts_legacy.py",
    "scripts/validate_e2e_harness_reuse.py",
    "scripts/verify_fast_ci_e2e_handoff.py",
    "tests/browser_progress.test.mjs",
    "tests/test_browser_progress_node.py",
    "tests/test_ci_e2e_artifacts.py",
    "tests/test_ci_e2e_private_path_redaction.py",
    "tests/test_docker_smoke_helpers.py",
    "tests/test_e2e_artifact_harness_reuse.py",
    "tests/test_e2e_harness_reuse.py",
    "tests/test_e2e_screenshot_contract.py",
    "tests/test_notification_e2e_fixture.py",
    "tests/test_telemetry_e2e_harness.py",
}
ALLOWED_PREFIXES = ("docker/anki-e2e/",)


class HarnessReuseError(ValueError):
    pass


def exact_sha(value: str, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if not SHA_RE.fullmatch(normalized):
        raise HarnessReuseError(f"{label} must be an exact lowercase 40-character SHA")
    return normalized


def normalize_path(value: str) -> str:
    normalized = str(value or "").strip().replace("\\", "/")
    pure = PurePosixPath(normalized)
    if (
        not normalized
        or pure.is_absolute()
        or re.match(r"^[A-Za-z]:/", normalized)
        or ".." in pure.parts
        or normalized.startswith("./")
    ):
        raise HarnessReuseError(f"Unsafe changed path: {value!r}")
    return normalized


def path_is_harness_only(path: str) -> bool:
    return path in ALLOWED_EXACT_PATHS or any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def validate_harness_reuse(
    *, package_tested_sha: str, harness_sha: str, workflow_source_sha: str, changed_paths: list[str],
) -> dict:
    package_sha = exact_sha(package_tested_sha, "package tested SHA")
    current_sha = exact_sha(harness_sha, "E2E harness SHA")
    source_sha = exact_sha(workflow_source_sha, "workflow source SHA")
    if current_sha != source_sha:
        raise HarnessReuseError("E2E harness SHA must match the workflow source SHA")

    normalized = sorted(dict.fromkeys(normalize_path(path) for path in changed_paths if str(path).strip()))
    if package_sha == current_sha:
        if normalized:
            raise HarnessReuseError("Exact-tree package reuse must not report changed paths")
        reuse_mode = "exact-tree"
    else:
        if not normalized:
            raise HarnessReuseError("Harness-only reuse requires at least one changed path")
        forbidden = [path for path in normalized if not path_is_harness_only(path)]
        if forbidden:
            raise HarnessReuseError(
                "Package reuse is forbidden because package-impacting or unrelated files changed: " + ", ".join(forbidden)
            )
        reuse_mode = "harness-only"

    encoded_paths = "".join(f"{path}\n" for path in normalized).encode("utf-8")
    return {
        "schemaVersion": 1,
        "reuseAllowed": True,
        "reuseMode": reuse_mode,
        "packageTestedCommitSha": package_sha,
        "e2eHarnessCommitSha": current_sha,
        "workflowSourceSha": source_sha,
        "changedFileCount": len(normalized),
        "changedPathsSha256": hashlib.sha256(encoded_paths).hexdigest(),
        "changedPaths": normalized,
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outputs(path: Path | None, value: dict) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in ("reuseMode", "packageTestedCommitSha", "e2eHarnessCommitSha", "changedFileCount", "changedPathsSha256"):
            output_name = {
                "reuseMode": "reuse_mode",
                "packageTestedCommitSha": "package_tested_sha",
                "e2eHarnessCommitSha": "harness_sha",
                "changedFileCount": "changed_file_count",
                "changedPathsSha256": "changed_paths_sha256",
            }[key]
            handle.write(f"{output_name}={value[key]}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate reuse of an exact Fast CI package with a newer E2E-only harness.")
    parser.add_argument("--package-tested-sha", required=True)
    parser.add_argument("--harness-sha", required=True)
    parser.add_argument("--workflow-source-sha", required=True)
    parser.add_argument("--changed-paths", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        paths = args.changed_paths.read_text(encoding="utf-8").splitlines()
        result = validate_harness_reuse(
            package_tested_sha=args.package_tested_sha,
            harness_sha=args.harness_sha,
            workflow_source_sha=args.workflow_source_sha,
            changed_paths=paths,
        )
        write_json(args.output, result)
        write_outputs(args.github_output, result)
        print(
            f"E2E package reuse accepted: mode={result['reuseMode']} "
            f"package={result['packageTestedCommitSha']} harness={result['e2eHarnessCommitSha']} "
            f"files={result['changedFileCount']}"
        )
        return 0
    except (HarnessReuseError, OSError) as exc:
        print(f"E2E harness reuse error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
