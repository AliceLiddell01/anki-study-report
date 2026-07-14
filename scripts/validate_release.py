from __future__ import annotations

import argparse
import json
from pathlib import Path

from release_common import ReleaseError, read_version, validate_release


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a prepared Anki Study Report release.")
    parser.add_argument("--version")
    parser.add_argument("--channel", choices=("stable", "prerelease"), default="stable")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-remote-tag-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-existing-tag", action="store_true")
    args = parser.parse_args()
    version = args.version or read_version()
    try:
        report = validate_release(
            version,
            args.channel,
            artifact=args.artifact,
            check_remote_tag=not args.skip_remote_tag_check,
            allow_existing_tag=args.allow_existing_tag,
        )
    except (ReleaseError, OSError, json.JSONDecodeError) as exc:
        print(f"Release validation failed: {exc}")
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"Release validation passed for v{version} ({args.channel}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
