import {
  Clipboard,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderSearch,
  RotateCcw,
  Search,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import type { LoadState } from "./HomePage";
import { dashboardToken, runReportAction, type ActionResponse, type BrowserActionKind, type ReportAction } from "../lib/actionsApi";
import type { StudyReport } from "../types/report";

type ButtonState = {
  loading: boolean;
  response: ActionResponse | null;
};

type ActionButton = {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  action?: ReportAction;
  kind?: BrowserActionKind;
  clientAction?: "copy-dashboard-url";
};

const sections: Array<{ title: string; actions: ActionButton[] }> = [
  {
    title: "Export",
    actions: [
      {
        id: "copy-markdown",
        label: "Copy Markdown",
        description: "Copy current report as Markdown to clipboard.",
        icon: Clipboard,
        action: "copy-markdown",
      },
      {
        id: "save-markdown",
        label: "Save .md",
        description: "Save current report as a Markdown file.",
        icon: Download,
        action: "save-markdown",
      },
    ],
  },
  {
    title: "Open in Anki",
    actions: [
      {
        id: "open-problematic",
        label: "Open problematic decks",
        description: "Open Anki Browser with cards and decks that need attention.",
        icon: FolderSearch,
        action: "open-browser",
        kind: "problematic-decks",
      },
      {
        id: "open-again",
        label: "Open Again for period",
        description: "Open Anki Browser filtered to Again answers in the selected period.",
        icon: RotateCcw,
        action: "open-again",
      },
      {
        id: "open-new",
        label: "Open New for period",
        description: "Open Anki Browser filtered to new cards in the selected period.",
        icon: Sparkles,
        action: "open-new",
      },
    ],
  },
  {
    title: "Dashboard",
    actions: [
      {
        id: "open-dashboard",
        label: "Open this report in dashboard",
        description: "Open the current dashboard report URL.",
        icon: ExternalLink,
        action: "open-dashboard",
      },
      {
        id: "copy-dashboard-url",
        label: "Copy dashboard URL",
        description: "Copy the current local dashboard URL.",
        icon: Copy,
        clientAction: "copy-dashboard-url",
      },
    ],
  },
];

function ActionsPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const [buttonStates, setButtonStates] = useState<Record<string, ButtonState>>({});
  const reportAvailable = Boolean(report) && loadState === "ready";
  const tokenAvailable = dashboardToken().length > 0;
  const disabledReason = useMemo(() => {
    if (!tokenAvailable) {
      return "Open dashboard from Anki Study Report to get a valid token.";
    }
    if (!reportAvailable) {
      return "No report is available yet. Build or open a report first.";
    }
    return "";
  }, [reportAvailable, tokenAvailable]);

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
      const response =
        button.clientAction === "copy-dashboard-url"
          ? await copyDashboardUrl()
          : await runReportAction(button.action || "open-browser", button.kind ? { kind: button.kind } : {});
      setButtonResponse(button.id, response);
    } catch {
      setButtonResponse(button.id, {
        ok: false,
        action: button.action || button.id,
        error: "Dashboard action failed.",
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
              {reportAvailable ? "report ready" : "report needed"}
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Actions</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Быстрые действия с текущим отчётом и Anki Browser.
            </p>
          </div>
          <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm text-report-muted">
            {reportAvailable ? report?.metadata.period || "Current report" : disabledReason}
          </div>
        </div>
      </section>

      {sections.map((section) => (
        <section key={section.title} className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
          <h2 className="text-lg font-semibold tracking-normal text-report-text">{section.title}</h2>
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
  const Icon = button.icon;
  const response = state.response;
  const tone = response ? (response.ok ? "good" : "danger") : "neutral";
  const text = response?.ok ? response.message || "Done." : response?.error;

  return (
    <article className={`rounded-xl border bg-ink-800/55 p-4 status-border-${tone}`}>
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-ink-700 bg-ink-900 text-report-blue">
          <Icon size={18} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h3 className="text-base font-semibold tracking-normal text-report-text">{button.label}</h3>
          <p className="mt-1 text-sm leading-6 text-report-muted">{button.description}</p>
        </div>
      </div>
      <button
        type="button"
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 text-sm font-medium text-report-blue transition hover:border-report-blue/70 disabled:cursor-not-allowed disabled:opacity-55"
        disabled={disabled || state.loading}
        onClick={onClick}
      >
        <Search size={16} aria-hidden="true" />
        {state.loading ? "Working..." : button.label}
      </button>
      {text ? <p className={`mt-3 text-sm leading-6 ${response?.ok ? "text-report-success" : "text-report-danger"}`}>{text}</p> : null}
    </article>
  );
}

async function copyDashboardUrl(): Promise<ActionResponse> {
  try {
    await navigator.clipboard.writeText(window.location.href);
    return {
      ok: true,
      action: "copy-dashboard-url",
      message: "Copied dashboard URL to clipboard.",
    };
  } catch {
    return {
      ok: false,
      action: "copy-dashboard-url",
      error: "Could not copy dashboard URL.",
    };
  }
}

export default ActionsPage;
