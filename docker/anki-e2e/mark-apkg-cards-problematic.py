#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply generic study-state scenarios to imported real cards.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()
    command = [
        sys.executable,
        "/e2e/bin/apply-real-deck-scenarios.py",
        "--profile-dir",
        str(args.profile_dir),
        "--artifacts-dir",
        str(args.artifacts_dir),
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
