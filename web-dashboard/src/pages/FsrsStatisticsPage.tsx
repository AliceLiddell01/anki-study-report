import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  CircleGauge,
  Database,
  ExternalLink,
  Info,
  Play,
  RefreshCw,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { CalibrationChart, WorkloadComparisonChart } from "../components/fsrs/FsrsCharts";
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";
import { runReportAction } from "../lib/actionsApi";
import { fetchFsrs, fsrsQueryKey } from "../lib/fsrsApi";
import { calibrationVerdict, simulatorFieldErrors, targetGap } from "../lib/fsrsPresentation";
import type {
  FsrsCapability,
  FsrsConfigurationGroup,
  FsrsQuery,
  FsrsResponse,
  FsrsScope,
  StudyReport,
} from "../types/report";
import type { LoadState } from "./HomePage";

export type FsrsSection = "overview" | "memory" | "calibration" | "steps" | "simulator";

const fsrsSections: Array<{ id: FsrsSection; path: string }> = [
  { id: "overview", path: "/stats/fsrs" },
  { id: "memory", path: "/stats/fsrs/memory" },
  { id: "calibration", path: "/stats/fsrs/calibration" },
  { id: "steps", path: "/stats/fsrs/steps" },
  { id: "simulator", path: "/stats/fsrs/simulator" },
];

const statisticsSections = [
  ["overview", "/stats"], ["quality", "/stats/quality"], ["load", "/stats/load"],
  ["progress", "/stats/progress"], ["decks", "/stats/decks"], ["fsrs", "/stats/fsrs"],
];

const tf = (key: string, options?: Record<string, unknown>) => i18n.t(key, { ns: "fsrs", ...options });

type Distribution = { label: string; count: number; percentage: number | null };
type MemoryResult = {
  availability: string;
  studiedCards: number;
  estimatedRemembered: number;
  averageRetrievability: number | null;
  medianRetrievability: number | null;
  medianStabilityDays: number | null;
  medianDifficulty: number | null;
  cardsBelowOwnTarget: number;
  overdueCards: number;
  retrievabilityDistribution: Distribution[];
  stabilityDistribution: Distribution[];
  difficultyDistribution: Distribution[];
  limitations: string[];
};
type OverviewResult = {
  configurations: FsrsConfigurationGroup[];
  mixedConfiguration: boolean;
  targetRetentionRange: { min: number; max: number } | null;
  estimatedRemembered: number;
  studiedCards: number;
  averageRetrievability: number | null;
  medianStabilityDays: number | null;
  actualRetention: number | null;
  dataSufficiency: string;
  insight: string;
};
type CalibrationResult = {
  configuration: FsrsConfigurationGroup;
  sampleSize: number;
  sufficiency: string;
  bins: Array<{ label: string; predicted: number | null; actual: number | null; sampleSize: number; sufficiency: string }>;
  rmseBins: number | null;
  hardIsRecall: boolean;
};
type StepsResult = {
  availability: string;
  configuration?: FsrsConfigurationGroup;
  scopeExpandedToPreset?: boolean;
  learningStepsSeconds?: number[];
  relearningStepsSeconds?: number[];
  shortTermMode?: string;
  scenarios: Array<{ id: string; sampleSize: number; retention: number | null; observedSuccessfulRangeSeconds: number[] | null; sufficiency: string }>;
  recommendation: { rangeSeconds: number[]; confidence: string; readOnly: true } | null;
};
type SimulationResult = {
  configuration: FsrsConfigurationGroup;
  current: SimulationScenario;
  hypothetical: SimulationScenario;
  delta: { reviewsPerDay: number; minutesPerDay: number };
  native: true;
  readOnly: true;
};
type SimulationScenario = {
  desiredRetention: number;
  averageReviewsPerDay: number;
  averageMinutesPerDay: number;
  peakReviews: number;
  backlog: number;
  daily: Array<{ day: number; reviews: number; minutes: number }>;
};
type SimulatorInputs = {
  desiredRetention: number;
  horizonDays: 90 | 180 | 365;
  additionalNewCards: number;
  newCardsPerDay: number;
  maximumReviewsPerDay: number;
};
type RequestStatus = "idle" | "loading" | "ready" | "error";

function FsrsStatisticsPage({ report, loadState, section }: { report: StudyReport | null; loadState: LoadState; section: FsrsSection }) {
  useTranslation("fsrs");
  const capability = report?.statisticsHub?.fsrs;
  if (loadState !== "ready" || !capability) {
    return (
      <section className="statistics-empty-page panel-surface">
        <Brain size={30} />
        <h1>FSRS</h1>
        <p>{tf("unavailable")}</p>
      </section>
    );
  }
  return <FsrsReady capability={capability} section={section} />;
}

function FsrsReady({ capability, section }: { capability: FsrsCapability; section: FsrsSection }) {
  const initialConfig = capability.defaultConfigurationId;
  const defaultGroup = capability.configurations.find((item) => item.id === initialConfig) || capability.configurations[0];
  const [scope, setScope] = useState<FsrsScope>(() => {
    if (section === "simulator" && defaultGroup?.deckDesiredRetentionOverrides.length) {
      return { kind: "deck", deckId: defaultGroup.deckIds[0] };
    }
    if (capability.mixedConfiguration && defaultGroup) return { kind: "configuration", configurationId: defaultGroup.id };
    return { kind: "all_collection" };
  });
  const [period, setPeriod] = useState<"30d" | "90d" | "180d" | "1y">("90d");
  const [response, setResponse] = useState<FsrsResponse | null>(null);
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [error, setError] = useState("");
  const [simulation, setSimulation] = useState<SimulatorInputs>({
    desiredRetention: 0.93,
    horizonDays: 180,
    additionalNewCards: 0,
    newCardsPerDay: 20,
    maximumReviewsPerDay: 500,
  });
  const cache = useRef(new Map<string, FsrsResponse>());
  const sequence = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const operation = section === "simulator" ? "simulate" : section;
  const explicit = section === "calibration" || section === "simulator";
  const query = useMemo<FsrsQuery>(() => ({
    operation,
    scope,
    period,
    ...(section === "simulator" ? { simulation } : {}),
  }), [operation, scope, period, section, simulation]);
  const selectedGroup = configurationForScope(capability, scope) || defaultGroup;
  const incompatibleExplicitScope = explicit && (
    !selectedGroup
    || (capability.mixedConfiguration && scope.kind !== "configuration" && scope.kind !== "deck")
  );

  useEffect(() => {
    sequence.current += 1;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setResponse(null);
    setError("");
    setStatus(explicit ? "idle" : "loading");
    if (explicit || !capability.enabled || !capability.configurations.length) return;
    void load(query);
    return () => activeRequest.current?.abort();
    // Query identity is represented by section/scope/period primitives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, scope, period, capability.enabled, capability.configurations.length]);

  async function load(nextQuery: FsrsQuery) {
    const key = fsrsQueryKey(nextQuery);
    if (cache.current.has(key)) {
      setResponse(cache.current.get(key)!);
      setStatus("ready");
      return;
    }
    activeRequest.current?.abort();
    const current = ++sequence.current;
    const controller = new AbortController();
    activeRequest.current = controller;
    setResponse(null);
    setStatus("loading");
    setError("");
    try {
      const next = await fetchFsrs(nextQuery, controller.signal);
      if (current !== sequence.current) return;
      cache.current.set(key, next);
      setResponse(next);
      setStatus("ready");
    } catch (caught) {
      if (current !== sequence.current || (caught as Error).name === "AbortError") return;
      setError((caught as Error).message || tf("calculationFailed"));
      setStatus("error");
    } finally {
      if (current === sequence.current) activeRequest.current = null;
    }
  }

  const deckForAction = selectedGroup?.deckIds[0] ?? capability.configurations[0]?.deckIds[0];
  const openOptions = () => deckForAction
    ? runReportAction("open-deck-options", { deckId: deckForAction }).then((result) => {
      if (!result.ok) setError(result.error || tf("optionsFailed"));
    })
    : undefined;

  return (
    <div className="statistics-shell fsrs-shell" data-testid="fsrs-page" data-fsrs-section={section}>
      <StatisticsSidebar />
      <div className="statistics-content">
        <header className="statistics-header statistics-page-surface fsrs-hero">
          <div>
            <span className="statistics-section-marker">{tf("marker")}</span>
            <h1>{section === "overview" ? "FSRS" : tf(`sections.${section}.label`)}</h1>
            <p>{headingDescription(section)}</p>
          </div>
          <button className="secondary-button" type="button" onClick={openOptions} disabled={!deckForAction}>
            <ExternalLink size={16} /> {tf("openOptions")}
          </button>
        </header>

        <nav className="fsrs-local-nav" aria-label={tf("navLabel")}>
          {fsrsSections.map((item) => (
            <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>
              <strong>{tf(`sections.${item.id}.label`)}</strong><span>{tf(`sections.${item.id}.short`)}</span>
            </a>
          ))}
        </nav>

        {!capability.enabled ? <DisabledState /> : !capability.configurations.length ? <NoConfigurationState /> : (
          <>
            <FsrsQueryBar capability={capability} scope={scope} setScope={setScope} period={period} setPeriod={setPeriod} />
            {capability.mixedConfiguration ? (
              <div className="fsrs-context-note" data-testid="fsrs-mixed-configuration">
                <Info size={16} />
                <span><strong>{tf("mixed.title")}</strong> {tf("mixed.detail")}</span>
              </div>
            ) : null}

            {section === "calibration" && (status === "idle" || status === "loading") ? (
              <CalibrationActionPanel
                status={status}
                scopeLabel={scopeLabel(capability, scope)}
                period={period}
                disabled={incompatibleExplicitScope}
                onRun={() => void load(query)}
              />
            ) : null}
            {section === "simulator" ? (
              <SimulatorControls
                values={simulation}
                setValues={setSimulation}
                onRun={() => void load(query)}
                status={status}
                selectedGroup={selectedGroup}
                scopeLabel={scopeLabel(capability, scope)}
                disabled={incompatibleExplicitScope}
              />
            ) : null}
            {status === "loading" && section !== "calibration" && section !== "simulator" ? <FsrsLoadingPanel /> : null}
            {status === "error" ? <FsrsErrorPanel message={error} onRetry={() => void load(query)} /> : null}
            {response?.operation === operation ? <FsrsResult section={section} result={response.result} /> : null}
          </>
        )}
      </div>
    </div>
  );
}

function StatisticsSidebar() {
  return (
    <aside className="statistics-sidebar" data-testid="statistics-sidebar">
      <div className="statistics-sidebar-heading">
        <span className="statistics-sidebar-icon"><Brain size={18} /></span>
        <div><strong>{i18n.t("shell.title", { ns: "statistics" })}</strong><span>{i18n.t("shell.subtitle", { ns: "statistics" })}</span></div>
      </div>
      <nav aria-label={i18n.t("shell.navLabel", { ns: "statistics" })}>
        {statisticsSections.map(([label, path]) => (
          <a key={path} href={`#${path}`} aria-current={path === "/stats/fsrs" ? "page" : undefined}>{i18n.t(`shell.${label}`, { ns: "statistics" })}</a>
        ))}
      </nav>
    </aside>
  );
}

function FsrsQueryBar({ capability, scope, setScope, period, setPeriod }: {
  capability: FsrsCapability;
  scope: FsrsScope;
  setScope: (scope: FsrsScope) => void;
  period: string;
  setPeriod: (period: "30d" | "90d" | "180d" | "1y") => void;
}) {
  const value = scope.kind === "configuration" ? scope.configurationId : scope.kind === "deck" ? `deck:${scope.deckId}` : scope.kind;
  const configurationIds = new Set(capability.configurations.map((group) => group.id));
  return (
    <section className="statistics-query-surface fsrs-query-surface" aria-label={tf("query.label")}>
      <div className="fsrs-query-heading">
        <span><SlidersHorizontal size={16} /> {tf("query.context")}</span>
        <strong>{scopeLabel(capability, scope)}</strong>
      </div>
      <div className="statistics-controls">
        <label>{tf("query.scope")}
          <select aria-label={tf("query.scopeAria")} value={value} onChange={(event) => {
            const next = event.target.value;
            setScope(configurationIds.has(next)
              ? { kind: "configuration", configurationId: next }
              : next.startsWith("deck:")
                ? { kind: "deck", deckId: Number(next.slice(5)) }
                : { kind: next as "dashboard" | "all_collection" });
          }}>
            <option value="dashboard">{tf("query.dashboard")}</option>
            <option value="all_collection">{tf("query.collection")}</option>
            {capability.configurations.map((group) => <option key={group.id} value={group.id}>{tf("query.configuration", { name: group.presetName })}</option>)}
            {capability.configurations.flatMap((group) => group.deckIds.map((deckId, index) => (
              <option key={`deck:${deckId}`} value={`deck:${deckId}`}>{tf("query.deck", { name: group.deckNames[index] })}</option>
            )))}
          </select>
        </label>
        <label>{tf("query.period")}
          <select aria-label={tf("query.periodAria")} value={period} onChange={(event) => setPeriod(event.target.value as "30d" | "90d" | "180d" | "1y")}>
            <option value="30d">{periodLabel("30d")}</option><option value="90d">{periodLabel("90d")}</option>
            <option value="180d">{periodLabel("180d")}</option><option value="1y">{periodLabel("1y")}</option>
          </select>
        </label>
        <span className={`statistics-confidence-badge is-${capability.availability}`}>{availabilityLabel(capability.availability)}</span>
      </div>
    </section>
  );
}

function CalibrationActionPanel({ status, scopeLabel: selectedScope, period, disabled, onRun }: {
  status: RequestStatus;
  scopeLabel: string;
  period: string;
  disabled: boolean;
  onRun: () => void;
}) {
  return (
    <section className="fsrs-action-panel panel-surface" data-testid="fsrs-calibration-idle">
      <span className="fsrs-action-icon"><CircleGauge size={26} /></span>
      <div className="fsrs-action-copy">
        <span className="statistics-section-marker">{tf("action.marker")}</span>
        <h2>{status === "loading" ? tf("action.loadingTitle") : tf("action.title")}</h2>
        <p>{tf("action.description")}</p>
        <dl><div><dt>{tf("action.scope")}</dt><dd>{selectedScope}</dd></div><div><dt>{tf("action.period")}</dt><dd>{periodLabel(period)}</dd></div><div><dt>{tf("action.safety")}</dt><dd>{tf("action.readOnly")}</dd></div></dl>
        {disabled ? <small className="fsrs-field-error">{tf("action.selectOne")}</small> : null}
      </div>
      <button className="primary-button" type="button" onClick={onRun} disabled={disabled || status === "loading"}>
        {status === "loading" ? <RefreshCw className="is-spinning" size={16} /> : <Play size={16} />}
        {status === "loading" ? tf("action.calculating") : tf("action.run")}
      </button>
    </section>
  );
}

function FsrsResult({ section, result }: { section: FsrsSection; result: Record<string, unknown> }) {
  if (section === "overview") return <OverviewView result={result as unknown as OverviewResult} />;
  if (section === "memory") return <MemoryView result={result as unknown as MemoryResult} />;
  if (section === "calibration") return <CalibrationView result={result as unknown as CalibrationResult} />;
  if (section === "steps") return <StepsView result={result as unknown as StepsResult} />;
  return <SimulatorView result={result as unknown as SimulationResult} />;
}

function OverviewView({ result }: { result: OverviewResult }) {
  const target = result.targetRetentionRange;
  const gap = targetGap(result.actualRetention, target);
  return (
    <div className="statistics-section-stack" data-testid="fsrs-overview">
      <InsightBanner icon={<Sparkles size={22} />} eyebrow={tf("overview.eyebrow")} title={tf("overview.title")} tone={result.dataSufficiency === "insufficient" ? "neutral" : "accent"}>
        {result.insight}
      </InsightBanner>

      <section className="fsrs-retention-comparison panel-surface" aria-labelledby="fsrs-retention-heading">
        <header className="statistics-panel-header">
          <div><h2 id="fsrs-retention-heading">{tf("overview.retentionTitle")}</h2><p>{tf("overview.retentionDescription")}</p></div>
          <ConfidenceBadge value={result.dataSufficiency} />
        </header>
        <div className="fsrs-retention-values">
          <MetricBlock label={tf("overview.actual")} value={formatPercent(result.actualRetention)} caption={tf("overview.actualCaption")} accent="success" />
          <span className="fsrs-comparison-arrow"><ArrowRight size={20} /></span>
          <MetricBlock label={tf("overview.target")} value={formatTarget(target)} caption={result.mixedConfiguration ? tf("overview.targetRange") : tf("overview.targetPreset")} accent="target" />
          <MetricBlock label={tf("overview.gap")} value={gap == null ? tf("overview.noData") : tf("overview.points", { value: signed(gap * 100) })} caption={gap === 0 ? tf("overview.gapInside") : tf("overview.gapNearest")} accent="neutral" />
        </div>
        <div className="fsrs-retention-track" aria-label={tf("overview.retentionScale")}>
          <span className="fsrs-target-range" style={target ? { left: `${target.min * 100}%`, width: `${Math.max(1, (target.max - target.min) * 100)}%` } : undefined} />
          {result.actualRetention != null ? <i className="fsrs-actual-marker" style={{ left: `${result.actualRetention * 100}%` }}><span>{formatPercent(result.actualRetention)}</span></i> : null}
        </div>
      </section>

      <section className="statistics-kpis fsrs-kpis-primary">
        <Kpi icon={<Brain size={17} />} label={tf("overview.remembered")} value={formatNumber(result.estimatedRemembered)} caption={tf("overview.studied", { count: formatNumber(result.studiedCards) })} accent="primary" featured />
        <Kpi icon={<Target size={17} />} label={tf("overview.averageProbability")} value={formatPercent(result.averageRetrievability)} caption={tf("overview.currentEstimate")} accent="success" featured />
        <Kpi label={tf("overview.medianStability")} value={formatDays(result.medianStabilityDays)} caption={tf("overview.stabilityCaption")} />
      </section>

      <section className="statistics-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>{tf("overview.configs")}</h2><p>{tf("overview.configsDescription")}</p></div><span className="fsrs-count-badge">{result.configurations.length}</span></header>
        <div className="statistics-table-wrap">
          <table className="statistics-table fsrs-config-table">
            <thead><tr><th>{tf("overview.presetDecks")}</th><th>{tf("overview.cards")}</th><th>{tf("overview.memoryCovered")}</th><th>{tf("overview.target")}</th><th>{tf("overview.data")}</th><th>{tf("overview.overrides")}</th></tr></thead>
            <tbody>{result.configurations.map((group) => (
              <tr key={group.id}>
                <th><strong>{group.presetName}</strong><small>{group.deckNames.slice(0, 2).join(", ")}{group.deckNames.length > 2 ? ` +${group.deckNames.length - 2}` : ""}</small></th>
                <td>{formatNumber(group.cardCount)}<small>{i18n.t("units.deck", { ns: "common", count: group.deckIds.length })}</small></td>
                <td>{formatNumber(group.reviewedCardCount)}<small>{group.cardCount ? formatPercent(group.reviewedCardCount / group.cardCount) : tf("overview.noData")}</small></td>
                <td>{formatPercent(group.defaultDesiredRetention)}</td>
                <td><ConfidenceBadge value={group.dataSufficiency} /></td>
                <td>{overrideLabel(group)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <nav className="fsrs-analysis-links" aria-label={tf("overview.details")}>
        {fsrsSections.filter((item) => item.id !== "overview").map((item) => (
          <a key={item.id} href={`#${item.path}`}><span><strong>{tf(`sections.${item.id}.label`)}</strong><small>{tf(`sections.${item.id}.short`)}</small></span><ArrowRight size={17} /></a>
        ))}
      </nav>
    </div>
  );
}

function MemoryView({ result }: { result: MemoryResult }) {
  return (
    <div className="statistics-section-stack" data-testid="fsrs-memory">
      <InsightBanner icon={<Brain size={22} />} eyebrow={tf("memory.eyebrow")} title={tf("memory.title", { count: formatNumber(result.estimatedRemembered) })}>
        {tf("memory.description", { count: formatNumber(result.studiedCards) })}
      </InsightBanner>
      <section className="statistics-kpis compact four fsrs-memory-kpis">
        <Kpi label={tf("memory.average")} value={formatPercent(result.averageRetrievability)} accent="success" />
        <Kpi label={tf("memory.median")} value={formatPercent(result.medianRetrievability)} />
        <Kpi label={tf("memory.belowTarget")} value={formatNumber(result.cardsBelowOwnTarget)} accent="warning" />
        <Kpi label={tf("memory.overdue")} value={formatNumber(result.overdueCards)} accent="danger" />
        <Kpi label={tf("memory.stability")} value={formatDays(result.medianStabilityDays)} />
        <Kpi label={tf("memory.difficulty")} value={result.medianDifficulty == null ? tf("overview.noData") : formatNumber(result.medianDifficulty)} caption={tf("memory.difficultyCaption")} />
      </section>
      <div className="statistics-analytical-grid fsrs-memory-grid">
        <DistributionPanel title={tf("memory.recallDistribution")} description={tf("memory.recallDescription")} rows={result.retrievabilityDistribution} tone="recall" />
        <DistributionPanel title={tf("memory.stabilityDistribution")} description={tf("memory.stabilityDescription")} rows={result.stabilityDistribution} tone="stability" />
      </div>
      <DistributionPanel title={tf("memory.difficultyDistribution")} description={tf("memory.difficultyDescription")} rows={result.difficultyDistribution} tone="difficulty" />
      <section className="fsrs-limitations panel-surface">
        <Info size={18} /><div><h2>{tf("memory.limits")}</h2><ul>{memoryLimitations(result.limitations).map((item) => <li key={item}>{item}</li>)}</ul></div>
      </section>
    </div>
  );
}

function CalibrationView({ result }: { result: CalibrationResult }) {
  const verdict = calibrationVerdict(result.sufficiency, result.bins);
  return (
    <div className="statistics-section-stack" data-testid="fsrs-calibration">
      <InsightBanner icon={<CircleGauge size={22} />} eyebrow={tf("calibration.eyebrow")} title={verdict.title} tone={verdict.tone} badge={<ConfidenceBadge value={result.sufficiency} />}>
        {verdict.detail}
      </InsightBanner>
      <section className="statistics-kpis compact four">
        <Kpi label={tf("calibration.sample")} value={formatNumber(result.sampleSize)} accent="primary" />
        <Kpi label={tf("calibration.rmse")} value={result.rmseBins == null ? tf("overview.noData") : formatPercent(result.rmseBins)} caption={tf("calibration.rmseCaption")} />
        <Kpi label={tf("calibration.gap")} value={verdict.weightedGap == null ? tf("calibration.noConclusion") : tf("overview.points", { value: signed(verdict.weightedGap * 100) })} />
        <Kpi label={tf("calibration.hard")} value={result.hardIsRecall ? tf("calibration.recalled") : tf("calibration.notRecalled")} caption={tf("calibration.hardCaption")} />
      </section>
      <section className="statistics-panel statistics-chart-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>{tf("calibration.title")}</h2><p>{tf("calibration.description")}</p></div></header>
        <p className="statistics-chart-summary">{tf("calibration.summary")}</p>
        <CalibrationChart bins={result.bins} />
        <details className="statistics-data-disclosure">
          <summary>{tf("calibration.table")}</summary>
          <div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>{tf("calibration.interval")}</th><th>{tf("calibration.predicted")}</th><th>{tf("calibration.actual")}</th><th>{tf("calibration.answers")}</th><th>{tf("calibration.reliability")}</th></tr></thead><tbody>{result.bins.map((bin) => (
            <tr key={bin.label}><th>{bin.label}</th><td>{formatPercent(bin.predicted)}</td><td>{formatPercent(bin.actual)}</td><td>{bin.sampleSize}</td><td>{sufficiencyLabel(bin.sufficiency)}</td></tr>
          ))}</tbody></table></div>
          <p className="statistics-footnote">{tf("calibration.footnote")}</p>
        </details>
      </section>
    </div>
  );
}

function StepsView({ result }: { result: StepsResult }) {
  if (result.availability === "mixed_configuration") {
    return <InsightBanner icon={<AlertTriangle size={22} />} eyebrow={tf("steps.oneSetEyebrow")} title={tf("steps.oneSetTitle")} tone="warning">{tf("steps.oneSetDetail")}</InsightBanner>;
  }
  const hasRecommendation = Boolean(result.recommendation);
  const config = result.configuration;
  return (
    <div className="statistics-section-stack" data-testid="fsrs-steps">
      <InsightBanner icon={hasRecommendation ? <CheckCircle2 size={22} /> : <Database size={22} />} eyebrow={tf("steps.verdict")} title={hasRecommendation ? tf("steps.enoughTitle") : tf("steps.sparseTitle")} tone={hasRecommendation ? "positive" : "neutral"}>
        {hasRecommendation ? tf("steps.enoughDetail") : tf("steps.sparseDetail")}
      </InsightBanner>
      {result.scopeExpandedToPreset ? <div className="fsrs-context-note"><Info size={16} /><span><strong>{tf("steps.expandedTitle")}</strong> {tf("steps.expandedDetail")}</span></div> : null}
      <section className="statistics-panel panel-surface fsrs-steps-config">
        <header className="statistics-panel-header"><div><h2>{tf("steps.current")}</h2><p>{config ? tf("steps.preset", { name: config.presetName, decks: i18n.t("units.deck", { ns: "common", count: config.deckIds.length }) }) : tf("steps.configUnavailable")}</p></div>{config ? <ConfidenceBadge value={config.dataSufficiency} /> : null}</header>
        <div className="fsrs-step-sequences">
          <StepSequence label={tf("steps.learning")} values={result.learningStepsSeconds || []} />
          <StepSequence label={tf("steps.relearning")} values={result.relearningStepsSeconds || []} />
          <MetricBlock label={tf("steps.shortTerm")} value={result.shortTermMode === "fsrs" ? tf("steps.managed") : tf("steps.configured")} caption={tf("steps.presetSetting")} accent="neutral" />
        </div>
      </section>
      <section className="statistics-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>{tf("steps.observed")}</h2><p>{tf("steps.observedDescription")}</p></div></header>
        <div className="statistics-table-wrap"><table className="statistics-table fsrs-scenarios-table"><thead><tr><th>{tf("steps.scenario")}</th><th>{tf("steps.answers")}</th><th>{tf("steps.retention")}</th><th>{tf("steps.successfulInterval")}</th><th>{tf("steps.reliability")}</th></tr></thead><tbody>{result.scenarios.map((item) => (
          <tr key={item.id}><th>{scenarioLabel(item.id)}</th><td>{formatNumber(item.sampleSize)}</td><td>{formatPercent(item.retention)}</td><td>{item.observedSuccessfulRangeSeconds ? formatRange(item.observedSuccessfulRangeSeconds) : tf("steps.insufficient")}</td><td><ConfidenceBadge value={item.sufficiency} /></td></tr>
        ))}</tbody></table></div>
      </section>
      <section className={`fsrs-recommendation panel-surface ${hasRecommendation ? "is-ready" : ""}`}>
        <ShieldCheck size={22} /><div><span className="statistics-section-marker">{tf("steps.recommendation")}</span><h2>{result.recommendation ? formatRange(result.recommendation.rangeSeconds) : tf("steps.unavailable")}</h2><p>{result.recommendation ? tf("steps.confidence", { value: sufficiencyLabel(result.recommendation.confidence) }) : tf("steps.needSample")}</p></div><strong>{tf("steps.readOnly")}</strong>
      </section>
    </div>
  );
}

function SimulatorControls({ values, setValues, onRun, status, selectedGroup, scopeLabel: selectedScope, disabled }: {
  values: SimulatorInputs;
  setValues: (values: SimulatorInputs) => void;
  onRun: () => void;
  status: RequestStatus;
  selectedGroup?: FsrsConfigurationGroup;
  scopeLabel: string;
  disabled: boolean;
}) {
  const errors = simulatorFieldErrors(values);
  const invalid = Object.keys(errors).length > 0;
  return (
    <section className="fsrs-simulator-lab panel-surface" data-testid="fsrs-simulator-form">
      <header className="statistics-panel-header">
        <div><span className="statistics-section-marker">{tf("simulator.marker")}</span><h2>{tf("simulator.title")}</h2><p>{tf("simulator.description")}</p></div>
        <span className="fsrs-readonly-badge"><ShieldCheck size={15} /> {tf("simulator.readOnly")}</span>
      </header>
      <div className="fsrs-simulator-baseline">
        <MetricBlock label={tf("simulator.selectedScope")} value={selectedScope} caption={selectedGroup ? tf("simulator.preset", { name: selectedGroup.presetName }) : tf("simulator.selectConfig")} accent="neutral" />
        <MetricBlock label={tf("simulator.currentTarget")} value={formatPercent(selectedGroup?.defaultDesiredRetention ?? null)} caption={tf("simulator.beforeRun")} accent="target" />
        <MetricBlock label={tf("simulator.horizon")} value={tf("simulator.horizonValue", { count: values.horizonDays })} caption={tf("simulator.window")} accent="neutral" />
      </div>
      <form className="fsrs-simulator-form" onSubmit={(event) => { event.preventDefault(); if (!invalid && !disabled && status !== "loading") onRun(); }}>
        <label>{tf("simulator.desired")}<div className="fsrs-input-with-unit"><input aria-label={tf("simulator.desiredAria")} type="number" min="0.75" max="0.99" step="0.01" value={finiteValue(values.desiredRetention)} onChange={(event) => setValues({ ...values, desiredRetention: Number(event.target.value) })} /><span>{tf("simulator.fraction")}</span></div>{errors.desiredRetention ? <small className="fsrs-field-error">{errors.desiredRetention}</small> : <small>{tf("simulator.desiredHint")}</small>}</label>
        <label>{tf("simulator.horizon")}<select aria-label={tf("simulator.horizonAria")} value={values.horizonDays} onChange={(event) => setValues({ ...values, horizonDays: Number(event.target.value) as 90 | 180 | 365 })}><option value="90">{tf("simulator.horizonValue", { count: 90 })}</option><option value="180">{tf("simulator.horizonValue", { count: 180 })}</option><option value="365">{tf("simulator.horizonValue", { count: 365 })}</option></select></label>
        <label>{tf("simulator.additional")}<div className="fsrs-input-with-unit"><input aria-label={tf("simulator.additionalAria")} type="number" min="0" max="100000" value={finiteValue(values.additionalNewCards)} onChange={(event) => setValues({ ...values, additionalNewCards: Number(event.target.value) })} /><span>{tf("simulator.cardsShort")}</span></div>{errors.additionalNewCards ? <small className="fsrs-field-error">{errors.additionalNewCards}</small> : null}</label>
        <label>{tf("simulator.perDay")}<div className="fsrs-input-with-unit"><input aria-label={tf("simulator.perDayAria")} type="number" min="0" max="1000" value={finiteValue(values.newCardsPerDay)} onChange={(event) => setValues({ ...values, newCardsPerDay: Number(event.target.value) })} /><span>{tf("simulator.cardsShort")}</span></div>{errors.newCardsPerDay ? <small className="fsrs-field-error">{errors.newCardsPerDay}</small> : null}</label>
        <label>{tf("simulator.reviewLimit")}<div className="fsrs-input-with-unit"><input aria-label={tf("simulator.reviewLimitAria")} type="number" min="1" max="10000" value={finiteValue(values.maximumReviewsPerDay)} onChange={(event) => setValues({ ...values, maximumReviewsPerDay: Number(event.target.value) })} /><span>{tf("simulator.perDayUnit")}</span></div>{errors.maximumReviewsPerDay ? <small className="fsrs-field-error">{errors.maximumReviewsPerDay}</small> : null}</label>
        <button className="primary-button fsrs-run-scenario" type="submit" disabled={invalid || disabled || status === "loading"}>
          {status === "loading" ? <RefreshCw className="is-spinning" size={16} /> : <Play size={16} />}
          {status === "loading" ? tf("simulator.calculating") : tf("simulator.run")}
        </button>
      </form>
      {values.desiredRetention >= .97 ? <p className="fsrs-retention-warning"><AlertTriangle size={16} /> {tf("simulator.highWarning")}</p> : null}
      {disabled ? <p className="fsrs-retention-warning"><AlertTriangle size={16} /> {tf("simulator.selectWarning")}</p> : null}
    </section>
  );
}

function SimulatorView({ result }: { result: SimulationResult }) {
  return (
    <div className="statistics-section-stack" data-testid="fsrs-simulator-result">
      <InsightBanner icon={<Activity size={22} />} eyebrow={tf("simulator.deltaEyebrow")} title={tf("simulator.deltaTitle", { reviews: signed(result.delta.reviewsPerDay), minutes: signed(result.delta.minutesPerDay) })} tone="accent" badge={<span className="fsrs-readonly-badge"><ShieldCheck size={15} /> {tf("simulator.readOnly")}</span>}>
        {tf("simulator.deltaDetail", { from: formatPercent(result.current.desiredRetention), to: formatPercent(result.hypothetical.desiredRetention) })}
      </InsightBanner>
      <section className="fsrs-scenario-comparison">
        <ScenarioColumn title={tf("charts.current")} scenario={result.current} />
        <span className="fsrs-scenario-arrow"><ArrowRight size={22} /></span>
        <ScenarioColumn title={tf("simulator.hypothetical")} scenario={result.hypothetical} highlighted />
      </section>
      <section className="statistics-kpis compact four">
        <Kpi label={tf("simulator.deltaReviews")} value={signed(result.delta.reviewsPerDay)} accent="primary" />
        <Kpi label={tf("simulator.deltaMinutes")} value={signed(result.delta.minutesPerDay)} />
        <Kpi label={tf("simulator.peak")} value={formatNumber(result.hypothetical.peakReviews)} />
        <Kpi label={tf("simulator.backlog")} value={formatNumber(result.hypothetical.backlog)} accent={result.hypothetical.backlog > 0 ? "warning" : "success"} />
      </section>
      <section className="statistics-panel statistics-chart-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>{tf("simulator.workload")}</h2><p>{tf("simulator.workloadDescription")}</p></div></header>
        <WorkloadComparisonChart current={result.current.daily} hypothetical={result.hypothetical.daily} />
        <details className="statistics-data-disclosure"><summary>{tf("simulator.dataTable")}</summary><div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>{tf("simulator.day")}</th><th>{tf("charts.current")}</th><th>{tf("simulator.scenario")}</th></tr></thead><tbody>{result.hypothetical.daily.map((day, index) => <tr key={day.day}><th>{day.day}</th><td>{result.current.daily[index]?.reviews ?? "—"}</td><td>{day.reviews}</td></tr>)}</tbody></table></div></details>
      </section>
      <section className="fsrs-safety-statement panel-surface"><ShieldCheck size={22} /><div><h2>{tf("simulator.safetyTitle")}</h2><p>{tf("simulator.safetyDetail")}</p></div></section>
    </div>
  );
}

function DistributionPanel({ title, description, rows, tone }: { title: string; description: string; rows: Distribution[]; tone: string }) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <section className={`statistics-panel statistics-chart-panel panel-surface fsrs-distribution-panel is-${tone}`}>
      <header className="statistics-panel-header"><div><h2>{title}</h2><p>{description}</p></div><span className="fsrs-count-badge">{formatNumber(total)}</span></header>
      {rows.length ? <div className="fsrs-distribution" role="img" aria-label={title}>{rows.map((row) => (
        <div key={row.label}><span>{row.label}</span><i><b style={{ width: `${row.count / max * 100}%` }} /></i><strong>{formatNumber(row.count)}</strong><small>{formatPercent(row.percentage)}</small></div>
      ))}</div> : <p className="statistics-empty">{tf("distribution.unavailable")}</p>}
      <details className="statistics-data-disclosure"><summary>{tf("distribution.table")}</summary><div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>{tf("distribution.range")}</th><th>{tf("distribution.cards")}</th><th>{tf("distribution.share")}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><th>{row.label}</th><td>{row.count}</td><td>{formatPercent(row.percentage)}</td></tr>)}</tbody></table></div></details>
    </section>
  );
}

function InsightBanner({ icon, eyebrow, title, children, tone = "accent", badge }: { icon: ReactNode; eyebrow: string; title: string; children: ReactNode; tone?: string; badge?: ReactNode }) {
  return <section className={`statistics-insight-card panel-surface fsrs-insight is-${tone}`}><span className="statistics-insight-icon">{icon}</span><div><span>{eyebrow}</span><h2>{title}</h2><p>{children}</p></div>{badge}</section>;
}

function Kpi({ icon, label, value, caption, accent = "neutral", featured = false }: { icon?: ReactNode; label: string; value: string; caption?: string; accent?: string; featured?: boolean }) {
  return <article className={`statistics-kpi-card fsrs-kpi is-${accent}${featured ? " is-featured" : ""}`}><i className="statistics-kpi-accent" />{icon ? <span className="fsrs-kpi-icon">{icon}</span> : null}<span className="statistics-kpi-label">{label}</span><strong>{value}</strong>{caption ? <small>{caption}</small> : null}</article>;
}

function MetricBlock({ label, value, caption, accent }: { label: string; value: string; caption: string; accent: string }) {
  return <div className={`fsrs-metric-block is-${accent}`}><span>{label}</span><strong>{value}</strong><small>{caption}</small></div>;
}

function ConfidenceBadge({ value }: { value: string }) {
  return <span className={`statistics-confidence-badge is-${value}`}>{sufficiencyLabel(value)}</span>;
}

function ScenarioColumn({ title, scenario, highlighted = false }: { title: string; scenario: SimulationScenario; highlighted?: boolean }) {
  return <article className={`fsrs-scenario-column panel-surface${highlighted ? " is-highlighted" : ""}`}><span>{title}</span><strong>{formatPercent(scenario.desiredRetention)}</strong><dl><div><dt>{tf("simulator.reviewsDay")}</dt><dd>{formatNumber(scenario.averageReviewsPerDay)}</dd></div><div><dt>{tf("simulator.minutesDay")}</dt><dd>{formatNumber(scenario.averageMinutesPerDay)}</dd></div><div><dt>{tf("simulator.peakShort")}</dt><dd>{formatNumber(scenario.peakReviews)}</dd></div><div><dt>{tf("simulator.backlogShort")}</dt><dd>{formatNumber(scenario.backlog)}</dd></div></dl></article>;
}

function StepSequence({ label, values }: { label: string; values: number[] }) {
  return <div className="fsrs-step-sequence"><span>{label}</span>{values.length ? <div>{values.map((value, index) => <span key={`${value}-${index}`}>{formatStep(value)}{index < values.length - 1 ? <ArrowRight size={15} /> : null}</span>)}</div> : <strong>{tf("steps.managed")}</strong>}</div>;
}

function FsrsLoadingPanel() {
  return <section className="fsrs-loading-panel panel-surface" role="status"><RefreshCw className="is-spinning" size={22} /><div><h2>{tf("state.loadingTitle")}</h2><p>{tf("state.loadingDetail")}</p></div></section>;
}

function FsrsErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <section className="fsrs-error-panel panel-surface" role="alert"><AlertTriangle size={22} /><div><h2>{tf("state.errorTitle")}</h2><p>{message || tf("state.errorDetail")}</p></div><button className="secondary-button" type="button" onClick={onRetry}><RefreshCw size={15} /> {tf("state.retry")}</button></section>;
}

function DisabledState() {
  return <section className="statistics-empty-page panel-surface fsrs-empty-state" data-testid="fsrs-disabled"><span><Brain size={30} /></span><h2>{tf("state.disabledTitle")}</h2><p>{tf("state.disabledDetail")}</p></section>;
}

function NoConfigurationState() {
  return <section className="statistics-empty-page panel-surface fsrs-empty-state" data-testid="fsrs-no-configuration"><span><Settings2 size={30} /></span><h2>{tf("state.noConfigTitle")}</h2><p>{tf("state.noConfigDetail")}</p></section>;
}

function configurationForScope(capability: FsrsCapability, scope: FsrsScope) {
  if (scope.kind === "configuration") return capability.configurations.find((group) => group.id === scope.configurationId);
  if (scope.kind === "deck") {
    const deckId = scope.deckId;
    return capability.configurations.find((group) => group.deckIds.includes(deckId));
  }
  if (capability.configurations.length === 1) return capability.configurations[0];
  return undefined;
}

function scopeLabel(capability: FsrsCapability, scope: FsrsScope) {
  if (scope.kind === "dashboard") return tf("scope.dashboard");
  if (scope.kind === "all_collection") return capability.mixedConfiguration ? tf("scope.collectionMixed") : tf("scope.collection");
  if (scope.kind === "configuration") return tf("scope.preset", { name: capability.configurations.find((group) => group.id === scope.configurationId)?.presetName || tf("scope.unavailable") });
  const deckId = "deckId" in scope ? scope.deckId : 0;
  for (const group of capability.configurations) {
    const index = group.deckIds.indexOf(deckId);
    if (index >= 0) return tf("scope.deck", { name: group.deckNames[index] });
  }
  return tf("scope.deckUnavailable");
}

function headingDescription(section: FsrsSection) {
  return tf(`sections.${section}.question`);
}

function availabilityLabel(value: string) {
  return tf(`availability.${value in availabilityKeys ? value : "preliminary"}`);
}

function sufficiencyLabel(value: string) {
  return tf(`availability.${value in availabilityKeys ? value : "preliminary"}`);
}

const availabilityKeys: Record<string, true> = { enabled: true, disabled: true, insufficient_data: true, partial_coverage: true, mixed_configuration: true, unavailable: true, error: true, sufficient: true, preliminary: true, insufficient: true, available: true };

function memoryLimitations(values: string[]) {
  const mapped = values.map((value) => availabilityKeys[value] ? tf(`limitations.${value}`) : tf(`limitations.${value}`, { defaultValue: value.replace(/_/g, " ") }));
  return mapped.length ? mapped : [tf("limitations.snapshot_not_history"), tf("limitations.missingValues")];
}

function overrideLabel(group: FsrsConfigurationGroup) {
  if (!group.deckDesiredRetentionOverrides.length) return tf("override.none");
  return group.deckDesiredRetentionOverrides.map((override) => {
    const index = group.deckIds.indexOf(override.deckId);
    return tf("override.deck", { name: group.deckNames[index] || tf("override.fallbackDeck"), value: formatPercent(override.desiredRetention) });
  }).join("; ");
}

function periodLabel(value: string) {
  return value === "1y" ? tf("query.year") : tf("query.days", { count: Number.parseInt(value, 10) });
}

function formatNumber(value: number) { return new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null) { return value == null ? tf("overview.noData") : `${formatNumber(value * 100)}%`; }
function formatTarget(value: { min: number; max: number } | null) { return !value ? tf("overview.noData") : value.min === value.max ? formatPercent(value.min) : `${formatPercent(value.min)}–${formatPercent(value.max)}`; }
function formatDays(value: number | null) { return value == null ? tf("overview.noData") : tf("query.days", { count: formatNumber(value) }); }
function formatStep(value: number) { return value < 3600 ? i18n.t("units.minutesShort", { ns: "common", value: Math.round(value / 60) }) : i18n.t("units.hoursShort", { ns: "common", value: formatNumber(value / 3600) }); }
function formatRange(values: number[]) { return `${formatStep(values[0])}–${formatStep(values[1])}`; }
function signed(value: number) { return `${value > 0 ? "+" : ""}${formatNumber(value)}`; }
function finiteValue(value: number) { return Number.isFinite(value) ? value : ""; }
function scenarioLabel(value: string) { return tf(`scenario.${value}`, { defaultValue: value }); }

export default FsrsStatisticsPage;
