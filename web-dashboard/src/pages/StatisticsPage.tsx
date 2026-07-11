import { BarChart3, ExternalLink, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { runReportAction } from "../lib/actionsApi";
import { fetchStatistics, statisticsQueryKey } from "../lib/statisticsApi";
import type {
  StatisticsHubModel,
  StatisticsPeriod,
  StatisticsQuery,
  StatisticsResult,
  StatisticsSeriesPoint,
  StudyReport,
} from "../types/report";
import type { LoadState } from "./HomePage";

export type StatisticsSection = "overview" | "quality" | "load" | "progress" | "decks";

const sections: Array<{ id: StatisticsSection; label: string; path: string }> = [
  { id: "overview", label: "Обзор", path: "/stats" },
  { id: "quality", label: "Качество", path: "/stats/quality" },
  { id: "load", label: "Нагрузка", path: "/stats/load" },
  { id: "progress", label: "Прогресс", path: "/stats/progress" },
  { id: "decks", label: "Колоды", path: "/stats/decks" },
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
  if (loadState !== "ready" || !hub) {
    return <StatisticsUnavailable loadState={loadState} />;
  }
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

  const updateQuery = (patch: Partial<StatisticsQuery>) => setQuery((current) => ({ ...current, ...patch }));
  const openNativeStats = async () => {
    const response = await runReportAction("open-native-stats", {});
    if (!response.ok) setError(response.error || "Не удалось открыть статистику Anki.");
  };

  return (
    <div className="statistics-shell" data-testid="statistics-page" data-statistics-section={section}>
      <aside className="statistics-sidebar">
        <div className="statistics-sidebar-heading">
          <BarChart3 size={18} aria-hidden="true" />
          <div><strong>Статистика</strong><span>Периоды и сравнения</span></div>
        </div>
        <nav aria-label="Разделы статистики">
          {sections.map((item) => (
            <a key={item.id} href={`#${item.path}`} aria-current={item.id === section ? "page" : undefined}>{item.label}</a>
          ))}
        </nav>
      </aside>

      <div className="statistics-content">
        <header className="statistics-header panel-surface">
          <div>
            <p className="eyebrow">Statistics v1</p>
            <h1>{sections.find((item) => item.id === section)?.label}</h1>
            <p>Качество, нагрузка и прогресс за выбранный период — без сырых данных карточек.</p>
          </div>
          <button type="button" className="secondary-button" onClick={openNativeStats}>
            <ExternalLink size={16} aria-hidden="true" /> Открыть статистику Anki
          </button>
        </header>

        <StatisticsControls hub={hub} query={query} updateQuery={updateQuery} />

        <CoverageNotice result={result} />
        {status === "loading" ? <div className="statistics-loading" role="status">Обновляем данные…</div> : null}
        {status === "error" || error ? (
          <div className="statistics-error" role="alert">
            <span>{error || "Не удалось обновить статистику."}</span>
            {status === "error" ? <button type="button" onClick={() => setRetryNonce((value) => value + 1)}><RefreshCw size={15} /> Повторить</button> : null}
          </div>
        ) : null}

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

function StatisticsControls({ hub, query, updateQuery }: { hub: StatisticsHubModel; query: StatisticsQuery; updateQuery: (patch: Partial<StatisticsQuery>) => void }) {
  const scopeKind = query.scope.kind;
  const selectedDeckId = scopeKind === "single_deck" ? query.scope.deckId : hub.deckOptions[0]?.deckId;
  return (
    <section className="statistics-controls panel-surface" aria-label="Параметры статистики">
      <label>Область
        <select value={scopeKind} onChange={(event) => {
          const kind = event.target.value;
          if (kind === "single_deck" && hub.deckOptions[0]) updateQuery({ scope: { kind, deckId: hub.deckOptions[0].deckId, mode: "subtree" } });
          else updateQuery({ scope: { kind: kind as "dashboard" | "all_collection" } });
        }}>
          <option value="dashboard">Текущая область dashboard</option>
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
      <label className="statistics-checkbox"><input type="checkbox" checked={query.comparison} disabled={query.period === "all"} onChange={(event) => updateQuery({ comparison: event.target.checked })} />Сравнить с предыдущим периодом</label>
    </section>
  );
}

function Overview({ result }: { result: StatisticsResult }) {
  const kpi = result.overview.kpis;
  return <div className="statistics-section-stack">
    <section className="statistics-kpis" aria-label="Ключевые показатели">
      <Metric label="Повторения" value={formatNumber(kpi.reviews)} /><Metric label="Время учёбы" value={formatDuration(kpi.studySeconds)} />
      <Metric label="Успешность" value={formatPercent(kpi.successRate)} /><Metric label="Новые карточки" value={formatNumber(kpi.introducedCards)} caption="Впервые изученные" />
      <Metric label="Активные дни" value={formatNumber(kpi.activeDays)} /><Metric label="Средний ответ" value={kpi.averageAnswerSeconds == null ? "Нет данных" : `${kpi.averageAnswerSeconds.toFixed(1)} с`} />
    </section>
    <InsightList insights={result.overview.insights} confidence={result.overview.confidence} />
    <SeriesPanel title="Повторения и время" description="Количество ответов и оценка времени по выбранным интервалам." points={result.overview.series} metrics={[{ key: "reviews", label: "Повторения" }, { key: "studySeconds", label: "Время, сек." }]} />
    <SeriesPanel title="Качество ответов" description="Взвешенная успешность и среднее время ответа." points={result.overview.series} metrics={[{ key: "successRate", label: "Успешность", percent: true }, { key: "averageAnswerSeconds", label: "Средний ответ, сек." }]} />
    <SeriesPanel title="Новые карточки и повторения" description="Фактически впервые изученные карточки рядом с общей практикой." points={result.overview.series} metrics={[{ key: "introducedCards", label: "Новые карточки" }, { key: "reviews", label: "Повторения" }]} />
  </div>;
}

function Quality({ result }: { result: StatisticsResult }) {
  const q = result.quality;
  const ratingTotal = Object.values(q.ratings).reduce((sum, value) => sum + value, 0);
  return <div className="statistics-section-stack">
    <section className="statistics-kpis compact"><Metric label="Успешность ответов" value={formatPercent(q.successRate)} /><Metric label="True Retention" value={formatPercent(q.trueRetention.overall)} caption="Первый review карточки за локальный день" /><Metric label="Выборка" value={formatNumber(q.trueRetention.sampleSize)} caption={confidenceLabel(q.confidence)} /></section>
    <SeriesPanel title="Тренд успешности" description="Pass / (Pass + Fail), взвешенно по всем ответам." points={q.series} metrics={[{ key: "successRate", label: "Успешность", percent: true }, { key: "pass", label: "Pass" }, { key: "fail", label: "Fail" }]} />
    <section className="statistics-grid-2">
      <DataCard title="Кнопки ответа" subtitle={`${ratingTotal} ответов`}><Distribution rows={[["Again", q.ratings.again], ["Hard", q.ratings.hard], ["Good", q.ratings.good], ["Easy", q.ratings.easy]]} /></DataCard>
      <DataCard title="Истинное удержание" subtitle="Mature: предыдущий интервал ≥ 21 дня"><Distribution percent rows={[["Молодые", q.trueRetention.young], ["Зрелые", q.trueRetention.mature], ["Все", q.trueRetention.overall]]} /></DataCard>
    </section>
  </div>;
}

function Load({ result }: { result: StatisticsResult }) {
  const load = result.load;
  return <div className="statistics-section-stack">
    <section className="statistics-kpis compact"><Metric label="Просрочено сейчас" value={formatNumber(load.overdue)} /><Metric label="Daily load" value={load.dailyLoad.toFixed(2)} caption="Σ 1 / max(interval, 1)" /><Metric label="Средняя нагрузка активного дня" value={load.averageActiveDayReviews == null ? "Нет данных" : formatNumber(load.averageActiveDayReviews)} /></section>
    <SeriesPanel title="Прошлая нагрузка" description="Повторения, время и новые карточки по интервалам." points={load.past} metrics={[{ key: "reviews", label: "Повторения" }, { key: "introducedCards", label: "Новые" }]} />
    <DataCard title="Будущая нагрузка" subtitle="Оценка текущего расписания. Не учитывает будущие новые карточки и будущие ошибки. Просроченные показаны отдельно.">
      {load.futureDue.length ? <table className="statistics-table"><thead><tr><th>Через дней</th><th>Learning</th><th>Review</th><th>Relearning</th><th>Всего</th></tr></thead><tbody>{load.futureDue.map((row) => <tr key={row.dayOffset}><th>{row.dayOffset}</th><td>{row.learning}</td><td>{row.review}</td><td>{row.relearning}</td><td>{row.total}</td></tr>)}</tbody></table> : <EmptyState text="В ближайшие 90 дней карточек по текущему расписанию нет." />}
    </DataCard>
  </div>;
}

function Progress({ result }: { result: StatisticsResult }) {
  const p = result.progress;
  const labels: Record<string, string> = { unseen: "Не изучались", learning: "Изучаются", young: "Молодые", mature: "Зрелые", suspended: "Приостановленные", buried: "Скрытые" };
  return <div className="statistics-section-stack">
    <section className="statistics-kpis compact"><Metric label="Всего карточек" value={formatNumber(p.totalCards)} /><Metric label="Всего заметок" value={formatNumber(p.totalNotes)} /><Metric label="Введено за период" value={formatNumber(p.introducedCards)} /></section>
    <DataCard title="Текущее состояние коллекции" subtitle="Снимок сейчас, а не реконструкция прошлого"><Distribution rows={Object.entries(p.currentStates).map(([key, value]) => [labels[key] || key, value])} /></DataCard>
    <SeriesPanel title="Введённые карточки" description="Фактические первые изучения. Исторические молодые/зрелые состояния не выдумываются." points={p.introducedSeries} metrics={[{ key: "introducedCards", label: "Введено" }, { key: "reviews", label: "Повторения" }]} />
  </div>;
}

function DeckComparison({ result }: { result: StatisticsResult }) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const visible = result.deckComparison.rows.filter((row) => row.fullName.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  const rows = selected.length ? visible.filter((row) => selected.includes(row.deckId)) : visible;
  const toggle = (deckId: number) => setSelected((current) => current.includes(deckId) ? current.filter((id) => id !== deckId) : current.length < 6 ? [...current, deckId] : current);
  return <div className="statistics-section-stack">
    <section className="deck-comparison-tools panel-surface"><label>Найти колоду<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Название или путь" /></label><span>Непересекающиеся корневые группы · максимум {result.deckComparison.limit}</span></section>
    <DataCard title="Сравнение колод" subtitle="Периодические агрегаты без оценок состояния. Выберите до шести строк для фокуса.">
      {visible.length ? <div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>Выбор</th><th>Колода</th><th>Повторения</th><th>Δ периода</th><th>Успешность</th><th>Средний ответ</th><th>Время</th><th>Новые</th><th>Доверие</th></tr></thead><tbody>{rows.map((row) => <tr key={row.deckId}><td><input aria-label={`Выбрать ${row.fullName}`} type="checkbox" checked={selected.includes(row.deckId)} disabled={!selected.includes(row.deckId) && selected.length >= 6} onChange={() => toggle(row.deckId)} /></td><th title={row.fullName}>{row.fullName}</th><td>{row.reviews}</td><td>{formatDelta(row.periodDelta?.reviews.delta)}</td><td>{formatPercent(row.successRate)}</td><td>{row.averageAnswerSeconds == null ? "Нет данных" : `${row.averageAnswerSeconds.toFixed(1)} с`}</td><td>{formatDuration(row.studySeconds)}</td><td>{row.introducedCards}</td><td>{confidenceLabel(row.confidence)}</td></tr>)}</tbody></table></div> : <EmptyState text="Подходящие обычные колоды не найдены." />}
      {selected.length ? <button className="text-button" type="button" onClick={() => setSelected([])}>Показать все строки</button> : null}
    </DataCard>
  </div>;
}

function SeriesPanel({ title, description, points, metrics }: { title: string; description: string; points: StatisticsSeriesPoint[]; metrics: Array<{ key: keyof StatisticsSeriesPoint; label: string; percent?: boolean }> }) {
  const maximum = Math.max(1, ...points.flatMap((point) => metrics.map((metric) => normalizedMetric(point[metric.key], metric.percent))));
  return <section className="statistics-series-card panel-surface">
    <div><h2>{title}</h2><p>{description}</p></div>
    {points.length ? <>
      <div className="statistics-chart" role="img" aria-label={`${title}. ${points.length} интервалов.`}>
        {points.map((point) => <div className="statistics-chart-group" key={point.key} title={point.label}><div className="statistics-chart-bars">{metrics.map((metric, index) => <span key={String(metric.key)} className={`series-${index + 1}`} style={{ height: `${Math.max(2, normalizedMetric(point[metric.key], metric.percent) / maximum * 100)}%` }} aria-hidden="true" />)}</div><small>{shortLabel(point.label)}</small></div>)}
      </div>
      <div className="statistics-legend">{metrics.map((metric, index) => <span key={String(metric.key)}><i className={`series-${index + 1}`} />{metric.label}</span>)}</div>
      <details><summary>Таблица данных</summary><div className="statistics-table-wrap"><table className="statistics-table"><thead><tr><th>Интервал</th>{metrics.map((metric) => <th key={String(metric.key)}>{metric.label}</th>)}</tr></thead><tbody>{points.map((point) => <tr key={point.key}><th>{point.label}</th>{metrics.map((metric) => <td key={String(metric.key)}>{formatMetric(point[metric.key], metric.percent)}</td>)}</tr>)}</tbody></table></div></details>
    </> : <EmptyState text="Для выбранного периода данных нет." />}
  </section>;
}

function Metric({ label, value, caption }: { label: string; value: string; caption?: string }) { return <article className="statistics-metric panel-surface"><span>{label}</span><strong>{value}</strong>{caption ? <small>{caption}</small> : null}</article>; }
function DataCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) { return <section className="statistics-data-card panel-surface"><h2>{title}</h2><p>{subtitle}</p>{children}</section>; }
function EmptyState({ text }: { text: string }) { return <p className="statistics-empty">{text}</p>; }

function CoverageNotice({ result }: { result: StatisticsResult }) {
  const c = result.coverage;
  if (c.coverage === "full") return <p className="statistics-coverage">Данные: {c.requestedFrom || c.dataFrom || "начало истории"} — {c.requestedTo} · {c.sampleSize} ответов</p>;
  return <p className={`statistics-coverage ${c.coverage}`} role="status">{c.coverage === "partial" ? `Период покрыт частично. Данные доступны с ${c.dataFrom}.` : "История повторений пока недоступна."}</p>;
}

function InsightList({ insights, confidence }: { insights: StatisticsResult["overview"]["insights"]; confidence: StatisticsResult["overview"]["confidence"] }) {
  if (!insights.length) return <p className="statistics-confidence panel-surface">{confidence === "insufficient" ? "Для выводов пока недостаточно данных; сами значения показаны без оценки тренда." : "Заметных изменений с достаточной выборкой не обнаружено."}</p>;
  const labels: Record<string, string> = { reviews_changed: "Число повторений", success_rate_changed: "Успешность", answer_time_changed: "Средний ответ", active_days_changed: "Активные дни", new_cards_changed: "Новые карточки" };
  return <section className="statistics-insights panel-surface" aria-label="Фактические наблюдения">{insights.map((item, index) => <p key={`${item.type}-${index}`}><strong>{labels[item.type] || item.type}</strong> {item.direction === "increase" ? "выросло" : "снизилось"} на {Math.abs(item.value)} {item.unit === "percentage_points" ? "п.п." : item.unit === "seconds" ? "с" : "%"}</p>)}</section>;
}

function Distribution({ rows, percent = false }: { rows: Array<[string, number | null]>; percent?: boolean }) {
  const values = rows.map(([, value]) => typeof value === "number" ? (percent ? value * 100 : value) : 0);
  const max = Math.max(1, ...values);
  return <div className="statistics-distribution">{rows.map(([label, value], index) => <div key={label}><span>{label}</span><div><i style={{ width: `${values[index] / max * 100}%` }} /></div><strong>{percent ? formatPercent(value) : formatNumber(value ?? 0)}</strong></div>)}</div>;
}

function StatisticsUnavailable({ loadState }: { loadState: LoadState }) {
  const text = loadState === "loading" ? "Загружаем статистику…" : loadState === "forbidden" ? "Недействительная ссылка dashboard." : "Статистика пока недоступна. Обновите cache в Настройки → Данные.";
  return <section className="statistics-empty-page panel-surface"><BarChart3 size={28} /><h1>Статистика</h1><p>{text}</p></section>;
}

function normalizedMetric(value: unknown, percent?: boolean): number { return typeof value === "number" && Number.isFinite(value) ? value * (percent ? 100 : 1) : 0; }
function formatMetric(value: unknown, percent?: boolean): string { return percent ? formatPercent(typeof value === "number" ? value : null) : typeof value === "number" ? new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value) : "Нет данных"; }
function formatNumber(value: number): string { return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value); }
function formatPercent(value: number | null): string { return value == null ? "Нет данных" : `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value * 100)}%`; }
function formatDuration(seconds: number | null): string { if (seconds == null) return "Нет данных"; if (!seconds) return "0 мин"; const minutes = Math.round(seconds / 60); return minutes >= 60 ? `${Math.floor(minutes / 60)} ч ${minutes % 60} мин` : `${minutes} мин`; }
function shortLabel(label: string): string { return label.length > 10 ? label.slice(-5) : label; }
function confidenceLabel(value: string): string { return value === "sufficient" ? "Достаточно" : value === "preliminary" ? "Предварительно" : "Мало данных"; }
function formatDelta(value: number | null | undefined): string { return value == null ? "Нет данных" : `${value > 0 ? "+" : ""}${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value)}%`; }

export default StatisticsPage;
