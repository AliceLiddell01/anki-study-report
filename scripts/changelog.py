"""Validate and deterministically render the structured localized changelog."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_CHANGELOG_FILE = ROOT / "release" / "changelog.json"
MARKDOWN_CHANGELOG_FILE = ROOT / "CHANGELOG.md"
ADDON_CHANGELOG_FILE = ROOT / "anki_study_report" / "changelog.json"
FRONTEND_CHANGELOG_FILE = ROOT / "web-dashboard" / "src" / "data" / "changelog.generated.ts"
CANONICAL_VERSION_FILE = ROOT / "anki_study_report" / "version.py"
MAX_DOCUMENT_BYTES = 2_000_000
SECTION_TITLES = {
    "added": "Added",
    "changed": "Changed",
    "fixed": "Fixed",
    "safety": "Safety",
    "removed": "Removed",
}
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ChangelogError(ValueError):
    pass


def load_changelog_document(path: Path = STRUCTURED_CHANGELOG_FILE) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangelogError(f"Could not read structured changelog: {exc}") from exc
    return validate_changelog_document(raw)


def validate_changelog_document(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schemaVersion", "unreleased", "releases"}:
        raise ChangelogError("Structured changelog root keys mismatch")
    if len(json.dumps(raw, ensure_ascii=False).encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ChangelogError("Structured changelog exceeds the size limit")
    if raw.get("schemaVersion") != 1:
        raise ChangelogError("Unsupported structured changelog schema")
    unreleased = raw.get("unreleased")
    if not isinstance(unreleased, dict) or set(unreleased) != {"sections"}:
        raise ChangelogError("Invalid unreleased changelog object")
    _validate_sections(unreleased.get("sections"), seen_ids=set(), label="unreleased")
    releases = raw.get("releases")
    if not isinstance(releases, list) or not releases or len(releases) > 100:
        raise ChangelogError("Structured changelog requires bounded releases")
    seen_versions: set[str] = set()
    seen_ids = {
        str(item["id"])
        for section in unreleased["sections"]
        for item in section["items"]
    }
    previous: tuple[Any, ...] | None = None
    for release in releases:
        if not isinstance(release, dict) or set(release) != {"version", "date", "sections"}:
            raise ChangelogError("Invalid release object")
        version = str(release.get("version") or "")
        if not SEMVER_RE.fullmatch(version):
            raise ChangelogError(f"Invalid changelog SemVer: {version!r}")
        if version in seen_versions:
            raise ChangelogError(f"Duplicate changelog version: {version}")
        seen_versions.add(version)
        key = semver_key(version)
        if previous is not None and not key < previous:
            raise ChangelogError("Changelog releases must be newest-first")
        previous = key
        release_date = release.get("date")
        if not isinstance(release_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", release_date):
            raise ChangelogError(f"Invalid changelog date for {version}")
        try:
            date.fromisoformat(release_date)
        except ValueError as exc:
            raise ChangelogError(f"Invalid changelog date for {version}") from exc
        _validate_sections(release.get("sections"), seen_ids=seen_ids, label=version)
    return deepcopy(raw)


def _validate_sections(value: Any, *, seen_ids: set[str], label: str) -> None:
    if not isinstance(value, list) or len(value) > 10:
        raise ChangelogError(f"Invalid changelog sections for {label}")
    seen_types: set[str] = set()
    for section in value:
        if not isinstance(section, dict) or set(section) != {"type", "items"}:
            raise ChangelogError(f"Invalid changelog section for {label}")
        section_type = section.get("type")
        if section_type not in SECTION_TITLES or section_type in seen_types:
            raise ChangelogError(f"Invalid or duplicate changelog section type: {section_type}")
        seen_types.add(str(section_type))
        items = section.get("items")
        if not isinstance(items, list) or not items or len(items) > 100:
            raise ChangelogError(f"Invalid changelog items for {label}/{section_type}")
        for item in items:
            if not isinstance(item, dict) or set(item) != {"id", "text"}:
                raise ChangelogError("Invalid changelog item")
            item_id = str(item.get("id") or "")
            if not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,79}", item_id):
                raise ChangelogError(f"Invalid changelog item ID: {item_id!r}")
            if item_id in seen_ids:
                raise ChangelogError(f"Duplicate changelog item ID: {item_id}")
            seen_ids.add(item_id)
            text = item.get("text")
            if not isinstance(text, dict) or set(text) != {"ru", "en"}:
                raise ChangelogError(f"Locale parity is required for {item_id}")
            for locale, content in text.items():
                if not isinstance(content, str) or not content.strip() or len(content) > 1000:
                    raise ChangelogError(f"Invalid {locale} changelog text for {item_id}")
                if "\n" in content or re.search(r"<[^>]+>|\[[^\]]+\]\([^\)]+\)", content):
                    raise ChangelogError(f"HTML or executable Markdown is forbidden in {item_id}")


def render_release_body(release: dict[str, Any], *, locale: str = "en") -> str:
    if locale not in {"ru", "en"}:
        raise ChangelogError(f"Unsupported changelog locale: {locale}")
    lines: list[str] = []
    for section in release.get("sections", []):
        title = SECTION_TITLES[section["type"]]
        lines.extend([f"### {title}", ""])
        for item in section["items"]:
            lines.append(f"- {item['text'][locale].strip()}")
        lines.append("")
    return "\n".join(lines).strip() + ("\n" if lines else "")


def render_changelog_markdown(document: dict[str, Any]) -> str:
    lines = [
        "# Changelog",
        "",
        "All notable user-facing changes to Anki Study Report are documented here.",
        "",
        "## [Unreleased]",
        "",
    ]
    unreleased_body = render_release_body(document["unreleased"], locale="en")
    if unreleased_body:
        lines.extend([unreleased_body.rstrip(), ""])
    for release in document["releases"]:
        lines.extend(
            [
                f"## [{release['version']}] - {release['date']}",
                "",
                render_release_body(release, locale="en").rstrip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_addon_json(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def render_frontend_typescript(document: dict[str, Any]) -> str:
    payload = json.dumps(document, ensure_ascii=False, indent=2)
    return (
        "// Generated by scripts/generate_changelog.py. Do not edit manually.\n"
        f"export const bundledChangelog = {payload} as const;\n\n"
        "export type BundledChangelog = typeof bundledChangelog;\n"
    )


def expected_outputs(document: dict[str, Any]) -> dict[Path, str]:
    return {
        MARKDOWN_CHANGELOG_FILE: render_changelog_markdown(document),
        ADDON_CHANGELOG_FILE: render_addon_json(document),
        FRONTEND_CHANGELOG_FILE: render_frontend_typescript(document),
    }


def generate_outputs(*, check: bool = False) -> list[Path]:
    document = load_changelog_document()
    version_match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
        CANONICAL_VERSION_FILE.read_text(encoding="utf-8-sig"),
        re.MULTILINE,
    )
    current_version = version_match.group(1) if version_match else None
    if current_version not in {release["version"] for release in document["releases"]}:
        raise ChangelogError("Current package version is missing from the structured changelog")
    changed: list[Path] = []
    for path, content in expected_outputs(document).items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        changed.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if check and changed:
        names = ", ".join(str(path.relative_to(ROOT)) for path in changed)
        raise ChangelogError(f"Generated changelog outputs are stale: {names}")
    return changed


def semver_key(value: str) -> tuple[Any, ...]:
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise ChangelogError(f"Invalid SemVer: {value!r}")
    prerelease = match.group(4)
    if prerelease is None:
        pre_key: tuple[Any, ...] = ((2, ""),)
    else:
        parts = tuple((0, int(part)) if part.isdigit() else (1, part) for part in prerelease.split("."))
        pre_key = ((1, ""),) + parts
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), pre_key
