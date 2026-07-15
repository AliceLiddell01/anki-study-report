import { useCallback, useEffect, useState } from "react";
import {
  fetchProductNotices,
  markCurrentReleaseSeen,
  savePrivacyChoices,
  type ProductNoticesResponse,
  type TelemetryPurpose,
} from "../lib/productNoticesApi";
import TelemetryConsentDialog from "./TelemetryConsentDialog";
import WhatsNewDialog from "./WhatsNewDialog";

type ActiveModal = "consent" | "whatsNew" | null;

export default function ProductNoticeCoordinator({ manualOpenSignal }: { manualOpenSignal: number }) {
  const [data, setData] = useState<ProductNoticesResponse | null>(null);
  const [active, setActive] = useState<ActiveModal>(null);
  const [busy, setBusy] = useState(false);

  const applyStartupOrder = useCallback((next: ProductNoticesResponse) => {
    setData(next);
    if (next.requiresConsent) setActive("consent");
    else if (next.showWhatsNew) setActive("whatsNew");
    else setActive(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void fetchProductNotices().then((response) => {
      if (!cancelled && response.ok) applyStartupOrder(response);
    });
    return () => { cancelled = true; };
  }, [applyStartupOrder]);

  useEffect(() => {
    if (manualOpenSignal > 0 && data) setActive("whatsNew");
  }, [data, manualOpenSignal]);

  const saveConsent = useCallback(async (purposes: Record<TelemetryPurpose, boolean>) => {
    setBusy(true);
    const saved = await savePrivacyChoices(purposes);
    if (saved.ok) {
      const refreshed = await fetchProductNotices();
      if (refreshed.ok) applyStartupOrder(refreshed);
    }
    setBusy(false);
  }, [applyStartupOrder]);

  const decline = useCallback(() => {
    void saveConsent({ reliabilityDiagnostics: false, featureUsage: false });
  }, [saveConsent]);

  const closeWhatsNew = useCallback(() => {
    setActive(null);
    void markCurrentReleaseSeen().then((response) => {
      if (response.ok) setData(response);
    });
  }, []);

  if (!data || !active) return null;
  if (active === "consent") {
    return <TelemetryConsentDialog busy={busy} onSave={(purposes) => void saveConsent(purposes)} onDecline={decline} />;
  }
  return <WhatsNewDialog data={data} onClose={closeWhatsNew} />;
}
