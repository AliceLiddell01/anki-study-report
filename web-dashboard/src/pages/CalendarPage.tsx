import { CalendarDays, ChevronDown, Clock3, Flame, History, Layers3, RotateCcw, Trophy } from "lucide-react";
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";
import {
  activityDayMap,
  activityDaysForPeriod,
  activityMetricIntensity,
  activityMetricValue,
  activityOverview,
  visibleActivityFeed,
} from "../lib/activityHub";
import { addDays, formatShortDate, localizedWeekdayLabels } from "../lib/dateUtils";
import { formatDurationSeconds, formatInteger, formatPercent } from "../lib/formatters";
import type {
  ActivityFeedDay,
  ActivityHighlight,
  ActivityHubDay,
  ActivityHubModel,
  ActivityMetric,
  ActivityPeriod,
  ActivityWeekSummary,
  StudyReport,
} from "../types/report";
import type { LoadState } from "./HomePage";

const metricOptions: ActivityMetric[] = ["reviews", "study_time", "new_cards", "success_rate"];

const periodOptions: ActivityPeriod[] = ["30d", "90d", "6m", "1y"];

function CalendarPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages");
  const hub = report?.activityHub;
  const [metric, setMetric] = useState<ActivityMetric>("reviews");
  const [period, setPeriod] = useState<ActivityPeriod>("90d");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [focusedDate, setFocusedDate] = useState<string | null>(null);
  const [decksExpanded, setDecksExpanded] = useState(false);
  const [feedLimit, setFeedLimit] = useState(14);

  if (loadState !== "ready") return <ActivityLoadState state={loadState} />;
  if (!hub || !report) return <ActivityEmptyState />;

  const days = activityDaysForPeriod(hub, period);
  const dayMap = activityDayMap(days);
  const effectiveSelected = selectedDate && dayMap.has(selectedDate) ? selectedDate : hub.today;
  const selectedDay = dayMap.get(effectiveSelected) ?? null;
  const overview = activityOverview(days, hub.overview.currentStreak);
  const feed = visibleActivityFeed(hub, period, feedLimit);
  const allDayMap = activityDayMap(hub.days);
  const observations = buildObservations(feed.days, feed.weeks);
  const hasAnyHistory = Boolean(hub.bounds.availableFrom);

  const changePeriod = (next: ActivityPeriod) => {
    setPeriod(next);
    setSelectedDate(hub.today);
    setFocusedDate(hub.today);
    setFeedLimit(hub.feed.pageSize || 14);
    setDecksExpanded(false);
  };

  return (
    <div className="activity-page grid min-w-0 gap-5" data-testid="activity-page">
      <header className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <h1 className="text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{t("activity.title")}</h1>
        <p className="mt-2 text-sm leading-6 text-report-muted">{t("activity.description")}</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard icon={<CalendarDays size={18} />} label={t("activity.activeDays")} value={formatInteger(overview.activeDays)} />
          <SummaryCard icon={<Flame size={18} />} label={t("activity.currentStreak")} value={formatDays(overview.currentStreak)} />
          <SummaryCard icon={<Trophy size={18} />} label={t("activity.bestStreak")} value={formatDays(overview.bestStreak)} />
          <SummaryCard icon={<Layers3 size={18} />} label={t("activity.periodReviews")} value={formatInteger(overview.reviews)} />
        </div>
        {observations.length ? (
          <ul className="mt-4 flex flex-wrap gap-2" aria-label={t("activity.observations")}>
            {observations.map((text) => <li key={text} className="rounded-full border border-ink-700 bg-ink-900/45 px-3 py-1.5 text-sm text-report-muted">{text}</li>)}
          </ul>
        ) : null}
      </header>

      {!hasAnyHistory ? <ActivityEmptyState embedded /> : (
        <>
          <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5" aria-labelledby="activity-calendar-title">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <h2 id="activity-calendar-title" className="text-lg font-semibold text-report-text">{t("activity.calendar")}</h2>
                <p className="mt-1 text-sm leading-6 text-report-muted">{hub.periods[period].start} — {hub.periods[period].end}</p>
              </div>
              <div className="flex flex-col gap-3 lg:flex-row">
                <div className="grid grid-cols-2 gap-1 rounded-xl border border-ink-700 bg-ink-900/45 p-1.5 sm:grid-cols-4" aria-label={t("activity.calendarMetric")}>
                  {metricOptions.map((option) => (
                    <button key={option} type="button" aria-pressed={metric === option} className={metric === option ? activeControlClass : idleControlClass} onClick={() => setMetric(option)}>{t(`activity.metrics.${option}`)}</button>
                  ))}
                </div>
                <label className="grid gap-1 text-xs font-medium text-report-muted" htmlFor="activity-period">
                  {t("activity.period")}
                  <span className="relative block min-w-52">
                    <select id="activity-period" value={period} onChange={(event) => changePeriod(event.target.value as ActivityPeriod)} className="form-control min-h-11 w-full appearance-none rounded-xl px-3 py-2.5 pr-9 text-sm text-report-text">
                      {periodOptions.map((option) => <option key={option} value={option}>{t(`activity.periods.${option}`)}</option>)}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} aria-hidden="true" />
                  </span>
                </label>
              </div>
            </div>

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
              <div>
                <ActivityCalendar
                  days={days}
                  metric={metric}
                  selectedDate={effectiveSelected}
                  focusedDate={focusedDate ?? effectiveSelected}
                  onFocus={setFocusedDate}
                  onSelect={(date) => { setSelectedDate(date); setFocusedDate(date); setDecksExpanded(false); }}
                />
                <CalendarLegend metric={metric} />
              </div>
              <DayDetail day={selectedDay} hub={hub} expanded={decksExpanded} onToggle={() => setDecksExpanded((value) => !value)} />
            </div>
          </section>

          <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5" aria-labelledby="activity-history-title">
            <div className="flex items-start gap-3">
              <span className="kpi-icon"><History size={18} aria-hidden="true" /></span>
              <div><h2 id="activity-history-title" className="text-lg font-semibold text-report-text">{t("activity.history")}</h2><p className="mt-1 text-sm text-report-muted">{t("activity.historyDescription")}</p></div>
            </div>
            {feed.days.length ? (
              <ActivityFeed days={feed.days} weeks={feed.weeks} dayMap={allDayMap} />
            ) : (
              <div className="mt-5 rounded-lg border border-dashed border-ink-700 bg-ink-900/35 p-5 text-center"><p className="font-medium text-report-text">{t("activity.noActivity")}</p><p className="mt-2 text-sm text-report-muted">{t("activity.noActivityDescription")}</p></div>
            )}
            {feed.hasMore ? (
              <button type="button" className="mt-5 rounded-lg border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm font-semibold text-report-text hover:border-report-blue/55 focus:outline-none focus:ring-2 focus:ring-report-blue/55" onClick={() => setFeedLimit((value) => value + (hub.feed.pageSize || 14))}>
                {t("activity.loadEarlier")}
              </button>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}

function ActivityCalendar({ days, metric, selectedDate, focusedDate, onFocus, onSelect }: { days: ActivityHubDay[]; metric: ActivityMetric; selectedDate: string; focusedDate: string; onFocus: (date: string) => void; onSelect: (date: string) => void }) {
  const { i18n: activeI18n } = useTranslation("pages");
  const refs = useRef(new Map<string, HTMLButtonElement>());
  const dates = useMemo(() => new Set(days.map((day) => day.date)), [days]);
  const months = useMemo(() => groupMonths(days), [days, activeI18n.resolvedLanguage]);
  const moveFocus = (date: string, offset: number) => {
    const next = addDays(date, offset);
    if (!next || !dates.has(next)) return;
    onFocus(next);
    window.requestAnimationFrame(() => refs.current.get(next)?.focus());
  };
  const handleKey = (event: KeyboardEvent<HTMLButtonElement>, day: ActivityHubDay) => {
    const weekday = mondayIndex(day.date);
    if (event.key === "ArrowLeft") { event.preventDefault(); moveFocus(day.date, -1); }
    else if (event.key === "ArrowRight") { event.preventDefault(); moveFocus(day.date, 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); moveFocus(day.date, -7); }
    else if (event.key === "ArrowDown") { event.preventDefault(); moveFocus(day.date, 7); }
    else if (event.key === "Home") { event.preventDefault(); moveFocus(day.date, -weekday); }
    else if (event.key === "End") { event.preventDefault(); moveFocus(day.date, 6 - weekday); }
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(day.date); }
  };
  return (
    <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3" data-testid="activity-calendar">
      {months.map((month) => (
        <section key={month.key} className="rounded-lg border border-ink-700 bg-ink-900/30 p-3" aria-label={month.label}>
          <h3 className="text-sm font-semibold capitalize text-report-text">{month.label}</h3>
          <div className="mt-3 grid grid-cols-7 gap-1 text-center text-[10px] uppercase text-report-muted" aria-hidden="true">{weekdayLabels(activeI18n.resolvedLanguage || activeI18n.language).map((day) => <span key={day}>{day}</span>)}</div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {Array.from({ length: month.offset }, (_, index) => <span key={`blank-${index}`} aria-hidden="true" />)}
            {month.days.map((day) => {
              const selected = day.date === selectedDate;
              const focused = day.date === focusedDate;
              const intensity = activityMetricIntensity(day, metric, days);
              return (
                <button
                  key={day.date}
                  ref={(node) => { if (node) refs.current.set(day.date, node); else refs.current.delete(day.date); }}
                  type="button"
                  tabIndex={focused ? 0 : -1}
                  aria-pressed={selected}
                  aria-label={activityDayLabel(day, metric)}
                  data-date={day.date}
                  data-availability={day.availability}
                  className={["activity-calendar-cell min-h-10 rounded-md border transition focus:outline-none focus:ring-2 focus:ring-report-blue/75 focus:ring-offset-1 focus:ring-offset-ink-850", selected ? "border-report-blue ring-2 ring-report-blue/55" : "border-ink-700 hover:border-report-blue/70", day.date.endsWith("-01") ? "font-bold" : ""].join(" ")}
                  style={dayCellStyle(day, metric, intensity)}
                  onFocus={() => onFocus(day.date)}
                  onClick={() => onSelect(day.date)}
                  onKeyDown={(event) => handleKey(event, day)}
                >
                  <span className="activity-calendar-date">{Number(day.date.slice(-2))}</span>
                  <span className="activity-calendar-value" aria-hidden="true">{activityCellValue(day, metric)}</span>
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function DayDetail({ day, hub, expanded, onToggle }: { day: ActivityHubDay | null; hub: ActivityHubModel; expanded: boolean; onToggle: () => void }) {
  const { t } = useTranslation(["pages", "common"]);
  if (!day || day.availability === "unavailable") return <aside className="rounded-lg border border-ink-700 bg-ink-900/45 p-4" data-testid="activity-day-detail"><h2 className="text-lg font-semibold text-report-text">{t("activity.selectedDay")}</h2><p className="mt-4 text-sm text-report-muted">{t("activity.unavailableDate")}</p></aside>;
  if (day.availability === "inactive") return <aside className="rounded-lg border border-ink-700 bg-ink-900/45 p-4" data-testid="activity-day-detail"><p className="text-xs uppercase tracking-wide text-report-muted">{day.date === hub.today ? t("activity.today") : formatShortDate(day.date)}</p><h2 className="mt-1 text-lg font-semibold text-report-text">{t("activity.inactive")}</h2><p className="mt-3 text-sm text-report-muted">{t("activity.inactiveDescription")}</p></aside>;
  const decks = day.decks ?? [];
  const visibleDecks = expanded ? decks : decks.slice(0, 5);
  const hidden = Math.max(0, decks.length - 5);
  return (
    <aside className="rounded-lg border border-ink-700 bg-ink-900/45 p-4" data-testid="activity-day-detail">
      <p className="text-xs uppercase tracking-wide text-report-muted">{day.date === hub.today ? t("activity.today") : t("activity.selectedDay")}</p>
      <h2 className="mt-1 text-lg font-semibold text-report-text">{formatFullDate(day.date)}</h2>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <Detail label={t("activity.reviews")} value={formatInteger(day.reviews)} />
        <Detail label={t("activity.newCards")} value={formatInteger(day.newCards)} />
        <Detail label={t("answers.pass", { ns: "common" })} value={formatInteger(day.pass)} />
        <Detail label={t("answers.fail", { ns: "common" })} value={formatInteger(day.fail)} />
        <Detail label={t("activity.successRate")} value={formatPercent(day.successRate)} />
        <Detail label={t("activity.studyTime")} value={formatDurationSeconds(day.studySeconds)} caption={studyTimeCaption(hub)} />
      </div>
      <div className="mt-5">
        <h3 className="text-sm font-semibold text-report-text">{t("activity.activeDecks", { count: formatInteger(day.activeDeckCount) })}</h3>
        {visibleDecks.length ? <div className="mt-2 grid gap-2">{visibleDecks.map((deck) => <div key={deck.id} className="activity-day-deck-row rounded-lg border border-ink-700 bg-ink-850 px-3 py-2.5" data-testid="activity-day-deck-row" title={deck.name}><span className="block break-words text-sm font-medium leading-5 text-report-text">{deck.name}</span><span className="mt-1 block text-xs leading-5 text-report-muted">{t("activity.deckSummary", { reviews: formatInteger(deck.reviews), rate: deck.successRate === null ? t("state.noData", { ns: "common" }) : formatPercent(deck.successRate) })}</span></div>)}</div> : <p className="mt-2 text-sm text-report-muted">{t("activity.deckNamesUnavailable")}</p>}
        {hidden > 0 ? <button type="button" aria-expanded={expanded} className="mt-3 text-sm font-medium text-report-blue underline-offset-4 hover:underline" onClick={onToggle}>{expanded ? t("activity.collapse") : t("activity.showMore", { count: hidden })}</button> : null}
      </div>
    </aside>
  );
}

function ActivityFeed({ days, weeks, dayMap }: { days: ActivityFeedDay[]; weeks: ActivityWeekSummary[]; dayMap: Map<string, ActivityHubDay> }) {
  const items = [...days.map((entry) => ({ kind: "day" as const, date: entry.date, entry })), ...weeks.map((entry) => ({ kind: "week" as const, date: entry.weekEnd, entry }))].sort((a, b) => b.date.localeCompare(a.date) || (a.kind === "day" ? -1 : 1));
  const monthGroups = groupActivityTimelineByMonth(items);
  return <div className="mt-5 grid gap-5" data-testid="activity-feed">{monthGroups.map((group) => <section key={group.key} aria-labelledby={`activity-month-${group.key}`} data-activity-month={group.key}><h3 id={`activity-month-${group.key}`} className="activity-month-heading">{group.label}</h3><ol className="mt-2 grid gap-2.5">{group.items.map((item) => item.kind === "day" ? <DailyEntry key={item.entry.id} entry={item.entry} day={dayMap.get(item.entry.date)} /> : <WeeklyEntry key={item.entry.id} week={item.entry} />)}</ol></section>)}</div>;
}

function DailyEntry({ entry, day }: { entry: ActivityFeedDay; day?: ActivityHubDay }) {
  const { t } = useTranslation("pages");
  if (!day) return null;
  const topDeck = day.decks?.[0];
  return <li className="activity-daily-entry rounded-lg border border-ink-700 bg-ink-900/35 px-3.5 py-3" data-feed-type="daily_summary"><span className="sr-only">{t("activity.dailySummaryLabel")} </span><div><p className="text-[11px] uppercase tracking-wide text-report-muted">{entry.date}</p><h4 className="mt-0.5 font-semibold text-report-text">{formatFullDate(entry.date)}</h4></div><p className="mt-1.5 text-sm leading-5 text-report-muted">{dailySummary(day)}{topDeck ? ` · ${t("activity.topDeck", { name: topDeck.name })}` : ""}</p>{entry.highlights.length ? <ul className="mt-2 grid gap-1.5">{entry.highlights.map((highlight) => <li key={highlight.id} className="flex items-start gap-2 rounded-md border border-report-blue/25 bg-report-blue/10 px-2.5 py-1.5 text-sm text-report-text"><span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-report-blue">{highlightLabel(highlight)}</span><span>{highlightText(highlight)}</span></li>)}</ul> : null}</li>;
}

function WeeklyEntry({ week }: { week: ActivityWeekSummary }) {
  const { t } = useTranslation("pages");
  return <li className="rounded-lg border border-report-purple/30 bg-report-purple/10 px-3.5 py-3" data-feed-type="weekly_summary"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-[11px] uppercase tracking-wide text-report-muted">{week.weekStart} — {week.weekEnd}</p><h4 className="mt-0.5 font-semibold text-report-text">{t("activity.weekSummary")}</h4></div><span className="status-pill status-neutral">{t("activity.week")}</span></div><p className="mt-2 text-sm leading-5 text-report-muted">{t("activity.weekMetrics", { days: formatInteger(week.activeDays), reviews: formatInteger(week.reviews), duration: formatDurationSeconds(week.studySeconds), rate: formatPercent(week.successRate) })}</p>{week.comparison ? <p className="mt-2 text-sm font-medium text-report-text">{weeklyComparisonText(week)}</p> : null}</li>;
}

function CalendarLegend({ metric }: { metric: ActivityMetric }) { const { t } = useTranslation("pages"); return <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-report-muted" aria-label={t("activity.legend")}><Legend swatch="unavailable" text={t("activity.statsUnavailable")} /><Legend swatch="inactive" text={t("activity.inactive")} /><Legend swatch="active" text={t("activity.hasActivity", { metric: t(`activity.metrics.${metric}`) })} /></div>; }
function Legend({ swatch, text }: { swatch: string; text: string }) { return <span className="inline-flex items-center gap-2"><span className={`h-3 w-3 rounded-sm border border-ink-700 activity-legend-${swatch}`} aria-hidden="true" />{text}</span>; }
function SummaryCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) { return <article className="rounded-xl border border-ink-700 bg-ink-900/35 p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wide text-report-muted">{label}</p><p className="mt-2 text-xl font-semibold text-report-text">{value}</p></div><span className="kpi-icon">{icon}</span></div></article>; }
function Detail({ label, value, caption }: { label: string; value: string; caption?: string }) { return <div className="rounded-lg border border-ink-700 bg-ink-850 px-3 py-2"><p className="text-xs uppercase tracking-wide text-report-muted">{label}</p><p className="mt-1 text-sm font-semibold text-report-text">{value}</p>{caption ? <p className="mt-1 text-[11px] text-report-muted">{caption}</p> : null}</div>; }

function ActivityLoadState({ state }: { state: LoadState }) { const { t } = useTranslation("pages"); return <section className="rounded-xl border border-dashed border-ink-700 bg-ink-850 p-6 text-center"><h1 className="text-xl font-semibold text-report-text">{state === "loading" ? t("activity.loading") : state === "forbidden" ? t("activity.invalidLink") : t("activity.unavailable")}</h1><p className="mt-2 text-sm text-report-muted">{t("activity.loadDescription")}</p></section>; }
function ActivityEmptyState({ embedded = false }: { embedded?: boolean }) { const { t } = useTranslation("pages"); const Tag = embedded ? "section" : "div"; return <Tag className="rounded-xl border border-dashed border-ink-700 bg-ink-850 p-6 text-center shadow-panel"><h2 className="text-lg font-semibold text-report-text">{t("activity.emptyTitle")}</h2><p className="mt-2 text-sm leading-6 text-report-muted">{t("activity.emptyDescription")}</p></Tag>; }

function groupMonths(days: ActivityHubDay[]) { const groups = new Map<string, ActivityHubDay[]>(); for (const day of days) { const key = day.date.slice(0, 7); groups.set(key, [...(groups.get(key) ?? []), day]); } return [...groups.entries()].map(([key, values]) => ({ key, days: values, offset: mondayIndex(values[0].date), label: new Date(`${key}-01T12:00:00`).toLocaleDateString(localeForLanguage(i18n.resolvedLanguage || i18n.language), { month: "long", year: "numeric" }) })); }
function mondayIndex(dateKey: string) { const day = new Date(`${dateKey}T12:00:00`).getDay(); return day === 0 ? 6 : day - 1; }
function dayCellStyle(day: ActivityHubDay, metric: ActivityMetric, intensity: number) { if (day.availability === "unavailable") return { backgroundColor: "rgb(var(--color-bg-elevated) / 0.4)", backgroundImage: "linear-gradient(135deg, transparent 42%, rgb(var(--color-text-muted) / 0.25) 43%, rgb(var(--color-text-muted) / 0.25) 57%, transparent 58%)", color: "rgb(var(--color-text-muted) / 0.7)" }; if (day.availability === "inactive") return { backgroundColor: "rgb(var(--color-bg-elevated))", color: "rgb(var(--color-text-muted))" }; const channel = metric === "new_cards" ? "var(--color-warning)" : metric === "study_time" ? "var(--color-good)" : metric === "success_rate" ? "var(--color-purple)" : "var(--color-accent)"; return { backgroundColor: `rgb(${channel} / ${0.14 + intensity * 0.62})`, color: "rgb(var(--color-text-primary))" }; }
function activityDayLabel(day: ActivityHubDay, metric: ActivityMetric) { const date = formatFullDate(day.date); if (day.availability === "unavailable") return i18n.t("activity.dayUnavailableLabel", { ns: "pages", date }); if (day.availability === "inactive") return i18n.t("activity.dayInactiveLabel", { ns: "pages", date }); const label = i18n.t(`activity.metrics.${metric}`, { ns: "pages" }); const value = activityMetricValue(day, metric); return i18n.t("activity.dayActiveLabel", { ns: "pages", date, metric: label, value: value === null ? i18n.t("state.noData", { ns: "common" }) : metric === "success_rate" ? formatPercent(value) : metric === "study_time" ? formatDurationSeconds(value) : formatInteger(value) }); }
function activityCellValue(day: ActivityHubDay, metric: ActivityMetric) { if (day.availability === "unavailable") return i18n.t("activity.notAvailableShort", { ns: "pages" }); if (day.availability === "inactive") return "—"; const value = activityMetricValue(day, metric); if (value === null) return i18n.t("activity.notAvailableShort", { ns: "pages" }); if (metric === "success_rate") return formatPercent(value); if (metric === "study_time") return value < 60 ? i18n.t("activity.lessThanMinute", { ns: "pages" }) : i18n.t("activity.minuteCompact", { ns: "pages", value: Math.round(value / 60) }); return formatInteger(value); }
function formatFullDate(value: string) { const date = new Date(`${value}T12:00:00`); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(localeForLanguage(i18n.resolvedLanguage || i18n.language), { day: "numeric", month: "long", year: "numeric" }); }
function formatDays(value: number) { const count = Math.max(0, Math.round(value)); return i18n.t("units.day", { ns: "common", count }); }
function studyTimeCaption(hub: ActivityHubModel) { return hub.metrics.studyTimeSource === "revlog_estimate" ? i18n.t("activity.sourceEstimate", { ns: "pages" }) : hub.metrics.studyTimeSource === "session_tracker" ? i18n.t("activity.sourceTracker", { ns: "pages" }) : hub.metrics.studyTimeSource === "study_time_stats" ? i18n.t("activity.sourceStudyTime", { ns: "pages" }) : i18n.t("activity.sourceUnavailable", { ns: "pages" }); }
function dailySummary(day: ActivityHubDay) { return [i18n.t("units.review", { ns: "common", count: day.reviews }), i18n.t("activity.newShort", { ns: "pages", count: day.newCards }), day.studySeconds == null ? null : formatDurationSeconds(day.studySeconds), day.successRate == null ? null : formatPercent(day.successRate), i18n.t("units.deck", { ns: "common", count: day.activeDeckCount })].filter(Boolean).join(" · "); }
function highlightText(highlight: ActivityHighlight) { if (highlight.type === "return_after_break") return i18n.t("activity.returnAfterBreak", { ns: "pages", count: highlight.inactiveDays }); if (highlight.type === "streak_milestone") return i18n.t("activity.streakReached", { ns: "pages", days: formatDays(highlight.days ?? 0) }); return i18n.t("activity.dailyRecord", { ns: "pages", count: formatInteger(highlight.reviews) }); }
function highlightLabel(highlight: ActivityHighlight) { if (highlight.type === "return_after_break") return i18n.t("activity.returnLabel", { ns: "pages" }); if (highlight.type === "streak_milestone") return i18n.t("activity.streakLabel", { ns: "pages" }); return i18n.t("activity.recordLabel", { ns: "pages" }); }
function weeklyComparisonText(week: ActivityWeekSummary) { const value = Math.abs(week.comparison?.reviewsPercentChange ?? 0); if (week.comparison?.direction === "more") return i18n.t("activity.weekMore", { ns: "pages", value }); if (week.comparison?.direction === "less") return i18n.t("activity.weekLess", { ns: "pages", value }); return i18n.t("activity.weekSame", { ns: "pages" }); }
function buildObservations(days: ActivityFeedDay[], weeks: ActivityWeekSummary[]) { const result: string[] = []; const milestone = days.flatMap((day) => day.highlights).find((item) => item.type === "streak_milestone"); if (milestone) result.push(i18n.t("activity.streakReached", { ns: "pages", days: formatDays(milestone.days ?? 0) })); if (weeks[0]) result.push(i18n.t("activity.lastWeek", { ns: "pages", count: formatInteger(weeks[0].reviews) })); return result.slice(0, 3); }
type ActivityTimelineItem = { kind: "day"; date: string; entry: ActivityFeedDay } | { kind: "week"; date: string; entry: ActivityWeekSummary };
function groupActivityTimelineByMonth(items: ActivityTimelineItem[]) { const groups: Array<{ key: string; label: string; items: ActivityTimelineItem[] }> = []; for (const item of items) { const key = item.date.slice(0, 7); let group = groups[groups.length - 1]; if (!group || group.key !== key) { group = { key, label: new Date(`${key}-01T12:00:00`).toLocaleDateString(localeForLanguage(i18n.resolvedLanguage || i18n.language), { month: "long", year: "numeric" }), items: [] }; groups.push(group); } group.items.push(item); } return groups; }

const weekdayLabels = localizedWeekdayLabels;

const activeControlClass = "min-h-10 rounded-lg bg-report-blue/20 px-3 py-2 text-sm text-report-text shadow-glow focus:outline-none focus:ring-2 focus:ring-report-blue/55";
const idleControlClass = "min-h-10 rounded-lg px-3 py-2 text-sm text-report-secondary hover:bg-ink-800 hover:text-report-text focus:outline-none focus:ring-2 focus:ring-report-blue/55";

export default CalendarPage;
