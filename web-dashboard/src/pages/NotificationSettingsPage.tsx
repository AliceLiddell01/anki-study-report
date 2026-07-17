import { BellRing } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NOTIFICATIONS_UPDATED_EVENT } from "../components/NotificationBell";
import { fetchNotificationPreferences, saveNotificationPreferences, type NotificationCategory, type NotificationPreferences, type NotificationSeverity } from "../lib/notificationsApi";

const categories: NotificationCategory[] = ["workload", "retention", "deck_health", "card_problems", "product_updates"];

export default function NotificationSettingsPage() {
  const { t } = useTranslation("notifications");
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    void fetchNotificationPreferences().then((value) => { if (!cancelled) setPreferences(value); }).catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, []);

  const save = async () => {
    if (!preferences) return;
    setSaving(true);
    setMessage("");
    try {
      const saved = await saveNotificationPreferences({
        showUnreadBadge: preferences.showUnreadBadge,
        showInAppToasts: preferences.showInAppToasts,
        minimumToastSeverity: preferences.minimumToastSeverity,
        toastCategories: preferences.toastCategories,
      });
      setPreferences(saved);
      setMessage(t("settings.saved"));
      window.dispatchEvent(new Event(NOTIFICATIONS_UPDATED_EVENT));
    } catch {
      setMessage(t("settings.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  if (failed) return <section className="rounded-xl border border-report-danger/45 bg-ink-850 p-5">{t("unavailable")}</section>;
  if (!preferences) return <section className="rounded-xl border border-ink-700 bg-ink-850 p-5">{t("loading")}</section>;

  const update = <K extends keyof NotificationPreferences>(key: K, value: NotificationPreferences[K]) => setPreferences((current) => current ? { ...current, [key]: value } : current);
  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-start gap-3">
          <span className="brand-icon-badge mt-0.5 h-10 w-10 shrink-0 rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue"><BellRing size={20} aria-hidden="true" /></span>
          <div><h1 className="text-2xl font-semibold text-report-text">{t("settings.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-report-secondary">{t("settings.description")}</p></div>
        </div>
      </section>
      <section className="grid gap-5 rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <PreferenceToggle label={t("settings.badge")} description={t("settings.badgeDescription")} checked={preferences.showUnreadBadge} onChange={(checked) => update("showUnreadBadge", checked)} />
        <PreferenceToggle label={t("settings.toasts")} description={t("settings.toastsDescription")} checked={preferences.showInAppToasts} onChange={(checked) => update("showInAppToasts", checked)} />
        <label className="grid max-w-sm gap-2 text-sm font-medium text-report-text" htmlFor="minimum-toast-severity">
          {t("settings.minimum")}
          <select id="minimum-toast-severity" className="form-control px-3 py-2 text-report-text" value={preferences.minimumToastSeverity} disabled={!preferences.showInAppToasts} onChange={(event) => update("minimumToastSeverity", event.target.value as NotificationSeverity)}>
            <option value="critical">{t("settings.critical")}</option><option value="warning">{t("settings.warning")}</option><option value="info">{t("settings.info")}</option>
          </select>
        </label>
        <fieldset className="grid gap-3" disabled={!preferences.showInAppToasts}>
          <legend className="text-sm font-semibold text-report-text">{t("settings.categories")}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {categories.map((category) => <label key={category} className="flex min-h-11 items-center gap-3 rounded-lg border border-ink-700 px-3 text-sm text-report-secondary"><input type="checkbox" className="h-4 w-4 accent-report-blue" checked={preferences.toastCategories[category]} onChange={(event) => update("toastCategories", { ...preferences.toastCategories, [category]: event.target.checked })} />{t(`categories.${category}`)}</label>)}
          </div>
        </fieldset>
        <p className="text-xs text-report-muted">{t("settings.sound")}</p>
        <div className="flex items-center gap-3"><button type="button" className="min-h-10 rounded-lg border border-report-blue/60 bg-report-blue/15 px-4 text-sm font-medium text-report-text disabled:opacity-50" disabled={saving} onClick={() => void save()}>{saving ? t("settings.saving") : t("settings.save")}</button>{message ? <p role="status" className="text-sm text-report-secondary">{message}</p> : null}</div>
      </section>
    </div>
  );
}

function PreferenceToggle({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex items-start justify-between gap-4 rounded-lg border border-ink-700 p-3"><span><span className="block text-sm font-medium text-report-text">{label}</span><span className="mt-1 block text-xs leading-5 text-report-muted">{description}</span></span><input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-report-blue" checked={checked} onChange={(event) => onChange(event.target.checked)} /></label>;
}
