import { lazy, Suspense, useState } from "react";
import { useTranslation } from "react-i18next";
import type { TelemetryPurpose } from "../lib/productNoticesApi";
import AccessibleModal from "./AccessibleModal";

const PrivacyNoticeContent = lazy(() => import("./PrivacyNoticeContent"));

const EMPTY_CHOICES: Record<TelemetryPurpose, boolean> = {
  reliabilityDiagnostics: false,
  featureUsage: false,
};

export default function TelemetryConsentDialog({
  onSave,
  onDecline,
  busy,
}: {
  onSave: (purposes: Record<TelemetryPurpose, boolean>) => void;
  onDecline: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation("pages");
  const [choices, setChoices] = useState(EMPTY_CHOICES);
  const hasSelection = Object.values(choices).some(Boolean);

  return (
    <AccessibleModal
      title={t("privacy.consent.title")}
      closeLabel={t("privacy.consent.closeDeclines")}
      onRequestClose={onDecline}
      testId="telemetry-consent-dialog"
      footer={
        <div className="product-modal-actions product-modal-actions-balanced">
          <button type="button" className="secondary-button" disabled={busy} onClick={onDecline}>
            {t("privacy.consent.doNotSend")}
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={busy || !hasSelection}
            aria-describedby={!hasSelection ? "telemetry-consent-selection-required" : undefined}
            onClick={() => onSave(choices)}
          >
            {busy ? t("privacy.consent.saving") : t("privacy.consent.saveSelected")}
          </button>
        </div>
      }
    >
      <p className="product-modal-lead">{t("privacy.consent.intro")}</p>
      <p className="product-modal-note">{t("privacy.consent.noDetriment")}</p>
      <fieldset className="privacy-purpose-list" disabled={busy}>
        <legend>{t("privacy.consent.purposesLegend")}</legend>
        {(["reliabilityDiagnostics", "featureUsage"] as TelemetryPurpose[]).map((purpose) => (
          <label className="privacy-purpose-card" key={purpose}>
            <input
              type="checkbox"
              checked={choices[purpose]}
              onChange={(event) => setChoices((current) => ({ ...current, [purpose]: event.target.checked }))}
            />
            <span>
              <strong>{t(`privacy.purposes.${purpose}.title`)}</strong>
              <span>{t(`privacy.purposes.${purpose}.description`)}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {!hasSelection ? (
        <p id="telemetry-consent-selection-required" className="product-modal-selection-hint">
          {t("privacy.consent.selectionRequired")}
        </p>
      ) : null}
      <details className="privacy-disclosure">
        <summary>{t("privacy.consent.exactData")}</summary>
        <ul>
          <li>{t("privacy.data.technicalVersions")}</li>
          <li>{t("privacy.data.interfaceCodes")}</li>
          <li>{t("privacy.data.eventCodes")}</li>
          <li>{t("privacy.data.buckets")}</li>
        </ul>
      </details>
      <details className="privacy-disclosure">
        <summary>{t("privacy.consent.notice")}</summary>
        <Suspense fallback={null}>
          <PrivacyNoticeContent />
        </Suspense>
      </details>
      <p className="privacy-never">{t("privacy.consent.neverContent")}</p>
    </AccessibleModal>
  );
}
