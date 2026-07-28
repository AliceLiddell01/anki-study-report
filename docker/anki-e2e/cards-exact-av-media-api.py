#!/usr/bin/env python3
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


class MediaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        src = values.get("src")
        if src and tag.lower() in {"img", "audio", "source", "video"}:
            self.sources.append((tag.lower(), media_name(src)))


class ClassTokenCounter(HTMLParser):
    def __init__(self, token: str) -> None:
        super().__init__(convert_charrefs=True)
        self.token = token
        self.count = 0

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.lower() != "class" or value is None:
                continue
            if self.token in value.split():
                self.count += 1


def count_class_token(html: str, token: str) -> int:
    parser = ClassTokenCounter(token)
    parser.feed(html)
    parser.close()
    return parser.count


def media_name(src: str) -> str:
    parsed = urlparse(src)
    query = parse_qs(parsed.query)
    if query.get("name"):
        return str(query["name"][0])
    return unquote(Path(parsed.path).name)


def extract_media(html: str) -> list[dict[str, str]]:
    parser = MediaParser()
    parser.feed(html)
    return [{"tag": tag, "name": name} for tag, name in parser.sources if name]


def fetch_bytes(base: str, path: str, token: str, params: dict[str, str] | None = None) -> tuple[int, str, bytes]:
    query = {"token": token}
    if params:
        query.update(params)
    request = Request(
        f"{base}{path}?{urlencode(query)}",
        headers={"User-Agent": "anki-study-report-cards-exact-e2e"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def fetch_json(base: str, path: str, token: str) -> dict[str, Any]:
    status, _content_type, body = fetch_bytes(base, path, token)
    if status != 200:
        raise AssertionError(f"{path} HTTP {status}")
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} did not return an object")
    return value


def post_json(base: str, path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{base}{path}?{urlencode({'token': token})}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "anki-study-report-cards-exact-e2e"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read()
    except HTTPError as error:
        status = error.code
        body = error.read()
    decoded = json.loads(body.decode("utf-8"))
    if status != 200 or decoded.get("ok") is not True or not isinstance(decoded.get("response"), dict):
        raise AssertionError(f"{path} HTTP {status}: {decoded}")
    return decoded["response"]


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact Cards AV/media API checks.")
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    card_id = required_env("ANKI_E2E_EXACT_CARD_ID")
    gif_name = required_env("ANKI_E2E_EXACT_GIF_NAME")
    mp3_name = required_env("ANKI_E2E_EXACT_MP3_NAME")
    png_name = required_env("ANKI_E2E_EXACT_PNG_NAME")
    expected_media = {
        gif_name: ("image/gif", required_env("ANKI_E2E_EXACT_GIF_SHA256")),
        mp3_name: ("audio/mpeg", required_env("ANKI_E2E_EXACT_MP3_SHA256")),
        png_name: ("image/png", required_env("ANKI_E2E_EXACT_PNG_SHA256")),
    }

    ready = json.loads(args.ready.read_text(encoding="utf-8"))
    base = str(ready["baseUrl"])
    token = str(ready["token"])

    health = fetch_json(base, "/api/health", token)
    if health.get("ok") is not True or health.get("mode") != "e2e":
        raise AssertionError("health contract failed")

    inspect = post_json(
        base,
        "/api/search/inspect",
        token,
        {
            "schemaVersion": 2,
            "mode": "cards",
            "cardId": card_id,
            "requestId": "cards-exact-av-media",
        },
    )
    details = inspect.get("details")
    if not isinstance(details, dict) or str(details.get("cardId")) != card_id:
        raise AssertionError("exact inspect returned the wrong card")
    rendered = details.get("renderedPreview")
    if not isinstance(rendered, dict) or rendered.get("renderSource") != "anki_native":
        raise AssertionError("exact card did not use native Anki rendering")
    if rendered.get("renderStatus") not in {"available", "sanitized"}:
        raise AssertionError("exact render is unavailable")

    front = str(rendered.get("frontHtml") or "")
    back = str(rendered.get("backHtml") or "")
    css = str(rendered.get("css") or "")
    combined = "\n".join((front, back, css))
    if "[sound:" in combined.lower() or "[anki:play:" in combined.lower():
        raise AssertionError("raw AV marker leaked to production preview")

    front_media = extract_media(front)
    back_media = extract_media(back)
    front_names = {item["name"] for item in front_media}
    back_names = {item["name"] for item in back_media}
    if gif_name not in front_names or mp3_name not in front_names:
        raise AssertionError(f"front side media mismatch: {front_media}")
    if png_name in front_names:
        raise AssertionError(f"answer-only PNG leaked into front side: {front_media}")
    if gif_name not in back_names or png_name not in back_names:
        raise AssertionError(f"back side media mismatch: {back_media}")

    media_refs = rendered.get("mediaRefs")
    if not isinstance(media_refs, list):
        raise AssertionError("mediaRefs are missing")
    safe_refs = sorted(
        {
            (str(item.get("name")), str(item.get("type")))
            for item in media_refs
            if isinstance(item, dict) and item.get("name")
        }
    )
    names = {name for name, _kind in safe_refs}
    if not set(expected_media).issubset(names):
        raise AssertionError(f"exact media refs are incomplete: {safe_refs}")

    triage = post_json(
        base,
        "/api/triage/query",
        token,
        {
            "schemaVersion": 4,
            "dataset": "automatic",
            "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
            "limit": 100,
            "contentCursor": None,
        },
    )
    items = [item for item in triage.get("items", []) if isinstance(item, dict)]
    exact_item = next((item for item in items if str(item.get("cardId")) == card_id), None)
    if exact_item is None:
        raise AssertionError("exact card is absent from automatic triage")
    reason_ids = [
        str(reason.get("reasonId"))
        for reason in exact_item.get("reasons", [])
        if isinstance(reason, dict) and reason.get("reasonId")
    ]
    if not any(reason.startswith("learning:") for reason in reason_ids):
        raise AssertionError("exact card has no learning reason")

    media_report: dict[str, Any] = {}
    for name, (expected_type, expected_sha) in expected_media.items():
        status, content_type, body = fetch_bytes(base, "/api/media", token, {"name": name})
        actual_sha = hashlib.sha256(body).hexdigest()
        if status != 200 or not body:
            raise AssertionError(f"media HTTP failed: {name} {status}")
        if expected_type not in content_type.lower():
            raise AssertionError(f"media type mismatch: {name} {content_type}")
        if actual_sha != expected_sha:
            raise AssertionError(f"media SHA mismatch: {name} expected={expected_sha} actual={actual_sha}")
        media_report[name] = {
            "status": status,
            "contentType": content_type,
            "sizeBytes": len(body),
            "sha256": actual_sha,
        }

    unsafe = {}
    for name in ("../secret.txt", "file:///secret.gif", "C:\\secret\\x.gif", "/etc/passwd"):
        status, content_type, body = fetch_bytes(base, "/api/media", token, {"name": name})
        if status not in {400, 404}:
            raise AssertionError(f"unsafe media path accepted: {name} HTTP {status}")
        unsafe[name] = {"status": status, "contentType": content_type, "sizeBytes": len(body)}

    front_replay_wrappers = count_class_token(front, "asr-card-replay")
    front_replay_buttons = count_class_token(front, "asr-card-replay-button")
    front_audio_elements = count(front, r"<audio\b")
    if (front_replay_wrappers, front_replay_buttons, front_audio_elements) != (1, 1, 1):
        raise AssertionError(
            "front replay structure mismatch: "
            f"wrapper={front_replay_wrappers} button={front_replay_buttons} audio={front_audio_elements}"
        )

    output = {
        "schemaVersion": 1,
        "status": "PASS",
        "baseOrigin": base,
        "cardId": int(card_id),
        "noteId": details.get("noteId"),
        "deckId": details.get("deckId"),
        "noteTypeId": details.get("noteTypeId"),
        "noteTypeName": details.get("noteTypeName"),
        "templateName": details.get("templateName"),
        "displayText": details.get("displayText"),
        "renderedPreview": {
            "renderSource": rendered.get("renderSource"),
            "renderStatus": rendered.get("renderStatus"),
            "frontHtmlSha256": hashlib.sha256(front.encode()).hexdigest(),
            "backHtmlSha256": hashlib.sha256(back.encode()).hexdigest(),
            "cssSha256": hashlib.sha256(css.encode()).hexdigest(),
            "frontHtmlLength": len(front),
            "backHtmlLength": len(back),
            "cssLength": len(css),
            "questionAvTagCount": 1,
            "frontReplayWrapperCount": front_replay_wrappers,
            "frontReplayButtonCount": front_replay_buttons,
            "frontAudioElementCount": front_audio_elements,
            "frontMedia": front_media,
            "backMedia": back_media,
            "mediaRefs": [{"name": name, "type": kind} for name, kind in safe_refs],
        },
        "triage": {
            "status": triage.get("status"),
            "itemId": exact_item.get("itemId"),
            "priority": exact_item.get("priority"),
            "reasonIds": reason_ids,
        },
        "media": media_report,
        "unsafeMedia": unsafe,
        "inspectionProfilesRequests": 0,
    }

    serialized = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if token in serialized or "token=" in serialized or "?token" in serialized:
        raise AssertionError("token leaked into exact API report")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(
        f"[cards-exact] API PASS card={card_id} media={len(media_report)} triageReasons={len(reason_ids)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
