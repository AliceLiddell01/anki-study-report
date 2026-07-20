import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cardDisplayText } from "../../lib/cardDisplayText";
import { evidenceLabel, reasonLabel, scopeLabel, stateLabel } from "../../lib/triagePresentation";
import type { TriageItem } from "../../types/triage";

export interface CardsInboxProps {
  items: TriageItem[];
  activeId: string | null;
  detailRegionId: string;
  drawerMode: boolean;
  drawerOpen: boolean;
  onActivate: (item: TriageItem, button: HTMLButtonElement) => void;
}

export function CardsInbox({
  items,
  activeId,
  detailRegionId,
  drawerMode,
  drawerOpen,
  onActivate,
}: CardsInboxProps) {
  return (
    <ol className="cards-inbox-list" data-testid="cards-inbox">
      {items.map((item, index) => (
        <CardsInboxItem
          key={item.itemId}
          item={item}
          index={index}
          active={item.itemId === activeId}
          detailRegionId={detailRegionId}
          drawerMode={drawerMode}
          drawerOpen={drawerOpen}
          onActivate={onActivate}
        />
      ))}
    </ol>
  );
}

function CardsInboxItem({
  item,
  index,
  active,
  detailRegionId,
  drawerMode,
  drawerOpen,
  onActivate,
}: {
  item: TriageItem;
  index: number;
  active: boolean;
  detailRegionId: string;
  drawerMode: boolean;
  drawerOpen: boolean;
  onActivate: CardsInboxProps["onActivate"];
}) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const reason = item.reasons[0];
  const itemKey = safeId(item.itemId);
  const identityId = `${itemKey}-identity`;
  const priorityId = `${itemKey}-priority`;
  const reasonId = `${itemKey}-reason`;
  const evidenceId = `${itemKey}-evidence`;
  const metadataId = `${itemKey}-metadata`;
  const scopeId = reason?.scope === "note" ? `${itemKey}-scope` : null;
  const describedBy = [priorityId, reasonId, evidenceId, metadataId, scopeId].filter(Boolean).join(" ");
  const text = cardDisplayText(item);

  return (
    <li className="cards-inbox-list-item" data-testid="cards-inbox-list-item">
      <button
        type="button"
        className={`cards-inbox-item${active ? " is-active" : ""}`}
        data-card-id={item.cardId}
        data-testid="cards-inbox-item"
        aria-current={active ? "true" : undefined}
        aria-labelledby={identityId}
        aria-describedby={describedBy}
        aria-controls={detailRegionId}
        aria-expanded={drawerMode ? active && drawerOpen : undefined}
        onClick={(event) => onActivate(item, event.currentTarget)}
      >
        <span className="cards-inbox-item-leading">
          <span id={priorityId} className={`cards-inbox-priority is-${item.priority || "neutral"}`}>
            {item.priority ? t(`priorities.${item.priority}`) : t("priorities.neutral")}
          </span>
          <span className="cards-inbox-position" aria-hidden="true">{index + 1}</span>
        </span>
        <span className="cards-inbox-item-main">
          <span className="cards-inbox-item-title-row">
            <strong id={identityId} className="cards-inbox-item-identity" title={text}>{text}</strong>
            {active ? <span className="cards-inbox-active-marker">{t("queue.active")}</span> : null}
          </span>
          <span className="cards-inbox-item-reason-row">
            <strong id={reasonId}>{reason ? reasonLabel(reason.code, t) : t("reasons.manual")}</strong>
            {item.reasons.length > 1 ? <span>{t("queue.moreReasons", { count: item.reasons.length - 1 })}</span> : null}
          </span>
          <span id={evidenceId} className="cards-inbox-item-evidence">
            {reason ? evidenceLabel(reason.evidence[0], t) : t("evidence.unavailable")}
          </span>
          <span id={metadataId} className="cards-inbox-item-meta">
            <span title={item.deck.name}>{item.deck.name || "—"}</span>
            <span aria-hidden="true">·</span>
            <span>{stateLabel(item, t)}</span>
            {item.noteType.name ? <><span aria-hidden="true">·</span><span>{item.noteType.name}</span></> : null}
          </span>
          {scopeId ? <span id={scopeId} className="cards-inbox-item-scope">{scopeLabel(reason, t)}</span> : null}
        </span>
        <ChevronRight className="cards-inbox-item-chevron" size={18} aria-hidden="true" />
      </button>
    </li>
  );
}

function safeId(value: string): string {
  return `cards-inbox-${value.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}
