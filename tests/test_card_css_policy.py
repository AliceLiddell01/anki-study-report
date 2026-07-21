from __future__ import annotations

import pytest

from conftest import fresh_import_addon_module


@pytest.mark.parametrize(
    "stylesheet",
    [
        '.card { background: url("https://evil.invalid/beacon") }',
        ".card { background: url( https://evil.invalid/beacon ) }",
        ".card { background: url(//evil.invalid/beacon) }",
        ".card { background: URL(HTTPS://evil.invalid/beacon) }",
        r".card { background: u\72l(https://evil.invalid/beacon) }",
        '.card { background: image-set(url("https://evil.invalid/a") 1x) }',
        '.card { --leak: url("https://evil.invalid/a"); background: var(--leak) }',
        '@import url("https://evil.invalid/import.css"); .card { color: red }',
        '@font-face { font-family: leak; src: url("https://evil.invalid/font"); unicode-range: U+0410; }',
        ":host { position: fixed; inset: 0; z-index: 2147483647 }",
        ":host-context(body) .card { pointer-events: auto }",
        r":\68ost { color: red }",
        r":is(:\68ost-context(body), .card) { color: red }",
        ".card { position: sticky; width: 100vw; height: 100vh; z-index: 999; pointer-events: none }",
    ],
)
def test_card_css_policy_blocks_external_loads_and_host_or_viewport_control(stylesheet):
    note_intelligence = fresh_import_addon_module("note_intelligence")

    sanitized = note_intelligence.sanitize_card_css(stylesheet)
    lowered = sanitized.lower()

    assert "evil.invalid" not in lowered
    assert "@import" not in lowered
    assert ":host" not in lowered
    assert "position:fixed" not in lowered.replace(" ", "")
    assert "position:sticky" not in lowered.replace(" ", "")
    assert "100vw" not in lowered
    assert "100vh" not in lowered
    assert "z-index" not in lowered
    assert "pointer-events" not in lowered
    assert "image-set" not in lowered
    assert "unicode-range" not in lowered


def test_card_css_policy_scopes_safe_visual_rules_and_rewrites_local_media():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    stylesheet = """
        .card, .card1 .term {
          color: rgb(20 30 40);
          background: #fff url("safe image.png") center / contain no-repeat;
          margin: 1rem;
          padding: 12px;
          border: 1px solid #ddd;
          display: grid;
          grid-template-columns: 1fr 2fr;
          text-align: center;
        }
        @media (max-width: 700px) {
          .term { font-size: 1.2rem; }
        }
    """

    sanitized = note_intelligence.sanitize_card_css(stylesheet)

    assert sanitized.startswith("@scope (.card)")
    assert "color:rgb(203040)" in sanitized.replace(" ", "")
    assert "/api/media?name=safe%20image.png" in sanitized
    assert "grid-template-columns" in sanitized
    assert "@media" in sanitized


def test_card_css_policy_allows_only_safe_local_font_faces():
    note_intelligence = fresh_import_addon_module("note_intelligence")

    sanitized = note_intelligence.sanitize_card_css(
        '@font-face { font-family: "Study Font"; src: url("study.woff2") format("woff2"); '
        "font-style: normal; font-weight: 400; } .card { font-family: \"Study Font\", sans-serif; }"
    )

    assert '@font-face' in sanitized
    assert "/api/media?name=study.woff2" in sanitized
    assert "unicode-range" not in sanitized
    assert "@scope (.card)" in sanitized


@pytest.mark.parametrize(
    "stylesheet",
    [
        ".card { color: red",
        ".card { color: red; } }",
        "/* unterminated",
        "@media screen { .card { color: red }",
    ],
)
def test_card_css_policy_fails_closed_on_malformed_stylesheets(stylesheet):
    note_intelligence = fresh_import_addon_module("note_intelligence")
    assert note_intelligence.sanitize_card_css(stylesheet) == ""


def test_card_css_policy_has_bounded_input_and_output():
    note_intelligence = fresh_import_addon_module("note_intelligence")

    assert note_intelligence.sanitize_card_css(".card{color:red}" * 2000) == ""
    sanitized = note_intelligence.sanitize_card_css(
        "".join(f".term-{index}{{color:rgb({index % 255} 0 0)}}" for index in range(300))
    )

    assert len(sanitized) <= 4000


def test_card_css_policy_is_idempotent_across_preview_and_payload_boundaries():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    original = '.term { color: rebeccapurple; background-image: url("safe.png"); }'

    first = note_intelligence.sanitize_card_css(original)
    second = note_intelligence.sanitize_card_css(first)

    assert first
    assert second == first


def test_card_css_policy_does_not_expose_raw_stylesheet_on_parser_failure(monkeypatch, capsys):
    policy = fresh_import_addon_module("card_css_policy")
    secret = "private-card-css-token"
    monkeypatch.setattr(
        policy.tinycss2,
        "parse_stylesheet",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    assert policy.sanitize_card_stylesheet(f".card{{color:red}}/*{secret}*/") == ""
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
