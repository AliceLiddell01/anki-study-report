import { Copy, ExternalLink, Power, RefreshCw, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  CheckboxControl,
  SettingRow,
  SettingsFormActions,
  SettingsPageHeader,
  SettingsSection,
} from "../components/SettingsControls";
import { dashboardToken } from "../lib/actionsApi";
import { usePublicSettingsForm } from "../lib/settingsApi";

type ServerStatus = {
  running?: boolean;
  host?: string;
  port?: number;
  requested_port?: number;
  configuredPort?: number;
  maskedUrl?: string;
  static_available?: boolean;
  report_available?: boolean;
  started_at?: string | null;
  last_request_at?: string | null;
  message?: string | null;
};

type ServerAction = "restart" | "stop" | "open-dashboard" | "copy-url";

function ServerSettingsPage() {
  const form = usePublicSettingsForm(["server"]);
  const settings = form.draft.server;
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<ServerAction | null>(null);
  const [confirmAction, setConfirmAction] = useState<"restart" | "stop" | null>(null);

  const loadStatus = useCallback(() => {
    setLoading(true);
    return fetch(`/api/server/status?token=${encodeURIComponent(dashboardToken())}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(response.status === 403 ? "Недействительный dashboard token." : "Не удалось загрузить статус сервера.");
        return response.json() as Promise<ServerStatus>;
      })
      .then((data) => setStatus(data))
      .catch((error: Error) => setStatusMessage(error.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadStatus().catch(() => undefined);
  }, [loadStatus]);

  const runServerAction = (nextAction: ServerAction) => {
    if ((nextAction === "restart" || nextAction === "stop") && confirmAction !== nextAction) {
      setConfirmAction(nextAction);
      setStatusMessage(nextAction === "restart" ? "Подтвердите перезапуск: текущая ссылка dashboard перестанет работать." : "Подтвердите остановку локального сервера.");
      return;
    }
    setConfirmAction(null);
    setAction(nextAction);
    setStatusMessage("");
    fetch(`/api/server/${nextAction}?token=${encodeURIComponent(dashboardToken())}`, { method: "POST", cache: "no-store" })
      .then((response) => response.json().then((data) => ({ response, data })))
      .then(({ response, data }) => {
        if (!response.ok || data.ok === false) throw new Error(data.error || data.message || "Действие сервера не выполнено.");
        setStatusMessage(actionMessage(nextAction));
        if (nextAction === "restart" || nextAction === "stop") {
          window.setTimeout(() => loadStatus().catch(() => undefined), 700);
        }
      })
      .catch((error: Error) => setStatusMessage(error.message))
      .finally(() => setAction(null));
  };

  const updateSettings = (patch: Partial<typeof settings>) => {
    form.setDraft((current) => ({ ...current, server: { ...current.server, ...patch } }));
  };

  return (
    <form className="grid gap-5" onSubmit={(event) => { event.preventDefault(); if (form.dirty && !form.saving) void form.save(); }}>
      <SettingsPageHeader
        title="Сервер"
        status={status?.running ? "сервер запущен" : "сервер остановлен"}
        description="Параметры token-protected сервера на 127.0.0.1 и отдельные действия над текущим runtime."
      />

      <SettingsSection title="Параметры запуска" description="Изменения порта и тайм-аута применятся после явного перезапуска сервера.">
        <SettingRow id="server-auto-start" label="Автоматический запуск" description="Запускать dashboard server при старте профиля Anki.">
          <CheckboxControl id="server-auto-start" checked={settings.autoStart} onChange={(autoStart) => updateSettings({ autoStart })} />
        </SettingRow>
        <SettingRow id="server-port" label="Порт" description="0 — выбрать свободный автоматически; иначе 1024–65535. Порт 8765 зарезервирован." error={form.fieldErrors["server.port"]}>
          <input id="server-port" type="number" min={0} max={65535} className="form-control w-full px-3 py-2.5 text-sm" value={settings.port} onChange={(event) => updateSettings({ port: Number(event.target.value) })} aria-invalid={Boolean(form.fieldErrors["server.port"])} />
        </SettingRow>
        <SettingRow id="server-idle" label="Авто-отключение после простоя" description="0 отключает остановку по idle; максимум 86400 секунд." error={form.fieldErrors["server.idleTimeoutSeconds"]}>
          <div className="flex items-center gap-2">
            <input id="server-idle" type="number" min={0} max={86400} className="form-control w-full px-3 py-2.5 text-sm" value={settings.idleTimeoutSeconds} onChange={(event) => updateSettings({ idleTimeoutSeconds: Number(event.target.value) })} />
            <span className="text-sm text-report-muted">сек</span>
          </div>
        </SettingRow>
      </SettingsSection>

      {form.restartRequired ? (
        <div className="rounded-xl border border-report-warning/40 bg-report-warning/10 px-4 py-3 text-sm leading-6 text-report-warning" role="status">
          Настройки сохранены. Чтобы применить порт или тайм-аут к текущему процессу, перезапустите сервер.
        </div>
      ) : null}
      <SettingsFormActions dirty={form.dirty} saving={form.saving} message={form.message} onSave={() => void form.save()} onCancel={form.cancel} />

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-normal text-report-text">Текущий runtime</h2>
            <p className="mt-2 text-sm leading-6 text-report-muted">Token скрыт. Полная ссылка не попадает в status payload или DOM dumps.</p>
          </div>
          <button className="toolbar-button" type="button" disabled={loading} onClick={() => loadStatus().catch(() => undefined)}>
            <RefreshCw size={16} aria-hidden="true" /> Обновить
          </button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Detail label="Статус" value={status?.running ? "запущен" : "остановлен"} />
          <Detail label="Host" value={status?.host || "127.0.0.1"} />
          <Detail label="Порт" value={String(status?.port ?? status?.configuredPort ?? status?.requested_port ?? "8766")} />
          <Detail label="Token" value="требуется, скрыт" />
          <Detail label="Статика" value={status?.static_available ? "доступна" : "fallback"} />
          <Detail label="Отчёт" value={status?.report_available ? "опубликован" : "не опубликован"} />
          <Detail label="Запущен" value={status?.started_at || "нет"} />
          <Detail label="Последний запрос" value={status?.last_request_at || "нет"} />
        </div>
        <p className="mt-4 break-words rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 font-mono text-sm text-report-muted">
          {status?.maskedUrl || "http://127.0.0.1:8766/?token=<hidden>#/home"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <ActionButton icon={ExternalLink} label="Открыть dashboard" busy={action === "open-dashboard"} onClick={() => runServerAction("open-dashboard")} />
          <ActionButton icon={Copy} label="Копировать безопасную ссылку" busy={action === "copy-url"} onClick={() => runServerAction("copy-url")} />
          <ActionButton icon={RotateCcw} label={confirmAction === "restart" ? "Подтвердить перезапуск" : "Перезапустить"} busy={action === "restart"} tone="warning" onClick={() => runServerAction("restart")} />
          <ActionButton icon={Power} label={confirmAction === "stop" ? "Подтвердить остановку" : "Остановить"} busy={action === "stop"} tone="warning" onClick={() => runServerAction("stop")} />
        </div>
        {statusMessage || status?.message ? <p className="mt-4 text-sm leading-6 text-report-muted" role="status">{statusMessage || status?.message}</p> : null}
      </section>
    </form>
  );
}

function ActionButton({ icon: Icon, label, busy, tone = "neutral", onClick }: {
  icon: typeof ExternalLink;
  label: string;
  busy: boolean;
  tone?: "neutral" | "warning";
  onClick: () => void;
}) {
  return (
    <button type="button" disabled={busy} onClick={onClick} className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${tone === "warning" ? "border-report-warning/40 bg-report-warning/10 text-report-warning" : "border-report-blue/35 bg-report-blue/10 text-report-blue"}`}>
      <Icon size={16} aria-hidden="true" /> {busy ? "Выполняю…" : label}
    </button>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-report-text">{value}</p>
    </div>
  );
}

function actionMessage(action: ServerAction): string {
  return {
    restart: "Перезапуск запланирован. Если token сменился, откройте dashboard из Anki заново.",
    stop: "Остановка сервера запланирована.",
    "open-dashboard": "Dashboard открыт.",
    "copy-url": "Ссылка скопирована.",
  }[action];
}

export default ServerSettingsPage;
