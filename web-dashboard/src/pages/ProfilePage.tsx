import { CalendarDays, Clock3, Layers3, Pencil, RotateCcw, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { enumerateDateKeys, formatShortDate, isDateKey, todayDateKey } from "../lib/dateUtils";
import { formatDurationSeconds, formatInteger, formatPercent } from "../lib/formatters";
import { saveProfilePreferences, type ProfileApiResponse } from "../lib/profileApi";
import type { ProfileDeckSort, ProfileModel, StudyReport } from "../types/report";

type Props = {
  report: StudyReport | null;
  onReportUpdated?: (report: StudyReport) => void;
};

function ProfilePage({ report, onReportUpdated }: Props) {
  const profile = report?.profile ?? emptyProfile;
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draftDate, setDraftDate] = useState(profile.preferences.customStudyStartedOn ?? "");
  const [fieldError, setFieldError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setDraftDate(profile.preferences.customStudyStartedOn ?? "");
  }, [profile.preferences.customStudyStartedOn]);

  const applyProfile = (next: ProfileModel) => {
    if (report && onReportUpdated) {
      onReportUpdated({ ...report, profile: next });
    }
  };

  const saveDeckSort = async (deckOverviewSort: ProfileDeckSort) => {
    setSaving(true);
    setMessage("Сохраняем порядок колод…");
    const result: ProfileApiResponse = await saveProfilePreferences({ deckOverviewSort }).catch(() => ({ ok: false }));
    setSaving(false);
    if (result.ok && result.profile) {
      applyProfile(result.profile);
      setMessage("Порядок колод сохранён.");
    } else {
      setMessage("Не удалось сохранить порядок колод.");
    }
  };

  const openDialog = () => {
    setDraftDate(profile.preferences.customStudyStartedOn ?? "");
    setFieldError("");
    setMessage("");
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  };

  const saveDate = async (value: string | null) => {
    if (value && (!isDateKey(value) || value > todayDateKey())) {
      setFieldError(value > todayDateKey() ? "Дата начала не может быть в будущем." : "Укажите корректную дату.");
      return;
    }
    setSaving(true);
    setFieldError("");
    setMessage("Сохраняем дату начала…");
    const result: ProfileApiResponse = await saveProfilePreferences({ customStudyStartedOn: value }).catch(() => ({ ok: false }));
    setSaving(false);
    if (result.ok && result.profile) {
      applyProfile(result.profile);
      setMessage(value ? "Дата начала сохранена." : "Возвращена найденная дата начала.");
      closeDialog();
      return;
    }
    setFieldError(result.fieldErrors?.customStudyStartedOn ?? "Не удалось сохранить дату.");
    setMessage("");
  };

  return (
    <div className="profile-page grid gap-5" data-testid="profile-page">
      <ProfileHero profile={profile} onEdit={openDialog} triggerRef={triggerRef} />

      <section aria-labelledby="profile-kpi-title">
        <h2 id="profile-kpi-title" className="sr-only">Учебный путь</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <Kpi label="Всего повторений" value={formatInteger(profile.studyHistory.totalReviews)} caption="за всю доступную историю" />
          <Kpi label="Активных дней" value={formatInteger(profile.studyHistory.activeDays)} caption="дни с повторениями" />
          <Kpi label="Текущая серия" value={formatDays(profile.studyHistory.currentStreak)} caption="сегодня или до вчера" />
          <Kpi label="Лучшая серия" value={formatDays(profile.studyHistory.bestStreak)} caption="за доступную историю" />
          <Kpi label="Время учёбы" value={formatDurationSeconds(profile.studyHistory.studyTimeSeconds)} caption={studyTimeCaption(profile.studyHistory.studyTimeSource)} />
          <Kpi label="Средняя успешность" value={formatPercent(profile.studyHistory.averagePassRate)} caption="Pass среди учтённых ответов" />
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <ActivityHeatmap profile={profile} />
        <RecentActivity profile={profile} />
      </div>

      <DeckOverview profile={profile} saving={saving} onSort={saveDeckSort} />
      <p className="sr-only" role="status" aria-live="polite">{message}</p>

      {dialogOpen ? (
        <StudyStartDialog
          value={draftDate}
          detectedDate={profile.studyHistory.detectedStartedOn}
          hasOverride={Boolean(profile.preferences.customStudyStartedOn)}
          error={fieldError}
          saving={saving}
          onChange={(value) => { setDraftDate(value); setFieldError(""); }}
          onSave={() => void saveDate(draftDate || null)}
          onReset={() => void saveDate(null)}
          onClose={closeDialog}
        />
      ) : null}
    </div>
  );
}

function ProfileHero({ profile, onEdit, triggerRef }: { profile: ProfileModel; onEdit: () => void; triggerRef: RefObject<HTMLButtonElement> }) {
  const history = profile.studyHistory;
  return (
    <section className="profile-hero overflow-hidden rounded-2xl border border-ink-700 bg-ink-850 shadow-panel" aria-labelledby="profile-heading" data-testid="profile-hero">
      <div className="relative h-32 overflow-hidden bg-gradient-to-br from-report-blue/35 via-violet-500/20 to-emerald-400/15 sm:h-40" data-testid="profile-banner" aria-hidden="true">
        <span className="absolute -right-16 -top-24 h-64 w-64 rounded-full bg-report-blue/20 blur-3xl" />
        <span className="absolute -bottom-28 left-1/4 h-56 w-56 rounded-full bg-violet-400/15 blur-3xl" />
      </div>
      <div className="relative px-5 pb-6 sm:px-7">
        <div className="-mt-12 flex flex-col gap-4 sm:-mt-14 sm:flex-row sm:items-end">
          <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border-4 border-ink-850 bg-ink-800 text-2xl font-semibold text-report-blue shadow-panel sm:h-28 sm:w-28" data-testid="profile-avatar" aria-label={`Аватар: инициалы ${profile.identity.initials}`}>
            {profile.identity.initials}
          </div>
          <div className="min-w-0 flex-1 pb-1">
            <span className="status-pill status-neutral">{profile.identity.label}</span>
            <h1 id="profile-heading" className="mt-3 break-words text-2xl font-semibold tracking-normal text-report-text sm:text-3xl" title={profile.identity.displayName}>
              {profile.identity.displayName}
            </h1>
          </div>
        </div>
        <div className="mt-5 flex flex-col gap-3 text-sm leading-6 text-report-muted sm:flex-row sm:items-end sm:justify-between">
          <div>
            {history.displayedStartedOn ? <p>В Anki с {formatMonthYear(history.displayedStartedOn)} · {formatDays(history.activeDays)} активности</p> : <p>Учебная история пока не найдена</p>}
            {history.displayedStartedOn && history.statsAvailableFrom && history.displayedStartedOn !== history.statsAvailableFrom ? (
              <p>Статистика доступна с {formatMonthYear(history.statsAvailableFrom)}</p>
            ) : null}
          </div>
          <button ref={triggerRef} type="button" className="inline-flex w-fit items-center gap-2 rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm font-medium text-report-text transition hover:border-report-blue/55 focus:outline-none focus:ring-2 focus:ring-report-blue/55" onClick={onEdit}>
            <Pencil size={15} aria-hidden="true" /> Изменить дату начала
          </button>
        </div>
      </div>
    </section>
  );
}

function Kpi({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <article className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel" aria-label={`${label}: ${value}`}>
      <p className="text-xs font-medium uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-3 break-words text-2xl font-semibold text-report-text">{value}</p>
      <p className="mt-2 text-xs leading-5 text-report-muted">{caption}</p>
    </article>
  );
}

function ActivityHeatmap({ profile }: { profile: ProfileModel }) {
  const activity = profile.activity;
  const dayMap = useMemo(() => new Map(activity.days.map((day) => [day.date, day])), [activity.days]);
  const dates = activity.rangeStart && activity.rangeEnd ? enumerateDateKeys(activity.rangeStart, activity.rangeEnd) : [];
  const maxReviews = Math.max(1, ...activity.days.map((day) => day.reviews));
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel" aria-labelledby="profile-activity-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="profile-activity-title" className="text-lg font-semibold text-report-text">История активности</h2>
          <p className="mt-1 text-sm text-report-muted">До 26 последних недель доступной истории</p>
        </div>
        <a href="#/calendar" className="text-sm font-medium text-report-blue underline-offset-4 hover:underline">Открыть календарь</a>
      </div>
      {dates.length ? (
        <div className="mt-5 grid grid-cols-[repeat(auto-fill,minmax(14px,1fr))] gap-1.5" role="img" aria-label={`Активность с ${activity.rangeStart} по ${activity.rangeEnd}`} data-testid="profile-heatmap">
          {dates.map((date) => {
            const day = dayMap.get(date);
            const reviews = day?.reviews ?? 0;
            const intensity = reviews ? Math.max(0.18, reviews / maxReviews) : 0;
            return <span key={date} className="aspect-square min-h-3 rounded-[3px] border border-ink-700/70 bg-ink-900" style={reviews ? { backgroundColor: `rgb(61 180 242 / ${intensity})` } : undefined} title={`${date}: ${reviews} повторений`} aria-label={`${date}: ${reviews} повторений`} />;
          })}
        </div>
      ) : (
        <Empty icon={<CalendarDays size={20} aria-hidden="true" />} text="История активности появится после первых повторений." />
      )}
    </section>
  );
}

function RecentActivity({ profile }: { profile: ProfileModel }) {
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel" aria-labelledby="recent-study-title">
      <h2 id="recent-study-title" className="text-lg font-semibold text-report-text">Последние занятия</h2>
      {profile.activity.recentActiveDays.length ? (
        <ol className="mt-4 grid gap-2" data-testid="profile-recent-days">
          {profile.activity.recentActiveDays.map((day) => (
            <li key={day.date} className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2.5">
              <p className="font-medium text-report-text">{formatLongDate(day.date)}</p>
              <p className="mt-1 text-sm text-report-muted">{recentDaySummary(day.reviews, day.studySeconds, day.passRate)}</p>
            </li>
          ))}
        </ol>
      ) : <Empty icon={<Clock3 size={20} aria-hidden="true" />} text="Недавних активных дней пока нет." />}
    </section>
  );
}

function DeckOverview({ profile, saving, onSort }: { profile: ProfileModel; saving: boolean; onSort: (sort: ProfileDeckSort) => void }) {
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel" aria-labelledby="profile-decks-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="profile-decks-title" className="text-lg font-semibold text-report-text">Колоды</h2>
          <p className="mt-1 text-sm text-report-muted">Спокойный обзор всей коллекции · {formatInteger(profile.decks.total)} всего</p>
        </div>
        <label className="grid gap-1 text-sm text-report-muted" htmlFor="profile-deck-sort">
          Сортировка
          <select id="profile-deck-sort" className="form-control min-w-52 px-3 py-2 text-sm text-report-text" value={profile.preferences.deckOverviewSort} disabled={saving} onChange={(event) => onSort(event.target.value as ProfileDeckSort)}>
            <option value="name">По имени</option>
            <option value="reviews">По числу повторений</option>
            <option value="active_days">По активным дням</option>
          </select>
        </label>
      </div>
      {profile.decks.overview.length ? (
        <div className="mt-5 grid gap-2" data-testid="profile-decks">
          {profile.decks.overview.map((deck) => (
            <article key={deck.id} className="grid gap-2 rounded-lg border border-ink-700 bg-ink-900/45 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center sm:gap-6">
              <h3 className="min-w-0 break-words font-medium text-report-text" title={deck.name}>{deck.name}</h3>
              <p className="text-sm text-report-muted"><span className="font-semibold text-report-text">{formatInteger(deck.totalReviews)}</span> повторений</p>
              <p className="text-sm text-report-muted"><span className="font-semibold text-report-text">{formatInteger(deck.activeDays)}</span> активных дней</p>
            </article>
          ))}
        </div>
      ) : <Empty icon={<Layers3 size={20} aria-hidden="true" />} text="Колоды появятся здесь после первых повторений." />}
      <a href="#/decks" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-report-blue underline-offset-4 hover:underline">Открыть все колоды</a>
    </section>
  );
}

function StudyStartDialog({ value, detectedDate, hasOverride, error, saving, onChange, onSave, onReset, onClose }: { value: string; detectedDate: string | null; hasOverride: boolean; error: string; saving: boolean; onChange: (value: string) => void; onSave: () => void; onReset: () => void; onClose: () => void }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { inputRef.current?.focus(); }, []);
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
    if (event.key !== "Tab") return;
    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])') ?? []);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="study-start-title" aria-describedby="study-start-description" className="w-full max-w-lg rounded-2xl border border-ink-700 bg-ink-850 p-5 shadow-[var(--shadow-popover)] sm:p-6" onKeyDown={handleKeyDown}>
        <div className="flex items-start justify-between gap-4">
          <div><h2 id="study-start-title" className="text-xl font-semibold text-report-text">Дата начала обучения</h2><p id="study-start-description" className="mt-2 text-sm leading-6 text-report-muted">Дата помогает рассказать вашу историю, но не добавляет отсутствующие повторения и не меняет серии или метрики.</p></div>
          <button type="button" className="rounded-lg p-2 text-report-muted hover:bg-ink-800 hover:text-report-text focus:outline-none focus:ring-2 focus:ring-report-blue/55" aria-label="Закрыть" onClick={onClose}><X size={18} /></button>
        </div>
        <p className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm text-report-muted">Найденная дата статистики: <span className="font-medium text-report-text">{detectedDate ? formatShortDate(detectedDate) : "не найдена"}</span></p>
        <label htmlFor="profile-study-start" className="mt-4 grid gap-2 text-sm font-medium text-report-text">Когда вы начали учиться
          <input ref={inputRef} id="profile-study-start" type="date" className="form-control px-3 py-2.5 text-sm" value={value} max={todayDateKey()} aria-invalid={Boolean(error)} aria-describedby={error ? "profile-study-start-error" : undefined} onChange={(event) => onChange(event.target.value)} />
        </label>
        {error ? <p id="profile-study-start-error" className="mt-2 text-sm text-report-danger" role="alert">{error}</p> : null}
        <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
          {hasOverride ? <button type="button" className="mr-auto inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-report-muted hover:bg-ink-800 hover:text-report-text" disabled={saving} onClick={onReset}><RotateCcw size={15} aria-hidden="true" /> Сбросить к найденной дате</button> : null}
          <button type="button" className="rounded-lg border border-ink-700 px-4 py-2 text-sm font-medium text-report-text hover:bg-ink-800" disabled={saving} onClick={onClose}>Отмена</button>
          <button type="button" className="inline-flex items-center gap-2 rounded-lg border border-report-blue/55 bg-report-blue/20 px-4 py-2 text-sm font-semibold text-report-text hover:border-report-blue disabled:opacity-55" disabled={saving} onClick={onSave}><Sparkles size={15} aria-hidden="true" /> {saving ? "Сохраняем…" : "Сохранить"}</button>
        </div>
      </div>
    </div>
  );
}

function Empty({ icon, text }: { icon: ReactNode; text: string }) { return <div className="mt-5 flex items-center gap-3 rounded-lg border border-ink-700 bg-ink-900/45 p-4 text-sm text-report-muted">{icon}<p>{text}</p></div>; }
function formatDays(value: number) { const n = Math.max(0, Math.round(value)); const mod10 = n % 10; const mod100 = n % 100; const word = mod10 === 1 && mod100 !== 11 ? "день" : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? "дня" : "дней"; return `${formatInteger(n)} ${word}`; }
function formatMonthYear(value: string) { const date = new Date(`${value}T12:00:00`); const months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]; return Number.isNaN(date.getTime()) ? "неизвестной даты" : `${months[date.getMonth()]} ${date.getFullYear()} года`; }
function formatLongDate(value: string) { const date = new Date(`${value}T12:00:00`); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" }); }
function studyTimeCaption(source: ProfileModel["studyHistory"]["studyTimeSource"]) { return source === "study_time_stats" ? "по данным Study Time Stats" : source === "session_tracker" ? "по трекеру сессий" : source === "revlog_estimate" ? "оценка по истории ответов" : "источник времени недоступен"; }
function recentDaySummary(reviews: number, seconds: number | null, passRate: number | null) { return [
  `${formatInteger(reviews)} повторений`,
  seconds ? formatDurationSeconds(seconds) : null,
  passRate === null ? null : formatPercent(passRate),
].filter(Boolean).join(" · "); }

const emptyProfile: ProfileModel = {
  identity: { ankiProfileName: null, displayName: "Пользователь Anki", initials: "ПА", label: "Локальный профиль" },
  studyHistory: { detectedStartedOn: null, customStartedOn: null, displayedStartedOn: null, statsAvailableFrom: null, totalReviews: 0, activeDays: 0, currentStreak: 0, bestStreak: 0, studyTimeSeconds: null, studyTimeSource: null, averagePassRate: null },
  activity: { days: [], recentActiveDays: [], rangeStart: null, rangeEnd: null },
  decks: { overview: [], total: 0, limit: 8, aggregation: "canonical_current_deck" },
  preferences: { customStudyStartedOn: null, deckOverviewSort: "name" },
};

export default ProfilePage;
