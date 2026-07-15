from __future__ import annotations

import argparse
from pathlib import Path
import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from fast_ci_e2e_handoff_common import (
    HANDOFF_PUBLIC_FIELDS, HandoffError, load_json, positive_integer,
    validate_source_inputs, write_json, write_outputs,
)
from fast_ci_e2e_handoff_contract import (
    resolve_source_run, validate_diagnostics, validate_package_handoff,
)

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
            result = validate_source_inputs(
                release_artifact_name=args.release_artifact_name,
                release_artifact_sha256=args.release_artifact_sha256,
                fast_ci_run_id=args.fast_ci_run_id,
            )
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
