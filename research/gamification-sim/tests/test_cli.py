from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gamification_sim.cli import day_from_dict, episode_from_dict
from gamification_sim.models import SupportKind
from gamification_sim.workspace import (
    OUTPUT_ENV,
    ResearchWorkspace,
    cargo_environment,
    cargo_run_command,
    default_output_root,
    resolve_research_workspace,
)


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


def episode_payload(**overrides):
    payload = {
        "source_event_key": "episode",
        "card_lineage": "card",
        "anki_day": "2026-07-16",
        "outcome": "good",
    }
    payload.update(overrides)
    return payload


def day_payload(**overrides):
    payload = {"anki_day": "2026-07-16"}
    payload.update(overrides)
    return payload


def fixture_with_day(day):
    return {
        "cases": [
            {
                "id": "day",
                "kind": "day",
                "input": day,
                "expected": {},
            }
        ]
    }


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
                "input": episode_payload(),
                "expected": {"total": 999},
            }
        ]
    }
    fixture = tmp_path / "broken.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")
    result = run_cli("evaluate", str(fixture))
    assert result.returncode == 1
    assert "FAIL broken" in result.stdout


@pytest.mark.parametrize("value", [0, 1])
def test_episode_loader_accepts_binary_integer_core_eligibility(value):
    episode = episode_from_dict(episode_payload(core_eligibility=value))
    assert episode.core_eligibility == value


@pytest.mark.parametrize(
    "value",
    [True, False, -1, 2, 0.0, 1.0, 1.7, "1", "30", None, float("nan"), float("inf")],
)
def test_episode_loader_rejects_coercible_or_invalid_core_eligibility(value):
    with pytest.raises(ValueError, match="core_eligibility"):
        episode_from_dict(episode_payload(core_eligibility=value))


@pytest.mark.parametrize("count", [0, 1, 30])
def test_repeat_episode_loader_accepts_non_negative_integer_counts(count):
    day = day_from_dict(
        day_payload(
            repeat_episodes=[
                {
                    "count": count,
                    "prefix": "repeat-",
                    "template": {},
                }
            ]
        )
    )
    assert len(day.episodes) == count


@pytest.mark.parametrize(
    "count",
    [True, False, -1, 0.0, 1.0, 1.7, "1", "30", None, float("nan"), float("inf")],
)
def test_repeat_episode_loader_rejects_non_integer_counts(count):
    with pytest.raises(ValueError, match="repeat_episodes count"):
        day_from_dict(
            day_payload(
                repeat_episodes=[
                    {
                        "count": count,
                        "template": {},
                    }
                ]
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "natural_due_at_start",
        "due_visible_under_limits",
        "due_hidden_by_limits",
    ],
)
@pytest.mark.parametrize(
    "value",
    [True, False, -1, 0.0, 1.0, 1.7, "1", "30", None, float("nan"), float("inf")],
)
def test_workload_loader_rejects_non_integer_counts(field, value):
    with pytest.raises(ValueError, match=field):
        day_from_dict(day_payload(workload={field: value}))


def test_support_loader_rejects_legacy_units_field():
    with pytest.raises(ValueError, match="unsupported field.*units"):
        day_from_dict(
            day_payload(
                support_events=[
                    {
                        "source_event_key": "support",
                        "parent_episode_key": "parent",
                        "kind": "first_step",
                        "units": 999,
                    }
                ]
            )
        )


def test_support_loader_rejects_arbitrary_unknown_fields():
    with pytest.raises(ValueError, match="unsupported field.*reward"):
        day_from_dict(
            day_payload(
                support_events=[
                    {
                        "source_event_key": "support",
                        "parent_episode_key": "parent",
                        "kind": "first_step",
                        "reward": 999,
                    }
                ]
            )
        )


def test_missing_support_kind_defaults_to_other_without_reward_override():
    day = day_from_dict(
        day_payload(
            support_events=[
                {
                    "source_event_key": "support",
                    "parent_episode_key": "parent",
                }
            ]
        )
    )
    assert day.support_events[0].kind is SupportKind.OTHER


def test_cli_rejects_fixture_with_legacy_support_units(tmp_path):
    payload = fixture_with_day(
        day_payload(
            support_events=[
                {
                    "source_event_key": "support",
                    "parent_episode_key": "parent",
                    "kind": "first_step",
                    "units": 999,
                }
            ]
        )
    )
    fixture = tmp_path / "legacy-support.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")

    result = run_cli("evaluate", str(fixture))

    assert result.returncode != 0
    assert "unsupported field(s): units" in result.stderr


def test_longitudinal_cli_validate_and_bounded_no_write():
    config = ROOT / "configs/review-longitudinal-v0.1.json"
    validated = run_cli("validate-longitudinal-config", str(config))
    assert validated.returncode == 0
    assert "VALID review-longitudinal-v0.1" in validated.stdout

    run = run_cli(
        "run-longitudinal",
        str(config),
        "--mode",
        "development",
        "--seed",
        "20260716",
        "--parameter-set",
        "R-CURRENT",
        "--policy",
        "stable-default",
        "--no-write",
    )
    assert run.returncode == 0
    assert "Longitudinal Review XP simulation" in run.stdout


def test_explicit_workspace_is_validated():
    workspace = resolve_research_workspace(ROOT)
    assert workspace.root == ROOT.resolve()
    assert workspace.schemas == (ROOT / "schemas").resolve()
    assert workspace.rust_manifest == (ROOT / "rust-oracle" / "Cargo.toml").resolve()


def test_checkout_workspace_fallback_is_bounded(monkeypatch):
    monkeypatch.chdir(ROOT / "tests")
    monkeypatch.delenv("GAMIFICATION_SIM_RESEARCH_ROOT", raising=False)
    assert resolve_research_workspace().root == ROOT.resolve()


def test_invalid_explicit_workspace_is_not_silently_replaced(tmp_path):
    with pytest.raises(ValueError, match="missing marker"):
        resolve_research_workspace(tmp_path)


def test_workspace_path_rejects_parent_escape():
    workspace = ResearchWorkspace.validated(ROOT)
    with pytest.raises(ValueError, match="bounded"):
        workspace.path("../README.md")


def test_default_output_root_uses_external_temp_location(monkeypatch, tmp_path):
    monkeypatch.delenv(OUTPUT_ENV, raising=False)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    output = default_output_root()
    assert output == (tmp_path / "anki-study-report" / "gamification-sim" / "outputs").resolve()
    assert ROOT.resolve() not in output.parents


def test_explicit_output_root_has_priority(monkeypatch, tmp_path):
    requested = tmp_path / "outputs"
    monkeypatch.setenv(OUTPUT_ENV, str(requested))
    assert default_output_root() == requested.resolve()


def test_cargo_command_uses_workspace_toolchain_and_locked_offline(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "cargo-proxy" if name == "cargo" else None)
    command = cargo_run_command(ROOT, "evaluate-jsonl")
    assert command[0] == "cargo-proxy"
    assert "+stable-x86_64-pc-windows-gnu" not in command
    assert command[1:5] == ["run", "--quiet", "--locked", "--offline"]
    assert command[command.index("--manifest-path") + 1] == str(
        (ROOT / "rust-oracle" / "Cargo.toml").resolve()
    )
    assert command[-2:] == ["--", "evaluate-jsonl"]


def test_cargo_environment_preserves_target_dir(monkeypatch, tmp_path):
    target = tmp_path / "rust-target"
    monkeypatch.setenv("CARGO_TARGET_DIR", str(target))
    environment = cargo_environment()
    assert environment["CARGO_TARGET_DIR"] == str(target)
    assert environment["CARGO_TERM_COLOR"] == "never"
