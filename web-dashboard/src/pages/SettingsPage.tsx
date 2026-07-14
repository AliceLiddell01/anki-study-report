import { Database, RefreshCw, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";
import { CheckboxControl, SettingRow, SettingsFormActions, SettingsSection } from "../components/SettingsControls";
import { cardAttentionState } from "../lib/cardAttention";
import { formatInteger, safeText } from "../lib/formatters";
import { usePublicSettingsForm } from "../lib/settingsApi";
import type { StudyReport, StatsCacheSummary, StatsCacheStatus } from "../types/report";

function SettingsPage({ report }: { report: StudyReport | null }) {
  const { t } = useTranslation(["pages", "common"]);
  const [cache, setCache] = useState<StatsCacheSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [actionState, setActionState] = useState<"idle" | "refreshing" | "rebuilding">("idle");
  const [message, setMessage] = useState("");
  const [confirmRebuild, setConfirmRebuild] = useState(false);
  const settingsForm = usePublicSettingsForm(["data"]);
  const dataSettings = settingsForm.draft.data;

  const loadCacheStatus = useCallback(() => {
    const token = dashboardToken();
    setLoadState("loading");
    return fetch(`/api/cache/status?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "forbidden" : "status_error");
        }
        return response.json() as Promise<StatsCacheSummary>;
      })
      .then((status) => {
        setCache(sanitizeCacheStatus(status));
        setLoadState("ready");
      })
      .catch((error: Error) => {
        setLoadState("error");
        setMessage(error.message === "forbidden" ? t("dataSettings.invalidToken") : t("dataSettings.statusLoadFailed"));
      });
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    const run = () => {
      loadCacheStatus().catch(() => undefined);
    };
    if (!cancelled) {
      run();
    }
    const busy = cache?.status === "scheduled" || cache?.status === "building" || cache?.isBuilding;
    const timer = window.setInterval(run, busy ? 2500 : 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [cache?.isBuilding, cache?.status, loadCacheStatus]);

  const runAction = (action: "refresh" | "rebuild") => {
    if (action === "rebuild" && !confirmRebuild) {
      setConfirmRebuild(true);
      setMessage(t("dataSettings.rebuildConfirmMessage"));
      return;
    }
    setConfirmRebuild(false);
    const token = dashboardToken();
    const nextActionState = action === "refresh" ? "refreshing" : "rebuilding";
    setActionState(nextActionState);
    setMessage("");
    fetch(`/api/cache/${action}?token=${encodeURIComponent(token)}`, {
      method: "POST",
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "forbidden" : "action_error");
        }
        return response.json() as Promise<{
          ok?: boolean;
          status?: StatsCacheStatus;
          error?: string | null;
          message?: string;
          alreadyBuilding?: boolean;
          addedRows?: number;
        }>;
      })
      .then((result) => {
        if (result.error) {
          setMessage(result.error);
        } else if (result.alreadyBuilding) {
          setMessage(result.message || t("dataSettings.alreadyRunning"));
        } else {
          setMessage(result.message || actionMessage(result.status, result.addedRows));
        }
        return loadCacheStatus();
      })
      .catch((error: Error) => {
        setMessage(error.message === "forbidden" ? t("dataSettings.invalidToken") : t("dataSettings.actionFailed"));
      })
      .finally(() => setActionState("idle"));
  };

  const status = cache?.status ?? (loadState === "loading" ? "building" : "error");
  const isBusy = actionState !== "idle" || Boolean(cache?.isBuilding) || status === "scheduled" || status === "building";
  const limitations = cache?.limitations && cache.limitations.length > 0
    ? cache.limitations
    : cache?.deckHistoryNote
      ? [cache.deckHistoryNote]
      : [];
  const reportCache = report?.cache;
  const reportSource = sourceLabel(report?.dataSource ?? reportCache?.dataSource ?? "legacy");
  const reportUsedFor = reportCache?.usedFor?.length ? reportCache.usedFor.join(", ") : t("dataSettings.none");
  const reportFallback = reportCache?.fallbackReason || t("dataSettings.none");
  const reportFlag = cache?.useStatsCacheForReport ?? reportCache?.useStatsCacheForReport ?? false;
  const parityMismatches = report?.cacheDebug?.mismatches?.length ?? 0;
  const cardLevel = cardAttentionState(report);

  return (
    <form className="grid gap-5" onSubmit={(event) => { event.preventDefault(); if (settingsForm.dirty && !settingsForm.saving) void settingsForm.save(); }}>
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill status-${statusTone(status)}`}>{cacheStatusLabel(status)}</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{t("dataSettings.title")}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              {t("dataSettings.description")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm font-medium text-report-text transition hover:border-report-blue/55 disabled:cursor-not-allowed disabled:opacity-55"
              disabled={isBusy}
              onClick={() => runAction("refresh")}
              title={t("dataSettings.refreshIncremental")}
            >
              <RefreshCw size={16} aria-hidden="true" />
              {t("dataSettings.refreshIncremental")}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-report-warning/35 bg-report-warning/10 px-3 py-2 text-sm font-medium text-report-warning transition hover:border-report-warning/70 disabled:cursor-not-allowed disabled:opacity-55"
              disabled={isBusy}
              onClick={() => runAction("rebuild")}
              title={t("dataSettings.rebuildAll")}
            >
              <RotateCcw size={16} aria-hidden="true" />
              {confirmRebuild ? t("dataSettings.confirmRebuild") : t("dataSettings.rebuild")}
            </button>
          </div>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <SettingsSection title={t("dataSettings.collectionTitle")} description={t("dataSettings.collectionDescription")}>
        <SettingRow id="track-sessions" label={t("dataSettings.trackSessions")} description={t("dataSettings.trackSessionsDescription")}>
          <CheckboxControl id="track-sessions" checked={dataSettings.trackReviewerSessions} onChange={(trackReviewerSessions) => settingsForm.setDraft((current) => ({ ...current, data: { ...current.data, trackReviewerSessions } }))} />
        </SettingRow>
        <SettingRow id="session-idle" label={t("dataSettings.sessionTimeout")} description={t("dataSettings.sessionTimeoutDescription")} error={settingsForm.fieldErrors["data.sessionIdleTimeoutSeconds"]}>
          <div className="flex items-center gap-2">
            <input id="session-idle" type="number" min={60} max={86400} className="form-control w-full px-3 py-2.5 text-sm" value={dataSettings.sessionIdleTimeoutSeconds} disabled={!dataSettings.trackReviewerSessions} onChange={(event) => settingsForm.setDraft((current) => ({ ...current, data: { ...current.data, sessionIdleTimeoutSeconds: Number(event.target.value) } }))} />
            <span className="text-sm text-report-muted">{t("units.secondsShort", { ns: "common", value: "" }).trim()}</span>
          </div>
        </SettingRow>
        <SettingRow id="session-gap" label={t("dataSettings.intervalLimit")} description={t("dataSettings.intervalLimitDescription")} error={settingsForm.fieldErrors["data.sessionGapCapSeconds"]}>
          <div className="flex items-center gap-2">
            <input id="session-gap" type="number" min={1} max={3600} className="form-control w-full px-3 py-2.5 text-sm" value={dataSettings.sessionGapCapSeconds} disabled={!dataSettings.trackReviewerSessions} onChange={(event) => settingsForm.setDraft((current) => ({ ...current, data: { ...current.data, sessionGapCapSeconds: Number(event.target.value) } }))} />
            <span className="text-sm text-report-muted">{t("units.secondsShort", { ns: "common", value: "" }).trim()}</span>
          </div>
        </SettingRow>
        <SettingRow id="study-time" label={t("dataSettings.useStudyTime")} description={t("dataSettings.useStudyTimeDescription")}>
          <CheckboxControl id="study-time" checked={dataSettings.useStudyTimeStats} onChange={(useStudyTimeStats) => settingsForm.setDraft((current) => ({ ...current, data: { ...current.data, useStudyTimeStats } }))} />
        </SettingRow>
        <SettingRow id="cache-report" label={t("dataSettings.useCache")} description={t("dataSettings.useCacheDescription")}>
          <CheckboxControl id="cache-report" checked={dataSettings.useStatsCacheForReport} onChange={(useStatsCacheForReport) => settingsForm.setDraft((current) => ({ ...current, data: { ...current.data, useStatsCacheForReport } }))} />
        </SettingRow>
      </SettingsSection>

      <SettingsFormActions dirty={settingsForm.dirty} saving={settingsForm.saving} message={settingsForm.message} onSave={() => void settingsForm.save()} onCancel={settingsForm.cancel} />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CacheMetric label={t("dataSettings.status")} value={cacheStatusLabel(cache?.status ?? loadState)} tone={statusTone(status)} />
        <CacheMetric label={t("dataSettings.cachedDays")} value={formatInteger(cache?.cachedDays ?? 0)} />
        <CacheMetric label={t("dataSettings.cachedDeckDays")} value={formatInteger(cache?.cachedDeckDays ?? 0)} />
        <CacheMetric label={t("dataSettings.lastRevlog")} value={formatInteger(cache?.lastRevlogId ?? 0)} />
        <CacheMetric label={t("dataSettings.build")} value={formatMilliseconds(cache?.lastBuildDurationMs)} />
        <CacheMetric label={t("dataSettings.refresh")} value={formatMilliseconds(cache?.lastRefreshDurationMs)} />
        <CacheMetric label={t("dataSettings.newRows")} value={formatInteger(cache?.lastRefreshAddedRows ?? 0)} />
        <CacheMetric label={t("dataSettings.operation")} value={status === "scheduled" || status === "building" ? t("dataSettings.inProgress") : t("dataSettings.waiting")} tone={statusTone(status)} />
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">{t("dataSettings.reportSource")}</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <CacheDetail label={t("dataSettings.mode")} value={reportFlag ? t("dataSettings.cacheHistory") : t("dataSettings.legacyOnly")} />
          <CacheDetail label={t("dataSettings.dataSource")} value={reportSource} />
          <CacheDetail label={t("dataSettings.cacheUsedFor")} value={reportUsedFor} />
          <CacheDetail label="Fallback" value={reportFallback} />
          <CacheDetail label={t("dataSettings.parityCheck")} value={report?.cacheDebug?.parityChecked ? t("dataSettings.mismatch", { count: parityMismatches }) : t("dataSettings.notChecked")} />
          <CacheDetail label={t("dataSettings.cacheRead")} value={formatMilliseconds(report?.performance?.cacheReadMs)} />
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">{t("dataSettings.cardCollector")}</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <CacheDetail label={t("dataSettings.status")} value={cardLevel.status} />
          <CacheDetail label={t("dataSettings.source")} value={cardLevel.source} />
          <CacheDetail label={t("dataSettings.collectorRan")} value={formatBoolean(cardLevel.collectorRan)} />
          <CacheDetail label={t("dataSettings.collectionAvailable")} value={formatBoolean(cardLevel.collectionAvailable)} />
          <CacheDetail label={t("dataSettings.scannedCards")} value={formatNullableInteger(cardLevel.scannedCards)} />
          <CacheDetail label={t("dataSettings.candidateCards")} value={formatNullableInteger(cardLevel.candidateCards)} />
          <CacheDetail label={t("dataSettings.revlogRows")} value={formatNullableInteger(cardLevel.revlogRows)} />
          <CacheDetail label={t("dataSettings.returnedCards")} value={formatNullableInteger(cardLevel.returnedCards)} />
        </div>
        {cardLevel.reason ? (
          <p className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm leading-6 text-report-muted">
            {cardLevel.reason}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="grid gap-3 md:grid-cols-2">
          <CacheDetail label={t("dataSettings.lastUpdated")} value={formatUnixSeconds(cache?.updatedAt)} />
          <CacheDetail label={t("dataSettings.created")} value={formatUnixSeconds(cache?.createdAt)} />
          <CacheDetail label={t("dataSettings.version")} value={formatInteger(cache?.version ?? 0)} />
          <CacheDetail label={t("dataSettings.cacheFile")} value={safeText(cache?.cachePath)} />
        </div>
        {status === "stale" ? (
          <div className="mt-4 rounded-lg border border-report-warning/35 bg-report-warning/10 p-3 text-sm leading-6 text-report-warning">
            {t("dataSettings.staleWarning")}
          </div>
        ) : null}
        {limitations.length > 0 ? (
          <div className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 p-3">
            <div className="flex items-start gap-3">
              <Database className="mt-0.5 shrink-0 text-report-blue" size={18} aria-hidden="true" />
              <div className="grid gap-1 text-sm leading-6 text-report-muted">
                {limitations.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            </div>
          </div>
        ) : null}
        {cache?.error ? (
          <div className="mt-4 rounded-lg border border-report-danger/35 bg-report-danger/10 p-3 text-sm leading-6 text-report-danger">
            {cache.error}
          </div>
        ) : null}
        {cache?.lastError && cache.lastError !== cache.error ? (
          <div className="mt-4 rounded-lg border border-report-danger/25 bg-report-danger/5 p-3 text-sm leading-6 text-report-muted">
            {t("dataSettings.lastError", { detail: cache.lastError })}
          </div>
        ) : null}
      </section>
    </form>
  );
}

function CacheMetric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "good" | "neutral" | "warning" | "danger";
}) {
  return (
    <article className={`rounded-xl border bg-ink-800/55 p-4 status-border-${tone}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-2 break-words text-xl font-semibold text-report-text">{value}</p>
    </article>
  );
}

function CacheDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm text-report-text">{value}</p>
    </div>
  );
}

function dashboardToken(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

function sanitizeCacheStatus(value: StatsCacheSummary): StatsCacheSummary {
  return {
    status: validCacheStatus(value.status) ? value.status : "error",
    dataSource: validReportDataSource(value.dataSource) ? value.dataSource : undefined,
    usedFor: Array.isArray(value.usedFor)
      ? value.usedFor.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [],
    version: finiteNumberOrZero(value.version),
    createdAt: finiteNumberOrZero(value.createdAt),
    updatedAt: finiteNumberOrZero(value.updatedAt),
    lastRevlogId: finiteNumberOrZero(value.lastRevlogId),
    cachedDays: finiteNumberOrZero(value.cachedDays),
    cachedDeckDays: finiteNumberOrZero(value.cachedDeckDays),
    isBuilding: Boolean(value.isBuilding),
    error: typeof value.error === "string" && value.error.trim() ? value.error : null,
    lastError: typeof value.lastError === "string" && value.lastError.trim() ? value.lastError : null,
    lastBuildDurationMs: finiteNumberOrZero(value.lastBuildDurationMs),
    lastRefreshDurationMs: finiteNumberOrZero(value.lastRefreshDurationMs),
    lastRefreshAddedRows: finiteNumberOrZero(value.lastRefreshAddedRows),
    fallbackReason: typeof value.fallbackReason === "string" && value.fallbackReason.trim() ? value.fallbackReason : null,
    limitations: Array.isArray(value.limitations)
      ? value.limitations.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [],
    cachePath: typeof value.cachePath === "string" ? value.cachePath : "",
    deckHistoryNote: typeof value.deckHistoryNote === "string" ? value.deckHistoryNote : "",
    useStatsCacheForReport: Boolean(value.useStatsCacheForReport),
    reportSourceMode: typeof value.reportSourceMode === "string" ? value.reportSourceMode : "",
  };
}

function validCacheStatus(value: unknown): value is StatsCacheStatus {
  return (
    value === "ready" ||
    value === "scheduled" ||
    value === "building" ||
    value === "stale" ||
    value === "empty" ||
    value === "error"
  );
}

function validReportDataSource(value: unknown): value is "legacy" | "cache" | "mixed" {
  return value === "legacy" || value === "cache" || value === "mixed";
}

function cacheStatusLabel(value: string): string {
  return {
    ready: i18n.t("dataSettings.statusReady", { ns: "pages" }),
    scheduled: i18n.t("dataSettings.statusScheduled", { ns: "pages" }),
    building: i18n.t("dataSettings.statusBuilding", { ns: "pages" }),
    stale: i18n.t("dataSettings.statusStale", { ns: "pages" }),
    empty: i18n.t("dataSettings.statusEmpty", { ns: "pages" }),
    error: i18n.t("dataSettings.statusError", { ns: "pages" }),
    loading: i18n.t("dataSettings.statusLoading", { ns: "pages" }),
  }[value] ?? value;
}

function sourceLabel(value: "legacy" | "cache" | "mixed" | string): string {
  return {
    legacy: "legacy",
    cache: i18n.t("dataSettings.sourceCache", { ns: "pages" }),
    mixed: i18n.t("dataSettings.sourceMixed", { ns: "pages" }),
  }[value] ?? value;
}

function statusTone(status: StatsCacheStatus): "good" | "neutral" | "warning" | "danger" {
  if (status === "ready") {
    return "good";
  }
  if (status === "scheduled" || status === "building") {
    return "neutral";
  }
  if (status === "stale" || status === "empty") {
    return "warning";
  }
  return "danger";
}

function finiteNumberOrZero(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatNullableInteger(value: number | null): string {
  return value === null ? i18n.t("state.noData", { ns: "common" }) : formatInteger(value);
}

function formatBoolean(value: boolean | null): string {
  if (value === null) {
    return i18n.t("state.noData", { ns: "common" });
  }
  return value ? "true" : "false";
}

function formatUnixSeconds(value: unknown): string {
  const seconds = finiteNumberOrZero(value);
  if (seconds <= 0) {
    return i18n.t("state.noData", { ns: "common" });
  }
  const date = new Date(seconds * 1000);
  if (Number.isNaN(date.getTime())) {
    return i18n.t("state.noData", { ns: "common" });
  }
  return date.toLocaleString(localeForLanguage(i18n.resolvedLanguage || i18n.language));
}

function formatMilliseconds(value: unknown): string {
  const milliseconds = finiteNumberOrZero(value);
  if (milliseconds <= 0) {
    return i18n.t("state.noData", { ns: "common" });
  }
  if (milliseconds < 1000) {
    return i18n.t("units.millisecondsShort", { ns: "common", value: formatInteger(milliseconds) });
  }
  return i18n.t("units.secondsShort", { ns: "common", value: new Intl.NumberFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), { maximumFractionDigits: milliseconds < 10_000 ? 1 : 0 }).format(milliseconds / 1000) });
}

function actionMessage(status: StatsCacheStatus | undefined, addedRows: unknown): string {
  if (status === "scheduled") {
    return i18n.t("dataSettings.cacheScheduled", { ns: "pages" });
  }
  if (status === "building") {
    return i18n.t("dataSettings.cacheBuilding", { ns: "pages" });
  }
  if (status === "ready") {
    const rows = finiteNumberOrZero(addedRows);
    return rows > 0 ? i18n.t("dataSettings.cacheUpdatedRows", { ns: "pages", count: formatInteger(rows) }) : i18n.t("dataSettings.cacheStatusUpdated", { ns: "pages" });
  }
  return i18n.t("dataSettings.cacheStatusUpdated", { ns: "pages" });
}

export default SettingsPage;
