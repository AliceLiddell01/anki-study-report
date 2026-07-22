from __future__ import annotations

from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

import pytest

from conftest import fresh_import_addon_module


NOW = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def request(self, method, url, *, headers, body, timeout):
        call = {"method": method, "url": url, "headers": dict(headers), "body": body, "timeout": timeout}
        self.calls.append(call)
        result = self.responder(call)
        if isinstance(result, Exception):
            raise result
        return result


def load_modules():
    product = fresh_import_addon_module("product_notices")
    contract = fresh_import_addon_module("telemetry_contract")
    store = fresh_import_addon_module("telemetry_store")
    client = fresh_import_addon_module("telemetry_client")
    return product, contract, store, client


def common():
    return {
        "addonVersion": "1.1.0",
        "ankiVersion": "26.05",
        "osFamily": "windows",
        "locale": "unknown",
        "theme": "unknown",
    }


def semantic(code="dashboard.opened"):
    return {"eventCode": code, "occurredAt": "2026-07-15T12:00:00Z"}


def make_client(tmp_path, *, purposes=None, endpoint="https://telemetry.invalid", transport=None):
    product, contract, store_module, client_module = load_modules()
    privacy = product.PrivacyStore(tmp_path / "privacy.json")
    if purposes is not None:
        privacy.save_choices({"purposes": purposes}, now=NOW)
    store = store_module.TelemetryStore(tmp_path / "telemetry.sqlite3")
    client = client_module.TelemetryClient(
        store,
        privacy,
        common,
        endpoint=endpoint,
        transport=transport or FakeTransport(lambda call: RuntimeError("network must not run")),
        now_provider=lambda: NOW,
        random_provider=lambda: 0.5,
    )
    return product, contract, store_module, client_module, privacy, store, client


def test_no_consent_means_no_queue_and_no_network(tmp_path):
    transport = FakeTransport(lambda call: RuntimeError("unexpected network"))
    *_, store, client = make_client(tmp_path, purposes=None, transport=transport)

    result = client.queue_semantic_event(semantic())

    assert result == {"ok": True, "code": "telemetry.disabled", "queued": False, "purpose": "featureUsage"}
    assert store.queue_count() == 0
    assert client.send_once()["code"] == "telemetry.disabled"
    assert transport.calls == []


def test_default_endpoint_is_pinned_and_explicit_empty_endpoint_stays_disabled(tmp_path):
    production = make_client(tmp_path / "production", purposes=None, endpoint=None)
    production_module, production_client = production[3], production[6]
    assert production_client.endpoint == production_module.PRODUCTION_TELEMETRY_ENDPOINT
    assert production_client.endpoint == "https://anki-study-report-telemetry.anki-study-report.workers.dev"

    disabled = make_client(tmp_path / "disabled", purposes=None, endpoint="")
    assert disabled[6].endpoint is None


def test_product_user_agent_uses_canonical_version_and_rejects_header_injection():
    version_module = fresh_import_addon_module("version")
    client_module = fresh_import_addon_module("telemetry_client")

    assert client_module.PRODUCT_USER_AGENT == f"AnkiStudyReport/{version_module.__version__}"
    assert client_module.PRODUCT_USER_AGENT.isascii()
    assert "\r" not in client_module.PRODUCT_USER_AGENT
    assert "\n" not in client_module.PRODUCT_USER_AGENT
    with pytest.raises(ValueError):
        client_module.product_user_agent("1.1.0\r\nX-Injected: true")


def test_one_purpose_only_and_spoofed_dimensions_rejected_before_queue(tmp_path):
    *_, contract, store_module, client_module, privacy, store, client = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
    )
    assert client.queue_semantic_event(semantic())["code"] == "telemetry.disabled"
    queued = client.queue_semantic_event({
        "eventCode": "api_operation.failed",
        "featureCode": "search_query",
        "errorCode": "timeout",
        "occurredAt": "2026-07-15T12:00:00Z",
    })
    assert queued["queued"] is True
    with pytest.raises(contract.TelemetryValidationError) as error:
        client.queue_semantic_event({**semantic(), "addonVersion": "9.9.9", "query": "private"})
    assert set(error.value.field_errors) == {"addonVersion", "query"}
    assert store.purpose_counts() == {"reliabilityDiagnostics": 1, "featureUsage": 0}


def test_enrollment_batch_ack_and_credential_secrecy(tmp_path):
    client_module_holder = {}

    def responder(call):
        module = client_module_holder["module"]
        if call["url"].endswith("/v1/installations"):
            return module.HttpResult(201, {}, {"installationId": "install-1", "writeToken": "write-secret"})
        body = json.loads(call["body"])
        return module.HttpResult(202, {}, {"acknowledgedEventIds": [event["eventId"] for event in body["events"]]})

    transport = FakeTransport(responder)
    *_, client_module, privacy, store, client = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    client_module_holder["module"] = client_module
    first = client.queue_semantic_event(semantic())
    second = client.queue_semantic_event({"eventCode": "page.opened", "pageCode": "search", "occurredAt": "2026-07-15T12:00:00Z"})
    assert first["queued"] and second["queued"]
    ids = [item.event_id for item in store.due_batch(now="2026-07-15T12:00:00Z")]
    assert len(ids) == len(set(ids)) == 2

    result = client.send_once()

    assert result == {"ok": True, "code": "telemetry.delivered", "acknowledgedCount": 2}
    assert store.queue_count() == 0
    assert len(transport.calls) == 2
    enrollment_body = json.loads(transport.calls[0]["body"])
    assert enrollment_body["purposes"] == ["featureUsage"]
    assert set(enrollment_body) == {
        "telemetrySchemaVersion",
        "consentSchemaVersion",
        "privacyNoticeVersion",
        "purposes",
    }
    event_call = transport.calls[1]
    event_body = json.loads(event_call["body"])
    assert isinstance(event_body["batchId"], str) and len(event_body["batchId"]) == 64
    assert event_call["headers"]["Authorization"] == "Bearer write-secret"
    assert "write-secret" not in event_call["url"]
    assert b"write-secret" not in event_call["body"]
    assert "write-secret" not in json.dumps(client.public_status())
    assert "install-1" not in json.dumps(client.public_status())


def test_actual_urllib_transport_completes_fake_service_lifecycle(tmp_path, caplog):
    calls = []
    state = {"deleted": False, "eventIds": []}
    write_token = "fake-service-write-token"
    installation_id = "fake-service-installation"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def _body(self):
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def _record(self):
            calls.append({
                "method": self.command,
                "path": self.path,
                "userAgent": self.headers.get("User-Agent"),
                "authorization": self.headers.get("Authorization"),
            })

        def _json(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802 - stdlib handler contract
            self._record()
            body = self._body()
            if self.path == "/v1/installations":
                self._json(201, {"installationId": installation_id, "writeToken": write_token})
                return
            if self.path == "/v1/events":
                if state["deleted"] or self.headers.get("Authorization") != f"Bearer {write_token}":
                    self._json(401, {"error": "unauthorized"})
                    return
                state["eventIds"] = [event["eventId"] for event in body["events"]]
                self._json(202, {"acknowledgedEventIds": state["eventIds"]})
                return
            self._json(404, {"error": "not_found"})

        def do_DELETE(self):  # noqa: N802 - stdlib handler contract
            self._record()
            if self.path != "/v1/installations/current" or self.headers.get("Authorization") != f"Bearer {write_token}":
                self._json(401, {"error": "unauthorized"})
                return
            state["deleted"] = True
            self._json(200, {"deleted": True})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        product, _, store_module, client_module = load_modules()
        privacy = product.PrivacyStore(tmp_path / "privacy.json")
        privacy.save_choices(
            {"purposes": {"reliabilityDiagnostics": False, "featureUsage": True}},
            now=NOW,
        )
        store = store_module.TelemetryStore(tmp_path / "telemetry.sqlite3")
        transport = client_module.UrlLibTransport()
        client = client_module.TelemetryClient(
            store,
            privacy,
            common,
            endpoint=f"http://127.0.0.1:{server.server_port}",
            transport=transport,
            allow_http_loopback=True,
            now_provider=lambda: NOW,
            random_provider=lambda: 0.5,
        )
        assert client.queue_semantic_event(semantic())["queued"] is True
        assert client.send_once() == {
            "ok": True,
            "code": "telemetry.delivered",
            "acknowledgedCount": 1,
        }

        assert client.attempt_deletion()["confirmed"] is True
        rejected = transport.request(
            "POST",
            f"http://127.0.0.1:{server.server_port}/v1/events",
            headers=client_module.telemetry_request_headers(authorization=write_token),
            body=json.dumps({"telemetrySchemaVersion": 1, "batchId": "old", "events": []}).encode("utf-8"),
            timeout=2.0,
        )
        assert rejected.status == 401
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)

    assert [call["method"] for call in calls] == ["POST", "POST", "DELETE", "POST"]
    assert all(call["userAgent"] == client_module.PRODUCT_USER_AGENT for call in calls)
    assert calls[0]["authorization"] is None
    assert "Python-urllib" not in json.dumps(calls)
    assert write_token not in json.dumps(client.public_status())
    assert installation_id not in json.dumps(client.public_status())
    assert write_token not in caplog.text


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_statuses_defer_with_retry_after_and_no_storm(tmp_path, status):
    holder = {}
    transport = FakeTransport(lambda call: holder["module"].HttpResult(status, {"retry-after": "120"}, {"ok": False}))
    *_, client_module, privacy, store, client = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    holder["module"] = client_module
    store.save_credentials("install", "token")
    client.queue_semantic_event(semantic())

    result = client.send_once()

    assert result["code"] == "telemetry.delivery_retry"
    assert result["nextAttemptAt"] == "2026-07-15T12:02:00Z"
    assert store.due_batch(now="2026-07-15T12:01:59Z") == []
    assert store.due_batch(now="2026-07-15T12:02:00Z")[0].retry_count == 1
    assert len(transport.calls) == 1


def test_timeout_backoff_and_non_retryable_4xx(tmp_path):
    timeout_transport = FakeTransport(lambda call: TimeoutError("bounded timeout"))
    *_, store, timeout_client = make_client(
        tmp_path / "timeout",
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=timeout_transport,
    )[-3:]
    store.save_credentials("install", "token")
    timeout_client.queue_semantic_event(semantic())
    retry = timeout_client.send_once()
    assert retry["code"] == "telemetry.delivery_retry"
    assert store.queue_count() == 1

    holder = {}
    transport = FakeTransport(lambda call: holder["module"].HttpResult(400, {}, {"ok": False}))
    result = make_client(
        tmp_path / "bad-request",
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    client_module, store, client = result[3], result[5], result[6]
    holder["module"] = client_module
    store.save_credentials("install", "token")
    client.queue_semantic_event(semantic())
    rejected = client.send_once()
    assert rejected["code"] == "telemetry.delivery_rejected"
    assert store.queue_count() == 0
    assert len(transport.calls) == 1


def test_partial_ack_keeps_unacknowledged_event_with_backoff(tmp_path):
    holder = {}

    def responder(call):
        body = json.loads(call["body"])
        return holder["module"].HttpResult(202, {}, {"acknowledgedEventIds": [body["events"][0]["eventId"]]})

    transport = FakeTransport(responder)
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    client_module, store, client = result[3], result[5], result[6]
    holder["module"] = client_module
    store.save_credentials("install", "token")
    client.queue_semantic_event(semantic())
    client.queue_semantic_event({"eventCode": "page.opened", "pageCode": "home", "occurredAt": "2026-07-15T12:00:00Z"})
    delivered = client.send_once()
    assert delivered["acknowledgedCount"] == 1
    assert store.queue_count() == 1
    assert store.due_batch(now="2026-07-15T12:00:29Z") == []


def test_withdrawal_clears_queue_and_offline_deletion_keeps_only_credentials(tmp_path):
    *_, privacy, store, client = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": True},
        endpoint="",
    )[-3:]
    store.save_credentials("install", "delete-token")
    client.queue_semantic_event(semantic())
    result = client.delete_remote_data()

    assert result["deletionPending"] is True
    assert privacy.read()["telemetry"]["status"] == "declined"
    assert privacy.read()["telemetry"]["deletionPending"] is True
    assert not any(privacy.read()["telemetry"]["effectivePurposes"].values())
    assert store.queue_count() == 0
    assert store.credentials().write_token == "delete-token"
    assert store.public_status()["deletionErrorCode"] == "endpoint_not_configured"


def test_confirmed_delete_destroys_credentials_and_pending_state(tmp_path):
    holder = {}
    transport = FakeTransport(lambda call: holder["module"].HttpResult(204, {}, None))
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
        transport=transport,
    )
    client_module, privacy, store, client = result[3], result[4], result[5], result[6]
    holder["module"] = client_module
    store.save_credentials("install/id", "delete-token")
    store.set_deletion_state(True)
    privacy.set_deletion_pending(True)

    deleted = client.attempt_deletion()

    assert deleted["confirmed"] is True
    assert store.credentials() is None
    assert privacy.read()["telemetry"]["deletionPending"] is False
    assert transport.calls[0]["method"] == "DELETE"
    assert transport.calls[0]["url"].endswith("/v1/installations/current")
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer delete-token"


def test_reconsent_pause_preserves_queue_and_credentials_without_network(tmp_path):
    transport = FakeTransport(lambda call: RuntimeError("network forbidden"))
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    privacy, store, client = result[4], result[5], result[6]
    client.queue_semantic_event(semantic())
    store.save_credentials("install", "token")
    document = json.loads(privacy.path.read_text(encoding="utf-8"))
    document["telemetry"]["privacyNoticeVersion"] = "2026-01-01"
    privacy.path.write_text(json.dumps(document), encoding="utf-8")

    assert client.send_once()["code"] == "telemetry.disabled"
    assert store.queue_count() == 1
    assert store.credentials() is not None
    assert transport.calls == []


def test_addon_update_reopen_preserves_decision_queue_and_credentials(tmp_path):
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        endpoint="",
    )
    product, store_module = result[0], result[2]
    privacy, store, client = result[4], result[5], result[6]
    client.queue_semantic_event(semantic())
    store.save_credentials("installation-before-update", "token-before-update")
    expected_privacy = privacy.read()
    store.close()

    reopened_privacy = product.PrivacyStore(tmp_path / "privacy.json")
    reopened_store = store_module.TelemetryStore(tmp_path / "telemetry.sqlite3")

    assert reopened_privacy.read() == expected_privacy
    assert reopened_store.queue_count() == 1
    assert reopened_store.credentials().installation_id == "installation-before-update"
    assert "token-before-update" not in json.dumps(reopened_store.public_status())
    reopened_store.close()


def test_transport_failures_do_not_print_event_body_or_token(tmp_path, capsys, caplog):
    transport = FakeTransport(lambda call: TimeoutError("private-content-must-not-be-logged"))
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    store, client = result[5], result[6]
    store.save_credentials("installation-secret", "write-token-secret")
    client.queue_semantic_event(semantic())

    client.send_once()

    captured = capsys.readouterr()
    combined = captured.out + captured.err + caplog.text
    assert "private-content-must-not-be-logged" not in combined
    assert "write-token-secret" not in combined
    assert "dashboard.opened" not in combined


def test_background_request_is_non_blocking_and_single_sender(tmp_path):
    holder = {}

    def slow(call):
        time.sleep(0.1)
        return holder["module"].HttpResult(201, {}, {"installationId": "install", "writeToken": "token"})

    transport = FakeTransport(slow)
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
        transport=transport,
    )
    holder["module"] = result[3]
    client = result[6]
    started = time.perf_counter()
    assert client.request_send(force=True) is True
    assert client.request_send(force=True) is False
    assert time.perf_counter() - started < 0.05
    client._worker.join(timeout=1)


def test_threshold_request_is_coalesced_while_enrollment_worker_is_busy(tmp_path):
    holder = {}

    def slow(call):
        if call["url"].endswith("/v1/installations"):
            time.sleep(0.05)
            return holder["module"].HttpResult(201, {}, {"installationId": "install", "writeToken": "token"})
        body = json.loads(call["body"])
        return holder["module"].HttpResult(202, {}, {"acknowledgedEventIds": [event["eventId"] for event in body["events"]]})

    transport = FakeTransport(slow)
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
        transport=transport,
    )
    holder["module"] = result[3]
    store, client = result[5], result[6]
    assert client.request_send(force=True) is True
    for _ in range(25):
        assert client.queue_semantic_event({
            "eventCode": "api_operation.failed",
            "featureCode": "dashboard_start",
            "errorCode": "internal_error",
            "occurredAt": "2026-07-15T12:00:00Z",
        })["queued"] is True
    deadline = time.monotonic() + 2
    while store.queue_count() and time.monotonic() < deadline:
        time.sleep(0.01)

    assert store.queue_count() == 0
    assert [call["url"].rsplit("/", 1)[-1] for call in transport.calls].count("events") >= 1


def test_background_worker_preserves_continuation_at_iteration_limit(tmp_path):
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
    )
    client = result[6]
    calls = 0

    def request_again_through_iteration_limit(*, bypass_enrollment_backoff=False):
        nonlocal calls
        calls += 1
        if calls <= 8:
            with client._worker_lock:
                client._send_again = True
            return {"ok": True, "code": "telemetry.delivered"}
        return {"ok": True, "code": "telemetry.queue_empty"}

    client.send_once = request_again_through_iteration_limit
    client._background_once(False)
    deadline = time.monotonic() + 1
    while calls < 9 and time.monotonic() < deadline:
        time.sleep(0.01)
    worker = client._worker
    if worker is not None:
        worker.join(timeout=1)

    assert calls == 9


def test_enrollment_backoff_persists_and_manual_check_bypasses_it_once(tmp_path):
    holder = {}
    transport = FakeTransport(
        lambda call: holder["module"].HttpResult(503, {"retry-after": "120"}, {"error": "service_disabled"})
    )
    result = make_client(
        tmp_path,
        purposes={"reliabilityDiagnostics": False, "featureUsage": True},
        transport=transport,
    )
    client_module, privacy, store, client = result[3], result[4], result[5], result[6]
    holder["module"] = client_module
    client.queue_semantic_event(semantic())

    first = client.send_once()
    waiting = client.send_once()

    assert first["code"] == "telemetry.enrollment_retry"
    assert first["errorCode"] == "service_disabled"
    assert first["nextAttemptAt"] == "2026-07-15T12:02:00Z"
    assert waiting == {
        "ok": False,
        "code": "telemetry.enrollment_waiting",
        "nextAttemptAt": "2026-07-15T12:02:00Z",
    }
    assert len(transport.calls) == 1
    assert client.public_status()["enrollmentState"] == "waiting_retry"
    store.close()

    reopened_store = result[2].TelemetryStore(tmp_path / "telemetry.sqlite3")
    reopened = client_module.TelemetryClient(
        reopened_store,
        privacy,
        common,
        endpoint="https://telemetry.invalid",
        transport=transport,
        now_provider=lambda: NOW,
        random_provider=lambda: 0.5,
    )
    assert reopened.send_once()["code"] == "telemetry.enrollment_waiting"
    manual = reopened.check_connection_and_send_now()
    assert manual == {"ok": True, "code": "telemetry.manual_send_started", "started": True}
    reopened._worker.join(timeout=1)
    assert len(transport.calls) == 2
    assert reopened.public_status()["lastEnrollmentErrorCode"] == "service_disabled"
    reopened.close()


def test_manual_check_requires_effective_purpose_and_refuses_deletion_or_busy_sender(tmp_path):
    disabled = make_client(tmp_path / "disabled", purposes=None)
    assert disabled[6].check_connection_and_send_now()["code"] == "telemetry.manual_send_disabled"

    deletion = make_client(
        tmp_path / "deletion",
        purposes={"reliabilityDiagnostics": True, "featureUsage": False},
        endpoint="",
    )
    deletion[4].set_deletion_pending(True)
    assert deletion[6].check_connection_and_send_now()["code"] == "telemetry.deletion_pending"


def test_active_client_timer_indirection_never_calls_closed_profile_client():
    module = load_modules()[3]

    class FakeClient:
        def __init__(self):
            self.calls = 0
            self.closed = False

        def request_send(self):
            assert not self.closed
            self.calls += 1

        def close(self):
            self.closed = True

    profile_a = FakeClient()
    profile_b = FakeClient()
    active = {"client": profile_a}
    module.request_active_client_send(lambda: active["client"])
    profile_a.close()
    active["client"] = profile_b
    module.request_active_client_send(lambda: active["client"])

    assert profile_a.calls == 1
    assert profile_b.calls == 1
