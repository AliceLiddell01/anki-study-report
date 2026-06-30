import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Flame,
  Layers3,
  Sparkles,
  Timer,
  Trophy,
} from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import {
  buildCalendarModel,
  calendarMetricValue,
  heatmapIntensity,
  isActiveDay,
  maxMetricValue,
  type CalendarMetric,
  type CalendarPeriod,
} from "../lib/calendarStats";
import { formatShortDate } from "../lib/dateUtils";
import { finiteNullableNumber, formatDurationSeconds, formatInteger, formatPercent } from "../lib/formatters";
import type { CalendarDayStats, CalendarInsight, Status, StudyReport } from "../types/report";
import type { LoadState } from "./HomePage";

const metricOptions: Array<{ key: CalendarMetric; label: string }> = [
  { key: "reviews", label: "Reviews" },
  { key: "study_time", label: "Study time" },
  { key: "new_cards", label: "New cards" },
  { key: "pass_rate", label: "Pass rate" },
  { key: "forecast", label: "Forecast" },
];

const periodOptions: Array<{ key: CalendarPeriod; label: string }> = [
  { key: "30", label: "30 days" },
  { key: "90", label: "90 days" },
  { key: "year", label: "Year" },
];

const statusTone: Record<string, Status> = {
  stable: "good",
  inconsistent: "warning",
  overload_risk: "danger",
  insufficient_data: "neutral",
};

function CalendarPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const [metric, setMetric] = useState<CalendarMetric>("reviews");
  const [period, setPeriod] = useState<CalendarPeriod>("90");
  const model = useMemo(() => buildCalendarModel(report, period), [period, report]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const selectedDay =
    model.visibleDays.find((day) => day.date === selectedDate) ??
    model.visibleDays.find((day) => day.isToday) ??
    [...model.historicalDays].reverse().find(isActiveDay) ??
    model.futureDays[0] ??
    null;
  const metricAvailable = model.metricAvailability[metric];
  const metricMax = maxMetricValue(model.visibleDays, metric);

  if (loadState !== "ready") {
    return <CalendarLoadState state={loadState} />;
  }

  if (!report) {
    return (
      <CalendarShell model={model}>
        <EmptyState title="Недостаточно истории для календаря" text="Данные появятся после накопления дневной статистики." />
      </CalendarShell>
    );
  }

  return (
    <CalendarShell model={model}>
      <section className="grid min-w-0 grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <SummaryCard icon={<Flame size={18} />} label="Current streak" value={formatOptionalDays(model.summary.currentStreak)} status="good" />
        <SummaryCard icon={<Trophy size={18} />} label="Best streak" value={formatOptionalDays(model.summary.bestStreak)} status="good" />
        <SummaryCard icon={<CalendarDays size={18} />} label="Active days this month" value={formatOptionalInteger(model.summary.activeDaysThisMonth)} status="neutral" />
        <SummaryCard icon={<Layers3 size={18} />} label="Reviews this month" value={formatOptionalInteger(model.summary.reviewsThisMonth)} status="neutral" />
        <SummaryCard icon={<Clock3 size={18} />} label="Study time this month" value={formatDurationSeconds(model.summary.studySecondsThisMonth, "—")} status="neutral" />
        <SummaryCard icon={<Timer size={18} />} label="Avg reviews / active day" value={formatOptionalInteger(model.summary.averageReviewsPerActiveDay)} status="neutral" />
        <SummaryCard
          icon={<Sparkles size={18} />}
          label="Most productive day"
          value={model.summary.mostProductiveDay ? `${formatShortDate(model.summary.mostProductiveDay.date)}, ${formatInteger(model.summary.mostProductiveDay.reviews)}` : "—"}
          status="good"
        />
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold tracking-normal text-report-text">Calendar heatmap</h2>
            <p className="mt-1 text-sm leading-6 text-report-muted">{calendarRangeText(model.periodStart, model.periodEnd, model.hasLimitedHistory)}</p>
          </div>
          <div className="flex flex-col gap-3 lg:flex-row">
            <div className="grid grid-cols-2 gap-1 rounded-lg border border-ink-700 bg-ink-900/45 p-1 sm:grid-cols-5">
              {metricOptions.map((item) => {
                const active = metric === item.key;
                const available = model.metricAvailability[item.key];
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setMetric(item.key)}
                    className={[
                      "rounded-md px-3 py-2 text-sm transition",
                      active
                        ? "bg-report-blue/20 text-report-blue"
                        : available
                          ? "text-report-muted hover:bg-ink-800 hover:text-report-text"
                          : "text-report-muted/55 hover:bg-ink-800/60",
                    ].join(" ")}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
            <label className="relative block min-w-36">
              <select
                value={period}
                onChange={(event) => setPeriod(event.target.value as CalendarPeriod)}
                className="w-full appearance-none rounded-lg border border-ink-700 bg-ink-900 px-3 py-2.5 pr-9 text-sm text-report-text outline-none transition focus:border-report-blue"
              >
                {periodOptions.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
            </label>
          </div>
        </div>

        {model.visibleDays.length && metricAvailable ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.35fr)]">
            <div className="min-w-0 overflow-x-auto rounded-lg border border-ink-700 bg-ink-900/35 p-3">
              <div className="grid w-full gap-1.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(18px, 18px))" }}>
                {model.visibleDays.map((day) => (
                  <DayCell
                    key={`${day.date}-${day.isFuture ? "future" : "history"}`}
                    day={day}
                    metric={metric}
                    max={metricMax}
                    selected={selectedDay?.date === day.date}
                    onSelect={() => setSelectedDate(day.date)}
                  />
                ))}
              </div>
            </div>
            <DayDetails day={selectedDay} />
          </div>
        ) : model.visibleDays.length ? (
          <EmptyState title="Метрика недоступна" text={metricUnavailableText(metric)} />
        ) : (
          <EmptyState title="Недостаточно истории для календаря" text="Данные появятся после накопления дневной статистики." />
        )}
      </section>

      <section className="grid min-w-0 gap-3 lg:grid-cols-2">
        {model.insights.map((insight) => (
          <InsightCard key={`${insight.title}-${insight.text}`} insight={insight} />
        ))}
      </section>
    </CalendarShell>
  );
}

function CalendarShell({ model, children }: { model: ReturnType<typeof buildCalendarModel>; children: ReactNode }) {
  const tone = statusTone[model.status] ?? "neutral";
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5">
      <header className="min-w-0 rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Calendar</h1>
              <StatusPill status={tone}>{statusLabel(model.status)}</StatusPill>
            </div>
            <p className="mt-2 text-sm leading-6 text-report-muted">История учёбы, streak и нагрузка по дням.</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-text">{model.statusText}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status="neutral">{model.streak.totalDays ? `${model.streak.totalDays} days` : "no history"}</StatusPill>
            <StatusPill status="good">{model.streak.activeDays} active</StatusPill>
            <StatusPill status={model.futureDays.length ? "warning" : "neutral"}>{model.futureDays.length} forecast</StatusPill>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

function DayCell({
  day,
  metric,
  max,
  selected,
  onSelect,
}: {
  day: CalendarDayStats;
  metric: CalendarMetric;
  max: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const intensity = heatmapIntensity(day, metric, max);
  const future = Boolean(day.isFuture);
  const title = dayTooltip(day);
  return (
    <button
      type="button"
      title={title}
      onClick={onSelect}
      className={[
        "h-[18px] w-[18px] rounded-[5px] border transition focus:outline-none focus:ring-2 focus:ring-report-blue/60",
        future ? "border-dashed border-report-purple/60" : "border-ink-700",
        day.isToday ? "ring-2 ring-report-warning/70" : "",
        selected ? "scale-110 border-report-blue" : "hover:border-report-blue/75",
      ].join(" ")}
      style={{ background: heatmapColor(day, metric, intensity) }}
      aria-label={title}
    />
  );
}

function DayDetails({ day }: { day: CalendarDayStats | null }) {
  if (!day) {
    return <EmptyState title="Нет дня" text="Недостаточно истории для календаря." />;
  }
  const future = Boolean(day.isFuture);
  return (
    <aside className="rounded-lg border border-ink-700 bg-ink-900/45 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{future ? "Forecast day" : day.isToday ? "Today" : "Study day"}</p>
          <h3 className="mt-1 text-lg font-semibold text-report-text">{day.date}</h3>
        </div>
        <StatusPill status={future ? "warning" : isActiveDay(day) ? "good" : "neutral"}>{future ? "forecast" : isActiveDay(day) ? "active" : "no study"}</StatusPill>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <DetailMetric label="Reviews" value={formatInteger(day.reviews)} />
        <DetailMetric label="New cards" value={formatInteger(day.newCards)} />
        <DetailMetric label="Study time" value={formatDurationSeconds(day.studySeconds, "—")} />
        <DetailMetric label="Pass rate" value={day.passRate === null || day.passRate === undefined ? "—" : formatPercent(day.passRate)} />
        <DetailMetric label="Fail" value={day.fail === undefined ? "—" : formatInteger(day.fail)} />
        <DetailMetric label="Active decks" value={day.activeDecks === undefined ? "—" : formatInteger(day.activeDecks)} />
      </div>
      {finiteNullableNumber(day.dueForecast) !== null && (
        <p className="mt-3 rounded-lg border border-report-purple/35 bg-report-purple/10 p-3 text-sm leading-6 text-report-text">
          Forecast: {formatInteger(day.dueForecast)} due cards. {future && day.reviews <= 0 ? "No historical reviews yet." : ""}
        </p>
      )}
    </aside>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  status,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  status: Status;
}) {
  return (
    <article className={`kpi-card status-${status}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.04em] text-report-muted">{label}</p>
          <p className="mt-2 break-words text-xl font-semibold text-report-text">{value}</p>
        </div>
        <div className="kpi-icon">{icon}</div>
      </div>
    </article>
  );
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-850 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-report-text">{value}</p>
    </div>
  );
}

function InsightCard({ insight }: { insight: CalendarInsight }) {
  const tone = insight.tone === "positive" ? "good" : insight.tone;
  const Icon = insight.tone === "warning" || insight.tone === "danger" ? AlertTriangle : CheckCircle2;
  return (
    <article className={`rounded-xl border bg-ink-850 p-4 shadow-panel status-border-${tone}`}>
      <div className="flex gap-3">
        <Icon className={toneTextClass(tone)} size={19} />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-report-text">{insight.title}</h3>
          <p className="mt-1 text-sm leading-6 text-report-muted">{insight.text}</p>
        </div>
      </div>
    </article>
  );
}

function CalendarLoadState({ state }: { state: LoadState }) {
  const title =
    state === "loading"
      ? "Загрузка календаря"
      : state === "empty"
        ? "Отчёт ещё не опубликован"
        : state === "forbidden"
          ? "Недействительная ссылка dashboard"
          : "Не удалось загрузить календарь";
  const text =
    state === "loading"
      ? "Проверяю локальный dashboard API."
      : state === "empty"
        ? "Откройте основное окно Anki Study Report и опубликуйте отчёт в dashboard."
        : state === "forbidden"
          ? "Откройте dashboard из Anki Study Report, чтобы получить действующий token."
          : "Локальный dashboard API не вернул данные календаря.";
  return <EmptyState title={title} text={text} />;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <section className="rounded-xl border border-dashed border-ink-700 bg-ink-850 p-5 text-center shadow-panel">
      <h2 className="text-lg font-semibold tracking-normal text-report-text">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-report-muted">{text}</p>
    </section>
  );
}

function StatusPill({ status, children }: { status: Status; children: ReactNode }) {
  return <span className={`status-pill status-${status}`}>{children}</span>;
}

function statusLabel(status: string): string {
  return {
    stable: "Стабильная неделя",
    inconsistent: "Есть пропуски",
    overload_risk: "Риск перегруза впереди",
    insufficient_data: "Мало данных",
  }[status] ?? "Мало данных";
}

function formatOptionalDays(value: number | null): string {
  return value === null ? "—" : `${formatInteger(value)} дней`;
}

function formatOptionalInteger(value: number | null): string {
  return value === null ? "—" : formatInteger(value);
}

function calendarRangeText(start: string | null, end: string | null, limited: boolean): string {
  if (!start || !end) {
    return "Недостаточно истории для календаря.";
  }
  const suffix = limited ? "Показан доступный диапазон, пустой год не дорисовывается." : "История и forecast визуально разделены.";
  return `${start} - ${end}. ${suffix}`;
}

function metricUnavailableText(metric: CalendarMetric): string {
  return {
    reviews: "Нет исторических reviews за выбранный диапазон.",
    study_time: "В payload нет дневного study time для выбранного диапазона.",
    new_cards: "В payload нет дневных new cards для выбранного диапазона.",
    pass_rate: "Pass rate появится, когда для дней есть reviews и fail/pass данные.",
    forecast: "Forecast недоступен в текущем payload.",
  }[metric];
}

function dayTooltip(day: CalendarDayStats): string {
  const lines = [day.date];
  if (day.isFuture && finiteNullableNumber(day.dueForecast) !== null) {
    lines.push(`Forecast: ${formatInteger(day.dueForecast)} due cards`);
    if (day.reviews <= 0) {
      lines.push("No historical reviews yet");
    }
    return lines.join("\n");
  }
  lines.push(`Reviews: ${formatInteger(day.reviews)}`);
  lines.push(`New cards: ${formatInteger(day.newCards)}`);
  lines.push(`Study time: ${formatDurationSeconds(day.studySeconds, "—")}`);
  if (day.passRate !== null && day.passRate !== undefined) {
    lines.push(`Pass rate: ${formatPercent(day.passRate)}`);
  }
  if (day.fail !== undefined) {
    lines.push(`Fail: ${formatInteger(day.fail)}`);
  }
  if (day.activeDecks !== undefined) {
    lines.push(`Active decks: ${formatInteger(day.activeDecks)}`);
  }
  return lines.join("\n");
}

function heatmapColor(day: CalendarDayStats, metric: CalendarMetric, intensity: number): string {
  if (intensity <= 0) {
    return day.isFuture ? "rgba(124, 92, 255, 0.06)" : "#111827";
  }
  if (metric === "forecast" || day.isFuture) {
    return `rgba(124, 92, 255, ${0.14 + intensity * 0.5})`;
  }
  if (metric === "pass_rate") {
    if ((calendarMetricValue(day, "pass_rate") ?? 0) < 0.7) {
      return `rgba(239, 111, 108, ${0.18 + intensity * 0.48})`;
    }
    if ((calendarMetricValue(day, "pass_rate") ?? 0) < 0.82) {
      return `rgba(246, 193, 119, ${0.16 + intensity * 0.46})`;
    }
    return `rgba(103, 211, 145, ${0.16 + intensity * 0.5})`;
  }
  if (metric === "new_cards") {
    return `rgba(246, 193, 119, ${0.14 + intensity * 0.5})`;
  }
  if (metric === "study_time") {
    return `rgba(103, 211, 145, ${0.12 + intensity * 0.46})`;
  }
  return `rgba(61, 180, 242, ${0.14 + intensity * 0.55})`;
}

function toneTextClass(tone: Status) {
  return {
    good: "text-report-success",
    neutral: "text-report-blue",
    warning: "text-report-warning",
    danger: "text-report-danger",
  }[tone];
}

export default CalendarPage;
