import {
  Clipboard,
  ChevronDown,
  CheckCircle2,
  ExternalLink,
  FolderSearch,
  Home,
  Loader2,
  RotateCcw,
  Search,
  Wand2,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  buildCardAttentionRows,
  buildCardBrowserSearch,
  cardAttentionState,
  cardIssueLabels,
  DEFAULT_CARD_FILTERS,
  explainCardAttentionEmptyState,
  filterCardAttentionRows,
  missingCardIssueTypes,
  reportTodayDate,
  summarizeCardAttentionRows,
  type CardAttentionAvailability,
  type CardsIssueFilter,
  type CardsPeriodFilter,
  type CardsSortKey,
} from "../lib/cardAttention";
import { dashboardToken, runReportAction, type ActionResponse } from "../lib/actionsApi";
import { AnkiCardShadowPreview } from "../components/AnkiCardShadowPreview";
import { finiteNumber, formatCompactSeconds, formatInteger, formatPercent, safeText } from "../lib/formatters";
import type { LoadState } from "./HomePage";
import type { CardAttention, CardIssueType, NoteTypeCatalogItem, Status, StudyReport } from "../types/report";

type CardsTab = "risk" | "gaps" | "patterns" | "check";
type FloatingStatusState = "idle" | "applying" | "applied" | "saving" | "saved" | "rebuilding" | "rebuilt" | "error";
type CardsDisplayMode = "table" | "tiles" | "ankiPreview";
const CARDS_DISPLAY_MODE_STORAGE_KEY = "anki-study-report.cards.displayMode";
const BULK_OPEN_LIMIT = 100;
const BULK_OPEN_MAX_QUERY_LENGTH = 1800;

const periodOptions: Array<{ value: CardsPeriodFilter; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "7d", label: "7 дней" },
  { value: "30d", label: "30 дней" },
  { value: "all", label: "Всё время" },
];

const issueOptions: Array<{ value: CardsIssueFilter; label: string }> = [
  { value: "all", label: "Все проблемы" },
  ...Object.entries(cardIssueLabels).map(([value, label]) => ({ value: value as CardIssueType, label })),
];

const sortOptions: Array<{ value: CardsSortKey; label: string }> = [
  { value: "risk", label: "Риск" },
  { value: "again", label: "Частые Again" },
  { value: "lapses", label: "Срывы" },
  { value: "avgAnswer", label: "Долгий ответ" },
  { value: "lastReviewed", label: "Последний повтор" },
];

function CardsPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const [period, setPeriod] = useState<CardsPeriodFilter>("7d");
  const [deck, setDeck] = useState("all");
  const [issue, setIssue] = useState<CardsIssueFilter>("all");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<CardsSortKey>("risk");
  const [tab, setTab] = useState<CardsTab>("risk");
  const [actionStatus, setActionStatus] = useState<ActionResponse | null>(null);
  const [rowStatus, setRowStatus] = useState<Record<string, string>>({});
  const [isOpening, setIsOpening] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [displayMode, setDisplayMode] = useState<CardsDisplayMode>(() => readDisplayMode());
  const [floatingStatus, setFloatingStatus] = useState<{ state: FloatingStatusState; reason?: string } | null>(null);
  const filtersTouched = useRef(false);

  const rows = useMemo(() => buildCardAttentionRows(report), [report]);
  const today = useMemo(() => reportTodayDate(report), [report]);
  const problemDecks = useMemo(() => (report?.decks ?? []).filter((item) => item.status === "danger" || item.status === "warning"), [report?.decks]);
  const deckOptions = useMemo(() => {
    const names = new Set<string>();
    for (const row of rows) {
      names.add(row.deckName);
    }
    for (const item of report?.decks ?? []) {
      names.add(item.name);
    }
    return [...names].sort((a, b) => a.localeCompare(b, "ru"));
  }, [report?.decks, rows]);
  const filteredRows = useMemo(
    () => filterCardAttentionRows(rows, { period, deck, issue, query, sortKey }, { today }),
    [deck, issue, period, query, rows, sortKey, today],
  );
  const tabRows = useMemo(() => rowsForTab(filteredRows, tab), [filteredRows, tab]);
  const summary = useMemo(() => summarizeCardAttentionRows(filteredRows), [filteredRows]);
  const reportReady = loadState === "ready" && Boolean(report);
  const tokenAvailable = dashboardToken().length > 0;
  const attentionState = useMemo(() => cardAttentionState(report), [report]);
  const cardLevelSourceAvailable = attentionState.status === "available";
  const cardLevelError = attentionState.status === "error";
  const cardKpiValue = (value: number) => (cardLevelSourceAvailable ? formatInteger(value) : "—");
  const emptyExplanation = useMemo(() => explainCardAttentionEmptyState(attentionState), [attentionState]);

  useEffect(() => {
    if (!filtersTouched.current) {
      filtersTouched.current = true;
      return;
    }
    let pendingTimer: number | undefined;
    let successTimer: number | undefined;
    let hideTimer: number | undefined;
    pendingTimer = window.setTimeout(() => {
      setFloatingStatus({ state: "applying" });
    }, 300);
    successTimer = window.setTimeout(() => {
      setFloatingStatus({ state: "applied" });
      hideTimer = window.setTimeout(() => setFloatingStatus(null), 2400);
    }, 520);
    return () => {
      window.clearTimeout(pendingTimer);
      window.clearTimeout(successTimer);
      window.clearTimeout(hideTimer);
    };
  }, [deck, issue, period, query, sortKey, tab]);

  useEffect(() => {
    window.localStorage.setItem(CARDS_DISPLAY_MODE_STORAGE_KEY, displayMode);
  }, [displayMode]);

  const resetFilters = () => {
    setPeriod(DEFAULT_CARD_FILTERS.period);
    setDeck(DEFAULT_CARD_FILTERS.deck);
    setIssue(DEFAULT_CARD_FILTERS.issue);
    setQuery(DEFAULT_CARD_FILTERS.query);
    setSortKey(DEFAULT_CARD_FILTERS.sortKey);
    setTab("risk");
  };

  const openProblemDecks = async (): Promise<boolean> => {
    if (!reportReady || !tokenAvailable) {
      setActionStatus({
        ok: false,
        action: "open-browser",
        error: !tokenAvailable ? "Откройте дашборд из Anki Study Report, чтобы получить действующую ссылку." : "Отчёт ещё не построен.",
      });
      return false;
    }
    setIsOpening(true);
    try {
      const response = await runReportAction("open-browser", { kind: "problematic-decks" });
      setActionStatus(response);
      return response.ok;
    } catch {
      setActionStatus({ ok: false, action: "open-browser", error: "Не удалось открыть Anki Browser." });
      return false;
    } finally {
      setIsOpening(false);
    }
  };

  const copySearch = async (row: CardAttention) => {
    const search = buildCardBrowserSearch(row);
    try {
      await navigator.clipboard.writeText(search);
      setRowStatus((current) => ({ ...current, [row.id]: "Запрос поиска скопирован." }));
    } catch {
      setRowStatus((current) => ({ ...current, [row.id]: search }));
    }
  };

  const openRow = async (row: CardAttention) => {
    const search = buildCardBrowserSearch(row);
    if (!tokenAvailable) {
      setRowStatus((current) => ({ ...current, [row.id]: "Нет действующей ссылки дашборда. Запрос поиска скопирован." }));
      await copySearch(row);
      return;
    }
    setRowStatus((current) => ({ ...current, [row.id]: `Открываю ${search}` }));
    const response = await runReportAction("open-browser-search", { query: search });
    setActionStatus(response);
    setRowStatus((current) => ({
      ...current,
      [row.id]: response.ok ? `Открыто в Anki Browser: ${search}` : response.error || `Не удалось открыть: ${search}`,
    }));
  };

  const openFilteredRows = async () => {
    if (!tokenAvailable) {
      setActionStatus({ ok: false, action: "open-browser-search", error: "Откройте дашборд из Anki Study Report, чтобы получить действующую ссылку." });
      return;
    }
    const queries = tabRows.slice(0, BULK_OPEN_LIMIT).map((row) => buildCardBrowserSearch(row)).filter(Boolean);
    const uniqueQueries = [...new Set(queries)];
    if (!uniqueQueries.length) {
      setActionStatus({ ok: false, action: "open-browser-search", error: "Нет карточек для открытия после текущих фильтров." });
      return;
    }
    const bulkQuery = uniqueQueries.length === 1 ? uniqueQueries[0] : uniqueQueries.map((item) => `(${item})`).join(" OR ");
    if (bulkQuery.length > BULK_OPEN_MAX_QUERY_LENGTH) {
      await navigator.clipboard?.writeText(bulkQuery).catch(() => undefined);
      setActionStatus({
        ok: false,
        action: "open-browser-search",
        error: `Запрос для прямого открытия слишком длинный. Поиск для ${uniqueQueries.length} карточек скопирован.`,
      });
      return;
    }
    const response = await runReportAction("open-browser-search", { query: bulkQuery });
    setActionStatus(response);
  };

  return (
    <div className="grid min-w-0 gap-5">
      <CardsHero
        reportReady={reportReady}
        cardLevelAvailable={cardLevelSourceAvailable}
        cardLevelStatus={attentionState.status}
        problemDeckCount={problemDecks.length}
        isOpening={isOpening}
        actionStatus={actionStatus}
        onOpenProblemDecks={openProblemDecks}
      />

      <section className="grid min-w-0 grid-cols-[repeat(auto-fit,minmax(155px,1fr))] gap-3">
        <SummaryCard label="Требуют внимания" value={cardKpiValue(summary.problemCards)} description="Все карточки, попавшие в список проверки." status={cardLevelSourceAvailable && summary.problemCards ? "danger" : "neutral"} />
        <SummaryCard label="Leech" value={cardKpiValue(summary.leech)} description="Карточки с частыми срывами." status={cardLevelSourceAvailable && summary.leech ? "danger" : "neutral"} />
        <SummaryCard label="Частые Again" value={cardKpiValue(summary.repeatedAgain)} description="Повторяющиеся ошибки в выбранном наборе." status={cardLevelSourceAvailable && summary.repeatedAgain ? "danger" : "neutral"} />
        <SummaryCard label="Долго вспоминаются" value={cardKpiValue(summary.slowAnswer)} description="Ответ занимает заметно больше времени." status={cardLevelSourceAvailable && summary.slowAnswer ? "warning" : "neutral"} />
        <SummaryCard label="Неполные карточки" value={cardKpiValue(summary.dataGaps)} description="Не хватает аудио, примера, изображения или смысла." status={cardLevelSourceAvailable && summary.dataGaps ? "warning" : "neutral"} />
      </section>

      {cardLevelSourceAvailable ? <CardsPreviewSettingsNotice rows={rows} report={report} displayMode={displayMode} /> : null}

      {cardLevelError ? (
        <section className="rounded-xl border border-report-danger/45 bg-report-danger/10 p-4 text-sm leading-6 text-report-text shadow-panel">
          Не удалось собрать данные по карточкам. Используется запасной режим по колодам.
        </section>
      ) : null}

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_220px_220px_220px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="form-control w-full py-2.5 pl-10 pr-3 text-sm"
              placeholder="Поиск по тексту карточки"
            />
          </label>
          <SelectControl label="Период" value={period} onChange={(value) => setPeriod(value as CardsPeriodFilter)}>
            {periodOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectControl>
          <SelectControl label="Проблема" value={issue} onChange={(value) => setIssue(value as CardsIssueFilter)}>
            {issueOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectControl>
          <SelectControl label="Сортировка" value={sortKey} onChange={(value) => setSortKey(value as CardsSortKey)}>
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectControl>
        </div>
        <div className="mt-3">
          <SelectControl label="Колода" value={deck} onChange={setDeck}>
            <option value="all">Все колоды</option>
            {deckOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </SelectControl>
        </div>
        <div className="mt-3 flex flex-col gap-2 text-xs leading-5 text-report-muted sm:flex-row sm:items-center sm:justify-between">
          <p>
            Показано {formatInteger(filteredRows.length)} карточек · период: {periodLabel(period)} · проблема: {issueLabel(issue)} · сортировка: {sortLabel(sortKey)}
          </p>
          <button type="button" className="toolbar-button w-fit px-3 py-1.5 text-xs" onClick={resetFilters}>
            Сбросить фильтры
          </button>
        </div>
        <p className="mt-2 text-xs leading-5 text-report-muted">
          Период применён к уже собранным данным по карточкам: строки фильтруются локально по последнему повтору, риск и Again за период не пересчитываются.
        </p>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <Tabs active={tab} onChange={setTab} counts={tabCounts(filteredRows)} />
          <div className="flex flex-wrap items-center gap-2">
            <DisplayModeSwitcher value={displayMode} onChange={setDisplayMode} />
            <button type="button" className="toolbar-button" onClick={openFilteredRows} disabled={!cardLevelSourceAvailable || tabRows.length === 0}>
              Открыть все отфильтрованные
            </button>
            <StatusPill status={cardLevelSourceAvailable ? "good" : "warning"}>
              {cardLevelSourceAvailable ? `${formatInteger(filteredRows.length)} после фильтров` : "данные по карточкам недоступны"}
            </StatusPill>
          </div>
        </div>
        {cardLevelSourceAvailable && tabRows.length > 0 ? (
          <p className="mt-3 text-xs leading-5 text-report-muted">
            Будет открыто до {formatInteger(Math.min(tabRows.length, BULK_OPEN_LIMIT))} карточек из текущего списка. Кнопка в строке открывает только одну карточку.
          </p>
        ) : null}

        <div className="mt-4">
          {loadState !== "ready" || !report ? (
            <CardsEmptyState title="Отчёт ещё не построен" text={loadStateText(loadState)} />
          ) : tab === "check" && deck === "all" ? (
            <CardsEmptyState title="Выберите колоду" text="Для проверки безопаснее сузить область до одной колоды: так список пропусков и паттернов не смешивается." />
          ) : !cardLevelSourceAvailable ? (
            <CardLevelPlannedState problemDecks={problemDecks.length} statusReason={attentionState.reason} />
          ) : rows.length === 0 ? (
            <CardLevelEmptyState
              explanation={emptyExplanation}
              attentionState={attentionState}
              report={report}
              period={period}
              deck={deck}
              issue={issue}
              showDiagnostics={showDiagnostics}
              onToggleDiagnostics={() => setShowDiagnostics((value) => !value)}
              onResetFilters={resetFilters}
              onOpenProblemDecks={openProblemDecks}
            />
          ) : filteredRows.length === 0 ? (
            <CardLevelEmptyState
              explanation={{
                ...emptyExplanation,
                title: period === "all" ? "Нет проблемных карточек" : "Нет данных за выбранный период",
                text:
                  period === "today"
                    ? "За сегодня в опубликованных данных по карточкам нет строк. Риск и Again локально не пересчитываются."
                    : "Фильтры скрыли все карточки. Сбросьте фильтры или выберите Всё время.",
              }}
              attentionState={attentionState}
              report={report}
              period={period}
              deck={deck}
              issue={issue}
              showDiagnostics={showDiagnostics}
              onToggleDiagnostics={() => setShowDiagnostics((value) => !value)}
              onResetFilters={resetFilters}
              onOpenProblemDecks={openProblemDecks}
            />
          ) : tabRows.length === 0 ? (
            <CardsEmptyState title={emptyTitleForTab(tab)} text="В этой вкладке нет карточек после текущих фильтров." />
          ) : displayMode === "table" ? (
            <RiskTable rows={tabRows} rowStatus={rowStatus} onCopySearch={copySearch} onOpenRow={openRow} />
          ) : displayMode === "tiles" ? (
            <CardTiles rows={tabRows} tab={tab} rowStatus={rowStatus} onCopySearch={copySearch} onOpenRow={openRow} />
          ) : (
            <AnkiPreviewGrid rows={tabRows} rowStatus={rowStatus} onCopySearch={copySearch} onOpenRow={openRow} />
          )}
        </div>
      </section>
      <FloatingStatusIndicator status={floatingStatus} onRetry={() => setFloatingStatus({ state: "applying" })} />
    </div>
  );
}

function CardLevelEmptyState({
  explanation,
  attentionState,
  report,
  period,
  deck,
  issue,
  showDiagnostics,
  onToggleDiagnostics,
  onResetFilters,
  onOpenProblemDecks,
}: {
  explanation: { title: string; text: string; sourceText: string };
  attentionState: ReturnType<typeof cardAttentionState>;
  report: StudyReport;
  period: CardsPeriodFilter;
  deck: string;
  issue: CardsIssueFilter;
  showDiagnostics: boolean;
  onToggleDiagnostics: () => void;
  onResetFilters: () => void;
  onOpenProblemDecks: () => void;
}) {
  return (
    <section className="rounded-xl border border-dashed border-ink-700 bg-ink-900/35 p-5">
      <div className="mx-auto max-w-5xl text-center">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">{explanation.title}</h2>
        <p className="mx-auto mt-2 max-w-3xl text-sm leading-6 text-report-muted">{explanation.text}</p>
        <p className="mx-auto mt-1 max-w-3xl text-sm leading-6 text-report-muted">{explanation.sourceText}</p>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <button type="button" className="toolbar-button" onClick={onResetFilters}>
          Сбросить фильтры
        </button>
        <button type="button" className="toolbar-button" onClick={onToggleDiagnostics}>
          {showDiagnostics ? "Скрыть диагностику" : "Показать диагностику"}
        </button>
        <button type="button" className="toolbar-button" onClick={onOpenProblemDecks}>
          <FolderSearch size={16} aria-hidden="true" />
          Открыть проблемные колоды
        </button>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <DetailBlock label="Backend scope" value={backendScopeLabel(report)} />
        <DetailBlock label="UI filter" value={`${periodLabel(period)} / ${deck === "all" ? "Все колоды" : deck} / ${issueLabel(issue)}`} />
      </div>
      {showDiagnostics ? <CardLevelDiagnostics state={attentionState} report={report} period={period} /> : null}
    </section>
  );
}

function CardsPreviewSettingsNotice({ rows, report, displayMode }: { rows: CardAttention[]; report: StudyReport | null; displayMode: CardsDisplayMode }) {
  const profiles = useMemo(() => summarizePreviewProfiles(rows), [rows]);
  const catalog = report?.noteTypeCatalog ?? [];
  const currentTypes = catalog.length
    ? catalog.filter((item) => item.usedInCurrentCards).length
    : new Set(profiles.map((profile) => profile.noteTypeName).filter((name) => name && name !== "Unknown")).size;
  return (
    <div className="grid gap-3">
      <section className="rounded-xl border border-ink-700 bg-ink-850/80 p-4 text-sm shadow-panel">
        <h2 className="text-base font-semibold tracking-normal text-report-text">Настройки отображения</h2>
        <p className="mt-2 text-sm leading-6 text-report-muted">
          Сейчас выбран режим «{displayModeLabel(displayMode)}». Переключатель ниже меняет только вид списка, не данные отчёта.
        </p>
      </section>
      <details className="rounded-xl border border-ink-700 bg-ink-850/80 p-4 text-sm shadow-panel">
        <summary className="cursor-pointer font-semibold text-report-text">Диагностика шаблонов</summary>
        <div className="mt-3 grid gap-3 text-sm leading-6 text-report-muted md:grid-cols-2">
          <DetailBlock label="Режим отображения" value={displayModeLabel(displayMode)} compact />
          <DetailBlock label="Превью шаблона" value="Используется безопасный рендер шаблона; при ошибке включается запасной режим" compact />
          <DetailBlock label="Типов записей в коллекции" value={formatInteger(catalog.length || profiles.length)} compact />
          <DetailBlock label="Типов записей в текущем списке" value={formatInteger(currentTypes)} compact />
        </div>
        <div className="mt-3 grid gap-2">
          {(catalog.length ? catalog : profilesToCatalog(profiles)).slice(0, 40).map((item) => (
            <NoteTypeCatalogRow key={`${item.noteTypeId}-${item.name}`} item={item} />
          ))}
        </div>
      </details>
    </div>
  );
}

function NoteTypeCatalogRow({ item }: { item: NoteTypeCatalogItem }) {
  return (
    <details className="rounded-lg border border-ink-700 bg-ink-950/45 px-3 py-2 text-sm">
      <summary className="cursor-pointer list-none">
        <span className="font-medium text-report-text">{item.name || "Неизвестный тип записи"}</span>
        <span className="ml-2 text-report-muted">
          {formatInteger(item.noteCount)} записей · {formatInteger(item.cardTemplateCount)} шаблонов
          {item.usedInCurrentCards ? " · в текущем списке" : ""}
        </span>
      </summary>
      <div className="mt-3 grid gap-3 text-report-muted md:grid-cols-2">
        <DetailBlock label="Поля" value={item.fields.length ? item.fields.join(", ") : "Нет данных"} compact />
        <DetailBlock label="Шаблоны" value={item.templates.length ? item.templates.map((template) => template.name).join(", ") : "Нет данных"} compact />
        <DetailBlock label="Превью шаблона" value={item.templates.length ? "рендер шаблона доступен" : "рендер шаблона недоступен"} compact />
        <DetailBlock label="CSS" value={item.cssAvailable ? "стили карточки доступны" : "стили карточки недоступны"} compact />
      </div>
    </details>
  );
}

function CardLevelDiagnostics({
  state,
  report,
  period,
}: {
  state: ReturnType<typeof cardAttentionState>;
  report: StudyReport;
  period: CardsPeriodFilter;
}) {
  return (
    <div className="mt-4 grid gap-4 text-left">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <DetailBlock label="Статус" value={availabilityLabel(state.status)} />
        <DetailBlock label="Источник" value={sourceLabel(state.source)} />
        <DetailBlock label="Сборщик запускался" value={booleanLabel(state.collectorRan)} />
        <DetailBlock label="Коллекция доступна" value={booleanLabel(state.collectionAvailable)} />
        <DetailBlock label="Период" value={`${report.metadata.period || periodLabel(period)} (${periodLabel(period)})`} />
        <DetailBlock label="Режим периода" value="фильтр на странице" />
        <DetailBlock label="Период в интерфейсе" value={periodLabel(period)} />
        <DetailBlock label="Риск пересчитан" value="нет" />
        <DetailBlock label="Выбранные колоды" value={backendScopeLabel(report)} />
        <DetailBlock label="Просканировано карточек" value={nullableInteger(state.scannedCards)} />
        <DetailBlock label="Карточек-кандидатов" value={nullableInteger(state.candidateCards)} />
        <DetailBlock label="Строк revlog" value={nullableInteger(state.revlogRows)} />
        <DetailBlock label="Вернулось карточек" value={nullableInteger(state.returnedCards)} />
        <DetailBlock label="Всего строк revlog" value={nullableInteger(state.revlogTotalRows)} />
        <DetailBlock label="Минимальный revlog id" value={nullableInteger(state.revlogMinId)} />
        <DetailBlock label="Максимальный revlog id" value={nullableInteger(state.revlogMaxId)} />
        <DetailBlock label="Строк revlog в периоде" value={nullableInteger(state.revlogRowsInPeriod)} />
        <DetailBlock label="Строк после фильтра колоды" value={nullableInteger(state.revlogRowsAfterDeckFilter)} />
        <DetailBlock label="Начало периода, исходное" value={nullableInteger(state.periodStartRaw)} />
        <DetailBlock label="Конец периода, исходное" value={nullableInteger(state.periodEndRaw)} />
        <DetailBlock label="Начало периода, мс" value={nullableInteger(state.periodStartMs)} />
        <DetailBlock label="Конец периода, мс" value={nullableInteger(state.periodEndMs)} />
        <DetailBlock label="Единицы времени нормализованы" value={state.timeUnitNormalized ? "да" : "нет"} />
        <DetailBlock label="Выбранных id колод" value={nullableInteger(state.selectedDeckIdsCount)} />
        <DetailBlock label="Фильтр колоды применён" value={state.deckFilterApplied ? "да" : "нет"} />
        <DetailBlock label="Всего карточек" value={nullableInteger(state.cardsTotal)} />
        <DetailBlock label="Загружено записей" value={nullableInteger(state.notesLoaded)} />
        <DetailBlock label="Профилей типов записей" value={nullableInteger(state.noteTypeProfilesCount)} />
        <DetailBlock label="Неопознанных типов" value={nullableInteger(state.unknownNoteTypesCount)} />
        <DetailBlock label="Стратегия превью" value={state.previewStrategy || "Нет данных"} />
        <DetailBlock label="Источник проверки полей" value={state.missingFieldRoleSource || "Нет данных"} />
        <DetailBlock label="Опознанные типы" value={detectedKindsLabel(state.detectedKinds)} />
      </div>
      {state.diagnosticWarning ? (
        <p className="rounded-lg border border-report-warning/35 bg-report-warning/10 px-3 py-2 text-sm leading-6 text-report-warning">
          {state.diagnosticWarning}
        </p>
      ) : null}
      {state.reason ? (
        <p className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 text-sm leading-6 text-report-muted">
          {state.reason}
        </p>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-2">
        <DiagnosticPanel title="Количество проблем">
          <DetailBlock label="Leech" value={formatInteger(state.issueCounts.leech)} compact />
          <DetailBlock label="Частые Again" value={formatInteger(state.issueCounts.repeatedAgain)} compact />
          <DetailBlock label="Долгий ответ" value={formatInteger(state.issueCounts.slowAnswer)} compact />
          <DetailBlock label="Низкая успешность" value={formatInteger(state.issueCounts.lowPassRate)} compact />
          <DetailBlock label="Нет аудио" value={formatInteger(state.issueCounts.missingAudio)} compact />
          <DetailBlock label="Нет примера" value={formatInteger(state.issueCounts.missingExample)} compact />
          <DetailBlock label="Нет изображения" value={formatInteger(state.issueCounts.missingImage)} compact />
          <DetailBlock label="Нет значения" value={formatInteger(state.issueCounts.missingMeaning)} compact />
          <DetailBlock label="Нет части речи" value={formatInteger(state.issueCounts.missingPartOfSpeech)} compact />
        </DiagnosticPanel>
        <DiagnosticPanel title="Пороги отбора">
          <DetailBlock label="Порог частых Again" value={formatInteger(state.thresholds.repeatedAgainThreshold)} compact />
          <DetailBlock label="Долгий ответ, сек" value={String(state.thresholds.slowAnswerSeconds)} compact />
          <DetailBlock label="Низкая успешность" value={formatPercent(state.thresholds.lowPassRateThreshold)} compact />
          <DetailBlock label="Порог leech по срывам" value={formatInteger(state.thresholds.leechLapsesFallback)} compact />
          <DetailBlock label="Лимит результатов" value={formatInteger(state.thresholds.maxResults)} compact />
        </DiagnosticPanel>
      </div>
    </div>
  );
}

function CardsHero({
  reportReady,
  cardLevelAvailable,
  cardLevelStatus,
  problemDeckCount,
  isOpening,
  actionStatus,
  onOpenProblemDecks,
}: {
  reportReady: boolean;
  cardLevelAvailable: boolean;
  cardLevelStatus: CardAttentionAvailability;
  problemDeckCount: number;
  isOpening: boolean;
  actionStatus: ActionResponse | null;
  onOpenProblemDecks: () => void;
}) {
  return (
    <header className="hero-surface rounded-xl border border-ink-700 p-4 shadow-panel sm:p-5">
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-start">
        <div className="min-w-0">
          <span className={`status-pill ${cardLevelAvailable ? "status-good" : reportReady ? "status-warning" : "status-neutral"}`}>
            {cardLevelAvailable ? "данные по карточкам доступны" : reportReady ? cardLevelStatus === "error" ? "нет данных по карточкам" : "ожидаю данные по карточкам" : "нужен отчёт"}
          </span>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Карточки</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-report-muted">
            Здесь собраны карточки, которые требуют внимания: частые ошибки, leech, долгие ответы, низкая успешность и неполные данные.
          </p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-report-muted">
            Только чтение: здесь можно найти проблему и открыть карточку в Anki, но не редактировать её.
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button type="button" className="toolbar-button justify-center" onClick={onOpenProblemDecks} disabled={!reportReady || isOpening}>
              <FolderSearch size={16} aria-hidden="true" />
              {isOpening ? "Открываю..." : "Открыть проблемные в Anki"}
            </button>
            <button
              type="button"
              className="toolbar-button justify-center"
              aria-label="Перейти в Действия"
              data-href="#/actions"
              onClick={() => {
                window.location.hash = "#/actions";
              }}
            >
              <Wand2 size={16} aria-hidden="true" />
              Перейти в Действия
            </button>
            <a className="toolbar-button justify-center opacity-80" href="#/home">
              <Home size={16} aria-hidden="true" />
              На главную
            </a>
          </div>
          {actionStatus ? (
            <p className={`mt-3 text-sm leading-6 ${actionStatus.ok ? "text-report-success" : "text-report-danger"}`}>
              {actionStatus.ok ? actionStatus.message || "Anki Browser открыт." : actionStatus.error || "Действие не выполнено."}
            </p>
          ) : null}
        </div>
        <aside className="flex flex-wrap gap-2 xl:max-w-[360px] xl:justify-end">
          <StatusPill status={problemDeckCount ? "warning" : "good"}>{formatInteger(problemDeckCount)} проблемных колод</StatusPill>
          <StatusPill status="good">только чтение</StatusPill>
        </aside>
      </div>
    </header>
  );
}

function RiskTable({
  rows,
  rowStatus,
  onCopySearch,
  onOpenRow,
}: {
  rows: CardAttention[];
  rowStatus: Record<string, string>;
  onCopySearch: (row: CardAttention) => void;
  onOpenRow: (row: CardAttention) => void;
}) {
  return (
    <div className="cards-table-wrap overflow-x-auto rounded-lg border border-ink-700" data-testid="cards-table-wrap">
      <table className="cards-risk-table table-readable w-full min-w-[1320px] border-collapse" data-testid="cards-risk-table">
        <thead className="sticky top-0 z-10 bg-ink-800 text-xs uppercase tracking-[0.04em] text-report-muted">
          <tr>
            <th className="text-left">Риск</th>
            <th className="text-left">Карточка</th>
            <th className="text-left">Колода</th>
            <th className="text-left">Проблемы</th>
            <th className="text-right">Again</th>
            <th className="text-right">Провалы</th>
            <th className="text-right">Средний ответ</th>
            <th className="text-left">Последний повтор</th>
            <th className="text-left">Действия</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="cards-risk-row border-t border-ink-700/80 hover:bg-ink-800/45" data-testid="cards-table-row" data-card-id={row.id}>
              <td className="w-[120px]" data-testid="cards-table-risk">
                <RiskBadge score={row.riskScore} />
              </td>
              <td className="cards-preview-table-cell" data-testid="cards-table-preview-cell">
                <CardPreviewCell row={row} />
              </td>
              <td className="max-w-[210px] text-report-muted">
                <span className="line-clamp-2" title={row.deckName}>
                  {row.deckName}
                </span>
              </td>
              <td className="max-w-[240px]" data-testid="cards-table-issues">
                <IssueChips issues={row.issues} />
              </td>
              <td className="w-[72px] text-right tabular-nums">{formatInteger(row.againCount)}</td>
              <td className="w-[78px] text-right tabular-nums">{formatInteger(row.lapses)}</td>
              <td className="w-[112px] text-right tabular-nums">{formatCompactSeconds(row.averageAnswerSeconds)}</td>
              <td className="w-[150px] text-report-muted">{safeText(row.lastReviewed, "Нет данных")}</td>
              <td className="w-[150px]" data-testid="cards-table-actions">
                <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InsightGrid({
  rows,
  tab,
  rowStatus,
  onCopySearch,
  onOpenRow,
}: {
  rows: CardAttention[];
  tab: CardsTab;
  rowStatus: Record<string, string>;
  onCopySearch: (row: CardAttention) => void;
  onOpenRow: (row: CardAttention) => void;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {rows.map((row) => (
        <article key={row.id} className={`rounded-xl border bg-ink-800/55 p-4 status-border-${riskStatus(row.riskScore)}`}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <StatusPill status={riskStatus(row.riskScore)}>{tabLabel(tab)}</StatusPill>
              <h3 className="mt-3 line-clamp-2 text-base font-semibold tracking-normal text-report-text">{cardFrontText(row)}</h3>
              <p className="mt-1 text-sm leading-6 text-report-muted">{row.deckName}</p>
            </div>
            <div className="text-left text-sm text-report-muted sm:text-right">
              <p>Again {formatInteger(row.againCount)}</p>
              <p>срывы {formatInteger(row.lapses)}</p>
              <p>{formatPercent(row.passRate)}</p>
            </div>
          </div>
          <div className="mt-3">
            <IssueChips issues={row.issues} />
          </div>
          <p className="mt-3 text-sm leading-6 text-report-muted">
            {tab === "patterns"
              ? row.answerPattern || "Паттерн ответа пока выводится из Again, срывов, успешности и среднего времени."
              : tab === "gaps"
                ? "Проверьте учебные поля в Anki: дашборд только показывает подозрение и готовый запрос поиска."
                : "Проверочный список для выбранной колоды без редактирования из дашборда."}
          </p>
          <div className="mt-4">
            <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} />
          </div>
        </article>
      ))}
    </div>
  );
}

function CardTiles({
  rows,
  tab,
  rowStatus,
  onCopySearch,
  onOpenRow,
}: {
  rows: CardAttention[];
  tab: CardsTab;
  rowStatus: Record<string, string>;
  onCopySearch: (row: CardAttention) => void;
  onOpenRow: (row: CardAttention) => void;
}) {
  return (
    <div className="cards-tiles-grid grid gap-3 lg:grid-cols-2">
      {rows.map((row) => (
        <article
          key={row.id}
          className={`cards-tile-card rounded-xl border bg-ink-800/55 p-4 status-border-${riskStatus(row.riskScore)}`}
          data-testid="cards-tile"
          data-card-id={row.id}
        >
          <div className="cards-tile-header flex flex-wrap items-center justify-between gap-2" data-testid="cards-tile-header">
            <StatusPill status={riskStatus(row.riskScore)}>риск {formatInteger(row.riskScore)}</StatusPill>
            <span className="text-xs text-report-muted">{tabLabel(tab)}</span>
          </div>
          <div className="cards-tile-preview-slot" data-testid="cards-tile-preview-slot">
            <FrontPreviewFrame row={row} variant="tile" />
          </div>
          <p className="cards-tile-meta line-clamp-2 text-sm leading-6 text-report-muted" data-testid="cards-tile-meta">
            {row.deckName}
          </p>
          <div className="cards-tile-metrics grid grid-cols-3 gap-2 text-xs text-report-muted" data-testid="cards-tile-metrics">
            <DetailMini label="Again" value={formatInteger(row.againCount)} />
            <DetailMini label="срывы" value={formatInteger(row.lapses)} />
            <DetailMini label="успех" value={formatPercent(row.passRate)} />
          </div>
          <div className="cards-tile-issues" data-testid="cards-tile-issues">
            <IssueChips issues={row.issues} />
          </div>
          <div className="cards-tile-actions" data-testid="cards-tile-actions">
            <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} compact />
          </div>
        </article>
      ))}
    </div>
  );
}

function AnkiPreviewGrid({
  rows,
  rowStatus,
  onCopySearch,
  onOpenRow,
}: {
  rows: CardAttention[];
  rowStatus: Record<string, string>;
  onCopySearch: (row: CardAttention) => void;
  onOpenRow: (row: CardAttention) => void;
}) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-4">
        {rows.map((row) => (
          <article key={row.id} className={`cards-anki-preview-card rounded-xl border bg-ink-800/55 p-4 status-border-${riskStatus(row.riskScore)}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <StatusPill status={riskStatus(row.riskScore)}>риск {formatInteger(row.riskScore)}</StatusPill>
              <span className="text-xs text-report-muted">{row.preview?.noteTypeName || row.preview?.detectedKind || "авто-превью"}</span>
            </div>
            <AnkiPreviewBox row={row} />
            <div className="cards-anki-preview-issues mt-3">
              <IssueChips issues={row.issues} />
            </div>
            <div className="cards-anki-preview-actions mt-4">
              <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} compact />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AnkiPreviewBox({ row }: { row: CardAttention }) {
  const rendered = row.renderedPreview;
  const canRenderFront = canRenderFrontHtml(row);
  const canRenderBack = canRenderBackHtml(row);
  if (canRenderBack || canRenderFront) {
    const usesAnswerFallback = !canRenderBack;
    const previewHtml = canRenderBack ? rendered?.backHtml || "" : rendered?.frontHtml || "";
    return (
      <div className="asr-card-rendered asr-front-preview asr-anki-preview-panel mt-3 grid gap-3">
        <PreviewSection title="Вид после ответа" testId="anki-preview-answer" side="answer">
          <AnkiCardShadowPreview
            mode="preview"
            side="answer"
            html={htmlWithMediaToken(previewHtml)}
            css={rendered?.css || ""}
            title={canRenderBack ? rendered?.backPlainText || cardFrontText(row) : cardFrontText(row)}
            cardOrd={rendered?.cardOrd || 0}
            renderSource={rendered?.renderSource || ""}
            className="asr-front-preview-anki asr-front-preview-anki-answer min-w-0"
          />
          {usesAnswerFallback ? (
            <p className="asr-preview-fallback-note mt-2 text-xs leading-5 text-report-muted">
              Ответ недоступен, показана лицевая сторона{rendered?.reason || rendered?.fallbackReason ? `: ${rendered.reason || rendered.fallbackReason}` : "."}
            </p>
          ) : null}
        </PreviewSection>
      </div>
    );
  }
  return (
    <div className="asr-card-rendered asr-front-preview asr-anki-preview-panel mt-3 grid gap-3 rounded-lg border border-ink-700 bg-ink-950 p-4">
      <p className="w-fit rounded-md border border-ink-700 bg-ink-900/70 px-2 py-0.5 text-xs text-report-muted">Упрощённое превью</p>
      <PreviewSection title="Вид после ответа" testId="anki-preview-answer" side="answer">
        <PlainPreviewText text={cardFrontText(row)} />
        <p className="asr-preview-fallback-note mt-2 text-xs leading-5 text-report-muted">Ответ недоступен, показана лицевая сторона.</p>
      </PreviewSection>
      {rendered?.reason ? <p className="text-xs leading-5 text-report-muted">{rendered.reason}</p> : null}
    </div>
  );
}

function PreviewSection({ title, children, testId, side }: { title: string; children: ReactNode; testId?: string; side?: "front" | "back" | "answer" }) {
  const overflowClass = side === "answer" ? "overflow-visible" : "overflow-hidden";
  return (
    <section
      className={`asr-preview-section min-h-[78px] ${overflowClass} rounded-md border border-ink-700 bg-ink-900/45 p-3`}
      data-testid={testId}
      data-preview-side={side}
    >
      <h3 className="text-xs font-semibold uppercase tracking-[0.04em] text-report-muted">{title}</h3>
      <div className="asr-preview-section-body mt-2">{children}</div>
    </section>
  );
}

function PlainPreviewText({ text, muted = false }: { text: string; muted?: boolean }) {
  return <p className={`whitespace-pre-wrap text-sm leading-6 ${muted ? "text-report-muted" : "text-report-text"}`}>{text || "Нет данных"}</p>;
}

function DetailMini({ label, value }: { label: string; value: string }) {
  return (
    <div className="cards-tile-metric rounded-lg border border-ink-700 bg-ink-900/45 px-2 py-1.5">
      <p className="uppercase tracking-[0.04em]">{label}</p>
      <p className="mt-0.5 font-semibold text-report-text">{value}</p>
    </div>
  );
}

function DisplayModeSwitcher({ value, onChange }: { value: CardsDisplayMode; onChange: (mode: CardsDisplayMode) => void }) {
  const options: Array<{ value: CardsDisplayMode; label: string }> = [
    { value: "table", label: "Таблица" },
    { value: "tiles", label: "Плитки" },
    { value: "ankiPreview", label: "Превью Anki" },
  ];
  return (
    <div className="flex flex-wrap gap-1 rounded-lg border border-ink-700 bg-ink-900/45 p-1" aria-label="Режим отображения карточек">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            value === option.value ? "bg-report-blue/25 text-report-text" : "text-report-muted hover:bg-ink-800 hover:text-report-text"
          }`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function CardPreviewCell({ row }: { row: CardAttention }) {
  return <FrontPreviewFrame row={row} variant="table" />;
}

function FrontPreviewFrame({ row, variant, className = "" }: { row: CardAttention; variant: "table" | "tile"; className?: string }) {
  const front = cardFrontText(row);
  if (canRenderFrontHtml(row)) {
    return (
      <AnkiCardShadowPreview
        mode={variant}
        html={htmlWithMediaToken(row.renderedPreview?.frontHtml || "")}
        css={row.renderedPreview?.css || ""}
        title={front}
        cardOrd={row.renderedPreview?.cardOrd || 0}
        renderSource={row.renderedPreview?.renderSource || ""}
        className={`asr-card-rendered asr-front-preview asr-front-preview-${variant} min-w-0 ${className}`}
      />
    );
  }
  return (
    <div className={`min-w-0 ${className}`}>
      <div className={variant === "table" ? "line-clamp-2 font-semibold text-report-text" : "line-clamp-2 text-base font-semibold tracking-normal text-report-text"} title={front}>
        {front}
      </div>
    </div>
  );
}

function FrontPreviewHtml({ row }: { row: CardAttention }) {
  const html = row.renderedPreview?.frontHtml;
  if (!html) {
    return <PlainPreviewText text={cardFrontText(row)} />;
  }
  return <div className="asr-front-preview-html text-sm leading-6 text-report-text" dangerouslySetInnerHTML={{ __html: htmlWithMediaToken(html) }} />;
}

function canRenderFrontHtml(row: CardAttention) {
  const rendered = row.renderedPreview;
  return Boolean(rendered && (rendered.renderStatus === "available" || rendered.renderStatus === "sanitized") && rendered.frontHtml);
}

function canRenderBackHtml(row: CardAttention) {
  const rendered = row.renderedPreview;
  return Boolean(rendered && (rendered.renderStatus === "available" || rendered.renderStatus === "sanitized") && rendered.backHtml);
}

function FloatingStatusIndicator({
  status,
  onRetry,
}: {
  status: { state: FloatingStatusState; reason?: string } | null;
  onRetry: () => void;
}) {
  const [topOffset, setTopOffset] = useState(80);
  useEffect(() => {
    const update = () => {
      const nav = document.querySelector(".topbar-surface");
      const bottom = nav instanceof HTMLElement ? nav.getBoundingClientRect().bottom : 68;
      setTopOffset(Math.max(56, Math.round(bottom + 12)));
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  if (!status || status.state === "idle") {
    return null;
  }
  const pending = status.state === "applying" || status.state === "saving" || status.state === "rebuilding";
  const isError = status.state === "error";
  const text =
    status.state === "applying"
      ? "Применение фильтров..."
      : status.state === "applied"
        ? "Фильтры применены"
        : status.state === "saving"
          ? "Сохранение настроек..."
          : status.state === "saved"
            ? "Настройки сохранены"
            : status.state === "rebuilding"
              ? "Обновление отчёта..."
              : status.state === "rebuilt"
                ? "Отчёт обновлён"
                : `Не удалось сохранить/обновить${status.reason ? `: ${status.reason}` : ""}`;
  const content = (
    <div
      className={`pointer-events-none fixed left-5 top-[84px] z-50 flex max-w-[min(360px,calc(100vw-40px))] items-center gap-3 rounded-xl border px-4 py-3 text-sm shadow-panel ${
        isError
          ? "border-report-danger/50 bg-ink-850 text-report-danger"
          : "border-report-blue/45 bg-ink-850 text-report-text"
      }`}
      aria-live="polite"
      role="status"
      data-testid="cards-floating-status"
      data-position="viewport-top-left"
      style={{ left: 20, top: topOffset }}
    >
      {pending ? <Loader2 className="shrink-0 animate-spin text-report-blue" size={17} aria-hidden="true" /> : <CheckCircle2 className="shrink-0 text-report-success" size={17} aria-hidden="true" />}
      <span className="min-w-0 break-words">{text}</span>
      {isError ? (
        <button type="button" className="toolbar-button pointer-events-auto ml-1 px-2 py-1 text-xs" onClick={onRetry}>
          <RotateCcw size={14} aria-hidden="true" />
          Повторить
        </button>
      ) : null}
    </div>
  );
  return createPortal(content, document.body);
}

function RowActions({
  row,
  status,
  onCopySearch,
  onOpenRow,
  compact = false,
}: {
  row: CardAttention;
  status?: string;
  onCopySearch: (row: CardAttention) => void;
  onOpenRow: (row: CardAttention) => void;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="cards-row-actions">
        <button type="button" className="cards-row-open" onClick={() => onOpenRow(row)}>
          <ExternalLink size={14} aria-hidden="true" />
          Открыть в Anki
        </button>
        <button type="button" className="cards-row-copy" onClick={() => onCopySearch(row)} title="Скопировать запрос поиска" aria-label="Скопировать запрос поиска">
          <Clipboard size={14} aria-hidden="true" />
          Запрос
        </button>
        {status ? <p className="cards-row-status">{status}</p> : null}
      </div>
    );
  }
  return (
    <div className="grid gap-2">
      <button type="button" className="toolbar-button justify-center" onClick={() => onOpenRow(row)}>
        <ExternalLink size={15} aria-hidden="true" />
        Открыть в Anki Browser
      </button>
      <button type="button" className="toolbar-button justify-center" onClick={() => onCopySearch(row)}>
        <Clipboard size={15} aria-hidden="true" />
        Скопировать запрос поиска
      </button>
      {status ? <p className="text-xs leading-5 text-report-muted">{status}</p> : null}
    </div>
  );
}

function RiskBadge({ score }: { score: number }) {
  const status = riskStatus(score);
  return (
    <span className={`cards-risk-badge status-${status}`}>
      <span>{riskLevelLabel(score)} ·</span>
      <strong>{formatInteger(score)}</strong>
    </span>
  );
}

function CardLevelPlannedState({ problemDecks, statusReason }: { problemDecks: number; statusReason?: string | null }) {
  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
      <CardsEmptyState
        title="В текущем отчёте нет данных уровня карточек"
        text="Отчёт уже показывает проблемные колоды и умеет открыть их в Anki Browser, но в текущих данных нет детализации по конкретным карточкам, превью, срывам и пропущенным полям."
      />
      <article className="rounded-xl border border-ink-700 bg-ink-800/55 p-4">
        <h3 className="text-base font-semibold tracking-normal text-report-text">Доступен запасной режим по колодам</h3>
        <p className="mt-2 text-2xl font-semibold leading-8 text-report-text">{formatInteger(problemDecks)} проблемных колод</p>
        <p className="mt-2 text-sm leading-6 text-report-muted">
          Можно открыть проблемные колоды в Anki Browser. Детализация по конкретным карточкам появится, когда отчёт передаст данные уровня карточек.
        </p>
        {statusReason ? <p className="mt-2 text-xs leading-5 text-report-muted">{statusReason}</p> : null}
      </article>
    </div>
  );
}

function SelectControl({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="relative block">
      <span className="sr-only">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="form-control w-full appearance-none px-3 py-2.5 pr-9 text-sm">
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-report-muted" size={17} />
    </label>
  );
}

function Tabs({ active, onChange, counts }: { active: CardsTab; onChange: (tab: CardsTab) => void; counts: Record<CardsTab, number> }) {
  const tabs: Array<{ value: CardsTab; label: string }> = [
    { value: "risk", label: "Рискованные" },
    { value: "gaps", label: "Пробелы" },
    { value: "patterns", label: "Паттерны" },
    { value: "check", label: "Проверка" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((item) => (
        <button
          key={item.value}
          type="button"
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            active === item.value
              ? "border-report-blue/65 bg-report-blue/20 text-report-text"
              : "border-ink-700 bg-ink-800/55 text-report-muted hover:border-report-blue/45 hover:text-report-text"
          }`}
          onClick={() => onChange(item.value)}
        >
          {item.label} {formatInteger(counts[item.value])}
        </button>
      ))}
    </div>
  );
}

function SummaryCard({ label, value, description, status }: { label: string; value: string; description: string; status: Status }) {
  return (
    <article className={`kpi-card min-h-[132px] status-${status}`}>
      <p className="text-[13px] font-medium uppercase leading-5 tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-3 break-words text-2xl font-semibold leading-8 text-report-text">{value}</p>
      <p className="mt-2 text-xs leading-5 text-report-muted">{description}</p>
    </article>
  );
}

function CardsEmptyState({ title, text }: { title: string; text: string }) {
  return (
    <section className="rounded-xl border border-dashed border-ink-700 bg-ink-900/35 p-5 text-center">
      <h2 className="text-lg font-semibold tracking-normal text-report-text">{title}</h2>
      <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-report-muted">{text}</p>
    </section>
  );
}

function DiagnosticPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-850 p-4">
      <h3 className="text-base font-semibold tracking-normal text-report-text">{title}</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">{children}</div>
    </section>
  );
}

function DetailBlock({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={`rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-2 ${compact ? "" : "min-h-[74px]"}`}>
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-report-text">{value}</p>
    </div>
  );
}

function IssueChips({ issues }: { issues: CardIssueType[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {issues.map((issue) => (
        <span key={issue} className={`status-pill ${missingCardIssueTypes.has(issue) ? "status-warning" : issue === "leech" || issue === "repeated_again" ? "status-danger" : "status-neutral"}`}>
          {cardIssueLabels[issue]}
        </span>
      ))}
    </div>
  );
}

function StatusPill({ status, children }: { status: Status; children: ReactNode }) {
  return <span className={`status-pill status-${status}`}>{children}</span>;
}

function rowsForTab(rows: CardAttention[], tab: CardsTab) {
  if (tab === "gaps") {
    return rows.filter((row) => row.issues.some((issue) => missingCardIssueTypes.has(issue)));
  }
  if (tab === "patterns") {
    return rows.filter((row) => row.issues.some((issue) => issue === "repeated_again" || issue === "slow_answer" || issue === "low_pass_rate"));
  }
  if (tab === "check") {
    return rows;
  }
  return rows;
}

function tabCounts(rows: CardAttention[]): Record<CardsTab, number> {
  return {
    risk: rows.length,
    gaps: rowsForTab(rows, "gaps").length,
    patterns: rowsForTab(rows, "patterns").length,
    check: rows.length,
  };
}

function riskStatus(score: number): Status {
  const normalized = finiteNumber(score);
  if (normalized >= 75) {
    return "danger";
  }
  if (normalized >= 45) {
    return "warning";
  }
  return "neutral";
}

function riskLevelLabel(score: number) {
  const normalized = finiteNumber(score);
  if (normalized >= 75) {
    return "Высокий";
  }
  if (normalized >= 45) {
    return "Средний";
  }
  return "Низкий";
}

function loadStateText(state: LoadState) {
  if (state === "loading") {
    return "Проверяю локальный API дашборда.";
  }
  if (state === "forbidden") {
    return "Откройте дашборд из Anki Study Report, чтобы получить действующую ссылку.";
  }
  if (state === "error") {
    return "Локальный API дашборда не вернул отчёт.";
  }
  return "Откройте основное окно Anki Study Report и опубликуйте отчёт в дашборде.";
}

function backendScopeLabel(report: StudyReport) {
  const decks = report.metadata.selectedDecks.filter((item) => item.trim().length > 0);
  if (!decks.length || decks.some((item) => /^все колоды$/i.test(item))) {
    return "Все колоды";
  }
  return decks.join(", ");
}

function periodLabel(period: CardsPeriodFilter) {
  return periodOptions.find((option) => option.value === period)?.label || period;
}

function issueLabel(issue: CardsIssueFilter) {
  if (issue === "all") {
    return "Все проблемы";
  }
  return cardIssueLabels[issue];
}

function sortLabel(sortKey: CardsSortKey) {
  return sortOptions.find((option) => option.value === sortKey)?.label || sortKey;
}

function availabilityLabel(value: CardAttentionAvailability) {
  if (value === "available") {
    return "доступно";
  }
  if (value === "skipped") {
    return "пропущено";
  }
  if (value === "error") {
    return "ошибка";
  }
  if (value === "absent") {
    return "нет данных";
  }
  return "недоступно";
}

function sourceLabel(value: ReturnType<typeof cardAttentionState>["source"]) {
  if (value === "fresh") {
    return "текущий отчёт";
  }
  if (value === "cache") {
    return "кэш";
  }
  if (value === "mock") {
    return "пример";
  }
  return "неизвестно";
}

function nullableInteger(value: number | null) {
  return value === null ? "Нет данных" : formatInteger(value);
}

function booleanLabel(value: boolean | null) {
  if (value === null) {
    return "Нет данных";
  }
  return value ? "да" : "нет";
}

function detectedKindsLabel(value: Record<string, number>) {
  const entries = Object.entries(value);
  if (!entries.length) {
    return "Нет данных";
  }
  return entries.map(([kind, count]) => `${kind}: ${formatInteger(count)}`).join(", ");
}

function emptyTitleForTab(tab: CardsTab) {
  if (tab === "gaps") {
    return "Пробелов не найдено";
  }
  if (tab === "patterns") {
    return "Подозрительных паттернов нет";
  }
  if (tab === "check") {
    return "Проверка пуста";
  }
  return "Нет проблемных карточек";
}

function tabLabel(tab: CardsTab) {
  if (tab === "gaps") {
    return "пробел";
  }
  if (tab === "patterns") {
    return "паттерн";
  }
  if (tab === "check") {
    return "проверка";
  }
  return "риск";
}

function readDisplayMode(): CardsDisplayMode {
  try {
    const value = window.localStorage.getItem(CARDS_DISPLAY_MODE_STORAGE_KEY);
    return value === "table" || value === "tiles" || value === "ankiPreview" ? value : "table";
  } catch {
    return "table";
  }
}

function displayModeLabel(mode: CardsDisplayMode) {
  if (mode === "tiles") {
    return "Плитки";
  }
  if (mode === "ankiPreview") {
    return "Превью Anki";
  }
  return "Таблица";
}

function cardFrontText(row: CardAttention) {
  return safeText(
    row.renderedPreview?.frontPlainText || row.preview?.frontText || row.preview?.frontOnly || row.preview?.primary || row.front,
    "Карточка без превью",
  );
}

function summarizePreviewProfiles(rows: CardAttention[]) {
  const map = new Map<string, { noteTypeName: string; templateName: string; kind: string; count: number }>();
  for (const row of rows) {
    const noteTypeName = row.preview?.noteTypeName || "Unknown";
    const templateName = row.preview?.cardTemplateName || "auto";
    const kind = row.preview?.detectedKind || "unknown";
    const key = `${noteTypeName}\u0000${templateName}\u0000${kind}`;
    const item = map.get(key) || { noteTypeName, templateName, kind, count: 0 };
    item.count += 1;
    map.set(key, item);
  }
  return [...map.values()].sort((a, b) => b.count - a.count);
}

function profilesToCatalog(profiles: ReturnType<typeof summarizePreviewProfiles>): NoteTypeCatalogItem[] {
  return profiles.map((profile, index) => ({
    noteTypeId: index + 1,
    name: profile.noteTypeName || "Unknown",
    noteCount: profile.count,
    cardTemplateCount: profile.templateName ? 1 : 0,
    fields: [],
    templates: profile.templateName ? [{ ord: 0, name: profile.templateName }] : [],
    cssAvailable: false,
    usedInCurrentCards: true,
  }));
}

function htmlWithMediaToken(html: string) {
  return html.replace(/(\/api\/media\?name=[^"'&<>]+)(?![^"'<>]*token=)/g, (match) => mediaUrlWithToken(match));
}

function mediaUrlWithToken(url: string) {
  const token = dashboardToken();
  if (!token || /(?:^https?:|^file:|token=)/i.test(url)) {
    return url;
  }
  return `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

export default CardsPage;
