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
WINDOWS_PRIVATE_PATH = re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\s\"'<>]+")
LINUX_PRIVATE_PATH = re.compile(
    r"(?:(?<![A-Za-z0-9_./-])|(?<=file://))/home/(?!e2e(?:/|$))[^\s\"'<>]+"
)
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
    redacted = WINDOWS_PRIVATE_PATH.sub("[PRIVATE_PATH]", redacted)
    redacted = LINUX_PRIVATE_PATH.sub("[PRIVATE_PATH]", redacted)
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


def read_readiness(source: Path) -> tuple[dict | None, list[str]]:
    path = source / "runtime" / "dashboard-ready.json"
    if not path.is_file():
        return None, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    tokens = [str(payload.get("token") or "")]
    payload.pop("token", None)
    for key, value in list(payload.items()):
        if isinstance(value, str):
            payload[key] = TOKEN_QUERY.sub("", value)
    payload["redacted"] = True
    return payload, tokens


def copy_safe_artifacts(source: Path, destination: Path, private_roots: Iterable[str]) -> tuple[str, list[str]]:
    manifest_status = "missing"
    manifest: dict | None = None
    manifest_path = source / "artifact-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_manifest(source, manifest)
        manifest_status = str(manifest.get("status") or "unknown")

    readiness, known_tokens = read_readiness(source)
    copied: list[str] = []
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            top = relative.split("/", 1)[0]
            if top not in ALLOWED_TOP_LEVEL or relative == "runtime/dashboard-ready.json":
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in TEXT_SUFFIXES or path.name == "artifact-manifest.json":
                text = path.read_text(encoding="utf-8")
                if path.suffix.lower() == ".json" or relative == "artifact-manifest.json":
                    data = json.loads(text)
                    if relative == "artifact-manifest.json":
                        runtime = data.get("runtime") or {}
                        if runtime.get("dashboardReady"):
                            runtime["dashboardReady"] = "runtime/dashboard-ready.redacted.json"
                    data = redact_json(data, known_tokens=known_tokens, private_roots=private_roots)
                    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                else:
                    text = redact_text(text, known_tokens=known_tokens, private_roots=private_roots)
                assert_safe_text(text, relative)
                target.write_text(text, encoding="utf-8")
            else:
                shutil.copyfile(path, target)
            copied.append(f"artifacts/{relative}")

    if readiness is not None:
        relative = "runtime/dashboard-ready.redacted.json"
        text = json.dumps(readiness, ensure_ascii=False, indent=2) + "\n"
        assert_safe_text(text, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        copied.append(f"artifacts/{relative}")
    return manifest_status, copied


def command_version(arguments: list[str]) -> str:
    try:
        result = subprocess.run(arguments, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return (result.stdout or result.stderr).strip().splitlines()[0]


def read_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json_file(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _phase_observations(phase_payload: dict) -> dict[str, dict]:
    rows = phase_payload.get("phases") if isinstance(phase_payload, dict) else []
    rows = rows if isinstance(rows, list) else []
    by_name = {
        item.get("name"): item
        for item in rows
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    result: dict[str, dict] = {}
    for key, name in PRODUCT_PHASES.items():
        row = by_name.get(name)
        if row is None:
            result[key] = {"status": "absent", "durationMs": None, "notes": None}
        else:
            duration = row.get("durationMs")
            result[key] = {
                "status": row.get("status") or "unknown",
                "durationMs": duration if isinstance(duration, (int, float)) else None,
                "notes": row.get("notes") or None,
            }
    return result


def _optional_positive(value: str) -> int | None:
    if not value:
        return None
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("source-fast-ci-run-id must be a positive integer")
    return parsed


def _optional_hash(value: str, pattern: re.Pattern[str], label: str) -> str | None:
    if not value:
        return None
    if not pattern.fullmatch(value):
        raise ValueError(f"{label} has an invalid format")
    return value
