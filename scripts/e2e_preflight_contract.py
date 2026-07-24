from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping, Sequence, Callable

SCHEMA_VERSION = 1
PRODUCER = "docker-e2e"
ALLOWED_CONTEXTS = {"github-actions", "local"}
CHECK_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$")
UNSAFE_RE = re.compile(r"(?i)(?:token=|authorization\s*:|github_pat_|gh[pousr]_|sk-|[A-Z]:[\\/]|/(?:home|users|mnt|tmp|var|root)(?:/|\b)|[\x00-\x1f\x7f])")
MAX_SUMMARY_BYTES = 240
MAX_DOCUMENT_BYTES = 32 * 1024
STATIC_CHECK_IDS = (
    "inputs.mode-scope", "inputs.workers", "inputs.restart",
    "package.source-exclusivity", "repository.required-files",
    "filesystem.artifact-root", "environment-lock.syntax",
    "environment-lock.consistency", "environment-lock.exact-reference",
    "compose.files",
)
RUNTIME_CHECK_IDS = (
    "package.staged-artifact", "docker-cli.available", "compose-cli.available",
    "docker-daemon.reachable", "docker-daemon.platform",
    "compose.resolved-model", "compose.expected-service",
    "compose.image-source", "compose.safe-mounts", "compose.no-external-ports",
)
ALL_CHECK_IDS = STATIC_CHECK_IDS + RUNTIME_CHECK_IDS
REQUIRED_FILES = (
    "scripts/e2e_preflight.py", "scripts/e2e_preflight_contract.py",
    "scripts/e2e_preflight_checks.py", "scripts/run_anki_e2e_docker.ps1",
    "scripts/run_full_check.ps1", "docker/anki-e2e/docker-compose.yml",
    "docker/anki-e2e/docker-compose.ghcr.yml",
    "docker/anki-e2e/environment-image-spec.json",
    "docker/anki-e2e/environment-image-lock.json", "docker/anki-e2e/run-e2e.sh",
    "docker/anki-e2e/run-e2e-failure-wrapper.sh",
    "docker/anki-e2e/cancellation_protocol.py",
)
MODES = {"standard", "strict-apkg", "perf100"}
SCOPES = {"full", "global", "stats", "decks", "activity", "cards", "settings", "notifications"}
PACKAGE_SOURCES = {"source-build", "fast-ci-artifact", "release-artifact"}

class PreflightError(ValueError):
    pass

@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], CommandResult]

def safe_summary(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreflightError("check summary must be a non-empty trimmed string")
    if len(value.encode()) > MAX_SUMMARY_BYTES or UNSAFE_RE.search(value) or value.startswith("::"):
        raise PreflightError("check summary contains unsafe or unbounded data")
    return value

def non_negative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PreflightError(f"{label} must be a non-negative integer")
    return value

def validate_report(report: dict[str, object]) -> dict[str, object]:
    fields = ("schemaVersion", "status", "producer", "executionContext", "startedAtUtc", "finishedAtUtc", "durationMs", "checks", "failedCheckId")
    if not isinstance(report, dict) or tuple(report) != fields:
        raise PreflightError("preflight report field order is invalid")
    if report["schemaVersion"] != SCHEMA_VERSION or report["producer"] != PRODUCER:
        raise PreflightError("preflight identity is invalid")
    if report["status"] not in {"PASS", "FAIL"} or report["executionContext"] not in ALLOWED_CONTEXTS:
        raise PreflightError("preflight status or context is invalid")
    stamp = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
    if not all(isinstance(report[k], str) and stamp.fullmatch(report[k]) for k in ("startedAtUtc", "finishedAtUtc")):
        raise PreflightError("preflight timestamps are invalid")
    non_negative(report["durationMs"], "durationMs")
    checks = report["checks"]
    if not isinstance(checks, list) or not checks:
        raise PreflightError("preflight checks must be non-empty")
    ids: list[str] = []; failed: list[str] = []; normalized: list[dict[str, object]] = []
    for check in checks:
        if not isinstance(check, dict) or tuple(check) != ("id", "status", "durationMs", "summary"):
            raise PreflightError("preflight check shape is invalid")
        check_id = check["id"]
        if not isinstance(check_id, str) or not CHECK_ID_RE.fullmatch(check_id) or check_id not in ALL_CHECK_IDS or check_id in ids:
            raise PreflightError("preflight check id is invalid")
        ids.append(check_id); status = check["status"]
        if status not in {"PASS", "FAIL"}: raise PreflightError("preflight check status is invalid")
        if status == "FAIL": failed.append(check_id)
        normalized.append({"id": check_id, "status": status, "durationMs": non_negative(check["durationMs"], "check durationMs"), "summary": safe_summary(check["summary"])})
    if ids != list(ALL_CHECK_IDS[:len(ids)]): raise PreflightError("preflight checks are not deterministic")
    failed_id = report["failedCheckId"]
    if report["status"] == "PASS":
        if failed or failed_id is not None or ids not in (list(STATIC_CHECK_IDS), list(ALL_CHECK_IDS)): raise PreflightError("PASS report is inconsistent")
    elif len(failed) != 1 or failed_id != failed[0] or ids[-1] != failed_id:
        raise PreflightError("FAIL report must stop at the first failed check")
    normalized_report = {**report, "checks": normalized}
    if len((json.dumps(normalized_report, ensure_ascii=False, separators=(",", ":")) + "\n").encode()) > MAX_DOCUMENT_BYTES:
        raise PreflightError("preflight report is too large")
    return normalized_report

def serialize_report(report: dict[str, object]) -> str:
    return json.dumps(validate_report(report), ensure_ascii=False, separators=(",", ":")) + "\n"

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent); tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally: tmp.unlink(missing_ok=True)

def load_report(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or not raw.endswith(b"\n"): raise PreflightError("preflight report encoding is invalid")
    try: report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise PreflightError("preflight report is not UTF-8 JSON") from exc
    normalized = validate_report(report)
    if serialize_report(normalized).encode() != raw: raise PreflightError("preflight report serialization is not deterministic")
    return normalized
