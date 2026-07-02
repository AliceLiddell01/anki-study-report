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
  { key: "reviews", label: "Повторения" },
  { key: "study_time", label: "Время" },
  { key: "new_cards", label: "Новые" },
  { key: "pass_rate", label: "Успешность" },
  { key: "forecast", label: "Прогноз" },
];

const periodOptions: Array<{ key: CalendarPeriod; label: string }> = [
  { key: "30", label: "Последние 30 дней" },
  { key: "90", label: "Последние 90 дней" },
  { key: "year", label: "Год" },
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
        <SummaryCard icon={<Flame size={18} />} label="Текущая серия" value={formatOptionalDays(model.summary.currentStreak)} status="good" />
        <SummaryCard icon={<Trophy size={18} />} label="Лучшая серия" value={formatOptionalDays(model.summary.bestStreak)} status="good" />
        <SummaryCard icon={<CalendarDays size={18} />} label="Активные дни месяца" value={formatOptionalInteger(model.summary.activeDaysThisMonth)} status="neutral" />
        <SummaryCard icon={<Layers3 size={18} />} label="Повторения месяца" value={formatOptionalInteger(model.summary.reviewsThisMonth)} status="neutral" />
        <SummaryCard icon={<Clock3 size={18} />} label="Время учёбы за месяц" value={formatDurationSeconds(model.summary.studySecondsThisMonth, "—")} status="neutral" />
        <SummaryCard icon={<Timer size={18} />} label="Среднее за активный день" value={formatOptionalInteger(model.summary.averageReviewsPerActiveDay)} status="neutral" />
        <SummaryCard
          icon={<Sparkles size={18} />}
          label="Лучший день"
          value={model.summary.mostProductiveDay ? `${formatShortDate(model.summary.mostProductiveDay.date)}, ${formatInteger(model.summary.mostProductiveDay.reviews)}` : "—"}
          status="good"
        />
      </section>

      <section className="panel-motion rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold tracking-normal text-report-text">Календарь активности</h2>
            <p className="mt-1 text-sm leading-6 text-report-muted">{calendarRangeText(model.periodStart, model.periodEnd, model.hasLimitedHistory)}</p>
          </div>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
            <div className="grid grid-cols-2 gap-1 rounded-xl border border-ink-700 bg-ink-900/45 p-1.5 sm:grid-cols-5">
              {metricOptions.map((item) => {
                const active = metric === item.key;
                const available = model.metricAvailability[item.key];
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setMetric(item.key)}
                    className={[
                      "min-h-11 rounded-lg px-3 py-2 text-sm transition focus:outline-none focus:ring-2 focus:ring-report-blue/45",
                      active
                        ? "bg-report-blue/20 text-report-text shadow-glow"
                        : available
                          ? "text-report-secondary hover:bg-ink-800 hover:text-report-text"
                          : "text-report-muted/60 hover:bg-ink-800/60",
                    ].join(" ")}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
            <label className="relative block min-w-44">
              <select
                value={period}
                onChange={(event) => setPeriod(event.target.value as CalendarPeriod)}
                className="form-control min-h-11 w-full appearance-none rounded-xl px-3 py-2.5 pr-9 text-sm"
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
          <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.35fr)]">
            <div className="min-w-0 self-start overflow-x-auto rounded-lg border border-ink-700 bg-ink-900/30 p-3">
              <div className="grid max-w-full content-start gap-1.5" style={{ gridTemplateColumns: "repeat(auto-fit, 16px)" }}>
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
            <h1 className="text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Календарь</h1>
              <StatusPill status={tone}>{statusLabel(model.status)}</StatusPill>
            </div>
            <p className="mt-2 text-sm leading-6 text-report-muted">История учёбы, серии и нагрузка по дням.</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-text">{model.statusText}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status="neutral">{model.streak.totalDays ? `${model.streak.totalDays} дней` : "нет истории"}</StatusPill>
            <StatusPill status="good">{model.streak.activeDays} активных</StatusPill>
            <StatusPill status={model.futureDays.length ? "warning" : "neutral"}>{model.futureDays.length} прогноз</StatusPill>
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
        "h-4 w-4 rounded-[5px] border transition focus:outline-none focus:ring-2 focus:ring-report-blue/60",
        future ? "border-dashed border-report-purple/65" : "border-ink-700/85",
        day.isToday ? "ring-2 ring-report-warning/80 ring-offset-1 ring-offset-ink-850" : "",
        selected ? "scale-110 border-report-blue ring-2 ring-report-blue/60 ring-offset-1 ring-offset-ink-850" : "hover:border-report-blue/75",
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
    <aside className="self-start rounded-lg border border-ink-700 bg-ink-900/45 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{future ? "День прогноза" : day.isToday ? "Сегодня" : "День учёбы"}</p>
          <h3 className="mt-1 text-lg font-semibold text-report-text">{day.date}</h3>
        </div>
        <StatusPill status={future ? "warning" : isActiveDay(day) ? "good" : "neutral"}>{future ? "прогноз" : isActiveDay(day) ? "были занятия" : "занятий не было"}</StatusPill>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <DetailMetric label="Повторения" value={formatInteger(day.reviews)} />
        <DetailMetric label="Новые" value={formatInteger(day.newCards)} />
        <DetailMetric label="Время" value={formatDurationSeconds(day.studySeconds, "—")} />
        <DetailMetric label="Успешность" value={day.passRate === null || day.passRate === undefined ? "—" : formatPercent(day.passRate)} />
        <DetailMetric label="Fail" value={day.fail === undefined ? "—" : formatInteger(day.fail)} />
        <DetailMetric label="Активные колоды" value={day.activeDecks === undefined ? "—" : formatInteger(day.activeDecks)} />
      </div>
      {finiteNullableNumber(day.dueForecast) !== null && (
        <p className="mt-3 rounded-lg border border-report-purple/35 bg-report-purple/10 p-3 text-sm leading-6 text-report-text">
          Прогноз: {formatInteger(day.dueForecast)} due-карточек. {future && day.reviews <= 0 ? "Исторических повторений за этот день ещё нет." : ""}
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
          ? "Недействительная ссылка дашборда"
          : "Не удалось загрузить календарь";
  const text =
    state === "loading"
      ? "Проверяю локальный API дашборда."
      : state === "empty"
        ? "Откройте основное окно Anki Study Report и опубликуйте отчёт в дашборде."
        : state === "forbidden"
          ? "Откройте дашборд из Anki Study Report, чтобы получить действующий token."
          : "Локальный API дашборда не вернул данные календаря.";
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
    inconsistent: "Регулярность: есть пропуски",
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
    pass_rate: "Успешность появится, когда для дней есть reviews и fail/pass данные.",
    forecast: "Forecast недоступен в текущем payload.",
  }[metric];
}

function dayTooltip(day: CalendarDayStats): string {
  const lines = [day.date];
  if (day.isFuture && finiteNullableNumber(day.dueForecast) !== null) {
    lines.push(`Forecast: ${formatInteger(day.dueForecast)} due cards`);
    if (day.reviews <= 0) {
    lines.push("Исторических повторений пока нет");
    }
    return lines.join("\n");
  }
  lines.push(`Повторения: ${formatInteger(day.reviews)}`);
  lines.push(`Новые: ${formatInteger(day.newCards)}`);
  lines.push(`Время учёбы: ${formatDurationSeconds(day.studySeconds, "—")}`);
  if (day.passRate !== null && day.passRate !== undefined) {
    lines.push(`Успешность: ${formatPercent(day.passRate)}`);
  }
  if (day.fail !== undefined) {
    lines.push(`Fail: ${formatInteger(day.fail)}`);
  }
  if (day.activeDecks !== undefined) {
    lines.push(`Активные колоды: ${formatInteger(day.activeDecks)}`);
  }
  return lines.join("\n");
}

function heatmapColor(day: CalendarDayStats, metric: CalendarMetric, intensity: number): string {
  if (intensity <= 0) {
    return day.isFuture ? "rgb(var(--color-purple) / 0.08)" : "rgb(var(--color-bg-elevated))";
  }
  if (metric === "forecast" || day.isFuture) {
    return `rgb(var(--color-purple) / ${0.16 + intensity * 0.46})`;
  }
  if (metric === "pass_rate") {
    if ((calendarMetricValue(day, "pass_rate") ?? 0) < 0.7) {
      return `rgb(var(--color-danger) / ${0.2 + intensity * 0.46})`;
    }
    if ((calendarMetricValue(day, "pass_rate") ?? 0) < 0.82) {
      return `rgb(var(--color-warning) / ${0.18 + intensity * 0.44})`;
    }
    return `rgb(var(--color-good) / ${0.18 + intensity * 0.48})`;
  }
  if (metric === "new_cards") {
    return `rgb(var(--color-warning) / ${0.16 + intensity * 0.48})`;
  }
  if (metric === "study_time") {
    return `rgb(var(--color-good) / ${0.14 + intensity * 0.44})`;
  }
  return `rgb(var(--color-accent) / ${0.16 + intensity * 0.52})`;
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
