import { ExternalLink, Maximize2, RotateCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AnkiCardShadowPreview } from "../AnkiCardShadowPreview";
import type { CardsTriageWorkspace } from "../../hooks/useCardsTriageWorkspace";
import type { CardsResolutionState } from "../../hooks/useCardsTriageWorkspace";
import { cardDisplayText } from "../../lib/cardDisplayText";
import {
  evidenceLabel,
  reasonLabel,
  recommendedStep,
  scopeLabel,
  sourceLabel,
  stateLabel,
} from "../../lib/triagePresentation";
import type { SearchCardDetails } from "../../types/search";
import type { TriagePriority, TriageReason } from "../../types/triage";
import type { CardEntityAction } from "../../types/entityActions";

export interface CardsDetailProps {
  workspace: CardsTriageWorkspace;
  headingId: string;
  onExpandAnswer: () => void;
  emptyAllowed?: boolean;
}

export function CardsDetail({ workspace, headingId, onExpandAnswer, emptyAllowed = true }: CardsDetailProps) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const item = workspace.activeItem;
  const details = workspace.inspectResponse?.details;
  const actionLocked = workspace.mutationPending || ["awaiting_recheck", "rechecking"].includes(workspace.resolution?.phase ?? "idle");

  if (!item) {
    return emptyAllowed ? (
      <div className="cards-detail-empty" data-testid="cards-detail-empty">
        <h2 id={headingId}>{t("inspector.title")}</h2>
        <strong>{t("inspector.emptyTitle")}</strong>
        <p>{t("inspector.empty")}</p>
      </div>
    ) : null;
  }

  return (
    <div className="cards-detail-content" data-testid="cards-detail-content">
      <header className="cards-detail-header">
        <div className="cards-detail-heading-copy">
          <PriorityBadge value={item.priority} />
          <h2 id={headingId}>{cardDisplayText(item)}</h2>
          <p>{item.deck.name || "—"} · {item.noteType.name || t("queue.unknownType")} · {stateLabel(item, t)}</p>
        </div>
      </header>

      <section className="cards-detail-section" aria-labelledby={`${headingId}-reasons`}>
        <h3 id={`${headingId}-reasons`}>{t("inspector.reasons")}</h3>
        <div className="cards-detail-reasons">
          {item.reasons.map((reason, index) => <ReasonCard key={reason.reasonId} reason={reason} primary={index === 0} />)}
        </div>
      </section>

      <section className="cards-detail-section" aria-labelledby={`${headingId}-preview`}>
        <div className="cards-detail-section-heading">
          <h3 id={`${headingId}-preview`}>{t("preview.frontTitle")}</h3>
          {details ? (
            <button
              type="button"
              className="secondary-button cards-detail-expand"
              onClick={onExpandAnswer}
              disabled={!hasUsableBackPreview(details.renderedPreview)}
            >
              <Maximize2 size={16} aria-hidden="true" />
              {t("preview.expand")}
            </button>
          ) : null}
        </div>
        {workspace.inspectStatus === "loading" ? (
          <div className="cards-detail-preview-state" role="status">{t("preview.loading")}</div>
        ) : workspace.inspectStatus === "error" ? (
          <div className="cards-detail-preview-state is-error" role="alert">
            <span>{workspace.inspectError?.code === "search_entity_not_found" ? t("preview.stale") : t("preview.failed")}</span>
            <button type="button" className="secondary-button" onClick={workspace.retryInspect}>
              <RotateCw size={16} aria-hidden="true" />{t("retry")}
            </button>
          </div>
        ) : details ? (
          <>
            <CardPreview details={details} side="front" />
            {!hasUsableBackPreview(details.renderedPreview) ? <p className="cards-detail-preview-hint" role="status">{t("preview.answerUnavailable")}</p> : null}
          </>
        ) : (
          <div className="cards-detail-preview-state" role="status">{t("preview.unavailable")}</div>
        )}
      </section>

      <section className="cards-detail-section" aria-labelledby={`${headingId}-next`}>
        <h3 id={`${headingId}-next`}>{t("inspector.next")}</h3>
        <p className="cards-detail-next-copy">{recommendedStep(item, t)}</p>
        <p className="cards-detail-resolution-rule">{t("resolution.rule")}</p>
        <div className="cards-detail-actions">
          {safeActions(item).map((action, index) => (
            <button
              key={action}
              type="button"
              className={index === 0 ? "primary-button" : "secondary-button"}
              onClick={() => void workspace.runSafeAction(action)}
              disabled={workspace.openPending || actionLocked}
            >
              {workspace.resolution?.phase === "action_pending" ? t("actions.working") : t(`actions.${action}`)}
            </button>
          ))}
          <button type="button" className={safeActions(item).length ? "secondary-button" : "primary-button"} onClick={() => void workspace.openInAnki()} disabled={workspace.openPending || workspace.mutationPending || workspace.resolution?.phase === "rechecking"}>
            <ExternalLink size={16} aria-hidden="true" />
            {workspace.openPending ? t("actions.opening") : t("actions.open")}
          </button>
          {item.reasons.some((reason) => reason.family === "content") ? (
            <a className="secondary-button" href="#/settings/inspection-profiles">{t("profiles.action")}</a>
          ) : null}
        </div>
        {workspace.openResult ? (
          <p className={workspace.openResult.ok ? "cards-detail-action-status" : "cards-detail-action-status is-error"} role="status">
            {workspace.openResult.ok ? t("actions.opened") : t("actions.failed")}
          </p>
        ) : null}
        <ResolutionResult state={workspace.resolution} onRecheck={() => void workspace.recheckActive()} />
      </section>

      <details className="cards-detail-technical">
        <summary>{t("inspector.technical")}</summary>
        <dl>
          <Entry label={t("inspector.cardId")} value={details?.cardId ?? item.cardId} />
          <Entry label={t("inspector.noteId")} value={details?.noteId ?? item.noteId ?? "—"} />
          <Entry label={t("inspector.template")} value={details?.templateName ?? item.template.name} />
          <Entry label={t("inspector.noteType")} value={details?.noteTypeName ?? item.noteType.name} />
          <Entry label={t("inspector.tags")} value={details?.tags.join(" · ") || "—"} />
          <Entry label={t("inspector.sources")} value={item.sources.map((source) => t(`sources.${source}`)).join(" · ")} />
        </dl>
      </details>
    </div>
  );
}

function ResolutionResult({ state, onRecheck }: { state: CardsResolutionState | null; onRecheck: () => void }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  if (!state) return null;
  const canRecheck = ["awaiting_recheck", "still_active", "partially_resolved", "recheck_failed", "evidence_stale", "entity_missing", "entity_changed"].includes(state.phase);
  const noChanges = state.actionResult && "resultCode" in state.actionResult && state.actionResult.resultCode === "action.no_changes";
  const actionSucceeded = state.actionResult && "resultCode" in state.actionResult && !noChanges;
  return (
    <div className={`cards-resolution-state is-${state.phase}`} data-testid="cards-resolution-state" role="status" aria-live="polite" aria-busy={state.phase === "action_pending" || state.phase === "rechecking"}>
      <strong>{t(`resolution.states.${state.phase}.title`)}</strong>
      <p>{t(`resolution.states.${state.phase}.description`)}</p>
      {actionSucceeded ? <p>{t("resolution.actionSucceeded")}</p> : null}
      {noChanges ? <p>{t("resolution.noChanges")}</p> : null}
      {state.reconciliation ? (
        <div className="cards-resolution-reconciliation">
          <ReasonChangeList title={t("resolution.removed")} reasons={state.reconciliation.removed} className="is-removed" />
          <ReasonChangeList title={t("resolution.remaining")} reasons={state.reconciliation.remaining} />
          <ReasonChangeList title={t("resolution.added")} reasons={state.reconciliation.added} className="is-added" />
        </div>
      ) : null}
      {canRecheck ? (
        <button type="button" className="secondary-button" onClick={onRecheck}>
          <RotateCw size={16} aria-hidden="true" />{t("resolution.recheck")}
        </button>
      ) : null}
    </div>
  );
}

function ReasonChangeList({ title, reasons, className }: { title: string; reasons: TriageReason[]; className?: string }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  if (!reasons.length) return null;
  return (
    <div className={className}>
      <span>{title}</span>
      <ul>{reasons.map((reason) => <li key={reason.reasonId}>{reasonLabel(reason.code, t)}</li>)}</ul>
    </div>
  );
}

function safeActions(item: NonNullable<CardsTriageWorkspace["activeItem"]>): CardEntityAction[] {
  if (!item.reasons.some((reason) => reason.family === "learning")) return [];
  const actions: CardEntityAction[] = [item.cardState.suspended ? "unsuspend" : "suspend"];
  actions.push(item.cardState.buried ? "unbury" : "bury");
  return actions;
}

function ReasonCard({ reason, primary }: { reason: TriageReason; primary: boolean }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  return (
    <article className={primary ? "is-primary" : undefined}>
      <div className="cards-detail-reason-heading">
        <strong>{reasonLabel(reason.code, t)}</strong>
        <PriorityBadge value={reason.priority} />
      </div>
      <p>{scopeLabel(reason, t)} · {sourceLabel(reason, t)}</p>
      {reason.evidence.map((evidence, index) => (
        <p key={`${reason.reasonId}-${index}`} className="cards-detail-reason-evidence">{evidenceLabel(evidence, t)}</p>
      ))}
    </article>
  );
}

function PriorityBadge({ value }: { value: TriagePriority | null }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  return <span className={`cards-inbox-priority is-${value || "neutral"}`}>{value ? t(`priorities.${value}`) : t("priorities.neutral")}</span>;
}

function Entry({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value || "—"}</dd></div>;
}

export function CardPreview({ details, side }: { details: SearchCardDetails; side: "front" | "back" }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const preview = details.renderedPreview;
  const usable = side === "front" ? hasUsableFrontPreview(preview) : hasUsableBackPreview(preview);
  if (!usable) return <div className="cards-detail-preview-state" role="status">{t(side === "front" ? "preview.frontUnavailable" : "preview.answerUnavailable")}</div>;
  const html = side === "front"
    ? preview.frontHtml || plainTextHtml(preview.frontPlainText || "")
    : preview.backHtml || plainTextHtml(preview.backPlainText || "");
  const title = side === "front"
    ? preview.frontPlainText || cardDisplayText(details)
    : preview.backPlainText || t("preview.answerTitle");
  return (
    <div className={side === "back" ? "cards-detail-preview is-expanded" : "cards-detail-preview"}>
      <AnkiCardShadowPreview
        mode={side === "back" ? "expanded" : "preview"}
        side={side}
        html={htmlWithMediaToken(html)}
        css={preview.css || ""}
        title={title}
        cardOrd={preview.cardOrd || details.templateOrdinal}
        renderSource={preview.renderSource || ""}
      />
    </div>
  );
}

export function hasUsableBackPreview(preview: PreviewPayload): boolean {
  return hasUsablePreviewStatus(preview.renderStatus) && !!(preview.backHtml || preview.backPlainText);
}

function hasUsableFrontPreview(preview: PreviewPayload): boolean {
  return hasUsablePreviewStatus(preview.renderStatus) && !!(preview.frontHtml || preview.frontPlainText);
}

function hasUsablePreviewStatus(status: string): boolean {
  return status === "available" || status === "sanitized" || status === "fallback";
}

type PreviewPayload = { renderStatus: string; frontHtml?: string; backHtml?: string; frontPlainText?: string; backPlainText?: string };

function plainTextHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#39;").replace(/\n/g, "<br>");
}

function htmlWithMediaToken(html: string): string {
  return html.replace(/(\/api\/media\?name=[^\"'&<>]+)(?![^\"'<>]*token=)/g, (url) => appendToken(url));
}

function appendToken(url: string): string {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  return !token || /(?:^https?:|^file:|token=)/i.test(url)
    ? url
    : `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}
