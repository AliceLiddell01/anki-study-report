from __future__ import annotations

import importlib.util
import shutil

import pytest

from gamification_sim.fsrs_reference import verify_fsrs_reference


ROOT = __import__("pathlib").Path(__file__).parents[1]
CONTRACT = ROOT / "contracts" / "fsrs-trajectories-v0.1.json"


@pytest.mark.skipif(importlib.util.find_spec("fsrs") is None, reason="optional fsrs extra is not installed")
def test_official_fsrs_references_are_reproducible_and_preserve_reward_baseline():
    cargo = __import__("pathlib").Path.home() / ".cargo" / "bin" / "cargo.exe"
    if not cargo.is_file() and shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    first = verify_fsrs_reference(CONTRACT, ROOT)
    repeated = verify_fsrs_reference(CONTRACT, ROOT)
    assert first["manifest"]["output_digest"] == repeated["manifest"]["output_digest"]
    assert first["manifest"]["py_fsrs_version"] == "6.3.1"
    assert first["manifest"]["fsrs_rs_crate_version"] == "6.6.1"
    assert not first["comparison"]["state_mismatches"]
    assert first["comparison"]["known_interval_differences"]
    assert first["reward_integration"]["all_baselines_equal"] is True
    assert first["reward_integration"]["core_baseline"] == 0.9


def test_fsrs_contract_has_no_real_collection_fields():
    text = CONTRACT.read_text(encoding="utf-8")
    assert all(value not in text for value in ("card_text", "deck_name", "revlog", "collection_path"))
