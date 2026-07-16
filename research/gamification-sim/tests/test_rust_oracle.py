from __future__ import annotations

import shutil

import pytest

from gamification_sim.canonical_json import canonical_dumps
from gamification_sim.rust_oracle import build_differential_cases, verify_rust_oracle


ROOT = __import__("pathlib").Path(__file__).parents[1]


def test_differential_corpus_has_every_required_source_class():
    cases = build_differential_cases(ROOT, "R-CURRENT")
    counts = {
        source: sum(item["source"] == source for item in cases)
        for source in {item["source"] for item in cases}
    }
    assert counts == {
        "golden": 31,
        "scenario": 43,
        "threshold": 42,
        "survivor": 14,
        "property-edge": 3,
        "invalid": 2,
    }
    assert len({item["case_id"] for item in cases}) == len(cases)


@pytest.mark.skipif(not (ROOT.parent.parent / ".git").exists(), reason="requires repository checkout")
def test_python_and_rust_oracle_match_for_full_contract():
    cargo = __import__("pathlib").Path.home() / ".cargo" / "bin" / "cargo.exe"
    if not cargo.is_file() and shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    payload = verify_rust_oracle(ROOT, "R-CURRENT")
    assert payload["manifest"]["case_count"] == 135
    assert payload["counts"]["semantic_mismatch"] == 0
    assert payload["counts"]["exact_match"] + payload["counts"]["within_tolerance"] == 135
