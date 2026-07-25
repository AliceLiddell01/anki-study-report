#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


REAL_DECK_FIXTURE_PATH = "docker/anki-e2e/fixtures/real-decks"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import all committed real working deck fixtures.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--require", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    workspace = Path(os.environ.get("WORKSPACE") or "/workspace")
    fixture_dir = workspace / REAL_DECK_FIXTURE_PATH
    manifest = fixture_dir / "manifest.json"
    command = [
        sys.executable,
        "/e2e/bin/prepare-real-decks.py",
        "--profile-dir",
        str(args.profile_dir),
        "--artifacts-dir",
        str(args.artifacts_dir),
        "--fixture-dir",
        str(fixture_dir),
        "--manifest",
        str(manifest),
    ]
    print("[real-decks] mandatory multi-package import", flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
