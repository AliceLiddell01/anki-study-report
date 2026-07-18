from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from gamification_sim.scenario_loader import load_corpus
from gamification_sim.scenario_models import ScenarioCategory
from gamification_sim.scenario_runner import run_corpus

ROOT = Path(__file__).parents[1]


def test_corpus_counts_and_unique_ids():
    definitions = load_corpus(ROOT / "scenarios")
    counts = Counter(item.category.value for item in definitions)
    assert counts == {"ordinary": 6, "edge": 7, "control": 6, "abuse": 6, "regression": 1}
    assert len({item.scenario_id for item in definitions}) == 26


def test_every_abuse_has_control():
    definitions = load_corpus(ROOT / "scenarios")
    by_id = {item.scenario_id: item for item in definitions}
    for item in definitions:
        if item.category is ScenarioCategory.ABUSE:
            assert item.control_scenario_id
            assert by_id[item.control_scenario_id].category is ScenarioCategory.CONTROL


def test_committed_corpus_passes():
    result = run_corpus(ROOT / "scenarios")
    assert result.passed
    assert all(item.assertions for item in result.scenario_results)


def test_input_digest_independent_of_file_discovery_order(monkeypatch):
    import gamification_sim.scenario_loader as loader
    original = loader.discover_scenario_paths
    baseline = run_corpus(ROOT / "scenarios").manifest.input_digest
    monkeypatch.setattr(loader, "discover_scenario_paths", lambda root: tuple(reversed(original(root))))
    assert run_corpus(ROOT / "scenarios").manifest.input_digest == baseline


def test_input_digest_is_checkout_path_invariant(tmp_path):
    import shutil
    copied = tmp_path / "different-checkout" / "scenarios"
    shutil.copytree(ROOT / "scenarios", copied)
    assert run_corpus(copied).manifest.input_digest == run_corpus(ROOT / "scenarios").manifest.input_digest
