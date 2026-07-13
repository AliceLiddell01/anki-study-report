import {
  BarChart3,
  Check,
  ExternalLink,
  Info,
  RefreshCw,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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

const sections: Array<{ id: StatisticsSection; label: string; path: string; description: string }> = [
  { id: "overview", label: "Обзор", path: "/stats", description: "Что изменилось за выбранный период" },
  { id: "quality", label: "Качество", path: "/stats/quality", description: "Насколько стабильно проходят ответы" },
  { id: "load", label: "Нагрузка", path: "/stats/load", description: "Сколько работы было и ожидается" },
  { id: "progress", label: "Прогресс", path: "/stats/progress", description: "Как растёт изученный материал" },
  { id: "decks", label: "Колоды", path: "/stats/decks", description: "Чем колоды отличаются за период" },
];

const periodLabels: Record<StatisticsPeriod, string> = {
  "7d": "Последние 7 дней",
  "30d": "Последние 30 дней",
  "90d": "Последние 90 дней",
  "1y": "Последний год",
  all: "Всё время",
};

function StatisticsPage({ report, loadState, section }: { report: StudyReport | null; loadState: LoadState; section: StatisticsSection }) {
  const hub = report?.statisticsHub;
  if (loadState !== "ready" || !hub) return <StatisticsUnavailable loadState={loadState} />;
  return <StatisticsReady hub={hub} section={section} />;
}

function StatisticsReady({ hub, section }: { hub: StatisticsHubModel; section: StatisticsSection }) {
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
        setError(caught.message || "Не удалось обновить статистику.");
      });
    return () => controller.abort();
  }, [query, retryNonce]);

  const currentSection = sections.find((item) => item.id === section)!;
  const updateQuery = (patch: Partial<StatisticsQuery>) => setQuery((current) => ({ ...current, ...patch }));
  const openNativeStats = async () => {
    const response = await runReportAction("open-native-stats", {});
    if (!response.ok) setError(response.error || "Не удалось открыть статистику Anki.");
  };

  return (
    <div className="statistics-shell" data-testid="statistics-page" data-statistics-section={section}>
      <StatisticsSidebar section={section} />
      <div className="statistics-content">
        <header className="statistics-header statistics-page-surface" data-testid="statistics-header">
          <div>
            <span className="statistics-section-marker">Личный аналитический центр</span>
            <h1>{section === "overview" ? "Статистика" : currentSection.label}</h1>
            <p>{currentSection.description}</p>
          </div>
          <button type="button" className="secondary-button" onClick={openNativeStats}>
            <ExternalLink size={16} aria-hidden="true" /> Открыть статистику Anki
          </button>
        </header>

        <StatisticsQueryBar hub={hub} query={query} result={result} updateQuery={updateQuery} />

        <div className="statistics-status-slot" aria-live="polite">
          {status === "loading" ? <div className="statistics-loading" role="status">Обновляем данные…</div> : null}
          {status === "error" || error ? (
            <div className="statistics-error" role="alert">
              <span>{error || "Не удалось обновить статистику."}</span>
              {status === "error" ? <button type="button" onClick={() => setRetryNonce((value) => value + 1)}><RefreshCw size={15} /> Повторить</button> : null}
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
  return (
    <aside className="statistics-sidebar" data-testid="statistics-sidebar">
      <div className="statistics-sidebar-heading">
        <span className="statistics-sidebar-icon"><BarChart3 size={18} aria-hidden="true" /></span>
        <div><strong>Статистика</strong><span>Периоды и сравнения</span></div>
      </div>
      <nav aria-label="Разделы статистики">
        {sections.map((item) => <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>{item.label}</a>)}
        <a href="#/stats/fsrs">FSRS</a>
      </nav>
    </aside>
  );
}

function StatisticsQueryBar({ hub, query, result, updateQuery }: { hub: StatisticsHubModel; query: StatisticsQuery; result: StatisticsResult; updateQuery: (patch: Partial<StatisticsQuery>) => void }) {
  const scopeKind = query.scope.kind;
  const selectedDeckId = scopeKind === "single_deck" ? query.scope.deckId : hub.deckOptions[0]?.deckId;
  return (
    <section className="statistics-query-surface" aria-label="Параметры статистики" data-testid="statistics-query-bar">
      <div className="statistics-controls">
        <label>Область
          <select value={scopeKind} onChange={(event) => {
            const kind = event.target.value;
            if (kind === "single_deck" && hub.deckOptions[0]) updateQuery({ scope: { kind, deckId: hub.deckOptions[0].deckId, mode: "subtree" } });
            else updateQuery({ scope: { kind: kind as "dashboard" | "all_collection" } });
          }}>
            <option value="dashboard">Текущая область</option>
            <option value="all_collection">Вся коллекция</option>
            <option value="single_deck">Одна колода</option>
          </select>
        </label>
        {scopeKind === "single_deck" ? <>
          <label>Колода
            <select value={selectedDeckId} onChange={(event) => updateQuery({ scope: { kind: "single_deck", deckId: Number(event.target.value), mode: query.scope.kind === "single_deck" ? query.scope.mode : "subtree" } })}>
              {hub.deckOptions.map((deck) => <option value={deck.deckId} key={deck.deckId}>{deck.fullName}</option>)}
            </select>
          </label>
          <fieldset className="statistics-segmented"><legend>Режим колоды</legend>
            {(["subtree", "direct"] as const).map((mode) => <label key={mode}><input type="radio" name="deck-mode" checked={query.scope.kind === "single_deck" && query.scope.mode === mode} onChange={() => updateQuery({ scope: { kind: "single_deck", deckId: selectedDeckId!, mode } })} />{mode === "subtree" ? "С подколодами" : "Только напрямую"}</label>)}
          </fieldset>
        </> : null}
        <label>Период
          <select value={query.period} onChange={(event) => updateQuery({ period: event.target.value as StatisticsPeriod, comparison: event.target.value === "all" ? false : query.comparison })}>
            {Object.entries(periodLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
        <label>Детализация
          <select value={query.granularity} onChange={(event) => updateQuery({ granularity: event.target.value as StatisticsQuery["granularity"] })}>
            <option value="auto">Автоматически</option><option value="day">По дням</option><option value="week">По неделям</option><option value="month">По месяцам</option>
          </select>
        </label>
        <label className="statistics-checkbox"><input type="checkbox" checked={query.comparison} disabled={query.period === "all"} onChange={(event) => updateQuery({ comparison: event.target.checked })} /><span>Сравнить периоды<small>{query.period === "all" ? "Для всего времени нет предыдущего периода" : "Показывать изменения KPI"}</small></span></label>
      </div>
      <CoverageNotice result={result} />
    </section>
  );
}

function Overview({ result }: { result: StatisticsResult }) {
  const kpi = result.overview.kpis;
  const comparison = result.overview.comparison;
  return <div className="statistics-section-stack" data-testid="statistics-overview">
    <InsightCard insights={result.overview.insights} confidence={result.overview.confidence} />
    <section className="statistics-kpis" aria-label="Ключевые показатели" data-testid="statistics-kpi-grid">
      <KpiCard label="Повторения" value={formatNumber(kpi.reviews)} delta={deltaModel(comparison, "reviews")} color="reviews" />
      <KpiCard label="Время учёбы" value={formatDuration(kpi.studySeconds)} delta={deltaModel(comparison, "studySeconds")} color="study-time" caption="Оценка по времени ответов" />
      <KpiCard label="Успешность" value={formatPercent(kpi.successRate)} delta={deltaModel(comparison, "successRate", "percentage-points")} color="success" />
      <KpiCard label="Новые карточки" value={formatNumber(kpi.introducedCards)} delta={deltaModel(comparison, "introducedCards")} color="introduced" caption="Впервые изученные" />
      <KpiCard label="Активные дни" value={formatNumber(kpi.activeDays)} delta={deltaModel(comparison, "activeDays")} color="reviews" />
      <KpiCard label="Средний ответ" value={kpi.averageAnswerSeconds == null ? "Нет данных" : `${kpi.averageAnswerSeconds.toFixed(1)} с`} delta={deltaModel(comparison, "averageAnswerSeconds", "seconds")} color="study-time" />
    </section>
    <div className="statistics-analytical-grid primary-secondary">
      <StatisticsChartPanel title="Динамика занятий" description="Количество ответов по интервалам" summary={seriesSummary(result.overview.series, "reviews", "Повторения")} points={result.overview.series} metrics={[{ key: "reviews", label: "Повторения", color: "reviews" }]} kind="line" testId="stats-overview-reviews" />
      <StatisticsChartPanel title="Время учёбы" description="Оценка времени отдельно от числа ответов" summary={seriesSummary(result.overview.series, "studySeconds", "Время учёбы")} points={result.overview.series} metrics={[{ key: "studySeconds", label: "Время, мин", color: "study-time", format: "duration" }]} kind="line" compact testId="stats-overview-time" />
    </div>
    <div className="statistics-analytical-grid">
      <StatisticsChartPanel title="Успешность" description="Доля ответов «Трудно», «Хорошо» и «Легко»" summary={seriesSummary(result.overview.series, "successRate", "Успешность")} points={result.overview.series} metrics={[{ key: "successRate", label: "Успешность", color: "success", format: "percent" }]} kind="line" testId="stats-overview-success" />
      <StatisticsChartPanel title="Средний ответ" description="Среднее время ответа — отдельная шкала" summary={seriesSummary(result.overview.series, "averageAnswerSeconds", "Средний ответ")} points={result.overview.series} metrics={[{ key: "averageAnswerSeconds", label: "Средний ответ", color: "study-time", format: "seconds" }]} kind="line" compact />
      <StatisticsChartPanel title="Новые карточки" description="Фактические первые изучения" summary={seriesSummary(result.overview.series, "introducedCards", "Новые карточки")} points={result.overview.series} metrics={[{ key: "introducedCards", label: "Новые карточки", color: "introduced" }]} kind="bar" compact testId="stats-overview-introduced" />
    </div>
  </div>;
}

function Quality({ result }: { result: StatisticsResult }) {
  const quality = result.quality;
  const ratingTotal = Object.values(quality.ratings).reduce((sum, value) => sum + value, 0);
  return <div className="statistics-section-stack" data-testid="statistics-quality">
    <InsightCard title="Стабильность ответов" text={quality.confidence === "insufficient" ? "Данных пока мало: значения показаны без сильного вывода о тренде." : `Успешность за период — ${formatPercent(quality.successRate)} при ${formatNumber(quality.pass + quality.fail)} ответах.`} confidence={quality.confidence} />
    <section className="statistics-kpis compact four" aria-label="Показатели качества">
      <KpiCard label="Успешность" value={formatPercent(quality.successRate)} color="success" />
      <KpiCard label="Истинное удержание" value={formatPercent(quality.trueRetention.overall)} color="mature" caption="Первый подход к карточке за день" />
      <KpiCard label="Средний ответ" value={result.overview.kpis.averageAnswerSeconds == null ? "Нет данных" : `${result.overview.kpis.averageAnswerSeconds.toFixed(1)} с`} color="study-time" />
      <KpiCard label="Объём выборки" value={formatNumber(quality.pass + quality.fail)} color="reviews" caption={confidenceLabel(quality.confidence)} />
    </section>
    <div className="statistics-analytical-grid primary-secondary">
      <StatisticsChartPanel title="Успешность по времени" description="Процент успешных ответов без смешения с объёмом" summary={seriesSummary(quality.series, "successRate", "Успешность")} points={quality.series} metrics={[{ key: "successRate", label: "Успешность", color: "success", format: "percent" }]} kind="line" testId="stats-quality-success" />
      <StatisticsChartPanel title="Объём ответов" description="Успешные и повторные попытки в общей нагрузке" summary={`${formatNumber(quality.pass)} успешных и ${formatNumber(quality.fail)} повторных попыток.`} points={quality.series} metrics={[{ key: "pass", label: "Успешно", color: "good", stackId: "answers" }, { key: "fail", label: "Снова", color: "again", stackId: "answers" }]} kind="stacked" compact testId="stats-quality-volume" />
    </div>
    <section className="statistics-analytical-grid">
      <StatisticsPanel title="Кнопки ответа" description={`${formatNumber(ratingTotal)} ответов · доли от общего числа`} testId="stats-answer-buttons">
        <AnswerDistribution ratings={quality.ratings} />
      </StatisticsPanel>
      <StatisticsPanel title="Истинное удержание" description="Первый подход к карточке за локальный день" testId="stats-retention-panel">
        <RetentionBreakdown result={quality.trueRetention} confidence={quality.confidence} />
      </StatisticsPanel>
    </section>
  </div>;
}

function Load({ result }: { result: StatisticsResult }) {
  const load = result.load;
  const futurePoints = load.futureDue.map((row) => ({ ...row, key: String(row.dayOffset), label: row.dayOffset === 0 ? "Сегодня" : `Через ${row.dayOffset} дн.` }));
  return <div className="statistics-section-stack" data-testid="statistics-load">
    <InsightCard title="Текущая и будущая нагрузка" text={load.overdue ? `Сейчас просрочено ${formatNumber(load.overdue)} карточек. Ближайшие сроки показаны отдельно от прошлой работы.` : "Просроченных карточек нет. Ближайшие сроки показаны отдельно от прошлой работы."} />
    <section className="statistics-kpis compact four" aria-label="Показатели нагрузки">
      <KpiCard label="Просрочено сейчас" value={formatNumber(load.overdue)} color="again" />
      <KpiCard label="Следующие 7 дней" value={formatNumber(futureDueTotal(load, 7))} color="review" />
      <KpiCard label="Следующие 30 дней" value={formatNumber(futureDueTotal(load, 30))} color="learning" />
      <KpiCard label="Средняя нагрузка активного дня" value={load.averageActiveDayReviews == null ? "Нет данных" : formatNumber(load.averageActiveDayReviews)} color="reviews" caption="Повторений в активный день" />
    </section>
    <div className="statistics-definition-line"><Info size={15} aria-hidden="true" /><span><strong>Ежедневная нагрузка: {load.dailyLoad.toFixed(2)}</strong> — долгосрочная оценка по текущим интервалам.</span><details><summary>Как считается</summary><p>Сумма обратных текущих интервалов карточек; это не число карточек на сегодня.</p></details></div>
    <section className="statistics-panel-group" aria-labelledby="past-load-title">
      <header><h2 id="past-load-title">Прошлая нагрузка</h2><p>Единицы разделены на самостоятельные малые графики.</p></header>
      <div className="statistics-analytical-grid thirds">
        <StatisticsChartPanel title="Повторения" description="Количество ответов" summary={seriesSummary(load.past, "reviews", "Повторения")} points={load.past} metrics={[{ key: "reviews", label: "Повторения", color: "reviews" }]} kind="line" compact testId="stats-load-reviews" />
        <StatisticsChartPanel title="Время" description="Оценка времени ответов" summary={seriesSummary(load.past, "studySeconds", "Время")} points={load.past} metrics={[{ key: "studySeconds", label: "Время, мин", color: "study-time", format: "duration" }]} kind="line" compact testId="stats-load-time" />
        <StatisticsChartPanel title="Новые карточки" description="Первые изучения" summary={seriesSummary(load.past, "introducedCards", "Новые карточки")} points={load.past} metrics={[{ key: "introducedCards", label: "Новые карточки", color: "introduced" }]} kind="bar" compact testId="stats-load-new" />
      </div>
    </section>
    <StatisticsChartPanel title="Будущая нагрузка" description="Текущее расписание по типам очереди" summary={futurePoints.length ? `${futurePoints.length} сроков в пределах 90 дней; просроченные карточки не включены.` : "В ближайшие 90 дней карточек нет."} points={futurePoints} metrics={[{ key: "learning", label: "Изучение", color: "learning", stackId: "due" }, { key: "review", label: "Повторение", color: "review", stackId: "due" }, { key: "relearning", label: "Переучивание", color: "relearning", stackId: "due" }]} kind="stacked" testId="stats-load-future-due" aside={<span className="statistics-panel-badge">90 дней</span>} />
    <p className="statistics-assumption"><Info size={16} aria-hidden="true" /> Прогноз основан на текущем расписании. Будущие новые карточки и будущие ошибки не учитываются. Просроченные карточки показаны отдельно.</p>
  </div>;
}

function Progress({ result }: { result: StatisticsResult }) {
  const progress = result.progress;
  return <div className="statistics-section-stack" data-testid="statistics-progress">
    <InsightCard title="Рост изученного материала" text={`В коллекции ${formatNumber(progress.totalCards)} карточек и ${formatNumber(progress.totalNotes)} заметок. За период впервые изучено ${formatNumber(progress.introducedCards)} карточек.`} />
    <section className="statistics-kpis compact" aria-label="Показатели прогресса">
      <KpiCard label="Всего карточек" value={formatNumber(progress.totalCards)} color="reviews" />
      <KpiCard label="Всего заметок" value={formatNumber(progress.totalNotes)} color="study-time" />
      <KpiCard label="Введено за период" value={formatNumber(progress.introducedCards)} color="introduced" />
    </section>
    <StatisticsPanel title="Текущее состояние коллекции" description="Снимок сейчас, а не реконструкция прошлого" testId="stats-progress-current-state">
      <CollectionStateBar states={progress.currentStates} />
      <p className="statistics-limitation"><Info size={15} aria-hidden="true" /> Состояния «молодые» и «зрелые» доступны только на текущий момент; исторический ряд не восстанавливается.</p>
    </StatisticsPanel>
    <StatisticsChartPanel title="Введённые карточки" description="Фактические первые изучения по интервалам" summary={seriesSummary(progress.introducedSeries, "introducedCards", "Введённые карточки")} points={progress.introducedSeries} metrics={[{ key: "introducedCards", label: "Введено", color: "introduced" }]} kind="bar" testId="stats-progress-introduced" />
  </div>;
}

function DeckComparison({ result }: { result: StatisticsResult }) {
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
    <InsightCard title="Сравнение корневых групп" text={selectedRows.length ? `Выбрано ${selectedRows.length} ${pluralDeck(selectedRows.length)} с наибольшим объёмом практики. Выбор можно изменить в таблице.` : "Для сравнения выберите колоды с достаточной выборкой."} />
    <section className="deck-comparison-tools statistics-supporting-panel"><label>Найти колоду<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Название или путь" /></label><span>Можно сравнить до {selectionLimit} непересекающихся групп</span></section>
    <StatisticsPanel title="Успешность по выбранным колодам" description="Количество повторений указано рядом и не используется как общая шкала" testId="stats-deck-comparison-chart">
      {selectedRows.length ? <DeckRankedBars rows={selectedRows} /> : <StatisticsEmptyState text="Выберите хотя бы одну колоду для сравнения." />}
    </StatisticsPanel>
    <StatisticsPanel title="Данные по колодам" description="Фактические показатели без оценок состояния и рекомендаций">
      {visible.length ? <div className="statistics-table-wrap"><table className="statistics-table statistics-deck-table"><thead><tr><th>Выбор</th><th>Колода</th><th>Повторения</th><th>Изменение</th><th>Успешность</th><th>Средний ответ</th><th>Время</th><th>Новые</th><th>Уверенность</th></tr></thead><tbody>{visible.map((row) => {
        const isSelected = selected.includes(row.deckId);
        return <tr key={row.deckId} className={isSelected ? "is-selected" : undefined} data-selected={isSelected ? "true" : "false"}><td><label className="statistics-row-selector"><input aria-label={`Выбрать ${row.fullName}`} type="checkbox" checked={isSelected} disabled={!isSelected && selected.length >= selectionLimit} onChange={() => toggle(row.deckId)} />{isSelected ? <Check size={14} aria-hidden="true" /> : null}</label></td><th title={row.fullName}>{row.fullName}</th><td>{formatNumber(row.reviews)}</td><td>{formatDelta(row.periodDelta?.reviews.delta)}</td><td>{formatPercent(row.successRate)}</td><td>{row.averageAnswerSeconds == null ? "Нет данных" : `${row.averageAnswerSeconds.toFixed(1)} с`}</td><td>{formatDuration(row.studySeconds)}</td><td>{formatNumber(row.introducedCards)}</td><td><ConfidenceBadge value={row.confidence} /></td></tr>;
      })}</tbody></table></div> : <StatisticsEmptyState text="Подходящие обычные колоды не найдены." />}
    </StatisticsPanel>
  </div>;
}

function StatisticsPanel({ title, description, children, testId }: { title: string; description: string; children: ReactNode; testId?: string }) {
  return <section className="statistics-panel" data-testid={testId}><header className="statistics-panel-header"><div><h2>{title}</h2><p>{description}</p></div></header>{children}</section>;
}

function KpiCard({ label, value, caption, delta, color }: { label: string; value: string; caption?: string; delta?: StatisticsDeltaModel; color: StatisticsSemanticColor }) {
  return <article className="statistics-kpi-card" data-testid="statistics-kpi-card"><span className={`statistics-kpi-accent ${statisticsColorClass[color]}`} aria-hidden="true" /><span className="statistics-kpi-label">{label}</span><strong>{value}</strong>{delta ? <span className={`statistics-delta is-${delta.direction}`} data-comparison-style={delta.comparisonStyle}>{delta.text}</span> : null}{caption ? <small>{caption}</small> : null}</article>;
}

function InsightCard({ insights, confidence, title = "Главный вывод", text }: { insights?: StatisticsResult["overview"]["insights"]; confidence?: StatisticsConfidence; title?: string; text?: string }) {
  const observation = text || insightText(insights || [], confidence);
  return <section className="statistics-insight-card" aria-label="Главный фактический вывод" data-testid="statistics-insight"><span className="statistics-insight-icon"><BarChart3 size={20} aria-hidden="true" /></span><div><span>{title}</span><p>{observation}</p></div>{confidence ? <ConfidenceBadge value={confidence} /> : null}</section>;
}

function ConfidenceBadge({ value }: { value: StatisticsConfidence }) {
  return <span className={`statistics-confidence-badge is-${value}`}>{confidenceLabel(value)}</span>;
}

function AnswerDistribution({ ratings }: { ratings: StatisticsResult["quality"]["ratings"] }) {
  const rows: Array<{ key: keyof typeof ratings; label: string; color: StatisticsSemanticColor }> = [
    { key: "again", label: "Снова", color: "again" }, { key: "hard", label: "Трудно", color: "hard" }, { key: "good", label: "Хорошо", color: "good" }, { key: "easy", label: "Легко", color: "easy" },
  ];
  const total = rows.reduce((sum, row) => sum + ratings[row.key], 0);
  return <div className="statistics-answer-distribution" role="img" aria-label={`Распределение ${total} ответов по четырём кнопкам`}>
    <div className="statistics-stacked-strip">{rows.map((row) => <span key={row.key} className={statisticsColorClass[row.color]} style={{ width: `${total ? ratings[row.key] / total * 100 : 0}%` }} title={`${row.label}: ${ratings[row.key]}`} />)}</div>
    <div className="statistics-direct-legend">{rows.map((row) => <div key={row.key}><i className={statisticsColorClass[row.color]} /><span>{row.label}</span><strong>{formatNumber(ratings[row.key])}</strong><small>{formatPercentValue(total ? ratings[row.key] / total : null)}</small></div>)}</div>
  </div>;
}

function RetentionBreakdown({ result, confidence }: { result: StatisticsResult["quality"]["trueRetention"]; confidence: StatisticsConfidence }) {
  const rows = [{ label: "Все", value: result.overall, sample: result.sampleSize, color: "success" as const }, { label: "Молодые", value: result.young, sample: result.youngPass + result.youngFail, color: "young" as const }, { label: "Зрелые", value: result.mature, sample: result.maturePass + result.matureFail, color: "mature" as const }];
  return <div className="statistics-retention"><div className="statistics-retention-summary"><strong>{formatPercent(result.overall)}</strong><ConfidenceBadge value={confidence} /></div>{rows.map((row) => <div className="statistics-retention-row" key={row.label}><span>{row.label}</span><div><i className={statisticsColorClass[row.color]} style={{ width: `${(row.value || 0) * 100}%` }} /></div><strong>{formatPercent(row.value)}</strong><small>{formatNumber(row.sample)} ответов</small></div>)}<details className="statistics-definition"><summary>Как считается</summary><p>Учитывается первый обычный подход к карточке за локальный день. Зрелые карточки имели предыдущий интервал не менее 21 дня.</p></details></div>;
}

function CollectionStateBar({ states }: { states: StatisticsResult["progress"]["currentStates"] }) {
  const rows: Array<{ key: keyof typeof states; label: string; color: StatisticsSemanticColor }> = [
    { key: "unseen", label: "Не изучались", color: "unseen" }, { key: "learning", label: "Изучаются", color: "learning" }, { key: "young", label: "Молодые", color: "young" }, { key: "mature", label: "Зрелые", color: "mature" }, { key: "suspended", label: "Приостановленные", color: "suspended" }, { key: "buried", label: "Скрытые", color: "buried" },
  ];
  const total = rows.reduce((sum, row) => sum + states[row.key], 0);
  return <div className="statistics-state-distribution" role="img" aria-label={`Текущее состояние ${total} карточек`}><div className="statistics-stacked-strip is-state">{rows.map((row) => <span key={row.key} className={statisticsColorClass[row.color]} style={{ width: `${total ? states[row.key] / total * 100 : 0}%` }} />)}</div><div className="statistics-direct-legend is-grid">{rows.map((row) => <div key={row.key}><i className={statisticsColorClass[row.color]} /><span>{row.label}</span><strong>{formatNumber(states[row.key])}</strong><small>{formatPercentValue(total ? states[row.key] / total : null)}</small></div>)}</div></div>;
}

function DeckRankedBars({ rows }: { rows: StatisticsResult["deckComparison"]["rows"] }) {
  return <div className="statistics-ranked-bars" role="img" aria-label="Успешность выбранных колод; количество повторений указано текстом">{[...rows].sort((a, b) => (b.successRate || 0) - (a.successRate || 0)).map((row, index) => <div key={row.deckId} className="statistics-ranked-row"><span className="statistics-rank">{index + 1}</span><div className="statistics-ranked-label"><strong title={row.fullName}>{row.fullName}</strong><small>{formatNumber(row.reviews)} повторений · {confidenceLabel(row.confidence).toLocaleLowerCase()}</small></div><div className="statistics-ranked-track"><i style={{ width: `${(row.successRate || 0) * 100}%` }} /></div><strong>{formatPercent(row.successRate)}</strong></div>)}</div>;
}

function CoverageNotice({ result }: { result: StatisticsResult }) {
  const coverage = result.coverage;
  if (coverage.coverage === "full") return <p className="statistics-coverage"><span>Покрытие</span>{coverage.requestedFrom || coverage.dataFrom || "начало истории"} — {coverage.requestedTo}<strong>{formatNumber(coverage.sampleSize)} ответов</strong></p>;
  return <p className={`statistics-coverage ${coverage.coverage}`} role="status"><span>Покрытие</span>{coverage.coverage === "partial" ? `Период покрыт частично: данные доступны с ${coverage.dataFrom}.` : "История повторений пока недоступна."}</p>;
}

function StatisticsUnavailable({ loadState }: { loadState: LoadState }) {
  const text = loadState === "loading" ? "Загружаем статистику…" : loadState === "forbidden" ? "Недействительная ссылка dashboard." : "Статистика пока недоступна. Обновите cache в Настройки → Данные.";
  return <section className="statistics-empty-page panel-surface"><BarChart3 size={28} /><h1>Статистика</h1><p>{text}</p></section>;
}

function insightText(insights: StatisticsResult["overview"]["insights"], confidence?: StatisticsConfidence): string {
  if (!insights.length) return confidence === "insufficient" ? "Для надёжного сравнения пока недостаточно данных. Значения показаны без оценки тренда." : "Существенных изменений при достаточной выборке не обнаружено.";
  const labels: Record<string, { label: string; increase: string; decrease: string; same: string }> = {
    reviews_changed: { label: "Число повторений", increase: "выросло", decrease: "снизилось", same: "не изменилось" },
    success_rate_changed: { label: "Успешность", increase: "выросла", decrease: "снизилась", same: "не изменилась" },
    answer_time_changed: { label: "Средний ответ", increase: "увеличился", decrease: "сократился", same: "не изменился" },
    active_days_changed: { label: "Число активных дней", increase: "выросло", decrease: "снизилось", same: "не изменилось" },
    new_cards_changed: { label: "Число новых карточек", increase: "выросло", decrease: "снизилось", same: "не изменилось" },
  };
  return insights.slice(0, 2).map((item) => {
    const wording = labels[item.type] || { label: "Показатель", increase: "вырос", decrease: "снизился", same: "не изменился" };
    return `${wording.label} ${item.direction === "increase" ? wording.increase : item.direction === "decrease" ? wording.decrease : wording.same} на ${formatInsightValue(item.value, item.unit)}`;
  }).join("; ") + ".";
}

function formatInsightValue(value: number, unit: string): string {
  const number = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(Math.abs(value));
  return `${number}${unit === "percentage_points" ? " п.п." : unit === "seconds" ? " с" : "%"}`;
}

function formatNumber(value: number): string { return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null): string { return value == null ? "Нет данных" : formatPercentValue(value); }
function formatPercentValue(value: number | null): string { return value == null ? "Нет данных" : `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value * 100)}%`; }
function formatDuration(seconds: number | null): string { if (seconds == null) return "Нет данных"; if (!seconds) return "0 мин"; const minutes = Math.round(seconds / 60); return minutes >= 60 ? `${Math.floor(minutes / 60)} ч ${minutes % 60} мин` : `${minutes} мин`; }
function confidenceLabel(value: StatisticsConfidence): string { return value === "sufficient" ? "Достаточно данных" : value === "preliminary" ? "Предварительно" : "Мало данных"; }
function formatDelta(value: number | null | undefined): string { return value == null ? "Нет данных" : `${value > 0 ? "+" : ""}${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value)}%`; }
function pluralDeck(value: number): string { return value === 1 ? "колода" : value >= 2 && value <= 4 ? "колоды" : "колод"; }

export default StatisticsPage;
