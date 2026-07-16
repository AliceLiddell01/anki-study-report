import { Bell } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchNotificationPreferences, fetchNotificationSummary, markAllNotificationsRead, markNotificationsRead, type NotificationSummary } from "../lib/notificationsApi";
import NotificationItemCard from "./NotificationItemCard";

export const NOTIFICATIONS_UPDATED_EVENT = "anki-study-report:notifications-updated";
export const NOTIFICATION_PANEL_EVENT = "anki-study-report:notification-panel";

export default function NotificationBell({ onOpenWhatsNew }: { onOpenWhatsNew: () => void }) {
  const { t } = useTranslation("notifications");
  const [summary, setSummary] = useState<NotificationSummary | null>(null);
  const [showBadge, setShowBadge] = useState(true);
  const [open, setOpen] = useState(false);
  const shellRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const refresh = useCallback(async () => {
    try {
      const [next, preferences] = await Promise.all([fetchNotificationSummary(), fetchNotificationPreferences()]);
      setSummary(next);
      setShowBadge(preferences.showUnreadBadge);
    } catch {
      setSummary(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
    window.addEventListener(NOTIFICATIONS_UPDATED_EVENT, refresh);
    return () => window.removeEventListener(NOTIFICATIONS_UPDATED_EVENT, refresh);
  }, [refresh]);

  useEffect(() => {
    window.dispatchEvent(new CustomEvent(NOTIFICATION_PANEL_EVENT, { detail: { open } }));
    if (!open) return;
    shellRef.current?.querySelector<HTMLElement>("[data-notification-panel-focus]")?.focus();
    const pointer = (event: PointerEvent) => {
      if (!shellRef.current?.contains(event.target as Node)) close(true);
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); close(true); }
    };
    document.addEventListener("pointerdown", pointer);
    document.addEventListener("keydown", keyboard);
    return () => { document.removeEventListener("pointerdown", pointer); document.removeEventListener("keydown", keyboard); };
  }, [open]);

  const close = (returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) requestAnimationFrame(() => triggerRef.current?.focus());
  };
  const markOne = async (id: string) => {
    try { setSummary(await markNotificationsRead([id])); window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT)); } catch { /* durable item remains unread */ }
  };
  const markAll = async () => {
    try { setSummary(await markAllNotificationsRead()); window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT)); } catch { /* durable item remains unread */ }
  };
  const unread = summary?.unreadCount ?? 0;

  return (
    <div className="relative shrink-0" ref={shellRef}>
      <button ref={triggerRef} type="button" className="relative inline-flex h-11 w-11 items-center justify-center rounded-xl border border-ink-700 bg-ink-850 text-report-text transition hover:border-report-blue/45 hover:bg-ink-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-report-blue/60" aria-label={t("bell")} aria-expanded={open} aria-controls="notification-panel" onClick={() => setOpen((value) => !value)}>
        <Bell size={19} aria-hidden="true" />
        {showBadge && unread > 0 ? <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-500 px-1 text-center text-[11px] font-bold leading-5 text-white" data-testid="notification-badge">{unread > 99 ? "99+" : unread}</span> : null}
      </button>
      {open ? (
        <div id="notification-panel" role="dialog" aria-modal="false" aria-labelledby="notification-panel-title" tabIndex={-1} data-notification-panel-focus className="popover-motion absolute right-0 top-[calc(100%+0.65rem)] z-50 w-[min(92vw,25rem)] rounded-xl border border-ink-700 bg-ink-850 p-3 shadow-[var(--shadow-popover)]">
          <div className="flex items-center justify-between gap-3 px-1 pb-3">
            <div><h2 id="notification-panel-title" className="font-semibold text-report-text">{t("panelTitle")}</h2><p className="text-xs text-report-muted">{t("unreadCount", { count: unread })}</p></div>
            <button type="button" className="text-xs font-medium text-report-blue hover:underline disabled:opacity-50" disabled={!unread} onClick={() => void markAll()}>{t("markAll")}</button>
          </div>
          <div className="grid max-h-[60vh] gap-2 overflow-y-auto">
            {summary?.items.length ? summary.items.slice(0, 8).map((item) => <NotificationItemCard key={item.notificationId} item={item} compact onOpenWhatsNew={() => { close(false); onOpenWhatsNew(); }} onRead={(id) => void markOne(id)} />) : <p className="rounded-lg border border-dashed border-ink-700 px-3 py-6 text-center text-sm text-report-muted">{t("empty")}</p>}
          </div>
          <a href="#/notifications" className="mt-3 flex min-h-10 items-center justify-center rounded-lg border border-report-blue/45 bg-report-blue/10 px-3 text-sm font-medium text-report-blue" onClick={() => close(false)}>{t("openAll")}</a>
        </div>
      ) : null}
    </div>
  );
}
