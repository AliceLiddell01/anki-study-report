from __future__ import annotations

from functools import partial
from types import SimpleNamespace

import pytest

from conftest import import_addon_module


def dashboard_handler_factory(module_name: str = "anki_study_report.dashboard_server"):
    handler_class = type("_DashboardRequestHandler", (), {})
    handler_class.__module__ = module_name
    return partial(handler_class)


def invoke_guard(module, server, error: BaseException) -> None:
    try:
        raise error
    except BaseException:
        module._handle_threading_http_error(server, object(), ("127.0.0.1", 8766))


@pytest.mark.parametrize(
    "error",
    [BrokenPipeError(), ConnectionAbortedError(), ConnectionResetError()],
)
def test_expected_dashboard_disconnects_do_not_delegate_to_default_traceback_handler(monkeypatch, error):
    extension_logging = import_addon_module("extension_logging")
    delegated = []
    monkeypatch.setattr(
        extension_logging,
        "_ORIGINAL_THREADING_HTTP_HANDLE_ERROR",
        lambda *args: delegated.append(args),
    )
    server = SimpleNamespace(RequestHandlerClass=dashboard_handler_factory())

    invoke_guard(extension_logging, server, error)

    assert delegated == []


def test_unexpected_dashboard_server_errors_still_delegate(monkeypatch):
    extension_logging = import_addon_module("extension_logging")
    delegated = []
    monkeypatch.setattr(
        extension_logging,
        "_ORIGINAL_THREADING_HTTP_HANDLE_ERROR",
        lambda *args: delegated.append(args),
    )
    server = SimpleNamespace(RequestHandlerClass=dashboard_handler_factory())

    invoke_guard(extension_logging, server, OSError("unexpected write failure"))

    assert len(delegated) == 1


def test_disconnect_from_other_threading_http_server_still_delegates(monkeypatch):
    extension_logging = import_addon_module("extension_logging")
    delegated = []
    monkeypatch.setattr(
        extension_logging,
        "_ORIGINAL_THREADING_HTTP_HANDLE_ERROR",
        lambda *args: delegated.append(args),
    )
    server = SimpleNamespace(RequestHandlerClass=dashboard_handler_factory("other.http_server"))

    invoke_guard(extension_logging, server, ConnectionResetError())

    assert len(delegated) == 1
