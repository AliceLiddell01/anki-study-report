from __future__ import annotations

from e2e_final_summary_common import *
import e2e_final_summary_build_projection as _projection
globals().update({name: getattr(_projection, name) for name in dir(_projection) if not name.startswith("__")})

def build_summary(
    artifact_root: Path,
    *,
    footprint_root: Path | None = None,
    footprint_summary_relative: str = "reports/final-run-summary.json",
    footprint_manifest_relative: str = "artifact-manifest.json",
    repository: str,
    run_id: int,
    run_attempt: int,
    event: str,
    ref: str,
    trigger_sha: str,
    workflow_source_sha: str,
    harness_sha: str,
    mode: str,
    scope: str,
    run_purpose: str,
    screenshot_workers: int,
    resource_telemetry: bool,
    contour: str,
    started_at_utc: str | None,
    finished_at_utc: str | None,
    exit_code: int,
    runner_os: str,
    runner_image: str,
    docker_client_version: str,
    docker_server_version: str,
    docker_compose_version: str,
    powershell_version: str,
    package_source: str,
    host_failure_code: str | None = None,
    host_failure_phase: str | None = None,
    host_failure_item: str | None = None,
    host_failure_mode: str = "override",
    artifact_preparation_duration_ms: int | None = None,
    workflow_duration_ms: int | None = None,
    cleanup_status: str = "unknown",
    cleanup_duration_ms: int | None = None,
    artifact_preparation_status: str = "success",
    source_validated: bool = True,
    public_validated: bool = False,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    footprint_root = (footprint_root or artifact_root).resolve()
    reports = artifact_root / "reports"
    manifest = read_json(artifact_root / "artifact-manifest.json")
    events = read_jsonl(reports / "run-events.jsonl")
    preflight_report = read_json(reports / "preflight-report.json")
    browser = read_json(reports / "browser-smoke-first.json")
    screenshot = read_json(reports / "screenshot-performance.json")
    phases = read_json(reports / "e2e-phase-timings.json")
    environment = read_json(reports / "environment-image-provenance.json")
    workload = read_json(reports / "real-deck-manifest-report.json")
    non_release_identity = read_json(reports / "non-release-build-identity.json")
    release_identity = read_json(reports / "release-build-identity.json")
    identity = release_identity if package_source == "release-artifact" else non_release_identity
    failure = read_json(reports / "failure-summary.json")
    cancellation = read_json(reports / "cancellation-summary.json")

    if host_failure_mode not in {"fallback", "override"}:
        raise FinalSummaryError("hostFailureMode must be fallback or override")
    if host_failure_code is not None:
        _id(host_failure_code, "hostFailureCode")
    try:
        result, finalization, terminal = _result_and_terminal(
            events=events, failure=failure, cancellation=cancellation,
            preflight=preflight_report, exit_code=exit_code,
        )
    except FinalSummaryError:
        if host_failure_code is None:
            raise
        result = "failure"
        finalization = "minimal"
        terminal = {
            "event": "host/fail",
            "phaseId": host_failure_phase or "host-setup",
            "itemId": host_failure_item,
            "failureCode": host_failure_code,
            "signal": None,
            "exitCode": exit_code,
        }
    if host_failure_code is not None and host_failure_mode == "override" and result == "success":
        result = "failure"
        finalization = "minimal"
        terminal = {
            "event": "host/fail",
            "phaseId": host_failure_phase or "host-finalization",
            "itemId": host_failure_item,
            "failureCode": host_failure_code,
            "signal": None,
            "exitCode": exit_code,
        }
    if run_purpose not in PURPOSES:
        raise FinalSummaryError("runPurpose must be acceptance, controlled, or measurement")
    if mode == "perf100":
        run_purpose = "measurement"
    if contour not in CONTOURS:
        raise FinalSummaryError("contour must be cloud or local")
    if result == "success" and exit_code != 0:
        raise FinalSummaryError("success summary requires exitCode=0")
    if result == "success" and not manifest:
        raise FinalSummaryError("success summary requires artifact-manifest.json")

    restart_executed = (reports / "api-smoke-restart.json").is_file()
    preflight = _preflight_projection(preflight_report)
    observed = {
        "runnerOs": runner_os,
        "runnerImage": runner_image,
        "dockerClientVersion": docker_client_version,
        "dockerServerVersion": docker_server_version,
        "dockerComposeVersion": docker_compose_version,
        "powershellVersion": powershell_version,
        "workflowSourceSha": workflow_source_sha,
        "harnessSha": harness_sha,
    }
    compatibility = build_compatibility(
        manifest=manifest, browser=browser, screenshot=screenshot, phases=phases,
        environment=environment, workload=workload, mode=mode, scope=scope,
        restart_executed=restart_executed, screenshot_workers=screenshot_workers,
        resource_telemetry=resource_telemetry, package_source=package_source,
        runner_family=runner_os, contour=contour, observed=observed,
    )
    if result == "success" and any(
        value == "unavailable" for value in compatibility["dimensions"].values()
    ):
        missing = sorted(
            key for key, value in compatibility["dimensions"].items()
            if value == "unavailable"
        )
        raise FinalSummaryError(f"successful compatibility dimensions are incomplete: {missing}")
    build = _build_projection(identity, package_source)
    if (
        result == "failure"
        and failure
        and manifest
        and cleanup_status != "unknown"
        and artifact_preparation_status == "success"
    ):
        finalization = "complete"
    if result == "success" and package_source in {"fast-ci-artifact", "release-artifact"} and build["status"] != "resolved":
        raise FinalSummaryError("successful artifact-backed run requires canonical build identity")

    if started_at_utc:
        start = normalize_utc(started_at_utc)
    elif events:
        start = normalize_utc(str(events[0].get("timestampUtc")))
    else:
        start = normalize_utc(str(preflight_report.get("startedAtUtc") or preflight_report.get("generatedAtUtc")))
    if finished_at_utc:
        finish = normalize_utc(finished_at_utc)
    elif events:
        finish = normalize_utc(str(events[-1].get("timestampUtc")))
    else:
        fallback_finish = preflight_report.get("finishedAtUtc") or preflight_report.get("generatedAtUtc")
        finish = normalize_utc(str(fallback_finish)) if fallback_finish else utc_now()
    if workflow_duration_ms is None:
        workflow_duration_ms = max(
            0, int((datetime.fromisoformat(finish[:-1] + "+00:00") - datetime.fromisoformat(start[:-1] + "+00:00")).total_seconds() * 1000)
        )

    performance = _performance_projection(
        phases, screenshot, environment, preflight,
        artifact_preparation_duration_ms, workflow_duration_ms,
    )
    performance["metrics"]["cleanupDurationMs"] = cleanup_duration_ms
    api_first = read_json(reports / "api-smoke-first.json")
    api_restart = read_json(reports / "api-smoke-restart.json")
    telemetry_restart = read_json(reports / "telemetry-restart-proof.json")
    checks = {
        "preflight": preflight,
        "browser": _browser_projection(browser, screenshot),
        "api": {
            "first": _status_bool(api_first),
            "restart": _status_bool(api_restart) if restart_executed else "not-run",
            "firstEvidencePath": _report_path("api-smoke-first.json") if api_first else None,
            "restartEvidencePath": _report_path("api-smoke-restart.json") if api_restart else None,
        },
        "restart": {
            "executed": restart_executed,
            "status": "pass" if restart_executed and _status_bool(api_restart) == "pass" else "not-run" if not restart_executed else "fail",
        },
        "telemetry": {
            "enabled": resource_telemetry,
            "restartPersistence": _status_bool(telemetry_restart) if telemetry_restart else "unavailable",
            "evidencePath": _report_path("telemetry-restart-proof.json") if telemetry_restart else None,
        },
        "screenshots": {
            "status": "pass" if browser.get("progress", {}).get("actualScreenshotCount") == browser.get("progress", {}).get("expectedScreenshotCount") else "fail",
            "actual": browser.get("progress", {}).get("actualScreenshotCount"),
            "expected": browser.get("progress", {}).get("expectedScreenshotCount"),
        },
    }
    evidence = {
        "runEvents": _report_path("run-events.jsonl") if events else None,
        "preflight": _report_path("preflight-report.json") if preflight_report else None,
        "buildIdentity": build["evidencePath"],
        "failureSummary": _report_path("failure-summary.json") if failure else None,
        "cancellationSummary": _report_path("cancellation-summary.json") if cancellation else None,
        "artifactManifest": "artifact-manifest.json" if manifest else None,
        "browser": _report_path("browser-smoke-first.json") if browser else None,
        "phaseTimings": _report_path("e2e-phase-timings.json") if phases else None,
        "resourceSummary": _report_path("resource-summary.json") if (reports / "resource-summary.json").is_file() else None,
    }
    summary = {
        "schemaVersion": SUMMARY_SCHEMA_VERSION,
        "result": result,
        "finalizationStatus": finalization,
        "execution": {
            "repository": repository,
            "runId": run_id,
            "runAttempt": run_attempt,
            "event": event,
            "ref": ref,
            "triggerSha": trigger_sha,
            "workflowSourceSha": workflow_source_sha,
            "harnessSha": harness_sha,
            "mode": mode,
            "scope": scope,
            "runPurpose": run_purpose,
            "restartExecuted": restart_executed,
            "screenshotWorkers": screenshot_workers,
            "resourceTelemetry": resource_telemetry,
            "contour": contour,
            "startedAtUtc": start,
            "finishedAtUtc": finish,
        },
        "build": build,
        "compatibility": compatibility,
        "terminal": terminal,
        "checks": checks,
        "performance": performance,
        "artifactFootprint": {},
        "evidence": evidence,
        "finalState": {
            "cleanupStatus": cleanup_status,
            "cleanupDurationMs": cleanup_duration_ms,
            "artifactManifestStatus": manifest.get("status") if manifest else "missing",
            "artifactPreparationStatus": artifact_preparation_status,
            "sourceValidated": source_validated,
            "publicValidated": public_validated,
        },
    }

    predicted = 0
    for _ in range(12):
        summary["artifactFootprint"] = _footprint(
            footprint_root,
            predicted_summary_bytes=predicted,
            summary_relative=footprint_summary_relative,
            manifest_relative=footprint_manifest_relative,
        )
        size = len(_json_bytes(summary))
        if size == predicted:
            break
        predicted = size
    summary["artifactFootprint"] = _footprint(
        footprint_root,
        predicted_summary_bytes=predicted,
        summary_relative=footprint_summary_relative,
        manifest_relative=footprint_manifest_relative,
    )
    from e2e_final_summary_build_validation import validate_summary
    validate_summary(summary)
    return summary

