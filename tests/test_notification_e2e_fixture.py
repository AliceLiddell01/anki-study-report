from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_notification_fixture_seeds_only_profile_state_and_sanitized_proof(tmp_path):
    profile = tmp_path / "E2E"
    reports = tmp_path / "artifacts" / "reports"
    reports.mkdir(parents=True)
    (reports / "fixture-summary.json").write_text(
        json.dumps({
            "reviewAnchorMs": 1784282400000,
            "cardIds": {"first": [101], "second": [202]},
            "actionDeckIds": {"source": 303},
        }),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "docker" / "anki-e2e" / "seed-notification-lifecycle.py"),
            "--addon-dir",
            str(ROOT / "anki_study_report"),
            "--profile-dir",
            str(profile),
            "--artifacts-dir",
            str(reports),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    proof = json.loads((reports / "notification-fixture-proof.json").read_text(encoding="utf-8"))
    serialized = json.dumps(proof)
    assert proof["normalEvaluationWasEmpty"] is True
    assert proof["statusCounts"]["resolved"] >= 1
    assert set(proof["categoryCounts"]) == {"workload", "retention", "deck_health", "card_problems"}
    assert "101" not in serialized and "202" not in serialized and "303" not in serialized
    assert not list(reports.glob("*.sqlite3*"))
    assert (profile / "addon_data" / "anki_study_report_e2e" / "notifications.sqlite3").is_file()
