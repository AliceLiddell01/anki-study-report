#!/usr/bin/env python3
from __future__ import annotations

from e2e_final_summary_common import *
from e2e_final_summary_build import *
from e2e_final_summary_history import *

def _context_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "footprint_root": args.footprint_root,
        "footprint_summary_relative": args.footprint_summary_relative,
        "footprint_manifest_relative": args.footprint_manifest_relative,
        "repository": args.repository,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "event": args.event,
        "ref": args.ref,
        "trigger_sha": args.trigger_sha,
        "workflow_source_sha": args.workflow_source_sha,
        "harness_sha": args.harness_sha,
        "mode": args.mode,
        "scope": args.scope,
        "run_purpose": args.run_purpose,
        "screenshot_workers": args.screenshot_workers,
        "resource_telemetry": args.resource_telemetry,
        "contour": args.contour,
        "started_at_utc": args.started_at_utc,
        "finished_at_utc": args.finished_at_utc,
        "exit_code": args.exit_code,
        "runner_os": args.runner_os,
        "runner_image": args.runner_image,
        "docker_client_version": args.docker_client_version,
        "docker_server_version": args.docker_server_version,
        "docker_compose_version": args.docker_compose_version,
        "powershell_version": args.powershell_version,
        "package_source": args.package_source,
        "host_failure_code": args.host_failure_code,
        "host_failure_phase": args.host_failure_phase,
        "host_failure_item": args.host_failure_item,
        "artifact_preparation_duration_ms": args.artifact_preparation_duration_ms,
        "workflow_duration_ms": args.workflow_duration_ms,
        "cleanup_status": args.cleanup_status,
        "cleanup_duration_ms": args.cleanup_duration_ms,
        "artifact_preparation_status": args.artifact_preparation_status,
        "source_validated": True,
        "public_validated": args.public_validated,
    }


def add_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--footprint-root", type=Path)
    parser.add_argument("--footprint-summary-relative", default="reports/final-run-summary.json")
    parser.add_argument("--footprint-manifest-relative", default="artifact-manifest.json")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--trigger-sha", required=True)
    parser.add_argument("--workflow-source-sha", required=True)
    parser.add_argument("--harness-sha", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--run-purpose", choices=sorted(PURPOSES), default="acceptance")
    parser.add_argument("--screenshot-workers", type=int, required=True)
    parser.add_argument("--resource-telemetry", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--contour", choices=sorted(CONTOURS), default="cloud")
    parser.add_argument("--started-at-utc")
    parser.add_argument("--finished-at-utc")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--runner-os", required=True)
    parser.add_argument("--runner-image", required=True)
    parser.add_argument("--docker-client-version", default="unavailable")
    parser.add_argument("--docker-server-version", default="unavailable")
    parser.add_argument("--docker-compose-version", default="unavailable")
    parser.add_argument("--powershell-version", default="unavailable")
    parser.add_argument("--package-source", required=True)
    parser.add_argument("--host-failure-code")
    parser.add_argument("--host-failure-phase")
    parser.add_argument("--host-failure-item")
    parser.add_argument("--artifact-preparation-duration-ms", type=int)
    parser.add_argument("--workflow-duration-ms", type=int)
    parser.add_argument("--cleanup-status", default="unknown")
    parser.add_argument("--cleanup-duration-ms", type=int)
    parser.add_argument("--artifact-preparation-status", default="success")
    parser.add_argument("--public-validated", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical E2E final summary and bounded history")
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build-summary")
    add_build_args(build_parser)

    finalize_parser = sub.add_parser("finalize-public")
    add_build_args(finalize_parser)
    finalize_parser.add_argument("--public-root", type=Path, required=True)
    finalize_parser.add_argument("--public-summary-relative", default="artifacts/reports/final-run-summary.json")
    finalize_parser.add_argument("--public-manifest-relative", default="artifacts/artifact-manifest.json")

    validate_parser = sub.add_parser("validate-summary")
    validate_parser.add_argument("--input", type=Path, required=True)

    export_parser = sub.add_parser("export-public")
    export_parser.add_argument("--raw", type=Path, required=True)
    export_parser.add_argument("--public", type=Path, required=True)

    pair_parser = sub.add_parser("validate-pair")
    pair_parser.add_argument("--raw", type=Path, required=True)
    pair_parser.add_argument("--public", type=Path, required=True)

    legacy_parser = sub.add_parser("derive-legacy")
    legacy_parser.add_argument("--input", type=Path, required=True)
    legacy_parser.add_argument("--json-output", type=Path, required=True)
    legacy_parser.add_argument("--markdown-output", type=Path, required=True)

    entry_parser = sub.add_parser("build-entry")
    entry_parser.add_argument("--summary", type=Path, required=True)
    entry_parser.add_argument("--output", type=Path, required=True)
    entry_parser.add_argument("--main-artifact-id", type=int)
    entry_parser.add_argument("--main-artifact-digest")
    entry_parser.add_argument("--main-artifact-size-bytes", type=int)
    entry_parser.add_argument("--main-artifact-expires-at-utc")
    entry_parser.add_argument("--artifact-upload-duration-ms", type=int)

    merge_parser = sub.add_parser("merge-history")
    merge_parser.add_argument("--previous", type=Path)
    merge_parser.add_argument("--entry", type=Path, required=True)
    merge_parser.add_argument("--output", type=Path, required=True)
    merge_parser.add_argument("--generated-at-utc")
    merge_parser.add_argument("--reset-reason")

    aggregate_parser = sub.add_parser("aggregate-history")
    aggregate_parser.add_argument("--history", type=Path, required=True)
    aggregate_parser.add_argument("--summary", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)

    observations_parser = sub.add_parser("render-observations")
    observations_parser.add_argument("--history", type=Path, required=True)
    observations_parser.add_argument("--summary", type=Path, required=True)
    observations_parser.add_argument("--aggregation", type=Path, required=True)
    observations_parser.add_argument("--json-output", type=Path, required=True)
    observations_parser.add_argument("--markdown-output", type=Path, required=True)

    github_parser = sub.add_parser("render-github-summary")
    github_parser.add_argument("--summary", type=Path, required=True)
    github_parser.add_argument("--aggregation", type=Path)
    github_parser.add_argument("--history", type=Path)
    github_parser.add_argument("--main-artifact-metadata", type=Path)
    github_parser.add_argument("--history-artifact-metadata", type=Path)
    github_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "build-summary":
        summary = build_summary(args.artifact_root, **_context_from_args(args))
        write_json(args.output, summary, max_bytes=MAX_SUMMARY_BYTES)
    elif args.command == "finalize-public":
        context = _context_from_args(args)
        context["public_validated"] = True
        finalize_public_artifact(
            args.artifact_root,
            args.public_root,
            args.output,
            context=context,
            public_summary_relative=args.public_summary_relative,
            public_manifest_relative=args.public_manifest_relative,
        )
    elif args.command == "validate-summary":
        load_summary(args.input)
    elif args.command == "export-public":
        _, digest = export_public_summary(args.raw, args.public)
        print(digest)
    elif args.command == "validate-pair":
        _, digest = validate_pair(args.raw, args.public)
        print(digest)
    elif args.command == "derive-legacy":
        summary = load_summary(args.input)
        write_json(args.json_output, legacy_projection(summary))
        atomic_write_bytes(args.markdown_output, render_legacy_markdown(summary).encode("utf-8"))
    elif args.command == "build-entry":
        summary = load_summary(args.summary)
        entry = build_history_entry(
            summary,
            summary_digest=file_digest(args.summary),
            main_artifact_id=args.main_artifact_id,
            main_artifact_digest=args.main_artifact_digest,
            main_artifact_size_bytes=args.main_artifact_size_bytes,
            main_artifact_expires_at_utc=args.main_artifact_expires_at_utc,
            artifact_upload_duration_ms=args.artifact_upload_duration_ms,
        )
        write_json(args.output, entry)
    elif args.command == "merge-history":
        previous = read_json(args.previous) if args.previous and args.previous.is_file() else None
        entry = read_json(args.entry, required=True)
        merged = merge_history(previous, entry, generated_at_utc=args.generated_at_utc, reset_reason=args.reset_reason)
        write_json(args.output, merged, max_bytes=MAX_HISTORY_BYTES)
    elif args.command == "aggregate-history":
        history = validate_history(read_json(args.history, required=True))
        summary = load_summary(args.summary)
        write_json(args.output, aggregate_history(history, summary))
    elif args.command == "render-observations":
        history = validate_history(read_json(args.history, required=True))
        summary = load_summary(args.summary)
        aggregation = read_json(args.aggregation, required=True)
        observations = render_observations(summary, history, aggregation)
        write_json(args.json_output, observations)
        atomic_write_bytes(args.markdown_output, render_observations_markdown(observations).encode("utf-8"))
    elif args.command == "render-github-summary":
        summary = load_summary(args.summary)
        aggregation = read_json(args.aggregation) if args.aggregation else None
        history = read_json(args.history) if args.history else None
        main_artifact = read_json(args.main_artifact_metadata) if args.main_artifact_metadata else None
        history_artifact = read_json(args.history_artifact_metadata) if args.history_artifact_metadata else None
        atomic_write_bytes(
            args.output,
            render_github_summary(
                summary, aggregation, history,
                main_artifact=main_artifact,
                history_artifact=history_artifact,
            ).encode("utf-8"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
