from __future__ import annotations

from e2e_final_summary_common import *
import e2e_final_summary_history_entry as _entry
import e2e_final_summary_history_core as _history
globals().update({name: getattr(_entry, name) for name in dir(_entry) if not name.startswith("__")})
globals().update({name: getattr(_history, name) for name in dir(_history) if not name.startswith("__")})

def aggregate_history(history: Mapping[str, Any], current_summary: Mapping[str, Any]) -> dict[str, Any]:
    validate_history(history)
    validate_summary(current_summary)
    key = current_summary["compatibility"]["key"]
    successes = _eligible_successes(history, key)
    metric_ids = (
        "workflowDurationMs", "canonicalDurationMs", "preflightDurationMs",
        "imagePreparationDurationMs", "browserContourDurationMs",
        "artifactPreparationDurationMs", "cleanupDurationMs",
        "artifactUncompressedBytes", "mainArtifactUploadedBytes", "artifactUploadDurationMs",
        "runEventProducerDurationMs", "runEventProducerCalls",
    )
    metrics: dict[str, Any] = {}
    for metric_id in metric_ids:
        values = [
            row["metrics"].get(metric_id)
            for row in successes
            if isinstance(row["metrics"].get(metric_id), (int, float))
        ]
        metrics[metric_id] = {
            "p50": percentile(values, percentile_value=50, minimum=3),
            "p95": percentile(values, percentile_value=95, minimum=20),
        }
    stable_phase_ids = sorted(set().union(*(row["phaseDurationsMs"].keys() for row in successes))) if successes else []
    phase_metrics = {}
    for phase_id in stable_phase_ids:
        values = [row["phaseDurationsMs"].get(phase_id) for row in successes if isinstance(row["phaseDurationsMs"].get(phase_id), (int, float))]
        phase_metrics[phase_id] = {
            "p50": percentile(values, percentile_value=50, minimum=3),
            "p95": percentile(values, percentile_value=95, minimum=20),
        }
    stable_item_ids = sorted(set().union(*(row["browserItemDurationsMs"].keys() for row in successes))) if successes else []
    item_metrics = {}
    for item_id in stable_item_ids:
        values = [row["browserItemDurationsMs"].get(item_id) for row in successes if isinstance(row["browserItemDurationsMs"].get(item_id), (int, float))]
        item_metrics[item_id] = {
            "p50": percentile(values, percentile_value=50, minimum=3),
            "p95": percentile(values, percentile_value=95, minimum=20),
        }
    return {
        "schemaVersion": AGGREGATION_SCHEMA_VERSION,
        "generatedAtUtc": history["generatedAtUtc"],
        "compatibilityKey": key,
        "compatibleSuccessfulSamples": len(successes),
        "percentileMethod": "statistics.quantiles(n=100, method=inclusive)",
        "minimumSamples": {"p50": 3, "p95": 20},
        "metrics": metrics,
        "phaseDurationsMs": phase_metrics,
        "browserItemDurationsMs": item_metrics,
        "firstRunPassRate": first_run_pass_rate(history),
    }


def render_observations(
    summary: Mapping[str, Any], history: Mapping[str, Any], aggregation: Mapping[str, Any]
) -> dict[str, Any]:
    current_metrics = summary["performance"].get("metrics", {})
    observations: dict[str, Any] = {}
    for metric_id, aggregate in aggregation.get("metrics", {}).items():
        current = current_metrics.get(metric_id)
        if metric_id == "artifactUncompressedBytes":
            current = summary["artifactFootprint"].get("totalUncompressedBytes")
        elif metric_id in {"mainArtifactUploadedBytes", "artifactUploadDurationMs"}:
            current_entry = next(
                (
                    row for row in reversed(history["entries"])
                    if row["runId"] == summary["execution"]["runId"]
                    and row["runAttempt"] == summary["execution"]["runAttempt"]
                ),
                None,
            )
            current = current_entry["metrics"].get(metric_id) if current_entry else None
        p50 = aggregate["p50"]
        p95 = aggregate["p95"]
        if not isinstance(current, (int, float)):
            status = "not-comparable"
        elif p50["value"] is None:
            status = "insufficient-history"
        elif p95["value"] is not None and current > p95["value"]:
            status = "above-p95"
        elif current > p50["value"]:
            status = "above-p50"
        elif current < p50["value"]:
            status = "improved"
        else:
            status = "within-history"
        baseline = p50["value"]
        observations[metric_id] = {
            "current": current,
            "p50": p50["value"],
            "p95": p95["value"],
            "absoluteDeltaFromP50": current - baseline if isinstance(current, (int, float)) and isinstance(baseline, (int, float)) else None,
            "percentDeltaFromP50": ((current - baseline) * 100 / baseline) if isinstance(current, (int, float)) and isinstance(baseline, (int, float)) and baseline else None,
            "sampleCount": p50["sampleCount"],
            "status": status,
        }
    current_observed = summary["compatibility"]["observed"]
    prior = [
        row for row in history["entries"]
        if row["compatibilityKey"] == summary["compatibility"]["key"]
        and (row["runId"], row["runAttempt"]) != (summary["execution"]["runId"], summary["execution"]["runAttempt"])
    ]
    caveats: list[str] = []
    if prior:
        previous_observed = prior[-1]["observed"]
        for key in sorted(set(current_observed) | set(previous_observed)):
            if current_observed.get(key) != previous_observed.get(key):
                caveats.append(f"{key} changed")
    document = {
        "schemaVersion": OBSERVATIONS_SCHEMA_VERSION,
        "generatedAtUtc": history["generatedAtUtc"],
        "classification": "observational-only",
        "historyContinuity": history["continuity"],
        "compatibilityKey": summary["compatibility"]["key"],
        "compatibleSuccessfulSamples": aggregation["compatibleSuccessfulSamples"],
        "runnerEnvironmentCaveats": caveats,
        "metrics": observations,
    }
    _safe_tree(document)
    return document


def render_observations_markdown(document: Mapping[str, Any]) -> str:
    lines = [
        "# Наблюдения E2E",
        "",
        "Классификация: **только наблюдение; CI не блокируется**.",
        "",
        f"- Continuity: `{document['historyContinuity']}`",
        f"- Compatible successful samples: `{document['compatibleSuccessfulSamples']}`",
        f"- Compatibility key: `{document['compatibilityKey']}`",
        "",
        "| Metric | Current | p50 | p95 | Samples | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for metric_id, row in sorted(document["metrics"].items()):
        def show(value: Any) -> str:
            return "n/a" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)
        lines.append(
            f"| `{metric_id}` | {show(row['current'])} | {show(row['p50'])} | "
            f"{show(row['p95'])} | {row['sampleCount']} | `{row['status']}` |"
        )
    if document["runnerEnvironmentCaveats"]:
        lines.extend(["", "## Caveats", ""])
        lines.extend(f"- {value}" for value in document["runnerEnvironmentCaveats"])
    return "\n".join(lines) + "\n"


def legacy_projection(summary: Mapping[str, Any]) -> dict[str, Any]:
    validate_summary(summary)
    execution = summary["execution"]
    build = summary["build"]
    footprint = summary["artifactFootprint"]
    observed = summary["compatibility"]["observed"]
    metrics = summary["performance"]["metrics"]
    return {
        "schemaVersion": 2,
        "derivedFrom": "artifacts/reports/final-run-summary.json",
        "repository": execution["repository"],
        "commitSha": execution["triggerSha"],
        "ref": execution["ref"],
        "event": execution["event"],
        "runId": str(execution["runId"]),
        "runAttempt": str(execution["runAttempt"]),
        "mode": execution["mode"],
        "scope": execution["scope"],
        "runPurpose": execution["runPurpose"],
        "screenshotWorkers": execution["screenshotWorkers"],
        "screenshotCount": summary["checks"]["screenshots"]["actual"],
        "runnerOs": observed.get("runnerOs"),
        "runnerImage": observed.get("runnerImage"),
        "powershellVersion": observed.get("powershellVersion"),
        "dockerClientVersion": observed.get("dockerClientVersion"),
        "dockerServerVersion": observed.get("dockerServerVersion"),
        "dockerComposeVersion": observed.get("dockerComposeVersion"),
        "ankiVersion": summary["compatibility"]["dimensions"].get("ankiVersion"),
        "packageSource": build["packageSource"],
        "buildIdentityDigest": build["identityDigest"],
        "e2eCheckoutSha": execution["harnessSha"],
        "result": summary["result"],
        "failureCategory": summary["terminal"]["failureCode"] or "none",
        "startedAt": execution["startedAtUtc"],
        "finishedAt": execution["finishedAtUtc"],
        "workflowDurationSeconds": metrics.get("workflowDurationMs") / 1000 if isinstance(metrics.get("workflowDurationMs"), (int, float)) else None,
        "canonicalDurationSeconds": metrics.get("canonicalDurationMs") / 1000 if isinstance(metrics.get("canonicalDurationMs"), (int, float)) else None,
        "artifactManifestStatus": summary["finalState"]["artifactManifestStatus"],
        "artifactFileCount": footprint["fileCount"],
        "artifactBytes": footprint["totalUncompressedBytes"],
        "compatibilityKey": summary["compatibility"]["key"],
    }


def render_legacy_markdown(summary: Mapping[str, Any]) -> str:
    execution = summary["execution"]
    return f"""# Full Docker / Anki E2E summary

> Производная compatibility-проекция из `artifacts/reports/final-run-summary.json`.

| Поле | Значение |
| --- | --- |
| Result | {summary['result']} |
| Finalization | {summary['finalizationStatus']} |
| Run / attempt | {execution['runId']} / {execution['runAttempt']} |
| Mode / scope / purpose | {execution['mode']} / {execution['scope']} / {execution['runPurpose']} |
| Build identity | `{summary['build']['identityDigest'] or 'n/a'}` |
| Compatibility key | `{summary['compatibility']['key']}` |
| Preflight | {summary['checks']['preflight']['passedChecks']}/{summary['checks']['preflight']['totalChecks']} |
| Browser | {summary['checks']['browser']['passedItems']}/{summary['checks']['browser']['totalItems']} |
| Screenshots | {summary['checks']['screenshots']['actual']}/{summary['checks']['screenshots']['expected']} |
| Artifact files / bytes | {summary['artifactFootprint']['fileCount']} / {summary['artifactFootprint']['totalUncompressedBytes']} |
"""


def render_github_summary(
    summary: Mapping[str, Any], aggregation: Mapping[str, Any] | None = None,
    history: Mapping[str, Any] | None = None, main_artifact: Mapping[str, Any] | None = None,
    history_artifact: Mapping[str, Any] | None = None,
) -> str:
    execution = summary["execution"]
    checks = summary["checks"]
    metrics = summary["performance"]["metrics"]
    lines = [
        "## Result", "",
        f"- Result / finalization: `{summary['result']}` / `{summary['finalizationStatus']}`",
        f"- Run / attempt: `{execution['runId']}` / `{execution['runAttempt']}`",
        f"- Build identity: `{summary['build']['identityDigest'] or 'n/a'}`",
        f"- Compatibility key: `{summary['compatibility']['key']}`",
        "", "## Checks", "",
        f"- Preflight: `{checks['preflight']['passedChecks']}/{checks['preflight']['totalChecks']}`",
        f"- Browser items / screenshots: `{checks['browser']['passedItems']}/{checks['browser']['totalItems']}` / `{checks['screenshots']['actual']}/{checks['screenshots']['expected']}`",
        f"- API / restart / telemetry: `{checks['api']['first']}` / `{checks['restart']['status']}` / `{checks['telemetry']['restartPersistence']}`",
        f"- Terminal: `{summary['terminal']['event']}` phase=`{summary['terminal']['phaseId'] or 'n/a'}` item=`{summary['terminal']['itemId'] or 'n/a'}`",
        "", "## Performance", "",
        f"- Canonical / browser / artifact: `{metrics.get('canonicalDurationMs')}` / `{metrics.get('browserContourDurationMs')}` / `{summary['artifactFootprint']['totalUncompressedBytes']}`",
    ]
    if aggregation:
        canonical = aggregation["metrics"].get("canonicalDurationMs", {})
        lines.append(
            f"- Compatible samples: `{aggregation['compatibleSuccessfulSamples']}`; "
            f"p50=`{canonical.get('p50', {}).get('value') or 'insufficient-history'}`; "
            f"p95=`{canonical.get('p95', {}).get('value') or 'insufficient-history'}`"
        )
        reliability = aggregation["firstRunPassRate"]
        lines.extend([
            "", "## Reliability", "",
            f"- Candidate key: `{candidate_key(summary) or 'n/a'}`",
            f"- First-run pass rate: `{reliability['passedCandidates']}/{reliability['eligibleCandidates']}`",
            f"- Excluded runs: `{reliability['excludedRuns']}`",
        ])
    if main_artifact or history_artifact or history:
        lines.extend(["", "## Artifacts", ""])
        if main_artifact:
            lines.append(
                f"- Main: ID `{main_artifact.get('id') or 'n/a'}`, digest `{main_artifact.get('digest') or 'n/a'}`, size `{main_artifact.get('sizeBytes') or 'n/a'}`"
            )
        if history_artifact:
            lines.append(
                f"- History: ID `{history_artifact.get('id') or 'n/a'}`, digest `{history_artifact.get('digest') or 'n/a'}`"
            )
        if history:
            lines.append(f"- History continuity: `{history['continuity']}`")
    return "\n".join(lines) + "\n"



__all__ = [name for name in globals() if not name.startswith("__")]
