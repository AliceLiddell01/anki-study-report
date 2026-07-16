from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "gamification_sim", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_verify_examples_smoke():
    result = run_cli("verify-examples")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "31/31 cases passed" in result.stdout


def test_evaluate_json_smoke():
    result = run_cli("evaluate", "fixtures/golden_cases.json", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload[0]["ok"] is True


def test_cli_returns_nonzero_for_mismatch(tmp_path):
    payload = {
        "cases": [
            {
                "id": "broken",
                "kind": "episode",
                "input": {
                    "source_event_key": "e",
                    "card_lineage": "c",
                    "anki_day": "2026-07-16",
                    "outcome": "good"
                },
                "expected": {"total": 999}
            }
        ]
    }
    fixture = tmp_path / "broken.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")
    result = run_cli("evaluate", str(fixture))
    assert result.returncode == 1
    assert "FAIL broken" in result.stdout
