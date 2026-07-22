from __future__ import annotations

from types import SimpleNamespace

from conftest import fresh_import_addon_module


class FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def all(self, query="", *args, **_kwargs):
        if "from revlog r" not in str(query):
            return self.rows
        return [
            row for row in self.rows
            if self._row_in_period(row, args, query)
            and self._row_in_decks(row, query, args)
        ]

    def scalar(self, query="", *args, **_kwargs):
        text = str(query).lower()
        if "count(*) from revlog" in text and "where" not in text:
            return len(self.rows)
        if "min(id) from revlog" in text:
            values = [row[10] for row in self.rows]
            return min(values) if values else None
        if "max(id) from revlog" in text:
            values = [row[10] for row in self.rows]
            return max(values) if values else None
        if "count(*)" in text and "from cards" in text:
            return len({row[0] for row in self.rows})
        if "count(*)" in text and "from notes" in text:
            if "where mid" in text and args:
                model_id = int(args[0])
                return len({row[1] for row in self.rows if int(row[4]) == model_id})
            return len({row[1] for row in self.rows})
        if "count(distinct r.cid)" in text:
            return len({
                row[0] for row in self.rows
                if self._row_in_period(row, args, query)
                and self._row_in_decks(row, query, args)
            })
        if "count(*)" in text and "from revlog r" in text:
            return len([
                row for row in self.rows
                if self._row_in_period(row, args, query)
                and self._row_in_decks(row, query, args)
            ])
        return len(self.rows)

    @staticmethod
    def _row_in_period(row, args, query=""):
        offset = 2 if "r.time" in str(query).lower() else 0
        if len(args) < offset + 2:
            return True
        start, end = int(args[offset]), int(args[offset + 1])
        return start <= int(row[10]) < end

    @staticmethod
    def _row_in_decks(row, query, args):
        text = str(query).lower()
        if "and 0" in text:
            return False
        if "c.did in" not in text:
            return True
        offset = 4 if "r.time" in text else 2
        deck_ids = {int(value) for value in args[offset:]}
        return int(row[2]) in deck_ids


class RaisingDb:
    def all(self, *_args, **_kwargs):
        raise RuntimeError("C:\\Users\\KykLa\\secret token=123")


class FakeModels:
    def __init__(self, model):
        self.models = model if isinstance(model, list) else ([model] if model is not None else [])

    def get(self, model_id):
        wanted = int(model_id or 0)
        for model in self.models:
            if int(model.get("id") or model.get("mid") or 0) == wanted:
                return model
        return self.models[0] if self.models else None

    def all(self):
        return list(self.models)


class FakeDecks:
    def all_names_and_ids(self):
        return [SimpleNamespace(id=10, name="Japanese::Core")]


class FakeCollection:
    def __init__(self, rows, model):
        self.db = FakeDb(rows)
        self.models = FakeModels(model)
        self.decks = FakeDecks()


def model_with_fields(*names, model_id=1, name=""):
    first = names[0] if names else "Front"
    back = names[5] if len(names) > 5 else (names[1] if len(names) > 1 else first)
    return {
        "id": model_id,
        "name": name,
        "flds": [{"name": field_name} for field_name in names],
        "tmpls": [{"ord": 0, "name": "Card 1", "qfmt": "{{" + first + "}}", "afmt": "{{FrontSide}}<hr>{{" + back + "}}"}],
        "css": ".card { color: red; }",
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

DEFAULT_NOTE_PROFILE_DIAGNOSTICS = {
    "noteTypeProfilesCount": 0,
    "unknownNoteTypesCount": 0,
    "detectedKinds": {},
    "previewStrategy": "role-based-note-intelligence",
    "missingFieldRoleSource": "detected_roles",
}


def test_triage_candidate_collector_uses_one_bounded_internal_raw_field_path():
    metrics = fresh_import_addon_module("metrics")
    rows = [(
        123, 456, 10, 0, 1, 0, "", "Front\x1f", 1, 0, 1_783_036_800_000, 1_783_036_800_000,
    )]
    col = FakeCollection(rows, model_with_fields("Front", "Meaning"))
    attention, candidates, status = metrics.collect_triage_candidates_with_status(
        col, 1_783_000_000_000, 1_783_100_000_000, max_results=100
    )
    assert status == {
        "status": "available", "itemCount": 1, "skippedCount": 0,
        "truncated": False, "errorCode": None,
    }
    assert candidates == [{
        "cardId": 123, "noteId": 456, "noteTypeId": 1, "templateOrdinal": 0,
        "rawFields": "Front\x1f", "siblingCount": 1,
    }]
    assert all("rawFields" not in item for item in attention)


def test_collect_attention_cards_builds_read_only_payload():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            123,
            456,
            10,
            4,
            1,
            " leech marked ",
            "\x1f".join(["<b>鑑みる</b>", "", "", "", "", "consider", ""]),
            4,
            3,
            50_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(
        rows,
        model_with_fields("Word", "Audio", "Example", "Pitch", "Image", "Meaning", "Part of Speech"),
    )

    payload = metrics.collect_attention_cards(col, 1_783_000_000_000, 1_783_100_000_000)

    assert len(payload) == 1
    assert payload[0] == {
        "cardId": 123,
        "noteId": 456,
        "noteTypeId": 1,
        "deckName": "Japanese::Core",
        "frontPreview": "鑑みる",
        "preview": {
            "frontText": "鑑みる",
            "backText": "consider",
            "primary": "鑑みる",
            "secondary": "consider",
            "tertiary": "consider",
            "mediaBadges": [],
            "noteTypeName": "",
            "cardTemplateName": "Card 1",
            "detectedKind": "japanese_vocab",
        },
        "renderedPreview": {
            "renderStatus": "sanitized",
            "renderSource": "anki_like_fallback",
            "fallbackReason": "native_unavailable_no_get_card",
            "frontHtml": "<b>鑑みる</b>",
            "backHtml": "<b>鑑みる</b><hr>consider",
            "css": "@scope (.card){:scope{color:red;}}",
            "frontPlainText": "鑑みる",
            "backPlainText": "鑑みる consider",
            "mediaRefs": [],
            "cardOrd": 0,
            "cardId": 123,
            "reason": "template renderer",
        },
        "issues": [
            "leech",
            "repeated again",
            "slow answer",
            "low pass rate",
            "missing_audio",
            "missing_example",
            "missing_image",
            "missing_part_of_speech",
        ],
        "riskScore": 100,
        "againCount": 3,
        "lapses": 4,
        "averageAnswerSeconds": 12.5,
        "passRate": 0.25,
        "lastReviewedAt": "2026-07-03",
        "searchQuery": "cid:123",
        "missingFields": [
            "missing_audio",
            "missing_example",
            "missing_image",
            "missing_part_of_speech",
        ],
        "noteTypeName": "",
        "cardTemplateName": "Card 1",
        "detectedKind": "japanese_vocab",
    }

    payload_with_status, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
    )
    assert payload_with_status == payload
    assert status == {
        "status": "available",
        "scannedCards": 1,
        "returnedCards": 1,
        "collectorRan": True,
        "collectionAvailable": True,
        "source": "fresh",
        "revlogRows": 1,
        "candidateCards": 1,
        "notesLoaded": 1,
        "fieldScanCards": 1,
        "cardsTotal": 1,
        "notesTotal": 1,
        "issueCounts": {
            **EMPTY_ISSUE_COUNTS,
            "leech": 1,
            "repeatedAgain": 1,
            "slowAnswer": 1,
            "lowPassRate": 1,
            "missingAudio": 1,
            "missingExample": 1,
            "missingPitch": 0,
            "missingImage": 1,
            "missingPartOfSpeech": 1,
        },
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": 1_783_000_000_000,
        "periodEndRaw": 1_783_100_000_000,
        "periodStartMs": 1_783_000_000_000,
        "periodEndMs": 1_783_100_000_000,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
        "revlogTotalRows": 1,
        "revlogMinId": 1_783_036_800_000,
        "revlogMaxId": 1_783_036_800_000,
        "revlogRowsInPeriod": 1,
        "revlogRowsAfterDeckFilter": 1,
        "noteTypeProfilesCount": 1,
        "unknownNoteTypesCount": 0,
        "detectedKinds": {"japanese_vocab": 1},
        "previewStrategy": "role-based-note-intelligence",
        "missingFieldRoleSource": "detected_roles",
        "noteTypeCatalog": [
            {
                "noteTypeId": 1,
                "name": "Note type 1",
                "noteCount": 1,
                "cardTemplateCount": 1,
                "fields": ["Word", "Audio", "Example", "Pitch", "Image", "Meaning", "Part of Speech"],
                "templates": [{"ord": 0, "name": "Card 1", "qfmtAvailable": True, "afmtAvailable": True}],
                "cssAvailable": True,
                "usedInCurrentCards": True,
            }
        ],
        "noteTypeCatalogCount": 1,
    }


def test_collect_attention_cards_can_skip_full_rendered_preview_for_triage(monkeypatch):
    metrics = fresh_import_addon_module("metrics")
    rows = [(
        123, 456, 10, 8, 1, " leech ", "Front\x1fBack",
        4, 3, 40_000, 1_783_036_800_000,
    )]
    col = FakeCollection(rows, model_with_fields("Front", "Back"))
    monkeypatch.setattr(
        metrics,
        "build_rendered_preview_native_first",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("preview must not render")),
    )

    payload = metrics.collect_attention_cards(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
        include_rendered_preview=False,
    )

    assert len(payload) == 1
    assert "renderedPreview" not in payload[0]
    assert payload[0]["frontPreview"] == "Front"


def test_collect_attention_cards_tolerates_unknown_note_types():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            321,
            654,
            10,
            0,
            999,
            "",
            "<b>Known text</b>",
            2,
            2,
            2_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, None)

    payload = metrics.collect_attention_cards(col, 1_783_000_000_000, 1_783_100_000_000)

    assert payload[0]["frontPreview"] == "Known text"
    assert payload[0]["issues"] == ["repeated again"]
    assert payload[0]["missingFields"] == []


def test_collect_attention_cards_sanitizes_front_preview():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            777,
            888,
            10,
            0,
            1,
            "",
            '<img src="file:///C:/Users/KykLa/secret.png">Word [sound:secret.mp3] C:\\Users\\KykLa\\private.txt',
            2,
            2,
            2_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, model_with_fields("Front"))

    payload = metrics.collect_attention_cards(col, 1_783_000_000_000, 1_783_100_000_000)
    preview = payload[0]["frontPreview"]

    assert preview == "Word"
    assert "<" not in preview
    assert "[sound:" not in preview
    assert "C:\\Users" not in preview
    assert "file://" not in preview


def test_collect_attention_cards_reports_available_empty_scan():
    metrics = fresh_import_addon_module("metrics")
    col = FakeCollection([], model_with_fields("Front"))

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
    )

    assert payload == []
    assert status == {
        "status": "available",
        "scannedCards": 0,
        "returnedCards": 0,
        "reason": "revlog table is empty",
        "collectorRan": True,
        "collectionAvailable": True,
        "source": "fresh",
        "revlogRows": 0,
        "candidateCards": 0,
        "notesLoaded": 0,
        "fieldScanCards": 0,
        "cardsTotal": 0,
        "notesTotal": 0,
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": 1_783_000_000_000,
        "periodEndRaw": 1_783_100_000_000,
        "periodStartMs": 1_783_000_000_000,
        "periodEndMs": 1_783_100_000_000,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
        "revlogTotalRows": 0,
        "revlogMinId": 0,
        "revlogMaxId": 0,
        "revlogRowsInPeriod": 0,
        "revlogRowsAfterDeckFilter": 0,
        **DEFAULT_NOTE_PROFILE_DIAGNOSTICS,
        "noteTypeCatalog": [
            {
                "noteTypeId": 1,
                "name": "Note type 1",
                "noteCount": 0,
                "cardTemplateCount": 1,
                "fields": ["Front"],
                "templates": [{"ord": 0, "name": "Card 1", "qfmtAvailable": True, "afmtAvailable": True}],
                "cssAvailable": True,
                "usedInCurrentCards": False,
            }
        ],
        "noteTypeCatalogCount": 1,
    }


def test_collect_attention_cards_reports_sanitized_error_status():
    metrics = fresh_import_addon_module("metrics")
    col = FakeCollection([], model_with_fields("Front"))
    col.db = RaisingDb()

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
    )

    assert payload == []
    assert status == {
        "status": "error",
        "scannedCards": 0,
        "returnedCards": 0,
        "reason": "Card-level collector failed.",
        "collectorRan": True,
        "collectionAvailable": True,
        "source": "fresh",
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": 1_783_000_000_000,
        "periodEndRaw": 1_783_100_000_000,
        "periodStartMs": 1_783_000_000_000,
        "periodEndMs": 1_783_100_000_000,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
    }


def test_collect_attention_cards_reports_collection_unavailable():
    metrics = fresh_import_addon_module("metrics")

    payload, status = metrics.collect_attention_cards_with_status(
        None,
        1_783_000_000_000,
        1_783_100_000_000,
    )

    assert payload == []
    assert status == {
        "status": "unavailable",
        "scannedCards": 0,
        "returnedCards": 0,
        "collectorRan": True,
        "collectionAvailable": False,
        "source": "fresh",
        "reason": "collection unavailable",
        "issueCounts": EMPTY_ISSUE_COUNTS,
        "thresholds": DEFAULT_THRESHOLDS,
        "periodStartRaw": 1_783_000_000_000,
        "periodEndRaw": 1_783_100_000_000,
        "periodStartMs": 1_783_000_000_000,
        "periodEndMs": 1_783_100_000_000,
        "timeUnitNormalized": False,
        "selectedDeckIdsCount": 0,
        "deckFilterApplied": False,
    }


def test_attention_search_query_falls_back_to_note_or_deck():
    metrics = fresh_import_addon_module("metrics")

    assert metrics._attention_search_query(123, 456, "Japanese::Core", "front") == "cid:123"
    assert metrics._attention_search_query(0, 456, "Japanese::Core", "front") == "nid:456"
    assert (
        metrics._attention_search_query(0, 0, 'Japanese::"Core"', 'front "quoted"')
        == 'deck:"Japanese::\\"Core\\"" front quoted'
    )


def test_collect_attention_cards_counts_issues_before_result_limit():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            100 + index,
            200 + index,
            10,
            8 if index == 0 else 0,
            1,
            "leech" if index == 0 else "",
            "\x1f".join([f"front {index}", "", "", "", "", "meaning", ""]),
            4,
            3,
            50_000,
            1_783_036_800_000,
        )
        for index in range(3)
    ]
    col = FakeCollection(
        rows,
        model_with_fields("Word", "Audio", "Example", "Pitch", "Image", "Meaning", "Part of Speech"),
    )

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
        max_results=1,
    )

    assert len(payload) == 1
    assert status["returnedCards"] == 1
    assert status["scannedCards"] == 3
    assert status["issueCounts"]["repeatedAgain"] == 3
    assert status["issueCounts"]["slowAnswer"] == 3
    assert status["issueCounts"]["missingAudio"] == 3
    assert status["thresholds"] == {**DEFAULT_THRESHOLDS, "maxResults": 1}


def test_collect_attention_cards_normalizes_seconds_timestamps():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            123,
            456,
            10,
            0,
            1,
            "",
            "front",
            2,
            2,
            2_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, model_with_fields("Front"))

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000,
        1_783_100_000,
    )

    assert payload
    assert status["timeUnitNormalized"] is True
    assert status["periodStartMs"] == 1_783_000_000_000
    assert status["periodEndMs"] == 1_783_100_000_000
    assert status["revlogRowsInPeriod"] == 1


def test_collect_attention_cards_preserves_millisecond_timestamps():
    metrics = fresh_import_addon_module("metrics")
    col = FakeCollection([], model_with_fields("Front"))

    _payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
    )

    assert status["timeUnitNormalized"] is False
    assert status["periodStartMs"] == 1_783_000_000_000
    assert status["periodEndMs"] == 1_783_100_000_000


def test_collect_attention_cards_empty_selected_decks_means_all_decks():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            123,
            456,
            10,
            0,
            1,
            "",
            "front",
            2,
            2,
            2_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, model_with_fields("Front"))

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
        deck_ids=[],
    )

    assert payload
    assert status["selectedDeckIdsCount"] == 0
    assert status["deckFilterApplied"] is False
    assert status["revlogRowsAfterDeckFilter"] == 1


def test_collect_attention_cards_reports_deck_filter_removed_rows():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            123,
            456,
            10,
            0,
            1,
            "",
            "front",
            2,
            2,
            2_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, model_with_fields("Front"))

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
        deck_ids=[999],
    )

    assert payload == []
    assert status["reason"] == "deck filter removed all revlog rows"
    assert status["selectedDeckIdsCount"] == 1
    assert status["deckFilterApplied"] is True
    assert status["revlogRowsInPeriod"] == 1
    assert status["revlogRowsAfterDeckFilter"] == 0


def test_collect_attention_cards_reports_no_attention_issues_found():
    metrics = fresh_import_addon_module("metrics")
    rows = [
        (
            123,
            456,
            10,
            0,
            1,
            "",
            "front",
            1,
            0,
            1_000,
            1_783_036_800_000,
        )
    ]
    col = FakeCollection(rows, model_with_fields("Front"))

    payload, status = metrics.collect_attention_cards_with_status(
        col,
        1_783_000_000_000,
        1_783_100_000_000,
    )

    assert payload == []
    assert status["reason"] == "no attention issues found"
    assert status["scannedCards"] == 1
    assert status["returnedCards"] == 0
