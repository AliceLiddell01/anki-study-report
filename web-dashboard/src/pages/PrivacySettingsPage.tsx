import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchPrivacy,
  savePrivacyChoices,
  type PrivacyResponse,
  type TelemetryPurpose,
} from "../lib/productNoticesApi";

const EMPTY_CHOICES: Record<TelemetryPurpose, boolean> = {
  reliabilityDiagnostics: false,
  featureUsage: false,
};

export default function PrivacySettingsPage({ onOpenWhatsNew }: { onOpenWhatsNew: () => void }) {
  const { t } = useTranslation("pages");
  const [response, setResponse] = useState<PrivacyResponse | null>(null);
  const [choices, setChoices] = useState(EMPTY_CHOICES);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    void fetchPrivacy().then((loaded) => {
      if (cancelled) return;
      setResponse(loaded);
      if (loaded.privacy) setChoices(loaded.privacy.telemetry.purposes);
    });
    return () => { cancelled = true; };
  }, []);

  const save = async () => {
    setSaving(true);
    setMessage("");
    const saved = await savePrivacyChoices(choices);
    setResponse(saved);
    if (saved.privacy) setChoices(saved.privacy.telemetry.purposes);
    setMessage(saved.ok ? t("privacy.settings.saved") : t("privacy.settings.saveFailed"));
    setSaving(false);
  };

  if (!response) {
    return <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">{t("privacy.settings.loading")}</section>;
  }
  if (!response.ok || !response.privacy) {
    return <section className="rounded-xl border border-report-danger/45 bg-ink-850 p-5 shadow-panel">{t("privacy.settings.loadFailed")}</section>;
  }

  const telemetry = response.privacy.telemetry;
  const statusKey = telemetry.requiresConsent ? "decisionRequired" : telemetry.status;
  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <div className="flex items-start gap-3">
          <span className="brand-icon-badge mt-0.5 h-10 w-10 shrink-0 rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue">
            <ShieldCheck size={20} aria-hidden="true" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-report-blue">{t("privacy.settings.eyebrow")}</p>
            <h1 className="mt-1 text-2xl font-semibold text-report-text">{t("privacy.settings.title")}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-report-secondary">{t("privacy.settings.description")}</p>
          </div>
        </div>
        <dl className="privacy-status-grid mt-5">
          <div><dt>{t("privacy.settings.status")}</dt><dd>{t(`privacy.status.${statusKey}`)}</dd></div>
          <div><dt>{t("privacy.settings.noticeVersion")}</dt><dd>{telemetry.privacyNoticeVersion}</dd></div>
          <div><dt>{t("privacy.settings.decidedAt")}</dt><dd>{telemetry.decidedAt ?? t("privacy.settings.notDecided")}</dd></div>
        </dl>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold text-report-text">{t("privacy.settings.purposes")}</h2>
        <p className="mt-2 text-sm text-report-secondary">{t("privacy.settings.purposesDescription")}</p>
        <div className="privacy-purpose-list mt-4">
          {(["reliabilityDiagnostics", "featureUsage"] as TelemetryPurpose[]).map((purpose) => (
            <label className="privacy-purpose-card" key={purpose}>
              <input
                type="checkbox"
                checked={choices[purpose]}
                disabled={saving}
                onChange={(event) => setChoices((current) => ({ ...current, [purpose]: event.target.checked }))}
              />
              <span>
                <strong>{t(`privacy.purposes.${purpose}.title`)}</strong>
                <span>{t(`privacy.purposes.${purpose}.description`)}</span>
              </span>
            </label>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" className="primary-button" disabled={saving} onClick={() => void save()}>
            {saving ? t("privacy.consent.saving") : t("privacy.settings.save")}
          </button>
          <button type="button" className="secondary-button" onClick={onOpenWhatsNew}>{t("privacy.settings.openWhatsNew")}</button>
          {message ? <span role="status" className="text-sm text-report-secondary">{message}</span> : null}
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold text-report-text">{t("privacy.settings.exactDataTitle")}</h2>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <div className="privacy-list-panel">
            <h3>{t("privacy.settings.maySend")}</h3>
            <ul>
              <li>{t("privacy.data.technicalVersions")}</li>
              <li>{t("privacy.data.interfaceCodes")}</li>
              <li>{t("privacy.data.eventCodes")}</li>
              <li>{t("privacy.data.buckets")}</li>
            </ul>
          </div>
          <div className="privacy-list-panel privacy-list-panel-never">
            <h3>{t("privacy.settings.neverSend")}</h3>
            <ul>
              <li>{t("privacy.never.content")}</li>
              <li>{t("privacy.never.names")}</li>
              <li>{t("privacy.never.identifiers")}</li>
              <li>{t("privacy.never.secrets")}</li>
              <li>{t("privacy.never.diagnostics")}</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold text-report-text">{t("privacy.notice.title")}</h2>
        <p className="mt-2 text-sm leading-6 text-report-secondary">{t("privacy.notice.technicalDraft")}</p>
        <p className="mt-2 text-sm leading-6 text-report-secondary">{t("privacy.notice.summary")}</p>
        <p className="mt-2 text-sm leading-6 text-report-secondary">{t("privacy.notice.version")}</p>
      </section>
    </div>
  );
}
