"""Anki Study Report add-on.

Minimal read-only UI scaffold for Anki 26.05 / Python 3.13 / PyQt6.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from time import monotonic
import threading
import traceback

from aqt import dialogs, gui_hooks, mw
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
    QMessageBox,
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

from .metrics import collect_action_card_ids, collect_metrics, expand_deck_ids
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
from .stats_cache import StatsCacheManager


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
BROWSER_ACTION_CARD_LIMIT = 500
SECONDS_IN_DAY = 86_400
_REPORT_CACHE: dict[str, object] = {
    "key": None,
    "created_at": 0.0,
    "metrics": None,
}
_DASHBOARD_ACTION_CONTEXT: dict[str, object] = {}
_STUDY_REPORT_DIALOG: StudyReportDialog | None = None
_INTEGRATIONS_DIALOG: IntegrationDiagnosticsDialog | None = None
_WEB_DASHBOARD_DIALOG: WebDashboardSettingsDialog | None = None
_DASHBOARD_SERVER = DashboardServerManager()
_STATS_CACHE = StatsCacheManager()


class _ReportCancelled(Exception):
    """Raised when the user cancels a potentially heavy report."""


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
                answer = QMessageBox.warning(
                    self,
                    ADDON_NAME,
                    (
                        "Найдено больше "
                        f"{BROWSER_ACTION_CARD_LIMIT} карточек. "
                        "Чтобы Anki Browser не завис на огромном поисковом запросе, "
                        f"будут открыты только первые {BROWSER_ACTION_CARD_LIMIT}.\n\n"
                        "Открыть Browser?"
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

            try:
                _open_browser_search(_card_ids_search_query(card_ids))
            except Exception:
                self._show_browser_action_error(traceback.format_exc())

        try:
            mw.taskman.run_in_background(
                lambda: _safe_collect_action_card_ids(
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
                if not _confirm_large_period(self):
                    raise _ReportCancelled()
        except _ReportCancelled:
            showInfo("Расчёт отчёта отменён.", title=ADDON_NAME, parent=self)
            return
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


def _clear_study_report_dialog(_result: int = 0) -> None:
    global _STUDY_REPORT_DIALOG
    _STUDY_REPORT_DIALOG = None


def _clear_integrations_dialog(_result: int = 0) -> None:
    global _INTEGRATIONS_DIALOG
    _INTEGRATIONS_DIALOG = None


def _clear_web_dashboard_dialog(_result: int = 0) -> None:
    global _WEB_DASHBOARD_DIALOG
    _WEB_DASHBOARD_DIALOG = None


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


def _start_web_dashboard_server():
    settings = _web_dashboard_config()
    _configure_dashboard_cache_handlers()
    state = _DASHBOARD_SERVER.start(
        port=int(settings["port"]),
        idle_timeout_seconds=int(settings["idle_timeout_seconds"]),
    )
    if _STUDY_REPORT_DIALOG is not None:
        _STUDY_REPORT_DIALOG._update_dashboard_status()
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
    _DASHBOARD_SERVER.configure_action_handler(_request_dashboard_action)


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


def _clear_report_cache() -> None:
    _REPORT_CACHE["key"] = None
    _REPORT_CACHE["created_at"] = 0.0
    _REPORT_CACHE["metrics"] = None
    _DASHBOARD_ACTION_CONTEXT.clear()
    _DASHBOARD_SERVER.clear_report()


def _publish_dashboard_action_context(
    markdown: str,
    metadata: dict,
    deck_ids: list[int] | None,
) -> None:
    _DASHBOARD_ACTION_CONTEXT.clear()
    _DASHBOARD_ACTION_CONTEXT.update(
        {
            "markdown": markdown,
            "metadata": dict(metadata),
            "start_ts": metadata.get("period_start_ts"),
            "end_ts": metadata.get("period_end_ts"),
            "deck_ids": list(deck_ids) if deck_ids is not None else None,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )


def _request_dashboard_action(action: str, payload: dict) -> dict:
    safe_action = str(action or "").strip()
    if safe_action == "open-browser":
        kind = str(payload.get("kind") or "problematic-decks")
        return _request_dashboard_browser_action(kind)
    if safe_action == "open-problematic":
        return _request_dashboard_browser_action("problematic-decks")
    if safe_action == "open-again":
        return _request_dashboard_browser_action("again")
    if safe_action == "open-new":
        return _request_dashboard_browser_action("new")
    if safe_action == "copy-markdown":
        return _request_dashboard_copy_markdown()
    if safe_action == "save-markdown":
        return _request_dashboard_save_markdown()
    if safe_action == "open-dashboard":
        return _request_dashboard_open_dashboard()
    return _dashboard_action_error(safe_action or "unknown", "Unknown dashboard action.")


def _request_dashboard_copy_markdown() -> dict:
    markdown = _dashboard_context_markdown()
    if markdown is None:
        return _dashboard_no_report_error("copy-markdown")

    def copy() -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            raise RuntimeError("Clipboard is unavailable.")
        clipboard.setText(markdown)

    result = _run_on_anki_main_sync(copy)
    if not result["ok"]:
        return _dashboard_action_error("copy-markdown", result["error"])
    return _dashboard_action_ok("copy-markdown", "Copied Markdown to clipboard.")


def _request_dashboard_save_markdown() -> dict:
    markdown = _dashboard_context_markdown()
    if markdown is None:
        return _dashboard_no_report_error("save-markdown")

    def save() -> str | None:
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

    result = _run_on_anki_main_sync(save, timeout_seconds=120.0)
    if not result["ok"]:
        return _dashboard_action_error("save-markdown", result["error"])
    filename = result.get("value")
    if not filename:
        return _dashboard_action_error("save-markdown", "Save cancelled.")
    return _dashboard_action_ok("save-markdown", f"Saved report to: {filename}")


def _request_dashboard_open_dashboard() -> dict:
    if not _DASHBOARD_ACTION_CONTEXT:
        return _dashboard_no_report_error("open-dashboard")

    def open_url() -> None:
        state = _ensure_web_dashboard_server()
        if not state.url:
            raise RuntimeError("Dashboard server is stopped.")
        QDesktopServices.openUrl(QUrl(state.url))

    result = _run_on_anki_main_sync(open_url)
    if not result["ok"]:
        return _dashboard_action_error("open-dashboard", result["error"])
    return _dashboard_action_ok("open-dashboard", "Opened current report in dashboard.")


def _request_dashboard_browser_action(kind: str) -> dict:
    action_map = {
        "problematic-decks": ("problem_decks", "open-browser", "No problematic decks found for the selected period."),
        "again": ("again", "open-again", "No Again answers found for the selected period."),
        "new": ("new", "open-new", "No new cards found for the selected period."),
    }
    if kind not in action_map:
        return _dashboard_action_error("open-browser", "Unknown browser action kind.")
    action, response_action, empty_message = action_map[kind]
    if not _DASHBOARD_ACTION_CONTEXT:
        return _dashboard_no_report_error(response_action)
    if mw is None or mw.col is None or not hasattr(mw, "taskman"):
        return _dashboard_action_error(response_action, "Anki collection is unavailable.")

    try:
        start_ts = int(_DASHBOARD_ACTION_CONTEXT["start_ts"])
        end_ts = int(_DASHBOARD_ACTION_CONTEXT["end_ts"])
        deck_ids = _DASHBOARD_ACTION_CONTEXT.get("deck_ids")
        deck_ids = deck_ids if isinstance(deck_ids, list) else None
    except Exception:
        return _dashboard_action_error(response_action, "No report is available for the selected period.")

    result = _collect_browser_action_on_background(start_ts, end_ts, deck_ids, action)
    if not result.get("ok"):
        return _dashboard_action_error(response_action, str(result.get("error") or "Browser action failed."))
    card_ids = result.get("card_ids") if isinstance(result.get("card_ids"), list) else []
    if not card_ids:
        return _dashboard_action_ok(response_action, empty_message)

    open_result = _run_on_anki_main_sync(lambda: _open_browser_search(_card_ids_search_query(card_ids)))
    if not open_result["ok"]:
        return _dashboard_action_error(response_action, open_result["error"])
    message = "Opened Anki Browser."
    if result.get("truncated"):
        message = f"Opened Anki Browser with the first {BROWSER_ACTION_CARD_LIMIT} cards."
    return _dashboard_action_ok(response_action, message)


def _collect_browser_action_on_background(
    start_ts: int,
    end_ts: int,
    deck_ids: list[int] | None,
    action: str,
) -> dict:
    event = threading.Event()
    holder: dict[str, object] = {}

    def finish(future) -> None:
        try:
            holder["result"] = future.result()
        except Exception:
            traceback.print_exc()
            holder["result"] = {"ok": False, "error": "Browser action failed."}
        finally:
            event.set()

    def start_background() -> None:
        mw.taskman.run_in_background(
            lambda: _safe_collect_action_card_ids(
                mw.col,
                start_ts,
                end_ts,
                deck_ids,
                action,
                BROWSER_ACTION_CARD_LIMIT,
            ),
            finish,
        )

    schedule_result = _run_on_anki_main_sync(start_background)
    if not schedule_result["ok"]:
        return {"ok": False, "error": schedule_result["error"]}

    if not event.wait(30.0):
        return {"ok": False, "error": "Browser action is still running."}
    result = holder.get("result")
    return result if isinstance(result, dict) else {"ok": False, "error": "Browser action failed."}


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


def _dashboard_context_markdown() -> str | None:
    markdown = _DASHBOARD_ACTION_CONTEXT.get("markdown")
    return markdown if isinstance(markdown, str) and markdown.strip() else None


def _dashboard_no_report_error(action: str) -> dict:
    return _dashboard_action_error(action, "No report is available yet. Build or open a report first.")


def _dashboard_action_ok(action: str, message: str) -> dict:
    return {
        "ok": True,
        "action": action,
        "message": message,
    }


def _dashboard_action_error(action: str, error: str) -> dict:
    safe_error = str(error or "Dashboard action failed.")
    if "Traceback" in safe_error:
        safe_error = "Dashboard action failed."
    return {
        "ok": False,
        "action": action,
        "error": safe_error,
    }


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


def _stop_web_dashboard_server(*_args) -> None:
    _DASHBOARD_SERVER.stop()
    if _WEB_DASHBOARD_DIALOG is not None:
        _WEB_DASHBOARD_DIALOG.refresh_status()
    if _STUDY_REPORT_DIALOG is not None:
        _STUDY_REPORT_DIALOG._update_dashboard_status()


def _maybe_auto_start_web_dashboard() -> None:
    if _web_dashboard_config().get("auto_start"):
        try:
            _start_web_dashboard_server()
        except Exception:
            traceback.print_exc()


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
    total_reviews = _dashboard_int(metrics.get("total_reviews"))
    new_cards = _dashboard_int(metrics.get("new_cards"))
    fail_count = _dashboard_fail_count(metrics)
    pass_count = max(0, _dashboard_int(metrics.get("pass_count")) or total_reviews - fail_count)
    pass_rate = _dashboard_rate(metrics.get("pass_rate"))
    fail_rate = _dashboard_rate(metrics.get("fail_rate"))
    if total_reviews > 0 and fail_rate <= 0:
        fail_rate = round(fail_count / total_reviews, 4)
    total_seconds = _dashboard_int(metrics.get("total_seconds"))
    average_answer_seconds = _dashboard_float(metrics.get("average_answer_seconds"))
    heatmap = metrics.get("heatmap") if isinstance(metrics.get("heatmap"), dict) else {}
    forecast = metrics.get("forecast") if isinstance(metrics.get("forecast"), dict) else {}
    fsrs = metrics.get("fsrs") if isinstance(metrics.get("fsrs"), dict) else {}
    due_forecast = forecast.get("due_forecast") if isinstance(forecast.get("due_forecast"), dict) else {}
    baseline = forecast.get("baseline") if isinstance(forecast.get("baseline"), dict) else {}
    forecast_recommendation = (
        forecast.get("recommendation")
        if isinstance(forecast.get("recommendation"), dict)
        else {}
    )
    risk = str(forecast_recommendation.get("risk") or "low")
    decks = _dashboard_decks(metrics.get("deck_breakdown"))
    problem_decks = [
        deck for deck in decks if deck["status"] in {"danger", "warning"}
    ]
    hardest_deck = problem_decks[0]["name"] if problem_decks else "проблемные колоды не выделены"
    tomorrow = _dashboard_int(due_forecast.get("tomorrow") or metrics.get("due_tomorrow"))
    next_7 = _dashboard_int(due_forecast.get("next_7_days_total"))
    next_30 = _dashboard_int(due_forecast.get("next_30_days_total"))
    risk_status = _dashboard_risk_status(risk)
    quality_status = _dashboard_quality_status(pass_rate, total_reviews)
    fail_status = "danger" if fail_rate >= 0.22 else "warning" if fail_rate >= 0.15 else "good"

    summary_verdict = _dashboard_summary_verdict(
        pass_rate,
        fail_rate,
        tomorrow,
        hardest_deck,
        risk_status,
    )
    main_action = _dashboard_main_action(problem_decks)
    new_cards_advice = _dashboard_new_cards_advice(pass_rate, risk_status)

    report = {
        "metadata": {
            "title": "Anki Study Report",
            "period": str(metadata.get("period") or "Не указан"),
            "selectedDecks": _dashboard_selected_decks(metadata.get("selected_decks")),
            "includeChildren": bool(metadata.get("include_child_decks")),
            "answerMode": (
                "pass_fail"
                if str(metrics.get("answer_mode") or metadata.get("requested_answer_mode")) == "pass_fail"
                else "standard"
            ),
            "createdAt": str(metadata.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M")),
            "detailMode": str(metadata.get("detail_level") or "normal"),
            "deletedCardReviews": _dashboard_deleted_reviews(metrics.get("deck_breakdown")),
            "unavailableTrackerNotes": _dashboard_tracker_notes(metrics),
        },
        "summary": {
            "verdict": summary_verdict,
            "riskLevel": "danger" if quality_status == "danger" else risk_status,
            "mainAction": main_action,
            "warning": _dashboard_warning(fail_rate),
            "newCardsAdvice": new_cards_advice,
        },
        "kpis": _dashboard_kpis(
            total_reviews,
            pass_rate,
            fail_rate,
            new_cards,
            total_seconds,
            average_answer_seconds,
            heatmap,
            tomorrow,
            next_7,
            next_30,
            fsrs,
            quality_status,
            fail_status,
        ),
        "answerDistribution": _dashboard_answer_distribution(metrics),
        "activity": _dashboard_activity(heatmap),
        "comparison": _dashboard_comparison(metrics.get("comparison")),
        "decks": decks,
        "forecast": _dashboard_forecast(forecast, tomorrow, next_7, next_30, baseline, risk_status),
        "fsrs": _dashboard_fsrs(fsrs, next_30),
        "recommendations": {
            "mainAction": main_action,
            "why": _dashboard_recommendation_why(problem_decks, tomorrow),
            "avoid": _dashboard_recommendation_avoid(pass_rate, risk_status),
            "checklist": _dashboard_checklist(problem_decks, pass_rate),
        },
        "cache": _dashboard_cache_summary(),
    }
    cache_parts = build_cached_report_parts(
        _STATS_CACHE,
        str(metadata.get("period_id") or ""),
        {
            **_read_config(),
            "period_start_ts": metadata.get("period_start_ts"),
            "period_end_ts": metadata.get("period_end_ts"),
            "period_start_date": metadata.get("period_start_date"),
            "period_end_date": metadata.get("period_end_date"),
            "today_date": metadata.get("today_date"),
        },
        legacy_report={"metrics": metrics, "payload": report},
    )
    return merge_cached_report_parts(report, cache_parts)


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


def _dashboard_kpis(
    total_reviews: int,
    pass_rate: float,
    fail_rate: float,
    new_cards: int,
    total_seconds: int,
    average_answer_seconds: float,
    heatmap: dict,
    tomorrow: int,
    next_7: int,
    next_30: int,
    fsrs: dict,
    quality_status: str,
    fail_status: str,
) -> list[dict]:
    fsrs_memory = fsrs.get("memory_state") if isinstance(fsrs.get("memory_state"), dict) else {}
    predicted_recall = _dashboard_optional_rate(fsrs_memory.get("average_recall"))
    return [
        _dashboard_kpi("total_reviews", "Total reviews", _dashboard_format_int(total_reviews), "за выбранный период", "good", "layers"),
        _dashboard_kpi("pass_rate", "Pass rate", _dashboard_format_percent(pass_rate), "качество ответов", quality_status, "check"),
        _dashboard_kpi("fail_rate", "Fail rate", _dashboard_format_percent(fail_rate), "ошибки за период", fail_status, "alert"),
        _dashboard_kpi("new_cards", "New cards", _dashboard_format_int(new_cards), "новые карточки", "warning" if new_cards >= 50 else "neutral", "sparkles"),
        _dashboard_kpi("study_time", "Study time", _dashboard_format_duration(total_seconds), "оценка по revlog", "neutral", "clock"),
        _dashboard_kpi("average_answer_time", "Average answer time", _dashboard_format_seconds(average_answer_seconds), "средний ответ", "good", "timer"),
        _dashboard_kpi("active_days", "Active days", _dashboard_format_int(_dashboard_int(heatmap.get("active_days"))), "дни с повторениями", "good", "calendar"),
        _dashboard_kpi("missed_days", "Missed days", _dashboard_format_int(_dashboard_int(heatmap.get("missed_days"))), "дни без повторений", "neutral", "pause"),
        _dashboard_kpi("current_streak", "Current streak", f"{_dashboard_int(heatmap.get('current_streak'))} дней", "текущая серия", "good", "flame"),
        _dashboard_kpi("best_streak", "Best streak", f"{_dashboard_int(heatmap.get('longest_streak'))} дней", "лучшая серия", "good", "trophy"),
        _dashboard_kpi("tomorrow_due", "Tomorrow due", _dashboard_format_int(tomorrow), "очередь на завтра", "warning" if tomorrow >= 100 else "good", "sun"),
        _dashboard_kpi("forecast_7", "7-day forecast", _dashboard_format_int(next_7), "следующие 7 дней", "neutral", "line"),
        _dashboard_kpi("forecast_30", "30-day forecast", _dashboard_format_int(next_30), "следующие 30 дней", "neutral", "bar"),
        _dashboard_kpi("fsrs_predicted_recall", "FSRS predicted recall", _dashboard_format_percent(predicted_recall) if predicted_recall is not None else "Нет данных", "average recall", "warning" if predicted_recall is not None and predicted_recall < 0.9 else "neutral", "brain"),
    ]


def _dashboard_kpi(
    metric_id: str,
    label: str,
    value: str,
    caption: str,
    status: str,
    icon: str,
) -> dict:
    return {
        "id": metric_id,
        "label": label,
        "value": value,
        "caption": caption,
        "status": _dashboard_status(status),
        "icon": icon,
    }


def _dashboard_answer_distribution(metrics: dict) -> list[dict]:
    distribution = (
        metrics.get("answer_distribution")
        if isinstance(metrics.get("answer_distribution"), dict)
        else {}
    )
    pass_fail = (
        metrics.get("pass_fail") if isinstance(metrics.get("pass_fail"), dict) else {}
    )
    return [
        {"label": "Pass", "value": _dashboard_int(pass_fail.get("pass_count") or distribution.get("good")), "color": "#67d391"},
        {"label": "Fail", "value": _dashboard_int(pass_fail.get("fail_count") or distribution.get("again")), "color": "#ef6f6c"},
        {"label": "Hard", "value": _dashboard_int(distribution.get("hard")), "color": "#f6c177"},
        {"label": "Easy", "value": _dashboard_int(distribution.get("easy")), "color": "#3db4f2"},
    ]


def _dashboard_activity(heatmap: dict) -> dict:
    days = [
        {
            "date": str(day.get("date") or ""),
            "reviews": _dashboard_int(day.get("reviews")),
            "newCards": _dashboard_int(day.get("new_cards")),
            "again": _dashboard_int(day.get("again")),
            "studySeconds": _dashboard_int(day.get("total_seconds")),
        }
        for day in _dashboard_list(heatmap.get("reviews_by_day"))
    ]
    best_days = _dashboard_list(heatmap.get("best_days"))
    best_day = "Нет данных"
    if best_days:
        best = best_days[0]
        best_day = f"{best.get('date')}, {_dashboard_int(best.get('reviews'))} reviews"
    weekday_average = heatmap.get("weekday_average")
    if not isinstance(weekday_average, dict):
        weekday_average = {}
    return {
        "available": bool(heatmap.get("available")),
        "activeDays": _dashboard_int(heatmap.get("active_days")),
        "missedDays": _dashboard_int(heatmap.get("missed_days")),
        "currentStreak": _dashboard_int(heatmap.get("current_streak")),
        "bestStreak": _dashboard_int(heatmap.get("longest_streak")),
        "bestDay": best_day,
        "weekdayAverage": [
            {
                "day": _dashboard_short_day(day),
                "reviews": _dashboard_float(value),
                "activeRate": 0,
            }
            for day, value in weekday_average.items()
        ],
        "days": days,
    }


def _dashboard_comparison(comparison: object) -> dict:
    data = comparison if isinstance(comparison, dict) else {}
    baselines = data.get("baselines") if isinstance(data.get("baselines"), dict) else {}
    comparisons = data.get("comparisons") if isinstance(data.get("comparisons"), dict) else {}
    return {
        "available": bool(data.get("available")),
        "message": str(
            data.get("message")
            or "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы."
        ),
        "today": _dashboard_comparison_stats(data.get("today"), "Сегодня"),
        "baselines": {
            "yesterday": _dashboard_comparison_stats(baselines.get("yesterday"), "Вчера"),
            "avg7": _dashboard_comparison_stats(baselines.get("avg7"), "Последние 7 дней"),
            "avg30": _dashboard_comparison_stats(baselines.get("avg30"), "Последние 30 дней"),
            "sameWeekdayLastWeek": _dashboard_comparison_stats(
                baselines.get("sameWeekdayLastWeek"),
                "Этот день прошлой недели",
            ),
            "currentWeek": _dashboard_comparison_stats(baselines.get("currentWeek"), "Эта неделя"),
            "previousWeek": _dashboard_comparison_stats(baselines.get("previousWeek"), "Прошлая неделя"),
            "currentMonth": _dashboard_comparison_stats(baselines.get("currentMonth"), "Этот месяц"),
            "previousMonth": _dashboard_comparison_stats(baselines.get("previousMonth"), "Прошлый месяц"),
        },
        "comparisons": {
            "yesterday": _dashboard_comparison_delta(comparisons.get("yesterday")),
            "avg7": _dashboard_comparison_delta(comparisons.get("avg7")),
            "avg30": _dashboard_comparison_delta(comparisons.get("avg30")),
            "sameWeekdayLastWeek": _dashboard_comparison_delta(comparisons.get("sameWeekdayLastWeek")),
            "week": _dashboard_comparison_delta(comparisons.get("week")),
            "month": _dashboard_comparison_delta(comparisons.get("month")),
        },
        "insights": _dashboard_comparison_insights(data.get("insights")),
        "source": data.get("source") if isinstance(data.get("source"), dict) else {},
    }


def _dashboard_comparison_stats(value: object, fallback_label: str) -> dict:
    item = value if isinstance(value, dict) else {}
    return {
        "date": str(item.get("date") or ""),
        "label": str(item.get("label") or fallback_label),
        "reviews": _dashboard_int(item.get("reviews")),
        "newCards": _dashboard_int(item.get("newCards")),
        "pass": _dashboard_int(item.get("pass")),
        "fail": _dashboard_int(item.get("fail")),
        "hard": _dashboard_int(item.get("hard")),
        "easy": _dashboard_int(item.get("easy")),
        "studySeconds": _dashboard_int(item.get("studySeconds")),
        "studyMinutes": _dashboard_int(item.get("studyMinutes")),
        "avgAnswerSeconds": _dashboard_optional_float(item.get("avgAnswerSeconds")),
        "activeDecks": _dashboard_int(item.get("activeDecks")),
        "passRate": _dashboard_optional_rate(item.get("passRate")),
        "failRate": _dashboard_optional_rate(item.get("failRate")),
    }


def _dashboard_comparison_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {
        "reviews": _dashboard_metric_delta(data.get("reviews")),
        "newCards": _dashboard_metric_delta(data.get("newCards")),
        "studyMinutes": _dashboard_metric_delta(data.get("studyMinutes")),
        "passRate": _dashboard_rate_delta(data.get("passRate")),
        "failRate": _dashboard_rate_delta(data.get("failRate")),
        "avgAnswerSeconds": _dashboard_metric_delta(data.get("avgAnswerSeconds")),
        "activeDecks": _dashboard_metric_delta(data.get("activeDecks")),
    }


def _dashboard_metric_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {
        "delta": _dashboard_optional_float(data.get("delta")),
        "percentDelta": _dashboard_optional_float(data.get("percentDelta")),
    }


def _dashboard_rate_delta(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    return {"deltaPp": _dashboard_optional_float(data.get("deltaPp"))}


def _dashboard_comparison_insights(value: object) -> list[dict]:
    insights = []
    for item in _dashboard_list(value):
        severity = str(item.get("severity") or "neutral")
        if severity not in {"positive", "neutral", "warning", "danger"}:
            severity = "neutral"
        insights.append(
            {
                "severity": severity,
                "title": str(item.get("title") or "Сравнение"),
                "text": str(item.get("text") or ""),
                "metric": str(item.get("metric") or ""),
            }
        )
    return insights


def _dashboard_decks(deck_breakdown) -> list[dict]:
    decks = []
    for index, deck in enumerate(_dashboard_list(deck_breakdown), start=1):
        total = _dashboard_int(deck.get("total_reviews"))
        fail = _dashboard_int(deck.get("fail_count") or deck.get("again_count"))
        pass_count = _dashboard_int(deck.get("pass_count")) or max(0, total - fail)
        pass_rate = _dashboard_rate(deck.get("pass_rate"))
        average_answer_seconds = _dashboard_float(deck.get("average_answer_seconds"))
        status = _dashboard_deck_status(pass_rate, total, fail)
        decks.append(
            {
                "id": _dashboard_int(deck.get("deck_id")) or index,
                "name": str(deck.get("deck_name") or f"Колода {index}"),
                "totalReviews": total,
                "newCards": _dashboard_int(deck.get("new_cards")),
                "passCount": pass_count,
                "failCount": fail,
                "hardCount": _dashboard_int(deck.get("hard_count")),
                "easyCount": _dashboard_int(deck.get("easy_count")),
                "passRate": pass_rate,
                "failRate": _dashboard_rate(deck.get("fail_rate")),
                "averageAnswerSeconds": average_answer_seconds,
                "studyMinutes": round(_dashboard_int(deck.get("total_seconds")) / 60),
                "status": status,
                "explanation": _dashboard_deck_explanation(status, fail, average_answer_seconds),
            }
        )
    return decks


def _dashboard_forecast(
    forecast: dict,
    tomorrow: int,
    next_7: int,
    next_30: int,
    baseline: dict,
    risk_status: str,
) -> dict:
    due_forecast = forecast.get("due_forecast") if isinstance(forecast.get("due_forecast"), dict) else {}
    recommendation = (
        forecast.get("recommendation")
        if isinstance(forecast.get("recommendation"), dict)
        else {}
    )
    daily = []
    for item in _dashboard_list(due_forecast.get("daily")):
        daily.append(
            {
                "offset": _dashboard_int(item.get("offset")),
                "date": str(item.get("date") or item.get("offset") or ""),
                "due": _dashboard_int(item.get("due")),
                "reviewDue": _dashboard_int(item.get("review_due")),
                "learningDue": _dashboard_int(item.get("learning_due")),
                "risk": str(item.get("risk") or "low"),
            }
        )
    return {
        "available": bool(forecast.get("available")),
        "tomorrow": tomorrow,
        "next7Days": next_7,
        "next30Days": next_30,
        "activeDayBaseline": _dashboard_float(baseline.get("median_reviews_active_day")),
        "overloadRisk": risk_status,
        "daily": daily,
        "recommendation": str(recommendation.get("new_cards_advice") or recommendation.get("summary") or "Прогноз пока недоступен."),
    }


def _dashboard_fsrs(fsrs: dict, fallback_future_load: int) -> dict:
    memory = fsrs.get("memory_state") if isinstance(fsrs.get("memory_state"), dict) else {}
    future = fsrs.get("future_load") if isinstance(fsrs.get("future_load"), dict) else {}
    source = fsrs.get("source") if isinstance(fsrs.get("source"), dict) else {}
    settings = _dashboard_fsrs_settings(fsrs)
    return {
        "predictedRecall": _dashboard_optional_rate(memory.get("average_recall")),
        "cardsBelowTarget": _dashboard_int(memory.get("below_90_count")),
        "highForgettingRisk": _dashboard_int(memory.get("high_risk_count")),
        "averageDifficulty": _dashboard_optional_float(memory.get("average_difficulty")),
        "futureLoad30Days": _dashboard_int(future.get("next_30_days") or fallback_future_load),
        "settings": {
            "enabled": bool(fsrs.get("enabled")),
            "desiredRetention": settings.get("desiredRetention"),
            "helperDetected": bool(source.get("helper_detected")),
            "helperConfigAvailable": bool(source.get("helper_config_available")),
            "rescheduleEnabled": bool(settings.get("rescheduleEnabled")),
            "autoDisperse": bool(settings.get("autoDisperse")),
        },
    }


def _dashboard_fsrs_settings(fsrs: dict) -> dict:
    deck_settings = _dashboard_list(fsrs.get("deck_settings"))
    desired = None
    for item in deck_settings:
        desired = _dashboard_optional_rate(item.get("desired_retention"))
        if desired is not None:
            break
    return {
        "desiredRetention": desired,
        "rescheduleEnabled": False,
        "autoDisperse": False,
    }


def _dashboard_selected_decks(value) -> list[str]:
    text = str(value or "Не указаны")
    if not text:
        return ["Не указаны"]
    return [part.strip() for part in text.split(",") if part.strip()] or [text]


def _dashboard_tracker_notes(metrics: dict) -> list[str]:
    notes = []
    real_time = metrics.get("real_study_time")
    if isinstance(real_time, dict) and not real_time.get("available"):
        notes.append(str(real_time.get("explanation") or "Real study time недоступен."))
    return notes


def _dashboard_deleted_reviews(deck_breakdown) -> int:
    total = 0
    for deck in _dashboard_list(deck_breakdown):
        name = str(deck.get("deck_name") or "").lower()
        if "удал" in name or "deleted" in name:
            total += _dashboard_int(deck.get("total_reviews"))
    return total


def _dashboard_summary_verdict(
    pass_rate: float,
    fail_rate: float,
    tomorrow: int,
    hardest_deck: str,
    risk_status: str,
) -> str:
    quality = "хорошее" if pass_rate >= 0.85 else "ошибок много" if fail_rate >= 0.2 else "качество среднее"
    load = "ближайшая очередь лёгкая" if tomorrow < 60 else "нагрузка заметная"
    action = f"Сначала разобрать {hardest_deck}" if hardest_deck != "проблемные колоды не выделены" else "Продолжать обычный темп"
    if risk_status == "danger":
        load = "есть риск перегруза"
    return f"Pass rate {_dashboard_format_percent(pass_rate)}: {quality}, {load}. {action}."


def _dashboard_main_action(problem_decks: list[dict]) -> str:
    if not problem_decks:
        return "Поддержать серию и продолжать обычный темп повторений."
    names = [deck["name"] for deck in problem_decks[:2]]
    return "Разобрать " + " и ".join(names) + "."


def _dashboard_new_cards_advice(pass_rate: float, risk_status: str) -> str:
    if pass_rate < 0.8 or risk_status in {"warning", "danger"}:
        return "Новые карточки лучше временно снизить и вернуть после стабилизации качества."
    return "Новые можно добавлять умеренно, если очередь остаётся комфортной."


def _dashboard_warning(fail_rate: float) -> str:
    if fail_rate >= 0.2:
        return f"Fail rate {_dashboard_format_percent(fail_rate)} выше комфортного уровня."
    return "Критичного fail rate не видно."


def _dashboard_recommendation_why(problem_decks: list[dict], tomorrow: int) -> str:
    if problem_decks:
        return "Эти колоды дают основную часть ошибок; текущая очередь позволяет сначала поднять качество."
    if tomorrow > 0:
        return "Очередь на завтра есть, но явных проблемных колод за период не видно."
    return "На завтра заметной due-нагрузки не видно."


def _dashboard_recommendation_avoid(pass_rate: float, risk_status: str) -> str:
    if pass_rate < 0.8 or risk_status in {"warning", "danger"}:
        return "Пока не повышать лимит новых и не открывать тяжёлые уроки."
    return "Не разгонять новые карточки резко; держать стабильный темп."


def _dashboard_checklist(problem_decks: list[dict], pass_rate: float) -> list[str]:
    items = [f"Разобрать {deck['name']}." for deck in problem_decks[:3]]
    if pass_rate < 0.8:
        items.append("Временно снизить новые карточки.")
        items.append("Вернуть новые после стабилизации pass rate.")
    if not items:
        items.append("Сделать обычную короткую сессию повторений.")
    return items


def _dashboard_deck_status(pass_rate: float, total: int, fail_count: int) -> str:
    if total <= 0:
        return "neutral"
    if pass_rate < 0.7 or fail_count >= 30:
        return "danger"
    if pass_rate < 0.82 or fail_count >= 15:
        return "warning"
    if pass_rate >= 0.88:
        return "good"
    return "neutral"


def _dashboard_deck_explanation(status: str, fail_count: int, average_answer_seconds: float) -> str:
    if status == "danger":
        return "много Fail, лучше разобрать до новых карточек"
    if status == "warning":
        return "ошибки заметны, нагрузку лучше не повышать"
    if average_answer_seconds >= 15:
        return "ответы медленные, стоит проверить сложные карточки"
    if fail_count <= 5:
        return "ошибки редкие, можно продолжать обычный темп"
    return "стабильная колода без явного риска"


def _dashboard_quality_status(pass_rate: float, total_reviews: int) -> str:
    if total_reviews <= 0:
        return "neutral"
    if pass_rate >= 0.88:
        return "good"
    if pass_rate >= 0.8:
        return "warning"
    return "danger"


def _dashboard_risk_status(risk: str) -> str:
    if risk == "high":
        return "danger"
    if risk == "medium":
        return "warning"
    if risk == "low":
        return "good"
    return "neutral"


def _dashboard_status(value: str) -> str:
    return value if value in {"good", "neutral", "warning", "danger"} else "neutral"


def _dashboard_fail_count(metrics: dict) -> int:
    pass_fail = metrics.get("pass_fail") if isinstance(metrics.get("pass_fail"), dict) else {}
    return _dashboard_int(metrics.get("fail_count") or pass_fail.get("fail_count") or metrics.get("again_count"))


def _dashboard_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dashboard_short_day(value) -> str:
    return {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }.get(str(value), str(value)[:3])


def _dashboard_rate(value) -> float:
    number = _dashboard_float(value)
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def _dashboard_optional_rate(value) -> float | None:
    if value is None:
        return None
    return _dashboard_rate(value)


def _dashboard_optional_float(value) -> float | None:
    if value is None:
        return None
    return _dashboard_float(value)


def _dashboard_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dashboard_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _dashboard_format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _dashboard_format_percent(value: float) -> str:
    return f"{round(_dashboard_rate(value) * 100)}%"


def _dashboard_format_duration(seconds: int) -> str:
    minutes = round(max(0, seconds) / 60)
    if minutes <= 0:
        return "0 мин"
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} ч {rest} мин"
    if hours:
        return f"{hours} ч"
    return f"{minutes} мин"


def _dashboard_format_seconds(seconds: float) -> str:
    if seconds <= 0:
        return "0 сек"
    if seconds >= 60:
        return _dashboard_format_duration(round(seconds))
    if float(seconds).is_integer():
        return f"{int(seconds)} сек"
    return f"{seconds:.1f} сек"


def _idle_timeout_label(seconds: int) -> str:
    if seconds <= 0:
        return "выключено"
    minutes = round(seconds / 60)
    if minutes >= 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} ч {rest} мин" if rest else f"{hours} ч"
    return f"{minutes} мин"


def _config_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _integration_diagnostics_text() -> str:
    diagnostics = _integration_diagnostics_sections()
    sections = ["Anki Study Report: диагностика интеграций"]
    for title, text in (
        ("Study Time Stats", diagnostics["study_time_stats"]),
        ("Трекер повторений", diagnostics["session_tracker"]),
        ("Heatmap", diagnostics["heatmap"]),
        ("Логи", diagnostics["logs"]),
    ):
        sections.extend(("", title, text))
    return "\n".join(sections)


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


def _read_config() -> dict:
    try:
        config = mw.addonManager.getConfig(__name__) if mw else None
    except Exception:
        config = None
    return dict(config or {})


def _write_config(config: dict) -> None:
    if mw is None:
        return
    try:
        mw.addonManager.writeConfig(__name__, config)
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


def _safe_collect_action_card_ids(
    col,
    start_ts: int,
    end_ts: int,
    deck_ids: list[int] | None,
    action: str,
    limit: int,
) -> dict:
    try:
        card_ids = collect_action_card_ids(
            col,
            start_ts,
            end_ts,
            deck_ids=deck_ids,
            action=action,
            max_results=limit + 1,
        )
        truncated = len(card_ids) > limit
        return {
            "ok": True,
            "card_ids": card_ids[:limit],
            "truncated": truncated,
        }
    except Exception:
        return {
            "ok": False,
            "error": traceback.format_exc(),
        }


def _card_ids_search_query(card_ids: list[int]) -> str:
    return _balanced_or_search_query([f"cid:{int(card_id)}" for card_id in card_ids])


def _balanced_or_search_query(terms: list[str]) -> str:
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]

    midpoint = len(terms) // 2
    left = _balanced_or_search_query(terms[:midpoint])
    right = _balanced_or_search_query(terms[midpoint:])
    return f"({left} OR {right})"


def _open_browser_search(search_query: str) -> None:
    if mw is None:
        raise RuntimeError("Главное окно Anki недоступно.")

    browser = dialogs.open("Browser", mw)
    if hasattr(browser, "search_for"):
        browser.search_for(search_query)
        return

    search_edit = getattr(getattr(browser, "form", None), "searchEdit", None)
    if search_edit is not None:
        if hasattr(search_edit, "lineEdit"):
            search_edit.lineEdit().setText(search_query)
        elif hasattr(search_edit, "setText"):
            search_edit.setText(search_query)

    if hasattr(browser, "onSearchActivated"):
        browser.onSearchActivated()
    elif hasattr(browser, "search"):
        browser.search()
    elif hasattr(browser, "onSearch"):
        browser.onSearch()


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


def _last_report_ts(config: dict) -> int | None:
    try:
        value = int(config.get("last_report_ts") or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


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


def _enabled_metrics_from_config(config: dict) -> dict[str, bool]:
    configured = config.get("enabled_metrics")
    if not isinstance(configured, dict):
        configured = {}

    return {
        metric: bool(configured.get(metric, DEFAULT_ENABLED_METRICS[metric]))
        for metric in METRIC_KEYS
    }


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


def _confirm_large_period(parent: QWidget) -> bool:
    result = QMessageBox.warning(
        parent,
        ADDON_NAME,
        "Выбран большой период. Расчёт может занять заметное время.\n\n"
        "Продолжить?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


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
    """Register Tools -> Study Report using Anki's modern Qt action API."""

    if main_window is None:
        return

    action = QAction("Study Report", main_window)
    action.triggered.connect(_open_study_report_dialog)
    main_window.form.menuTools.addAction(action)

    integrations_action = QAction("Study Report: интеграции", main_window)
    integrations_action.triggered.connect(_open_integrations_dialog)
    main_window.form.menuTools.addAction(integrations_action)

    setup_session_tracking(gui_hooks, mw)
    _maybe_auto_start_web_dashboard()


gui_hooks.main_window_did_init.append(lambda: _setup_menu(mw))

if hasattr(gui_hooks, "profile_will_close"):
    gui_hooks.profile_will_close.append(_stop_web_dashboard_server)

if hasattr(gui_hooks, "main_window_will_close"):
    gui_hooks.main_window_will_close.append(_stop_web_dashboard_server)
