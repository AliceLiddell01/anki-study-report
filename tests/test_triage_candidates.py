from __future__ import annotations

from conftest import import_addon_module

candidates = import_addon_module("triage_candidates")


class FakeDb:
    def __init__(self, note_rows, card_rows):
        self.note_rows = note_rows
        self.card_rows = card_rows
        self.calls = []

    def all(self, sql, *params):
        self.calls.append((sql, params))
        if "select distinct n.id" in sql:
            return list(self.note_rows)
        if "with sibling_counts" in sql:
            return list(self.card_rows)
        if "from revlog r" in sql:
            return list(self.note_rows)
        raise AssertionError(sql)


class FakeCol:
    def __init__(self, db):
        self.db = db


def profile(note_type_id="7", *, state="confirmed", checks=None, ordinals=None):
    return {
        "profileId": f"note-type-{note_type_id}",
        "noteTypeId": note_type_id,
        "storedState": state,
        "checks": checks if checks is not None else [{"checkId": "audio-required"}],
        "appliesTo": {"templateOrdinals": ordinals or []},
    }


def snapshot(*profiles):
    return {"status": "available", "revision": 3, "profiles": list(profiles)}


def structure(note_type_id="7"):
    return {"noteTypeId": note_type_id, "fingerprint": {"value": "a" * 64}}


def patch_profiles(monkeypatch, *, failures=True):
    monkeypatch.setattr(
        candidates,
        "read_note_type_structures",
        lambda _col, ids, limit: {"status": "available", "items": [structure(str(value)) for value in ids]},
    )
    monkeypatch.setattr(
        candidates,
        "effective_profile_state",
        lambda item, _structure: {
            "state": item["storedState"],
            "authoritative": item["storedState"] == "confirmed",
        },
    )
    monkeypatch.setattr(
        candidates,
        "evaluate_inspection_profile",
        lambda _profile, _structure, candidate, profile_revision: ([{
            "profileId": "note-type-7",
            "checkId": "audio-required",
            "checkKind": "contains_audio",
            "scope": "note",
            "priority": "medium",
            "targetRoles": ["audio"],
            "mappedFields": [],
            "evidence": {
                "expectedCondition": "any_contains_audio",
                "actualTextLength": None,
                "expectedTextLength": None,
                "marker": "audio",
                "markerPresent": False,
            },
            "profileRevision": profile_revision,
            "fingerprint": "a" * 64,
            "affectedSiblingCount": candidate["siblingCount"],
            "templateOrdinals": [],
        }] if failures else []),
    )
    monkeypatch.setattr(
        candidates,
        "content_reason_from_failure",
        lambda failure: {
            "reasonId": "profile:note-type-7:check:audio-required",
            "code": "content.audio_missing",
            "family": "content",
            "scope": "note",
            "priority": "medium",
            "sources": ["profile_checks"],
            "evidence": [{"kind": "profile_check", "affectedSiblingCount": failure["affectedSiblingCount"]}],
            "detectedAtMs": None,
        },
    )
    monkeypatch.setattr(candidates, "expand_deck_ids", lambda _col, ids: ids)


def test_zero_reviews_do_not_block_current_content(monkeypatch):
    patch_profiles(monkeypatch)
    db = FakeDb([(100,)], [(10, 100, 1, 0, 7, "term\x1f", 2)])
    result = candidates.collect_current_content_candidates(FakeCol(db), [], None, snapshot(profile()))
    assert [row["reason"]["code"] for row in result["reasons"]] == ["content.audio_missing"]
    assert result["sourceStatus"]["scannedNoteCount"] == 1
    assert result["contentChecks"]["evaluatedNoteCount"] == 1
    assert len(db.calls) == 2


def test_period_is_not_an_input_to_current_content(monkeypatch):
    patch_profiles(monkeypatch)
    db1 = FakeDb([(100,)], [(10, 100, 1, 0, 7, "term\x1f", 1)])
    db2 = FakeDb([(100,)], [(10, 100, 1, 0, 7, "term\x1f", 1)])
    left = candidates.collect_current_content_candidates(FakeCol(db1), [], None, snapshot(profile()))
    right = candidates.collect_current_content_candidates(FakeCol(db2), [], None, snapshot(profile()))
    assert left == right


def test_no_confirmed_profiles_skips_content_sql(monkeypatch):
    patch_profiles(monkeypatch)
    db = FakeDb([], [])
    result = candidates.collect_current_content_candidates(FakeCol(db), [], None, snapshot(profile(state="suggested")))
    assert db.calls == []
    assert result["sourceStatus"]["status"] == "empty"
    assert result["sourceStatus"]["errorCode"] == "no_confirmed_profiles"


def test_keyset_truncation_and_representative_are_deterministic(monkeypatch):
    patch_profiles(monkeypatch)
    note_rows = [(value,) for value in range(1, candidates.CONTENT_SCAN_NOTE_LIMIT + 2)]
    card_rows = [
        (20, 1, 1, 0, 7, "x", 2),
        (10, 1, 1, 0, 7, "x", 2),
    ] + [
        (1000 + value, value, 1, 0, 7, "x", 1)
        for value in range(2, candidates.CONTENT_SCAN_NOTE_LIMIT + 1)
    ]
    db = FakeDb(note_rows, card_rows)
    result = candidates.collect_current_content_candidates(FakeCol(db), [], None, snapshot(profile()))
    assert result["sourceStatus"]["truncated"] is True
    assert result["sourceStatus"]["nextCursor"] == str(candidates.CONTENT_SCAN_NOTE_LIMIT)
    first = next(row for row in result["reasons"] if row["noteId"] == 1)
    assert first["cardId"] == 10
    assert first["reason"]["evidence"][0]["affectedSiblingCount"] == 2
    assert len(db.calls) == 2


def test_continuation_uses_strict_note_id_cursor(monkeypatch):
    patch_profiles(monkeypatch)
    db = FakeDb([(501,)], [(1501, 501, 1, 0, 7, "x", 1)])
    candidates.collect_current_content_candidates(FakeCol(db), [], 500, snapshot(profile()))
    note_sql, note_params = db.calls[0]
    assert "n.id > ?" in note_sql
    assert 500 in note_params


def test_programming_profile_without_audio_check_has_no_audio_failure(monkeypatch):
    patch_profiles(monkeypatch, failures=False)
    db = FakeDb([(200,)], [(20, 200, 1, 0, 8, "question\x1fanswer", 1)])
    result = candidates.collect_current_content_candidates(
        FakeCol(db), [], None, snapshot(profile("8", checks=[{"checkId": "question"}, {"checkId": "answer"}]))
    )
    assert result["reasons"] == []
    assert result["contentChecks"]["evaluatedNoteCount"] == 1


def test_learning_source_is_period_bound_and_reads_no_note_fields(monkeypatch):
    monkeypatch.setattr(candidates, "expand_deck_ids", lambda _col, ids: ids)
    row = (10, 100, 0, 7, 0, "", 4, 3, 4000, 1700)
    db = FakeDb([row], [])
    result, status = candidates.collect_learning_triage_candidates_with_status(
        FakeCol(db), 1000, 2000, [], max_results=100
    )
    assert result[0]["issues"] == ["repeated_again", "low_pass_rate"]
    sql, params = db.calls[0]
    assert "n.flds" not in sql
    assert 1000 in params and 2000 in params
    assert status["status"] == "available"
