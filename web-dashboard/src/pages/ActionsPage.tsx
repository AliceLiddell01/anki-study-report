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
  label: string;
  description: string;
  icon: LucideIcon;
  action?: ReportAction;
  kind?: BrowserActionKind;
};

const sections: Array<{ title: string; actions: ActionButton[] }> = [
  {
    title: "Основные действия",
    actions: [
      {
        id: "open-problematic",
        label: "Открыть проблемные колоды",
        description: "Открыть Anki Browser с карточками и колодами, которым нужно внимание.",
        icon: FolderSearch,
        action: "open-browser",
        kind: "problematic-decks",
      },
      {
        id: "open-again",
        label: "Открыть Again за период",
        description: "Открыть Anki Browser с ответами Again за выбранный период.",
        icon: RotateCcw,
        action: "open-again",
      },
      {
        id: "open-new",
        label: "Открыть New за период",
        description: "Открыть Anki Browser с новыми карточками за выбранный период.",
        icon: Sparkles,
        action: "open-new",
      },
    ],
  },
  {
    title: "Экспорт",
    actions: [
      {
        id: "copy-markdown",
        label: "Copy Markdown",
        description: "Скопировать текущий отчёт как Markdown.",
        icon: Clipboard,
        action: "copy-markdown",
      },
      {
        id: "save-markdown",
        label: "Сохранить .md",
        description: "Сохранить текущий отчёт в Markdown-файл.",
        icon: Download,
        action: "save-markdown",
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
      return "Откройте дашборд из Anki Study Report, чтобы получить действующий token.";
    }
    if (!reportAvailable) {
      return "Отчёт ещё не опубликован. Сначала откройте или создайте отчёт.";
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
      const response = await runReportAction(button.action || "open-browser", button.kind ? { kind: button.kind } : {});
      setButtonResponse(button.id, response);
    } catch {
      setButtonResponse(button.id, {
        ok: false,
        action: button.action || button.id,
        error: "Действие дашборда не выполнено.",
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
              {reportAvailable ? "отчёт готов" : "нужен отчёт"}
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Инструменты</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Быстрые действия с текущим отчётом и Anki Browser.
            </p>
          </div>
          <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm text-report-muted">
            {reportAvailable ? report?.metadata.period || "Текущий отчёт" : disabledReason}
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
  const text = response?.ok ? successText(button.id, response.message) : response?.error;

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
        className="action-button mt-4"
        disabled={disabled || state.loading}
        onClick={onClick}
      >
        <MousePointerClick size={16} aria-hidden="true" />
        {state.loading ? "Выполняю..." : button.label}
      </button>
      {text ? <p className={`mt-3 text-sm leading-6 ${response?.ok ? "text-report-success" : "text-report-danger"}`}>{text}</p> : null}
    </article>
  );
}

function successText(buttonId: string, fallback?: string) {
  if (buttonId === "copy-markdown") {
    return "Markdown скопирован.";
  }
  if (buttonId === "save-markdown") {
    return fallback?.startsWith("Saved report to:") ? fallback.replace("Saved report to:", "Файл сохранён:") : "Файл сохранён.";
  }
  if (buttonId.startsWith("open-")) {
    return "Anki Browser открыт.";
  }
  return fallback || "Готово.";
}

export default ActionsPage;
