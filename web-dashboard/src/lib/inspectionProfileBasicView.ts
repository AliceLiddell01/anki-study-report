import type {
  InspectionCheck,
  InspectionFieldMapping,
  InspectionProfile,
  InspectionProfileCheckKind,
  InspectionProfileSummary,
} from "../types/inspectionProfiles";

export type InspectionProfileLanguage = "ru" | "en";

export interface FriendlyDefinition {
  label: string;
  description: string;
  known: boolean;
}

export interface BasicRoleView extends FriendlyDefinition {
  role: string;
  mapping: InspectionFieldMapping;
  blockingIssue?: string;
}

export interface BasicRequirementView {
  checkId: string;
  check: InspectionCheck;
  title: string;
  description: string;
  fields: string[];
  roles: string[];
  blockingIssue?: string;
}

export interface BasicProfileView {
  detectedKind: FriendlyDefinition;
  confidence: "high" | "review" | "insufficient";
  roles: BasicRoleView[];
  requirements: BasicRequirementView[];
  unresolvedFields: string[];
  warnings: string[];
}

const ROLE_COPY: Record<string, { ru: [string, string]; en: [string, string] }> = {
  term: { ru: ["Слово", "Основное слово или термин."], en: ["Word", "The main word or term."] },
  reading: { ru: ["Чтение", "Чтение слова или выражения."], en: ["Reading", "The reading of the word or expression."] },
  meaning: { ru: ["Значение", "Перевод или краткое значение."], en: ["Meaning", "A translation or concise meaning."] },
  example: { ru: ["Пример", "Пример употребления или контекст."], en: ["Example", "An example or usage context."] },
  part_of_speech: { ru: ["Часть речи", "Грамматическая категория слова."], en: ["Part of speech", "The grammatical category of the word."] },
  pitch: { ru: ["Ударение", "Сведения о японском pitch accent."], en: ["Pitch accent", "Japanese pitch-accent information."] },
  audio: { ru: ["Аудио", "Поле со звуковым маркером Anki."], en: ["Audio", "The field that contains an Anki audio marker."] },
  image: { ru: ["Изображение", "Поле с изображением или media-маркером."], en: ["Image", "The field that contains an image or media marker."] },
  question: { ru: ["Вопрос", "Текст, который должен сформулировать вопрос."], en: ["Question", "The text that should formulate the question."] },
  answer: { ru: ["Ответ", "Основной ответ на вопрос."], en: ["Answer", "The primary answer to the question."] },
  code: { ru: ["Код", "Фрагмент кода, связанный с вопросом."], en: ["Code", "A code sample associated with the question."] },
  explanation: { ru: ["Объяснение", "Дополнительное объяснение решения."], en: ["Explanation", "Additional explanation of the solution."] },
};

const KIND_COPY: Record<string, { ru: [string, string]; en: [string, string] }> = {
  japanese_vocab: { ru: ["Японская лексика", "Поля слова, значения и учебных media."], en: ["Japanese vocabulary", "Word, meaning, and study-media fields."] },
  japanese_grammar: { ru: ["Японская грамматика", "Грамматическая конструкция, значение и примеры."], en: ["Japanese grammar", "Grammar pattern, meaning, and examples."] },
  programming: { ru: ["Вопрос по программированию", "Вопрос, ответ, код и объяснение."], en: ["Programming question/answer", "Question, answer, code, and explanation."] },
  generic: { ru: ["Общий front/back", "Универсальная структура вопроса и ответа."], en: ["General front/back", "A general question-and-answer structure."] },
  cloze: { ru: ["Пропуски", "Тип записи с cloze-карточками."], en: ["Cloze", "A note type that generates cloze cards."] },
  unknown: { ru: ["Пользовательский тип", "Автоматическая семантика определена не полностью."], en: ["Unknown/custom", "Automatic semantics are incomplete."] },
};

const REQUIREMENT_COPY: Record<InspectionProfileCheckKind, { ru: string; en: string }> = {
  non_empty: { ru: "Выбранное поле не должно быть пустым.", en: "The selected field must not be empty." },
  contains_audio: { ru: "В выбранном поле должен присутствовать аудиомаркер.", en: "Audio must be present in the selected field." },
  contains_image: { ru: "В выбранном поле должно присутствовать изображение.", en: "An image must be present in the selected field." },
  min_text_length: { ru: "Текст должен содержать не меньше заданного числа символов.", en: "Text must contain at least the configured number of characters." },
  one_of_roles_non_empty: { ru: "Хотя бы одно из выбранных полей должно быть заполнено.", en: "At least one of the selected fields must be filled." },
  all_roles_non_empty: { ru: "Все выбранные поля должны быть заполнены.", en: "All selected fields must be filled." },
};

export function profileLanguage(language: string | undefined): InspectionProfileLanguage {
  return language?.toLowerCase().startsWith("ru") ? "ru" : "en";
}

export function friendlyRole(role: string, language: InspectionProfileLanguage): FriendlyDefinition {
  const copy = ROLE_COPY[role];
  if (copy) return { label: copy[language][0], description: copy[language][1], known: true };
  const label = humanize(role);
  return {
    label,
    description: language === "ru" ? "Пользовательская семантическая роль." : "A custom semantic role.",
    known: false,
  };
}

export function friendlyDetectedKind(kind: string, language: InspectionProfileLanguage): FriendlyDefinition {
  const copy = KIND_COPY[kind] ?? KIND_COPY.unknown;
  return { label: copy[language][0], description: copy[language][1], known: kind in KIND_COPY && kind !== "unknown" };
}

export function confidenceCategory(value: number): BasicProfileView["confidence"] {
  if (value >= 0.8) return "high";
  if (value >= 0.5) return "review";
  return "insufficient";
}

export function projectBasicProfile(
  item: InspectionProfileSummary,
  draft: InspectionProfile,
  language: InspectionProfileLanguage,
): BasicProfileView {
  const roles = draft.fieldMappings.map((mapping) => {
    const definition = friendlyRole(mapping.role, language);
    return {
      role: mapping.role,
      mapping,
      ...definition,
      blockingIssue: mapping.fields.length ? undefined : language === "ru" ? "Выберите поле Anki." : "Choose an Anki field.",
    };
  });
  const byRole = new Map(roles.map((role) => [role.role, role]));
  const requirements = draft.checks.map((check) => projectRequirement(check, byRole, language));
  return {
    detectedKind: friendlyDetectedKind(item.suggestion.detectedKind, language),
    confidence: confidenceCategory(item.suggestion.confidence),
    roles,
    requirements,
    unresolvedFields: item.suggestion.unresolvedFields.map((field) => field.name),
    warnings: [...item.suggestion.warnings],
  };
}

export function projectRequirement(
  check: InspectionCheck,
  roles: Map<string, BasicRoleView>,
  language: InspectionProfileLanguage,
): BasicRequirementView {
  const roleViews = check.roles.map((role) => roles.get(role)).filter((role): role is BasicRoleView => Boolean(role));
  const roleLabels = check.roles.map((role) => roles.get(role)?.label ?? humanize(role));
  const fields = roleViews.flatMap((role) => role.mapping.fields.map((field) => field.name));
  const subject = roleLabels.join(language === "ru" ? ", " : ", ") || (language === "ru" ? "Поле" : "Field");
  let title: string;
  switch (check.kind) {
    case "non_empty": title = language === "ru" ? `${subject}: обязательно` : `${subject} is required`; break;
    case "contains_audio": title = language === "ru" ? `${subject}: требуется аудио` : `${subject} must contain audio`; break;
    case "contains_image": title = language === "ru" ? `${subject}: требуется изображение` : `${subject} must contain an image`; break;
    case "min_text_length": title = language === "ru" ? `${subject}: минимум ${check.minLength} символов` : `${subject}: at least ${check.minLength} characters`; break;
    case "one_of_roles_non_empty": title = language === "ru" ? "Заполнить хотя бы одно поле" : "Fill at least one field"; break;
    case "all_roles_non_empty": title = language === "ru" ? "Заполнить все выбранные поля" : "Fill every selected field"; break;
  }
  const missingRoles = check.roles.filter((role) => !roles.has(role));
  return {
    checkId: check.checkId,
    check,
    title,
    description: REQUIREMENT_COPY[check.kind][language],
    fields,
    roles: roleLabels,
    blockingIssue: missingRoles.length
      ? language === "ru" ? "Проверка ссылается на отсутствующую роль." : "The requirement references a missing role."
      : undefined,
  };
}

export function createStableCheckId(profile: InspectionProfile, kind: InspectionProfileCheckKind): string {
  const base = kind.replace(/_/g, "-").slice(0, 64);
  let index = 1;
  let candidate = `${base}-${index}`;
  const used = new Set(profile.checks.map((check) => check.checkId));
  while (used.has(candidate)) {
    index += 1;
    candidate = `${base}-${index}`;
  }
  return candidate;
}

export function createCheck(profile: InspectionProfile, kind: InspectionProfileCheckKind): InspectionCheck {
  const roles = profile.fieldMappings.slice(0, kind.startsWith("all_") || kind.startsWith("one_") ? 2 : 1).map((mapping) => mapping.role);
  const base = { checkId: createStableCheckId(profile, kind), roles, priority: "medium" as const };
  if (kind === "min_text_length") return { ...base, kind, mode: "any", minLength: 1 };
  if (kind === "one_of_roles_non_empty" || kind === "all_roles_non_empty") return { ...base, kind };
  return { ...base, kind, mode: "any" };
}

export function canonicalProfileJson(profile: InspectionProfile): string {
  return JSON.stringify(profile, Object.keys(profile).sort());
}

function humanize(value: string): string {
  const text = value.replace(/[_-]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Custom";
}
