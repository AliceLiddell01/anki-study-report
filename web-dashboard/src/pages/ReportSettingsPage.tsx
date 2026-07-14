import { useMemo } from "react";
import { useTranslation } from "react-i18next";
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

const periodOptions: ReportPeriod[] = ["today", "yesterday", "since_last_report", "last_7_days", "last_30_days", "custom", "all_time"];

function ReportSettingsPage({ onReportUpdated }: { onReportUpdated?: (report: StudyReport) => void }) {
  const { t } = useTranslation(["pages", "common"]);
  const form = usePublicSettingsForm(["dashboard", "report"], (response) => {
    if (isStudyReport(response.report)) onReportUpdated?.(response.report);
  });
  const dashboard = form.draft.dashboard;
  const report = form.draft.report;
  const dashboardScopeLabel = dashboard.scope === "selected" ? t("units.deck", { ns: "common", count: dashboard.selectedDeckIds.length }) : t("reportSettings.allDecks");
  const reportDeckNames = useMemo(
    () => report.selectedDeckIds.map((id) => form.deckOptions.find((option) => option.id === id)?.name || t("reportSettings.generatedDeck", { id })),
    [form.deckOptions, report.selectedDeckIds, t],
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
        title={t("reportSettings.title")}
        status={form.loadState === "loading" ? t("reportSettings.loading") : t("reportSettings.status")}
        description={t("reportSettings.description")}
      />

      <SettingsSection title={t("reportSettings.dashboardTitle")} description={t("reportSettings.dashboardDescription")}>
        <SettingRow id="dashboard-scope" label={t("reportSettings.decks")} description={t("reportSettings.scopeDescription")} error={form.fieldErrors["dashboard.scope"]}>
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
            <option value="all">{t("reportSettings.allDecks")}</option>
            <option value="selected">{t("reportSettings.selectedDecks")}</option>
          </select>
        </SettingRow>
        <SettingRow
          id="dashboard-decks"
          label={t("reportSettings.selectedDecks")}
          description={t("reportSettings.currentScope", { scope: dashboardScopeLabel })}
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
        <SettingRow id="dashboard-children" label={t("reportSettings.includeChildren")} description={t("reportSettings.includeChildrenDescription")}>
          <CheckboxControl id="dashboard-children" checked={dashboard.includeChildDecks} onChange={(includeChildDecks) => updateDashboard({ includeChildDecks })} />
        </SettingRow>
      </SettingsSection>

      <div className="rounded-xl border border-report-blue/30 bg-report-blue/5 px-4 py-3 text-sm leading-6 text-report-secondary">
        {t("reportSettings.todayNote")}
      </div>

      <SettingsSection title={t("reportSettings.ankiReportTitle")} description={t("reportSettings.ankiReportDescription")}>
        <SettingRow id="report-period" label={t("reportSettings.period")} description={t("reportSettings.periodDescription")} error={form.fieldErrors["report.defaultPeriod"]}>
          <select id="report-period" className="form-control w-full px-3 py-2.5 text-sm" value={report.defaultPeriod} onChange={(event) => updateReport({ defaultPeriod: event.target.value as ReportPeriod })}>
            {periodOptions.map((option) => <option key={option} value={option}>{t(`reportSettings.periods.${option}`)}</option>)}
          </select>
        </SettingRow>
        {report.defaultPeriod === "custom" ? (
          <SettingRow id="report-custom-start" label={t("reportSettings.customBounds")} description={t("reportSettings.customBoundsDescription")}>
            <div className="grid gap-2 sm:grid-cols-2">
              <input id="report-custom-start" type="date" className="form-control px-3 py-2.5 text-sm" value={report.customStartDate} onChange={(event) => updateReport({ customStartDate: event.target.value })} aria-label={t("reportSettings.startDate")} />
              <input type="date" className="form-control px-3 py-2.5 text-sm" value={report.customEndDate} onChange={(event) => updateReport({ customEndDate: event.target.value })} aria-label={t("reportSettings.endDate")} />
            </div>
          </SettingRow>
        ) : null}
        <SettingRow id="report-scope" label={t("reportSettings.reportScope")} description={t("reportSettings.reportScopeDescription")} error={form.fieldErrors["report.scope"]}>
          <select id="report-scope" className="form-control w-full px-3 py-2.5 text-sm" value={report.scope} onChange={(event) => {
            const scope = event.target.value as ReportScope;
            updateReport({ scope, selectedDeckIds: scope === "selected" ? report.selectedDeckIds : [] });
          }}>
            <option value="all">{t("reportSettings.allDecks")}</option>
            <option value="current">{t("reportSettings.currentDeck")}</option>
            <option value="selected">{t("reportSettings.selectedDecks")}</option>
          </select>
        </SettingRow>
        <SettingRow id="report-decks" label={t("reportSettings.reportDecks")} description={reportDeckNames.length ? t("reportSettings.selectedNames", { names: reportDeckNames.join(", ") }) : t("reportSettings.selectDecksHint")} error={form.fieldErrors["report.selectedDeckIds"]}>
          <DeckMultiSelect id="report-decks" options={form.deckOptions} selectedIds={report.selectedDeckIds} onChange={(selectedDeckIds) => updateReport({ selectedDeckIds })} disabled={report.scope !== "selected"} error={form.fieldErrors["report.selectedDeckIds"]} />
        </SettingRow>
        <SettingRow id="report-children" label={t("reportSettings.includeChildren")} description={t("reportSettings.reportChildrenDescription")}>
          <CheckboxControl id="report-children" checked={report.includeChildDecks} onChange={(includeChildDecks) => updateReport({ includeChildDecks })} />
        </SettingRow>
        <SettingRow id="report-detail" label={t("reportSettings.detail")} description={t("reportSettings.detailDescription")}>
          <select id="report-detail" className="form-control w-full px-3 py-2.5 text-sm" value={report.detailLevel} onChange={(event) => updateReport({ detailLevel: event.target.value as typeof report.detailLevel })}>
            <option value="compact">{t("reportSettings.compact")}</option>
            <option value="normal">{t("reportSettings.normal")}</option>
            <option value="full">{t("reportSettings.full")}</option>
          </select>
        </SettingRow>
        <SettingRow id="report-answer-mode" label={t("reportSettings.answerMode")} description={t("reportSettings.answerModeDescription")}>
          <select id="report-answer-mode" className="form-control w-full px-3 py-2.5 text-sm" value={report.answerMode} onChange={(event) => updateReport({ answerMode: event.target.value as typeof report.answerMode })}>
            <option value="auto">{t("reportSettings.auto")}</option>
            <option value="standard">{t("reportSettings.standard")}</option>
            <option value="pass_fail">{t("reportSettings.passFail")}</option>
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
