import { AlertTriangle, BellRing, CircleAlert, Info, Megaphone } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { NotificationItem } from "../lib/notificationsApi";
import { writeNotificationHandoff } from "../lib/notificationHandoff";

export function notificationDestination(item: NotificationItem): string | null {
  if (item.category === "workload") return "/stats/load";
  if (item.category === "retention") return "/stats/quality";
  if (item.category === "deck_health") return "/decks";
  if (item.category === "card_problems") return "/search";
  return null;
}

export function openNotificationDestination(item: NotificationItem, onOpenWhatsNew: () => void): void {
  if (item.category === "product_updates") {
    onOpenWhatsNew();
    return;
  }
  const destination = notificationDestination(item);
  if (!destination) return;
  if (item.entity?.id) {
    if ((item.category === "deck_health" && item.entity.type === "deck") || (item.category === "card_problems" && item.entity.type === "card")) {
      writeNotificationHandoff({ category: item.category, entityType: item.entity.type, entityId: item.entity.id, createdAt: new Date().toISOString() });
    }
  }
  window.location.hash = destination;
}

export function notificationCopy(item: NotificationItem, t: (key: string, values?: Record<string, unknown>) => string): { title: string; evidence: string } {
  const evidence = item.evidence;
  if (item.category === "workload") return {
    title: t("signals.workload.title"),
    evidence: t("signals.workload.evidence", { current: evidence.currentLoad ?? 0, baseline: evidence.baselineMedian ?? 0 }),
  };
  if (item.category === "retention") return {
    title: t("signals.retention.title"),
    evidence: t("signals.retention.evidence", { drop: evidence.dropPoints ?? 0, recent: evidence.recentAnswers ?? 0 }),
  };
  if (item.category === "deck_health") return {
    title: t("signals.deck.title"),
    evidence: t("signals.deck.evidence", { health: evidence.health ?? "warning", reviews: evidence.reviews ?? 0 }),
  };
  if (item.category === "card_problems") return {
    title: t("signals.card.title"),
    evidence: t("signals.card.evidence", { again: evidence.againCount ?? 0, reviews: evidence.reviewCount ?? 0 }),
  };
  return { title: t("signals.release.title"), evidence: t("signals.release.evidence") };
}

export default function NotificationItemCard({ item, compact = false, onOpenWhatsNew, onRead }: { item: NotificationItem; compact?: boolean; onOpenWhatsNew: () => void; onRead?: (id: string) => void }) {
  const { t, i18n } = useTranslation("notifications");
  const copy = notificationCopy(item, t);
  const Icon = item.category === "product_updates" ? Megaphone : item.severity === "critical" ? CircleAlert : item.severity === "warning" ? AlertTriangle : Info;
  const destination = notificationDestination(item);
  const unread = item.readAt === null;
  const action = t(`actions.${item.category}`);
  const activate = () => {
    if (unread) onRead?.(item.notificationId);
    openNotificationDestination(item, onOpenWhatsNew);
  };
  return (
    <article className={["rounded-xl border p-3", unread ? "border-report-blue/45 bg-report-blue/10" : "border-ink-700 bg-ink-900/45"].join(" ")} data-testid="notification-item">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-report-blue"><Icon size={18} aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-report-text">{copy.title}</h3>
            {unread ? <span className="h-2 w-2 rounded-full bg-report-blue" aria-label={t("unread")} /> : null}
          </div>
          <p className={`mt-1 text-sm leading-5 text-report-secondary ${compact ? "line-clamp-2" : ""}`}>{copy.evidence}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-report-muted">
            <time dateTime={item.createdAt}>{new Intl.DateTimeFormat(i18n.resolvedLanguage?.startsWith("en") ? "en" : "ru", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.createdAt))}</time>
            {item.signalStatus ? <span>· {t(item.signalStatus)}</span> : null}
            {item.kind === "severity_escalated" ? <span className="inline-flex items-center gap-1"><BellRing size={12} aria-hidden="true" />↑</span> : null}
          </div>
          {!compact || destination || item.category === "product_updates" ? (
            <button type="button" className="mt-2 text-sm font-medium text-report-blue underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-report-blue/60" onClick={activate}>
              {action}
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
