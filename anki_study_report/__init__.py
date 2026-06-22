"""Anki Study Report add-on.

Minimal read-only UI scaffold for Anki 26.05 / Python 3.13 / PyQt6.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from time import monotonic
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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showCritical, showInfo

from .metrics import collect_action_card_ids, collect_metrics, expand_deck_ids
from .report_builder import build_markdown_report, render_html_report
from .study_time_integration import (
    collect_real_study_time,
    diagnose_study_time_stats,
    integration_log_text,
    unavailable_study_time,
)


ADDON_NAME = "Anki Study Report"
SCOPE_ALL = "all"
SCOPE_CURRENT = "current"
SCOPE_SELECTED = "selected"
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
]
DEFAULT_ENABLED_METRICS = {metric: True for metric in METRIC_KEYS}
PROFILES = [
    (
        "daily_control",
        "Ежедневный контроль",
        {
            "period": "today",
            "scope": SCOPE_ALL,
            "selected_deck_ids": [],
            "include_child_decks": True,
            "enabled_metrics": DEFAULT_ENABLED_METRICS,
        },
    ),
    (
        "japanese",
        "Японский",
        {
            "period": "today",
            "scope": SCOPE_SELECTED,
            "selected_deck_ids": [],
            "include_child_decks": True,
            "enabled_metrics": DEFAULT_ENABLED_METRICS,
            "deck_name_keywords": ["япон", "japanese", "日本"],
        },
    ),
    (
        "before_new",
        "Перед новыми",
        {
            "period": "today",
            "scope": SCOPE_CURRENT,
            "selected_deck_ids": [],
            "include_child_decks": True,
            "enabled_metrics": DEFAULT_ENABLED_METRICS,
        },
    ),
    (
        "problem_decks",
        "Проблемные колоды",
        {
            "period": "last_7_days",
            "scope": SCOPE_ALL,
            "selected_deck_ids": [],
            "include_child_decks": True,
            "enabled_metrics": DEFAULT_ENABLED_METRICS,
        },
    ),
    (
        "weekly_summary",
        "Недельный итог",
        {
            "period": "last_7_days",
            "scope": SCOPE_ALL,
            "selected_deck_ids": [],
            "include_child_decks": True,
            "enabled_metrics": DEFAULT_ENABLED_METRICS,
        },
    ),
]
PROFILE_SETTINGS = {profile_id: settings for profile_id, _label, settings in PROFILES}
REPORT_CACHE_TTL_SECONDS = 5
LARGE_PERIOD_WARNING_DAYS = 180
_REPORT_CACHE: dict[str, object] = {
    "key": None,
    "created_at": 0.0,
    "metrics": None,
}
_STUDY_REPORT_DIALOG: StudyReportDialog | None = None
_INTEGRATIONS_DIALOG: IntegrationDiagnosticsDialog | None = None


class _ReportCancelled(Exception):
    """Raised when the user cancels a potentially heavy report."""


class StudyReportDialog(QDialog):
    """Small placeholder dialog for future read-only study reports."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = _read_config()
        self._deck_items: list[QListWidgetItem] = []
        self._enabled_metrics = _enabled_metrics_from_config(self._config)

        self.setWindowTitle(ADDON_NAME)
        self.setMinimumSize(760, 560)

        title = QLabel("Anki Study Report")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        profile_label = QLabel("Профиль:")
        self.profile_combo = QComboBox()
        for profile_id, label, _settings in PROFILES:
            self.profile_combo.addItem(label, profile_id)
        self._restore_profile()

        profile_row = QHBoxLayout()
        profile_row.addWidget(profile_label)
        profile_row.addWidget(self.profile_combo, 1)

        detail_label = QLabel("Детализация:")
        self.detail_combo = QComboBox()
        for detail_id, label in DETAIL_LEVELS:
            self.detail_combo.addItem(label, detail_id)
        self._restore_detail_level()

        detail_row = QHBoxLayout()
        detail_row.addWidget(detail_label)
        detail_row.addWidget(self.detail_combo, 1)

        period_label = QLabel("Период:")
        self.period_combo = QComboBox()
        for period_id, label in PERIODS:
            self.period_combo.addItem(label, period_id)
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
        self._restore_scope()
        self.scope_combo.currentIndexChanged.connect(self._update_deck_list_state)

        scope_row = QHBoxLayout()
        scope_row.addWidget(scope_label)
        scope_row.addWidget(self.scope_combo, 1)

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

        self.show_button = QPushButton("Показать отчёт")
        self.copy_markdown_button = QPushButton("Скопировать Markdown")
        self.save_markdown_button = QPushButton("Сохранить .md")
        self.open_problem_decks_button = QPushButton("Открыть проблемные колоды")
        self.open_again_button = QPushButton("Открыть Again за период")
        self.open_new_button = QPushButton("Открыть новые за период")
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self._save_and_close)
        self.show_button.clicked.connect(self._show_report)
        self.copy_markdown_button.clicked.connect(self._copy_markdown)
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
        layout.addLayout(period_row)
        layout.addLayout(scope_row)
        layout.addWidget(self.include_child_decks)
        layout.addWidget(self.deck_list, 1)
        layout.addWidget(self.report_text, 3)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self._update_period_controls_state()
        self._update_deck_list_state()
        self.profile_combo.currentIndexChanged.connect(self._apply_selected_profile)

    def closeEvent(self, event) -> None:
        self._save_config()
        super().closeEvent(event)

    def selected_scope(self) -> str:
        return str(self.scope_combo.currentData() or SCOPE_ALL)

    def selected_period(self) -> str:
        return str(self.period_combo.currentData() or "today")

    def selected_profile(self) -> str:
        return str(self.profile_combo.currentData() or "daily_control")

    def selected_detail_level(self) -> str:
        detail_level = str(self.detail_combo.currentData() or "normal")
        if detail_level not in {"compact", "normal", "full"}:
            return "normal"
        return detail_level

    def selected_custom_period(self) -> tuple[str, str]:
        return (
            self.custom_start_date.date().toString("yyyy-MM-dd"),
            self.custom_end_date.date().toString("yyyy-MM-dd"),
        )

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
        profile = str(self._config.get("selected_profile", "daily_control"))
        index = self.profile_combo.findData(profile)
        if index < 0:
            index = self.profile_combo.findData("daily_control")
        self.profile_combo.setCurrentIndex(index)

    def _restore_detail_level(self) -> None:
        detail_level = str(self._config.get("report_detail_level", "normal"))
        index = self.detail_combo.findData(detail_level)
        if index < 0:
            index = self.detail_combo.findData("normal")
        self.detail_combo.setCurrentIndex(index)

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
        settings = PROFILE_SETTINGS.get(self.selected_profile())
        if not settings:
            return

        self._apply_profile_settings(settings)

    def _apply_profile_settings(self, settings: dict) -> None:
        period = str(settings.get("period", "today"))
        period_index = self.period_combo.findData(period)
        if period_index >= 0:
            self.period_combo.setCurrentIndex(period_index)

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
        self._update_period_controls_state()
        self._update_deck_list_state()

    def _update_period_controls_state(self) -> None:
        enabled = self.selected_period() == "custom"
        self.custom_start_label.setVisible(enabled)
        self.custom_start_date.setVisible(enabled)
        self.custom_end_label.setVisible(enabled)
        self.custom_end_date.setVisible(enabled)

    def _save_and_close(self) -> None:
        self._save_config()
        self.close()

    def _save_config(self) -> None:
        config = _read_config()
        config["selected_profile"] = self.selected_profile()
        config["report_detail_level"] = self.selected_detail_level()
        config["default_period"] = self.selected_period()
        custom_start_date, custom_end_date = self.selected_custom_period()
        config["custom_start_date"] = custom_start_date
        config["custom_end_date"] = custom_end_date
        config["report_scope"] = self.selected_scope()
        config["selected_deck_ids"] = self.selected_deck_ids()
        config["include_child_decks"] = self.include_child_decks.isChecked()
        config["enabled_metrics"] = dict(self._enabled_metrics)
        _write_config(config)

    def _show_report(self) -> None:
        def on_success(metrics: dict) -> None:
            self.report_text.setHtml(render_html_report(metrics, self._report_metadata()))
            showInfo("Отчёт готов.", title=ADDON_NAME, parent=self)

        self._run_metrics(on_success, "Не удалось построить отчёт.")

    def _copy_markdown(self) -> None:
        def on_success(metrics: dict) -> None:
            markdown = build_markdown_report(metrics, self._report_metadata())
            QApplication.clipboard().setText(markdown)
            self._remember_last_report()
            showInfo("Markdown-отчёт скопирован в буфер обмена.", title=ADDON_NAME, parent=self)

        self._run_metrics(on_success, "Не удалось скопировать Markdown-отчёт.")

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
            card_ids = collect_action_card_ids(
                mw.col,
                start_ts,
                end_ts,
                deck_ids=deck_ids,
                action=action,
            )
            if not card_ids:
                showInfo(empty_message, title=ADDON_NAME, parent=self)
                return

            _open_browser_search(_card_ids_search_query(card_ids))
        except Exception:
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
                    request["use_study_time_stats"],
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
        use_study_time_stats = bool(self._config.get("use_study_time_stats", True))
        return {
            "start_ts": start_ts,
            "end_ts": end_ts,
            "deck_ids": deck_ids,
            "cache_key": (cache_key, use_study_time_stats),
            "use_study_time_stats": use_study_time_stats,
        }

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
        return {
            "period": self._period_label_for_report(),
            "period_id": self.selected_period(),
            "period_human": self._period_human_label(),
            "scope": self._scope_label_for_report(),
            "selected_decks": self._selected_deck_names_for_report(),
            "include_child_decks": self.include_child_decks.isChecked(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "detail_level": self.selected_detail_level(),
        }

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
        self.setMinimumSize(760, 520)

        title = QLabel("Проверка интеграций")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(360)
        self.log_text.setPlaceholderText("Здесь появится диагностика интеграций.")

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
        layout.addWidget(self.log_text, 1)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        try:
            diagnostics = _integration_diagnostics_text()
            self.log_text.setPlainText(diagnostics)
        except Exception:
            traceback.print_exc()
            self.log_text.setPlainText(
                "Не удалось собрать диагностику интеграций.\n\n"
                "Подробности напечатаны в консоль Anki."
            )

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.log_text.toPlainText())
        showInfo("Лог интеграций скопирован в буфер обмена.", title=ADDON_NAME, parent=self)


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


def _clear_study_report_dialog(_result: int = 0) -> None:
    global _STUDY_REPORT_DIALOG
    _STUDY_REPORT_DIALOG = None


def _clear_integrations_dialog(_result: int = 0) -> None:
    global _INTEGRATIONS_DIALOG
    _INTEGRATIONS_DIALOG = None


def _integration_diagnostics_text() -> str:
    sections = [
        "Anki Study Report: диагностика интеграций",
        "",
        diagnose_study_time_stats(mw.col if mw and mw.col else None),
        "",
        "Лог интеграций",
        integration_log_text(),
    ]
    return "\n".join(sections)


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


def _safe_collect_metrics(
    col,
    start_ts: int,
    end_ts: int,
    deck_ids: list[int] | None,
    use_study_time_stats: bool,
) -> dict:
    try:
        metrics = collect_metrics(
            col,
            start_ts,
            end_ts,
            deck_ids=deck_ids,
        )
        if use_study_time_stats:
            metrics["real_study_time"] = collect_real_study_time(
                col,
                start_ts,
                end_ts,
                deck_ids=deck_ids,
            )
        else:
            metrics["real_study_time"] = unavailable_study_time(
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


gui_hooks.main_window_did_init.append(lambda: _setup_menu(mw))
