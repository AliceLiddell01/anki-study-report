from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci-e2e.yml"


class FinalSummaryWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_run_purpose_is_bounded_in_call_and_dispatch_inputs(self):
        self.assertGreaterEqual(self.text.count("run_purpose:"), 2)
        for value in ("acceptance", "controlled", "measurement"):
            self.assertIn(f"- {value}", self.text)
        self.assertIn("E2E_RUN_PURPOSE", self.text)
        self.assertIn("perf100", self.text)
        self.assertIn("measurement", self.text)

    def test_canonical_summary_is_built_before_public_upload(self):
        build = self.text.index("build-summary")
        finalize = self.text.index("finalize-public")
        upload = self.text.index("name: Upload E2E artifact")
        self.assertLess(build, finalize)
        self.assertLess(finalize, upload)
        self.assertIn("reports/final-run-summary.json", self.text)
        self.assertIn("validate-pair", self.text)

    def test_cleanup_state_is_captured_before_final_summary(self):
        cleanup = self.text.index("name: Finalize Docker E2E state before artifact preparation")
        build = self.text.index("build-summary")
        self.assertLess(cleanup, build)
        self.assertIn("E2E_FINAL_CLEANUP_STATUS", self.text)
        self.assertIn("E2E_FINAL_CLEANUP_DURATION_MS", self.text)

    def test_history_transport_is_api_backed_and_nonblocking_for_previous_history(self):
        self.assertIn("scripts/e2e_history_transport.py select", self.text)
        self.assertIn("actions/artifacts?per_page=100", self.text)
        self.assertIn("continuity", self.text)
        self.assertIn("bootstrap", self.text)
        self.assertNotIn("actions/cache", self.text)

    def test_main_upload_metadata_is_only_added_to_history_entry(self):
        upload = self.text.index("name: Upload E2E artifact")
        entry = self.text.index("build-entry")
        self.assertLess(upload, entry)
        self.assertIn("--main-artifact-id", self.text)
        self.assertIn("--main-artifact-digest", self.text)
        self.assertIn("--main-artifact-size-bytes", self.text)

    def test_compact_history_artifact_has_explicit_allowlist_and_retention(self):
        for path in (
            "reports/final-run-summary.json",
            "reports/e2e-run-history.json",
            "reports/e2e-history-aggregation.json",
            "reports/e2e-regression-observations.json",
            "reports/e2e-regression-observations.md",
        ):
            self.assertIn(path, self.text)
        self.assertIn("retention-days: 90", self.text)
        self.assertIn("ci-e2e-history-", self.text)

    def test_regression_observations_are_not_a_gate(self):
        self.assertNotIn("::error", self.text)
        self.assertNotIn("performance-threshold", self.text)
        self.assertNotIn("retry", self.text.lower())
        self.assertIn("render-observations", self.text)

    def test_cancellation_keeps_inner_evidence_and_adds_final_summary(self):
        cancellation = self.text.index("name: Prepare bounded cancellation artifact")
        self.assertIn("cancellation-summary.json", self.text[cancellation:])
        self.assertIn("final-run-summary.json", self.text[cancellation:])
        self.assertNotIn("rewrite cancellation-summary", self.text.lower())

    def test_step_summary_is_compact_rendering(self):
        self.assertIn("render-github-summary", self.text)
        self.assertIn("GITHUB_STEP_SUMMARY", self.text)
        self.assertNotIn("Get-Content reports/e2e-run-history.json", self.text)


if __name__ == "__main__":
    unittest.main()
