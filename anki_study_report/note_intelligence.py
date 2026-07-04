"""Read-only note type and preview heuristics for card-level diagnostics."""

from __future__ import annotations

from html import escape, unescape
import re
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse


FIELD_SEPARATOR = "\x1f"
PREVIEW_SCHEMA_VERSION = 1
RENDER_SOURCE_ANKI_NATIVE = "anki_native"
RENDER_SOURCE_ANKI_LIKE_FALLBACK = "anki_like_fallback"
IMAGE_MEDIA_EXTENSIONS = {"gif", "png", "jpg", "jpeg", "webp"}
AUDIO_MEDIA_EXTENSIONS = {"mp3", "ogg", "wav", "m4a", "flac"}
MEDIA_EXTENSIONS = IMAGE_MEDIA_EXTENSIONS | AUDIO_MEDIA_EXTENSIONS
SAFE_INLINE_STYLE_PROPERTIES = {
    "color",
    "background-color",
    "font-weight",
    "font-style",
    "text-decoration",
    "text-align",
    "vertical-align",
    "white-space",
    "font-size",
    "line-height",
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "border",
    "border-color",
    "border-width",
    "border-style",
    "border-radius",
    "display",
}
SAFE_DISPLAY_VALUES = {
    "block",
    "inline",
    "inline-block",
    "flex",
    "inline-flex",
    "grid",
    "inline-grid",
    "none",
}
UNSAFE_STYLE_VALUE_RE = re.compile(
    r"(?:expression\s*\(|url\s*\(|@import|javascript\s*:|vbscript\s*:|data\s*:|behavior\s*:|position\s*:|z-index\s*:)",
    re.IGNORECASE,
)

_ROLE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("reading", ("чтение", "reading", "kana", "furigana", "yomi", "pronunciation")),
    ("partOfSpeech", ("часть речи", "part of speech", "pos", "speech")),
    ("meaning", ("значение", "перевод", "meaning", "translation", "definition", "gloss", "back")),
    ("example", ("пример", "sentence", "example", "context", "предложение")),
    ("audio", ("audio", "sound", "звук", "аудио")),
    ("pitch", ("pitch", "accent", "ударение", "акцент")),
    ("kanjiGif", ("kanji gif", "kanjigif", "stroke", "gif")),
    ("image", ("image", "picture", "photo", "img", "картинка", "изображение", "kanji")),
    ("answer", ("answer", "ответ", "solution", "definition")),
    ("explanation", ("explanation", "объяснение", "notes", "note", "комментарий")),
    ("term", ("слово", "word", "expression", "term", "vocab", "выражение")),
    ("question", ("front", "question", "вопрос", "title", "prompt")),
)


def analyze_note_type(model: Any, raw_fields: Any = None) -> dict[str, Any]:
    """Return a safe, best-effort profile for an Anki note type model."""

    model_dict = model if isinstance(model, dict) else {}
    note_type_name = _safe_text(model_dict.get("name") or "")
    raw_values = split_field_values(raw_fields)
    fields = []
    japanese_signals = 0
    programming_signals = 0
    for index, field in enumerate(model_dict.get("flds") if isinstance(model_dict.get("flds"), list) else []):
        name = _field_name(field, index)
        value = raw_values[index] if index < len(raw_values) else ""
        role, confidence = detect_field_role(name, value)
        if _contains_japanese(name) or _contains_japanese(value):
            japanese_signals += 1
        if _looks_like_code(name) or _looks_like_code(value):
            programming_signals += 1
        fields.append(
            {
                "name": name,
                "index": index,
                "normalizedName": normalize_name(name),
                "detectedRole": role,
                "confidence": confidence,
            }
        )

    if not fields and raw_values:
        for index, value in enumerate(raw_values):
            role, confidence = detect_field_role(f"field_{index + 1}", value)
            fields.append(
                {
                    "name": f"field_{index + 1}",
                    "index": index,
                    "normalizedName": f"field {index + 1}",
                    "detectedRole": role,
                    "confidence": confidence,
                }
            )

    templates = _template_profiles(model_dict.get("tmpls"), fields)
    kind, confidence = _detect_kind(note_type_name, fields, templates, japanese_signals, programming_signals)
    return {
        "noteTypeId": _safe_int(model_dict.get("id") or model_dict.get("mid")),
        "noteTypeName": note_type_name,
        "fields": fields,
        "templates": templates,
        "detectedKind": kind,
        "confidence": confidence,
    }


def build_note_preview(model: Any, raw_fields: Any, card_ord: Any = 0) -> dict[str, Any]:
    """Build a compact, sanitized table preview for a note/card pair."""

    profile = analyze_note_type(model, raw_fields)
    values = split_field_values(raw_fields)
    field_values = _fields_with_values(profile, values)
    template = _template_for_card(profile, card_ord)
    kind = str(profile.get("detectedKind") or "unknown")

    primary = _first_value_for_roles(field_values, _primary_roles(kind))
    secondary = _first_value_for_roles(field_values, _secondary_roles(kind))
    tertiary = _tertiary_value(field_values, profile, template, kind)
    front_text = _front_text_for_template(template, field_values)
    back_text = _back_text_for_template(template, field_values)

    if not primary:
        primary = front_text or _first_meaningful_value(field_values)
    if not primary:
        primary = "Карточка без front preview"
    if not front_text:
        front_text = primary
    if not back_text:
        back_text = _first_value_for_roles(field_values, ("answer", "meaning", "explanation"))
    if not secondary and kind == "unknown":
        secondary = _join_compact([profile.get("noteTypeName"), template.get("name") if template else None], " / ")
    if not tertiary and kind in {"programming", "basic", "unknown"}:
        tertiary = _join_compact([profile.get("noteTypeName"), template.get("name") if template else None], " / ")

    badges = detect_media_badges(field_values, profile)
    return {
        "frontText": _truncate_text(front_text, 160),
        "backText": _truncate_text(back_text, 220) if back_text else "",
        "primary": _truncate_text(primary, 120),
        "secondary": _truncate_text(secondary, 120) if secondary else "",
        "tertiary": _truncate_text(tertiary, 140) if tertiary else "",
        "mediaBadges": badges,
        "noteTypeName": _safe_text(profile.get("noteTypeName")),
        "cardTemplateName": _safe_text(template.get("name") if template else ""),
        "detectedKind": kind,
    }


def build_rendered_preview_native_first(
    col: Any,
    card_id: Any,
    model: Any,
    raw_fields: Any,
    card_ord: Any = 0,
) -> dict[str, Any]:
    """Render from a live Anki Card first, with the template renderer as fallback."""

    native, fallback_reason = try_render_native_card_preview(col, card_id, card_ord=card_ord)
    if native is not None:
        return native
    return build_rendered_preview(
        model,
        raw_fields,
        card_ord,
        card_id=card_id,
        fallback_reason=fallback_reason or "native_unavailable",
    )


def try_render_native_card_preview(col: Any, card_id: Any, card_ord: Any = 0) -> tuple[dict[str, Any] | None, str | None]:
    """Best-effort native Anki render for one card.

    The add-on may also run in unit tests without Anki, so this function never
    raises to callers. It returns a short machine-readable fallback reason when
    native rendering is unavailable.
    """

    card_id_int = _safe_int(card_id)
    if card_id_int <= 0:
        return None, "native_unavailable_no_card_id"
    if col is None:
        return None, "native_unavailable_no_collection"
    try:
        get_card = getattr(col, "get_card")
    except Exception:
        return None, "native_unavailable_no_get_card"
    if not callable(get_card):
        return None, "native_unavailable_no_get_card"
    try:
        card = get_card(card_id_int)
    except Exception:
        return None, "native_unavailable_get_card_failed"
    if card is None:
        return None, "native_unavailable_card_missing"
    return render_card_preview_native(card, card_id=card_id_int, card_ord=card_ord)


def render_card_preview_native(card: Any, *, card_id: Any = None, card_ord: Any = 0) -> tuple[dict[str, Any] | None, str | None]:
    """Render a safe card preview using Anki's Card/TemplateRenderOutput APIs."""

    try:
        native = _native_render_output(card)
        if native is None:
            native = _native_question_answer(card)
        if native is None:
            return None, "native_render_failed"

        front_raw = native.get("frontHtml") or ""
        back_raw = native.get("backHtml") or ""
        front_raw = _append_av_media_html(front_raw, native.get("frontAvTags"))
        back_raw = _append_av_media_html(back_raw, native.get("backAvTags"))
        front_html, front_media = sanitize_rendered_html(front_raw)
        back_html, back_media = sanitize_rendered_html(back_raw)
        css = sanitize_card_css(native.get("css"))
        media_refs = _unique_media_refs(front_media + back_media)
        if not front_html and not back_html and not safe_plain_text(front_raw) and not safe_plain_text(back_raw):
            return None, "native_render_empty"
        return {
            "renderStatus": "sanitized",
            "renderSource": RENDER_SOURCE_ANKI_NATIVE,
            "fallbackReason": None,
            "frontHtml": front_html,
            "backHtml": back_html,
            "css": css,
            "frontPlainText": safe_plain_text(front_raw, 240),
            "backPlainText": safe_plain_text(back_raw, 320),
            "mediaRefs": media_refs,
            "cardOrd": _safe_int(card_ord, _safe_int(getattr(card, "ord", 0))),
            "cardId": _safe_int(card_id, _safe_int(getattr(card, "id", 0))),
            "reason": "native Anki renderer",
        }, None
    except Exception:
        return None, "native_render_failed"


def build_rendered_preview(
    model: Any,
    raw_fields: Any,
    card_ord: Any = 0,
    *,
    card_id: Any = None,
    fallback_reason: str = "native_unavailable_not_requested",
) -> dict[str, Any]:
    """Render a safe Anki-like front/back preview from card templates."""

    model_dict = model if isinstance(model, dict) else {}
    template = _raw_template_for_card(model_dict, card_ord)
    if not template:
        return {
            "renderStatus": "unavailable",
            "renderSource": RENDER_SOURCE_ANKI_LIKE_FALLBACK,
            "fallbackReason": fallback_reason or "anki_like_template_unavailable",
            "reason": "Card template is unavailable; structured preview is used.",
            "mediaRefs": [],
            "cardOrd": _safe_int(card_ord),
            "cardId": _safe_int(card_id),
        }

    fields = _field_value_map(model_dict, split_field_values(raw_fields))
    qfmt = str(template.get("qfmt") or "")
    afmt = str(template.get("afmt") or "")
    css = sanitize_card_css(model_dict.get("css"))

    front_raw = _render_template(qfmt, fields, front_side="")
    back_raw = _render_template(afmt, fields, front_side=front_raw)
    front_html, front_media = sanitize_rendered_html(front_raw)
    back_html, _back_media = sanitize_rendered_html(back_raw)
    media_refs = _unique_media_refs(front_media)
    front_plain = safe_plain_text(front_raw, 240)
    back_plain = safe_plain_text(back_raw, 320)
    reason = "template renderer"
    if _template_contains_javascript(qfmt) or _template_contains_javascript(afmt):
        reason = "template renderer; template contains JavaScript, scripts are not executed in card list preview for safety."

    if not front_html and not back_html and not front_plain and not back_plain:
        return {
            "renderStatus": "fallback",
            "renderSource": RENDER_SOURCE_ANKI_LIKE_FALLBACK,
            "fallbackReason": fallback_reason,
            "frontPlainText": "Карточка без front preview",
            "backPlainText": "",
            "css": css,
            "mediaRefs": media_refs,
            "cardOrd": _safe_int(card_ord),
            "cardId": _safe_int(card_id),
            "reason": "Template rendered no visible front/back content.",
        }

    return {
        "renderStatus": "sanitized",
        "renderSource": RENDER_SOURCE_ANKI_LIKE_FALLBACK,
        "fallbackReason": fallback_reason,
        "frontHtml": front_html,
        "backHtml": back_html,
        "css": css,
        "frontPlainText": front_plain,
        "backPlainText": back_plain,
        "mediaRefs": media_refs,
        "cardOrd": _safe_int(card_ord),
        "cardId": _safe_int(card_id),
        "reason": reason,
    }


def sanitize_rendered_html(value: Any) -> tuple[str, list[dict[str, str]]]:
    """Sanitize rendered card HTML and rewrite local media references."""

    media_refs: list[dict[str, str]] = []
    text = str(value or "")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(?:iframe|object|embed|meta|link)\b[^>]*>.*?</(?:iframe|object|embed)>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(?:iframe|object|embed|meta|link)\b[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\son\w+\s*=\s*[^\s>]+", "", text, flags=re.IGNORECASE)
    text = _sanitize_style_attributes(text)
    text = re.sub(r"\ssrcset\s*=\s*(['\"]).*?\1", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\ssrcset\s*=\s*[^\s>]+", "", text, flags=re.IGNORECASE)
    text = _rewrite_media_attributes(text, media_refs)
    text = _rewrite_sound_tags(text, media_refs)
    text = re.sub(r"\b[A-Za-z]:\\[^\s<>\"']+", " ", text)
    text = re.sub(r"file://[^\s<>\"']+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"token=[^\s&<>\"']+", "token=[redacted]", text, flags=re.IGNORECASE)
    return text[:6000], _unique_media_refs(media_refs)


def sanitize_card_css(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"@import[^;]+;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"url\((?:file://|https?://|[A-Za-z]:\\)[^)]+\)", "url()", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Za-z]:\\[^\s;{}]+", " ", text)
    text = re.sub(r"token=[^\s;{}]+", "token=[redacted]", text, flags=re.IGNORECASE)
    return text[:4000]


def _sanitize_style_attributes(text: str) -> str:
    def replace_quoted(match: re.Match[str]) -> str:
        quote_char = match.group(1)
        safe_style = _sanitize_inline_style(match.group(2))
        if not safe_style:
            return ""
        return f" style={quote_char}{escape(safe_style, quote=True)}{quote_char}"

    text = re.sub(r"\sstyle\s*=\s*(['\"])(.*?)\1", replace_quoted, text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\sstyle\s*=\s*(?!['\"])[^\s>]+", "", text, flags=re.IGNORECASE)


def _sanitize_inline_style(value: Any) -> str:
    declarations: list[str] = []
    for raw_declaration in str(value or "").split(";"):
        if ":" not in raw_declaration:
            continue
        raw_property, raw_value = raw_declaration.split(":", 1)
        property_name = re.sub(r"\s+", "", raw_property.strip().lower())
        property_value = raw_value.strip()
        if property_name not in SAFE_INLINE_STYLE_PROPERTIES or not property_value:
            continue
        if property_name in {"position", "z-index", "behavior"}:
            continue
        if "<" in property_value or ">" in property_value or UNSAFE_STYLE_VALUE_RE.search(property_value):
            continue
        if property_name == "display" and property_value.lower() not in SAFE_DISPLAY_VALUES:
            continue
        declarations.append(f"{property_name}: {property_value}")
    return "; ".join(declarations)


def missing_fields_for_profile(profile: dict[str, Any], raw_fields: Any) -> list[str]:
    """Return explainable missing-field issues based on detected field roles."""

    values = split_field_values(raw_fields)
    field_values = _fields_with_values(profile, values)
    kind = str(profile.get("detectedKind") or "unknown")
    missing: list[str] = []
    role_to_issue = {
        "audio": "missing_audio",
        "example": "missing_example",
        "pitch": "missing_pitch",
        "image": "missing_image",
        "kanjiGif": "missing_image",
        "meaning": "missing_meaning",
        "partOfSpeech": "missing_part_of_speech",
    }
    japanese_only_roles = {"audio", "example", "pitch", "image", "kanjiGif"}
    for role, issue in role_to_issue.items():
        matches = [item for item in field_values if item["role"] == role]
        if not matches:
            continue
        if role in japanese_only_roles and kind not in {"japanese_vocab", "japanese_grammar"}:
            continue
        if all(_role_value_is_empty(role, item["raw"]) for item in matches) and issue not in missing:
            missing.append(issue)
    return missing


def split_field_values(raw_fields: Any) -> list[str]:
    return [str(value or "") for value in str(raw_fields or "").split(FIELD_SEPARATOR)]


def detect_field_role(name: Any, value: Any = "") -> tuple[str, float]:
    normalized = normalize_name(name)
    for role, aliases in _ROLE_ALIASES:
        if any(alias in normalized for alias in aliases):
            return role, 0.92
    raw = str(value or "")
    lower = raw.lower()
    if "[sound:" in lower:
        return "audio", 0.78
    if "<img" in lower:
        return "image", 0.72
    if ".gif" in lower:
        return "kanjiGif", 0.7
    if _looks_like_code(raw):
        return "question", 0.48
    return "unknown", 0.2


def detect_media_badges(field_values: list[dict[str, Any]], profile: dict[str, Any]) -> list[str]:
    badges: list[str] = []
    for item in field_values:
        role = item["role"]
        raw = str(item["raw"] or "")
        lower = raw.lower()
        if (role == "audio" or "[sound:" in lower) and "[sound:" in lower:
            _add_unique(badges, "audio")
        if role == "pitch" and _plain_text(raw):
            _add_unique(badges, "pitch")
        if role == "example" and _plain_text(raw):
            _add_unique(badges, "example")
        if "<img" in lower or (role == "image" and _plain_text(raw)):
            _add_unique(badges, "image")
        if ".gif" in lower or role == "kanjiGif":
            _add_unique(badges, "gif")
    if str(profile.get("detectedKind")) == "japanese_vocab":
        return [badge for badge in badges if badge in {"audio", "pitch", "image", "gif", "example"}]
    return badges


def sanitize_media_filename(value: Any) -> str:
    text = unquote(str(value or "").strip())
    if not text:
        return ""
    if re.search(r"^[a-z][a-z0-9+.-]*:", text, flags=re.IGNORECASE):
        return ""
    if "\\" in text or "/" in text or ".." in text or text.startswith("."):
        return ""
    if re.match(r"^[A-Za-z]:", text):
        return ""
    extension = text.rsplit(".", 1)[-1].lower() if "." in text else ""
    if extension not in MEDIA_EXTENSIONS:
        return ""
    return text


def media_ref_for_name(name: str) -> dict[str, str]:
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    media_type = "audio" if extension in AUDIO_MEDIA_EXTENSIONS else "image"
    return {
        "name": name,
        "type": media_type,
        "url": f"/api/media?name={quote(name, safe='')}",
    }


def _native_render_output(card: Any) -> dict[str, Any] | None:
    render_output = getattr(card, "render_output", None)
    if not callable(render_output):
        return None
    output = _call_native_render_output(render_output)
    if output is None:
        return None
    front = _native_output_text(output, ("question_text", "question_html", "question"), "question_and_style")
    back = _native_output_text(output, ("answer_text", "answer_html", "answer"), "answer_and_style")
    css = _native_output_attr(output, "css")
    return {
        "frontHtml": front,
        "backHtml": back,
        "css": css,
        "frontAvTags": _native_output_attr(output, "question_av_tags"),
        "backAvTags": _native_output_attr(output, "answer_av_tags"),
    }


def _native_question_answer(card: Any) -> dict[str, Any] | None:
    question = _call_native_card_method(getattr(card, "question", None))
    answer = _call_native_card_method(getattr(card, "answer", None))
    if question is None and answer is None:
        return None
    return {"frontHtml": question or "", "backHtml": answer or "", "css": ""}


def _call_native_render_output(render_output: Any) -> Any:
    for kwargs in (
        {"reload": True, "browser": True},
        {"browser": True},
        {"reload": True},
        {},
    ):
        try:
            return render_output(**kwargs)
        except TypeError:
            continue
    return None


def _call_native_card_method(method: Any) -> str | None:
    if not callable(method):
        return None
    for kwargs in (
        {"reload": True, "browser": True},
        {"browser": True},
        {"reload": True},
        {},
    ):
        try:
            return str(method(**kwargs) or "")
        except TypeError:
            continue
    return None


def _native_output_text(output: Any, attrs: tuple[str, ...], method_name: str) -> str:
    for attr in attrs:
        value = _native_output_attr(output, attr)
        if value:
            return str(value)
    method = getattr(output, method_name, None)
    if callable(method):
        try:
            return str(method() or "")
        except Exception:
            return ""
    return ""


def _native_output_attr(output: Any, attr: str) -> Any:
    try:
        if isinstance(output, dict):
            return output.get(attr)
        return getattr(output, attr)
    except Exception:
        return None


def _append_av_media_html(html: Any, av_tags: Any) -> str:
    text = str(html or "")
    refs = _media_refs_from_av_tags(av_tags)
    if not refs:
        return text
    existing_names = {ref["name"] for ref in _unique_media_refs(sanitize_rendered_html(text)[1])}
    additions = []
    for ref in refs:
        if ref["name"] in existing_names:
            continue
        additions.append(
            f'<audio class="asr-card-audio" controls controlsList="nodownload noplaybackrate" preload="none" '
            f'src="{escape(ref["url"], quote=True)}"></audio>'
        )
    return text + "".join(additions)


def _media_refs_from_av_tags(av_tags: Any) -> list[dict[str, str]]:
    raw_tags = av_tags if isinstance(av_tags, (list, tuple, set)) else ([av_tags] if av_tags else [])
    refs: list[dict[str, str]] = []
    for tag in raw_tags:
        name = ""
        for attr in ("filename", "fname", "sound", "path"):
            try:
                name = sanitize_media_filename(getattr(tag, attr))
            except Exception:
                name = ""
            if name:
                break
        if not name and isinstance(tag, dict):
            for key in ("filename", "fname", "sound", "path"):
                name = sanitize_media_filename(tag.get(key))
                if name:
                    break
        if not name:
            match = re.search(r"([^\\/\s'\"<>]+\.(?:mp3|ogg|wav|m4a|flac))", str(tag), flags=re.IGNORECASE)
            name = sanitize_media_filename(match.group(1) if match else "")
        if name:
            refs.append(media_ref_for_name(name))
    return _unique_media_refs(refs)


def safe_plain_text(value: Any, limit: int | None = None) -> str:
    text = _plain_text(value)
    return _truncate_text(text, limit) if limit else text


def normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text)


def _template_profiles(raw_templates: Any, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates = raw_templates if isinstance(raw_templates, list) else []
    result = []
    for index, template in enumerate(templates):
        item = template if isinstance(template, dict) else {}
        qfmt = str(item.get("qfmt") or "")
        afmt = str(item.get("afmt") or "")
        result.append(
            {
                "ord": _safe_int(item.get("ord"), index),
                "name": _safe_text(item.get("name") or f"Card {index + 1}"),
                "qfmtSignals": _template_field_signals(qfmt, fields),
                "afmtSignals": _template_field_signals(afmt, fields),
            }
        )
    return result


def _raw_template_for_card(model: dict[str, Any], card_ord: Any) -> dict[str, Any]:
    templates = model.get("tmpls") if isinstance(model.get("tmpls"), list) else []
    wanted = _safe_int(card_ord)
    for template in templates:
        if isinstance(template, dict) and _safe_int(template.get("ord")) == wanted:
            return template
    for template in templates:
        if isinstance(template, dict):
            return template
    return {}


def _field_value_map(model: dict[str, Any], values: list[str]) -> dict[str, str]:
    fields = model.get("flds") if isinstance(model.get("flds"), list) else []
    result: dict[str, str] = {}
    for index, field in enumerate(fields):
        name = _field_name(field, index)
        value = values[index] if index < len(values) else ""
        result[name] = value
        result[normalize_name(name)] = value
    if not result:
        for index, value in enumerate(values):
            result[f"field_{index + 1}"] = value
            result[f"field {index + 1}"] = value
    return result


def _render_template(template: str, fields: dict[str, str], front_side: str) -> str:
    rendered = str(template or "")
    rendered = _render_conditionals(rendered, fields, inverted=False)
    rendered = _render_conditionals(rendered, fields, inverted=True)
    rendered = rendered.replace("{{FrontSide}}", front_side)

    def replace_field(match: re.Match[str]) -> str:
        raw_filter = normalize_name(match.group(1) or "")
        raw_name = str(match.group(2) or "").strip()
        if normalize_name(raw_name) == "frontside":
            return front_side
        value = _field_value(fields, raw_name)
        if raw_filter in {"text", "type"}:
            return escape(_plain_text(value))
        if raw_filter in {"hint"}:
            text = escape(_plain_text(value))
            return f"<span class=\"hint\">{text}</span>" if text else ""
        if raw_filter in {"cloze", "furigana", "kana", "kanji"}:
            return str(value or "")
        if raw_filter:
            return str(value or "")
        return str(value or "")

    rendered = re.sub(r"{{\s*(?:(\w+):)?\s*([^{}#/][^{}]*?)\s*}}", replace_field, rendered)
    rendered = re.sub(r"{{[^{}]+}}", " ", rendered)
    return rendered


def _render_conditionals(template: str, fields: dict[str, str], *, inverted: bool) -> str:
    marker = "^" if inverted else "#"
    pattern = re.compile(r"{{" + re.escape(marker) + r"\s*([^{}]+?)\s*}}(.*?){{/\s*\1\s*}}", re.IGNORECASE | re.DOTALL)

    def replace(match: re.Match[str]) -> str:
        value = _field_value(fields, match.group(1))
        present = bool(_plain_text(value) or "[sound:" in str(value).lower() or "<img" in str(value).lower())
        return match.group(2) if (not present if inverted else present) else ""

    previous = None
    current = template
    while previous != current:
        previous = current
        current = pattern.sub(replace, current)
    return current


def _field_value(fields: dict[str, str], name: Any) -> str:
    text = str(name or "").strip()
    return fields.get(text) or fields.get(normalize_name(text)) or ""


def _rewrite_sound_tags(text: str, media_refs: list[dict[str, str]]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = sanitize_media_filename(match.group(1))
        if not name:
            return '<span class="asr-card-media-missing">медиа недоступно</span>'
        ref = media_ref_for_name(name)
        media_refs.append(ref)
        return f'<audio class="asr-card-audio" controls controlsList="nodownload noplaybackrate" preload="none" src="{escape(ref["url"], quote=True)}"></audio>'

    return re.sub(r"\[sound:([^\]]+)\]", replace, text, flags=re.IGNORECASE)


def _rewrite_media_attributes(text: str, media_refs: list[dict[str, str]]) -> str:
    def replace_quoted(match: re.Match[str]) -> str:
        attr = match.group(1).lower()
        quote_char = match.group(2)
        name = _media_name_from_attribute_url(match.group(3))
        if not name:
            return ""
        ref = media_ref_for_name(name)
        media_refs.append(ref)
        return f'{attr}={quote_char}{escape(ref["url"], quote=True)}{quote_char}'

    def replace_unquoted(match: re.Match[str]) -> str:
        attr = match.group(1).lower()
        name = _media_name_from_attribute_url(match.group(2))
        if not name:
            return ""
        ref = media_ref_for_name(name)
        media_refs.append(ref)
        return f'{attr}="{escape(ref["url"], quote=True)}"'

    text = re.sub(r"\b(src|href)\s*=\s*(['\"])(.*?)\2", replace_quoted, text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\b(src|href)\s*=\s*(?!['\"])([^\s>]+)", replace_unquoted, text, flags=re.IGNORECASE)


def _media_name_from_attribute_url(value: Any) -> str:
    raw = unescape(str(value or "").strip())
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.path == "/api/media":
        names = parse_qs(parsed.query).get("name") or []
        return sanitize_media_filename(names[0] if names else "")
    return sanitize_media_filename(raw)


def _template_contains_javascript(value: Any) -> bool:
    text = str(value or "")
    return bool(re.search(r"<script\b|\son\w+\s*=|javascript\s*:", text, flags=re.IGNORECASE))


def _unique_media_refs(refs: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for ref in refs:
        name = sanitize_media_filename(ref.get("name") if isinstance(ref, dict) else "")
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(media_ref_for_name(name))
    return result


def _template_field_signals(template: str, fields: list[dict[str, Any]]) -> list[str]:
    names = {normalize_name(field.get("name")): str(field.get("name") or "") for field in fields}
    signals: list[str] = []
    for match in re.finditer(r"{{#?/?(?:cloze:)?([^}:]+)}}", template):
        normalized = normalize_name(match.group(1))
        if normalized in names:
            _add_unique(signals, names[normalized])
    return signals


def _detect_kind(
    note_type_name: str,
    fields: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    japanese_signals: int,
    programming_signals: int,
) -> tuple[str, float]:
    text = " ".join(
        [
            normalize_name(note_type_name),
            " ".join(str(field.get("normalizedName") or "") for field in fields),
            " ".join(str(template.get("name") or "") for template in templates),
        ]
    )
    roles = {str(field.get("detectedRole")) for field in fields}
    if "cloze" in text:
        return "cloze", 0.9
    if any(word in text for word in ("grammar", "граммат", "文法")):
        return "japanese_grammar", 0.82
    if japanese_signals or roles.intersection({"term", "reading", "pitch", "kanjiGif"}):
        return "japanese_vocab", 0.78
    if programming_signals or any(word in text for word in ("program", "code", "javascript", "python", "sql")):
        return "programming", 0.76
    if roles.intersection({"question", "answer"}) or all(word in text for word in ("front", "back")):
        return "basic", 0.68
    return "unknown", 0.3


def _fields_with_values(profile: dict[str, Any], values: list[str]) -> list[dict[str, Any]]:
    result = []
    fields = profile.get("fields") if isinstance(profile.get("fields"), list) else []
    for index, field in enumerate(fields):
        raw = values[index] if index < len(values) else ""
        result.append(
            {
                "name": str(field.get("name") or f"field_{index + 1}"),
                "role": str(field.get("detectedRole") or "unknown"),
                "raw": raw,
                "text": _plain_text(raw),
                "index": index,
            }
        )
    return result


def _template_for_card(profile: dict[str, Any], card_ord: Any) -> dict[str, Any]:
    templates = profile.get("templates") if isinstance(profile.get("templates"), list) else []
    wanted = _safe_int(card_ord)
    for template in templates:
        if _safe_int(template.get("ord")) == wanted:
            return template
    return templates[0] if templates else {}


def _primary_roles(kind: str) -> tuple[str, ...]:
    if kind in {"japanese_vocab", "japanese_grammar"}:
        return ("term", "question")
    if kind == "programming":
        return ("question", "term")
    return ("question", "term", "meaning")


def _secondary_roles(kind: str) -> tuple[str, ...]:
    if kind in {"japanese_vocab", "japanese_grammar"}:
        return ("reading", "meaning")
    if kind == "programming":
        return ("answer", "meaning", "explanation")
    return ("answer", "meaning", "reading")


def _tertiary_value(
    field_values: list[dict[str, Any]],
    profile: dict[str, Any],
    template: dict[str, Any],
    kind: str,
) -> str:
    if kind in {"japanese_vocab", "japanese_grammar"}:
        return _join_compact(
            [
                _first_value_for_roles(field_values, ("meaning",)),
                _first_value_for_roles(field_values, ("partOfSpeech",)),
            ],
            " / ",
        )
    return _join_compact([profile.get("noteTypeName"), template.get("name") if template else None], " / ")


def _first_value_for_roles(field_values: list[dict[str, Any]], roles: tuple[str, ...]) -> str:
    for role in roles:
        for item in field_values:
            if item["role"] == role and item["text"]:
                return str(item["text"])
    return ""


def _first_meaningful_value(field_values: list[dict[str, Any]]) -> str:
    for item in field_values:
        if item["text"]:
            return str(item["text"])
    return ""


def _front_text_for_template(template: dict[str, Any], field_values: list[dict[str, Any]]) -> str:
    qfmt_signals = template.get("qfmtSignals") if isinstance(template.get("qfmtSignals"), list) else []
    return _text_for_template_signals(qfmt_signals, field_values)


def _back_text_for_template(template: dict[str, Any], field_values: list[dict[str, Any]]) -> str:
    afmt_signals = template.get("afmtSignals") if isinstance(template.get("afmtSignals"), list) else []
    qfmt_signals = template.get("qfmtSignals") if isinstance(template.get("qfmtSignals"), list) else []
    front_names = {normalize_name(signal) for signal in qfmt_signals}
    back_only = [signal for signal in afmt_signals if normalize_name(signal) not in front_names]
    return _text_for_template_signals(back_only or afmt_signals, field_values)


def _text_for_template_signals(signals: list[Any], field_values: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for signal in signals:
        normalized = normalize_name(signal)
        for item in field_values:
            if normalize_name(item["name"]) == normalized and item["text"]:
                _add_unique(parts, str(item["text"]))
    return _join_compact(parts, " ")


def _role_value_is_empty(role: str, value: str) -> bool:
    lower = value.lower()
    if role == "audio":
        return "[sound:" not in lower
    if role in {"image", "kanjiGif"}:
        return "<img" not in lower and ".gif" not in lower
    return not _plain_text(value)


def _plain_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\[sound:[^\]]+\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b[A-Za-z]:\\[^\s<>\"']+", " ", text)
    text = re.sub(r"file://[^\s<>\"']+", " ", text, flags=re.IGNORECASE)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _field_name(field: Any, index: int) -> str:
    if isinstance(field, dict):
        text = str(field.get("name") or "").strip()
        if text:
            return text
    return f"field_{index + 1}"


def _contains_japanese(value: Any) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", str(value or "")))


def _looks_like_code(value: Any) -> bool:
    text = str(value or "")
    lowered = text.lower()
    if any(word in lowered for word in ("function ", "const ", "let ", "class ", "import ", "select ", "def ", "return ")):
        return True
    return bool(re.search(r"[{};=<>]{2,}|```|</?[a-z]+>", text))


def _safe_text(value: Any) -> str:
    return _plain_text(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _truncate_text(value: str, limit: int | None) -> str:
    if limit is None or len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def _join_compact(values: list[Any], separator: str) -> str:
    parts = [_plain_text(value) for value in values if _plain_text(value)]
    return separator.join(parts)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
