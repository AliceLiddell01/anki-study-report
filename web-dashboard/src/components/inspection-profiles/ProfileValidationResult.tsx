import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { profileLanguage, projectBasicProfile } from "../../lib/inspectionProfileBasicView";
import type { InspectionProfile, InspectionProfileSummary, InspectionValidateResponse } from "../../types/inspectionProfiles";

interface ProfileValidationResultProps {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  validation: InspectionValidateResponse;
}

export default function ProfileValidationResult({ item, draft, validation }: ProfileValidationResultProps) {
  const { i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const ru = language === "ru";
  const view = useMemo(() => projectBasicProfile(item, draft, language), [draft, item, language]);
  const requirements = new Map(view.requirements.map((requirement) => [requirement.checkId, requirement]));
  const grouped = new Map<string, typeof validation.preview.items[number]["failures"]>();
  for (const sample of validation.preview.items) {
    for (const failure of sample.failures) grouped.set(failure.checkId, [...(grouped.get(failure.checkId) ?? []), failure]);
  }
  const noCards = validation.preview.status === "unavailable" || validation.preview.evaluatedCount === 0;
  return (
    <section
      className={`inspection-validation-result${validation.valid ? " is-valid" : " is-invalid"}`}
      aria-labelledby="inspection-validation-title"
      role={validation.valid ? "status" : "alert"}
      tabIndex={-1}
    >
      <div className="inspection-validation-heading">
        {validation.valid ? <CheckCircle2 size={21} aria-hidden="true" /> : <AlertTriangle size={21} aria-hidden="true" />}
        <div>
          <h3 id="inspection-validation-title">{validation.valid ? (ru ? "Настройка структурно корректна" : "The setup is structurally valid") : (ru ? "Настройку нужно исправить" : "The setup needs correction")}</h3>
          <p>{!validation.valid
          ? (ru ? "Исправьте структурные ошибки перед включением профиля." : "Fix the structural errors before enabling the profile.")
          : noCards
            ? (ru ? "Профиль структурно корректен, но карточек для содержательного примера нет." : "The profile is structurally valid, but there are no cards available for a content sample.")
            : (ru ? "Backend проверил ограниченную безопасную выборку без передачи содержимого заметок." : "The backend checked a bounded safe sample without exposing note contents.")}</p>
        </div>
      </div>
      <dl className="inspection-validation-metrics">
        <div><dt>{ru ? "Проверено карточек" : "Cards evaluated"}</dt><dd>{validation.preview.evaluatedCount}</dd></div>
        <div><dt>{ru ? "Карточек с проблемами" : "Cards with problems"}</dt><dd>{validation.preview.items.filter((sample) => sample.failureCount > 0).length}</dd></div>
        <div><dt>{ru ? "Недоступно или устарело" : "Missing or stale"}</dt><dd>{validation.preview.missingCardIds.length}</dd></div>
        <div><dt>{ru ? "Выборка ограничена" : "Sample truncated"}</dt><dd>{validation.preview.truncated ? (ru ? "Да" : "Yes") : (ru ? "Нет" : "No")}</dd></div>
      </dl>
      {grouped.size ? (
        <div className="inspection-validation-groups">
          {[...grouped.entries()].map(([checkId, failures]) => {
            const requirement = requirements.get(checkId);
            const first = failures[0];
            return (
              <details key={checkId} className="inspection-validation-group">
                <summary>
                  <span>{requirement?.title ?? (ru ? "Пользовательское требование" : "Custom requirement")}</span>
                  <strong>{failures.length}</strong>
                </summary>
                <div>
                  {requirement?.fields.length ? <p>{ru ? "Поля" : "Fields"}: {requirement.fields.join(", ")}</p> : null}
                  {first ? <p>{evidenceLabel(first.evidence, ru)}</p> : null}
                  <p>{ru ? "Затронуто связанных карточек" : "Affected sibling cards"}: {Math.max(...failures.map((failure) => failure.affectedSiblingCount), 0)}</p>
                </div>
              </details>
            );
          })}
        </div>
      ) : !noCards ? <p className="inspection-validation-clean">{ru ? "В ограниченной выборке проблем не найдено." : "No problems were found in the bounded sample."}</p> : null}
    </section>
  );
}

function evidenceLabel(
  evidence: InspectionValidateResponse["preview"]["items"][number]["failures"][number]["evidence"],
  ru: boolean,
): string {
  if (evidence.marker === "audio") return ru ? "Не найден требуемый аудиомаркер." : "The required audio marker was not found.";
  if (evidence.marker === "image") return ru ? "Не найден требуемый маркер изображения." : "The required image marker was not found.";
  if (evidence.expectedTextLength !== null) return ru
    ? `Длина текста: ${evidence.actualTextLength ?? 0}; требуется не меньше ${evidence.expectedTextLength}.`
    : `Text length: ${evidence.actualTextLength ?? 0}; at least ${evidence.expectedTextLength} required.`;
  return ru ? "Условие требования не выполнено." : "The requirement condition was not met.";
}
