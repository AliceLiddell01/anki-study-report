import {
  AlertTriangle,
  ArrowDown,
  ArrowUpDown,
  BarChart3,
  Brain,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Flame,
  Layers3,
  LineChart as LineChartIcon,
  PauseCircle,
  Search,
  Sparkles,
  SunMedium,
  Timer,
  Trophy,
} from "lucide-react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  ComparisonDelta,
  ComparisonPeriod,
  DailyStats,
  DeckPerformance,
  KpiMetric,
  Status,
  StudyReport,
} from "../types/report";

const chartColors = {
  blue: "#3db4f2",
  purple: "#7c5cff",
  success: "#67d391",
  warning: "#f6c177",
  danger: "#ef6f6c",
};
const collapsedDeckTableRows = 12;

const iconMap = {
  alert: AlertTriangle,
  bar: BarChart3,
  brain: Brain,
  calendar: CalendarDays,
  check: CheckCircle2,
  clock: Clock3,
  flame: Flame,
  layers: Layers3,
  line: LineChartIcon,
  pause: PauseCircle,
  sparkles: Sparkles,
  sun: SunMedium,
  timer: Timer,
  trophy: Trophy,
};

type SortKey = "name" | "totalReviews" | "passRate" | "failCount" | "averageAnswerSeconds";
type SortDirection = "asc" | "desc";
type DeckFilter = "all" | Status;
export type LoadState = "loading" | "ready" | "empty" | "forbidden" | "error";

const statusLabel: Record<Status, string> = {
  good: "good",
  neutral: "neutral",
  warning: "warning",
  danger: "danger",
};
const comparisonStatusLabel: Record<"good" | "neutral" | "warning" | "danger", string> = {
  good: "better",
  neutral: "normal",
  warning: "warning",
  danger: "overload",
};
const comparisonPeriods: Array<{ key: ComparisonPeriod; label: string }> = [
  { key: "yesterday", label: "Вчера" },
  { key: "avg7", label: "7 дней" },
  { key: "avg30", label: "30 дней" },
  { key: "week", label: "Неделя" },
];

const ReportContext = createContext<StudyReport | null>(null);

function useReport() {
  const report = useContext(ReportContext);
  if (!report) {
    throw new Error("Study report is not loaded");
  }
  return report;
}

function HomePage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  if (loadState !== "ready" || !report) {
    return <EmptyDashboard state={loadState} />;
  }

  const problemDecks = report.decks
    .filter((deck) => deck.status === "danger" || deck.status === "warning")
    .slice(0, 3);
  const bestDecks = [...report.decks]
    .filter((deck) => deck.status === "good")
    .sort((a, b) => b.passRate - a.passRate)
    .slice(0, 3);

  return (
    <ReportContext.Provider value={report}>
      <div className="grid min-w-0 gap-5">
        <Header />
        <HeroSummary />
        <KpiGrid metrics={report.kpis} />
        <ProgressComparisonSection />
        <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.15fr)]">
          <AnswerDistribution />
          <ActivitySection />
        </section>
        <DeckPerformanceSection problemDecks={problemDecks} bestDecks={bestDecks} />
        <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <ForecastSection />
          <FsrsSection />
        </section>
        <RecommendationsSection />
        <TechnicalDetails />
      </div>
    </ReportContext.Provider>
  );
}

function EmptyDashboard({ state }: { state: LoadState }) {
  const isLoading = state === "loading";
  const title = isLoading
    ? "Загрузка отчёта"
    : state === "empty"
      ? "Отчёт ещё не опубликован"
      : state === "forbidden"
        ? "Недействительная ссылка dashboard"
      : "Не удалось загрузить отчёт";
  const text = isLoading
    ? "Проверяю локальный dashboard API."
    : state === "empty"
      ? "Откройте основное окно Anki Study Report и нажмите “Открыть этот отчёт в dashboard”."
      : state === "forbidden"
        ? "Недействительная ссылка dashboard. Откройте dashboard из Anki Study Report."
      : "Локальный dashboard API не вернул отчёт. Попробуйте опубликовать отчёт ещё раз.";

  return (
    <section className="mx-auto max-w-2xl rounded-xl border border-dashed border-ink-700 bg-ink-850 p-6 text-center shadow-panel">
      <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-report-muted">{text}</p>
    </section>
  );
}

function Header() {
  const { metadata } = useReport();

  return (
    <header className="rounded-xl border border-ink-700/90 bg-ink-850/95 px-4 py-4 shadow-panel sm:px-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-normal text-report-text sm:text-2xl">
              {metadata.title}
            </h1>
            <StatusPill status="warning">личная статистика</StatusPill>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-report-muted">
            <MetaChip label="Период" value={metadata.period} />
            <MetaChip label="Колоды" value={metadata.selectedDecks.join(", ")} />
            <MetaChip label="Режим" value={metadata.answerMode === "pass_fail" ? "Pass/Fail" : "4-button"} />
            <MetaChip label="Создано" value={metadata.createdAt} />
            <MetaChip label="Детализация" value={metadata.detailMode} />
          </div>
        </div>
      </div>
    </header>
  );
}

function HeroSummary() {
  const report = useReport();
  const { summary } = report;

  return (
    <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
      <div className="rounded-xl border border-ink-700 bg-gradient-to-br from-ink-850 via-ink-850 to-ink-800 p-5 shadow-glow">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={summary.riskLevel}>risk level: {statusLabel[summary.riskLevel]}</StatusPill>
          <StatusPill status="neutral">pass/fail view</StatusPill>
        </div>
        <p className="mt-5 max-w-5xl text-2xl font-semibold leading-snug tracking-normal text-report-text lg:text-3xl">
          {summary.verdict}
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <HeroNote title="Главное действие" text={summary.mainAction} status="good" />
          <HeroNote title="Что тревожит" text={summary.warning} status="danger" />
          <HeroNote title="Новые карточки" text={summary.newCardsAdvice} status="warning" />
        </div>
      </div>
      <div className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-report-muted">Следующий шаг</p>
            <h2 className="mt-1 text-lg font-semibold">Стабилизировать качество</h2>
          </div>
          <div className="rounded-lg bg-report-blue/15 p-3 text-report-blue">
            <Brain size={24} />
          </div>
        </div>
        <div className="mt-5 space-y-3">
          {report.recommendations.checklist.slice(0, 3).map((item) => (
            <div key={item} className="flex gap-3 rounded-lg border border-ink-700 bg-ink-800/55 p-3">
              <CheckCircle2 className="mt-0.5 shrink-0 text-report-success" size={18} />
              <span className="text-sm leading-6 text-report-text">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function KpiGrid({ metrics }: { metrics: KpiMetric[] }) {
  return (
    <section className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-7">
      {metrics.map((metric) => {
        const Icon = iconMap[metric.icon as keyof typeof iconMap] ?? BarChart3;
        return (
          <article key={metric.id} className={`kpi-card status-${metric.status}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium uppercase tracking-[0.04em] text-report-muted">
                  {metric.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-report-text">{metric.value}</p>
              </div>
              <div className="kpi-icon">
                <Icon size={18} />
              </div>
            </div>
            <p className="mt-2 text-sm text-report-muted">{metric.caption}</p>
          </article>
        );
      })}
    </section>
  );
}

function AnswerDistribution() {
  const data = useReport().answerDistribution;
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const pass = data.find((item) => item.label === "Pass")?.value ?? 0;
  const fail = data.find((item) => item.label === "Fail")?.value ?? 0;

  return (
    <Panel title="Answer Distribution" action={<StatusPill status="neutral">Pass/Fail главный</StatusPill>}>
      <div className="grid gap-4 md:grid-cols-[220px_minmax(0,1fr)]">
        <div className="h-56">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius={62} outerRadius={92} paddingAngle={3}>
                {data.map((item) => (
                  <Cell key={item.label} fill={item.color} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col justify-center gap-3">
          {data.map((item) => (
            <div key={item.label} className="flex items-center justify-between gap-4 rounded-lg bg-ink-800/50 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm text-report-muted">{item.label}</span>
              </div>
              <span className="text-sm font-semibold text-report-text">
                {item.value} · {formatPercent(item.value / total)}
              </span>
            </div>
          ))}
          <p className="rounded-lg border border-report-warning/35 bg-report-warning/10 p-3 text-sm leading-6 text-report-text">
            Pass {formatPercent(pass / total)}, Fail {formatPercent(fail / total)}. Главная проблема не в объеме, а в качестве ответов на нескольких колодах.
          </p>
        </div>
      </div>
    </Panel>
  );
}

function ProgressComparisonSection() {
  const comparison = useReport().comparison ?? emptyComparison();
  const [period, setPeriod] = useState<ComparisonPeriod>("avg7");
  const current = period === "week" ? comparison.baselines.currentWeek : comparison.today;
  const baseline = period === "week" ? comparison.baselines.previousWeek : comparison.baselines[period];
  const delta = period === "week" ? comparison.comparisons.week : comparison.comparisons[period];
  const status = comparisonStatus(current, baseline, delta, comparison.available);
  const title = period === "week" ? "Эта неделя против прошлой" : `Сегодня против ${baseline.label || "нормы"}`;

  return (
    <Panel title="Сегодня против нормы" action={<StatusPill status={status}>{comparisonStatusLabel[status]}</StatusPill>}>
      {comparison.available ? (
        <div className="grid gap-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <p className="text-sm text-report-muted">{title}</p>
              <p className="mt-2 text-xl font-semibold leading-snug text-report-text">
                {comparisonVerdict(status, period)}
              </p>
            </div>
            <div className="grid grid-cols-4 gap-1 rounded-lg border border-ink-700 bg-ink-900/45 p-1">
              {comparisonPeriods.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setPeriod(item.key)}
                  className={`rounded-md px-3 py-2 text-sm transition ${
                    period === item.key
                      ? "bg-report-blue/20 text-report-blue"
                      : "text-report-muted hover:bg-ink-800 hover:text-report-text"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ComparisonMiniStat
              label="Reviews"
              value={formatCount(current.reviews)}
              delta={formatCountDelta(delta.reviews.delta)}
              detail={formatPercentDelta(delta.reviews.percentDelta)}
              tone={deltaTone(delta.reviews.delta, "moreIsGood")}
            />
            <ComparisonMiniStat
              label="Study time"
              value={formatMinutes(current.studyMinutes)}
              delta={formatMinuteDelta(delta.studyMinutes.delta)}
              detail={formatPercentDelta(delta.studyMinutes.percentDelta)}
              tone="neutral"
            />
            <ComparisonMiniStat
              label="Pass rate"
              value={formatNullablePercent(current.passRate)}
              delta={formatPointDelta(delta.passRate.deltaPp)}
              detail="процентные пункты"
              tone={deltaTone(delta.passRate.deltaPp, "moreIsGood")}
            />
            <ComparisonMiniStat
              label="New cards"
              value={formatCount(current.newCards)}
              delta={formatCountDelta(delta.newCards.delta)}
              detail={formatPercentDelta(delta.newCards.percentDelta)}
              tone={newCardsTone(delta.newCards.percentDelta)}
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.42fr)]">
            <div className="grid gap-2">
              {comparison.insights.slice(0, 3).map((insight) => (
                <div
                  key={`${insight.title}-${insight.metric}`}
                  className={`rounded-lg border bg-ink-900/45 p-3 status-border-${severityStatus(insight.severity)}`}
                >
                  <p className="text-sm font-semibold text-report-text">{insight.title}</p>
                  <p className="mt-1 text-sm leading-6 text-report-muted">{insight.text}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label="Fail rate" value={formatNullablePercent(current.failRate)} tone={deltaTone(delta.failRate.deltaPp, "lessIsGood")} />
              <MiniStat label="Avg answer" value={formatSeconds(current.avgAnswerSeconds)} />
              <MiniStat label="Active decks" value={formatCount(current.activeDecks)} />
              <MiniStat label="Baseline" value={baseline.reviews > 0 ? formatCount(baseline.reviews) : "Нет данных"} />
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="История ещё короткая" text={comparison.message || "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы."} />
      )}
    </Panel>
  );
}

function ActivitySection() {
  const { activity } = useReport();
  const heatmapMax = Math.max(...activity.days.map((day) => day.reviews), 1);

  return (
    <Panel title="Activity" action={<StatusPill status="good">{activity.currentStreak} day streak</StatusPill>}>
      {activity.available ? (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <MiniStat label="Active" value={activity.activeDays.toString()} />
            <MiniStat label="Missed" value={activity.missedDays.toString()} />
            <MiniStat label="Current" value={`${activity.currentStreak} дней`} />
            <MiniStat label="Best" value={`${activity.bestStreak} дней`} />
            <MiniStat label="Best day" value={activity.bestDay} />
          </div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={activity.weekdayAverage}>
                <CartesianGrid stroke="#2b3a50" vertical={false} />
                <XAxis dataKey="day" stroke="#8fa3bf" tickLine={false} axisLine={false} />
                <YAxis stroke="#8fa3bf" tickLine={false} axisLine={false} width={34} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="reviews" radius={[7, 7, 0, 0]} fill={chartColors.blue} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-[repeat(12,minmax(18px,1fr))] gap-2 sm:grid-cols-[repeat(23,minmax(18px,1fr))]">
            {activity.days.map((day) => (
              <div
                key={day.date}
                title={`${day.date}: ${day.reviews} reviews`}
                className="aspect-square rounded-[6px] border border-ink-700"
                style={{ backgroundColor: heatmapColor(day.reviews, heatmapMax) }}
              />
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="Нет данных активности" text="Revlog за выбранный период пустой, поэтому heatmap пока нечего показать." />
      )}
    </Panel>
  );
}

function DeckPerformanceSection({
  problemDecks,
  bestDecks,
}: {
  problemDecks: DeckPerformance[];
  bestDecks: DeckPerformance[];
}) {
  return (
    <section className="grid min-w-0 gap-5">
      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Panel title="Problem Decks" action={<StatusPill status="danger">{problemDecks.length} требуют внимания</StatusPill>}>
          <div className="grid gap-3 lg:grid-cols-3">
            {problemDecks.map((deck) => (
              <DeckCard key={deck.id} deck={deck} />
            ))}
          </div>
        </Panel>
        <Panel title="Best Decks" action={<StatusPill status="good">стабильные</StatusPill>}>
          <div className="grid min-w-0 gap-3">
            {bestDecks.map((deck) => (
              <div key={deck.id} className="flex min-w-0 max-w-full items-center justify-between gap-4 rounded-lg border border-ink-700 bg-ink-800/55 p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{deck.name}</p>
                  <p className="mt-1 truncate text-xs text-report-muted">{deck.explanation}</p>
                </div>
                <span className="shrink-0 text-lg font-semibold text-report-success">{formatPercent(deck.passRate)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <DeckTable />
    </section>
  );
}

function DeckCard({ deck }: { deck: DeckPerformance }) {
  return (
    <article className={`deck-card status-${deck.status}`}>
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 text-sm font-semibold leading-6">{deck.name}</h3>
        <StatusPill status={deck.status}>{statusLabel[deck.status]}</StatusPill>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <MiniStat label="Pass" value={formatPercent(deck.passRate)} />
        <MiniStat label="Fail" value={deck.failCount.toString()} />
        <MiniStat label="Avg" value={`${deck.averageAnswerSeconds}s`} />
      </div>
      <p className="mt-4 text-sm leading-6 text-report-muted">{deck.explanation}.</p>
    </article>
  );
}

function DeckTable() {
  const report = useReport();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<DeckFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("failCount");
  const [direction, setDirection] = useState<SortDirection>("desc");
  const [expanded, setExpanded] = useState(false);

  const rows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return report.decks
      .filter((deck) => filter === "all" || deck.status === filter)
      .filter((deck) => deck.name.toLowerCase().includes(normalizedQuery))
      .sort((a, b) => {
        const aValue = a[sortKey];
        const bValue = b[sortKey];
        const result =
          typeof aValue === "string" && typeof bValue === "string"
            ? aValue.localeCompare(bValue)
            : Number(aValue) - Number(bValue);
        return direction === "asc" ? result : -result;
      });
  }, [direction, filter, query, report.decks, sortKey]);

  useEffect(() => {
    setExpanded(false);
  }, [direction, filter, query, sortKey]);

  const canCollapse = rows.length > collapsedDeckTableRows;
  const visibleRows = canCollapse && !expanded ? rows.slice(0, collapsedDeckTableRows) : rows;
  const hiddenRows = rows.length - visibleRows.length;

  const requestSort = (key: SortKey) => {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setDirection(key === "name" ? "asc" : "desc");
  };

  return (
    <Panel title="Deck Performance Table" action={<StatusPill status="neutral">{rows.length} decks</StatusPill>}>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <label className="relative block md:w-96">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full rounded-lg border border-ink-700 bg-ink-900 py-2.5 pl-10 pr-3 text-sm text-report-text outline-none transition focus:border-report-blue"
            placeholder="Search deck name"
          />
        </label>
        <label className="relative block md:w-56">
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as DeckFilter)}
            className="w-full appearance-none rounded-lg border border-ink-700 bg-ink-900 px-3 py-2.5 text-sm text-report-text outline-none transition focus:border-report-blue"
          >
            <option value="all">All statuses</option>
            <option value="good">Good</option>
            <option value="neutral">Neutral</option>
            <option value="warning">Warning</option>
            <option value="danger">Danger</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
        </label>
      </div>
      <div className="overflow-x-auto rounded-lg border border-ink-700">
        <table className="min-w-[920px] w-full border-collapse text-sm">
          <thead className="sticky top-0 bg-ink-800 text-xs uppercase tracking-[0.04em] text-report-muted">
            <tr>
              <SortableTh label="Deck" sortKey="name" activeKey={sortKey} direction={direction} onSort={requestSort} />
              <SortableTh label="Reviews" sortKey="totalReviews" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <th className="px-3 py-3 text-right">New</th>
              <SortableTh label="Pass rate" sortKey="passRate" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <SortableTh label="Fail" sortKey="failCount" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <SortableTh label="Avg answer" sortKey="averageAnswerSeconds" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <th className="px-3 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((deck) => (
              <tr key={deck.id} className="border-t border-ink-700/80 hover:bg-ink-800/45">
                <td className="max-w-[340px] px-3 py-3">
                  <div className="truncate font-medium text-report-text" title={deck.name}>
                    {deck.name}
                  </div>
                  <div className="mt-1 truncate text-xs text-report-muted">{deck.explanation}</div>
                </td>
                <td className="px-3 py-3 text-right tabular-nums">{deck.totalReviews}</td>
                <td className="px-3 py-3 text-right tabular-nums">{deck.newCards}</td>
                <td className="px-3 py-3 text-right tabular-nums">{formatPercent(deck.passRate)}</td>
                <td className="px-3 py-3 text-right tabular-nums">{deck.failCount}</td>
                <td className="px-3 py-3 text-right tabular-nums">{deck.averageAnswerSeconds}s</td>
                <td className="px-3 py-3">
                  <StatusPill status={deck.status}>{statusLabel[deck.status]}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {canCollapse && (
        <div className="mt-3 flex flex-col gap-2 rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-3 text-sm text-report-muted sm:flex-row sm:items-center sm:justify-between">
          <span>
            {expanded
              ? `Показаны все ${rows.length} строк.`
              : `Показаны первые ${visibleRows.length} строк, ещё ${hiddenRows} скрыто.`}
          </span>
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="inline-flex items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 font-medium text-report-blue transition hover:border-report-blue hover:bg-report-blue/15"
          >
            {expanded ? "Свернуть таблицу" : "Показать все строки"}
          </button>
        </div>
      )}
    </Panel>
  );
}

function ForecastSection() {
  const { forecast } = useReport();

  return (
    <Panel title="Forecast" action={<StatusPill status={forecast.overloadRisk}>overload: {statusLabel[forecast.overloadRisk]}</StatusPill>}>
      {forecast.available ? (
        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MiniStat label="Tomorrow" value={forecast.tomorrow.toString()} />
            <MiniStat label="Next 7 days" value={forecast.next7Days.toString()} />
            <MiniStat label="Next 30 days" value={forecast.next30Days.toString()} />
            <MiniStat label="Active day" value={forecast.activeDayBaseline.toString()} />
          </div>
          <div className="h-64">
            <ResponsiveContainer>
              <AreaChart data={forecast.daily}>
                <defs>
                  <linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={chartColors.purple} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={chartColors.purple} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#2b3a50" vertical={false} />
                <XAxis dataKey="offset" stroke="#8fa3bf" tickLine={false} axisLine={false} />
                <YAxis stroke="#8fa3bf" tickLine={false} axisLine={false} width={34} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="due" stroke={chartColors.purple} fill="url(#forecastFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="rounded-lg border border-report-blue/35 bg-report-blue/10 p-3 text-sm leading-6">
            {forecast.recommendation}
          </p>
        </div>
      ) : (
        <EmptyState title="Нет прогноза" text="Планировщик Anki не отдал due-данные, поэтому график нагрузки скрыт." />
      )}
    </Panel>
  );
}

function FsrsSection() {
  const { fsrs } = useReport();
  const recall = fsrs.predictedRecall ?? 0;

  return (
    <Panel title="FSRS" action={<StatusPill status={fsrs.settings.enabled ? "good" : "neutral"}>{fsrs.settings.enabled ? "enabled" : "disabled"}</StatusPill>}>
      {fsrs.settings.enabled ? (
        <div className="grid gap-4">
          <div className="rounded-lg border border-ink-700 bg-ink-800/55 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-report-muted">Average predicted recall</p>
                <p className="mt-1 text-3xl font-semibold">{formatPercent(recall)}</p>
              </div>
              <Brain className="text-report-purple" size={34} />
            </div>
            <div className="mt-4 h-3 rounded-full bg-ink-900">
              <div
                className="h-full rounded-full bg-gradient-to-r from-report-purple to-report-blue"
                style={{ width: `${Math.round(recall * 100)}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-report-muted">
              Desired retention: {fsrs.settings.desiredRetention ? formatPercent(fsrs.settings.desiredRetention) : "нет данных"}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <MiniStat label="Below target" value={fsrs.cardsBelowTarget.toString()} />
            <MiniStat label="High forgetting risk" value={fsrs.highForgettingRisk.toString()} tone="danger" />
            <MiniStat label="Avg difficulty" value={fsrs.averageDifficulty ? `${fsrs.averageDifficulty}%` : "Нет данных"} />
            <MiniStat label="Future FSRS load" value={fsrs.futureLoad30Days.toString()} />
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status={fsrs.settings.helperDetected ? "good" : "neutral"}>FSRS Helper detected</StatusPill>
            <StatusPill status={fsrs.settings.helperConfigAvailable ? "good" : "neutral"}>config available</StatusPill>
            <StatusPill status="neutral">reschedule {fsrs.settings.rescheduleEnabled ? "on" : "off"}</StatusPill>
            <StatusPill status={fsrs.settings.autoDisperse ? "good" : "neutral"}>auto disperse</StatusPill>
          </div>
        </div>
      ) : (
        <EmptyState title="FSRS выключен" text="Когда FSRS появится в JSON, блок покажет recall, difficulty и риск забывания." />
      )}
    </Panel>
  );
}

function RecommendationsSection() {
  const { recommendations } = useReport();

  return (
    <section className="rounded-xl border border-report-blue/35 bg-gradient-to-br from-report-blue/12 via-ink-850 to-report-purple/12 p-5 shadow-glow">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <p className="text-sm uppercase tracking-[0.04em] text-report-blue">Recommendations / Next Actions</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">{recommendations.mainAction}</h2>
          <p className="mt-4 text-sm leading-6 text-report-muted">{recommendations.why}</p>
          <p className="mt-3 rounded-lg border border-report-danger/35 bg-report-danger/10 p-3 text-sm leading-6 text-report-text">
            Пока не делать: {recommendations.avoid}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {recommendations.checklist.map((item) => (
            <div key={item} className="flex gap-3 rounded-lg border border-ink-700 bg-ink-800/65 p-3">
              <CheckCircle2 className="mt-0.5 shrink-0 text-report-success" size={18} />
              <span className="text-sm leading-6">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TechnicalDetails() {
  const { metadata } = useReport();
  const rows = [
    ["period", metadata.period],
    ["selected decks", metadata.selectedDecks.join(", ")],
    ["include children", metadata.includeChildren ? "yes" : "no"],
    ["detail mode", metadata.detailMode],
    ["answer mode", metadata.answerMode === "pass_fail" ? "Pass/Fail" : "4-button"],
    ["deleted card reviews", metadata.deletedCardReviews.toString()],
    ["unavailable tracker notes", metadata.unavailableTrackerNotes.join(" ")],
  ];

  return (
    <Panel title="Technical Details" action={<StatusPill status="neutral">secondary</StatusPill>}>
      <div className="grid gap-2 md:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-ink-700 bg-ink-900/50 px-3 py-2">
            <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
            <p className="mt-1 text-sm leading-6 text-report-text">{value}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold tracking-normal">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="max-w-full rounded-lg border border-ink-700 bg-ink-800/70 px-2.5 py-1">
      <span className="text-report-muted">{label}: </span>
      <span className="text-report-text">{value}</span>
    </span>
  );
}

function HeroNote({ title, text, status }: { title: string; text: string; status: Status }) {
  return (
    <div className={`rounded-lg border bg-ink-900/45 p-3 status-border-${status}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{title}</p>
      <p className="mt-2 text-sm leading-6 text-report-text">{text}</p>
    </div>
  );
}

function MiniStat({ label, value, tone = "neutral" }: { label: string; value: string; tone?: Status }) {
  return (
    <div className={`rounded-lg border border-ink-700 bg-ink-900/45 p-3 status-border-${tone}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-report-text">{value}</p>
    </div>
  );
}

function ComparisonMiniStat({
  label,
  value,
  delta,
  detail,
  tone,
}: {
  label: string;
  value: string;
  delta: string;
  detail: string;
  tone: Status;
}) {
  return (
    <div className={`rounded-lg border border-ink-700 bg-ink-900/45 p-3 status-border-${tone}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-report-text">{value}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        <span className={`font-semibold ${toneTextClass(tone)}`}>{delta}</span>
        <span className="text-report-muted">{detail}</span>
      </div>
    </div>
  );
}

function StatusPill({ status, children }: { status: Status; children: React.ReactNode }) {
  return <span className={`status-pill status-${status}`}>{children}</span>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-700 bg-ink-900/45 p-5 text-center">
      <p className="font-semibold">{title}</p>
      <p className="mt-2 text-sm leading-6 text-report-muted">{text}</p>
    </div>
  );
}

function SortableTh({
  label,
  sortKey,
  activeKey,
  direction,
  align = "left",
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  direction: SortDirection;
  align?: "left" | "right";
  onSort: (key: SortKey) => void;
}) {
  const active = sortKey === activeKey;
  return (
    <th className={`px-3 py-3 ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 ${align === "right" ? "justify-end" : "justify-start"} w-full hover:text-report-blue`}
      >
        <span>{label}</span>
        {active && direction === "desc" ? <ArrowDown size={14} /> : <ArrowUpDown size={14} />}
      </button>
    </th>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-sm shadow-panel">
      {label !== undefined && <p className="mb-1 text-report-muted">{label}</p>}
      {payload.map((item: any) => (
        <p key={`${item.name}-${item.value}`} className="text-report-text">
          {item.name}: <span className="font-semibold">{item.value}</span>
        </p>
      ))}
    </div>
  );
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) {
    return "0%";
  }
  return `${Math.round(value * 100)}%`;
}

function comparisonStatus(current: DailyStats, baseline: DailyStats, delta: ComparisonDelta, available: boolean): Status {
  if (!available || baseline.reviews <= 0) {
    return "neutral";
  }
  const reviewLift = delta.reviews.percentDelta ?? 0;
  const passDelta = delta.passRate.deltaPp ?? 0;
  const failDelta = delta.failRate.deltaPp ?? 0;
  const answerLift = delta.avgAnswerSeconds.percentDelta ?? 0;
  if (reviewLift >= 50 && failDelta >= 3 && answerLift >= 15) {
    return "danger";
  }
  if ((delta.newCards.percentDelta ?? 0) >= 50 && failDelta > 0) {
    return "warning";
  }
  if (current.reviews >= baseline.reviews && passDelta >= -2 && failDelta < 3) {
    return "good";
  }
  return "neutral";
}

function emptyComparison(): NonNullable<StudyReport["comparison"]> {
  const emptyStats: DailyStats = {
    date: "",
    label: "Нет данных",
    reviews: 0,
    newCards: 0,
    pass: 0,
    fail: 0,
    hard: 0,
    easy: 0,
    studySeconds: 0,
    studyMinutes: 0,
    avgAnswerSeconds: null,
    activeDecks: 0,
    passRate: null,
    failRate: null,
  };
  const emptyDelta: ComparisonDelta = {
    reviews: { delta: null, percentDelta: null },
    newCards: { delta: null, percentDelta: null },
    studyMinutes: { delta: null, percentDelta: null },
    passRate: { deltaPp: null },
    failRate: { deltaPp: null },
    avgAnswerSeconds: { delta: null, percentDelta: null },
    activeDecks: { delta: null, percentDelta: null },
  };
  return {
    available: false,
    message: "Недостаточно истории для сравнения. Данные начнут появляться после нескольких дней учёбы.",
    today: { ...emptyStats, label: "Сегодня" },
    baselines: {
      yesterday: { ...emptyStats, label: "Вчера" },
      avg7: { ...emptyStats, label: "Последние 7 дней" },
      avg30: { ...emptyStats, label: "Последние 30 дней" },
      sameWeekdayLastWeek: { ...emptyStats, label: "Этот день прошлой недели" },
      currentWeek: { ...emptyStats, label: "Эта неделя" },
      previousWeek: { ...emptyStats, label: "Прошлая неделя" },
      currentMonth: { ...emptyStats, label: "Этот месяц" },
      previousMonth: { ...emptyStats, label: "Прошлый месяц" },
    },
    comparisons: {
      yesterday: emptyDelta,
      avg7: emptyDelta,
      avg30: emptyDelta,
      sameWeekdayLastWeek: emptyDelta,
      week: emptyDelta,
      month: emptyDelta,
    },
    insights: [],
  };
}

function comparisonVerdict(status: Status, period: ComparisonPeriod) {
  if (status === "good") {
    return period === "week" ? "Неделя идёт активнее обычного." : "Сегодня вы учитесь лучше или активнее нормы.";
  }
  if (status === "danger") {
    return "Объём высокий, но качество просело.";
  }
  if (status === "warning") {
    return "Есть сигнал к осторожности с нагрузкой.";
  }
  return period === "week" ? "Неделя близка к прошлой." : "Сегодня примерно в вашем обычном темпе.";
}

function severityStatus(severity: "positive" | "neutral" | "warning" | "danger"): Status {
  return severity === "positive" ? "good" : severity;
}

function deltaTone(value: number | null, mode: "moreIsGood" | "lessIsGood"): Status {
  if (value === null || Math.abs(value) < 0.5) {
    return "neutral";
  }
  const isGood = mode === "moreIsGood" ? value > 0 : value < 0;
  return isGood ? "good" : "warning";
}

function newCardsTone(percentDelta: number | null): Status {
  if (percentDelta === null || Math.abs(percentDelta) < 20) {
    return "neutral";
  }
  return percentDelta > 50 ? "warning" : "neutral";
}

function toneTextClass(tone: Status) {
  return {
    good: "text-report-success",
    neutral: "text-report-blue",
    warning: "text-report-warning",
    danger: "text-report-danger",
  }[tone];
}

function formatNullablePercent(value: number | null) {
  return value === null ? "Нет данных" : formatPercent(value);
}

function formatCount(value: number) {
  return Number.isFinite(value) ? Math.round(value).toLocaleString("ru-RU") : "0";
}

function formatCountDelta(value: number | null) {
  return formatSignedValue(value, "");
}

function formatMinuteDelta(value: number | null) {
  const formatted = formatSignedValue(value, " мин");
  return formatted === "нет данных" ? formatted : formatted.replace("+0 мин", "0 мин");
}

function formatPercentDelta(value: number | null) {
  if (value === null) {
    return "нет истории";
  }
  const rounded = Math.round(value);
  if (Math.abs(rounded) < 1) {
    return "→ около нормы";
  }
  return `${rounded > 0 ? "↑" : "↓"} ${Math.abs(rounded)}% к норме`;
}

function formatPointDelta(value: number | null) {
  if (value === null) {
    return "нет данных";
  }
  if (Math.abs(value) < 0.5) {
    return "→ 0 п.п.";
  }
  return `${value > 0 ? "↑" : "↓"} ${Math.abs(value).toFixed(1)} п.п.`;
}

function formatMinutes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 мин";
  }
  const minutes = Math.round(value);
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours && rest) {
    return `${hours} ч ${rest} мин`;
  }
  if (hours) {
    return `${hours} ч`;
  }
  return `${minutes} мин`;
}

function formatSeconds(value: number | null) {
  if (value === null || !Number.isFinite(value) || value <= 0) {
    return "Нет данных";
  }
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)} сек`;
}

function formatSignedValue(value: number | null, suffix: string) {
  if (value === null) {
    return "нет данных";
  }
  const rounded = Math.round(value);
  if (rounded === 0) {
    return `→ 0${suffix}`;
  }
  return `${rounded > 0 ? "↑ +" : "↓ -"}${Math.abs(rounded).toLocaleString("ru-RU")}${suffix}`;
}

function heatmapColor(reviews: number, max: number) {
  if (reviews <= 0) {
    return "#111827";
  }
  const intensity = Math.min(1, reviews / max);
  if (intensity > 0.75) {
    return "#3db4f2";
  }
  if (intensity > 0.5) {
    return "#287eaf";
  }
  if (intensity > 0.25) {
    return "#1d5578";
  }
  return "#17364f";
}

export default HomePage;
