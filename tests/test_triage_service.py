from __future__ import annotations

import json
import math
import random

import pytest

from conftest import import_addon_module


triage = import_addon_module("triage_service")


def request(dataset="automatic", *, card_ids=None, limit=None):
    value = {
        "schemaVersion": 4,
        "dataset": dataset,
        "scope": {"periodStartMs": 1_700_000_000_000, "periodEndMs": 1_700_604_800_000, "deckIds": []},
        "limit": limit or (200 if dataset == "search_workset" else 100),
    }
    if dataset == "automatic":
        value["contentCursor"] = None
    if dataset == "search_workset":
        value["cardIds"] = card_ids or ["1"]
    return value


def source(status="available", *, items=0, skipped=0, truncated=False, error=None):
    return {
        "status": status,
        "itemCount": items,
        "skippedCount": skipped,
        "truncated": truncated,
        "errorCode": error,
    }


def display(text: str, *, source_name="reviewer_front", status="available", truncated=False):
    return {
        "displayText": text,
        "displaySource": source_name,
        "displayStatus": status,
        "displayTruncated": truncated,
    }


def card_row(card_id: int, *, state="review"):
    return {
        "cardId": str(card_id),
        "noteId": str(10_000 + card_id),
        "deckId": "3",
        "deckName": "Languages::Japanese",
        "noteTypeId": "7",
        "noteTypeName": "Basic",
        "templateOrdinal": 0,
        "templateName": "Card 1",
        **display(f"Card {card_id}"),
        "state": state,
        "due": 1,
        "interval": 10,
        "repetitions": 5,
        "lapses": 0,
        "flag": 2,
        "tagSummary": [],
    }


def attention_row(card_id: int, issues=None, **overrides):
    return {
        "cardId": card_id,
        "noteId": 10_000 + card_id,
        "noteTypeId": 7,
        "deckName": "Languages::Japanese",
        "frontPreview": f"<b>Legacy {card_id}</b>",
        "cardTemplateName": "Card 1",
        "issues": issues or ["repeated again"],
        "againCount": 4,
        "lapses": 2,
        "averageAnswerSeconds": 12.5,
        "passRate": 0.5,
        "lastReviewedAt": "2026-07-18T01:02:03Z",
        "riskScore": 99,
        "renderedPreview": {"frontHtml": "<script>forbidden</script>"},
        **overrides,
    }


def repeated_signal(card_id: int, *, severity="critical", again=5):
    return {
        "code": "card.repeated_again",
        "severity": severity,
        "entityType": "card",
        "entityId": str(card_id),
        "evidence": {
            "againCount": again,
            "reviewCount": 8,
            "windowDays": 7,
            "lastReviewAt": "2026-07-18T02:03:04Z",
        },
        "detectorVersion": "signals-v1.0",
        "firstSeenAt": "2026-07-17T00:00:00Z",
        "lastSeenAt": "2026-07-18T02:03:04Z",
    }


def content_checks(status="no_confirmed_profiles"):
    return {
        "status": status,
        "confirmedProfileCount": 0,
        "needsReviewProfileCount": 0,
        "disabledProfileCount": 0,
        "suggestedProfileCount": 0,
        "scannedNoteCount": 0,
        "evaluatedNoteCount": 0,
        "failedCheckCount": 0,
        "skippedCount": 0,
        "truncated": False,
        "nextCursor": None,
        "errorCode": None,
    }


def project(req, *, attention=None, signals=None, resolved=None, signal_status=None, resolver_status=None, profile_reasons=None):
    normalized = triage.normalize_triage_query_request(req)
    attention = attention or []
    signals = signals or []
    resolved = resolved or []
    return triage.build_triage_projection(
        normalized,
        attention_rows=attention,
        learning_source_status=source("available" if attention else "empty", items=len(attention)),
        content_candidate_source_status={**source("empty"), "scannedNoteCount": 0, "nextCursor": None},
        signal_rows=signals,
        signal_source_status=signal_status or source("available" if signals else "empty", items=len(signals)),
        resolved_card_rows=resolved,
        resolver_source_status=resolver_status or source("available" if resolved else "empty", items=len(resolved)),
        profile_reasons=profile_reasons or [],
        profile_source_status=source("empty"),
        content_checks=content_checks(),
        generated_at_ms=1_721_000_000_000,
    )


def test_request_contract_is_strict_versioned_bounded_and_deduplicates_workset_ids():
    normalized = triage.normalize_triage_query_request(request("search_workset", card_ids=["9", "9", "2"]))
    assert normalized["cardIds"] == [9, 2]

    invalid = [
        {**request(), "schemaVersion": 3},
        {key: value for key, value in request().items() if key != "schemaVersion"},
        {**request(), "rawSql": "select * from revlog"},
        {**request(), "cardIds": ["1"]},
        {**request(), "scope": {**request()["scope"], "query": "deck:*"}},
        {**request(), "scope": {**request()["scope"], "periodEndMs": request()["scope"]["periodStartMs"]}},
        request("search_workset", card_ids=["0"]),
        request("search_workset", card_ids=[str(2**63)]),
        request("search_workset", card_ids=[str(index + 1) for index in range(201)]),
    ]
    for value in invalid:
        with pytest.raises(triage.TriageValidationError):
            triage.normalize_triage_query_request(value)


def test_projection_merges_reasons_and_copies_search_display_identity_without_legacy_aliases():
    row = attention_row(
        1,
        ["missing_audio", "leech", "repeated again", "low pass rate", "slow answer"],
        lapses=9,
    )
    response = project(request(), attention=[row, dict(row)], signals=[repeated_signal(1)], resolved=[card_row(1)])

    assert response["schemaVersion"] == 4
    assert response["status"] == "available"
    assert response["contentChecks"] == content_checks()
    assert response["returnedCount"] == response["totalCount"] == 1
    item = response["items"][0]
    assert item["itemId"] == "card:1"
    assert {key: item[key] for key in display("")} == display("Card 1")
    assert "primaryText" not in item
    assert item["priority"] == "high"
    assert item["primaryReasonCode"] == "learning.leech"
    assert [reason["code"] for reason in item["reasons"]] == [
        "learning.leech",
        "learning.repeated_again",
        "learning.low_pass_rate",
        "learning.slow_answer",
    ]
    repeated = item["reasons"][1]
    assert repeated["sources"] == ["attention", "signals"]
    assert [evidence["kind"] for evidence in repeated["evidence"]] == ["signal_evidence", "review_counts"]
    encoded = json.dumps(response, allow_nan=False)
    assert "riskScore" not in encoded
    assert "missing_audio" not in encoded
    assert "renderedPreview" not in encoded
    assert "<script>" not in encoded
    assert "Legacy 1" not in encoded


def test_projection_order_is_deterministic_for_shuffled_duplicate_sources_and_stable_card_ties():
    rows = [
        attention_row(30, ["slow answer"]),
        attention_row(20, ["repeated again"]),
        attention_row(10, ["leech"], lapses=8),
        attention_row(21, ["repeated again"]),
    ]
    signals = [repeated_signal(20, severity="warning", again=4), repeated_signal(20, severity="warning", again=4)]
    resolved = [card_row(card_id) for card_id in (10, 20, 21, 30)]
    baseline = project(request(), attention=rows, signals=signals, resolved=resolved)
    assert [item["cardId"] for item in baseline["items"]] == ["10", "20", "21", "30"]

    for seed in range(8):
        shuffled_rows = list(rows)
        shuffled_signals = list(signals)
        shuffled_resolved = list(resolved)
        random.Random(seed).shuffle(shuffled_rows)
        random.Random(seed + 20).shuffle(shuffled_signals)
        random.Random(seed + 40).shuffle(shuffled_resolved)
        assert project(request(), attention=shuffled_rows, signals=shuffled_signals, resolved=shuffled_resolved) == baseline


def test_partial_and_caps_are_explicit_and_malformed_evidence_is_bounded():
    rows = [attention_row(card_id, ["low pass rate"], passRate=math.nan) for card_id in range(1, 102)]
    resolved = [card_row(card_id) for card_id in range(1, 102)]
    response = project(
        request(limit=100),
        attention=rows,
        signals=[{"code": "unknown", "entityType": "card", "entityId": "1"}],
        resolved=resolved,
        signal_status=source("error", skipped=1, error="signal_store_failed"),
    )
    assert response["status"] == "partial"
    assert response["totalCount"] == 101
    assert response["returnedCount"] == 100
    assert response["truncated"] is True
    assert response["sourceStatus"]["signals"]["status"] == "error"
    assert response["items"][0]["reasons"][0]["evidence"] == []
    json.dumps(response, allow_nan=False)


def test_search_workset_preserves_order_and_missing_card_has_unavailable_identity():
    req = request("search_workset", card_ids=["20", "20", "10"])
    response = project(req, attention=[attention_row(10, ["repeated again"])], resolved=[card_row(20)])

    assert [item["cardId"] for item in response["items"]] == ["20", "10"]
    neutral, enriched_missing = response["items"]
    assert neutral["availability"] == "available"
    assert neutral["displayText"] == "Card 20"
    assert neutral["priority"] is None
    assert neutral["primaryReasonCode"] is None
    assert neutral["reasons"] == []
    assert neutral["sources"] == ["search_workset"]
    assert enriched_missing["availability"] == "missing"
    assert enriched_missing["priority"] == "medium"
    assert enriched_missing["inspect"] is None
    assert enriched_missing["sources"] == ["search_workset", "attention"]
    assert {key: enriched_missing[key] for key in display("")} == display("", source_name="none", status="unavailable")
    assert "Legacy 10" not in json.dumps(enriched_missing)

    degraded = project(
        request("search_workset", card_ids=["20"]),
        resolved=[card_row(20)],
        signal_status=source("error", error="signal_store_failed"),
    )
    degraded["sourceStatus"]["learningCandidates"] = source("unavailable", error="attention_source_unavailable")
    assert triage._response_status("search_workset", degraded["sourceStatus"]) == "partial"


def test_invalid_resolver_display_identity_fails_closed_without_attention_preview():
    malformed = {**card_row(1), "displayText": "", "displayStatus": "available"}
    response = project(request(), attention=[attention_row(1)], resolved=[malformed])
    item = response["items"][0]
    assert item["displayStatus"] == "unavailable"
    assert item["displaySource"] == "none"
    assert item["displayText"] == ""


def test_execute_reuses_attention_and_search_adapters_without_full_preview(monkeypatch):
    calls = {}

    def collect_learning(_col, start, end, deck_ids, *, max_results):
        calls["attention"] = (start, end, deck_ids, max_results)
        return [attention_row(7)], {"status": "available"}

    def resolve(_col, card_ids):
        calls["resolve"] = list(card_ids)
        return {"items": [card_row(7)], "missingCardIds": []}

    monkeypatch.setattr(triage, "collect_learning_triage_candidates_with_status", collect_learning)
    monkeypatch.setattr(triage, "collect_current_content_candidates", lambda *_args, **_kwargs: {
        "reasons": [],
        "sourceStatus": {"status": "empty", "scannedNoteCount": 0, "nextCursor": None},
        "profileSourceStatus": {"status": "empty"},
        "contentChecks": {"status": "no_confirmed_profiles", "errorCode": "no_confirmed_profiles"},
    })
    monkeypatch.setattr(triage, "resolve_card_rows", resolve)
    response = triage.execute_triage_query(object(), request(), signal_rows=[], signal_source_status={"status": "empty"})

    assert calls["attention"][-1] == 100
    assert calls["resolve"] == [7]
    assert response["items"][0]["inspect"] == {"mode": "cards", "cardId": "7"}
    assert response["items"][0]["displayText"] == "Card 7"


def test_triage_reuses_search_formatter_resolver_and_keeps_v4_wire_shape(monkeypatch):
    formatter_service = import_addon_module("card_display_formatter_service")
    formatter = {
        "noteTypeId": "7", "noteTypeName": "Japanese", "templateOrdinal": None,
        "templateName": None, "storedState": "enabled", "inputSource": "reviewer_front",
        "textMode": "preserve", "imageMode": "stem", "audioMode": "omit",
        "maxLines": 1, "lineSeparator": " ", "maxCharacters": 240,
        "updatedAt": "2026-07-19T00:00:00Z",
    }
    resolver = formatter_service.CardDisplayFormatterResolver.from_snapshot(
        {"status": "available", "revision": 1, "formatters": [formatter]}
    )
    monkeypatch.setattr(
        triage,
        "collect_learning_triage_candidates_with_status",
        lambda *_args, **_kwargs: ([attention_row(7)], {"status": "available"}),
    )
    monkeypatch.setattr(triage, "collect_current_content_candidates", lambda *_args, **_kwargs: {
        "reasons": [],
        "sourceStatus": {"status": "empty", "scannedNoteCount": 0, "nextCursor": None},
        "profileSourceStatus": {"status": "empty"},
        "contentChecks": {"status": "no_confirmed_profiles", "errorCode": "no_confirmed_profiles"},
    })
    seen = []
    custom = card_row(7)
    custom["displayText"] = "【に】感謝（する）"
    monkeypatch.setattr(
        triage,
        "resolve_card_rows",
        lambda _col, ids, value: seen.append((ids, value)) or {"items": [custom], "missingCardIds": []},
    )
    response = triage.execute_triage_query(
        object(), request(), signal_rows=[], signal_source_status={"status": "empty"}, formatter_resolver=resolver
    )
    assert response["schemaVersion"] == 4
    assert response["items"][0]["displayText"] == "【に】感謝（する）"
    assert seen == [([7], resolver)]
    assert "formatterApplied" not in response["items"][0]
