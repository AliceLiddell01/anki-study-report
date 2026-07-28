from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from conftest import import_addon_module


service = import_addon_module("inspection_profile_service")
authority = import_addon_module("exact_card_authority")


def model() -> dict:
    return {
        "id": 123,
        "name": "Japanese Vocabulary",
        "type": 0,
        "css": ".card { color: red; }",
        "flds": [
            {"name": "Expression", "ord": 0},
            {"name": "Meaning", "ord": 1},
            {"name": "Audio", "ord": 2},
            {"name": "Example", "ord": 3},
            {"name": "Image", "ord": 4},
        ],
        "tmpls": [
            {
                "name": "Recognition",
                "ord": 0,
                "qfmt": "Static {{Expression}}",
                "afmt": "{{FrontSide}} {{Meaning}} {{Audio}} {{Example}} {{Image}}",
            },
            {
                "name": "Recall",
                "ord": 1,
                "qfmt": "{{Meaning}}",
                "afmt": "{{Expression}}",
            },
        ],
    }


def confirmed_profile(structure: dict) -> dict:
    return {
        "profileId": "note-type-123",
        "noteTypeId": "123",
        "noteTypeName": structure["name"],
        "storedState": "confirmed",
        "displayName": "Japanese vocabulary",
        "expectedFingerprint": structure["fingerprint"],
        "appliesTo": {"templateOrdinals": []},
        "fieldMappings": [
            {"role": "term", "fields": [{"ordinal": 0, "name": "Expression"}]},
            {"role": "meaning", "fields": [{"ordinal": 1, "name": "Meaning"}]},
            {"role": "audio", "fields": [{"ordinal": 2, "name": "Audio"}]},
            {"role": "example", "fields": [{"ordinal": 3, "name": "Example"}]},
            {"role": "image", "fields": [{"ordinal": 4, "name": "Image"}]},
        ],
        "checks": [
            {"checkId": "meaning-required", "kind": "non_empty", "roles": ["meaning"], "mode": "any", "priority": "high"},
            {"checkId": "audio-required", "kind": "contains_audio", "roles": ["audio"], "mode": "any", "priority": "medium"},
            {"checkId": "image-required", "kind": "contains_image", "roles": ["image"], "mode": "any", "priority": "low"},
            {"checkId": "example-length", "kind": "min_text_length", "roles": ["example"], "mode": "any", "minLength": 4, "priority": "medium"},
            {"checkId": "term-or-meaning", "kind": "one_of_roles_non_empty", "roles": ["term", "meaning"], "priority": "low"},
            {"checkId": "term-and-meaning", "kind": "all_roles_non_empty", "roles": ["term", "meaning"], "priority": "high"},
        ],
        "confirmedAt": "2026-07-18T00:00:00Z",
        "updatedAt": "2026-07-18T00:00:00Z",
    }


def test_fingerprint_is_semantic_deterministic_and_ignores_css_and_static_text():
    original = service.build_note_type_structure(model())
    same = deepcopy(model())
    same["css"] = ".card { background: blue; }"
    same["tmpls"][0]["qfmt"] = "Completely different static text {{Expression}}"
    assert service.build_note_type_structure(same)["fingerprint"] == original["fingerprint"]

    renamed = deepcopy(model())
    renamed["flds"][1]["name"] = "Definition"
    renamed["tmpls"][0]["afmt"] = renamed["tmpls"][0]["afmt"].replace("Meaning", "Definition")
    assert service.build_note_type_structure(renamed)["fingerprint"] != original["fingerprint"]

    changed_usage = deepcopy(model())
    changed_usage["tmpls"][1]["afmt"] += " {{Example}}"
    assert service.build_note_type_structure(changed_usage)["fingerprint"] != original["fingerprint"]


def test_only_confirmed_current_profile_is_authoritative():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    assert service.effective_profile_state(profile, structure) == {
        "state": "confirmed", "reason": None, "authoritative": True
    }
    for state in ("suggested", "disabled"):
        changed = {**profile, "storedState": state, "confirmedAt": None}
        assert service.effective_profile_state(changed, structure)["authoritative"] is False
    stale = deepcopy(profile)
    stale["expectedFingerprint"] = {"algorithm": "sha256", "value": "0" * 64}
    assert service.effective_profile_state(stale, structure) == {
        "state": "needs_review", "reason": "fingerprint_mismatch", "authoritative": False
    }
    assert service.effective_profile_state(profile, None)["reason"] == "note_type_missing"


def test_allowlisted_runtime_emits_typed_safe_evidence_without_raw_content():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    candidate = {
        "cardId": 7,
        "noteId": 8,
        "noteTypeId": 123,
        "templateOrdinal": 0,
        "rawFields": "猫\x1f<span> </span>\x1fno marker\x1fabc\x1f<div>none</div>",
        "siblingCount": 2,
    }
    failures = service.evaluate_inspection_profile(profile, structure, candidate, profile_revision=4)
    assert [item["checkId"] for item in failures] == [
        "meaning-required", "audio-required", "image-required", "example-length", "term-and-meaning"
    ]
    reason = service.content_reason_from_failure(failures[0])
    assert reason["reasonId"] == "profile:note-type-123:check:meaning-required"
    assert reason["scope"] == "note"
    assert reason["evidence"][0]["affectedSiblingCount"] == 2
    encoded = str(failures)
    assert "猫" not in encoded
    assert "no marker" not in encoded
    assert "abc" not in encoded


def test_group_checks_evaluate_roles_not_individual_mapped_fields():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    profile["fieldMappings"][1]["fields"].append({"ordinal": 3, "name": "Example"})
    profile["checks"] = [
        {"checkId": "required-group", "kind": "all_roles_non_empty", "roles": ["term", "meaning"], "priority": "high"}
    ]
    candidate = {
        "cardId": 7, "noteId": 8, "noteTypeId": 123, "templateOrdinal": 0,
        "rawFields": "term\x1f\x1fmeaning fallback\x1funused\x1f", "siblingCount": 1,
    }
    assert service.evaluate_inspection_profile(profile, structure, candidate, profile_revision=1) == []


def test_suggestions_are_deterministic_non_authoritative_and_do_not_contain_samples():
    structure = service.build_note_type_structure(model())
    first = service.suggest_inspection_profile(structure)
    assert first == service.suggest_inspection_profile(structure)
    assert any(mapping["role"] == "meaning" for mapping in first["fieldMappings"])
    assert "confirmed" not in str(first).lower()
    assert "rawFields" not in str(first)


def test_suggestion_preserves_multiple_exact_fields_and_leaves_low_confidence_unresolved():
    custom = {
        "id": 987,
        "name": "Custom vocabulary",
        "type": 0,
        "flds": [
            {"name": "Word", "ord": 0},
            {"name": "Vocabulary", "ord": 1},
            {"name": "Mystery", "ord": 2},
        ],
        "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Word}} {{Vocabulary}}", "afmt": "{{Mystery}}"}],
    }

    suggestion = service.suggest_inspection_profile(service.build_note_type_structure(custom))
    term = next(item for item in suggestion["fieldMappings"] if item["role"] == "term")
    assert term["fields"] == [{"ordinal": 0, "name": "Word"}, {"ordinal": 1, "name": "Vocabulary"}]
    assert suggestion["unresolvedFields"] == [{"ordinal": 2, "name": "Mystery"}]
    assert suggestion["warnings"] == ["unresolved_fields", "no_checks_suggested"]


def test_validate_v2_selects_a_bounded_deterministic_note_type_sample_without_values():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)

    class Models:
        def all(self):
            return [model()]

    class Db:
        def __init__(self):
            self.sample_limits = []

        def all(self, query, *args):
            if "where n.mid = ?" in query:
                self.sample_limits.append(args)
                return [
                    (9, 90, 123, 0, "PRIVATE_RAW_A\x1f\x1f\x1f\x1f"),
                    (10, 100, 123, 1, "PRIVATE_RAW_B\x1fPRIVATE_RAW_C\x1f\x1fPRIVATE_RAW_D\x1f"),
                    (11, 110, 123, 0, "PRIVATE_RAW_E\x1fPRIVATE_RAW_F\x1f\x1f\x1f"),
                ]
            if "count(*)" in query:
                return [(90, 2), (100, 1)]
            raise AssertionError(query)

    db = Db()
    col = SimpleNamespace(models=Models(), db=db)
    response = service.execute_inspection_validate(col, {
        "schemaVersion": 2,
        "profile": profile,
        "preview": {"mode": "sample", "limit": 2},
    })
    assert response["schemaVersion"] == 2
    assert response["valid"] is True
    assert response["preview"]["requestedCount"] == 2
    assert response["preview"]["evaluatedCount"] == 2
    assert response["preview"]["truncated"] is True
    assert db.sample_limits == [(123, 3)]
    encoded = str(response)
    assert "PRIVATE_RAW" not in encoded


def test_validate_v2_rejects_unknown_preview_fields_and_preserves_v1_empty_ids():
    with pytest.raises(service.InspectionProfileValidationError):
        service.normalize_inspection_validate_request({
            "schemaVersion": 2,
            "profile": confirmed_profile(service.build_note_type_structure(model())),
            "preview": {"mode": "sample", "limit": 5, "query": "deck:private"},
        })
    normalized = service.normalize_inspection_validate_request({
        "schemaVersion": 1,
        "profile": confirmed_profile(service.build_note_type_structure(model())),
        "cardIds": [],
    })
    assert normalized["schemaVersion"] == 1
    assert normalized["cardIds"] == []


def test_triage_content_reason_is_note_deduped_and_workset_order_selects_representative():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    profile["checks"] = [
        {"checkId": "meaning-required", "kind": "non_empty", "roles": ["meaning"], "mode": "any", "priority": "high"}
    ]

    class Models:
        def all(self):
            return [model()]

    class Db:
        def all(self, query, *_args):
            assert "count(*)" in query
            return [(8, 2)]

    col = SimpleNamespace(models=Models(), db=Db())
    candidates = [
        {"cardId": 20, "noteId": 8, "noteTypeId": 123, "templateOrdinal": 1, "rawFields": "term\x1f\x1f\x1f\x1f", "siblingCount": 1},
        {"cardId": 10, "noteId": 8, "noteTypeId": 123, "templateOrdinal": 0, "rawFields": "term\x1f\x1f\x1f\x1f", "siblingCount": 1},
    ]
    snapshot = {"status": "available", "revision": 4, "profiles": [profile]}
    workset = service.evaluate_profiles_for_triage(col, candidates, snapshot, dataset="search_workset")
    automatic = service.evaluate_profiles_for_triage(col, candidates, snapshot, dataset="automatic")
    assert len(workset["reasons"]) == len(automatic["reasons"]) == 1
    assert workset["reasons"][0]["cardId"] == 20
    assert automatic["reasons"][0]["cardId"] == 10
    evidence = workset["reasons"][0]["reason"]["evidence"][0]
    assert evidence["affectedSiblingCount"] == 2
    assert workset["reasons"][0]["reason"]["reasonId"] == "profile:note-type-123:check:meaning-required"


def test_exact_card_authority_ignores_unrelated_profile_health_but_aggregate_warning_remains(monkeypatch):
    structure_a = service.build_note_type_structure(model())
    model_b = deepcopy(model())
    model_b.update({"id": 456, "name": "Programming"})
    structure_b = service.build_note_type_structure(model_b)
    profile_a = confirmed_profile(structure_a)
    profile_b = confirmed_profile(structure_b)
    profile_b.update({
        "profileId": "note-type-456",
        "noteTypeId": "456",
        "noteTypeName": structure_b["name"],
        "expectedFingerprint": {"algorithm": "sha256", "value": "0" * 64},
    })
    snapshot = {"status": "available", "revision": 4, "profiles": [profile_a, profile_b]}
    candidate = {
        "cardId": 1,
        "noteId": 8,
        "noteTypeId": 123,
        "templateOrdinal": 0,
        "rawFields": "term\x1fmeaning\x1f[sound:voice.mp3]\x1flong example\x1f<img src=\"image.png\">",
        "siblingCount": 1,
    }
    monkeypatch.setattr(service, "attach_sibling_counts", lambda _col, values: values)
    col = SimpleNamespace(models=SimpleNamespace(all=lambda: [model(), model_b]))

    aggregate = service.evaluate_profiles_for_triage(col, [candidate], snapshot, dataset="search_workset")
    exact = service.evaluate_profiles_for_triage(
        col,
        [candidate],
        snapshot,
        dataset="search_workset",
        exact_note_type_id=123,
        previous_reason_ids=("learning:learning.repeated_again",),
    )

    assert aggregate["sourceStatus"]["status"] == "partial"
    assert aggregate["contentChecks"]["needsReviewProfileCount"] == 1
    assert exact["sourceStatus"]["status"] == "empty"
    assert exact["contentChecks"]["status"] == "available"
    assert exact["contentChecks"]["needsReviewProfileCount"] == 0
    assert exact["reasons"] == []


def test_exact_card_authority_fails_closed_only_for_relevant_dependencies(monkeypatch):
    structure = service.build_note_type_structure(model())
    stale = confirmed_profile(structure)
    stale["expectedFingerprint"] = {"algorithm": "sha256", "value": "0" * 64}
    col = SimpleNamespace(models=SimpleNamespace(all=lambda: [model()]))
    monkeypatch.setattr(service, "attach_sibling_counts", lambda _col, values: values)
    candidate = {
        "cardId": 1, "noteId": 8, "noteTypeId": 123, "templateOrdinal": 0,
        "rawFields": "term\x1fmeaning\x1f[sound:voice.mp3]\x1flong example\x1f<img src=\"image.png\">",
    }

    relevant_stale = service.evaluate_profiles_for_triage(
        col,
        [candidate],
        {"status": "available", "revision": 4, "profiles": [stale]},
        dataset="search_workset",
        exact_note_type_id=123,
        previous_reason_ids=("learning:learning.repeated_again",),
    )
    lost_previous_content = service.evaluate_profiles_for_triage(
        col,
        [candidate],
        {"status": "available", "revision": 4, "profiles": []},
        dataset="search_workset",
        exact_note_type_id=123,
        previous_reason_ids=("profile:note-type-123:check:audio-required",),
    )

    assert relevant_stale["sourceStatus"]["status"] == "partial"
    assert relevant_stale["contentChecks"]["status"] == "profiles_need_review"
    assert lost_previous_content["sourceStatus"]["status"] == "partial"
    assert lost_previous_content["sourceStatus"]["errorCode"] == "profile_authority_changed"


@pytest.mark.parametrize("store_status", ["corrupt", "future_schema", "unavailable"])
def test_exact_card_learning_only_authority_does_not_depend_on_unrelated_unreadable_inventory(store_status):
    scope = authority.scope_exact_card_profile(
        {"status": store_status, "profiles": []},
        note_type_id=123,
        previous_reason_ids=("learning:learning.repeated_again",),
    )
    assert scope.profile is None
    assert scope.requires_profile_authority is False
    assert scope.blocking_error_code is None


def test_programming_suggestion_has_question_answer_without_audio_and_media_checks_pass():
    programming = {
        "id": 456,
        "name": "Programming",
        "type": 0,
        "flds": [{"name": "Question", "ord": 0}, {"name": "Answer", "ord": 1}, {"name": "Code", "ord": 2}],
        "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Question}}", "afmt": "{{Answer}} {{Code}}"}],
    }
    suggestion = service.suggest_inspection_profile(service.build_note_type_structure(programming))
    assert {item["role"] for item in suggestion["fieldMappings"]} >= {"question", "answer"}
    assert {item["checkId"] for item in suggestion["checks"]} == {"question-required", "answer-required"}
    assert all("audio" not in str(item) for item in suggestion["checks"])

    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    candidate = {
        "cardId": 1, "noteId": 2, "noteTypeId": 123, "templateOrdinal": 0,
        "rawFields": "term\x1fmeaning\x1f[sound:voice.mp3]\x1f十分に長い例\x1f<img src=\"image.png\">",
        "siblingCount": 1,
    }
    assert service.evaluate_inspection_profile(profile, structure, candidate, profile_revision=1) == []


def test_template_scope_and_cloze_kind_are_exact_and_fail_closed():
    structure = service.build_note_type_structure(model())
    profile = confirmed_profile(structure)
    profile["appliesTo"] = {"templateOrdinals": [1]}
    candidate = {
        "cardId": 1, "noteId": 2, "noteTypeId": 123, "templateOrdinal": 0,
        "rawFields": "\x1f\x1f\x1f\x1f", "siblingCount": 1,
    }
    assert service.evaluate_inspection_profile(profile, structure, candidate, profile_revision=1) == []

    cloze = deepcopy(model())
    cloze["type"] = 1
    cloze["name"] = "Not named Cloze"
    standard_named_cloze = deepcopy(model())
    standard_named_cloze["type"] = 0
    standard_named_cloze["name"] = "Cloze-looking standard"
    assert service.build_note_type_structure(cloze)["kind"] == "cloze"
    assert service.build_note_type_structure(standard_named_cloze)["kind"] == "standard"
