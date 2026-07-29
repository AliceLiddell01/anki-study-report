import { useTranslation } from "react-i18next";
import { friendlyDetectedKind, profileLanguage } from "../../lib/inspectionProfileBasicView";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";

export interface InspectionProfileLifecycleGuidance {
  title: string;
  description: string;
}

interface InspectionProfileEditorIdentityProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  generatedDraft: boolean;
  dirty: boolean;
  guidance: InspectionProfileLifecycleGuidance;
  reviewReason: string | null;
}

export default function InspectionProfileEditorIdentity({
  item,
  draft,
  generatedDraft,
  dirty,
  guidance,
  reviewReason,
}: InspectionProfileEditorIdentityProps) {
  const { t, i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const detectedKind = friendlyDetectedKind(item.suggestion.detectedKind, language);
  const identity = resolveInspectionProfileDisplayIdentity({
    item,
    draft,
    generatedDraft,
    detectedKindLabel: detectedKind.label,
    detectedKindMeaningful: detectedKind.known && !["basic", "generic", "unknown"].includes(item.suggestion.detectedKind),
    noIndependentName: t("inspectionProfiles.editor.proposedProfileNoName"),
  });
  const identityRepeatsDetectedKind = normalizeIdentity(identity.value, language) === normalizeIdentity(detectedKind.label, language);
  const structureSummary = identityRepeatsDetectedKind
    ? t("inspectionProfiles.editor.structureCounts", {
      fields: item.structure.fields.length,
      templates: item.structure.templates.length,
    })
    : t("inspectionProfiles.editor.structureSummary", {
      kind: detectedKind.label,
      fields: item.structure.fields.length,
      templates: item.structure.templates.length,
    });

  return (
    <section className="inspection-editor-identity">
      <div className="inspection-editor-identity-inner">
        <div className="inspection-identity-title">
          <p className="inspection-identity-kicker">{t("inspectionProfiles.editor.noteType")}</p>
          <h2>{item.structure.name}</h2>
          <p className="inspection-profile-identity" data-identity-source={identity.source}>
            {generatedDraft ? t("inspectionProfiles.editor.proposedProfile") : t("inspectionProfiles.editor.profileLabel")}:{" "}
            <strong>{identity.value}</strong>
          </p>
          <p className="inspection-identity-structure">{structureSummary}</p>
          <div className="inspection-header-badges">
            <span className={`inspection-state-badge is-${item.effectiveState}`}>{t(`inspectionProfiles.states.${item.effectiveState}`)}</span>
            {generatedDraft ? <span className="inspection-custom-badge">{t("inspectionProfiles.editor.browserDraft")}</span> : null}
            {dirty ? <span className="inspection-dirty-badge">{t("inspectionProfiles.editor.unsaved")}</span> : null}
          </div>
        </div>
        <div
          className={`inspection-lifecycle is-${item.effectiveState}`}
          role={item.effectiveState === "needs_review" ? "alert" : "status"}
        >
          <strong>{guidance.title}</strong>
          <span>{guidance.description}</span>
          {reviewReason ? <small>{reviewReason}</small> : null}
        </div>
      </div>
    </section>
  );
}

export function resolveInspectionProfileDisplayIdentity({
  item,
  draft,
  generatedDraft,
  detectedKindLabel,
  detectedKindMeaningful,
  noIndependentName,
}: {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  generatedDraft: boolean;
  detectedKindLabel: string;
  detectedKindMeaningful: boolean;
  noIndependentName: string;
}): { value: string; source: "stored" | "suggestion" | "draft" | "explicit-fallback" | "note-type-fallback" } {
  const storedName = item.storedProfile?.displayName.trim();
  if (storedName) return { value: storedName, source: "stored" };

  if (generatedDraft && detectedKindMeaningful && detectedKindLabel.trim()) {
    return { value: detectedKindLabel.trim(), source: "suggestion" };
  }

  const draftName = draft.displayName.trim();
  if (draftName && normalizeIdentity(draftName, "en") !== normalizeIdentity(item.structure.name, "en")) {
    return { value: draftName, source: "draft" };
  }

  if (noIndependentName.trim()) return { value: noIndependentName.trim(), source: "explicit-fallback" };
  return { value: item.structure.name, source: "note-type-fallback" };
}

function normalizeIdentity(value: string, language: string): string {
  return value.normalize("NFKC").trim().toLocaleLowerCase(language);
}
