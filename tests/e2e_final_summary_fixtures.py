from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import unittest

import e2e_final_summary as final
import non_release_build_identity as build_identity


SHA_A = "a" * 40
SHA_B = "b" * 40
IDENTITY = "sha256:" + "1" * 64
ENVIRONMENT = "sha256:" + "2" * 64
IMAGE = "sha256:" + "3" * 64


def non_release_identity_document() -> dict[str, object]:
    identity = {
        "repository": "AliceLiddell01/anki-study-report",
        "package": {
            "source": "fast-ci-artifact",
            "testedCommitSha": SHA_A,
            "sourceRunId": 10,
            "sourceRunAttempt": 1,
            "artifactId": 20,
            "artifactDigest": "sha256:" + "6" * 64,
            "innerSha256": hashlib.sha256(b"addon").hexdigest(),
            "sizeBytes": len(b"addon"),
        },
        "harness": {
            "commitSha": SHA_A,
            "checkoutSha": SHA_A,
        },
        "workflow": {
            "repository": "AliceLiddell01/anki-study-report",
            "filePath": ".github/workflows/ci-e2e.yml",
            "sourceSha": SHA_A,
        },
        "environment": {
            "imageReference": "ghcr.io/example/e2e@" + IMAGE,
            "imageDigest": IMAGE,
            "platform": "linux/amd64",
            "contractSha256": "2" * 64,
            "publishedFromCommitSha": SHA_A,
        },
        "reuse": {
            "mode": "exact-tree",
            "changedFileCount": 0,
            "changedPathsSha256": hashlib.sha256(b"").hexdigest(),
        },
    }
    document = {
        "schemaVersion": build_identity.SCHEMA_VERSION,
        "kind": build_identity.KIND,
        "identityDigest": build_identity.compute_identity_digest(identity),
        "identity": identity,
        "execution": {
            "runId": 100,
            "runAttempt": 1,
            "triggerSha": SHA_A,
            "ref": "refs/heads/platform/e2e-i6-final-summary-history",
        },
    }
    build_identity.validate_document(document)
    return document


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def event(status: str, *, phase: str = "run", kind: str = "run", failure: str | None = None, elapsed: int = 0) -> dict:
    return {
        "schemaVersion": 2,
        "timestampUtc": f"2026-07-25T00:00:{elapsed:02d}.000Z",
        "elapsedMs": elapsed * 1000,
        "producer": "docker-e2e",
        "phaseId": phase,
        "eventKind": kind,
        "status": status,
        "durationMs": elapsed * 1000 if status in {"pass", "fail", "cancel"} else None,
        "current": None,
        "total": None,
        "message": None,
        "failureCode": failure,
    }


def make_root(base: Path, *, result: str = "success", include_identity: bool = True) -> Path:
    root = base / "artifact"
    reports = root / "reports"
    reports.mkdir(parents=True)
    (root / "screenshots").mkdir()
    (root / "diagnostics").mkdir()
    (root / "runtime").mkdir()
    (root / "package").mkdir()
    (root / "screenshots" / "a.png").write_bytes(b"png")
    (root / "diagnostics" / "safe.log").write_text("safe\n", encoding="utf-8")
    (root / "runtime" / "events.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "package" / "anki_study_report.ankiaddon").write_bytes(b"addon")

    manifest = {
        "artifactSchemaVersion": 2,
        "status": "success" if result == "success" else "failed",
        "ankiVersion": "26.05",
        "execution": {"mode": "standard", "scope": "full", "screenshotWorkers": 3, "resourceTelemetry": True},
        "generatedAtUtc": "2026-07-25T00:00:02+00:00",
        "runtime": {"dashboardReady": None, "events": "runtime/events.jsonl"},
        "artifacts": {"reports": [], "diagnostics": ["diagnostics/safe.log"], "html": [], "package": ["package/anki_study_report.ankiaddon"]},
        "screenshots": [{"path": "screenshots/a.png", "kind": "other"}],
    }
    write_json(root / "artifact-manifest.json", manifest)
    write_json(reports / "preflight-report.json", {
        "schemaVersion": 1, "status": "PASS", "durationMs": 100,
        "checks": [{"id": f"check-{index}", "status": "PASS"} for index in range(20)],
    })
    browser = {
        "schemaVersion": 3, "ok": result == "success", "label": "first",
        "plan": {"schemaVersion": 1, "label": "first", "mode": "standard", "scope": "full", "telemetryEnabled": True, "itemCount": 2, "expectedScreenshotCount": 1, "countsByKind": {"browser-launch": 1, "route-capture": 1}, "items": []},
        "progress": {"terminalItems": 2, "passedItems": 2 if result == "success" else 1, "failedItems": 0 if result == "success" else 1, "skippedItems": 0, "remainingItems": 0, "totalItems": 2, "failedItemId": None if result == "success" else "route.home.light", "activeItemId": None, "expectedScreenshotCount": 1, "actualScreenshotCount": 1 if result == "success" else 0, "runEventProducerCalls": 5, "runEventProducerDurationMs": 20, "runEventProducerFailures": 0},
    }
    write_json(reports / "browser-smoke-first.json", browser)
    write_json(reports / "screenshot-performance.json", {
        "schemaVersion": 3, "label": "first", "status": "pass" if result == "success" else "fail", "durationMs": 500, "screenshotCount": 1 if result == "success" else 0, "configuredWorkers": 3, "mode": "standard", "scope": "full", "plan": {"schemaVersion": 1}, "progress": browser["progress"],
        "items": [
            {"id": "browser.launch", "kind": "browser-launch", "status": "pass", "order": 1, "operationDurationMs": 10, "expectedScreenshots": 0, "actualScreenshots": 0, "screenshotPaths": []},
            {"id": "route.home.light", "kind": "route-capture", "status": "pass" if result == "success" else "fail", "order": 2, "operationDurationMs": 300, "expectedScreenshots": 1, "actualScreenshots": 1 if result == "success" else 0, "screenshotPaths": ["screenshots/a.png"] if result == "success" else []},
        ],
        "slowestItems": [], "itemTimingSemantics": "operation-only",
        "producerMetrics": {"runEventProducerCalls": 5, "runEventProducerDurationMs": 20, "runEventProducerFailures": 0},
    })
    write_json(reports / "e2e-phase-timings.json", {
        "schemaVersion": 1,
        "phases": [
            {"name": "total canonical E2E", "startedAt": "2026-07-25T00:00:00.000Z", "finishedAt": "2026-07-25T00:00:01.000Z", "durationMs": 1000, "status": "success" if result == "success" else "failure", "scope": "full", "mode": "standard", "cacheState": None, "notes": None},
            {"name": "browser real-deck and dashboard capture", "startedAt": "2026-07-25T00:00:00.100Z", "finishedAt": "2026-07-25T00:00:00.600Z", "durationMs": 500, "status": "success" if result == "success" else "failure", "scope": "full", "mode": "standard", "cacheState": None, "notes": None},
        ], "slowest": [],
    })
    write_json(reports / "environment-image-provenance.json", {
        "schemaVersion": 1, "imageSource": "ghcr", "imageReference": "ghcr.io/example/e2e@" + IMAGE, "imageDigest": IMAGE, "imagePlatform": "linux/amd64", "imagePreparationDurationMs": 200, "imageSizeBytes": 1000, "environmentContractSha256": ENVIRONMENT, "environmentPublicationRunId": 1, "environmentReuseVerificationRunId": 2, "cacheState": "ghcr-digest", "workflowSourceSha": SHA_A, "e2eCheckoutSha": SHA_A, "packageSource": "fast-ci-artifact", "sourceFastCiRunId": 10, "sourceFastCiTestedSha": SHA_A, "sourcePackageSha256": "4" * 64,
    })
    write_json(reports / "real-deck-manifest-report.json", {
        "schemaVersion": 1, "status": "PASS", "manifestPath": "fixtures/real-decks/manifest.json", "packageCount": 1, "anchorCount": 3,
        "packages": [{"id": "words", "path": "words.apkg", "sizeBytes": 100, "sha256": "5" * 64, "status": "PASS"}], "syntheticFallback": False,
    })
    write_json(reports / "api-smoke-first.json", {"ok": result == "success"})
    write_json(reports / "api-smoke-restart.json", {"ok": result == "success"})
    write_json(reports / "telemetry-restart-proof.json", {"ok": result == "success"})
    write_json(reports / "resource-summary.json", {"schemaVersion": 1, "sampleCount": 1})
    if include_identity:
        write_json(
            reports / build_identity.CANONICAL_FILENAME,
            non_release_identity_document(),
        )

    if result == "success":
        events = [event("start", elapsed=0), event("start", phase="artifact-manifest", kind="phase", elapsed=1), event("pass", phase="artifact-manifest", kind="phase", elapsed=1), event("pass", elapsed=2)]
    elif result == "failure":
        code = "ASR-E2E-BROWSER"
        events = [event("start", elapsed=0), event("start", phase="browser-smoke-first", kind="phase", elapsed=1), event("fail", phase="browser-smoke-first", kind="phase", failure=code, elapsed=1), event("fail", failure=code, elapsed=2)]
        write_json(reports / "failure-summary.json", {
            "schemaVersion": 1, "result": "failure", "producer": "docker-e2e",
            "primary": {"failureCode": code, "category": "browser", "phaseId": "browser-smoke-first", "itemId": "route.home.light", "summary": "browser smoke failed", "errorType": "AssertionError", "evidencePaths": ["reports/browser-smoke-first.json"], "exitCode": 4, "signal": None},
            "secondary": [], "context": {"lastSuccessfulPhaseId": "api-smoke-first", "lastSuccessfulItemId": None, "activePhaseId": "browser-smoke-first", "activeItemId": "route.home.light"}, "cleanup": {"status": "success", "failureCount": 0},
        })
    elif result == "cancelled":
        events = [event("start", elapsed=0), event("start", phase="browser-smoke-first", kind="phase", elapsed=1), event("cancel", phase="browser-smoke-first", kind="phase", failure="ASR-E2E-CANCELLED", elapsed=1), event("cancel", failure="ASR-E2E-CANCELLED", elapsed=2)]
        write_json(reports / "cancellation-summary.json", {
            "schemaVersion": 1, "result": "cancelled", "producer": "docker-e2e", "cancellationCode": "ASR-E2E-CANCELLED", "observedAtUtc": "2026-07-25T00:00:02.000Z", "elapsedMs": 2000, "originalExitCode": 143, "originalSignal": "SIGTERM", "context": {"lastSuccessfulPhaseId": "api-smoke-first", "lastSuccessfulItemId": None, "activePhaseId": "browser-smoke-first", "activeItemId": "route.home.light"}, "cleanup": {"status": "partial", "durationMs": 50, "attempts": 1}, "artifact": {"policy": "best-effort-minimal", "status": "unavailable"}, "evidencePaths": ["reports/run-events.jsonl"],
        })
    else:
        raise AssertionError(result)
    write_jsonl(reports / "run-events.jsonl", events)
    return root


def build(root: Path, *, result: str = "success", purpose: str = "acceptance", run_id: int = 100, attempt: int = 1, **changes):
    kwargs = {
        "repository": "AliceLiddell01/anki-study-report", "run_id": run_id, "run_attempt": attempt, "event": "workflow_dispatch", "ref": "refs/heads/platform/e2e-i6-final-summary-history", "trigger_sha": SHA_A, "workflow_source_sha": SHA_A, "harness_sha": SHA_A, "mode": "standard", "scope": "full", "run_purpose": purpose, "screenshot_workers": 3, "resource_telemetry": True, "contour": "cloud", "started_at_utc": "2026-07-25T00:00:00.000Z", "finished_at_utc": "2026-07-25T00:00:02.000Z", "exit_code": {"success": 0, "failure": 4, "cancelled": 143}[result], "runner_os": "Linux", "runner_image": "ubuntu24:20260720.1", "docker_client_version": "28.0.4", "docker_server_version": "28.0.4", "docker_compose_version": "2.38.2", "powershell_version": "7.6.3", "package_source": "fast-ci-artifact", "artifact_preparation_duration_ms": 25, "workflow_duration_ms": 2000, "cleanup_status": "success", "cleanup_duration_ms": 10, "artifact_preparation_status": "success", "source_validated": True, "public_validated": True,
    }
    kwargs.update(changes)
    return final.build_summary(root, **kwargs)


def entry(summary: dict, artifact_id: int | None = 10) -> dict:
    return final.build_history_entry(
        summary,
        summary_digest=final.sha256_digest(final._json_bytes(summary)),
        main_artifact_id=artifact_id,
        main_artifact_digest="sha256:" + "6" * 64 if artifact_id else None,
        main_artifact_size_bytes=1000 if artifact_id else None,
        main_artifact_expires_at_utc="2026-10-01T00:00:00.000Z" if artifact_id else None,
    )
