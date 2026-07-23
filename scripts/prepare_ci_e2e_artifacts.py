from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import prepare_ci_e2e_artifacts_legacy as legacy
from verify_fast_ci_e2e_handoff import validate_package_reuse_boundary


# Preserve the established import surface for tests and callers that import this
# wrapper as a module. The implementation remains owned by the legacy exporter.
TEXT_SUFFIXES = legacy.TEXT_SUFFIXES
copy_safe_artifacts = legacy.copy_safe_artifacts
validate_manifest = legacy.validate_manifest
assert_safe_text = legacy.assert_safe_text
utc_now = legacy.utc_now

_ORIGINAL_WRITE_SUMMARY = legacy.write_summary


def __getattr__(name: str):
    """Delegate unchanged exporter helpers to the canonical legacy module."""
    try:
        return getattr(legacy, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


def _read_reuse_evidence(args: argparse.Namespace) -> dict | None:
    package_source = args.package_source or "source-build"
    package_sha = str(args.source_fast_ci_tested_sha or "").strip().lower()
    checkout_sha = str(args.e2e_checkout_sha or args.commit_sha or "").strip().lower()
    if package_source != "fast-ci-artifact" or not package_sha or package_sha == checkout_sha:
        return None

    # Older direct unit/library callers do not carry the CLI-only raw_logs field.
    # Preserve their exact-tree validation path; the production CLI always defines
    # raw_logs and therefore still fails closed for harness-only reuse.
    raw_logs = getattr(args, "raw_logs", None)
    if raw_logs is None:
        return None

    evidence_path = Path(raw_logs) / "e2e-harness-reuse.json"
    try:
        actual = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Harness-only package reuse requires valid evidence at {evidence_path}: {exc}") from exc
    if not isinstance(actual, dict):
        raise ValueError("Harness-only package reuse evidence must be a JSON object")

    expected = validate_package_reuse_boundary(
        package_tested_sha=package_sha,
        e2e_workflow_source_sha=checkout_sha,
        e2e_checkout_sha=checkout_sha,
    )
    if actual != expected:
        raise ValueError("Harness-only package reuse evidence does not match the independently recomputed boundary")
    if expected.get("reuseMode") != "harness-only":
        raise ValueError("Distinct package and harness SHAs require reuseMode=harness-only")
    return expected


def _patch_json(path: Path, update) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    update(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rewrite_public_identity(output: Path, *, checkout_sha: str, reuse: dict) -> None:
    reuse_fields = {
        "e2eCheckoutSha": checkout_sha,
        "packageReuseMode": reuse["reuseMode"],
        "packageReuseChangedFileCount": reuse["changedFileCount"],
        "packageReuseChangedPathsSha256": reuse["changedPathsSha256"],
        "packageReuseEvidence": "artifacts/reports/e2e-harness-reuse.json",
    }

    _patch_json(output / "ci-e2e-summary.json", lambda payload: payload.update(reuse_fields))

    performance_path = output / "artifacts" / "reports" / "e2e-performance-summary.json"
    if performance_path.is_file():
        def update_performance(payload: dict) -> None:
            current = payload.setdefault("current", {})
            if not isinstance(current, dict):
                raise ValueError("E2E performance current section must be an object")
            current.update(reuse_fields)
        _patch_json(performance_path, update_performance)

    markdown_path = output / "ci-e2e-summary.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    package_sha = reuse["packageTestedCommitSha"]
    old_row = f"| E2E checkout | `{package_sha}` |"
    new_rows = (
        f"| E2E checkout | `{checkout_sha}` |\n"
        f"| Package tested commit | `{package_sha}` |\n"
        f"| Package reuse mode | {reuse['reuseMode']} |\n"
        f"| Harness-only changed files | {reuse['changedFileCount']} |"
    )
    if old_row not in markdown:
        raise ValueError("Could not locate E2E checkout row in public Markdown summary")
    markdown_path.write_text(markdown.replace(old_row, new_rows, 1), encoding="utf-8")

    environment_path = output / "environment.txt"
    lines = environment_path.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith("e2eCheckoutSha="):
            lines[index] = f"e2eCheckoutSha={checkout_sha}"
            replaced = True
            break
    if not replaced:
        raise ValueError("Could not locate e2eCheckoutSha in public environment evidence")
    lines.extend([
        f"packageReuseMode={reuse['reuseMode']}",
        f"packageReuseChangedFileCount={reuse['changedFileCount']}",
        f"packageReuseChangedPathsSha256={reuse['changedPathsSha256']}",
    ])
    environment_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(output: Path, *, args: argparse.Namespace, manifest_status: str, artifact_files: list[str]) -> None:
    # Keep monkeypatching and direct module users compatible with the historical
    # public surface while the canonical implementation remains in legacy.
    legacy.utc_now = utc_now

    reuse = _read_reuse_evidence(args)
    if reuse is None:
        _ORIGINAL_WRITE_SUMMARY(output, args=args, manifest_status=manifest_status, artifact_files=artifact_files)
        return

    public_relative = "artifacts/reports/e2e-harness-reuse.json"
    public_path = output / public_relative
    public_path.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_json_file(public_path, reuse)
    if public_relative not in artifact_files:
        artifact_files.append(public_relative)

    actual_checkout_sha = str(args.e2e_checkout_sha or args.commit_sha).strip().lower()
    compatibility_args = argparse.Namespace(**vars(args))
    compatibility_args.e2e_checkout_sha = str(args.source_fast_ci_tested_sha).strip().lower()
    _ORIGINAL_WRITE_SUMMARY(
        output,
        args=compatibility_args,
        manifest_status=manifest_status,
        artifact_files=artifact_files,
    )
    _rewrite_public_identity(output, checkout_sha=actual_checkout_sha, reuse=reuse)


legacy.write_summary = write_summary


def _load_run_event_protocol():
    path = _SCRIPT_DIR.parent / "docker" / "anki-e2e" / "run_event_protocol.py"
    spec = importlib.util.spec_from_file_location("asr_run_event_protocol_export", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load run event protocol from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_events = _load_run_event_protocol()


def _argument_path(name: str, default: str) -> Path:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return Path(default)
    if index + 1 >= len(sys.argv):
        raise ValueError(f"Missing value for {name}")
    return Path(sys.argv[index + 1])


def _manifest_status(source: Path) -> str:
    path = source / "artifact-manifest.json"
    if not path.is_file():
        return "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Artifact manifest is not valid JSON: {path}") from exc
    return str(payload.get("status") or "unknown") if isinstance(payload, dict) else "unknown"


def main() -> int:
    source = _argument_path("--source", "e2e-artifacts").resolve()
    output = _argument_path("--output", "ci-e2e").resolve()
    source_stream = source / "reports" / "run-events.jsonl"
    status = _manifest_status(source)
    if source_stream.is_file():
        run_events.validate_stream(source_stream, expected_producer="docker-e2e", require_final=True)
    elif status == "success":
        raise ValueError("Successful E2E artifacts require reports/run-events.jsonl")

    result = legacy.main()
    public_stream = output / "artifacts" / "reports" / "run-events.jsonl"
    if source_stream.is_file():
        run_events.validate_stream(public_stream, expected_producer="docker-e2e", require_final=True)
    elif public_stream.exists():
        raise ValueError("Public run event stream exists without validated source evidence")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
