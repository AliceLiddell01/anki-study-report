from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import e2e_final_summary as final
from e2e_final_summary_fixtures import *

class HistoryTests(unittest.TestCase):
    def test_bootstrap_append_deduplicate_and_deterministic_sort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root, run_id=100)
            second = build(root, run_id=101, finished_at_utc="2026-07-25T00:00:03.000Z")
            history = final.merge_history(None, entry(first), generated_at_utc=first["execution"]["finishedAtUtc"])
            self.assertEqual("bootstrap", history["continuity"])
            history = final.merge_history(history, entry(second), generated_at_utc=second["execution"]["finishedAtUtc"])
            self.assertEqual("append", history["continuity"])
            history = final.merge_history(history, entry(second), generated_at_utc=second["execution"]["finishedAtUtc"])
            self.assertEqual([100, 101], [row["runId"] for row in history["entries"]])

    def test_invalid_previous_history_resets_but_current_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            history = final.merge_history({"schemaVersion": 99}, entry(summary))
            self.assertEqual("reset", history["continuity"])
            self.assertEqual(1, len(history["entries"]))
            final.validate_history(history)

    def test_max_age_total_and_per_key_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            base = build(root)
            now = datetime(2026, 7, 25, tzinfo=timezone.utc)
            previous = final.empty_history()
            previous["generatedAtUtc"] = "2026-07-25T00:00:00.000Z"
            previous["entries"] = []
            for index in range(150):
                summary = deepcopy(base)
                summary["execution"]["runId"] = index + 1
                stamp = now - timedelta(days=100 if index == 0 else index % 30, seconds=index)
                summary["execution"]["startedAtUtc"] = stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                summary["execution"]["finishedAtUtc"] = (stamp + timedelta(seconds=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                previous["entries"].append(entry(summary))
            previous["entries"].sort(key=lambda row: (row["startedAtUtc"], row["runId"], row["runAttempt"]))
            current = deepcopy(base)
            current["execution"]["runId"] = 999
            history = final.merge_history(previous, entry(current), generated_at_utc="2026-07-25T00:00:02.000Z")
            self.assertEqual("reset", history["continuity"])
            self.assertLessEqual(len(history["entries"]), final.MAX_HISTORY_ENTRIES)

            history = None
            for index in range(final.MAX_HISTORY_PER_COMPATIBILITY + 5):
                summary = deepcopy(base)
                summary["execution"]["runId"] = 2000 + index
                stamp = now + timedelta(seconds=index)
                summary["execution"]["startedAtUtc"] = stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                summary["execution"]["finishedAtUtc"] = (stamp + timedelta(seconds=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                history = final.merge_history(history, entry(summary), generated_at_utc=summary["execution"]["finishedAtUtc"])
            self.assertLessEqual(len(history["entries"]), final.MAX_HISTORY_PER_COMPATIBILITY)

    def test_history_entry_keeps_post_upload_metadata_outside_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            row = entry(summary, artifact_id=42)
            self.assertNotIn("mainArtifact", summary)
            self.assertEqual(42, row["mainArtifact"]["id"])
            self.assertEqual(1000, row["mainArtifact"]["sizeBytes"])

    def test_candidate_key_rerun_and_new_run_same_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root, run_id=100, attempt=1)
            rerun = build(root, run_id=100, attempt=2)
            new_run = build(root, run_id=101, attempt=1)
            self.assertEqual(final.candidate_key(first), final.candidate_key(rerun))
            self.assertEqual(final.candidate_key(first), final.candidate_key(new_run))

    def test_first_run_pass_rate_counts_candidate_once_and_excludes_controlled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            success = build(root, run_id=100)
            rerun = build(root, run_id=100, attempt=2)
            same_candidate = build(root, run_id=101)
            controlled = build(root, run_id=102, purpose="controlled")
            history = None
            for summary in (success, rerun, same_candidate, controlled):
                history = final.merge_history(history, entry(summary), generated_at_utc=summary["execution"]["finishedAtUtc"])
            rate = final.first_run_pass_rate(history)
            self.assertEqual(1, rate["passedCandidates"])
            self.assertEqual(1, rate["eligibleCandidates"])
            self.assertGreaterEqual(rate["excludedRuns"], 1)

    def test_new_build_identity_creates_new_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root, run_id=100)
            identity = json.loads((root / "reports/non-release-build-identity.json").read_text())
            identity["identityDigest"] = "sha256:" + "8" * 64
            write_json(root / "reports/non-release-build-identity.json", identity)
            second = build(root, run_id=101)
            self.assertNotEqual(final.candidate_key(first), final.candidate_key(second))

    def test_measurement_and_cancellation_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            measurement = build(make_root(Path(tmp) / "m"), purpose="measurement")
            cancelled = build(make_root(Path(tmp) / "c", result="cancelled"), result="cancelled", purpose="controlled")
            self.assertFalse(entry(measurement)["firstAttempt"]["eligible"])
            self.assertEqual("purpose:measurement", entry(measurement)["firstAttempt"]["exclusionReason"])
            self.assertFalse(entry(cancelled)["firstAttempt"]["eligible"])

    def test_p50_and_p95_minimums_and_inclusive_method(self):
        self.assertEqual("insufficient-history", final.percentile([1, 2], percentile_value=50, minimum=3)["status"])
        self.assertEqual(2.0, final.percentile([1, 2, 3], percentile_value=50, minimum=3)["value"])
        self.assertEqual("insufficient-history", final.percentile(list(range(19)), percentile_value=95, minimum=20)["status"])
        p95 = final.percentile(list(range(1, 21)), percentile_value=95, minimum=20)
        expected = statistics.quantiles(list(range(1, 21)), n=100, method="inclusive")[94]
        self.assertEqual(expected, p95["value"])

    def test_aggregation_excludes_failed_cancelled_incompatible_and_missing_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp) / "s")
            current = build(root, run_id=100)
            history = None
            for index in range(3):
                summary = deepcopy(current)
                summary["execution"]["runId"] = 100 + index
                summary["performance"]["metrics"]["canonicalDurationMs"] = 1000 + index
                history = final.merge_history(history, entry(summary), generated_at_utc=summary["execution"]["finishedAtUtc"])
            incompatible = deepcopy(current)
            incompatible["execution"]["runId"] = 200
            incompatible["compatibility"]["dimensions"]["scope"] = "cards"
            incompatible["compatibility"]["key"] = final.hash_object(incompatible["compatibility"]["dimensions"])
            history = final.merge_history(history, entry(incompatible), generated_at_utc=incompatible["execution"]["finishedAtUtc"])
            aggregation = final.aggregate_history(history, current)
            self.assertEqual(3, aggregation["compatibleSuccessfulSamples"])
            self.assertEqual(3, aggregation["metrics"]["canonicalDurationMs"]["p50"]["sampleCount"])
            self.assertEqual(10.0, aggregation["metrics"]["cleanupDurationMs"]["p50"]["value"])

    def test_observations_are_informational_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            history = final.merge_history(None, entry(summary))
            aggregation = final.aggregate_history(history, summary)
            observations = final.render_observations(summary, history, aggregation)
            self.assertEqual("observational-only", observations["classification"])
            self.assertEqual("insufficient-history", observations["metrics"]["canonicalDurationMs"]["status"])
            markdown = final.render_observations_markdown(observations)
            self.assertIn("CI не блокируется", markdown)
            self.assertNotIn("::error", markdown)

    def test_compact_github_summary_does_not_embed_json_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            history = final.merge_history(None, entry(summary))
            aggregation = final.aggregate_history(history, summary)
            markdown = final.render_github_summary(summary, aggregation, history)
            self.assertIn("## Result", markdown)
            self.assertIn("## Reliability", markdown)
            self.assertLess(len(markdown.encode("utf-8")), 32 * 1024)
            self.assertNotIn('"entries"', markdown)


if __name__ == "__main__":
    unittest.main()
