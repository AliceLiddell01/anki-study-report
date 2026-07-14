import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DeckOption } from "../types/settings";

export function SettingsPageHeader({ title, description, status }: { title: string; description: string; status?: string }) {
  return (
    <header className="settings-page-header rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
      {status ? <span className="status-pill status-neutral">{status}</span> : null}
      <h1 className={`${status ? "mt-4 " : ""}text-2xl font-semibold tracking-normal text-report-text sm:text-3xl`}>{title}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">{description}</p>
    </header>
  );
}

export function SettingsSection({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="settings-section rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
      <h2 className="text-lg font-semibold tracking-normal text-report-text">{title}</h2>
      {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-report-muted">{description}</p> : null}
      <div className="mt-4 divide-y divide-ink-700/80">{children}</div>
    </section>
  );
}

export function SettingRow({ id, label, description, error, children }: {
  id: string;
  label: string;
  description: string;
  error?: string;
  children: ReactNode;
}) {
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  return (
    <div className="grid gap-3 py-4 first:pt-0 last:pb-0 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.72fr)] lg:items-center">
      <div className="min-w-0">
        <label className="text-sm font-semibold text-report-text" htmlFor={id}>{label}</label>
        <p className="mt-1 text-sm leading-6 text-report-muted" id={descriptionId}>{description}</p>
        {error ? <p className="mt-2 text-sm text-report-danger" id={errorId} role="alert">{error}</p> : null}
      </div>
      <div className="min-w-0" data-control-id={id}>{children}</div>
    </div>
  );
}

export function CheckboxControl({ id, checked, onChange, descriptionId }: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  descriptionId?: string;
}) {
  return (
    <input
      id={id}
      type="checkbox"
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
      aria-describedby={descriptionId || `${id}-description`}
      className="dark-checkbox h-5 w-5"
    />
  );
}

export function DeckMultiSelect({
  id,
  options,
  selectedIds,
  onChange,
  disabled,
  error,
}: {
  id: string;
  options: DeckOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
  error?: string;
}) {
  const { t } = useTranslation("pages");
  const knownIds = new Set(options.map((option) => option.id));
  const stale = selectedIds.filter((idValue) => !knownIds.has(idValue));
  return (
    <select
      id={id}
      multiple
      size={Math.min(8, Math.max(4, options.length + stale.length))}
      className="form-control w-full px-3 py-2 text-sm"
      value={selectedIds.map(String)}
      disabled={disabled}
      aria-describedby={`${id}-description${error ? ` ${id}-error` : ""}`}
      aria-invalid={Boolean(error)}
      onChange={(event) => onChange(Array.from(event.currentTarget.selectedOptions, (option) => Number(option.value)))}
    >
      {options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
      {stale.map((deckId) => <option key={deckId} value={deckId}>{t("settingsCommon.unavailableDeck", { id: deckId })}</option>)}
    </select>
  );
}

export function SettingsFormActions({ dirty, saving, message, onSave, onCancel }: {
  dirty: boolean;
  saving: boolean;
  message: string;
  onSave: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation(["pages", "common"]);
  return (
    <div className="settings-actions flex flex-wrap items-center gap-3 rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel">
      <button
        type="button"
        className="rounded-lg border border-report-blue/50 bg-report-blue/15 px-4 py-2 text-sm font-semibold text-report-text transition hover:border-report-blue disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!dirty || saving}
        onClick={onSave}
      >
        {saving ? t("settingsCommon.saving") : t("actions.saveChanges", { ns: "common" })}
      </button>
      <button
        type="button"
        className="rounded-lg border border-ink-700 bg-ink-900 px-4 py-2 text-sm font-medium text-report-secondary transition hover:border-report-blue/50 hover:text-report-text disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!dirty || saving}
        onClick={onCancel}
      >
        {t("settingsCommon.cancelChanges")}
      </button>
      <p className="min-w-0 flex-1 text-sm text-report-muted" role="status" aria-live="polite">
        {message || (dirty ? t("settingsCommon.unsaved") : t("settingsCommon.saved"))}
      </p>
    </div>
  );
}
