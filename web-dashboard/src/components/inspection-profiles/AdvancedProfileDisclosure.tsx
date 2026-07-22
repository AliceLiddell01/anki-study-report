import { useTranslation } from "react-i18next";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";
import { ChecksEditor, FieldMappingsEditor, TemplateScopeEditor } from "./ProfileEditors";

interface AdvancedProfileDisclosureProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  errors: Record<string, string>;
  onChange: (draft: InspectionProfile) => void;
}

export default function AdvancedProfileDisclosure({ item, draft, errors, onChange }: AdvancedProfileDisclosureProps) {
  const { i18n } = useTranslation("pages");
  const ru = i18n.resolvedLanguage?.startsWith("ru");
  return (
    <section id="inspection-advanced-panel" className="inspection-advanced-panel" role="tabpanel" aria-labelledby="inspection-mode-advanced" tabIndex={0}>
      <div className="inspection-advanced-intro">
        <strong>{ru ? "Точная структура профиля" : "Exact profile structure"}</strong>
        <small>{ru ? "Роли, ordinal, check kind, mode и стабильные ID" : "Roles, ordinals, check kinds, modes, and stable IDs"}</small>
      </div>
        <section className="inspection-panel">
          <label className="inspection-display-name" htmlFor="inspection-profile-display-name">
            {ru ? "Название профиля" : "Profile name"}
            <input
              id="inspection-profile-display-name"
              className="form-control"
              value={draft.displayName}
              aria-describedby={errors["profile.displayName"] ? "inspection-profile-display-name-error" : "inspection-profile-display-name-help"}
              onChange={(event) => onChange({ ...draft, displayName: event.target.value })}
            />
          </label>
          <p id="inspection-profile-display-name-help" className="inspection-help">{ru ? "Локальное название; тип записи Anki не переименовывается." : "A local name; the Anki note type is not renamed."}</p>
          {errors["profile.displayName"] ? <p id="inspection-profile-display-name-error" className="inspection-inline-error">{ru ? "Укажите название." : "Enter a name."}</p> : null}
        </section>
        <TemplateScopeEditor item={item} draft={draft} onChange={onChange} errors={errors} />
        <FieldMappingsEditor item={item} draft={draft} onChange={onChange} errors={errors} />
        <ChecksEditor draft={draft} onChange={onChange} errors={errors} />
    </section>
  );
}
