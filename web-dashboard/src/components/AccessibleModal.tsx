import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export default function AccessibleModal({
  title,
  closeLabel,
  onRequestClose,
  children,
  footer,
  testId,
  portal = false,
  className = "",
}: {
  title: string;
  closeLabel: string;
  onRequestClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  testId: string;
  portal?: boolean;
  className?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const titleId = `${testId}-title`;

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const shell = document.getElementById("dashboard-app-shell");
    const previousAriaHidden = shell?.getAttribute("aria-hidden");
    const previousInert = shell?.inert ?? false;
    const previousOverflow = document.body.style.overflow;
    if (shell) {
      shell.inert = true;
      shell.setAttribute("aria-hidden", "true");
    }
    document.body.style.overflow = "hidden";
    headingRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onRequestClose();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])
        .filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) {
        event.preventDefault();
        headingRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (shell) {
        shell.inert = previousInert;
        if (previousAriaHidden === null || previousAriaHidden === undefined) shell.removeAttribute("aria-hidden");
        else shell.setAttribute("aria-hidden", previousAriaHidden);
      }
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [onRequestClose]);

  const modal = (
    <div className="product-modal-backdrop" data-testid={`${testId}-backdrop`}>
      <div
        ref={dialogRef}
        className={`product-modal ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid={testId}
      >
        <header className="product-modal-header">
          <h2 ref={headingRef} id={titleId} tabIndex={-1}>{title}</h2>
          <button type="button" className="product-modal-close" aria-label={closeLabel} onClick={onRequestClose}>
            <X size={19} aria-hidden="true" />
          </button>
        </header>
        <div className="product-modal-content">{children}</div>
        {footer ? <footer className="product-modal-footer">{footer}</footer> : null}
      </div>
    </div>
  );
  return portal ? createPortal(modal, document.body) : modal;
}
