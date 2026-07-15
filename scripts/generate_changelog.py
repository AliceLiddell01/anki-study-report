from __future__ import annotations

import argparse

from changelog import ChangelogError, generate_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate localized changelog outputs.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changed = generate_outputs(check=args.check)
    except (ChangelogError, OSError) as exc:
        print(f"Changelog generation failed: {exc}")
        return 1
    if args.check:
        print("Generated changelog outputs are current.")
    elif changed:
        print("Generated: " + ", ".join(str(path) for path in changed))
    else:
        print("Generated changelog outputs were already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
