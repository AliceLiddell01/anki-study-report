"""Consent-gated bounded telemetry sender for the Python runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
import threading
import urllib.error
import urllib.request
from typing import Any, Callable

from .product_notices import PrivacyStore
from .telemetry_contract import (
    CONSENT_SCHEMA_VERSION,
    CONTRACT,
    PRIVACY_NOTICE_VERSION,
    TELEMETRY_SCHEMA_VERSION,
    TelemetryValidationError,
    build_queued_event,
    utc_now,
)
from .telemetry_store import QueuedEvent, TelemetryStore


PRODUCTION_TELEMETRY_ENDPOINT = "https://anki-study-report-telemetry.anki-study-report.workers.dev"
CONNECT_TOTAL_TIMEOUT_SECONDS = 10.0
PERIODIC_MIN_SECONDS = 15 * 60
QUEUE_SEND_THRESHOLD = 25
ENROLLMENT_ERROR_CODES = {
    "network_error",
    "http_400",
    "http_401",
    "http_403",
    "http_409",
    "http_429",
    "http_5xx",
    "unsupported_contract",
    "invalid_response",
    "service_disabled",
}


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: dict[str, Any] | None


class UrlLibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResult:
        request = urllib.request.Request(url, method=method, headers=headers, data=body)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read(int(CONTRACT["limits"]["requestBodyMaxBytes"]) + 1)
                return HttpResult(
                    int(response.status),
                    {str(key).lower(): str(value) for key, value in response.headers.items()},
                    _decode_json(payload),
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read(int(CONTRACT["limits"]["requestBodyMaxBytes"]) + 1)
            return HttpResult(
                int(exc.code),
                {str(key).lower(): str(value) for key, value in exc.headers.items()},
                _decode_json(payload),
            )


def request_active_client_send(client_provider: Callable[[], Any]) -> None:
    """Timer-safe indirection that resolves the current per-profile client."""
    client_provider().request_send()


class TelemetryClient:
    def __init__(
        self,
        store: TelemetryStore,
        privacy_store: PrivacyStore,
        common_dimensions_provider: Callable[[], dict[str, Any]],
        *,
        endpoint: str | None,
        transport: Any | None = None,
        allow_http_loopback: bool = False,
        now_provider: Callable[[], datetime] | None = None,
        random_provider: Callable[[], float] | None = None,
    ) -> None:
        self.store = store
        self.privacy_store = privacy_store
        self._common_dimensions_provider = common_dimensions_provider
        resolved_endpoint = endpoint
        if resolved_endpoint is None and not allow_http_loopback:
            resolved_endpoint = PRODUCTION_TELEMETRY_ENDPOINT
        self.endpoint = _validated_endpoint(resolved_endpoint, allow_http_loopback=allow_http_loopback)
        self._transport = transport or UrlLibTransport()
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._random_provider = random_provider or random.random
        self._send_lock = threading.Lock()
        self._worker_lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self._send_again = False
        self._deletion_requested = False
        self._closed = False
        self._last_background_start: datetime | None = None

    def queue_semantic_event(self, value: Any) -> dict[str, Any]:
        privacy = self.privacy_store.read()
        try:
            purpose, payload = build_queued_event(value, self._common_dimensions_provider())
        except TelemetryValidationError:
            raise
        except Exception as exc:
            raise TelemetryValidationError({"event": "Trusted event dimensions unavailable."}) from exc
        telemetry = privacy["telemetry"]
        if telemetry["deletionPending"] or telemetry["effectivePurposes"].get(purpose) is not True:
            return {"ok": True, "code": "telemetry.disabled", "queued": False, "purpose": purpose}
        queued = self.store.enqueue(purpose, payload, now=self._now_iso())
        if not queued:
            return {"ok": False, "code": "telemetry.queue_unavailable", "queued": False, "purpose": purpose}
        count = self.store.queue_count()
        if count >= QUEUE_SEND_THRESHOLD:
            self.request_send()
        return {"ok": True, "code": "telemetry.queued", "queued": True, "purpose": purpose}

    def apply_privacy_choices(self, purposes: dict[str, bool]) -> dict[str, Any]:
        disabled = [purpose for purpose in CONTRACT["purposes"] if purposes.get(purpose) is not True]
        self.store.delete_purposes(disabled)
        if not any(purposes.get(purpose) is True for purpose in CONTRACT["purposes"]):
            return self.disable_all_and_delete()
        if not self.privacy_store.read()["telemetry"]["deletionPending"]:
            self.request_send(force=True)
        return {"ok": True, "code": "telemetry.choices_applied", "deletionPending": self.privacy_store.read()["telemetry"]["deletionPending"]}

    def disable_all_and_delete(self) -> dict[str, Any]:
        self.store.clear_queue()
        credentials = self.store.credentials()
        if credentials is None:
            self.store.set_deletion_state(False)
            self.privacy_store.set_deletion_pending(False)
            return {"ok": True, "code": "telemetry.no_remote_data", "deletionPending": False, "confirmed": True}
        self.store.set_deletion_state(True)
        self.privacy_store.set_deletion_pending(True)
        self.request_send(force=True, deletion_only=True)
        return {"ok": True, "code": "telemetry.deletion_pending", "deletionPending": True, "confirmed": False}

    def delete_remote_data(self) -> dict[str, Any]:
        self.privacy_store.decline()
        return self.disable_all_and_delete()

    def request_send(
        self,
        *,
        force: bool = False,
        deletion_only: bool = False,
        bypass_enrollment_backoff: bool = False,
    ) -> bool:
        if self.endpoint is None or self._closed:
            if deletion_only and self.store.credentials() is not None:
                self._mark_deletion_failure("endpoint_not_configured", retry_after_seconds=PERIODIC_MIN_SECONDS)
            return False
        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                if bypass_enrollment_backoff:
                    return False
                self._send_again = self._send_again or force
                self._deletion_requested = self._deletion_requested or deletion_only
                return False
            now = self._now_provider().astimezone(timezone.utc)
            if not force and self._last_background_start and (now - self._last_background_start).total_seconds() < PERIODIC_MIN_SECONDS:
                return False
            self._last_background_start = now
            self._worker = threading.Thread(
                target=self._background_once,
                args=(deletion_only, bypass_enrollment_backoff),
                name="anki-study-report-telemetry",
                daemon=True,
            )
            self._worker.start()
            return True

    def _background_once(self, deletion_only: bool, bypass_enrollment_backoff: bool = False) -> None:
        try:
            delete_next = deletion_only
            bypass_next = bypass_enrollment_backoff
            for _ in range(8):
                if delete_next or self.privacy_store.read()["telemetry"]["deletionPending"]:
                    result = self.attempt_deletion()
                else:
                    result = self.send_once(bypass_enrollment_backoff=bypass_next)
                bypass_next = False
                with self._worker_lock:
                    requested = self._send_again or self._deletion_requested
                    if requested:
                        delete_next = self._deletion_requested
                        self._send_again = False
                        self._deletion_requested = False
                if requested:
                    continue
                if not delete_next and result.get("code") in {"telemetry.delivered", "telemetry.queue_empty"}:
                    threading.Event().wait(0.1)
                    if self.store.due_batch(now=self._now_iso()):
                        continue
                break
        except Exception:
            # Background telemetry must never propagate into Anki or dashboard.
            return
        finally:
            with self._worker_lock:
                self._worker = None
                if not self._closed and (self._send_again or self._deletion_requested):
                    delete_next = self._deletion_requested
                    self._send_again = False
                    self._deletion_requested = False
                    self._worker = threading.Thread(
                        target=self._background_once,
                        args=(delete_next, False),
                        name="anki-study-report-telemetry",
                        daemon=True,
                    )
                    self._worker.start()

    def send_once(self, *, bypass_enrollment_backoff: bool = False) -> dict[str, Any]:
        if not self._send_lock.acquire(blocking=False):
            return {"ok": True, "code": "telemetry.sender_busy"}
        try:
            privacy = self.privacy_store.read()["telemetry"]
            if privacy["deletionPending"]:
                return self.attempt_deletion(_lock_held=True)
            if not any(privacy["effectivePurposes"].values()):
                return {"ok": True, "code": "telemetry.disabled"}
            if self.endpoint is None:
                return {"ok": True, "code": "telemetry.endpoint_not_configured"}
            credentials = self.store.credentials()
            if credentials is None:
                enrollment = self._enroll(
                    privacy["effectivePurposes"],
                    bypass_backoff=bypass_enrollment_backoff,
                )
                if not enrollment["ok"]:
                    return enrollment
                credentials = self.store.credentials()
            batch = self.store.due_batch(now=self._now_iso())
            if not batch:
                return {"ok": True, "code": "telemetry.queue_empty"}
            return self._send_batch(batch, credentials)
        finally:
            self._send_lock.release()

    def _enroll(self, purposes: dict[str, bool], *, bypass_backoff: bool = False) -> dict[str, Any]:
        retry_state = self.store.enrollment_retry_state()
        next_attempt = retry_state["enrollmentNextAttemptAt"]
        if not bypass_backoff and isinstance(next_attempt, str) and not _iso_is_due(next_attempt, self._now_provider()):
            return {
                "ok": False,
                "code": "telemetry.enrollment_waiting",
                "nextAttemptAt": next_attempt,
            }
        payload = {
            "telemetrySchemaVersion": TELEMETRY_SCHEMA_VERSION,
            "consentSchemaVersion": CONSENT_SCHEMA_VERSION,
            "privacyNoticeVersion": PRIVACY_NOTICE_VERSION,
            "purposes": [purpose for purpose in CONTRACT["purposes"] if purposes.get(purpose) is True],
        }
        attempt_at = self._now_iso()
        self.store.record_enrollment_attempt(attempt_at)
        result = self._request_json("POST", "/v1/installations", payload=payload)
        if isinstance(result, Exception):
            return self._record_enrollment_failure("network_error", retry_after=None)
        if result.status not in {200, 201}:
            error_code = _enrollment_error_code(result)
            retry_after = _retry_after_seconds(result.headers.get("retry-after"), self._now_provider())
            return self._record_enrollment_failure(error_code, retry_after=retry_after)
        body = result.body or {}
        installation_id = body.get("installationId")
        write_token = body.get("writeToken")
        if not isinstance(installation_id, str) or not isinstance(write_token, str):
            return self._record_enrollment_failure("invalid_response", retry_after=None)
        success_at = self._now_iso()
        self.store.save_credentials(installation_id, write_token, created_at=success_at)
        self.store.record_enrollment_success(success_at)
        return {"ok": True, "code": "telemetry.enrolled"}

    def _record_enrollment_failure(self, error_code: str, *, retry_after: int | None) -> dict[str, Any]:
        bounded_code = error_code if error_code in ENROLLMENT_ERROR_CODES else "invalid_response"
        retry_state = self.store.enrollment_retry_state()
        retry_count = int(retry_state["retryCount"]) + 1
        base = min(24 * 60 * 60, 30 * (2 ** min(retry_count - 1, 10)))
        jittered = int(base * (0.75 + self._random_provider() * 0.5))
        seconds = max(jittered, int(retry_after or 0))
        next_attempt = (
            self._now_provider().astimezone(timezone.utc) + timedelta(seconds=seconds)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.store.record_enrollment_failure(
            error_code=bounded_code,
            next_attempt_at=next_attempt,
            retry_count=retry_count,
        )
        return {
            "ok": False,
            "code": "telemetry.enrollment_retry",
            "errorCode": bounded_code,
            "nextAttemptAt": next_attempt,
        }

    def check_connection_and_send_now(self) -> dict[str, Any]:
        privacy = self.privacy_store.read()["telemetry"]
        if privacy["deletionPending"]:
            return {"ok": False, "code": "telemetry.deletion_pending", "started": False}
        if not any(privacy["effectivePurposes"].values()):
            return {"ok": False, "code": "telemetry.manual_send_disabled", "started": False}
        if self.public_status()["senderState"] == "busy":
            return {"ok": False, "code": "telemetry.sender_busy", "started": False}
        started = self.request_send(force=True, bypass_enrollment_backoff=True)
        return {
            "ok": started,
            "code": "telemetry.manual_send_started" if started else "telemetry.manual_send_unavailable",
            "started": started,
        }

    def _send_batch(self, batch: list[QueuedEvent], credentials: Any) -> dict[str, Any]:
        ids = [item.event_id for item in batch]
        batch_id = hashlib.sha256(("telemetry-batch-v1\0" + "\0".join(ids)).encode("utf-8")).hexdigest()
        payload = {
            "telemetrySchemaVersion": TELEMETRY_SCHEMA_VERSION,
            "batchId": batch_id,
            "events": [item.payload for item in batch],
        }
        body_size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if body_size > int(CONTRACT["limits"]["requestBodyMaxBytes"]):
            self.store.acknowledge(ids)
            return {"ok": False, "code": "telemetry.batch_oversize"}
        attempt_at = self._now_iso()
        result = self._request_json(
            "POST",
            "/v1/events",
            payload=payload,
            authorization=credentials.write_token,
        )
        if isinstance(result, Exception):
            next_attempt = self._defer_batch(batch, retry_after=None)
            self.store.set_delivery_state(attempt_at=attempt_at, error_code="network_error")
            return {"ok": False, "code": "telemetry.delivery_retry", "nextAttemptAt": next_attempt}
        if result.status in {200, 202}:
            acknowledged = (result.body or {}).get("acknowledgedEventIds")
            if not isinstance(acknowledged, list) or any(item not in ids for item in acknowledged):
                next_attempt = self._defer_batch(batch, retry_after=None)
                self.store.set_delivery_state(attempt_at=attempt_at, error_code="invalid_response")
                return {"ok": False, "code": "telemetry.delivery_invalid_response", "nextAttemptAt": next_attempt}
            deleted = self.store.acknowledge(acknowledged, delivered_at=attempt_at)
            remaining = [item for item in batch if item.event_id not in set(acknowledged)]
            if remaining:
                self._defer_batch(remaining, retry_after=None)
            self.store.set_delivery_state(attempt_at=attempt_at, error_code=None)
            return {"ok": True, "code": "telemetry.delivered", "acknowledgedCount": deleted}
        if _retryable_status(result.status):
            retry_after = _retry_after_seconds(result.headers.get("retry-after"), self._now_provider())
            next_attempt = self._defer_batch(batch, retry_after=retry_after)
            self.store.set_delivery_state(attempt_at=attempt_at, error_code=f"http_{result.status}")
            return {"ok": False, "code": "telemetry.delivery_retry", "nextAttemptAt": next_attempt}
        if result.status == 401:
            self.store.clear_credentials()
            next_attempt = self._defer_batch(batch, retry_after=PERIODIC_MIN_SECONDS)
            self.store.set_delivery_state(attempt_at=attempt_at, error_code="authentication_rejected")
            return {"ok": False, "code": "telemetry.authentication_rejected", "nextAttemptAt": next_attempt}
        dropped = self.store.acknowledge(ids)
        self.store.set_delivery_state(attempt_at=attempt_at, error_code=f"non_retryable_{result.status}")
        return {"ok": False, "code": "telemetry.delivery_rejected", "droppedCount": dropped}

    def attempt_deletion(self, *, _lock_held: bool = False) -> dict[str, Any]:
        acquired = _lock_held or self._send_lock.acquire(blocking=False)
        if not acquired:
            return {"ok": True, "code": "telemetry.sender_busy", "deletionPending": True}
        try:
            credentials = self.store.credentials()
            if credentials is None:
                return self._confirm_deletion()
            if self.endpoint is None:
                self._mark_deletion_failure("endpoint_not_configured", retry_after_seconds=PERIODIC_MIN_SECONDS)
                return {"ok": False, "code": "telemetry.deletion_pending", "deletionPending": True}
            result = self._request_json(
                "DELETE",
                "/v1/installations/current",
                authorization=credentials.write_token,
            )
            if isinstance(result, Exception):
                self._mark_deletion_failure("network_error", retry_after_seconds=PERIODIC_MIN_SECONDS)
                return {"ok": False, "code": "telemetry.deletion_pending", "deletionPending": True}
            if result.status in {200, 202, 204, 404}:
                return self._confirm_deletion()
            retry_after = _retry_after_seconds(result.headers.get("retry-after"), self._now_provider()) if _retryable_status(result.status) else PERIODIC_MIN_SECONDS
            self._mark_deletion_failure(f"http_{result.status}", retry_after_seconds=retry_after or PERIODIC_MIN_SECONDS)
            return {"ok": False, "code": "telemetry.deletion_pending", "deletionPending": True}
        finally:
            if not _lock_held:
                self._send_lock.release()

    def _confirm_deletion(self) -> dict[str, Any]:
        self.store.clear_credentials()
        self.store.clear_queue()
        self.store.set_deletion_state(False)
        self.privacy_store.set_deletion_pending(False)
        return {"ok": True, "code": "telemetry.deletion_confirmed", "deletionPending": False, "confirmed": True}

    def _mark_deletion_failure(self, code: str, *, retry_after_seconds: int) -> None:
        next_attempt = (self._now_provider().astimezone(timezone.utc) + timedelta(seconds=retry_after_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.store.set_deletion_state(True, error_code=code, next_attempt_at=next_attempt)
        self.privacy_store.set_deletion_pending(True)

    def _defer_batch(self, batch: list[QueuedEvent], *, retry_after: int | None) -> str:
        retry_count = max((item.retry_count for item in batch), default=0) + 1
        base = min(24 * 60 * 60, 30 * (2 ** min(retry_count - 1, 10)))
        jittered = int(base * (0.75 + self._random_provider() * 0.5))
        seconds = max(jittered, int(retry_after or 0))
        next_attempt = (self._now_provider().astimezone(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.store.defer([item.event_id for item in batch], next_attempt)
        return next_attempt

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        authorization: str | None = None,
    ) -> HttpResult | Exception:
        if self.endpoint is None:
            return RuntimeError("endpoint not configured")
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if payload is not None else None
        if body is not None and len(body) > int(CONTRACT["limits"]["requestBodyMaxBytes"]):
            return ValueError("request too large")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if authorization:
            headers["Authorization"] = f"Bearer {authorization}"
        try:
            return self._transport.request(
                method,
                f"{self.endpoint}{path}",
                headers=headers,
                body=body,
                timeout=CONNECT_TOTAL_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            return exc

    def public_status(self) -> dict[str, Any]:
        status = self.store.public_status()
        if status["enrollmentState"] != "enrolled":
            next_attempt = status.get("enrollmentNextAttemptAt")
            if isinstance(next_attempt, str) and not _iso_is_due(next_attempt, self._now_provider()):
                status["enrollmentState"] = "waiting_retry"
            elif status.get("lastEnrollmentErrorCode"):
                status["enrollmentState"] = "failed"
        status.update(
            {
                "telemetrySchemaVersion": TELEMETRY_SCHEMA_VERSION,
                "endpointState": "configured" if self.endpoint else "not_configured",
                "senderState": "busy" if self._worker is not None and self._worker.is_alive() else "idle",
            }
        )
        return status

    def close(self) -> None:
        self._closed = True
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=0.2)
        if worker is None or not worker.is_alive():
            self.store.close()

    def _now_iso(self) -> str:
        return self._now_provider().astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _decode_json(payload: bytes) -> dict[str, Any] | None:
    if not payload or len(payload) > int(CONTRACT["limits"]["requestBodyMaxBytes"]):
        return None
    try:
        value = json.loads(payload.decode("utf-8"))
        return value if isinstance(value, dict) else None
    except (UnicodeError, json.JSONDecodeError):
        return None


def _validated_endpoint(value: str | None, *, allow_http_loopback: bool) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().rstrip("/")
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme == "https" and parsed.netloc and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
        return normalized
    if allow_http_loopback and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.netloc and not parsed.username and not parsed.password:
        return normalized
    raise ValueError("Telemetry endpoint must be HTTPS; only explicit loopback E2E may use HTTP")


def _retryable_status(status: int) -> bool:
    return status in {408, 425, 429} or 500 <= status <= 599


def _retry_after_seconds(value: str | None, now: datetime) -> int | None:
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return min(24 * 60 * 60, max(0, int(text)))
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(text).astimezone(timezone.utc)
        return min(24 * 60 * 60, max(0, int((parsed - now.astimezone(timezone.utc)).total_seconds())))
    except (TypeError, ValueError, OverflowError):
        return None


def _iso_is_due(value: str, now: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return parsed <= now.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return True


def _enrollment_error_code(result: HttpResult) -> str:
    public_error = (result.body or {}).get("error")
    if public_error == "service_disabled":
        return "service_disabled"
    if public_error == "invalid_enrollment":
        return "unsupported_contract"
    if result.status in {400, 401, 403, 409, 429}:
        return f"http_{result.status}"
    if 500 <= result.status <= 599:
        return "http_5xx"
    return "invalid_response"
