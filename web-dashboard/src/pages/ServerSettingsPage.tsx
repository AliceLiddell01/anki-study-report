import { Copy, ExternalLink, Power, RefreshCw, RotateCcw, ScrollText } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { dashboardToken } from "../lib/actionsApi";
import { useThemePreference, type ThemeMode } from "../lib/theme";

type ServerStatus = {
  running?: boolean;
  host?: string;
  port?: number;
  requested_port?: number;
  autoStart?: boolean;
  configuredPort?: number;
  idleTimeoutSeconds?: number;
  maskedUrl?: string;
  static_available?: boolean;
  report_available?: boolean;
  started_at?: string | null;
  last_request_at?: string | null;
  cacheStatus?: {
    status?: string;
    useStatsCacheForReport?: boolean;
    dataSource?: string;
    fallbackReason?: string | null;
  };
  logs?: {
    path?: string;
    size?: number;
  };
};

function ServerSettingsPage() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const { themeMode, resolvedTheme, setThemeMode } = useThemePreference();

  const loadStatus = useCallback(() => {
    const token = dashboardToken();
    setLoading(true);
    return fetch(`/api/server/status?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "Недействительный dashboard token." : "Не удалось загрузить статус сервера.");
        }
        return response.json() as Promise<ServerStatus>;
      })
      .then((data) => {
        setStatus(data);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadStatus().catch(() => undefined);
    const timer = window.setInterval(() => loadStatus().catch(() => undefined), 10000);
    return () => window.clearInterval(timer);
  }, [loadStatus]);

  const runServerAction = (action: "restart" | "stop" | "open-dashboard" | "copy-url") => {
    const token = dashboardToken();
    setMessage("");
    fetch(`/api/server/${action}?token=${encodeURIComponent(token)}`, { method: "POST", cache: "no-store" })
      .then((response) => response.json().then((data) => ({ response, data })))
      .then(({ response, data }) => {
        if (!response.ok || data.ok === false) {
          throw new Error(data.error || data.message || "Действие сервера не выполнено.");
        }
        setMessage(actionMessage(action, data.message));
        window.setTimeout(() => loadStatus().catch(() => undefined), action === "restart" || action === "stop" ? 700 : 100);
      })
      .catch((error: Error) => setMessage(error.message));
  };

  const serverTone = status?.running ? "good" : "warning";

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill status-${serverTone}`}>{status?.running ? "сервер запущен" : "сервер остановлен"}</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Настройки</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Пользовательские настройки, локальный сервер и техническая диагностика разделены по зонам.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <IconButton icon={ExternalLink} label="Открыть дашборд" onClick={() => runServerAction("open-dashboard")} />
            <IconButton icon={Copy} label="Скопировать ссылку" onClick={() => runServerAction("copy-url")} />
            <IconButton icon={RefreshCw} label="Обновить" onClick={() => loadStatus().catch(() => undefined)} disabled={loading} />
          </div>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Настройки интерфейса</h2>
        <p className="mt-2 text-sm leading-6 text-report-muted">
          Период отчёта и выбранные колоды настраиваются в разделе «Профиль».
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <ThemeSwitcher themeMode={themeMode} resolvedTheme={resolvedTheme} onChange={setThemeMode} />
          <a className="inline-flex min-h-10 items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 text-sm font-medium text-report-blue transition hover:border-report-blue focus:outline-none focus:ring-2 focus:ring-report-blue/45" href="#/profile">
            Открыть Профиль
          </a>
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-normal text-report-text">Сервер</h2>
            <p className="mt-2 text-sm leading-6 text-report-muted">Локальный дашборд работает только на 127.0.0.1.</p>
          </div>
          <div className="flex flex-wrap gap-2 rounded-lg border border-report-warning/30 bg-report-warning/5 p-2">
            <IconButton icon={RotateCcw} label="Перезапустить" onClick={() => runServerAction("restart")} tone="warning" />
            <IconButton icon={Power} label="Остановить" onClick={() => runServerAction("stop")} tone="warning" />
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Detail label="Host" value={status?.host || "127.0.0.1"} />
        <Detail label="Port" value={String(status?.port ?? status?.configuredPort ?? status?.requested_port ?? "8766")} />
        <Detail label="Auto start" value={status?.autoStart ? "включено" : "выключено"} />
        <Detail label="Token" value="нужен, скрыт" />
        <Detail label="Статический дашборд" value={status?.static_available ? "доступен" : "fallback"} />
        <Detail label="Отчёт" value={status?.report_available ? "опубликован" : "не опубликован"} />
        <Detail label="Запущен" value={status?.started_at || "не запущен"} />
        <Detail label="Последний запрос" value={status?.last_request_at || "нет"} />
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Ссылка на дашборд</h2>
        <p className="mt-3 break-words rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 font-mono text-sm text-report-muted">
          {status?.maskedUrl || "http://127.0.0.1:8766/?token=<hidden>#/home"}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Panel title="Кэш и диагностика" icon={RefreshCw}>
          <Detail label="Статус кэша" value={statusLabel(status?.cacheStatus?.status)} compact />
          <Detail label="use_stats_cache_for_report" value={status?.cacheStatus?.useStatsCacheForReport ? "true" : "false"} compact />
          <Detail label="Источник данных" value={sourceLabel(status?.cacheStatus?.dataSource)} compact />
          <Detail label="Fallback" value={emptyLabel(status?.cacheStatus?.fallbackReason)} compact />
        </Panel>
        <Panel title="Логи" icon={ScrollText}>
          <Detail label="Путь" value={status?.logs?.path || "ещё не создан"} compact />
          <Detail label="Размер" value={`${status?.logs?.size ?? 0} bytes`} compact />
          <a className="mt-3 inline-flex text-sm font-medium text-report-blue hover:text-report-text" href="#/logs">
            Открыть логи
          </a>
        </Panel>
      </section>
    </div>
  );
}

const themeOptions: Array<{ mode: ThemeMode; label: string }> = [
  { mode: "light", label: "Светлая" },
  { mode: "dark", label: "Тёмная" },
  { mode: "system", label: "Авто" },
];

function ThemeSwitcher({
  themeMode,
  resolvedTheme,
  onChange,
}: {
  themeMode: ThemeMode;
  resolvedTheme: "light" | "dark";
  onChange: (mode: ThemeMode) => void;
}) {
  return (
    <fieldset className="min-w-0">
      <legend className="text-base font-semibold text-report-text">Тема</legend>
      <p className="mt-1 text-sm leading-6 text-report-muted">Выберите оформление дашборда или используйте системную тему.</p>
      <div className="mt-3 inline-grid rounded-xl border border-ink-700 bg-ink-900/60 p-1 sm:grid-cols-3" role="radiogroup" aria-label="Тема дашборда">
        {themeOptions.map((option) => {
          const checked = themeMode === option.mode;
          return (
            <label
              key={option.mode}
              className={[
                "relative min-h-11 cursor-pointer rounded-lg px-3 py-2.5 text-center text-sm font-semibold transition focus-within:ring-2 focus-within:ring-report-blue/65 focus-within:ring-offset-2 focus-within:ring-offset-ink-900",
                checked ? "border border-report-blue/45 bg-report-blue/25 text-report-text shadow-glow" : "border border-transparent text-report-secondary hover:border-ink-700 hover:bg-ink-800 hover:text-report-text",
              ].join(" ")}
            >
              <input
                type="radio"
                name="dashboard-theme"
                value={option.mode}
                checked={checked}
                onChange={() => onChange(option.mode)}
                className="sr-only"
              />
              {option.label}
            </label>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-report-muted">
        Сейчас применяется: {resolvedTheme === "dark" ? "тёмная" : "светлая"}.
      </p>
    </fieldset>
  );
}

function actionMessage(action: "restart" | "stop" | "open-dashboard" | "copy-url", fallback?: string) {
  if (action === "restart") {
    return "Сервер перезапущен.";
  }
  if (action === "stop") {
    return "Сервер остановлен.";
  }
  if (action === "copy-url") {
    return "Ссылка скопирована.";
  }
  if (action === "open-dashboard") {
    return "Дашборд открыт.";
  }
  return fallback || "Готово.";
}

function statusLabel(value: string | undefined) {
  return {
    ready: "готово",
    scheduled: "запланировано",
    building: "собирается",
    stale: "устарел",
    empty: "пусто",
    error: "ошибка",
  }[value || ""] ?? "нет данных";
}

function sourceLabel(value: string | undefined) {
  return {
    legacy: "legacy",
    cache: "кэш",
    mixed: "смешанный",
  }[value || ""] ?? "legacy";
}

function emptyLabel(value: string | null | undefined) {
  return value && value.trim() ? value : "нет";
}

function IconButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  tone = "neutral",
}: {
  icon: typeof ExternalLink;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: "neutral" | "warning";
}) {
  const toneClass =
    tone === "warning"
      ? "border-report-warning/35 bg-report-warning/10 text-report-warning hover:border-report-warning/70"
      : "border-report-blue/35 bg-report-blue/10 text-report-blue hover:border-report-blue/70";
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-55 ${toneClass}`}
      disabled={disabled}
      onClick={onClick}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
    </button>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof ExternalLink; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
      <div className="flex items-center gap-3">
        <span className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-report-blue">
          <Icon size={18} aria-hidden="true" />
        </span>
        <h2 className="text-lg font-semibold tracking-normal text-report-text">{title}</h2>
      </div>
      <div className="mt-4 grid gap-3">{children}</div>
    </section>
  );
}

function Detail({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={`rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 ${compact ? "" : "min-h-[82px]"}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-report-text">{value}</p>
    </div>
  );
}

export default ServerSettingsPage;
