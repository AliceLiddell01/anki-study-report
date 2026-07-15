import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChangelogRelease, ProductNoticesResponse } from "../lib/productNoticesApi";
import AccessibleModal from "./AccessibleModal";

const SECTION_KEYS: Record<ChangelogRelease["sections"][number]["type"], string> = {
  added: "added",
  changed: "changed",
  fixed: "fixed",
  safety: "safety",
  removed: "removed",
};

export default function WhatsNewDialog({
  data,
  onClose,
}: {
  data: ProductNoticesResponse;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation("pages");
  const locale = i18n.resolvedLanguage === "en" ? "en" : "ru";
  const firstInstall = data.notice.lastSeenReleaseVersion === null;
  const initiallyExpanded = new Set(firstInstall ? [data.currentVersion] : data.unseenReleaseVersions);
  const [expanded, setExpanded] = useState(initiallyExpanded);

  useEffect(() => {
    setExpanded((current) => current.size ? current : initiallyExpanded);
    // Expansion is intentionally not reset when language or theme changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.currentVersion]);

  return (
    <AccessibleModal
      title={firstInstall ? t("whatsNew.firstInstallTitle") : t("whatsNew.updateTitle")}
      closeLabel={t("whatsNew.close")}
      onRequestClose={onClose}
      testId="whats-new-dialog"
      footer={
        <button type="button" className="primary-button" onClick={onClose}>{t("whatsNew.gotIt")}</button>
      }
    >
      <p className="product-modal-lead">
        {firstInstall ? t("whatsNew.firstInstallIntro") : t("whatsNew.updateIntro", { version: data.notice.lastSeenReleaseVersion })}
      </p>
      <div className="release-history">
        {data.changelog.releases.map((release) => {
          const isExpanded = expanded.has(release.version);
          return (
            <section className="release-card" key={release.version}>
              <button
                type="button"
                className="release-card-trigger"
                aria-expanded={isExpanded}
                onClick={() => setExpanded((current) => {
                  const next = new Set(current);
                  if (next.has(release.version)) next.delete(release.version);
                  else next.add(release.version);
                  return next;
                })}
              >
                <span>{t("whatsNew.version", { version: release.version })}</span>
                <time dateTime={release.date}>{release.date}</time>
              </button>
              {isExpanded ? (
                <div className="release-card-content">
                  {release.sections.map((section) => (
                    <div key={section.type}>
                      <h3>{t(`whatsNew.sections.${SECTION_KEYS[section.type]}`)}</h3>
                      <ul>
                        {section.items.map((item) => <li key={item.id}>{item.text[locale]}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
    </AccessibleModal>
  );
}
