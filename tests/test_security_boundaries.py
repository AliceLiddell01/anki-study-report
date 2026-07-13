from __future__ import annotations

import pytest

from conftest import fresh_import_addon_module, import_addon_module


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../front.gif",
        "nested/front.gif",
        "nested\\front.gif",
        "/tmp/front.gif",
        "C:/tmp/front.gif",
        "C:\\tmp\\front.gif",
        "C:front.gif",
        "\\\\server\\share\\front.gif",
        "front.gif\x00.txt",
    ],
)
def test_safe_leaf_name_rejects_paths_and_invalid_components(value):
    path_safety = import_addon_module("path_safety")
    assert path_safety.safe_leaf_name(value) is None


def test_safe_leaf_name_preserves_unicode_media_filename():
    path_safety = import_addon_module("path_safety")
    assert path_safety.safe_leaf_name("要望.mp3") == "要望.mp3"


def test_trusted_file_inventory_selects_only_files_below_root(tmp_path):
    path_safety = import_addon_module("path_safety")
    root = tmp_path / "dashboard"
    asset = root / "assets" / "nested" / "app.js"
    asset.parent.mkdir(parents=True)
    asset.write_text("safe", encoding="utf-8")
    index = root / "index.html"
    index.write_text("index", encoding="utf-8")
    sibling = tmp_path / "dashboard-secret" / "secret.txt"
    sibling.parent.mkdir()
    sibling.write_text("secret", encoding="utf-8")

    assert path_safety.trusted_file_from_inventory(root, "assets/nested/app.js") == asset.resolve()
    assert path_safety.trusted_file_from_inventory(root, "index.html") == index.resolve()
    for candidate in (
        "../dashboard-secret/secret.txt",
        "assets/../../dashboard-secret/secret.txt",
        "/etc/passwd",
        "C:/Windows/win.ini",
        "C:win.ini",
        "\\\\server/share/file",
        "assets\\nested\\app.js",
        "assets//app.js",
        "assets/./app.js",
        "assets/app.js\x00.txt",
        "",
    ):
        assert path_safety.trusted_file_from_inventory(root, candidate) is None


def test_trusted_file_inventory_rejects_symlink_escape(tmp_path):
    path_safety = import_addon_module("path_safety")
    root = tmp_path / "dashboard"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "outside.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable in this environment")
    assert path_safety.trusted_file_from_inventory(root, "outside.txt") is None


def test_static_target_uses_inventory_and_keeps_spa_fallback_bounded(tmp_path):
    dashboard_server = import_addon_module("dashboard_server")
    root = tmp_path / "dashboard"
    asset = root / "assets" / "app.js"
    asset.parent.mkdir(parents=True)
    asset.write_text("safe", encoding="utf-8")
    index = root / "index.html"
    index.write_text("index", encoding="utf-8")

    assert dashboard_server._safe_static_target(root, "/assets/app.js") == asset.resolve()
    assert dashboard_server._safe_static_target(root, "/profile") == index.resolve()
    assert dashboard_server._safe_static_target(root, "/assets/missing.js") is None
    for path in (
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/C:/Windows/win.ini",
        "/\\server\\share\\file",
        "/assets/app.js\x00.txt",
        "/api/report",
    ):
        assert dashboard_server._safe_static_target(root, path) is None


def test_rendered_html_parser_blocks_active_and_obfuscated_markup():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    payload = (
        '<ScRiPt type="text/javascript">alert(1)</sCrIpT>'
        '<style>@import url(https://evil.invalid/x)</style>'
        '<iframe srcdoc="<script>alert(2)</script>"><b>hidden</b></iframe>'
        '<svg><script>alert(3)</script><a href="javascript:alert(4)">x</a></svg>'
        '<math><annotation-xml encoding="text/html"><img src=x onerror=alert(5)></annotation-xml></math>'
        '<img src="safe.gif" ONERROR="alert(6)" srcset="evil.gif 2x">'
        '<a href="&#x6a;avascript:alert(7)">bad</a>'
        '<a href="vbscript:alert(8)">bad2</a>'
        '<img src="data:text/html;base64,evil">'
        '<span style="color:red;background-image:url(javascript:alert(9));width:expression(alert(10));position:absolute">safe</span>'
        '<!-- <script>alert(11)</script> -->'
    )

    html, refs = note_intelligence.sanitize_rendered_html(payload)
    lowered = html.lower()
    for forbidden in (
        "<script", "<style", "<iframe", "<svg", "<math", "onerror", "srcset",
        "javascript:", "vbscript:", "data:", "expression(", "url(", "position",
    ):
        assert forbidden not in lowered
    assert '<img src="/api/media?name=safe.gif">' in html
    assert '<span style="color: red">safe</span>' in html
    assert refs == [{"name": "safe.gif", "type": "image", "url": "/api/media?name=safe.gif"}]


def test_rendered_html_parser_preserves_legitimate_anki_formatting_and_media():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    source = (
        '[sound:要望.mp3]<div class="card"><ruby>要<rt>よう</rt></ruby>'
        '<span style="color: rgb(170, 170, 127); font-weight: 700">望</span>'
        '<br><img src="要.gif" alt="stroke"></div>'
    )

    html, refs = note_intelligence.sanitize_rendered_html(source)
    assert '<div class="card">' in html
    assert '<ruby>要<rt>よう</rt></ruby>' in html
    assert 'style="color: rgb(170, 170, 127); font-weight: 700"' in html
    assert '<img src="/api/media?name=%E8%A6%81.gif" alt="stroke">' in html
    assert 'class="asr-card-replay-button"' in html
    assert 'class="asr-card-audio"' in html
    assert refs == [
        {"name": "要.gif", "type": "image", "url": "/api/media?name=%E8%A6%81.gif"},
        {"name": "要望.mp3", "type": "audio", "url": "/api/media?name=%E8%A6%81%E6%9C%9B.mp3"},
    ]


def test_rendered_html_sanitization_is_stable_and_bounded():
    note_intelligence = fresh_import_addon_module("note_intelligence")
    source = '<div class="x">' + ("word " * 5000) + '</div><img src="x.gif">'
    first_html, first_refs = note_intelligence.sanitize_rendered_html(source)
    second_html, second_refs = note_intelligence.sanitize_rendered_html(first_html)

    assert len(first_html) <= 6000
    assert first_html == second_html
    assert first_refs == second_refs
