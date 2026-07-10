"""Configuration helpers for Anki Study Report."""

from __future__ import annotations

import traceback
import threading
from datetime import date

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
REPORT_PERIODS = {
    "today",
    "yesterday",
    "since_last_report",
    "last_7_days",
    "last_30_days",
    "custom",
    "all_time",
}
REPORT_SCOPES = {"all", "current", "selected"}
REPORT_DETAIL_LEVELS = {"compact", "normal", "full"}
ANSWER_MODES = {"auto", "standard", "pass_fail"}
PUBLIC_SETTINGS_SECTIONS = {"dashboard", "report", "data", "server"}
PUBLIC_SETTINGS_FIELDS = {
    "dashboard": {"scope", "selectedDeckIds", "includeChildDecks"},
    "report": {
        "defaultPeriod",
        "customStartDate",
        "customEndDate",
        "scope",
        "selectedDeckIds",
        "includeChildDecks",
        "detailLevel",
        "answerMode",
    },
    "data": {
        "trackReviewerSessions",
        "sessionIdleTimeoutSeconds",
        "sessionGapCapSeconds",
        "useStudyTimeStats",
        "useStatsCacheForReport",
    },
    "server": {"autoStart", "port", "idleTimeoutSeconds"},
}
SESSION_IDLE_TIMEOUT_RANGE = (60, 86_400)
SESSION_GAP_CAP_RANGE = (1, 3_600)
SERVER_IDLE_TIMEOUT_RANGE = (0, 86_400)
_CONFIG_WRITE_LOCK = threading.RLock()
DEFAULT_CONFIG = {
    "default_period": "today",
    "custom_start_date": "",
    "custom_end_date": "",
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
        with _CONFIG_WRITE_LOCK:
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
    if port == 8765 or (port != 0 and not 1024 <= port <= 65535):
        port = DEFAULT_PORT
    idle_timeout = _config_int(
        web_dashboard.get("idle_timeout_seconds"),
        DEFAULT_IDLE_TIMEOUT_SECONDS,
    )
    if not SERVER_IDLE_TIMEOUT_RANGE[0] <= idle_timeout <= SERVER_IDLE_TIMEOUT_RANGE[1]:
        idle_timeout = DEFAULT_IDLE_TIMEOUT_SECONDS
    return {
        "auto_start": bool(web_dashboard.get("auto_start", False)),
        "port": port,
        "idle_timeout_seconds": idle_timeout,
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
    return {
        # Dashboard period is deprecated. Home owns a dedicated today view and
        # the remaining dashboard pages keep the full historical dataset.
        "period": "all_time",
        "custom_start_date": "",
        "custom_end_date": "",
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


class SettingsValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid public settings payload.")
        self.field_errors = field_errors


def public_settings_config(
    config: dict | None = None,
    *,
    deck_options: list[dict] | None = None,
) -> dict:
    source = _normalize_config(config) if config is not None else _read_config()
    display = _dashboard_display_from_config(source)
    web = _web_dashboard_from_config(source)
    dashboard_ids = display["selected_deck_ids"]
    dashboard_names = _deck_names_for_ids(
        dashboard_ids,
        deck_options,
        fallback=display["selected_deck_names"],
    )
    report_period = _enum_or_default(source.get("default_period"), REPORT_PERIODS, "today")
    report_scope = _enum_or_default(source.get("report_scope"), REPORT_SCOPES, "all")
    report_ids = _config_int_list(source.get("selected_deck_ids"))
    session_idle = _bounded_int(
        source.get("session_idle_timeout_seconds"),
        DEFAULT_CONFIG["session_idle_timeout_seconds"],
        *SESSION_IDLE_TIMEOUT_RANGE,
    )
    session_gap = _bounded_int(
        source.get("session_gap_cap_seconds"),
        DEFAULT_CONFIG["session_gap_cap_seconds"],
        *SESSION_GAP_CAP_RANGE,
    )
    session_gap = min(session_gap, session_idle)
    return {
        "dashboard": {
            "scope": "selected" if dashboard_ids else "all",
            "selectedDeckIds": dashboard_ids,
            "selectedDeckNames": dashboard_names,
            "includeChildDecks": display["include_child_decks"],
        },
        "report": {
            "defaultPeriod": report_period,
            "customStartDate": _config_str(source.get("custom_start_date")),
            "customEndDate": _config_str(source.get("custom_end_date")),
            "scope": report_scope,
            "selectedDeckIds": report_ids,
            "includeChildDecks": bool(source.get("include_child_decks", True)),
            "detailLevel": _enum_or_default(
                source.get("report_detail_level"), REPORT_DETAIL_LEVELS, "normal"
            ),
            "answerMode": _enum_or_default(source.get("answer_mode"), ANSWER_MODES, "auto"),
        },
        "data": {
            "trackReviewerSessions": bool(source.get("track_reviewer_sessions", False)),
            "sessionIdleTimeoutSeconds": session_idle,
            "sessionGapCapSeconds": session_gap,
            "useStudyTimeStats": bool(source.get("use_study_time_stats", False)),
            "useStatsCacheForReport": bool(source.get("use_stats_cache_for_report", False)),
        },
        "server": {
            "autoStart": web["auto_start"],
            "port": web["port"],
            "idleTimeoutSeconds": web["idle_timeout_seconds"],
        },
    }


def write_public_settings(
    patch: dict,
    *,
    deck_options: list[dict] | None = None,
) -> dict:
    normalized_patch = _validate_public_settings_patch(patch)
    with _CONFIG_WRITE_LOCK:
        config = _read_config()
        current = public_settings_config(config, deck_options=deck_options)
        updated = _merge_public_settings(current, normalized_patch)
        invariant_errors: dict[str, str] = {}
        if updated["dashboard"]["scope"] == "selected" and not updated["dashboard"]["selectedDeckIds"]:
            invariant_errors["dashboard.selectedDeckIds"] = "Выберите хотя бы одну колоду."
        if updated["report"]["scope"] == "selected" and not updated["report"]["selectedDeckIds"]:
            invariant_errors["report.selectedDeckIds"] = "Выберите хотя бы одну колоду."
        if updated["data"]["sessionGapCapSeconds"] > updated["data"]["sessionIdleTimeoutSeconds"]:
            invariant_errors["data.sessionGapCapSeconds"] = "Лимит интервала не может быть больше тайм-аута сессии."
        if invariant_errors:
            raise SettingsValidationError(invariant_errors)
        _apply_public_settings(config, updated, deck_options=deck_options)
        _write_config(config)
        return public_settings_config(config, deck_options=deck_options)


def _web_dashboard_from_config(config: dict) -> dict:
    web = config.get("web_dashboard") if isinstance(config.get("web_dashboard"), dict) else {}
    port = _config_int(web.get("port"), DEFAULT_PORT)
    if port == 8765 or (port != 0 and not 1024 <= port <= 65535):
        port = DEFAULT_PORT
    idle = _bounded_int(
        web.get("idle_timeout_seconds"),
        DEFAULT_IDLE_TIMEOUT_SECONDS,
        *SERVER_IDLE_TIMEOUT_RANGE,
    )
    return {
        "auto_start": bool(web.get("auto_start", False)),
        "port": port,
        "idle_timeout_seconds": idle,
    }


def _validate_public_settings_patch(patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise SettingsValidationError({"settings": "Ожидается JSON object."})
    errors: dict[str, str] = {}
    unknown_sections = sorted(set(patch) - PUBLIC_SETTINGS_SECTIONS)
    for section in unknown_sections:
        errors[section] = "Неизвестный раздел настроек."

    normalized: dict[str, dict] = {}
    for section, value in patch.items():
        if section not in PUBLIC_SETTINGS_SECTIONS:
            continue
        if not isinstance(value, dict):
            errors[section] = "Ожидается object."
            continue
        unknown_fields = sorted(set(value) - PUBLIC_SETTINGS_FIELDS[section])
        for field in unknown_fields:
            errors[f"{section}.{field}"] = "Неизвестная настройка."
        normalized[section] = dict(value)

    _validate_dashboard_patch(normalized.get("dashboard"), errors)
    _validate_report_patch(normalized.get("report"), errors)
    _validate_data_patch(normalized.get("data"), errors)
    _validate_server_patch(normalized.get("server"), errors)
    if errors:
        raise SettingsValidationError(errors)
    return normalized


def _validate_dashboard_patch(value: dict | None, errors: dict[str, str]) -> None:
    if value is None:
        return
    _validate_enum(value, "scope", {"all", "selected"}, "dashboard.scope", errors)
    _validate_int_array(value, "selectedDeckIds", "dashboard.selectedDeckIds", errors)
    _validate_bool(value, "includeChildDecks", "dashboard.includeChildDecks", errors)
    if value.get("scope") == "selected" and not value.get("selectedDeckIds"):
        errors["dashboard.selectedDeckIds"] = "Выберите хотя бы одну колоду."


def _validate_report_patch(value: dict | None, errors: dict[str, str]) -> None:
    if value is None:
        return
    _validate_enum(value, "defaultPeriod", REPORT_PERIODS, "report.defaultPeriod", errors)
    _validate_enum(value, "scope", REPORT_SCOPES, "report.scope", errors)
    _validate_enum(value, "detailLevel", REPORT_DETAIL_LEVELS, "report.detailLevel", errors)
    _validate_enum(value, "answerMode", ANSWER_MODES, "report.answerMode", errors)
    _validate_int_array(value, "selectedDeckIds", "report.selectedDeckIds", errors)
    _validate_bool(value, "includeChildDecks", "report.includeChildDecks", errors)
    for key in ("customStartDate", "customEndDate"):
        if key in value and not isinstance(value[key], str):
            errors[f"report.{key}"] = "Ожидается строка даты YYYY-MM-DD."
        elif key in value and value[key] and _parse_date(value[key]) is None:
            errors[f"report.{key}"] = "Ожидается корректная дата YYYY-MM-DD."
    if value.get("defaultPeriod") == "custom":
        start = _parse_date(value.get("customStartDate"))
        end = _parse_date(value.get("customEndDate"))
        if start is None:
            errors["report.customStartDate"] = "Укажите дату начала выбранного периода."
        if end is None:
            errors["report.customEndDate"] = "Укажите дату окончания выбранного периода."
        if start is not None and end is not None and end < start:
            errors["report.customEndDate"] = "Дата окончания не может быть раньше даты начала."
    if value.get("scope") == "selected" and not value.get("selectedDeckIds"):
        errors["report.selectedDeckIds"] = "Выберите хотя бы одну колоду."


def _validate_data_patch(value: dict | None, errors: dict[str, str]) -> None:
    if value is None:
        return
    for key in ("trackReviewerSessions", "useStudyTimeStats", "useStatsCacheForReport"):
        _validate_bool(value, key, f"data.{key}", errors)
    _validate_int_range(
        value, "sessionIdleTimeoutSeconds", "data.sessionIdleTimeoutSeconds", errors, *SESSION_IDLE_TIMEOUT_RANGE
    )
    _validate_int_range(value, "sessionGapCapSeconds", "data.sessionGapCapSeconds", errors, *SESSION_GAP_CAP_RANGE)
    idle = value.get("sessionIdleTimeoutSeconds")
    gap = value.get("sessionGapCapSeconds")
    if _is_strict_int(idle) and _is_strict_int(gap) and gap > idle:
        errors["data.sessionGapCapSeconds"] = "Лимит интервала не может быть больше тайм-аута сессии."


def _validate_server_patch(value: dict | None, errors: dict[str, str]) -> None:
    if value is None:
        return
    _validate_bool(value, "autoStart", "server.autoStart", errors)
    if "port" in value:
        port = value["port"]
        if not _is_strict_int(port) or (port != 0 and not 1024 <= port <= 65535) or port == 8765:
            errors["server.port"] = "Порт должен быть 0 или числом от 1024 до 65535; 8765 зарезервирован."
    _validate_int_range(value, "idleTimeoutSeconds", "server.idleTimeoutSeconds", errors, *SERVER_IDLE_TIMEOUT_RANGE)


def _merge_public_settings(current: dict, patch: dict) -> dict:
    merged = {section: dict(values) for section, values in current.items()}
    for section, values in patch.items():
        merged[section].update(values)
    if merged["dashboard"]["scope"] == "all":
        merged["dashboard"]["selectedDeckIds"] = []
        merged["dashboard"]["selectedDeckNames"] = []
    return merged


def _apply_public_settings(config: dict, settings: dict, *, deck_options: list[dict] | None) -> None:
    dashboard = settings["dashboard"]
    dashboard_ids = _config_int_list(dashboard["selectedDeckIds"])
    previous_display = config.get("dashboard_display") if isinstance(config.get("dashboard_display"), dict) else {}
    config["dashboard_display"] = {
        **previous_display,
        "selected_deck_ids": dashboard_ids,
        "selected_deck_names": _deck_names_for_ids(dashboard_ids, deck_options),
        "include_child_decks": bool(dashboard["includeChildDecks"]),
    }

    report = settings["report"]
    config.update(
        {
            "default_period": report["defaultPeriod"],
            "custom_start_date": _config_str(report["customStartDate"]),
            "custom_end_date": _config_str(report["customEndDate"]),
            "report_scope": report["scope"],
            "selected_deck_ids": _config_int_list(report["selectedDeckIds"]),
            "include_child_decks": bool(report["includeChildDecks"]),
            "report_detail_level": report["detailLevel"],
            "answer_mode": report["answerMode"],
        }
    )

    data = settings["data"]
    config.update(
        {
            "track_reviewer_sessions": bool(data["trackReviewerSessions"]),
            "session_idle_timeout_seconds": int(data["sessionIdleTimeoutSeconds"]),
            "session_gap_cap_seconds": int(data["sessionGapCapSeconds"]),
            "use_study_time_stats": bool(data["useStudyTimeStats"]),
            "use_stats_cache_for_report": bool(data["useStatsCacheForReport"]),
        }
    )

    server = settings["server"]
    previous_web = config.get("web_dashboard") if isinstance(config.get("web_dashboard"), dict) else {}
    config["web_dashboard"] = {
        **previous_web,
        "auto_start": bool(server["autoStart"]),
        "port": int(server["port"]),
        "idle_timeout_seconds": int(server["idleTimeoutSeconds"]),
    }


def _validate_enum(value: dict, key: str, allowed: set[str], field: str, errors: dict[str, str]) -> None:
    if key in value and (not isinstance(value[key], str) or value[key] not in allowed):
        errors[field] = f"Допустимые значения: {', '.join(sorted(allowed))}."


def _validate_bool(value: dict, key: str, field: str, errors: dict[str, str]) -> None:
    if key in value and not isinstance(value[key], bool):
        errors[field] = "Ожидается boolean."


def _validate_int_array(value: dict, key: str, field: str, errors: dict[str, str]) -> None:
    if key not in value:
        return
    raw = value[key]
    if not isinstance(raw, list) or any(not _is_strict_int(item) or item <= 0 for item in raw):
        errors[field] = "Ожидается массив положительных integer ID."


def _validate_int_range(
    value: dict,
    key: str,
    field: str,
    errors: dict[str, str],
    minimum: int,
    maximum: int,
) -> None:
    if key not in value:
        return
    number = value[key]
    if not _is_strict_int(number) or not minimum <= number <= maximum:
        errors[field] = f"Допустимое значение: от {minimum} до {maximum}."


def _is_strict_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _enum_or_default(value, allowed: set[str], fallback: str) -> str:
    return value if isinstance(value, str) and value in allowed else fallback


def _bounded_int(value, fallback: int, minimum: int, maximum: int) -> int:
    number = _config_int(value, fallback)
    return number if minimum <= number <= maximum else fallback


def _parse_date(value) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _deck_names_for_ids(
    deck_ids: list[int],
    deck_options: list[dict] | None,
    *,
    fallback: list[str] | None = None,
) -> list[str]:
    names = {
        int(option["id"]): str(option["name"])
        for option in deck_options or []
        if isinstance(option, dict)
        and _is_strict_int(option.get("id"))
        and isinstance(option.get("name"), str)
    }
    result = [names[deck_id] for deck_id in deck_ids if deck_id in names]
    if result:
        return result
    return _config_str_list(fallback)
