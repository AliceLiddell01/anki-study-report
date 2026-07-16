import { ShieldCheck } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatDateTime, isValidDateTime } from "../lib/localizedDateTime";
import {
  fetchPrivacy,
  savePrivacyChoices,
  type PrivacyResponse,
  type TelemetryPurpose,
} from "../lib/productNoticesApi";
import { checkConnectionAndSendNow, deleteTelemetryData } from "../lib/telemetryApi";
import { privacyTelemetryStatusCopy } from "./privacyTelemetryStatusCopy";

const PrivacyNoticeContent = lazy(() => import("../components/PrivacyNoticeContent"));

const EMPTY_CHOICES: Record<TelemetryPurpose, boolean> = {
  reliabilityDiagnostics: false,
  featureUsage: false,
};

const PUBLIC_TELEMETRY_ERRORS = new Set([
  "network_error", "http_400", "http_401", "http_403", "http_409", "http_429", "http_5xx",
  "unsupported_contract", "invalid_response", "service_disabled", "authentication_rejected",
]);

function LocalizedDateTime({ value, fallback }: { value: string | null | undefined; fallback: string }) {
  const formatted = formatDateTime(value, fallback);
  if (!isValidDateTime(value)) return <span title={value || undefined}>{formatted}</span>;
  return <time dateTime={value} title={value}>{formatted}</time>;
}

export default function PrivacySettingsPage({ onOpenWhatsNew }: { onOpenWhatsNew: () => void }) {
  const { t, i18n } = useTranslation("pages");
  const telemetryCopy = privacyTelemetryStatusCopy[i18n.resolvedLanguage === "en" ? "en" : "ru"];
  const [response, setResponse] = useState<PrivacyResponse | null>(null);
  const [choices, setChoices] = useState(EMPTY_CHOICES);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [checking, setChecking] = useState(false);
  const refreshTimer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchPrivacy().then((loaded) => {
      if (cancelled) return;
      setResponse(loaded);
      if (loaded.privacy) setChoices(loaded.privacy.telemetry.purposes);
    });
    return () => {
      cancelled = true;
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
    };
  }, []);

  const refreshAfterManualSend = async (attempt = 0) => {
    const refreshed = await fetchPrivacy();
    setResponse(refreshed);
    if (refreshed.privacy) setChoices(refreshed.privacy.telemetry.purposes);
    if (refreshed.telemetryClient?.senderState === "busy" && attempt < 15) {
      refreshTimer.current = window.setTimeout(() => void refreshAfterManualSend(attempt + 1), 1000);
      return;
    }
    setChecking(false);
  };

  const checkAndSend = async () => {
    setChecking(true);
    setMessage("");
    const result = await checkConnectionAndSendNow();
    const resultCode = result.code?.replace(/^telemetry\./, "") ?? "failed";
    setMessage(result.started
      ? telemetryCopy.checkStarted
      : telemetryCopy.checkResult[resultCode as keyof typeof telemetryCopy.checkResult] ?? telemetryCopy.checkResult.failed);
    await refreshAfterManualSend();
  };

  const save = async () => {
    setSaving(true);
    setMessage("");
    const saved = await savePrivacyChoices(choices);
    setResponse(saved);
    if (saved.privacy) setChoices(saved.privacy.telemetry.purposes);
    setMessage(saved.ok ? t("privacy.settings.saved") : t("privacy.settings.saveFailed"));
    setSaving(false);
  };

  const disableAll = async () => {
    setChoices(EMPTY_CHOICES);
    setSaving(true);
    setMessage("");
    const saved = await savePrivacyChoices(EMPTY_CHOICES);
    setResponse(saved);
    setMessage(saved.ok ? t("privacy.settings.disabled") : t("privacy.settings.saveFailed"));
    setSaving(false);
  };

  const deleteData = async () => {
    setDeleting(true);
    setMessage("");
    const result = await deleteTelemetryData();
    const refreshed = await fetchPrivacy();
    setResponse(refreshed);
    if (refreshed.privacy) setChoices(refreshed.privacy.telemetry.purposes);
    setMessage(
      result.confirmed
        ? t("privacy.settings.deletionConfirmed")
        : result.deletionPending
          ? t("privacy.settings.deletionPending")
          : t("privacy.settings.deletionFailed"),
    );
    setDeleting(false);
  };

  if (!response) {
    return <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">{t("privacy.settings.loading")}</section>;
  }
  if (!response.ok || !response.privacy) {
    return <section className="rounded-xl border border-report-danger/45 bg-ink-850 p-5 shadow-panel">{t("privacy.settings.loadFailed")}</section>;
  }

  const telemetry = response.privacy.telemetry;
  const client = response.telemetryClient;
  const statusKey = telemetry.requiresConsent ? "decisionRequired" : telemetry.status;
  const deletionPending = Boolean(client?.deletionPending || telemetry.deletionPending);
  const hasPersistedPurpose = Object.values(telemetry.purposes).some(Boolean);
  const hasPendingTelemetry = (client?.pendingEventCount ?? 0) > 0 || deletionPending;
  const canDisableAll = hasPersistedPurpose || hasPendingTelemetry;
  const canDeleteRemote = Boolean(
    client?.enrollmentState === "enrolled"
      || (client?.pendingEventCount ?? 0) > 0
      || deletionPending
      || client?.lastSuccessfulDeliveryAt,
  );
  const hasEffectivePurpose = Object.values(telemetry.effectivePurposes).some(Boolean);
  const senderBusy = client?.senderState === "busy";
  const canCheckSend = hasEffectivePurpose && !deletionPending && !senderBusy && !checking;
  const enrollmentError = client?.lastEnrollmentErrorCode;
  const deliveryError = client?.lastDeliveryErrorCode;
  const localizedError = (code: string | null | undefined) => telemetryCopy.error[
    (code && PUBLIC_TELEMETRY_ERRORS.has(code) ? code : "unknown") as keyof typeof telemetryCopy.error
  ];
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
          <div><dt>{t("privacy.settings.decidedAt")}</dt><dd><LocalizedDateTime value={telemetry.decidedAt} fallback={t("privacy.settings.notDecided")} /></dd></div>
        </dl>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold text-report-text">{t("privacy.settings.connectionTitle")}</h2>
        <p className="mt-2 text-sm text-report-secondary">{t("privacy.settings.connectionDescription")}</p>
        <dl className="privacy-status-grid mt-5">
          <div><dt>{t("privacy.settings.endpointState")}</dt><dd>{t(`privacy.client.endpoint.${client?.endpointState ?? "not_configured"}`)}</dd></div>
          <div><dt>{telemetryCopy.senderState}</dt><dd>{telemetryCopy.sender[client?.senderState ?? "idle"]}</dd></div>
          <div><dt>{t("privacy.settings.enrollmentState")}</dt><dd>{telemetryCopy.enrollment[client?.enrollmentState ?? "not_attempted"]}</dd></div>
          <div><dt>{t("privacy.settings.pendingEvents")}</dt><dd>{client?.pendingEventCount ?? 0}</dd></div>
          <div><dt>{telemetryCopy.lastEnrollmentAttempt}</dt><dd><LocalizedDateTime value={client?.lastEnrollmentAttemptAt} fallback={telemetryCopy.notAttempted} /></dd></div>
          <div><dt>{telemetryCopy.lastEnrollmentResult}</dt><dd>{enrollmentError ? localizedError(enrollmentError) : client?.lastEnrollmentSuccessAt ? telemetryCopy.enrollmentSucceeded : telemetryCopy.notAttempted}</dd></div>
          <div><dt>{telemetryCopy.nextEnrollmentRetry}</dt><dd><LocalizedDateTime value={client?.enrollmentNextAttemptAt} fallback={telemetryCopy.notScheduled} /></dd></div>
          <div><dt>{telemetryCopy.lastDeliveryAttempt}</dt><dd><LocalizedDateTime value={client?.lastDeliveryAttemptAt} fallback={telemetryCopy.notAttempted} /></dd></div>
          <div><dt>{t("privacy.settings.lastDelivery")}</dt><dd><LocalizedDateTime value={client?.lastSuccessfulDeliveryAt} fallback={t("privacy.settings.neverDelivered")} /></dd></div>
          <div><dt>{telemetryCopy.lastError}</dt><dd>{enrollmentError ? localizedError(enrollmentError) : deliveryError ? localizedError(deliveryError) : t("privacy.settings.noError")}</dd></div>
          <div><dt>{t("privacy.settings.deletionState")}</dt><dd>{deletionPending ? t("privacy.client.deletion.pending") : t("privacy.client.deletion.none")}</dd></div>
        </dl>
        <p className="privacy-action-explanation mt-4">{telemetryCopy.queueDeliveryDistinction}</p>
        <p className="privacy-action-explanation">{telemetryCopy.refreshEventNote}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="secondary-button"
            disabled={!canCheckSend}
            aria-describedby={!canCheckSend ? "privacy-check-unavailable" : undefined}
            onClick={() => void checkAndSend()}
          >
            {checking ? telemetryCopy.checking : telemetryCopy.checkAndSend}
          </button>
          {!canCheckSend ? <span id="privacy-check-unavailable" className="privacy-action-explanation">{telemetryCopy.checkUnavailable}</span> : null}
        </div>
        {deletionPending ? (
          <p role="status" className="privacy-deletion-warning mt-4" title={client?.deletionNextAttemptAt || undefined}>
            {t("privacy.settings.deletionPendingDetail", {
              retryAt: formatDateTime(client?.deletionNextAttemptAt, t("privacy.settings.retryUnknown")),
            })}
          </p>
        ) : null}
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

      <section className="rounded-xl border border-report-danger/35 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold text-report-text">{t("privacy.settings.withdrawTitle")}</h2>
        <p className="mt-2 text-sm leading-6 text-report-secondary">{t("privacy.settings.withdrawDescription")}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            className="secondary-button"
            disabled={saving || deleting || !canDisableAll}
            aria-describedby={!canDisableAll ? "privacy-disable-unavailable" : undefined}
            title={!canDisableAll ? t("privacy.settings.disableUnavailable") : undefined}
            onClick={() => void disableAll()}
          >
            {t("privacy.settings.disableAll")}
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={saving || deleting || !canDeleteRemote}
            aria-describedby={!canDeleteRemote ? "privacy-delete-unavailable" : undefined}
            title={!canDeleteRemote ? t("privacy.settings.deleteUnavailable") : undefined}
            onClick={() => void deleteData()}
          >
            {deleting ? t("privacy.settings.deleting") : t("privacy.settings.deleteRemote")}
          </button>
        </div>
        {!canDisableAll ? <p id="privacy-disable-unavailable" className="privacy-action-explanation">{t("privacy.settings.disableUnavailable")}</p> : null}
        {!canDeleteRemote ? <p id="privacy-delete-unavailable" className="privacy-action-explanation">{t("privacy.settings.deleteUnavailable")}</p> : null}
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
        <div className="mt-3">
<Suspense fallback={<p className="text-sm leading-6 text-report-secondary">{t("privacy.notice.summary")}</p>}>
  <PrivacyNoticeContent />
</Suspense>
        </div>
      </section>
    </div>
  );
}
