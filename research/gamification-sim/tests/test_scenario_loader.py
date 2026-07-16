from __future__ import annotations

import json
from pathlib import Path

import pytest

from gamification_sim.scenario_loader import ScenarioDomainError, load_corpus, load_scenario


def payload(sid="valid-scenario", category="ordinary"):
    return {
        "scenario_version": "review-scenario-v0.1",
        "scenario_id": sid,
        "title": sid,
        "category": category,
        "rule_version": "review-v0.1",
        "days": [{"anki_day": "2026-07-16", "sessions": [{"session_id": "main", "episodes": []}]}],
        "assertions": [],
    }


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_multiday_and_session_flattening(tmp_path):
    p = payload()
    p["days"] = [
        {"anki_day": "2026-07-15", "sessions": [{"session_id": "a", "episodes": [], "repeat_episodes": [{"count": 2, "prefix": "a-", "template": {"outcome": "good"}}]}]},
        {"anki_day": "2026-07-16", "sessions": [{"session_id": "b", "episodes": []}]},
    ]
    result = load_scenario(write(tmp_path / "s.json", p))
    assert len(result.days) == 2
    assert len(result.days[0].day_input.episodes) == 2
    assert result.days[0].day_input.session_ids == ("a",)


def test_duplicate_day_rejected(tmp_path):
    p = payload(); p["days"] *= 2
    with pytest.raises(ScenarioDomainError, match="duplicate anki_day"):
        load_scenario(write(tmp_path / "s.json", p))


def test_unsorted_days_rejected(tmp_path):
    p = payload(); p["days"] = [
        {"anki_day":"2026-07-17","sessions":[{"session_id":"a","episodes":[]}]},
        {"anki_day":"2026-07-16","sessions":[{"session_id":"b","episodes":[]}]},
    ]
    with pytest.raises(ScenarioDomainError, match="strictly increasing"):
        load_scenario(write(tmp_path / "s.json", p))


def test_duplicate_session_id_rejected(tmp_path):
    p = payload(); p["days"][0]["sessions"] *= 2
    with pytest.raises(ScenarioDomainError, match="duplicate session_id"):
        load_scenario(write(tmp_path / "s.json", p))


def test_episode_day_mismatch_rejected(tmp_path):
    p = payload(); p["days"][0]["sessions"][0]["episodes"] = [{"source_event_key":"e","card_lineage":"c","anki_day":"2026-07-15","outcome":"good"}]
    with pytest.raises(ScenarioDomainError, match="mismatch"):
        load_scenario(write(tmp_path / "s.json", p))


def test_duplicate_source_rejected_for_ordinary_but_allowed_for_abuse(tmp_path):
    episodes = [{"source_event_key":"e","card_lineage":"c","anki_day":"2026-07-16","outcome":"good"}]*2
    p = payload(); p["days"][0]["sessions"][0]["episodes"] = episodes
    with pytest.raises(ScenarioDomainError, match="duplicate source_event_key"):
        load_scenario(write(tmp_path / "ordinary.json", p))
    p["category"] = "abuse"; p["control_scenario_id"] = "control"
    load_scenario(write(tmp_path / "abuse.json", p))


def test_strict_integer_contract_reaches_repeat_loader(tmp_path):
    p = payload(); p["days"][0]["sessions"][0]["repeat_episodes"] = [{"count":1.0,"prefix":"x-","template":{}}]
    with pytest.raises(ValueError, match="without coercion"):
        load_scenario(write(tmp_path / "s.json", p))


def test_invalid_assertion_cross_fields(tmp_path):
    p = payload(); p["assertions"] = [{"type":"equals","scope":"day","metric":"total_review_units","expected":0}]
    with pytest.raises(ScenarioDomainError, match="existing anki_day"):
        load_scenario(write(tmp_path / "s.json", p))


def test_corpus_control_reference_rules(tmp_path):
    root = tmp_path / "scenarios"
    abuse = payload("abuse", "abuse"); abuse["control_scenario_id"] = "missing"
    write(root / "abuse.json", abuse)
    with pytest.raises(ScenarioDomainError, match="control does not exist"):
        load_corpus(root)


def test_control_wrong_category_rejected(tmp_path):
    root = tmp_path / "scenarios"
    control = payload("control", "ordinary")
    abuse = payload("abuse", "abuse"); abuse["control_scenario_id"] = "control"
    write(root / "control.json", control); write(root / "abuse.json", abuse)
    with pytest.raises(ScenarioDomainError, match="referenced control has category"):
        load_corpus(root)


def test_duplicate_scenario_id_rejected(tmp_path):
    root = tmp_path / "scenarios"
    write(root / "a.json", payload("same")); write(root / "b.json", payload("same"))
    with pytest.raises(ScenarioDomainError, match="duplicate scenario_id"):
        load_corpus(root)


def test_self_reference_rejected(tmp_path):
    p = payload("self", "abuse"); p["control_scenario_id"] = "self"
    with pytest.raises(ScenarioDomainError, match="itself"):
        load_scenario(write(tmp_path / "s.json", p))


def test_cyclic_control_reference_rejected(tmp_path):
    root = tmp_path / "scenarios"
    first = payload("first-control", "control"); first["control_scenario_id"] = "second-control"
    second = payload("second-control", "control"); second["control_scenario_id"] = "first-control"
    write(root / "first.json", first); write(root / "second.json", second)
    with pytest.raises(ScenarioDomainError, match="cyclic control reference"):
        load_corpus(root)


def test_symlink_scenario_file_rejected(tmp_path):
    root = tmp_path / "scenarios"; root.mkdir()
    target = write(tmp_path / "outside.json", payload("outside"))
    link = root / "linked.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(ScenarioDomainError, match="symlink"):
        load_corpus(root)
