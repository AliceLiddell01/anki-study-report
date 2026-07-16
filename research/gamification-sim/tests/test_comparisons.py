from __future__ import annotations

from pathlib import Path

from gamification_sim.scenario_runner import run_corpus

ROOT = Path(__file__).parents[1]


def result_map():
    result = run_corpus(ROOT / "scenarios")
    return result, {item.scenario_id: item for item in result.scenario_results}


def test_comparison_contains_required_component_deltas():
    _, results = result_map()
    comparison = results["intentional-backlog"].comparison
    assert comparison is not None
    names = set(dict(comparison.deltas))
    assert names == {
        "total_review_units",
        "core_baseline",
        "core_context",
        "support",
        "supplemental",
        "volume_credit",
        "completion_credit",
    }


def test_documented_memory_difference_produces_warning():
    result, results = result_map()
    warnings = results["intentional-backlog"].warnings
    assert "initial memory states differ" in warnings
    assert any(item.startswith("documented difference:") for item in warnings)
    assert "initial memory states differ" in result.warnings


def test_zero_control_component_ratio_is_none():
    _, results = result_map()
    comparison = results["duplicate-replay"].comparison
    assert dict(comparison.ratios)["support"] is None
