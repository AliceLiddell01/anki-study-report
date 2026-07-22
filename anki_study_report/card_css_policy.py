"""Parser-backed allowlist for untrusted Anki card stylesheets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import parse_qs, quote, unquote, urlparse

from ._vendor import tinycss2


MAX_CARD_CSS_INPUT_CHARS = 12_000
MAX_CARD_CSS_OUTPUT_CHARS = 4_000

_IMAGE_EXTENSIONS = {"gif", "jpeg", "jpg", "png", "webp"}
_FONT_EXTENSIONS = {"otf", "ttf", "woff", "woff2"}
_VIEWPORT_UNITS = {
    "dvb", "dvh", "dvi", "dvw", "lvb", "lvh", "lvi", "lvw",
    "svb", "svh", "svi", "svw", "vb", "vh", "vi", "vmax", "vmin", "vw",
}
_SAFE_PROPERTIES = {
    "align-content", "align-items", "align-self",
    "background", "background-color", "background-image", "background-position",
    "background-repeat", "background-size",
    "border", "border-block", "border-block-color", "border-block-end",
    "border-block-start", "border-bottom", "border-bottom-color", "border-bottom-left-radius",
    "border-bottom-right-radius", "border-bottom-style", "border-bottom-width", "border-collapse",
    "border-color", "border-inline", "border-inline-color", "border-inline-end",
    "border-inline-start", "border-left", "border-left-color", "border-left-style",
    "border-left-width", "border-radius", "border-right", "border-right-color",
    "border-right-style", "border-right-width", "border-spacing", "border-style",
    "border-top", "border-top-color", "border-top-left-radius", "border-top-right-radius",
    "border-top-style", "border-top-width", "border-width",
    "box-decoration-break", "box-shadow", "box-sizing",
    "break-after", "break-before", "break-inside",
    "caption-side", "clear", "color", "column-gap", "columns",
    "direction", "display",
    "flex", "flex-basis", "flex-direction", "flex-flow", "flex-grow", "flex-shrink",
    "flex-wrap", "float", "font", "font-family", "font-feature-settings", "font-kerning",
    "font-optical-sizing", "font-size", "font-stretch", "font-style", "font-variant",
    "font-variant-caps", "font-variant-east-asian", "font-variant-ligatures",
    "font-variant-numeric", "font-weight",
    "gap", "grid", "grid-area", "grid-auto-columns", "grid-auto-flow", "grid-auto-rows",
    "grid-column", "grid-column-end", "grid-column-gap", "grid-column-start", "grid-gap",
    "grid-row", "grid-row-end", "grid-row-gap", "grid-row-start", "grid-template",
    "grid-template-areas", "grid-template-columns", "grid-template-rows",
    "height", "hyphens", "justify-content", "justify-items", "justify-self",
    "letter-spacing", "line-break", "line-height", "list-style", "list-style-position",
    "list-style-type",
    "margin", "margin-block", "margin-block-end", "margin-block-start", "margin-bottom",
    "margin-inline", "margin-inline-end", "margin-inline-start", "margin-left", "margin-right",
    "margin-top", "max-height", "max-width", "min-height", "min-width",
    "object-fit", "object-position", "opacity", "order", "orphans", "outline",
    "outline-color", "outline-offset", "outline-style", "outline-width", "overflow",
    "overflow-wrap", "overflow-x", "overflow-y",
    "padding", "padding-block", "padding-block-end", "padding-block-start", "padding-bottom",
    "padding-inline", "padding-inline-end", "padding-inline-start", "padding-left", "padding-right",
    "padding-top", "place-content", "place-items", "place-self", "position",
    "row-gap", "ruby-align", "ruby-position", "tab-size", "table-layout", "text-align",
    "text-align-last", "text-decoration", "text-decoration-color", "text-decoration-line",
    "text-decoration-style", "text-emphasis", "text-emphasis-color", "text-emphasis-position",
    "text-emphasis-style", "text-indent", "text-justify", "text-orientation", "text-overflow",
    "text-shadow", "text-transform", "text-underline-offset", "text-underline-position",
    "unicode-bidi", "vertical-align", "white-space", "widows", "width", "word-break",
    "word-spacing", "word-wrap", "writing-mode",
}
_URL_PROPERTIES = {"background", "background-image"}
_SAFE_FUNCTIONS = {
    "calc", "clamp", "conic-gradient", "hsl", "hsla", "hwb", "lab", "lch",
    "linear-gradient", "max", "min", "oklab", "oklch", "radial-gradient", "repeat",
    "repeating-conic-gradient", "repeating-linear-gradient", "repeating-radial-gradient",
    "rgb", "rgba",
}
_SAFE_DISPLAY_VALUES = {
    "block", "contents", "flex", "flow-root", "grid", "inline", "inline-block",
    "inline-flex", "inline-grid", "inline-table", "list-item", "none", "ruby", "table",
    "table-caption", "table-cell", "table-column", "table-column-group", "table-footer-group",
    "table-header-group", "table-row", "table-row-group",
}
_SAFE_POSITION_VALUES = {"absolute", "relative", "static"}
_FONT_FACE_PROPERTIES = {"font-display", "font-family", "font-stretch", "font-style", "font-weight", "src"}
_FONT_FACE_FUNCTIONS = {"format", "local", "tech"}
_MAX_ABSOLUTE_NUMBER = 10_000


@dataclass(frozen=True)
class _SanitizedRules:
    scoped: tuple[str, ...] = ()
    font_faces: tuple[str, ...] = ()

    def merged(self, other: "_SanitizedRules") -> "_SanitizedRules":
        return _SanitizedRules(self.scoped + other.scoped, self.font_faces + other.font_faces)


def sanitize_card_stylesheet(value: Any) -> str:
    """Return bounded card CSS whose selectors and resource loads are constrained."""

    try:
        text = str(value or "")
    except Exception:
        return ""
    if not text.strip() or len(text) > MAX_CARD_CSS_INPUT_CHARS or not _has_balanced_css_structure(text):
        return ""
    try:
        parsed = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True)
        if any(getattr(node, "type", "") == "error" for node in parsed):
            return ""
        sanitized = _sanitize_rule_nodes(parsed, depth=0)
        if not sanitized.scoped and not sanitized.font_faces:
            return ""
        chunks = list(sanitized.font_faces)
        if sanitized.scoped:
            chunks.append(f"@scope (.card){{{''.join(sanitized.scoped)}}}")
        result = "".join(chunks)
        return result if len(result) <= MAX_CARD_CSS_OUTPUT_CHARS else ""
    except Exception:
        # Untrusted card content must never surface parser details or raw CSS.
        return ""


def sanitize_card_css_media_name(value: Any) -> str:
    """Return a safe local image/font leaf name accepted by card CSS."""

    raw = str(value or "").strip()
    safe_url = _safe_local_media_url(raw, _IMAGE_EXTENSIONS | _FONT_EXTENSIONS)
    if not safe_url:
        return ""
    return parse_qs(urlparse(safe_url).query).get("name", [""])[0]


def _sanitize_rule_nodes(nodes: Iterable[Any], *, depth: int) -> _SanitizedRules:
    if depth > 3:
        return _SanitizedRules()
    result = _SanitizedRules()
    for node in nodes:
        node_type = getattr(node, "type", "")
        if node_type == "qualified-rule":
            rule = _sanitize_qualified_rule(node)
            if rule:
                result = result.merged(_SanitizedRules(scoped=(rule,)))
            continue
        if node_type != "at-rule":
            continue
        keyword = str(getattr(node, "lower_at_keyword", "") or "")
        if keyword == "font-face":
            font_face = _sanitize_font_face(node)
            if font_face:
                result = result.merged(_SanitizedRules(font_faces=(font_face,)))
        elif keyword == "media":
            media = _sanitize_media_rule(node, depth=depth)
            if media:
                result = result.merged(_SanitizedRules(scoped=(media,)))
        elif keyword == "scope" and _is_card_scope_prelude(getattr(node, "prelude", ())):
            content = getattr(node, "content", None)
            if content is not None:
                nested = tinycss2.parse_rule_list(content, skip_comments=True, skip_whitespace=True)
                if not any(getattr(item, "type", "") == "error" for item in nested):
                    result = result.merged(_sanitize_rule_nodes(nested, depth=depth + 1))
    return result


def _sanitize_qualified_rule(rule: Any) -> str:
    prelude = tuple(getattr(rule, "prelude", ()) or ())
    if not _selector_is_safe(prelude):
        return ""
    declarations = _sanitize_declarations(getattr(rule, "content", ()) or ())
    if not declarations:
        return ""
    selector = _rewrite_scoped_selector_list(prelude)
    if not selector:
        return ""
    return f"{selector}{{{declarations}}}"


def _rewrite_scoped_selector_list(tokens: Iterable[Any]) -> str:
    """Map native Anki root selectors to the actual ``@scope`` root.

    Anki applies ``.card`` and ordinal classes to the reviewer root itself.
    Inside ``@scope (.card)``, keeping a leading ``.card`` would instead look
    for a nested card.  Selector-list branches are rewritten independently so
    an ambiguous branch can fail closed without changing another branch's
    meaning.
    """

    branches: list[list[Any]] = [[]]
    for token in tokens:
        if getattr(token, "type", "") == "literal" and getattr(token, "value", "") == ",":
            branches.append([])
        else:
            branches[-1].append(token)
    rewritten: list[str] = []
    for branch in branches:
        value = _rewrite_scoped_selector(branch)
        if not value:
            return ""
        rewritten.append(value)
    return ",".join(rewritten)


def _rewrite_scoped_selector(tokens: Iterable[Any]) -> str:
    branch = list(tokens)
    while branch and getattr(branch[0], "type", "") in {"comment", "whitespace"}:
        branch.pop(0)
    while branch and getattr(branch[-1], "type", "") in {"comment", "whitespace"}:
        branch.pop()
    if not branch:
        return ""

    # Document roots are not part of the isolated Shadow DOM preview.  Reject
    # them instead of retaining a selector that could acquire new meaning.
    for token in branch:
        if getattr(token, "type", "") == "ident" and str(
            getattr(token, "lower_value", getattr(token, "value", ""))
        ).lower() in {"html", "body"}:
            return ""

    def class_name_at(index: int) -> str:
        if index + 1 >= len(branch):
            return ""
        dot, name = branch[index], branch[index + 1]
        if getattr(dot, "type", "") != "literal" or getattr(dot, "value", "") != ".":
            return ""
        if getattr(name, "type", "") != "ident":
            return ""
        return str(getattr(name, "value", "") or "")

    def root_tail(value: Iterable[Any]) -> str:
        tail = list(value)
        serialized = tinycss2.serialize(tail).strip()
        if serialized and tail and getattr(tail[0], "type", "") in {"comment", "whitespace"}:
            return f" {serialized}"
        return serialized

    first_class = class_name_at(0)
    if first_class.lower() == "card":
        return f":scope{root_tail(branch[2:])}"
    if first_class.lower().startswith("card") and first_class[4:].isdigit():
        return f":scope{tinycss2.serialize(branch).strip()}"

    # Native Anki styles commonly use `.nightMode .card`; the preview mirrors
    # that context by placing nightMode on the exact card root.
    if first_class.lower() == "nightmode":
        index = 2
        while index < len(branch) and getattr(branch[index], "type", "") in {"comment", "whitespace"}:
            index += 1
        nested_class = class_name_at(index)
        if nested_class.lower() == "card":
            return f":scope.nightMode{root_tail(branch[index + 2:])}"
        if nested_class.lower().startswith("card") and nested_class[4:].isdigit():
            return f":scope.nightMode{tinycss2.serialize(branch[index:]).strip()}"

    return tinycss2.serialize(branch).strip()


def _sanitize_declarations(tokens: Iterable[Any]) -> str:
    parsed = tinycss2.parse_declaration_list(tokens, skip_comments=True, skip_whitespace=True)
    if any(getattr(item, "type", "") == "error" for item in parsed):
        return ""
    declarations: list[str] = []
    for item in parsed:
        if getattr(item, "type", "") != "declaration":
            continue
        name = str(getattr(item, "lower_name", "") or "")
        if name.startswith("--") or name not in _SAFE_PROPERTIES:
            continue
        value_tokens = tuple(getattr(item, "value", ()) or ())
        if name == "display" and not _single_safe_ident(value_tokens, _SAFE_DISPLAY_VALUES):
            continue
        if name == "position" and not _single_safe_ident(value_tokens, _SAFE_POSITION_VALUES):
            continue
        value = _serialize_safe_values(value_tokens, allow_url=name in _URL_PROPERTIES, allowed_extensions=_IMAGE_EXTENSIONS)
        if not value:
            continue
        important = "!important" if bool(getattr(item, "important", False)) else ""
        declarations.append(f"{name}:{value}{important};")
    return "".join(declarations)


def _sanitize_font_face(rule: Any) -> str:
    prelude = tuple(getattr(rule, "prelude", ()) or ())
    if getattr(rule, "content", None) is None or any(
        getattr(token, "type", "") not in {"comment", "whitespace"} for token in prelude
    ):
        return ""
    parsed = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
    if any(getattr(item, "type", "") == "error" for item in parsed):
        return ""
    declarations: list[str] = []
    names: set[str] = set()
    for item in parsed:
        if getattr(item, "type", "") != "declaration":
            continue
        name = str(getattr(item, "lower_name", "") or "")
        if name not in _FONT_FACE_PROPERTIES:
            continue
        if name == "src":
            value = _serialize_safe_values(
                tuple(getattr(item, "value", ()) or ()),
                allow_url=True,
                allowed_extensions=_FONT_EXTENSIONS,
                extra_functions=_FONT_FACE_FUNCTIONS,
            )
        else:
            value = _serialize_safe_values(tuple(getattr(item, "value", ()) or ()), allow_url=False)
        if not value:
            continue
        declarations.append(f"{name}:{value};")
        names.add(name)
    if not {"font-family", "src"}.issubset(names):
        return ""
    return f"@font-face{{{''.join(declarations)}}}"


def _sanitize_media_rule(rule: Any, *, depth: int) -> str:
    content = getattr(rule, "content", None)
    prelude = tuple(getattr(rule, "prelude", ()) or ())
    if content is None or not _media_prelude_is_safe(prelude):
        return ""
    nested = tinycss2.parse_rule_list(content, skip_comments=True, skip_whitespace=True)
    if any(getattr(item, "type", "") == "error" for item in nested):
        return ""
    sanitized = _sanitize_rule_nodes(nested, depth=depth + 1)
    if not sanitized.scoped or sanitized.font_faces:
        return ""
    return f"@media {tinycss2.serialize(prelude).strip()}{{{''.join(sanitized.scoped)}}}"


def _selector_is_safe(tokens: Iterable[Any]) -> bool:
    significant = [token for token in tokens if getattr(token, "type", "") not in {"comment", "whitespace"}]
    if not significant:
        return False
    previous: Any = None
    for token in significant:
        token_type = getattr(token, "type", "")
        if token_type in {"at-keyword", "error", "url", "{} block"}:
            return False
        if token_type == "function":
            name = str(getattr(token, "lower_name", "") or "")
            if name in {"has", "host", "host-context"}:
                return False
            if not _selector_is_safe(getattr(token, "arguments", ()) or ()):
                return False
        elif token_type in {"[] block", "() block"}:
            if not _selector_is_safe(getattr(token, "content", ()) or ()):
                return False
        elif token_type == "ident" and getattr(previous, "value", None) == ":":
            if str(getattr(token, "lower_value", getattr(token, "value", ""))).lower() in {"host", "root"}:
                return False
        previous = token
    return True


def _media_prelude_is_safe(tokens: Iterable[Any]) -> bool:
    for token in tokens:
        token_type = getattr(token, "type", "")
        if token_type in {"at-keyword", "error", "function", "url", "{} block", "[] block"}:
            return False
        if token_type == "dimension" and _dimension_is_unsafe(token):
            return False
        if token_type == "() block" and not _media_prelude_is_safe(getattr(token, "content", ()) or ()):
            return False
    return True


def _serialize_safe_values(
    tokens: Iterable[Any],
    *,
    allow_url: bool,
    allowed_extensions: set[str] | None = None,
    extra_functions: set[str] | None = None,
) -> str:
    parts: list[str] = []
    function_allowlist = _SAFE_FUNCTIONS | set(extra_functions or ())
    for token in tokens:
        token_type = getattr(token, "type", "")
        if token_type == "error" or token_type in {"at-keyword", "{} block"}:
            return ""
        if token_type == "url":
            if not allow_url:
                return ""
            safe_url = _safe_local_media_url(getattr(token, "value", ""), allowed_extensions or set())
            if not safe_url:
                return ""
            parts.append(f'url("{safe_url}")')
            continue
        if token_type == "function":
            name = str(getattr(token, "lower_name", "") or "")
            if name == "url":
                if not allow_url:
                    return ""
                safe_url = _safe_url_function(getattr(token, "arguments", ()) or (), allowed_extensions or set())
                if not safe_url:
                    return ""
                parts.append(f'url("{safe_url}")')
                continue
            if name not in function_allowlist:
                return ""
            inner = _serialize_safe_values(
                getattr(token, "arguments", ()) or (),
                allow_url=False,
                allowed_extensions=allowed_extensions,
                extra_functions=extra_functions,
            )
            if not inner and any(getattr(item, "type", "") not in {"comment", "whitespace"} for item in token.arguments):
                return ""
            parts.append(f"{name}({inner})")
            continue
        if token_type == "dimension" and _dimension_is_unsafe(token):
            return ""
        if token_type in {"number", "percentage"} and abs(float(getattr(token, "value", 0) or 0)) > _MAX_ABSOLUTE_NUMBER:
            return ""
        if token_type in {"[] block", "() block"}:
            inner = _serialize_safe_values(
                getattr(token, "content", ()) or (),
                allow_url=False,
                allowed_extensions=allowed_extensions,
                extra_functions=extra_functions,
            )
            if not inner:
                return ""
            opening, closing = ("[", "]") if token_type == "[] block" else ("(", ")")
            parts.append(f"{opening}{inner}{closing}")
            continue
        parts.append(token.serialize())
    return "".join(parts).strip()


def _safe_url_function(tokens: Iterable[Any], allowed_extensions: set[str]) -> str:
    significant = [token for token in tokens if getattr(token, "type", "") not in {"comment", "whitespace"}]
    if len(significant) != 1 or getattr(significant[0], "type", "") != "string":
        return ""
    return _safe_local_media_url(getattr(significant[0], "value", ""), allowed_extensions)


def _safe_local_media_url(value: Any, allowed_extensions: set[str]) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return ""
    if parsed.path == "/api/media":
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) != {"name"} or len(query.get("name", ())) != 1:
            return ""
        name = query["name"][0]
    elif parsed.query or "/" in raw or "\\" in raw:
        return ""
    else:
        name = unquote(raw)
    if not name or name.startswith(".") or ".." in name or "/" in name or "\\" in name or "\x00" in name:
        return ""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in allowed_extensions:
        return ""
    return f"/api/media?name={quote(name, safe='')}"


def _single_safe_ident(tokens: Iterable[Any], allowed: set[str]) -> bool:
    significant = [token for token in tokens if getattr(token, "type", "") not in {"comment", "whitespace"}]
    if len(significant) != 1 or getattr(significant[0], "type", "") != "ident":
        return False
    return str(getattr(significant[0], "value", "") or "").lower() in allowed


def _dimension_is_unsafe(token: Any) -> bool:
    unit = str(getattr(token, "lower_unit", getattr(token, "unit", "")) or "").lower()
    value = abs(float(getattr(token, "value", 0) or 0))
    return unit in _VIEWPORT_UNITS or value > _MAX_ABSOLUTE_NUMBER


def _is_card_scope_prelude(tokens: Iterable[Any]) -> bool:
    return "".join(token.serialize() for token in tokens if getattr(token, "type", "") != "whitespace") == "(.card)"


def _has_balanced_css_structure(text: str) -> bool:
    stack: list[str] = []
    quote_char = ""
    in_comment = False
    escaped = False
    index = 0
    pairs = {"{": "}", "[": "]", "(": ")"}
    closers = set(pairs.values())
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_comment:
            if char == "*" and next_char == "/":
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if quote_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = ""
            elif char in "\r\n\f":
                return False
            index += 1
            continue
        if char == "/" and next_char == "*":
            in_comment = True
            index += 2
            continue
        if char in {'"', "'"}:
            quote_char = char
        elif char == "\\":
            index += 1
            if index >= len(text):
                return False
        elif char in pairs:
            stack.append(pairs[char])
        elif char in closers:
            if not stack or stack.pop() != char:
                return False
        index += 1
    return not stack and not quote_char and not in_comment and not escaped
