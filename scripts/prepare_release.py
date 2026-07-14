from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from release_common import (
    CHANGELOG_FILE,
    MANIFEST_FILE,
    ReleaseError,
    SemVer,
    ensure_new_tag,
    normalize_markdown,
    parse_changelog,
    read_version,
    validate_manifest_release_date,
    write_version,
)


def prepared_state(version: str) -> None:
    if read_version() != version:
        raise ReleaseError(f"Canonical version is not {version}")
    sections = parse_changelog()
    if not sections.get(version) or not sections[version].body:
        raise ReleaseError(f"Missing non-empty changelog section for {version}")
    validate_manifest_release_date(version)


def prepare(version: str, release_date: str, mod_timestamp: int, *, dry_run: bool) -> list[str]:
    target = SemVer.parse(version)
    current_text = read_version()
    current = SemVer.parse(current_text)
    if not current < target:
        raise ReleaseError(f"New version {version} must be greater than canonical version {current_text}")
    ensure_new_tag(version)
    changelog_text = CHANGELOG_FILE.read_text(encoding="utf-8-sig")
    sections = parse_changelog(changelog_text)
    if version in sections:
        raise ReleaseError(f"Changelog already contains released version {version}")
    unreleased = sections["Unreleased"].body.strip()
    if not unreleased:
        raise ReleaseError("[Unreleased] is empty; add user-facing release notes before preparation")
    marker = "## [Unreleased]"
    start = changelog_text.index(marker)
    next_heading = changelog_text.find("\n## [", start + len(marker))
    if next_heading < 0:
        next_heading = len(changelog_text)
    replacement = f"{marker}\n\n## [{version}] - {release_date}\n\n{unreleased}\n"
    new_changelog = normalize_markdown(changelog_text[:start] + replacement + changelog_text[next_heading:])
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8-sig"))
    manifest["mod"] = mod_timestamp
    changed = ["anki_study_report/version.py", "anki_study_report/manifest.json", "CHANGELOG.md"]
    if not dry_run:
        write_version(version)
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        CHANGELOG_FILE.write_text(new_changelog, encoding="utf-8", newline="\n")
        prepared_state(version)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare canonical release metadata without committing.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--date")
    parser.add_argument("--mod-timestamp", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    release_date = args.date or now.date().isoformat()
    try:
        datetime.strptime(release_date, "%Y-%m-%d")
        mod_timestamp = args.mod_timestamp if args.mod_timestamp is not None else int(now.timestamp())
        if datetime.fromtimestamp(mod_timestamp, timezone.utc).date().isoformat() != release_date:
            raise ReleaseError("mod timestamp UTC date must match the release date")
        if args.check:
            prepared_state(args.version)
            ensure_new_tag(args.version)
            print(f"Release v{args.version} is prepared and untagged.")
        else:
            changed = prepare(args.version, release_date, mod_timestamp, dry_run=args.dry_run)
            verb = "Would update" if args.dry_run else "Updated"
            print(f"{verb}: {', '.join(changed)}")
        return 0
    except (ReleaseError, OSError, json.JSONDecodeError) as exc:
        print(f"Release preparation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
