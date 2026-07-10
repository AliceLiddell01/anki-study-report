from __future__ import annotations

from datetime import date
import json

import pytest

from conftest import fresh_import_addon_module


@pytest.fixture
def service():
    return fresh_import_addon_module("profile_service")


@pytest.fixture
def snapshot():
    return {
        "daily": [
            {"date": "2024-07-01", "reviews": 10, "pass_count": 8, "fail_count": 2, "study_seconds": 100},
            {"date": "2024-07-02", "reviews": 20, "pass_count": 15, "fail_count": 5, "study_seconds": 200},
            {"date": "2026-07-10", "reviews": 5, "pass_count": 4, "fail_count": 1, "study_seconds": 50},
        ],
        "deckDaily": [
            {"date": "2024-07-01", "deck_id": 1, "deck_name": "Zulu", "reviews": 10},
            {"date": "2024-07-02", "deck_id": 2, "deck_name": "Alpha", "reviews": 20},
            {"date": "2026-07-10", "deck_id": 1, "deck_name": "Zulu", "reviews": 5},
        ],
    }


def test_profile_preferences_defaults_and_corrupt_file(service, tmp_path):
    store = service.ProfilePreferencesStore(tmp_path / "profile.json")
    assert store.read() == {"customStudyStartedOn": None, "deckOverviewSort": "name"}

    store.path.write_text("not json", encoding="utf-8")
    assert store.read() == {"customStudyStartedOn": None, "deckOverviewSort": "name"}


def test_profile_preferences_save_reset_and_atomic_document(service, tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"futureField": {"kept": True}}), encoding="utf-8")
    store = service.ProfilePreferencesStore(path)

    saved = store.update(
        {"customStudyStartedOn": "2021-03-14", "deckOverviewSort": "reviews"},
        today=date(2026, 7, 11),
    )
    assert saved == {"customStudyStartedOn": "2021-03-14", "deckOverviewSort": "reviews"}
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == 1
    assert document["futureField"] == {"kept": True}
    assert not list(tmp_path.glob("*.tmp"))

    assert store.update({"customStudyStartedOn": None}, today=date(2026, 7, 11))["customStudyStartedOn"] is None


@pytest.mark.parametrize("value", ["invalid", "2026-02-30", 123])
def test_profile_preferences_reject_invalid_dates(service, tmp_path, value):
    store = service.ProfilePreferencesStore(tmp_path / "profile.json")
    with pytest.raises(service.ProfileValidationError) as error:
        store.update({"customStudyStartedOn": value}, today=date(2026, 7, 11))
    assert "customStudyStartedOn" in error.value.field_errors


def test_profile_preferences_reject_future_and_unknown_fields(service, tmp_path):
    store = service.ProfilePreferencesStore(tmp_path / "profile.json")
    with pytest.raises(service.ProfileValidationError):
        store.update({"customStudyStartedOn": "2026-07-12"}, today=date(2026, 7, 11))
    with pytest.raises(service.ProfileValidationError) as error:
        store.update({"totalReviews": 999})
    assert error.value.field_errors == {"totalReviews": "Поле нельзя изменять."}


@pytest.mark.parametrize("sort", ["name", "reviews", "active_days"])
def test_profile_preferences_accept_deck_sorts(service, tmp_path, sort):
    store = service.ProfilePreferencesStore(tmp_path / "profile.json")
    assert store.update({"deckOverviewSort": sort})["deckOverviewSort"] == sort


def test_unknown_stored_sort_normalizes_to_name(service, tmp_path):
    path = tmp_path / "profile.json"
    path.write_text('{"deckOverviewSort":"mystery"}', encoding="utf-8")
    assert service.ProfilePreferencesStore(path).read()["deckOverviewSort"] == "name"


def test_profile_storage_is_separate_per_runtime_directory(service, tmp_path):
    first = service.ProfilePreferencesStore(tmp_path / "profile-a" / "profile.json")
    second = service.ProfilePreferencesStore(tmp_path / "profile-b" / "profile.json")
    first.update({"customStudyStartedOn": "2020-01-01"})
    assert first.read()["customStudyStartedOn"] == "2020-01-01"
    assert second.read()["customStudyStartedOn"] is None


def test_profile_payload_exact_public_shape_and_metrics(service, snapshot):
    profile = service.build_profile_payload(
        snapshot,
        "2026-07-11",
        anki_profile_name="E2E",
        preferences={"deckOverviewSort": "name"},
    )

    assert set(profile) == {"identity", "studyHistory", "activity", "decks", "preferences"}
    assert profile["identity"] == {
        "ankiProfileName": "E2E",
        "displayName": "E2E",
        "initials": "E",
        "label": "Локальный профиль",
    }
    assert profile["studyHistory"] == {
        "detectedStartedOn": "2024-07-01",
        "customStartedOn": None,
        "displayedStartedOn": "2024-07-01",
        "statsAvailableFrom": "2024-07-01",
        "totalReviews": 35,
        "activeDays": 3,
        "currentStreak": 1,
        "bestStreak": 2,
        "studyTimeSeconds": 350,
        "studyTimeSource": "revlog_estimate",
        "averagePassRate": 0.7714,
    }
    assert [deck["name"] for deck in profile["decks"]["overview"]] == ["Alpha", "Zulu"]
    assert "token" not in json.dumps(profile).lower()
    assert "addon_data" not in json.dumps(profile).lower()
    json.dumps(profile)


def test_profile_override_changes_identity_date_only(service, snapshot):
    base = service.build_profile_payload(snapshot, "2026-07-11", anki_profile_name="E2E")
    overridden = service.build_profile_payload(
        snapshot,
        "2026-07-11",
        anki_profile_name="E2E",
        preferences={"customStudyStartedOn": "2021-03-01"},
    )
    assert overridden["studyHistory"]["displayedStartedOn"] == "2021-03-01"
    assert overridden["studyHistory"]["statsAvailableFrom"] == "2024-07-01"
    for key in ("totalReviews", "activeDays", "currentStreak", "bestStreak", "studyTimeSeconds", "averagePassRate"):
        assert overridden["studyHistory"][key] == base["studyHistory"][key]
    assert overridden["activity"] == base["activity"]


def test_profile_sorting_uses_all_collection_rows_independent_of_dashboard_scope(service, snapshot):
    by_reviews = service.build_profile_payload(snapshot, "2026-07-11", anki_profile_name="E2E", preferences={"deckOverviewSort": "reviews"})
    by_days = service.build_profile_payload(snapshot, "2026-07-11", anki_profile_name="E2E", preferences={"deckOverviewSort": "active_days"})
    assert [deck["name"] for deck in by_reviews["decks"]["overview"]] == ["Alpha", "Zulu"]
    assert [deck["name"] for deck in by_days["decks"]["overview"]] == ["Zulu", "Alpha"]
    assert by_reviews["studyHistory"]["totalReviews"] == 35


def test_profile_name_fallback_empty_collection_and_large_values(service):
    empty = service.build_profile_payload({}, "2026-07-11", anki_profile_name=None)
    assert empty["identity"]["displayName"] == "Пользователь Anki"
    assert empty["studyHistory"]["detectedStartedOn"] is None
    assert empty["studyHistory"]["studyTimeSeconds"] is None
    assert empty["studyHistory"]["averagePassRate"] is None
    assert empty["activity"]["days"] == []
    assert empty["decks"]["overview"] == []

    large = service.build_profile_payload(
        {"daily": [{"date": "2026-07-10", "reviews": 10**15, "pass_count": 10**15}]},
        "2026-07-11",
        anki_profile_name="非常に長いプロファイル名 " * 20,
    )
    assert large["studyHistory"]["totalReviews"] == 10**15
    json.dumps(large, ensure_ascii=False)
