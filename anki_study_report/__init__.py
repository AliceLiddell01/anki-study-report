"""Anki Study Report add-on.

Minimal read-only UI scaffold for Anki 26.05 / Python 3.13 / PyQt6.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import json
import os
import platform
from pathlib import Path
from time import monotonic
import shutil
import sys
import threading
import traceback

from .version import __version__


def _e2e_events_enabled() -> bool:
    return os.environ.get("ANKI_STUDY_REPORT_E2E") == "1"


def _e2e_events_path() -> Path:
    explicit = os.environ.get("ANKI_STUDY_REPORT_E2E_EVENTS_FILE")
    if explicit:
        return Path(explicit)
    artifacts = (
        os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR")
        or os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS")
        or "/e2e/artifacts"
    )
    return Path(artifacts) / "runtime" / "addon-e2e-events.jsonl"


def _e2e_json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def _e2e_safe_repr(value) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<unreprable {type(value).__name__}>"
    return text[:500]


def _write_e2e_event(stage: str, **fields) -> None:
    if not _e2e_events_enabled():
        return
    try:
        payload = {
            "stage": str(stage),
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "pid": os.getpid(),
        }
        payload.update({str(key): _e2e_json_safe(value) for key, value in fields.items()})
        path = _e2e_events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            file.write("\n")
        print(f"[ASR:E2E] stage={stage}")
    except Exception:
        pass


_write_e2e_event("import_start")
if _e2e_events_enabled():
    _addon_dir = Path(__file__).resolve().parent
    _write_e2e_event(
        "addon_folder_present",
        path=str(_addon_dir),
        hasInit=(_addon_dir / "__init__.py").is_file(),
        hasManifest=(_addon_dir / "manifest.json").is_file(),
    )
    _write_e2e_event(
        "e2e_env_detected",
        artifacts=str(_e2e_events_path().parent),
        envVar="ANKI_STUDY_REPORT_E2E",
    )

from aqt import gui_hooks, mw
from aqt.qt import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDate,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QDesktopServices,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showCritical, showInfo

from .metrics import (
    ATTENTION_CARD_LIMIT,
    collect_attention_cards_with_status,
    collect_metrics,
    expand_deck_ids,
)
from .heatmap_metrics import diagnose_review_heatmap_personal
from .report_builder import build_markdown_report, render_html_report
from .report_from_cache import build_cached_report_parts, merge_cached_report_parts
from .report_publication import report_metrics_cache_key
from .session_tracker import (
    collect_tracked_study_time,
    diagnose_session_tracker,
    session_tracker_log_text,
    setup_session_tracking,
    unavailable_tracked_time,
)
from .study_time_integration import (
    collect_real_study_time,
    diagnose_study_time_stats,
    integration_log_text,
)
from .dashboard_server import (
    DEFAULT_IDLE_TIMEOUT_SECONDS,
    DEFAULT_PORT,
    DashboardServerManager,
)
from .dashboard_actions import DashboardActions
from .dashboard_payload import (
    build_dashboard_report_payload,
    build_default_dashboard_metadata,
    build_today_dashboard_payload,
    dashboard_int,
    metrics_from_cache_snapshot,
)
from .browser_actions import (
    BROWSER_ACTION_CARD_LIMIT,
    card_ids_search_query,
    collect_browser_action_card_ids,
    open_browser_search,
)
from .search_runtime import run_search_inspect_sync, run_search_query_sync
from .triage_runtime import run_triage_query_sync
from .inspection_profile_runtime import (
    run_inspection_profile_query_sync,
    run_inspection_profile_update_sync,
    run_inspection_profile_validate_sync,
)
from .inspection_profile_store import InspectionProfileStore
from .entity_action_runtime import run_card_action_sync, run_note_action_sync
from .config_service import (
    DEFAULT_ENABLED_METRICS,
    SettingsValidationError,
    _custom_profiles_from_config,
    dashboard_display_config,
    _enabled_metrics_from_config,
    _last_report_ts,
    _read_config,
    _web_dashboard_config,
    _write_config,
    public_settings_config,
    write_public_settings,
)
from .extension_logging import configure_log_dir, log_event, log_exception, log_status
from .stats_cache import StatsCacheManager
from .profile_service import (
    ProfilePreferencesStore,
    ProfileValidationError,
    build_profile_payload,
)
from .product_notices import (
    PrivacyStore,
    ProductNoticeStore,
    ProductNoticeValidationError,
    load_bundled_changelog,
    privacy_response,
    product_notices_response,
)
from .telemetry_client import TelemetryClient, request_active_client_send
from .telemetry_contract import TelemetryValidationError, utc_now
from .telemetry_store import TelemetryStore
from .notification_store import NotificationStore, NotificationValidationError
from .signal_detection import SignalEvaluator, collect_repeated_again_cards, source_revision as signal_source_revision
from .activity_service import build_activity_hub_payload
from .deck_hub import collect_deck_catalog
from .statistics_service import (
    StatisticsValidationError,
    build_statistics_hub,
    build_statistics_result,
    collect_statistics_current_snapshot,
    normalize_statistics_query,
)
from .fsrs_service import FsrsValidationError, execute_fsrs_query


ADDON_NAME = "Anki Study Report"
SCOPE_ALL = "all"
SCOPE_CURRENT = "current"
SCOPE_SELECTED = "selected"
MANUAL_PROFILE_ID = "manual"
CUSTOM_PROFILE_PREFIX = "custom:"
SCOPE_LABELS = {
    SCOPE_ALL: "Все колоды",
    SCOPE_CURRENT: "Текущая колода",
    SCOPE_SELECTED: "Выбранные колоды",
}
PERIODS = [
    ("today", "Сегодня"),
    ("yesterday", "Вчера"),
    ("since_last_report", "С последнего отчёта"),
    ("last_7_days", "Последние 7 дней"),
    ("last_30_days", "Последние 30 дней"),
    ("custom", "Выбранный период"),
    ("all_time", "Всё время"),
]
DETAIL_LEVELS = [
    ("compact", "Компактный"),
    ("normal", "Обычный"),
    ("full", "Полный"),
]
ANSWER_MODES = [
    ("auto", "Авто"),
    ("standard", "Обычный Anki"),
    ("pass_fail", "Pass/Fail"),
]
PROFILES = [
    (
        MANUAL_PROFILE_ID,
        "Ручной режим",
        None,
    ),
]
PROFILE_SETTINGS = {profile_id: settings for profile_id, _label, settings in PROFILES}
REPORT_CACHE_TTL_SECONDS = 5
LARGE_PERIOD_WARNING_DAYS = 180
SECONDS_IN_DAY = 86_400


def _addon_runtime_data_dir() -> Path:
    addon_id = "anki_study_report"
    try:
        addon_id = str(mw.addonManager.addonFromModule(__name__) or addon_id)
    except Exception:
        pass
    try:
        profile_dir = Path(mw.pm.profileFolder())
        return profile_dir / "addon_data" / addon_id
    except Exception:
        return Path(__file__).resolve().parent / "user_files"


def _configure_runtime_data_paths() -> Path:
    data_dir = _addon_runtime_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        _migrate_legacy_user_files(data_dir)
    except Exception:
        traceback.print_exc()
    configure_log_dir(data_dir / "logs")
    return data_dir


def _migrate_legacy_user_files(data_dir: Path) -> None:
    legacy_dir = Path(__file__).resolve().parent / "user_files"
    if not legacy_dir.exists() or legacy_dir.resolve() == data_dir.resolve():
        return

    cache_src = legacy_dir / "study_report_cache.sqlite3"
    cache_dst = data_dir / "study_report_cache.sqlite3"
    if cache_src.is_file() and not cache_dst.exists():
        try:
            shutil.copy2(cache_src, cache_dst)
        except OSError:
            pass

    logs_src = legacy_dir / "logs"
    logs_dst = data_dir / "logs"
    if logs_src.is_dir():
        logs_dst.mkdir(parents=True, exist_ok=True)
        for source in logs_src.glob("anki_study_report.log*"):
            target = logs_dst / source.name
            if target.exists():
                continue
            try:
                shutil.copy2(source, target)
            except OSError:
                pass

    try:
        shutil.rmtree(legacy_dir)
    except OSError:
        pass


_RUNTIME_DATA_DIR = _configure_runtime_data_paths()
_REPORT_CACHE: dict[str, object] = {
    "key": None,
    "created_at": 0.0,
    "metrics": None,
}
_STATISTICS_QUERY_CACHE: dict[str, object] = {"key": None, "value": None}
_DASHBOARD_ACTIONS: DashboardActions | None = None
_STUDY_REPORT_DIALOG: StudyReportDialog | None = None
_INTEGRATIONS_DIALOG: IntegrationDiagnosticsDialog | None = None
_WEB_DASHBOARD_DIALOG: WebDashboardSettingsDialog | None = None
_LAUNCHER_DIALOG: LauncherDialog | None = None
_DASHBOARD_SERVER = DashboardServerManager()
_STATS_CACHE = StatsCacheManager(_RUNTIME_DATA_DIR / "study_report_cache.sqlite3")
_PROFILE_STORE = ProfilePreferencesStore(_RUNTIME_DATA_DIR / "profile.json")
_INSPECTION_PROFILE_STORE = InspectionProfileStore(_RUNTIME_DATA_DIR / "inspection_profiles.json")
_PRODUCT_NOTICE_STORE = ProductNoticeStore(_RUNTIME_DATA_DIR / "product_notices.json")
_PRIVACY_STORE = PrivacyStore(_RUNTIME_DATA_DIR / "privacy.json")
_TELEMETRY_STORE = TelemetryStore(_RUNTIME_DATA_DIR / "telemetry.sqlite3")
_NOTIFICATION_STORE = NotificationStore(_RUNTIME_DATA_DIR / "notifications.sqlite3")
_SIGNAL_EVALUATOR = SignalEvaluator(_NOTIFICATION_STORE, diagnostic_logger=log_event)


def _new_telemetry_client(store: TelemetryStore, privacy_store: PrivacyStore) -> TelemetryClient:
    return TelemetryClient(
        store,
        privacy_store,
        lambda: _trusted_telemetry_dimensions(),
        endpoint=(
            os.environ.get("ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT")
            if _e2e_events_enabled()
            else None
        ),
        allow_http_loopback=_e2e_events_enabled(),
    )


_TELEMETRY_CLIENT = _new_telemetry_client(_TELEMETRY_STORE, _PRIVACY_STORE)
_TELEMETRY_TIMER: object | None = None
_TELEMETRY_STARTED_CLIENT: TelemetryClient | None = None
try:
    _notice_state = _PRODUCT_NOTICE_STORE.record_started(__version__)
    _NOTIFICATION_STORE.upsert_release(__version__, source_revision=f"release:{__version__}")
    if _notice_state.get("lastSeenReleaseVersion") == __version__:
        _NOTIFICATION_STORE.mark_release_read(__version__)
except Exception:
    log_exception("product_notices.startup.error", "Could not persist product notice startup state")
_E2E_BOOTSTRAP_STARTED = False
_E2E_BOOTSTRAP_DONE = False


class StudyReportDialog(QDialog):
    """Small placeholder dialog for future read-only study reports."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = _read_config()
        self._custom_profiles = _custom_profiles_from_config(self._config)
        self._deck_items: list[QListWidgetItem] = []
        self._enabled_metrics = _enabled_metrics_from_config(self._config)
        self._latest_report_markdown: str | None = None
        self._latest_report_cache_key: object | None = None

        self.setWindowTitle(ADDON_NAME)
        self.setMinimumSize(760, 560)

        title = QLabel("Anki Study Report")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        profile_label = QLabel("Профиль:")
        self.profile_combo = QComboBox()
        self._populate_profile_combo()
        self._restore_profile()

        profile_row = QHBoxLayout()
        profile_row.addWidget(profile_label)
        profile_row.addWidget(self.profile_combo, 1)

        detail_label = QLabel("Детализация:")
        self.detail_combo = QComboBox()
        for detail_id, label in DETAIL_LEVELS:
            self.detail_combo.addItem(label, detail_id)
        self._describe_combobox(
            self.detail_combo,
            "detail_level_combo",
            "Детализация отчёта",
            "Выберите уровень детализации отчёта.",
        )
        self._restore_detail_level()

        detail_row = QHBoxLayout()
        detail_row.addWidget(detail_label)
        detail_row.addWidget(self.detail_combo, 1)

        answer_mode_label = QLabel("Режим ответов:")
        self.answer_mode_combo = QComboBox()
        for mode_id, label in ANSWER_MODES:
            self.answer_mode_combo.addItem(label, mode_id)
        self._describe_combobox(
            self.answer_mode_combo,
            "answer_mode_combo",
            "Режим ответов",
            "Выберите режим подсчёта ответов: авто, обычный Anki или Pass/Fail.",
        )
        self._restore_answer_mode()

        answer_mode_row = QHBoxLayout()
        answer_mode_row.addWidget(answer_mode_label)
        answer_mode_row.addWidget(self.answer_mode_combo, 1)

        self.dashboard_status_label = QLabel()
        self.open_dashboard_button = QPushButton("Открыть web dashboard")
        self.dashboard_settings_button = QPushButton("Настройки dashboard")
        self.stop_dashboard_button = QPushButton("Остановить")
        self.open_dashboard_button.clicked.connect(self._open_dashboard_from_report)
        self.dashboard_settings_button.clicked.connect(_open_web_dashboard_settings_dialog)
        self.stop_dashboard_button.clicked.connect(self._stop_dashboard_from_report)

        dashboard_row = QHBoxLayout()
        dashboard_row.addWidget(QLabel("Web dashboard:"))
        dashboard_row.addWidget(self.dashboard_status_label, 1)
        dashboard_row.addWidget(self.open_dashboard_button)
        dashboard_row.addWidget(self.dashboard_settings_button)
        dashboard_row.addWidget(self.stop_dashboard_button)

        period_label = QLabel("Период:")
        self.period_combo = QComboBox()
        for period_id, label in PERIODS:
            self.period_combo.addItem(label, period_id)
        self._describe_combobox(
            self.period_combo,
            "period_combo",
            "Период отчёта",
            "Выберите период, за который нужно построить отчёт.",
        )
        self._restore_period()
        self.period_combo.currentIndexChanged.connect(self._update_period_controls_state)

        self.custom_start_date = QDateEdit()
        self.custom_start_date.setCalendarPopup(True)
        self.custom_start_date.setDisplayFormat("yyyy-MM-dd")
        self.custom_end_date = QDateEdit()
        self.custom_end_date.setCalendarPopup(True)
        self.custom_end_date.setDisplayFormat("yyyy-MM-dd")
        self._restore_custom_dates()

        period_row = QHBoxLayout()
        period_row.addWidget(period_label)
        period_row.addWidget(self.period_combo, 1)
        self.custom_start_label = QLabel("с:")
        self.custom_end_label = QLabel("по:")
        period_row.addWidget(self.custom_start_label)
        period_row.addWidget(self.custom_start_date)
        period_row.addWidget(self.custom_end_label)
        period_row.addWidget(self.custom_end_date)

        scope_label = QLabel("Область:")
        self.scope_combo = QComboBox()
        for scope, label in SCOPE_LABELS.items():
            self.scope_combo.addItem(label, scope)
        self._describe_combobox(
            self.scope_combo,
            "scope_combo",
            "Область отчёта",
            "Выберите колоды, которые попадут в отчёт.",
        )
        self._restore_scope()
        self.scope_combo.currentIndexChanged.connect(self._update_deck_list_state)

        scope_row = QHBoxLayout()
        scope_row.addWidget(scope_label)
        scope_row.addWidget(self.scope_combo, 1)

        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Название профиля")
        self.profile_name_edit.setClearButtonEnabled(True)
        self.save_profile_button = QPushButton("Сохранить профиль")
        self.save_profile_button.clicked.connect(self._save_current_profile)

        save_profile_row = QHBoxLayout()
        save_profile_row.addWidget(self.profile_name_edit, 1)
        save_profile_row.addWidget(self.save_profile_button)

        self.include_child_decks = QCheckBox("Включать дочерние колоды")
        self.include_child_decks.setChecked(
            bool(self._config.get("include_child_decks", True))
        )

        self.deck_list = QListWidget()
        self.deck_list.setMinimumHeight(180)
        self.deck_list.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._fill_deck_list()

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setMinimumHeight(220)
        self.report_text.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.report_text.setPlaceholderText("Здесь появится отчёт.")

        self.status_label = QLabel("Готов к построению отчёта.")
        self.status_label.setObjectName("report_status_label")
        self.status_label.setAccessibleName("Статус отчёта")
        self.status_label.setWordWrap(True)

        self.show_button = QPushButton("Показать отчёт")
        self.copy_markdown_button = QPushButton("Copy Markdown")
        self.open_report_dashboard_button = QPushButton("Открыть этот отчёт в dashboard")
        self.save_markdown_button = QPushButton("Сохранить .md")
        self.open_problem_decks_button = QPushButton("Открыть проблемные колоды")
        self.open_again_button = QPushButton("Открыть Again за период")
        self.open_new_button = QPushButton("Открыть новые за период")
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self._save_and_close)
        self.show_button.clicked.connect(self._show_report)
        self.copy_markdown_button.clicked.connect(self._copy_markdown)
        self.open_report_dashboard_button.clicked.connect(self._open_current_report_dashboard)
        self.save_markdown_button.clicked.connect(self._save_markdown)
        self.open_problem_decks_button.clicked.connect(self._open_problem_decks)
        self.open_again_button.clicked.connect(self._open_again_for_period)
        self.open_new_button.clicked.connect(self._open_new_for_period)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for button in (
            self.show_button,
            self.copy_markdown_button,
            self.save_markdown_button,
            self.open_problem_decks_button,
            self.open_again_button,
            self.open_new_button,
            self.open_report_dashboard_button,
            close_button,
        ):
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            buttons.addWidget(button, 1)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(profile_row)
        layout.addLayout(detail_row)
        layout.addLayout(answer_mode_row)
        layout.addLayout(dashboard_row)
        layout.addLayout(period_row)
        layout.addLayout(scope_row)
        layout.addLayout(save_profile_row)
        layout.addWidget(self.include_child_decks)
        layout.addWidget(self.deck_list, 1)
        layout.addWidget(self.report_text, 3)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self._update_period_controls_state()
        self._update_deck_list_state()
        self._update_dashboard_status()
        self.profile_combo.currentIndexChanged.connect(self._apply_selected_profile)

    def closeEvent(self, event) -> None:
        self._save_config()
        super().closeEvent(event)

    def _describe_combobox(
        self,
        combo: QComboBox,
        object_name: str,
        accessible_name: str,
        tooltip: str,
    ) -> None:
        combo.setObjectName(object_name)
        combo.setAccessibleName(accessible_name)
        combo.setToolTip(tooltip)

    def selected_scope(self) -> str:
        return str(self.scope_combo.currentData() or SCOPE_ALL)

    def selected_period(self) -> str:
        return str(self.period_combo.currentData() or "today")

    def selected_profile(self) -> str:
        return str(self.profile_combo.currentData() or MANUAL_PROFILE_ID)

    def selected_detail_level(self) -> str:
        detail_level = str(self.detail_combo.currentData() or "normal")
        if detail_level not in {"compact", "normal", "full"}:
            return "normal"
        return detail_level

    def selected_answer_mode(self) -> str:
        answer_mode = str(self.answer_mode_combo.currentData() or "auto")
        if answer_mode not in {"auto", "standard", "pass_fail"}:
            return "auto"
        return answer_mode

    def selected_custom_period(self) -> tuple[str, str]:
        return (
            self.custom_start_date.date().toString("yyyy-MM-dd"),
            self.custom_end_date.date().toString("yyyy-MM-dd"),
        )

    def _populate_profile_combo(self) -> None:
        self.profile_combo.clear()
        for profile_id, label, _settings in PROFILES:
            self.profile_combo.addItem(label, profile_id)

        for profile_id, profile in sorted(
            self._custom_profiles.items(),
            key=lambda item: str(item[1].get("label", item[0])).lower(),
        ):
            label = str(profile.get("label") or profile_id)
            self.profile_combo.addItem(label, f"{CUSTOM_PROFILE_PREFIX}{profile_id}")

    def selected_deck_ids(self) -> list[int]:
        selected: list[int] = []
        for item in self._deck_items:
            if item.checkState() == Qt.CheckState.Checked:
                deck_id = item.data(Qt.ItemDataRole.UserRole)
                selected.append(int(deck_id))
        return selected

    def report_deck_ids(self) -> list[int] | None:
        scope = self.selected_scope()
        if scope == SCOPE_ALL:
            return None
        if scope == SCOPE_CURRENT:
            current_id = _current_deck_id()
            deck_ids = [current_id] if current_id is not None else []
        else:
            deck_ids = self.selected_deck_ids()

        if self.include_child_decks.isChecked():
            return expand_deck_ids(mw.col, deck_ids) if mw and mw.col else deck_ids
        return deck_ids

    def _restore_period(self) -> None:
        period = str(self._config.get("default_period", "today"))
        index = self.period_combo.findData(period)
        if index < 0:
            index = self.period_combo.findData("today")
        self.period_combo.setCurrentIndex(index)

    def _restore_profile(self) -> None:
        profile = str(self._config.get("selected_profile", MANUAL_PROFILE_ID))
        index = self.profile_combo.findData(profile)
        if index < 0:
            index = self.profile_combo.findData(MANUAL_PROFILE_ID)
        self.profile_combo.setCurrentIndex(index)

    def _restore_detail_level(self) -> None:
        detail_level = str(self._config.get("report_detail_level", "normal"))
        index = self.detail_combo.findData(detail_level)
        if index < 0:
            index = self.detail_combo.findData("normal")
        self.detail_combo.setCurrentIndex(index)

    def _restore_answer_mode(self) -> None:
        answer_mode = str(self._config.get("answer_mode", "auto"))
        index = self.answer_mode_combo.findData(answer_mode)
        if index < 0:
            index = self.answer_mode_combo.findData("auto")
        self.answer_mode_combo.setCurrentIndex(index)

    def _restore_custom_dates(self) -> None:
        today = QDate.currentDate()
        start = _qdate_from_config(
            self._config.get("custom_start_date"),
            today.addDays(-30),
        )
        end = _qdate_from_config(self._config.get("custom_end_date"), today)
        self.custom_start_date.setDate(start)
        self.custom_end_date.setDate(end)

    def _restore_scope(self) -> None:
        scope = str(self._config.get("report_scope", SCOPE_ALL))
        index = self.scope_combo.findData(scope)
        if index < 0:
            index = self.scope_combo.findData(SCOPE_ALL)
        self.scope_combo.setCurrentIndex(index)

    def _fill_deck_list(self) -> None:
        selected_deck_ids = {
            int(deck_id)
            for deck_id in self._config.get("selected_deck_ids", [])
            if _is_int_like(deck_id)
        }

        for deck_id, deck_name in _deck_names():
            item = QListWidgetItem(deck_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.ItemDataRole.UserRole, deck_id)
            item.setCheckState(
                Qt.CheckState.Checked
                if deck_id in selected_deck_ids
                else Qt.CheckState.Unchecked
            )
            self.deck_list.addItem(item)
            self._deck_items.append(item)

    def _update_deck_list_state(self) -> None:
        selected_scope = self.selected_scope()
        enabled = selected_scope == SCOPE_SELECTED
        if not enabled:
            self._clear_deck_selection()
        self.deck_list.setEnabled(enabled)
        self.include_child_decks.setEnabled(selected_scope != SCOPE_ALL)

    def _clear_deck_selection(self) -> None:
        for item in self._deck_items:
            item.setCheckState(Qt.CheckState.Unchecked)

    def _set_selected_deck_ids(self, deck_ids: list[int]) -> None:
        selected = set(deck_ids)
        for item in self._deck_items:
            deck_id = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(
                Qt.CheckState.Checked
                if int(deck_id) in selected
                else Qt.CheckState.Unchecked
            )

    def _apply_selected_profile(self) -> None:
        profile_id = self.selected_profile()
        settings = PROFILE_SETTINGS.get(profile_id)
        if profile_id.startswith(CUSTOM_PROFILE_PREFIX):
            custom_profile_id = profile_id[len(CUSTOM_PROFILE_PREFIX) :]
            profile = self._custom_profiles.get(custom_profile_id, {})
            settings = profile.get("settings") if isinstance(profile, dict) else None
        if not settings:
            return

        self._apply_profile_settings(settings)

    def _apply_profile_settings(self, settings: dict) -> None:
        period = str(settings.get("period", "today"))
        period_index = self.period_combo.findData(period)
        if period_index >= 0:
            self.period_combo.setCurrentIndex(period_index)

        start_date = settings.get("custom_start_date")
        end_date = settings.get("custom_end_date")
        if start_date is not None:
            self.custom_start_date.setDate(
                _qdate_from_config(start_date, self.custom_start_date.date())
            )
        if end_date is not None:
            self.custom_end_date.setDate(
                _qdate_from_config(end_date, self.custom_end_date.date())
            )

        scope = str(settings.get("scope", SCOPE_ALL))
        scope_index = self.scope_combo.findData(scope)
        if scope_index >= 0:
            self.scope_combo.setCurrentIndex(scope_index)

        self.include_child_decks.setChecked(
            bool(settings.get("include_child_decks", True))
        )

        deck_ids = [
            int(deck_id)
            for deck_id in settings.get("selected_deck_ids", [])
            if _is_int_like(deck_id)
        ]
        keywords = settings.get("deck_name_keywords", [])
        if keywords:
            deck_ids = _deck_ids_matching_keywords(keywords)
        self._set_selected_deck_ids(deck_ids)

        self._enabled_metrics = _enabled_metrics_from_config(
            {"enabled_metrics": settings.get("enabled_metrics", DEFAULT_ENABLED_METRICS)}
        )
        detail_level = str(settings.get("detail_level", settings.get("report_detail_level", "")))
        detail_index = self.detail_combo.findData(detail_level)
        if detail_index >= 0:
            self.detail_combo.setCurrentIndex(detail_index)

        answer_mode = str(settings.get("answer_mode", ""))
        answer_mode_index = self.answer_mode_combo.findData(answer_mode)
        if answer_mode_index >= 0:
            self.answer_mode_combo.setCurrentIndex(answer_mode_index)

        self._update_period_controls_state()
        self._update_deck_list_state()

    def _current_profile_settings(self) -> dict:
        custom_start_date, custom_end_date = self.selected_custom_period()
        return {
            "period": self.selected_period(),
            "custom_start_date": custom_start_date,
            "custom_end_date": custom_end_date,
            "scope": self.selected_scope(),
            "selected_deck_ids": self.selected_deck_ids(),
            "include_child_decks": self.include_child_decks.isChecked(),
            "enabled_metrics": dict(self._enabled_metrics),
            "detail_level": self.selected_detail_level(),
            "answer_mode": self.selected_answer_mode(),
        }

    def _save_current_profile(self) -> None:
        profile_name = self.profile_name_edit.text().strip()
        if not profile_name:
            self.status_label.setText("Введите название профиля перед сохранением.")
            self.profile_name_edit.setFocus()
            return

        config = _read_config()
        custom_profiles = config.get("custom_profiles")
        if not isinstance(custom_profiles, dict):
            custom_profiles = {}

        custom_profiles[profile_name] = {
            "label": profile_name,
            "settings": self._current_profile_settings(),
        }
        config["custom_profiles"] = custom_profiles
        config["selected_profile"] = f"{CUSTOM_PROFILE_PREFIX}{profile_name}"
        config["report_detail_level"] = self.selected_detail_level()
        config["answer_mode"] = self.selected_answer_mode()
        config["default_period"] = self.selected_period()
        custom_start_date, custom_end_date = self.selected_custom_period()
        config["custom_start_date"] = custom_start_date
        config["custom_end_date"] = custom_end_date
        config["report_scope"] = self.selected_scope()
        config["selected_deck_ids"] = self.selected_deck_ids()
        config["include_child_decks"] = self.include_child_decks.isChecked()
        config["enabled_metrics"] = dict(self._enabled_metrics)
        _write_config(config)

        self._config = config
        self._custom_profiles = _custom_profiles_from_config(config)
        previous_block = self.profile_combo.blockSignals(True)
        self._populate_profile_combo()
        index = self.profile_combo.findData(config["selected_profile"])
        self.profile_combo.setCurrentIndex(
            index if index >= 0 else self.profile_combo.findData(MANUAL_PROFILE_ID)
        )
        self.profile_combo.blockSignals(previous_block)
        self.status_label.setText(f"Профиль «{profile_name}» сохранён.")

    def _update_period_controls_state(self) -> None:
        enabled = self.selected_period() == "custom"
        self.custom_start_label.setVisible(enabled)
        self.custom_start_date.setVisible(enabled)
        self.custom_end_label.setVisible(enabled)
        self.custom_end_date.setVisible(enabled)

    def _save_and_close(self) -> None:
        self._save_config()
        self.close()

    def _open_dashboard_from_report(self) -> None:
        _open_web_dashboard()
        self._update_dashboard_status()

    def _stop_dashboard_from_report(self) -> None:
        _stop_web_dashboard_server()
        self._update_dashboard_status()

    def _update_dashboard_status(self) -> None:
        state = _DASHBOARD_SERVER.state()
        if state.running:
            text = state.url or "запущен"
            if state.port_collision:
                text = f"{text} · порт {state.requested_port} занят, используется {state.port}"
            self.dashboard_status_label.setText(text)
            self.stop_dashboard_button.setEnabled(True)
        else:
            self.dashboard_status_label.setText("остановлен")
            self.stop_dashboard_button.setEnabled(False)

    def _save_config(self) -> None:
        config = _read_config()
        config["selected_profile"] = self.selected_profile()
        config["report_detail_level"] = self.selected_detail_level()
        config["answer_mode"] = self.selected_answer_mode()
        config["default_period"] = self.selected_period()
        custom_start_date, custom_end_date = self.selected_custom_period()
        config["custom_start_date"] = custom_start_date
        config["custom_end_date"] = custom_end_date
        config["report_scope"] = self.selected_scope()
        config["selected_deck_ids"] = self.selected_deck_ids()
        config["include_child_decks"] = self.include_child_decks.isChecked()
        config["enabled_metrics"] = dict(self._enabled_metrics)
        _write_config(config)
        self._config = config

    def _show_report(self) -> None:
        def on_success(metrics: dict) -> None:
            metadata = self._report_metadata()
            self.report_text.setHtml(render_html_report(metrics, metadata))
            self._latest_report_markdown = build_markdown_report(metrics, metadata)
            self._latest_report_cache_key = self._current_metrics_cache_key()
            self.status_label.setText(
                f"Отчёт готов · {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

        self._run_metrics(on_success, "Не удалось построить отчёт.")

    def _copy_markdown(self) -> None:
        if not self._latest_report_markdown:
            self.status_label.setText("Сначала постройте отчёт, затем скопируйте Markdown.")
            return

        current_cache_key = self._current_metrics_cache_key()
        if current_cache_key != self._latest_report_cache_key:
            self.status_label.setText(
                "Настройки отчёта изменились. Постройте отчёт заново перед копированием."
            )
            return

        try:
            clipboard = QApplication.clipboard()
            if clipboard is None:
                raise RuntimeError("Буфер обмена недоступен.")
            clipboard.setText(self._latest_report_markdown)
            self.status_label.setText("Markdown отчёта скопирован в буфер обмена.")
        except Exception as error:
            traceback.print_exc()
            self.status_label.setText(f"Не удалось скопировать Markdown: {error}")

    def _open_current_report_dashboard(self) -> None:
        def on_success(metrics: dict) -> None:
            metadata = self._report_metadata()
            markdown = build_markdown_report(metrics, metadata)
            report = _dashboard_report_payload(metrics, metadata)
            state = _ensure_web_dashboard_server()
            _DASHBOARD_SERVER.publish_report(report)
            self._latest_report_markdown = markdown
            self._latest_report_cache_key = self._current_metrics_cache_key()
            _publish_dashboard_action_context(markdown, metadata, self.report_deck_ids())
            if state.url:
                QDesktopServices.openUrl(QUrl(state.url))
            self._remember_last_report()
            self._update_dashboard_status()

        self._run_metrics(on_success, "Не удалось открыть отчёт в dashboard.")

    def _save_markdown(self) -> None:
        try:
            self._save_config()
            filename, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Сохранить Markdown-отчёт",
                _default_markdown_filename(),
                "Markdown (*.md);;Text files (*.txt);;All files (*)",
            )
            if not filename:
                return
        except Exception:
            traceback.print_exc()
            showCritical(
                "Не удалось сохранить Markdown-отчёт.",
                title=ADDON_NAME,
                parent=self,
            )
            return

        def on_success(metrics: dict) -> None:
            try:
                markdown = build_markdown_report(metrics, self._report_metadata())
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(markdown)
                    file.write("\n")
                self._remember_last_report()
                showInfo("Markdown-отчёт сохранён.", title=ADDON_NAME, parent=self)
            except Exception:
                traceback.print_exc()
                showCritical(
                    "Не удалось сохранить Markdown-отчёт.",
                    title=ADDON_NAME,
                    parent=self,
                )

        self._run_metrics(on_success, "Не удалось сохранить Markdown-отчёт.")

    def _open_problem_decks(self) -> None:
        self._open_browser_action(
            "problem_decks",
            "Проблемных колод за выбранный период не найдено.",
        )

    def _open_again_for_period(self) -> None:
        self._open_browser_action(
            "again",
            "Again за выбранный период не найдено.",
        )

    def _open_new_for_period(self) -> None:
        self._open_browser_action(
            "new",
            "Новых карточек за выбранный период не найдено.",
        )

    def _open_browser_action(self, action: str, empty_message: str) -> None:
        try:
            self._save_config()
            if mw is None or mw.col is None:
                raise RuntimeError("Коллекция Anki недоступна.")

            start_ts, end_ts = self._selected_period_bounds()
            deck_ids = self.report_deck_ids()
        except Exception:
            traceback.print_exc()
            showCritical(
                "Не удалось открыть Browser Anki.\n\n"
                "Подробности напечатаны в консоль Anki.",
                title=ADDON_NAME,
                parent=self,
            )
            return

        self._set_report_buttons_enabled(False)
        self.report_text.setPlainText("Собираю карточки для Browser...")

        def finish(future) -> None:
            self._set_report_buttons_enabled(True)
            try:
                result = future.result()
            except Exception:
                self._show_browser_action_error(traceback.format_exc())
                return

            if not result.get("ok"):
                self._show_browser_action_error(str(result.get("error") or "Неизвестная ошибка."))
                return

            card_ids = result.get("card_ids")
            card_ids = card_ids if isinstance(card_ids, list) else []
            if not card_ids:
                showInfo(empty_message, title=ADDON_NAME, parent=self)
                return

            if result.get("truncated"):
                self.status_label.setText(
                    "Найден большой набор карточек. "
                    f"Открываю первые {BROWSER_ACTION_CARD_LIMIT}, чтобы Browser не завис."
                )
                log_event(
                    "browser.open_truncated",
                    "Large browser action result truncated",
                    action=action,
                    limit=BROWSER_ACTION_CARD_LIMIT,
                )

            try:
                open_browser_search(card_ids_search_query(card_ids))
            except Exception:
                self._show_browser_action_error(traceback.format_exc())

        try:
            mw.taskman.run_in_background(
                lambda: collect_browser_action_card_ids(
                    mw.col,
                    start_ts,
                    end_ts,
                    deck_ids,
                    action,
                    BROWSER_ACTION_CARD_LIMIT,
                ),
                finish,
            )
        except Exception:
            self._set_report_buttons_enabled(True)
            self._show_browser_action_error(traceback.format_exc())

    def _show_browser_action_error(self, details: str | None = None) -> None:
        if details:
            print(details)
        else:
            traceback.print_exc()
        showCritical(
            "Не удалось открыть Browser Anki.\n\n"
            "Подробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=self,
        )

    def _run_metrics(
        self,
        on_success: Callable[[dict], None],
        error_message: str,
    ) -> None:
        try:
            self._save_config()
            request = self._metrics_request()
            cached_metrics = _cached_metrics(request["cache_key"])
            if cached_metrics is not None:
                on_success(cached_metrics)
                return

            if _is_large_period(request["start_ts"], request["end_ts"]):
                self.status_label.setText("All-time report requested. This may take a moment.")
                log_event(
                    "report.large_period",
                    "Large report period requested",
                    period=self.selected_period(),
                )
        except Exception:
            self._show_report_error(error_message)
            return

        self._set_report_buttons_enabled(False)
        self.report_text.setPlainText("Расчёт...")

        def finish_success(metrics: dict) -> None:
            _store_cached_metrics(request["cache_key"], metrics)
            self._set_report_buttons_enabled(True)
            on_success(metrics)

        def finish_failure(message: str) -> None:
            self._set_report_buttons_enabled(True)
            self._show_report_error(error_message, message)

        try:
            mw.taskman.run_in_background(
                lambda: _safe_collect_metrics(
                    mw.col,
                    request["start_ts"],
                    request["end_ts"],
                    request["deck_ids"],
                    request["answer_mode"],
                    request["use_study_time_stats"],
                    request["track_reviewer_sessions"],
                ),
                lambda future: self._handle_metrics_future(
                    future,
                    finish_success,
                    finish_failure,
                ),
            )
        except Exception:
            self._set_report_buttons_enabled(True)
            self._show_report_error(error_message)

    def _metrics_request(self) -> dict:
        if mw is None or mw.col is None:
            raise RuntimeError("Коллекция Anki недоступна.")

        start_ts, end_ts = self._selected_period_bounds()
        deck_ids = self.report_deck_ids()
        cache_key = _report_cache_key(self._selected_period_cache_key(), deck_ids)
        answer_mode = self.selected_answer_mode()
        use_study_time_stats = bool(self._config.get("use_study_time_stats", False))
        track_reviewer_sessions = bool(self._config.get("track_reviewer_sessions", False))
        use_stats_cache_for_report = bool(
            self._config.get("use_stats_cache_for_report", False)
        )
        return {
            "start_ts": start_ts,
            "end_ts": end_ts,
            "deck_ids": deck_ids,
            "answer_mode": answer_mode,
            "cache_key": report_metrics_cache_key(
                cache_key,
                answer_mode,
                use_study_time_stats,
                track_reviewer_sessions,
                use_stats_cache_for_report,
                _STATS_CACHE.status(),
            ),
            "use_study_time_stats": use_study_time_stats,
            "track_reviewer_sessions": track_reviewer_sessions,
        }

    def _current_metrics_cache_key(self) -> object | None:
        try:
            request = self._metrics_request()
            return (
                request["cache_key"],
                self.selected_detail_level(),
                self.selected_scope(),
                tuple(self.selected_deck_ids()),
                self.include_child_decks.isChecked(),
                self.selected_custom_period() if self.selected_period() == "custom" else None,
            )
        except Exception:
            return None

    def _handle_metrics_future(
        self,
        future,
        finish_success: Callable[[dict], None],
        finish_failure: Callable[[str], None],
    ) -> None:
        try:
            result = future.result()
        except Exception:
            finish_failure(traceback.format_exc())
            return

        self._handle_metrics_result(result, finish_success, finish_failure)

    def _handle_metrics_result(
        self,
        result: dict,
        finish_success: Callable[[dict], None],
        finish_failure: Callable[[str], None],
    ) -> None:
        if result.get("ok"):
            metrics = result.get("metrics")
            if isinstance(metrics, dict):
                finish_success(metrics)
                return
        finish_failure(str(result.get("error") or "Неизвестная ошибка."))

    def _set_report_buttons_enabled(self, enabled: bool) -> None:
        self.show_button.setEnabled(enabled)
        self.copy_markdown_button.setEnabled(enabled)
        self.open_report_dashboard_button.setEnabled(enabled)
        self.save_markdown_button.setEnabled(enabled)
        self.open_problem_decks_button.setEnabled(enabled)
        self.open_again_button.setEnabled(enabled)
        self.open_new_button.setEnabled(enabled)

    def _show_report_error(self, message: str, details: str | None = None) -> None:
        if details:
            print(details)
        else:
            traceback.print_exc()
        showCritical(
            f"{message}\n\nПодробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=self,
        )

    def _selected_period_bounds(self) -> tuple[int, int]:
        if self.selected_period() == "since_last_report":
            last_report_ts = _last_report_ts(_read_config())
            if last_report_ts is None:
                showInfo(
                    "Предыдущий отчёт ещё не запомнен. "
                    "Пока использую период “Сегодня”.",
                    title=ADDON_NAME,
                    parent=self,
                )
                return _period_bounds("today")
            return last_report_ts, int(datetime.now().timestamp())

        if self.selected_period() != "custom":
            return _period_bounds(self.selected_period())

        start_date = self.custom_start_date.date().toPyDate()
        end_date = self.custom_end_date.date().toPyDate()
        if end_date < start_date:
            raise ValueError("Дата окончания периода не может быть раньше даты начала.")

        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        return int(start.timestamp()), int(end.timestamp())

    def _selected_period_cache_key(self) -> tuple[str, str, str] | str:
        if self.selected_period() == "since_last_report":
            last_report_ts = _last_report_ts(_read_config())
            return "since_last_report", str(last_report_ts or "today_fallback")

        if self.selected_period() != "custom":
            return self.selected_period()

        start_date, end_date = self.selected_custom_period()
        return "custom", start_date, end_date

    def _remember_last_report(self) -> None:
        config = _read_config()
        config["last_report_ts"] = int(datetime.now().timestamp())
        _write_config(config)
        self._config = config

    def _report_metadata(self) -> dict:
        period_context = self._period_context_for_report()
        return {
            "period": self._period_label_for_report(),
            "period_id": self.selected_period(),
            "period_human": self._period_human_label(),
            "scope": self._scope_label_for_report(),
            "selected_decks": self._selected_deck_names_for_report(),
            "include_child_decks": self.include_child_decks.isChecked(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "detail_level": self.selected_detail_level(),
            "requested_answer_mode": self.selected_answer_mode(),
            **period_context,
        }

    def _period_context_for_report(self) -> dict:
        try:
            start_ts, end_ts = self._selected_period_bounds_quiet()
        except Exception:
            return {}
        return {
            "period_start_ts": start_ts,
            "period_end_ts": end_ts,
            "period_start_date": _date_key_from_timestamp(start_ts),
            "period_end_date": _date_key_from_timestamp(max(start_ts, end_ts - 1)),
            "today_date": _current_anki_today_date_key(),
        }

    def _selected_period_bounds_quiet(self) -> tuple[int, int]:
        period = self.selected_period()
        if period == "since_last_report":
            last_report_ts = _last_report_ts(_read_config())
            if last_report_ts is None:
                return _period_bounds("today")
            return last_report_ts, int(datetime.now().timestamp())
        if period != "custom":
            return _period_bounds(period)

        start_date = self.custom_start_date.date().toPyDate()
        end_date = self.custom_end_date.date().toPyDate()
        if end_date < start_date:
            raise ValueError("Дата окончания периода не может быть раньше даты начала.")
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        return int(start.timestamp()), int(end.timestamp())

    def _period_label_for_report(self) -> str:
        if self.selected_period() == "custom":
            start_date, end_date = self.selected_custom_period()
            return f"{start_date} — {end_date}"
        return self.period_combo.currentText()

    def _period_human_label(self) -> str:
        period = self.selected_period()
        if period == "today":
            return "сегодня"
        if period == "yesterday":
            return "вчера"
        if period == "last_7_days":
            return "за последние 7 дней"
        if period == "last_30_days":
            return "за последние 30 дней"
        if period == "custom":
            start_date, end_date = self.selected_custom_period()
            return f"за период {start_date} — {end_date}"
        if period == "all_time":
            return "за всё время"
        if period == "since_last_report":
            return "с последнего отчёта"
        return "за выбранный период"

    def _scope_label_for_report(self) -> str:
        scope = self.selected_scope()
        if scope == SCOPE_SELECTED:
            count = len(self.selected_deck_ids())
            return f"{self.scope_combo.currentText()} ({count})"
        return self.scope_combo.currentText()

    def _selected_deck_names_for_report(self) -> str:
        scope = self.selected_scope()
        if scope == SCOPE_ALL:
            return "Все колоды"

        deck_name_by_id = dict(_deck_names())
        if scope == SCOPE_CURRENT:
            current_id = _current_deck_id()
            if current_id is None:
                return "Текущая колода не определена"
            return deck_name_by_id.get(current_id, f"Колода {current_id}")

        selected_ids = self.selected_deck_ids()
        if not selected_ids:
            return "Выбранные колоды не указаны"

        names = [
            deck_name_by_id.get(deck_id, f"Колода {deck_id}")
            for deck_id in selected_ids
        ]
        if len(names) <= 5:
            return ", ".join(names)
        visible_names = ", ".join(names[:5])
        return f"{visible_names} и ещё {len(names) - 5}"


class IntegrationDiagnosticsDialog(QDialog):
    """Small diagnostics window for optional add-on integrations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{ADDON_NAME}: интеграции")
        self.setMinimumSize(820, 560)

        title = QLabel("Проверка интеграций")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        intro = QLabel(
            "Здесь отдельно показаны внешние источники времени, внутренний трекер "
            "повторений, heatmap и технические логи."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #666;")

        self.tabs = QTabWidget()
        self._diagnostic_views: dict[str, QTextEdit] = {}
        for tab_key, tab_label in (
            ("study_time_stats", "Study Time Stats"),
            ("session_tracker", "Трекер повторений"),
            ("heatmap", "Heatmap"),
            ("logs", "Логи"),
        ):
            view = QTextEdit()
            view.setReadOnly(True)
            view.setMinimumHeight(360)
            view.setPlaceholderText("Здесь появится диагностика.")
            self._diagnostic_views[tab_key] = view
            self.tabs.addTab(view, tab_label)

        refresh_button = QPushButton("Обновить")
        copy_button = QPushButton("Скопировать лог")
        close_button = QPushButton("Закрыть")
        refresh_button.clicked.connect(self.refresh)
        copy_button.clicked.connect(self.copy_log)
        close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addWidget(copy_button)
        buttons.addWidget(close_button)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        try:
            diagnostics = _integration_diagnostics_sections()
            for tab_key, text in diagnostics.items():
                view = self._diagnostic_views.get(tab_key)
                if view is not None:
                    view.setPlainText(text)
        except Exception:
            traceback.print_exc()
            message = (
                "Не удалось собрать диагностику интеграций.\n\n"
                "Подробности напечатаны в консоль Anki."
            )
            for view in self._diagnostic_views.values():
                view.setPlainText(message)

    def copy_log(self) -> None:
        parts = []
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            if isinstance(view, QTextEdit):
                parts.append(f"{self.tabs.tabText(index)}\n{view.toPlainText()}")
        QApplication.clipboard().setText("\n\n".join(parts))
        showInfo("Лог интеграций скопирован в буфер обмена.", title=ADDON_NAME, parent=self)


class WebDashboardSettingsDialog(QDialog):
    """Start/stop the local companion dashboard without using a console."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{ADDON_NAME}: web dashboard")
        self.setMinimumSize(560, 360)

        config = _web_dashboard_config()

        title = QLabel("Web dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.auto_start_checkbox = QCheckBox("Запускать сервер автоматически при старте Anki")
        self.auto_start_checkbox.setChecked(bool(config.get("auto_start", False)))

        port_label = QLabel("Порт:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(0, 65535)
        self.port_spin.setSpecialValueText("Авто")
        self.port_spin.setValue(int(config.get("port", DEFAULT_PORT) or DEFAULT_PORT))

        idle_label = QLabel("Авто-отключение после простоя:")
        self.idle_timeout_spin = QSpinBox()
        self.idle_timeout_spin.setRange(0, 24 * 60 * 60)
        self.idle_timeout_spin.setSingleStep(60)
        self.idle_timeout_spin.setSuffix(" сек")
        self.idle_timeout_spin.setSpecialValueText("Не отключать")
        self.idle_timeout_spin.setValue(
            int(config.get("idle_timeout_seconds", DEFAULT_IDLE_TIMEOUT_SECONDS) or 0)
        )

        port_row = QHBoxLayout()
        port_row.addWidget(port_label)
        port_row.addWidget(self.port_spin, 1)

        idle_row = QHBoxLayout()
        idle_row.addWidget(idle_label)
        idle_row.addWidget(self.idle_timeout_spin, 1)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(130)

        start_button = QPushButton("Запустить")
        stop_button = QPushButton("Остановить")
        open_button = QPushButton("Открыть dashboard")
        save_button = QPushButton("Сохранить")
        close_button = QPushButton("Закрыть")

        start_button.clicked.connect(self.start_server)
        stop_button.clicked.connect(self.stop_server)
        open_button.clicked.connect(self.open_dashboard)
        save_button.clicked.connect(self.save_settings)
        close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        for button in (start_button, stop_button, open_button, save_button, close_button):
            buttons.addWidget(button)

        help_label = QLabel(
            "Сервер слушает только 127.0.0.1. Пользователю не нужна консоль: "
            "Anki сам запускает, открывает и останавливает локальную страницу."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666;")

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(help_label)
        layout.addWidget(self.auto_start_checkbox)
        layout.addLayout(port_row)
        layout.addLayout(idle_row)
        layout.addWidget(QLabel("Статус:"))
        layout.addWidget(self.status_text, 1)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.refresh_status()

    def closeEvent(self, event) -> None:
        self.save_settings(show_message=False)
        super().closeEvent(event)

    def start_server(self) -> None:
        self.save_settings(show_message=False)
        try:
            state = _start_web_dashboard_server()
        except Exception:
            traceback.print_exc()
            showCritical(
                "Не удалось запустить web dashboard.\n\n"
                "Подробности напечатаны в консоль Anki.",
                title=ADDON_NAME,
                parent=self,
            )
            return
        self.refresh_status()
        if state.url:
            message = f"Web dashboard запущен:\n{state.url}"
            if state.port_collision:
                message += (
                    f"\n\nПорт {state.requested_port} занят, поэтому используется "
                    f"фактический порт {state.port}."
                )
            showInfo(message, title=ADDON_NAME, parent=self)

    def stop_server(self) -> None:
        _stop_web_dashboard_server()
        self.refresh_status()

    def open_dashboard(self) -> None:
        try:
            state = _ensure_web_dashboard_server()
        except Exception:
            traceback.print_exc()
            showCritical(
                "Не удалось открыть web dashboard.\n\n"
                "Подробности напечатаны в консоль Anki.",
                title=ADDON_NAME,
                parent=self,
            )
            return

        if state.url:
            QDesktopServices.openUrl(QUrl(state.url))
        self.refresh_status()

    def save_settings(self, show_message: bool = True) -> None:
        port = int(self.port_spin.value())
        if port == 8765:
            port = DEFAULT_PORT
            self.port_spin.setValue(port)
        config = _read_config()
        config["web_dashboard"] = {
            "auto_start": self.auto_start_checkbox.isChecked(),
            "port": port,
            "idle_timeout_seconds": int(self.idle_timeout_spin.value()),
        }
        _write_config(config)
        if show_message:
            showInfo("Настройки web dashboard сохранены.", title=ADDON_NAME, parent=self)
        self.refresh_status()

    def refresh_status(self) -> None:
        self.status_text.setPlainText(_web_dashboard_status_text())


class LauncherDialog(QDialog):
    """Compact entrypoint for the local dashboard."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anki Study Report Launcher")
        self.setMinimumSize(460, 260)

        title = QLabel("Anki Study Report")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        subtitle = QLabel("Local dashboard launcher")
        subtitle.setStyleSheet("color: #666;")

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.url_label = QLabel()
        self.url_label.setWordWrap(True)
        self.report_label = QLabel()
        self.report_label.setWordWrap(True)
        self.cache_label = QLabel()
        self.cache_label.setWordWrap(True)

        self.open_dashboard_button = QPushButton("Open Dashboard")
        copy_url_button = QPushButton("Copy Dashboard URL")
        close_button = QPushButton("Close")

        self.open_dashboard_button.clicked.connect(self._open_dashboard)
        copy_url_button.clicked.connect(self._copy_dashboard_url)
        close_button.clicked.connect(self.close)

        button_rows = [
            (self.open_dashboard_button, copy_url_button),
            (close_button, None),
        ]

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Server status:"))
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("Dashboard URL:"))
        layout.addWidget(self.url_label)
        layout.addWidget(QLabel("Report/cache:"))
        layout.addWidget(self.report_label)
        layout.addWidget(self.cache_label)
        layout.addSpacing(8)
        for left, right in button_rows:
            row = QHBoxLayout()
            row.addWidget(left)
            if right is not None:
                row.addWidget(right)
            layout.addLayout(row)
        self.setLayout(layout)
        self.refresh_status()
        log_event("launcher.opened", "Launcher opened")

    def _open_dashboard(self) -> None:
        try:
            _ensure_web_dashboard_server()
        except Exception:
            log_exception("launcher.open_dashboard", "Could not start dashboard server")
            showCritical(
                "Не удалось открыть web dashboard.\n\n"
                "Подробности записаны в лог расширения.",
                title=ADDON_NAME,
                parent=self,
            )
            self.refresh_status()
            return

        self._set_busy(True, "Preparing all-time report from cache...")

        def finish(future) -> None:
            self._set_busy(False)
            try:
                result = future.result()
                report = result.get("report")
                if isinstance(report, dict):
                    _DASHBOARD_SERVER.publish_report(report)
                markdown = result.get("markdown")
                metadata = result.get("metadata")
                _publish_dashboard_action_context(
                    markdown if isinstance(markdown, str) else "",
                    metadata if isinstance(metadata, dict) else {},
                    None,
                )
                url = str(result.get("url") or _dashboard_url_for_route("/home", start=False))
                QDesktopServices.openUrl(QUrl(url))
                self.status_label.setText(str(result.get("message") or "Dashboard ready."))
                log_event("launcher.open_dashboard", "Dashboard opened with all-time report")
            except Exception:
                log_exception("launcher.open_dashboard", "Could not prepare default dashboard report")
                showCritical(
                    "Не удалось подготовить отчёт для dashboard.\n\n"
                    "Подробности записаны в лог расширения.",
                    title=ADDON_NAME,
                    parent=self,
                )
            self.refresh_status()

        try:
            mw.taskman.run_in_background(_prepare_default_dashboard_report, finish)
        except Exception:
            self._set_busy(False)
            log_exception("launcher.open_dashboard", "Could not schedule dashboard report preparation")
            showCritical(
                "Не удалось запланировать подготовку отчёта.\n\n"
                "Подробности записаны в лог расширения.",
                title=ADDON_NAME,
                parent=self,
            )
            self.refresh_status()

    def _copy_dashboard_url(self) -> None:
        try:
            url = _dashboard_url_for_route("/home")
            QApplication.clipboard().setText(url)
            self.status_label.setText("Dashboard URL copied.")
            log_event("launcher.copy_url", "Dashboard URL copied")
        except Exception:
            log_exception("launcher.copy_url", "Could not copy dashboard URL")
            self.status_label.setText("Could not copy dashboard URL.")
        self.refresh_status()

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self.open_dashboard_button.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    def refresh_status(self) -> None:
        state = _DASHBOARD_SERVER.state()
        status = "running" if state.running else "stopped"
        if state.message:
            status = f"{status} · {state.message}"
        self.status_label.setText(
            f"{status}\nhost: {state.host}\nport: {state.port if state.running else state.requested_port}"
        )
        self.url_label.setText(_masked_dashboard_url(_dashboard_url_for_route("/home", start=False)))
        self.report_label.setText(
            "current report: available" if state.report_available else "current report: not published"
        )
        try:
            cache = _cache_status_response()
            self.cache_label.setText(
                "cache: "
                f"{cache.get('status', 'unknown')} · "
                f"use_stats_cache_for_report={cache.get('useStatsCacheForReport')}"
            )
        except Exception:
            self.cache_label.setText("cache: unavailable")


def _open_study_report_dialog() -> None:
    """Open the report dialog without allowing UI errors to crash Anki."""

    global _STUDY_REPORT_DIALOG
    try:
        if _STUDY_REPORT_DIALOG is not None:
            _STUDY_REPORT_DIALOG.raise_()
            _STUDY_REPORT_DIALOG.activateWindow()
            return

        dialog = StudyReportDialog(mw)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.finished.connect(_clear_study_report_dialog)
        _STUDY_REPORT_DIALOG = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        traceback.print_exc()
        showCritical(
            "Не удалось открыть окно Study Report.\n\n"
            "Подробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=mw,
        )


def _open_integrations_dialog() -> None:
    """Open optional integration diagnostics without affecting the report window."""

    global _INTEGRATIONS_DIALOG
    try:
        if _INTEGRATIONS_DIALOG is not None:
            _INTEGRATIONS_DIALOG.raise_()
            _INTEGRATIONS_DIALOG.activateWindow()
            return

        dialog = IntegrationDiagnosticsDialog(mw)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.finished.connect(_clear_integrations_dialog)
        _INTEGRATIONS_DIALOG = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        traceback.print_exc()
        showCritical(
            "Не удалось открыть окно интеграций Study Report.\n\n"
            "Подробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=mw,
        )


def _open_web_dashboard_settings_dialog() -> None:
    """Open web dashboard server controls."""

    global _WEB_DASHBOARD_DIALOG
    try:
        if _WEB_DASHBOARD_DIALOG is not None:
            _WEB_DASHBOARD_DIALOG.raise_()
            _WEB_DASHBOARD_DIALOG.activateWindow()
            return

        dialog = WebDashboardSettingsDialog(mw)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.finished.connect(_clear_web_dashboard_dialog)
        _WEB_DASHBOARD_DIALOG = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        traceback.print_exc()
        showCritical(
            "Не удалось открыть настройки web dashboard.\n\n"
            "Подробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=mw,
        )


def _open_web_dashboard() -> None:
    """Start the local dashboard if needed and open it in the default browser."""

    try:
        state = _ensure_web_dashboard_server()
        if state.url:
            QDesktopServices.openUrl(QUrl(state.url))
    except Exception:
        traceback.print_exc()
        showCritical(
            "Не удалось открыть web dashboard.\n\n"
            "Подробности напечатаны в консоль Anki.",
            title=ADDON_NAME,
            parent=mw,
        )


def _open_launcher_dialog() -> None:
    """Open the compact dashboard launcher."""

    global _LAUNCHER_DIALOG
    try:
        if _LAUNCHER_DIALOG is not None:
            _LAUNCHER_DIALOG.refresh_status()
            _LAUNCHER_DIALOG.raise_()
            _LAUNCHER_DIALOG.activateWindow()
            return

        dialog = LauncherDialog(mw)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.finished.connect(_clear_launcher_dialog)
        _LAUNCHER_DIALOG = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        log_exception("launcher.error", "Could not open launcher")
        showCritical(
            "Не удалось открыть launcher Anki Study Report.\n\n"
            "Подробности записаны в лог расширения.",
            title=ADDON_NAME,
            parent=mw,
        )


def _clear_study_report_dialog(_result: int = 0) -> None:
    global _STUDY_REPORT_DIALOG
    _STUDY_REPORT_DIALOG = None


def _clear_integrations_dialog(_result: int = 0) -> None:
    global _INTEGRATIONS_DIALOG
    _INTEGRATIONS_DIALOG = None


def _clear_web_dashboard_dialog(_result: int = 0) -> None:
    global _WEB_DASHBOARD_DIALOG
    _WEB_DASHBOARD_DIALOG = None


def _clear_launcher_dialog(_result: int = 0) -> None:
    global _LAUNCHER_DIALOG
    _LAUNCHER_DIALOG = None


def _dashboard_url_for_route(route: str = "/home", start: bool = True) -> str:
    route = "/" + str(route or "/home").lstrip("/")
    state = _ensure_web_dashboard_server() if start else _DASHBOARD_SERVER.state()
    if state.url:
        return f"{state.url}#{route}"
    return f"http://{state.host}:{state.requested_port}/?token=<hidden>#{route}"


def _masked_dashboard_url(url: str | None) -> str:
    if not url:
        return "server stopped"
    if "token=" not in url:
        return url
    prefix, rest = url.split("token=", 1)
    suffix = ""
    for delimiter in ("#", "&"):
        if delimiter in rest:
            suffix = rest[rest.index(delimiter) :]
            break
    return f"{prefix}token=<hidden>{suffix}"


def _start_web_dashboard_server():
    settings = _web_dashboard_config()
    _configure_dashboard_cache_handlers()
    state = _DASHBOARD_SERVER.start(
        port=int(settings["port"]),
        idle_timeout_seconds=int(settings["idle_timeout_seconds"]),
    )
    if _STUDY_REPORT_DIALOG is not None:
        _STUDY_REPORT_DIALOG._update_dashboard_status()
    if _LAUNCHER_DIALOG is not None:
        _LAUNCHER_DIALOG.refresh_status()
    return state


def _ensure_web_dashboard_server():
    _configure_dashboard_cache_handlers()
    state = _DASHBOARD_SERVER.state()
    if state.running:
        return state
    return _start_web_dashboard_server()


def _configure_dashboard_cache_handlers() -> None:
    _DASHBOARD_SERVER.configure_cache_handlers(
        status_provider=_cache_status_response,
        rebuild_handler=_request_cache_rebuild,
        refresh_handler=_request_cache_refresh,
    )
    actions = _dashboard_actions()
    _DASHBOARD_SERVER.configure_action_handler(actions.request_dashboard_action)
    _DASHBOARD_SERVER.configure_server_handlers(
        action_handler=actions.request_server_action,
        status_provider=_server_status_response,
    )
    _DASHBOARD_SERVER.configure_health_handler(_dashboard_health_response)
    _DASHBOARD_SERVER.configure_display_settings_handlers(
        settings_provider=_dashboard_display_settings_response,
        settings_handler=_update_dashboard_display_settings,
    )
    _DASHBOARD_SERVER.configure_profile_handlers(
        profile_provider=_profile_response,
        profile_handler=_update_profile,
    )
    _DASHBOARD_SERVER.configure_product_notice_handlers(
        notices_provider=_product_notices_response,
        release_seen_handler=_mark_current_release_seen,
        privacy_provider=_privacy_response,
        privacy_handler=_update_privacy,
    )
    _DASHBOARD_SERVER.configure_telemetry_handlers(
        status_provider=_telemetry_status_response,
        event_handler=_queue_telemetry_event,
        delete_handler=_delete_telemetry_data,
        check_handler=_check_telemetry_connection,
    )
    _DASHBOARD_SERVER.configure_notification_handlers(
        summary_provider=_notification_summary_response,
        list_handler=_notification_list_response,
        read_handler=_notification_read_response,
        read_all_handler=_notification_read_all_response,
        settings_provider=_notification_settings_response,
        settings_handler=_notification_settings_update_response,
        toasts_handler=_notification_toasts_response,
        toast_delivered_handler=_notification_toast_delivered_response,
    )
    _DASHBOARD_SERVER.configure_statistics_handler(_statistics_query_response)
    _DASHBOARD_SERVER.configure_fsrs_handler(_fsrs_query_response)
    _DASHBOARD_SERVER.configure_search_handlers(
        query_handler=_search_query_response,
        inspect_handler=_search_inspect_response,
    )
    _DASHBOARD_SERVER.configure_triage_handler(_triage_query_response)
    _DASHBOARD_SERVER.configure_inspection_profile_handlers(
        query_handler=_inspection_profile_query_response,
        validate_handler=_inspection_profile_validate_response,
        update_handler=_inspection_profile_update_response,
    )
    _DASHBOARD_SERVER.configure_entity_action_handlers(
        card_handler=_card_action_response,
        note_handler=_note_action_response,
    )
    _DASHBOARD_SERVER.configure_media_handler(_dashboard_media_file)


def _cache_status_response() -> dict:
    status = _STATS_CACHE.status()
    config = _read_config()
    status["useStatsCacheForReport"] = bool(config.get("use_stats_cache_for_report", False))
    status["reportSourceMode"] = (
        "Cache for historical data"
        if status["useStatsCacheForReport"]
        else "Legacy only"
    )
    return status


def _server_status_response() -> dict:
    config = _web_dashboard_config()
    cache = _cache_status_response()
    logs = log_status()
    integrations = _integration_status_response()
    return {
        "autoStart": bool(config.get("auto_start")),
        "configuredPort": int(config.get("port", DEFAULT_PORT)),
        "idleTimeoutSeconds": int(config.get("idle_timeout_seconds", DEFAULT_IDLE_TIMEOUT_SECONDS)),
        "hostLocked": True,
        "hostPolicy": "local-only",
        "maskedUrl": _masked_dashboard_url(_dashboard_url_for_route("/home", start=False)),
        "cacheStatus": {
            "status": cache.get("status", "unknown"),
            "useStatsCacheForReport": bool(cache.get("useStatsCacheForReport", False)),
            "dataSource": cache.get("dataSource"),
            "fallbackReason": cache.get("fallbackReason"),
        },
        "logs": logs,
        "integrations": integrations,
    }


def _dashboard_health_response() -> dict:
    state = _DASHBOARD_SERVER.state()
    return {
        "ok": state.running,
        "addon": ADDON_NAME,
        "mode": "e2e" if _is_e2e_mode() else "normal",
        "profile": _current_anki_profile_name(),
        "hasReport": state.report_available,
    }


def _dashboard_display_settings_response() -> dict:
    deck_options = _dashboard_deck_options()
    return {
        "ok": True,
        "settings": public_settings_config(deck_options=deck_options),
        "deckOptions": deck_options,
    }


def _update_dashboard_display_settings(payload: dict) -> dict:
    deck_options = _dashboard_deck_options()
    before = public_settings_config(deck_options=deck_options)
    try:
        settings = write_public_settings(
            payload if isinstance(payload, dict) else {},
            deck_options=deck_options,
        )
    except SettingsValidationError as error:
        return {
            "ok": False,
            "error": "invalid_settings",
            "message": "Проверьте значения настроек.",
            "fieldErrors": error.field_errors,
        }
    before_server = before.get("server") if isinstance(before.get("server"), dict) else {}
    saved_server = settings.get("server") if isinstance(settings.get("server"), dict) else {}
    restart_required = bool(
        _DASHBOARD_SERVER.state().running
        and any(
            before_server.get(key) != saved_server.get(key)
            for key in ("port", "idleTimeoutSeconds")
        )
    )
    response = {
        "ok": True,
        "message": "Настройки сохранены.",
        "settings": settings,
        "deckOptions": deck_options,
        "restartRequired": restart_required,
    }
    if "dashboard" not in payload:
        return response
    try:
        result = _prepare_default_dashboard_report()
        report = result.get("report")
        metadata = result.get("metadata")
        markdown = result.get("markdown")
        if isinstance(report, dict):
            _DASHBOARD_SERVER.publish_report(report)
            response["report"] = report
        _publish_dashboard_action_context(
            markdown if isinstance(markdown, str) else "",
            metadata if isinstance(metadata, dict) else {},
            None,
        )
        response["message"] = "Настройки сохранены, данные dashboard обновлены."
    except Exception:
        traceback.print_exc()
        response["reportRefreshError"] = "Settings saved, but dashboard report refresh failed."
    return response


def _dashboard_deck_options() -> list[dict]:
    return [
        {"id": deck_id, "name": deck_name}
        for deck_id, deck_name in _deck_names()
    ]


def _profile_model(snapshot: dict | None = None) -> dict:
    source = snapshot if isinstance(snapshot, dict) else _STATS_CACHE.report_snapshot()
    return build_profile_payload(
        source,
        _current_anki_today_date_key(),
        anki_profile_name=_current_anki_profile_name(),
        preferences=_PROFILE_STORE.read(),
    )


def _profile_response() -> dict:
    return {"ok": True, "profile": _profile_model()}


def _update_profile(payload: dict) -> dict:
    try:
        _PROFILE_STORE.update(payload if isinstance(payload, dict) else {})
    except ProfileValidationError as error:
        return {
            "ok": False,
            "error": "invalid_profile_preferences",
            "message": "Проверьте данные профиля.",
            "fieldErrors": error.field_errors,
        }
    profile = _profile_model()
    state = _DASHBOARD_SERVER.state()
    if state.report_path:
        try:
            report = json.loads(Path(state.report_path).read_text(encoding="utf-8"))
            if isinstance(report, dict):
                report["profile"] = profile
                _DASHBOARD_SERVER.publish_report(report)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "ok": True,
        "message": "Профиль сохранён.",
        "profile": profile,
    }


def _bundled_changelog() -> dict:
    return load_bundled_changelog(Path(__file__).resolve().parent / "changelog.json")


def _product_notices_response() -> dict:
    return product_notices_response(
        __version__,
        _PRODUCT_NOTICE_STORE,
        _PRIVACY_STORE,
        _bundled_changelog(),
    )


def _mark_current_release_seen() -> dict:
    _PRODUCT_NOTICE_STORE.mark_release_seen(__version__)
    _NOTIFICATION_STORE.mark_release_read(__version__)
    return _product_notices_response()


def _privacy_response() -> dict:
    response = privacy_response(_PRIVACY_STORE)
    response["telemetryClient"] = _TELEMETRY_CLIENT.public_status()
    return response


def _update_privacy(payload: dict) -> dict:
    try:
        privacy = _PRIVACY_STORE.save_choices(payload)
    except ProductNoticeValidationError as error:
        return {
            "ok": False,
            "error": "invalid_privacy_choices",
            "message": "Проверьте выбор приватности.",
            "fieldErrors": error.field_errors,
        }
    _TELEMETRY_CLIENT.apply_privacy_choices(privacy["telemetry"]["purposes"])
    response = _privacy_response()
    response["message"] = "Настройки приватности сохранены."
    return response


def _trusted_telemetry_dimensions() -> dict:
    aqt_module = sys.modules.get("aqt")
    raw_anki_version = str(getattr(aqt_module, "appVersion", "0.0.0") or "0.0.0")
    version_match = __import__("re").search(r"\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?", raw_anki_version)
    system = platform.system().lower()
    return {
        "addonVersion": __version__,
        "ankiVersion": version_match.group(0) if version_match else "0.0.0",
        "osFamily": {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(system, "other"),
        "locale": "unknown",
        "theme": "unknown",
    }


def _telemetry_status_response() -> dict:
    return {"ok": True, "telemetryClient": _TELEMETRY_CLIENT.public_status()}


def _queue_telemetry_event(payload: dict) -> dict:
    try:
        return _TELEMETRY_CLIENT.queue_semantic_event(payload)
    except TelemetryValidationError as error:
        return {
            "ok": False,
            "error": "invalid_telemetry_event",
            "fieldErrors": error.field_errors,
        }


def _delete_telemetry_data() -> dict:
    return _TELEMETRY_CLIENT.delete_remote_data()


def _check_telemetry_connection() -> dict:
    return _TELEMETRY_CLIENT.check_connection_and_send_now()


def _notification_summary_response() -> dict:
    return {"ok": True, **_NOTIFICATION_STORE.summary()}


def _notification_list_response(payload: dict) -> dict:
    if set(payload) != {"page", "pageLimit", "tab", "category"}:
        return {"ok": False, "error": "invalid_notification_request"}
    try:
        return {
            "ok": True,
            **_NOTIFICATION_STORE.list_notifications(
                page=payload["page"],
                page_limit=payload["pageLimit"],
                tab=payload["tab"],
                category=payload["category"],
            ),
        }
    except NotificationValidationError as error:
        return {"ok": False, "error": "invalid_notification_request", "fieldErrors": error.field_errors}


def _notification_read_response(payload: dict) -> dict:
    if set(payload) != {"notificationIds"} or not isinstance(payload.get("notificationIds"), list):
        return {"ok": False, "error": "invalid_notification_request"}
    try:
        return {"ok": True, "updated": _NOTIFICATION_STORE.mark_read(payload["notificationIds"]), **_NOTIFICATION_STORE.summary()}
    except NotificationValidationError as error:
        return {"ok": False, "error": "invalid_notification_request", "fieldErrors": error.field_errors}


def _notification_read_all_response(payload: dict) -> dict:
    if payload != {}:
        return {"ok": False, "error": "invalid_notification_request"}
    return {"ok": True, "updated": _NOTIFICATION_STORE.mark_all_read(), **_NOTIFICATION_STORE.summary()}


def _notification_settings_response() -> dict:
    return {"ok": True, "schemaVersion": 1, "preferences": _NOTIFICATION_STORE.preferences()}


def _notification_settings_update_response(payload: dict) -> dict:
    try:
        preferences = _NOTIFICATION_STORE.update_preferences(payload)
        return {"ok": True, "schemaVersion": 1, "preferences": preferences}
    except NotificationValidationError as error:
        return {"ok": False, "error": "invalid_notification_request", "fieldErrors": error.field_errors}


def _notification_toasts_response(payload: dict) -> dict:
    if set(payload) != {"sessionStartedAt"}:
        return {"ok": False, "error": "invalid_notification_request"}
    try:
        _maybe_seed_e2e_notification_toast(payload["sessionStartedAt"])
        return {
            "ok": True,
            "schemaVersion": 1,
            "items": _NOTIFICATION_STORE.toast_candidates(session_started_at=payload["sessionStartedAt"]),
        }
    except NotificationValidationError as error:
        return {"ok": False, "error": "invalid_notification_request", "fieldErrors": error.field_errors}


def _maybe_seed_e2e_notification_toast(session_started_at: str) -> None:
    if not _is_e2e_mode() or os.environ.get("ANKI_E2E_SCOPE") not in {"full", "notifications"}:
        return
    critical_revision = "e2e:toast-critical"
    warning_revision = "e2e:toast-warning"
    preferences = _NOTIFICATION_STORE.preferences()
    if not preferences["showInAppToasts"]:
        return
    evidence = {
        "recentAnswers": 70,
        "baselineAnswers": 280,
        "recentRetention": 0.72,
        "baselineRetention": 0.9,
        "dropPoints": 18.0,
    }
    candidate = {
        "code": "retention.recent_drop",
        "category": "retention",
        "severity": "critical",
        "dedupeKey": "retention.recent_drop:all",
        "entityType": "all_collection",
        "entityId": None,
        "evidence": evidence,
        "detectorVersion": "signals-v1.0",
    }
    if not _NOTIFICATION_STORE.has_notification_source_revision(critical_revision):
        _NOTIFICATION_STORE.reconcile(
            "retention.recent_drop",
            [candidate],
            source_revision=critical_revision,
            evaluated_at=session_started_at,
        )
        return
    if preferences["minimumToastSeverity"] not in {"warning", "info"}:
        return
    if _NOTIFICATION_STORE.has_notification_source_revision(warning_revision):
        return
    _NOTIFICATION_STORE.reconcile(
        "retention.recent_drop",
        [],
        source_revision="e2e:toast-warning-missing-1",
        evaluated_at=session_started_at,
    )
    _NOTIFICATION_STORE.reconcile(
        "retention.recent_drop",
        [],
        source_revision="e2e:toast-warning-missing-2",
        evaluated_at=session_started_at,
    )
    candidate["severity"] = "warning"
    candidate["evidence"] = {**evidence, "recentRetention": 0.8, "dropPoints": 10.0}
    _NOTIFICATION_STORE.reconcile(
        "retention.recent_drop",
        [candidate],
        source_revision=warning_revision,
        evaluated_at=session_started_at,
    )


def _notification_toast_delivered_response(payload: dict) -> dict:
    if set(payload) != {"notificationIds"} or not isinstance(payload.get("notificationIds"), list):
        return {"ok": False, "error": "invalid_notification_request"}
    try:
        return {"ok": True, "updated": _NOTIFICATION_STORE.mark_toast_delivered(payload["notificationIds"])}
    except NotificationValidationError as error:
        return {"ok": False, "error": "invalid_notification_request", "fieldErrors": error.field_errors}


def _statistics_query_response(payload: dict) -> dict:
    result = _run_on_anki_main_sync(
        lambda: _statistics_query_on_main(payload),
        timeout_seconds=30.0,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "error": "statistics_query_failed",
            "message": str(result.get("error") or "Statistics query failed."),
        }
    value = result.get("value")
    return value if isinstance(value, dict) else {
        "ok": False,
        "error": "statistics_query_failed",
        "message": "Statistics query failed.",
    }


def _search_query_response(payload: dict) -> dict:
    return run_search_query_sync(mw, payload)


def _search_inspect_response(payload: dict) -> dict:
    return run_search_inspect_sync(mw, payload)


def _triage_query_response(payload: dict) -> dict:
    return run_triage_query_sync(
        mw,
        payload,
        signal_provider=_NOTIFICATION_STORE.list_active_card_signals,
        profile_store_provider=_INSPECTION_PROFILE_STORE.read,
    )


def _inspection_profile_query_response(payload: dict) -> dict:
    return run_inspection_profile_query_sync(mw, payload, _INSPECTION_PROFILE_STORE)


def _inspection_profile_validate_response(payload: dict) -> dict:
    return run_inspection_profile_validate_sync(mw, payload, _INSPECTION_PROFILE_STORE)


def _inspection_profile_update_response(payload: dict) -> dict:
    return run_inspection_profile_update_sync(mw, payload, _INSPECTION_PROFILE_STORE)


def _card_action_response(payload: dict) -> dict:
    return run_card_action_sync(mw, payload)


def _note_action_response(payload: dict) -> dict:
    return run_note_action_sync(mw, payload)


def _statistics_query_on_main(payload: dict) -> dict:
    if mw is None or mw.col is None:
        return {"ok": False, "error": "statistics_unavailable", "message": "Collection is unavailable."}
    snapshot = _STATS_CACHE.report_snapshot()
    today_key = _current_anki_today_date_key()
    display_settings = _dashboard_display_settings_for_payload()
    current = collect_statistics_current_snapshot(mw.col, today_key)
    try:
        query = normalize_statistics_query(
            payload,
            current.get("deckCatalog"),
            display_settings=display_settings,
        )
    except StatisticsValidationError as error:
        return {
            "ok": False,
            "error": "invalid_statistics_query",
            "message": "Проверьте параметры запроса статистики.",
            "fieldErrors": error.field_errors,
        }
    status = snapshot.get("status") if isinstance(snapshot.get("status"), dict) else {}
    cache_key = json.dumps(
        {"query": query, "cacheUpdatedAt": status.get("updatedAt"), "today": today_key},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    if _STATISTICS_QUERY_CACHE.get("key") == cache_key and isinstance(_STATISTICS_QUERY_CACHE.get("value"), dict):
        return {"ok": True, "result": _STATISTICS_QUERY_CACHE["value"], "memoized": True}
    built = build_statistics_result(
        snapshot,
        current,
        today_key,
        query,
        display_settings=display_settings,
    )
    _STATISTICS_QUERY_CACHE.update({"key": cache_key, "value": built})
    return {"ok": True, "result": built, "memoized": False}


def _fsrs_query_response(payload: dict) -> dict:
    result = _run_on_anki_main_sync(lambda: _fsrs_query_on_main(payload), timeout_seconds=45.0)
    if not result.get("ok"):
        return {"ok": False, "error": "fsrs_query_failed", "message": str(result.get("error") or "FSRS query failed.")}
    value = result.get("value")
    return value if isinstance(value, dict) else {"ok": False, "error": "fsrs_query_failed", "message": "FSRS query failed."}


def _fsrs_query_on_main(payload: dict) -> dict:
    if mw is None or mw.col is None:
        return {"ok": False, "error": "fsrs_unavailable", "message": "Collection is unavailable."}
    try:
        response = execute_fsrs_query(mw.col, payload, dashboard_deck_ids=_dashboard_display_settings_for_payload().get("selected_deck_ids"))
    except FsrsValidationError as error:
        return {"ok": False, "error": "invalid_fsrs_query", "message": "Проверьте параметры FSRS-запроса.", "fieldErrors": error.field_errors}
    return {"ok": True, "response": response}


def _dashboard_display_settings_for_payload() -> dict:
    settings = dashboard_display_config()
    configured_ids = [
        int(deck_id)
        for deck_id in settings.get("selected_deck_ids", [])
        if _is_int_like(deck_id)
    ]
    deck_name_by_id = dict(_deck_names())
    selected_names = [
        deck_name_by_id.get(deck_id, f"Колода {deck_id}")
        for deck_id in configured_ids
    ]
    if not selected_names:
        selected_names = [
            str(name)
            for name in settings.get("selected_deck_names", [])
            if str(name or "").strip()
        ]
    selected_ids = configured_ids
    if selected_ids and settings.get("include_child_decks", True) and mw and mw.col:
        selected_ids = expand_deck_ids(mw.col, selected_ids)
    return {
        **settings,
        "selected_deck_ids": selected_ids,
        "selected_deck_names": selected_names,
    }


def _integration_status_response() -> dict:
    diagnostics = _integration_diagnostics_sections()
    return {
        "items": [
            _integration_item(
                "study_time_stats",
                "Study Time Stats",
                diagnostics.get("study_time_stats", ""),
            ),
            _integration_item(
                "session_tracker",
                "Review session tracker",
                diagnostics.get("session_tracker", ""),
            ),
            _integration_item(
                "heatmap",
                "Review heatmap",
                diagnostics.get("heatmap", ""),
            ),
            _integration_item("logs", "Integration logs", diagnostics.get("logs", "")),
        ],
        "notes": [
            "Optional integrations are detected from local Anki/add-on state.",
            "AnkiConnect is not required.",
        ],
    }


def _integration_item(key: str, label: str, diagnostics: str) -> dict:
    text = str(diagnostics or "")
    lowered = text.lower()
    status = "warning"
    if any(marker in lowered for marker in ("available", "найден", "включ", "ok", "готов")):
        status = "good"
    if any(marker in lowered for marker in ("error", "traceback", "ошибка")):
        status = "danger"
    if not text.strip():
        status = "neutral"
    return {
        "id": key,
        "label": label,
        "status": status,
        "enabled": status in {"good", "warning"},
        "diagnostics": text[:4000],
        "description": _integration_description(key),
    }


def _integration_description(key: str) -> str:
    return {
        "study_time_stats": "Optional source for real study time, used only when available.",
        "session_tracker": "Built-in lightweight tracker for review-session timing.",
        "heatmap": "Personal review heatmap diagnostics.",
        "logs": "Local technical logs for optional integration diagnostics.",
    }.get(key, "Optional local integration.")


def _dashboard_actions() -> DashboardActions:
    global _DASHBOARD_ACTIONS
    if _DASHBOARD_ACTIONS is None:
        _DASHBOARD_ACTIONS = DashboardActions(
            run_on_main=_run_on_anki_main_sync,
            copy_markdown=_copy_dashboard_markdown_to_clipboard,
            save_markdown=_save_dashboard_markdown,
            open_current_dashboard=_open_current_dashboard_from_action,
            open_route=_open_dashboard_route_from_action,
            copy_url=_copy_dashboard_url_from_action,
            restart_server=_restart_web_dashboard_server,
            stop_server=_stop_web_dashboard_server,
            log_event=log_event,
            open_native_stats=_open_native_anki_stats,
        )
    return _DASHBOARD_ACTIONS


def _copy_dashboard_markdown_to_clipboard(markdown: str) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is None:
        raise RuntimeError("Clipboard is unavailable.")
    clipboard.setText(markdown)


def _save_dashboard_markdown(markdown: str) -> str | None:
    filename, _selected_filter = QFileDialog.getSaveFileName(
        mw,
        "Сохранить Markdown-отчёт",
        _default_markdown_filename(),
        "Markdown (*.md);;Text files (*.txt);;All files (*)",
    )
    if not filename:
        return None
    with open(filename, "w", encoding="utf-8") as file:
        file.write(markdown)
        file.write("\n")
    return filename


def _open_current_dashboard_from_action() -> None:
    state = _ensure_web_dashboard_server()
    if not state.url:
        raise RuntimeError("Dashboard server is stopped.")
    QDesktopServices.openUrl(QUrl(state.url))


def _open_native_anki_stats() -> None:
    if mw is None or not hasattr(mw, "onStats"):
        raise RuntimeError("Native Anki statistics is unavailable.")
    mw.onStats()


def _open_dashboard_route_from_action(route: str, event: str) -> None:
    url = _dashboard_url_for_route(route)
    QDesktopServices.openUrl(QUrl(url))
    log_event(event, "Dashboard route opened", route=route)


def _copy_dashboard_url_from_action() -> None:
    url = _dashboard_url_for_route("/home")
    QApplication.clipboard().setText(url)
    log_event("server.copy_url", "Dashboard URL copied")


def _clear_report_cache() -> None:
    _REPORT_CACHE["key"] = None
    _REPORT_CACHE["created_at"] = 0.0
    _REPORT_CACHE["metrics"] = None
    _STATISTICS_QUERY_CACHE.update({"key": None, "value": None})
    _dashboard_actions().clear_report_context()
    _DASHBOARD_SERVER.clear_report()


def _publish_dashboard_action_context(
    markdown: str,
    metadata: dict,
    deck_ids: list[int] | None,
) -> None:
    _dashboard_actions().publish_report_context(markdown, metadata, deck_ids)


def _run_on_anki_main_sync(callback: Callable[[], object], timeout_seconds: float = 8.0) -> dict:
    if mw is None or not hasattr(mw, "taskman"):
        return {"ok": False, "error": "Anki task manager is unavailable."}

    event = threading.Event()
    holder: dict[str, object] = {}

    def run() -> None:
        try:
            holder["value"] = callback()
            holder["ok"] = True
        except Exception:
            traceback.print_exc()
            holder["ok"] = False
            holder["error"] = "Dashboard action failed."
        finally:
            event.set()

    try:
        mw.taskman.run_on_main(run)
    except Exception:
        traceback.print_exc()
        return {"ok": False, "error": "Could not schedule dashboard action."}

    if not event.wait(timeout_seconds):
        return {"ok": False, "error": "Dashboard action did not finish yet."}
    if holder.get("ok"):
        return {"ok": True, "value": holder.get("value")}
    return {"ok": False, "error": str(holder.get("error") or "Dashboard action failed.")}


def _request_cache_rebuild() -> dict:
    return _schedule_cache_action("rebuild")


def _request_cache_refresh() -> dict:
    return _schedule_cache_action("refresh")


def _schedule_cache_action(action: str) -> dict:
    if mw is None or not hasattr(mw, "taskman"):
        _STATS_CACHE.mark_error("Anki task manager is unavailable.")
        return {
            "ok": False,
            "status": "error",
            "message": "Anki task manager is unavailable.",
        }

    prepare = (
        _STATS_CACHE.prepare_rebuild
        if action == "rebuild"
        else _STATS_CACHE.prepare_refresh
    )
    if not prepare():
        return {
            "ok": True,
            "status": "building",
            "alreadyBuilding": True,
            "message": "Cache operation is already running",
        }
    _clear_report_cache()

    def start_on_main() -> None:
        _start_cache_action_on_main(action)

    try:
        mw.taskman.run_on_main(start_on_main)
    except Exception:
        traceback.print_exc()
        _STATS_CACHE.mark_error(f"Could not schedule cache {action}.")
        return {
            "ok": False,
            "status": "error",
            "message": f"Could not schedule cache {action}.",
        }

    return {
        "ok": True,
        "status": "scheduled",
        "message": f"Statistics cache {action} scheduled.",
    }


def _start_cache_action_on_main(action: str) -> None:
    if mw is None or mw.col is None:
        _STATS_CACHE.mark_error("Collection is unavailable.")
        return

    if not _STATS_CACHE.mark_building():
        return

    col = mw.col
    profile_name = _current_anki_profile_name()

    def finish(future) -> None:
        try:
            future.result()
            _clear_report_cache()
        except Exception:
            traceback.print_exc()
            _STATS_CACHE.mark_error(f"Background cache {action} failed.")

    try:
        if action == "rebuild":
            operation = lambda: _STATS_CACHE.rebuild_all_time_cache(
                col,
                profile_name=profile_name,
                already_started=True,
            )
        else:
            operation = lambda: _STATS_CACHE.refresh_incremental(
                col,
                profile_name=profile_name,
                already_started=True,
            )
        mw.taskman.run_in_background(
            operation,
            finish,
        )
    except Exception:
        traceback.print_exc()
        _STATS_CACHE.mark_error(f"Could not start cache {action}.")


def _current_anki_profile_name() -> str | None:
    try:
        return str(mw.pm.name)
    except Exception:
        return None


def _prepare_default_dashboard_report() -> dict:
    """Prepare the default dashboard report from cache and display settings."""

    if mw is None or mw.col is None:
        raise RuntimeError("Collection is unavailable.")

    cache_result = _ensure_default_dashboard_cache_current()
    snapshot = _STATS_CACHE.report_snapshot()
    today_key = _current_anki_today_date_key()
    display_settings = _dashboard_display_settings_for_payload()
    metadata = build_default_dashboard_metadata(
        snapshot,
        today_key,
        display_settings=display_settings,
    )
    metrics = metrics_from_cache_snapshot(snapshot, today_key, display_settings)
    metrics = _apply_default_dashboard_attention_cards(metrics, metadata, display_settings)
    metrics = _apply_default_dashboard_deck_catalog(metrics, display_settings)
    report = _dashboard_report_payload(metrics, metadata)
    report["today"] = build_today_dashboard_payload(
        snapshot,
        today_key,
        display_settings=display_settings,
        cache_summary=_dashboard_cache_summary(),
    )
    try:
        markdown = build_markdown_report(metrics, metadata)
    except Exception:
        traceback.print_exc()
        markdown = ""

    return {
        "ok": True,
        "url": _dashboard_url_for_route("/home", start=False),
        "message": "Dashboard ready.",
        "cacheResult": cache_result,
        "report": report,
        "markdown": markdown,
        "metadata": metadata,
    }


def _dashboard_media_file(name: str) -> tuple[bytes, str] | None:
    from .note_intelligence import sanitize_media_filename
    from .path_safety import safe_leaf_name

    safe_name = safe_leaf_name(sanitize_media_filename(name))
    if not safe_name or mw is None or getattr(mw, "col", None) is None:
        return None
    media = getattr(mw.col, "media", None)
    if media is None:
        return None
    media_dir = None
    try:
        dir_attr = getattr(media, "dir", None)
        media_dir = dir_attr() if callable(dir_attr) else dir_attr
    except Exception:
        media_dir = None
    if not media_dir:
        return None
    try:
        root = Path(media_dir).resolve()
        target = (root / safe_name).resolve(strict=True)
        target.relative_to(root)
        payload = target.read_bytes()
    except (OSError, RuntimeError, ValueError):
        return None
    return payload, target.suffix.lower()


def _apply_default_dashboard_attention_cards(
    metrics: dict,
    metadata: dict,
    display_settings: dict,
) -> dict:
    """Overlay fresh card-level rows onto cache-backed default dashboard metrics."""

    updated = dict(metrics if isinstance(metrics, dict) else {})
    col = getattr(mw, "col", None) if mw is not None else None
    if col is None or getattr(col, "db", None) is None:
        updated["attention_cards"] = []
        updated["note_type_catalog"] = []
        updated["attention_cards_status"] = {
            "status": "unavailable",
            "scannedCards": 0,
            "returnedCards": 0,
            "reason": "collection unavailable",
            "collectorRan": False,
            "collectionAvailable": False,
            "source": "fresh",
        }
        return updated

    start_ts = dashboard_int(metadata.get("period_start_ts"))
    end_ts = dashboard_int(metadata.get("period_end_ts"))
    selected_deck_ids = display_settings.get("selected_deck_ids") if isinstance(display_settings, dict) else None
    try:
        attention_cards, attention_status = collect_attention_cards_with_status(
            col,
            start_ts,
            end_ts,
            selected_deck_ids if isinstance(selected_deck_ids, list) else None,
            max_results=ATTENTION_CARD_LIMIT,
        )
        updated["attention_cards"] = attention_cards
        status_payload = attention_status if isinstance(attention_status, dict) else {}
        if isinstance(status_payload.get("noteTypeCatalog"), list):
            updated["note_type_catalog"] = status_payload["noteTypeCatalog"]
        normalized_status = str(status_payload.get("status") or "unavailable")
        updated["attention_cards_status"] = {
            **status_payload,
            "status": normalized_status,
            "collectorRan": True,
            "collectionAvailable": bool(
                status_payload.get("collectionAvailable")
                if status_payload.get("collectionAvailable") is not None
                else normalized_status == "available"
            ),
            "source": "fresh",
        }
    except Exception as exc:
        traceback.print_exc()
        updated["attention_cards"] = []
        updated["attention_cards_status"] = {
            "status": "error",
            "scannedCards": 0,
            "returnedCards": 0,
            "reason": _safe_dashboard_attention_reason(exc),
            "collectorRan": True,
            "collectionAvailable": col is not None and getattr(col, "db", None) is not None,
            "source": "fresh",
        }
    return updated


def _apply_default_dashboard_deck_catalog(metrics: dict, display_settings: dict) -> dict:
    """Attach the current normal/filtered deck catalog to cache aggregates."""

    updated = dict(metrics if isinstance(metrics, dict) else {})
    col = getattr(mw, "col", None) if mw is not None else None
    updated["deck_catalog"] = collect_deck_catalog(col) if col is not None else []
    selected = display_settings.get("selected_deck_ids") if isinstance(display_settings, dict) else None
    updated["deck_scope_ids"] = list(selected) if isinstance(selected, list) and selected else None
    updated["deck_active_dates_available"] = True
    return updated


def _safe_dashboard_attention_reason(error: object) -> str:
    text = str(error or "").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    if not text:
        return "Card-level collector failed."
    for marker in ("token=", "Traceback", "File "):
        if marker.lower() in text.lower():
            return "Card-level collector failed."
    if len(text) > 160:
        return text[:159].rstrip() + "…"
    return text


def _ensure_default_dashboard_cache_current() -> dict:
    """Refresh a ready cache or rebuild it when no reliable all-time cache exists."""

    profile_name = _current_anki_profile_name()
    status = _STATS_CACHE.status()
    current_status = str(status.get("status") or "empty")
    if current_status in {"scheduled", "building"}:
        if dashboard_int(status.get("cachedDays")) > 0:
            return {
                "ok": True,
                "status": current_status,
                "message": "Using existing cache while another cache operation is running.",
            }
        raise RuntimeError("Statistics cache is already building.")

    if current_status == "ready" and dashboard_int(status.get("cachedDays")) > 0:
        refresh = _STATS_CACHE.refresh_incremental(
            mw.col,
            profile_name=profile_name,
        )
        if refresh.get("rebuildRequired") or str(refresh.get("status") or "") in {"stale", "empty"}:
            return _STATS_CACHE.rebuild_all_time_cache(
                mw.col,
                profile_name=profile_name,
            )
        if not refresh.get("ok"):
            raise RuntimeError(str(refresh.get("error") or refresh.get("message") or "Cache refresh failed."))
        return refresh

    rebuild = _STATS_CACHE.rebuild_all_time_cache(
        mw.col,
        profile_name=profile_name,
    )
    if not rebuild.get("ok"):
        raise RuntimeError(str(rebuild.get("error") or rebuild.get("message") or "Cache rebuild failed."))
    return rebuild


def _stop_web_dashboard_server(*_args) -> None:
    _DASHBOARD_SERVER.stop()
    if _WEB_DASHBOARD_DIALOG is not None:
        _WEB_DASHBOARD_DIALOG.refresh_status()
    if _STUDY_REPORT_DIALOG is not None:
        _STUDY_REPORT_DIALOG._update_dashboard_status()
    if _LAUNCHER_DIALOG is not None:
        _LAUNCHER_DIALOG.refresh_status()


def _restart_web_dashboard_server() -> None:
    _stop_web_dashboard_server()
    _start_web_dashboard_server()


def _maybe_auto_start_web_dashboard() -> None:
    if _web_dashboard_config().get("auto_start"):
        try:
            _start_web_dashboard_server()
        except Exception:
            log_exception("server.auto_start", "Dashboard auto-start failed")


def _is_e2e_mode() -> bool:
    return os.environ.get("ANKI_STUDY_REPORT_E2E") == "1"


def _e2e_artifacts_dir() -> Path:
    return Path(
        os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR")
        or os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS")
        or "/e2e/artifacts"
    )


def _e2e_ready_file() -> Path:
    return Path(
        os.environ.get("ANKI_STUDY_REPORT_E2E_READY_FILE")
        or str(_e2e_artifacts_dir() / "runtime" / "dashboard-ready.json")
    )


def _current_mw():
    try:
        import aqt as _aqt

        current = getattr(_aqt, "mw", None)
    except Exception:
        current = None
    return current if current is not None else mw


def _maybe_configure_e2e_logging() -> None:
    if not _is_e2e_mode():
        return
    diagnostics_dir = _e2e_artifacts_dir() / "diagnostics"
    try:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        configure_log_dir(diagnostics_dir)
    except Exception:
        error_traceback = traceback.format_exc()
        _write_e2e_event(
            "error",
            where="e2e_logging_config",
            error=str(error_traceback.splitlines()[-1] if error_traceback else ""),
            traceback=error_traceback,
        )


def _e2e_context_fields() -> dict[str, object]:
    main_window = _current_mw()
    collection = getattr(main_window, "col", None) if main_window is not None else None
    profile_manager = getattr(main_window, "pm", None) if main_window is not None else None
    return {
        "mwExists": main_window is not None,
        "mwRepr": _e2e_safe_repr(main_window),
        "colExists": collection is not None,
        "colRepr": _e2e_safe_repr(collection),
        "profileManagerRepr": _e2e_safe_repr(profile_manager),
        "profile": _current_anki_profile_name(),
        "profileFolder": _safe_profile_folder(),
    }


def _safe_profile_folder() -> str | None:
    try:
        main_window = _current_mw()
        return str(main_window.pm.profileFolder())
    except Exception:
        return None


def _schedule_e2e_dashboard_bootstrap(hook_name: str) -> None:
    global _E2E_BOOTSTRAP_STARTED
    if not _is_e2e_mode():
        return
    if _E2E_BOOTSTRAP_STARTED or _E2E_BOOTSTRAP_DONE:
        _write_e2e_event(
            "bootstrap_already_started",
            hook=hook_name,
            started=_E2E_BOOTSTRAP_STARTED,
            done=_E2E_BOOTSTRAP_DONE,
        )
        return
    _E2E_BOOTSTRAP_STARTED = True
    _write_e2e_event("bootstrap_scheduled", hook=hook_name, delayMs=0)
    _schedule_e2e_on_main_thread(_maybe_start_e2e_dashboard)


def _schedule_e2e_on_main_thread(callback: Callable[[], None]) -> None:
    try:
        from aqt.qt import QTimer as _QTimer

        _QTimer.singleShot(0, callback)
    except Exception:
        _write_e2e_event("timer_unavailable", fallback="direct_call")
        callback()


def _maybe_start_e2e_dashboard() -> None:
    global mw, _E2E_BOOTSTRAP_DONE
    if not _is_e2e_mode():
        return

    _maybe_configure_e2e_logging()
    try:
        artifacts_dir = _e2e_artifacts_dir()
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        current_main_window = _current_mw()
        if current_main_window is not None and current_main_window is not mw:
            mw = current_main_window
            _write_e2e_event("main_window_refreshed")
        if mw is None or getattr(mw, "col", None) is None:
            _write_e2e_event("collection_unavailable", **_e2e_context_fields())
            return
        _write_e2e_event("collection_available", **_e2e_context_fields())
        _configure_dashboard_cache_handlers()
        _write_e2e_event("report_build_start")
        result = _prepare_default_dashboard_report()
        report = result.get("report")
        _write_e2e_event("report_build_done", hasReport=isinstance(report, dict))
        state = _DASHBOARD_SERVER.state()
        e2e_port = _e2e_port()
        _write_e2e_event("server_start_start", port=e2e_port, alreadyRunning=state.running)
        if not state.running:
            state = _DASHBOARD_SERVER.start(port=e2e_port, idle_timeout_seconds=0)
            _write_e2e_event("server_start_done", port=state.port)
        else:
            _write_e2e_event("server_start_done", port=state.port, alreadyRunning=True)
        _write_e2e_event("report_publish_start", hasReport=isinstance(report, dict))
        if isinstance(report, dict):
            _DASHBOARD_SERVER.publish_report(report)
        _write_e2e_event("report_publish_done", hasReport=isinstance(report, dict))
        _write_e2e_event("report_published", hasReport=isinstance(report, dict))
        _publish_dashboard_action_context(
            result.get("markdown") if isinstance(result.get("markdown"), str) else "",
            result.get("metadata") if isinstance(result.get("metadata"), dict) else {},
            None,
        )
        _write_e2e_event("readiness_write_start", path=str(_e2e_ready_file()))
        _write_e2e_readiness_file(_DASHBOARD_SERVER.state())
        _write_e2e_event("readiness_write_done", path=str(_e2e_ready_file()))
        log_event("e2e.ready", "Dashboard E2E readiness file written")
        _E2E_BOOTSTRAP_DONE = True
    except Exception:
        error_traceback = traceback.format_exc()
        _write_e2e_event(
            "error",
            where="e2e_bootstrap",
            error=str(error_traceback.splitlines()[-1] if error_traceback else ""),
            traceback=error_traceback,
        )
        traceback.print_exc()
        log_exception("e2e.startup", "Dashboard E2E startup failed")


def _e2e_port() -> int:
    try:
        return int(os.environ.get("ANKI_STUDY_REPORT_E2E_PORT") or DEFAULT_PORT)
    except (TypeError, ValueError):
        return DEFAULT_PORT


def _write_e2e_readiness_file(state) -> None:
    ready_file = _e2e_ready_file()
    ready_file.parent.mkdir(parents=True, exist_ok=True)
    base_url = f"http://{state.host}:{state.port}"
    payload = {
        "port": state.port,
        "baseUrl": base_url,
        "url": f"{base_url}/?token={_dashboard_token_from_url(state.url)}#/home",
        "token": _dashboard_token_from_url(state.url),
        "startedAt": datetime.now().isoformat(timespec="seconds"),
        "addonVersion": _addon_manifest_version(),
        "profile": _current_anki_profile_name(),
        "mode": "e2e",
        "reportAvailable": bool(state.report_available),
    }
    ready_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _dashboard_token_from_url(url: str | None) -> str:
    if not url or "token=" not in url:
        return ""
    token = url.split("token=", 1)[1]
    for delimiter in ("&", "#"):
        if delimiter in token:
            token = token.split(delimiter, 1)[0]
    return token


def _addon_manifest_version() -> str:
    return __version__


def _web_dashboard_status_text() -> str:
    state = _DASHBOARD_SERVER.state()
    running = "да" if state.running else "нет"
    static = "да" if state.static_available else "нет"
    report = "да" if state.report_available else "нет"
    lines = [
        f"Запущен: {running}",
        f"URL: {state.url or 'сервер остановлен'}",
        f"Порт: {state.port}",
        f"Запрошенный порт: {state.requested_port}",
        f"Конфликт порта: {'да' if state.port_collision else 'нет'}",
        f"Статика dashboard найдена: {static}",
        f"Временный отчёт опубликован: {report}",
        f"Папка статики: {state.static_dir or 'не найдена'}",
        f"Запущен в: {state.started_at or '—'}",
        f"Последний запрос: {state.last_request_at or '—'}",
        f"Авто-отключение: {_idle_timeout_label(state.idle_timeout_seconds)}",
    ]
    if state.message:
        lines.extend(["", state.message])
    if not state.static_available:
        lines.extend(
            [
                "",
                "Полный Vite dashboard не найден, поэтому сервер отдаёт встроенный dashboard.",
                "Он показывает опубликованный временный отчёт из /api/report и не требует сборки frontend.",
            ]
        )
    return "\n".join(lines)


def _dashboard_report_payload(metrics: dict, metadata: dict) -> dict:
    report = build_dashboard_report_payload(
        metrics,
        metadata,
        cache_summary=_dashboard_cache_summary(),
    )
    snapshot = _STATS_CACHE.report_snapshot()
    today_key = _current_anki_today_date_key()
    display_settings = _dashboard_display_settings_for_payload()
    report["profile"] = _profile_model(snapshot)
    report["activityHub"] = build_activity_hub_payload(
        snapshot,
        today_key,
        display_settings=display_settings,
    )
    current_statistics = (
        collect_statistics_current_snapshot(mw.col, today_key)
        if mw is not None and mw.col is not None
        else {"deckCatalog": metrics.get("deck_catalog", [])}
    )
    report["statisticsHub"] = build_statistics_hub(
        snapshot,
        current_statistics,
        today_key,
        display_settings=display_settings,
    )
    cache_status = snapshot.get("status") if isinstance(snapshot.get("status"), dict) else {}
    if cache_status.get("status") == "ready":
        revision = signal_source_revision(snapshot, today_key)
        signal_inputs = {**current_statistics, "deckHub": report.get("deckHub"), "detectorFailures": []}
        if _NOTIFICATION_STORE.detector_revision("card.repeated_again") != revision:
            try:
                signal_inputs["repeatedAgainCards"] = collect_repeated_again_cards(mw.col, today_key)
            except Exception:
                signal_inputs["detectorFailures"].append("card.repeated_again")
        _SIGNAL_EVALUATOR.evaluate(snapshot, signal_inputs, today_key, source_revision=revision)
    cache_config = {
        **_read_config(),
        "period_start_ts": metadata.get("period_start_ts"),
        "period_end_ts": metadata.get("period_end_ts"),
        "period_start_date": metadata.get("period_start_date"),
        "period_end_date": metadata.get("period_end_date"),
        "today_date": metadata.get("today_date"),
    }
    if metadata.get("force_stats_cache_for_report"):
        cache_config["use_stats_cache_for_report"] = True
    if metadata.get("dashboard_display_deck_filter"):
        return report
    cache_parts = build_cached_report_parts(
        _STATS_CACHE,
        str(metadata.get("period_id") or ""),
        cache_config,
        legacy_report={"metrics": metrics, "payload": report},
    )
    merged = merge_cached_report_parts(report, cache_parts)
    merged["profile"] = report["profile"]
    merged["activityHub"] = report["activityHub"]
    merged["statisticsHub"] = report["statisticsHub"]
    return merged


def _dashboard_cache_summary() -> dict:
    try:
        return _STATS_CACHE.report_summary()
    except Exception:
        traceback.print_exc()
        return {
            "status": "error",
            "updatedAt": 0,
            "cachedDays": 0,
            "cachedDeckDays": 0,
        }


def _idle_timeout_label(seconds: int) -> str:
    if seconds <= 0:
        return "выключено"
    minutes = round(seconds / 60)
    if minutes >= 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} ч {rest} мин" if rest else f"{hours} ч"
    return f"{minutes} мин"


def _integration_diagnostics_sections() -> dict[str, str]:
    col = mw.col if mw and mw.col else None
    return {
        "study_time_stats": diagnose_study_time_stats(col),
        "session_tracker": diagnose_session_tracker(col),
        "heatmap": diagnose_review_heatmap_personal(),
        "logs": "\n\n".join(
            [
                "Лог интеграций",
                integration_log_text(),
                "Лог трекера повторений",
                session_tracker_log_text(),
            ]
        ),
    }


def _safe_collect_metrics(
    col,
    start_ts: int,
    end_ts: int,
    deck_ids: list[int] | None,
    answer_mode: str,
    use_study_time_stats: bool,
    track_reviewer_sessions: bool,
) -> dict:
    try:
        metrics = collect_metrics(
            col,
            start_ts,
            end_ts,
            deck_ids=deck_ids,
            answer_mode=answer_mode,
        )
        if track_reviewer_sessions:
            tracked_time = collect_tracked_study_time(
                col,
                start_ts,
                end_ts,
                deck_ids=deck_ids,
            )
            if tracked_time.get("available"):
                metrics["real_study_time"] = tracked_time
            elif use_study_time_stats:
                study_time = collect_real_study_time(
                    col,
                    start_ts,
                    end_ts,
                    deck_ids=deck_ids,
                )
                metrics["real_study_time"] = (
                    study_time if study_time.get("available") else tracked_time
                )
            else:
                metrics["real_study_time"] = tracked_time
        elif use_study_time_stats:
            metrics["real_study_time"] = collect_real_study_time(
                col,
                start_ts,
                end_ts,
                deck_ids=deck_ids,
            )
        else:
            metrics["real_study_time"] = unavailable_tracked_time(
                "disabled",
                "Реальное время занятий отключено в настройках.",
            )
        return {
            "ok": True,
            "metrics": metrics,
        }
    except Exception:
        return {
            "ok": False,
            "error": traceback.format_exc(),
        }


def _deck_names() -> list[tuple[int, str]]:
    if mw is None or mw.col is None:
        return []

    try:
        decks = [
            (int(deck.id), str(deck.name))
            for deck in mw.col.decks.all_names_and_ids()
        ]
    except Exception:
        traceback.print_exc()
        return []

    return sorted(decks, key=lambda deck: deck[1].lower())


def _deck_ids_matching_keywords(keywords) -> list[int]:
    normalized_keywords = [
        str(keyword).lower()
        for keyword in keywords
        if str(keyword or "").strip()
    ]
    if not normalized_keywords:
        return []

    deck_ids = []
    for deck_id, deck_name in _deck_names():
        normalized_name = deck_name.lower()
        if any(keyword in normalized_name for keyword in normalized_keywords):
            deck_ids.append(deck_id)
    return deck_ids


def _current_deck_id() -> int | None:
    if mw is None or mw.col is None:
        return None

    try:
        deck = mw.col.decks.current()
        if isinstance(deck, dict):
            return int(deck["id"])
        return int(deck.id)
    except Exception:
        traceback.print_exc()
        return None


def _is_int_like(value) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _qdate_from_config(value, fallback: QDate) -> QDate:
    qdate = QDate.fromString(str(value or ""), "yyyy-MM-dd")
    return qdate if qdate.isValid() else fallback


def _date_key_from_timestamp(timestamp: int | float) -> str:
    try:
        value = max(0, float(timestamp))
    except (TypeError, ValueError):
        value = 0
    return datetime.fromtimestamp(value).date().isoformat()


def _current_anki_today_date_key() -> str:
    try:
        day_cutoff = int(mw.col.sched.day_cutoff) if mw and mw.col else 0
    except Exception:
        day_cutoff = 0
    if day_cutoff > SECONDS_IN_DAY:
        return _date_key_from_timestamp(day_cutoff - SECONDS_IN_DAY)
    return _date_key_from_timestamp(int(datetime.now().timestamp()))


def _period_bounds(period: str) -> tuple[int, int]:
    now = datetime.now()
    now_ts = int(now.timestamp())

    if period in {"today", "yesterday"}:
        anki_bounds = _anki_day_bounds(period, now_ts)
        if anki_bounds is not None:
            return anki_bounds

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "yesterday":
        start = today - timedelta(days=1)
        end = today
    elif period == "last_7_days":
        start = now - timedelta(days=7)
        end = now
    elif period == "last_30_days":
        start = now - timedelta(days=30)
        end = now
    elif period == "all_time":
        return 0, int(now.timestamp())
    else:
        start = today
        end = now

    start_ts = 0 if start.year <= 1970 else int(start.timestamp())
    return start_ts, int(end.timestamp())


def _anki_day_bounds(period: str, now_ts: int) -> tuple[int, int] | None:
    try:
        day_cutoff = int(mw.col.sched.day_cutoff) if mw and mw.col else 0
    except Exception:
        return None
    if day_cutoff <= 0:
        return None

    # Anki's "today" rolls over at the scheduler cutoff, not at system midnight.
    today_start = day_cutoff - SECONDS_IN_DAY
    if period == "today":
        return today_start, now_ts
    if period == "yesterday":
        return today_start - SECONDS_IN_DAY, today_start
    return None


def _is_large_period(start_ts: int, end_ts: int) -> bool:
    return end_ts - start_ts > LARGE_PERIOD_WARNING_DAYS * 24 * 60 * 60


def _report_cache_key(period: object, deck_ids: list[int] | None) -> tuple:
    if deck_ids is None:
        deck_key = None
    else:
        deck_key = tuple(sorted(int(deck_id) for deck_id in deck_ids))
    return period, deck_key


def _cached_metrics(cache_key: tuple) -> dict | None:
    if _REPORT_CACHE["key"] != cache_key:
        return None
    if monotonic() - float(_REPORT_CACHE["created_at"]) > REPORT_CACHE_TTL_SECONDS:
        return None

    metrics = _REPORT_CACHE["metrics"]
    return metrics if isinstance(metrics, dict) else None


def _store_cached_metrics(cache_key: tuple, metrics: dict) -> None:
    _REPORT_CACHE["key"] = cache_key
    _REPORT_CACHE["created_at"] = monotonic()
    _REPORT_CACHE["metrics"] = metrics


def _default_markdown_filename() -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    return f"anki-study-report-{date}.md"


def _setup_menu(main_window) -> None:
    """Register Tools -> Anki Study Report Launcher."""

    if main_window is None:
        return

    action = QAction("Open Anki Study Report Launcher", main_window)
    action.triggered.connect(_open_launcher_dialog)
    main_window.form.menuTools.addAction(action)

    setup_session_tracking(gui_hooks, mw)
    _maybe_configure_e2e_logging()
    log_event("addon.startup", "Anki Study Report add-on initialized")
    _start_telemetry_runtime(main_window)
    _maybe_auto_start_web_dashboard()
    _schedule_e2e_dashboard_bootstrap("main_window_did_init")


def _start_telemetry_runtime(main_window) -> None:
    global _TELEMETRY_TIMER, _TELEMETRY_STARTED_CLIENT
    try:
        from aqt.qt import QTimer as _QTimer

        if _TELEMETRY_STARTED_CLIENT is not _TELEMETRY_CLIENT:
            _TELEMETRY_CLIENT.queue_semantic_event({"eventCode": "addon.started", "occurredAt": utc_now()})
            _TELEMETRY_CLIENT.request_send(force=True)
            _TELEMETRY_STARTED_CLIENT = _TELEMETRY_CLIENT
        if _TELEMETRY_TIMER is None:
            _TELEMETRY_TIMER = _QTimer(main_window)
            _TELEMETRY_TIMER.setInterval(15 * 60 * 1000)
            _TELEMETRY_TIMER.timeout.connect(_telemetry_timer_tick)
        _TELEMETRY_TIMER.start()
    except Exception:
        log_exception("telemetry.startup.error", "Telemetry runtime initialization failed")


def _telemetry_timer_tick() -> None:
    request_active_client_send(lambda: _TELEMETRY_CLIENT)


def _stop_runtime_services(*args) -> None:
    global _TELEMETRY_TIMER, _TELEMETRY_STARTED_CLIENT
    if _TELEMETRY_TIMER is not None:
        _TELEMETRY_TIMER.stop()
        _TELEMETRY_TIMER = None
    _TELEMETRY_CLIENT.close()
    _NOTIFICATION_STORE.close()
    _TELEMETRY_STARTED_CLIENT = None
    _stop_web_dashboard_server(*args)


def _on_main_window_did_init() -> None:
    _write_e2e_event("hook_fired", hook="main_window_did_init")
    _setup_menu(_current_mw())


def _on_profile_did_open(*_args) -> None:
    _write_e2e_event("hook_fired", hook="profile_did_open")
    _rebind_profile_notice_telemetry_runtime()
    _start_telemetry_runtime(_current_mw())
    _schedule_e2e_dashboard_bootstrap("profile_did_open")


def _rebind_profile_notice_telemetry_runtime() -> None:
    global _PRODUCT_NOTICE_STORE, _PRIVACY_STORE, _TELEMETRY_STORE, _TELEMETRY_CLIENT, _NOTIFICATION_STORE, _SIGNAL_EVALUATOR
    data_dir = _addon_runtime_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        _TELEMETRY_CLIENT.close()
    except Exception:
        pass
    try:
        _NOTIFICATION_STORE.close()
    except Exception:
        pass
    _PRODUCT_NOTICE_STORE = ProductNoticeStore(data_dir / "product_notices.json")
    _PRIVACY_STORE = PrivacyStore(data_dir / "privacy.json")
    _TELEMETRY_STORE = TelemetryStore(data_dir / "telemetry.sqlite3")
    _TELEMETRY_CLIENT = _new_telemetry_client(_TELEMETRY_STORE, _PRIVACY_STORE)
    _NOTIFICATION_STORE = NotificationStore(data_dir / "notifications.sqlite3")
    _SIGNAL_EVALUATOR = SignalEvaluator(_NOTIFICATION_STORE, diagnostic_logger=log_event)
    notice_state = _PRODUCT_NOTICE_STORE.record_started(__version__)
    _NOTIFICATION_STORE.upsert_release(__version__, source_revision=f"release:{__version__}")
    if notice_state.get("lastSeenReleaseVersion") == __version__:
        _NOTIFICATION_STORE.mark_release_read(__version__)


if hasattr(gui_hooks, "main_window_did_init"):
    gui_hooks.main_window_did_init.append(_on_main_window_did_init)
    _write_e2e_event("hook_registered", hook="main_window_did_init")
elif not hasattr(gui_hooks, "profile_did_open"):
    _write_e2e_event("error", where="hook_registration", error="No supported startup hook found")

if hasattr(gui_hooks, "profile_did_open"):
    gui_hooks.profile_did_open.append(_on_profile_did_open)
    _write_e2e_event("hook_registered", hook="profile_did_open")

if hasattr(gui_hooks, "profile_will_close"):
    gui_hooks.profile_will_close.append(_stop_runtime_services)

if hasattr(gui_hooks, "main_window_will_close"):
    gui_hooks.main_window_will_close.append(_stop_runtime_services)

_write_e2e_event("import_done")
