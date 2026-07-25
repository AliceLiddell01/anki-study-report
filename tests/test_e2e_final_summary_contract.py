from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

import e2e_final_summary as final
from e2e_final_summary_fixtures import *

class FinalSummaryTests(unittest.TestCase):
    def test_valid_success_is_complete_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp), result="success"))
            self.assertEqual("success", summary["result"])
            self.assertEqual("complete", summary["finalizationStatus"])
            self.assertEqual("run/pass", summary["terminal"]["event"])
            self.assertIsNone(summary["terminal"]["failureCode"])
            self.assertLessEqual(len(final._json_bytes(summary)), final.MAX_SUMMARY_BYTES)
            final.validate_summary(summary)

    def test_valid_failure_preserves_primary_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp), result="failure"), result="failure")
            self.assertEqual("failure", summary["result"])
            self.assertEqual("ASR-E2E-BROWSER", summary["terminal"]["failureCode"])
            self.assertEqual("route.home.light", summary["terminal"]["itemId"])

    def test_valid_cancellation_preserves_signal_exit_and_inner_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), result="cancelled")
            original = json.loads((root / "reports/cancellation-summary.json").read_text())
            summary = build(root, result="cancelled", purpose="controlled", cleanup_status="failure")
            self.assertEqual("cancelled", summary["result"])
            self.assertEqual("SIGTERM", summary["terminal"]["signal"])
            self.assertEqual(143, summary["terminal"]["exitCode"])
            self.assertEqual(original, json.loads((root / "reports/cancellation-summary.json").read_text()))

    def test_preflight_minimal_failure_has_no_fake_build_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), result="success", include_identity=False)
            (root / "reports/run-events.jsonl").unlink()
            report = json.loads((root / "reports/preflight-report.json").read_text())
            report["status"] = "FAIL"
            report["checks"][3]["status"] = "FAIL"
            write_json(root / "reports/preflight-report.json", report)
            summary = build(root, result="failure", package_source="unresolved", exit_code=2, finished_at_utc="2026-07-25T00:00:01.000Z")
            self.assertEqual("minimal", summary["finalizationStatus"])
            self.assertIsNone(summary["build"]["identityDigest"])
            self.assertEqual("check-3", summary["terminal"]["itemId"])

    def test_closed_schema_rejects_unknown_and_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            unknown = deepcopy(summary)
            unknown["surprise"] = True
            with self.assertRaises(final.FinalSummaryError):
                final.validate_summary(unknown)
            missing = deepcopy(summary)
            del missing["checks"]
            with self.assertRaises(final.FinalSummaryError):
                final.validate_summary(missing)

    def test_type_enum_sha_digest_and_timestamp_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            mutations = [("result", "maybe"), ("execution.triggerSha", "bad"), ("build.identityDigest", "sha256:bad"), ("execution.startedAtUtc", "2026-07-25")]
            for path, value in mutations:
                broken = deepcopy(summary)
                target = broken
                parts = path.split(".")
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = value
                with self.subTest(path=path), self.assertRaises(final.FinalSummaryError):
                    final.validate_summary(broken)

    def test_deterministic_serialization_and_atomic_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root)
            second = build(root)
            self.assertEqual(final._json_bytes(first), final._json_bytes(second))
            output = Path(tmp) / "summary.json"
            final.write_json(output, first, max_bytes=final.MAX_SUMMARY_BYTES)
            self.assertEqual(first, final.load_summary(output))

    def test_safe_paths_secrets_private_paths_and_controls_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            for value in ("../escape.json", "/home/user/file", "reports/file?token=secret", "reports/\x00bad"):
                broken = deepcopy(summary)
                broken["evidence"]["browser"] = value
                with self.subTest(value=value), self.assertRaises(final.FinalSummaryError):
                    final.validate_summary(broken)

    def test_source_public_pair_requires_semantic_equality_and_hashes_public_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            summary = build(root)
            raw = Path(tmp) / "raw.json"
            public = Path(tmp) / "public.json"
            final.write_json(raw, summary)
            final.write_json(public, summary)
            loaded, digest = final.validate_pair(raw, public)
            self.assertEqual(summary, loaded)
            self.assertEqual(final.file_digest(public), digest)
            changed = deepcopy(summary)
            changed["execution"]["runAttempt"] = 2
            final.write_json(public, changed)
            with self.assertRaises(final.FinalSummaryError):
                final.validate_pair(raw, public)

    def test_success_requires_resolved_non_release_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), include_identity=False)
            with self.assertRaises(final.FinalSummaryError):
                build(root)

    def test_result_terminal_parity_and_single_terminal_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            summary = build(root)
            broken = deepcopy(summary)
            broken["terminal"]["event"] = "run/fail"
            with self.assertRaises(final.FinalSummaryError):
                final.validate_summary(broken)
            rows = final.read_jsonl(root / "reports/run-events.jsonl")
            rows.append(event("pass", elapsed=3))
            write_jsonl(root / "reports/run-events.jsonl", rows)
            with self.assertRaises(final.FinalSummaryError):
                build(root)

    def test_compatibility_key_is_order_independent_and_excludes_run_build_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root, run_id=100)
            second = build(root, run_id=101, attempt=2, trigger_sha=SHA_B)
            self.assertEqual(first["compatibility"]["key"], second["compatibility"]["key"])
            identity = json.loads((root / "reports/non-release-build-identity.json").read_text())
            identity["identityDigest"] = "sha256:" + "9" * 64
            write_json(root / "reports/non-release-build-identity.json", identity)
            third = build(root, run_id=102)
            self.assertEqual(first["compatibility"]["key"], third["compatibility"]["key"])
            self.assertNotEqual(final.candidate_key(first), final.candidate_key(third))
            reordered = dict(reversed(list(first["compatibility"]["dimensions"].items())))
            self.assertEqual(first["compatibility"]["key"], final.hash_object(reordered))

    def test_hard_dimension_mutations_change_compatibility_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            baseline = build(root)
            for change in [{"mode": "strict-apkg"}, {"scope": "cards"}, {"screenshot_workers": 2}, {"resource_telemetry": False}]:
                changed = build(root, **change)
                with self.subTest(change=change):
                    self.assertNotEqual(baseline["compatibility"]["key"], changed["compatibility"]["key"])

    def test_observed_dimension_change_adds_caveat_without_changing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            first = build(root, run_id=100, runner_image="ubuntu24:one")
            second = build(root, run_id=101, runner_image="ubuntu24:two")
            self.assertEqual(first["compatibility"]["key"], second["compatibility"]["key"])
            history = final.merge_history(None, entry(first), generated_at_utc=first["execution"]["finishedAtUtc"])
            history = final.merge_history(history, entry(second), generated_at_utc=second["execution"]["finishedAtUtc"])
            observations = final.render_observations(second, history, final.aggregate_history(history, second))
            self.assertIn("runnerImage changed", observations["runnerEnvironmentCaveats"])

    def test_local_and_cloud_are_not_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            self.assertNotEqual(build(root, contour="cloud")["compatibility"]["key"], build(root, contour="local")["compatibility"]["key"])

    def test_browser_uses_operation_only_timing_and_explicit_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            self.assertEqual("operation-only", summary["checks"]["browser"]["itemTimingSemantics"])
            self.assertEqual(2, summary["checks"]["browser"]["terminalItems"])
            self.assertEqual(300, summary["performance"]["browserItems"]["route.home.light"]["durationMs"])

    def test_artifact_footprint_categories_largest_files_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            footprint = build(root)["artifactFootprint"]
            self.assertGreater(footprint["fileCount"], 0)
            self.assertEqual(1, footprint["screenshotCount"])
            self.assertLessEqual(len(footprint["largestFiles"]), final.MAX_LARGEST_FILES)
            self.assertEqual(final.file_digest(root / "artifact-manifest.json"), footprint["manifestDigest"])
            self.assertFalse(any("artifact-id" in row["path"] for row in footprint["largestFiles"]))

    def test_legacy_projection_is_derived_from_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)))
            projection = final.legacy_projection(summary)
            self.assertEqual("artifacts/reports/final-run-summary.json", projection["derivedFrom"])
            self.assertEqual(summary["result"], projection["result"])
            self.assertEqual(summary["compatibility"]["key"], projection["compatibilityKey"])
            self.assertIn("Производная compatibility-проекция", final.render_legacy_markdown(summary))

    def test_finalize_public_reaches_fixed_point_and_uses_full_upload_footprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_root(base / "raw")
            public_root = base / "public"
            (public_root / "artifacts").mkdir(parents=True)
            import shutil
            shutil.copytree(root, public_root / "artifacts", dirs_exist_ok=True)
            (public_root / "logs").mkdir()
            (public_root / "logs" / "docker-system.txt").write_text("safe\n", encoding="utf-8")
            raw_output = root / "reports/final-run-summary.json"
            context = {"repository": "AliceLiddell01/anki-study-report", "run_id": 100, "run_attempt": 1, "event": "workflow_dispatch", "ref": "refs/heads/platform/e2e-i6-final-summary-history", "trigger_sha": SHA_A, "workflow_source_sha": SHA_A, "harness_sha": SHA_A, "mode": "standard", "scope": "full", "run_purpose": "acceptance", "screenshot_workers": 3, "resource_telemetry": True, "contour": "cloud", "started_at_utc": "2026-07-25T00:00:00.000Z", "finished_at_utc": "2026-07-25T00:00:02.000Z", "exit_code": 0, "runner_os": "Linux", "runner_image": "ubuntu24:one", "docker_client_version": "28.0.4", "docker_server_version": "28.0.4", "docker_compose_version": "2.38.2", "powershell_version": "7.6.3", "package_source": "fast-ci-artifact", "artifact_preparation_duration_ms": 25, "workflow_duration_ms": 2000, "cleanup_status": "success", "cleanup_duration_ms": 10, "artifact_preparation_status": "success", "source_validated": True, "public_validated": True}
            summary = final.finalize_public_artifact(root, public_root, raw_output, context=context)
            final.validate_pair(raw_output, public_root / "artifacts/reports/final-run-summary.json")
            self.assertTrue((public_root / "ci-e2e-summary.json").is_file())
            self.assertTrue((public_root / "ci-e2e-summary.md").is_file())
            self.assertGreater(summary["artifactFootprint"]["totalUncompressedBytes"], sum(path.stat().st_size for path in root.rglob("*") if path.is_file()))

    def test_host_cleanup_failure_overrides_run_pass_without_console_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(make_root(Path(tmp)), result="success", exit_code=5, host_failure_code="ASR-E2E-CLEANUP", host_failure_phase="host-cleanup", cleanup_status="failure")
            self.assertEqual("failure", summary["result"])
            self.assertEqual("host/fail", summary["terminal"]["event"])
            self.assertEqual("ASR-E2E-CLEANUP", summary["terminal"]["failureCode"])
            self.assertEqual("minimal", summary["finalizationStatus"])
