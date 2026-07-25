from __future__ import annotations

from e2e_final_summary_common import *
import e2e_final_summary_build_projection as _projection
import e2e_final_summary_build_core as _core
globals().update({name: getattr(_projection, name) for name in dir(_projection) if not name.startswith("__")})
globals().update({name: getattr(_core, name) for name in dir(_core) if not name.startswith("__")})

def validate_summary(document: Any) -> dict[str, Any]:
    root = _closed(document, SUMMARY_FIELDS, "final summary")
    if root["schemaVersion"] != SUMMARY_SCHEMA_VERSION:
        raise FinalSummaryError("unsupported final summary schemaVersion")
    if root["result"] not in RESULTS:
        raise FinalSummaryError("result is invalid")
    if root["finalizationStatus"] not in FINALIZATION_STATUSES:
        raise FinalSummaryError("finalizationStatus is invalid")
    execution = _closed(root["execution"], EXECUTION_FIELDS, "execution")
    if not isinstance(execution["repository"], str) or "/" not in execution["repository"]:
        raise FinalSummaryError("execution.repository is invalid")
    _positive_int(execution["runId"], "execution.runId")
    _positive_int(execution["runAttempt"], "execution.runAttempt")
    for key in ("event", "ref", "mode", "scope"):
        if not isinstance(execution[key], str) or not execution[key]:
            raise FinalSummaryError(f"execution.{key} is invalid")
        _safe_string(execution[key], f"execution.{key}")
    _sha(execution["triggerSha"], "execution.triggerSha")
    _sha(execution["workflowSourceSha"], "execution.workflowSourceSha")
    _sha(execution["harnessSha"], "execution.harnessSha")
    if execution["runPurpose"] not in PURPOSES:
        raise FinalSummaryError("execution.runPurpose is invalid")
    if execution["contour"] not in CONTOURS:
        raise FinalSummaryError("execution.contour is invalid")
    if not isinstance(execution["restartExecuted"], bool) or not isinstance(execution["resourceTelemetry"], bool):
        raise FinalSummaryError("execution boolean fields are invalid")
    _positive_int(execution["screenshotWorkers"], "execution.screenshotWorkers")
    started = _utc(execution["startedAtUtc"], "execution.startedAtUtc")
    finished = _utc(execution["finishedAtUtc"], "execution.finishedAtUtc")
    if datetime.fromisoformat(finished[:-1] + "+00:00") < datetime.fromisoformat(started[:-1] + "+00:00"):
        raise FinalSummaryError("execution finished before it started")

    build = _closed(root["build"], BUILD_FIELDS, "build")
    if build["packageSource"] not in {"fast-ci-artifact", "release-artifact", "source-build", "unresolved"}:
        raise FinalSummaryError("build.packageSource is invalid")
    if build["status"] not in {"resolved", "unresolved"}:
        raise FinalSummaryError("build.status is invalid")
    if build["identityDigest"] is not None:
        _digest(build["identityDigest"], "build.identityDigest")
    if build["evidencePath"] is not None:
        safe_relative_path(build["evidencePath"], "build.evidencePath")
    if root["result"] == "success" and root["finalizationStatus"] != "complete":
        raise FinalSummaryError("successful final summary must be complete")
    if root["result"] == "success" and build["packageSource"] in {"fast-ci-artifact", "release-artifact"} and build["status"] != "resolved":
        raise FinalSummaryError("successful artifact-backed summary requires resolved build identity")

    compatibility = _closed(root["compatibility"], COMPATIBILITY_FIELDS, "compatibility")
    if compatibility["schemaVersion"] != COMPATIBILITY_SCHEMA_VERSION:
        raise FinalSummaryError("compatibility schemaVersion is invalid")
    _digest(compatibility["key"], "compatibility.key")
    if not isinstance(compatibility["dimensions"], dict) or not compatibility["dimensions"]:
        raise FinalSummaryError("compatibility.dimensions must be a non-empty object")
    if compatibility["key"] != hash_object(compatibility["dimensions"]):
        raise FinalSummaryError("compatibility.key differs from canonical dimensions")
    if not isinstance(compatibility["observed"], dict):
        raise FinalSummaryError("compatibility.observed must be an object")

    terminal = _closed(root["terminal"], TERMINAL_FIELDS, "terminal")
    if terminal["event"] not in {"run/pass", "run/fail", "run/cancel", "host/fail"}:
        raise FinalSummaryError("terminal.event is invalid")
    if terminal["phaseId"] is not None:
        _id(terminal["phaseId"], "terminal.phaseId")
    if terminal["itemId"] is not None:
        _id(terminal["itemId"], "terminal.itemId")
    if terminal["failureCode"] is not None:
        _id(terminal["failureCode"], "terminal.failureCode")
    if terminal["signal"] not in {None, "SIGINT", "SIGTERM"}:
        raise FinalSummaryError("terminal.signal is invalid")
    if isinstance(terminal["exitCode"], bool) or not isinstance(terminal["exitCode"], int):
        raise FinalSummaryError("terminal.exitCode must be an integer")
    expected_event = {"success": "run/pass", "failure": {"run/fail", "host/fail"}, "cancelled": "run/cancel"}
    if root["result"] == "failure":
        if terminal["event"] not in expected_event["failure"]:
            raise FinalSummaryError("failure result differs from terminal event")
    elif terminal["event"] != expected_event[root["result"]]:
        raise FinalSummaryError("result differs from terminal event")
    if root["result"] == "success" and (terminal["exitCode"] != 0 or terminal["failureCode"] is not None or terminal["signal"] is not None):
        raise FinalSummaryError("success terminal fields are inconsistent")
    if root["result"] == "cancelled":
        if terminal["failureCode"] != "ASR-E2E-CANCELLED" or terminal["exitCode"] not in {130, 143}:
            raise FinalSummaryError("cancellation terminal fields are inconsistent")
        expected_signal = "SIGINT" if terminal["exitCode"] == 130 else "SIGTERM"
        if terminal["signal"] != expected_signal:
            raise FinalSummaryError("cancellation signal/exitCode parity failed")

    final_state = _closed(root["finalState"], FINAL_STATE_FIELDS, "finalState")
    if final_state["cleanupStatus"] not in CLEANUP_STATUSES:
        raise FinalSummaryError("finalState.cleanupStatus is invalid")
    if final_state["artifactPreparationStatus"] not in ARTIFACT_PREPARATION_STATUSES:
        raise FinalSummaryError("finalState.artifactPreparationStatus is invalid")
    _non_negative(final_state["cleanupDurationMs"], "finalState.cleanupDurationMs", nullable=True)
    for key in ("sourceValidated", "publicValidated"):
        if not isinstance(final_state[key], bool):
            raise FinalSummaryError(f"finalState.{key} must be boolean")
    if root["finalizationStatus"] == "complete":
        if final_state["cleanupStatus"] in {"unknown", "not-started"}:
            raise FinalSummaryError("complete summary requires a known final cleanup state")
        if final_state["publicValidated"] and final_state["artifactPreparationStatus"] != "success":
            raise FinalSummaryError("publicly finalized summary requires successful artifact preparation")
        if not final_state["sourceValidated"]:
            raise FinalSummaryError("complete summary requires validated source evidence")
    if root["result"] == "success" and final_state["cleanupStatus"] != "success":
        raise FinalSummaryError("successful summary requires successful final cleanup")
    if not isinstance(root["checks"], dict) or not isinstance(root["performance"], dict):
        raise FinalSummaryError("checks and performance must be objects")
    footprint = root["artifactFootprint"]
    if not isinstance(footprint, dict):
        raise FinalSummaryError("artifactFootprint must be an object")
    for key in ("fileCount", "totalUncompressedBytes", "screenshotCount", "screenshotBytes", "reportsCount", "reportsBytes"):
        _non_negative(footprint.get(key), f"artifactFootprint.{key}")
    largest = footprint.get("largestFiles")
    if not isinstance(largest, list) or len(largest) > MAX_LARGEST_FILES:
        raise FinalSummaryError("artifactFootprint.largestFiles is invalid")
    for row in largest:
        if not isinstance(row, dict) or set(row) != {"path", "bytes"}:
            raise FinalSummaryError("largestFiles row is invalid")
        safe_relative_path(row["path"], "largestFiles.path")
        _non_negative(row["bytes"], "largestFiles.bytes")
    evidence = root["evidence"]
    if not isinstance(evidence, dict):
        raise FinalSummaryError("evidence must be an object")
    for key, value in evidence.items():
        if value is not None:
            safe_relative_path(value, f"evidence.{key}")
    _safe_tree(root)
    if len(_json_bytes(root)) > MAX_SUMMARY_BYTES:
        raise FinalSummaryError(f"final summary exceeds {MAX_SUMMARY_BYTES} UTF-8 bytes")
    return dict(root)


def export_public_summary(raw_path: Path, public_path: Path) -> tuple[dict[str, Any], str]:
    raw = load_summary(raw_path)
    _safe_tree(raw)
    write_json(public_path, raw, max_bytes=MAX_SUMMARY_BYTES)
    return validate_pair(raw_path, public_path)


def finalize_public_artifact(
    artifact_root: Path,
    public_root: Path,
    raw_output: Path,
    *,
    context: Mapping[str, Any],
    public_summary_relative: str = "artifacts/reports/final-run-summary.json",
    public_manifest_relative: str = "artifacts/artifact-manifest.json",
    legacy_json_relative: str = "ci-e2e-summary.json",
    legacy_markdown_relative: str = "ci-e2e-summary.md",
) -> dict[str, Any]:
    from e2e_final_summary_history import legacy_projection, render_legacy_markdown

    public_root = public_root.resolve()
    public_summary = public_root / PurePosixPath(safe_relative_path(public_summary_relative))
    legacy_json = public_root / PurePosixPath(safe_relative_path(legacy_json_relative))
    legacy_markdown = public_root / PurePosixPath(safe_relative_path(legacy_markdown_relative))
    previous_bytes: bytes | None = None
    summary: dict[str, Any] | None = None
    build_context = dict(context)
    build_context.pop("footprint_root", None)
    build_context.pop("footprint_summary_relative", None)
    build_context.pop("footprint_manifest_relative", None)
    for _ in range(12):
        summary = build_summary(
            artifact_root,
            footprint_root=public_root,
            footprint_summary_relative=public_summary_relative,
            footprint_manifest_relative=public_manifest_relative,
            **build_context,
        )
        current_bytes = _json_bytes(summary)
        write_json(raw_output, summary, max_bytes=MAX_SUMMARY_BYTES)
        export_public_summary(raw_output, public_summary)
        write_json(legacy_json, legacy_projection(summary))
        atomic_write_bytes(legacy_markdown, render_legacy_markdown(summary).encode("utf-8"))
        if current_bytes == previous_bytes:
            break
        previous_bytes = current_bytes
    else:
        raise FinalSummaryError("public artifact footprint did not reach a deterministic fixed point")
    assert summary is not None
    validate_pair(raw_output, public_summary)
    return summary


def load_summary(path: Path) -> dict[str, Any]:
    return validate_summary(read_json(path, required=True))


def validate_pair(raw_path: Path, public_path: Path) -> tuple[dict[str, Any], str]:
    raw = load_summary(raw_path)
    public = load_summary(public_path)
    if raw != public:
        raise FinalSummaryError("raw/public final summaries are not semantically equal")
    return raw, file_digest(public_path)



__all__ = [name for name in globals() if not name.startswith("__")]
