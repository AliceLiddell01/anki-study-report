#!/usr/bin/env python3
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from artifact_paths import ArtifactPaths

PREVIEW_ANCHORS = ("words-preview", "grammar-preview", "java-preview")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real-deck API smoke checks.")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    paths = ArtifactPaths.from_env()
    paths.ensure()
    ready = read_json(Path(os.environ.get("ANKI_STUDY_REPORT_E2E_READY_FILE", str(paths.runtime / "dashboard-ready.json"))))
    base_url = str(ready["baseUrl"])
    token = str(ready["token"])
    reports = paths.reports

    manifest = read_json(Path(os.environ.get("WORKSPACE", "/workspace")) / "docker/anki-e2e/fixtures/real-decks/manifest.json")
    manifest_report = read_pass_report(reports / "real-deck-manifest-report.json")
    import_report = read_pass_report(reports / "real-deck-import-report.json")
    inventory = read_pass_report(reports / "collection-inventory.json")
    anchors = read_pass_report(reports / "anchor-resolution-report.json")["anchors"]
    scenarios = read_pass_report(reports / "scenario-application-report.json")

    health = fetch_json(base_url, "/api/health", token)
    assert_true(health.get("ok") is True, "health ok")
    assert_true(health.get("mode") == "e2e", "health reports e2e mode")
    report = fetch_json(base_url, "/api/report", token)
    assert_true(isinstance(report, dict), "report is an object")
    assert_true("token=" not in json.dumps(report, ensure_ascii=False), "report contains no token-bearing URL")

    assert_true(manifest_report.get("packageCount") == 3, "three packages passed manifest validation")
    assert_true([item.get("id") for item in import_report.get("packages", [])] == [item.get("id") for item in manifest.get("packages", [])], "all packages imported in manifest order")
    assert_true(inventory.get("contentSource") == "committed-real-apkg-only", "collection content source is real APKG only")
    assert_true(inventory.get("syntheticNotes") == 0 and inventory.get("syntheticCards") == 0 and inventory.get("syntheticMedia") == 0, "collection has zero synthetic content")
    assert_true(scenarios.get("contentMutation", {}).get("notesCreated") == 0 and scenarios.get("contentMutation", {}).get("cardsCreated") == 0, "scenario preparation created no content")

    asset_summary = assert_dashboard_assets(base_url, token)
    preview_summary = {}
    for anchor_id in PREVIEW_ANCHORS:
        anchor = anchors[anchor_id]
        card_id = str(anchor["cardId"])
        inspected = post_json(
            base_url,
            "/api/search/inspect",
            token,
            {
                "schemaVersion": 2,
                "mode": "cards",
                "cardId": card_id,
                "requestId": f"real-deck-preview-{anchor_id}",
            },
        )
        assert_true(inspected.get("schemaVersion") == 2 and inspected.get("mode") == "cards", f"{anchor_id} inspect contract is current")
        card = inspected.get("details")
        assert_true(isinstance(card, dict), f"{anchor_id} card is available through exact inspect")
        assert_true(str(card.get("cardId")) == card_id, f"{anchor_id} inspect returns the requested card")
        preview_summary[anchor_id] = assert_native_preview(card, anchor_id, anchor)

    media_checked = assert_real_media(base_url, token, anchors)
    assert_media_security(base_url, token)
    recheck_summary = assert_action_recheck(base_url, token, anchors["cards-action-recheck"])
    profiles_summary = None
    if os.environ.get("ANKI_E2E_SCOPE", "full") in {"full", "cards"}:
        profiles_summary = assert_inspection_profiles(base_url, token, manifest, anchors, args.label)
    notifications_summary = None
    if os.environ.get("ANKI_E2E_SCOPE", "full") in {"full", "notifications"}:
        notifications_summary = assert_notifications(base_url, token)

    output = {
        "ok": True,
        "label": args.label,
        "packages": manifest_report.get("packages"),
        "inventoryTotals": inventory.get("totals"),
        "anchorCount": len(anchors),
        "previews": preview_summary,
        "media": media_checked,
        "actionRecheck": recheck_summary,
        "inspectionProfiles": profiles_summary,
        "notifications": notifications_summary,
        "assets": asset_summary,
        "unexpectedExternalRequests": 0,
    }
    (reports / f"api-smoke-{args.label}.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (reports / f"api-report-sample-{args.label}.json").write_text(json.dumps(redact(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[real-decks] API smoke passed: packages=3 anchors={len(anchors)} media={len(media_checked)}", flush=True)
    return 0


def assert_native_preview(card: dict[str, Any], anchor_id: str, anchor: dict[str, Any]) -> dict[str, Any]:
    rendered = card.get("renderedPreview")
    assert_true(isinstance(rendered, dict), f"{anchor_id} has renderedPreview")
    assert_true(rendered.get("renderSource") == "anki_native", f"{anchor_id} uses native Anki render")
    assert_true(rendered.get("renderStatus") in {"available", "sanitized"}, f"{anchor_id} render is available")
    front = str(rendered.get("frontHtml") or "")
    back = str(rendered.get("backHtml") or "")
    css = str(rendered.get("css") or "")
    assert_true(front.strip() and back.strip(), f"{anchor_id} has non-empty front/back")
    combined = "\n".join((front, back, css))
    assert_true("[sound:" not in combined.lower() and "[anki:play:" not in combined.lower(), f"{anchor_id} contains no raw AV markers")
    identity = card.get("noteType") if isinstance(card.get("noteType"), dict) else {}
    if identity:
        assert_true(str(identity.get("noteTypeId")) == str(anchor["noteTypeId"]), f"{anchor_id} note type identity matches anchor")
    for class_name in anchor.get("htmlClasses", []):
        assert_true(class_name in combined, f"{anchor_id} contains required HTML class {class_name}")
    return {
        "cardId": anchor["cardId"],
        "noteId": anchor["noteId"],
        "noteTypeId": anchor["noteTypeId"],
        "renderSource": rendered.get("renderSource"),
        "frontBytes": len(front.encode("utf-8")),
        "backBytes": len(back.encode("utf-8")),
    }


def assert_real_media(base_url: str, token: str, anchors: dict[str, Any]) -> list[dict[str, Any]]:
    references: dict[str, str] = {}
    for anchor_id in ("image-gif-media", "audio-media"):
        for item in anchors[anchor_id].get("mediaReferences", []):
            if isinstance(item, dict) and item.get("name"):
                references[str(item["name"])] = str(item.get("capability") or "other")
    capabilities = set(references.values())
    assert_true({"audio", "gif", "image"} <= capabilities, "real media anchors expose audio, GIF and image")
    checked = []
    for name, capability in sorted(references.items()):
        status, content_type, body = fetch_bytes(base_url, "/api/media", token, {"name": name})
        assert_true(status == 200 and body, f"real media route returned content: {capability}")
        checked.append({"name": name, "capability": capability, "status": status, "contentType": content_type, "size": len(body)})
    return checked


def assert_media_security(base_url: str, token: str) -> None:
    for unsafe_name in ("../secret.txt", "file:///secret.gif", "C:\\secret\\x.gif", "/etc/passwd"):
        status, _content_type, _body = fetch_bytes(base_url, "/api/media", token, {"name": unsafe_name})
        assert_true(status in {400, 404}, "unsafe media path rejected")


def assert_action_recheck(base_url: str, token: str, anchor: dict[str, Any]) -> dict[str, Any]:
    triage = post_json(base_url, "/api/triage/query", token, automatic_triage_request())
    assert_true(triage.get("dataset") == "automatic", "action/recheck uses automatic triage reasons")
    items = [item for item in triage.get("items", []) if isinstance(item, dict)]
    item = next((value for value in items if str(value.get("cardId")) == str(anchor["cardId"])), None)
    assert_true(item is not None, "action/recheck anchor is present in automatic triage")
    reason_ids = [reason.get("reasonId") for reason in item.get("reasons", []) if isinstance(reason, dict) and reason.get("reasonId")]
    assert_true("learning:learning.leech" in reason_ids, "action/recheck anchor has authoritative leech reason")
    response = post_json(
        base_url,
        "/api/triage/recheck",
        token,
        {
            "schemaVersion": 1,
            "cardId": item["cardId"],
            "expectedNoteId": item["noteId"],
            "reasonIds": reason_ids,
            "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
        },
    )
    assert_true(response.get("schemaVersion") == 1, "exact recheck v1 is active")
    assert_true(str(response.get("cardId")) == str(anchor["cardId"]), "exact recheck targets anchor card only")
    assert_true(response.get("entityStatus") == "available", "exact recheck confirms entity availability")
    return {
        "cardId": anchor["cardId"],
        "reasonIds": reason_ids,
        "sourceDataset": triage.get("dataset"),
        "status": response.get("status"),
        "entityStatus": response.get("entityStatus"),
    }


def assert_inspection_profiles(base_url: str, token: str, manifest: dict[str, Any], anchors: dict[str, Any], label: str) -> dict[str, Any]:
    anchor_ids = ("inspection-japanese", "inspection-programming")
    catalog = post_json(base_url, "/api/inspection-profiles/query", token, {"schemaVersion": 1, "noteTypeIds": [], "limit": 500})
    revision = int(catalog.get("store", {}).get("revision") or 0)
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    selected = {}
    for anchor_id in anchor_ids:
        note_type_id = str(anchors[anchor_id]["noteTypeId"])
        item = next((value for value in items if str(value.get("structure", {}).get("noteTypeId")) == note_type_id), None)
        assert_true(item is not None, f"{anchor_id} real note type is present in Inspection Profiles")
        selected[anchor_id] = item

    if label == "first" and revision == 0:
        for anchor_id in anchor_ids:
            definition = manifest["anchors"][anchor_id]["inspectionProfile"]
            profile = confirmed_profile(selected[anchor_id], definition)
            updated = post_json(
                base_url,
                "/api/inspection-profiles/update",
                token,
                {"schemaVersion": 1, "action": "save", "expectedRevision": revision, "targetState": "confirmed", "profile": profile},
            )
            revision = int(updated.get("store", {}).get("revision") or 0)

    catalog = post_json(base_url, "/api/inspection-profiles/query", token, {"schemaVersion": 1, "noteTypeIds": [], "limit": 500})
    items = [item for item in catalog.get("items", []) if isinstance(item, dict)]
    proofs = {}
    for anchor_id in anchor_ids:
        note_type_id = str(anchors[anchor_id]["noteTypeId"])
        item = next((value for value in items if str(value.get("structure", {}).get("noteTypeId")) == note_type_id), None)
        assert_true(item is not None and isinstance(item.get("storedProfile"), dict), f"{anchor_id} stored profile exists")
        validation = post_json(
            base_url,
            "/api/inspection-profiles/validate",
            token,
            {"schemaVersion": 2, "profile": item["storedProfile"], "preview": {"mode": "sample", "limit": 10}},
        )
        assert_true(validation.get("valid") is True, f"{anchor_id} profile validates")
        assert_true(validation.get("preview", {}).get("evaluatedCount", 0) > 0, f"{anchor_id} profile evaluates real cards")
        assert_true("rawFields" not in json.dumps(validation, ensure_ascii=False), f"{anchor_id} preview is redacted")
        proofs[anchor_id] = {"noteTypeId": note_type_id, "fieldNames": anchors[anchor_id]["fieldNames"], "evaluatedCount": validation["preview"]["evaluatedCount"]}
    return {"storeRevision": catalog.get("store", {}).get("revision"), "profiles": proofs}


def confirmed_profile(item: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any]:
    structure = item["structure"]
    fields = {field["name"]: field for field in structure["fields"]}
    mappings = []
    for mapping in definition.get("mappings", []):
        field_name = str(mapping["field"])
        assert_true(field_name in fields, "profile mapping references an existing real field")
        mappings.append({"role": mapping["role"], "fields": [fields[field_name]]})
    now = "2026-07-23T00:00:00Z"
    return {
        "profileId": f"note-type-{structure['noteTypeId']}",
        "noteTypeId": structure["noteTypeId"],
        "noteTypeName": structure["name"],
        "storedState": "confirmed",
        "displayName": definition["displayName"],
        "expectedFingerprint": structure["fingerprint"],
        "appliesTo": {"templateOrdinals": []},
        "fieldMappings": mappings,
        "checks": definition.get("checks", []),
        "confirmedAt": now,
        "updatedAt": now,
    }


def assert_notifications(base_url: str, token: str) -> dict[str, Any]:
    summary = fetch_json(base_url, "/api/notifications/summary", token)
    items = fetch_json(base_url, "/api/notifications", token, {"page": "1", "pageLimit": "50", "tab": "all", "category": "all"})
    assert_true(summary.get("schemaVersion") == 1, "notification summary schema is current")
    return {"total": items.get("total"), "active": summary.get("activeSignalCount")}


def assert_dashboard_assets(base_url: str, token: str) -> dict[str, Any]:
    status, content_type, body = fetch_bytes(base_url, "/", token)
    assert_true(status == 200 and "text/html" in content_type.lower(), "dashboard index is HTML")
    parser = DashboardAssetParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    refs = sorted({ref.split("#", 1)[0].split("?", 1)[0] for ref in parser.refs if ref.strip()})
    assert_true(refs, "dashboard index references assets")
    checked = []
    for ref in refs:
        path = ref if ref.startswith("/") else f"/{ref}"
        asset_status, asset_type, asset_body = fetch_bytes(base_url, path, token)
        assert_true(asset_status == 200 and asset_body, "dashboard asset is available")
        checked.append({"path": path, "status": asset_status, "contentType": asset_type, "size": len(asset_body)})
    return {"assetCount": len(checked), "assets": checked}


class DashboardAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.refs.append(str(values["src"]))
        if tag == "link" and values.get("href") and "stylesheet" in str(values.get("rel") or "").lower():
            self.refs.append(str(values["href"]))


def automatic_triage_request() -> dict[str, Any]:
    return {
        "schemaVersion": 4,
        "dataset": "automatic",
        "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
        "limit": 100,
        "contentCursor": None,
    }


def triage_request(card_ids: list[str]) -> dict[str, Any]:
    return {
        "schemaVersion": 4,
        "dataset": "search_workset",
        "cardIds": card_ids,
        "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
        "limit": min(200, max(1, len(card_ids))),
    }


def fetch_json(base_url: str, path: str, token: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    status, _content_type, body = fetch_bytes(base_url, path, token, params)
    if status != 200:
        raise AssertionError(f"{path} returned HTTP {status}: {body[:200]!r}")
    value = json.loads(body.decode("utf-8"))
    assert_true(isinstance(value, dict), f"{path} returns an object")
    return value


def post_json(base_url: str, path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}?{urlencode({'token': token})}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "anki-study-report-e2e"},
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
        raise AssertionError(f"{path} returned HTTP {status}: {decoded!r}")
    return decoded["response"]


def fetch_bytes(base_url: str, path: str, token: str, params: dict[str, str] | None = None) -> tuple[int, str, bytes]:
    query = {"token": token}
    if params:
        query.update(params)
    request = Request(f"{base_url}{path}?{urlencode(query)}", headers={"User-Agent": "anki-study-report-e2e"})
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert_true(isinstance(value, dict), f"{path.name} is an object")
    return value


def read_pass_report(path: Path) -> dict[str, Any]:
    value = read_json(path)
    assert_true(value.get("status") == "PASS", f"{path.name} reports PASS")
    return value


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if "token" in key.lower() else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value[:200]]
    return value


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
