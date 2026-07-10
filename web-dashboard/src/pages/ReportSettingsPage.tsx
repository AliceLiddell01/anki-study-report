import { useMemo } from "react";
import {
  CheckboxControl,
  DeckMultiSelect,
  SettingRow,
  SettingsFormActions,
  SettingsPageHeader,
  SettingsSection,
} from "../components/SettingsControls";
import { usePublicSettingsForm } from "../lib/settingsApi";
import type { StudyReport } from "../types/report";
import type { DashboardScope, ReportPeriod, ReportScope } from "../types/settings";

const periodOptions: Array<{ value: ReportPeriod; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "yesterday", label: "Вчера" },
  { value: "since_last_report", label: "С последнего отчёта" },
  { value: "last_7_days", label: "Последние 7 дней" },
  { value: "last_30_days", label: "Последние 30 дней" },
  { value: "custom", label: "Выбранный период" },
  { value: "all_time", label: "Всё время" },
];

function ReportSettingsPage({ onReportUpdated }: { onReportUpdated?: (report: StudyReport) => void }) {
  const form = usePublicSettingsForm(["dashboard", "report"], (response) => {
    if (isStudyReport(response.report)) onReportUpdated?.(response.report);
  });
  const dashboard = form.draft.dashboard;
  const report = form.draft.report;
  const dashboardScopeLabel = dashboard.scope === "selected" ? `${dashboard.selectedDeckIds.length} колод` : "Все колоды";
  const reportDeckNames = useMemo(
    () => report.selectedDeckIds.map((id) => form.deckOptions.find((option) => option.id === id)?.name || `Колода ${id}`),
    [form.deckOptions, report.selectedDeckIds],
  );

  const updateDashboard = (patch: Partial<typeof dashboard>) => {
    form.setDraft((current) => ({ ...current, dashboard: { ...current.dashboard, ...patch } }));
  };
  const updateReport = (patch: Partial<typeof report>) => {
    form.setDraft((current) => ({ ...current, report: { ...current.report, ...patch } }));
  };

  return (
    <form className="grid gap-5" onSubmit={(event) => { event.preventDefault(); if (form.dirty && !form.saving) void form.save(); }}>
      <SettingsPageHeader
        title="Отчёт"
        status={form.loadState === "loading" ? "загрузка" : "настройки отчётов"}
        description="Область данных dashboard и значения по умолчанию для Markdown/HTML-отчёта Anki сохраняются отдельно."
      />

      <SettingsSection title="Дашборд" description="Эта область применяется к страницам dashboard. Страница «Сегодня» всегда использует текущий локальный день.">
        <SettingRow id="dashboard-scope" label="Колоды" description="Показывать данные по всем колодам или ограничить dashboard выбранными." error={form.fieldErrors["dashboard.scope"]}>
          <select
            id="dashboard-scope"
            className="form-control w-full px-3 py-2.5 text-sm"
            value={dashboard.scope}
            onChange={(event) => {
              const scope = event.target.value as DashboardScope;
              updateDashboard({ scope, selectedDeckIds: scope === "all" ? [] : dashboard.selectedDeckIds });
            }}
            aria-describedby="dashboard-scope-description"
          >
            <option value="all">Все колоды</option>
            <option value="selected">Выбранные колоды</option>
          </select>
        </SettingRow>
        <SettingRow
          id="dashboard-decks"
          label="Выбранные колоды"
          description={`Текущая область: ${dashboardScopeLabel}. Ctrl/⌘ позволяет выбрать несколько колод.`}
          error={form.fieldErrors["dashboard.selectedDeckIds"]}
        >
          <DeckMultiSelect
            id="dashboard-decks"
            options={form.deckOptions}
            selectedIds={dashboard.selectedDeckIds}
            onChange={(selectedDeckIds) => updateDashboard({ selectedDeckIds })}
            disabled={dashboard.scope !== "selected"}
            error={form.fieldErrors["dashboard.selectedDeckIds"]}
          />
        </SettingRow>
        <SettingRow id="dashboard-children" label="Включать дочерние колоды" description="Расширять выбранные родительские колоды их дочерними колодами.">
          <CheckboxControl id="dashboard-children" checked={dashboard.includeChildDecks} onChange={(includeChildDecks) => updateDashboard({ includeChildDecks })} />
        </SettingRow>
      </SettingsSection>

      <div className="rounded-xl border border-report-blue/30 bg-report-blue/5 px-4 py-3 text-sm leading-6 text-report-secondary">
        Страница «Сегодня» всегда показывает текущий локальный день. Период ниже относится только к отчёту, который открывается в Anki.
      </div>

      <SettingsSection title="Отчёт Anki" description="Значения по умолчанию для диалога отчёта и Markdown/HTML export.">
        <SettingRow id="report-period" label="Период отчёта" description="Начальное значение периода при открытии диалога отчёта." error={form.fieldErrors["report.defaultPeriod"]}>
          <select id="report-period" className="form-control w-full px-3 py-2.5 text-sm" value={report.defaultPeriod} onChange={(event) => updateReport({ defaultPeriod: event.target.value as ReportPeriod })}>
            {periodOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </SettingRow>
        {report.defaultPeriod === "custom" ? (
          <SettingRow id="report-custom-start" label="Границы выбранного периода" description="Даты сохраняются как значения по умолчанию для диалога отчёта.">
            <div className="grid gap-2 sm:grid-cols-2">
              <input id="report-custom-start" type="date" className="form-control px-3 py-2.5 text-sm" value={report.customStartDate} onChange={(event) => updateReport({ customStartDate: event.target.value })} aria-label="Дата начала отчёта" />
              <input type="date" className="form-control px-3 py-2.5 text-sm" value={report.customEndDate} onChange={(event) => updateReport({ customEndDate: event.target.value })} aria-label="Дата окончания отчёта" />
            </div>
          </SettingRow>
        ) : null}
        <SettingRow id="report-scope" label="Область отчёта" description="Колоды, которые будут выбраны по умолчанию в диалоге отчёта." error={form.fieldErrors["report.scope"]}>
          <select id="report-scope" className="form-control w-full px-3 py-2.5 text-sm" value={report.scope} onChange={(event) => {
            const scope = event.target.value as ReportScope;
            updateReport({ scope, selectedDeckIds: scope === "selected" ? report.selectedDeckIds : [] });
          }}>
            <option value="all">Все колоды</option>
            <option value="current">Текущая колода</option>
            <option value="selected">Выбранные колоды</option>
          </select>
        </SettingRow>
        <SettingRow id="report-decks" label="Колоды отчёта" description={reportDeckNames.length ? `Выбрано: ${reportDeckNames.join(", ")}` : "Выберите колоды для области «Выбранные колоды»."} error={form.fieldErrors["report.selectedDeckIds"]}>
          <DeckMultiSelect id="report-decks" options={form.deckOptions} selectedIds={report.selectedDeckIds} onChange={(selectedDeckIds) => updateReport({ selectedDeckIds })} disabled={report.scope !== "selected"} error={form.fieldErrors["report.selectedDeckIds"]} />
        </SettingRow>
        <SettingRow id="report-children" label="Включать дочерние колоды" description="Применяется только к области отчёта Anki.">
          <CheckboxControl id="report-children" checked={report.includeChildDecks} onChange={(includeChildDecks) => updateReport({ includeChildDecks })} />
        </SettingRow>
        <SettingRow id="report-detail" label="Детализация" description="Уровень подробности Markdown/HTML-отчёта.">
          <select id="report-detail" className="form-control w-full px-3 py-2.5 text-sm" value={report.detailLevel} onChange={(event) => updateReport({ detailLevel: event.target.value as typeof report.detailLevel })}>
            <option value="compact">Компактный</option>
            <option value="normal">Обычный</option>
            <option value="full">Полный</option>
          </select>
        </SettingRow>
        <SettingRow id="report-answer-mode" label="Режим ответов" description="Авто использует осторожное определение Pass/Fail по данным revlog.ease.">
          <select id="report-answer-mode" className="form-control w-full px-3 py-2.5 text-sm" value={report.answerMode} onChange={(event) => updateReport({ answerMode: event.target.value as typeof report.answerMode })}>
            <option value="auto">Авто</option>
            <option value="standard">Обычный Anki</option>
            <option value="pass_fail">Pass/Fail</option>
          </select>
        </SettingRow>
      </SettingsSection>

      <SettingsFormActions dirty={form.dirty} saving={form.saving} message={form.message} onSave={() => void form.save()} onCancel={form.cancel} />
    </form>
  );
}

function isStudyReport(value: unknown): value is StudyReport {
  if (!value || typeof value !== "object") return false;
  const report = value as Partial<StudyReport>;
  return Boolean(report.metadata && report.summary && Array.isArray(report.kpis));
}

export default ReportSettingsPage;
