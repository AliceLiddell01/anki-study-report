from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import import_addon_module


store_module = import_addon_module("inspection_profile_store")


def profile(*, state: str = "confirmed") -> dict:
    return {
        "profileId": "note-type-123",
        "noteTypeId": "123",
        "noteTypeName": "Basic",
        "storedState": state,
        "displayName": "Basic",
        "expectedFingerprint": {"algorithm": "sha256", "value": "a" * 64},
        "appliesTo": {"templateOrdinals": []},
        "fieldMappings": [{"role": "meaning", "fields": [{"ordinal": 1, "name": "Meaning"}]}],
        "checks": [
            {
                "checkId": "meaning-required",
                "kind": "non_empty",
                "roles": ["meaning"],
                "mode": "any",
                "priority": "high",
            }
        ],
        "confirmedAt": "2026-07-18T00:00:00Z" if state == "confirmed" else None,
        "updatedAt": "2026-07-18T00:00:00Z",
    }


def test_missing_atomic_revision_disable_delete_and_conflict(tmp_path: Path):
    path = tmp_path / "addon_data" / "addon" / "inspection_profiles.json"
    store = store_module.InspectionProfileStore(path)
    assert store.read() == {
        "status": "empty", "revision": 0, "profiles": [], "errorCode": None, "quarantined": False
    }

    saved = store.save_profile(profile(), expected_revision=0)
    assert saved["revision"] == 1
    assert json.loads(path.read_text(encoding="utf-8"))["profiles"][0]["noteTypeId"] == "123"
    assert list(path.parent.glob("*.tmp")) == []

    with pytest.raises(store_module.InspectionProfileConflictError) as conflict:
        store.save_profile(profile(), expected_revision=0)
    assert conflict.value.current_revision == 1

    disabled = store.disable_profile("123", expected_revision=1, updated_at="2026-07-18T01:00:00Z")
    assert disabled["revision"] == 2
    assert disabled["profiles"][0]["storedState"] == "disabled"
    deleted = store.delete_profile("123", expected_revision=2)
    assert deleted["revision"] == 3
    assert deleted["profiles"] == []


def test_corruption_is_quarantined_and_future_schema_is_preserved(tmp_path: Path):
    path = tmp_path / "inspection_profiles.json"
    path.write_text("{broken", encoding="utf-8")
    store = store_module.InspectionProfileStore(path)
    corrupt = store.read()
    assert corrupt["status"] == "corrupt"
    assert corrupt["quarantined"] is True
    assert not path.exists()
    assert len(list(tmp_path.glob("inspection_profiles.json.corrupt-*"))) == 1

    future = {"schemaVersion": 99, "revision": 7, "profiles": [], "future": {"keep": True}}
    path.write_text(json.dumps(future), encoding="utf-8")
    assert store.read()["status"] == "future_schema"
    with pytest.raises(store_module.UnsupportedInspectionProfileSchemaError):
        store.save_profile(profile(), expected_revision=0)
    assert json.loads(path.read_text(encoding="utf-8")) == future


def test_python_validator_and_draft_2020_12_schema_agree_on_parity_fixtures():
    jsonschema = pytest.importorskip("jsonschema")
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "inspection-profile-v1.schema.json").read_text(encoding="utf-8"))
    fixture = json.loads((root / "tests" / "fixtures" / "inspection_profiles" / "parity-v1.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.check_schema(schema)

    for case in fixture["cases"]:
        schema_valid = not list(validator.iter_errors(case["document"]))
        try:
            store_module.validate_inspection_profile_document(deepcopy(case["document"]))
            python_valid = True
        except store_module.InspectionProfileValidationError:
            python_valid = False
        assert schema_valid == python_valid == case["valid"], case["name"]


def test_strict_allowlist_rejects_unmapped_roles_duplicates_and_code_fields():
    value = profile(state="suggested")
    value["checks"][0]["roles"] = ["audio"]
    value["checks"][0]["python"] = "open('/tmp/x')"
    with pytest.raises(store_module.InspectionProfileValidationError) as error:
        store_module.validate_inspection_profile(value)
    assert "profile.checks.0.python" in error.value.field_errors
    assert "profile.checks.0.roles" in error.value.field_errors


def test_concurrent_writers_have_one_winner_and_deterministic_document(tmp_path: Path):
    path = tmp_path / "inspection_profiles.json"
    store = store_module.InspectionProfileStore(path)

    def write_once():
        try:
            return store.save_profile(profile(), expected_revision=0)["revision"]
        except store_module.InspectionProfileConflictError as error:
            return f"conflict:{error.current_revision}"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(lambda _index: write_once(), range(2)), key=str)
    assert results == [1, "conflict:1"]
    first = path.read_bytes()
    assert first.endswith(b"\n")
    assert json.loads(first)["revision"] == 1


def test_write_failure_and_size_cap_preserve_previous_document(monkeypatch, tmp_path: Path):
    path = tmp_path / "inspection_profiles.json"
    store = store_module.InspectionProfileStore(path)
    store.save_profile(profile(), expected_revision=0)
    original = path.read_bytes()
    monkeypatch.setattr(store_module.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        store.save_profile(profile(), expected_revision=1)
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []

    oversized = profile(state="suggested")
    oversized["fieldMappings"][0]["fields"] = [
        {"ordinal": index, "name": f"Field {index} " + "x" * 140}
        for index in range(16)
    ]
    small_store = store_module.InspectionProfileStore(tmp_path / "small.json", max_document_bytes=1024)
    with pytest.raises(store_module.InspectionProfileValidationError):
        small_store.save_profile(oversized, expected_revision=0)
    assert not small_store.path.exists()


def test_document_rejects_duplicate_profile_note_type_role_check_and_bounds():
    base = profile(state="suggested")
    variants = []
    duplicate_profiles = {"schemaVersion": 1, "revision": 0, "profiles": [base, deepcopy(base)]}
    variants.append(duplicate_profiles)
    duplicate_role = deepcopy(base)
    duplicate_role["fieldMappings"].append({"role": "meaning", "fields": [{"ordinal": 2, "name": "Other"}]})
    variants.append({"schemaVersion": 1, "revision": 0, "profiles": [duplicate_role]})
    duplicate_check = deepcopy(base)
    duplicate_check["checks"].append(deepcopy(duplicate_check["checks"][0]))
    variants.append({"schemaVersion": 1, "revision": 0, "profiles": [duplicate_check]})
    invalid_ordinal = deepcopy(base)
    invalid_ordinal["fieldMappings"][0]["fields"][0]["ordinal"] = 64
    variants.append({"schemaVersion": 1, "revision": 0, "profiles": [invalid_ordinal]})
    invalid_priority = deepcopy(base)
    invalid_priority["checks"][0]["priority"] = "critical"
    variants.append({"schemaVersion": 1, "revision": 0, "profiles": [invalid_priority]})
    for value in variants:
        with pytest.raises(store_module.InspectionProfileValidationError):
            store_module.validate_inspection_profile_document(value)
