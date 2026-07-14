import { Info, Plug, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
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
  const { t } = useTranslation(["pages", "common"]);
  const [data, setData] = useState<IntegrationStatus>({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const loadIntegrations = useCallback(() => {
    const token = dashboardToken();
    setLoading(true);
    return fetch(`/api/integrations/status?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? t("integrations.invalidToken") : t("integrations.loadFailed"));
        }
        return response.json() as Promise<IntegrationStatus>;
      })
      .then((status) => {
        setData(status || {});
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    loadIntegrations().catch(() => undefined);
  }, [loadIntegrations]);

  const items = data.items || [];

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className="status-pill status-neutral">{t("integrations.optional")}</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{t("integrations.title")}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              {t("integrations.description")}
            </p>
          </div>
          <button className="toolbar-button" type="button" disabled={loading} onClick={() => loadIntegrations().catch(() => undefined)}>
            <RefreshCw size={16} aria-hidden="true" />
            {loading ? t("integrations.refreshing") : t("actions.refresh", { ns: "common" })}
          </button>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted" role="status">{message}</p> : null}
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
            <p className="mt-2 text-sm text-report-muted">{t("integrations.mode")} {item.enabled ? t("integrations.enabled") : t("integrations.readonly")}</p>
          </article>
        ))}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-center gap-3">
          <Info size={18} className="text-report-blue" aria-hidden="true" />
          <h2 className="text-lg font-semibold tracking-normal text-report-text">{t("integrations.diagnostics")}</h2>
        </div>
        <div className="mt-4 grid gap-3">
          {items.map((item) => (
            <details key={item.id} className="rounded-lg border border-ink-700 bg-ink-900/45 p-3">
              <summary className="cursor-pointer text-sm font-semibold text-report-blue">{item.label}</summary>
              <pre className="log-viewer mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words font-mono text-report-muted">
                {item.diagnostics || t("integrations.diagnosticsUnavailable")}
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
    good: i18n.t("integrations.statusGood", { ns: "pages" }),
    neutral: i18n.t("integrations.statusNeutral", { ns: "pages" }),
    warning: i18n.t("integrations.statusWarning", { ns: "pages" }),
    danger: i18n.t("integrations.statusDanger", { ns: "pages" }),
  }[status];
}

function integrationDescription(description: string | undefined) {
  if (!description) {
    return i18n.t("integrations.genericDescription", { ns: "pages" });
  }
  const normalized = description.toLowerCase();
  if (normalized.includes("real study time")) {
    return i18n.t("integrations.studyTimeDescription", { ns: "pages" });
  }
  if (normalized.includes("lightweight tracker")) {
    return i18n.t("integrations.trackerDescription", { ns: "pages" });
  }
  if (normalized.includes("review heatmap")) {
    return i18n.t("integrations.heatmapDescription", { ns: "pages" });
  }
  if (normalized.includes("technical logs")) {
    return i18n.t("integrations.logsDescription", { ns: "pages" });
  }
  return description;
}

export default IntegrationsPage;
