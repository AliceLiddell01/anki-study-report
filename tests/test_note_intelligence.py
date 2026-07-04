from __future__ import annotations

from conftest import fresh_import_addon_module


def model(name, fields, templates=None, css=""):
    return {
        "id": 42,
        "name": name,
        "flds": [{"name": field} for field in fields],
        "tmpls": templates or [{"ord": 0, "name": "Card 1", "qfmt": "{{Слово}}", "afmt": "{{Значение}}"}],
        "css": css,
    }


def test_detects_japanese_vocab_fields_by_russian_names():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    profile = note_intelligence.analyze_note_type(
        model("Японский словарь", ["Слово", "Чтение", "Значение", "Часть речи", "Pitch"]),
        "\x1f".join(["鑑みる", "かんがみる", "учитывать", "глагол", "LHL"]),
    )

    roles = {field["name"]: field["detectedRole"] for field in profile["fields"]}
    assert profile["detectedKind"] == "japanese_vocab"
    assert roles["Слово"] == "term"
    assert roles["Чтение"] == "reading"
    assert roles["Значение"] == "meaning"
    assert roles["Часть речи"] == "partOfSpeech"
    assert roles["Pitch"] == "pitch"


def test_detects_audio_image_and_gif_badges():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    preview = note_intelligence.build_note_preview(
        model("Japanese", ["Word", "Audio", "Image", "Pitch", "Example"]),
        "\x1f".join(["承", "[sound:jou.mp3]", '<img src="kanji.gif">', "HL", "承知しました"]),
    )

    assert preview["primary"] == "承"
    assert preview["mediaBadges"] == ["audio", "image", "gif", "pitch", "example"]


def test_detects_programming_and_basic_safely():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    programming = note_intelligence.analyze_note_type(
        model("Programming", ["Question", "Answer"], [{"ord": 0, "name": "Forward", "qfmt": "{{Question}}", "afmt": "{{Answer}}"}]),
        "\x1f".join(["What does const do?", "Declares a binding"]),
    )
    basic = note_intelligence.analyze_note_type(model("Basic", ["Front", "Back"]), "\x1f".join(["Front", "Back"]))

    assert programming["detectedKind"] == "programming"
    assert basic["detectedKind"] == "basic"


def test_unknown_note_type_does_not_crash():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    profile = note_intelligence.analyze_note_type(None, "Known text")
    preview = note_intelligence.build_note_preview(None, "Known text")

    assert profile["detectedKind"] == "unknown"
    assert preview["primary"] == "Known text"


def test_preview_sanitizes_html_sound_and_paths():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    preview = note_intelligence.build_note_preview(
        model("Basic", ["Front"]),
        '<script>alert(1)</script><b>Word</b> [sound:x.mp3] C:\\Users\\KykLa\\secret.png file:///C:/secret.gif',
    )

    assert preview["primary"] == "alert(1) Word"
    assert "<" not in preview["primary"]
    assert "[sound:" not in preview["primary"]
    assert "C:\\Users" not in preview["primary"]
    assert "file://" not in preview["primary"]


def test_preview_picks_term_reading_meaning_for_japanese_cards():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    preview = note_intelligence.build_note_preview(
        model("Japanese vocab", ["Слово", "Чтение", "Значение", "Часть речи"]),
        "\x1f".join(["鑑みる", "かんがみる", "учитывать", "глагол"]),
    )

    assert preview["frontText"] == "鑑みる"
    assert preview["backText"] == "учитывать"
    assert preview["primary"] == "鑑みる"
    assert preview["secondary"] == "かんがみる"
    assert preview["tertiary"] == "учитывать / глагол"


def test_preview_uses_qfmt_for_front_and_does_not_mix_afmt_only_fields():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    preview = note_intelligence.build_note_preview(
        model(
            "Japanese vocab",
            ["Слово", "Пример", "Значение", "Часть речи"],
            [{"ord": 0, "name": "Recognition", "qfmt": "{{Слово}}<br>{{Пример}}", "afmt": "{{FrontSide}}<hr>{{Значение}} {{Часть речи}}"}],
        ),
        "\x1f".join(["約束する", "明日、友達と約束する。", "обещать", "глагол"]),
    )

    assert preview["frontText"] == "約束する 明日、友達と約束する。"
    assert preview["backText"] == "обещать глагол"
    assert "обещать" not in preview["frontText"]
    assert "глагол" not in preview["frontText"]


def test_rendered_preview_uses_front_template_and_front_media_only():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    rendered = note_intelligence.build_rendered_preview(
        model(
            "Japanese vocab",
            ["Слово", "Гифка", "Звук", "Значение"],
            [
                {
                    "ord": 0,
                    "name": "Recognition",
                    "qfmt": '<div class="card-content"><div class="main-word">[sound:front.mp3]{{Слово}}</div><img src="{{Гифка}}"></div>',
                    "afmt": "{{FrontSide}}<hr>{{Значение}} [sound:answer.mp3]",
                }
            ],
        ),
        "\x1f".join(["承", "front.gif", "front.mp3", "answer text"]),
    )

    assert rendered["frontPlainText"] == "承"
    assert '<audio class="asr-card-audio" controls controlsList="nodownload noplaybackrate" preload="none" src="/api/media?name=front.mp3"></audio>' in rendered["frontHtml"]
    assert '<div class="main-word">' in rendered["frontHtml"]
    assert "承" in rendered["frontHtml"]
    assert "/api/media?name=front.gif" in rendered["frontHtml"]
    assert "answer text" not in rendered["frontPlainText"]
    assert rendered["mediaRefs"] == [
        {"name": "front.gif", "type": "image", "url": "/api/media?name=front.gif"},
        {"name": "front.mp3", "type": "audio", "url": "/api/media?name=front.mp3"},
    ]


def test_rendered_preview_preserves_safe_inline_styles_class_and_media_order():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    front = (
        '[sound:要望.mp3]<br>【<span style="color: rgb(170, 170, 127);"><b>を</b></span>】'
        '<img src="要.gif"><img src="望.gif">（<span style="color: rgb(255, 165, 0);"><b>する</b></span>）'
        '<br><br>（改善を<span class="word-focus">要望する</span>。）'
    )

    rendered = note_intelligence.build_rendered_preview(
        model(
            "Any user note type",
            ["Слово"],
            [{"ord": 0, "name": "Recognition", "qfmt": "{{Слово}}", "afmt": "{{FrontSide}}"}],
            css=".word-focus { color: #67d391; font-weight: 700; } .card.nightMode { background: #111827; }",
        ),
        front,
    )

    html = rendered["frontHtml"]
    assert '<audio class="asr-card-audio" controls controlsList="nodownload noplaybackrate" preload="none" src="/api/media?name=%E8%A6%81%E6%9C%9B.mp3"></audio>' in html
    assert 'style="color: rgb(170, 170, 127)"' in html
    assert 'style="color: rgb(255, 165, 0)"' in html
    assert 'class="word-focus"' in html
    assert html.index("asr-card-audio") < html.index("rgb(170, 170, 127)") < html.index("%E8%A6%81.gif") < html.index("%E6%9C%9B.gif") < html.index("word-focus")
    assert rendered["css"].startswith(".word-focus")
    assert rendered["cardOrd"] == 0
    assert rendered["mediaRefs"] == [
        {"name": "要.gif", "type": "image", "url": "/api/media?name=%E8%A6%81.gif"},
        {"name": "望.gif", "type": "image", "url": "/api/media?name=%E6%9C%9B.gif"},
        {"name": "要望.mp3", "type": "audio", "url": "/api/media?name=%E8%A6%81%E6%9C%9B.mp3"},
    ]


def test_rendered_preview_removes_dangerous_html_urls_and_styles():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    html, refs = note_intelligence.sanitize_rendered_html(
        '<script>alert(1)</script>'
        '<span class="word-focus" style="position:absolute;color:red;background-image:url(javascript:alert(1));font-weight:700">x</span>'
        '<img src="x.gif" onerror="alert(1)" srcset="evil.gif 2x">'
        '<a href="javascript:alert(1)">bad</a>'
        '<img src="file:///C:/secret.png">'
        '<img src="C:\\Users\\KykLa\\secret.png">'
    )

    assert "<script" not in html
    assert "onerror" not in html
    assert "javascript:" not in html
    assert "file://" not in html
    assert "C:\\Users" not in html
    assert "srcset" not in html
    assert 'class="word-focus"' in html
    assert 'style="color: red; font-weight: 700"' in html
    assert refs == [{"name": "x.gif", "type": "image", "url": "/api/media?name=x.gif"}]


def test_preview_front_fallback_uses_primary_only_when_template_is_unavailable():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    preview = note_intelligence.build_note_preview(
        {"id": 42, "name": "Japanese vocab", "flds": [{"name": "Слово"}, {"name": "Значение"}, {"name": "Чтение"}], "tmpls": []},
        "\x1f".join(["電話する", "звонить", "でんわする"]),
    )

    assert preview["frontText"] == "電話する"
    assert preview["backText"] == "звонить"


def test_missing_pitch_and_example_require_existing_role_fields():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    without_pitch = note_intelligence.analyze_note_type(model("Japanese", ["Word", "Meaning"]), "\x1f".join(["語", "word"]))
    with_pitch = note_intelligence.analyze_note_type(model("Japanese", ["Word", "Meaning", "Pitch", "Example"]), "\x1f".join(["語", "word", "", ""]))
    programming = note_intelligence.analyze_note_type(model("Programming", ["Question", "Answer"]), "\x1f".join(["Q", "A"]))

    assert "missing_pitch" not in note_intelligence.missing_fields_for_profile(without_pitch, "\x1f".join(["語", "word"]))
    assert "missing_example" not in note_intelligence.missing_fields_for_profile(without_pitch, "\x1f".join(["語", "word"]))
    assert note_intelligence.missing_fields_for_profile(with_pitch, "\x1f".join(["語", "word", "", ""])) == ["missing_example", "missing_pitch"]
    assert note_intelligence.missing_fields_for_profile(programming, "\x1f".join(["Q", "A"])) == []
