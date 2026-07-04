#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API smoke checks against Anki Study Report dashboard.")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    artifacts = Path(os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS", "/e2e/artifacts"))
    ready_file = Path(os.environ.get("ANKI_STUDY_REPORT_E2E_READY_FILE", str(artifacts / "dashboard-ready.json")))
    ready = json.loads(ready_file.read_text(encoding="utf-8"))
    base_url = ready["baseUrl"]
    token = ready["token"]

    health = fetch_json(base_url, "/api/health", token)
    assert_true(health.get("ok") is True, "health ok")
    assert_true(health.get("mode") == "e2e", "health reports e2e mode")
    assert_true(health.get("profile") == "E2E", "health reports E2E profile")

    report = fetch_json(base_url, "/api/report", token)
    assert_true(isinstance(report, dict), "report is an object")
    assert_true("token=" not in json.dumps(report, ensure_ascii=False), "token is absent from report payload")

    cards = report_cards(report)
    assert_true(cards, "report contains card-level payload")
    fixture_card = find_fixture_card(cards)
    assert_true(fixture_card is not None, "fixture card with 要望 found")
    assert_fixture_preview(fixture_card or {})

    for media_name in ("要.gif", "望.gif", "要望.mp3"):
        status, content_type, body = fetch_bytes(base_url, "/api/media", token, {"name": media_name})
        assert_true(status == 200, f"{media_name} media returned 200")
        assert_true(len(body) > 0, f"{media_name} media body is non-empty")
        assert_true(content_type, f"{media_name} content type present")

    for unsafe_name in ("../secret.txt", "file:///secret.gif", "C:\\secret\\x.gif"):
        status, _content_type, _body = fetch_bytes(base_url, "/api/media", token, {"name": unsafe_name})
        assert_true(status in {400, 404}, f"unsafe media rejected: {unsafe_name}")

    (artifacts / f"api-report-sample-{args.label}.json").write_text(
        json.dumps(redact(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifacts / f"api-smoke-{args.label}.json").write_text(
        json.dumps(
            {
                "ok": True,
                "cardCount": len(cards),
                "fixtureCardId": fixture_card.get("cardId") if isinstance(fixture_card, dict) else None,
                "fixtureRenderSource": (
                    fixture_card.get("renderedPreview", {}).get("renderSource")
                    if isinstance(fixture_card.get("renderedPreview"), dict)
                    else None
                ) if isinstance(fixture_card, dict) else None,
                "checkedMedia": ["要.gif", "望.gif", "要望.mp3"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"API smoke passed for {base_url}")
    return 0


def fetch_json(base_url: str, path: str, token: str) -> dict:
    status, _content_type, body = fetch_bytes(base_url, path, token)
    if status != 200:
        raise AssertionError(f"{path} returned HTTP {status}: {body[:200]!r}")
    return json.loads(body.decode("utf-8"))


def fetch_bytes(base_url: str, path: str, token: str, params: dict[str, str] | None = None) -> tuple[int, str, bytes]:
    query = {"token": token}
    if params:
        query.update(params)
    request = Request(
        f"{base_url}{path}?{urlencode(query)}",
        headers={"User-Agent": "anki-study-report-e2e"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def report_cards(report: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("cards", "attentionCards", "cardIssues", "problemCards"):
        value = report.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def find_fixture_card(cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    for card in cards:
        if "要望" in json.dumps(card, ensure_ascii=False):
            return card
    return None


def assert_fixture_preview(card: dict[str, Any]) -> None:
    rendered = card.get("renderedPreview")
    assert_true(isinstance(rendered, dict), "fixture card has renderedPreview")
    rendered = rendered if isinstance(rendered, dict) else {}
    front_html = str(rendered.get("frontHtml") or "")
    back_html = str(rendered.get("backHtml") or "")
    front_plain = str(rendered.get("frontPlainText") or "")
    back_plain = str(rendered.get("backPlainText") or "")
    rendered_dump = json.dumps(rendered, ensure_ascii=False)
    assert_true(rendered.get("renderStatus") in {"available", "sanitized", "fallback"}, "renderStatus marker present")
    assert_true(rendered.get("renderSource") == "anki_native", "fixture card used native Anki render")
    assert_true(not rendered.get("fallbackReason"), "native fixture has no fallback reason")
    for label, value in (
        ("frontHtml", front_html),
        ("backHtml", back_html),
        ("frontPlainText", front_plain),
        ("backPlainText", back_plain),
    ):
        assert_true("[anki:play:" not in value, f"{label} has no raw Anki AV marker")
        assert_true("[sound:" not in value.lower(), f"{label} has no raw sound marker")
    assert_true("要望" in rendered_dump, "rendered preview contains 要望")
    assert_true("word-focus" in front_html, "word-focus class preserved")
    assert_true("rgb(255, 165, 0)" in front_html or "orange" in front_html.lower(), "inline color style preserved")
    assert_true("asr-card-replay-button" in front_html, "replay button present in frontHtml")
    assert_true("asr-card-audio" in front_html and "<audio" in front_html.lower(), "hidden audio element present in frontHtml")
    assert_true("<audio" not in front_html.lower() or " controls" not in front_html.lower(), "native audio controls are not visible in frontHtml")
    assert_true(front_html.find("asr-card-replay-button") < front_html.find("word-focus"), "replay button keeps native marker placement")
    assert_true("要.gif" in rendered_dump or "%E8%A6%81.gif" in rendered_dump, "要.gif reference present")
    assert_true("望.gif" in rendered_dump or "%E6%9C%9B.gif" in rendered_dump, "望.gif reference present")
    assert_true("要望.mp3" in rendered_dump or "%E8%A6%81%E6%9C%9B.mp3" in rendered_dump, "audio reference present")
    media_names = {
        str(item.get("name") or "")
        for item in rendered.get("mediaRefs", [])
        if isinstance(item, dict)
    }
    assert_true({"要.gif", "望.gif", "要望.mp3"}.issubset(media_names), "fixture mediaRefs contain images and audio")
    assert_true("<script" not in front_html.lower(), "scripts stripped from preview")
    assert_true("file://" not in front_html.lower(), "file URLs stripped from preview")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("token=", "token=<redacted>")
    return value


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
