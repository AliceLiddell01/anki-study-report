import {
  BarChart3,
  Check,
  ExternalLink,
  Info,
  RefreshCw,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";
import {
  StatisticsChartPanel,
  StatisticsEmptyState,
  seriesSummary,
} from "../components/statistics/StatisticsCharts";
import {
  deltaModel,
  futureDueTotal,
  selectDefaultDeckIds,
  statisticsColorClass,
  type StatisticsDeltaModel,
  type StatisticsSemanticColor,
} from "../components/statistics/statisticsPresentation";
import { runReportAction } from "../lib/actionsApi";
import { fetchStatistics, statisticsQueryKey } from "../lib/statisticsApi";
import type {
  StatisticsConfidence,
  StatisticsHubModel,
  StatisticsPeriod,
  StatisticsQuery,
  StatisticsResult,
  StatisticsSeriesPoint,
  StudyReport,
} from "../types/report";
import type { LoadState } from "./HomePage";

export type StatisticsSection = "overview" | "quality" | "load" | "progress" | "decks";

const sections: Array<{ id: StatisticsSection; path: string }> = [
  { id: "overview", path: "/stats" }, { id: "quality", path: "/stats/quality" }, { id: "load", path: "/stats/load" }, { id: "progress", path: "/stats/progress" }, { id: "decks", path: "/stats/decks" },
];
const periods: StatisticsPeriod[] = ["7d", "30d", "90d", "1y", "all"];

function StatisticsPage({ report, loadState, section }: { report: StudyReport | null; loadState: LoadState; section: StatisticsSection }) {
  const hub = report?.statisticsHub;
  if (loadState !== "ready" || !hub) return <StatisticsUnavailable loadState={loadState} />;
  return <StatisticsReady hub={hub} section={section} />;
}

function StatisticsReady({ hub, section }: { hub: StatisticsHubModel; section: StatisticsSection }) {
  const { t } = useTranslation(["statistics", "common"]);
  const initialQuery = useMemo<StatisticsQuery>(() => ({ ...hub.defaultQuery, scope: { ...hub.defaultQuery.scope } }), [hub]);
  const [query, setQuery] = useState<StatisticsQuery>(initialQuery);
  const [result, setResult] = useState<StatisticsResult>(hub.initialResult);
  const [status, setStatus] = useState<"ready" | "loading" | "error">("ready");
  const [error, setError] = useState("");
  const [retryNonce, setRetryNonce] = useState(0);
  const cacheRef = useRef(new Map([[statisticsQueryKey(initialQuery), hub.initialResult]]));
  const requestSequence = useRef(0);

  useEffect(() => {
    const normalizedQuery = query.period === "all" && query.comparison ? { ...query, comparison: false } : query;
    const key = statisticsQueryKey(normalizedQuery);
    const cached = cacheRef.current.get(key);
    if (cached && retryNonce === 0) {
      setResult(cached);
      setStatus("ready");
      setError("");
      return;
    }
    const controller = new AbortController();
    const sequence = ++requestSequence.current;
    setStatus("loading");
    setError("");
    fetchStatistics(normalizedQuery, controller.signal)
      .then((next) => {
        if (sequence !== requestSequence.current) return;
        cacheRef.current.set(key, next);
        setResult(next);
        setStatus("ready");
        setRetryNonce(0);
      })
      .catch((caught: Error) => {
        if (caught.name === "AbortError" || sequence !== requestSequence.current) return;
        setStatus("error");
        setError(caught.message || t("shell.refreshFailed"));
      });
    return () => controller.abort();
  }, [query, retryNonce, t]);

  const currentSection = sections.find((item) => item.id === section)!;
  const updateQuery = (patch: Partial<StatisticsQuery>) => setQuery((current) => ({ ...current, ...patch }));
  const openNativeStats = async () => {
    const response = await runReportAction("open-native-stats", {});
    if (!response.ok) setError(response.error || t("shell.openNativeFailed"));
  };

  return (
    <div className="statistics-shell" data-testid="statistics-page" data-statistics-section={section}>
      <StatisticsSidebar section={section} />
      <div className="statistics-content">
        <header className="statistics-header statistics-page-surface" data-testid="statistics-header">
          <div>
            <span className="statistics-section-marker">{t("shell.marker")}</span>
            <h1>{section === "overview" ? t("shell.title") : t(`shell.${section}`)}</h1>
            <p>{t(`shell.${section}Description`)}</p>
          </div>
          <button type="button" className="secondary-button" onClick={openNativeStats}>
            <ExternalLink size={16} aria-hidden="true" /> {t("shell.openNative")}
          </button>
        </header>

        <StatisticsQueryBar hub={hub} query={query} result={result} updateQuery={updateQuery} />

        <div className="statistics-status-slot" aria-live="polite">
          {status === "loading" ? <div className="statistics-loading" role="status">{t("shell.refreshing")}</div> : null}
          {status === "error" || error ? (
            <div className="statistics-error" role="alert">
              <span>{error || t("shell.refreshFailed")}</span>
              {status === "error" ? <button type="button" onClick={() => setRetryNonce((value) => value + 1)}><RefreshCw size={15} /> {t("shell.retry")}</button> : null}
            </div>
          ) : null}
        </div>

        <div aria-busy={status === "loading"} className={status === "loading" ? "statistics-result is-loading" : "statistics-result"}>
          {section === "overview" ? <Overview result={result} /> : null}
          {section === "quality" ? <Quality result={result} /> : null}
          {section === "load" ? <Load result={result} /> : null}
          {section === "progress" ? <Progress result={result} /> : null}
          {section === "decks" ? <DeckComparison result={result} /> : null}
        </div>
      </div>
    </div>
  );
}

function StatisticsSidebar({ section }: { section: StatisticsSection }) {
  const { t } = useTranslation("statistics");
  return (
    <aside className="statistics-sidebar" data-testid="statistics-sidebar">
      <div className="statistics-sidebar-heading">
        <span className="statistics-sidebar-icon"><BarChart3 size={18} aria-hidden="true" /></span>
        <div><strong>{t("shell.title")}</strong><span>{t("shell.subtitle")}</span></div>
      </div>
      <nav aria-label={t("shell.navLabel")}>
        {sections.map((item) => <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>{t(`shell.${item.id}`)}</a>)}
        <a href="#/stats/fsrs">FSRS</a>
      </nav>
    </aside>
  );
}

function StatisticsQueryBar({ hub, query, result, updateQuery }: { hub: StatisticsHubModel; query: StatisticsQuery; result: StatisticsResult; updateQuery: (patch: Partial<StatisticsQuery>) => void }) {
  const { t } = useTranslation("statistics");
  const scopeKind = query.scope.kind;
  const selectedDeckId = scopeKind === "single_deck" ? query.scope.deckId : hub.deckOptions[0]?.deckId;
  return (
    <section className="statistics-query-surface" aria-label={t("query.label")} data-testid="statistics-query-bar">
      <div className="statistics-controls">
        <label>{t("query.scope")}
          <select value={scopeKind} onChange={(event) => {
            const kind = event.target.value;
            if (kind === "single_deck" && hub.deckOptions[0]) updateQuery({ scope: { kind, deckId: hub.deckOptions[0].deckId, mode: "subtree" } });
            else updateQuery({ scope: { kind: kind as "dashboard" | "all_collection" } });
          }}>
            <option value="dashboard">{t("query.dashboard")}</option><option value="all_collection">{t("query.collection")}</option><option value="single_deck">{t("query.singleDeck")}</option>
          </select>
        </label>
        {scopeKind === "single_deck" ? <>
          <label>{t("query.deck")}
            <select value={selectedDeckId} onChange={(event) => updateQuery({ scope: { kind: "single_deck", deckId: Number(event.target.value), mode: query.scope.kind === "single_deck" ? query.scope.mode : "subtree" } })}>
              {hub.deckOptions.map((deck) => <option value={deck.deckId} key={deck.deckId}>{deck.fullName}</option>)}
            </select>
          </label>
          <fieldset className="statistics-segmented"><legend>{t("query.deckMode")}</legend>
            {(["subtree", "direct"] as const).map((mode) => <label key={mode}><input type="radio" name="deck-mode" checked={query.scope.kind === "single_deck" && query.scope.mode === mode} onChange={() => updateQuery({ scope: { kind: "single_deck", deckId: selectedDeckId!, mode } })} />{t(`query.${mode}`)}</label>)}
          </fieldset>
        </> : null}
        <label>{t("query.period")}
          <select value={query.period} onChange={(event) => updateQuery({ period: event.target.value as StatisticsPeriod, comparison: event.target.value === "all" ? false : query.comparison })}>
            {periods.map((value) => <option value={value} key={value}>{t(`periods.${value}`)}</option>)}
          </select>
        </label>
        <label>{t("query.granularity")}
          <select value={query.granularity} onChange={(event) => updateQuery({ granularity: event.target.value as StatisticsQuery["granularity"] })}>
            <option value="auto">{t("query.auto")}</option><option value="day">{t("query.day")}</option><option value="week">{t("query.week")}</option><option value="month">{t("query.month")}</option>
          </select>
        </label>
        <label className="statistics-checkbox"><input type="checkbox" checked={query.comparison} disabled={query.period === "all"} onChange={(event) => updateQuery({ comparison: event.target.checked })} /><span>{t("query.compare")}<small>{query.period === "all" ? t("query.compareDisabled") : t("query.compareHint")}</small></span></label>
      </div>
      <CoverageNotice result={result} />
    </section>
  );
}

function Overview({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation(["statistics", "common"]);
  const kpi = result.overview.kpis;
  const comparison = result.overview.comparison;
  return <div className="statistics-section-stack" data-testid="statistics-overview">
    <InsightCard insights={result.overview.insights} confidence={result.overview.confidence} />
    <section className="statistics-kpis" aria-label={t("labels.keyMetrics")} data-testid="statistics-kpi-grid">
      <KpiCard label={t("labels.reviews")} value={formatNumber(kpi.reviews)} delta={deltaModel(comparison, "reviews")} color="reviews" />
      <KpiCard label={t("labels.studyTime")} value={formatDuration(kpi.studySeconds)} delta={deltaModel(comparison, "studySeconds")} color="study-time" caption={t("overview.studyEstimate")} />
      <KpiCard label={t("labels.successRate")} value={formatPercent(kpi.successRate)} delta={deltaModel(comparison, "successRate", "percentage-points")} color="success" />
      <KpiCard label={t("labels.newCards")} value={formatNumber(kpi.introducedCards)} delta={deltaModel(comparison, "introducedCards")} color="introduced" caption={t("overview.introducedCaption")} />
      <KpiCard label={t("labels.activeDays")} value={formatNumber(kpi.activeDays)} delta={deltaModel(comparison, "activeDays")} color="reviews" />
      <KpiCard label={t("labels.averageAnswer")} value={kpi.averageAnswerSeconds == null ? t("state.noData", { ns: "common" }) : t("units.secondsShort", { ns: "common", value: formatNumber(kpi.averageAnswerSeconds) })} delta={deltaModel(comparison, "averageAnswerSeconds", "seconds")} color="study-time" />
    </section>
    <div className="statistics-analytical-grid primary-secondary">
      <StatisticsChartPanel title={t("overview.trend")} description={t("overview.trendDescription")} summary={seriesSummary(result.overview.series, "reviews", t("labels.reviews"))} points={result.overview.series} metrics={[{ key: "reviews", label: t("labels.reviews"), color: "reviews" }]} kind="line" testId="stats-overview-reviews" />
      <StatisticsChartPanel title={t("labels.studyTime")} description={t("overview.timeDescription")} summary={seriesSummary(result.overview.series, "studySeconds", t("labels.studyTime"))} points={result.overview.series} metrics={[{ key: "studySeconds", label: t("labels.timeMinutes"), color: "study-time", format: "duration" }]} kind="line" compact testId="stats-overview-time" />
    </div>
    <div className="statistics-analytical-grid">
      <StatisticsChartPanel title={t("labels.successRate")} description={t("overview.successDescription")} summary={seriesSummary(result.overview.series, "successRate", t("labels.successRate"))} points={result.overview.series} metrics={[{ key: "successRate", label: t("labels.successRate"), color: "success", format: "percent" }]} kind="line" testId="stats-overview-success" />
      <StatisticsChartPanel title={t("labels.averageAnswer")} description={t("overview.answerDescription")} summary={seriesSummary(result.overview.series, "averageAnswerSeconds", t("labels.averageAnswer"))} points={result.overview.series} metrics={[{ key: "averageAnswerSeconds", label: t("labels.averageAnswer"), color: "study-time", format: "seconds" }]} kind="line" compact />
      <StatisticsChartPanel title={t("labels.newCards")} description={t("overview.introducedDescription")} summary={seriesSummary(result.overview.series, "introducedCards", t("labels.newCards"))} points={result.overview.series} metrics={[{ key: "introducedCards", label: t("labels.newCards"), color: "introduced" }]} kind="bar" compact testId="stats-overview-introduced" />
    </div>
  </div>;
}

function Quality({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation(["statistics", "common"]);
  const quality = result.quality;
  const ratingTotal = Object.values(quality.ratings).reduce((sum, value) => sum + value, 0);
  return <div className="statistics-section-stack" data-testid="statistics-quality">
    <InsightCard title={t("quality.insightTitle")} text={quality.confidence === "insufficient" ? t("quality.insufficient") : t("quality.insight", { rate: formatPercent(quality.successRate), count: formatNumber(quality.pass + quality.fail) })} confidence={quality.confidence} />
    <section className="statistics-kpis compact four" aria-label={t("quality.metrics")}>
      <KpiCard label={t("labels.successRate")} value={formatPercent(quality.successRate)} color="success" />
      <KpiCard label={t("quality.trueRetention")} value={formatPercent(quality.trueRetention.overall)} color="mature" caption={t("quality.trueRetentionCaption")} />
      <KpiCard label={t("labels.averageAnswer")} value={result.overview.kpis.averageAnswerSeconds == null ? t("state.noData", { ns: "common" }) : t("units.secondsShort", { ns: "common", value: formatNumber(result.overview.kpis.averageAnswerSeconds) })} color="study-time" />
      <KpiCard label={t("quality.sample")} value={formatNumber(quality.pass + quality.fail)} color="reviews" caption={confidenceLabel(quality.confidence)} />
    </section>
    <div className="statistics-analytical-grid primary-secondary">
      <StatisticsChartPanel title={t("quality.successTime")} description={t("quality.successTimeDescription")} summary={seriesSummary(quality.series, "successRate", t("labels.successRate"))} points={quality.series} metrics={[{ key: "successRate", label: t("labels.successRate"), color: "success", format: "percent" }]} kind="line" testId="stats-quality-success" />
      <StatisticsChartPanel title={t("quality.answerVolume")} description={t("quality.answerVolumeDescription")} summary={t("quality.volumeSummary", { pass: formatNumber(quality.pass), fail: formatNumber(quality.fail) })} points={quality.series} metrics={[{ key: "pass", label: t("quality.passed"), color: "good", stackId: "answers" }, { key: "fail", label: t("labels.again"), color: "again", stackId: "answers" }]} kind="stacked" compact testId="stats-quality-volume" />
    </div>
    <section className="statistics-analytical-grid">
      <StatisticsPanel title={t("quality.answerButtons")} description={t("quality.answerButtonsDescription", { count: formatNumber(ratingTotal) })} testId="stats-answer-buttons">
        <AnswerDistribution ratings={quality.ratings} />
      </StatisticsPanel>
      <StatisticsPanel title={t("quality.trueRetention")} description={t("quality.retentionDescription")} testId="stats-retention-panel">
        <RetentionBreakdown result={quality.trueRetention} confidence={quality.confidence} />
      </StatisticsPanel>
    </section>
  </div>;
}

function Load({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation(["statistics", "common"]);
  const load = result.load;
  const futurePoints = load.futureDue.map((row) => ({ ...row, key: String(row.dayOffset), label: row.dayOffset === 0 ? t("load.today") : t("load.inDays", { count: row.dayOffset }) }));
  return <div className="statistics-section-stack" data-testid="statistics-load">
    <InsightCard title={t("load.insightTitle")} text={load.overdue ? t("load.overdue", { count: formatNumber(load.overdue) }) : t("load.noOverdue")} />
    <section className="statistics-kpis compact four" aria-label={t("load.metrics")}>
      <KpiCard label={t("load.overdueNow")} value={formatNumber(load.overdue)} color="again" />
      <KpiCard label={t("load.next7")} value={formatNumber(futureDueTotal(load, 7))} color="review" />
      <KpiCard label={t("load.next30")} value={formatNumber(futureDueTotal(load, 30))} color="learning" />
      <KpiCard label={t("load.activeAverage")} value={load.averageActiveDayReviews == null ? t("state.noData", { ns: "common" }) : formatNumber(load.averageActiveDayReviews)} color="reviews" caption={t("load.activeAverageCaption")} />
    </section>
    <div className="statistics-definition-line"><Info size={15} aria-hidden="true" /><span><strong>{t("load.dailyLoad", { value: formatNumber(load.dailyLoad) })}</strong> — {t("load.dailyLoadDescription")}</span><details><summary>{t("load.calculation")}</summary><p>{t("chart.loadCalculationDescription")}</p></details></div>
    <section className="statistics-panel-group" aria-labelledby="past-load-title">
      <header><h2 id="past-load-title">{t("load.past")}</h2><p>{t("load.pastDescription")}</p></header>
      <div className="statistics-analytical-grid thirds">
        <StatisticsChartPanel title={t("labels.reviews")} description={t("load.reviewsDescription")} summary={seriesSummary(load.past, "reviews", t("labels.reviews"))} points={load.past} metrics={[{ key: "reviews", label: t("labels.reviews"), color: "reviews" }]} kind="line" compact testId="stats-load-reviews" />
        <StatisticsChartPanel title={t("load.time")} description={t("load.timeDescription")} summary={seriesSummary(load.past, "studySeconds", t("load.time"))} points={load.past} metrics={[{ key: "studySeconds", label: t("labels.timeMinutes"), color: "study-time", format: "duration" }]} kind="line" compact testId="stats-load-time" />
        <StatisticsChartPanel title={t("labels.newCards")} description={t("load.newDescription")} summary={seriesSummary(load.past, "introducedCards", t("labels.newCards"))} points={load.past} metrics={[{ key: "introducedCards", label: t("labels.newCards"), color: "introduced" }]} kind="bar" compact testId="stats-load-new" />
      </div>
    </section>
    <StatisticsChartPanel title={t("load.future")} description={t("load.futureDescription")} summary={futurePoints.length ? t("load.futureSummary", { count: futurePoints.length }) : t("load.futureEmpty")} points={futurePoints} metrics={[{ key: "learning", label: t("labels.learning"), color: "learning", stackId: "due" }, { key: "review", label: t("labels.review"), color: "review", stackId: "due" }, { key: "relearning", label: t("labels.relearning"), color: "relearning", stackId: "due" }]} kind="stacked" testId="stats-load-future-due" aside={<span className="statistics-panel-badge">{t("load.days90")}</span>} />
    <p className="statistics-assumption"><Info size={16} aria-hidden="true" /> {t("load.assumption")}</p>
  </div>;
}

function Progress({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation("statistics");
  const progress = result.progress;
  return <div className="statistics-section-stack" data-testid="statistics-progress">
    <InsightCard title={t("progress.insightTitle")} text={t("progress.insight", { cards: formatNumber(progress.totalCards), notes: formatNumber(progress.totalNotes), introduced: formatNumber(progress.introducedCards) })} />
    <section className="statistics-kpis compact" aria-label={t("progress.metrics")}>
      <KpiCard label={t("progress.totalCards")} value={formatNumber(progress.totalCards)} color="reviews" />
      <KpiCard label={t("progress.totalNotes")} value={formatNumber(progress.totalNotes)} color="study-time" />
      <KpiCard label={t("progress.introducedPeriod")} value={formatNumber(progress.introducedCards)} color="introduced" />
    </section>
    <StatisticsPanel title={t("progress.currentState")} description={t("progress.currentStateDescription")} testId="stats-progress-current-state">
      <CollectionStateBar states={progress.currentStates} />
      <p className="statistics-limitation"><Info size={15} aria-hidden="true" /> {t("progress.limitation")}</p>
    </StatisticsPanel>
    <StatisticsChartPanel title={t("progress.introducedCards")} description={t("progress.introducedDescription")} summary={seriesSummary(progress.introducedSeries, "introducedCards", t("progress.introducedCards"))} points={progress.introducedSeries} metrics={[{ key: "introducedCards", label: t("labels.introduced"), color: "introduced" }]} kind="bar" testId="stats-progress-introduced" />
  </div>;
}

function DeckComparison({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation(["statistics", "common"]);
  const [search, setSearch] = useState("");
  const defaultIds = useMemo(() => selectDefaultDeckIds(result.deckComparison.rows), [result.deckComparison.rows]);
  const rowsKey = result.deckComparison.rows.map((row) => `${row.deckId}:${row.reviews}:${row.confidence}`).join("|");
  const [selected, setSelected] = useState<number[]>(defaultIds);
  useEffect(() => setSelected(defaultIds), [rowsKey]);
  const visible = result.deckComparison.rows.filter((row) => row.fullName.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  const selectedRows = result.deckComparison.rows.filter((row) => selected.includes(row.deckId));
  const selectionLimit = Math.min(6, result.deckComparison.limit);
  const toggle = (deckId: number) => setSelected((current) => current.includes(deckId) ? current.filter((id) => id !== deckId) : current.length < selectionLimit ? [...current, deckId] : current);

  return <div className="statistics-section-stack" data-testid="statistics-decks">
    <InsightCard title={t("decks.insightTitle")} text={selectedRows.length ? t("decks.selected", { count: selectedRows.length }) : t("decks.selectHint")} />
    <section className="deck-comparison-tools statistics-supporting-panel"><label>{t("decks.search")}<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("decks.placeholder")} /></label><span>{t("decks.limit", { count: selectionLimit })}</span></section>
    <StatisticsPanel title={t("decks.chartTitle")} description={t("decks.chartDescription")} testId="stats-deck-comparison-chart">
      {selectedRows.length ? <DeckRankedBars rows={selectedRows} /> : <StatisticsEmptyState text={t("decks.selectOne")} />}
    </StatisticsPanel>
    <StatisticsPanel title={t("decks.dataTitle")} description={t("decks.dataDescription")}>
      {visible.length ? <div className="statistics-table-wrap"><table className="statistics-table statistics-deck-table"><thead><tr><th>{t("decks.select")}</th><th>{t("decks.deck")}</th><th>{t("labels.reviews")}</th><th>{t("decks.change")}</th><th>{t("labels.successRate")}</th><th>{t("labels.averageAnswer")}</th><th>{t("decks.time")}</th><th>{t("labels.newCards")}</th><th>{t("labels.confidence")}</th></tr></thead><tbody>{visible.map((row) => {
        const isSelected = selected.includes(row.deckId);
        return <tr key={row.deckId} className={isSelected ? "is-selected" : undefined} data-selected={isSelected ? "true" : "false"}><td><label className="statistics-row-selector"><input aria-label={t("decks.selectAria", { name: row.fullName })} type="checkbox" checked={isSelected} disabled={!isSelected && selected.length >= selectionLimit} onChange={() => toggle(row.deckId)} />{isSelected ? <Check size={14} aria-hidden="true" /> : null}</label></td><th title={row.fullName}>{row.fullName}</th><td>{formatNumber(row.reviews)}</td><td>{formatDelta(row.periodDelta?.reviews.delta)}</td><td>{formatPercent(row.successRate)}</td><td>{row.averageAnswerSeconds == null ? t("state.noData", { ns: "common" }) : t("units.secondsShort", { ns: "common", value: formatNumber(row.averageAnswerSeconds) })}</td><td>{formatDuration(row.studySeconds)}</td><td>{formatNumber(row.introducedCards)}</td><td><ConfidenceBadge value={row.confidence} /></td></tr>;
      })}</tbody></table></div> : <StatisticsEmptyState text={t("decks.noMatches")} />}
    </StatisticsPanel>
  </div>;
}

function StatisticsPanel({ title, description, children, testId }: { title: string; description: string; children: ReactNode; testId?: string }) {
  return <section className="statistics-panel" data-testid={testId}><header className="statistics-panel-header"><div><h2>{title}</h2><p>{description}</p></div></header>{children}</section>;
}

function KpiCard({ label, value, caption, delta, color }: { label: string; value: string; caption?: string; delta?: StatisticsDeltaModel; color: StatisticsSemanticColor }) {
  return <article className="statistics-kpi-card" data-testid="statistics-kpi-card"><span className={`statistics-kpi-accent ${statisticsColorClass[color]}`} aria-hidden="true" /><span className="statistics-kpi-label">{label}</span><strong>{value}</strong>{delta ? <span className={`statistics-delta is-${delta.direction}`} data-comparison-style={delta.comparisonStyle}>{delta.text}</span> : null}{caption ? <small>{caption}</small> : null}</article>;
}

function InsightCard({ insights, confidence, title, text }: { insights?: StatisticsResult["overview"]["insights"]; confidence?: StatisticsConfidence; title?: string; text?: string }) {
  const { t } = useTranslation("statistics");
  const observation = text || insightText(insights || [], confidence);
  return <section className="statistics-insight-card" aria-label={t("insight.aria")} data-testid="statistics-insight"><span className="statistics-insight-icon"><BarChart3 size={20} aria-hidden="true" /></span><div><span>{title || t("insight.title")}</span><p>{observation}</p></div>{confidence ? <ConfidenceBadge value={confidence} /> : null}</section>;
}

function ConfidenceBadge({ value }: { value: StatisticsConfidence }) {
  return <span className={`statistics-confidence-badge is-${value}`}>{confidenceLabel(value)}</span>;
}

function AnswerDistribution({ ratings }: { ratings: StatisticsResult["quality"]["ratings"] }) {
  const { t } = useTranslation("statistics");
  const rows: Array<{ key: keyof typeof ratings; label: string; color: StatisticsSemanticColor }> = [
    { key: "again", label: t("labels.again"), color: "again" }, { key: "hard", label: t("labels.hard"), color: "hard" }, { key: "good", label: t("labels.good"), color: "good" }, { key: "easy", label: t("labels.easy"), color: "easy" },
  ];
  const total = rows.reduce((sum, row) => sum + ratings[row.key], 0);
  return <div className="statistics-answer-distribution" role="img" aria-label={t("quality.distributionLabel", { count: total })}>
    <div className="statistics-stacked-strip">{rows.map((row) => <span key={row.key} className={statisticsColorClass[row.color]} style={{ width: `${total ? ratings[row.key] / total * 100 : 0}%` }} title={`${row.label}: ${ratings[row.key]}`} />)}</div>
    <div className="statistics-direct-legend">{rows.map((row) => <div key={row.key}><i className={statisticsColorClass[row.color]} /><span>{row.label}</span><strong>{formatNumber(ratings[row.key])}</strong><small>{formatPercentValue(total ? ratings[row.key] / total : null)}</small></div>)}</div>
  </div>;
}

function RetentionBreakdown({ result, confidence }: { result: StatisticsResult["quality"]["trueRetention"]; confidence: StatisticsConfidence }) {
  const { t } = useTranslation("statistics");
  const rows = [{ label: t("quality.all"), value: result.overall, sample: result.sampleSize, color: "success" as const }, { label: t("labels.young"), value: result.young, sample: result.youngPass + result.youngFail, color: "young" as const }, { label: t("labels.mature"), value: result.mature, sample: result.maturePass + result.matureFail, color: "mature" as const }];
  return <div className="statistics-retention"><div className="statistics-retention-summary"><strong>{formatPercent(result.overall)}</strong><ConfidenceBadge value={confidence} /></div>{rows.map((row) => <div className="statistics-retention-row" key={row.label}><span>{row.label}</span><div><i className={statisticsColorClass[row.color]} style={{ width: `${(row.value || 0) * 100}%` }} /></div><strong>{formatPercent(row.value)}</strong><small>{t("quality.sampleAnswers", { count: formatNumber(row.sample) })}</small></div>)}<details className="statistics-definition"><summary>{t("quality.calculation")}</summary><p>{t("quality.retentionDefinition")}</p></details></div>;
}

function CollectionStateBar({ states }: { states: StatisticsResult["progress"]["currentStates"] }) {
  const { t } = useTranslation("statistics");
  const rows: Array<{ key: keyof typeof states; label: string; color: StatisticsSemanticColor }> = [
    { key: "unseen", label: t("labels.unseen"), color: "unseen" }, { key: "learning", label: t("labels.studying"), color: "learning" }, { key: "young", label: t("labels.young"), color: "young" }, { key: "mature", label: t("labels.mature"), color: "mature" }, { key: "suspended", label: t("labels.suspended"), color: "suspended" }, { key: "buried", label: t("labels.buried"), color: "buried" },
  ];
  const total = rows.reduce((sum, row) => sum + states[row.key], 0);
  return <div className="statistics-state-distribution" role="img" aria-label={t("progress.stateLabel", { count: total })}><div className="statistics-stacked-strip is-state">{rows.map((row) => <span key={row.key} className={statisticsColorClass[row.color]} style={{ width: `${total ? states[row.key] / total * 100 : 0}%` }} />)}</div><div className="statistics-direct-legend is-grid">{rows.map((row) => <div key={row.key}><i className={statisticsColorClass[row.color]} /><span>{row.label}</span><strong>{formatNumber(states[row.key])}</strong><small>{formatPercentValue(total ? states[row.key] / total : null)}</small></div>)}</div></div>;
}

function DeckRankedBars({ rows }: { rows: StatisticsResult["deckComparison"]["rows"] }) {
  const { t } = useTranslation("statistics");
  return <div className="statistics-ranked-bars" role="img" aria-label={t("decks.rankedAria")}>{[...rows].sort((a, b) => (b.successRate || 0) - (a.successRate || 0)).map((row, index) => <div key={row.deckId} className="statistics-ranked-row"><span className="statistics-rank">{index + 1}</span><div className="statistics-ranked-label"><strong title={row.fullName}>{row.fullName}</strong><small>{t("decks.reviewConfidence", { count: formatNumber(row.reviews), confidence: confidenceLabel(row.confidence).toLocaleLowerCase(localeForLanguage(i18n.language)) })}</small></div><div className="statistics-ranked-track"><i style={{ width: `${(row.successRate || 0) * 100}%` }} /></div><strong>{formatPercent(row.successRate)}</strong></div>)}</div>;
}

function CoverageNotice({ result }: { result: StatisticsResult }) {
  const { t } = useTranslation("statistics");
  const coverage = result.coverage;
  if (coverage.coverage === "full") return <p className="statistics-coverage"><span>{t("coverage.label")}</span>{coverage.requestedFrom || coverage.dataFrom || t("coverage.historyStart")} — {coverage.requestedTo}<strong>{t("coverage.answers", { count: formatNumber(coverage.sampleSize) })}</strong></p>;
  return <p className={`statistics-coverage ${coverage.coverage}`} role="status"><span>{t("coverage.label")}</span>{coverage.coverage === "partial" ? t("coverage.partial", { date: coverage.dataFrom }) : t("coverage.unavailable")}</p>;
}

function StatisticsUnavailable({ loadState }: { loadState: LoadState }) {
  const { t } = useTranslation("statistics");
  const text = loadState === "loading" ? t("unavailable.loading") : loadState === "forbidden" ? t("unavailable.forbidden") : t("unavailable.default");
  return <section className="statistics-empty-page panel-surface"><BarChart3 size={28} /><h1>{t("shell.title")}</h1><p>{text}</p></section>;
}

function insightText(insights: StatisticsResult["overview"]["insights"], confidence?: StatisticsConfidence): string {
  if (!insights.length) return i18n.t(confidence === "insufficient" ? "insight.insufficient" : "insight.stable", { ns: "statistics" });
  const labels: Record<string, { label: string; increase: string; decrease: string; same: string }> = {
    reviews_changed: { label: i18n.t("insight.reviews", { ns: "statistics" }), increase: i18n.t("insight.increased", { ns: "statistics" }), decrease: i18n.t("insight.decreased", { ns: "statistics" }), same: i18n.t("insight.unchanged", { ns: "statistics" }) },
    success_rate_changed: { label: i18n.t("insight.success", { ns: "statistics" }), increase: i18n.t("insight.increasedFeminine", { ns: "statistics" }), decrease: i18n.t("insight.decreasedFeminine", { ns: "statistics" }), same: i18n.t("insight.unchangedFeminine", { ns: "statistics" }) },
    answer_time_changed: { label: i18n.t("insight.answerTime", { ns: "statistics" }), increase: i18n.t("insight.answerIncreased", { ns: "statistics" }), decrease: i18n.t("insight.answerDecreased", { ns: "statistics" }), same: i18n.t("insight.unchangedMasculine", { ns: "statistics" }) },
    active_days_changed: { label: i18n.t("insight.activeDays", { ns: "statistics" }), increase: i18n.t("insight.increased", { ns: "statistics" }), decrease: i18n.t("insight.decreased", { ns: "statistics" }), same: i18n.t("insight.unchanged", { ns: "statistics" }) },
    new_cards_changed: { label: i18n.t("insight.newCards", { ns: "statistics" }), increase: i18n.t("insight.increased", { ns: "statistics" }), decrease: i18n.t("insight.decreased", { ns: "statistics" }), same: i18n.t("insight.unchanged", { ns: "statistics" }) },
  };
  return insights.slice(0, 2).map((item) => {
    const wording = labels[item.type] || { label: i18n.t("insight.metric", { ns: "statistics" }), increase: i18n.t("insight.increasedMasculine", { ns: "statistics" }), decrease: i18n.t("insight.decreasedMasculine", { ns: "statistics" }), same: i18n.t("insight.unchangedMasculine", { ns: "statistics" }) };
    return i18n.t("insight.sentence", { ns: "statistics", label: wording.label, direction: item.direction === "increase" ? wording.increase : item.direction === "decrease" ? wording.decrease : wording.same, value: formatInsightValue(item.value, item.unit) });
  }).join("; ") + ".";
}

function formatInsightValue(value: number, unit: string): string {
  const number = new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(Math.abs(value));
  return `${number}${unit === "percentage_points" ? i18n.t("comparison.percentagePoints", { ns: "statistics" }) : unit === "seconds" ? i18n.t("comparison.seconds", { ns: "statistics" }) : "%"}`;
}

function formatNumber(value: number): string { return new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null): string { return value == null ? i18n.t("labels.noData", { ns: "statistics" }) : formatPercentValue(value); }
function formatPercentValue(value: number | null): string { return value == null ? i18n.t("labels.noData", { ns: "statistics" }) : `${new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value * 100)}%`; }
function formatDuration(seconds: number | null): string { if (seconds == null) return i18n.t("labels.noData", { ns: "statistics" }); const minutes = Math.round(seconds / 60); return minutes >= 60 ? `${i18n.t("common:units.hoursShort", { value: Math.floor(minutes / 60) })} ${i18n.t("common:units.minutesShort", { value: minutes % 60 })}` : i18n.t("common:units.minutesShort", { value: minutes }); }
function confidenceLabel(value: StatisticsConfidence): string { return i18n.t(`confidence.${value}`, { ns: "statistics" }); }
function formatDelta(value: number | null | undefined): string { return value == null ? i18n.t("labels.noData", { ns: "statistics" }) : `${value > 0 ? "+" : ""}${new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value)}%`; }

export default StatisticsPage;
