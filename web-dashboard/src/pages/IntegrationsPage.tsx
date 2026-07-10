import { Info, Plug, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { dashboardToken } from "../lib/actionsApi";
import type { Status } from "../types/report";

type IntegrationItem = {
  id: string;
  label: string;
  status: Status;
  enabled?: boolean;
  description?: string;
  diagnostics?: string;
};

type IntegrationStatus = {
  items?: IntegrationItem[];
  notes?: string[];
};

function IntegrationsPage() {
  const [data, setData] = useState<IntegrationStatus>({});
  const [message, setMessage] = useState("");

  const loadIntegrations = useCallback(() => {
    const token = dashboardToken();
    return fetch(`/api/integrations/status?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "Недействительный dashboard token." : "Не удалось загрузить интеграции.");
        }
        return response.json() as Promise<IntegrationStatus>;
      })
      .then((status) => {
        setData(status || {});
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    loadIntegrations().catch(() => undefined);
  }, [loadIntegrations]);

  const items = data.items || [];

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className="status-pill status-neutral">опционально</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Источники данных</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Опциональные локальные источники и диагностика, которые использует Anki Study Report.
            </p>
          </div>
          <button className="toolbar-button" type="button" onClick={() => loadIntegrations().catch(() => undefined)}>
            <RefreshCw size={16} aria-hidden="true" />
            Обновить
          </button>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => (
          <article key={item.id} className={`rounded-xl border bg-ink-800/55 p-4 status-border-${item.status || "neutral"}`}>
            <div className="flex min-w-0 items-start gap-3">
              <span className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-report-blue">
                <Plug size={18} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="text-base font-semibold tracking-normal text-report-text">{item.label}</h2>
                <span className={`mt-2 status-pill status-${item.status || "neutral"}`}>{statusText(item.status || "neutral")}</span>
              </div>
            </div>
            <p className="mt-3 text-sm leading-6 text-report-muted">{integrationDescription(item.description)}</p>
            <p className="mt-2 text-sm text-report-muted">Режим: {item.enabled ? "доступно/настроено" : "диагностика только для чтения"}</p>
          </article>
        ))}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-center gap-3">
          <Info size={18} className="text-report-blue" aria-hidden="true" />
          <h2 className="text-lg font-semibold tracking-normal text-report-text">Диагностика</h2>
        </div>
        <div className="mt-4 grid gap-3">
          {items.map((item) => (
            <details key={item.id} className="rounded-lg border border-ink-700 bg-ink-900/45 p-3">
              <summary className="cursor-pointer text-sm font-semibold text-report-blue">{item.label}</summary>
              <pre className="log-viewer mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words font-mono text-report-muted">
                {item.diagnostics || "Диагностика недоступна."}
              </pre>
            </details>
          ))}
        </div>
        {data.notes?.length ? (
          <div className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 p-3 text-sm leading-6 text-report-muted">
            {data.notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}

function statusText(status: Status) {
  return {
    good: "хорошо",
    neutral: "инфо",
    warning: "внимание",
    danger: "опасно",
  }[status];
}

function integrationDescription(description: string | undefined) {
  if (!description) {
    return "Опциональная локальная интеграция.";
  }
  const normalized = description.toLowerCase();
  if (normalized.includes("real study time")) {
    return "Источник реального времени учёбы, используется только если доступен.";
  }
  if (normalized.includes("lightweight tracker")) {
    return "Встроенный лёгкий трекер длительности review-сессий.";
  }
  if (normalized.includes("review heatmap")) {
    return "Диагностика личной heatmap повторений.";
  }
  if (normalized.includes("technical logs")) {
    return "Локальные технические логи интеграций.";
  }
  return description;
}

export default IntegrationsPage;
