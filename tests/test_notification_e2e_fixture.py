from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CARD_IDS = (1648933037737, 1649481469689)
DECK_ID = 1784820790366


def test_notification_fixture_seeds_only_profile_state_and_sanitized_proof(tmp_path):
    profile = tmp_path / "E2E"
    reports = tmp_path / "artifacts" / "reports"
    reports.mkdir(parents=True)
    (reports / "anchor-resolution-report.json").write_text(
        json.dumps({
            "schemaVersion": 1,
            "status": "PASS",
            "resolvedCount": 2,
            "anchors": {
                "cards-action-recheck": {"status": "PASS", "cardId": CARD_IDS[0], "deckId": DECK_ID},
                "cards-low-success": {"status": "PASS", "cardId": CARD_IDS[1], "deckId": DECK_ID},
            },
        }),
        encoding="utf-8",
    )
    (reports / "scenario-application-report.json").write_text(
        json.dumps({
            "schemaVersion": 1,
            "status": "PASS",
            "schedulerDay": {"startMs": 1784779200000, "cutoffMs": 1784865600000},
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
    assert proof["fixtureSchemaVersion"] == 2
    assert proof["contentSource"] == "committed-real-apkg-anchors"
    assert proof["anchorIds"] == ["cards-action-recheck", "cards-low-success"]
    assert proof["normalEvaluationWasEmpty"] is True
    assert proof["statusCounts"]["resolved"] >= 1
    assert set(proof["categoryCounts"]) == {"workload", "retention", "deck_health", "card_problems"}
    assert all(str(value) not in serialized for value in (*CARD_IDS, DECK_ID))
    assert not (reports / "fixture-summary.json").exists()
    assert not list(reports.glob("*.sqlite3*"))
    assert (profile / "addon_data" / "anki_study_report_e2e" / "notifications.sqlite3").is_file()
