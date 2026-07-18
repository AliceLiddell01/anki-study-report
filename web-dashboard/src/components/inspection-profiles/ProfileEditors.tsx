import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type {
  InspectionCheck,
  InspectionProfile,
  InspectionProfileSummary,
  InspectionValidateResponse,
} from "../../types/inspectionProfiles";

const CHECK_KINDS: InspectionCheck["kind"][] = [
  "non_empty", "contains_audio", "contains_image", "min_text_length",
  "one_of_roles_non_empty", "all_roles_non_empty",
];
const PRIORITIES = ["high", "medium", "low"] as const;

export function SuggestionPanel({ item, onUse }: { item: InspectionProfileSummary; onUse: () => void }) {
  const { t } = useTranslation("pages");
  const suggestion = item.suggestion;
  return (
    <section className="inspection-panel" aria-labelledby="inspection-suggestion-title">
      <div className="inspection-panel-heading">
        <div>
          <h2 id="inspection-suggestion-title">{t("inspectionProfiles.suggestion.title")}</h2>
          <p>{t("inspectionProfiles.suggestion.description")}</p>
        </div>
        <span className="inspection-confidence">{t("inspectionProfiles.suggestion.confidence", { value: Math.round(suggestion.confidence * 100) })}</span>
      </div>
      <dl className="inspection-detail-grid">
        <div><dt>{t("inspectionProfiles.suggestion.kind")}</dt><dd>{safeKindLabel(t, suggestion.detectedKind)}</dd></div>
        <div><dt>{t("inspectionProfiles.suggestion.roles")}</dt><dd>{suggestion.fieldMappings.map((mapping) => mapping.role).join(", ") || "—"}</dd></div>
        <div><dt>{t("inspectionProfiles.suggestion.checks")}</dt><dd>{suggestion.checks.length}</dd></div>
      </dl>
      {suggestion.fieldMappings.length ? (
        <ul className="inspection-compact-list">
          {suggestion.fieldMappings.map((mapping) => (
            <li key={mapping.role}>
              <strong>{roleLabel(t, mapping.role)}</strong>
              <span>{mapping.fields.map((field) => field.name).join(", ")} · {Math.round(mapping.confidence * 100)}%</span>
            </li>
          ))}
        </ul>
      ) : null}
      {suggestion.warnings.length || suggestion.unresolvedFields.length ? (
        <details className="inspection-disclosure">
          <summary>{t("inspectionProfiles.suggestion.diagnostics")}</summary>
          <ul>
            {suggestion.warnings.map((warning) => <li key={warning}>{safeWarningLabel(t, warning)}</li>)}
            {suggestion.unresolvedFields.map((field) => <li key={`${field.ordinal}:${field.name}`}>{t("inspectionProfiles.suggestion.unresolved", { name: field.name })}</li>)}
          </ul>
        </details>
      ) : null}
      <button type="button" className="secondary-button mt-4" onClick={onUse}>{t("inspectionProfiles.actions.useSuggestion")}</button>
    </section>
  );
}

export function TemplateScopeEditor({ item, draft, onChange, errors }: EditorProps) {
  const { t } = useTranslation("pages");
  const all = draft.appliesTo.templateOrdinals.length === 0;
  const descriptionId = "inspection-template-scope-help";
  return (
    <fieldset className="inspection-panel" aria-describedby={descriptionId}>
      <legend>{t("inspectionProfiles.templates.title")}</legend>
      <p id={descriptionId} className="inspection-help">{t("inspectionProfiles.templates.description")}</p>
      <label className="inspection-choice-row">
        <input type="radio" name="template-scope" checked={all} onChange={() => onChange({ ...draft, appliesTo: { templateOrdinals: [] } })} />
        <span><strong>{t("inspectionProfiles.templates.all")}</strong><small>{t("inspectionProfiles.templates.allHint")}</small></span>
      </label>
      <label className="inspection-choice-row">
        <input type="radio" name="template-scope" checked={!all} onChange={() => onChange({ ...draft, appliesTo: { templateOrdinals: item.structure.templates.slice(0, 1).map((template) => template.ordinal) } })} />
        <span><strong>{t("inspectionProfiles.templates.selected")}</strong><small>{t("inspectionProfiles.templates.selectedHint")}</small></span>
      </label>
      {!all ? (
        <div className="inspection-checkbox-grid">
          {item.structure.templates.map((template) => {
            const checked = draft.appliesTo.templateOrdinals.includes(template.ordinal);
            return (
              <label key={template.ordinal}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...draft.appliesTo.templateOrdinals, template.ordinal].sort((a, b) => a - b)
                      : draft.appliesTo.templateOrdinals.filter((value) => value !== template.ordinal);
                    onChange({ ...draft, appliesTo: { templateOrdinals: next } });
                  }}
                />
                <span>{template.name}<small>{t("inspectionProfiles.templates.ordinal", { value: template.ordinal })}</small></span>
              </label>
            );
          })}
        </div>
      ) : null}
      {errors["profile.appliesTo.templateOrdinals"] ? <p className="inspection-inline-error">{errorLabel(t, errors["profile.appliesTo.templateOrdinals"])}</p> : null}
    </fieldset>
  );
}

export function FieldMappingsEditor({ item, draft, onChange, errors }: EditorProps) {
  const { t } = useTranslation("pages");
  const usedByOther = (mappingIndex: number, ordinal: number) => draft.fieldMappings.some((mapping, index) => index !== mappingIndex && mapping.fields.some((field) => field.ordinal === ordinal));
  const updateMapping = (index: number, next: InspectionProfile["fieldMappings"][number]) => {
    const mappings = draft.fieldMappings.map((mapping, current) => current === index ? next : mapping);
    onChange({ ...draft, fieldMappings: mappings });
  };
  return (
    <fieldset className="inspection-panel">
      <legend>{t("inspectionProfiles.mappings.title")}</legend>
      <p className="inspection-help">{t("inspectionProfiles.mappings.description")}</p>
      <div className="inspection-editor-list">
        {draft.fieldMappings.map((mapping, index) => {
          const roleId = `inspection-role-${index}`;
          const helpId = `${roleId}-help`;
          const error = errors[`profile.fieldMappings.${index}.role`] || errors[`profile.fieldMappings.${index}.fields`];
          return (
            <fieldset className="inspection-editor-card" key={`${index}:${mapping.role}`}>
              <legend>{t("inspectionProfiles.mappings.mapping", { value: index + 1 })}</legend>
              <div className="inspection-card-toolbar">
                <label htmlFor={roleId}>
                  {t("inspectionProfiles.mappings.role")}
                  <input id={roleId} className="form-control" value={mapping.role} aria-describedby={`${helpId}${error ? ` ${roleId}-error` : ""}`} onChange={(event) => updateMapping(index, { ...mapping, role: event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_").slice(0, 40) })} />
                </label>
                <button type="button" className="inspection-icon-button" aria-label={t("inspectionProfiles.mappings.remove", { role: mapping.role })} onClick={() => onChange({ ...draft, fieldMappings: draft.fieldMappings.filter((_, current) => current !== index), checks: draft.checks.filter((check) => !check.roles.includes(mapping.role)) })}><Trash2 size={17} aria-hidden="true" /></button>
              </div>
              <p id={helpId} className="inspection-help">{t("inspectionProfiles.mappings.roleHelp")}</p>
              <div className="inspection-checkbox-grid">
                {item.structure.fields.map((field) => {
                  const checked = mapping.fields.some((candidate) => candidate.ordinal === field.ordinal && candidate.name === field.name);
                  const disabled = !checked && usedByOther(index, field.ordinal);
                  return (
                    <label key={field.ordinal} className={disabled ? "is-disabled" : undefined}>
                      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => updateMapping(index, {
                        ...mapping,
                        fields: event.target.checked ? [...mapping.fields, { ...field }].sort((a, b) => a.ordinal - b.ordinal) : mapping.fields.filter((candidate) => candidate.ordinal !== field.ordinal),
                      })} />
                      <span>{field.name}<small>{t("inspectionProfiles.mappings.fieldOrdinal", { value: field.ordinal })}</small></span>
                    </label>
                  );
                })}
              </div>
              {error ? <p id={`${roleId}-error`} className="inspection-inline-error">{errorLabel(t, error)}</p> : null}
            </fieldset>
          );
        })}
      </div>
      <button type="button" className="secondary-button" onClick={() => onChange({ ...draft, fieldMappings: [...draft.fieldMappings, { role: nextRole(draft), fields: [] }] })}><Plus size={16} aria-hidden="true" />{t("inspectionProfiles.mappings.add")}</button>
      {errors["profile.fieldMappings"] ? <p className="inspection-inline-error">{errorLabel(t, errors["profile.fieldMappings"])}</p> : null}
    </fieldset>
  );
}

export function ChecksEditor({ draft, onChange, errors }: Omit<EditorProps, "item">) {
  const { t } = useTranslation("pages");
  const updateCheck = (index: number, next: InspectionCheck) => onChange({ ...draft, checks: draft.checks.map((check, current) => current === index ? next : check) });
  return (
    <fieldset className="inspection-panel">
      <legend>{t("inspectionProfiles.checks.title")}</legend>
      <p className="inspection-help">{t("inspectionProfiles.checks.description")}</p>
      <div className="inspection-editor-list">
        {draft.checks.map((check, index) => {
          const rolesError = errors[`profile.checks.${index}.roles`];
          const minError = errors[`profile.checks.${index}.minLength`];
          return (
            <fieldset className="inspection-editor-card" key={check.checkId}>
              <legend>{t("inspectionProfiles.checks.check", { value: index + 1 })}</legend>
              <div className="inspection-card-toolbar">
                <div className="inspection-form-grid">
                  <label htmlFor={`inspection-check-kind-${index}`}>{t("inspectionProfiles.checks.kind")}<select id={`inspection-check-kind-${index}`} className="form-control" value={check.kind} onChange={(event) => updateCheck(index, changeCheckKind(check, event.target.value as InspectionCheck["kind"]))}>{CHECK_KINDS.map((kind) => <option key={kind} value={kind}>{t(`inspectionProfiles.checkKinds.${kind}`)}</option>)}</select></label>
                  <label htmlFor={`inspection-check-priority-${index}`}>{t("inspectionProfiles.checks.priority")}<select id={`inspection-check-priority-${index}`} className="form-control" value={check.priority} onChange={(event) => updateCheck(index, { ...check, priority: event.target.value as InspectionCheck["priority"] })}>{PRIORITIES.map((priority) => <option key={priority} value={priority}>{t(`inspectionProfiles.priorities.${priority}`)}</option>)}</select></label>
                  {"mode" in check ? <label htmlFor={`inspection-check-mode-${index}`}>{t("inspectionProfiles.checks.mode")}<select id={`inspection-check-mode-${index}`} className="form-control" value={check.mode} onChange={(event) => updateCheck(index, { ...check, mode: event.target.value as "any" | "all" })}><option value="any">{t("inspectionProfiles.modes.any")}</option><option value="all">{t("inspectionProfiles.modes.all")}</option></select></label> : null}
                  {check.kind === "min_text_length" ? <label htmlFor={`inspection-check-length-${index}`}>{t("inspectionProfiles.checks.minLength")}<input id={`inspection-check-length-${index}`} type="number" min="1" max="10000" className="form-control" value={check.minLength} aria-describedby={minError ? `inspection-check-length-${index}-error` : undefined} onChange={(event) => updateCheck(index, { ...check, minLength: Number(event.target.value) })} /></label> : null}
                </div>
                <button type="button" className="inspection-icon-button" aria-label={t("inspectionProfiles.checks.remove", { value: index + 1 })} onClick={() => onChange({ ...draft, checks: draft.checks.filter((_, current) => current !== index) })}><Trash2 size={17} aria-hidden="true" /></button>
              </div>
              <p className="inspection-machine-id">{t("inspectionProfiles.checks.id")}: <code>{check.checkId}</code></p>
              <fieldset className="inspection-role-group" aria-describedby={rolesError ? `inspection-check-roles-${index}-error` : undefined}>
                <legend>{t("inspectionProfiles.checks.roles")}</legend>
                <div className="inspection-checkbox-grid">
                  {draft.fieldMappings.map((mapping) => <label key={mapping.role}><input type="checkbox" checked={check.roles.includes(mapping.role)} onChange={(event) => updateCheck(index, { ...check, roles: event.target.checked ? [...check.roles, mapping.role] : check.roles.filter((role) => role !== mapping.role) })} /><span>{roleLabel(t, mapping.role)}</span></label>)}
                </div>
              </fieldset>
              {rolesError ? <p id={`inspection-check-roles-${index}-error`} className="inspection-inline-error">{errorLabel(t, rolesError)}</p> : null}
              {minError ? <p id={`inspection-check-length-${index}-error`} className="inspection-inline-error">{errorLabel(t, minError)}</p> : null}
            </fieldset>
          );
        })}
      </div>
      <button type="button" className="secondary-button" disabled={!draft.fieldMappings.length} onClick={() => onChange({ ...draft, checks: [...draft.checks, newCheck(draft)] })}><Plus size={16} aria-hidden="true" />{t("inspectionProfiles.checks.add")}</button>
      <p className="inspection-help">{t("inspectionProfiles.checks.priorityHelp")}</p>
      {errors["profile.checks"] ? <p className="inspection-inline-error">{errorLabel(t, errors["profile.checks"])}</p> : null}
    </fieldset>
  );
}

export function InspectionPreview({ validation }: { validation: InspectionValidateResponse }) {
  const { t } = useTranslation("pages");
  const grouped = new Map<string, typeof validation.preview.items[number]["failures"]>();
  for (const item of validation.preview.items) for (const failure of item.failures) grouped.set(failure.checkId, [...(grouped.get(failure.checkId) ?? []), failure]);
  return (
    <section className="inspection-panel" aria-labelledby="inspection-preview-title">
      <div className="inspection-panel-heading"><div><h2 id="inspection-preview-title">{t("inspectionProfiles.preview.title")}</h2><p>{validation.preview.status === "available" ? t("inspectionProfiles.preview.description") : t("inspectionProfiles.preview.unavailable")}</p></div></div>
      <dl className="inspection-detail-grid">
        <div><dt>{t("inspectionProfiles.preview.evaluated")}</dt><dd>{validation.preview.evaluatedCount}</dd></div>
        <div><dt>{t("inspectionProfiles.preview.missing")}</dt><dd>{validation.preview.missingCardIds.length}</dd></div>
        <div><dt>{t("inspectionProfiles.preview.failures")}</dt><dd>{validation.preview.failureCount}</dd></div>
        <div><dt>{t("inspectionProfiles.preview.truncated")}</dt><dd>{validation.preview.truncated ? t("inspectionProfiles.yes") : t("inspectionProfiles.no")}</dd></div>
      </dl>
      {[...grouped.entries()].map(([checkId, failures]) => (
        <details className="inspection-disclosure" key={checkId} open>
          <summary>{checkId} · {failures.length}</summary>
          <ul className="inspection-preview-list">
            {failures.map((failure, index) => <li key={`${failure.checkId}:${failure.mappedFields.map((field) => field.ordinal).join("-")}:${index}`}><strong>{t(`inspectionProfiles.checkKinds.${failure.checkKind}`)}</strong><span>{t("inspectionProfiles.preview.roles", { value: failure.targetRoles.map((role) => roleLabel(t, role)).join(", ") })}</span><span>{t("inspectionProfiles.preview.fields", { value: failure.mappedFields.map((field) => field.name).join(", ") })}</span><span>{evidenceLabel(t, failure.evidence)}</span><small>{t("inspectionProfiles.preview.siblings", { value: failure.affectedSiblingCount })}</small></li>)}
          </ul>
        </details>
      ))}
    </section>
  );
}

interface EditorProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  onChange: (draft: InspectionProfile) => void;
  errors: Record<string, string>;
}

function newCheck(draft: InspectionProfile): InspectionCheck {
  let index = draft.checks.length + 1;
  while (draft.checks.some((check) => check.checkId === `non-empty-${index}`)) index += 1;
  return { checkId: `non-empty-${index}`, kind: "non_empty", roles: [draft.fieldMappings[0]?.role ?? "role"], mode: "any", priority: "medium" };
}

function changeCheckKind(check: InspectionCheck, kind: InspectionCheck["kind"]): InspectionCheck {
  const base = { checkId: check.checkId, kind, roles: [...check.roles], priority: check.priority };
  if (kind === "min_text_length") return { ...base, kind, mode: "any", minLength: 1 };
  if (kind === "one_of_roles_non_empty" || kind === "all_roles_non_empty") return { ...base, kind };
  return { ...base, kind, mode: "any" };
}

function nextRole(draft: InspectionProfile): string {
  let index = draft.fieldMappings.length + 1;
  while (draft.fieldMappings.some((mapping) => mapping.role === `role_${index}`)) index += 1;
  return `role_${index}`;
}

type Translate = (key: string, options?: Record<string, unknown>) => string;
function roleLabel(t: Translate, role: string): string { return t(`inspectionProfiles.roles.${role}`, { defaultValue: role.replace(/_/g, " ") }); }
function safeKindLabel(t: Translate, kind: string): string { return t(`inspectionProfiles.detectedKinds.${kind}`, { defaultValue: t("inspectionProfiles.suggestion.unknownKind") }); }
function safeWarningLabel(t: Translate, warning: string): string { return t(`inspectionProfiles.warnings.${warning}`, { defaultValue: t("inspectionProfiles.suggestion.unknownWarning") }); }
function errorLabel(t: Translate, error: string): string { return t(`inspectionProfiles.errors.${error}`, { defaultValue: error }); }
function evidenceLabel(t: Translate, evidence: InspectionValidateResponse["preview"]["items"][number]["failures"][number]["evidence"]): string {
  if (evidence.marker) return t("inspectionProfiles.preview.markerMissing", { marker: evidence.marker });
  if (evidence.expectedTextLength !== null) return t("inspectionProfiles.preview.length", { actual: evidence.actualTextLength ?? 0, expected: evidence.expectedTextLength });
  return t("inspectionProfiles.preview.condition", { value: evidence.expectedCondition });
}
