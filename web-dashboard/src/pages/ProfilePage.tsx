import { CalendarDays, Check, ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { dashboardToken } from "../lib/actionsApi";
import type { StudyReport } from "../types/report";

type DashboardPeriod = "all_time" | "last_7_days" | "last_30_days" | "custom";

type DeckOption = {
  id: number;
  name: string;
};

type DashboardDisplaySettings = {
  period: DashboardPeriod;
  custom_start_date: string;
  custom_end_date: string;
  selected_deck_ids: number[];
  selected_deck_names: string[];
  include_child_decks: boolean;
};

const periodOptions: Array<{ key: DashboardPeriod; label: string }> = [
  { key: "all_time", label: "Всё время" },
  { key: "last_7_days", label: "Неделя" },
  { key: "last_30_days", label: "Месяц" },
  { key: "custom", label: "От / до" },
];

const emptySettings: DashboardDisplaySettings = {
  period: "all_time",
  custom_start_date: "",
  custom_end_date: "",
  selected_deck_ids: [],
  selected_deck_names: [],
  include_child_decks: true,
};

function ProfilePage({
  report,
  onReportUpdated,
}: {
  report: StudyReport | null;
  onReportUpdated?: (report: StudyReport) => void;
}) {
  const [settings, setSettings] = useState<DashboardDisplaySettings>(emptySettings);
  const [deckOptions, setDeckOptions] = useState<DeckOption[]>([]);
  const [query, setQuery] = useState("");
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [saveState, setSaveState] = useState<"idle" | "saving">("idle");
  const [message, setMessage] = useState("");

  const loadSettings = useCallback(() => {
    const token = dashboardToken();
    setLoadState("loading");
    return fetch(`/api/dashboard/settings?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "forbidden" : "load_error");
        }
        return response.json();
      })
      .then((data) => {
        setSettings(normalizeSettings(data.settings));
        setDeckOptions(normalizeDeckOptions(data.deckOptions));
        setLoadState("ready");
        setMessage("");
      })
      .catch((error: Error) => {
        setLoadState("error");
        setMessage(error.message === "forbidden" ? "Недействительный dashboard token." : "Не удалось загрузить настройки.");
      });
  }, []);

  useEffect(() => {
    loadSettings().catch(() => undefined);
  }, [loadSettings]);

  const selectedDecks = useMemo(() => selectedDecksFor(settings, deckOptions), [deckOptions, settings]);

  const suggestions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return [];
    }
    const selected = new Set(settings.selected_deck_ids);
    return deckOptions
      .filter((deck) => !selected.has(deck.id))
      .filter((deck) => deck.name.toLowerCase().includes(normalizedQuery))
      .slice(0, 8);
  }, [deckOptions, query, settings.selected_deck_ids]);

  const saveSettings = (nextSettings: DashboardDisplaySettings = settings) => {
    const selectedNames = selectedDecksFor(nextSettings, deckOptions).map((deck) => deck.name);
    setSaveState("saving");
    setMessage("");
    fetch(`/api/dashboard/settings?token=${encodeURIComponent(dashboardToken())}`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...nextSettings,
        selected_deck_names: selectedNames,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status === 403 ? "forbidden" : "save_error");
        }
        return response.json();
      })
      .then((data) => {
        setSettings(normalizeSettings(data.settings));
        setDeckOptions(normalizeDeckOptions(data.deckOptions));
        if (isStudyReport(data.report)) {
          onReportUpdated?.(data.report);
        }
        setMessage(
          typeof data.reportRefreshError === "string" && data.reportRefreshError
            ? "Настройки сохранены, но отчёт не обновился автоматически."
            : "Настройки дашборда сохранены, отчёт обновлён.",
        );
      })
      .catch((error: Error) => {
        setMessage(error.message === "forbidden" ? "Недействительный dashboard token." : "Не удалось сохранить настройки.");
      })
      .finally(() => setSaveState("idle"));
  };

  const setPeriod = (period: DashboardPeriod) => {
    const nextSettings = { ...settings, period };
    setSettings(nextSettings);
    if (period !== "custom") {
      saveSettings(nextSettings);
    }
  };

  const addDeck = (deck: DeckOption) => {
    setSettings((current) => ({
      ...current,
      selected_deck_ids: current.selected_deck_ids.includes(deck.id)
        ? current.selected_deck_ids
        : [...current.selected_deck_ids, deck.id],
    }));
    setQuery("");
  };

  const removeDeck = (deckId: number) => {
    setSettings((current) => ({
      ...current,
      selected_deck_ids: current.selected_deck_ids.filter((id) => id !== deckId),
    }));
  };

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <span className={`status-pill status-${loadState === "error" ? "warning" : "neutral"}`}>
              настройки интерфейса
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Профиль</h1>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 text-sm font-medium text-report-blue transition hover:border-report-blue/70 disabled:cursor-not-allowed disabled:opacity-55"
            onClick={() => saveSettings()}
            disabled={loadState === "loading" || saveState === "saving"}
          >
            <Check size={16} aria-hidden="true" />
            {saveState === "saving" ? "Сохраняю..." : "Сохранить"}
          </button>
        </div>
        {message ? <p className="mt-4 text-sm leading-6 text-report-muted">{message}</p> : null}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Период отчёта</h2>
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          {periodOptions.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setPeriod(option.key)}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                settings.period === option.key
                  ? "border-report-blue/70 bg-report-blue/15 text-report-blue"
                  : "border-ink-700 bg-ink-900/45 text-report-muted hover:border-report-blue/45 hover:text-report-text"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {settings.period === "custom" ? (
          <div className="mt-4">
            <DateRangePicker
              startValue={settings.custom_start_date}
              endValue={settings.custom_end_date}
              onChange={(start, end) =>
                setSettings((current) => ({
                  ...current,
                  custom_start_date: start,
                  custom_end_date: end,
                }))
              }
            />
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-normal text-report-text">Колоды отчёта</h2>
            <p className="mt-1 text-sm text-report-muted">
              {selectedDecks.length ? `Выбрано: ${selectedDecks.length}` : "Все колоды"}
            </p>
          </div>
          <label className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm text-report-secondary transition hover:border-report-blue/45 hover:bg-ink-800/55">
            <input
              type="checkbox"
              checked={settings.include_child_decks}
              onChange={(event) => setSettings((current) => ({ ...current, include_child_decks: event.target.checked }))}
              className="dark-checkbox"
            />
            Включать дочерние колоды
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {selectedDecks.map((deck) => (
            <span key={deck.id} className="inline-flex max-w-full items-center gap-2 rounded-lg border border-report-blue/35 bg-report-blue/10 px-2.5 py-1 text-sm text-report-blue">
              <span className="truncate">{deck.name}</span>
              <button type="button" onClick={() => removeDeck(deck.id)} aria-label={`Убрать ${deck.name}`}>
                <X size={14} aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>

        <div className="relative mt-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Найти колоду"
            className="form-control w-full py-2.5 pl-10 pr-3 text-sm"
          />
        </div>
        {suggestions.length > 0 ? (
          <div className="mt-2 grid gap-2">
            {suggestions.map((deck) => (
              <button
                key={deck.id}
                type="button"
                onClick={() => addDeck(deck)}
                className="min-w-0 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-left text-sm text-report-text transition hover:border-report-blue/55"
              >
                <span className="block truncate">{deck.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <ScopeMetric label="Текущий период отчёта" value={report?.metadata.period || "Всё время"} />
        <ScopeMetric label="Текущие колоды отчёта" value={currentDeckScope(report)} />
      </section>
    </div>
  );
}

type RangeField = "start" | "end";

const weekdayLabels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });
const displayDateFormatter = new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", year: "numeric" });

function DateRangePicker({
  startValue,
  endValue,
  onChange,
}: {
  startValue: string;
  endValue: string;
  onChange: (start: string, end: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeField, setActiveField] = useState<RangeField>("start");
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(parseDateKey(startValue) ?? new Date()));
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const todayKey = formatDateKey(new Date());
  const days = useMemo(() => monthGrid(visibleMonth), [visibleMonth]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const openPicker = (field: RangeField) => {
    setActiveField(field);
    const source = parseDateKey(field === "start" ? startValue : endValue) ?? parseDateKey(startValue) ?? new Date();
    setVisibleMonth(startOfMonth(source));
    setOpen(true);
  };

  const selectDate = (dateKey: string) => {
    if (activeField === "start") {
      onChange(dateKey, endValue && endValue < dateKey ? "" : endValue);
      setActiveField("end");
      return;
    }
    if (startValue && dateKey < startValue) {
      onChange(dateKey, startValue);
      setActiveField("start");
      return;
    }
    onChange(startValue, dateKey);
  };

  const selectToday = () => {
    selectDate(todayKey);
    setVisibleMonth(startOfMonth(new Date()));
  };

  const clearRange = () => {
    onChange("", "");
    setActiveField("start");
  };

  return (
    <div ref={wrapperRef} className="relative grid gap-2">
      <div className="grid gap-3 sm:grid-cols-2">
        <DateTrigger label="От" value={startValue} active={open && activeField === "start"} onClick={() => openPicker("start")} />
        <DateTrigger label="До" value={endValue} active={open && activeField === "end"} onClick={() => openPicker("end")} />
      </div>
      {open ? (
        <div className="popover-motion absolute left-0 top-[calc(100%+0.75rem)] z-30 w-full max-w-[420px] rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-[0_24px_80px_rgba(3,8,20,0.42)]">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-ink-700 bg-ink-900 text-report-muted transition hover:border-report-blue/60 hover:text-report-text focus:outline-none focus:ring-2 focus:ring-report-blue/50"
              onClick={() => setVisibleMonth((current) => addMonths(current, -1))}
              aria-label="Предыдущий месяц"
            >
              <ChevronLeft size={16} aria-hidden="true" />
            </button>
            <div className="text-sm font-semibold capitalize text-report-text">{monthFormatter.format(visibleMonth)}</div>
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-ink-700 bg-ink-900 text-report-muted transition hover:border-report-blue/60 hover:text-report-text focus:outline-none focus:ring-2 focus:ring-report-blue/50"
              onClick={() => setVisibleMonth((current) => addMonths(current, 1))}
              aria-label="Следующий месяц"
            >
              <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="mt-4 grid grid-cols-7 gap-1 text-center text-[11px] font-medium uppercase text-report-muted">
            {weekdayLabels.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
          <div className="mt-2 grid grid-cols-7 gap-1">
            {days.map((day) => {
              const key = formatDateKey(day);
              const inMonth = day.getMonth() === visibleMonth.getMonth();
              const selected = key === startValue || key === endValue;
              const inRange = Boolean(startValue && endValue && key > startValue && key < endValue);
              const today = key === todayKey;
              return (
                <button
                  key={key}
                  type="button"
                  className={[
                    "h-9 rounded-lg border text-sm transition focus:outline-none focus:ring-2 focus:ring-report-blue/55",
                    selected
                      ? "border-report-blue/80 bg-report-blue/25 text-report-text shadow-glow"
                      : inRange
                        ? "border-report-blue/10 bg-report-blue/10 text-report-text"
                        : "border-transparent text-report-muted hover:border-ink-700 hover:bg-ink-800 hover:text-report-text",
                    today && !selected ? "ring-1 ring-report-warning/70" : "",
                    inMonth ? "" : "opacity-40",
                  ].join(" ")}
                  onClick={() => selectDate(key)}
                  aria-label={displayDateKey(key)}
                >
                  {day.getDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-ink-700 pt-3">
            <p className="text-xs text-report-muted">
              {activeField === "start" ? "Выберите дату начала" : "Выберите дату окончания"}
            </p>
            <div className="flex gap-2">
              <button type="button" className="toolbar-button px-2.5 py-1.5 text-xs" onClick={selectToday}>
                Сегодня
              </button>
              <button type="button" className="toolbar-button toolbar-button-warning px-2.5 py-1.5 text-xs" onClick={clearRange}>
                Очистить
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function DateTrigger({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={[
        "grid min-h-16 gap-1 rounded-lg border bg-ink-900/55 px-3 py-2 text-left transition focus:outline-none focus:ring-2 focus:ring-report-blue/55",
        active ? "border-report-blue/70 bg-report-blue/10" : "border-ink-700 hover:border-report-blue/45 hover:bg-ink-900",
      ].join(" ")}
      onClick={onClick}
    >
      <span className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.04em] text-report-muted">
        {label}
        <CalendarDays size={15} aria-hidden="true" />
      </span>
      <span className="text-sm font-semibold text-report-text">{value ? displayDateKey(value) : "Выбрать дату"}</span>
    </button>
  );
}

function parseDateKey(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function displayDateKey(value: string): string {
  const date = parseDateKey(value);
  return date ? displayDateFormatter.format(date) : value;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}

function monthGrid(month: Date): Date[] {
  const firstDay = startOfMonth(month);
  const mondayOffset = (firstDay.getDay() + 6) % 7;
  const start = new Date(firstDay);
  start.setDate(firstDay.getDate() - mondayOffset);
  return Array.from({ length: 42 }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
}

function ScopeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-850 px-4 py-3 shadow-panel">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold leading-6 text-report-text">{value}</p>
    </div>
  );
}

function normalizeSettings(value: unknown): DashboardDisplaySettings {
  const data = value && typeof value === "object" ? (value as Partial<DashboardDisplaySettings>) : {};
  const period = isDashboardPeriod(data.period) ? data.period : "all_time";
  return {
    period,
    custom_start_date: typeof data.custom_start_date === "string" ? data.custom_start_date : "",
    custom_end_date: typeof data.custom_end_date === "string" ? data.custom_end_date : "",
    selected_deck_ids: Array.isArray(data.selected_deck_ids)
      ? data.selected_deck_ids.filter((item): item is number => typeof item === "number" && Number.isFinite(item))
      : [],
    selected_deck_names: Array.isArray(data.selected_deck_names)
      ? data.selected_deck_names.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [],
    include_child_decks: data.include_child_decks !== false,
  };
}

function normalizeDeckOptions(value: unknown): DeckOption[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (item && typeof item === "object" ? (item as Partial<DeckOption>) : null))
    .filter((item): item is Partial<DeckOption> => Boolean(item))
    .map((item) => ({
      id: typeof item.id === "number" && Number.isFinite(item.id) ? item.id : 0,
      name: typeof item.name === "string" ? item.name : "",
    }))
    .filter((item) => item.id !== 0 && item.name.trim().length > 0);
}

function isDashboardPeriod(value: unknown): value is DashboardPeriod {
  return value === "all_time" || value === "last_7_days" || value === "last_30_days" || value === "custom";
}

function isStudyReport(value: unknown): value is StudyReport {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<StudyReport>;
  return Boolean(data.metadata && data.summary && Array.isArray(data.kpis));
}

function currentDeckScope(report: StudyReport | null): string {
  const decks = report?.metadata.selectedDecks.filter((deck) => deck.trim().length > 0) ?? [];
  if (decks.length === 0 || (decks.length === 1 && decks[0].toLowerCase() === "все колоды")) {
    return "Все колоды";
  }
  if (decks.length <= 3) {
    return decks.join(", ");
  }
  return `${decks.length} колод: ${decks.slice(0, 3).join(", ")} + ещё ${decks.length - 3}`;
}

function selectedDecksFor(settings: DashboardDisplaySettings, deckOptions: DeckOption[]): DeckOption[] {
  const deckNameById = new Map(deckOptions.map((deck) => [deck.id, deck.name]));
  return settings.selected_deck_ids.map((id) => ({
    id,
    name: deckNameById.get(id) || `Колода ${id}`,
  }));
}

export default ProfilePage;
