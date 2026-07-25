import { CheckCircle2, ExternalLink, Maximize2, RotateCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AnkiCardShadowPreview } from "../AnkiCardShadowPreview";
import type { CardsResolutionState, CardsTriageWorkspace } from "../../hooks/useCardsTriageWorkspace";
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
  const phase = workspace.resolution?.phase ?? "idle";
  const resolved = phase === "resolved";
  const actionLocked = workspace.mutationPending || ["awaiting_recheck", "rechecking"].includes(phase);

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
    <div className="cards-detail-content" data-testid="cards-detail-content" data-resolution-phase={phase}>
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true" data-testid="cards-resolution-live-status">
        {workspace.resolution ? `${t(`resolution.states.${phase}.title`)}. ${t(`resolution.states.${phase}.description`)}` : ""}
      </div>

      <header className="cards-detail-header">
        <div className="cards-detail-heading-copy">
          <div className={`cards-detail-state is-${phase}`} data-testid="cards-resolution-state">
            {resolved ? <CheckCircle2 size={15} aria-hidden="true" /> : <span className="cards-detail-state-dot" aria-hidden="true" />}
            <span>{t(`resolution.states.${phase}.title`)}</span>
          </div>
          <h2 id={headingId}>{cardDisplayText(item)}</h2>
          <p className="cards-detail-identity-meta">
            <span>{item.deck.name || "—"}</span>
            <span aria-hidden="true">·</span>
            <span>{item.noteType.name || t("queue.unknownType")}</span>
            <span aria-hidden="true">·</span>
            <span>{details?.templateName ?? item.template.name}</span>
            <span aria-hidden="true">·</span>
            <span>{stateLabel(item, t)}</span>
          </p>
        </div>
        {resolved ? <span className="cards-detail-resolved-badge">{t("queue.resolved")}</span> : <PriorityBadge value={item.priority} />}
      </header>

      <div className="cards-detail-workspace-body">
        <section className="cards-detail-preview-region" aria-labelledby={`${headingId}-preview`}>
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
          <div className="cards-detail-preview-frame">
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
          </div>
        </section>

        <aside className="cards-detail-resolution-rail" aria-label={t("inspector.resolutionRail")}>
          <section className="cards-detail-flow-section" aria-labelledby={`${headingId}-reasons`}>
            <h3 id={`${headingId}-reasons`}>{t("inspector.reasons")}</h3>
            {resolved ? (
              <div className="cards-detail-resolved-summary">
                <CheckCircle2 size={18} aria-hidden="true" />
                <p>{t("resolution.noActiveReasons")}</p>
              </div>
            ) : (
              <ul className="cards-detail-reasons">
                {item.reasons.map((reason, index) => <ReasonRow key={reason.reasonId} reason={reason} primary={index === 0} />)}
              </ul>
            )}
          </section>

          <section className="cards-detail-flow-section" aria-labelledby={`${headingId}-next`}>
            <h3 id={`${headingId}-next`}>{t("inspector.next")}</h3>
            <p className="cards-detail-next-copy">{resolved ? t("resolution.resolvedNext") : recommendedStep(item, t)}</p>
          </section>

          <section className="cards-detail-flow-section cards-detail-action-zone" aria-labelledby={`${headingId}-actions`}>
            <h3 id={`${headingId}-actions`}>{resolved ? t("inspector.result") : t("inspector.execution")}</h3>
            {resolved ? (
              <button type="button" className="primary-button cards-detail-next-card" onClick={workspace.advanceResolved}>
                {t("resolution.nextCard")}
              </button>
            ) : (
              <>
                <div className="cards-detail-actions">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => void workspace.openInAnki()}
                    disabled={workspace.openPending || workspace.mutationPending || phase === "rechecking"}
                  >
                    <ExternalLink size={16} aria-hidden="true" />
                    {workspace.openPending ? t("actions.opening") : t("actions.open")}
                  </button>
                  <div className="cards-detail-action-alternatives">
                    {safeActions(item).map((action) => (
                      <button
                        key={action}
                        type="button"
                        className="secondary-button"
                        onClick={() => void workspace.runSafeAction(action)}
                        disabled={workspace.openPending || actionLocked}
                      >
                        {phase === "action_pending" ? t("actions.working") : t(`actions.${action}`)}
                      </button>
                    ))}
                  </div>
                  {item.reasons.some((reason) => reason.family === "content") ? (
                    <a className="tertiary-button" href="#/settings/inspection-profiles">{t("profiles.action")}</a>
                  ) : null}
                </div>
                <p className="cards-detail-resolution-rule">{t("resolution.rule")}</p>
                <ResolutionResult
                  state={workspace.resolution}
                  headingId={`${headingId}-result`}
                  recheckDisabled={workspace.mutationPending}
                  onRecheck={() => void workspace.recheckActive()}
                />
              </>
            )}
          </section>
        </aside>
      </div>

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

function ResolutionResult({
  state,
  headingId,
  recheckDisabled,
  onRecheck,
}: {
  state: CardsResolutionState | null;
  headingId: string;
  recheckDisabled: boolean;
  onRecheck: () => void;
}) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  if (!state || state.phase === "resolved") return null;
  const canRecheck = ["awaiting_recheck", "still_active", "partially_resolved", "recheck_failed", "evidence_stale", "entity_missing", "entity_changed"].includes(state.phase);
  const noChanges = state.actionResult && "resultCode" in state.actionResult && state.actionResult.resultCode === "action.no_changes";
  const actionSucceeded = state.actionResult && "resultCode" in state.actionResult && !noChanges;
  const openResult = state.actionResult && "ok" in state.actionResult ? state.actionResult : null;
  const isError = state.phase === "action_failed" || state.phase === "recheck_failed";
  return (
    <div className={`cards-resolution-state is-${state.phase}${isError ? " is-error" : ""}`} data-testid="cards-resolution-result" aria-busy={state.phase === "action_pending" || state.phase === "rechecking"} aria-labelledby={headingId}>
      <h4 id={headingId}>{t(`resolution.states.${state.phase}.title`)}</h4>
      <p>{t(`resolution.states.${state.phase}.description`)}</p>
      {actionSucceeded ? <p>{t(`resolution.actionResults.${state.actionResult!.action}`)}</p> : null}
      {noChanges ? <p>{t("resolution.noChanges")}</p> : null}
      {openResult?.ok ? <p>{t("actions.opened")}</p> : null}
      {openResult && !openResult.ok ? <p>{t("actions.failed")}</p> : null}
      {state.actionError ? <p>{t("resolution.actionFailed")}</p> : null}
      {state.recheckError ? <p>{t("resolution.recheckFailed")}</p> : null}
      {state.reconciliation ? (
        <div className="cards-resolution-reconciliation">
          <ReasonChangeList title={t("resolution.removed")} reasons={state.reconciliation.removed} className="is-removed" />
          <ReasonChangeList title={t("resolution.remaining")} reasons={state.reconciliation.remaining} />
          <ReasonChangeList title={t("resolution.added")} reasons={state.reconciliation.added} className="is-added" />
        </div>
      ) : null}
      {canRecheck ? (
        <button type="button" className="secondary-button" onClick={onRecheck} disabled={recheckDisabled}>
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
  return [item.cardState.suspended ? "unsuspend" : "suspend", item.cardState.buried ? "unbury" : "bury"];
}

function ReasonRow({ reason, primary }: { reason: TriageReason; primary: boolean }) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  return (
    <li className={primary ? "is-primary" : undefined}>
      <div className="cards-detail-reason-heading">
        <strong>{reasonLabel(reason.code, t)}</strong>
        <PriorityBadge value={reason.priority} />
      </div>
      <p>{scopeLabel(reason, t)} · {sourceLabel(reason, t)}</p>
      {reason.evidence.map((evidence, index) => (
        <p key={`${reason.reasonId}-${index}`} className="cards-detail-reason-evidence">{evidenceLabel(evidence, t)}</p>
      ))}
    </li>
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
        css={cssWithMediaToken(preview.css || "")}
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

export function cssWithMediaToken(css: string): string {
  return css.replace(/\/api\/media\?name=[^\"'&\\)\s]+/g, (url) => appendToken(url));
}

function appendToken(url: string): string {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  return !token || /(?:^https?:|^file:|token=)/i.test(url)
    ? url
    : `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}
