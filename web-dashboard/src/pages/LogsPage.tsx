import { Clipboard, Download, RefreshCw, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { dashboardToken } from "../lib/actionsApi";

type LogStatus = {
  path?: string;
  exists?: boolean;
  size?: number;
  modified?: number | null;
  maxBytes?: number;
  backupCount?: number;
};

type LevelFilter = "all" | "info" | "warning" | "error" | "debug";

function LogsPage() {
  const [status, setStatus] = useState<LogStatus | null>(null);
  const [text, setText] = useState("");
  const [level, setLevel] = useState<LevelFilter>("all");
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  const loadLogs = useCallback(() => {
    const token = dashboardToken();
    return fetch(`/api/logs/recent?token=${encodeURIComponent(token)}&max_bytes=200000`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "Недействительный dashboard token." : "Не удалось загрузить логи.");
        }
        return response.json() as Promise<{ text?: string; status?: LogStatus }>;
      })
      .then((data) => {
        setText(data.text || "");
        setStatus(data.status || null);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    loadLogs().catch(() => undefined);
  }, [loadLogs]);

  const filteredLines = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return text
      .split(/\r?\n/)
      .filter((line) => {
        if (!line.trim()) {
          return false;
        }
        const levelMatch = level === "all" || line.includes(`| ${level.toUpperCase()} |`);
        const searchMatch = !needle || line.toLowerCase().includes(needle);
        return levelMatch && searchMatch;
      })
      .slice(-1000);
  }, [level, search, text]);

  const copyLogs = async () => {
    try {
      await navigator.clipboard.writeText(filteredLines.join("\n"));
      setMessage("Логи скопированы.");
    } catch {
      setMessage("Не удалось скопировать логи.");
    }
  };

  const clearLogs = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      setMessage("Нажмите «Очистить логи» ещё раз для подтверждения.");
      return;
    }
    const token = dashboardToken();
    fetch(`/api/logs/clear?token=${encodeURIComponent(token)}`, { method: "POST", cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "Недействительный dashboard token." : "Не удалось очистить логи.");
        }
        return response.json();
      })
      .then(() => {
        setConfirmClear(false);
        setMessage("Логи очищены.");
        return loadLogs();
      })
      .catch((error: Error) => setMessage(error.message));
  };

  const token = dashboardToken();
  const modified = status?.modified ? new Date(status.modified * 1000).toLocaleString("ru-RU") : "ещё не создан";

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill ${status?.exists ? "status-good" : "status-warning"}`}>
              {status?.exists ? "логи готовы" : "логов пока нет"}
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Логи</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Последние строки локального лога расширения. Секреты и dashboard token скрываются до записи.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="toolbar-button" type="button" onClick={() => loadLogs().catch(() => undefined)}>
              <RefreshCw size={16} aria-hidden="true" />
              Обновить
            </button>
            <button className="toolbar-button" type="button" onClick={copyLogs}>
              <Clipboard size={16} aria-hidden="true" />
              Скопировать
            </button>
            <a className="toolbar-button" href={`/api/logs/download?token=${encodeURIComponent(token)}`}>
              <Download size={16} aria-hidden="true" />
              Скачать
            </a>
            <button className="toolbar-button toolbar-button-warning" type="button" onClick={clearLogs}>
              <Trash2 size={16} aria-hidden="true" />
              {confirmClear ? "Подтвердить очистку" : "Очистить логи"}
            </button>
          </div>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Detail label="Путь" value={status?.path || "ещё не создан"} />
        <Detail label="Размер" value={`${status?.size ?? 0} bytes`} />
        <Detail label="Изменён" value={modified} />
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)]">
          <select
            className="form-control px-3 py-2.5 text-sm"
            value={level}
            onChange={(event) => setLevel(event.target.value as LevelFilter)}
          >
            <option value="all">Все уровни</option>
            <option value="info">INFO</option>
            <option value="warning">WARNING</option>
            <option value="error">ERROR</option>
            <option value="debug">DEBUG</option>
          </select>
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={16} />
            <input
              className="form-control w-full py-2.5 pl-10 pr-3 text-sm"
              placeholder="Найти в логах"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        <pre className="log-viewer mt-4 max-h-[620px] overflow-auto rounded-lg border border-ink-700 bg-ink-950 p-4 font-mono text-report-muted">
          {filteredLines.length
            ? filteredLines.map((line, index) => <LogLine key={`${index}-${line.slice(0, 40)}`} line={line} />)
            : "Подходящих строк нет."}
        </pre>
      </section>
    </div>
  );
}

function LogLine({ line }: { line: string }) {
  const looksLikeTrace = /^(Traceback|[A-Za-z_][\w.]*Error:|\s+(File |at |\^))/.test(line);
  const tone = line.includes("| ERROR |")
    ? "text-report-danger"
    : line.includes("| WARNING |")
      ? "text-report-warning"
      : line.includes("| INFO |")
        ? "log-info"
        : line.includes("| DEBUG |")
          ? "text-report-blue"
          : "text-report-muted";
  const label = line.match(/\| (ERROR|WARNING|INFO|DEBUG) \|/)?.[1];
  return (
    <span className={`block whitespace-pre-wrap break-words pl-2 ${tone} ${looksLikeTrace ? "log-trace py-0.5" : `border-l-2 ${label ? levelBorder(label) : "border-transparent"}`}`}>
      {line}
    </span>
  );
}

function levelBorder(label: string) {
  return {
    ERROR: "border-report-danger/70",
    WARNING: "border-report-warning/70",
    INFO: "border-report-success/70",
    DEBUG: "border-report-blue/70",
  }[label] ?? "border-transparent";
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="nested-surface rounded-xl border border-ink-700 p-4">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-report-text">{value}</p>
    </div>
  );
}

export default LogsPage;
