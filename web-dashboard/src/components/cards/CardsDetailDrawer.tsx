import { X } from "lucide-react";
import { useCallback, useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface CardsDetailDrawerProps {
  open: boolean;
  labelledBy: string;
  regionId: string;
  closeLabel: string;
  contextLabel?: string;
  restoreFocusTo: HTMLElement | null;
  fallbackFocusTo: HTMLElement | null;
  onRequestClose: () => void;
  children: ReactNode;
}

export function CardsDetailDrawer({
  open,
  labelledBy,
  regionId,
  closeLabel,
  contextLabel,
  restoreFocusTo,
  fallbackFocusTo,
  onRequestClose,
  children,
}: CardsDetailDrawerProps) {
  const closeAndRestore = useCallback(() => {
    onRequestClose();
    queueMicrotask(() => {
      const target = restoreFocusTo?.isConnected ? restoreFocusTo : fallbackFocusTo?.isConnected ? fallbackFocusTo : null;
      target?.focus();
    });
  }, [fallbackFocusTo, onRequestClose, restoreFocusTo]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (document.querySelector('[aria-modal="true"]')) return;
      event.preventDefault();
      closeAndRestore();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [closeAndRestore, open]);

  if (!open) return null;
  return createPortal(
    <aside
      id={regionId}
      className="cards-detail-drawer workspace-region workspace-safe-area"
      role="region"
      aria-labelledby={labelledBy}
      data-testid="cards-detail-drawer"
    >
      <div className="cards-detail-drawer-bar">
        <span className="cards-detail-drawer-context">{contextLabel}</span>
        <button type="button" className="cards-detail-drawer-close" aria-label={closeLabel} onClick={closeAndRestore}>
          <X size={19} aria-hidden="true" />
        </button>
      </div>
      <div className="cards-detail-drawer-scroll">{children}</div>
    </aside>,
    document.body,
  );
}
