from __future__ import annotations

from types import SimpleNamespace

import pytest

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
        self.config = config


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


def test_public_settings_normalize_incomplete_legacy_config():
    config_service = fresh_import_addon_module("config_service")

    settings = config_service.public_settings_config(
        {
            "default_period": "invalid",
            "dashboard_display": {
                "period": "last_7_days",
                "selected_deck_ids": [2, "2", "bad", 3],
                "selected_deck_names": ["Stale deck"],
            },
            "session_idle_timeout_seconds": -1,
            "session_gap_cap_seconds": 999999,
            "web_dashboard": {"port": 80, "idle_timeout_seconds": -5},
        },
        deck_options=[{"id": 2, "name": "Japanese"}],
    )

    assert settings["dashboard"] == {
        "scope": "selected",
        "selectedDeckIds": [2, 3],
        "selectedDeckNames": ["Japanese"],
        "includeChildDecks": True,
    }
    assert settings["report"]["defaultPeriod"] == "today"
    assert settings["data"]["sessionIdleTimeoutSeconds"] == 600
    assert settings["data"]["sessionGapCapSeconds"] == 120
    assert settings["server"] == {
        "autoStart": False,
        "port": config_service.DEFAULT_PORT,
        "idleTimeoutSeconds": config_service.DEFAULT_IDLE_TIMEOUT_SECONDS,
    }


def test_public_settings_valid_write_preserves_internal_and_unknown_keys(monkeypatch):
    config_service = fresh_import_addon_module("config_service")
    manager = FakeAddonManager(
        {
            "last_report_ts": 123,
            "internal_future_key": {"keep": True},
            "dashboard_display": {"period": "last_30_days", "internal": "keep"},
            "web_dashboard": {"future": "keep"},
        }
    )
    monkeypatch.setattr(config_service, "mw", SimpleNamespace(addonManager=manager))

    saved = config_service.write_public_settings(
        {
            "dashboard": {
                "scope": "selected",
                "selectedDeckIds": [20, 20, 10],
                "includeChildDecks": False,
            },
            "report": {
                "defaultPeriod": "last_7_days",
                "scope": "selected",
                "selectedDeckIds": [10],
                "includeChildDecks": True,
                "detailLevel": "full",
                "answerMode": "pass_fail",
            },
            "data": {
                "trackReviewerSessions": True,
                "sessionIdleTimeoutSeconds": 900,
                "sessionGapCapSeconds": 120,
                "useStudyTimeStats": False,
                "useStatsCacheForReport": True,
            },
            "server": {"autoStart": True, "port": 9000, "idleTimeoutSeconds": 600},
        },
        deck_options=[{"id": 10, "name": "A"}, {"id": 20, "name": "B"}],
    )

    written = manager.written[1]
    assert written["last_report_ts"] == 123
    assert written["internal_future_key"] == {"keep": True}
    assert written["dashboard_display"]["internal"] == "keep"
    assert written["dashboard_display"]["period"] == "last_30_days"
    assert written["web_dashboard"]["future"] == "keep"
    assert saved["dashboard"]["selectedDeckIds"] == [20, 10]
    assert saved["dashboard"]["selectedDeckNames"] == ["B", "A"]
    assert saved["report"]["detailLevel"] == "full"
    assert saved["server"]["port"] == 9000


def test_public_settings_partial_update_preserves_other_public_values(monkeypatch):
    config_service = fresh_import_addon_module("config_service")
    manager = FakeAddonManager(
        {
            "default_period": "all_time",
            "report_scope": "current",
            "use_stats_cache_for_report": False,
            "web_dashboard": {"port": 9001},
        }
    )
    monkeypatch.setattr(config_service, "mw", SimpleNamespace(addonManager=manager))

    saved = config_service.write_public_settings({"data": {"useStatsCacheForReport": True}})

    assert saved["data"]["useStatsCacheForReport"] is True
    assert saved["report"]["defaultPeriod"] == "all_time"
    assert saved["report"]["scope"] == "current"
    assert saved["server"]["port"] == 9001


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"unknown": {}}, "unknown"),
        ({"server": {"token": "secret"}}, "server.token"),
        ({"server": {"port": 80}}, "server.port"),
        ({"server": {"autoStart": "yes"}}, "server.autoStart"),
        ({"report": {"answerMode": "magic"}}, "report.answerMode"),
        ({"report": {"defaultPeriod": "custom", "customStartDate": "2026-07-02", "customEndDate": "2026-07-01"}}, "report.customEndDate"),
        ({"dashboard": {"scope": "selected", "selectedDeckIds": []}}, "dashboard.selectedDeckIds"),
        ({"data": {"sessionGapCapSeconds": 1000, "sessionIdleTimeoutSeconds": 600}}, "data.sessionGapCapSeconds"),
    ],
)
def test_public_settings_reject_invalid_or_internal_fields(payload, field):
    config_service = fresh_import_addon_module("config_service")

    with pytest.raises(config_service.SettingsValidationError) as error:
        config_service.write_public_settings(payload)

    assert field in error.value.field_errors


def test_dashboard_period_is_deprecated_and_normalized_to_all_time():
    config_service = fresh_import_addon_module("config_service")

    display = config_service._dashboard_display_from_config(
        {"dashboard_display": {"period": "custom", "custom_start_date": "2026-01-01"}}
    )

    assert display["period"] == "all_time"
    assert display["custom_start_date"] == ""
