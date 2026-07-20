import { useTranslation } from "react-i18next";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";
import { ChecksEditor, FieldMappingsEditor, TemplateScopeEditor } from "./ProfileEditors";

interface AdvancedProfileDisclosureProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  errors: Record<string, string>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChange: (draft: InspectionProfile) => void;
}

export default function AdvancedProfileDisclosure({ item, draft, errors, open, onOpenChange, onChange }: AdvancedProfileDisclosureProps) {
  const { i18n } = useTranslation("pages");
  const ru = i18n.resolvedLanguage?.startsWith("ru");
  const errorCount = Object.keys(errors).filter((path) => path.includes("fieldMappings") || path.includes("checks") || path.includes("appliesTo") || path.includes("displayName")).length;
  return (
    <details
      className="inspection-major-disclosure"
      open={open}
      onToggle={(event) => onOpenChange(event.currentTarget.open)}
    >
      <summary id="inspection-advanced-summary">
        <span>
          <strong>{ru ? "Расширенные настройки" : "Advanced settings"}</strong>
          <small>{ru ? "Точные роли, ordinal, check kind, mode и стабильные ID" : "Exact roles, ordinals, check kinds, modes, and stable IDs"}</small>
        </span>
        {errorCount ? <span className="inspection-disclosure-errors" role="status">{ru ? `Ошибок: ${errorCount}` : `${errorCount} errors`}</span> : null}
      </summary>
      <div id="inspection-advanced-panel" className="inspection-advanced-panel">
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
      </div>
    </details>
  );
}
