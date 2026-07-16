from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from fast_ci_e2e_handoff_common import (
    FAST_WORKFLOW_PATH, HANDOFF_PUBLIC_FIELDS, HandoffError, load_json,
    positive_integer, safe_text, validate_source_inputs, write_json,
    write_outputs,
)
from fast_ci_e2e_handoff_contract import (
    resolve_source_run as _resolve_source_run,
    validate_diagnostics,
    validate_package_handoff,
)


_ALLOWED_MODES = {"standard", "strict-apkg", "perf100"}
_ALLOWED_SCOPES = {"full", "global", "stats", "decks", "activity", "cards", "settings"}
_ALLOWED_SCREENSHOT_WORKERS = {"auto", "1", "2", "3", "4"}
_ALLOWED_TELEMETRY = {"true", "false"}
_ALLOWED_RESTART = {"auto", "true", "false"}
_SAFE_INITIAL_E2E_ENV = {
    "E2E_MODE": "standard",
    "E2E_SCOPE": "full",
    "ANKI_E2E_SCOPE": "full",
    "ANKI_E2E_SCREENSHOT_WORKERS": "3",
    "ANKI_E2E_RESOURCE_TELEMETRY": "0",
    "ANKI_E2E_VERIFY_RESTART": "auto",
    "ANKI_E2E_PACKAGE_SOURCE": "source-build",
    "ANKI_E2E_FAST_CI_RUN_ID": "",
    "ANKI_E2E_FAST_CI_TESTED_SHA": "",
    "ANKI_E2E_FAST_CI_PACKAGE_SHA256": "",
}


def normalize_workflow_run_path(
    value: Any, expected_path: str = FAST_WORKFLOW_PATH
) -> tuple[str, str | None]:
    raw_path = safe_text(value, "run.path")
    canonical_path = safe_text(expected_path, "expected workflow path")
    if raw_path == canonical_path:
        return canonical_path, None
    prefix = f"{canonical_path}@"
    if not raw_path.startswith(prefix):
        raise HandoffError(f"Source run workflow path is not {canonical_path}")
    qualifier = safe_text(raw_path[len(prefix):], "run.path ref qualifier")
    return canonical_path, qualifier


def normalize_e2e_inputs(
    *, mode: Any, scope: Any, screenshot_workers: Any,
    resource_telemetry: Any, verify_restart: Any,
) -> dict[str, str]:
    normalized_mode = safe_text(mode, "mode")
    normalized_scope = safe_text(scope, "scope")
    workers_input = safe_text(screenshot_workers, "screenshot workers")
    telemetry_input = safe_text(resource_telemetry, "resource telemetry")
    restart_input = safe_text(verify_restart, "restart policy")

    if normalized_mode not in _ALLOWED_MODES:
        raise HandoffError(f"Unsupported E2E mode: {normalized_mode}")
    if normalized_scope not in _ALLOWED_SCOPES:
        raise HandoffError(f"Unsupported E2E scope: {normalized_scope}")
    if normalized_mode in {"strict-apkg", "perf100"} and normalized_scope not in {"full", "cards"}:
        raise HandoffError(f"Mode {normalized_mode} requires scope=full or scope=cards")
    if workers_input not in _ALLOWED_SCREENSHOT_WORKERS:
        raise HandoffError(f"Unsupported screenshot workers: {workers_input}")
    if telemetry_input not in _ALLOWED_TELEMETRY:
        raise HandoffError(f"Unsupported resource telemetry: {telemetry_input}")
    if restart_input not in _ALLOWED_RESTART:
        raise HandoffError(f"Unsupported restart policy: {restart_input}")

    workers = "3" if workers_input == "auto" else workers_input
    telemetry = "1" if telemetry_input == "true" else "0"
    restart = {"true": "1", "false": "0", "auto": "auto"}[restart_input]
    return {
        "E2E_MODE": normalized_mode,
        "E2E_SCOPE": normalized_scope,
        "ANKI_E2E_SCOPE": normalized_scope,
        "ANKI_E2E_SCREENSHOT_WORKERS": workers,
        "ANKI_E2E_RESOURCE_TELEMETRY": telemetry,
        "ANKI_E2E_VERIFY_RESTART": restart,
    }


def append_github_env(path: Path | None, values: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            rendered = "" if value is None else str(value)
            if "\n" in rendered or "\r" in rendered:
                raise HandoffError(f"Environment value {key} must be single-line")
            handle.write(f"{key}={rendered}\n")


def resolve_source_run(
    *, run_payload: dict[str, Any], artifacts_payload: dict[str, Any],
    repository: str, input_run_id: int,
) -> dict[str, Any]:
    normalized_payload = dict(run_payload)
    canonical_path, _ = normalize_workflow_run_path(run_payload.get("path"))
    normalized_payload["path"] = canonical_path
    result = _resolve_source_run(
        run_payload=normalized_payload,
        artifacts_payload=artifacts_payload,
        repository=repository,
        input_run_id=input_run_id,
    )
    result["sourceWorkflowPath"] = canonical_path
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the exact Fast CI to Docker E2E package handoff.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inputs = subparsers.add_parser("validate-inputs")
    inputs.add_argument("--release-artifact-name", default="")
    inputs.add_argument("--release-artifact-sha256", default="")
    inputs.add_argument("--fast-ci-run-id", default="")
    inputs.add_argument("--output", type=Path, required=True)
    inputs.add_argument("--github-output", type=Path)

    resolve = subparsers.add_parser("resolve-run")
    resolve.add_argument("--run-json", type=Path, required=True)
    resolve.add_argument("--artifacts-json", type=Path, required=True)
    resolve.add_argument("--repository", required=True)
    resolve.add_argument("--run-id", required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--github-output", type=Path)

    diagnostics = subparsers.add_parser("validate-diagnostics")
    diagnostics.add_argument("--resolution", type=Path, required=True)
    diagnostics.add_argument("--directory", type=Path, required=True)
    diagnostics.add_argument("--output", type=Path, required=True)
    diagnostics.add_argument("--github-output", type=Path)

    package = subparsers.add_parser("validate-package")
    package.add_argument("--resolution", type=Path, required=True)
    package.add_argument("--diagnostics", type=Path, required=True)
    package.add_argument("--directory", type=Path, required=True)
    package.add_argument("--e2e-workflow-source-sha", required=True)
    package.add_argument("--e2e-checkout-sha", required=True)
    package.add_argument("--output", type=Path, required=True)
    package.add_argument("--github-output", type=Path)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "validate-inputs":
            github_env_value = os.environ.get("GITHUB_ENV", "")
            github_env = Path(github_env_value) if github_env_value else None
            append_github_env(github_env, _SAFE_INITIAL_E2E_ENV)
            normalized_inputs = normalize_e2e_inputs(
                mode=os.environ.get("E2E_MODE", "standard"),
                scope=os.environ.get("E2E_SCOPE", "full"),
                screenshot_workers=os.environ.get("SCREENSHOT_WORKERS_INPUT", "auto"),
                resource_telemetry=os.environ.get("RESOURCE_TELEMETRY_INPUT", "true"),
                verify_restart=os.environ.get("VERIFY_RESTART_INPUT", "auto"),
            )
            append_github_env(github_env, normalized_inputs)
            result = validate_source_inputs(
                release_artifact_name=args.release_artifact_name,
                release_artifact_sha256=args.release_artifact_sha256,
                fast_ci_run_id=args.fast_ci_run_id,
            )
            append_github_env(github_env, {
                "ANKI_E2E_PACKAGE_SOURCE": result["packageSource"],
                "ANKI_E2E_FAST_CI_RUN_ID": result["fastCiRunId"],
            })
            write_json(args.output, result)
            write_outputs(args.github_output, {
                "package_source": result["packageSource"],
                "fast_ci_run_id": result["fastCiRunId"],
            })
        elif args.command == "resolve-run":
            run_id = positive_integer(args.run_id, "fast_ci_run_id")
            result = resolve_source_run(
                run_payload=load_json(args.run_json),
                artifacts_payload=load_json(args.artifacts_json),
                repository=args.repository,
                input_run_id=run_id,
            )
            write_json(args.output, result)
            write_outputs(args.github_output, {
                "source_run_id": result["sourceRunId"],
                "source_run_attempt": result["sourceRunAttempt"],
                "diagnostics_artifact_id": result["diagnosticsArtifact"]["id"],
                "package_artifact_id": result["packageArtifact"]["id"],
                "package_artifact_name": result["packageArtifact"]["name"],
            })
        elif args.command == "validate-diagnostics":
            resolution = load_json(args.resolution)
            result = validate_diagnostics(resolution=resolution, directory=args.directory)
            write_json(args.output, result)
            write_outputs(args.github_output, {
                "tested_sha": result["testedCommitSha"],
                "source_head_sha": result["sourceHeadSha"],
                "source_base_sha": result["sourceBaseSha"],
                "source_event": result["sourceEvent"],
                "source_ref": result["sourceRef"],
            })
        elif args.command == "validate-package":
            result = validate_package_handoff(
                resolution=load_json(args.resolution),
                diagnostics=load_json(args.diagnostics),
                directory=args.directory,
                e2e_workflow_source_sha=args.e2e_workflow_source_sha,
                e2e_checkout_sha=args.e2e_checkout_sha,
            )
            write_json(args.output, result)
            write_outputs(args.github_output, {
                "package_sha256": result["packageSha256"],
                "package_size_bytes": result["packageSizeBytes"],
                "tested_sha": result["sourceTestedCommitSha"],
            })
        else:
            parser.error("Unsupported command")
        return 0
    except (HandoffError, OSError) as exc:
        print(f"Fast CI E2E handoff error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
