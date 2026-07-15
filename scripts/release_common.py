"""Shared deterministic release parsing, rendering, and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

try:
    from changelog import (
        STRUCTURED_CHANGELOG_FILE,
        load_changelog_document,
        render_changelog_markdown,
        render_release_body,
    )
except ModuleNotFoundError:
    _changelog_path = Path(__file__).resolve().with_name("changelog.py")
    _changelog_spec = importlib.util.spec_from_file_location("changelog", _changelog_path)
    if _changelog_spec is None or _changelog_spec.loader is None:
        raise RuntimeError("Could not load structured changelog helpers.")
    _changelog_module = importlib.util.module_from_spec(_changelog_spec)
    sys.modules.setdefault("changelog", _changelog_module)
    _changelog_spec.loader.exec_module(_changelog_module)
    STRUCTURED_CHANGELOG_FILE = _changelog_module.STRUCTURED_CHANGELOG_FILE
    load_changelog_document = _changelog_module.load_changelog_document
    render_changelog_markdown = _changelog_module.render_changelog_markdown
    render_release_body = _changelog_module.render_release_body


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "anki_study_report" / "version.py"
MANIFEST_FILE = ROOT / "anki_study_report" / "manifest.json"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
ANKIWEB_METADATA_FILE = ROOT / "release" / "ankiweb.yml"
ANKIWEB_DESCRIPTION_FILE = ROOT / "release" / "ankiweb-description.md"
APPROVED_ARTIFACT_NAME = "anki_study_report.ankiaddon"
MAX_PUBLIC_MARKDOWN_BYTES = 60_000

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
CHANGELOG_HEADING_RE = re.compile(
    r"^## \[(?P<version>Unreleased|[^\]]+)\](?: - (?P<date>\d{4}-\d{2}-\d{2}))?$",
    re.MULTILINE,
)
EXPECTED_METADATA_KEYS = {
    "schema_version",
    "addon_id",
    "title",
    "tags",
    "support_url",
    "expected_branch_label",
    "minimum_anki_version",
    "maximum_anki_version",
    "download_client_version",
    "repository_url",
    "releases_url",
    "donation_url",
}
PUBLIC_TEXT_GUARDS = (
    (re.compile(r"(?i)\b(?:TODO|TBD|CHANGEME|PLACEHOLDER)\b"), "placeholder"),
    (re.compile(r"(?i)(?:[?&]|&amp;)token=[^\s&]+"), "token-bearing URL"),
    (re.compile(r"(?i)\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_]{12,}"), "token-like value"),
    (re.compile(r"(?i)\b(?:password|passwd|secret)\s*[:=]\s*\S+"), "credential-like value"),
    (re.compile(r"(?i)(?:[A-Z]:[\\/](?:Users|Documents)[\\/]|/home/[^/\s]+/|/Users/[^/\s]+/)"), "private path"),
    (re.compile(r"(?i)\b(?:internal stage|stage\s+\d+(?:\.\d+)*)\b"), "internal stage reference"),
)


class ReleaseError(ValueError):
    """Raised for a release contract violation."""


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = SEMVER_RE.fullmatch(value)
        if not match:
            raise ReleaseError(f"Invalid SemVer: {value!r}")
        prerelease = tuple((match.group(4) or "").split(".")) if match.group(4) else ()
        build = tuple((match.group(5) or "").split(".")) if match.group(5) else ()
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease, build)

    def precedence_key(self) -> tuple[Any, ...]:
        if not self.prerelease:
            pre_key: tuple[Any, ...] = ((2, ""),)
        else:
            parts = tuple((0, int(item)) if item.isdigit() else (1, item) for item in self.prerelease)
            pre_key = ((1, ""),) + parts
        return self.major, self.minor, self.patch, pre_key

    def __lt__(self, other: "SemVer") -> bool:
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            if left.isdigit() and right.isdigit():
                return int(left) < int(right)
            if left.isdigit() != right.isdigit():
                return left.isdigit()
            return left < right
        return len(self.prerelease) < len(other.prerelease)


@dataclass(frozen=True)
class ChangelogSection:
    version: str
    release_date: str | None
    body: str


def normalize_markdown(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_markdown(text).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version(path: Path = VERSION_FILE) -> str:
    try:
        module = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (FileNotFoundError, SyntaxError, UnicodeDecodeError) as exc:
        raise ReleaseError(f"Could not read canonical version source: {exc}") from exc
    assignments = []
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            assignments.append(node.value)
    if len(assignments) != 1:
        raise ReleaseError("version.py must contain exactly one __version__ assignment")
    try:
        value = ast.literal_eval(assignments[0])
    except (ValueError, TypeError) as exc:
        raise ReleaseError("__version__ must be a pure string literal") from exc
    if not isinstance(value, str):
        raise ReleaseError("__version__ must be a string")
    SemVer.parse(value)
    return value


def write_version(version: str, path: Path = VERSION_FILE) -> None:
    SemVer.parse(version)
    path.write_text(
        '"""Canonical package version for Anki Study Report."""\n\n'
        f'__version__ = {json.dumps(version)}\n',
        encoding="utf-8",
    )


def parse_changelog(text: str | None = None, path: Path = CHANGELOG_FILE) -> dict[str, ChangelogSection]:
    if text is None and path == CHANGELOG_FILE:
        document = load_changelog_document(STRUCTURED_CHANGELOG_FILE)
        generated = normalize_markdown(render_changelog_markdown(document))
        tracked = normalize_markdown(path.read_text(encoding="utf-8-sig"))
        if tracked != generated:
            raise ReleaseError("CHANGELOG.md is stale; run scripts/generate_changelog.py")
        sections: dict[str, ChangelogSection] = {
            "Unreleased": ChangelogSection(
                "Unreleased",
                None,
                render_release_body(document["unreleased"], locale="en").strip(),
            )
        }
        for release in document["releases"]:
            sections[release["version"]] = ChangelogSection(
                release["version"],
                release["date"],
                render_release_body(release, locale="en").strip(),
            )
        return sections
    content = normalize_markdown(text if text is not None else path.read_text(encoding="utf-8-sig"))
    matches = list(CHANGELOG_HEADING_RE.finditer(content))
    if not matches or matches[0].group("version") != "Unreleased":
        raise ReleaseError("CHANGELOG.md must start its release sections with [Unreleased]")
    sections: dict[str, ChangelogSection] = {}
    for index, match in enumerate(matches):
        version = match.group("version")
        if version in sections:
            raise ReleaseError(f"Duplicate changelog section: {version}")
        if version != "Unreleased":
            SemVer.parse(version)
            if not match.group("date"):
                raise ReleaseError(f"Released changelog section {version} is missing a date")
            try:
                date.fromisoformat(match.group("date"))
            except ValueError as exc:
                raise ReleaseError(f"Invalid changelog date for {version}") from exc
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[match.end():end].strip()
        sections[version] = ChangelogSection(version, match.group("date"), body)
    return sections


def release_notes(version: str) -> str:
    SemVer.parse(version)
    section = parse_changelog().get(version)
    if not section or not section.body:
        raise ReleaseError(f"Missing non-empty changelog section for {version}")
    if "[Unreleased]" in section.body:
        raise ReleaseError("Unreleased content leaked into release notes")
    rendered = normalize_markdown(section.body)
    assert_public_text(rendered, "release notes")
    return rendered


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value.startswith(('"', "'")):
        try:
            return json.loads(value) if value.startswith('"') else ast.literal_eval(value)
        except (json.JSONDecodeError, ValueError, SyntaxError) as exc:
            raise ReleaseError(f"Invalid quoted YAML scalar: {value}") from exc
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value in {"true", "false"}:
        return value == "true"
    if any(marker in value for marker in ("#", "{", "}", "[", "]")):
        raise ReleaseError(f"YAML scalar must be quoted: {value}")
    return value


def parse_simple_yaml(path: Path = ANKIWEB_METADATA_FILE) -> dict[str, Any]:
    result: dict[str, Any] = {}
    active_list: str | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - "):
            if active_list is None:
                raise ReleaseError(f"Unexpected list item at {path}:{line_number}")
            result[active_list].append(parse_scalar(raw[4:]))
            continue
        if raw.startswith((" ", "\t")) or ":" not in raw:
            raise ReleaseError(f"Unsupported YAML structure at {path}:{line_number}")
        key, value = raw.split(":", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in result:
            raise ReleaseError(f"Invalid or duplicate YAML key at {path}:{line_number}: {key}")
        scalar = parse_scalar(value)
        if scalar is None:
            result[key] = []
            active_list = key
        else:
            result[key] = scalar
            active_list = None
    return result


def validate_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = dict(metadata or parse_simple_yaml())
    keys = set(metadata)
    if keys != EXPECTED_METADATA_KEYS:
        raise ReleaseError(f"AnkiWeb metadata keys mismatch; missing={sorted(EXPECTED_METADATA_KEYS - keys)}, unknown={sorted(keys - EXPECTED_METADATA_KEYS)}")
    if metadata["schema_version"] != 1 or metadata["addon_id"] != 373100400:
        raise ReleaseError("Unexpected AnkiWeb schema version or add-on ID")
    if metadata["title"] != "Anki Study Report" or metadata["expected_branch_label"] != "Branch 1":
        raise ReleaseError("Unexpected AnkiWeb title or branch")
    tags = metadata["tags"]
    if not isinstance(tags, list) or not tags or len(tags) != len(set(tags)) or not all(re.fullmatch(r"[a-z0-9-]+", str(tag)) for tag in tags):
        raise ReleaseError("AnkiWeb tags must be a non-empty ordered unique slug list")
    for key in ("support_url", "repository_url", "releases_url", "donation_url"):
        if not isinstance(metadata[key], str) or not metadata[key].startswith("https://"):
            raise ReleaseError(f"{key} must be an HTTPS URL")
    if metadata["minimum_anki_version"] != "26.05.0" or metadata["maximum_anki_version"] != "26.05.0":
        raise ReleaseError("AnkiWeb branch must use the approved 26.05.0 minimum and non-restrictive maximum")
    if metadata["download_client_version"] != 260500:
        raise ReleaseError("download_client_version must match Anki 26.05")
    return metadata


def stable_description() -> str:
    text = normalize_markdown(ANKIWEB_DESCRIPTION_FILE.read_text(encoding="utf-8-sig"))
    if not text.strip():
        raise ReleaseError("Stable AnkiWeb description is empty")
    assert_public_text(text, "stable AnkiWeb description")
    return text


def render_ankiweb_description(version: str) -> str:
    metadata = validate_metadata()
    notes = release_notes(version).rstrip()
    stable = stable_description().rstrip()
    rendered = normalize_markdown(
        f"# {metadata['title']}\n\n"
        f"## What's new in {version}\n\n"
        f"{notes}\n\n"
        f"[Full release history]({metadata['releases_url']})\n\n"
        "---\n\n"
        f"{stable}\n"
    )
    if rendered.count("## What's new in") != 1:
        raise ReleaseError("Rendered AnkiWeb description contains duplicate What's new blocks")
    assert_public_text(rendered, "rendered AnkiWeb description")
    return rendered


def assert_public_text(text: str, label: str) -> None:
    encoded = normalize_markdown(text).encode("utf-8")
    if not encoded.strip() or len(encoded) > MAX_PUBLIC_MARKDOWN_BYTES:
        raise ReleaseError(f"{label} must be non-empty and at most {MAX_PUBLIC_MARKDOWN_BYTES} bytes")
    for pattern, reason in PUBLIC_TEXT_GUARDS:
        if pattern.search(text):
            raise ReleaseError(f"{label} contains {reason}")


def validate_manifest_release_date(version: str) -> dict[str, Any]:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8-sig"))
    mod = manifest.get("mod")
    if not isinstance(mod, int) or mod <= 0:
        raise ReleaseError("manifest.json.mod must be a positive Unix timestamp")
    section = parse_changelog().get(version)
    if not section or not section.release_date:
        raise ReleaseError(f"Missing changelog release date for {version}")
    mod_date = datetime.fromtimestamp(mod, tz=timezone.utc).date().isoformat()
    if mod_date != section.release_date:
        raise ReleaseError(f"manifest.json.mod UTC date {mod_date} does not match changelog date {section.release_date}")
    return manifest


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def stable_version_tags() -> list[tuple[SemVer, str]]:
    result: list[tuple[SemVer, str]] = []
    for tag in git("tag", "--list", "v*").stdout.splitlines():
        try:
            parsed = SemVer.parse(tag.removeprefix("v"))
        except ReleaseError:
            continue
        if not parsed.prerelease and not parsed.build:
            result.append((parsed, tag))
    return sorted(result, key=lambda item: item[0].precedence_key())


def ensure_new_tag(version: str, *, check_remote: bool = True) -> None:
    tag = f"v{version}"
    if git("rev-parse", "--verify", f"refs/tags/{tag}", check=False).returncode == 0:
        raise ReleaseError(f"Git tag already exists: {tag}")
    if check_remote:
        remote = git("ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}", check=False)
        if remote.returncode == 0:
            raise ReleaseError(f"Remote Git tag already exists: {tag}")
        if remote.returncode not in {2}:
            raise ReleaseError(f"Could not verify remote tag {tag}: exit {remote.returncode}")


def validate_release(
    version: str,
    channel: str,
    *,
    artifact: Path | None = None,
    check_remote_tag: bool = True,
    allow_existing_tag: bool = False,
) -> dict[str, Any]:
    parsed = SemVer.parse(version)
    if channel not in {"stable", "prerelease"}:
        raise ReleaseError(f"Unsupported release channel: {channel}")
    if channel == "stable" and parsed.prerelease:
        raise ReleaseError("Stable channel requires a non-prerelease version")
    if channel == "prerelease" and not parsed.prerelease:
        raise ReleaseError("Prerelease channel requires a SemVer prerelease identifier")
    canonical = read_version()
    if version != canonical:
        raise ReleaseError(f"Workflow version {version} does not match canonical version {canonical}")
    release_notes(version)
    metadata = validate_metadata()
    render_ankiweb_description(version)
    manifest = validate_manifest_release_date(version)
    previous = stable_version_tags()
    if allow_existing_tag:
        if previous and parsed < previous[-1][0]:
            raise ReleaseError(f"Version {version} must not regress below stable tag {previous[-1][1]}")
    else:
        ensure_new_tag(version, check_remote=check_remote_tag)
        if previous and not (previous[-1][0] < parsed):
            raise ReleaseError(f"Version {version} must be greater than previous stable tag {previous[-1][1]}")
    if artifact is not None:
        if artifact.name != APPROVED_ARTIFACT_NAME or not artifact.is_file():
            raise ReleaseError(f"Release artifact must be an existing {APPROVED_ARTIFACT_NAME}")
    return {
        "schemaVersion": 1,
        "version": version,
        "channel": channel,
        "tag": f"v{version}",
        "artifactName": APPROVED_ARTIFACT_NAME,
        "manifestMod": manifest["mod"],
        "ankiwebAddonId": metadata["addon_id"],
        "ankiwebBranch": metadata["expected_branch_label"],
        "descriptionSha256": sha256_text(render_ankiweb_description(version)),
        "artifactSha256": sha256_file(artifact) if artifact else None,
    }
