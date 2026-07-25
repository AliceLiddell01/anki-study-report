from __future__ import annotations

from e2e_final_summary_common import *
from e2e_final_summary_build import *

def candidate_key(summary: Mapping[str, Any]) -> str | None:
    identity = summary["build"].get("identityDigest")
    compatibility = summary["compatibility"].get("key")
    if not isinstance(identity, str) or not isinstance(compatibility, str):
        return None
    identity_kind = summary["build"].get("identityKind")
    return hash_object({"identityKind": identity_kind, "identityDigest": identity, "compatibilityKey": compatibility})


def build_history_entry(
    summary: Mapping[str, Any],
    *,
    summary_digest: str,
    main_artifact_id: int | None,
    main_artifact_digest: str | None,
    main_artifact_size_bytes: int | None,
    main_artifact_expires_at_utc: str | None,
    artifact_upload_duration_ms: int | None = None,
) -> dict[str, Any]:
    validate_summary(summary)
    execution = summary["execution"]
    purpose = execution["runPurpose"]
    candidate = candidate_key(summary)
    eligible = (
        purpose == "acceptance"
        and execution["contour"] == "cloud"
        and execution["mode"] != "perf100"
        and candidate is not None
        and summary["finalizationStatus"] == "complete"
        and summary["result"] in {"success", "failure"}
        and execution["runAttempt"] == 1
    )
    exclusion = None
    if not eligible:
        if purpose != "acceptance":
            exclusion = f"purpose:{purpose}"
        elif execution["contour"] != "cloud":
            exclusion = "local-contour"
        elif execution["mode"] == "perf100":
            exclusion = "perf100"
        elif candidate is None:
            exclusion = "candidate-unavailable"
        elif execution["runAttempt"] > 1:
            exclusion = "rerun-attempt"
        elif summary["result"] == "cancelled":
            exclusion = "cancelled"
        else:
            exclusion = f"finalization:{summary['finalizationStatus']}"
    metrics = summary["performance"].get("metrics", {})
    selected_phases = {
        key: row.get("durationMs")
        for key, row in summary["performance"].get("phases", {}).items()
        if key in {
            "total-canonical-e2e", "browser-real-deck-and-dashboard-capture",
            "manifest-generation-and-validation", "ghcr-exact-pull-validation",
        }
    }
    selected_items = {
        key: row.get("durationMs")
        for key, row in summary["performance"].get("browserItems", {}).items()
        if key in {"browser.launch", "dashboard.setup", "route.home.light", "cards-route.light", "cards-route.dark"}
    }
    entry = {
        "runId": execution["runId"],
        "runAttempt": execution["runAttempt"],
        "candidateKey": candidate,
        "result": summary["result"],
        "finalizationStatus": summary["finalizationStatus"],
        "purpose": purpose,
        "contour": execution["contour"],
        "compatibilityKey": summary["compatibility"]["key"],
        "buildIdentityKind": summary["build"]["identityKind"],
        "buildIdentityDigest": summary["build"]["identityDigest"],
        "summaryDigest": summary_digest,
        "startedAtUtc": execution["startedAtUtc"],
        "finishedAtUtc": execution["finishedAtUtc"],
        "metrics": {
            "workflowDurationMs": metrics.get("workflowDurationMs"),
            "canonicalDurationMs": metrics.get("canonicalDurationMs"),
            "preflightDurationMs": metrics.get("preflightDurationMs"),
            "imagePreparationDurationMs": metrics.get("imagePreparationDurationMs"),
            "browserContourDurationMs": metrics.get("browserContourDurationMs"),
            "artifactPreparationDurationMs": metrics.get("artifactPreparationDurationMs"),
            "cleanupDurationMs": metrics.get("cleanupDurationMs"),
            "artifactUncompressedBytes": summary["artifactFootprint"].get("totalUncompressedBytes"),
            "mainArtifactUploadedBytes": main_artifact_size_bytes,
            "artifactUploadDurationMs": artifact_upload_duration_ms,
            "runEventProducerCalls": summary["performance"].get("producer", {}).get("runEventProducerCalls"),
            "runEventProducerDurationMs": summary["performance"].get("producer", {}).get("runEventProducerDurationMs"),
        },
        "phaseDurationsMs": selected_phases,
        "browserItemDurationsMs": selected_items,
        "mainArtifact": {
            "id": main_artifact_id,
            "digest": main_artifact_digest,
            "sizeBytes": main_artifact_size_bytes,
            "expiresAtUtc": main_artifact_expires_at_utc,
        },
        "firstAttempt": {
            "eligible": eligible,
            "outcome": "pass" if eligible and summary["result"] == "success" else "fail" if eligible and summary["result"] == "failure" else None,
            "exclusionReason": exclusion,
        },
        "observed": summary["compatibility"]["observed"],
    }
    validate_history_entry(entry)
    return entry


def validate_history_entry(entry: Any) -> dict[str, Any]:
    fields = {
        "runId", "runAttempt", "candidateKey", "result", "finalizationStatus", "purpose",
        "contour", "compatibilityKey", "buildIdentityKind", "buildIdentityDigest",
        "summaryDigest", "startedAtUtc", "finishedAtUtc", "metrics",
        "phaseDurationsMs", "browserItemDurationsMs", "mainArtifact", "firstAttempt", "observed",
    }
    if not isinstance(entry, dict) or set(entry) != fields:
        raise FinalSummaryError("history entry field set differs from schema")
    _positive_int(entry["runId"], "history.runId")
    _positive_int(entry["runAttempt"], "history.runAttempt")
    if entry["candidateKey"] is not None:
        _digest(entry["candidateKey"], "history.candidateKey")
    if entry["result"] not in RESULTS or entry["finalizationStatus"] not in FINALIZATION_STATUSES:
        raise FinalSummaryError("history result/finalization is invalid")
    if entry["purpose"] not in PURPOSES or entry["contour"] not in CONTOURS:
        raise FinalSummaryError("history purpose/contour is invalid")
    _digest(entry["compatibilityKey"], "history.compatibilityKey")
    if entry["buildIdentityDigest"] is not None:
        _digest(entry["buildIdentityDigest"], "history.buildIdentityDigest")
    _digest(entry["summaryDigest"], "history.summaryDigest")
    _utc(entry["startedAtUtc"], "history.startedAtUtc")
    _utc(entry["finishedAtUtc"], "history.finishedAtUtc")
    if not isinstance(entry["metrics"], dict) or not isinstance(entry["phaseDurationsMs"], dict) or not isinstance(entry["browserItemDurationsMs"], dict):
        raise FinalSummaryError("history metrics are invalid")
    artifact = entry["mainArtifact"]
    if not isinstance(artifact, dict) or set(artifact) != {"id", "digest", "sizeBytes", "expiresAtUtc"}:
        raise FinalSummaryError("history mainArtifact is invalid")
    if artifact["id"] is not None:
        _positive_int(artifact["id"], "history.mainArtifact.id")
    if artifact["digest"] is not None:
        _digest(artifact["digest"], "history.mainArtifact.digest")
    if artifact["sizeBytes"] is not None:
        _non_negative(artifact["sizeBytes"], "history.mainArtifact.sizeBytes")
    if artifact["expiresAtUtc"] is not None:
        _utc(artifact["expiresAtUtc"], "history.mainArtifact.expiresAtUtc")
    first = entry["firstAttempt"]
    if not isinstance(first, dict) or set(first) != {"eligible", "outcome", "exclusionReason"}:
        raise FinalSummaryError("history firstAttempt is invalid")
    if not isinstance(first["eligible"], bool) or first["outcome"] not in {None, "pass", "fail"}:
        raise FinalSummaryError("history firstAttempt values are invalid")
    _safe_tree(entry)
    return entry
