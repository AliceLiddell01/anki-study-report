import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { runReportAction } from "../lib/actionsApi";
import { buildDeckHealth } from "../lib/deckHealth";
import {
  exactDeckMatch,
  nearestVisibleSelection,
  sortedRootIds,
  type DeckHubFilter,
  type DeckHubSort,
  visibleDeckRows,
} from "../lib/deckTree";
import { finiteNumber, formatInteger, formatPercent, formatSeconds, safeText } from "../lib/formatters";
import type { DeckHubMetrics, DeckHubModel, DeckHubNode, DeckPerformance, Status, StudyReport } from "../types/report";
import type { LoadState } from "./HomePage";

const statusLabels: Record<Status, string> = {
  good: "Хорошо",
  neutral: "Норма",
  warning: "Внимание",
  danger: "Опасно",
};

const confidenceLabels: Record<DeckHubNode["dataConfidence"], string> = {
  sufficient: "Данных достаточно",
  preliminary: "Предварительная оценка",
  insufficient: "Недостаточно данных",
};

function DecksPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<DeckHubFilter>("all");
  const [sort, setSort] = useState<DeckHubSort>("name");
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => new Set());
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showAllIssues, setShowAllIssues] = useState(false);
  const [actionState, setActionState] = useState<{ pending: boolean; message: string; error: boolean }>({ pending: false, message: "", error: false });

  const hub = useMemo(() => report?.deckHub ?? legacyDeckHub(report?.decks ?? []), [report?.deckHub, report?.decks]);
  const rows = useMemo(() => visibleDeckRows(hub, expandedIds, query, filter, sort), [expandedIds, filter, hub, query, sort]);
  const visibleIds = useMemo(() => new Set(rows.map((row) => row.node.deckId)), [rows]);
  const selectedNode = selectedId === null ? null : hub.nodes[String(selectedId)] ?? null;
  const transformActive = Boolean(query.trim()) || filter !== "all";
  const hasManualExpansion = expandedIds.size > 0;

  useEffect(() => {
    if (!hub.rootIds.length) {
      setSelectedId(null);
      return;
    }
    setSelectedId((current) => current ?? sortedRootIds(hub, "name")[0] ?? null);
  }, [hub]);

  useEffect(() => {
    const exact = exactDeckMatch(hub, query);
    if (exact !== null && visibleIds.has(exact)) {
      setSelectedId(exact);
      return;
    }
    if (query.trim()) {
      const firstMatch = rows.find((row) => !row.contextOnly && !row.node.structuralOnly);
      setSelectedId(firstMatch?.node.deckId ?? null);
      return;
    }
    if (filter !== "all") {
      const severity = { danger: 4, warning: 3, neutral: 2, good: 1 } as const;
      const strongest = rows
        .filter((row) => !row.contextOnly && !row.node.structuralOnly)
        .sort((left, right) => severity[right.node.aggregateHealth] - severity[left.node.aggregateHealth])[0];
      setSelectedId(strongest?.node.deckId ?? null);
      return;
    }
    setSelectedId((current) => nearestVisibleSelection(hub, visibleIds, current));
  }, [filter, hub, query, rows, visibleIds]);

  useEffect(() => {
    setShowAllIssues(false);
    setActionState({ pending: false, message: "", error: false });
  }, [selectedId]);

  if (loadState !== "ready") return <DecksLoadState state={loadState} />;
  if (!report) return <EmptyDecksState title="Отчёт ещё не опубликован" text="Откройте Anki Study Report и опубликуйте dashboard report." />;

  const selectIssue = (deckId: number) => {
    setExpandedIds((current) => expandPath(hub, deckId, current));
    setSelectedId(deckId);
  };
  const openDeck = async (mode: "subtree" | "direct") => {
    if (!selectedNode) return;
    setActionState({ pending: true, message: "", error: false });
    const result = await runReportAction("open-deck-browser", { deckId: selectedNode.deckId, mode });
    setActionState({ pending: false, message: result.message || result.error || "Действие завершено.", error: !result.ok });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <header className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <h1 className="text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Колоды</h1>
        <p className="mt-2 text-sm leading-6 text-report-muted">Состояние структуры колод и области, требующие внимания.</p>
        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <SummaryMetric label="Всего колод" value={formatInteger(hub.summary.totalDecks)} />
          <SummaryMetric label="Требуют внимания" value={formatInteger(hub.summary.attentionDecks)} tone={hub.summary.attentionDecks ? "warning" : "neutral"} />
          <SummaryMetric label="Опасные" value={formatInteger(hub.summary.dangerDecks)} tone={hub.summary.dangerDecks ? "danger" : "neutral"} />
          <SummaryMetric label="Средняя успешность" value={formatPercent(hub.summary.aggregatePassRate)} />
        </div>
        {hub.summary.groupsWithDescendantIssues > 0 && (
          <p className="mt-3 text-xs text-report-muted">{formatInteger(hub.summary.groupsWithDescendantIssues)} групп содержат проблемы внутри.</p>
        )}
        {hub.summary.filteredDecksExcluded > 0 && (
          <p className="mt-3 flex items-center gap-2 text-sm text-report-muted" data-testid="filtered-decks-info">
            <span className="text-report-blue" aria-hidden="true">ⓘ</span>
            {formatInteger(hub.summary.filteredDecksExcluded)} {filteredDeckNoun(hub.summary.filteredDecksExcluded)} не участвует в оценке
          </p>
        )}
      </header>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="grid gap-3 xl:grid-cols-[minmax(240px,1fr)_220px_220px_auto]">
          <label className="relative block">
            <span className="sr-only">Найти колоду</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="form-control w-full py-2.5 pl-10 pr-3 text-sm" placeholder="Найти колоду…" />
          </label>
          <label>
            <span className="sr-only">Фильтр состояния</span>
            <select value={filter} onChange={(event) => setFilter(event.target.value as DeckHubFilter)} className="form-control w-full px-3 py-2.5 text-sm">
              <option value="all">Все статусы</option>
              <option value="attention">Требуют внимания</option>
              <option value="danger">Опасные</option>
              <option value="insufficient">Недостаточно данных</option>
            </select>
          </label>
          <label>
            <span className="sr-only">Сортировка колод</span>
            <select value={sort} onChange={(event) => setSort(event.target.value as DeckHubSort)} className="form-control w-full px-3 py-2.5 text-sm">
              <option value="name">По имени</option>
              <option value="status">По статусу</option>
              <option value="reviews">По числу повторений</option>
              <option value="success">По успешности</option>
            </select>
          </label>
          <button
            type="button"
            className="min-h-10 rounded-lg border border-ink-700 px-4 py-2 text-sm font-medium text-report-text hover:bg-ink-800 focus:outline-none focus:ring-2 focus:ring-report-blue/55 disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="deck-groups-toggle"
            disabled={transformActive}
            title={transformActive ? "Во время поиска и фильтра совпавшие ветки раскрываются автоматически" : undefined}
            onClick={() => setExpandedIds(hasManualExpansion ? new Set() : expandedRootGroups(hub))}
          >
            {transformActive ? "Группы раскрыты фильтром" : hasManualExpansion ? "Свернуть все" : "Развернуть группы"}
          </button>
        </div>
      </section>

      {hub.summary.totalDecks === 0 ? (
        <EmptyDecksState title="Колоды пока не найдены" text="Пустая Default и фильтрованные колоды не получают фиктивную оценку состояния." />
      ) : (
        <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
          <section className="min-w-0 self-start overflow-hidden rounded-xl border border-ink-700 bg-ink-850 shadow-panel" aria-label="Иерархия колод" data-testid="deck-tree-panel">
            <div className="grid grid-cols-[minmax(260px,1fr)_110px_110px_120px] border-b border-ink-700 bg-ink-800 px-3 py-3 text-xs font-semibold uppercase tracking-[0.04em] text-report-muted">
              <span>Колода</span><span className="text-right">Повторения</span><span className="text-right">Успешность</span><span className="pl-4">Статус</span>
            </div>
            {rows.length ? (
              <div className="divide-y divide-ink-700/80">
                {rows.map(({ node, level, contextOnly }) => {
                  const selected = node.deckId === selectedId;
                  const hasChildren = node.childIds.length > 0;
                  const expanded = transformActive ? hasChildren : expandedIds.has(node.deckId);
                  return (
                    <div key={node.deckId} className={`grid grid-cols-[minmax(260px,1fr)_110px_110px_120px] items-center px-3 py-2.5 ${selected ? "bg-report-blue/12 ring-1 ring-inset ring-report-blue/55" : "hover:bg-ink-800/45"}`}>
                      <div className="flex min-w-0 items-start gap-1" style={{ paddingLeft: `${Math.min(level - 1, 5) * 18}px` }}>
                        {hasChildren ? (
                          <button type="button" aria-label={`${expanded ? "Свернуть" : "Развернуть"} ${node.fullName}`} aria-expanded={expanded} onClick={() => setExpandedIds((current) => toggleSet(current, node.deckId))} className="deck-disclosure-button mt-0.5 text-report-muted hover:text-report-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-report-blue">
                            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          </button>
                        ) : <span className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full bg-ink-500" aria-hidden="true" />}
                        <button type="button" aria-pressed={selected} title={node.fullName} onClick={() => setSelectedId(node.deckId)} className="min-w-0 rounded px-2 py-1 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-report-blue">
                          <span className="block truncate font-semibold text-report-text">{node.shortName}</span>
                          <span className="mt-0.5 block truncate text-xs text-report-muted">
                            {contextOnly || node.structuralOnly ? "Контекст ветки" : hasChildren ? "включая дочерние колоды" : node.fullName}
                          </span>
                          {node.descendantIssueCount > 0 && <span className="mt-1 block text-xs text-report-warning">{formatInteger(node.descendantIssueCount)} проблем внутри</span>}
                        </button>
                      </div>
                      <span className="text-right tabular-nums text-report-text">{formatInteger(node.subtreeMetrics.reviews)}</span>
                      <span className="text-right tabular-nums text-report-text">{formatPercent(node.subtreeMetrics.passRate)}</span>
                      <span className="pl-4"><StatusPill status={node.aggregateHealth}>{node.structuralOnly ? "Контекст" : statusLabels[node.aggregateHealth]}</StatusPill>{node.dataConfidence !== "sufficient" && !node.structuralOnly && <span className="mt-1 block text-[11px] text-report-muted">Предварительно</span>}</span>
                    </div>
                  );
                })}
              </div>
            ) : <EmptyDecksState title="Ничего не найдено" text="Поиск или фильтр скрыли все колоды." compact />}
          </section>

          <aside className="min-w-0 xl:sticky xl:top-5 xl:self-start">
            {selectedNode ? (
              <DeckDetail node={selectedNode} showAllIssues={showAllIssues} onToggleIssues={() => setShowAllIssues((value) => !value)} onSelectIssue={selectIssue} onOpen={openDeck} actionState={actionState} />
            ) : <EmptyDecksState title="Колода не выбрана" text="Выберите видимую колоду, чтобы увидеть причины и действия." />}
          </aside>
        </div>
      )}
    </div>
  );
}

function DeckDetail({ node, showAllIssues, onToggleIssues, onSelectIssue, onOpen, actionState }: { node: DeckHubNode; showAllIssues: boolean; onToggleIssues: () => void; onSelectIssue: (id: number) => void; onOpen: (mode: "subtree" | "direct") => void; actionState: { pending: boolean; message: string; error: boolean } }) {
  const metrics = node.subtreeMetrics;
  const visibleIssues = showAllIssues ? node.descendantIssues : node.descendantIssues.slice(0, 5);
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel" aria-live="polite" data-testid="deck-detail-panel">
      <div data-detail-section="identity">
        <p className="truncate text-xs text-report-muted" title={node.fullName}>{node.fullName.split("::").join(" › ")}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold text-report-text">{node.shortName}</h2><StatusPill status={node.aggregateHealth}>{node.structuralOnly ? "Контекст" : statusLabels[node.aggregateHealth]}</StatusPill></div>
        <p className="mt-2 text-sm text-report-muted">{confidenceLabels[node.dataConfidence]}</p>
      </div>

      <div className="deck-detail-section" data-detail-section="reasons"><h3 className="deck-detail-heading">Почему такой статус</h3><ul className="mt-2 space-y-1 text-sm leading-6 text-report-muted">{node.reasons.slice(0, 3).map((reason) => <li key={reason}>• {reason}</li>)}</ul></div>

      <div className="deck-detail-section" data-detail-section="metrics"><h3 className="deck-detail-heading">Основные показатели</h3><MetricsGrid metrics={metrics} /></div>

      {node.childIds.length > 0 && (
        <div className="deck-detail-section" data-detail-section="direct-subtree">
          <p className="text-sm font-semibold text-report-text">Прямые и иерархические данные</p>
          <p className="mt-2 text-sm text-report-muted">С дочерними: {formatInteger(metrics.reviews)} повторений · {formatPercent(metrics.passRate)}</p>
          {node.directMetrics.directCardCount > 0 || node.directMetrics.reviews > 0 ? (
            <p className="mt-1 text-sm text-report-muted">В самой колоде: {formatInteger(node.directMetrics.reviews)} повторений · {formatPercent(node.directMetrics.passRate)}</p>
          ) : <p className="mt-1 text-sm text-report-muted">В самой родительской колоде карточек нет.</p>}
        </div>
      )}

      {visibleIssues.length > 0 && (
        <div className="deck-detail-section" data-detail-section="issues"><h3 className="deck-detail-heading">Проблемы внутри</h3><div className="mt-2 space-y-2">{visibleIssues.map((issue) => <button key={issue.deckId} type="button" onClick={() => onSelectIssue(issue.deckId)} className="block w-full rounded-lg border border-ink-700 bg-ink-900/35 p-3 text-left hover:border-report-blue/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-report-blue"><span className="font-medium text-report-text">{issue.fullName.split("::").join(" › ")}</span><span className="mt-1 block text-xs text-report-muted">{statusLabels[issue.status]} · {issue.reason}</span></button>)}</div>{node.descendantIssues.length > 5 && <button type="button" className="mt-2 text-sm text-report-blue hover:underline" aria-expanded={showAllIssues} onClick={onToggleIssues}>{showAllIssues ? "Свернуть" : `Показать ещё ${node.descendantIssues.length - 5}`}</button>}</div>
      )}

      {node.recommendations.length > 0 && <div className="deck-detail-section" data-detail-section="recommendations"><h3 className="deck-detail-heading">Что делать</h3><ul className="mt-2 space-y-1 text-sm leading-6 text-report-muted">{node.recommendations.map((item) => <li key={item}>• {item}</li>)}</ul></div>}

      {!node.structuralOnly && <div className="deck-detail-section" data-detail-section="actions"><h3 className="deck-detail-heading">Действия</h3><div className="mt-3 flex flex-wrap gap-2"><button type="button" disabled={actionState.pending} className="rounded-lg border border-report-blue/55 bg-report-blue/20 px-4 py-2 text-sm font-semibold text-report-text hover:border-report-blue focus:outline-none focus:ring-2 focus:ring-report-blue/55 disabled:opacity-55" onClick={() => onOpen("subtree")}>{node.childIds.length ? "Открыть с дочерними" : "Открыть в Anki Browser"}</button>{node.actions.directOnly && <button type="button" disabled={actionState.pending} className="rounded-lg border border-ink-700 px-4 py-2 text-sm font-medium text-report-text hover:bg-ink-800 focus:outline-none focus:ring-2 focus:ring-report-blue/55 disabled:opacity-55" onClick={() => onOpen("direct")}>Только эта колода</button>}</div></div>}
      {actionState.message && <p className={`mt-3 text-sm ${actionState.error ? "text-report-danger" : "text-report-muted"}`}>{actionState.message}</p>}
    </section>
  );
}

function MetricsGrid({ metrics }: { metrics: DeckHubMetrics }) {
  const values = [["Повторения", formatInteger(metrics.reviews)], ["Новые", formatInteger(metrics.newCards)], ["Pass", formatInteger(metrics.passCount)], ["Fail", formatInteger(metrics.failCount)], ["Успешность", formatPercent(metrics.passRate)], ["Средний ответ", formatSeconds(metrics.averageAnswerSeconds)], ["Активные дни", metrics.activeDays === null ? "Нет данных" : formatInteger(metrics.activeDays)]];
  return <div className="mt-2 grid grid-cols-2 gap-2">{values.map(([label, value]) => <div key={label} className="rounded-lg border border-ink-700 bg-ink-900/35 p-2.5"><p className="text-[11px] uppercase tracking-[0.04em] text-report-muted">{label}</p><p className="mt-1 text-sm font-semibold text-report-text">{value}</p></div>)}</div>;
}

function SummaryMetric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: Status }) { return <div className={`rounded-lg border border-ink-700 bg-ink-900/35 p-3 status-border-${tone}`}><p className="text-xs text-report-muted">{label}</p><p className="mt-1 text-xl font-semibold text-report-text">{value}</p></div>; }
function StatusPill({ status, children }: { status: Status; children: ReactNode }) { return <span className={`status-pill status-${status}`}>{children}</span>; }

function DecksLoadState({ state }: { state: LoadState }) {
  const title = state === "loading" ? "Загрузка колод" : state === "forbidden" ? "Недействительная ссылка dashboard" : "Не удалось загрузить колоды";
  return <EmptyDecksState title={title} text={state === "loading" ? "Проверяю локальный API dashboard." : "Откройте dashboard из Anki Study Report и повторите попытку."} />;
}

function EmptyDecksState({ title, text, compact = false }: { title: string; text: string; compact?: boolean }) { return <section className={`rounded-xl border border-dashed border-ink-700 bg-ink-850 text-center ${compact ? "m-4 p-4" : "p-5 shadow-panel"}`}><h2 className="text-lg font-semibold text-report-text">{title}</h2><p className="mt-2 text-sm leading-6 text-report-muted">{text}</p></section>; }

function toggleSet(current: Set<number>, value: number) { const next = new Set(current); if (next.has(value)) next.delete(value); else next.add(value); return next; }
function expandedRootGroups(hub: DeckHubModel) { return new Set(hub.rootIds.filter((id) => (hub.nodes[String(id)]?.childIds.length ?? 0) > 0)); }
function filteredDeckNoun(value: number) { const count = Math.abs(Math.round(value)) % 100; const last = count % 10; if (count >= 11 && count <= 14) return "фильтрованных колод"; if (last === 1) return "фильтрованная колода"; if (last >= 2 && last <= 4) return "фильтрованные колоды"; return "фильтрованных колод"; }
function expandPath(hub: DeckHubModel, deckId: number, current: Set<number>) { const next = new Set(current); let parent = hub.nodes[String(deckId)]?.parentId ?? null; const seen = new Set<number>(); while (parent !== null && !seen.has(parent)) { next.add(parent); seen.add(parent); parent = hub.nodes[String(parent)]?.parentId ?? null; } return next; }

function legacyDeckHub(decks: DeckPerformance[]): DeckHubModel {
  const nodes: DeckHubModel["nodes"] = {};
  for (const deck of decks) {
    const health = buildDeckHealth(deck);
    const metrics: DeckHubMetrics = { reviews: Math.max(0, finiteNumber(deck.totalReviews)), newCards: Math.max(0, finiteNumber(deck.newCards)), passCount: Math.max(0, finiteNumber(deck.passCount)), failCount: Math.max(0, finiteNumber(deck.failCount)), hardCount: Math.max(0, finiteNumber(deck.hardCount)), easyCount: Math.max(0, finiteNumber(deck.easyCount)), passRate: health.passRate, failRate: health.failRate, averageAnswerSeconds: health.averageAnswerSeconds, studySeconds: Math.max(0, finiteNumber(deck.studyMinutes)) * 60, activeDays: null, directCardCount: 0 };
    nodes[String(deck.id)] = { deckId: deck.id, fullName: safeText(deck.name), shortName: safeText(deck.name).split("::").slice(-1)[0] || safeText(deck.name), parentId: null, depth: 0, childIds: [], filtered: false, structuralOnly: false, directMetrics: metrics, subtreeMetrics: metrics, aggregateHealth: health.status, dataConfidence: health.hasEnoughData ? "sufficient" : metrics.reviews > 0 ? "preliminary" : "insufficient", descendantIssueCount: 0, descendantIssues: [], reasons: [health.reason], recommendations: [health.action], actions: { includeDescendants: true, directOnly: false } };
  }
  const list = Object.values(nodes);
  const reviews = list.reduce((sum, node) => sum + node.directMetrics.reviews, 0);
  const passed = list.reduce((sum, node) => sum + node.directMetrics.passCount, 0);
  return { schemaVersion: 0, scope: { kind: "all", selectedDeckIds: [], includeChildDecks: true }, summary: { totalDecks: list.length, attentionDecks: list.filter((node) => ["warning", "danger"].includes(node.aggregateHealth)).length, dangerDecks: list.filter((node) => node.aggregateHealth === "danger").length, groupsWithDescendantIssues: 0, aggregatePassRate: reviews ? passed / reviews : null, filteredDecksExcluded: 0 }, nodes, rootIds: list.map((node) => node.deckId) };
}

export default DecksPage;
