from __future__ import annotations

import argparse
from pathlib import Path

from release_common import ReleaseError, render_ankiweb_description, sha256_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the exact AnkiWeb release description.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hash-output", type=Path)
    args = parser.parse_args()
    try:
        rendered = render_ankiweb_description(args.version)
    except (ReleaseError, OSError) as exc:
        print(f"AnkiWeb description rendering failed: {exc}")
        return 1
    digest = sha256_text(rendered)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if args.hash_output:
        args.hash_output.parent.mkdir(parents=True, exist_ok=True)
        args.hash_output.write_text(digest + "\n", encoding="utf-8", newline="\n")
    print(f"Rendered {args.output} (sha256={digest}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
