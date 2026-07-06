import type { AttentionIssueCounts, AttentionThresholds, CardAttention, CardIssueType, CardPreview, RenderedCardPreview, StudyReport } from "../types/report";
import { finiteNullableNumber, finiteNumber, safeText } from "./formatters";

export type CardsPeriodFilter = "today" | "7d" | "30d" | "all";
export type CardsIssueFilter = "all" | CardIssueType;
export type CardsSortKey = "risk" | "again" | "lapses" | "avgAnswer" | "lastReviewed";
export type CardAttentionAvailability = "available" | "unavailable" | "skipped" | "error" | "absent";

export const DEFAULT_CARD_FILTERS = {
  period: "all",
  deck: "all",
  issue: "all",
  query: "",
  sortKey: "risk",
} as const satisfies {
  period: CardsPeriodFilter;
  deck: string;
  issue: CardsIssueFilter;
  query: string;
  sortKey: CardsSortKey;
};

export interface CardAttentionState {
  status: CardAttentionAvailability;
  scannedCards: number | null;
  returnedCards: number | null;
  reason: string | null;
  collectorRan: boolean | null;
  collectionAvailable: boolean | null;
  revlogRows: number | null;
  candidateCards: number | null;
  notesLoaded: number | null;
  fieldScanCards: number | null;
  cardsTotal: number | null;
  notesTotal: number | null;
  source: "fresh" | "cache" | "mock" | "unknown";
  issueCounts: Required<AttentionIssueCounts>;
  thresholds: Required<AttentionThresholds>;
  periodStartRaw: number | null;
  periodEndRaw: number | null;
  periodStartMs: number | null;
  periodEndMs: number | null;
  timeUnitNormalized: boolean;
  selectedDeckIdsCount: number | null;
  deckFilterApplied: boolean;
  revlogTotalRows: number | null;
  revlogMinId: number | null;
  revlogMaxId: number | null;
  revlogRowsInPeriod: number | null;
  revlogRowsAfterDeckFilter: number | null;
  diagnosticWarning: string | null;
  noteTypeProfilesCount: number | null;
  unknownNoteTypesCount: number | null;
  detectedKinds: Record<string, number>;
  previewStrategy: string | null;
  missingFieldRoleSource: string | null;
  hasExplicitStatus: boolean;
  hasRowsKey: boolean;
}

export interface CardAttentionEmptyExplanation {
  title: string;
  text: string;
  sourceText: string;
}

export const cardIssueLabels: Record<CardIssueType, string> = {
  leech: "частые провалы",
  repeated_again: "повторные ошибки",
  slow_answer: "долгий ответ",
  low_pass_rate: "низкая успешность",
  missing_audio: "нет аудио",
  missing_example: "нет примера",
  missing_image: "нет изображения",
  missing_meaning: "нет значения",
  missing_part_of_speech: "нет части речи",
};

export const missingCardIssueTypes = new Set<CardIssueType>([
  "missing_audio",
  "missing_example",
  "missing_image",
  "missing_meaning",
  "missing_part_of_speech",
]);

const issueAliases: Record<string, CardIssueType> = {
  leech: "leech",
  repeated_again: "repeated_again",
  "repeated again": "repeated_again",
  again: "repeated_again",
  slow_answer: "slow_answer",
  "slow answer": "slow_answer",
  low_pass_rate: "low_pass_rate",
  "low pass rate": "low_pass_rate",
  missing_audio: "missing_audio",
  "missing audio": "missing_audio",
  missing_example: "missing_example",
  "missing example": "missing_example",
  missing_image: "missing_image",
  "missing image": "missing_image",
  missing_meaning: "missing_meaning",
  "missing meaning": "missing_meaning",
  meaning: "missing_meaning",
  missing_part_of_speech: "missing_part_of_speech",
  "missing part of speech": "missing_part_of_speech",
  part_of_speech: "missing_part_of_speech",
  pos: "missing_part_of_speech",
};

const issueWeights: Record<CardIssueType, number> = {
  leech: 35,
  repeated_again: 24,
  slow_answer: 14,
  low_pass_rate: 18,
  missing_audio: 8,
  missing_example: 8,
  missing_image: 7,
  missing_meaning: 12,
  missing_part_of_speech: 6,
};

export function buildCardAttentionRows(report: StudyReport | null): CardAttention[] {
  if (!report) {
    return [];
  }

  const rawRows = readRawCardRows(report);
  return rawRows
    .map((row, index) => normalizeCardAttention(row, index))
    .filter((row): row is CardAttention => Boolean(row))
    .sort((a, b) => b.riskScore - a.riskScore);
}

export function hasCardAttentionSource(report: StudyReport | null): boolean {
  return cardAttentionState(report).status === "available";
}

export function cardAttentionState(report: StudyReport | null): CardAttentionState {
  if (!report) {
    return emptyCardAttentionState("absent");
  }
  const record = report as unknown as Record<string, unknown>;
  const rows = readRawCardRows(report);
  const hasRowsKey = hasRawCardRowsKey(report);
  const statusRecord =
    record.attentionCardsStatus && typeof record.attentionCardsStatus === "object"
      ? (record.attentionCardsStatus as Record<string, unknown>)
      : null;

  if (statusRecord) {
    const rawStatus = String(statusRecord.status ?? "").trim().toLowerCase();
    const status: CardAttentionAvailability =
      rawStatus === "available" || rawStatus === "unavailable" || rawStatus === "skipped" || rawStatus === "error"
        ? rawStatus
        : "unavailable";
    return {
      status,
      scannedCards: finiteNullableNumber(statusRecord.scannedCards ?? statusRecord.scanned_cards),
      returnedCards: finiteNullableNumber(statusRecord.returnedCards ?? statusRecord.returned_cards),
      reason: safeNullableText(statusRecord.reason),
      collectorRan: finiteNullableBoolean(statusRecord.collectorRan ?? statusRecord.collector_ran),
      collectionAvailable: finiteNullableBoolean(statusRecord.collectionAvailable ?? statusRecord.collection_available),
      revlogRows: finiteNullableNumber(statusRecord.revlogRows ?? statusRecord.revlog_rows),
      candidateCards: finiteNullableNumber(statusRecord.candidateCards ?? statusRecord.candidate_cards),
      notesLoaded: finiteNullableNumber(statusRecord.notesLoaded ?? statusRecord.notes_loaded),
      fieldScanCards: finiteNullableNumber(statusRecord.fieldScanCards ?? statusRecord.field_scan_cards),
      cardsTotal: finiteNullableNumber(statusRecord.cardsTotal ?? statusRecord.cards_total),
      notesTotal: finiteNullableNumber(statusRecord.notesTotal ?? statusRecord.notes_total),
      source: normalizeStatusSource(statusRecord.source),
      issueCounts: normalizeIssueCounts(statusRecord.issueCounts ?? statusRecord.issue_counts),
      thresholds: normalizeThresholds(statusRecord.thresholds),
      periodStartRaw: finiteNullableNumber(statusRecord.periodStartRaw ?? statusRecord.period_start_raw),
      periodEndRaw: finiteNullableNumber(statusRecord.periodEndRaw ?? statusRecord.period_end_raw),
      periodStartMs: finiteNullableNumber(statusRecord.periodStartMs ?? statusRecord.period_start_ms),
      periodEndMs: finiteNullableNumber(statusRecord.periodEndMs ?? statusRecord.period_end_ms),
      timeUnitNormalized: Boolean(statusRecord.timeUnitNormalized ?? statusRecord.time_unit_normalized),
      selectedDeckIdsCount: finiteNullableNumber(statusRecord.selectedDeckIdsCount ?? statusRecord.selected_deck_ids_count),
      deckFilterApplied: Boolean(statusRecord.deckFilterApplied ?? statusRecord.deck_filter_applied),
      revlogTotalRows: finiteNullableNumber(statusRecord.revlogTotalRows ?? statusRecord.revlog_total_rows),
      revlogMinId: finiteNullableNumber(statusRecord.revlogMinId ?? statusRecord.revlog_min_id),
      revlogMaxId: finiteNullableNumber(statusRecord.revlogMaxId ?? statusRecord.revlog_max_id),
      revlogRowsInPeriod: finiteNullableNumber(statusRecord.revlogRowsInPeriod ?? statusRecord.revlog_rows_in_period),
      revlogRowsAfterDeckFilter: finiteNullableNumber(statusRecord.revlogRowsAfterDeckFilter ?? statusRecord.revlog_rows_after_deck_filter),
      diagnosticWarning: safeNullableText(statusRecord.diagnosticWarning ?? statusRecord.diagnostic_warning),
      noteTypeProfilesCount: finiteNullableNumber(statusRecord.noteTypeProfilesCount ?? statusRecord.note_type_profiles_count),
      unknownNoteTypesCount: finiteNullableNumber(statusRecord.unknownNoteTypesCount ?? statusRecord.unknown_note_types_count),
      detectedKinds: normalizeNumberRecord(statusRecord.detectedKinds ?? statusRecord.detected_kinds),
      previewStrategy: safeNullableText(statusRecord.previewStrategy ?? statusRecord.preview_strategy),
      missingFieldRoleSource: safeNullableText(statusRecord.missingFieldRoleSource ?? statusRecord.missing_field_role_source),
      hasExplicitStatus: true,
      hasRowsKey,
    };
  }

  if (rows.length > 0) {
    return {
      status: "available",
      scannedCards: rows.length,
      returnedCards: rows.length,
      reason: null,
      collectorRan: true,
      collectionAvailable: true,
      revlogRows: null,
      candidateCards: rows.length,
      notesLoaded: null,
      fieldScanCards: null,
      cardsTotal: null,
      notesTotal: null,
      source: "unknown",
      issueCounts: emptyIssueCounts(),
      thresholds: defaultThresholds(),
      periodStartRaw: null,
      periodEndRaw: null,
      periodStartMs: null,
      periodEndMs: null,
      timeUnitNormalized: false,
      selectedDeckIdsCount: null,
      deckFilterApplied: false,
      revlogTotalRows: null,
      revlogMinId: null,
      revlogMaxId: null,
      revlogRowsInPeriod: null,
      revlogRowsAfterDeckFilter: null,
      diagnosticWarning: null,
      noteTypeProfilesCount: null,
      unknownNoteTypesCount: null,
      detectedKinds: {},
      previewStrategy: null,
      missingFieldRoleSource: null,
      hasExplicitStatus: false,
      hasRowsKey,
    };
  }

  return {
    ...emptyCardAttentionState(hasRowsKey ? "unavailable" : "absent"),
    hasRowsKey,
  };
}

export function summarizeCardAttentionRows(rows: CardAttention[]) {
  return {
    problemCards: rows.length,
    leech: rows.filter((row) => row.issues.includes("leech")).length,
    repeatedAgain: rows.filter((row) => row.issues.includes("repeated_again")).length,
    slowAnswer: rows.filter((row) => row.issues.includes("slow_answer")).length,
    dataGaps: rows.filter((row) => row.issues.some((issue) => missingCardIssueTypes.has(issue))).length,
  };
}

export function explainCardAttentionEmptyState(state: CardAttentionState): CardAttentionEmptyExplanation {
  const sourceText =
    state.source === "fresh" && state.status === "available"
      ? "Данные уровня карточек собраны из текущей коллекции Anki."
      : state.source === "cache"
        ? "Данные уровня карточек не собраны fresh path."
        : "Источник card-level данных не подтверждён.";

  if (state.status !== "available") {
    return {
      title: "В текущем отчёте нет данных уровня карточек",
      text: state.reason || sourceText,
      sourceText,
    };
  }
  if ((state.revlogTotalRows ?? 0) > 0 && state.revlogRowsInPeriod === 0) {
    return {
      title: "Нет проблемных карточек",
      text: "Повторы в revlog есть, но выбранный период не совпал с timestamp range.",
      sourceText,
    };
  }
  if (state.deckFilterApplied && (state.revlogRowsAfterDeckFilter ?? 0) === 0 && (state.revlogRowsInPeriod ?? 0) > 0) {
    return {
      title: "Нет проблемных карточек",
      text: "Фильтр колоды отсеял все revlog-записи.",
      sourceText,
    };
  }
  if (state.revlogRows === 0) {
    return {
      title: "Нет проблемных карточек",
      text: "В выбранном периоде нет повторений для выбранной колоды.",
      sourceText,
    };
  }
  if (state.candidateCards === 0) {
    return {
      title: "Нет проблемных карточек",
      text: "В выбранном периоде не найдено карточек-кандидатов для анализа.",
      sourceText,
    };
  }
  if ((state.scannedCards ?? 0) > 0 && state.returnedCards === 0) {
    return {
      title: "Нет проблемных карточек",
      text: "Карточки были просканированы, но leech, repeated Again, slow answer, low pass rate и missing-field issues не найдены.",
      sourceText,
    };
  }
  return {
    title: "Нет проблемных карточек",
    text: state.reason || "Сканирование выполнено, но карточки не попали под критерии риска.",
    sourceText,
  };
}

export function filterCardAttentionRows(
  rows: CardAttention[],
  filters: {
    period: CardsPeriodFilter;
    deck: string;
    issue: CardsIssueFilter;
    query: string;
    sortKey: CardsSortKey;
  },
  options: { today?: string | null } = {},
): CardAttention[] {
  const normalizedQuery = filters.query.trim().toLowerCase();
  const today = normalizeDateKey(options.today) ?? todayDateKey();
  return rows
    .filter((row) => rowMatchesLocalPeriod(row, filters.period, today))
    .filter((row) => filters.deck === "all" || row.deckName === filters.deck)
    .filter((row) => filters.issue === "all" || row.issues.includes(filters.issue))
    .filter((row) => {
      if (!normalizedQuery) {
        return true;
      }
      return `${row.front} ${row.preview?.secondary ?? ""} ${row.preview?.tertiary ?? ""} ${row.deckName} ${row.issues.map((issue) => cardIssueLabels[issue]).join(" ")}`
        .toLowerCase()
        .includes(normalizedQuery);
    })
    .sort((a, b) => compareCardRows(a, b, filters.sortKey));
}

export function buildCardBrowserSearch(row: Pick<CardAttention, "deckName"> & Partial<Pick<CardAttention, "cardId" | "noteId" | "front" | "browserSearch">>): string {
  if (row.browserSearch?.trim()) {
    return row.browserSearch.trim();
  }
  if (typeof row.cardId === "number" && Number.isFinite(row.cardId)) {
    return `cid:${Math.trunc(row.cardId)}`;
  }
  if (typeof row.noteId === "number" && Number.isFinite(row.noteId)) {
    return `nid:${Math.trunc(row.noteId)}`;
  }
  const preview = attentionSearchText(row.front ?? "");
  return `deck:${quoteAnkiSearchValue(row.deckName)}${preview ? ` ${preview}` : ""}`;
}

function readRawCardRows(report: StudyReport): unknown[] {
  const record = report as unknown as Record<string, unknown>;
  for (const key of ["attentionCards", "cards", "cardIssues"]) {
    const value = record[key];
    if (Array.isArray(value)) {
      return value;
    }
  }
  return [];
}

function hasRawCardRowsKey(report: StudyReport): boolean {
  const record = report as unknown as Record<string, unknown>;
  return ["attentionCards", "cards", "cardIssues"].some((key) => Array.isArray(record[key]));
}

function emptyCardAttentionState(status: CardAttentionAvailability): CardAttentionState {
  return {
    status,
    scannedCards: null,
    returnedCards: null,
    reason: null,
    collectorRan: null,
    collectionAvailable: null,
    revlogRows: null,
    candidateCards: null,
    notesLoaded: null,
    fieldScanCards: null,
    cardsTotal: null,
    notesTotal: null,
    source: "unknown",
    issueCounts: emptyIssueCounts(),
    thresholds: defaultThresholds(),
    periodStartRaw: null,
    periodEndRaw: null,
    periodStartMs: null,
    periodEndMs: null,
    timeUnitNormalized: false,
    selectedDeckIdsCount: null,
    deckFilterApplied: false,
    revlogTotalRows: null,
    revlogMinId: null,
    revlogMaxId: null,
    revlogRowsInPeriod: null,
    revlogRowsAfterDeckFilter: null,
    diagnosticWarning: null,
    noteTypeProfilesCount: null,
    unknownNoteTypesCount: null,
    detectedKinds: {},
    previewStrategy: null,
    missingFieldRoleSource: null,
    hasExplicitStatus: false,
    hasRowsKey: false,
  };
}

function normalizeIssueCounts(value: unknown): Required<AttentionIssueCounts> {
  const record = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const empty = emptyIssueCounts();
  return {
    leech: Math.max(0, finiteNumber(record.leech, empty.leech)),
    repeatedAgain: Math.max(0, finiteNumber(record.repeatedAgain ?? record.repeated_again, empty.repeatedAgain)),
    slowAnswer: Math.max(0, finiteNumber(record.slowAnswer ?? record.slow_answer, empty.slowAnswer)),
    lowPassRate: Math.max(0, finiteNumber(record.lowPassRate ?? record.low_pass_rate, empty.lowPassRate)),
    missingAudio: Math.max(0, finiteNumber(record.missingAudio ?? record.missing_audio, empty.missingAudio)),
    missingExample: Math.max(0, finiteNumber(record.missingExample ?? record.missing_example, empty.missingExample)),
    missingPitch: Math.max(0, finiteNumber(record.missingPitch ?? record.missing_pitch, empty.missingPitch)),
    missingImage: Math.max(0, finiteNumber(record.missingImage ?? record.missing_image, empty.missingImage)),
    missingMeaning: Math.max(0, finiteNumber(record.missingMeaning ?? record.missing_meaning, empty.missingMeaning)),
    missingPartOfSpeech: Math.max(0, finiteNumber(record.missingPartOfSpeech ?? record.missing_part_of_speech, empty.missingPartOfSpeech)),
  };
}

function emptyIssueCounts(): Required<AttentionIssueCounts> {
  return {
    leech: 0,
    repeatedAgain: 0,
    slowAnswer: 0,
    lowPassRate: 0,
    missingAudio: 0,
    missingExample: 0,
    missingPitch: 0,
    missingImage: 0,
    missingMeaning: 0,
    missingPartOfSpeech: 0,
  };
}

function normalizeThresholds(value: unknown): Required<AttentionThresholds> {
  const record = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const defaults = defaultThresholds();
  return {
    repeatedAgainThreshold: Math.max(0, finiteNumber(record.repeatedAgainThreshold ?? record.repeated_again_threshold, defaults.repeatedAgainThreshold)),
    slowAnswerSeconds: Math.max(0, finiteNumber(record.slowAnswerSeconds ?? record.slow_answer_seconds, defaults.slowAnswerSeconds)),
    lowPassRateThreshold: Math.max(0, finiteNumber(record.lowPassRateThreshold ?? record.low_pass_rate_threshold, defaults.lowPassRateThreshold)),
    leechLapsesFallback: Math.max(0, finiteNumber(record.leechLapsesFallback ?? record.leech_lapses_fallback, defaults.leechLapsesFallback)),
    maxResults: Math.max(0, finiteNumber(record.maxResults ?? record.max_results, defaults.maxResults)),
  };
}

function defaultThresholds(): Required<AttentionThresholds> {
  return {
    repeatedAgainThreshold: 2,
    slowAnswerSeconds: 10,
    lowPassRateThreshold: 0.6,
    leechLapsesFallback: 8,
    maxResults: 100,
  };
}

function normalizeCardAttention(value: unknown, index: number): CardAttention | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  const cardId = finiteOptionalInteger(record.cardId ?? record.cid ?? record.card_id);
  const noteId = finiteOptionalInteger(record.noteId ?? record.nid ?? record.note_id);
  const deckId = finiteOptionalInteger(record.deckId ?? record.did ?? record.deck_id);
  const deckName = safeText(record.deckName ?? record.deck ?? record.deck_name, "Неизвестная колода");
  const preview = normalizePreview(record.preview);
  const renderedPreview = normalizeRenderedPreview(record.renderedPreview ?? record.rendered_preview);
  const front = safeText(preview?.frontText ?? record.front ?? record.frontPreview ?? record.front_preview ?? record.question, "Карточка без front preview");
  const againCount = Math.max(0, finiteNumber(record.againCount ?? record.again_count ?? record.again, 0));
  const lapses = Math.max(0, finiteNumber(record.lapses ?? record.lapseCount ?? record.lapse_count, 0));
  const averageAnswerSeconds = finiteNullableNumber(record.averageAnswerSeconds ?? record.avgAnswerSeconds ?? record.average_answer_seconds);
  const passRate = finiteNullableNumber(record.passRate ?? record.pass_rate);
  const issues = normalizeIssues(record, { againCount, lapses, averageAnswerSeconds, passRate });
  if (!issues.length) {
    return null;
  }

  const riskScore = Math.max(0, Math.min(100, finiteNumber(record.riskScore ?? record.risk_score, inferRiskScore(issues, againCount, lapses, averageAnswerSeconds, passRate))));
  const row: CardAttention = {
    id: safeText(record.id, cardId ? `cid-${cardId}` : `card-${index + 1}`),
    cardId,
    noteId,
    deckId,
    deckName,
    front,
    preview: preview ?? { frontText: front, primary: front },
    renderedPreview,
    issues,
    againCount,
    lapses,
    averageAnswerSeconds,
    passRate,
    lastReviewed: safeNullableText(record.lastReviewed ?? record.lastReviewedAt ?? record.last_reviewed ?? record.last_reviewed_at ?? record.reviewedAt ?? record.reviewed_at),
    riskScore,
    browserSearch: safeNullableText(record.browserSearch ?? record.search ?? record.searchQuery ?? record.search_query) ?? undefined,
    periods: normalizePeriods(record.periods ?? record.period),
    answerPattern: safeNullableText(record.answerPattern ?? record.pattern ?? record.answer_pattern) ?? undefined,
  };
  row.browserSearch = buildCardBrowserSearch(row);
  return row;
}

function normalizeRenderedPreview(value: unknown): RenderedCardPreview | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const renderStatus = safeText(record.renderStatus ?? record.render_status, "unavailable");
  const renderSource = safeText(record.renderSource ?? record.render_source, "");
  return {
    renderStatus:
      renderStatus === "available" || renderStatus === "sanitized" || renderStatus === "fallback" || renderStatus === "error" || renderStatus === "unavailable"
        ? renderStatus
        : "unavailable",
    frontHtml: safeText(record.frontHtml ?? record.front_html, "") || undefined,
    backHtml: safeText(record.backHtml ?? record.back_html, "") || undefined,
    frontPlainText: safeText(record.frontPlainText ?? record.front_plain_text, "") || undefined,
    backPlainText: safeText(record.backPlainText ?? record.back_plain_text, "") || undefined,
    css: safeText(record.css, "") || undefined,
    mediaRefs: normalizeMediaRefs(record.mediaRefs ?? record.media_refs),
    cardOrd: finiteOptionalInteger(record.cardOrd ?? record.card_ord),
    cardId: finiteOptionalInteger(record.cardId ?? record.card_id),
    renderSource: renderSource || undefined,
    fallbackReason: safeText(record.fallbackReason ?? record.fallback_reason, "") || undefined,
    reason: safeText(record.reason, "") || undefined,
  };
}

function normalizePreview(value: unknown): CardPreview | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const primary = safeText(record.primary, "");
  const frontText = safeText(record.frontText ?? record.front_text ?? record.frontOnly ?? record.front_only, "") || primary;
  const backText = safeText(record.backText ?? record.back_text, "");
  const secondary = safeText(record.secondary, "");
  const tertiary = safeText(record.tertiary, "");
  const mediaBadges = Array.isArray(record.mediaBadges)
    ? record.mediaBadges
        .map((item) => safeText(item, "").toLowerCase())
        .filter((item) => item === "audio" || item === "image" || item === "gif" || item === "pitch" || item === "example")
    : [];
  const preview: CardPreview = {
    frontText,
    backText: backText || undefined,
    primary,
    frontOnly: safeText(record.frontOnly ?? record.front_only, "") || undefined,
    secondary: secondary || undefined,
    tertiary: tertiary || undefined,
    mediaBadges: [...new Set(mediaBadges)],
    noteTypeName: safeText(record.noteTypeName, "") || undefined,
    cardTemplateName: safeText(record.cardTemplateName, "") || undefined,
    detectedKind: safeText(record.detectedKind, "") || undefined,
  };
  return preview.frontText || preview.primary || preview.secondary || preview.tertiary ? preview : undefined;
}

function normalizeIssues(
  record: Record<string, unknown>,
  metrics: {
    againCount: number;
    lapses: number;
    averageAnswerSeconds: number | null;
    passRate: number | null;
  },
): CardIssueType[] {
  const issues = new Set<CardIssueType>();
  for (const source of [record.issues, record.problemTypes, record.problem_types, record.missingFields, record.missing_fields]) {
    if (Array.isArray(source)) {
      for (const item of source) {
        addIssue(issues, item);
      }
    }
  }

  for (const [key, issue] of Object.entries({
    leech: "leech",
    isLeech: "leech",
    repeatedAgain: "repeated_again",
    slowAnswer: "slow_answer",
    lowPassRate: "low_pass_rate",
    missingAudio: "missing_audio",
    missingExample: "missing_example",
    missingImage: "missing_image",
    missingMeaning: "missing_meaning",
    missingPartOfSpeech: "missing_part_of_speech",
  }) as Array<[string, CardIssueType]>) {
    if (record[key] === true) {
      issues.add(issue);
    }
  }

  if (metrics.lapses >= 8) {
    issues.add("leech");
  }
  if (metrics.againCount >= 2) {
    issues.add("repeated_again");
  }
  if (metrics.averageAnswerSeconds !== null && metrics.averageAnswerSeconds >= 15) {
    issues.add("slow_answer");
  }
  if (metrics.passRate !== null && metrics.passRate < 0.75) {
    issues.add("low_pass_rate");
  }
  return [...issues];
}

function addIssue(issues: Set<CardIssueType>, value: unknown) {
  const key = String(value ?? "").trim().toLowerCase().replace(/-/g, "_");
  const normalized = issueAliases[key];
  if (normalized) {
    issues.add(normalized);
  }
}

function normalizeMediaRefs(value: unknown): NonNullable<RenderedCardPreview["mediaRefs"]> {
  if (!Array.isArray(value)) {
    return [];
  }
  const refs: NonNullable<RenderedCardPreview["mediaRefs"]> = [];
  for (const item of value) {
    const record: Record<string, unknown> = item && typeof item === "object" ? (item as Record<string, unknown>) : { name: item };
    const name = safeText(record.name, "");
    if (!name || /(?:^\.|[\\/]|\.{2}|^[a-z][a-z0-9+.-]:)/i.test(name)) {
      continue;
    }
    const type = safeText(record.type, "") === "audio" ? "audio" : "image";
    const url = safeText(record.url, "") || `/api/media?name=${encodeURIComponent(name)}`;
    if (/^(?:https?:|file:)/i.test(url) || /token=/i.test(url)) {
      refs.push({ name, type, url: `/api/media?name=${encodeURIComponent(name)}` });
    } else {
      refs.push({ name, type, url });
    }
  }
  return refs;
}

function inferRiskScore(
  issues: CardIssueType[],
  againCount: number,
  lapses: number,
  averageAnswerSeconds: number | null,
  passRate: number | null,
): number {
  const base = issues.reduce((sum, issue) => sum + issueWeights[issue], 0);
  const againWeight = Math.min(18, againCount * 3);
  const lapseWeight = Math.min(16, lapses * 2);
  const answerWeight = averageAnswerSeconds === null ? 0 : Math.min(12, Math.max(0, averageAnswerSeconds - 10));
  const passWeight = passRate === null ? 0 : Math.max(0, (0.82 - passRate) * 45);
  return Math.round(Math.min(100, base + againWeight + lapseWeight + answerWeight + passWeight));
}

function compareCardRows(a: CardAttention, b: CardAttention, sortKey: CardsSortKey) {
  if (sortKey === "lastReviewed") {
    return dateValue(b.lastReviewed) - dateValue(a.lastReviewed);
  }
  if (sortKey === "again") {
    return b.againCount - a.againCount;
  }
  if (sortKey === "lapses") {
    return b.lapses - a.lapses;
  }
  if (sortKey === "avgAnswer") {
    return finiteNumber(b.averageAnswerSeconds, -1) - finiteNumber(a.averageAnswerSeconds, -1);
  }
  return b.riskScore - a.riskScore;
}

function normalizePeriods(value: unknown): CardAttention["periods"] {
  const rawValues = Array.isArray(value) ? value : value ? [value] : [];
  const periods = rawValues
    .map((item) => String(item).trim().toLowerCase())
    .map((item) => (item === "7days" || item === "7_days" ? "7d" : item))
    .map((item) => (item === "30days" || item === "30_days" ? "30d" : item))
    .filter((item): item is CardsPeriodFilter => item === "today" || item === "7d" || item === "30d" || item === "all");
  return periods.length ? [...new Set(periods)] : ["all"];
}

function rowMatchesLocalPeriod(row: CardAttention, period: CardsPeriodFilter, today: string): boolean {
  if (period === "all") {
    return true;
  }
  const reviewed = normalizeDateKey(row.lastReviewed);
  if (!reviewed) {
    return false;
  }
  const todayMs = Date.parse(`${today}T00:00:00Z`);
  const reviewedMs = Date.parse(`${reviewed}T00:00:00Z`);
  if (!Number.isFinite(todayMs) || !Number.isFinite(reviewedMs)) {
    return false;
  }
  const days = period === "today" ? 0 : period === "7d" ? 6 : 29;
  const startMs = todayMs - days * 24 * 60 * 60 * 1000;
  return reviewedMs >= startMs && reviewedMs <= todayMs;
}

export function reportTodayDate(report: StudyReport | null): string {
  const metadata = report?.metadata;
  return normalizeDateKey(metadata?.todayDate) ?? normalizeDateKey(metadata?.createdAt) ?? todayDateKey();
}

function normalizeDateKey(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const match = value.match(/\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : null;
}

function todayDateKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function finiteOptionalInteger(value: unknown): number | undefined {
  const normalized =
    typeof value === "string" && value.trim() ? Number.parseInt(value.trim(), 10) : finiteNullableNumber(value);
  return typeof normalized === "number" && Number.isFinite(normalized) ? Math.trunc(normalized) : undefined;
}

function safeNullableText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const text = value.trim();
  return text || null;
}

function finiteNullableBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") {
    return value;
  }
  return null;
}

function normalizeStatusSource(value: unknown): CardAttentionState["source"] {
  const source = String(value ?? "").trim().toLowerCase();
  return source === "fresh" || source === "cache" || source === "mock" || source === "unknown" ? source : "unknown";
}

function normalizeNumberRecord(value: unknown): Record<string, number> {
  const record = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const result: Record<string, number> = {};
  for (const [key, raw] of Object.entries(record)) {
    const number = finiteNumber(raw, 0);
    if (key.trim() && Number.isFinite(number)) {
      result[key] = Math.max(0, number);
    }
  }
  return result;
}

function dateValue(value: string | null): number {
  if (!value) {
    return 0;
  }
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function quoteAnkiSearchValue(value: string): string {
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function attentionSearchText(value: string): string {
  return value
    .replace(/["\\<>]/g, " ")
    .replace(/\b[A-Za-z]:\\\S+/g, " ")
    .replace(/file:\/\/\S+/gi, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 40);
}
