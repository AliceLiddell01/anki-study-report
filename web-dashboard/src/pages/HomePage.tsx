import {
  AlertTriangle,
  ArrowDown,
  ArrowUpDown,
  BarChart3,
  Brain,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
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
import { useTranslation } from "react-i18next";
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
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";

const chartColors = {
  blue: "#3db4f2",
  purple: "#7c5cff",
  success: "#67d391",
  warning: "#f6c177",
  danger: "#ef6f6c",
};
const collapsedDeckTableRows = 5;
const homeKpiIds = new Set(["pass_rate", "fail_rate", "new_cards", "study_time", "active_decks", "tomorrow_due"]);

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

const comparisonPeriods: ComparisonPeriod[] = ["yesterday", "avg7", "avg30", "week"];
const th = (key: string, options?: Record<string, unknown>) => i18n.t(`home.${key}`, { ns: "pages", ...options });
const statusText = (status: Status) => th(`status.${status}`);
const comparisonStatusText = (status: Status) => th(`status.${status === "good" ? "better" : status === "neutral" ? "normal" : status === "danger" ? "overload" : "warning"}`);

const ReportContext = createContext<StudyReport | null>(null);

function useReport() {
  const report = useContext(ReportContext);
  if (!report) {
    throw new Error("Study report is not loaded");
  }
  return report;
}

function HomePage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  useTranslation("pages");
  if (loadState !== "ready" || !report) {
    return <EmptyDashboard state={loadState} />;
  }

  const homeReport: StudyReport = report.today ? { ...report, ...report.today } : report;
  const problemDecks = homeReport.decks
    .filter((deck) => deck.status === "danger" || deck.status === "warning")
    .slice(0, 3);
  const bestDecks = [...homeReport.decks]
    .filter((deck) => deck.status === "good")
    .sort((a, b) => b.passRate - a.passRate)
    .slice(0, 3);

  return (
    <ReportContext.Provider value={homeReport}>
      <div className="grid min-w-0 gap-5">
        <Header />
        <HeroSummary />
        <KpiGrid metrics={homeReport.kpis} />
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
    ? th("empty.loadingTitle")
    : state === "empty"
      ? th("empty.emptyTitle")
      : state === "forbidden"
        ? th("empty.forbiddenTitle")
      : th("empty.errorTitle");
  const text = isLoading
    ? th("empty.loadingText")
    : state === "empty"
      ? th("empty.emptyText")
      : state === "forbidden"
        ? th("empty.forbiddenText")
      : th("empty.errorText");

  return (
    <section className="mx-auto max-w-2xl rounded-xl border border-dashed border-ink-700 bg-ink-850 p-6 text-center shadow-panel">
      <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-report-muted">{text}</p>
    </section>
  );
}

function Header() {
  const { metadata } = useReport();
  const deckScope = deckScopeSummary(metadata);
  const filtered = deckScope.summary !== th("header.allDecks");

  return (
    <header className="rounded-xl border border-ink-700/90 bg-ink-850/95 px-4 py-4 shadow-panel sm:px-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-normal text-report-text sm:text-2xl">
              {th("header.title")}
            </h1>
            <StatusPill status="warning">{th("header.badge")}</StatusPill>
          </div>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
            {th("header.localDay", { date: metadata.todayDate ? ` · ${metadata.todayDate}` : "" })}
          </p>
        </div>
        {filtered ? (
          <a href="#/settings" className="inline-flex items-center rounded-lg border border-report-blue/40 bg-report-blue/10 px-3 py-2 text-sm font-medium text-report-blue" title={deckScope.detail || deckScope.summary}>
            {deckScope.summary}
          </a>
        ) : null}
      </div>
    </header>
  );
}

function HeroSummary() {
  const report = useReport();
  const { summary } = report;

  return (
    <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
      <div className="hero-surface rounded-xl border border-ink-700 p-5 shadow-glow">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={summary.riskLevel}>{th("hero.risk", { status: statusText(summary.riskLevel) })}</StatusPill>
          <StatusPill status="neutral">Pass/Fail</StatusPill>
        </div>
        <p className="mt-5 max-w-5xl text-2xl font-semibold leading-snug tracking-normal text-report-text lg:text-3xl">
          {summary.verdict}
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <HeroNote title={th("hero.mainAction")} text={summary.mainAction} status="good" />
          <HeroNote title={th("hero.warning")} text={humanizeUiText(summary.warning)} status="danger" />
          <HeroNote title={th("hero.newCards")} text={summary.newCardsAdvice} status="warning" />
        </div>
      </div>
      <div className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-report-muted">{th("hero.next")}</p>
            <h2 className="mt-1 text-lg font-semibold">{th("hero.stabilize")}</h2>
          </div>
          <div className="rounded-lg bg-report-blue/15 p-3 text-report-blue">
            <Brain size={24} />
          </div>
        </div>
        <div className="mt-5 space-y-3">
          {report.recommendations.checklist.slice(0, 3).map((item) => (
            <div key={item} className="nested-surface flex gap-3 rounded-lg border border-ink-700 p-3">
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
  const visibleMetrics = metrics
    .filter((metric) => homeKpiIds.has(metric.id))
    .slice(0, 6);

  return (
    <section className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
      {visibleMetrics.map((metric) => {
        const Icon = iconMap[metric.icon as keyof typeof iconMap] ?? BarChart3;
        return (
          <article key={metric.id} className={`kpi-card status-${metric.status}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium uppercase tracking-[0.04em] text-report-muted">
                  {kpiLabel(metric)}
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
    <Panel title={th("answers.title")} action={<StatusPill status="neutral">{th("answers.badge")}</StatusPill>}>
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(260px,340px)_minmax(240px,1fr)] lg:items-center">
        <div className="h-[min(340px,58vw)] min-h-[260px] max-h-[340px] min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius="55%" outerRadius="82%" paddingAngle={3}>
                {data.map((item) => (
                  <Cell key={item.label} fill={item.color} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grid min-w-0 gap-3">
          {data.map((item) => (
            <div key={item.label} className="nested-surface flex items-center justify-between gap-4 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm text-report-muted">{answerLabel(item.label)}</span>
              </div>
              <span className="text-sm font-semibold text-report-text">
                {item.value} · {formatPercent(item.value / total)}
              </span>
            </div>
          ))}
          <p className="rounded-lg border border-report-warning/35 bg-report-warning/10 p-3 text-sm leading-6 text-report-text">
            {th("answers.summary", { pass: formatPercent(pass / total), fail: formatPercent(fail / total) })}
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
  const title = period === "week" ? th("comparison.weekTitle") : th("comparison.todayTitle", { baseline: baseline.label || th("comparison.baseline") });

  return (
    <Panel title={th("comparison.title")} action={<StatusPill status={status}>{comparisonStatusText(status)}</StatusPill>}>
      {comparison.available ? (
        <div className="grid gap-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <p className="text-sm text-report-muted">{title}</p>
              <p className="mt-2 text-xl font-semibold leading-snug text-report-text">
                {comparisonVerdict(status, period)}
              </p>
            </div>
            <div className="nested-surface grid grid-cols-4 gap-1 rounded-lg border border-ink-700 p-1">
              {comparisonPeriods.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setPeriod(item)}
                  className={`rounded-md px-3 py-2 text-sm transition ${
                    period === item
                      ? "bg-report-blue/20 text-report-blue"
                      : "text-report-muted hover:bg-ink-800 hover:text-report-text"
                  }`}
                >
                  {th(`periods.${item}`)}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ComparisonMiniStat
              label={th("comparison.reviews")}
              value={formatCount(current.reviews)}
              delta={formatCountDelta(delta.reviews.delta)}
              detail={formatPercentDelta(delta.reviews.percentDelta)}
              tone={deltaTone(delta.reviews.delta, "moreIsGood")}
            />
            <ComparisonMiniStat
              label={th("comparison.study")}
              value={formatMinutes(current.studyMinutes)}
              delta={formatMinuteDelta(delta.studyMinutes.delta)}
              detail={formatPercentDelta(delta.studyMinutes.percentDelta)}
              tone="neutral"
            />
            <ComparisonMiniStat
              label={th("comparison.success")}
              value={formatNullablePercent(current.passRate)}
              delta={formatPointDelta(delta.passRate.deltaPp)}
              detail={th("comparison.percentagePoints")}
              tone={deltaTone(delta.passRate.deltaPp, "moreIsGood")}
            />
            <ComparisonMiniStat
              label={th("comparison.new")}
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
                  className={`nested-surface rounded-lg border p-3 status-border-${severityStatus(insight.severity)}`}
                >
                  <p className="text-sm font-semibold text-report-text">{insight.title}</p>
                  <p className="mt-1 text-sm leading-6 text-report-muted">{insight.text}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label={th("comparison.failures")} value={formatNullablePercent(current.failRate)} tone={deltaTone(delta.failRate.deltaPp, "lessIsGood")} />
              <MiniStat label={th("comparison.averageAnswer")} value={formatSeconds(current.avgAnswerSeconds)} />
              <MiniStat label={th("comparison.activeDecks")} value={formatCount(current.activeDecks)} />
              <MiniStat label={th("comparison.norm")} value={baseline.reviews > 0 ? formatCount(baseline.reviews) : th("comparison.noData")} />
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title={th("comparison.shortTitle")} text={comparison.message || th("comparison.shortText")} />
      )}
    </Panel>
  );
}

function ActivitySection() {
  const { activity } = useReport();
  const [selectedYear, setSelectedYear] = useState(() => defaultActivityYear(activity.days));
  const years = useMemo(() => activityYears(activity.days, selectedYear), [activity.days, selectedYear]);
  const visibleDays = useMemo(
    () => activity.days.filter((day) => yearFromDate(day.date) === selectedYear),
    [activity.days, selectedYear],
  );
  const heatmapMax = Math.max(...visibleDays.map((day) => day.reviews), 1);

  useEffect(() => {
    setSelectedYear(defaultActivityYear(activity.days));
  }, [activity.days]);

  return (
    <Panel
      title={th("activity.title")}
      action={
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="form-control inline-flex h-9 w-9 items-center justify-center text-report-muted hover:text-report-text"
            onClick={() => setSelectedYear((year) => year - 1)}
            title={th("activity.previous")}
            aria-label={th("activity.previousAria")}
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </button>
          <select
            value={selectedYear}
            onChange={(event) => setSelectedYear(Number(event.target.value))}
            className="form-control h-9 px-3 text-sm"
            aria-label={th("activity.yearAria")}
          >
            {years.map((year) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
          <button
            type="button"
            className="form-control inline-flex h-9 w-9 items-center justify-center text-report-muted hover:text-report-text"
            onClick={() => setSelectedYear((year) => year + 1)}
            title={th("activity.next")}
            aria-label={th("activity.nextAria")}
          >
            <ChevronRight size={16} aria-hidden="true" />
          </button>
        </div>
      }
    >
      {activity.available ? (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <MiniStat label={th("activity.activeDays")} value={activity.activeDays.toString()} />
            <MiniStat label={th("activity.missed")} value={activity.missedDays.toString()} />
            <MiniStat label={th("activity.currentStreak")} value={th("activity.days", { count: activity.currentStreak })} />
            <MiniStat label={th("activity.bestStreak")} value={th("activity.days", { count: activity.bestStreak })} />
            <MiniStat label={th("activity.bestDay")} value={activity.bestDay} />
          </div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={activity.weekdayAverage}>
                <CartesianGrid stroke="rgb(var(--color-border-subtle))" vertical={false} />
                <XAxis dataKey="day" stroke="rgb(var(--color-text-muted))" tickLine={false} axisLine={false} />
                <YAxis stroke="rgb(var(--color-text-muted))" tickLine={false} axisLine={false} width={34} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="reviews" radius={[7, 7, 0, 0]} fill={chartColors.blue} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {visibleDays.length > 0 ? (
            <div className="grid grid-cols-[repeat(12,minmax(18px,1fr))] gap-2 sm:grid-cols-[repeat(23,minmax(18px,1fr))]">
              {visibleDays.map((day) => (
                <div
                  key={day.date}
                  title={`${day.date}: ${day.reviews} reviews`}
                  className="aspect-square rounded-[6px] border border-ink-700"
                  style={{ backgroundColor: heatmapColor(day.reviews, heatmapMax) }}
                />
              ))}
            </div>
          ) : (
            <EmptyState title={th("activity.noYear")} text={th("activity.noYearText", { year: selectedYear })} />
          )}
        </div>
      ) : (
        <EmptyState title={th("activity.noData")} text={th("activity.noDataText")} />
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
        <Panel title={th("decks.problems")} action={<StatusPill status="danger">{th("decks.attention", { count: problemDecks.length })}</StatusPill>}>
          <div className="grid gap-3 lg:grid-cols-3">
            {problemDecks.map((deck) => (
              <DeckCard key={deck.id} deck={deck} />
            ))}
          </div>
        </Panel>
        <Panel title={th("decks.stable")} action={<StatusPill status="good">{th("decks.stableBadge")}</StatusPill>}>
          <div className="grid min-w-0 gap-3">
            {bestDecks.map((deck) => (
              <div key={deck.id} className="nested-surface flex min-w-0 max-w-full items-center justify-between gap-4 rounded-lg border border-ink-700 p-3">
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
        <StatusPill status={deck.status}>{statusText(deck.status)}</StatusPill>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <MiniStat label="Pass" value={formatPercent(deck.passRate)} />
        <MiniStat label="Fail" value={deck.failCount.toString()} />
        <MiniStat label="Avg" value={i18n.t("units.secondsShort", { ns: "common", value: deck.averageAnswerSeconds })} />
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
    <Panel title={th("decks.summary")} action={<StatusPill status="neutral">{th("decks.count", { count: rows.length })}</StatusPill>}>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <label className="relative block md:w-96">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="form-control w-full py-2.5 pl-10 pr-3 text-sm"
            placeholder={th("decks.search")}
          />
        </label>
        <label className="relative block md:w-56">
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as DeckFilter)}
            className="form-control w-full appearance-none px-3 py-2.5 pr-9 text-sm"
          >
            <option value="all">{th("decks.allStatuses")}</option>
            <option value="good">{th("decks.good")}</option>
            <option value="neutral">{th("decks.neutral")}</option>
            <option value="warning">{th("decks.warning")}</option>
            <option value="danger">{th("decks.danger")}</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
        </label>
      </div>
      <div className="overflow-x-auto rounded-lg border border-ink-700">
        <table className="table-readable min-w-[920px] w-full border-collapse">
          <thead className="sticky top-0 z-10 bg-ink-800 text-xs uppercase tracking-[0.04em] text-report-muted">
            <tr>
              <SortableTh label={th("decks.deck")} sortKey="name" activeKey={sortKey} direction={direction} onSort={requestSort} />
              <SortableTh label={th("decks.reviews")} sortKey="totalReviews" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <th className="px-3 py-3 text-right">{th("decks.new")}</th>
              <SortableTh label={th("decks.success")} sortKey="passRate" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <SortableTh label={th("decks.failures")} sortKey="failCount" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <SortableTh label={th("decks.answer")} sortKey="averageAnswerSeconds" activeKey={sortKey} direction={direction} onSort={requestSort} align="right" />
              <th className="px-3 py-3 text-left">{th("decks.status")}</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((deck) => (
              <tr key={deck.id} className="border-t border-ink-700/80 hover:bg-ink-800/45">
                <td className="max-w-[340px] px-3 py-3.5">
                  <div className="truncate font-semibold text-report-text" title={deck.name}>
                    {deck.name}
                  </div>
                  <div className="mt-1 truncate text-xs text-report-muted">{deck.explanation}</div>
                </td>
                <td className="px-3 py-3.5 text-right tabular-nums">{deck.totalReviews}</td>
                <td className="px-3 py-3.5 text-right tabular-nums">{deck.newCards}</td>
                <td className="px-3 py-3.5 text-right tabular-nums">{formatPercent(deck.passRate)}</td>
                <td className="px-3 py-3.5 text-right tabular-nums">{deck.failCount}</td>
                <td className="px-3 py-3.5 text-right tabular-nums">{i18n.t("units.secondsShort", { ns: "common", value: deck.averageAnswerSeconds })}</td>
                <td className="px-3 py-3.5">
                  <StatusPill status={deck.status}>{statusText(deck.status)}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {canCollapse && (
        <div className="nested-surface mt-3 flex flex-col gap-2 rounded-lg border border-ink-700 px-3 py-3 text-sm text-report-muted sm:flex-row sm:items-center sm:justify-between">
          <span>
            {expanded
              ? th("decks.allRows", { count: rows.length })
              : th("decks.limitedRows", { visible: visibleRows.length, hidden: hiddenRows })}
          </span>
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="inline-flex items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 font-medium text-report-blue transition hover:border-report-blue hover:bg-report-blue/15"
          >
            {expanded ? th("decks.collapse") : th("decks.showAll")}
          </button>
        </div>
      )}
    </Panel>
  );
}

function ForecastSection() {
  const { forecast } = useReport();

  return (
    <Panel title={th("forecast.title")} action={<StatusPill status={forecast.overloadRisk}>{th("forecast.overload", { status: statusText(forecast.overloadRisk) })}</StatusPill>}>
      {forecast.available ? (
        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MiniStat label={th("forecast.tomorrow")} value={forecast.tomorrow.toString()} />
            <MiniStat label={th("forecast.days7")} value={forecast.next7Days.toString()} />
            <MiniStat label={th("forecast.days30")} value={forecast.next30Days.toString()} />
            <MiniStat label={th("forecast.activeDay")} value={forecast.activeDayBaseline.toString()} />
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
                <CartesianGrid stroke="rgb(var(--color-border-subtle))" vertical={false} />
                <XAxis dataKey="offset" stroke="rgb(var(--color-text-muted))" tickLine={false} axisLine={false} />
                <YAxis stroke="rgb(var(--color-text-muted))" tickLine={false} axisLine={false} width={34} />
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
        <EmptyState title={th("forecast.emptyTitle")} text={th("forecast.emptyText")} />
      )}
    </Panel>
  );
}

function FsrsSection() {
  const { fsrs } = useReport();
  const recall = fsrs.predictedRecall ?? 0;

  return (
    <Panel title="FSRS" action={<StatusPill status={fsrs.settings.enabled ? "good" : "neutral"}>{fsrs.settings.enabled ? th("fsrs.enabled") : th("fsrs.disabled")}</StatusPill>}>
      {fsrs.settings.enabled ? (
        <div className="grid gap-4">
          <div className="nested-surface rounded-lg border border-ink-700 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-report-muted">{th("fsrs.predicted")}</p>
                <p className="mt-1 text-3xl font-semibold">{formatPercent(recall)}</p>
              </div>
              <Brain className="text-report-purple" size={34} />
            </div>
            <div className="mt-4 h-3 rounded-full bg-ink-900/70">
              <div
                className="h-full rounded-full bg-gradient-to-r from-report-purple to-report-blue"
                style={{ width: `${Math.round(recall * 100)}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-report-muted">
              {th("fsrs.desired", { value: fsrs.settings.desiredRetention ? formatPercent(fsrs.settings.desiredRetention) : th("fsrs.noDataLower") })}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <MiniStat label={th("fsrs.belowTarget")} value={fsrs.cardsBelowTarget.toString()} />
            <MiniStat label={th("fsrs.forgettingRisk")} value={fsrs.highForgettingRisk.toString()} tone="danger" />
            <MiniStat label={th("fsrs.difficulty")} value={fsrs.averageDifficulty ? `${fsrs.averageDifficulty}%` : th("technical.noData")} />
            <MiniStat label={th("fsrs.workload")} value={fsrs.futureLoad30Days.toString()} />
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status={fsrs.settings.helperDetected ? "good" : "neutral"}>{th("fsrs.helper")}</StatusPill>
            <StatusPill status={fsrs.settings.helperConfigAvailable ? "good" : "neutral"}>{th("fsrs.config")}</StatusPill>
            <StatusPill status="neutral">reschedule {fsrs.settings.rescheduleEnabled ? "on" : "off"}</StatusPill>
            <StatusPill status={fsrs.settings.autoDisperse ? "good" : "neutral"}>auto disperse</StatusPill>
          </div>
        </div>
      ) : (
        <EmptyState title={th("fsrs.emptyTitle")} text={th("fsrs.emptyText")} />
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
          <p className="text-sm uppercase tracking-[0.04em] text-report-blue">{th("recommendations.next")}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">{recommendations.mainAction}</h2>
          <p className="mt-4 text-sm leading-6 text-report-muted">{recommendations.why}</p>
          <p className="mt-3 rounded-lg border border-report-danger/35 bg-report-danger/10 p-3 text-sm leading-6 text-report-text">
            {th("recommendations.avoid", { value: recommendations.avoid })}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {recommendations.checklist.map((item) => (
            <div key={item} className="nested-surface flex gap-3 rounded-lg border border-ink-700 p-3">
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
  const deckScope = deckScopeSummary(metadata);
  const rows: Array<{ label: string; value: string; detail?: string }> = [
    { label: "period", value: metadata.period },
    { label: "selected decks", value: deckScope.summary, detail: deckScope.fullList },
    { label: "include children", value: metadata.includeChildren ? "yes" : "no" },
    { label: "created at", value: metadata.createdAt },
    { label: "detail mode", value: metadata.detailMode },
    { label: "answer mode", value: metadata.answerMode === "pass_fail" ? "Pass/Fail" : "4-button" },
    { label: "deleted card reviews", value: metadata.deletedCardReviews.toString() },
    { label: "unavailable tracker notes", value: metadata.unavailableTrackerNotes.join(" ") },
  ];

  return (
    <details className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
      <summary className="cursor-pointer text-lg font-semibold tracking-normal text-report-text">
        {th("technical.title")}
      </summary>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {rows.map((row) => (
          <TechnicalDetail key={row.label} {...row} />
        ))}
      </div>
    </details>
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

function TechnicalDetail({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900/50 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm leading-6 text-report-text">{value || th("technical.noData")}</p>
      {detail ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs font-medium text-report-blue hover:text-report-text">
            {th("technical.showList")}
          </summary>
          <p className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-words rounded-md border border-ink-700 bg-ink-900/50 p-2 text-xs leading-5 text-report-muted">
            {detail}
          </p>
        </details>
      ) : null}
    </div>
  );
}

function HeroNote({ title, text, status }: { title: string; text: string; status: Status }) {
  return (
    <div className={`nested-surface rounded-lg border p-3 status-border-${status}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{title}</p>
      <p className="mt-2 text-sm leading-6 text-report-text">{humanizeUiText(text)}</p>
    </div>
  );
}

function MiniStat({ label, value, tone = "neutral" }: { label: string; value: string; tone?: Status }) {
  return (
    <div className={`nested-surface rounded-lg border border-ink-700 p-3 status-border-${tone}`}>
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
    <div className={`nested-surface rounded-lg border border-ink-700 p-3 status-border-${tone}`}>
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
    <div className="nested-surface rounded-lg border border-dashed border-ink-700 p-5 text-center">
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
    <div className="rounded-lg border border-ink-700 bg-ink-900/75 px-3 py-2 text-sm shadow-panel">
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

function kpiLabel(metric: KpiMetric) {
  return homeKpiIds.has(metric.id) ? th(`kpi.${metric.id}`) : metric.label;
}

function answerLabel(label: string) {
  return {
    Pass: "Pass",
    Fail: "Fail",
    Hard: "Hard",
    Easy: "Easy",
  }[label] ?? label;
}

function humanizeUiText(value: string) {
  return value.replace(/\bPass rate\b/g, th("kpi.pass_rate")).replace(/\bFail rate\b/g, th("kpi.fail_rate"));
}

function deckScopeSummary(metadata: StudyReport["metadata"]) {
  const decks = metadata.selectedDecks.filter((deck) => deck.trim().length > 0);
  const allDeckLabels = [i18n.getFixedT("ru", "pages")("home.header.allDecks"), i18n.getFixedT("en", "pages")("home.header.allDecks")].map((value) => value.toLowerCase());
  if (decks.length === 0 || (decks.length === 1 && allDeckLabels.includes(decks[0].toLowerCase()))) {
    return { summary: th("header.allDecks") };
  }
  if (decks.length <= 3) {
    return { summary: `${i18n.t("units.deck", { ns: "common", count: decks.length })}: ${decks.join(", ")}` };
  }
  const visible = decks.slice(0, 3).join(", ");
  return {
    summary: th("decks.scope", { decks: i18n.t("units.deck", { ns: "common", count: decks.length }), visible, hidden: decks.length - 3 }),
    detail: th("decks.hiddenList"),
    fullList: decks.join(", "),
  };
}

function defaultActivityYear(days: Array<{ date: string }>) {
  const currentYear = new Date().getFullYear();
  const yearsWithData = days
    .map((day) => yearFromDate(day.date))
    .filter((year): year is number => Number.isFinite(year));
  if (yearsWithData.includes(currentYear)) {
    return currentYear;
  }
  return yearsWithData.length ? Math.max(...yearsWithData) : currentYear;
}

function activityYears(days: Array<{ date: string }>, selectedYear: number) {
  const years = new Set<number>([selectedYear, new Date().getFullYear()]);
  for (const day of days) {
    const year = yearFromDate(day.date);
    if (Number.isFinite(year)) {
      years.add(year);
    }
  }
  return [...years].sort((a, b) => b - a);
}

function yearFromDate(value: string) {
  const year = Number(value.slice(0, 4));
  return Number.isFinite(year) && year > 0 ? year : Number.NaN;
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
    label: th("fallback.noData"),
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
    message: th("comparison.shortText"),
    today: { ...emptyStats, label: th("fallback.today") },
    baselines: {
      yesterday: { ...emptyStats, label: th("fallback.yesterday") },
      avg7: { ...emptyStats, label: th("fallback.last7") },
      avg30: { ...emptyStats, label: th("fallback.last30") },
      sameWeekdayLastWeek: { ...emptyStats, label: th("fallback.weekday") },
      currentWeek: { ...emptyStats, label: th("fallback.currentWeek") },
      previousWeek: { ...emptyStats, label: th("fallback.previousWeek") },
      currentMonth: { ...emptyStats, label: th("fallback.currentMonth") },
      previousMonth: { ...emptyStats, label: th("fallback.previousMonth") },
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
    return period === "week" ? th("comparison.goodWeek") : th("comparison.goodToday");
  }
  if (status === "danger") {
    return th("comparison.danger");
  }
  if (status === "warning") {
    return th("comparison.warning");
  }
  return period === "week" ? th("comparison.neutralWeek") : th("comparison.neutralToday");
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
  return value === null ? th("comparison.noData") : formatPercent(value);
}

function formatCount(value: number) {
  return Number.isFinite(value) ? Math.round(value).toLocaleString("ru-RU") : "0";
}

function formatCountDelta(value: number | null) {
  return formatSignedValue(value, "");
}

function formatMinuteDelta(value: number | null) {
  const suffix = th("comparison.minutesSuffix");
  const formatted = formatSignedValue(value, suffix);
  return formatted === th("comparison.noValue") ? formatted : formatted.replace(`+0${suffix}`, `0${suffix}`);
}

function formatPercentDelta(value: number | null) {
  if (value === null) {
    return th("comparison.noHistory");
  }
  const rounded = Math.round(value);
  if (Math.abs(rounded) < 1) {
    return th("comparison.nearNorm");
  }
  return th("comparison.normDelta", { arrow: rounded > 0 ? "↑" : "↓", value: Math.abs(rounded) });
}

function formatPointDelta(value: number | null) {
  if (value === null) {
    return th("comparison.noValue");
  }
  if (Math.abs(value) < 0.5) {
    return th("comparison.zeroPoints");
  }
  return th("comparison.pointsDelta", { arrow: value > 0 ? "↑" : "↓", value: Math.abs(value).toFixed(1) });
}

function formatMinutes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return i18n.t("units.minutesShort", { ns: "common", value: 0 });
  }
  const minutes = Math.round(value);
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours && rest) {
    return `${i18n.t("units.hoursShort", { ns: "common", value: hours })} ${i18n.t("units.minutesShort", { ns: "common", value: rest })}`;
  }
  if (hours) {
    return i18n.t("units.hoursShort", { ns: "common", value: hours });
  }
  return i18n.t("units.minutesShort", { ns: "common", value: minutes });
}

function formatSeconds(value: number | null) {
  if (value === null || !Number.isFinite(value) || value <= 0) {
    return th("comparison.noData");
  }
  return i18n.t("units.secondsShort", { ns: "common", value: new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value) });
}

function formatSignedValue(value: number | null, suffix: string) {
  if (value === null) {
    return th("comparison.noValue");
  }
  const rounded = Math.round(value);
  if (rounded === 0) {
    return `→ 0${suffix}`;
  }
  return `${rounded > 0 ? "↑ +" : "↓ -"}${Math.abs(rounded).toLocaleString("ru-RU")}${suffix}`;
}

function heatmapColor(reviews: number, max: number) {
  if (reviews <= 0) {
    return "rgb(var(--color-bg-elevated))";
  }
  const intensity = Math.min(1, reviews / max);
  if (intensity > 0.75) {
    return "rgb(var(--color-accent) / 0.9)";
  }
  if (intensity > 0.5) {
    return "rgb(var(--color-accent) / 0.68)";
  }
  if (intensity > 0.25) {
    return "rgb(var(--color-accent) / 0.46)";
  }
  return "rgb(var(--color-accent) / 0.28)";
}

export default HomePage;
