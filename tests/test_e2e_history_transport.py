from __future__ import annotations

from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import e2e_history_transport as transport


def artifact(
    artifact_id: int, run_id: int, *,
    name: str | None = None, expired: bool = False,
    repository_id: int = 99, created: str = "2026-07-25T00:00:00Z",
) -> dict:
    return {
        "id": artifact_id,
        "name": name or f"ci-e2e-history-{run_id}-1",
        "size_in_bytes": 1000,
        "digest": "sha256:" + "a" * 64,
        "expired": expired,
        "created_at": created,
        "expires_at": "2026-10-20T00:00:00Z",
        "workflow_run": {"id": run_id, "repository_id": repository_id},
    }


class HistoryTransportTests(unittest.TestCase):
    def test_selects_latest_nonexpired_other_run(self):
        payload = {"artifacts": [
            artifact(1, 100, created="2026-07-20T00:00:00Z"),
            artifact(2, 101, created="2026-07-24T00:00:00Z"),
            artifact(3, 102, created="2026-07-25T00:00:00Z"),
        ]}
        result = transport.select_previous_artifact(payload, repository_id=99, current_run_id=102)
        self.assertEqual("selected", result["status"])
        self.assertEqual(2, result["selected"]["artifactId"])

    def test_does_not_trust_name_alone(self):
        payload = {"artifacts": [
            artifact(1, 100, expired=True),
            artifact(2, 101, repository_id=77),
            artifact(3, 102, name="other-artifact"),
        ]}
        result = transport.select_previous_artifact(payload, repository_id=99, current_run_id=200)
        self.assertEqual("missing", result["status"])
        self.assertEqual(1, result["rejected"]["expired"])
        self.assertEqual(1, result["rejected"]["repository-mismatch"])

    def test_metadata_validates_id_repository_run_digest_and_expiry(self):
        payload = artifact(42, 500)
        result = transport.artifact_metadata(payload, expected_id=42, repository_id=99, current_run_id=500)
        self.assertEqual(42, result["id"])
        self.assertEqual(1000, result["sizeBytes"])
        for mutation in (
            {"id": 43}, {"digest": "bad"}, {"expired": True},
            {"workflow_run": {"id": 501, "repository_id": 99}},
            {"workflow_run": {"id": 500, "repository_id": 77}},
        ):
            changed = dict(payload)
            changed.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(transport.HistoryTransportError):
                transport.artifact_metadata(changed, expected_id=42, repository_id=99, current_run_id=500)


if __name__ == "__main__":
    unittest.main()
