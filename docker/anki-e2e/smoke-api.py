#!/usr/bin/env python3
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from artifact_paths import ArtifactPaths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API smoke checks against Anki Study Report dashboard.")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    paths = ArtifactPaths.from_env()
    paths.ensure()
    artifacts = paths.reports
    ready_file = Path(os.environ.get("ANKI_STUDY_REPORT_E2E_READY_FILE", str(paths.runtime / "dashboard-ready.json")))
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
    asset_summary = assert_dashboard_assets(base_url, token, artifacts, args.label)
    notification_summary = None
    if os.environ.get("ANKI_E2E_SCOPE", "full") in {"full", "notifications"}:
        notification_summary = assert_notification_contract(base_url, token, artifacts, args.label)
    inspection_profiles_summary = None
    if os.environ.get("ANKI_E2E_SCOPE", "full") == "cards":
        inspection_profiles_summary = assert_inspection_profiles_contract(
            base_url, token, artifacts, args.label
        )

    cards = report_cards(report)
    assert_true(cards, "No attention cards found in canonical attentionCards.")
    problem_summary = read_json_if_exists(artifacts / "apkg-problematic-summary.json")
    perf100_enabled = bool(problem_summary.get("performanceScenario", {}).get("enabled"))
    fixture_card = find_fixture_card(cards)
    if fixture_card is None:
        assert_true(perf100_enabled, "fixture card with 要望 found")
    else:
        assert_fixture_preview(fixture_card)
    apkg_summary = assert_apkg_report_if_enabled(artifacts, args.label, base_url, token, cards)

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
                "assets": asset_summary,
                "apkg": apkg_summary,
                "notifications": notification_summary,
                "inspectionProfiles": inspection_profiles_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"API smoke passed for {base_url}")
    return 0


def fetch_json(base_url: str, path: str, token: str, params: dict[str, str] | None = None) -> dict:
    status, _content_type, body = fetch_bytes(base_url, path, token, params)
    if status != 200:
        raise AssertionError(f"{path} returned HTTP {status}: {body[:200]!r}")
    return json.loads(body.decode("utf-8"))


def post_json(base_url: str, path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}?{urlencode({'token': token})}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "anki-study-report-e2e"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
            body = response.read()
    except HTTPError as error:
        status = error.code
        body = error.read()
    decoded = json.loads(body.decode("utf-8"))
    if status != 200 or decoded.get("ok") is not True or not isinstance(decoded.get("response"), dict):
        raise AssertionError(f"{path} returned HTTP {status}: {decoded!r}")
    return decoded["response"]


def assert_inspection_profiles_contract(
    base_url: str,
    token: str,
    artifacts: Path,
    label: str,
) -> dict[str, Any]:
    catalog = post_json(
        base_url,
        "/api/inspection-profiles/query",
        token,
        {"schemaVersion": 1, "noteTypeIds": [], "limit": 500},
    )
    items = catalog.get("items") if isinstance(catalog.get("items"), list) else []
    japanese = find_structure(items, "E2E Japanese Vocabulary")
    programming = find_structure(items, "E2E Programming")
    assert_true(japanese is not None, "Japanese Inspection Profile structure is available")
    assert_true(programming is not None, "Programming Inspection Profile structure is available")

    if label == "first":
        revision = int(catalog.get("store", {}).get("revision") or 0)
        assert_true(revision == 0, "Inspection Profile store starts empty")
        for structure, definition in (
            (
                japanese,
                {
                    "displayName": "Japanese vocabulary",
                    "mappings": [("meaning", "Значение"), ("audio", "Аудио")],
                    "checks": [
                        {"checkId": "meaning-required", "kind": "non_empty", "roles": ["meaning"], "mode": "any", "priority": "high"},
                        {"checkId": "audio-required", "kind": "contains_audio", "roles": ["audio"], "mode": "any", "priority": "medium"},
                    ],
                },
            ),
            (
                programming,
                {
                    "displayName": "Programming",
                    "mappings": [("question", "Question"), ("answer", "Answer")],
                    "checks": [
                        {"checkId": "question-required", "kind": "non_empty", "roles": ["question"], "mode": "any", "priority": "high"},
                        {"checkId": "answer-required", "kind": "non_empty", "roles": ["answer"], "mode": "any", "priority": "high"},
                    ],
                },
            ),
        ):
            profile = confirmed_profile(structure, definition)
            updated = post_json(
                base_url,
                "/api/inspection-profiles/update",
                token,
                {
                    "schemaVersion": 1,
                    "action": "save",
                    "expectedRevision": revision,
                    "targetState": "confirmed",
                    "profile": profile,
                },
            )
            revision = int(updated.get("store", {}).get("revision") or 0)
        assert_true(revision == 2, "two confirmed profiles increment the store revision")
        catalog = post_json(
            base_url,
            "/api/inspection-profiles/query",
            token,
            {"schemaVersion": 1, "noteTypeIds": [], "limit": 500},
        )
        items = catalog.get("items") if isinstance(catalog.get("items"), list) else []
        japanese = find_structure(items, "E2E Japanese Vocabulary")
        programming = find_structure(items, "E2E Programming")

    assert_true(japanese is not None and programming is not None, "Inspection Profile catalog remains complete")
    expected_japanese_state = "confirmed" if label == "first" else "needs_review"
    assert_true(japanese.get("effectiveState") == expected_japanese_state, f"Japanese profile state is {expected_japanese_state}")
    assert_true(programming.get("effectiveState") == "confirmed", "Programming profile remains confirmed")
    assert_true(int(catalog.get("store", {}).get("revision") or 0) == 2, "Inspection Profile store revision survives restart")

    programming_preview = post_json(
        base_url,
        "/api/inspection-profiles/validate",
        token,
        {
            "schemaVersion": 2,
            "profile": programming["storedProfile"],
            "preview": {"mode": "sample", "limit": 10},
        },
    )
    assert_true(programming_preview.get("schemaVersion") == 2, "Inspection Profile sample preview v2 is active")
    assert_true(programming_preview.get("valid") is True, "current Programming profile validates")
    assert_true(programming_preview.get("preview", {}).get("evaluatedCount", 0) > 0, "sample preview evaluates bounded live cards")
    assert_true("rawFields" not in json.dumps(programming_preview, ensure_ascii=False), "sample preview excludes raw note values")

    japanese_cards = search_note_type_cards(base_url, token, japanese["structure"]["noteTypeId"], "japanese")
    programming_cards = search_note_type_cards(base_url, token, programming["structure"]["noteTypeId"], "programming")
    card_ids = [item["cardId"] for item in japanese_cards + programming_cards]
    triage = post_json(
        base_url,
        "/api/triage/query",
        token,
        {
            "schemaVersion": 4,
            "dataset": "search_workset",
            "cardIds": card_ids,
            "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
            "limit": min(200, max(1, len(card_ids))),
        },
    )
    assert_true(triage.get("schemaVersion") == 4, "canonical triage v4 is active")
    triage_items = triage.get("items") if isinstance(triage.get("items"), list) else []
    japanese_id = japanese["structure"]["noteTypeId"]
    programming_id = programming["structure"]["noteTypeId"]
    japanese_reasons = reasons_for_note_type(triage_items, japanese_id)
    programming_reasons = reasons_for_note_type(triage_items, programming_id)
    japanese_audio = [reason for reason in japanese_reasons if reason.get("code") == "content.audio_missing"]
    programming_audio = [reason for reason in programming_reasons if reason.get("code") == "content.audio_missing"]
    if label == "first":
        assert_true(len(japanese_audio) == 1, "missing audio is emitted once for the configured Japanese note")
        assert_true(triage.get("contentChecks", {}).get("status") == "available", "profile checks are available")
    else:
        assert_true(not japanese_audio, "stale Japanese profile fails closed after structure change")
        assert_true(triage.get("contentChecks", {}).get("status") in {"partial", "available"}, "mixed profile lifecycle is explicit")
    assert_true(not programming_audio, "Programming profile never receives an audio requirement")
    assert_true(
        any(str(reason.get("code") or "").startswith("learning.") for reason in japanese_reasons),
        "learning reasons remain independent of profile lifecycle",
    )
    profile_evidence = [
        evidence
        for reason in japanese_reasons + programming_reasons
        for evidence in reason.get("evidence", [])
        if isinstance(evidence, dict) and evidence.get("kind") == "profile_check"
    ]
    encoded_evidence = json.dumps(profile_evidence, ensure_ascii=False)
    assert_true("rawFields" not in encoded_evidence and ".mp3" not in encoded_evidence, "profile evidence excludes values and media filenames")

    proof = {
        "ok": True,
        "label": label,
        "storeRevision": catalog.get("store", {}).get("revision"),
        "japaneseState": japanese.get("effectiveState"),
        "programmingState": programming.get("effectiveState"),
        "japaneseCardCount": len(japanese_cards),
        "programmingCardCount": len(programming_cards),
        "japaneseAudioReasonCount": len(japanese_audio),
        "programmingAudioReasonCount": len(programming_audio),
        "learningReasonPreserved": True,
        "profileEvidenceValueLeak": False,
        "samplePreviewV2": True,
    }
    (artifacts / f"inspection-profiles-{label}.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return proof


def find_structure(items: list[Any], name: str) -> dict[str, Any] | None:
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("structure"), dict) and item["structure"].get("name") == name:
            return item
    return None


def confirmed_profile(item: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any]:
    structure = item["structure"]
    fields = {field["name"]: field for field in structure["fields"]}
    mappings = []
    for role, field_name in definition["mappings"]:
        assert_true(field_name in fields, f"profile field exists: {field_name}")
        mappings.append({"role": role, "fields": [fields[field_name]]})
    now = "2026-07-18T00:00:00Z"
    return {
        "profileId": f"note-type-{structure['noteTypeId']}",
        "noteTypeId": structure["noteTypeId"],
        "noteTypeName": structure["name"],
        "storedState": "confirmed",
        "displayName": definition["displayName"],
        "expectedFingerprint": structure["fingerprint"],
        "appliesTo": {"templateOrdinals": []},
        "fieldMappings": mappings,
        "checks": definition["checks"],
        "confirmedAt": now,
        "updatedAt": now,
    }


def search_note_type_cards(base_url: str, token: str, note_type_id: str, request_id: str) -> list[dict[str, Any]]:
    response = post_json(
        base_url,
        "/api/search/query",
        token,
        {
            "schemaVersion": 2,
            "mode": "cards",
            "query": "",
            "filters": [{"type": "note_type", "noteTypeId": note_type_id}],
            "sort": {"key": "entity_id", "direction": "asc"},
            "page": 1,
            "pageSize": 50,
            "requestId": f"inspection-{request_id}",
        },
    )
    items = response.get("items") if isinstance(response.get("items"), list) else []
    assert_true(items, f"Search returns cards for note type {note_type_id}")
    return [item for item in items if isinstance(item, dict)]


def reasons_for_note_type(items: list[Any], note_type_id: str) -> list[dict[str, Any]]:
    return [
        reason
        for item in items
        if isinstance(item, dict) and item.get("noteType", {}).get("noteTypeId") == note_type_id
        for reason in item.get("reasons", [])
        if isinstance(reason, dict)
    ]


def assert_notification_contract(base_url: str, token: str, artifacts: Path, label: str) -> dict[str, Any]:
    summary = fetch_json(base_url, "/api/notifications/summary", token)
    all_items = fetch_json(
        base_url,
        "/api/notifications",
        token,
        {"page": "1", "pageLimit": "50", "tab": "all", "category": "all"},
    )
    active = fetch_json(
        base_url,
        "/api/notifications",
        token,
        {"page": "1", "pageLimit": "50", "tab": "active", "category": "all"},
    )
    settings = fetch_json(base_url, "/api/settings/notifications", token)
    assert_true(summary.get("schemaVersion") == 1, "notification summary schema is current")
    assert_true(all_items.get("pageLimit") == 50 and all_items.get("total", 0) >= 5, "notification history is bounded and seeded")
    assert_true(active.get("total", 0) >= 1, "active signal tab has fixture data")
    assert_true(any(item.get("signalStatus") == "resolved" for item in all_items.get("items", [])), "resolved signal remains in history")
    assert_true(settings.get("preferences", {}).get("notificationCenterEnabled") is True, "durable notification center remains enabled")

    fixture = read_json_if_exists(artifacts / "notification-fixture-proof.json")
    assert_true(fixture.get("normalEvaluationWasEmpty") is True, "normal notification fixture starts empty")
    assert_true(fixture.get("lifecycle", {}).get("severityEscalated") is True, "fixture proves severity escalation")
    assert_true(fixture.get("lifecycle", {}).get("resolved") is True, "fixture proves two-miss resolution")
    expected_categories = {"workload", "retention", "deck_health", "card_problems"}
    assert_true(expected_categories <= set(fixture.get("categoryCounts", {})), "all detector categories are represented")

    result = {
        "schemaVersion": summary.get("schemaVersion"),
        "notificationCount": all_items.get("total"),
        "activeSignalCount": summary.get("activeSignalCount"),
        "resolvedHistoryPresent": True,
        "fixtureLifecycle": fixture.get("lifecycle"),
        "preferencesPersistedAfterRestart": None,
    }
    if label == "restart":
        preferences = settings.get("preferences", {})
        assert_true(preferences.get("showUnreadBadge") is False, "badge preference persists across Anki restart")
        assert_true(preferences.get("minimumToastSeverity") == "warning", "toast severity persists across Anki restart")
        assert_true(summary.get("unreadCount") == 0, "read state persists across Anki restart")
        result["preferencesPersistedAfterRestart"] = True
        (artifacts / "notification-restart-proof.json").write_text(
            json.dumps({"ok": True, "unreadCount": 0, "showUnreadBadge": False, "minimumToastSeverity": "warning"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


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


class DashboardAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.refs.append(str(values.get("src") or ""))
        if tag == "link" and values.get("href"):
            rel = str(values.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.refs.append(str(values.get("href") or ""))


def assert_dashboard_assets(base_url: str, token: str, artifacts: Path, label: str) -> dict[str, Any]:
    status, content_type, body = fetch_bytes(base_url, "/", token)
    assert_true(status == 200, "dashboard index returned 200")
    assert_true("text/html" in content_type.lower(), "dashboard index content-type is HTML")
    html = body.decode("utf-8", errors="replace")
    parser = DashboardAssetParser()
    parser.feed(html)
    refs = sorted({ref.split("#", 1)[0].split("?", 1)[0] for ref in parser.refs if ref.strip()})
    assert_true(refs, "dashboard index links JS/CSS assets")

    checked: list[dict[str, Any]] = []
    css_payloads: list[str] = []
    for ref in refs:
        path = ref if ref.startswith("/") else f"/{ref}"
        status, asset_type, asset_body = fetch_bytes(base_url, path, token)
        suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        assert_true(status == 200, f"dashboard asset returned 200: {ref}")
        assert_true(len(asset_body) > 0, f"dashboard asset body is non-empty: {ref}")
        if suffix == "css":
            assert_true("text/css" in asset_type.lower(), f"CSS asset content-type is text/css: {ref}")
            css_payloads.append(asset_body.decode("utf-8", errors="replace"))
        if suffix == "js":
            lower_type = asset_type.lower()
            assert_true(
                "javascript" in lower_type or "text/plain" not in lower_type,
                f"JS asset content-type is script-like: {ref}",
            )
        checked.append(
            {
                "href": urljoin(base_url, path),
                "path": path,
                "status": status,
                "contentType": asset_type,
                "size": len(asset_body),
            }
        )

    css_payload = "\n".join(css_payloads)
    markers = [
        "[data-theme=light]",
        ".topbar-surface",
        ".shadow-panel",
        ".cards-inbox-page",
        ".anki-card-shadow-preview",
    ]
    missing_markers = [marker for marker in markers if marker not in css_payload]
    assert_true(not missing_markers, f"dashboard CSS markers missing: {missing_markers}")
    summary = {
        "ok": True,
        "indexContentType": content_type,
        "assetCount": len(checked),
        "cssAssetCount": len(css_payloads),
        "assets": checked,
        "missingCssMarkers": missing_markers,
    }
    (artifacts / f"api-asset-smoke-{label}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


CARD_ROW_KEYS = ("attentionCards",)


def report_cards(report: dict[str, Any]) -> list[dict[str, Any]]:
    return _card_rows_from_report(report)


def _card_rows_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    for key in CARD_ROW_KEYS:
        value = report.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def find_fixture_card(cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    for card in cards:
        rendered = card.get("renderedPreview") if isinstance(card.get("renderedPreview"), dict) else {}
        front_html = str(rendered.get("frontHtml") or "")
        rendered_dump = json.dumps(rendered, ensure_ascii=False)
        has_fixture_media = "要.gif" in rendered_dump or "%E8%A6%81.gif" in rendered_dump
        if has_fixture_media and 'class="card-content"' in front_html:
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
    css = str(rendered.get("css") or "")
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
    assert_true(".word-focus" in css, "note type CSS includes word-focus rule")
    assert_true("rgb(255, 170, 0)" in css, "note type CSS sets expected word-focus color")
    assert_true("#2563eb" not in css.lower(), "fixture word-focus CSS is not the old blue")
    assert_true('class="card-content"' in front_html, "front template card-content wrapper preserved")
    assert_true('class="main-word"' in front_html, "front template main-word wrapper preserved")
    assert_true("word-focus" in front_html, "word-focus class preserved")
    assert_true("rgb(255, 165, 0)" in front_html or "orange" in front_html.lower(), "inline color style preserved")
    assert_true("asr-card-replay-button" in front_html, "replay button present in frontHtml")
    assert_true("asr-card-audio" in front_html and "<audio" in front_html.lower(), "hidden audio element present in frontHtml")
    assert_true("<audio" not in front_html.lower() or " controls" not in front_html.lower(), "native audio controls are not visible in frontHtml")
    assert_true(front_html.find("asr-card-replay-button") < front_html.find("word-focus"), "replay button keeps native marker placement")
    assert_true("要.gif" in rendered_dump or "%E8%A6%81.gif" in rendered_dump, "要.gif reference present")
    assert_true("望.gif" in rendered_dump or "%E6%9C%9B.gif" in rendered_dump, "望.gif reference present")
    assert_true("要望.mp3" in rendered_dump or "%E8%A6%81%E6%9C%9B.mp3" in rendered_dump, "audio reference present")
    assert_true('class="pos-tag"' in back_html, "back template pos-tag wrapper preserved")
    assert_true('class="meaning-box"' in back_html, "back template meaning-box wrapper preserved")
    assert_true('class="reading-box"' in back_html, "back template reading-box wrapper preserved")
    assert_true('class="section-container"' in back_html, "back template section-container wrapper preserved")
    media_names = {
        str(item.get("name") or "")
        for item in rendered.get("mediaRefs", [])
        if isinstance(item, dict)
    }
    assert_true({"要.gif", "望.gif", "要望.mp3"}.issubset(media_names), "fixture mediaRefs contain images and audio")
    assert_true("<script" not in front_html.lower(), "scripts stripped from preview")
    assert_true("file://" not in front_html.lower(), "file URLs stripped from preview")


def assert_apkg_report_if_enabled(
    artifacts: Path,
    label: str,
    base_url: str,
    token: str,
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    import_summary = read_json_if_exists(artifacts / "apkg-import-summary.json")
    if not import_summary.get("enabled"):
        summary = {
            "enabled": False,
            "skipReason": import_summary.get("skipReason") or "APKG fixture mode disabled.",
        }
        (artifacts / f"api-smoke-apkg-{label}.json").write_text(
            json.dumps({"apkg": summary}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    assert_true(import_summary.get("imported") is True, "APKG import summary reports imported")
    problem_summary = read_json_if_exists(artifacts / "apkg-problematic-summary.json")
    assert_true(problem_summary.get("enabled") is True, "APKG problematic summary enabled")
    imported_card_count = int(import_summary.get("cardCount") or 0)
    marked_count = int(problem_summary.get("cardsMarked") or 0)
    assert_true(imported_card_count > 0, "APKG imported card count is non-zero")
    assert_true(marked_count >= imported_card_count, "APKG cards were marked problematic")

    apkg_cards = find_apkg_cards(cards, import_summary)
    assert_true(len(apkg_cards) >= min(3, imported_card_count), "APKG cards present in attentionCards")
    if imported_card_count <= 100:
        assert_true(len(apkg_cards) >= imported_card_count, "all imported APKG cards present in attentionCards")

    distinct_note_types = sorted({card_note_type(card) for card in apkg_cards if card_note_type(card)})
    expected_note_types = [str(name) for name in import_summary.get("noteTypeNames", []) if str(name).strip()]
    assert_true(len(distinct_note_types) >= min(3, len(expected_note_types) or 3), "APKG cards represent at least 3 note types")
    for expected in ("Основная", "Грамматика", "Слова", "Копия Грамматика"):
        if expected in expected_note_types:
            assert_true(expected in distinct_note_types, f"APKG note type represented: {expected}")

    raw_sound_markers = 0
    raw_anki_markers = 0
    media_cards_checked = 0
    render_sources: dict[str, int] = {}
    fetched_media: list[str] = []
    for card in apkg_cards:
        preview = card.get("preview") if isinstance(card.get("preview"), dict) else {}
        assert_true(bool(card_note_type(card)), "APKG card has note type name")
        assert_true(bool(preview.get("cardTemplateName")), "APKG card has card template name")
        rendered = card.get("renderedPreview")
        assert_true(isinstance(rendered, dict), "APKG card has renderedPreview")
        rendered = rendered if isinstance(rendered, dict) else {}
        source = str(rendered.get("renderSource") or "")
        render_sources[source] = render_sources.get(source, 0) + 1
        assert_true(source == "anki_native", "APKG card used native Anki render")
        assert_true(not rendered.get("fallbackReason"), "APKG native card has empty fallbackReason")
        front_html = str(rendered.get("frontHtml") or "")
        back_html = str(rendered.get("backHtml") or "")
        front_plain = str(rendered.get("frontPlainText") or "")
        back_plain = str(rendered.get("backPlainText") or "")
        rendered_text = "\n".join([front_html, back_html, front_plain, back_plain])
        lower_rendered = rendered_text.lower()
        if "[sound:" in lower_rendered:
            raw_sound_markers += 1
        if "[anki:play:" in lower_rendered:
            raw_anki_markers += 1
        assert_true("[sound:" not in lower_rendered, "APKG rendered preview has no raw sound marker")
        assert_true("[anki:play:" not in lower_rendered, "APKG rendered preview has no raw Anki AV marker")
        assert_true("<script" not in lower_rendered, "APKG rendered preview strips script tags")
        assert_true("javascript:" not in lower_rendered, "APKG rendered preview strips javascript URLs")
        assert_true("cdnjs" not in lower_rendered, "APKG rendered preview strips external CDN refs from HTML")
        assert_true("<link" not in lower_rendered, "APKG rendered preview strips link tags")
        media_refs = [item for item in rendered.get("mediaRefs", []) if isinstance(item, dict)]
        if media_refs:
            media_cards_checked += 1
        for ref in media_refs[:2]:
            name = str(ref.get("name") or "")
            if not name or name in fetched_media:
                continue
            status, _content_type, body = fetch_bytes(base_url, "/api/media", token, {"name": name})
            assert_true(status == 200, f"APKG media returned 200: {name}")
            assert_true(len(body) > 0, f"APKG media body is non-empty: {name}")
            fetched_media.append(name)

    assert_true(raw_sound_markers == 0, "APKG raw sound marker count is zero")
    assert_true(raw_anki_markers == 0, "APKG raw Anki AV marker count is zero")
    if import_summary.get("mediaFilesFound"):
        assert_true(media_cards_checked >= 2, "APKG media cards have media refs")

    summary = {
        "enabled": True,
        "cardCount": imported_card_count,
        "attentionCardsFromApkg": len(apkg_cards),
        "performanceScenario": problem_summary.get("performanceScenario") or {"enabled": False},
        "distinctNoteTypes": distinct_note_types,
        "renderSources": render_sources,
        "rawSoundMarkersFound": raw_sound_markers,
        "rawAnkiPlayMarkersFound": raw_anki_markers,
        "mediaCardsChecked": media_cards_checked,
        "fetchedMedia": fetched_media,
    }
    (artifacts / f"api-smoke-apkg-{label}.json").write_text(
        json.dumps({"apkg": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def find_apkg_cards(cards: list[dict[str, Any]], import_summary: dict[str, Any]) -> list[dict[str, Any]]:
    deck_names = {str(name) for name in import_summary.get("deckNames", []) if str(name).strip()}
    note_type_names = {str(name) for name in import_summary.get("noteTypeNames", []) if str(name).strip()}
    card_ids = {int(value) for value in import_summary.get("cardIds", []) if str(value).strip().isdigit()}
    result = []
    for card in cards:
        try:
            card_id = int(card.get("cardId") or 0)
        except (TypeError, ValueError):
            card_id = 0
        if card_id in card_ids:
            result.append(card)
            continue
        if str(card.get("deckName") or "") in deck_names:
            result.append(card)
            continue
        if card_note_type(card) in note_type_names:
            result.append(card)
    return result


def card_note_type(card: dict[str, Any]) -> str:
    preview = card.get("preview") if isinstance(card.get("preview"), dict) else {}
    return str(preview.get("noteTypeName") or card.get("noteTypeName") or "")


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


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
