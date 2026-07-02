from __future__ import annotations

from types import SimpleNamespace

from conftest import fresh_import_addon_module


class FakeAddonManager:
    def __init__(self, config=None) -> None:
        self.config = config
        self.written = None

    def getConfig(self, addon_name):
        self.requested_addon_name = addon_name
        return self.config

    def writeConfig(self, addon_name, config):
        self.written = (addon_name, config)


def test_config_service_imports_without_anki_qt():
    config_service = fresh_import_addon_module("config_service")

    assert config_service.DEFAULT_CONFIG["default_period"] == "today"
    assert config_service.DEFAULT_CONFIG["web_dashboard"]["auto_start"] is False


def test_enabled_metrics_defaults_are_preserved():
    config_service = fresh_import_addon_module("config_service")

    enabled = config_service._enabled_metrics_from_config({"enabled_metrics": {"pass_rate": False}})

    assert enabled["pass_rate"] is False
    assert enabled["total_reviews"] is True
    assert set(enabled) == set(config_service.METRIC_KEYS)


def test_web_dashboard_config_sanitizes_values(monkeypatch):
    config_service = fresh_import_addon_module("config_service")
    manager = FakeAddonManager(
        {
            "web_dashboard": {
                "auto_start": True,
                "port": 8765,
                "idle_timeout_seconds": "30",
            }
        }
    )
    monkeypatch.setattr(config_service, "mw", SimpleNamespace(addonManager=manager))

    web_config = config_service._web_dashboard_config()

    assert web_config["auto_start"] is True
    assert web_config["port"] == config_service.DEFAULT_PORT
    assert web_config["idle_timeout_seconds"] == 30


def test_write_config_is_noop_without_anki(monkeypatch):
    config_service = fresh_import_addon_module("config_service")
    monkeypatch.setattr(config_service, "mw", None)

    config_service._write_config({"default_period": "today"})
