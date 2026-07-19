from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from gamification_sim import fsrs_reference
from gamification_sim.cli import main
from gamification_sim.fsrs_reference import _resolve_contract_path, verify_fsrs_reference
from gamification_sim.workspace import ResearchWorkspace


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "contracts" / "fsrs-trajectories-v0.1.json"


@pytest.mark.skipif(importlib.util.find_spec("fsrs") is None, reason="optional fsrs extra is not installed")
def test_official_fsrs_references_are_reproducible_and_preserve_reward_baseline():
    cargo = Path.home() / ".cargo" / "bin" / "cargo.exe"
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


def test_cli_relative_contract_path_is_absolute_before_rust_handoff(
    monkeypatch,
    capsys,
):
    repository_root = ROOT.parents[1]
    relative_contract = CONTRACT.relative_to(repository_root)
    captured: dict[str, Path] = {}

    monkeypatch.chdir(repository_root)
    monkeypatch.setattr(
        fsrs_reference,
        "_python_reference",
        lambda payload: {"package_version": "6.3.1", "trajectories": []},
    )

    def fake_rust_reference(package_root: Path, contract_path: Path):
        captured["package_root"] = package_root
        captured["contract_path"] = contract_path
        return {"crate_version": "6.6.1", "trajectories": []}

    monkeypatch.setattr(fsrs_reference, "_rust_reference", fake_rust_reference)
    monkeypatch.setattr(
        fsrs_reference,
        "_reward_integration",
        lambda: {"all_baselines_equal": True, "core_baseline": 0.9, "states": {}},
    )

    exit_code = main(
        [
            "--research-root",
            str(ROOT),
            "verify-fsrs-reference",
            str(relative_contract),
            "--no-write",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["manifest"]["fsrs_rs_crate_version"] == "6.6.1"
    assert captured["package_root"] == ROOT.resolve()
    assert captured["contract_path"] == CONTRACT.resolve()
    assert captured["contract_path"].is_absolute()


def test_relative_contract_path_with_spaces_resolves_from_invocation_cwd(tmp_path, monkeypatch):
    workspace_root = tmp_path / "research workspace with spaces"
    markers = (
        "pyproject.toml",
        "schemas/review-scenario-v0.2.schema.json",
        "schemas/review-longitudinal-v0.1.schema.json",
        "schemas/review-sweep-v0.1.schema.json",
        "schemas/review-persona-v0.1.schema.json",
        "fixtures/golden_cases.json",
        "rust-toolchain.toml",
        "rust-oracle/Cargo.toml",
        "rust-oracle/Cargo.lock",
    )
    for marker in markers:
        path = workspace_root / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    contract = workspace_root / "contracts/fsrs-trajectories-v0.1.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")

    workspace = ResearchWorkspace.validated(workspace_root)
    monkeypatch.chdir(tmp_path)

    resolved = _resolve_contract_path(
        Path("research workspace with spaces/contracts/fsrs-trajectories-v0.1.json"),
        workspace,
    )

    assert resolved == contract.resolve()
    assert resolved.is_absolute()


def test_fsrs_contract_must_stay_inside_workspace_contracts(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")
    workspace = ResearchWorkspace.validated(ROOT)

    with pytest.raises(ValueError, match="inside the research workspace"):
        _resolve_contract_path(outside, workspace)

    with pytest.raises(ValueError, match="inside the workspace contracts directory"):
        _resolve_contract_path(ROOT / "fixtures/golden_cases.json", workspace)


def test_fsrs_contract_has_no_real_collection_fields():
    text = CONTRACT.read_text(encoding="utf-8")
    assert all(value not in text for value in ("card_text", "deck_name", "revlog", "collection_path"))
