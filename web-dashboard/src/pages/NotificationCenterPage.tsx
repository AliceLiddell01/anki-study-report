import { Bell, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import NotificationItemCard from "../components/NotificationItemCard";
import { NOTIFICATIONS_UPDATED_EVENT } from "../components/NotificationBell";
import {
  fetchNotifications,
  fetchNotificationSummary,
  markAllNotificationsRead,
  markNotificationsRead,
  type NotificationCategory,
  type NotificationList,
  type NotificationTab,
} from "../lib/notificationsApi";

const tabs: NotificationTab[] = ["all", "unread", "active"];
const categories: Array<NotificationCategory | "all"> = ["all", "workload", "retention", "deck_health", "card_problems", "product_updates"];

export default function NotificationCenterPage({ onOpenWhatsNew }: { onOpenWhatsNew: () => void }) {
  const { t } = useTranslation("notifications");
  const [tab, setTab] = useState<NotificationTab>("all");
  const [category, setCategory] = useState<NotificationCategory | "all">("all");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<NotificationList | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [next, summary] = await Promise.all([
        fetchNotifications({ page, pageLimit: 20, tab, category }),
        fetchNotificationSummary(),
      ]);
      setResult(next);
      setUnreadCount(summary.unreadCount);
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [category, page, tab]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { setPage(1); }, [category, tab]);

  const markOne = async (notificationId: string) => {
    try {
      await markNotificationsRead([notificationId]);
      window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT));
      await refresh();
    } catch { /* leave the durable unread state unchanged */ }
  };
  const markAll = async () => {
    try {
      await markAllNotificationsRead();
      window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT));
      await refresh();
    } catch { /* leave the durable unread state unchanged */ }
  };

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="brand-icon-badge mt-0.5 h-10 w-10 shrink-0 rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue"><Bell size={20} aria-hidden="true" /></span>
            <div>
              <h1 className="text-2xl font-semibold text-report-text">{t("title")}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-report-secondary">{t("subtitle")}</p>
              <p className="mt-1 text-xs text-report-muted">{t("unreadCount", { count: unreadCount })}</p>
            </div>
          </div>
          <button type="button" className="min-h-10 rounded-lg border border-report-blue/45 bg-report-blue/10 px-3 text-sm font-medium text-report-blue disabled:opacity-50" disabled={unreadCount === 0} onClick={() => void markAll()}>{t("markAll")}</button>
        </div>
        <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label={t("tabsLabel")}>
            {tabs.map((value) => <button key={value} type="button" role="tab" aria-selected={tab === value} className={`min-h-10 rounded-lg border px-3 text-sm font-medium ${tab === value ? "border-report-blue/60 bg-report-blue/15 text-report-text" : "border-ink-700 text-report-secondary hover:bg-ink-800"}`} onClick={() => setTab(value)}>{t(`tabs.${value}`)}</button>)}
          </div>
          <label className="grid gap-1 text-xs font-medium text-report-muted" htmlFor="notification-category">
            {t("categoryLabel")}
            <select id="notification-category" className="form-control min-w-52 px-3 py-2 text-sm text-report-text" value={category} onChange={(event) => setCategory(event.target.value as NotificationCategory | "all")}>
              {categories.map((value) => <option key={value} value={value}>{t(`categories.${value}`)}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="grid gap-3" aria-busy={loading}>
        {loading ? <p className="rounded-xl border border-ink-700 bg-ink-850 p-5 text-report-muted">{t("loading")}</p> : null}
        {!loading && failed ? <p className="rounded-xl border border-report-danger/45 bg-ink-850 p-5 text-report-secondary">{t("unavailable")}</p> : null}
        {!loading && !failed && result?.items.length === 0 ? <p className="rounded-xl border border-dashed border-ink-700 bg-ink-850 p-8 text-center text-report-muted">{t("noMatches")}</p> : null}
        {!loading && !failed ? result?.items.map((item) => <NotificationItemCard key={item.notificationId} item={item} onOpenWhatsNew={onOpenWhatsNew} onRead={(id) => void markOne(id)} />) : null}
      </section>

      {result && result.pageCount > 1 ? <nav className="flex items-center justify-center gap-3" aria-label={t("paginationLabel")}>
        <button type="button" aria-label={t("previousPage")} className="rounded-lg border border-ink-700 p-2 text-report-secondary disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={18} /></button>
        <span className="text-sm text-report-muted">{t("page", { page: result.page, count: result.pageCount })}</span>
        <button type="button" aria-label={t("nextPage")} className="rounded-lg border border-ink-700 p-2 text-report-secondary disabled:opacity-40" disabled={page >= result.pageCount} onClick={() => setPage((value) => value + 1)}><ChevronRight size={18} /></button>
      </nav> : null}
    </div>
  );
}
