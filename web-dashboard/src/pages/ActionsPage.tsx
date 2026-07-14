import {
  Clipboard,
  Download,
  FolderSearch,
  MousePointerClick,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import type { LoadState } from "./HomePage";
import {
  dashboardToken,
  runReportAction,
  type ActionResponse,
  type BrowserActionKind,
  type ReportAction,
} from "../lib/actionsApi";
import type { StudyReport } from "../types/report";

type ButtonState = {
  loading: boolean;
  response: ActionResponse | null;
};

type ActionButton = {
  id: string;
  labelKey: string;
  descriptionKey: string;
  icon: LucideIcon;
  action?: ReportAction;
  kind?: BrowserActionKind;
};

const sections: Array<{ titleKey: string; actions: ActionButton[] }> = [
  {
    titleKey: "actions.primary",
    actions: [
      {
        id: "open-problematic",
        labelKey: "actions.openProblematic",
        descriptionKey: "actions.openProblematicDescription",
        icon: FolderSearch,
        action: "open-browser",
        kind: "problematic-decks",
      },
      {
        id: "open-again",
        labelKey: "actions.openAgain",
        descriptionKey: "actions.openAgainDescription",
        icon: RotateCcw,
        action: "open-again",
      },
      {
        id: "open-new",
        labelKey: "actions.openNew",
        descriptionKey: "actions.openNewDescription",
        icon: Sparkles,
        action: "open-new",
      },
    ],
  },
  {
    titleKey: "actions.export",
    actions: [
      {
        id: "copy-markdown",
        labelKey: "actions.copyMarkdown",
        descriptionKey: "actions.copyMarkdownDescription",
        icon: Clipboard,
        action: "copy-markdown",
      },
      {
        id: "save-markdown",
        labelKey: "actions.saveMarkdown",
        descriptionKey: "actions.saveMarkdownDescription",
        icon: Download,
        action: "save-markdown",
      },
    ],
  },
];

function ActionsPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages");
  const [buttonStates, setButtonStates] = useState<Record<string, ButtonState>>({});
  const reportAvailable = Boolean(report) && loadState === "ready";
  const tokenAvailable = dashboardToken().length > 0;
  const disabledReason = useMemo(() => {
    if (!tokenAvailable) {
      return t("actions.tokenRequired");
    }
    if (!reportAvailable) {
      return t("actions.unpublished");
    }
    return "";
  }, [reportAvailable, t, tokenAvailable]);

  const runButton = async (button: ActionButton) => {
    if (!reportAvailable || !tokenAvailable) {
      setButtonResponse(button.id, { ok: false, action: button.action || button.id, error: disabledReason });
      return;
    }
    setButtonStates((current) => ({
      ...current,
      [button.id]: { loading: true, response: null },
    }));
    try {
      const response = await runReportAction(button.action || "open-browser", button.kind ? { kind: button.kind } : {});
      setButtonResponse(button.id, response);
    } catch {
      setButtonResponse(button.id, {
        ok: false,
        action: button.action || button.id,
        error: t("actions.failed"),
      });
    }
  };

  const setButtonResponse = (id: string, response: ActionResponse) => {
    setButtonStates((current) => ({
      ...current,
      [id]: { loading: false, response },
    }));
  };

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill ${reportAvailable ? "status-good" : "status-warning"}`}>
              {reportAvailable ? t("actions.reportReady") : t("actions.reportRequired")}
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{t("actions.title")}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              {t("actions.description")}
            </p>
          </div>
          <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm text-report-muted">
            {reportAvailable ? report?.metadata.period || t("actions.currentReport") : disabledReason}
          </div>
        </div>
      </section>

      {sections.map((section) => (
        <section key={section.titleKey} className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
          <h2 className="text-lg font-semibold tracking-normal text-report-text">{t(section.titleKey)}</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {section.actions.map((button) => (
              <ActionCard
                key={button.id}
                button={button}
                state={buttonStates[button.id] || { loading: false, response: null }}
                disabled={!reportAvailable || !tokenAvailable}
                onClick={() => runButton(button)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function ActionCard({
  button,
  state,
  disabled,
  onClick,
}: {
  button: ActionButton;
  state: ButtonState;
  disabled: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation("pages");
  const Icon = button.icon;
  const response = state.response;
  const tone = response ? (response.ok ? "good" : "danger") : "neutral";
  const text = response?.ok ? successText(button.id, response.message) : response?.error;

  return (
    <article className={`rounded-xl border bg-ink-800/55 p-4 status-border-${tone}`}>
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-ink-700 bg-ink-900 text-report-blue">
          <Icon size={18} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h3 className="text-base font-semibold tracking-normal text-report-text">{t(button.labelKey)}</h3>
          <p className="mt-1 text-sm leading-6 text-report-muted">{t(button.descriptionKey)}</p>
        </div>
      </div>
      <button
        type="button"
        className="action-button mt-4"
        disabled={disabled || state.loading}
        onClick={onClick}
      >
        <MousePointerClick size={16} aria-hidden="true" />
        {state.loading ? t("actions.running") : t(button.labelKey)}
      </button>
      {text ? <p className={`mt-3 text-sm leading-6 ${response?.ok ? "text-report-success" : "text-report-danger"}`}>{text}</p> : null}
    </article>
  );
}

function successText(buttonId: string, fallback?: string) {
  if (buttonId === "copy-markdown") {
    return i18n.t("actions.copied", { ns: "pages" });
  }
  if (buttonId === "save-markdown") {
    return fallback?.startsWith("Saved report to:") ? i18n.t("actions.fileSavedAt", { ns: "pages", path: fallback.slice("Saved report to:".length) }) : i18n.t("actions.fileSaved", { ns: "pages" });
  }
  if (buttonId.startsWith("open-")) {
    return i18n.t("actions.browserOpened", { ns: "pages" });
  }
  return fallback || i18n.t("actions.done", { ns: "pages" });
}

export default ActionsPage;
