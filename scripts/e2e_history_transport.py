#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

PREFIX = "ci-e2e-history-"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class HistoryTransportError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryTransportError(f"invalid JSON input: {path}") from exc
    if not isinstance(value, dict):
        raise HistoryTransportError("JSON input must be an object")
    return value


def _positive(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise HistoryTransportError(f"{label} must be positive")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HistoryTransportError(f"{label} must be positive") from exc
    if parsed <= 0:
        raise HistoryTransportError(f"{label} must be positive")
    return parsed


def _utc(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise HistoryTransportError(f"{label} must be a UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise HistoryTransportError(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def select_previous_artifact(
    payload: dict[str, Any], *, repository_id: int, current_run_id: int
) -> dict[str, Any]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise HistoryTransportError("artifact listing has no artifacts array")
    candidates: list[dict[str, Any]] = []
    rejected: dict[str, int] = {}
    for row in artifacts:
        if not isinstance(row, dict):
            rejected["invalid-row"] = rejected.get("invalid-row", 0) + 1
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.startswith(PREFIX):
            continue
        if row.get("expired") is True:
            rejected["expired"] = rejected.get("expired", 0) + 1
            continue
        workflow = row.get("workflow_run")
        if not isinstance(workflow, dict):
            rejected["missing-workflow-run"] = rejected.get("missing-workflow-run", 0) + 1
            continue
        if workflow.get("repository_id") != repository_id:
            rejected["repository-mismatch"] = rejected.get("repository-mismatch", 0) + 1
            continue
        run_id = _positive(workflow.get("id"), "workflow_run.id")
        if run_id == current_run_id:
            continue
        artifact_id = _positive(row.get("id"), "artifact.id")
        created = _utc(row.get("created_at"), "artifact.created_at")
        candidates.append({
            "artifactId": artifact_id,
            "name": name,
            "runId": run_id,
            "createdAtUtc": created,
            "expiresAtUtc": _utc(row.get("expires_at"), "artifact.expires_at") if row.get("expires_at") else None,
            "sizeBytes": _positive(row.get("size_in_bytes"), "artifact.size_in_bytes"),
            "digest": row.get("digest"),
        })
    candidates.sort(key=lambda row: (row["createdAtUtc"], row["artifactId"]), reverse=True)
    chosen = candidates[0] if candidates else None
    return {
        "schemaVersion": 1,
        "status": "selected" if chosen else "missing",
        "reason": None if chosen else "no non-expired compatible history artifact was found",
        "selected": chosen,
        "rejected": dict(sorted(rejected.items())),
    }


def artifact_metadata(
    payload: dict[str, Any], *, expected_id: int, repository_id: int, current_run_id: int
) -> dict[str, Any]:
    artifact_id = _positive(payload.get("id"), "artifact.id")
    if artifact_id != expected_id:
        raise HistoryTransportError("artifact ID mismatch")
    workflow = payload.get("workflow_run")
    if not isinstance(workflow, dict):
        raise HistoryTransportError("artifact workflow_run is unavailable")
    if workflow.get("repository_id") != repository_id:
        raise HistoryTransportError("artifact repository mismatch")
    if _positive(workflow.get("id"), "workflow_run.id") != current_run_id:
        raise HistoryTransportError("artifact run mismatch")
    digest = payload.get("digest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise HistoryTransportError("artifact digest is invalid")
    if payload.get("expired") is True:
        raise HistoryTransportError("new artifact is unexpectedly expired")
    return {
        "schemaVersion": 1,
        "id": artifact_id,
        "name": payload.get("name"),
        "digest": digest,
        "sizeBytes": _positive(payload.get("size_in_bytes"), "artifact.size_in_bytes"),
        "createdAtUtc": _utc(payload.get("created_at"), "artifact.created_at"),
        "expiresAtUtc": _utc(payload.get("expires_at"), "artifact.expires_at"),
        "runId": current_run_id,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_github_output(path: Path | None, values: dict[str, Any]) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={'' if value is None else value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub artifact transport metadata for E2E history")
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select")
    select.add_argument("--input", type=Path, required=True)
    select.add_argument("--repository-id", type=int, required=True)
    select.add_argument("--current-run-id", type=int, required=True)
    select.add_argument("--output", type=Path, required=True)
    select.add_argument("--github-output", type=Path)

    metadata = sub.add_parser("metadata")
    metadata.add_argument("--input", type=Path, required=True)
    metadata.add_argument("--expected-id", type=int, required=True)
    metadata.add_argument("--repository-id", type=int, required=True)
    metadata.add_argument("--current-run-id", type=int, required=True)
    metadata.add_argument("--output", type=Path, required=True)
    metadata.add_argument("--github-output", type=Path)

    args = parser.parse_args()
    payload = read_json(args.input)
    if args.command == "select":
        result = select_previous_artifact(
            payload, repository_id=args.repository_id, current_run_id=args.current_run_id
        )
        write_json(args.output, result)
        selected = result["selected"] or {}
        write_github_output(args.github_output, {
            "status": result["status"],
            "artifact_id": selected.get("artifactId"),
            "source_run_id": selected.get("runId"),
        })
    else:
        result = artifact_metadata(
            payload, expected_id=args.expected_id,
            repository_id=args.repository_id, current_run_id=args.current_run_id,
        )
        write_json(args.output, result)
        write_github_output(args.github_output, {
            "artifact_id": result["id"],
            "artifact_digest": result["digest"],
            "artifact_size_bytes": result["sizeBytes"],
            "artifact_expires_at_utc": result["expiresAtUtc"],
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
