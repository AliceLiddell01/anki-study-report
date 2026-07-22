import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createCheck,
  friendlyRole,
  profileLanguage,
  projectBasicProfile,
} from "../../lib/inspectionProfileBasicView";
import type {
  InspectionCheck,
  InspectionProfile,
  InspectionProfileCheckKind,
  InspectionProfileSummary,
} from "../../types/inspectionProfiles";

const CHECK_KINDS: InspectionProfileCheckKind[] = [
  "non_empty",
  "contains_audio",
  "contains_image",
  "min_text_length",
  "one_of_roles_non_empty",
  "all_roles_non_empty",
];

export interface BasicProfileEditorProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  onChange: (draft: InspectionProfile) => void;
  errors: Record<string, string>;
}

export default function BasicProfileEditor({ item, draft, onChange, errors }: BasicProfileEditorProps) {
  const { i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const copy = guidedCopy(language);
  const view = useMemo(() => projectBasicProfile(item, draft, language), [draft, item, language]);
  const [newKind, setNewKind] = useState<InspectionProfileCheckKind>("non_empty");

  const updateMapping = (index: number, value: string) => {
    const field = value === "" ? null : item.structure.fields.find((candidate) => candidate.ordinal === Number(value)) ?? null;
    onChange({
      ...draft,
      fieldMappings: draft.fieldMappings.map((mapping, current) => current === index ? { ...mapping, fields: field ? [{ ...field }] : [] } : mapping),
    });
  };

  const usedByOther = (index: number, ordinal: number) => draft.fieldMappings.some(
    (mapping, current) => current !== index && mapping.fields.some((field) => field.ordinal === ordinal),
  );

  const updateCheck = (index: number, next: InspectionCheck) => {
    onChange({ ...draft, checks: draft.checks.map((check, current) => current === index ? next : check) });
  };

  const missingTemplates = draft.appliesTo.templateOrdinals.filter(
    (ordinal) => !item.structure.templates.some((template) => template.ordinal === ordinal),
  );

  return (
    <div className="inspection-basic" data-testid="inspection-basic-editor">
      <section className="inspection-guided-summary" aria-labelledby="inspection-guided-summary-title">
        <div>
          <p className="inspection-section-kicker"><span className="inspection-milestone" aria-hidden="true">2</span>{copy.suggestedSetup}</p>
          <h3 id="inspection-guided-summary-title">{view.detectedKind.label}</h3>
          <p>{view.detectedKind.description}</p>
        </div>
        <dl>
          <div><dt>{copy.confidence}</dt><dd>{copy.confidenceLabels[view.confidence]}</dd></div>
          <div><dt>{copy.recognizedFields}</dt><dd>{draft.fieldMappings.length}</dd></div>
          <div><dt>{copy.requirements}</dt><dd>{draft.checks.length}</dd></div>
        </dl>
        {(view.unresolvedFields.length > 0 || view.warnings.length > 0) ? (
          <div className="inspection-basic-warning" role="alert">
            <AlertTriangle size={18} aria-hidden="true" />
            <div>
              <strong>{copy.reviewRequired}</strong>
              {view.unresolvedFields.length ? <p>{copy.unresolved}: {view.unresolvedFields.join(", ")}</p> : null}
              {view.warnings.length ? <p>{copy.warningFallback}</p> : null}
            </div>
          </div>
        ) : null}
      </section>

      <fieldset className="inspection-basic-section inspection-basic-fields">
        <legend><span className="inspection-milestone" aria-hidden="true">3</span>{copy.fieldsTitle}</legend>
        <p className="inspection-help">{copy.fieldsHelp}</p>
        <div className="inspection-basic-list">
          {view.roles.map((role, index) => {
            const selectId = `inspection-basic-role-${index}`;
            const error = errors[`profile.fieldMappings.${index}.fields`];
            return (
              <div className="inspection-basic-row" key={`${role.role}:${index}`}>
                <div className="inspection-basic-row-copy">
                  <div className="inspection-basic-title-line">
                    <strong>{role.label}</strong>
                    {!role.known ? <span className="inspection-custom-badge">{copy.custom}</span> : null}
                  </div>
                  <p>{role.description}</p>
                </div>
                <label htmlFor={selectId}>
                  <span>{copy.ankiField}</span>
                  <select
                    id={selectId}
                    className="form-control"
                    value={role.mapping.fields[0]?.ordinal ?? ""}
                    aria-describedby={error || role.blockingIssue ? `${selectId}-error` : `${selectId}-help`}
                    aria-invalid={Boolean(error || role.blockingIssue) || undefined}
                    onChange={(event) => updateMapping(index, event.target.value)}
                  >
                    <option value="">{copy.chooseField}</option>
                    {item.structure.fields.map((field) => {
                      const selected = role.mapping.fields.some((candidate) => candidate.ordinal === field.ordinal && candidate.name === field.name);
                      const disabled = !selected && usedByOther(index, field.ordinal);
                      return <option key={field.ordinal} value={field.ordinal} disabled={disabled}>{field.name}{disabled ? ` — ${copy.usedElsewhere}` : ""}</option>;
                    })}
                  </select>
                  <small id={`${selectId}-help`}>{role.mapping.fields.length > 1 ? copy.multipleAdvanced : copy.exactFieldHelp}</small>
                </label>
                {error || role.blockingIssue ? <p id={`${selectId}-error`} className="inspection-inline-error">{role.blockingIssue ?? copy.invalidField}</p> : null}
              </div>
            );
          })}
        </div>
        {!draft.fieldMappings.length ? <p className="inspection-basic-empty">{copy.noRoles}</p> : null}
        {errors["profile.fieldMappings"] ? <p className="inspection-inline-error">{copy.duplicateField}</p> : null}
      </fieldset>

      <fieldset className="inspection-basic-section inspection-basic-requirements">
        <legend><span className="inspection-milestone" aria-hidden="true">4</span>{copy.requirementsTitle}</legend>
        <p className="inspection-help">{copy.requirementsHelp}</p>
        <div className="inspection-basic-list">
          {view.requirements.map((requirement, index) => {
            const check = draft.checks[index];
            const rolesError = errors[`profile.checks.${index}.roles`];
            const lengthError = errors[`profile.checks.${index}.minLength`];
            const multiRole = check.kind === "one_of_roles_non_empty" || check.kind === "all_roles_non_empty";
            return (
              <fieldset className="inspection-requirement-row" key={check.checkId}>
                <legend className="sr-only">{requirement.title}</legend>
                <div className="inspection-requirement-heading">
                  <div>
                    <strong>{requirement.title}</strong>
                    <p>{requirement.description}</p>
                    {requirement.fields.length ? <small>{copy.fieldsUsed}: {requirement.fields.join(", ")}</small> : null}
                  </div>
                  <button
                    type="button"
                    className="inspection-icon-button"
                    aria-label={`${copy.removeRequirement}: ${requirement.title}`}
                    onClick={() => onChange({ ...draft, checks: draft.checks.filter((_, current) => current !== index) })}
                  >
                    <Trash2 size={17} aria-hidden="true" />
                  </button>
                </div>
                <div className="inspection-requirement-controls">
                  <label htmlFor={`inspection-basic-priority-${index}`}>
                    <span>{copy.priority}</span>
                    <select
                      id={`inspection-basic-priority-${index}`}
                      className="form-control"
                      value={check.priority}
                      onChange={(event) => updateCheck(index, { ...check, priority: event.target.value as InspectionCheck["priority"] })}
                    >
                      <option value="high">{copy.high}</option>
                      <option value="medium">{copy.medium}</option>
                      <option value="low">{copy.low}</option>
                    </select>
                  </label>
                  {!multiRole ? (
                    <label htmlFor={`inspection-basic-check-role-${index}`}>
                      <span>{copy.fieldPurpose}</span>
                      <select
                        id={`inspection-basic-check-role-${index}`}
                        className="form-control"
                        value={check.roles[0] ?? ""}
                        aria-describedby={rolesError ? `inspection-basic-check-role-${index}-error` : undefined}
                        onChange={(event) => updateCheck(index, { ...check, roles: event.target.value ? [event.target.value] : [] })}
                      >
                        <option value="">{copy.choosePurpose}</option>
                        {draft.fieldMappings.map((mapping) => <option key={mapping.role} value={mapping.role}>{friendlyRole(mapping.role, language).label}</option>)}
                      </select>
                    </label>
                  ) : (
                    <fieldset className="inspection-basic-role-choices" aria-describedby={rolesError ? `inspection-basic-check-role-${index}-error` : undefined}>
                      <legend>{copy.fieldPurposes}</legend>
                      {draft.fieldMappings.map((mapping) => (
                        <label key={mapping.role}>
                          <input
                            type="checkbox"
                            checked={check.roles.includes(mapping.role)}
                            onChange={(event) => updateCheck(index, {
                              ...check,
                              roles: event.target.checked ? [...check.roles, mapping.role] : check.roles.filter((role) => role !== mapping.role),
                            })}
                          />
                          <span>{friendlyRole(mapping.role, language).label}</span>
                        </label>
                      ))}
                    </fieldset>
                  )}
                  {check.kind === "min_text_length" ? (
                    <label htmlFor={`inspection-basic-min-length-${index}`}>
                      <span>{copy.minLength}</span>
                      <input
                        id={`inspection-basic-min-length-${index}`}
                        className="form-control"
                        type="number"
                        min="1"
                        max="10000"
                        value={check.minLength}
                        aria-describedby={lengthError ? `inspection-basic-min-length-${index}-error` : undefined}
                        onChange={(event) => updateCheck(index, { ...check, minLength: Number(event.target.value) })}
                      />
                    </label>
                  ) : null}
                </div>
                {rolesError || requirement.blockingIssue ? <p id={`inspection-basic-check-role-${index}-error`} className="inspection-inline-error">{requirement.blockingIssue ?? copy.choosePurpose}</p> : null}
                {lengthError ? <p id={`inspection-basic-min-length-${index}-error`} className="inspection-inline-error">{copy.invalidLength}</p> : null}
              </fieldset>
            );
          })}
        </div>
        {!draft.checks.length ? <p className="inspection-basic-empty">{copy.noRequirements}</p> : null}
        <div className="inspection-add-requirement">
          <label htmlFor="inspection-basic-new-requirement">
            <span>{copy.addRequirement}</span>
            <select id="inspection-basic-new-requirement" className="form-control" value={newKind} onChange={(event) => setNewKind(event.target.value as InspectionProfileCheckKind)}>
              {CHECK_KINDS.map((kind) => <option key={kind} value={kind}>{requirementKindLabel(kind, language)}</option>)}
            </select>
          </label>
          <button
            type="button"
            className="secondary-button"
            disabled={!draft.fieldMappings.length}
            onClick={() => onChange({ ...draft, checks: [...draft.checks, createCheck(draft, newKind)] })}
          >
            <Plus size={16} aria-hidden="true" />{copy.add}
          </button>
        </div>
      </fieldset>

      <fieldset className="inspection-basic-section inspection-basic-scope">
        <legend><span className="inspection-milestone" aria-hidden="true">5</span>{copy.scopeTitle}</legend>
        {item.structure.templates.length === 1 ? (
          <div className="inspection-one-template">
            <strong>{copy.allCards}</strong>
            <p>{copy.singleTemplate}: {item.structure.templates[0]?.name}</p>
          </div>
        ) : (
          <>
            <label className="inspection-choice-row">
              <input type="radio" name="inspection-basic-template-scope" checked={draft.appliesTo.templateOrdinals.length === 0} onChange={() => onChange({ ...draft, appliesTo: { templateOrdinals: [] } })} />
              <span><strong>{copy.allTemplates}</strong><small>{copy.allTemplatesHelp}</small></span>
            </label>
            <label className="inspection-choice-row">
              <input type="radio" name="inspection-basic-template-scope" checked={draft.appliesTo.templateOrdinals.length > 0} onChange={() => onChange({ ...draft, appliesTo: { templateOrdinals: item.structure.templates.slice(0, 1).map((template) => template.ordinal) } })} />
              <span><strong>{copy.selectedTemplates}</strong><small>{copy.selectedTemplatesHelp}</small></span>
            </label>
            {draft.appliesTo.templateOrdinals.length > 0 ? (
              <div className="inspection-basic-template-list">
                {item.structure.templates.map((template) => (
                  <label key={template.ordinal}>
                    <input
                      type="checkbox"
                      checked={draft.appliesTo.templateOrdinals.includes(template.ordinal)}
                      onChange={(event) => {
                        const ordinals = event.target.checked
                          ? [...draft.appliesTo.templateOrdinals, template.ordinal].sort((a, b) => a - b)
                          : draft.appliesTo.templateOrdinals.filter((ordinal) => ordinal !== template.ordinal);
                        onChange({ ...draft, appliesTo: { templateOrdinals: ordinals } });
                      }}
                    />
                    <span>{template.name}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </>
        )}
        {missingTemplates.length || errors["profile.appliesTo.templateOrdinals"] ? <p className="inspection-inline-error">{copy.missingTemplate}</p> : null}
      </fieldset>
    </div>
  );
}

function requirementKindLabel(kind: InspectionProfileCheckKind, language: "ru" | "en"): string {
  const labels: Record<InspectionProfileCheckKind, [string, string]> = {
    non_empty: ["Обязательное поле", "Required field"],
    contains_audio: ["Требовать аудио", "Require audio"],
    contains_image: ["Требовать изображение", "Require image"],
    min_text_length: ["Минимальная длина", "Minimum text length"],
    one_of_roles_non_empty: ["Хотя бы одно поле", "At least one field"],
    all_roles_non_empty: ["Все выбранные поля", "Every selected field"],
  };
  return labels[kind][language === "ru" ? 0 : 1];
}

function guidedCopy(language: "ru" | "en") {
  return language === "ru" ? {
    suggestedSetup: "Предложенная настройка", confidence: "Надёжность", recognizedFields: "Распознано полей", requirements: "Требований",
    confidenceLabels: { high: "Высокая", review: "Рекомендуется проверка", insufficient: "Недостаточно данных" },
    reviewRequired: "Нужна проверка", unresolved: "Не определены поля", warningFallback: "Подсказка содержит предупреждение — проверьте сопоставления перед включением.",
    fieldsTitle: "Какие поля используются", fieldsHelp: "Свяжите понятные роли с точными полями выбранного типа записи Anki.", custom: "Пользовательская роль",
    ankiField: "Поле Anki", chooseField: "Выберите поле", usedElsewhere: "уже используется", multipleAdvanced: "Несколько полей сохранены; точную комбинацию можно изменить в расширенных настройках.", exactFieldHelp: "Используется точное имя поля текущего типа записи.", invalidField: "Выберите доступное поле.", noRoles: "Подсказка не определила роли. Используйте расширенные настройки или начните с пустого профиля.", duplicateField: "Одно поле нельзя незаметно использовать для конфликтующих ролей.",
    requirementsTitle: "Что проверять", requirementsHelp: "Требования компилируются только в поддерживаемые декларативные проверки Inspection Profile v1.", fieldsUsed: "Поля", removeRequirement: "Удалить требование",
    priority: "Важность", high: "Высокая", medium: "Средняя", low: "Низкая", fieldPurpose: "Проверяемая роль", fieldPurposes: "Проверяемые роли", choosePurpose: "Выберите роль", minLength: "Минимум символов", invalidLength: "Введите целое число от 1 до 10000.", noRequirements: "Требований пока нет. Профиль можно сохранить как черновик, но перед включением добавьте необходимые проверки.", addRequirement: "Добавить безопасное требование", add: "Добавить",
    scopeTitle: "Какие карточки проверять", allCards: "Все карточки этого типа записи", singleTemplate: "Шаблон", allTemplates: "Все шаблоны карточек", allTemplatesHelp: "Профиль применяется ко всем карточкам, создаваемым этим типом записи.", selectedTemplates: "Только выбранные шаблоны", selectedTemplatesHelp: "Выберите шаблоны по понятным именам.", missingTemplate: "Один из сохранённых шаблонов больше не существует. Проверьте область и подтвердите профиль заново.",
  } : {
    suggestedSetup: "Suggested setup", confidence: "Confidence", recognizedFields: "Recognized fields", requirements: "Requirements",
    confidenceLabels: { high: "High", review: "Review recommended", insufficient: "Insufficient" },
    reviewRequired: "Review required", unresolved: "Unresolved fields", warningFallback: "The suggestion contains a warning. Review the mappings before enabling it.",
    fieldsTitle: "Fields used", fieldsHelp: "Map friendly roles to exact fields from the selected Anki note type.", custom: "Custom role",
    ankiField: "Anki field", chooseField: "Choose a field", usedElsewhere: "already used", multipleAdvanced: "Multiple fields are preserved; edit the exact combination in Advanced settings.", exactFieldHelp: "The exact field name from this note type is used.", invalidField: "Choose an available field.", noRoles: "The suggestion did not detect roles. Use Advanced settings or start with an empty profile.", duplicateField: "A field cannot be silently claimed by conflicting roles.",
    requirementsTitle: "Requirements", requirementsHelp: "Requirements compile only to the supported Inspection Profile v1 declarative checks.", fieldsUsed: "Fields", removeRequirement: "Remove requirement",
    priority: "Priority", high: "High", medium: "Medium", low: "Low", fieldPurpose: "Checked role", fieldPurposes: "Checked roles", choosePurpose: "Choose a role", minLength: "Minimum characters", invalidLength: "Enter an integer from 1 to 10000.", noRequirements: "There are no requirements yet. The profile can be saved as a draft, but add the necessary checks before enabling it.", addRequirement: "Add a safe requirement", add: "Add",
    scopeTitle: "Card scope", allCards: "All cards from this note type", singleTemplate: "Template", allTemplates: "All card templates", allTemplatesHelp: "The profile applies to every card generated by this note type.", selectedTemplates: "Selected templates only", selectedTemplatesHelp: "Choose templates by their friendly names.", missingTemplate: "A saved template no longer exists. Review the scope and reconfirm the profile.",
  };
}
