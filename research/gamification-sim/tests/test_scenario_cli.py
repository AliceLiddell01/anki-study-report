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
        [sys.executable, "-m", "gamification_sim", *map(str, args)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_scenarios_command():
    result = run_cli("validate-scenarios", "scenarios")
    assert result.returncode == 0
    assert "VALID 26 scenarios" in result.stdout


def test_validate_scenarios_json():
    result = run_cli("validate-scenarios", "scenarios", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["scenario_ids"]) == 26


def test_run_scenario_no_write(tmp_path):
    result = run_cli(
        "run-scenario",
        "scenarios/ordinary/stable-seven-days.json",
        "--json",
        "--no-write",
        "--output-dir",
        tmp_path,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["manifest"]["scenario_ids"] == ["stable-seven-days"]
    assert not any(tmp_path.iterdir())


def test_run_abuse_scenario_resolves_control():
    result = run_cli("run-scenario", "scenarios/abuse/intentional-backlog.json", "--json", "--no-write")
    assert result.returncode == 0
    ids = json.loads(result.stdout)["manifest"]["scenario_ids"]
    assert ids == ["intentional-backlog", "timely-backlog-control"]


def test_run_corpus_no_write():
    result = run_cli("run-scenarios", "scenarios", "--json", "--no-write")
    assert result.returncode == 0
    assert len(json.loads(result.stdout)["scenario_results"]) == 26


def test_compare_scenarios():
    result = run_cli(
        "compare-scenarios",
        "scenarios/controls/timely-backlog-control.json",
        "scenarios/abuse/intentional-backlog.json",
        "--json",
        "--no-write",
    )
    assert result.returncode == 0
    assert len(json.loads(result.stdout)["scenario_results"]) == 2


def test_invalid_contract_exit_code_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"scenario_id":"bad"}', encoding="utf-8")
    result = run_cli("run-scenario", bad, "--no-write")
    assert result.returncode == 2
    assert "INVALID:" in result.stderr


def test_assertion_failure_exit_code_1(tmp_path):
    payload = json.loads((ROOT / "scenarios/ordinary/high-volume-day.json").read_text())
    payload["scenario_id"] = "failing-assertion"
    payload["assertions"][0]["expected"] = 999
    path = tmp_path / "failure.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = run_cli("run-scenario", path, "--no-write")
    assert result.returncode == 1


def test_internal_error_exit_code_3_is_defensive_boundary(monkeypatch, capsys):
    import gamification_sim.cli as cli
    monkeypatch.setattr(cli, "_run_new_command", lambda args: (_ for _ in ()).throw(RuntimeError("boom")))
    code = cli.main(["validate-scenarios", "scenarios"])
    assert code == 3
    assert "INTERNAL ERROR" in capsys.readouterr().err




def test_run_corpus_writes_only_to_explicit_output_dir(tmp_path):
    result = run_cli("run-scenarios", "scenarios", "--output-dir", tmp_path, "--json")
    assert result.returncode == 0
    run_dirs = list(tmp_path.glob("run-*"))
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "results.json").is_file()
    assert (run_dirs[0] / "summary.md").is_file()
