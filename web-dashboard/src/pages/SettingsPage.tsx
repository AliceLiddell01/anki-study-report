import { Database, RefreshCw, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { cardAttentionState } from "../lib/cardAttention";
import { formatInteger, safeText } from "../lib/formatters";
import type { StudyReport, StatsCacheSummary, StatsCacheStatus } from "../types/report";

function SettingsPage({ report }: { report: StudyReport | null }) {
  const [cache, setCache] = useState<StatsCacheSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [actionState, setActionState] = useState<"idle" | "refreshing" | "rebuilding">("idle");
  const [message, setMessage] = useState("");

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
        setMessage("");
      })
      .catch((error: Error) => {
        setLoadState("error");
        setMessage(error.message === "forbidden" ? "Недействительный dashboard token." : "Не удалось загрузить статус.");
      });
  }, []);

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
          setMessage(result.message || "Операция с кэшем уже выполняется.");
        } else {
          setMessage(result.message || actionMessage(result.status, result.addedRows));
        }
        return loadCacheStatus();
      })
      .catch((error: Error) => {
        setMessage(error.message === "forbidden" ? "Недействительный dashboard token." : "Не удалось выполнить действие.");
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
  const reportUsedFor = reportCache?.usedFor?.length ? reportCache.usedFor.join(", ") : "нет";
  const reportFallback = reportCache?.fallbackReason || "нет";
  const reportFlag = cache?.useStatsCacheForReport ?? reportCache?.useStatsCacheForReport ?? false;
  const parityMismatches = report?.cacheDebug?.mismatches?.length ?? 0;
  const cardLevel = cardAttentionState(report);

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill status-${statusTone(status)}`}>{cacheStatusLabel(status)}</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Кэш и диагностика</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Локальные агрегаты revlog для быстрого фильтра по периодам.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm font-medium text-report-text transition hover:border-report-blue/55 disabled:cursor-not-allowed disabled:opacity-55"
              disabled={isBusy}
              onClick={() => runAction("refresh")}
              title="Обновить инкрементально"
            >
              <RefreshCw size={16} aria-hidden="true" />
              Обновить инкрементально
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-report-warning/35 bg-report-warning/10 px-3 py-2 text-sm font-medium text-report-warning transition hover:border-report-warning/70 disabled:cursor-not-allowed disabled:opacity-55"
              disabled={isBusy}
              onClick={() => runAction("rebuild")}
              title="Пересобрать кэш за всё время"
            >
              <RotateCcw size={16} aria-hidden="true" />
              Пересобрать кэш
            </button>
          </div>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CacheMetric label="Статус" value={cacheStatusLabel(cache?.status ?? loadState)} tone={statusTone(status)} />
        <CacheMetric label="Дней в кэше" value={formatInteger(cache?.cachedDays ?? 0)} />
        <CacheMetric label="Колода-дней" value={formatInteger(cache?.cachedDeckDays ?? 0)} />
        <CacheMetric label="Последний revlog id" value={formatInteger(cache?.lastRevlogId ?? 0)} />
        <CacheMetric label="Сборка" value={formatMilliseconds(cache?.lastBuildDurationMs)} />
        <CacheMetric label="Обновление" value={formatMilliseconds(cache?.lastRefreshDurationMs)} />
        <CacheMetric label="Новые строки" value={formatInteger(cache?.lastRefreshAddedRows ?? 0)} />
        <CacheMetric label="Операция" value={status === "scheduled" || status === "building" ? "Выполняется..." : "Ожидание"} tone={statusTone(status)} />
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Источник отчёта</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <CacheDetail label="Режим" value={reportFlag ? "Кэш для исторических данных" : "Только legacy"} />
          <CacheDetail label="Источник данных" value={reportSource} />
          <CacheDetail label="Кэш используется для" value={reportUsedFor} />
          <CacheDetail label="Fallback" value={reportFallback} />
          <CacheDetail label="Parity check" value={report?.cacheDebug?.parityChecked ? `${formatInteger(parityMismatches)} расхождений` : "Не проверялось"} />
          <CacheDetail label="Чтение кэша" value={formatMilliseconds(report?.performance?.cacheReadMs)} />
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Card-level collector</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <CacheDetail label="Status" value={cardLevel.status} />
          <CacheDetail label="Source" value={cardLevel.source} />
          <CacheDetail label="Collector ran" value={formatBoolean(cardLevel.collectorRan)} />
          <CacheDetail label="Collection available" value={formatBoolean(cardLevel.collectionAvailable)} />
          <CacheDetail label="Scanned cards" value={formatNullableInteger(cardLevel.scannedCards)} />
          <CacheDetail label="Candidate cards" value={formatNullableInteger(cardLevel.candidateCards)} />
          <CacheDetail label="Revlog rows" value={formatNullableInteger(cardLevel.revlogRows)} />
          <CacheDetail label="Returned cards" value={formatNullableInteger(cardLevel.returnedCards)} />
        </div>
        {cardLevel.reason ? (
          <p className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm leading-6 text-report-muted">
            {cardLevel.reason}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="grid gap-3 md:grid-cols-2">
          <CacheDetail label="Последнее обновление" value={formatUnixSeconds(cache?.updatedAt)} />
          <CacheDetail label="Создан" value={formatUnixSeconds(cache?.createdAt)} />
          <CacheDetail label="Версия" value={formatInteger(cache?.version ?? 0)} />
          <CacheDetail label="Файл кэша" value={safeText(cache?.cachePath)} />
        </div>
        {status === "stale" ? (
          <div className="mt-4 rounded-lg border border-report-warning/35 bg-report-warning/10 p-3 text-sm leading-6 text-report-warning">
            Схема кэша устарела или кэш не готов. Нужна пересборка.
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
            Последняя ошибка: {cache.lastError}
          </div>
        ) : null}
      </section>
    </div>
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
    ready: "готово",
    scheduled: "запланировано",
    building: "собирается",
    stale: "устарел",
    empty: "пусто",
    error: "ошибка",
    loading: "загрузка",
  }[value] ?? value;
}

function sourceLabel(value: "legacy" | "cache" | "mixed" | string): string {
  return {
    legacy: "legacy",
    cache: "кэш",
    mixed: "смешанный",
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
  return value === null ? "Нет данных" : formatInteger(value);
}

function formatBoolean(value: boolean | null): string {
  if (value === null) {
    return "Нет данных";
  }
  return value ? "true" : "false";
}

function formatUnixSeconds(value: unknown): string {
  const seconds = finiteNumberOrZero(value);
  if (seconds <= 0) {
    return "Нет данных";
  }
  const date = new Date(seconds * 1000);
  if (Number.isNaN(date.getTime())) {
    return "Нет данных";
  }
  return date.toLocaleString("ru-RU");
}

function formatMilliseconds(value: unknown): string {
  const milliseconds = finiteNumberOrZero(value);
  if (milliseconds <= 0) {
    return "Нет данных";
  }
  if (milliseconds < 1000) {
    return `${milliseconds} мс`;
  }
  return `${(milliseconds / 1000).toFixed(milliseconds < 10_000 ? 1 : 0)} сек`;
}

function actionMessage(status: StatsCacheStatus | undefined, addedRows: unknown): string {
  if (status === "scheduled") {
    return "Операция с кэшем запланирована.";
  }
  if (status === "building") {
    return "Операция с кэшем выполняется.";
  }
  if (status === "ready") {
    const rows = finiteNumberOrZero(addedRows);
    return rows > 0 ? `Кэш обновлён: ${formatInteger(rows)} новых строк.` : "Статус кэша обновлён.";
  }
  return "Статус кэша обновлён.";
}

export default SettingsPage;
