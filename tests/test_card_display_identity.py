from __future__ import annotations

import builtins

import pytest

from conftest import import_addon_module


identity = import_addon_module("card_display_identity")


class FakeCard:
    def __init__(
        self,
        *,
        browser_html: str = "",
        reviewer_html: str = "",
        browser_error: Exception | None = None,
        reviewer_error: Exception | None = None,
    ) -> None:
        self.browser_html = browser_html
        self.reviewer_html = reviewer_html
        self.browser_error = browser_error
        self.reviewer_error = reviewer_error
        self.question_calls: list[tuple[bool, bool]] = []
        self.answer_calls = 0

    def question(self, reload: bool = False, browser: bool = False) -> str:
        self.question_calls.append((reload, browser))
        error = self.browser_error if browser else self.reviewer_error
        if error is not None:
            raise error
        return self.browser_html if browser else self.reviewer_html

    def answer(self) -> str:
        self.answer_calls += 1
        raise AssertionError("compact identity must not render the answer")


def wire(card: FakeCard) -> dict[str, object]:
    return identity.project_card_display_identity(card).to_wire()


def test_browser_question_is_preferred_over_reviewer_front():
    card = FakeCard(browser_html="<b>Browser label</b>", reviewer_html="Reviewer label")
    assert wire(card) == {
        "displayText": "Browser label",
        "displaySource": "browser_question",
        "displayStatus": "available",
        "displayTruncated": False,
    }
    assert card.question_calls == [(True, True)]
    assert card.answer_calls == 0


@pytest.mark.parametrize("browser_html", ["", "  \n ", '<img src="front.png">', "[sound:front.mp3]"])
def test_empty_or_media_only_browser_question_falls_back_to_reviewer_front(browser_html):
    card = FakeCard(browser_html=browser_html, reviewer_html="<span>Reviewer front</span>")
    assert wire(card) == {
        "displayText": "Reviewer front",
        "displaySource": "reviewer_front",
        "displayStatus": "available",
        "displayTruncated": False,
    }
    assert card.question_calls == [(True, True), (True, False)]


def test_browser_render_failure_falls_back_without_exposing_exception():
    card = FakeCard(browser_error=RuntimeError("private path token=secret"), reviewer_html="Safe front")
    assert wire(card)["displayText"] == "Safe front"
    assert "private" not in repr(wire(FakeCard(reviewer_html="Safe front")))


def test_reviewer_media_only_and_unavailable_are_distinct():
    media = wire(FakeCard(reviewer_html='<img src="private-file.png">[sound:private.mp3]'))
    unavailable = wire(FakeCard(reviewer_error=RuntimeError("private")))
    assert media == {
        "displayText": "",
        "displaySource": "reviewer_front",
        "displayStatus": "media_only",
        "displayTruncated": False,
    }
    assert unavailable == {
        "displayText": "",
        "displaySource": "none",
        "displayStatus": "unavailable",
        "displayTruncated": False,
    }
    assert "private-file.png" not in repr(media)


def test_browser_media_is_retained_only_when_reviewer_has_no_identity():
    result = wire(FakeCard(browser_html='<img src="x.png">', reviewer_html=""))
    assert result["displaySource"] == "browser_question"
    assert result["displayStatus"] == "media_only"


def test_first_meaningful_line_wins_and_inline_japanese_nodes_stay_adjacent():
    projected = identity.project_compact_html(
        "<br><div>  </div>【<span><b>に</b></span>】"
        '<img src="感.gif"><img src="謝.gif">（<span><b>する</b></span>）'
        "<br>Ignored second line"
    )
    assert projected.text == "【に】（する）"
    assert projected.media_found is True
    assert projected.truncated is False


def test_exact_user_fixture_never_exposes_unrelated_note_field():
    unrelated_sort_field = "「Существительное」"
    card = FakeCard(
        reviewer_html=(
            "[sound:感謝.mp3]<br>"
            '【<span style="color: rgb(170, 170, 127);"><b>に</b></span>】'
            '<img src="感.gif"><img src="謝.gif">'
            '（<span style="color: rgb(255, 165, 0);"><b>する</b></span>）'
            '<br><br>（先生に<span class="word-focus">感謝<b>する</b></span>。）'
        )
    )
    result = wire(card)
    assert result["displayText"] == "【に】（する）"
    assert result["displayText"] != unrelated_sort_field


def test_scripts_styles_and_unsafe_embedded_content_are_dropped_with_contents():
    projected = identity.project_compact_html(
        "<script>secret()</script><style>.secret{}</style>"
        "<iframe>private</iframe><object>hidden</object><template>draft</template>Visible"
    )
    assert projected.text == "Visible"


def test_audio_markers_are_removed_and_mark_media():
    for value in ("[sound:private.mp3]", "[anki:play:q:0]"):
        projected = identity.project_compact_html(value)
        assert projected.text == ""
        assert projected.media_found is True


def test_html_entities_are_decoded_and_whitespace_collapsed_per_line():
    projected = identity.project_compact_html("&lbrack; A&nbsp;&amp; B &rbrack;")
    assert projected.text == "[ A & B ]"


def test_truncation_is_exact_and_adds_one_ellipsis():
    exact = identity.project_compact_html("a" * identity.MAX_DISPLAY_TEXT_LENGTH)
    truncated = identity.project_compact_html("a" * (identity.MAX_DISPLAY_TEXT_LENGTH + 50))
    assert len(exact.text) == identity.MAX_DISPLAY_TEXT_LENGTH
    assert exact.truncated is False
    assert len(truncated.text) == identity.MAX_DISPLAY_TEXT_LENGTH
    assert truncated.text.endswith("…")
    assert not truncated.text.endswith("……")
    assert truncated.truncated is True


def test_malformed_blocked_html_fails_closed():
    projected = identity.project_compact_html("<script>never closed")
    assert projected.valid is False
    assert projected.text == ""
    assert wire(FakeCard(reviewer_html="<script>never closed"))["displayStatus"] == "unavailable"


def test_projector_does_not_read_media_files_or_render_answer(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("media read")))
    card = FakeCard(reviewer_html='<img src="private.png">')
    assert wire(card)["displayStatus"] == "media_only"
    assert card.answer_calls == 0
