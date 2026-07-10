from __future__ import annotations

import pytest

from conftest import fresh_import_addon_module, load_dashboard_fixture


TOP_LEVEL_KEYS = {
    "metadata",
    "summary",
    "kpis",
    "answerDistribution",
    "activity",
    "comparison",
    "decks",
    "attentionCards",
    "attentionCardsStatus",
    "forecast",
    "fsrs",
    "recommendations",
    "cache",
}


EMPTY_ISSUE_COUNTS = {
    "leech": 0,
    "repeatedAgain": 0,
    "slowAnswer": 0,
    "lowPassRate": 0,
    "missingAudio": 0,
    "missingExample": 0,
    "missingPitch": 0,
    "missingImage": 0,
    "missingMeaning": 0,
    "missingPartOfSpeech": 0,
}


DEFAULT_THRESHOLDS = {
    "repeatedAgainThreshold": 2,
    "slowAnswerSeconds": 10.0,
    "lowPassRateThreshold": 0.6,
    "leechLapsesFallback": 8,
    "maxResults": 100,
}


@pytest.mark.parametrize(
    "fixture_name",
    ["minimal_metrics", "empty_collection", "normal_day", "large_collection"],
)
def test_build_dashboard_report_payload_contract_for_demo_fixtures(fixture_name):
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture(fixture_name)

    payload = dashboard_payload.build_dashboard_report_payload(
        fixture["metrics"],
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert_dashboard_contract(payload)
    assert payload["metadata"]["title"] == "Anki Study Report"
    assert payload["metadata"]["period"] == fixture["metadata"]["period"]
    assert payload["cache"]["status"] == fixture["cache"]["status"]


def test_dashboard_payload_normal_day_key_values():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")

    payload = dashboard_payload.build_dashboard_report_payload(
        fixture["metrics"],
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["metadata"]["answerMode"] == "pass_fail"
    assert payload["kpis"][0]["id"] == "total_reviews"
    assert payload["kpis"][0]["value"] == "100"
    assert payload["forecast"]["tomorrow"] == 80
    assert payload["decks"][0]["name"] == "Japanese::Core"


def test_dashboard_payload_cache_snapshot_fixture():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")
    snapshot = fixture["snapshot"]
    today = fixture["today"]

    metrics = dashboard_payload.metrics_from_cache_snapshot(snapshot, today)
    metadata = dashboard_payload.build_default_dashboard_metadata(snapshot, today)
    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        metadata,
        cache_summary=snapshot["status"],
    )

    assert_dashboard_contract(payload)
    assert payload["metadata"]["period"] == "Всё время"
    assert payload["kpis"][0]["value"] == "50"
    assert payload["activity"]["activeDays"] == 2
    assert payload["decks"][0]["totalReviews"] == 50
    assert payload["cache"]["status"] == "ready"
    assert payload["attentionCards"] == []
    assert_subset(payload["attentionCardsStatus"], {
        "status": "unavailable",
        "source": "cache",
        "reason": "cache snapshot has no card-level payload; fresh overlay not applied",
        "collectorRan": False,
        "collectionAvailable": False,
    })
    assert payload["noteTypeCatalog"] == []
    assert "cards" not in payload
    assert "cardIssues" not in payload
    assert "problemCards" not in payload


def test_today_dashboard_payload_uses_only_current_local_day_and_keeps_scope():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")

    today = dashboard_payload.build_today_dashboard_payload(
        fixture["snapshot"],
        fixture["today"],
        display_settings={
            "selected_deck_ids": [10],
            "selected_deck_names": ["Core"],
            "include_child_decks": True,
        },
        cache_summary=fixture["snapshot"]["status"],
        now=dashboard_payload.datetime(2026, 7, 1, 12, 0, 0),
    )

    assert today["metadata"]["period"] == "Сегодня"
    assert today["metadata"]["periodId"] == "today"
    assert today["metadata"]["todayDate"] == "2026-07-01"
    assert today["metadata"]["selectedDecks"] == ["Core"]
    assert today["kpis"][0]["value"] == "30"
    assert today["activity"]["days"] == [
        {
            "date": "2026-07-01",
            "reviews": 30,
            "newCards": 4,
            "again": 3,
            "studySeconds": 360,
        }
    ]
    assert today["comparison"]["today"]["reviews"] == 30


def test_today_dashboard_payload_does_not_change_historical_snapshot_totals():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")

    historical = dashboard_payload.metrics_from_cache_snapshot(fixture["snapshot"], fixture["today"])
    today = dashboard_payload.build_today_dashboard_payload(fixture["snapshot"], fixture["today"])

    assert historical["total_reviews"] == 50
    assert today["kpis"][0]["value"] == "30"


def test_dashboard_payload_emits_canonical_attention_card_keys_only():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [
            {
                "cardId": 123,
                "noteId": 456,
                "deckName": "Japanese::Core",
                "frontPreview": "canonical front",
                "issues": ["leech"],
                "riskScore": 42,
            }
        ],
        "attention_cards_status": {
            "status": "available",
            "scannedCards": 1,
            "returnedCards": 1,
            "source": "fresh",
            "noteTypeCatalog": [
                {
                    "noteTypeId": 9,
                    "name": "Japanese vocab",
                    "noteCount": 1,
                    "cardTemplateCount": 1,
                    "fields": ["Front", "Back"],
                    "templates": [{"ord": 0, "name": "Card 1"}],
                    "cssAvailable": True,
                    "usedInCurrentCards": True,
                }
            ],
        },
    }

    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["attentionCards"][0]["cardId"] == 123
    assert_subset(payload["attentionCardsStatus"], {
        "status": "available",
        "scannedCards": 1,
        "returnedCards": 1,
        "source": "fresh",
    })
    assert payload["noteTypeCatalog"] == [
        {
            "noteTypeId": 9,
            "name": "Japanese vocab",
            "noteCount": 1,
            "cardTemplateCount": 1,
            "fields": ["Front", "Back"],
            "templates": [{"ord": 0, "name": "Card 1", "qfmtAvailable": False, "afmtAvailable": False}],
            "cssAvailable": True,
            "usedInCurrentCards": True,
        }
    ]
    assert "cards" not in payload
    assert "cardIssues" not in payload
    assert "problemCards" not in payload


def test_dashboard_payload_includes_sanitized_attention_cards():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [
            {
                "cardId": 123,
                "noteId": 456,
                "deckName": "Japanese::Core",
                "frontPreview": "抽象的な動詞",
                "preview": {
                    "frontText": "抽象的な動詞",
                    "backText": "",
                    "primary": "抽象的な動詞",
                    "secondary": "",
                    "tertiary": "",
                    "mediaBadges": [],
                    "noteTypeName": "",
                    "cardTemplateName": "",
                    "detectedKind": "",
                },
                "issues": ["repeated again", "missing_audio"],
                "riskScore": 130,
                "againCount": 3,
                "lapses": 4,
                "averageAnswerSeconds": 12.5,
                "passRate": 0.5,
                "lastReviewedAt": "2026-07-03",
                "searchQuery": "cid:123",
                "missingFields": ["missing_audio"],
            }
        ],
    }

    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["attentionCards"] == [
        {
            "cardId": 123,
            "noteId": 456,
            "deckName": "Japanese::Core",
            "frontPreview": "抽象的な動詞",
            "preview": {
                "frontText": "抽象的な動詞",
                "backText": "",
                "primary": "抽象的な動詞",
                "secondary": "",
                "tertiary": "",
                "mediaBadges": [],
                "noteTypeName": "",
                "cardTemplateName": "",
                "detectedKind": "",
            },
            "renderedPreview": {
                "renderStatus": "unavailable",
                "renderSource": "",
                "fallbackReason": "",
                "frontHtml": "",
                "backHtml": "",
                "frontPlainText": "",
                "backPlainText": "",
                "css": "",
                "mediaRefs": [],
                "cardOrd": 0,
                "cardId": 0,
                "reason": "",
            },
            "issues": ["repeated again", "missing_audio"],
            "riskScore": 100,
            "againCount": 3,
            "lapses": 4,
            "averageAnswerSeconds": 12.5,
            "passRate": 0.5,
            "lastReviewedAt": "2026-07-03",
            "searchQuery": "cid:123",
            "missingFields": ["missing_audio"],
        }
    ]
    assert_subset(payload["attentionCardsStatus"], {
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
        "status": "available",
        "scannedCards": 1,
        "returnedCards": 1,
        "collectorRan": True,
        "collectionAvailable": True,
        "source": "unknown",
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
    })


def test_dashboard_payload_sanitizes_rendered_preview():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [
            {
                "cardId": 123,
                "deckName": "Japanese::Core",
                "frontPreview": "front",
                "issues": ["leech"],
                "renderedPreview": {
                    "renderStatus": "available",
                    "renderSource": "anki_native",
                    "frontHtml": '<script>alert(1)</script><img src="file:///C:/Users/KykLa/secret.png"><b>front</b>',
                    "backHtml": '<a href="https://example.com/?token=secret">x</a>C:\\Users\\KykLa\\secret',
                    "css": '@import url("https://example.com/x.css"); .card { background: url(file:///secret.png); }',
                    "mediaRefs": ["file:///C:/secret.png", "safe-media.mp3"],
                },
            }
        ],
    }

    payload = dashboard_payload.build_dashboard_report_payload(metrics, fixture["metadata"], cache_summary=fixture["cache"])
    rendered = payload["attentionCards"][0]["renderedPreview"]

    assert rendered["renderStatus"] == "sanitized"
    assert rendered["renderSource"] == "anki_native"
    assert rendered["fallbackReason"] == ""
    assert "<script" not in rendered["frontHtml"]
    assert "file://" not in rendered["frontHtml"]
    assert "https://" not in rendered["backHtml"]
    assert "C:\\Users" not in rendered["backHtml"]
    assert "https://" not in rendered["css"]
    assert "file://" not in rendered["css"]
    assert rendered["mediaRefs"] == [{"name": "safe-media.mp3", "type": "audio", "url": "/api/media?name=safe-media.mp3"}]
    assert rendered["cardOrd"] == 0


def test_dashboard_payload_preserves_safe_rendered_style_class_and_media_refs():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [
            {
                "cardId": 123,
                "deckName": "Japanese::Core",
                "frontPreview": "要望する",
                "issues": ["missing_audio"],
                "renderedPreview": {
                    "renderStatus": "available",
                    "renderSource": "anki_like_fallback",
                    "fallbackReason": "native_render_failed",
                    "frontHtml": (
                        '<span class="word-focus" style="color: rgb(255, 165, 0); position:absolute">要望する</span>'
                        '<img src="/api/media?name=%E8%A6%81.gif&token=secret">'
                    ),
                    "css": ".word-focus { color: orange; }",
                    "mediaRefs": [
                        {"name": "要.gif", "type": "image", "url": "/api/media?name=%E8%A6%81.gif&token=secret"},
                    ],
                    "cardOrd": 1,
                },
            }
        ],
    }

    payload = dashboard_payload.build_dashboard_report_payload(metrics, fixture["metadata"], cache_summary=fixture["cache"])
    rendered = payload["attentionCards"][0]["renderedPreview"]

    assert rendered["renderStatus"] == "sanitized"
    assert rendered["renderSource"] == "anki_like_fallback"
    assert rendered["fallbackReason"] == "native_render_failed"
    assert 'class="word-focus"' in rendered["frontHtml"]
    assert 'style="color: rgb(255, 165, 0)"' in rendered["frontHtml"]
    assert "position" not in rendered["frontHtml"]
    assert "token=secret" not in rendered["frontHtml"]
    assert rendered["css"] == ".word-focus { color: orange; }"
    assert rendered["mediaRefs"] == [{"name": "要.gif", "type": "image", "url": "/api/media?name=%E8%A6%81.gif"}]
    assert rendered["cardOrd"] == 1


def test_dashboard_payload_marks_missing_attention_card_collector_unavailable():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {**fixture["metrics"], "attention_cards": []}

    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["attentionCards"] == []
    assert_subset(payload["attentionCardsStatus"], {
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
        "status": "unavailable",
        "scannedCards": 0,
        "returnedCards": 0,
        "collectorRan": False,
        "collectionAvailable": False,
        "source": "unknown",
        "reason": "collector not invoked",
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
    })


def test_dashboard_payload_preserves_available_empty_attention_card_status():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [],
        "attention_cards_status": {
            "status": "available",
            "scannedCards": 12,
            "returnedCards": 0,
        },
    }

    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["attentionCards"] == []
    assert_subset(payload["attentionCardsStatus"], {
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
        "status": "available",
        "scannedCards": 12,
        "returnedCards": 0,
        "collectorRan": True,
        "collectionAvailable": True,
        "source": "unknown",
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": None,
        "periodEndRaw": None,
        "periodStartMs": 0,
        "periodEndMs": 0,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
    })


def test_cache_snapshot_marks_legacy_card_level_payload_unavailable():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")

    metrics = dashboard_payload.metrics_from_cache_snapshot(fixture["snapshot"], "2026-07-03")

    assert metrics["attention_cards"] == []
    assert metrics["attention_cards_status"] == {
        "status": "unavailable",
        "scannedCards": 0,
        "returnedCards": 0,
        "reason": "cache snapshot has no card-level payload; fresh overlay not applied",
        "collectorRan": False,
        "collectionAvailable": False,
        "source": "cache",
    }


def test_default_dashboard_metadata_uses_display_period_bounds():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("cache_snapshot")
    now = dashboard_payload.datetime(2026, 7, 3, 12, 0, 0)

    last_7 = dashboard_payload.build_default_dashboard_metadata(
        fixture["snapshot"],
        "2026-07-03",
        display_settings={"period": "last_7_days"},
        now=now,
    )
    last_30 = dashboard_payload.build_default_dashboard_metadata(
        fixture["snapshot"],
        "2026-07-03",
        display_settings={"period": "last_30_days"},
        now=now,
    )
    custom = dashboard_payload.build_default_dashboard_metadata(
        fixture["snapshot"],
        "2026-07-03",
        display_settings={
            "period": "custom",
            "custom_start_date": "2026-06-30",
            "custom_end_date": "2026-07-02",
        },
        now=now,
    )
    all_time = dashboard_payload.build_default_dashboard_metadata(
        fixture["snapshot"],
        "2026-07-03",
        display_settings={"period": "all_time"},
        now=now,
    )

    assert last_7["period_start_date"] == "2026-06-27"
    assert last_7["period_end_date"] == "2026-07-03"
    assert last_7["period_start_ts"] > 0
    assert last_7["period_end_ts"] > last_7["period_start_ts"]
    assert last_30["period_start_date"] == "2026-06-04"
    assert custom["period_start_date"] == "2026-06-30"
    assert custom["period_end_date"] == "2026-07-02"
    assert all_time["period_start_ts"] == 0
    assert all_time["period_end_ts"] == int(now.timestamp())


def test_dashboard_payload_sanitizes_attention_card_status_error_reason():
    dashboard_payload = fresh_import_addon_module("dashboard_payload")
    fixture = load_dashboard_fixture("normal_day")
    metrics = {
        **fixture["metrics"],
        "attention_cards": [],
        "attention_cards_status": {
            "status": "error",
            "reason": "Traceback\nCard-level collector failed with token=secret",
        },
    }

    payload = dashboard_payload.build_dashboard_report_payload(
        metrics,
        fixture["metadata"],
        cache_summary=fixture["cache"],
    )

    assert payload["attentionCardsStatus"]["status"] == "error"
    assert "\n" not in payload["attentionCardsStatus"]["reason"]
    assert "token=secret" not in payload["attentionCardsStatus"]["reason"]


def test_dashboard_payload_imports_without_qt_ui_browser_opening_logic():
    fresh_import_addon_module("dashboard_payload")


def assert_dashboard_contract(payload: dict) -> None:
    assert TOP_LEVEL_KEYS.issubset(payload)
    assert isinstance(payload["metadata"], dict)
    assert isinstance(payload["summary"], dict)
    assert isinstance(payload["kpis"], list)
    assert isinstance(payload["answerDistribution"], list)
    assert isinstance(payload["activity"], dict)
    assert isinstance(payload["comparison"], dict)
    assert isinstance(payload["decks"], list)
    assert isinstance(payload["attentionCards"], list)
    assert isinstance(payload["attentionCardsStatus"], dict)
    assert isinstance(payload["forecast"], dict)
    assert isinstance(payload["fsrs"], dict)
    assert isinstance(payload["recommendations"], dict)
    assert isinstance(payload["cache"], dict)


def assert_subset(actual: dict, expected: dict) -> None:
    for key, value in expected.items():
        assert actual.get(key) == value
