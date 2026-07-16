from __future__ import annotations

from pathlib import Path

from gamification_sim.cli import evaluate_cases


def test_all_golden_cases_match():
    fixture = Path(__file__).parents[1] / "fixtures" / "golden_cases.json"
    failures, results = evaluate_cases(fixture)
    assert failures == 0, [result for result in results if not result["ok"]]
    assert len(results) >= 30
