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
import { memo, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { createPortal } from "react-dom";
import {
  buildCardAttentionRows,
  buildCardBrowserSearch,
  cardAttentionState,
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
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";

type CardsTab = "risk" | "gaps" | "patterns" | "check";
type FloatingStatusState = "idle" | "applying" | "applied" | "saving" | "saved" | "rebuilding" | "rebuilt" | "error";
type CardsDisplayMode = "table" | "tiles" | "ankiPreview";
const CARDS_DISPLAY_MODE_STORAGE_KEY = "anki-study-report.cards.displayMode";
const BULK_OPEN_LIMIT = 100;
const BULK_OPEN_MAX_QUERY_LENGTH = 1800;

const periodOptions: CardsPeriodFilter[] = ["today", "7d", "30d", "all"];
const issueOptions: CardsIssueFilter[] = ["all", "leech", "repeated_again", "slow_answer", "low_pass_rate", "missing_audio", "missing_example", "missing_image", "missing_meaning", "missing_part_of_speech"];
const sortOptions: CardsSortKey[] = ["risk", "again", "lapses", "avgAnswer", "lastReviewed"];
const tc = (key: string, options?: Record<string, unknown>) => i18n.t(`cards.${key}`, { ns: "pages", ...options });
const issueKey = (value: CardsIssueFilter) => ({ repeated_again: "repeatedAgain", slow_answer: "slowAnswer", low_pass_rate: "lowPassRate", missing_audio: "missingAudio", missing_example: "missingExample", missing_image: "missingImage", missing_meaning: "missingMeaning", missing_part_of_speech: "missingPartOfSpeech" } as Record<string, string>)[value] || value;

function CardsPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  useTranslation("pages");
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
    return [...names].sort((a, b) => a.localeCompare(b, localeForLanguage(i18n.language)));
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

  const resetFilters = useCallback(() => {
    setPeriod(DEFAULT_CARD_FILTERS.period);
    setDeck(DEFAULT_CARD_FILTERS.deck);
    setIssue(DEFAULT_CARD_FILTERS.issue);
    setQuery(DEFAULT_CARD_FILTERS.query);
    setSortKey(DEFAULT_CARD_FILTERS.sortKey);
    setTab("risk");
  }, []);

  const openProblemDecks = async (): Promise<boolean> => {
    if (!reportReady || !tokenAvailable) {
      setActionStatus({
        ok: false,
        action: "open-browser",
        error: !tokenAvailable ? tc("action.openFromReport") : tc("action.reportMissing"),
      });
      return false;
    }
    setIsOpening(true);
    try {
      const response = await runReportAction("open-browser", { kind: "problematic-decks" });
      setActionStatus(response);
      return response.ok;
    } catch {
      setActionStatus({ ok: false, action: "open-browser", error: tc("action.browserFailed") });
      return false;
    } finally {
      setIsOpening(false);
    }
  };

  const copySearch = useCallback(async (row: CardAttention) => {
    const search = buildCardBrowserSearch(row);
    try {
      await navigator.clipboard.writeText(search);
      setRowStatus((current) => ({ ...current, [row.id]: tc("action.copied") }));
    } catch {
      setRowStatus((current) => ({ ...current, [row.id]: search }));
    }
  }, []);

  const openRow = useCallback(async (row: CardAttention) => {
    const search = buildCardBrowserSearch(row);
    if (!tokenAvailable) {
      setRowStatus((current) => ({ ...current, [row.id]: tc("action.noLinkCopied") }));
      await copySearch(row);
      return;
    }
    setRowStatus((current) => ({ ...current, [row.id]: tc("action.opening", { search }) }));
    const response = await runReportAction("open-browser-search", { query: search });
    setActionStatus(response);
    setRowStatus((current) => ({
      ...current,
      [row.id]: response.ok ? tc("action.opened", { search }) : response.error || tc("action.openFailed", { search }),
    }));
  }, [copySearch, tokenAvailable]);

  const openFilteredRows = async () => {
    if (!tokenAvailable) {
      setActionStatus({ ok: false, action: "open-browser-search", error: tc("action.openFromReport") });
      return;
    }
    const queries = tabRows.slice(0, BULK_OPEN_LIMIT).map((row) => buildCardBrowserSearch(row)).filter(Boolean);
    const uniqueQueries = [...new Set(queries)];
    if (!uniqueQueries.length) {
      setActionStatus({ ok: false, action: "open-browser-search", error: tc("action.noCards") });
      return;
    }
    const bulkQuery = uniqueQueries.length === 1 ? uniqueQueries[0] : uniqueQueries.map((item) => `(${item})`).join(" OR ");
    if (bulkQuery.length > BULK_OPEN_MAX_QUERY_LENGTH) {
      await navigator.clipboard?.writeText(bulkQuery).catch(() => undefined);
      setActionStatus({
        ok: false,
        action: "open-browser-search",
        error: tc("action.tooLong", { count: uniqueQueries.length }),
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
        <SummaryCard label={tc("summary.attention")} value={cardKpiValue(summary.problemCards)} description={tc("summary.attentionDescription")} status={cardLevelSourceAvailable && summary.problemCards ? "danger" : "neutral"} />
        <SummaryCard label="Leech" value={cardKpiValue(summary.leech)} description={tc("summary.leechDescription")} status={cardLevelSourceAvailable && summary.leech ? "danger" : "neutral"} />
        <SummaryCard label={tc("summary.again")} value={cardKpiValue(summary.repeatedAgain)} description={tc("summary.againDescription")} status={cardLevelSourceAvailable && summary.repeatedAgain ? "danger" : "neutral"} />
        <SummaryCard label={tc("summary.slow")} value={cardKpiValue(summary.slowAnswer)} description={tc("summary.slowDescription")} status={cardLevelSourceAvailable && summary.slowAnswer ? "warning" : "neutral"} />
        <SummaryCard label={tc("summary.gaps")} value={cardKpiValue(summary.dataGaps)} description={tc("summary.gapsDescription")} status={cardLevelSourceAvailable && summary.dataGaps ? "warning" : "neutral"} />
      </section>

      {cardLevelSourceAvailable ? <CardsPreviewSettingsNotice rows={rows} report={report} displayMode={displayMode} /> : null}

      {cardLevelError ? (
        <section className="rounded-xl border border-report-danger/45 bg-report-danger/10 p-4 text-sm leading-6 text-report-text shadow-panel">
          {tc("summary.fallback")}
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
              placeholder={tc("filters.search")}
            />
          </label>
          <SelectControl label={tc("filters.period")} value={period} onChange={(value) => setPeriod(value as CardsPeriodFilter)}>
            {periodOptions.map((option) => (
              <option key={option} value={option}>
                {tc(`periods.${option}`)}
              </option>
            ))}
          </SelectControl>
          <SelectControl label={tc("filters.issue")} value={issue} onChange={(value) => setIssue(value as CardsIssueFilter)}>
            {issueOptions.map((option) => (
              <option key={option} value={option}>
                {tc(`issues.${issueKey(option)}`)}
              </option>
            ))}
          </SelectControl>
          <SelectControl label={tc("filters.sort")} value={sortKey} onChange={(value) => setSortKey(value as CardsSortKey)}>
            {sortOptions.map((option) => (
              <option key={option} value={option}>
                {tc(`sort.${option}`)}
              </option>
            ))}
          </SelectControl>
        </div>
        <div className="mt-3">
          <SelectControl label={tc("filters.deck")} value={deck} onChange={setDeck}>
            <option value="all">{tc("filters.allDecks")}</option>
            {deckOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </SelectControl>
        </div>
        <div className="mt-3 flex flex-col gap-2 text-xs leading-5 text-report-muted sm:flex-row sm:items-center sm:justify-between">
          <p>
            {tc("filters.summary", { count: formatInteger(filteredRows.length), period: periodLabel(period), issue: issueLabel(issue), sort: sortLabel(sortKey) })}
          </p>
          <button type="button" className="toolbar-button w-fit px-3 py-1.5 text-xs" onClick={resetFilters}>
            {tc("filters.reset")}
          </button>
        </div>
        <p className="mt-2 text-xs leading-5 text-report-muted">
          {tc("filters.periodNote")}
        </p>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel sm:p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <Tabs active={tab} onChange={setTab} counts={tabCounts(filteredRows)} />
          <div className="flex flex-wrap items-center gap-2">
            <DisplayModeSwitcher value={displayMode} onChange={setDisplayMode} />
            <button type="button" className="toolbar-button" onClick={openFilteredRows} disabled={!cardLevelSourceAvailable || tabRows.length === 0}>
              {tc("filters.openAll")}
            </button>
            <StatusPill status={cardLevelSourceAvailable ? "good" : "warning"}>
              {cardLevelSourceAvailable ? tc("filters.afterFilters", { count: formatInteger(filteredRows.length) }) : tc("filters.unavailable")}
            </StatusPill>
          </div>
        </div>
        {cardLevelSourceAvailable && tabRows.length > 0 ? (
          <p className="mt-3 text-xs leading-5 text-report-muted">
            {tc("filters.bulkNote", { count: formatInteger(Math.min(tabRows.length, BULK_OPEN_LIMIT)) })}
          </p>
        ) : null}

        <div className="mt-4">
          {loadState !== "ready" || !report ? (
            <CardsEmptyState title={tc("empty.report")} text={loadStateText(loadState)} />
          ) : tab === "check" && deck === "all" ? (
            <CardsEmptyState title={tc("empty.selectDeck")} text={tc("empty.selectDeckText")} />
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
                title: period === "all" ? tc("empty.noProblems") : tc("empty.noPeriod"),
                text:
                  period === "today"
                    ? tc("empty.todayText")
                    : tc("empty.filteredText"),
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
            <CardsEmptyState title={emptyTitleForTab(tab)} text={tc("empty.tabText")} />
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
          {tc("filters.reset")}
        </button>
        <button type="button" className="toolbar-button" onClick={onToggleDiagnostics}>
          {showDiagnostics ? tc("diagnostics.hide") : tc("diagnostics.show")}
        </button>
        <button type="button" className="toolbar-button" onClick={onOpenProblemDecks}>
          <FolderSearch size={16} aria-hidden="true" />
          {tc("diagnostics.openDecks")}
        </button>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <DetailBlock label={tc("diagnostics.backendScope")} value={backendScopeLabel(report)} />
        <DetailBlock label={tc("diagnostics.uiFilter")} value={`${periodLabel(period)} / ${deck === "all" ? tc("filters.allDecks") : deck} / ${issueLabel(issue)}`} />
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
        <h2 className="text-base font-semibold tracking-normal text-report-text">{tc("diagnostics.displayTitle")}</h2>
        <p className="mt-2 text-sm leading-6 text-report-muted">
          {tc("diagnostics.displayText", { mode: displayModeLabel(displayMode) })}
        </p>
      </section>
      <details className="rounded-xl border border-ink-700 bg-ink-850/80 p-4 text-sm shadow-panel">
        <summary className="cursor-pointer font-semibold text-report-text">{tc("diagnostics.templateTitle")}</summary>
        <div className="mt-3 grid gap-3 text-sm leading-6 text-report-muted md:grid-cols-2">
          <DetailBlock label={tc("diagnostics.displayMode")} value={displayModeLabel(displayMode)} compact />
          <DetailBlock label={tc("diagnostics.templatePreview")} value={tc("diagnostics.safeRender")} compact />
          <DetailBlock label={tc("diagnostics.collectionTypes")} value={formatInteger(catalog.length || profiles.length)} compact />
          <DetailBlock label={tc("diagnostics.listTypes")} value={formatInteger(currentTypes)} compact />
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
        <span className="font-medium text-report-text">{item.name || tc("diagnostics.unknownType")}</span>
        <span className="ml-2 text-report-muted">
          {tc("diagnostics.notesTemplates", { notes: formatInteger(item.noteCount), templates: formatInteger(item.cardTemplateCount) })}
          {item.usedInCurrentCards ? tc("diagnostics.currentList") : ""}
        </span>
      </summary>
      <div className="mt-3 grid gap-3 text-report-muted md:grid-cols-2">
        <DetailBlock label={tc("diagnostics.fields")} value={item.fields.length ? item.fields.join(", ") : tc("diagnostics.noData")} compact />
        <DetailBlock label={tc("diagnostics.templates")} value={item.templates.length ? item.templates.map((template) => template.name).join(", ") : tc("diagnostics.noData")} compact />
        <DetailBlock label={tc("diagnostics.templatePreview")} value={item.templates.length ? tc("diagnostics.renderAvailable") : tc("diagnostics.renderUnavailable")} compact />
        <DetailBlock label="CSS" value={item.cssAvailable ? tc("diagnostics.cssAvailable") : tc("diagnostics.cssUnavailable")} compact />
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
        <DetailBlock label={tc("diagnostics.status")} value={availabilityLabel(state.status)} />
        <DetailBlock label={tc("diagnostics.source")} value={sourceLabel(state.source)} />
        <DetailBlock label={tc("diagnostics.collectorRan")} value={booleanLabel(state.collectorRan)} />
        <DetailBlock label={tc("diagnostics.collectionAvailable")} value={booleanLabel(state.collectionAvailable)} />
        <DetailBlock label={tc("diagnostics.period")} value={`${report.metadata.period || periodLabel(period)} (${periodLabel(period)})`} />
        <DetailBlock label={tc("diagnostics.periodMode")} value={tc("diagnostics.pageFilter")} />
        <DetailBlock label={tc("diagnostics.uiPeriod")} value={periodLabel(period)} />
        <DetailBlock label={tc("diagnostics.riskRecalculated")} value={tc("diagnostics.no")} />
        <DetailBlock label={tc("diagnostics.selectedDecks")} value={backendScopeLabel(report)} />
        <DetailBlock label={tc("diagnosticFields.scannedCards")} value={nullableInteger(state.scannedCards)} />
        <DetailBlock label={tc("diagnosticFields.candidateCards")} value={nullableInteger(state.candidateCards)} />
        <DetailBlock label={tc("diagnosticFields.revlogRows")} value={nullableInteger(state.revlogRows)} />
        <DetailBlock label={tc("diagnosticFields.returnedCards")} value={nullableInteger(state.returnedCards)} />
        <DetailBlock label={tc("diagnosticFields.revlogTotalRows")} value={nullableInteger(state.revlogTotalRows)} />
        <DetailBlock label={tc("diagnosticFields.revlogMinId")} value={nullableInteger(state.revlogMinId)} />
        <DetailBlock label={tc("diagnosticFields.revlogMaxId")} value={nullableInteger(state.revlogMaxId)} />
        <DetailBlock label={tc("diagnosticFields.revlogRowsInPeriod")} value={nullableInteger(state.revlogRowsInPeriod)} />
        <DetailBlock label={tc("diagnosticFields.revlogRowsAfterDeckFilter")} value={nullableInteger(state.revlogRowsAfterDeckFilter)} />
        <DetailBlock label={tc("diagnosticFields.periodStartRaw")} value={nullableInteger(state.periodStartRaw)} />
        <DetailBlock label={tc("diagnosticFields.periodEndRaw")} value={nullableInteger(state.periodEndRaw)} />
        <DetailBlock label={tc("diagnosticFields.periodStartMs")} value={nullableInteger(state.periodStartMs)} />
        <DetailBlock label={tc("diagnosticFields.periodEndMs")} value={nullableInteger(state.periodEndMs)} />
        <DetailBlock label={tc("diagnosticFields.timeUnitNormalized")} value={state.timeUnitNormalized ? tc("diagnostics.yes") : tc("diagnostics.no")} />
        <DetailBlock label={tc("diagnosticFields.selectedDeckIdsCount")} value={nullableInteger(state.selectedDeckIdsCount)} />
        <DetailBlock label={tc("diagnosticFields.deckFilterApplied")} value={state.deckFilterApplied ? tc("diagnostics.yes") : tc("diagnostics.no")} />
        <DetailBlock label={tc("diagnosticFields.cardsTotal")} value={nullableInteger(state.cardsTotal)} />
        <DetailBlock label={tc("diagnosticFields.notesLoaded")} value={nullableInteger(state.notesLoaded)} />
        <DetailBlock label={tc("diagnosticFields.noteTypeProfilesCount")} value={nullableInteger(state.noteTypeProfilesCount)} />
        <DetailBlock label={tc("diagnosticFields.unknownNoteTypesCount")} value={nullableInteger(state.unknownNoteTypesCount)} />
        <DetailBlock label={tc("diagnosticFields.previewStrategy")} value={state.previewStrategy || tc("diagnostics.noData")} />
        <DetailBlock label={tc("diagnosticFields.missingFieldRoleSource")} value={state.missingFieldRoleSource || tc("diagnostics.noData")} />
        <DetailBlock label={tc("diagnosticFields.detectedKinds")} value={detectedKindsLabel(state.detectedKinds)} />
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
        <DiagnosticPanel title={tc("diagnostics.issueCount")}>
          <DetailBlock label="Leech" value={formatInteger(state.issueCounts.leech)} compact />
          <DetailBlock label={tc("issues.repeatedAgain")} value={formatInteger(state.issueCounts.repeatedAgain)} compact />
          <DetailBlock label={tc("issues.slowAnswer")} value={formatInteger(state.issueCounts.slowAnswer)} compact />
          <DetailBlock label={tc("issues.lowPassRate")} value={formatInteger(state.issueCounts.lowPassRate)} compact />
          <DetailBlock label={tc("issues.missingAudio")} value={formatInteger(state.issueCounts.missingAudio)} compact />
          <DetailBlock label={tc("issues.missingExample")} value={formatInteger(state.issueCounts.missingExample)} compact />
          <DetailBlock label={tc("issues.missingImage")} value={formatInteger(state.issueCounts.missingImage)} compact />
          <DetailBlock label={tc("issues.missingMeaning")} value={formatInteger(state.issueCounts.missingMeaning)} compact />
          <DetailBlock label={tc("issues.missingPartOfSpeech")} value={formatInteger(state.issueCounts.missingPartOfSpeech)} compact />
        </DiagnosticPanel>
        <DiagnosticPanel title={tc("diagnostics.thresholds")}>
          <DetailBlock label={tc("thresholds.again")} value={formatInteger(state.thresholds.repeatedAgainThreshold)} compact />
          <DetailBlock label={tc("thresholds.slow")} value={String(state.thresholds.slowAnswerSeconds)} compact />
          <DetailBlock label={tc("thresholds.lowPass")} value={formatPercent(state.thresholds.lowPassRateThreshold)} compact />
          <DetailBlock label={tc("thresholds.leech")} value={formatInteger(state.thresholds.leechLapsesFallback)} compact />
          <DetailBlock label={tc("thresholds.limit")} value={formatInteger(state.thresholds.maxResults)} compact />
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
            {cardLevelAvailable ? tc("header.available") : reportReady ? cardLevelStatus === "error" ? tc("header.error") : tc("header.waiting") : tc("header.reportNeeded")}
          </span>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{tc("header.title")}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-report-muted">
            {tc("header.description")}
          </p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-report-muted">
            {tc("header.readOnlyText")}
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button type="button" className="toolbar-button justify-center" onClick={onOpenProblemDecks} disabled={!reportReady || isOpening}>
              <FolderSearch size={16} aria-hidden="true" />
              {isOpening ? tc("header.opening") : tc("header.openProblems")}
            </button>
            <button
              type="button"
              className="toolbar-button justify-center"
              aria-label={tc("header.toolsAria")}
              data-href="#/actions"
              onClick={() => {
                window.location.hash = "#/actions";
              }}
            >
              <Wand2 size={16} aria-hidden="true" />
              {tc("header.tools")}
            </button>
            <a className="toolbar-button justify-center opacity-80" href="#/home">
              <Home size={16} aria-hidden="true" />
              {tc("header.today")}
            </a>
          </div>
          {actionStatus ? (
            <p className={`mt-3 text-sm leading-6 ${actionStatus.ok ? "text-report-success" : "text-report-danger"}`}>
              {actionStatus.ok ? actionStatus.message || tc("action.openedDefault") : actionStatus.error || tc("action.notDone")}
            </p>
          ) : null}
        </div>
        <aside className="flex flex-wrap gap-2 xl:max-w-[360px] xl:justify-end">
          <StatusPill status={problemDeckCount ? "warning" : "good"}>{tc("header.problemDecks", { count: formatInteger(problemDeckCount) })}</StatusPill>
          <StatusPill status="good">{tc("header.readOnly")}</StatusPill>
        </aside>
      </div>
    </header>
  );
}

const RiskTable = memo(function RiskTable({
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
            <th className="text-left">{tc("table.risk")}</th>
            <th className="text-left">{tc("table.card")}</th>
            <th className="text-left">{tc("table.deck")}</th>
            <th className="text-left">{tc("table.issues")}</th>
            <th className="text-right">{i18n.t("answers.again", { ns: "common" })}</th>
            <th className="text-right">{tc("table.failures")}</th>
            <th className="text-right">{tc("table.average")}</th>
            <th className="text-left">{tc("table.last")}</th>
            <th className="text-left">{tc("table.actions")}</th>
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
              <td className="w-[150px] text-report-muted">{safeText(row.lastReviewed, tc("table.noData"))}</td>
              <td className="w-[150px]" data-testid="cards-table-actions">
                <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});

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
              <p>{i18n.t("answers.again", { ns: "common" })} {formatInteger(row.againCount)}</p>
              <p>{tc("table.lapses")} {formatInteger(row.lapses)}</p>
              <p>{formatPercent(row.passRate)}</p>
            </div>
          </div>
          <div className="mt-3">
            <IssueChips issues={row.issues} />
          </div>
          <p className="mt-3 text-sm leading-6 text-report-muted">
            {tab === "patterns"
              ? row.answerPattern || tc("table.patternFallback")
              : tab === "gaps"
                ? tc("table.gapsHint")
                : tc("table.checklistHint")}
          </p>
          <div className="mt-4">
            <RowActions row={row} status={rowStatus[row.id]} onCopySearch={onCopySearch} onOpenRow={onOpenRow} />
          </div>
        </article>
      ))}
    </div>
  );
}

const CardTiles = memo(function CardTiles({
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
            <StatusPill status={riskStatus(row.riskScore)}>{tc("table.riskValue", { value: formatInteger(row.riskScore) })}</StatusPill>
            <span className="text-xs text-report-muted">{tabLabel(tab)}</span>
          </div>
          <div className="cards-tile-preview-slot" data-testid="cards-tile-preview-slot">
            <FrontPreviewFrame row={row} variant="tile" />
          </div>
          <p className="cards-tile-meta line-clamp-2 text-sm leading-6 text-report-muted" data-testid="cards-tile-meta">
            {row.deckName}
          </p>
          <div className="cards-tile-metrics grid grid-cols-3 gap-2 text-xs text-report-muted" data-testid="cards-tile-metrics">
            <DetailMini label={i18n.t("answers.again", { ns: "common" })} value={formatInteger(row.againCount)} />
            <DetailMini label={tc("table.lapses")} value={formatInteger(row.lapses)} />
            <DetailMini label={tc("table.success")} value={formatPercent(row.passRate)} />
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
});

const AnkiPreviewGrid = memo(function AnkiPreviewGrid({
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
              <StatusPill status={riskStatus(row.riskScore)}>{tc("table.riskValue", { value: formatInteger(row.riskScore) })}</StatusPill>
              <span className="text-xs text-report-muted">{row.preview?.noteTypeName || row.preview?.detectedKind || tc("table.autoPreview")}</span>
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
});

const AnkiPreviewBox = memo(function AnkiPreviewBox({ row }: { row: CardAttention }) {
  const rendered = row.renderedPreview;
  const canRenderFront = canRenderFrontHtml(row);
  const canRenderBack = canRenderBackHtml(row);
  if (canRenderBack || canRenderFront) {
    const usesAnswerFallback = !canRenderBack;
    const previewHtml = canRenderBack ? rendered?.backHtml || "" : rendered?.frontHtml || "";
    return (
      <div className="asr-card-rendered asr-front-preview asr-anki-preview-panel mt-3 grid gap-3">
        <PreviewSection title={tc("preview.answer")} testId="anki-preview-answer" side="answer">
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
              {tc("preview.unavailableReason", { reason: rendered?.reason || rendered?.fallbackReason ? `: ${rendered.reason || rendered.fallbackReason}` : "." })}
            </p>
          ) : null}
        </PreviewSection>
      </div>
    );
  }
  return (
    <div className="asr-card-rendered asr-front-preview asr-anki-preview-panel mt-3 grid gap-3 rounded-lg border border-ink-700 bg-ink-950 p-4">
      <p className="w-fit rounded-md border border-ink-700 bg-ink-900/70 px-2 py-0.5 text-xs text-report-muted">{tc("preview.simplified")}</p>
      <PreviewSection title={tc("preview.answer")} testId="anki-preview-answer" side="answer">
        <PlainPreviewText text={cardFrontText(row)} />
        <p className="asr-preview-fallback-note mt-2 text-xs leading-5 text-report-muted">{tc("preview.unavailable")}</p>
      </PreviewSection>
      {rendered?.reason ? <p className="text-xs leading-5 text-report-muted">{rendered.reason}</p> : null}
    </div>
  );
});

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
  return <p className={`whitespace-pre-wrap text-sm leading-6 ${muted ? "text-report-muted" : "text-report-text"}`}>{text || tc("preview.noData")}</p>;
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
  const options: CardsDisplayMode[] = ["table", "tiles", "ankiPreview"];
  return (
    <div className="flex flex-wrap gap-1 rounded-lg border border-ink-700 bg-ink-900/45 p-1" aria-label={tc("display.aria")}>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            value === option ? "bg-report-blue/25 text-report-text" : "text-report-muted hover:bg-ink-800 hover:text-report-text"
          }`}
          onClick={() => onChange(option)}
        >
          {tc(`display.${option}`)}
        </button>
      ))}
    </div>
  );
}

function CardPreviewCell({ row }: { row: CardAttention }) {
  return <FrontPreviewFrame row={row} variant="table" />;
}

const FrontPreviewFrame = memo(function FrontPreviewFrame({ row, variant, className = "" }: { row: CardAttention; variant: "table" | "tile"; className?: string }) {
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
});

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
      ? tc("floating.applying")
      : status.state === "applied"
        ? tc("floating.applied")
        : status.state === "saving"
          ? tc("floating.saving")
          : status.state === "saved"
            ? tc("floating.saved")
            : status.state === "rebuilding"
              ? tc("floating.rebuilding")
              : status.state === "rebuilt"
                ? tc("floating.rebuilt")
                : tc("floating.failed", { reason: status.reason ? `: ${status.reason}` : "" });
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
          {tc("floating.retry")}
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
          {tc("rowAction.open")}
        </button>
        <button type="button" className="cards-row-copy" onClick={() => onCopySearch(row)} title={tc("rowAction.copyTitle")} aria-label={tc("rowAction.copyTitle")}>
          <Clipboard size={14} aria-hidden="true" />
          {tc("rowAction.query")}
        </button>
        {status ? <p className="cards-row-status">{status}</p> : null}
      </div>
    );
  }
  return (
    <div className="grid gap-2">
      <button type="button" className="toolbar-button justify-center" onClick={() => onOpenRow(row)}>
        <ExternalLink size={15} aria-hidden="true" />
        {tc("rowAction.openBrowser")}
      </button>
      <button type="button" className="toolbar-button justify-center" onClick={() => onCopySearch(row)}>
        <Clipboard size={15} aria-hidden="true" />
        {tc("rowAction.copy")}
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
        title={tc("empty.noCardData")}
        text={tc("empty.noCardDataText")}
      />
      <article className="rounded-xl border border-ink-700 bg-ink-800/55 p-4">
        <h3 className="text-base font-semibold tracking-normal text-report-text">{tc("empty.fallbackTitle")}</h3>
        <p className="mt-2 text-2xl font-semibold leading-8 text-report-text">{tc("empty.problemDecks", { count: formatInteger(problemDecks) })}</p>
        <p className="mt-2 text-sm leading-6 text-report-muted">
          {tc("empty.fallbackText")}
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
  const tabs: CardsTab[] = ["risk", "gaps", "patterns", "check"];
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((item) => (
        <button
          key={item}
          type="button"
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            active === item
              ? "border-report-blue/65 bg-report-blue/20 text-report-text"
              : "border-ink-700 bg-ink-800/55 text-report-muted hover:border-report-blue/45 hover:text-report-text"
          }`}
          onClick={() => onChange(item)}
        >
          {tc(`tabs.${item}`)} {formatInteger(counts[item])}
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
          {tc(`issues.${issueKey(issue)}`)}
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
    return tc("risk.high");
  }
  if (normalized >= 45) {
    return tc("risk.medium");
  }
  return tc("risk.low");
}

function loadStateText(state: LoadState) {
  if (state === "loading") {
    return tc("load.loading");
  }
  if (state === "forbidden") {
    return tc("load.forbidden");
  }
  if (state === "error") {
    return tc("load.error");
  }
  return tc("load.empty");
}

function backendScopeLabel(report: StudyReport) {
  const decks = report.metadata.selectedDecks.filter((item) => item.trim().length > 0);
  const allDeckLabels = [i18n.getFixedT("ru", "pages")("cards.filters.allDecks"), i18n.getFixedT("en", "pages")("cards.filters.allDecks")];
  if (!decks.length || decks.some((item) => allDeckLabels.some((label) => label.toLowerCase() === item.toLowerCase()))) {
    return tc("filters.allDecks");
  }
  return decks.join(", ");
}

function periodLabel(period: CardsPeriodFilter) { return tc(`periods.${period}`); }

function issueLabel(issue: CardsIssueFilter) {
  if (issue === "all") {
    return tc("issues.all");
  }
  return tc(`issues.${issueKey(issue)}`);
}

function sortLabel(sortKey: CardsSortKey) { return tc(`sort.${sortKey}`); }

function availabilityLabel(value: CardAttentionAvailability) {
  if (value === "available") {
    return tc("availability.available");
  }
  if (value === "skipped") {
    return tc("availability.skipped");
  }
  if (value === "error") {
    return tc("availability.error");
  }
  if (value === "absent") {
    return tc("availability.absent");
  }
  return tc("availability.unavailable");
}

function sourceLabel(value: ReturnType<typeof cardAttentionState>["source"]) {
  if (value === "fresh") {
    return tc("availability.fresh");
  }
  if (value === "cache") {
    return tc("availability.cache");
  }
  if (value === "mock") {
    return tc("availability.mock");
  }
  return tc("availability.unknown");
}

function nullableInteger(value: number | null) {
  return value === null ? tc("diagnostics.noData") : formatInteger(value);
}

function booleanLabel(value: boolean | null) {
  if (value === null) {
    return tc("diagnostics.noData");
  }
  return value ? tc("diagnostics.yes") : tc("diagnostics.no");
}

function detectedKindsLabel(value: Record<string, number>) {
  const entries = Object.entries(value);
  if (!entries.length) {
    return tc("diagnostics.noData");
  }
  return entries.map(([kind, count]) => `${kind}: ${formatInteger(count)}`).join(", ");
}

function emptyTitleForTab(tab: CardsTab) {
  if (tab === "gaps") {
    return tc("empty.gaps");
  }
  if (tab === "patterns") {
    return tc("empty.patterns");
  }
  if (tab === "check") {
    return tc("empty.check");
  }
  return tc("empty.noProblems");
}

function tabLabel(tab: CardsTab) {
  if (tab === "gaps") {
    return tc("tabs.gapsShort");
  }
  if (tab === "patterns") {
    return tc("tabs.patternsShort");
  }
  if (tab === "check") {
    return tc("tabs.checkShort");
  }
  return tc("tabs.riskShort");
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
    return tc("display.tiles");
  }
  if (mode === "ankiPreview") {
    return tc("display.ankiPreview");
  }
  return tc("display.table");
}

function cardFrontText(row: CardAttention) {
  return safeText(
    row.renderedPreview?.frontPlainText || row.preview?.frontText || row.preview?.frontOnly || row.preview?.primary || row.front,
    tc("preview.noPreview"),
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
