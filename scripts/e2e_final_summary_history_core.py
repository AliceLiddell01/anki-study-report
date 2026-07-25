from __future__ import annotations

from e2e_final_summary_common import *
import e2e_final_summary_history_entry as _entry
globals().update({name: getattr(_entry, name) for name in dir(_entry) if not name.startswith("__")})

def empty_history(*, continuity: str = "bootstrap", reason: str = "no compatible previous history") -> dict[str, Any]:
    return {
        "schemaVersion": HISTORY_SCHEMA_VERSION,
        "generatedAtUtc": utc_now(),
        "continuity": continuity,
        "continuityReason": reason,
        "limits": {
            "maxAgeDays": MAX_HISTORY_AGE_DAYS,
            "maxEntries": MAX_HISTORY_ENTRIES,
            "maxEntriesPerCompatibilityKey": MAX_HISTORY_PER_COMPATIBILITY,
        },
        "entries": [],
    }


def validate_history(document: Any) -> dict[str, Any]:
    root = _closed(document, HISTORY_FIELDS, "history")
    if root["schemaVersion"] != HISTORY_SCHEMA_VERSION:
        raise FinalSummaryError("unsupported history schemaVersion")
    _utc(root["generatedAtUtc"], "history.generatedAtUtc")
    if root["continuity"] not in HISTORY_CONTINUITY:
        raise FinalSummaryError("history.continuity is invalid")
    if not isinstance(root["continuityReason"], str):
        raise FinalSummaryError("history.continuityReason is invalid")
    limits = _closed(root["limits"], HISTORY_LIMIT_FIELDS, "history.limits")
    if limits != {
        "maxAgeDays": MAX_HISTORY_AGE_DAYS,
        "maxEntries": MAX_HISTORY_ENTRIES,
        "maxEntriesPerCompatibilityKey": MAX_HISTORY_PER_COMPATIBILITY,
    }:
        raise FinalSummaryError("history limits differ from schema v1")
    entries = root["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_HISTORY_ENTRIES:
        raise FinalSummaryError("history entries are invalid")
    identities: set[tuple[int, int]] = set()
    for entry in entries:
        validate_history_entry(entry)
        identity = (int(entry["runId"]), int(entry["runAttempt"]))
        if identity in identities:
            raise FinalSummaryError("history contains duplicate runId/runAttempt")
        identities.add(identity)
    expected = sorted(entries, key=lambda row: (row["startedAtUtc"], row["runId"], row["runAttempt"]))
    if entries != expected:
        raise FinalSummaryError("history entries are not deterministically sorted")
    _safe_tree(root)
    if len(_json_bytes(root)) > MAX_HISTORY_BYTES:
        raise FinalSummaryError(f"history exceeds {MAX_HISTORY_BYTES} UTF-8 bytes")
    return dict(root)


def merge_history(
    previous: Mapping[str, Any] | None,
    current_entry: Mapping[str, Any],
    *,
    generated_at_utc: str | None = None,
    reset_reason: str | None = None,
) -> dict[str, Any]:
    validate_history_entry(current_entry)
    now_value = generated_at_utc or current_entry["finishedAtUtc"]
    now_dt = datetime.fromisoformat(now_value[:-1] + "+00:00")
    continuity = "bootstrap"
    reason = "no previous history artifact"
    rows: list[dict[str, Any]] = []
    if previous is not None:
        try:
            validated = validate_history(previous)
        except FinalSummaryError as exc:
            continuity = "reset"
            reason = reset_reason or f"previous history rejected: {exc}"
        else:
            rows = [dict(row) for row in validated["entries"]]
            continuity = "append"
            reason = "validated previous history appended"
    dedup = {(int(row["runId"]), int(row["runAttempt"])): row for row in rows}
    dedup[(int(current_entry["runId"]), int(current_entry["runAttempt"]))] = dict(current_entry)
    cutoff = now_dt - timedelta(days=MAX_HISTORY_AGE_DAYS)
    rows = [
        row for row in dedup.values()
        if datetime.fromisoformat(row["finishedAtUtc"][:-1] + "+00:00") >= cutoff
    ]
    rows.sort(key=lambda row: (row["startedAtUtc"], row["runId"], row["runAttempt"]))
    per_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        per_key.setdefault(row["compatibilityKey"], []).append(row)
    kept: set[tuple[int, int]] = set()
    for group in per_key.values():
        for row in group[-MAX_HISTORY_PER_COMPATIBILITY:]:
            kept.add((int(row["runId"]), int(row["runAttempt"])))
    rows = [row for row in rows if (int(row["runId"]), int(row["runAttempt"])) in kept]
    rows = rows[-MAX_HISTORY_ENTRIES:]
    document = {
        "schemaVersion": HISTORY_SCHEMA_VERSION,
        "generatedAtUtc": normalize_utc(now_value),
        "continuity": continuity,
        "continuityReason": reason,
        "limits": {
            "maxAgeDays": MAX_HISTORY_AGE_DAYS,
            "maxEntries": MAX_HISTORY_ENTRIES,
            "maxEntriesPerCompatibilityKey": MAX_HISTORY_PER_COMPATIBILITY,
        },
        "entries": rows,
    }
    return validate_history(document)


def _inclusive_percentile(values: Sequence[float], percentile: int) -> float:
    if not values:
        raise FinalSummaryError("percentile sample is empty")
    if len(values) == 1:
        return float(values[0])
    return float(statistics.quantiles(values, n=100, method="inclusive")[percentile - 1])


def percentile(values: Sequence[int | float], *, percentile_value: int, minimum: int) -> dict[str, Any]:
    normalized = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if len(normalized) < minimum:
        return {"value": None, "sampleCount": len(normalized), "status": "insufficient-history"}
    return {
        "value": _inclusive_percentile(sorted(normalized), percentile_value),
        "sampleCount": len(normalized),
        "status": "available",
    }


def _eligible_successes(history: Mapping[str, Any], compatibility_key: str) -> list[Mapping[str, Any]]:
    return [
        row for row in history["entries"]
        if row["compatibilityKey"] == compatibility_key
        and row["result"] == "success"
        and row["purpose"] == "acceptance"
        and row["contour"] == "cloud"
        and row["finalizationStatus"] == "complete"
    ]


def first_run_pass_rate(history: Mapping[str, Any]) -> dict[str, Any]:
    candidates: dict[str, list[Mapping[str, Any]]] = {}
    excluded: dict[str, int] = {}
    for row in history["entries"]:
        first = row["firstAttempt"]
        if not first["eligible"] or row["candidateKey"] is None:
            reason = first["exclusionReason"] or "ineligible"
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        candidates.setdefault(row["candidateKey"], []).append(row)
    outcomes: list[str] = []
    for rows in candidates.values():
        rows = sorted(rows, key=lambda row: (row["startedAtUtc"], row["runId"], row["runAttempt"]))
        first = rows[0]
        if first["runAttempt"] != 1:
            excluded["missing-first-attempt"] = excluded.get("missing-first-attempt", 0) + 1
            continue
        outcomes.append("pass" if first["result"] == "success" else "fail")
        for repeated in rows[1:]:
            reason = "rerun-attempt" if repeated["runId"] == first["runId"] else "repeat-candidate-execution"
            excluded[reason] = excluded.get(reason, 0) + 1
    numerator = outcomes.count("pass")
    denominator = len(outcomes)
    return {
        "passedCandidates": numerator,
        "eligibleCandidates": denominator,
        "rate": numerator / denominator if denominator else None,
        "excludedRuns": sum(excluded.values()),
        "excludedReasons": dict(sorted(excluded.items())),
    }

