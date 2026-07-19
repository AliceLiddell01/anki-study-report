"""Canonical bounded compact identity for one exact Anki card.

The projector renders only the Browser question and, when needed, the native
reviewer front. Optional declarative formatters operate on ordered safe tokens;
they never read media files or execute user code. The returned wire fields are
plain text and bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
from typing import Any


MAX_DISPLAY_TEXT_LENGTH = 240
MAX_MEDIA_FILENAME_LENGTH = 255
DISPLAY_SOURCES = frozenset({"browser_question", "reviewer_front", "none"})
DISPLAY_STATUSES = frozenset({"available", "media_only", "unavailable"})
IMAGE_MARKER = "🖼"
AUDIO_MARKER = "🔊"

_SOUND_TOKEN = re.compile(r"\[sound:([^\]\r\n]{1,500})\]", re.IGNORECASE)
_ANKI_AV_TOKEN = re.compile(r"\[anki:play:[^\]\r\n]{1,100}\]", re.IGNORECASE)
_INLINE_AUDIO_TOKEN = re.compile(
    r"\[sound:([^\]\r\n]{1,500})\]|\[anki:play:[^\]\r\n]{1,100}\]",
    re.IGNORECASE,
)
_DROP_CONTENT_TAGS = frozenset({
    "script", "style", "iframe", "object", "embed", "svg", "math",
    "template", "form", "audio", "video", "picture",
})
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


@dataclass(frozen=True)
class DisplayToken:
    kind: str
    value: str | None = None


@dataclass(frozen=True)
class TokenizedQuestion:
    tokens: tuple[DisplayToken, ...]
    media_found: bool
    valid: bool


@dataclass(frozen=True)
class _RenderedQuestion:
    available: bool
    html: str


class _RenderCache:
    def __init__(self, card: Any) -> None:
        self.card = card
        self._values: dict[str, _RenderedQuestion] = {}

    def get(self, source: str) -> _RenderedQuestion:
        if source not in self._values:
            self._values[source] = _render_question(
                self.card,
                browser=source == "browser_question",
            )
        return self._values[source]


def project_card_display_identity(
    card: Any,
    formatter: dict[str, Any] | None = None,
) -> CardDisplayIdentity:
    """Render one exact card through supported question contexts.

    A valid enabled formatter may override compact text. Any missing render,
    invalid token stream, empty output, or omitted-only output falls back to the
    unchanged canonical Browser → reviewer projection using cached renders.
    """

    cache = _RenderCache(card)
    if isinstance(formatter, dict):
        source = formatter.get("inputSource")
        if source in {"browser_question", "reviewer_front"}:
            rendered = cache.get(source)
            if rendered.available:
                tokenized = tokenize_compact_html(rendered.html)
                configured = project_formatter_tokens(tokenized, formatter)
                if configured.valid and configured.text:
                    return CardDisplayIdentity(
                        configured.text,
                        source,
                        "available",
                        configured.truncated,
                    )
    return _canonical_identity(cache)


def unavailable_card_display_identity() -> CardDisplayIdentity:
    return CardDisplayIdentity("", "none", "unavailable", False)


def project_compact_html(value: object) -> CompactProjection:
    """Project the first meaningful rendered line without inventing spacing."""

    tokenized = tokenize_compact_html(value)
    if not tokenized.valid:
        return _invalid_projection()
    text, truncated = _render_lines(
        tokenized.tokens,
        text_mode="preserve",
        image_mode="omit",
        audio_mode="omit",
        max_lines=1,
        line_separator=" ",
        max_characters=MAX_DISPLAY_TEXT_LENGTH,
    )
    return CompactProjection(text, truncated, tokenized.media_found, True)


def tokenize_compact_html(value: object) -> TokenizedQuestion:
    parser = _CompactTokenParser()
    try:
        parser.feed(str(value or ""))
        parser.close()
    except Exception:
        return _invalid_tokenization()
    if parser.failed or parser.drop_depth:
        return _invalid_tokenization()
    return TokenizedQuestion(tuple(parser.tokens), parser.media_found, True)


def project_formatter_tokens(
    tokenized: TokenizedQuestion,
    formatter: dict[str, Any],
) -> CompactProjection:
    if not tokenized.valid:
        return _invalid_projection()
    try:
        text, truncated = _render_lines(
            tokenized.tokens,
            text_mode=formatter["textMode"],
            image_mode=formatter["imageMode"],
            audio_mode=formatter["audioMode"],
            max_lines=int(formatter["maxLines"]),
            line_separator=str(formatter["lineSeparator"]),
            max_characters=min(MAX_DISPLAY_TEXT_LENGTH, int(formatter["maxCharacters"])),
        )
    except (KeyError, TypeError, ValueError):
        return _invalid_projection()
    return CompactProjection(text, truncated, tokenized.media_found, True)


def _canonical_identity(cache: _RenderCache) -> CardDisplayIdentity:
    browser = cache.get("browser_question")
    browser_projection = (
        project_compact_html(browser.html) if browser.available else _invalid_projection()
    )
    if browser_projection.valid and browser_projection.text:
        return CardDisplayIdentity(
            browser_projection.text,
            "browser_question",
            "available",
            browser_projection.truncated,
        )

    reviewer = cache.get("reviewer_front")
    reviewer_projection = (
        project_compact_html(reviewer.html) if reviewer.available else _invalid_projection()
    )
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


def _render_lines(
    tokens: tuple[DisplayToken, ...],
    *,
    text_mode: str,
    image_mode: str,
    audio_mode: str,
    max_lines: int,
    line_separator: str,
    max_characters: int,
) -> tuple[str, bool]:
    lines: list[str] = [""]
    for token in tokens:
        if token.kind == "line_break":
            lines.append("")
            continue
        emitted = ""
        if token.kind == "text" and text_mode == "preserve":
            emitted = token.value or ""
        elif token.kind == "image":
            emitted = _emit_media(token.value, image_mode, IMAGE_MARKER)
        elif token.kind == "audio":
            emitted = _emit_media(token.value, audio_mode, AUDIO_MARKER)
        if emitted:
            lines[-1] += emitted

    meaningful: list[str] = []
    for line in lines:
        normalized = " ".join(line.replace("\xa0", " ").split())
        if normalized:
            meaningful.append(normalized)
        if len(meaningful) >= max_lines:
            break
    text = line_separator.join(meaningful)
    return _truncate(text, max_characters)


def _emit_media(filename: str | None, mode: str, marker: str) -> str:
    if mode == "omit":
        return ""
    if mode == "marker":
        return marker
    if not filename:
        return ""
    if mode == "filename":
        return filename
    if mode == "stem":
        head, separator, _suffix = filename.rpartition(".")
        return head if separator and head else filename
    return ""


def _truncate(value: str, maximum: int) -> tuple[str, bool]:
    maximum = max(1, min(MAX_DISPLAY_TEXT_LENGTH, int(maximum)))
    if len(value) <= maximum:
        return value, False
    if maximum == 1:
        return "…", True
    return value[: maximum - 1].rstrip() + "…", True


def _render_question(card: Any, *, browser: bool) -> _RenderedQuestion:
    try:
        question = getattr(card, "question", None)
        if not callable(question):
            return _RenderedQuestion(False, "")
        return _RenderedQuestion(
            True,
            str(question(reload=True, browser=browser) or ""),
        )
    except Exception:
        return _RenderedQuestion(False, "")


def _safe_media_filename(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = unescape(value).strip()
    if not text or len(text) > MAX_MEDIA_FILENAME_LENGTH:
        return None
    if text in {".", ".."} or "/" in text or "\\" in text:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        return None
    lowered = text.casefold()
    if ":" in text or lowered.startswith(("data:", "file:", "http:", "https:")):
        return None
    return text


def _invalid_projection() -> CompactProjection:
    return CompactProjection("", False, False, False)


def _invalid_tokenization() -> TokenizedQuestion:
    return TokenizedQuestion((), False, False)


class _CompactTokenParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[DisplayToken] = []
        self.media_found = False
        self.drop_depth = 0
        self.failed = False
        self._drop_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if self.drop_depth:
            container = self._drop_stack[-1] if self._drop_stack else ""
            if name == "img" and container == "picture":
                self.media_found = True
                self.tokens.append(
                    DisplayToken("image", _safe_media_filename(_attribute(attrs, "src")))
                )
            elif name == "source" and container in {"audio", "video", "picture"}:
                self.media_found = True
                kind = "image" if container == "picture" else "audio"
                self.tokens.append(
                    DisplayToken(kind, _safe_media_filename(_attribute(attrs, "src")))
                )
            if name not in _VOID_TAGS:
                self.drop_depth += 1
                self._drop_stack.append(name)
            return
        if name in _DROP_CONTENT_TAGS:
            self.media_found = self.media_found or name in {"audio", "video", "picture"}
            if name in {"audio", "video"}:
                self.tokens.append(
                    DisplayToken("audio", _safe_media_filename(_attribute(attrs, "src")))
                )
            if name not in _VOID_TAGS:
                self.drop_depth = 1
                self._drop_stack.append(name)
            return
        if name == "img":
            self.media_found = True
            self.tokens.append(DisplayToken("image", _safe_media_filename(_attribute(attrs, "src"))))
            return
        if name == "source":
            self.media_found = True
            self.tokens.append(DisplayToken("audio", _safe_media_filename(_attribute(attrs, "src"))))
            return
        if name == "br" or name in _BLOCK_TAGS:
            self._line_break()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        previous_depth = self.drop_depth
        self.handle_starttag(tag, attrs)
        while self.drop_depth > previous_depth and self._drop_stack:
            self._drop_stack.pop()
            self.drop_depth -= 1

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
        if self.drop_depth or not data:
            return
        cursor = 0
        for match in _INLINE_AUDIO_TOKEN.finditer(data):
            if match.start() > cursor:
                self.tokens.append(DisplayToken("text", data[cursor:match.start()]))
            self.media_found = True
            filename = _safe_media_filename(match.group(1)) if match.group(1) is not None else None
            self.tokens.append(DisplayToken("audio", filename))
            cursor = match.end()
        if cursor < len(data):
            self.tokens.append(DisplayToken("text", data[cursor:]))

    def _line_break(self) -> None:
        if not self.tokens or self.tokens[-1].kind != "line_break":
            self.tokens.append(DisplayToken("line_break"))


def _attribute(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key.lower() == name:
            return value
    return None
