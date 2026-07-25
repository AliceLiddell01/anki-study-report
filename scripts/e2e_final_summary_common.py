#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import statistics
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SUMMARY_SCHEMA_VERSION = 1
COMPATIBILITY_SCHEMA_VERSION = 1
HISTORY_SCHEMA_VERSION = 1
AGGREGATION_SCHEMA_VERSION = 1
OBSERVATIONS_SCHEMA_VERSION = 1

MAX_SUMMARY_BYTES = 64 * 1024
MAX_HISTORY_BYTES = 512 * 1024
MAX_HISTORY_ENTRIES = 120
MAX_HISTORY_AGE_DAYS = 90
MAX_HISTORY_PER_COMPATIBILITY = 30
MAX_LARGEST_FILES = 10
MAX_STABLE_PHASES = 32
MAX_STABLE_BROWSER_ITEMS = 32

RESULTS = {"success", "failure", "cancelled"}
FINALIZATION_STATUSES = {"complete", "partial", "minimal", "unavailable"}
PURPOSES = {"acceptance", "controlled", "measurement"}
CLEANUP_STATUSES = {"not-started", "success", "failure", "partial", "skipped", "unknown"}
ARTIFACT_PREPARATION_STATUSES = {"success", "failure", "partial", "unavailable"}
CONTOURS = {"cloud", "local"}
HISTORY_CONTINUITY = {"bootstrap", "append", "reset"}
OBSERVATION_STATUSES = {
    "insufficient-history", "within-history", "above-p50", "above-p95", "improved", "not-comparable"
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_RE = re.compile(
    r"(?i)(?:authorization\s*:\s*bearer|[?&](?:access_)?token=|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})"
)
PRIVATE_PATH_RE = re.compile(r"""(?i)(?:[A-Z]:[\\/](?:Users|home)[\\/]|(?:^|[\s"'])/(?:home|users|mnt|tmp|var|root)(?:/|\b))""")

SUMMARY_FIELDS = (
    "schemaVersion", "result", "finalizationStatus", "execution", "build",
    "compatibility", "terminal", "checks", "performance", "artifactFootprint",
    "evidence", "finalState",
)
EXECUTION_FIELDS = (
    "repository", "runId", "runAttempt", "event", "ref", "triggerSha",
    "workflowSourceSha", "harnessSha", "mode", "scope", "runPurpose",
    "restartExecuted", "screenshotWorkers", "resourceTelemetry", "contour",
    "startedAtUtc", "finishedAtUtc",
)
BUILD_FIELDS = (
    "packageSource", "identityKind", "identityDigest", "evidencePath", "status", "reason",
)
COMPATIBILITY_FIELDS = ("schemaVersion", "key", "dimensions", "observed")
TERMINAL_FIELDS = ("event", "phaseId", "itemId", "failureCode", "signal", "exitCode")
FINAL_STATE_FIELDS = (
    "cleanupStatus", "cleanupDurationMs", "artifactManifestStatus",
    "artifactPreparationStatus", "sourceValidated", "publicValidated",
)
HISTORY_FIELDS = ("schemaVersion", "generatedAtUtc", "continuity", "continuityReason", "limits", "entries")
HISTORY_LIMIT_FIELDS = ("maxAgeDays", "maxEntries", "maxEntriesPerCompatibilityKey")

class FinalSummaryError(ValueError):
    pass


def _closed(value: Any, fields: Sequence[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise FinalSummaryError(f"{label} must be an object")
    if set(value) != set(fields):
        unknown = sorted(set(value) - set(fields))
        missing = sorted(set(fields) - set(value))
        raise FinalSummaryError(f"{label} field set differs from schema; unknown={unknown}, missing={missing}")
    return value


def _json_bytes(value: Any, *, pretty: bool = True) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n"
    return text.encode("utf-8")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def hash_object(value: Any) -> str:
    return sha256_digest(canonical_bytes(value))


def _utc(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise FinalSummaryError(f"{label} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FinalSummaryError(f"{label} is invalid") from exc
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_utc(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise FinalSummaryError("timestamp is unavailable")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_relative_path(value: Any, label: str = "path") -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise FinalSummaryError(f"{label} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or re.match(r"^[A-Za-z]:", value):
        raise FinalSummaryError(f"{label} is unsafe: {value!r}")
    _safe_string(value, label)
    return value


def _safe_string(value: str, label: str) -> str:
    if CONTROL_RE.search(value):
        raise FinalSummaryError(f"{label} contains control characters")
    if SECRET_RE.search(value):
        raise FinalSummaryError(f"{label} contains secret-like data")
    if PRIVATE_PATH_RE.search(value):
        raise FinalSummaryError(f"{label} contains a private absolute path")
    return value


def _safe_tree(value: Any, label: str = "document") -> None:
    if isinstance(value, str):
        _safe_string(value, label)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _safe_tree(item, f"{label}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise FinalSummaryError(f"{label} has a non-string key")
            _safe_string(key, f"{label}.key")
            _safe_tree(item, f"{label}.{key}")


def _non_negative(value: Any, label: str, *, nullable: bool = False) -> int | float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise FinalSummaryError(f"{label} must be non-negative")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise FinalSummaryError(f"{label} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise FinalSummaryError(f"{label} must be a positive integer") from exc
    if parsed <= 0:
        raise FinalSummaryError(f"{label} must be a positive integer")
    return parsed


def _sha(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise FinalSummaryError(f"{label} must be a lowercase 40-hex SHA")
    return value


def _digest(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise FinalSummaryError(f"{label} must be a sha256 digest")
    return value


def _id(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not SAFE_ID_RE.fullmatch(value):
        raise FinalSummaryError(f"{label} must be a bounded stable ID")
    return value


def read_json(path: Path, *, required: bool = False) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise FinalSummaryError(f"required JSON evidence is missing: {path}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalSummaryError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise FinalSummaryError(f"JSON evidence must be an object: {path}")
    return value


def read_jsonl(path: Path, *, required: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        if required:
            raise FinalSummaryError(f"required JSONL evidence is missing: {path}")
        return []
    rows: list[dict[str, Any]] = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise FinalSummaryError(f"JSONL row {number} is not an object: {path}")
            rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalSummaryError(f"invalid JSONL evidence: {path}") from exc
    return rows


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: Any, *, max_bytes: int | None = None) -> None:
    data = _json_bytes(value)
    if max_bytes is not None and len(data) > max_bytes:
        raise FinalSummaryError(f"{path.name} exceeds {max_bytes} UTF-8 bytes")
    atomic_write_bytes(path, data)


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _phase_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return normalized[:96] or "unknown"


def _report_path(name: str) -> str:
    return f"reports/{name}"


def _manifest_paths(manifest: Mapping[str, Any]) -> list[str]:
    result: list[str] = []
    runtime = manifest.get("runtime")
    if isinstance(runtime, dict):
        result.extend(v for v in runtime.values() if isinstance(v, str) and v)
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for values in artifacts.values():
            if isinstance(values, list):
                result.extend(v for v in values if isinstance(v, str) and v)
    screenshots = manifest.get("screenshots")
    if isinstance(screenshots, list):
        for row in screenshots:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                result.append(row["path"])
    return result


def _category(path: str) -> str:
    first = path.split("/", 1)[0]
    return first if first in {"reports", "screenshots", "diagnostics", "package", "runtime", "html"} else "other"


def _footprint(
    root: Path,
    *,
    predicted_summary_bytes: int = 0,
    summary_relative: str = "reports/final-run-summary.json",
    manifest_relative: str = "artifact-manifest.json",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    safe_relative_path(summary_relative, "summary footprint path")
    safe_relative_path(manifest_relative, "manifest footprint path")
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        safe_relative_path(relative)
        if relative == summary_relative:
            continue
        rows.append({"path": relative, "bytes": path.stat().st_size})
    if predicted_summary_bytes:
        rows.append({"path": summary_relative, "bytes": predicted_summary_bytes})
    rows.sort(key=lambda row: row["path"])
    categories: dict[str, dict[str, int]] = {
        name: {"fileCount": 0, "bytes": 0}
        for name in ("reports", "screenshots", "diagnostics", "package", "runtime", "html", "other")
    }
    for row in rows:
        bucket = categories[_category(row["path"])]
        bucket["fileCount"] += 1
        bucket["bytes"] += int(row["bytes"])
    manifest_path = root / PurePosixPath(manifest_relative)
    return {
        "measurementBoundary": "pre-upload",
        "fileCount": len(rows),
        "totalUncompressedBytes": sum(int(row["bytes"]) for row in rows),
        "categories": categories,
        "largestFiles": sorted(rows, key=lambda row: (-int(row["bytes"]), row["path"]))[:MAX_LARGEST_FILES],
        "screenshotCount": categories["screenshots"]["fileCount"],
        "screenshotBytes": categories["screenshots"]["bytes"],
        "reportsCount": categories["reports"]["fileCount"],
        "reportsBytes": categories["reports"]["bytes"],
        "diagnosticsCount": categories["diagnostics"]["fileCount"],
        "diagnosticsBytes": categories["diagnostics"]["bytes"],
        "packageCount": categories["package"]["fileCount"],
        "packageBytes": categories["package"]["bytes"],
        "runtimeCount": categories["runtime"]["fileCount"],
        "runtimeBytes": categories["runtime"]["bytes"],
        "manifestBytes": manifest_path.stat().st_size if manifest_path.is_file() else None,
        "manifestDigest": file_digest(manifest_path) if manifest_path.is_file() else None,
    }


def _terminal_event(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    terminals = [
        row for row in events
        if row.get("eventKind") == "run" and row.get("status") in {"pass", "fail", "cancel"}
    ]
    if len(terminals) > 1:
        raise FinalSummaryError("run-events contains more than one terminal run event")
    return terminals[0] if terminals else None


def _last_context(events: Sequence[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    phase = None
    item = None
    for row in events:
        if row.get("eventKind") == "phase" and row.get("status") in {"start", "pass", "fail", "cancel"}:
            phase = row.get("phaseId") if isinstance(row.get("phaseId"), str) else phase
        if row.get("eventKind") == "message" and row.get("status") == "info":
            message = row.get("message")
            if isinstance(message, str) and message.startswith("item="):
                fields = dict(
                    token.split("=", 1)
                    for token in message.split()
                    if "=" in token
                )
                event = fields.get("item")
                candidate = fields.get("id")
                if event == "start" and candidate:
                    item = candidate
                elif event == "fail" and candidate:
                    item = candidate
                elif event == "pass" and candidate == item:
                    item = None
    return phase, item


def _workload_digest(report: Mapping[str, Any]) -> str | None:
    packages = report.get("packages")
    if not isinstance(packages, list) or not packages:
        return None
    projection = {
        "schemaVersion": report.get("schemaVersion"),
        "manifestPath": report.get("manifestPath"),
        "packageCount": report.get("packageCount"),
        "anchorCount": report.get("anchorCount"),
        "syntheticFallback": report.get("syntheticFallback"),
        "packages": sorted(
            [
                {
                    "id": row.get("id"), "path": row.get("path"),
                    "sizeBytes": row.get("sizeBytes"), "sha256": row.get("sha256"),
                }
                for row in packages if isinstance(row, dict)
            ],
            key=lambda row: (str(row.get("id")), str(row.get("path"))),
        ),
    }
    return hash_object(projection)



__all__ = [name for name in globals() if not name.startswith("__")]
