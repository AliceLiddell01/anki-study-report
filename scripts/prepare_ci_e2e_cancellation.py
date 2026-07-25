#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil

from non_release_build_identity import CANONICAL_FILENAME, load_document

ALLOWED = (
    "reports/cancellation-summary.json",
    "reports/preflight-report.json",
    f"reports/{CANONICAL_FILENAME}",
    "reports/run-events.jsonl",
    "diagnostics/cancellation-host.log",
)
MAX_TEXT_BYTES = 256 * 1024
TOKEN_RE = re.compile(
    r"(?i)(?:[?&](?:access_)?token=|authorization\s*:\s*bearer|"
    r"github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|sk-[a-z0-9_-]{20,})"
)
PRIVATE_RE = re.compile(r"(?i)(?:[A-Z]:[\\/]|/(?:home|users|mnt|tmp|var|root)(?:/|\b))")


class MinimalCancellationArtifactError(ValueError):
    pass


def _safe_text(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) > MAX_TEXT_BYTES:
        raise MinimalCancellationArtifactError(f"cancelled evidence exceeds the bounded size: {path.name}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MinimalCancellationArtifactError(f"cancelled evidence is not UTF-8 text: {path.name}") from exc
    if TOKEN_RE.search(text) or PRIVATE_RE.search(text):
        raise MinimalCancellationArtifactError(f"cancelled evidence contains private or secret-like data: {path.name}")
    return raw


def prepare(source: Path, output: Path) -> list[str]:
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    copied: list[str] = []
    for relative in ALLOWED:
        candidate = source / PurePosixPath(relative)
        if not candidate.is_file():
            continue
        if candidate.name == CANONICAL_FILENAME:
            load_document(candidate)
        raw = _safe_text(candidate)
        destination = output / PurePosixPath(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        if candidate.name == CANONICAL_FILENAME:
            load_document(destination)
        copied.append(relative)
    required = "reports/cancellation-summary.json"
    if required not in copied:
        raise MinimalCancellationArtifactError("canonical cancellation-summary.json is unavailable")
    manifest = {
        "schemaVersion": 1,
        "policy": "best-effort-minimal",
        "status": "partial",
        "files": copied,
    }
    (output / "cancellation-artifact.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare bounded public cancellation evidence")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        copied = prepare(args.source, args.output)
        print(f"[CANCEL-ARTIFACT] files={len(copied)}", flush=True)
        return 0
    except (MinimalCancellationArtifactError, OSError, ValueError) as exc:
        parser.exit(2, f"cancelled artifact error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
