import { X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { acknowledgeToastDelivery, fetchToastCandidates, type NotificationItem } from "../lib/notificationsApi";
import { NOTIFICATION_PANEL_EVENT, NOTIFICATIONS_UPDATED_EVENT } from "./NotificationBell";
import { notificationCopy } from "./NotificationItemCard";

type Toast = { id: string; severity: "info" | "warning" | "critical"; title: string; evidence: string; notificationIds: string[] };

export default function NotificationToasts() {
  const { t } = useTranslation("notifications");
  const sessionStartedAt = useRef(new Date().toISOString());
  const [queue, setQueue] = useState<Toast[]>([]);
  const [paused, setPaused] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const accepted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    void fetchToastCandidates(sessionStartedAt.current).then((items) => {
      if (cancelled || accepted.current || items.length === 0) return;
      accepted.current = true;
      const next = buildNotificationToastQueue(items, t);
      setQueue(next);
      void acknowledgeToastDelivery(next.flatMap((item) => item.notificationIds)).then(() => window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT))).catch(() => undefined);
    }).catch(() => undefined);
    const panel = (event: Event) => setPanelOpen(Boolean((event as CustomEvent<{ open?: boolean }>).detail?.open));
    window.addEventListener(NOTIFICATION_PANEL_EVENT, panel);
    return () => { cancelled = true; window.removeEventListener(NOTIFICATION_PANEL_EVENT, panel); };
  }, [t]);

  const current = queue[0];
  const timeoutMs = useMemo(() => current && current.severity !== "critical" ? 8000 : null, [current]);
  useEffect(() => {
    if (!current || paused || panelOpen || timeoutMs === null) return;
    const timer = window.setTimeout(() => setQueue((items) => items.slice(1)), timeoutMs);
    return () => window.clearTimeout(timer);
  }, [current, panelOpen, paused, timeoutMs]);

  if (!current || panelOpen) return null;
  return (
    <div className="fixed right-4 top-20 z-[45] w-[min(92vw,23rem)]" data-testid="notification-toast-viewport">
      <div role={current.severity === "critical" ? "alert" : "status"} aria-live={current.severity === "critical" ? "assertive" : "polite"} className={`rounded-xl border bg-ink-850 p-4 shadow-[var(--shadow-popover)] motion-reduce:transition-none ${current.severity === "critical" ? "border-red-500/60" : "border-report-blue/45"}`} onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setPaused(false); }}>
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1"><p className="font-semibold text-report-text">{current.title}</p><p className="mt-1 line-clamp-2 text-sm leading-5 text-report-secondary">{current.evidence}</p></div>
          <button type="button" className="rounded-md p-1 text-report-muted hover:bg-ink-700 hover:text-report-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-report-blue/60" aria-label={t("close")} onClick={() => setQueue((items) => items.slice(1))}><X size={17} aria-hidden="true" /></button>
        </div>
      </div>
    </div>
  );
}

export function buildNotificationToastQueue(items: NotificationItem[], t: (key: string, values?: Record<string, unknown>) => string): Toast[] {
  const visible = items.length > 3 ? items.slice(0, 2) : items.slice(0, 3);
  const result = visible.map((item) => {
    const copy = notificationCopy(item, t);
    return { id: item.notificationId, severity: item.severity, title: copy.title, evidence: copy.evidence, notificationIds: [item.notificationId] };
  });
  if (items.length > 3) {
    const collapsed = items.slice(2);
    result.push({ id: "summary", severity: "info", title: t("panelTitle"), evidence: t("summaryToast", { count: collapsed.length }), notificationIds: collapsed.map((item) => item.notificationId) });
  }
  return result;
}
