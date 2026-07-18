"""Canonical bounded compact identity for one exact Anki card.

The projector renders only the Browser question and, when needed, the native
reviewer front. It never scans arbitrary note fields and never reads media
files. The returned wire fields are plain text and bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Any


MAX_DISPLAY_TEXT_LENGTH = 240
DISPLAY_SOURCES = frozenset({"browser_question", "reviewer_front", "none"})
DISPLAY_STATUSES = frozenset({"available", "media_only", "unavailable"})

_SOUND_MARKER = re.compile(r"\[sound:[^\]\r\n]{1,500}\]", re.IGNORECASE)
_ANKI_AV_MARKER = re.compile(r"\[anki:play:[^\]\r\n]{1,100}\]", re.IGNORECASE)
_DROP_CONTENT_TAGS = frozenset({
    "script", "style", "iframe", "object", "embed", "svg", "math",
    "template", "form", "audio", "video", "picture",
})
_MEDIA_TAGS = frozenset({"img", "audio", "video", "source", "picture"})
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "dd", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4",
    "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
    "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
})


@dataclass(frozen=True)
class CardDisplayIdentity:
    display_text: str
    display_source: str
    display_status: str
    display_truncated: bool

    def to_wire(self) -> dict[str, object]:
        return {
            "displayText": self.display_text,
            "displaySource": self.display_source,
            "displayStatus": self.display_status,
            "displayTruncated": self.display_truncated,
        }


@dataclass(frozen=True)
class CompactProjection:
    text: str
    truncated: bool
    media_found: bool
    valid: bool


def project_card_display_identity(card: Any) -> CardDisplayIdentity:
    """Render one exact card through the supported Anki question contexts."""

    browser = _render_question(card, browser=True)
    browser_projection = project_compact_html(browser.html) if browser.available else _invalid_projection()
    if browser_projection.valid and browser_projection.text:
        return CardDisplayIdentity(
            browser_projection.text,
            "browser_question",
            "available",
            browser_projection.truncated,
        )

    reviewer = _render_question(card, browser=False)
    reviewer_projection = project_compact_html(reviewer.html) if reviewer.available else _invalid_projection()
    if reviewer_projection.valid and reviewer_projection.text:
        return CardDisplayIdentity(
            reviewer_projection.text,
            "reviewer_front",
            "available",
            reviewer_projection.truncated,
        )

    if reviewer_projection.valid and reviewer_projection.media_found:
        return CardDisplayIdentity("", "reviewer_front", "media_only", False)
    if browser_projection.valid and browser_projection.media_found:
        return CardDisplayIdentity("", "browser_question", "media_only", False)
    return unavailable_card_display_identity()


def unavailable_card_display_identity() -> CardDisplayIdentity:
    return CardDisplayIdentity("", "none", "unavailable", False)


def project_compact_html(value: object) -> CompactProjection:
    """Project the first meaningful rendered line without inventing spacing."""

    raw = str(value or "")
    media_found = False

    def mark_media(_match: re.Match[str]) -> str:
        nonlocal media_found
        media_found = True
        return ""

    raw = _SOUND_MARKER.sub(mark_media, raw)
    raw = _ANKI_AV_MARKER.sub(mark_media, raw)
    parser = _CompactHTMLParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return _invalid_projection()
    if parser.failed or parser.drop_depth:
        return _invalid_projection()
    media_found = media_found or parser.media_found

    for raw_line in parser.lines:
        line = " ".join(raw_line.replace("\xa0", " ").split())
        if not line:
            continue
        if len(line) <= MAX_DISPLAY_TEXT_LENGTH:
            return CompactProjection(line, False, media_found, True)
        return CompactProjection(
            line[: MAX_DISPLAY_TEXT_LENGTH - 1].rstrip() + "…",
            True,
            media_found,
            True,
        )
    return CompactProjection("", False, media_found, True)


@dataclass(frozen=True)
class _RenderedQuestion:
    available: bool
    html: str


def _render_question(card: Any, *, browser: bool) -> _RenderedQuestion:
    try:
        question = getattr(card, "question", None)
        if not callable(question):
            return _RenderedQuestion(False, "")
        return _RenderedQuestion(True, str(question(reload=True, browser=browser) or ""))
    except Exception:
        return _RenderedQuestion(False, "")


def _invalid_projection() -> CompactProjection:
    return CompactProjection("", False, False, False)


class _CompactHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = [""]
        self.media_found = False
        self.drop_depth = 0
        self.failed = False
        self._drop_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in _MEDIA_TAGS:
            self.media_found = True
        if self.drop_depth:
            if name not in _VOID_TAGS:
                self.drop_depth += 1
                self._drop_stack.append(name)
            return
        if name in _DROP_CONTENT_TAGS:
            if name not in _VOID_TAGS:
                self.drop_depth = 1
                self._drop_stack.append(name)
            return
        if name == "br" or name in _BLOCK_TAGS:
            self._line_break()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in _MEDIA_TAGS:
            self.media_found = True
        if not self.drop_depth and (name == "br" or name in _BLOCK_TAGS):
            self._line_break()

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if self.drop_depth:
            if not self._drop_stack or self._drop_stack[-1] != name:
                self.failed = True
                return
            self._drop_stack.pop()
            self.drop_depth -= 1
            return
        if name in _BLOCK_TAGS:
            self._line_break()

    def handle_data(self, data: str) -> None:
        if not self.drop_depth:
            self.lines[-1] += data

    def _line_break(self) -> None:
        if self.lines[-1]:
            self.lines.append("")
        elif len(self.lines) == 1:
            self.lines.append("")
