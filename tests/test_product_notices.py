from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from conftest import fresh_import_addon_module


@pytest.fixture
def service():
    return fresh_import_addon_module("product_notices")


@pytest.fixture
def changelog():
    return {
        "schemaVersion": 1,
        "unreleased": {"sections": []},
        "releases": [
            {
                "version": "1.2.0",
                "date": "2026-07-16",
                "sections": [
                    {"type": "added", "items": [{"id": "privacy", "text": {"ru": "Приватность.", "en": "Privacy."}}]},
                ],
            },
            {
                "version": "1.1.0",
                "date": "2026-07-15",
                "sections": [
                    {"type": "fixed", "items": [{"id": "search_fix", "text": {"ru": "Исправлен поиск.", "en": "Fixed search."}}]},
                ],
            },
            {
                "version": "1.0.0",
                "date": "2026-07-14",
                "sections": [
                    {"type": "added", "items": [{"id": "dashboard", "text": {"ru": "Добавлен dashboard.", "en": "Added dashboard."}}]},
                ],
            },
        ],
    }


def test_notice_store_first_write_update_and_unknown_key_preservation(service, tmp_path):
    path = tmp_path / "product_notices.json"
    store = service.ProductNoticeStore(path)
    assert store.record_started("1.1.0") == {
        "schemaVersion": 1,
        "firstObservedVersion": "1.1.0",
        "lastStartedVersion": "1.1.0",
        "lastSeenReleaseVersion": None,
    }
    document = json.loads(path.read_text(encoding="utf-8"))
    document["futureKey"] = {"preserved": True}
    path.write_text(json.dumps(document), encoding="utf-8")
    store.mark_release_seen("1.1.0")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["futureKey"] == {"preserved": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_notice_store_migrates_legacy_keys_and_preserves_first_version(service, tmp_path):
    path = tmp_path / "product_notices.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 0,
                "first_observed_version": "1.0.0",
                "last_started_version": "1.0.0",
                "last_seen_release_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    state = service.ProductNoticeStore(path).record_started("1.2.0")
    assert state["firstObservedVersion"] == "1.0.0"
    assert state["lastStartedVersion"] == "1.2.0"
    assert state["lastSeenReleaseVersion"] == "1.0.0"


def test_notice_store_preserves_future_schema_and_unknown_keys_on_known_field_update(service, tmp_path):
    path = tmp_path / "product_notices.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 7,
                "firstObservedVersion": "1.0.0",
                "lastStartedVersion": "1.1.0",
                "lastSeenReleaseVersion": "1.0.0",
                "future": {"enabled": True},
            }
        ),
        encoding="utf-8",
    )

    service.ProductNoticeStore(path).record_started("1.2.0")

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schemaVersion"] == 7
    assert saved["future"] == {"enabled": True}
    assert saved["lastStartedVersion"] == "1.2.0"


def test_corrupt_documents_are_quarantined_instead_of_overwritten(service, tmp_path):
    path = tmp_path / "privacy.json"
    path.write_text("not-json", encoding="utf-8")
    state = service.PrivacyStore(path).read()
    assert state["telemetry"]["status"] == "undecided"
    quarantined = list(tmp_path.glob("privacy.json.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == "not-json"
    assert not path.exists()


def test_privacy_accept_and_decline_survive_application_updates(service, tmp_path):
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    accepted = service.PrivacyStore(tmp_path / "accepted" / "privacy.json")
    declined = service.PrivacyStore(tmp_path / "declined" / "privacy.json")
    accepted.save_choices(
        {"purposes": {"reliabilityDiagnostics": True, "featureUsage": False}},
        now=now,
    )
    declined.decline(now=now)
    assert service.PrivacyStore(accepted.path).read()["telemetry"]["status"] == "accepted"
    assert service.PrivacyStore(accepted.path).read()["telemetry"]["effectivePurposes"] == {
        "reliabilityDiagnostics": True,
        "featureUsage": False,
    }
    assert service.PrivacyStore(declined.path).read()["telemetry"]["status"] == "declined"
    assert service.PrivacyStore(declined.path).read()["telemetry"]["effectivePurposes"] == {
        "reliabilityDiagnostics": False,
        "featureUsage": False,
    }


def test_reconsent_pauses_effective_purposes_without_rewriting_old_choice(service, tmp_path):
    path = tmp_path / "privacy.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "telemetry": {
                    "status": "accepted",
                    "consentSchemaVersion": 1,
                    "privacyNoticeVersion": "2026-01-01",
                    "purposes": {"reliabilityDiagnostics": True, "featureUsage": True},
                    "decidedAt": "2026-01-01T00:00:00Z",
                    "deletionPending": False,
                },
            }
        ),
        encoding="utf-8",
    )
    privacy = service.PrivacyStore(path).read()
    assert privacy["telemetry"]["status"] == "accepted"
    assert privacy["requiresConsent"] is True
    assert not any(privacy["telemetry"]["effectivePurposes"].values())


def test_privacy_choices_are_granular_and_reject_unknown_or_non_boolean_values(service, tmp_path):
    store = service.PrivacyStore(tmp_path / "privacy.json")
    with pytest.raises(service.ProductNoticeValidationError) as missing:
        store.save_choices({"purposes": {"reliabilityDiagnostics": True}})
    assert "purposes.featureUsage" in missing.value.field_errors
    with pytest.raises(service.ProductNoticeValidationError) as unknown:
        store.save_choices(
            {
                "purposes": {"reliabilityDiagnostics": False, "featureUsage": False},
                "profileName": "forbidden",
            }
        )
    assert unknown.value.field_errors == {"profileName": "Unexpected field."}
    with pytest.raises(service.ProductNoticeValidationError):
        store.save_choices(
            {"purposes": {"reliabilityDiagnostics": "yes", "featureUsage": False}}
        )


def test_per_profile_isolation_and_no_package_path_write(service, tmp_path):
    package_dir = tmp_path / "anki_study_report"
    first = service.PrivacyStore(tmp_path / "profile-a" / "addon_data" / "addon" / "privacy.json")
    second = service.PrivacyStore(tmp_path / "profile-b" / "addon_data" / "addon" / "privacy.json")
    first.decline()
    assert first.read()["telemetry"]["status"] == "declined"
    assert second.read()["telemetry"]["status"] == "undecided"
    assert not package_dir.exists()


def test_product_notice_response_covers_first_install_and_skipped_versions(service, tmp_path, changelog):
    notice = service.ProductNoticeStore(tmp_path / "product_notices.json")
    privacy = service.PrivacyStore(tmp_path / "privacy.json")
    notice.record_started("1.2.0")
    first = service.product_notices_response("1.2.0", notice, privacy, changelog)
    assert first["showWhatsNew"] is True
    assert first["requiresConsent"] is True
    assert first["unseenReleaseVersions"] == ["1.2.0", "1.1.0", "1.0.0"]

    notice.mark_release_seen("1.0.0")
    updated = service.product_notices_response("1.2.0", notice, privacy, changelog)
    assert updated["unseenReleaseVersions"] == ["1.2.0", "1.1.0"]
    notice.mark_release_seen("1.2.0")
    assert service.product_notices_response("1.2.0", notice, privacy, changelog)["showWhatsNew"] is False

    notice.mark_release_seen("1.3.0")
    rollback = service.product_notices_response("1.2.0", notice, privacy, changelog)
    assert rollback["showWhatsNew"] is False
    assert rollback["unseenReleaseVersions"] == []


def test_changelog_validation_requires_order_locale_parity_and_unique_ids(service, tmp_path, changelog):
    path = tmp_path / "changelog.json"
    path.write_text(json.dumps(changelog, ensure_ascii=False), encoding="utf-8")
    assert [item["version"] for item in service.load_bundled_changelog(path)["releases"]] == [
        "1.2.0",
        "1.1.0",
        "1.0.0",
    ]
    duplicate = json.loads(json.dumps(changelog))
    duplicate["releases"][1]["sections"][0]["items"][0]["id"] = "privacy"
    path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate changelog item ID"):
        service.load_bundled_changelog(path)
    parity = json.loads(json.dumps(changelog))
    del parity["releases"][0]["sections"][0]["items"][0]["text"]["ru"]
    path.write_text(json.dumps(parity), encoding="utf-8")
    with pytest.raises(ValueError, match="locale parity"):
        service.load_bundled_changelog(path)
