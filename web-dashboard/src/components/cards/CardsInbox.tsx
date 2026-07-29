import { useTranslation } from "react-i18next";
import { cardDisplayText } from "../../lib/cardDisplayText";
import { reasonLabel, stateLabel } from "../../lib/triagePresentation";
import type { TriageItem } from "../../types/triage";

export interface CardsInboxProps {
  items: TriageItem[];
  activeId: string | null;
  resolvedId?: string | null;
  detailRegionId: string;
  drawerMode: boolean;
  drawerOpen: boolean;
  busy?: boolean;
  onActivate: (item: TriageItem, button: HTMLButtonElement) => void;
}

export function CardsInbox({
  items,
  activeId,
  resolvedId = null,
  detailRegionId,
  drawerMode,
  drawerOpen,
  busy = false,
  onActivate,
}: CardsInboxProps) {
  return (
    <ol className="cards-inbox-list" data-testid="cards-inbox">
      {items.map((item) => (
        <CardsInboxItem
          key={item.itemId}
          item={item}
          active={item.itemId === activeId}
          resolved={item.itemId === resolvedId}
          detailRegionId={detailRegionId}
          drawerMode={drawerMode}
          drawerOpen={drawerOpen}
          busy={busy && item.itemId === activeId}
          onActivate={onActivate}
        />
      ))}
    </ol>
  );
}

function CardsInboxItem({
  item,
  active,
  resolved,
  detailRegionId,
  drawerMode,
  drawerOpen,
  busy,
  onActivate,
}: {
  item: TriageItem;
  active: boolean;
  resolved: boolean;
  detailRegionId: string;
  drawerMode: boolean;
  drawerOpen: boolean;
  busy?: boolean;
  onActivate: CardsInboxProps["onActivate"];
}) {
  const { t } = useTranslation("pages", { keyPrefix: "cards.workspace" });
  const reason = item.reasons[0];
  const itemKey = safeId(item.itemId);
  const identityId = `${itemKey}-identity`;
  const contextId = `${itemKey}-context`;
  const reasonId = reason ? `${itemKey}-reason` : null;
  const statusId = `${itemKey}-status`;
  const describedBy = [contextId, reasonId, statusId].filter(Boolean).join(" ");
  const text = cardDisplayText(item);

  return (
    <li className="cards-inbox-list-item" data-testid="cards-inbox-list-item">
      <button
        id={`${itemKey}-button`}
        type="button"
        className={`cards-inbox-item workspace-interactive${active ? " is-active workspace-selected" : ""}${busy ? " is-busy" : ""}${resolved ? " is-resolved" : ""}`}
        data-card-id={item.cardId}
        data-testid="cards-inbox-item"
        data-busy={busy ? "true" : "false"}
        aria-current={active ? "true" : undefined}
        aria-labelledby={identityId}
        aria-describedby={describedBy}
        aria-controls={detailRegionId}
        aria-expanded={drawerMode ? active && drawerOpen : undefined}
        onClick={(event) => onActivate(item, event.currentTarget)}
      >
        <span className="cards-inbox-item-main">
          <span className="cards-inbox-item-title-row">
            <strong id={identityId} className="cards-inbox-item-identity" title={text}>{text}</strong>
            {resolved ? <span className="cards-inbox-resolved-marker">{t("queue.resolved")}</span> : null}
          </span>
          <span id={contextId} className="cards-inbox-item-meta">
            <span title={item.deck.name}>{item.deck.name || "—"}</span>
            <span aria-hidden="true">·</span>
            <span>{item.noteType.name || t("queue.unknownType")}</span>
          </span>
          {reason ? (
            <span id={reasonId ?? undefined} className="cards-inbox-item-reason-row">
              <span>{reasonLabel(reason.code, t)}</span>
              {item.reasons.length > 1 ? <span>{t("queue.moreReasons", { count: item.reasons.length - 1 })}</span> : null}
            </span>
          ) : null}
        </span>
        <span id={statusId} className={`cards-inbox-status${active ? " is-active" : ""}${resolved ? " is-resolved" : ""}`}>
          <span className="sr-only">{resolved ? t("queue.resolved") : stateLabel(item, t)}</span>
        </span>
      </button>
    </li>
  );
}

function safeId(value: string): string {
  return `cards-inbox-${value.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}
