from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from gamification_sim import learn_confirmatory as confirmatory


def workspace() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    return workspace().parents[1]


def head_sha() -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository_root()), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def fake_continuity() -> dict:
    return {
        "status": "PASS",
        "bundle_sha256": "a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78",
        "evidence_json_sha256": "d0d79802f8512fa40730aac5c377d75021ff39100330483a784c43ce20b09462",
        "manifest_digest": "fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a",
        "evidence_digest": "5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6",
        "files_sha256": "PASS",
        "archive_inventory": "PASS",
        "tar_gzip_metadata": "PASS",
        "detached_validation": "SKIPPED_FOR_FOCUSED_TEST",
        "accounting": {
            "expected": 340,
            "actual": 340,
            "unique": 340,
            "missing": 0,
            "extra": 0,
            "duplicates": 0,
        },
        "source_identities": {
            "g2_1_contract_blob": "cef3a60bac31eab12faf40f1f2d27221dafc6cc4",
            "g2_2_model_blob": "d892f98485789150807c8e8280cb5194943dd1d2",
            "g2_3_protocol_blob": "f2fda31abcc9a9990229a3193d589214222de241",
            "g2_4_harness_blob": "10980716fb3f058d402ed3d47f1450045892d086",
        },
        "invalid_attempt": {
            "implementation_sha": "ef7c638a70b7bbb7883f512309a1e248118a9203",
            "bundle_sha256": "58989ea862be86e2edb0c71b19aec520214af7bb0abe08791d7f72396d66b2c3",
            "evidence_digest": "51ef8d8caa55a2579795a72f5af1576da69da224a5023190d5fde6c145aac726",
            "status": "INVALID",
            "classification": "HARNESS",
            "old_new_evidence_mixed": False,
            "bundle_validation": "SKIPPED_FOR_FOCUSED_TEST",
            "mode_defect_confirmed": False,
            "member_modes": {},
        },
        "validator_output_sha256": "0" * 64,
    }


@pytest.fixture
def payload(monkeypatch):
    continuity = fake_continuity()
    monkeypatch.setattr(confirmatory, "validate_g2_4_bundle", lambda *args, **kwargs: continuity)
    sha = head_sha()
    monkeypatch.setattr(confirmatory, "BASELINE_SHA", sha)
    frozen = {
        "research/gamification-sim/contracts/learn-xp-problem-contract-v1.json": "cef3a60bac31eab12faf40f1f2d27221dafc6cc4",
        "research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json": "d892f98485789150807c8e8280cb5194943dd1d2",
        "research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json": "f2fda31abcc9a9990229a3193d589214222de241",
        "research/gamification-sim/src/gamification_sim/learn_bounded_screening.py": "10980716fb3f058d402ed3d47f1450045892d086",
    }

    def fixture_blob(root, commit, path):
        if path in frozen:
            return frozen[path]
        return subprocess.check_output(
            ["git", "-C", str(repository_root()), "hash-object", path],
            text=True,
        ).strip()

    monkeypatch.setattr(confirmatory, "_git_blob", fixture_blob)
    return confirmatory.run_confirmatory(
        workspace(),
        implementation_sha=sha,
        base_sha=sha,
        protocol_publication_sha=sha,
        g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
        g2_4_invalid_evidence=None,
        exact_command=(
            "run-learn-xp-confirmatory --implementation-sha <published-sha> "
            "--base-sha <base-sha> --g2-4-evidence <external-g2-4-evidence>"
        ),
        detached_g2_4_validator=False,
    )


def test_protocol_and_exact_manifest_budget():
    protocol, identities = confirmatory.load_and_validate_protocol(workspace())
    units = confirmatory.generate_units(protocol)
    assert len(units) == len({item["unit_id"] for item in units}) == 216
    assert {item["replay_identity"] for item in units} == {"FORWARD", "REVERSE"}
    assert {item["candidate_or_reference_id"] for item in units} == {
        "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING",
        "C-PENDING-SPLIT-D1-NOTE-SIBLING",
        "R-NO-LEARN-XP-NOTE-SIBLING",
    }
    assert identities["schema_draft"] == "https://json-schema.org/draft/2020-12/schema"


def test_core_d1_boundaries_are_inclusive_and_expiry_is_exclusive():
    protocol, _ = confirmatory.load_and_validate_protocol(workspace())
    variant = protocol["variants"][0]
    before = confirmatory._core_result(variant, "C-CORE-D1-BEFORE-MINIMUM")
    exact = confirmatory._core_result(variant, "C-CORE-D1-EXACT-MINIMUM")
    inside = confirmatory._core_result(variant, "C-CORE-D1-JUST-INSIDE-EXPIRY")
    expired = confirmatory._core_result(variant, "C-CORE-D1-EXACT-ELAPSED-EXPIRY")
    assert before["allocation"]["settled_total_lru"] == 0.0
    assert exact["allocation"]["settled_total_lru"] == 1.0
    assert inside["allocation"]["settled_total_lru"] == 1.0
    assert expired["allocation"]["current_total_lru"] == 0.0


def test_pending_split_is_idempotent_non_spendable_and_capped():
    protocol, _ = confirmatory.load_and_validate_protocol(workspace())
    variant = protocol["variants"][1]
    pending = confirmatory._core_result(variant, "C-CORE-REPEATED-AGAIN-RETRY")
    confirmed = confirmatory._core_result(variant, "C-CORE-FAILURE-THEN-SUCCESS")
    assert pending["allocation"]["pending_creation_count"] == 1
    assert pending["allocation"]["pending_lru"] == 0.25
    assert pending["allocation"]["spendable"] is False
    assert confirmed["allocation"]["settled_total_lru"] == 1.0


def test_identity_contract_fails_closed_without_private_content():
    protocol, _ = confirmatory.load_and_validate_protocol(workspace())
    variant = protocol["variants"][0]
    result = confirmatory._identity_result(variant, "I-DELETE-REIMPORT-AMBIGUOUS")
    assert result["identity"]["continuity_code"] == "AMBIGUOUS_FAIL_CLOSED"
    assert result["identity"]["private_content_read"] is False
    assert result["allocation"]["current_total_lru"] == 0.0


def test_both_survivors_are_inconclusive_without_disposable_anki_probe(payload):
    outcomes = {item["candidate_id"]: item for item in payload["candidate_outcomes"]}
    assert set(outcomes) == {
        "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING",
        "C-PENDING-SPLIT-D1-NOTE-SIBLING",
    }
    assert all(item["outcome"] == "CONFIRMATORY_INCONCLUSIVE" for item in outcomes.values())
    assert all(
        item["inconclusive_reason"] == "DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE"
        for item in outcomes.values()
    )
    assert payload["reference"]["outcome"] == "REFERENCE_ONLY"
    assert payload["reference"]["allocation_always_zero"] is True


def test_no_ranking_winner_or_production_boundary(payload):
    assert payload["boundaries"] == {
        "ranking_performed": False,
        "winner_selected": False,
        "recommendation_present": False,
        "final_model_selected": False,
        "production_approved": False,
        "production_integration": False,
        "final_decision_stage_started": False,
    }
    assert all("winner" not in item for item in payload["contrast_ledger"])


def test_detached_validation_rejects_fake_stored_outcome(payload, monkeypatch):
    continuity = fake_continuity()
    monkeypatch.setattr(confirmatory, "validate_g2_4_bundle", lambda *args, **kwargs: continuity)
    tampered = copy.deepcopy(payload)
    tampered["candidate_outcomes"][0]["outcome"] = "CONFIRMATORY_ELIGIBLE"
    with pytest.raises(ValueError, match="candidate outcomes mismatch|schema validation failed"):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )


def test_unknown_fields_and_true_production_flags_are_rejected(payload, monkeypatch):
    continuity = fake_continuity()
    monkeypatch.setattr(confirmatory, "validate_g2_4_bundle", lambda *args, **kwargs: continuity)
    tampered = copy.deepcopy(payload)
    tampered["unknown"] = True
    with pytest.raises(ValueError, match="schema validation failed"):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )
    tampered = copy.deepcopy(payload)
    tampered["boundaries"]["production_approved"] = True
    with pytest.raises(ValueError, match="schema validation failed|boundary violated"):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )


def test_private_paths_and_forbidden_claims_are_rejected(payload, monkeypatch):
    continuity = fake_continuity()
    monkeypatch.setattr(confirmatory, "validate_g2_4_bundle", lambda *args, **kwargs: continuity)
    tampered = copy.deepcopy(payload)
    tampered["provenance"]["exact_command"] = "/home/private/run"
    with pytest.raises(ValueError, match="private content or paths"):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )
    tampered = copy.deepcopy(payload)
    tampered["units"][0]["result"]["explanation"]["reason_codes"] = ["mastered"]
    with pytest.raises(ValueError):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )


def test_bundle_is_byte_identical_across_roots_and_uses_0644(payload, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _, archive_a = confirmatory.write_bundle(payload, first)
    _, archive_b = confirmatory.write_bundle(payload, second)
    assert archive_a.read_bytes() == archive_b.read_bytes()
    assert hashlib.sha256(archive_a.read_bytes()).hexdigest() == hashlib.sha256(archive_b.read_bytes()).hexdigest()
    with tarfile.open(archive_a, "r:gz") as tf:
        assert [item.name for item in tf.getmembers()] == list(confirmatory.BUNDLE_NAMES)
        assert all(
            item.mode == 0o644
            and item.mtime == 0
            and item.uid == 0
            and item.gid == 0
            and item.uname == ""
            and item.gname == ""
            for item in tf.getmembers()
        )


def test_public_command_redacts_private_paths_and_is_stable():
    command = confirmatory._public_command(
        "run-learn-xp-confirmatory",
        [
            "--implementation-sha", "a" * 40,
            "--base-sha", "b" * 40,
            "--g2-4-evidence", "/home/private/valid.tar.gz",
            "--g2-4-invalid-evidence", "/mnt/c/Users/private/invalid.tar.gz",
            "--output-dir", "/home/private/output",
        ],
    )
    assert "/home/private" not in command
    assert "/mnt/c/Users" not in command
    assert "<external-g2-4-evidence>" in command
    assert "<external-invalid-g2-4-evidence>" in command
    assert "<external-output-root>" in command


def test_protocol_rejects_d2_or_s_card(monkeypatch, tmp_path):
    protocol_path = workspace() / confirmatory.PROTOCOL_RELATIVE_PATH
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["variants"][0]["candidate_id"] = "C-CONFIRMATION-ONLY-D2-S-CARD"
    altered = tmp_path / "protocol.json"
    altered.write_text(json.dumps(protocol), encoding="utf-8")
    monkeypatch.setattr(confirmatory, "PROTOCOL_RELATIVE_PATH", altered)
    with pytest.raises((ValueError, TypeError)):
        confirmatory.load_and_validate_protocol(workspace())


def test_result_and_unit_digests_are_path_and_order_independent(payload):
    assert len(payload["units"]) == 216
    assert all(
        row["result_digest"] == confirmatory.canonical_digest(row["result"])
        for row in payload["units"]
    )
    assert all(
        row["unit_digest"] == confirmatory.canonical_digest({**row, "unit_digest": ""})
        for row in payload["units"]
    )


def test_protocol_rejects_hypothesis_condition_drift(monkeypatch):
    protocol_path = workspace() / confirmatory.PROTOCOL_RELATIVE_PATH
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["hypotheses"][0]["required_conditions"] = []
    real_load = confirmatory.load_strict_json

    def altered_load(path, *args, **kwargs):
        if Path(path) == protocol_path:
            return protocol
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(confirmatory, "load_strict_json", altered_load)
    with pytest.raises(ValueError, match="hypothesis registry drifted"):
        confirmatory.load_and_validate_protocol(workspace())


def test_manifest_protocol_provenance_is_strict(payload, monkeypatch):
    continuity = fake_continuity()
    monkeypatch.setattr(confirmatory, "validate_g2_4_bundle", lambda *args, **kwargs: continuity)
    tampered = copy.deepcopy(payload)
    tampered["manifest"]["protocol"]["unknown"] = True
    with pytest.raises(ValueError, match="schema validation failed"):
        confirmatory.validate_evidence(
            tampered,
            workspace=workspace(),
            g2_4_evidence=Path("external-g2-4-evidence.tar.gz"),
            g2_4_invalid_evidence=None,
            detached_g2_4_validator=False,
        )
