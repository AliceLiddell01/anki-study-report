from __future__ import annotations

import builtins

import pytest

from conftest import import_addon_module

identity = import_addon_module("card_display_identity")


class FakeCard:
    def __init__(self, *, browser_html="", reviewer_html="", browser_error=None, reviewer_error=None):
        self.browser_html = browser_html
        self.reviewer_html = reviewer_html
        self.browser_error = browser_error
        self.reviewer_error = reviewer_error
        self.question_calls = []
        self.answer_calls = 0

    def question(self, reload=False, browser=False):
        self.question_calls.append((reload, browser))
        error = self.browser_error if browser else self.reviewer_error
        if error:
            raise error
        return self.browser_html if browser else self.reviewer_html

    def answer(self):
        self.answer_calls += 1
        raise AssertionError("answer must not be rendered")


def formatter(**updates):
    value = {
        "inputSource": "reviewer_front",
        "textMode": "preserve",
        "imageMode": "stem",
        "audioMode": "omit",
        "maxLines": 1,
        "lineSeparator": " ",
        "maxCharacters": 240,
    }
    value.update(updates)
    return value


FIXTURE = (
    "[sound:感謝.mp3]<br>"
    '【<b>に</b>】<img src="感.gif"><img src="謝.gif">（<b>する</b>）'
    "<br><br>（先生に感謝する。）"
)


def test_exact_japanese_default_and_configured_output():
    canonical_card = FakeCard(reviewer_html=FIXTURE)
    canonical = identity.project_card_display_identity(canonical_card).to_wire()
    assert canonical["displayText"] == "【に】（する）"

    configured_card = FakeCard(reviewer_html=FIXTURE)
    configured = identity.project_card_display_identity(configured_card, formatter()).to_wire()
    assert configured == {
        "displayText": "【に】感謝（する）",
        "displaySource": "reviewer_front",
        "displayStatus": "available",
        "displayTruncated": False,
    }
    assert configured_card.question_calls == [(True, False)]
    assert configured_card.answer_calls == 0


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("omit", "AB"),
        ("filename", "A感.gif謝.pngB"),
        ("stem", "A感謝B"),
        ("marker", "A🖼🖼B"),
    ],
)
def test_image_modes_preserve_token_order(mode, expected):
    card = FakeCard(reviewer_html='A<img src="感.gif"><img src="謝.png">B')
    result = identity.project_card_display_identity(card, formatter(imageMode=mode)).to_wire()
    assert result["displayText"] == expected


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("omit", "AB"),
        ("filename", "Avoice.mp3B"),
        ("stem", "AvoiceB"),
        ("marker", "A🔊🔊B"),
    ],
)
def test_audio_modes_and_unnamed_av_marker(mode, expected):
    card = FakeCard(reviewer_html="A[sound:voice.mp3][anki:play:q:0]B")
    result = identity.project_card_display_identity(card, formatter(audioMode=mode, imageMode="omit")).to_wire()
    assert result["displayText"] == expected


def test_audio_and_picture_source_tags_use_safe_local_names():
    card = FakeCard(reviewer_html=(
        '<audio><source src="voice.ogg"></audio>'
        '<picture><source src="kanji.webp"><img src="fallback.png"></picture>'
    ))
    result = identity.project_card_display_identity(
        card, formatter(audioMode="stem", imageMode="stem")
    ).to_wire()
    assert result["displayText"] == "voice kanjifallback" or result["displayText"] == "voicekanjifallback"


def test_text_omit_lines_separator_and_truncation_are_exact():
    card = FakeCard(reviewer_html="A<img src='one.png'><br>B<img src='two.png'><br>C")
    result = identity.project_card_display_identity(
        card,
        formatter(textMode="omit", imageMode="stem", maxLines=2, lineSeparator=" / ", maxCharacters=9),
    ).to_wire()
    assert result["displayText"] == "one / two"
    assert result["displayTruncated"] is False
    truncated = identity.project_card_display_identity(
        FakeCard(reviewer_html="abcdefghijk"), formatter(maxCharacters=5)
    ).to_wire()
    assert truncated["displayText"] == "abcd…"
    assert truncated["displayTruncated"] is True


@pytest.mark.parametrize(
    "src",
    ["../secret.png", "folder/file.png", r"folder\\file.png", "https://example.test/a.png", "data:image/png;base64,x", "file:///tmp/a.png", "C:private.png"],
)
def test_unsafe_media_never_emits_filename(src):
    card = FakeCard(reviewer_html=f'A<img src="{src}">B')
    result = identity.project_card_display_identity(card, formatter(imageMode="filename")).to_wire()
    assert result["displayText"] == "AB"
    assert src not in result["displayText"]


def test_empty_or_invalid_configured_result_reuses_renders_for_canonical_fallback():
    card = FakeCard(browser_html="Browser", reviewer_html="[sound:voice.mp3]")
    result = identity.project_card_display_identity(
        card, formatter(textMode="omit", audioMode="omit")
    ).to_wire()
    assert result["displayText"] == "Browser"
    assert result["displaySource"] == "browser_question"
    assert card.question_calls == [(True, False), (True, True)]

    browser = FakeCard(browser_html="Browser")
    result = identity.project_card_display_identity(
        browser, formatter(inputSource="browser_question", textMode="omit", imageMode="omit")
    ).to_wire()
    assert result["displayText"] == "Browser"
    assert browser.question_calls == [(True, True)]


def test_malformed_blocked_html_falls_back_and_never_reads_files(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("file read")))
    card = FakeCard(browser_html="Safe", reviewer_html="<script>never closed")
    result = identity.project_card_display_identity(card, formatter()).to_wire()
    assert result["displayText"] == "Safe"
    assert card.answer_calls == 0


def test_self_closing_blocked_and_media_tags_do_not_poison_parser():
    card = FakeCard(
        reviewer_html='<script/><audio src="voice.ogg"/><img src="kanji.png"/>Text'
    )
    result = identity.project_card_display_identity(
        card, formatter(audioMode="stem", imageMode="stem")
    ).to_wire()
    assert result["displayText"] == "voicekanjiText"
    assert result["displayStatus"] == "available"
