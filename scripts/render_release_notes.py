from __future__ import annotations

import argparse
from pathlib import Path

from release_common import ReleaseError, release_notes, sha256_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Render current-version GitHub Release notes.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rendered = release_notes(args.version)
    except (ReleaseError, OSError) as exc:
        print(f"Release notes rendering failed: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Rendered {args.output} (sha256={sha256_text(rendered)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
