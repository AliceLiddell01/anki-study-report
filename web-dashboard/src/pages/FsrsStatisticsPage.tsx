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
import { CalibrationChart, WorkloadComparisonChart } from "../components/fsrs/FsrsCharts";
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

const fsrsSections: Array<{ id: FsrsSection; label: string; path: string; short: string }> = [
  { id: "overview", label: "Обзор", short: "Как работает FSRS", path: "/stats/fsrs" },
  { id: "memory", label: "Состояние памяти", short: "Что помнится сейчас", path: "/stats/fsrs/memory" },
  { id: "calibration", label: "Точность модели", short: "Прогноз и факт", path: "/stats/fsrs/calibration" },
  { id: "steps", label: "Шаги обучения", short: "Краткосрочная память", path: "/stats/fsrs/steps" },
  { id: "simulator", label: "Симулятор", short: "Сценарий нагрузки", path: "/stats/fsrs/simulator" },
];

const statisticsSections = [
  ["Обзор", "/stats"], ["Качество", "/stats/quality"], ["Нагрузка", "/stats/load"],
  ["Прогресс", "/stats/progress"], ["Колоды", "/stats/decks"], ["FSRS", "/stats/fsrs"],
];

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
  const capability = report?.statisticsHub?.fsrs;
  if (loadState !== "ready" || !capability) {
    return (
      <section className="statistics-empty-page panel-surface">
        <Brain size={30} />
        <h1>FSRS</h1>
        <p>FSRS-аналитика пока недоступна в опубликованном отчёте.</p>
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
      setError((caught as Error).message || "Не удалось выполнить read-only расчёт.");
      setStatus("error");
    } finally {
      if (current === sequence.current) activeRequest.current = null;
    }
  }

  const deckForAction = selectedGroup?.deckIds[0] ?? capability.configurations[0]?.deckIds[0];
  const openOptions = () => deckForAction
    ? runReportAction("open-deck-options", { deckId: deckForAction }).then((result) => {
      if (!result.ok) setError(result.error || "Не удалось открыть настройки колоды.");
    })
    : undefined;

  return (
    <div className="statistics-shell fsrs-shell" data-testid="fsrs-page" data-fsrs-section={section}>
      <StatisticsSidebar />
      <div className="statistics-content">
        <header className="statistics-header statistics-page-surface fsrs-hero">
          <div>
            <span className="statistics-section-marker">Статистика · FSRS</span>
            <h1>{section === "overview" ? "FSRS" : fsrsSections.find((item) => item.id === section)?.label}</h1>
            <p>{headingDescription(section)}</p>
          </div>
          <button className="secondary-button" type="button" onClick={openOptions} disabled={!deckForAction}>
            <ExternalLink size={16} /> Открыть настройки колоды
          </button>
        </header>

        <nav className="fsrs-local-nav" aria-label="Разделы FSRS">
          {fsrsSections.map((item) => (
            <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>
              <strong>{item.label}</strong><span>{item.short}</span>
            </a>
          ))}
        </nav>

        {!capability.enabled ? <DisabledState /> : !capability.configurations.length ? <NoConfigurationState /> : (
          <>
            <FsrsQueryBar capability={capability} scope={scope} setScope={setScope} period={period} setPeriod={setPeriod} />
            {capability.mixedConfiguration ? (
              <div className="fsrs-context-note" data-testid="fsrs-mixed-configuration">
                <Info size={16} />
                <span><strong>Несколько несовместимых наборов.</strong> Они анализируются отдельно и не усредняются.</span>
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
        <div><strong>Статистика</strong><span>Периоды и сравнения</span></div>
      </div>
      <nav aria-label="Разделы статистики">
        {statisticsSections.map(([label, path]) => (
          <a key={path} href={`#${path}`} aria-current={path === "/stats/fsrs" ? "page" : undefined}>{label}</a>
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
    <section className="statistics-query-surface fsrs-query-surface" aria-label="Параметры FSRS">
      <div className="fsrs-query-heading">
        <span><SlidersHorizontal size={16} /> Контекст анализа</span>
        <strong>{scopeLabel(capability, scope)}</strong>
      </div>
      <div className="statistics-controls">
        <label>Область
          <select aria-label="Область FSRS" value={value} onChange={(event) => {
            const next = event.target.value;
            setScope(configurationIds.has(next)
              ? { kind: "configuration", configurationId: next }
              : next.startsWith("deck:")
                ? { kind: "deck", deckId: Number(next.slice(5)) }
                : { kind: next as "dashboard" | "all_collection" });
          }}>
            <option value="dashboard">Текущая область dashboard</option>
            <option value="all_collection">Вся коллекция</option>
            {capability.configurations.map((group) => <option key={group.id} value={group.id}>Набор: {group.presetName}</option>)}
            {capability.configurations.flatMap((group) => group.deckIds.map((deckId, index) => (
              <option key={`deck:${deckId}`} value={`deck:${deckId}`}>Колода: {group.deckNames[index]}</option>
            )))}
          </select>
        </label>
        <label>Период
          <select aria-label="Период FSRS" value={period} onChange={(event) => setPeriod(event.target.value as "30d" | "90d" | "180d" | "1y")}>
            <option value="30d">30 дней</option><option value="90d">90 дней</option>
            <option value="180d">180 дней</option><option value="1y">1 год</option>
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
        <span className="statistics-section-marker">Ручной read-only расчёт</span>
        <h2>{status === "loading" ? "Сопоставляем прогнозы и ответы" : "Рассчитать точность модели"}</h2>
        <p>Сравним вероятность воспоминания FSRS с фактическими ответами по интервалам. Расчёт запускается вручную, потому что читает историю выбранного периода.</p>
        <dl><div><dt>Область</dt><dd>{selectedScope}</dd></div><div><dt>Период</dt><dd>{periodLabel(period)}</dd></div><div><dt>Безопасность</dt><dd>Ничего не меняет в Anki</dd></div></dl>
        {disabled ? <small className="fsrs-field-error">Выберите один совместимый набор настроек или колоду.</small> : null}
      </div>
      <button className="primary-button" type="button" onClick={onRun} disabled={disabled || status === "loading"}>
        {status === "loading" ? <RefreshCw className="is-spinning" size={16} /> : <Play size={16} />}
        {status === "loading" ? "Рассчитываем…" : "Рассчитать точность"}
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
      <InsightBanner icon={<Sparkles size={22} />} eyebrow="Главный вывод" title="Как сейчас работает FSRS" tone={result.dataSufficiency === "insufficient" ? "neutral" : "accent"}>
        {result.insight}
      </InsightBanner>

      <section className="fsrs-retention-comparison panel-surface" aria-labelledby="fsrs-retention-heading">
        <header className="statistics-panel-header">
          <div><h2 id="fsrs-retention-heading">Фактическое и целевое удержание</h2><p>Исторические ответы сравниваются с целью; текущая вероятность памяти показана отдельно.</p></div>
          <ConfidenceBadge value={result.dataSufficiency} />
        </header>
        <div className="fsrs-retention-values">
          <MetricBlock label="Фактически" value={formatPercent(result.actualRetention)} caption="По ответам за период" accent="success" />
          <span className="fsrs-comparison-arrow"><ArrowRight size={20} /></span>
          <MetricBlock label="Цель" value={formatTarget(target)} caption={result.mixedConfiguration ? "Диапазон совместимых групп" : "Настройка выбранного пресета"} accent="target" />
          <MetricBlock label="Разница" value={gap == null ? "Нет данных" : `${signed(gap * 100)} п. п.`} caption={gap === 0 ? "Факт внутри целевого диапазона" : "До ближайшей границы цели"} accent="neutral" />
        </div>
        <div className="fsrs-retention-track" aria-label="Шкала фактического и целевого удержания">
          <span className="fsrs-target-range" style={target ? { left: `${target.min * 100}%`, width: `${Math.max(1, (target.max - target.min) * 100)}%` } : undefined} />
          {result.actualRetention != null ? <i className="fsrs-actual-marker" style={{ left: `${result.actualRetention * 100}%` }}><span>{formatPercent(result.actualRetention)}</span></i> : null}
        </div>
      </section>

      <section className="statistics-kpis fsrs-kpis-primary">
        <Kpi icon={<Brain size={17} />} label="Ожидаемо помните сейчас" value={formatNumber(result.estimatedRemembered)} caption={`Изучено хотя бы раз: ${formatNumber(result.studiedCards)}`} accent="primary" featured />
        <Kpi icon={<Target size={17} />} label="Средняя вероятность" value={formatPercent(result.averageRetrievability)} caption="Текущая оценка памяти, не историческое удержание" accent="success" featured />
        <Kpi label="Медианная стабильность" value={formatDays(result.medianStabilityDays)} caption="Время снижения вероятности до 90%" />
      </section>

      <section className="statistics-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>Совместимые наборы настроек</h2><p>Пресеты с разными параметрами FSRS показаны отдельно и не усредняются.</p></div><span className="fsrs-count-badge">{result.configurations.length}</span></header>
        <div className="statistics-table-wrap">
          <table className="statistics-table fsrs-config-table">
            <thead><tr><th>Пресет и колоды</th><th>Карточки</th><th>Память покрыта</th><th>Цель</th><th>Данные</th><th>Переопределения</th></tr></thead>
            <tbody>{result.configurations.map((group) => (
              <tr key={group.id}>
                <th><strong>{group.presetName}</strong><small>{group.deckNames.slice(0, 2).join(", ")}{group.deckNames.length > 2 ? ` +${group.deckNames.length - 2}` : ""}</small></th>
                <td>{formatNumber(group.cardCount)}<small>{group.deckIds.length} {plural(group.deckIds.length, "колода", "колоды", "колод")}</small></td>
                <td>{formatNumber(group.reviewedCardCount)}<small>{group.cardCount ? formatPercent(group.reviewedCardCount / group.cardCount) : "Нет данных"}</small></td>
                <td>{formatPercent(group.defaultDesiredRetention)}</td>
                <td><ConfidenceBadge value={group.dataSufficiency} /></td>
                <td>{overrideLabel(group)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <nav className="fsrs-analysis-links" aria-label="Подробнее об FSRS">
        {fsrsSections.filter((item) => item.id !== "overview").map((item) => (
          <a key={item.id} href={`#${item.path}`}><span><strong>{item.label}</strong><small>{item.short}</small></span><ArrowRight size={17} /></a>
        ))}
      </nav>
    </div>
  );
}

function MemoryView({ result }: { result: MemoryResult }) {
  return (
    <div className="statistics-section-stack" data-testid="fsrs-memory">
      <InsightBanner icon={<Brain size={22} />} eyebrow="Оценка текущего состояния" title={`Вероятно помните сейчас ${formatNumber(result.estimatedRemembered)} карточек`}>
        Изучено хотя бы раз: {formatNumber(result.studiedCards)}. Это математическое ожидание, а не гарантированный список известных карточек.
      </InsightBanner>
      <section className="statistics-kpis compact four fsrs-memory-kpis">
        <Kpi label="Средняя вероятность" value={formatPercent(result.averageRetrievability)} accent="success" />
        <Kpi label="Медианная вероятность" value={formatPercent(result.medianRetrievability)} />
        <Kpi label="Ниже своей цели" value={formatNumber(result.cardsBelowOwnTarget)} accent="warning" />
        <Kpi label="Просрочено" value={formatNumber(result.overdueCards)} accent="danger" />
        <Kpi label="Медианная стабильность" value={formatDays(result.medianStabilityDays)} />
        <Kpi label="Медианная сложность" value={result.medianDifficulty == null ? "Нет данных" : formatNumber(result.medianDifficulty)} caption="Свойство модели, не оценка качества колоды" />
      </section>
      <div className="statistics-analytical-grid fsrs-memory-grid">
        <DistributionPanel title="Вероятность воспоминания" description="Текущая вероятность успешно вспомнить карточку. Карточки ниже собственной цели вынесены в KPI выше." rows={result.retrievabilityDistribution} tone="recall" />
        <DistributionPanel title="Стабильность памяти" description="Стабильность — время, за которое вероятность воспоминания снижается со 100% до 90%." rows={result.stabilityDistribution} tone="stability" />
      </div>
      <DistributionPanel title="Сложность по модели" description="Сложность влияет на рост интервалов; высокий диапазон сам по себе не означает ошибку или плохую колоду." rows={result.difficultyDistribution} tone="difficulty" />
      <section className="fsrs-limitations panel-surface">
        <Info size={18} /><div><h2>Границы оценки</h2><ul>{memoryLimitations(result.limitations).map((item) => <li key={item}>{item}</li>)}</ul></div>
      </section>
    </div>
  );
}

function CalibrationView({ result }: { result: CalibrationResult }) {
  const verdict = calibrationVerdict(result.sufficiency, result.bins);
  return (
    <div className="statistics-section-stack" data-testid="fsrs-calibration">
      <InsightBanner icon={<CircleGauge size={22} />} eyebrow="Вердикт калибровки" title={verdict.title} tone={verdict.tone} badge={<ConfidenceBadge value={result.sufficiency} />}>
        {verdict.detail}
      </InsightBanner>
      <section className="statistics-kpis compact four">
        <Kpi label="Ответов в выборке" value={formatNumber(result.sampleSize)} accent="primary" />
        <Kpi label="RMSE по интервалам" value={result.rmseBins == null ? "Нет данных" : formatPercent(result.rmseBins)} caption="Меньше означает ближе к факту" />
        <Kpi label="Среднее расхождение" value={verdict.weightedGap == null ? "Нет вывода" : `${signed(verdict.weightedGap * 100)} п. п.`} />
        <Kpi label="Трудно считается" value={result.hardIsRecall ? "Вспомнил" : "Не вспомнил"} caption="«Снова» остаётся ошибкой воспоминания" />
      </section>
      <section className="statistics-panel statistics-chart-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>Прогноз и фактическое удержание</h2><p>Пунктирная линия показывает идеальное совпадение. Интервалы с малой выборкой отмечены отдельно.</p></div></header>
        <p className="statistics-chart-summary">FSRS считает «Трудно», «Хорошо» и «Легко» успешным воспоминанием; «Снова» — неуспешным.</p>
        <CalibrationChart bins={result.bins} />
        <details className="statistics-data-disclosure">
          <summary>Таблица данных и методика</summary>
          <div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>Интервал</th><th>Прогноз</th><th>Фактически</th><th>Ответов</th><th>Надёжность</th></tr></thead><tbody>{result.bins.map((bin) => (
            <tr key={bin.label}><th>{bin.label}</th><td>{formatPercent(bin.predicted)}</td><td>{formatPercent(bin.actual)}</td><td>{bin.sampleSize}</td><td>{sufficiencyLabel(bin.sufficiency)}</td></tr>
          ))}</tbody></table></div>
          <p className="statistics-footnote">Вывод строится только по интервалам, которые backend не пометил как недостаточные. Граница «близко» для presentation — до 2 п. п. взвешенного расхождения.</p>
        </details>
      </section>
    </div>
  );
}

function StepsView({ result }: { result: StepsResult }) {
  if (result.availability === "mixed_configuration") {
    return <InsightBanner icon={<AlertTriangle size={22} />} eyebrow="Нужен один набор" title="Выберите совместимый пресет" tone="warning">Шаги разных наборов настроек нельзя объединять в один вывод.</InsightBanner>;
  }
  const hasRecommendation = Boolean(result.recommendation);
  const config = result.configuration;
  return (
    <div className="statistics-section-stack" data-testid="fsrs-steps">
      <InsightBanner icon={hasRecommendation ? <CheckCircle2 size={22} /> : <Database size={22} />} eyebrow="Вердикт по наблюдениям" title={hasRecommendation ? "Данных достаточно для справочного диапазона" : "Для рекомендации пока мало наблюдений"} tone={hasRecommendation ? "positive" : "neutral"}>
        {hasRecommendation ? "Диапазон получен из наблюдаемого успешного поведения и ничего не применяет." : "Отдельные проценты могут быть видны, но ключевым сценариям нужно не менее 100 наблюдений."}
      </InsightBanner>
      {result.scopeExpandedToPreset ? <div className="fsrs-context-note"><Info size={16} /><span><strong>Область расширена до пресета.</strong> Анализ включает обычные колоды с тем же совместимым набором.</span></div> : null}
      <section className="statistics-panel panel-surface fsrs-steps-config">
        <header className="statistics-panel-header"><div><h2>Текущая конфигурация</h2><p>{config ? `Пресет «${config.presetName}», ${config.deckIds.length} ${plural(config.deckIds.length, "колода", "колоды", "колод")}.` : "Конфигурация недоступна."}</p></div>{config ? <ConfidenceBadge value={config.dataSufficiency} /> : null}</header>
        <div className="fsrs-step-sequences">
          <StepSequence label="Шаги обучения" values={result.learningStepsSeconds || []} />
          <StepSequence label="Шаги переучивания" values={result.relearningStepsSeconds || []} />
          <MetricBlock label="Краткосрочный режим" value={result.shortTermMode === "fsrs" ? "Управляет FSRS" : "Заданы шаги"} caption="Текущая настройка пресета" accent="neutral" />
        </div>
      </section>
      <section className="statistics-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>Наблюдаемое краткосрочное поведение</h2><p>Каждый сценарий сохраняет собственный размер выборки и уровень достаточности.</p></div></header>
        <div className="statistics-table-wrap"><table className="statistics-table fsrs-scenarios-table"><thead><tr><th>Сценарий</th><th>Ответов</th><th>Удержание</th><th>Успешный интервал</th><th>Надёжность</th></tr></thead><tbody>{result.scenarios.map((item) => (
          <tr key={item.id}><th>{scenarioLabel(item.id)}</th><td>{formatNumber(item.sampleSize)}</td><td>{formatPercent(item.retention)}</td><td>{item.observedSuccessfulRangeSeconds ? formatRange(item.observedSuccessfulRangeSeconds) : "Недостаточно данных"}</td><td><ConfidenceBadge value={item.sufficiency} /></td></tr>
        ))}</tbody></table></div>
      </section>
      <section className={`fsrs-recommendation panel-surface ${hasRecommendation ? "is-ready" : ""}`}>
        <ShieldCheck size={22} /><div><span className="statistics-section-marker">Наблюдательная рекомендация</span><h2>{result.recommendation ? formatRange(result.recommendation.rangeSeconds) : "Диапазон пока недоступен"}</h2><p>{result.recommendation ? `Уверенность: ${sufficiencyLabel(result.recommendation.confidence)}. Это справочный вывод, а не оптимальное значение.` : "Нужна достаточная выборка ключевых сценариев."}</p></div><strong>Только чтение</strong>
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
        <div><span className="statistics-section-marker">Контролируемый эксперимент</span><h2>Сценарий нагрузки</h2><p>Измените предположения и сравните результат с текущей целью. Настройки Anki останутся без изменений.</p></div>
        <span className="fsrs-readonly-badge"><ShieldCheck size={15} /> Только чтение</span>
      </header>
      <div className="fsrs-simulator-baseline">
        <MetricBlock label="Выбранная область" value={selectedScope} caption={selectedGroup ? `Пресет «${selectedGroup.presetName}»` : "Выберите совместимый набор"} accent="neutral" />
        <MetricBlock label="Текущая цель" value={formatPercent(selectedGroup?.defaultDesiredRetention ?? null)} caption="До запуска сценария" accent="target" />
        <MetricBlock label="Горизонт" value={`${values.horizonDays} дней`} caption="Окно моделирования" accent="neutral" />
      </div>
      <form className="fsrs-simulator-form" onSubmit={(event) => { event.preventDefault(); if (!invalid && !disabled && status !== "loading") onRun(); }}>
        <label>Целевое удержание<div className="fsrs-input-with-unit"><input aria-label="Целевое удержание" type="number" min="0.75" max="0.99" step="0.01" value={finiteValue(values.desiredRetention)} onChange={(event) => setValues({ ...values, desiredRetention: Number(event.target.value) })} /><span>доля</span></div>{errors.desiredRetention ? <small className="fsrs-field-error">{errors.desiredRetention}</small> : <small>Например, 0,93 = 93%</small>}</label>
        <label>Горизонт<select aria-label="Горизонт симуляции" value={values.horizonDays} onChange={(event) => setValues({ ...values, horizonDays: Number(event.target.value) as 90 | 180 | 365 })}><option value="90">90 дней</option><option value="180">180 дней</option><option value="365">365 дней</option></select></label>
        <label>Дополнительные новые<div className="fsrs-input-with-unit"><input aria-label="Дополнительные новые карточки" type="number" min="0" max="100000" value={finiteValue(values.additionalNewCards)} onChange={(event) => setValues({ ...values, additionalNewCards: Number(event.target.value) })} /><span>карт.</span></div>{errors.additionalNewCards ? <small className="fsrs-field-error">{errors.additionalNewCards}</small> : null}</label>
        <label>Новых в день<div className="fsrs-input-with-unit"><input aria-label="Новых карточек в день" type="number" min="0" max="1000" value={finiteValue(values.newCardsPerDay)} onChange={(event) => setValues({ ...values, newCardsPerDay: Number(event.target.value) })} /><span>карт.</span></div>{errors.newCardsPerDay ? <small className="fsrs-field-error">{errors.newCardsPerDay}</small> : null}</label>
        <label>Лимит повторений<div className="fsrs-input-with-unit"><input aria-label="Максимум повторений в день" type="number" min="1" max="10000" value={finiteValue(values.maximumReviewsPerDay)} onChange={(event) => setValues({ ...values, maximumReviewsPerDay: Number(event.target.value) })} /><span>в день</span></div>{errors.maximumReviewsPerDay ? <small className="fsrs-field-error">{errors.maximumReviewsPerDay}</small> : null}</label>
        <button className="primary-button fsrs-run-scenario" type="submit" disabled={invalid || disabled || status === "loading"}>
          {status === "loading" ? <RefreshCw className="is-spinning" size={16} /> : <Play size={16} />}
          {status === "loading" ? "Рассчитываем…" : "Рассчитать сценарий"}
        </button>
      </form>
      {values.desiredRetention >= .97 ? <p className="fsrs-retention-warning"><AlertTriangle size={16} /> Значения около 100% обычно резко увеличивают нагрузку.</p> : null}
      {disabled ? <p className="fsrs-retention-warning"><AlertTriangle size={16} /> Для симуляции выберите одну совместимую конфигурацию или колоду.</p> : null}
    </section>
  );
}

function SimulatorView({ result }: { result: SimulationResult }) {
  return (
    <div className="statistics-section-stack" data-testid="fsrs-simulator-result">
      <InsightBanner icon={<Activity size={22} />} eyebrow="Разница сценария" title={`${signed(result.delta.reviewsPerDay)} повторений и ${signed(result.delta.minutesPerDay)} мин. в день`} tone="accent" badge={<span className="fsrs-readonly-badge"><ShieldCheck size={15} /> Только чтение</span>}>
        Цель меняется с {formatPercent(result.current.desiredRetention)} на {formatPercent(result.hypothetical.desiredRetention)}. Рост или снижение нагрузки не оценивается автоматически как хорошо или плохо.
      </InsightBanner>
      <section className="fsrs-scenario-comparison">
        <ScenarioColumn title="Текущая цель" scenario={result.current} />
        <span className="fsrs-scenario-arrow"><ArrowRight size={22} /></span>
        <ScenarioColumn title="Гипотетический сценарий" scenario={result.hypothetical} highlighted />
      </section>
      <section className="statistics-kpis compact four">
        <Kpi label="Δ повторений в день" value={signed(result.delta.reviewsPerDay)} accent="primary" />
        <Kpi label="Δ минут в день" value={signed(result.delta.minutesPerDay)} />
        <Kpi label="Пиковая нагрузка" value={formatNumber(result.hypothetical.peakReviews)} />
        <Kpi label="Накопленный хвост" value={formatNumber(result.hypothetical.backlog)} accent={result.hypothetical.backlog > 0 ? "warning" : "success"} />
      </section>
      <section className="statistics-panel statistics-chart-panel panel-surface">
        <header className="statistics-panel-header"><div><h2>Нагрузка по дням</h2><p>Текущая цель и гипотетический сценарий показаны на одной шкале повторений.</p></div></header>
        <WorkloadComparisonChart current={result.current.daily} hypothetical={result.hypothetical.daily} />
        <details className="statistics-data-disclosure"><summary>Таблица данных</summary><div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>День</th><th>Текущая цель</th><th>Сценарий</th></tr></thead><tbody>{result.hypothetical.daily.map((day, index) => <tr key={day.day}><th>{day.day}</th><td>{result.current.daily[index]?.reviews ?? "—"}</td><td>{day.reviews}</td></tr>)}</tbody></table></div></details>
      </section>
      <section className="fsrs-safety-statement panel-surface"><ShieldCheck size={22} /><div><h2>Симулятор работает только для чтения</h2><p>Он не меняет расписание, параметры колод и карточки в Anki. Результат остаётся оценкой при выбранных предположениях.</p></div></section>
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
      ))}</div> : <p className="statistics-empty">Для этой области распределение недоступно.</p>}
      <details className="statistics-data-disclosure"><summary>Таблица данных</summary><div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>Диапазон</th><th>Карточки</th><th>Доля</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><th>{row.label}</th><td>{row.count}</td><td>{formatPercent(row.percentage)}</td></tr>)}</tbody></table></div></details>
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
  return <article className={`fsrs-scenario-column panel-surface${highlighted ? " is-highlighted" : ""}`}><span>{title}</span><strong>{formatPercent(scenario.desiredRetention)}</strong><dl><div><dt>Повторений/день</dt><dd>{formatNumber(scenario.averageReviewsPerDay)}</dd></div><div><dt>Минут/день</dt><dd>{formatNumber(scenario.averageMinutesPerDay)}</dd></div><div><dt>Пик</dt><dd>{formatNumber(scenario.peakReviews)}</dd></div><div><dt>Хвост</dt><dd>{formatNumber(scenario.backlog)}</dd></div></dl></article>;
}

function StepSequence({ label, values }: { label: string; values: number[] }) {
  return <div className="fsrs-step-sequence"><span>{label}</span>{values.length ? <div>{values.map((value, index) => <span key={`${value}-${index}`}>{formatStep(value)}{index < values.length - 1 ? <ArrowRight size={15} /> : null}</span>)}</div> : <strong>Управляет FSRS</strong>}</div>;
}

function FsrsLoadingPanel() {
  return <section className="fsrs-loading-panel panel-surface" role="status"><RefreshCw className="is-spinning" size={22} /><div><h2>Обновляем анализ</h2><p>Результат предыдущей области скрыт, пока загружается новый запрос.</p></div></section>;
}

function FsrsErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <section className="fsrs-error-panel panel-surface" role="alert"><AlertTriangle size={22} /><div><h2>Расчёт не завершён</h2><p>{message || "Не удалось получить результат."}</p></div><button className="secondary-button" type="button" onClick={onRetry}><RefreshCw size={15} /> Повторить</button></section>;
}

function DisabledState() {
  return <section className="statistics-empty-page panel-surface fsrs-empty-state" data-testid="fsrs-disabled"><span><Brain size={30} /></span><h2>FSRS не включён</h2><p>Аналитика появится после включения FSRS в настройках Anki. Этот экран не подменяет FSRS другим алгоритмом.</p></section>;
}

function NoConfigurationState() {
  return <section className="statistics-empty-page panel-surface fsrs-empty-state" data-testid="fsrs-no-configuration"><span><Settings2 size={30} /></span><h2>Совместимая конфигурация не найдена</h2><p>FSRS включён, но для текущих обычных колод нет набора параметров, который можно безопасно анализировать.</p></section>;
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
  if (scope.kind === "dashboard") return "Текущая область dashboard";
  if (scope.kind === "all_collection") return capability.mixedConfiguration ? "Вся коллекция · несколько наборов" : "Вся коллекция";
  if (scope.kind === "configuration") return `Пресет «${capability.configurations.find((group) => group.id === scope.configurationId)?.presetName || "Недоступен"}»`;
  const deckId = "deckId" in scope ? scope.deckId : 0;
  for (const group of capability.configurations) {
    const index = group.deckIds.indexOf(deckId);
    if (index >= 0) return `Колода «${group.deckNames[index]}»`;
  }
  return "Колода недоступна";
}

function headingDescription(section: FsrsSection) {
  return ({
    overview: "Как FSRS работает для меня прямо сейчас?",
    memory: "В каком состоянии находится моя память сейчас?",
    calibration: "Совпадают ли прогнозы FSRS с фактическими ответами?",
    steps: "Соответствуют ли шаги обучения наблюдаемой краткосрочной памяти?",
    simulator: "Как может измениться нагрузка при другой целевой вероятности?",
  })[section];
}

function availabilityLabel(value: string) {
  return ({ enabled: "Доступно", disabled: "Выключено", insufficient_data: "Мало данных", partial_coverage: "Частичное покрытие", mixed_configuration: "Несколько наборов", unavailable: "Недоступно", error: "Ошибка" } as Record<string, string>)[value] || "Предварительно";
}

function sufficiencyLabel(value: string) {
  return ({ sufficient: "Достаточно", preliminary: "Предварительно", insufficient: "Мало данных", enabled: "Доступно", available: "Доступно", mixed_configuration: "Несколько наборов" } as Record<string, string>)[value] || "Предварительно";
}

function memoryLimitations(values: string[]) {
  const map: Record<string, string> = {
    snapshot_not_history: "Это снимок текущего состояния, а не историческая реконструкция.",
    current_memory_snapshot: "Оценка описывает текущее состояние памяти.",
    sparse_groups: "В малых группах вывод остаётся предварительным.",
    mixed_configuration: "Несовместимые конфигурации не объединяются.",
    unavailable_fields: "Часть полей может отсутствовать у карточек без валидного состояния FSRS.",
  };
  const mapped = values.map((value) => map[value] || value.replace(/_/g, " "));
  return mapped.length ? mapped : ["Это снимок текущего состояния, а не историческая реконструкция.", "Недоступные значения не заменяются нулями."];
}

function overrideLabel(group: FsrsConfigurationGroup) {
  if (!group.deckDesiredRetentionOverrides.length) return "Нет";
  return group.deckDesiredRetentionOverrides.map((override) => {
    const index = group.deckIds.indexOf(override.deckId);
    return `${group.deckNames[index] || "Колода"}: ${formatPercent(override.desiredRetention)}`;
  }).join("; ");
}

function periodLabel(value: string) {
  return ({ "30d": "30 дней", "90d": "90 дней", "180d": "180 дней", "1y": "1 год" } as Record<string, string>)[value] || value;
}

function formatNumber(value: number) { return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null) { return value == null ? "Нет данных" : `${formatNumber(value * 100)}%`; }
function formatTarget(value: { min: number; max: number } | null) { return !value ? "Нет данных" : value.min === value.max ? formatPercent(value.min) : `${formatPercent(value.min)}–${formatPercent(value.max)}`; }
function formatDays(value: number | null) { return value == null ? "Нет данных" : `${formatNumber(value)} дн.`; }
function formatStep(value: number) { return value < 3600 ? `${Math.round(value / 60)} мин` : `${formatNumber(value / 3600)} ч`; }
function formatRange(values: number[]) { return `${formatStep(values[0])}–${formatStep(values[1])}`; }
function signed(value: number) { return `${value > 0 ? "+" : ""}${formatNumber(value)}`; }
function finiteValue(value: number) { return Number.isFinite(value) ? value : ""; }
function plural(value: number, one: string, few: string, many: string) { const mod10 = value % 10; const mod100 = value % 100; return mod10 === 1 && mod100 !== 11 ? one : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? few : many; }
function scenarioLabel(value: string) { return ({ first_again: "Первый ответ: Снова", first_hard: "Первый ответ: Трудно", first_good: "Первый ответ: Хорошо", again_then_good: "Снова → Хорошо", good_then_again: "Хорошо → Снова", relearning: "Переучивание" } as Record<string, string>)[value] || value; }

export default FsrsStatisticsPage;
