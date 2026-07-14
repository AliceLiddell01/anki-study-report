"""Canonical composition for the public AnkiWeb add-on description."""

from __future__ import annotations

import re

from release_common import (
    ANKIWEB_DESCRIPTION_FILE,
    ReleaseError,
    assert_public_text,
    normalize_markdown,
    release_notes,
    validate_metadata,
)


LEVEL_ONE_HEADING_RE = re.compile(r"(?m)^#\s+\S")


def stable_ankiweb_description() -> str:
    """Return validated stable product copy without an AnkiWeb-owned page title."""
    text = normalize_markdown(ANKIWEB_DESCRIPTION_FILE.read_text(encoding="utf-8-sig"))
    if not text.strip():
        raise ReleaseError("Stable AnkiWeb description is empty")
    if LEVEL_ONE_HEADING_RE.search(text):
        raise ReleaseError("Stable AnkiWeb description must not contain a level-one heading")
    assert_public_text(text, "stable AnkiWeb description")
    return text


def render_ankiweb_description(version: str) -> str:
    """Append current-version notes after the stable public product description."""
    metadata = validate_metadata()
    stable = stable_ankiweb_description().rstrip()
    notes = release_notes(version).rstrip()
    rendered = normalize_markdown(
        f"{stable}\n\n"
        "---\n\n"
        f"## What's new in {version}\n\n"
        f"{notes}\n\n"
        f"[Full release history]({metadata['releases_url']})\n"
    )
    if LEVEL_ONE_HEADING_RE.search(rendered):
        raise ReleaseError("Rendered AnkiWeb description must not contain a level-one heading")
    if rendered.count("## What's new in") != 1:
        raise ReleaseError("Rendered AnkiWeb description contains duplicate What's new blocks")
    if rendered.count(metadata["donation_url"]) != 1:
        raise ReleaseError("Rendered AnkiWeb description must contain exactly one donation URL")
    assert_public_text(rendered, "rendered AnkiWeb description")
    return rendered
