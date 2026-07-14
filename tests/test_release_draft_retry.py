from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import ROOT


def load_manager():
    common_path = ROOT / "scripts" / "release_common.py"
    common_spec = importlib.util.spec_from_file_location("release_common", common_path)
    assert common_spec and common_spec.loader
    common = importlib.util.module_from_spec(common_spec)
    sys.modules[common_spec.name] = common
    common_spec.loader.exec_module(common)

    path = ROOT / "scripts" / "manage_github_release.py"
    spec = importlib.util.spec_from_file_location("manage_github_release_retry", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def completed() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["gh"], 0, "", "")


def release_record(commit: str) -> dict:
    return {
        "id": 101,
        "tag_name": "v1.1.0",
        "name": "Anki Study Report 1.1.0",
        "draft": True,
        "prerelease": False,
        "target_commitish": commit,
        "assets": [],
    }


def test_prepare_draft_retries_listing_without_recreating(monkeypatch, tmp_path: Path) -> None:
    manager = load_manager()
    commit = "b" * 40
    created = release_record(commit)
    sequence = iter([None, None, created])
    calls = []
    sleeps = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: next(sequence))
    monkeypatch.setattr(manager, "get_release_by_id", lambda *args, **kwargs: created)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    monkeypatch.setattr(manager.time, "sleep", lambda seconds: sleeps.append(seconds))
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes\n", encoding="utf-8")

    release, action = manager.prepare_draft(
        "owner/repo", "v1.1.0", "Anki Study Report 1.1.0", notes, "stable", commit
    )

    assert action == "created"
    assert release["id"] == created["id"]
    assert sleeps == [1]
    assert sum(call[:2] == ("release", "create") for call in calls) == 1


def test_prepare_draft_lookup_failure_is_bounded(monkeypatch, tmp_path: Path) -> None:
    manager = load_manager()
    commit = "b" * 40
    calls = []
    sleeps = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: None)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    monkeypatch.setattr(manager.time, "sleep", lambda seconds: sleeps.append(seconds))
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes\n", encoding="utf-8")

    with pytest.raises(manager.ReleaseError, match="bounded post-create verification retries"):
        manager.prepare_draft(
            "owner/repo", "v1.1.0", "Anki Study Report 1.1.0", notes, "stable", commit
        )

    assert sleeps == list(manager.DRAFT_LOOKUP_DELAYS)
    assert sum(call[:2] == ("release", "create") for call in calls) == 1
