import { ExternalLink, Maximize2, RefreshCw, RotateCw, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import AccessibleModal from "../components/AccessibleModal";
import { AnkiCardShadowPreview } from "../components/AnkiCardShadowPreview";
import { useCardsTriageWorkspace } from "../hooks/useCardsTriageWorkspace";
import { cardDisplayText } from "../lib/cardDisplayText";
import type { TriageEvidence, TriageItem, TriagePriority, TriageReason } from "../types/triage";
import type { StudyReport } from "../types/report";
import type { SearchCardDetails } from "../types/search";
import type { LoadState } from "./HomePage";

type PriorityFilter = "all" | TriagePriority;
type FamilyFilter = "all" | "learning" | "content";

export default function CardsPage({ report }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const deckIds = useMemo(() => (report?.deckHub?.scope.selectedDeckIds ?? []).map(String), [report?.deckHub?.scope.selectedDeckIds]);
  const workspace = useCardsTriageWorkspace(deckIds);
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [family, setFamily] = useState<FamilyFilter>("all");
  const [deck, setDeck] = useState("all");
  const [textFilter, setTextFilter] = useState("");
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setExpanded(false);
  }, [workspace.activeId]);

  const allItems = workspace.response?.items ?? [];
  const decks = useMemo(() => [...new Set(allItems.map((item) => item.deck.name).filter(Boolean))].sort((a, b) => a.localeCompare(b)), [allItems]);
  const visibleItems = useMemo(() => {
    const needle = textFilter.trim().toLocaleLowerCase();
    return allItems.filter((item) => {
      if (priority !== "all" && item.priority !== priority) return false;
      if (family !== "all" && !item.reasons.some((reason) => reason.family === family)) return false;
      if (deck !== "all" && item.deck.name !== deck) return false;
      return !needle || `${cardDisplayText(item)} ${item.deck.name} ${item.noteType.name}`.toLocaleLowerCase().includes(needle);
    });
  }, [allItems, deck, family, priority, textFilter]);
  const highCount = allItems.filter((item) => item.priority === "high").length;

  useEffect(() => {
    if (workspace.queryStatus !== "ready") return;
    if (!visibleItems.length) {
      if (workspace.activeId) workspace.clearActive();
      return;
    }
    if (!workspace.activeId || !visibleItems.some((item) => item.itemId === workspace.activeId)) {
      workspace.activate(visibleItems[0]!);
    }
  }, [visibleItems, workspace.activeId, workspace.activate, workspace.clearActive, workspace.queryStatus]);

  return <div className="cards-v2-page page-stack" data-testid="cards-v2-page">
    <header className="cards-v2-heading">
      <div><span className="page-eyebrow">{t("eyebrow")}</span><h1>{t("title")}</h1><p>{t("description")}</p></div>
      <span className="cards-v2-readonly">{t("readOnly")}</span>
    </header>

    <section className="cards-v2-controls panel-surface" aria-label={t("filters.label")}>
      <div className="cards-v2-summary" aria-live="polite">
        <strong>{workspace.response ? t("summary.items", { count: workspace.response.returnedCount }) : t("summary.loading")}</strong>
        {workspace.response ? <span>{t("summary.high", { count: highCount })}</span> : null}
        {workspace.response?.truncated ? <span className="is-warning">{t("summary.truncated", { count: workspace.response.limit })}</span> : null}
      </div>
      <div className="cards-v2-filter-row">
        <label><span>{t("filters.priority")}</span><select value={priority} onChange={(event) => setPriority(event.target.value as PriorityFilter)}><option value="all">{t("filters.allPriorities")}</option><option value="high">{t("priorities.high")}</option><option value="medium">{t("priorities.medium")}</option><option value="low">{t("priorities.low")}</option></select></label>
        <label><span>{t("filters.reason")}</span><select value={family} onChange={(event) => setFamily(event.target.value as FamilyFilter)}><option value="all">{t("filters.allReasons")}</option><option value="learning">{t("families.learning")}</option><option value="content">{t("families.content")}</option></select></label>
        <label><span>{t("filters.deck")}</span><select value={deck} onChange={(event) => setDeck(event.target.value)}><option value="all">{t("filters.allDecks")}</option>{decks.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
        <label className="cards-v2-text-filter"><span>{t("filters.text")}</span><input value={textFilter} onChange={(event) => setTextFilter(event.target.value)} placeholder={t("filters.textPlaceholder")} /></label>
        <button type="button" className="secondary-button" onClick={workspace.refresh} disabled={workspace.queryStatus === "loading"}><RefreshCw size={16} aria-hidden="true" />{t("refresh")}</button>
      </div>
    </section>

    {workspace.response?.contentChecks.status === "profiles_need_review" ? <div className="cards-v2-warning" role="status"><TriangleAlert size={18} aria-hidden="true" /><span><strong>{t("profiles.title", { count: workspace.response.contentChecks.needsReviewProfileCount })}</strong> {t("profiles.description")}</span><a className="secondary-button" href="#/settings/inspection-profiles">{t("profiles.action")}</a></div> : null}
    {workspace.response?.status === "partial" ? <div className="cards-v2-partial" role="status"><TriangleAlert size={17} aria-hidden="true" />{t("states.partial")}</div> : null}

    <div className="cards-v2-workspace">
      <section className="cards-v2-queue panel-surface" aria-labelledby="cards-v2-queue-title">
        <header><div><h2 id="cards-v2-queue-title">{t("queue.title")}</h2><p>{workspace.response ? t("queue.visible", { visible: visibleItems.length, total: workspace.response.returnedCount }) : t("queue.period")}</p></div></header>
        <QueueState workspace={workspace} visibleItems={visibleItems} filtersActive={priority !== "all" || family !== "all" || deck !== "all" || !!textFilter.trim()} onClear={() => { setPriority("all"); setFamily("all"); setDeck("all"); setTextFilter(""); }} />
      </section>
      <Inspector workspace={workspace} onExpand={() => setExpanded(true)} />
    </div>

    {expanded && workspace.inspectResponse && hasUsableBackPreview(workspace.inspectResponse.details.renderedPreview) ? <AccessibleModal title={t("preview.expandedTitle")} closeLabel={t("preview.close")} onRequestClose={() => setExpanded(false)} testId="cards-preview-modal" portal className="cards-answer-modal" footer={<button type="button" className="secondary-button" onClick={() => setExpanded(false)}>{t("preview.close")}</button>}><Preview details={workspace.inspectResponse.details} side="back" /></AccessibleModal> : null}
  </div>;
}

function QueueState({ workspace, visibleItems, filtersActive, onClear }: { workspace: ReturnType<typeof useCardsTriageWorkspace>; visibleItems: TriageItem[]; filtersActive: boolean; onClear: () => void }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  if (workspace.queryStatus === "loading") return <WorkspaceMessage status title={t("states.loadingTitle")} text={t("states.loading")} />;
  if (workspace.queryStatus === "error") return <WorkspaceMessage alert title={t("states.errorTitle")} text={t("states.error")} action={<button type="button" className="secondary-button" onClick={workspace.refresh}><RotateCw size={16} aria-hidden="true" />{t("retry")}</button>} />;
  if (workspace.response?.status === "unavailable") return <WorkspaceMessage alert title={t("states.unavailableTitle")} text={t("states.unavailable")} action={<button type="button" className="secondary-button" onClick={workspace.refresh}>{t("retry")}</button>} />;
  if (!visibleItems.length) return <WorkspaceMessage title={filtersActive ? t("states.filteredTitle") : t("states.emptyTitle")} text={filtersActive ? t("states.filtered") : t("states.empty")} action={filtersActive ? <button type="button" className="secondary-button" onClick={onClear}>{t("filters.clear")}</button> : undefined} />;
  return <div className="cards-v2-table-wrap"><table className="cards-v2-table" data-testid="cards-triage-table"><thead><tr><th>{t("columns.priority")}</th><th>{t("columns.card")}</th><th>{t("columns.reason")}</th><th className="cards-v2-evidence-column">{t("columns.evidence")}</th><th className="cards-v2-deck-column">{t("columns.deck")}</th><th className="cards-v2-state-column">{t("columns.state")}</th></tr></thead><tbody>{visibleItems.map((item) => <QueueRow key={item.itemId} item={item} active={workspace.activeId === item.itemId} onActivate={() => workspace.activate(item)} />)}</tbody></table></div>;
}

function QueueRow({ item, active, onActivate }: { item: TriageItem; active: boolean; onActivate: () => void }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const reason = item.reasons[0];
  return <tr className={active ? "is-active" : ""} aria-current={active ? "true" : undefined} data-testid="cards-triage-row"><td><PriorityBadge value={item.priority} /></td><td><button type="button" className="cards-v2-row-activate" onClick={onActivate}><strong>{cardDisplayText(item)}</strong><span>{item.noteType.name || t("queue.unknownType")}</span></button></td><td><strong>{reason ? reasonLabel(reason.code, t) : t("reasons.manual")}</strong><span className="cards-v2-secondary">{item.reasons.length > 1 ? t("queue.moreReasons", { count: item.reasons.length - 1 }) : scopeLabel(reason, t)}</span></td><td className="cards-v2-evidence-column">{reason ? evidenceLabel(reason.evidence[0], t) : "—"}</td><td className="cards-v2-deck-column"><span title={item.deck.name}>{item.deck.name || "—"}</span></td><td className="cards-v2-state-column">{stateLabel(item, t)}</td></tr>;
}

function Inspector({ workspace, onExpand }: { workspace: ReturnType<typeof useCardsTriageWorkspace>; onExpand: () => void }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const item = workspace.activeItem;
  const details = workspace.inspectResponse?.details;
  return <aside className="cards-v2-inspector panel-surface" aria-labelledby="cards-v2-inspector-title" data-testid="cards-inspector"><header><h2 id="cards-v2-inspector-title">{t("inspector.title")}</h2></header>{!item ? <WorkspaceMessage title={t("inspector.emptyTitle")} text={t("inspector.empty")} /> : <div className="cards-v2-inspector-body"><PriorityBadge value={item.priority} /><h3>{cardDisplayText(item)}</h3><p className="cards-v2-inspector-meta">{item.deck.name} · {item.noteType.name} · {item.template.name}</p>
    <section aria-labelledby="cards-preview-title"><h4 id="cards-preview-title">{t("preview.frontTitle")}</h4>{workspace.inspectStatus === "loading" ? <div className="cards-v2-preview-state" role="status">{t("preview.loading")}</div> : workspace.inspectStatus === "error" ? <div className="cards-v2-preview-state is-error" role="alert"><span>{workspace.inspectError?.code === "search_entity_not_found" ? t("preview.stale") : t("preview.failed")}</span><button type="button" className="secondary-button" onClick={workspace.retryInspect}>{t("retry")}</button></div> : details ? <><Preview details={details} side="front" /><button type="button" className="secondary-button cards-v2-expand" onClick={onExpand} disabled={!hasUsableBackPreview(details.renderedPreview)}><Maximize2 size={16} aria-hidden="true" />{t("preview.expand")}</button>{!hasUsableBackPreview(details.renderedPreview) ? <p className="cards-v2-preview-hint" role="status">{t("preview.answerUnavailable")}</p> : null}</> : null}</section>
    <section><h4>{t("inspector.reasons")}</h4><div className="cards-v2-reasons">{item.reasons.map((reason) => <ReasonCard key={reason.reasonId} reason={reason} />)}</div></section>
    {details ? <section><h4>{t("inspector.details")}</h4><dl className="cards-v2-details"><Entry label={t("columns.state")} value={stateLabel(item, t)} /><Entry label={t("inspector.noteType")} value={details.noteTypeName} /><Entry label={t("inspector.template")} value={details.templateName} /><Entry label={t("inspector.tags")} value={details.tags.join(" · ") || "—"} /><Entry label={t("inspector.cardId")} value={details.cardId} /><Entry label={t("inspector.noteId")} value={details.noteId} /></dl></section> : null}
    <section><h4>{t("inspector.next")}</h4><p>{recommendedStep(item, t)}</p><div className="cards-v2-actions"><button type="button" className="primary-button" onClick={() => void workspace.openInAnki()} disabled={workspace.openPending}><ExternalLink size={16} aria-hidden="true" />{workspace.openPending ? t("actions.opening") : t("actions.open")}</button>{item.reasons.some((reason) => reason.family === "content") ? <a className="secondary-button" href="#/settings/inspection-profiles">{t("profiles.action")}</a> : null}</div>{workspace.openResult ? <p className={workspace.openResult.ok ? "cards-v2-action-status" : "cards-v2-action-status is-error"} role="status">{workspace.openResult.ok ? t("actions.opened") : t("actions.failed")}</p> : null}</section>
  </div>}</aside>;
}

function Preview({ details, side }: { details: SearchCardDetails; side: "front" | "back" }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const preview = details.renderedPreview;
  const usable = side === "front" ? hasUsableFrontPreview(preview) : hasUsableBackPreview(preview);
  if (!usable) return <div className="cards-v2-preview-state" role="status">{t(side === "front" ? "preview.frontUnavailable" : "preview.answerUnavailable")}</div>;
  const html = side === "front"
    ? preview.frontHtml || plainTextHtml(preview.frontPlainText || "")
    : preview.backHtml || plainTextHtml(preview.backPlainText || "");
  const title = side === "front"
    ? preview.frontPlainText || cardDisplayText(details)
    : preview.backPlainText || t("preview.answerTitle");
  return <div className={side === "back" ? "cards-v2-preview is-expanded" : "cards-v2-preview"}><AnkiCardShadowPreview mode={side === "back" ? "expanded" : "preview"} side={side} html={htmlWithMediaToken(html)} css={preview.css || ""} title={title} cardOrd={preview.cardOrd || details.templateOrdinal} renderSource={preview.renderSource || ""} /></div>;
}

function ReasonCard({ reason }: { reason: TriageReason }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  return <article><strong>{reasonLabel(reason.code, t)}</strong><p>{scopeLabel(reason, t)} · {sourceLabel(reason.sources, t)}</p>{reason.evidence.map((evidence, index) => <p key={`${reason.reasonId}-${index}`} className="cards-v2-reason-evidence">{evidenceLabel(evidence, t)}</p>)}</article>;
}

function PriorityBadge({ value }: { value: TriagePriority | null }) { const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" }); return <span className={`cards-v2-priority is-${value || "neutral"}`}>{value ? t(`priorities.${value}`) : t("priorities.neutral")}</span>; }
function Entry({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value || "—"}</dd></div>; }
function WorkspaceMessage({ title, text, action, alert = false, status = false }: { title: string; text: string; action?: ReactNode; alert?: boolean; status?: boolean }) { return <div className="cards-v2-message" role={alert ? "alert" : status ? "status" : undefined}><strong>{title}</strong><p>{text}</p>{action}</div>; }

type Translate = (key: string, options?: Record<string, unknown>) => string;
function reasonLabel(code: string, t: Translate): string { return t(`reasons.${code.replace(/\./g, "_")}`, { defaultValue: code }); }
function scopeLabel(reason: TriageReason | undefined, t: Translate): string { if (!reason) return ""; const profile = reason.evidence.find((item) => item.kind === "profile_check"); return reason.scope === "note" ? t("scope.note", { count: profile?.kind === "profile_check" ? profile.affectedSiblingCount : 1 }) : t("scope.card"); }
function sourceLabel(sources: string[], t: Translate): string { return sources.map((source) => t(`sources.${source}`)).join(" · "); }
function evidenceLabel(evidence: TriageEvidence | undefined, t: Translate): string {
  if (!evidence) return t("evidence.unavailable");
  if (evidence.kind === "leech_state") return t("evidence.lapses", { count: evidence.lapses });
  if (evidence.kind === "review_counts") return t("evidence.again", { count: evidence.againCount });
  if (evidence.kind === "pass_rate") return t("evidence.passRate", { value: Math.round(evidence.passRate * 100) });
  if (evidence.kind === "answer_time") return t("evidence.answerTime", { value: new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(evidence.averageAnswerSeconds) });
  if (evidence.kind === "signal_evidence") return t("evidence.signal", { again: evidence.againCount, reviews: evidence.reviewCount, days: evidence.windowDays });
  if (evidence.marker) return t("evidence.marker", { marker: evidence.marker });
  if (evidence.expectedTextLength !== null) return t("evidence.length", { actual: evidence.actualTextLength ?? 0, expected: evidence.expectedTextLength });
  return t("evidence.profile", { condition: evidence.expectedCondition });
}
function stateLabel(item: TriageItem, t: Translate): string { const state = item.cardState.state; const base = state ? t(`states.card.${state}`) : t("states.card.unknown"); return item.cardState.flag ? `${base} · ${t("states.flag", { value: item.cardState.flag })}` : base; }
function recommendedStep(item: TriageItem, t: Translate): string { return item.reasons.some((reason) => reason.family === "content") ? t("inspector.recommendProfile") : t("inspector.recommendAnki"); }
type PreviewPayload = { renderStatus: string; frontHtml?: string; backHtml?: string; frontPlainText?: string; backPlainText?: string };
function hasUsablePreviewStatus(status: string): boolean { return status === "available" || status === "sanitized" || status === "fallback"; }
function hasUsableFrontPreview(preview: PreviewPayload): boolean { return hasUsablePreviewStatus(preview.renderStatus) && !!(preview.frontHtml || preview.frontPlainText); }
function hasUsableBackPreview(preview: PreviewPayload): boolean { return hasUsablePreviewStatus(preview.renderStatus) && !!(preview.backHtml || preview.backPlainText); }
function plainTextHtml(value: string): string { return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/\n/g, "<br>"); }
function htmlWithMediaToken(html: string): string { return html.replace(/(\/api\/media\?name=[^"'&<>]+)(?![^"'<>]*token=)/g, (url) => appendToken(url)); }
function appendToken(url: string): string { const token = new URLSearchParams(window.location.search).get("token") || ""; return !token || /(?:^https?:|^file:|token=)/i.test(url) ? url : `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`; }
