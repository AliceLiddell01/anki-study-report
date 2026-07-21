import { RefreshCw, RotateCw, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import AccessibleModal from "../components/AccessibleModal";
import { CardsDetail, CardPreview, hasUsableBackPreview } from "../components/cards/CardsDetail";
import { CardsDetailDrawer } from "../components/cards/CardsDetailDrawer";
import { CardsInbox } from "../components/cards/CardsInbox";
import {
  useCardsTriageWorkspace,
  type LearningPeriodDays,
} from "../hooks/useCardsTriageWorkspace";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { cardDisplayText } from "../lib/cardDisplayText";
import { reasonLabel, sourceStatusLabel } from "../lib/triagePresentation";
import type { TriageItem, TriagePriority } from "../types/triage";
import type { StudyReport } from "../types/report";
import type { LoadState } from "./HomePage";

type PriorityFilter = "all" | TriagePriority;
type ReasonFilter = "all" | "learning" | "content" | string;

const WIDE_WORKSPACE_QUERY = "(min-width: 1200px)";
const REASON_CODES = [
  "learning.leech",
  "learning.repeated_again",
  "learning.low_pass_rate",
  "learning.slow_answer",
  "content.required_text_missing",
  "content.audio_missing",
  "content.image_missing",
  "content.text_too_short",
  "content.required_group_missing",
] as const;

export default function CardsPage({ report }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const deckIds = useMemo(
    () => (report?.deckHub?.scope.selectedDeckIds ?? []).map(String),
    [report?.deckHub?.scope.selectedDeckIds],
  );
  const workspace = useCardsTriageWorkspace(deckIds);
  const isWide = useMediaQuery(WIDE_WORKSPACE_QUERY, true);
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [reason, setReason] = useState<ReasonFilter>("all");
  const [deck, setDeck] = useState("all");
  const [textFilter, setTextFilter] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const activatorRef = useRef<HTMLElement | null>(null);
  const queueHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const detailRegionId = "cards-detail-region";
  const detailHeadingId = "cards-detail-title";

  useEffect(() => setExpanded(false), [workspace.activeId]);
  useEffect(() => {
    if (isWide) setDrawerOpen(false);
  }, [isWide]);
  useEffect(() => {
    if (workspace.queryStatus !== "ready") setDrawerOpen(false);
  }, [workspace.queryStatus]);
  useEffect(() => {
    if (!workspace.focusRequest.version) return;
    const target = workspace.focusRequest.itemId
      ? document.getElementById(`${safeInboxId(workspace.focusRequest.itemId)}-button`)
      : null;
    if (target instanceof HTMLElement) target.focus();
    else queueHeadingRef.current?.focus();
  }, [workspace.focusRequest]);

  const allItems = workspace.response?.items ?? [];
  const decks = useMemo(
    () => [...new Set(allItems.map((item) => item.deck.name).filter(Boolean))].sort((left, right) => left.localeCompare(right)),
    [allItems],
  );
  const visibleItems = useMemo(() => {
    const needle = textFilter.trim().toLocaleLowerCase();
    return allItems.filter((item) => {
      if (priority !== "all" && item.priority !== priority) return false;
      if (reason === "learning" || reason === "content") {
        if (!item.reasons.some((itemReason) => itemReason.family === reason)) return false;
      } else if (reason !== "all" && !item.reasons.some((itemReason) => itemReason.code === reason)) {
        return false;
      }
      if (deck !== "all" && item.deck.name !== deck) return false;
      if (!needle) return true;
      const searchable = [
        cardDisplayText(item),
        item.deck.name,
        item.noteType.name,
        ...item.reasons.map((itemReason) => reasonLabel(itemReason.code, t)),
      ].join(" ").toLocaleLowerCase();
      return searchable.includes(needle);
    });
  }, [allItems, deck, priority, reason, t, textFilter]);

  useEffect(() => {
    if (workspace.queryStatus !== "ready") return;
    const activeVisible = workspace.activeId && visibleItems.some((item) => item.itemId === workspace.activeId);
    if (activeVisible) return;
    if (isWide) {
      const next = visibleItems.find((item) => item.inspect);
      if (next) workspace.activate(next);
      else workspace.clearActive();
    } else {
      workspace.clearActive();
      setDrawerOpen(false);
    }
  }, [isWide, visibleItems, workspace.activate, workspace.activeId, workspace.clearActive, workspace.queryStatus]);

  const filtersActive = priority !== "all" || reason !== "all" || deck !== "all" || !!textFilter.trim();
  const highCount = allItems.filter((item) => item.priority === "high").length;

  const clearFilters = useCallback(() => {
    setPriority("all");
    setReason("all");
    setDeck("all");
    setTextFilter("");
  }, []);

  const activateItem = useCallback((item: TriageItem, button: HTMLButtonElement) => {
    activatorRef.current = button;
    workspace.activate(item);
    if (!isWide && item.inspect) setDrawerOpen(true);
  }, [isWide, workspace.activate]);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  return (
    <div className="cards-inbox-page page-stack workspace-page" data-testid="cards-inbox-page" data-workspace-mode={isWide ? "wide" : "drawer"}>
      <header className="cards-inbox-heading">
        <div>
          <span className="page-eyebrow">{t("eyebrow")}</span>
          <h1 className="workspace-page-title">{t("title")}</h1>
          <p className="workspace-body">{t("description")}</p>
        </div>
        <span className="cards-inbox-readonly">{t("singleCard")}</span>
      </header>

      <section className="cards-inbox-controls panel-surface workspace-region" aria-label={t("filters.label")}>
        <div className="cards-inbox-summary" aria-live="polite">
          <strong>{workspace.response ? t("summary.items", { count: allItems.length }) : t("summary.loading")}</strong>
          {workspace.response ? <span>{t("summary.high", { count: highCount })}</span> : null}
          <span>{t("summary.period", { count: workspace.learningPeriodDays })}</span>
          {workspace.response ? <span>{t("summary.contentScanned", { count: workspace.scannedNoteCount })}</span> : null}
          {workspace.hasMoreContent ? <span className="is-warning">{t("summary.contentMore")}</span> : null}
          {workspace.response?.truncated ? <span className="is-warning">{t("summary.responseTruncated", { count: workspace.response.limit })}</span> : null}
        </div>

        <div className="cards-inbox-filter-row">
          <label>
            <span>{t("filters.priority")}</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value as PriorityFilter)}>
              <option value="all">{t("filters.allPriorities")}</option>
              <option value="high">{t("priorities.high")}</option>
              <option value="medium">{t("priorities.medium")}</option>
              <option value="low">{t("priorities.low")}</option>
            </select>
          </label>
          <label>
            <span>{t("filters.reason")}</span>
            <select value={reason} onChange={(event) => setReason(event.target.value)}>
              <option value="all">{t("filters.allReasons")}</option>
              <optgroup label={t("families.groups")}>
                <option value="learning">{t("families.learning")}</option>
                <option value="content">{t("families.content")}</option>
              </optgroup>
              <optgroup label={t("families.learning")}>
                {REASON_CODES.filter((code) => code.startsWith("learning.")).map((code) => <option key={code} value={code}>{reasonLabel(code, t)}</option>)}
              </optgroup>
              <optgroup label={t("families.content")}>
                {REASON_CODES.filter((code) => code.startsWith("content.")).map((code) => <option key={code} value={code}>{reasonLabel(code, t)}</option>)}
              </optgroup>
            </select>
          </label>
          <label>
            <span>{t("filters.deck")}</span>
            <select value={deck} onChange={(event) => setDeck(event.target.value)}>
              <option value="all">{t("filters.allDecks")}</option>
              {decks.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
          <label className="cards-inbox-text-filter">
            <span>{t("filters.text")}</span>
            <input value={textFilter} onChange={(event) => setTextFilter(event.target.value)} placeholder={t("filters.textPlaceholder")} />
          </label>
          <label>
            <span>{t("period.label")}</span>
            <select
              value={workspace.learningPeriodDays}
              title={t("period.help")}
              onChange={(event) => workspace.setLearningPeriodDays(Number(event.target.value) as LearningPeriodDays)}
            >
              <option value={7}>{t("period.days", { count: 7 })}</option>
              <option value={30}>{t("period.days", { count: 30 })}</option>
              <option value={90}>{t("period.days", { count: 90 })}</option>
            </select>
          </label>
          <div className="cards-inbox-toolbar-actions">
            {filtersActive ? <button type="button" className="secondary-button" onClick={clearFilters}>{t("filters.clear")}</button> : null}
            <button type="button" className="secondary-button" onClick={workspace.refresh} disabled={workspace.queryStatus === "loading"}>
              <RefreshCw size={16} aria-hidden="true" />{t("refresh")}
            </button>
          </div>
        </div>
        <p className="cards-inbox-period-help">{t("period.help")}</p>
      </section>

      <CardsWorkspaceWarnings workspace={workspace} />
      {workspace.lastOutcome ? (
        <div className={`cards-inbox-warning cards-resolution-outcome workspace-state is-${workspace.lastOutcome.phase}`} role="status" aria-live="polite" data-testid="cards-resolution-outcome">
          <strong>{t(`resolution.states.${workspace.lastOutcome.phase}.title`)}</strong>
          <span>{t(`resolution.states.${workspace.lastOutcome.phase}.description`)}</span>
        </div>
      ) : null}
      <CoverageDisclosure workspace={workspace} />

      <div className="cards-inbox-workspace">
        <section className="cards-inbox-queue panel-surface workspace-region" aria-labelledby="cards-inbox-queue-title">
          <header className="cards-inbox-queue-header">
            <div>
              <h2 id="cards-inbox-queue-title" className="workspace-section-title" ref={queueHeadingRef} tabIndex={-1}>{t("queue.title")}</h2>
              <p className="workspace-meta">{workspace.response ? t("queue.visible", { visible: visibleItems.length, total: allItems.length }) : t("queue.loading")}</p>
            </div>
          </header>
          <QueueState
            workspace={workspace}
            visibleItems={visibleItems}
            filtersActive={filtersActive}
            onClear={clearFilters}
            detailRegionId={detailRegionId}
            drawerMode={!isWide}
            drawerOpen={drawerOpen}
            onActivate={activateItem}
          />
          <ContinuationFooter workspace={workspace} />
        </section>

        {isWide ? (
          <aside id={detailRegionId} className="cards-inbox-inspector panel-surface workspace-region workspace-safe-area" aria-labelledby={detailHeadingId} data-testid="cards-inspector">
            <CardsDetail workspace={workspace} headingId={detailHeadingId} onExpandAnswer={() => setExpanded(true)} />
          </aside>
        ) : null}
      </div>

      {!isWide ? (
        <CardsDetailDrawer
          open={drawerOpen && !!workspace.activeItem}
          labelledBy={detailHeadingId}
          regionId={detailRegionId}
          closeLabel={t("drawer.close")}
          restoreFocusTo={activatorRef.current}
          fallbackFocusTo={queueHeadingRef.current}
          onRequestClose={closeDrawer}
        >
          <CardsDetail workspace={workspace} headingId={detailHeadingId} onExpandAnswer={() => setExpanded(true)} emptyAllowed={false} />
        </CardsDetailDrawer>
      ) : null}

      <div className="sr-only" role="status" aria-live="polite" data-testid="cards-live-status">
        {workspace.lastContinuationAddedCount === 0
          ? t("continuation.noNew")
          : workspace.lastContinuationAddedCount !== null
            ? t("continuation.added", { count: workspace.lastContinuationAddedCount })
            : ""}
      </div>

      {expanded && workspace.inspectResponse && hasUsableBackPreview(workspace.inspectResponse.details.renderedPreview) ? (
        <AccessibleModal
          title={t("preview.expandedTitle")}
          closeLabel={t("preview.close")}
          onRequestClose={() => setExpanded(false)}
          testId="cards-preview-modal"
          portal
          className="cards-answer-modal"
          footer={<button type="button" className="secondary-button" onClick={() => setExpanded(false)}>{t("preview.close")}</button>}
        >
          <CardPreview details={workspace.inspectResponse.details} side="back" />
        </AccessibleModal>
      ) : null}
    </div>
  );
}

function safeInboxId(value: string): string {
  return `cards-inbox-${value.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function QueueState({
  workspace,
  visibleItems,
  filtersActive,
  onClear,
  detailRegionId,
  drawerMode,
  drawerOpen,
  onActivate,
}: {
  workspace: ReturnType<typeof useCardsTriageWorkspace>;
  visibleItems: TriageItem[];
  filtersActive: boolean;
  onClear: () => void;
  detailRegionId: string;
  drawerMode: boolean;
  drawerOpen: boolean;
  onActivate: (item: TriageItem, button: HTMLButtonElement) => void;
}) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  if (workspace.queryStatus === "loading") return <WorkspaceMessage status title={t("states.loadingTitle")} text={t("states.loading")} />;
  if (workspace.queryStatus === "error") return <WorkspaceMessage alert title={t("states.errorTitle")} text={t("states.error")} action={<button type="button" className="secondary-button" onClick={workspace.refresh}><RotateCw size={16} aria-hidden="true" />{t("retry")}</button>} />;
  if (workspace.response?.status === "unavailable") return <WorkspaceMessage alert title={t("states.unavailableTitle")} text={t("states.unavailable")} action={<button type="button" className="secondary-button" onClick={workspace.refresh}>{t("retry")}</button>} />;
  if (!visibleItems.length) return <WorkspaceMessage title={filtersActive ? t("states.filteredTitle") : t("states.emptyTitle")} text={filtersActive ? t("states.filtered") : t("states.empty")} action={filtersActive ? <button type="button" className="secondary-button" onClick={onClear}>{t("filters.clear")}</button> : undefined} />;
  return <CardsInbox items={visibleItems} activeId={workspace.activeId} detailRegionId={detailRegionId} drawerMode={drawerMode} drawerOpen={drawerOpen} onActivate={onActivate} />;
}

function CardsWorkspaceWarnings({ workspace }: { workspace: ReturnType<typeof useCardsTriageWorkspace> }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  return (
    <div className="cards-inbox-warnings">
      {workspace.mutationPending ? (
        <div className="cards-inbox-warning" role="status" aria-live="polite" aria-busy="true" data-testid="cards-mutation-pending">
          <RotateCw size={18} aria-hidden="true" />
          <span>
            <strong>{t("resolution.states.action_pending.title")}</strong>{" "}
            {t("resolution.states.action_pending.description")}
          </span>
        </div>
      ) : null}
      {workspace.response?.contentChecks.status === "profiles_need_review" ? (
        <div className="cards-inbox-warning" role="status">
          <TriangleAlert size={18} aria-hidden="true" />
          <span><strong>{t("profiles.title", { count: workspace.response.contentChecks.needsReviewProfileCount })}</strong> {t("profiles.description")}</span>
          <a className="secondary-button" href="#/settings/inspection-profiles">{t("profiles.action")}</a>
        </div>
      ) : null}
      {workspace.response?.status === "partial" ? (
        <div className="cards-inbox-warning is-partial" role="status"><TriangleAlert size={17} aria-hidden="true" />{t("states.partial")}</div>
      ) : null}
      {workspace.response?.truncated ? (
        <div className="cards-inbox-warning is-partial" role="status"><TriangleAlert size={17} aria-hidden="true" />{t("states.responseTruncated", { count: workspace.response.limit })}</div>
      ) : null}
    </div>
  );
}

function CoverageDisclosure({ workspace }: { workspace: ReturnType<typeof useCardsTriageWorkspace> }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const response = workspace.response;
  if (!response) return null;
  return (
    <details className="cards-inbox-coverage panel-surface">
      <summary>{t("coverage.summary", { count: workspace.scannedNoteCount })}</summary>
      <dl>
        <CoverageEntry label={t("coverage.learning")} value={sourceStatusLabel(response.sourceStatus.learningCandidates, t)} />
        <CoverageEntry label={t("coverage.content")} value={sourceStatusLabel(response.sourceStatus.contentCandidates, t)} />
        <CoverageEntry label={t("coverage.profiles")} value={sourceStatusLabel(response.sourceStatus.profileChecks, t)} />
        <CoverageEntry label={t("coverage.signals")} value={sourceStatusLabel(response.sourceStatus.signals, t)} />
        <CoverageEntry label={t("coverage.scanned")} value={t("coverage.noteCount", { count: workspace.scannedNoteCount })} />
      </dl>
    </details>
  );
}

function CoverageEntry({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function ContinuationFooter({ workspace }: { workspace: ReturnType<typeof useCardsTriageWorkspace> }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const visible = workspace.hasMoreContent
    || workspace.continuationStatus === "loading"
    || workspace.continuationStatus === "error"
    || workspace.continuationStatus === "capped"
    || workspace.loadedContentPages > 0;
  if (!visible) return null;
  return (
    <footer className="cards-inbox-continuation" data-testid="cards-continuation">
      <div>
        <strong>{t("continuation.title")}</strong>
        <p>{workspace.continuationStatus === "capped" ? t("continuation.capped") : workspace.continuationStatus === "exhausted" ? t("continuation.exhausted") : t("continuation.help")}</p>
        {workspace.continuationStatus === "error" ? <p className="is-error" role="alert">{t("continuation.error")}</p> : null}
        {workspace.lastContinuationAddedCount === 0 ? <p role="status">{t("continuation.noNew")}</p> : null}
      </div>
      {workspace.hasMoreContent || workspace.continuationStatus === "error" ? (
        <button type="button" className="secondary-button" disabled={workspace.continuationStatus === "loading"} onClick={() => void workspace.continueContentScan()}>
          {workspace.continuationStatus === "loading" ? t("continuation.loading") : workspace.continuationStatus === "error" ? t("continuation.retry") : t("continuation.action")}
        </button>
      ) : null}
    </footer>
  );
}

function WorkspaceMessage({ title, text, action, alert = false, status = false }: { title: string; text: string; action?: ReactNode; alert?: boolean; status?: boolean }) {
  return <div className="cards-inbox-message" role={alert ? "alert" : status ? "status" : undefined}><strong>{title}</strong><p>{text}</p>{action}</div>;
}
