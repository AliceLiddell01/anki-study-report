#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".log", ".html", ".trace", ".network", ".stacks"}
KEEP_NAMES = {
    "failure-summary.json",
    "failure-summary.md",
    "exact-browser.json",
    "exact-api.json",
    "exact-scenario.json",
    "page-console-summary.json",
    "request-ledger.json",
    "geometry-metrics.json",
    "artifact-manifest.json",
    "run-events.jsonl",
    "container.log",
}
KEEP_PREFIXES = (
    "diagnostics/",
    "reports/",
    "screenshots/failures/",
    "screenshots/cards/exact-av-media/",
)


def safe_relative(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts or any(part in {"", "."} for part in path.parts):
        raise ValueError(f"Unsafe relative path: {value}")
    return path.as_posix()


def redact_text(value: str, token: str, home: str) -> str:
    if token:
        value = value.replace(token, "[REDACTED]")
    value = re.sub(r"([?&](?:access_)?token=)[^&\s\"']+", r"\1[REDACTED]", value, flags=re.I)
    value = re.sub(r"https?://127\.0\.0\.1:\d+/\S*", "[LOOPBACK_URL]", value, flags=re.I)
    value = re.sub(r"(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/])\S*", "[PRIVATE_PATH]", value)
    value = re.sub(r"/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:/\S*)?", "[PRIVATE_PATH]", value)
    if home:
        value = value.replace(home, "[PRIVATE_PATH]")
    return value


def sanitize_bytes(data: bytes, suffix: str, token: str, home: str) -> bytes:
    token_bytes = token.encode("utf-8") if token else b""
    if suffix in TEXT_SUFFIXES:
        return redact_text(data.decode("utf-8", errors="replace"), token, home).encode("utf-8")
    if token_bytes and token_bytes in data:
        replacement = b"[REDACTED]"
        if len(replacement) < len(token_bytes):
            replacement += b"_" * (len(token_bytes) - len(replacement))
        data = data.replace(token_bytes, replacement[: len(token_bytes)])
    return data


def sanitize_nested_zip(source: Path, destination: Path, token: str, home: str) -> None:
    with zipfile.ZipFile(source, "r") as incoming, zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as outgoing:
        bad = incoming.testzip()
        if bad is not None:
            raise RuntimeError(f"Nested ZIP CRC failure: {bad}")
        for member in incoming.infolist():
            name = safe_relative(member.filename)
            if member.is_dir():
                continue
            data = incoming.read(member)
            outgoing.writestr(name, sanitize_bytes(data, Path(name).suffix.lower(), token, home))


def include_path(relative: str) -> bool:
    return Path(relative).name in KEEP_NAMES or any(relative.startswith(prefix) for prefix in KEEP_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one public-safe Cards exact E2E failure bundle.")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--process-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--home", default="")
    args = parser.parse_args()

    root = args.artifacts.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cards-exact-failure-") as temp:
        stage = Path(temp) / "cards-exact-av-media-failure"
        stage.mkdir()
        rows = []

        candidates = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
        if args.process_log.is_file():
            candidates.append(args.process_log)

        for source in sorted(set(candidates)):
            if source == args.process_log:
                relative = "diagnostics/process-logs/container.log"
            else:
                relative = source.relative_to(root).as_posix()
                if not include_path(relative):
                    continue
            safe_relative(relative)
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".zip" and "browser-trace" in relative:
                sanitize_nested_zip(source, destination, args.token, args.home)
            else:
                data = sanitize_bytes(source.read_bytes(), source.suffix.lower(), args.token, args.home)
                destination.write_bytes(data)
            rows.append({"path": relative, "sizeBytes": destination.stat().st_size})

        (stage / "README.md").write_text(
            "# Cards exact AV/media failure diagnostics\n\n"
            "Public-safe diagnostic subset. Raw runtime state remains only in the local artifact directory.\n",
            encoding="utf-8",
        )
        (stage / "diagnostics/inventory.json").parent.mkdir(parents=True, exist_ok=True)
        (stage / "diagnostics/inventory.json").write_text(
            json.dumps({"schemaVersion": 1, "status": "FAIL", "files": rows}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if args.output.exists():
            raise RuntimeError(f"Failure bundle already exists: {args.output}")
        with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        with zipfile.ZipFile(args.output, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"Failure bundle CRC failure: {bad}")

    print(f"[cards-exact] failure diagnostics: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
