from __future__ import annotations

from e2e_final_summary_common import *

def build_compatibility(
    *, manifest: Mapping[str, Any], browser: Mapping[str, Any],
    screenshot: Mapping[str, Any], phases: Mapping[str, Any],
    environment: Mapping[str, Any], workload: Mapping[str, Any],
    mode: str, scope: str, restart_executed: bool, screenshot_workers: int,
    resource_telemetry: bool, package_source: str, runner_family: str,
    contour: str, observed: Mapping[str, Any],
) -> dict[str, Any]:
    plan = browser.get("plan") if isinstance(browser.get("plan"), dict) else {}
    dimensions = {
        "contour": contour,
        "mode": mode,
        "scope": scope,
        "restartExecuted": restart_executed,
        "screenshotWorkers": screenshot_workers,
        "resourceTelemetry": resource_telemetry,
        "ankiVersion": manifest.get("ankiVersion"),
        "packageSourceClass": "release" if package_source == "release-artifact" else "non-release",
        "realDeckWorkloadDigest": _workload_digest(workload),
        "browserPlanSchemaVersion": plan.get("schemaVersion"),
        "browserReportSchemaVersion": browser.get("schemaVersion"),
        "browserItemTimingSemantics": screenshot.get("itemTimingSemantics"),
        "runEventSchemaVersion": 2,
        "phaseTimingSchemaVersion": phases.get("schemaVersion"),
        "artifactSchemaVersion": manifest.get("artifactSchemaVersion"),
        "environmentContractDigest": environment.get("environmentContractSha256"),
        "imagePlatform": environment.get("imagePlatform"),
        "runnerFamily": runner_family,
    }
    dimensions = {
        key: ("unavailable" if value is None else value)
        for key, value in dimensions.items()
    }
    return {
        "schemaVersion": COMPATIBILITY_SCHEMA_VERSION,
        "key": hash_object(dimensions),
        "dimensions": dimensions,
        "observed": dict(observed),
    }


def _status_bool(report: Mapping[str, Any]) -> str:
    if report.get("ok") is True:
        return "pass"
    if report.get("ok") is False:
        return "fail"
    status = report.get("status")
    if isinstance(status, str):
        lowered = status.lower()
        if lowered in {"pass", "passed", "success"}:
            return "pass"
        if lowered in {"fail", "failed", "failure"}:
            return "fail"
    return "unavailable"


def _preflight_projection(report: Mapping[str, Any]) -> dict[str, Any]:
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    passed = sum(1 for row in checks if isinstance(row, dict) and str(row.get("status")).upper() == "PASS")
    failed_rows = [row for row in checks if isinstance(row, dict) and str(row.get("status")).upper() == "FAIL"]
    overall = str(report.get("status") or report.get("result") or "").upper()
    return {
        "status": "pass" if overall in {"PASS", "SUCCESS"} and not failed_rows else "fail" if failed_rows or overall in {"FAIL", "FAILURE"} else "unavailable",
        "passedChecks": passed,
        "failedChecks": len(failed_rows),
        "totalChecks": len(checks),
        "failedCheckId": str(failed_rows[0].get("id")) if failed_rows and failed_rows[0].get("id") else None,
        "durationMs": report.get("durationMs") if isinstance(report.get("durationMs"), (int, float)) else None,
        "evidencePath": _report_path("preflight-report.json") if report else None,
    }


def _browser_projection(browser: Mapping[str, Any], screenshot: Mapping[str, Any]) -> dict[str, Any]:
    progress = browser.get("progress") if isinstance(browser.get("progress"), dict) else {}
    return {
        "status": _status_bool(browser),
        "terminalItems": progress.get("terminalItems"),
        "passedItems": progress.get("passedItems"),
        "failedItems": progress.get("failedItems"),
        "skippedItems": progress.get("skippedItems"),
        "remainingItems": progress.get("remainingItems"),
        "totalItems": progress.get("totalItems"),
        "expectedScreenshots": progress.get("expectedScreenshotCount"),
        "actualScreenshots": progress.get("actualScreenshotCount"),
        "configuredWorkers": screenshot.get("configuredWorkers"),
        "itemTimingSemantics": screenshot.get("itemTimingSemantics"),
        "evidencePath": _report_path("browser-smoke-first.json") if browser else None,
    }


def _performance_projection(
    phases: Mapping[str, Any], screenshot: Mapping[str, Any], environment: Mapping[str, Any],
    preflight: Mapping[str, Any], artifact_preparation_duration_ms: int | None,
    workflow_duration_ms: int | None,
) -> dict[str, Any]:
    phase_rows = phases.get("phases") if isinstance(phases.get("phases"), list) else []
    stable_phases: dict[str, dict[str, Any]] = {}
    for row in phase_rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        duration = row.get("durationMs")
        if not isinstance(duration, (int, float)) or duration < 0:
            continue
        phase_id = _phase_id(row["name"])
        stable_phases[phase_id] = {
            "durationMs": duration,
            "status": row.get("status"),
            "source": _report_path("e2e-phase-timings.json"),
            "semantics": "producer-wall-time",
        }
        if len(stable_phases) >= MAX_STABLE_PHASES:
            break
    item_rows = screenshot.get("items") if isinstance(screenshot.get("items"), list) else []
    stable_items: dict[str, dict[str, Any]] = {}
    for row in item_rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        duration = row.get("operationDurationMs")
        if not isinstance(duration, (int, float)) or duration < 0:
            continue
        stable_items[row["id"]] = {
            "durationMs": duration,
            "status": row.get("status"),
            "source": _report_path("screenshot-performance.json"),
            "semantics": "operation-only",
        }
        if len(stable_items) >= MAX_STABLE_BROWSER_ITEMS:
            break
    total = stable_phases.get("total-canonical-e2e", {}).get("durationMs")
    browser_contour = screenshot.get("durationMs") if isinstance(screenshot.get("durationMs"), (int, float)) else None
    producer = screenshot.get("producerMetrics") if isinstance(screenshot.get("producerMetrics"), dict) else {}
    metrics = {
        "workflowDurationMs": workflow_duration_ms,
        "canonicalDurationMs": total,
        "preflightDurationMs": preflight.get("durationMs"),
        "imagePreparationDurationMs": environment.get("imagePreparationDurationMs"),
        "browserContourDurationMs": browser_contour,
        "artifactPreparationDurationMs": artifact_preparation_duration_ms,
        "cleanupDurationMs": None,
    }
    return {
        "metrics": metrics,
        "phases": stable_phases,
        "browserItems": stable_items,
        "producer": {
            "runEventProducerCalls": producer.get("runEventProducerCalls"),
            "runEventProducerDurationMs": producer.get("runEventProducerDurationMs"),
            "runEventProducerFailures": producer.get("runEventProducerFailures"),
        },
        "evidencePaths": {
            "phaseTimings": _report_path("e2e-phase-timings.json") if phases else None,
            "browserTiming": _report_path("screenshot-performance.json") if screenshot else None,
            "resourceSummary": _report_path("resource-summary.json"),
        },
    }


def _build_projection(identity: Mapping[str, Any], package_source: str) -> dict[str, Any]:
    if package_source == "fast-ci-artifact":
        digest = identity.get("identityDigest")
        return {
            "packageSource": package_source,
            "identityKind": "non-release-build",
            "identityDigest": digest if isinstance(digest, str) else None,
            "evidencePath": _report_path("non-release-build-identity.json") if identity else None,
            "status": "resolved" if isinstance(digest, str) else "unresolved",
            "reason": None if isinstance(digest, str) else "build materials were not resolved",
        }
    if package_source == "release-artifact":
        digest = identity.get("identityDigest") or identity.get("artifactDigest") or identity.get("sha256")
        return {
            "packageSource": package_source,
            "identityKind": "release-artifact",
            "identityDigest": digest if isinstance(digest, str) and DIGEST_RE.fullmatch(digest) else None,
            "evidencePath": _report_path("release-build-identity.json") if identity else None,
            "status": "resolved" if isinstance(digest, str) else "unresolved",
            "reason": None if isinstance(digest, str) else "release identity evidence is unavailable",
        }
    return {
        "packageSource": package_source,
        "identityKind": None,
        "identityDigest": None,
        "evidencePath": None,
        "status": "unresolved",
        "reason": "build materials were not resolved",
    }


def _result_and_terminal(
    *, events: Sequence[Mapping[str, Any]], failure: Mapping[str, Any],
    cancellation: Mapping[str, Any], preflight: Mapping[str, Any], exit_code: int,
) -> tuple[str, str, dict[str, Any]]:
    terminal = _terminal_event(events)
    phase, item = _last_context(events)
    if terminal:
        status = terminal.get("status")
        mapping = {"pass": "success", "fail": "failure", "cancel": "cancelled"}
        result = mapping.get(status)
        if result is None:
            raise FinalSummaryError("terminal run-event status is invalid")
        event = f"run/{status}"
        failure_code = terminal.get("failureCode")
        signal = None
        terminal_exit = exit_code
        if result == "failure":
            primary = failure.get("primary") if isinstance(failure.get("primary"), dict) else {}
            expected = primary.get("failureCode")
            if expected is not None and failure_code != expected:
                raise FinalSummaryError("run/fail failureCode differs from failure-summary primary")
            phase = primary.get("phaseId") or phase
            item = primary.get("itemId") or item
        elif result == "cancelled":
            expected = cancellation.get("cancellationCode")
            if expected is not None and failure_code not in {None, expected}:
                raise FinalSummaryError("run/cancel failureCode differs from cancellation summary")
            failure_code = expected or failure_code
            signal = cancellation.get("originalSignal")
            terminal_exit = cancellation.get("originalExitCode", exit_code)
            context = cancellation.get("context") if isinstance(cancellation.get("context"), dict) else {}
            phase = context.get("activePhaseId") or phase
            item = context.get("activeItemId") or item
        return result, "complete" if result == "success" else "partial", {
            "event": event,
            "phaseId": phase,
            "itemId": item,
            "failureCode": failure_code,
            "signal": signal,
            "exitCode": terminal_exit,
        }
    projected = _preflight_projection(preflight)
    if projected["status"] == "fail":
        return "failure", "minimal", {
            "event": "host/fail",
            "phaseId": "preflight",
            "itemId": projected["failedCheckId"],
            "failureCode": None,
            "signal": None,
            "exitCode": exit_code,
        }
    raise FinalSummaryError("no terminal run event or failed preflight evidence is available")
