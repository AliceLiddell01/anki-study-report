import { Brain, ExternalLink, Play, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { fetchFsrs, fsrsQueryKey } from "../lib/fsrsApi";
import { runReportAction } from "../lib/actionsApi";
import type { FsrsCapability, FsrsConfigurationGroup, FsrsQuery, FsrsResponse, FsrsScope, StudyReport } from "../types/report";
import type { LoadState } from "./HomePage";

export type FsrsSection = "overview" | "memory" | "calibration" | "steps" | "simulator";

const fsrsSections: Array<{ id: FsrsSection; label: string; path: string }> = [
  { id: "overview", label: "Обзор", path: "/stats/fsrs" },
  { id: "memory", label: "Состояние памяти", path: "/stats/fsrs/memory" },
  { id: "calibration", label: "Точность модели", path: "/stats/fsrs/calibration" },
  { id: "steps", label: "Шаги обучения", path: "/stats/fsrs/steps" },
  { id: "simulator", label: "Симулятор", path: "/stats/fsrs/simulator" },
];

const statisticsSections = [
  ["Обзор", "/stats"], ["Качество", "/stats/quality"], ["Нагрузка", "/stats/load"],
  ["Прогресс", "/stats/progress"], ["Колоды", "/stats/decks"], ["FSRS", "/stats/fsrs"],
];

type MemoryResult = {
  availability: string; studiedCards: number; estimatedRemembered: number; averageRetrievability: number | null;
  medianRetrievability: number | null; medianStabilityDays: number | null; medianDifficulty: number | null;
  cardsBelowOwnTarget: number; overdueCards: number; retrievabilityDistribution: Distribution[];
  stabilityDistribution: Distribution[]; difficultyDistribution: Distribution[]; limitations: string[];
};
type Distribution = { label: string; count: number; percentage: number | null };
type OverviewResult = { configurations: FsrsConfigurationGroup[]; mixedConfiguration: boolean; targetRetentionRange: { min: number; max: number } | null; estimatedRemembered: number; studiedCards: number; averageRetrievability: number | null; medianStabilityDays: number | null; actualRetention: number | null; dataSufficiency: string; insight: string };
type CalibrationResult = { configuration: FsrsConfigurationGroup; sampleSize: number; sufficiency: string; bins: Array<{ label: string; predicted: number | null; actual: number | null; sampleSize: number; sufficiency: string }>; rmseBins: number | null; hardIsRecall: boolean };
type StepsResult = { availability: string; configuration?: FsrsConfigurationGroup; scopeExpandedToPreset?: boolean; learningStepsSeconds?: number[]; relearningStepsSeconds?: number[]; shortTermMode?: string; scenarios: Array<{ id: string; sampleSize: number; retention: number | null; observedSuccessfulRangeSeconds: number[] | null; sufficiency: string }>; recommendation: { rangeSeconds: number[]; confidence: string; readOnly: true } | null };
type SimulationResult = { configuration: FsrsConfigurationGroup; current: SimulationScenario; hypothetical: SimulationScenario; delta: { reviewsPerDay: number; minutesPerDay: number }; native: true; readOnly: true };
type SimulationScenario = { desiredRetention: number; averageReviewsPerDay: number; averageMinutesPerDay: number; peakReviews: number; backlog: number; daily: Array<{ day: number; reviews: number; minutes: number }> };
type SimulatorInputs = { desiredRetention: number; horizonDays: 90 | 180 | 365; additionalNewCards: number; newCardsPerDay: number; maximumReviewsPerDay: number };

function FsrsStatisticsPage({ report, loadState, section }: { report: StudyReport | null; loadState: LoadState; section: FsrsSection }) {
  const capability = report?.statisticsHub?.fsrs;
  if (loadState !== "ready" || !capability) return <section className="statistics-empty-page panel-surface"><h1>FSRS</h1><p>FSRS-аналитика пока недоступна.</p></section>;
  return <FsrsReady capability={capability} section={section} />;
}

function FsrsReady({ capability, section }: { capability: FsrsCapability; section: FsrsSection }) {
  const initialConfig = capability.defaultConfigurationId;
  const defaultGroup = capability.configurations.find((item) => item.id === initialConfig) || capability.configurations[0];
  const [scope, setScope] = useState<FsrsScope>(section === "simulator" && defaultGroup?.deckDesiredRetentionOverrides.length ? { kind: "deck", deckId: defaultGroup.deckIds[0] } : capability.mixedConfiguration && initialConfig ? { kind: "configuration", configurationId: initialConfig } : { kind: "all_collection" });
  const [period, setPeriod] = useState<"30d" | "90d" | "180d" | "1y">("90d");
  const [response, setResponse] = useState<FsrsResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState("");
  const [simulation, setSimulation] = useState({ desiredRetention: 0.93, horizonDays: 180 as 90 | 180 | 365, additionalNewCards: 0, newCardsPerDay: 20, maximumReviewsPerDay: 500 });
  const cache = useRef(new Map<string, FsrsResponse>());
  const sequence = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const operation = section === "simulator" ? "simulate" : section;
  const explicit = section === "calibration" || section === "simulator";
  const query = useMemo<FsrsQuery>(() => ({ operation, scope, period, ...(section === "simulator" ? { simulation } : {}) }), [operation, scope, period, section, simulation]);

  useEffect(() => {
    sequence.current += 1;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setResponse(null); setError(""); setStatus(explicit ? "idle" : "loading");
    if (explicit) return;
    void load(query);
    return () => activeRequest.current?.abort();
    // query identity is represented by the primitive dependencies above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, scope, period]);

  async function load(nextQuery: FsrsQuery) {
    const key = fsrsQueryKey(nextQuery);
    if (cache.current.has(key)) { setResponse(cache.current.get(key)!); setStatus("ready"); return; }
    activeRequest.current?.abort();
    const current = ++sequence.current;
    const controller = new AbortController();
    activeRequest.current = controller;
    setStatus("loading"); setError("");
    try {
      const next = await fetchFsrs(nextQuery, controller.signal);
      if (current !== sequence.current) return;
      cache.current.set(key, next); setResponse(next); setStatus("ready");
    } catch (caught) {
      if (current !== sequence.current || (caught as Error).name === "AbortError") return;
      setError((caught as Error).message); setStatus("error");
    } finally {
      if (current === sequence.current) activeRequest.current = null;
    }
  }

  const deckForAction = capability.configurations.find((item) => item.id === (scope.kind === "configuration" ? scope.configurationId : initialConfig))?.deckIds[0] ?? capability.configurations[0]?.deckIds[0];
  const openOptions = () => deckForAction ? runReportAction("open-deck-options", { deckId: deckForAction }).then((result) => { if (!result.ok) setError(result.error || "Не удалось открыть настройки колоды."); }) : undefined;

  return <div className="statistics-shell fsrs-shell" data-testid="fsrs-page" data-fsrs-section={section}>
    <StatisticsSidebar />
    <div className="statistics-content">
      <header className="statistics-header statistics-page-surface"><div><span className="statistics-section-marker">Личный аналитический центр</span><h1>{section === "overview" ? "FSRS" : fsrsSections.find((item) => item.id === section)?.label}</h1><p>{headingDescription(section)}</p></div><button className="secondary-button" type="button" onClick={openOptions}><ExternalLink size={16} /> Открыть настройки колоды</button></header>
      <nav className="fsrs-local-nav" aria-label="Разделы FSRS">{fsrsSections.map((item) => <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>{item.label}</a>)}</nav>
      {!capability.enabled ? <DisabledState /> : <>
        <FsrsQueryBar capability={capability} scope={scope} setScope={setScope} period={period} setPeriod={setPeriod} />
        {capability.mixedConfiguration && scope.kind !== "configuration" && section !== "overview" && section !== "memory" ? <Notice title="Несколько наборов настроек">Для точной оценки выберите один совместимый набор настроек.</Notice> : null}
        {explicit && status === "idle" ? <section className="statistics-insight-card panel-surface" data-testid={`fsrs-${section}-idle`}><Brain size={22} /><div><h2>{section === "simulator" ? "Расчёт запускается только по вашей команде" : "Оценка строится по запросу"}</h2><p>Тяжёлая операция не запускается при каждом открытии маршрута.</p></div></section> : null}
        {section === "simulator" ? <SimulatorControls values={simulation} setValues={setSimulation} onRun={() => void load(query)} disabled={status === "loading"} /> : null}
        {section === "calibration" && status === "idle" ? <button className="primary-button fsrs-calculate" type="button" onClick={() => void load(query)}><Play size={16} /> Рассчитать точность</button> : null}
        {status === "loading" ? <div className="statistics-loading" role="status">Выполняем read-only расчёт…</div> : null}
        {status === "error" ? <div className="statistics-error" role="alert"><span>{error}</span><button onClick={() => void load(query)}><RefreshCw size={15} /> Повторить</button></div> : null}
        {response?.operation === operation ? <FsrsResult section={section} result={response.result} /> : null}
      </>}
    </div>
  </div>;
}

function StatisticsSidebar() { return <aside className="statistics-sidebar" data-testid="statistics-sidebar"><div className="statistics-sidebar-heading"><span className="statistics-sidebar-icon"><Brain size={18} /></span><div><strong>Статистика</strong><span>Периоды и сравнения</span></div></div><nav aria-label="Разделы статистики">{statisticsSections.map(([label, path]) => <a key={path} href={`#${path}`} aria-current={path === "/stats/fsrs" ? "page" : undefined}>{label}</a>)}</nav></aside>; }

function FsrsQueryBar({ capability, scope, setScope, period, setPeriod }: { capability: FsrsCapability; scope: FsrsScope; setScope: (scope: FsrsScope) => void; period: string; setPeriod: (period: "30d" | "90d" | "180d" | "1y") => void }) {
  const value = scope.kind === "configuration" ? scope.configurationId : scope.kind === "deck" ? `deck:${scope.deckId}` : scope.kind;
  return <section className="statistics-query-surface" aria-label="Параметры FSRS"><div className="statistics-controls"><label>Область<select value={value} onChange={(event) => { const next = event.target.value; setScope(next.startsWith("cfg-") ? { kind: "configuration", configurationId: next } : next.startsWith("deck:") ? { kind: "deck", deckId: Number(next.slice(5)) } : { kind: next as "dashboard" | "all_collection" }); }}><option value="dashboard">Текущая область</option><option value="all_collection">Вся коллекция</option>{capability.configurations.map((group) => <option key={group.id} value={group.id}>Набор: {group.presetName}</option>)}{capability.configurations.flatMap((group) => group.deckIds.map((deckId, index) => <option key={`deck:${deckId}`} value={`deck:${deckId}`}>Колода: {group.deckNames[index]}</option>))}</select></label><label>Период<select value={period} onChange={(event) => setPeriod(event.target.value as "30d" | "90d" | "180d" | "1y")}><option value="30d">30 дней</option><option value="90d">90 дней</option><option value="180d">180 дней</option><option value="1y">1 год</option></select></label><span className={`statistics-confidence-badge is-${capability.availability}`}>{availabilityLabel(capability.availability)}</span></div></section>;
}

function FsrsResult({ section, result }: { section: FsrsSection; result: Record<string, unknown> }) {
  if (section === "overview") return <OverviewView result={result as unknown as OverviewResult} />;
  if (section === "memory") return <MemoryView result={result as unknown as MemoryResult} />;
  if (section === "calibration") return <CalibrationView result={result as unknown as CalibrationResult} />;
  if (section === "steps") return <StepsView result={result as unknown as StepsResult} />;
  return <SimulatorView result={result as unknown as SimulationResult} />;
}

function OverviewView({ result }: { result: OverviewResult }) { const target = result.targetRetentionRange; return <div className="statistics-section-stack" data-testid="fsrs-overview"><Notice title="Как сейчас работает FSRS">{result.insight}</Notice><section className="statistics-kpis"><Kpi label="Оценка запомненного" value={formatNumber(result.estimatedRemembered)} caption={`Изучено хотя бы раз: ${formatNumber(result.studiedCards)}`} /><Kpi label="Средняя вероятность воспоминания" value={formatPercent(result.averageRetrievability)} /><Kpi label="Медианная стабильность" value={formatDays(result.medianStabilityDays)} /><Kpi label="Фактическое удержание" value={formatPercent(result.actualRetention)} caption={result.dataSufficiency === "insufficient" ? "Пока мало данных" : undefined} /><Kpi label="Целевое удержание" value={target ? target.min === target.max ? formatPercent(target.min) : `${formatPercent(target.min)}–${formatPercent(target.max)}` : "Нет данных"} /></section><section className="statistics-chart-panel panel-surface"><h2>Наборы настроек</h2><p>Соответствуют пресетам параметров Anki; несовместимые параметры не усредняются.</p><table><thead><tr><th>Набор настроек</th><th>Карточки</th><th>Состояние памяти</th><th>Цель</th></tr></thead><tbody>{result.configurations.map((group) => <tr key={group.id}><td>{group.presetName}</td><td>{formatNumber(group.cardCount)}</td><td>{formatNumber(group.reviewedCardCount)}</td><td>{formatPercent(group.defaultDesiredRetention)}</td></tr>)}</tbody></table></section></div>; }

function MemoryView({ result }: { result: MemoryResult }) { return <div className="statistics-section-stack" data-testid="fsrs-memory"><Notice title={`Вероятно помните сейчас ${formatNumber(result.estimatedRemembered)} карточек`}>Изучено хотя бы раз: {formatNumber(result.studiedCards)}. Это ожидаемая оценка, а не список гарантированно известных карточек.</Notice><section className="statistics-kpis"><Kpi label="Средняя вероятность" value={formatPercent(result.averageRetrievability)} /><Kpi label="Медианная вероятность" value={formatPercent(result.medianRetrievability)} /><Kpi label="Ниже своей цели" value={formatNumber(result.cardsBelowOwnTarget)} /><Kpi label="Просрочено" value={formatNumber(result.overdueCards)} /><Kpi label="Медианная стабильность" value={formatDays(result.medianStabilityDays)} /></section><DistributionPanel title="Вероятность воспоминания" description="Текущая вероятность успешного воспоминания" rows={result.retrievabilityDistribution} /><DistributionPanel title="Стабильность памяти" description="Время снижения вероятности воспоминания со 100% до 90%" rows={result.stabilityDistribution} /><DistributionPanel title="Сложность по модели" description="Показатель FSRS, влияющий на скорость роста интервалов" rows={result.difficultyDistribution} /><p className="statistics-footnote">Снимок текущего состояния; историческая реконструкция не выполняется.</p></div>; }

function CalibrationView({ result }: { result: CalibrationResult }) { return <div className="statistics-section-stack" data-testid="fsrs-calibration"><Notice title={result.sufficiency === "insufficient" ? "Данных пока недостаточно" : "Прогноз и фактические ответы сопоставлены"}>FSRS считает «Трудно» успешным воспоминанием. Если ответ не был вспомнен, используется «Снова».</Notice><section className="statistics-chart-panel panel-surface"><h2>Прогноз и фактическое удержание</h2><p>Диагональ 1:1 — идеальное совпадение; разреженные интервалы не трактуются как надёжные.</p><div className="fsrs-calibration-plot" role="img" aria-label="Точность модели по интервалам вероятности">{result.bins.map((bin) => <div key={bin.label} style={{ height: `${Math.max(4, (bin.actual || 0) * 100)}%` }} title={`${bin.label}: ${formatPercent(bin.actual)}`}><span>{bin.label}</span></div>)}</div><table><thead><tr><th>Прогноз</th><th>Фактически</th><th>Ответов</th><th>Статус</th></tr></thead><tbody>{result.bins.map((bin) => <tr key={bin.label}><td>{formatPercent(bin.predicted)}</td><td>{formatPercent(bin.actual)}</td><td>{bin.sampleSize}</td><td>{bin.sufficiency}</td></tr>)}</tbody></table><details><summary>Технические показатели</summary><p>RMSE по интервалам: {result.rmseBins == null ? "Нет данных" : formatPercent(result.rmseBins)}</p></details></section></div>; }

function StepsView({ result }: { result: StepsResult }) { if (result.availability === "mixed_configuration") return <Notice title="Выберите один набор настроек">Шаги разных наборов не объединяются.</Notice>; return <div className="statistics-section-stack" data-testid="fsrs-steps"><Notice title="Область анализа расширена">Для надёжной оценки используются все обычные колоды с этим набором настроек.</Notice><section className="statistics-kpis"><Kpi label="Шаги обучения" value={formatSteps(result.learningStepsSeconds || [])} /><Kpi label="Шаги переучивания" value={formatSteps(result.relearningStepsSeconds || [])} /><Kpi label="Краткосрочный режим" value={result.shortTermMode === "fsrs" ? "Управляет FSRS" : "Заданы шаги"} /></section><section className="statistics-chart-panel panel-surface"><h2>Наблюдаемая краткосрочная память</h2><table><thead><tr><th>Сценарий</th><th>Ответов</th><th>Удержание</th><th>Наблюдаемый диапазон</th></tr></thead><tbody>{result.scenarios.map((item) => <tr key={item.id}><td>{scenarioLabel(item.id)}</td><td>{item.sampleSize}</td><td>{formatPercent(item.retention)}</td><td>{item.observedSuccessfulRangeSeconds ? formatRange(item.observedSuccessfulRangeSeconds) : "Недостаточно данных"}</td></tr>)}</tbody></table>{result.recommendation ? <p><strong>Рекомендуемый наблюдаемый диапазон:</strong> {formatRange(result.recommendation.rangeSeconds)}. Только справочная оценка; изменения не применяются.</p> : <p>Для рекомендации ключевым сценариям требуется не менее 100 наблюдений.</p>}</section></div>; }

function SimulatorControls({ values, setValues, onRun, disabled }: { values: SimulatorInputs; setValues: (values: SimulatorInputs) => void; onRun: () => void; disabled: boolean }) { return <section className="statistics-query-surface fsrs-simulator-controls"><div className="statistics-controls"><label>Целевое удержание<input type="number" min="0.75" max="0.99" step="0.01" value={values.desiredRetention} onChange={(e) => setValues({ ...values, desiredRetention: Number(e.target.value) })} /></label><label>Горизонт<select value={values.horizonDays} onChange={(e) => setValues({ ...values, horizonDays: Number(e.target.value) as 90 | 180 | 365 })}><option value="90">90 дней</option><option value="180">180 дней</option><option value="365">365 дней</option></select></label><label>Доп. новые<input type="number" min="0" max="100000" value={values.additionalNewCards} onChange={(e) => setValues({ ...values, additionalNewCards: Number(e.target.value) })} /></label><label>Новых в день<input type="number" min="0" max="1000" value={values.newCardsPerDay} onChange={(e) => setValues({ ...values, newCardsPerDay: Number(e.target.value) })} /></label><label>Максимум повторений<input type="number" min="1" max="10000" value={values.maximumReviewsPerDay} onChange={(e) => setValues({ ...values, maximumReviewsPerDay: Number(e.target.value) })} /></label><button className="primary-button" type="button" onClick={onRun} disabled={disabled}><Play size={16} /> Рассчитать</button></div><p>Значения около 100% резко увеличивают нагрузку. Симулятор ничего не применяет.</p></section>; }

function SimulatorView({ result }: { result: SimulationResult }) { return <div className="statistics-section-stack" data-testid="fsrs-simulator-result"><Notice title={`Переход с ${formatPercent(result.current.desiredRetention)} на ${formatPercent(result.hypothetical.desiredRetention)}`}>{signed(result.delta.reviewsPerDay)} повторения в день; {signed(result.delta.minutesPerDay)} минуты в день. Больше или меньше не оценивается как хорошо/плохо.</Notice><section className="statistics-kpis"><Kpi label="Повторений в день" value={formatNumber(result.hypothetical.averageReviewsPerDay)} /><Kpi label="Минут в день" value={formatNumber(result.hypothetical.averageMinutesPerDay)} /><Kpi label="Пиковая нагрузка" value={formatNumber(result.hypothetical.peakReviews)} /><Kpi label="Накопленный хвост" value={formatNumber(result.hypothetical.backlog)} /></section><section className="statistics-chart-panel panel-surface"><h2>Ежедневная нагрузка</h2><div className="fsrs-workload-chart" role="img" aria-label="Симулированные повторения по дням">{result.hypothetical.daily.slice(0, 120).map((day) => <i key={day.day} style={{ height: `${Math.max(2, day.reviews / Math.max(1, result.hypothetical.peakReviews) * 100)}%` }} title={`День ${day.day}: ${day.reviews}`} />)}</div><p>Нативная read-only симуляция Anki; расписание и настройки не изменялись.</p></section></div>; }

function DistributionPanel({ title, description, rows }: { title: string; description: string; rows: Distribution[] }) { const max = Math.max(1, ...rows.map((row) => row.count)); return <section className="statistics-chart-panel panel-surface"><h2>{title}</h2><p>{description}</p><div className="fsrs-distribution" role="img" aria-label={title}>{rows.map((row) => <div key={row.label}><span>{row.label}</span><i style={{ width: `${row.count / max * 100}%` }} /><strong>{formatNumber(row.count)}</strong></div>)}</div><table><thead><tr><th>Диапазон</th><th>Карточки</th><th>Доля</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><td>{row.label}</td><td>{row.count}</td><td>{formatPercent(row.percentage)}</td></tr>)}</tbody></table></section>; }
function Notice({ title, children }: { title: string; children: ReactNode }) { return <section className="statistics-insight-card panel-surface"><Brain size={22} /><div><h2>{title}</h2><p>{children}</p></div></section>; }
function Kpi({ label, value, caption }: { label: string; value: string; caption?: string }) { return <article className="statistics-kpi-card"><span>{label}</span><strong>{value}</strong>{caption ? <small>{caption}</small> : null}</article>; }
function DisabledState() { return <section className="statistics-empty-page panel-surface" data-testid="fsrs-disabled"><Brain size={28} /><h2>FSRS не включён</h2><p>Этот раздел станет доступен после включения FSRS в Anki.</p></section>; }
function headingDescription(section: FsrsSection) { return ({ overview: "Состояние памяти, точность модели и ожидаемая нагрузка.", memory: "В каком состоянии находятся знания сейчас?", calibration: "Совпадают ли прогнозы FSRS с фактическими ответами?", steps: "Подходят ли шаги к наблюдаемой краткосрочной памяти?", simulator: "Как изменится нагрузка при другой целевой вероятности?" })[section]; }
function availabilityLabel(value: string) { return ({ enabled: "Доступно", disabled: "Выключено", insufficient_data: "Мало данных", mixed_configuration: "Несколько наборов" } as Record<string, string>)[value] || "Предварительно"; }
function formatNumber(value: number) { return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null) { return value == null ? "Нет данных" : `${formatNumber(value * 100)}%`; }
function formatDays(value: number | null) { return value == null ? "Нет данных" : `${formatNumber(value)} дн.`; }
function formatSteps(values: number[]) { return values.length ? values.map((value) => value < 3600 ? `${Math.round(value / 60)} мин` : `${formatNumber(value / 3600)} ч`).join(", ") : "Управляет FSRS"; }
function formatRange(values: number[]) { return `${Math.round(values[0] / 60)}–${Math.round(values[1] / 60)} мин`; }
function signed(value: number) { return `${value > 0 ? "+" : ""}${formatNumber(value)}`; }
function scenarioLabel(value: string) { return ({ first_again: "Первый ответ: Снова", first_hard: "Первый ответ: Трудно", first_good: "Первый ответ: Хорошо", again_then_good: "Снова → Хорошо", good_then_again: "Хорошо → Снова", relearning: "Переучивание" } as Record<string, string>)[value] || value; }

export default FsrsStatisticsPage;
