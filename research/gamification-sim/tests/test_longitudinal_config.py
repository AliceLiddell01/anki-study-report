from __future__ import annotations

import json

import pytest

from gamification_sim.longitudinal_config import load_longitudinal_config
from gamification_sim.strict_json import StrictJsonError


ROOT = __import__("pathlib").Path(__file__).parents[1]
CONFIG = ROOT / "configs" / "review-longitudinal-v0.1.json"


def test_longitudinal_config_is_strict_bounded_and_complete():
    config = load_longitudinal_config(CONFIG)
    assert config.version == "review-longitudinal-v0.1"
    assert config.mode("development").horizon_days == 30
    assert config.mode("calibration-90").horizon_days == 90
    assert config.mode("calibration-365").horizon_days == 365
    assert len(config.policies) == 9
    assert all(policy.retention_timeline[0].start_day == 0 for policy in config.policies)


def test_longitudinal_config_rejects_unknown_fields(tmp_path):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload["code"] = "eval(1)"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Additional properties"):
        load_longitudinal_config(path)


def test_longitudinal_config_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"version":"review-longitudinal-v0.1","version":"x"}', encoding="utf-8")
    with pytest.raises(StrictJsonError, match="duplicate object key"):
        load_longitudinal_config(path)


def test_longitudinal_config_rejects_unsorted_timeline(tmp_path):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload["policies"][0]["retention_timeline"] = [
        {"start_day": 1, "desired_retention": 0.9},
        {"start_day": 0, "desired_retention": 0.9},
    ]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="start at 0 and increase"):
        load_longitudinal_config(path)


def test_longitudinal_config_rejects_symlink(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(ValueError, match="symlink"):
        load_longitudinal_config(link)
