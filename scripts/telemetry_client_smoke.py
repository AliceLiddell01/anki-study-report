"""Manual sanitized cloud lifecycle smoke using the production urllib client."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import types
from typing import Any
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_CONFIRMATION = "RUN_PRODUCTION_TELEMETRY_CLIENT_SMOKE"
_CONTROLLED_FAILURE_CODES = {
    "production_confirmation_required",
    "staging_endpoint_not_configured",
    "health_payload_invalid",
    "schema_contract_mismatch",
    "synthetic_event_not_queued",
    "batch_not_acknowledged",
    "enrollment_credentials_missing",
    "batch_request_missing",
    "duplicate_ack_mismatch",
    "deletion_not_confirmed",
}
_HTTP_FAILURE_PREFIXES = ("health", "schema", "duplicate", "post_delete_token")


def _load_addon_module(name: str):
    package = sys.modules.get("anki_study_report")
    if package is None:
        package = types.ModuleType("anki_study_report")
        package.__path__ = [str(ROOT / "anki_study_report")]
        package.__file__ = str(ROOT / "anki_study_report" / "__init__.py")
        sys.modules["anki_study_report"] = package
    return importlib.import_module(f"anki_study_report.{name}")


class SmokeStageError(RuntimeError):
    def __init__(self, stage: str, error: Exception) -> None:
        super().__init__(stage)
        self.stage = stage
        self.error = error


@contextmanager
def _stage(name: str):
    try:
        yield
    except SmokeStageError:
        raise
    except Exception as error:
        raise SmokeStageError(name, error) from error


class RecordingTransport:
    """Keep one request in memory for idempotency proof; never serialize it."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.last_batch: dict[str, Any] | None = None

    def request(self, method: str, url: str, *, headers: dict[str, str], body: bytes | None, timeout: float):
        if method == "POST" and url.endswith("/v1/events"):
            self.last_batch = {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        return self.delegate.request(method, url, headers=headers, body=body, timeout=timeout)


def _request(
    transport: Any,
    telemetry_client: Any,
    method: str,
    endpoint: str,
    path: str,
    *,
    token: str | None = None,
    body: bytes | None = None,
):
    return transport.request(
        method,
        f"{endpoint}{path}",
        headers=telemetry_client.telemetry_request_headers(authorization=token),
        body=body,
        timeout=telemetry_client.CONNECT_TOTAL_TIMEOUT_SECONDS,
    )


def _require_status(result: Any, expected: set[int], step: str) -> None:
    if result.status not in expected:
        raise RuntimeError(f"{step}_failed_http_{result.status}")


def _safe_failure_code(error: Exception) -> str:
    if isinstance(error, urllib.error.URLError):
        reason = error.reason
        if isinstance(reason, socket.gaierror):
            return "dns_error"
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "network_timeout"
        if isinstance(reason, ssl.SSLError):
            return "tls_error"
        return "network_error"
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "network_timeout"
    if isinstance(error, ssl.SSLError):
        return "tls_error"
    if isinstance(error, RuntimeError):
        value = str(error)
        if value in _CONTROLLED_FAILURE_CODES:
            return value
        for prefix in _HTTP_FAILURE_PREFIXES:
            marker = f"{prefix}_failed_http_"
            if value.startswith(marker) and value.removeprefix(marker).isdigit():
                return value
    return "unexpected_error"


def _failure_stage(code: str) -> str:
    if code.startswith("health_"):
        return "health"
    if code.startswith("schema_"):
        return "schema"
    if code in {"synthetic_event_not_queued"}:
        return "queue"
    if code in {"batch_not_acknowledged", "enrollment_credentials_missing", "batch_request_missing"}:
        return "delivery"
    if code.startswith("duplicate_"):
        return "idempotency"
    if code == "deletion_not_confirmed":
        return "deletion"
    if code.startswith("post_delete_token_"):
        return "post_delete_rejection"
    if code in {"production_confirmation_required", "staging_endpoint_not_configured"}:
        return "configuration"
    if code in {"dns_error", "network_timeout", "tls_error", "network_error"}:
        return "transport"
    return "unexpected"


def _empty_report(target: str, repository_sha: str | None) -> dict[str, Any]:
    return {
        "targetKind": target,
        "schemaAccepted": False,
        "enrollmentPassed": False,
        "batchAcknowledged": False,
        "duplicateAcknowledged": False,
        "deletionPassed": False,
        "postDeleteTokenRejected": False,
        "failureStage": None,
        "failureCode": None,
        "repositorySha": repository_sha,
    }


def run(target: str, confirmation: str, repository_sha: str | None) -> dict[str, Any]:
    telemetry_client = _load_addon_module("telemetry_client")
    telemetry_contract = _load_addon_module("telemetry_contract")
    product_notices = _load_addon_module("product_notices")
    telemetry_store = _load_addon_module("telemetry_store")

    with _stage("configuration"):
        if target == "production":
            if confirmation != PRODUCTION_CONFIRMATION:
                raise RuntimeError("production_confirmation_required")
            endpoint = telemetry_client.PRODUCTION_TELEMETRY_ENDPOINT
        else:
            endpoint = os.environ.get("TELEMETRY_STAGING_ENDPOINT", "").strip().rstrip("/")
            if not endpoint:
                raise RuntimeError("staging_endpoint_not_configured")

    report = _empty_report(target, repository_sha)
    urllib_transport = telemetry_client.UrlLibTransport()
    recording_transport = RecordingTransport(urllib_transport)
    credentials = None
    deleted = False

    with tempfile.TemporaryDirectory(prefix="anki-study-report-telemetry-smoke-") as directory:
        runtime = Path(directory)
        privacy = product_notices.PrivacyStore(runtime / "privacy.json")
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        privacy.save_choices(
            {"purposes": {"reliabilityDiagnostics": True, "featureUsage": False}},
            now=now,
        )
        store = telemetry_store.TelemetryStore(runtime / "telemetry.sqlite3")
        client = telemetry_client.TelemetryClient(
            store,
            privacy,
            lambda: {
                "addonVersion": telemetry_client.__version__,
                "ankiVersion": "26.05",
                "osFamily": "other",
                "locale": "unknown",
                "theme": "unknown",
            },
            endpoint=endpoint,
            transport=recording_transport,
        )
        try:
            with _stage("health"):
                health = _request(urllib_transport, telemetry_client, "GET", endpoint, "/health")
                _require_status(health, {200}, "health")
                if (health.body or {}).get("status") != "ok":
                    raise RuntimeError("health_payload_invalid")

            with _stage("schema"):
                schema = _request(urllib_transport, telemetry_client, "GET", endpoint, "/v1/schema")
                _require_status(schema, {200}, "schema")
                schema_body = schema.body or {}
                if (
                    schema_body.get("telemetrySchemaVersion") != telemetry_contract.TELEMETRY_SCHEMA_VERSION
                    or schema_body.get("consentSchemaVersion") != telemetry_contract.CONSENT_SCHEMA_VERSION
                    or schema_body.get("privacyNoticeVersion") != telemetry_contract.PRIVACY_NOTICE_VERSION
                ):
                    raise RuntimeError("schema_contract_mismatch")
                report["schemaAccepted"] = True

            with _stage("delivery"):
                queued = client.queue_semantic_event(
                    {"eventCode": "addon.started", "occurredAt": now.isoformat().replace("+00:00", "Z")}
                )
                if queued.get("queued") is not True:
                    raise RuntimeError("synthetic_event_not_queued")
                delivered = client.send_once()
                if delivered.get("code") != "telemetry.delivered" or delivered.get("acknowledgedCount") != 1:
                    raise RuntimeError("batch_not_acknowledged")
                credentials = store.credentials()
                if credentials is None:
                    raise RuntimeError("enrollment_credentials_missing")
                report["enrollmentPassed"] = True
                report["batchAcknowledged"] = True

            with _stage("idempotency"):
                batch = recording_transport.last_batch
                if batch is None:
                    raise RuntimeError("batch_request_missing")
                duplicate = urllib_transport.request(**batch)
                _require_status(duplicate, {200}, "duplicate")
                duplicate_body = duplicate.body or {}
                original_body = json.loads(batch["body"] or b"{}")
                original_ids = [event["eventId"] for event in original_body.get("events", [])]
                if (
                    duplicate_body.get("batchId") != original_body.get("batchId")
                    or duplicate_body.get("acknowledgedEventIds") != original_ids
                ):
                    raise RuntimeError("duplicate_ack_mismatch")
                report["duplicateAcknowledged"] = True

            with _stage("deletion"):
                deletion = client.attempt_deletion()
                if deletion.get("confirmed") is not True:
                    raise RuntimeError("deletion_not_confirmed")
                deleted = True
                report["deletionPassed"] = True

            with _stage("post_delete_rejection"):
                rejected = _request(
                    urllib_transport,
                    telemetry_client,
                    "POST",
                    endpoint,
                    "/v1/events",
                    token=credentials.write_token,
                    body=batch["body"],
                )
                _require_status(rejected, {401}, "post_delete_token")
                report["postDeleteTokenRejected"] = True
        finally:
            if credentials is None:
                credentials = store.credentials()
            if credentials is not None and not deleted:
                try:
                    _request(
                        urllib_transport,
                        telemetry_client,
                        "DELETE",
                        endpoint,
                        "/v1/installations/current",
                        token=credentials.write_token,
                    )
                except Exception:
                    pass
            client.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("staging", "production"), default="staging")
    parser.add_argument("--confirm-production", default="")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    repository_sha = os.environ.get("GITHUB_SHA")
    exit_code = 0
    try:
        report = run(args.target, args.confirm_production, repository_sha)
    except Exception as error:
        report = _empty_report(args.target, repository_sha)
        source_error = error.error if isinstance(error, SmokeStageError) else error
        report["failureCode"] = _safe_failure_code(source_error)
        report["failureStage"] = error.stage if isinstance(error, SmokeStageError) else _failure_stage(report["failureCode"])
        exit_code = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("telemetry client smoke passed" if exit_code == 0 else "telemetry client smoke failed")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
