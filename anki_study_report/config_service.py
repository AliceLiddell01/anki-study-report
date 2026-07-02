"""Configuration helpers for Anki Study Report."""

from __future__ import annotations

import traceback

try:
    from aqt import mw
except Exception:
    mw = None

from .dashboard_server import DEFAULT_IDLE_TIMEOUT_SECONDS, DEFAULT_PORT


CONFIG_ADDON_NAME = __package__ or "anki_study_report"

METRIC_KEYS = [
    "total_reviews",
    "new_cards",
    "again_count",
    "pass_rate",
    "total_seconds",
    "real_study_time",
    "average_answer_seconds",
    "estimated_minutes",
    "answer_distribution",
    "deck_breakdown",
    "due_tomorrow",
    "forecast",
    "heatmap",
]
DEFAULT_ENABLED_METRICS = {metric: True for metric in METRIC_KEYS}
DEFAULT_WEB_DASHBOARD_CONFIG = {
    "auto_start": False,
    "port": DEFAULT_PORT,
    "idle_timeout_seconds": DEFAULT_IDLE_TIMEOUT_SECONDS,
}
DEFAULT_DASHBOARD_DISPLAY_CONFIG = {
    "period": "all_time",
    "custom_start_date": "",
    "custom_end_date": "",
    "selected_deck_ids": [],
    "selected_deck_names": [],
    "include_child_decks": True,
}
DEFAULT_CONFIG = {
    "default_period": "today",
    "report_scope": "all",
    "selected_deck_ids": [],
    "include_child_decks": True,
    "track_reviewer_sessions": False,
    "session_idle_timeout_seconds": 600,
    "session_gap_cap_seconds": 120,
    "use_study_time_stats": False,
    "use_stats_cache_for_report": False,
    "selected_profile": "manual",
    "report_detail_level": "normal",
    "answer_mode": "auto",
    "enabled_metrics": dict(DEFAULT_ENABLED_METRICS),
    "last_report_ts": None,
    "web_dashboard": dict(DEFAULT_WEB_DASHBOARD_CONFIG),
    "dashboard_display": dict(DEFAULT_DASHBOARD_DISPLAY_CONFIG),
}


def _config_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_config(config) -> dict:
    return dict(config or {}) if isinstance(config, dict) else {}


def _read_config() -> dict:
    try:
        config = mw.addonManager.getConfig(CONFIG_ADDON_NAME) if mw else None
    except Exception:
        config = None
    return _normalize_config(config)


def _write_config(config: dict) -> None:
    if mw is None:
        return
    try:
        mw.addonManager.writeConfig(CONFIG_ADDON_NAME, _normalize_config(config))
    except Exception:
        traceback.print_exc()


def _custom_profiles_from_config(config: dict) -> dict[str, dict]:
    configured = config.get("custom_profiles")
    if not isinstance(configured, dict):
        return {}

    profiles: dict[str, dict] = {}
    for profile_id, profile in configured.items():
        if not isinstance(profile, dict):
            continue
        label = str(profile.get("label") or profile_id).strip()
        settings = profile.get("settings")
        if not label or not isinstance(settings, dict):
            continue
        profiles[str(profile_id)] = {
            "label": label,
            "settings": dict(settings),
        }
    return profiles


def _last_report_ts(config: dict) -> int | None:
    try:
        value = int(config.get("last_report_ts") or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _enabled_metrics_from_config(config: dict) -> dict[str, bool]:
    configured = config.get("enabled_metrics")
    if not isinstance(configured, dict):
        configured = {}

    return {
        metric: bool(configured.get(metric, DEFAULT_ENABLED_METRICS[metric]))
        for metric in METRIC_KEYS
    }


def _web_dashboard_config() -> dict:
    config = _read_config()
    web_dashboard = config.get("web_dashboard")
    if not isinstance(web_dashboard, dict):
        web_dashboard = {}
    port = _config_int(web_dashboard.get("port"), DEFAULT_PORT)
    if port == 8765:
        port = DEFAULT_PORT
    return {
        "auto_start": bool(web_dashboard.get("auto_start", False)),
        "port": port,
        "idle_timeout_seconds": _config_int(
            web_dashboard.get("idle_timeout_seconds"),
            DEFAULT_IDLE_TIMEOUT_SECONDS,
        ),
    }


def _config_str(value, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _config_int_list(value) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number not in result:
            result.append(number)
    return result


def _config_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _dashboard_display_from_config(config: dict | None = None) -> dict:
    source = _normalize_config(config) if config is not None else _read_config()
    display = source.get("dashboard_display")
    if not isinstance(display, dict):
        display = {}
    period = _config_str(display.get("period"), DEFAULT_DASHBOARD_DISPLAY_CONFIG["period"])
    if period not in {"all_time", "last_7_days", "last_30_days", "custom"}:
        period = DEFAULT_DASHBOARD_DISPLAY_CONFIG["period"]
    return {
        "period": period,
        "custom_start_date": _config_str(display.get("custom_start_date")),
        "custom_end_date": _config_str(display.get("custom_end_date")),
        "selected_deck_ids": _config_int_list(display.get("selected_deck_ids")),
        "selected_deck_names": _config_str_list(display.get("selected_deck_names")),
        "include_child_decks": bool(display.get("include_child_decks", True)),
    }


def dashboard_display_config() -> dict:
    return _dashboard_display_from_config()


def write_dashboard_display_config(settings: dict) -> dict:
    config = _read_config()
    current = _dashboard_display_from_config(config)
    if isinstance(settings, dict):
        current.update(_dashboard_display_from_config({"dashboard_display": settings}))
    config["dashboard_display"] = current
    _write_config(config)
    return current
