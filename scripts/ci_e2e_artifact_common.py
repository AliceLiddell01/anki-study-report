from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from typing import Iterable


SCHEMA_VERSION = 2
ALLOWED_MODES = {"standard", "strict-apkg", "perf100"}
ALLOWED_SCOPES = {"full", "global", "stats", "decks", "activity", "cards", "settings", "notifications"}
ALLOWED_PACKAGE_SOURCES = {"source-build", "fast-ci-artifact", "release-artifact"}
ALLOWED_TOP_LEVEL = {
    "artifact-manifest.json",
    "runtime",
    "diagnostics",
    "reports",
    "html",
    "package",
    "screenshots",
}
TEXT_SUFFIXES = {".json", ".jsonl", ".txt", ".log", ".md", ".html", ".htm", ".xml"}
SECRET_PATTERNS = (
    re.compile(r"ghp" + r"_[A-Za-z0-9]{20,}"),
    re.compile(r"github" + r"_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[ousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKI" + r"A[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN " + r"(?:OPENSSH |RSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)author" + r"ization:\s*bearer\s+\S+"),
)
TOKEN_QUERY = re.compile(
    r"(?:[?&]|&amp;)token=(?:<redacted-token>|\[REDACTED\]|[^&\s\"'<>]+)",
    re.IGNORECASE,
)
WINDOWS_PRIVATE_PATH = re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\\/\s\"'<>]+")
LINUX_PRIVATE_PATH = re.compile(r"/home/(?!e2e(?:/|$))[^/\s\"'<>]+")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRODUCT_PHASES = {
    "frontendDependencyInstall": "frontend dependency install",
    "frontendBuild": "frontend build",
    "addOnPackage": "add-on package",
    "exactPrebuiltValidationAndExtraction": "exact prebuilt add-on validation and extraction",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"Unsafe artifact path: {value}")
    return normalized


def manifest_paths(manifest: dict) -> list[str]:
    paths: list[str] = []
    for value in (manifest.get("runtime") or {}).values():
        if isinstance(value, str) and value:
            paths.append(value)
    for values in (manifest.get("artifacts") or {}).values():
        if isinstance(values, list):
            paths.extend(value for value in values if isinstance(value, str) and value)
    for entry in manifest.get("screenshots") or []:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    return paths


def validate_manifest(source: Path, manifest: dict) -> list[str]:
    paths = [safe_relative_path(value) for value in manifest_paths(manifest)]
    if len(paths) != len(set(paths)):
        raise ValueError("Artifact manifest contains duplicate paths")
    for relative in paths:
        if not (source / relative).is_file():
            raise ValueError(f"Artifact manifest references a missing file: {relative}")
    return paths


def redact_text(text: str, *, known_tokens: Iterable[str], private_roots: Iterable[str]) -> str:
    redacted = TOKEN_QUERY.sub("", text)
    for token in known_tokens:
        if token:
            redacted = redacted.replace(token, "[REDACTED]")
    for root in private_roots:
        if not root:
            continue
        variants = {root, root.replace("\\", "/"), root.replace("/", "\\")}
        for variant in variants:
            redacted = redacted.replace(variant, "[WORKSPACE]")
    return redacted


def redact_json(value, *, known_tokens: Iterable[str], private_roots: Iterable[str]):
    if isinstance(value, str):
        return redact_text(value, known_tokens=known_tokens, private_roots=private_roots)
    if isinstance(value, list):
        return [redact_json(item, known_tokens=known_tokens, private_roots=private_roots) for item in value]
    if isinstance(value, dict):
        return {
            key: redact_json(item, known_tokens=known_tokens, private_roots=private_roots)
            for key, item in value.items()
        }
    return value


def assert_safe_text(text: str, relative_path: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Secret-like content remains in {relative_path}")
    if TOKEN_QUERY.search(text):
        raise ValueError(f"Token-bearing URL remains in {relative_path}")
    if WINDOWS_PRIVATE_PATH.search(text) or LINUX_PRIVATE_PATH.search(text):
        raise ValueError(f"Private absolute path remains in {relative_path}")


def read_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_version(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    output = (completed.stdout or completed.stderr or "").strip()
    return output if completed.returncode == 0 and output else "unavailable"


def _optional_positive(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    parsed = int(value)
    if parsed < 1:
        raise ValueError("Expected a positive integer")
    return parsed


def _optional_hash(value: str | None, pattern: re.Pattern[str], name: str) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if not pattern.fullmatch(normalized):
        raise ValueError(f"Invalid {name}")
    return normalized


def _phase_observations(payload: dict) -> dict:
    observations = {
        key: {"status": "absent", "durationMs": None, "notes": None}
        for key in PRODUCT_PHASES
    }
    phases = payload.get("phases") if isinstance(payload, dict) else []
    if not isinstance(phases, list):
        return observations
    by_name = {
        item.get("name"): item
        for item in phases
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    for key, phase_name in PRODUCT_PHASES.items():
        item = by_name.get(phase_name)
        if item:
            observations[key] = {
                "status": str(item.get("status") or "unknown"),
                "durationMs": item.get("durationMs") if isinstance(item.get("durationMs"), (int, float)) else None,
                "notes": item.get("notes") if isinstance(item.get("notes"), str) else None,
            }
    return observations


def read_readiness(source: Path) -> tuple[dict, list[str]]:
    readiness_path = source / "runtime" / "dashboard-ready.json"
    if not readiness_path.is_file():
        return {}, []
    try:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}, []
    tokens: list[str] = []
    if isinstance(readiness, dict):
        token = readiness.get("token")
        if isinstance(token, str) and token:
            tokens.append(token)
    return readiness if isinstance(readiness, dict) else {}, tokens


def copy_safe_artifacts(source: Path, destination: Path, private_roots: Iterable[str]) -> tuple[str, list[str]]:
    manifest_path = source / "artifact-manifest.json"
    if not manifest_path.is_file():
        return "missing", []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_paths = validate_manifest(source, manifest)
    readiness, known_tokens = read_readiness(source)
    copied: list[str] = []
    for relative in relative_paths:
        source_path = source / relative
        output_relative = relative
        if relative == "runtime/dashboard-ready.json":
            output_relative = "runtime/dashboard-ready.redacted.json"
            safe = {
                key: redact_json(value, known_tokens=known_tokens, private_roots=private_roots)
                for key, value in readiness.items()
                if key not in {"token", "baseUrl", "url"}
            }
            safe["redacted"] = True
            target = destination / output_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif source_path.suffix.lower() in TEXT_SUFFIXES:
            text = source_path.read_text(encoding="utf-8", errors="replace")
            text = redact_text(text, known_tokens=known_tokens, private_roots=private_roots)
            assert_safe_text(text, output_relative)
            target = destination / output_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        else:
            target = destination / output_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        copied.append(f"artifacts/{output_relative}")

    exported_manifest = redact_json(manifest, known_tokens=known_tokens, private_roots=private_roots)
    runtime = exported_manifest.setdefault("runtime", {})
    if runtime.get("dashboardReady") == "runtime/dashboard-ready.json":
        runtime["dashboardReady"] = "runtime/dashboard-ready.redacted.json"
    write_json_file(destination / "artifact-manifest.json", exported_manifest)
    copied.append("artifacts/artifact-manifest.json")
    return str(manifest.get("status") or "unknown"), copied
