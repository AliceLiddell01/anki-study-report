import { ChevronDown, Search } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  type DeckHealth,
  averageNumber,
  averageRate,
  buildDeckHealthRows,
  countDeckStatuses,
  type DeckHealthStatus,
} from "../lib/deckHealth";
import { finiteNumber, formatCompactSeconds, formatInteger, formatPercent, formatSeconds, safeText } from "../lib/formatters";
import type { LoadState } from "./HomePage";
import type { DeckPerformance, StudyReport } from "../types/report";

type DeckStatusFilter = "all" | "good" | "normal" | "warning" | "danger";
type DeckSortKey = "totalReviews" | "passRate" | "failRate" | "averageAnswerSeconds" | "status";
type SortDirection = "asc" | "desc";
type DeckHealthRow = DeckPerformance & { health: DeckHealth };

const statusLabels: Record<DeckStatusFilter, string> = {
  all: "Все статусы",
  good: "Хорошо",
  normal: "Норма",
  warning: "Внимание",
  danger: "Опасно",
};
const statusOrder: Record<Exclude<DeckStatusFilter, "all">, number> = {
  danger: 4,
  warning: 3,
  normal: 2,
  good: 1,
};

function DecksPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<DeckStatusFilter>("all");
  const [sortKey, setSortKey] = useState<DeckSortKey>("status");
  const [direction, setDirection] = useState<SortDirection>("desc");
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);

  const rows = useMemo(() => buildDeckHealthRows(report?.decks ?? []), [report?.decks]);
  const counts = useMemo(() => countDeckStatuses(rows), [rows]);
  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return rows
      .filter((deck) => filter === "all" || deck.health.statusLabel === filter)
      .filter((deck) => safeText(deck.name, "").toLowerCase().includes(normalizedQuery))
      .sort((a, b) => compareDeckRows(a, b, sortKey, direction));
  }, [direction, filter, query, rows, sortKey]);
  const totalReviews = rows.reduce((sum, deck) => sum + finiteNumber(deck.totalReviews), 0);
  const averagePassRate = weightedAverage(rows.map((deck) => [deck.health.passRate, deck.health.totalReviews]));
  const averageAnswerTime = averageNumber(rows.map((deck) => deck.health.averageAnswerSeconds));

  const requestSort = (key: DeckSortKey) => {
    if (sortKey === key) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setDirection(key === "passRate" ? "asc" : "desc");
  };

  if (loadState !== "ready") {
    return <DecksLoadState state={loadState} />;
  }

  if (!report || rows.length === 0) {
    return (
      <DecksShell totalDecks={0} counts={counts}>
        <EmptyDecksState title="Нет колод" text="В отчёте пока нет разбивки по колодам. После публикации отчёта с повторениями здесь появится здоровье колод." />
      </DecksShell>
    );
  }

  return (
    <DecksShell totalDecks={rows.length} counts={counts}>
      <section className="grid min-w-0 grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <SummaryCard label="Всего колод" value={formatInteger(rows.length)} status="neutral" />
        <SummaryCard label="Хорошие колоды" value={formatInteger(counts.good)} status="good" />
        <SummaryCard label="Требуют внимания" value={formatInteger(counts.warning)} status="warning" />
        <SummaryCard label="Опасная зона" value={formatInteger(counts.danger)} status="danger" />
        <SummaryCard label="Средняя успешность" value={formatPercent(averagePassRate)} status={counts.danger ? "danger" : counts.warning ? "warning" : "good"} />
        <SummaryCard label="Средний ответ" value={formatSeconds(averageAnswerTime)} status="neutral" />
        <SummaryCard label="Повторений сегодня" value={formatInteger(totalReviews)} status={totalReviews > 0 ? "neutral" : "warning"} />
      </section>

      {totalReviews <= 0 && (
        <EmptyDecksState title="Нет повторений сегодня" text="Колодам пока нельзя поставить сильный статус: за текущий отчёт нет повторений." />
      )}

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-normal">Состояние колод</h2>
            <p className="mt-1 text-sm text-report-muted">Поиск, фильтр и сортировка по текущим метрикам колод.</p>
          </div>
          <div className="flex flex-col gap-3 md:flex-row">
            <label className="relative block md:w-80">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="form-control w-full py-2.5 pl-10 pr-3 text-sm"
                placeholder="Найти колоду"
              />
            </label>
            <label className="relative block md:w-52">
              <select
                value={filter}
                onChange={(event) => setFilter(event.target.value as DeckStatusFilter)}
                className="form-control w-full appearance-none px-3 py-2.5 pr-9 text-sm"
              >
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
            </label>
          </div>
        </div>

        {filteredRows.length ? (
          <div className="overflow-x-auto rounded-lg border border-ink-700">
            <table className="table-readable w-full min-w-[1180px] border-collapse">
              <thead className="sticky top-0 z-10 bg-ink-800 text-xs uppercase tracking-[0.04em] text-report-muted">
                <tr>
                  <th className="px-3 py-3 text-left">Колода</th>
                  <DeckSortHeader label="Повторения" sortKey="totalReviews" activeKey={sortKey} direction={direction} onSort={requestSort} />
                  <th className="px-3 py-3 text-right">Новые</th>
                  <DeckSortHeader label="Успешность" sortKey="passRate" activeKey={sortKey} direction={direction} onSort={requestSort} />
                  <DeckSortHeader label="Ошибки / доля" sortKey="failRate" activeKey={sortKey} direction={direction} onSort={requestSort} />
                  <DeckSortHeader label="Средний ответ" sortKey="averageAnswerSeconds" activeKey={sortKey} direction={direction} onSort={requestSort} />
                  <DeckSortHeader label="Статус" sortKey="status" activeKey={sortKey} direction={direction} onSort={requestSort} align="left" />
                  <th className="px-3 py-3 text-left">Причина</th>
                  <th className="px-3 py-3 text-left">Что делать</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((deck) => (
                  <Fragment key={deck.id}>
                    <tr
                      className="cursor-pointer border-t border-ink-700/80 transition hover:bg-ink-800/45"
                      onClick={() => setSelectedDeckId((current) => (current === deck.id ? null : deck.id))}
                    >
                      <td className="max-w-[280px] px-3 py-3.5">
                        <div className="truncate font-semibold text-report-text" title={safeText(deck.name)}>
                          {safeText(deck.name)}
                        </div>
                        {!deck.health.hasEnoughData && <p className="mt-1 text-xs text-report-muted">Предварительная оценка</p>}
                      </td>
                      <td className="px-3 py-3.5 text-right tabular-nums">{formatInteger(deck.totalReviews)}</td>
                      <td className="px-3 py-3.5 text-right tabular-nums">{formatInteger(deck.newCards)}</td>
                      <td className="px-3 py-3.5 text-right tabular-nums">{formatPercent(deck.health.passRate)}</td>
                      <td className="px-3 py-3.5 text-right tabular-nums">
                        {formatInteger(deck.failCount)} / {formatPercent(deck.health.failRate)}
                      </td>
                      <td className="px-3 py-3.5 text-right tabular-nums">{formatCompactSeconds(deck.health.averageAnswerSeconds)}</td>
                      <td className="px-3 py-3.5">
                        <StatusPill status={deck.health.status}>{deckStatusText(deck.health.statusLabel)}</StatusPill>
                      </td>
                      <td className="max-w-[300px] px-3 py-3.5 text-report-muted">{deck.health.reason}</td>
                      <td className="max-w-[260px] px-3 py-3.5 text-report-muted">{deck.health.action}</td>
                    </tr>
                    {selectedDeckId === deck.id && (
                      <tr className="border-t border-ink-700/80 bg-ink-900/35">
                        <td colSpan={9} className="px-3 py-4">
                          <DeckDetails deck={deck} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyDecksState title="Ничего не найдено" text="Поиск или фильтр скрыли все колоды. Измените запрос или статус." />
        )}
      </section>

    </DecksShell>
  );
}

function DecksShell({
  totalDecks,
  counts,
  children,
}: {
  totalDecks: number;
  counts: { good: number; normal: number; warning: number; danger: number };
  children: ReactNode;
}) {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5">
      <header className="min-w-0 rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Колоды</h1>
            <p className="mt-2 text-sm leading-6 text-report-muted">Состояние колод, качество ответов и проблемные зоны.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status="neutral">{formatInteger(totalDecks)} колод</StatusPill>
            <StatusPill status="good">хорошо {formatInteger(counts.good)}</StatusPill>
            <StatusPill status="neutral">норма {formatInteger(counts.normal)}</StatusPill>
            <StatusPill status="warning">внимание {formatInteger(counts.warning)}</StatusPill>
            <StatusPill status="danger">опасно {formatInteger(counts.danger)}</StatusPill>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

function DeckDetails({ deck }: { deck: DeckHealthRow }) {
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold tracking-normal text-report-text">{safeText(deck.name)}</h2>
            <StatusPill status={deck.health.status}>{deckStatusText(deck.health.statusLabel)}</StatusPill>
          </div>
          <p className="mt-2 text-sm leading-6 text-report-muted">{deck.health.reason}</p>
        </div>
        <p className="rounded-lg border border-report-blue/35 bg-report-blue/10 px-3 py-2 text-sm text-report-text">
          {deck.health.action}
        </p>
      </div>
      <div className="mt-4 grid min-w-0 grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-3">
        <DetailMetric label="Повторения" value={formatInteger(deck.totalReviews)} />
        <DetailMetric label="Новые" value={formatInteger(deck.newCards)} />
        <DetailMetric label="Pass" value={formatInteger(deck.passCount)} />
        <DetailMetric label="Fail" value={formatInteger(deck.failCount)} tone={deck.health.status === "danger" ? "danger" : "neutral"} />
        <DetailMetric label="Hard / Easy" value={`${formatInteger(deck.hardCount)} / ${formatInteger(deck.easyCount)}`} />
        <DetailMetric label="Время учёбы" value={`${formatInteger(deck.studyMinutes)} мин`} />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <InfoBox title="Качество" text={`Pass ${formatPercent(deck.health.passRate)}, fail ${formatPercent(deck.health.failRate)}.`} status={deck.health.status} />
        <InfoBox title="Скорость" text={`Средний ответ: ${formatSeconds(deck.health.averageAnswerSeconds)}.`} status="neutral" />
        <InfoBox
          title="История"
          text="История по дням для конкретной колоды пока не передается API, поэтому график не рисуется."
          status="neutral"
        />
      </div>
      {safeText(deck.explanation, "") && (
        <p className="mt-4 rounded-lg border border-ink-700 bg-ink-900/45 p-3 text-sm leading-6 text-report-muted">
          Исходное пояснение отчёта: {deck.explanation}
        </p>
      )}
    </section>
  );
}

function SummaryCard({ label, value, status }: { label: string; value: string; status: DeckHealthStatus }) {
  return (
    <article className={`kpi-card min-h-[112px] status-${status}`}>
      <p className="text-[13px] font-medium uppercase leading-5 tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-3 break-words text-2xl font-semibold leading-8 text-report-text">{value}</p>
    </article>
  );
}

function DetailMetric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: DeckHealthStatus }) {
  return (
    <div className={`rounded-lg border border-ink-700 bg-ink-900/45 p-3 status-border-${tone}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-report-text">{value}</p>
    </div>
  );
}

function InfoBox({ title, text, status }: { title: string; text: string; status: DeckHealthStatus }) {
  return (
    <div className={`rounded-lg border bg-ink-900/45 p-3 status-border-${status}`}>
      <p className="text-sm font-semibold text-report-text">{title}</p>
      <p className="mt-1 text-sm leading-6 text-report-muted">{text}</p>
    </div>
  );
}

function DecksLoadState({ state }: { state: LoadState }) {
  const title =
    state === "loading"
      ? "Загрузка колод"
      : state === "empty"
        ? "Отчёт ещё не опубликован"
        : state === "forbidden"
          ? "Недействительная ссылка дашборда"
          : "Не удалось загрузить колоды";
  const text =
    state === "loading"
      ? "Проверяю локальный API дашборда."
      : state === "empty"
        ? "Откройте основное окно Anki Study Report и опубликуйте отчёт в дашборде."
        : state === "forbidden"
          ? "Откройте дашборд из Anki Study Report, чтобы получить действующий token."
          : "Локальный API дашборда не вернул разбивку по колодам.";
  return <EmptyDecksState title={title} text={text} />;
}

function EmptyDecksState({ title, text }: { title: string; text: string }) {
  return (
    <section className="rounded-xl border border-dashed border-ink-700 bg-ink-850 p-5 text-center shadow-panel">
      <h2 className="text-lg font-semibold tracking-normal text-report-text">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-report-muted">{text}</p>
    </section>
  );
}

function DeckSortHeader({
  label,
  sortKey,
  activeKey,
  direction,
  align = "right",
  onSort,
}: {
  label: string;
  sortKey: DeckSortKey;
  activeKey: DeckSortKey;
  direction: SortDirection;
  align?: "left" | "right";
  onSort: (key: DeckSortKey) => void;
}) {
  const active = sortKey === activeKey;
  return (
    <th className={`px-3 py-3 ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex w-full items-center gap-1 hover:text-report-blue ${align === "right" ? "justify-end" : "justify-start"}`}
      >
        <span>{label}</span>
        <span aria-hidden="true">{active ? (direction === "asc" ? "↑" : "↓") : "↕"}</span>
      </button>
    </th>
  );
}

function StatusPill({ status, children }: { status: DeckHealthStatus; children: ReactNode }) {
  return <span className={`status-pill status-${status}`}>{children}</span>;
}

function deckStatusText(status: DeckStatusFilter) {
  return statusLabels[status] ?? status;
}

function compareDeckRows(a: DeckHealthRow, b: DeckHealthRow, key: DeckSortKey, direction: SortDirection) {
  const result = rawSortValue(a, key) - rawSortValue(b, key);
  return direction === "asc" ? result : -result;
}

function rawSortValue(deck: DeckHealthRow, key: DeckSortKey) {
  if (key === "status") {
    return statusOrder[deck.health.statusLabel];
  }
  if (key === "passRate") {
    return deck.health.passRate ?? -1;
  }
  if (key === "failRate") {
    return deck.health.failRate ?? -1;
  }
  if (key === "averageAnswerSeconds") {
    return deck.health.averageAnswerSeconds ?? -1;
  }
  return deck.health.totalReviews;
}

function weightedAverage(values: Array<[number | null, number]>): number | null {
  const totals = values.reduce(
    (acc, [value, weight]) => {
      const normalizedWeight = Math.max(0, finiteNumber(weight));
      if (value !== null && normalizedWeight > 0) {
        acc.weight += normalizedWeight;
        acc.value += value * normalizedWeight;
      }
      return acc;
    },
    { value: 0, weight: 0 },
  );
  if (totals.weight <= 0) {
    return averageRate(values.map(([value]) => value));
  }
  return totals.value / totals.weight;
}

export default DecksPage;
