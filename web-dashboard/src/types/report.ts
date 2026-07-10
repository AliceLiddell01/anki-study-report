export type Status = "good" | "neutral" | "warning" | "danger";

export type AnswerMode = "pass_fail" | "standard";
export type ReportDataSource = "legacy" | "cache" | "mixed";

export interface ReportMetadata {
  title: string;
  period: string;
  periodId?: string;
  scope?: string;
  selectedDecks: string[];
  includeChildren: boolean;
  answerMode: AnswerMode;
  createdAt: string;
  todayDate?: string;
  detailMode: "compact" | "normal" | "full";
  deletedCardReviews: number;
  unavailableTrackerNotes: string[];
  reportSchemaVersion?: number;
  cardLevelSchemaVersion?: number;
  cardLevelSource?: "fresh" | "cache" | "mock" | "unknown";
}

export interface KpiMetric {
  id: string;
  label: string;
  value: string;
  caption: string;
  status: Status;
  icon: string;
}

export interface AnswerDistributionItem {
  label: "Pass" | "Fail" | "Hard" | "Easy";
  value: number;
  color: string;
}

export interface ActivityDay {
  date: string;
  reviews: number;
  newCards: number;
  again: number;
  hard?: number;
  good?: number;
  easy?: number;
  pass?: number;
  fail?: number;
  passRate?: number | null;
  failRate?: number | null;
  studySeconds?: number;
  avgAnswerSeconds?: number | null;
}

export interface WeekdayActivity {
  day: string;
  reviews: number;
  activeRate: number;
}

export interface DeckPerformance {
  id: number;
  name: string;
  totalReviews: number;
  newCards: number;
  passCount: number;
  failCount: number;
  hardCount: number;
  easyCount: number;
  passRate: number;
  failRate: number;
  averageAnswerSeconds: number;
  studyMinutes: number;
  status: Status;
  explanation: string;
}

export type CardIssueType =
  | "leech"
  | "repeated_again"
  | "slow_answer"
  | "low_pass_rate"
  | "missing_audio"
  | "missing_example"
  | "missing_image"
  | "missing_meaning"
  | "missing_part_of_speech";

export interface CardAttention {
  id: string;
  cardId?: number;
  noteId?: number;
  deckId?: number;
  deckName: string;
  front: string;
  preview?: CardPreview;
  renderedPreview?: RenderedCardPreview;
  issues: CardIssueType[];
  againCount: number;
  lapses: number;
  averageAnswerSeconds: number | null;
  passRate: number | null;
  lastReviewed: string | null;
  riskScore: number;
  browserSearch?: string;
  periods?: Array<"today" | "7d" | "30d" | "all">;
  answerPattern?: string;
}

export interface CardPreview {
  frontText: string;
  backText?: string;
  primary: string;
  secondary?: string;
  tertiary?: string;
  frontOnly?: string;
  mediaBadges?: string[];
  noteTypeName?: string;
  cardTemplateName?: string;
  detectedKind?: string;
}

export interface RenderedCardPreview {
  frontHtml?: string;
  backHtml?: string;
  frontPlainText?: string;
  backPlainText?: string;
  css?: string;
  mediaRefs?: CardMediaRef[];
  cardOrd?: number;
  cardId?: number;
  renderSource?: "anki_native" | "anki_like_fallback" | string;
  renderStatus: "available" | "unavailable" | "sanitized" | "fallback" | "error";
  fallbackReason?: string;
  reason?: string;
}

export interface CardMediaRef {
  name: string;
  type: "image" | "audio";
  url: string;
}

export interface NoteTypeCatalogItem {
  noteTypeId: number;
  name: string;
  noteCount: number;
  cardTemplateCount: number;
  fields: string[];
  templates: Array<{
    ord: number;
    name: string;
    qfmtAvailable?: boolean;
    afmtAvailable?: boolean;
  }>;
  cssAvailable: boolean;
  usedInCurrentCards: boolean;
}

// Optional raw card-level payload shape. `attentionCards` is the canonical input.
export interface RawCardAttentionPayload {
  cardId: number | string;
  noteId?: number | string;
  deckName: string;
  frontPreview: string;
  preview?: CardPreview;
  renderedPreview?: RenderedCardPreview;
  issues: string[];
  riskScore?: number;
  againCount?: number;
  lapses?: number;
  averageAnswerSeconds?: number;
  passRate?: number;
  lastReviewedAt?: string;
  searchQuery?: string;
  missingFields?: string[];
}

export interface AttentionCardsStatus {
  status: "available" | "unavailable" | "skipped" | "error";
  scannedCards?: number;
  returnedCards?: number;
  reason?: string;
  collectorRan?: boolean;
  collectionAvailable?: boolean;
  revlogRows?: number;
  candidateCards?: number;
  notesLoaded?: number;
  fieldScanCards?: number;
  cardsTotal?: number;
  notesTotal?: number;
  source?: "fresh" | "cache" | "mock" | "unknown";
  issueCounts?: AttentionIssueCounts;
  thresholds?: AttentionThresholds;
  periodStartRaw?: number | null;
  periodEndRaw?: number | null;
  periodStartMs?: number;
  periodEndMs?: number;
  timeUnitNormalized?: boolean;
  selectedDeckIdsCount?: number;
  deckFilterApplied?: boolean;
  revlogTotalRows?: number;
  revlogMinId?: number;
  revlogMaxId?: number;
  revlogRowsInPeriod?: number;
  revlogRowsAfterDeckFilter?: number;
  diagnosticWarning?: string;
  noteTypeProfilesCount?: number;
  unknownNoteTypesCount?: number;
  detectedKinds?: Record<string, number>;
  previewStrategy?: string;
  missingFieldRoleSource?: string;
}

export interface AttentionIssueCounts {
  leech?: number;
  repeatedAgain?: number;
  slowAnswer?: number;
  lowPassRate?: number;
  missingAudio?: number;
  missingExample?: number;
  missingPitch?: number;
  missingImage?: number;
  missingMeaning?: number;
  missingPartOfSpeech?: number;
}

export interface AttentionThresholds {
  repeatedAgainThreshold?: number;
  slowAnswerSeconds?: number;
  lowPassRateThreshold?: number;
  leechLapsesFallback?: number;
  maxResults?: number;
}

export interface CardsPreviewSettings {
  displayMode: "table" | "tiles" | "ankiPreview";
  noteTypeOverrides: Record<
    string,
    {
      kind?: string;
      primaryField?: string;
      secondaryField?: string;
      tertiaryField?: string;
      roleOverrides?: Record<string, string>;
      previewMode?: "auto" | "structured" | "ankiLike" | "disabled";
      cardTemplate?: "auto" | number | string;
      customFrontTemplate?: string;
      customBackTemplate?: string;
      customCss?: string;
    }
  >;
}

export interface ForecastDay {
  offset: number;
  date: string;
  due: number;
  reviewDue: number;
  learningDue: number;
  risk: "low" | "medium" | "high";
}

export interface FsrsSettings {
  enabled: boolean;
  desiredRetention: number | null;
  helperDetected: boolean;
  helperConfigAvailable: boolean;
  rescheduleEnabled: boolean;
  autoDisperse: boolean;
}

export interface FsrsSummary {
  predictedRecall: number | null;
  cardsBelowTarget: number;
  highForgettingRisk: number;
  averageDifficulty: number | null;
  futureLoad30Days: number;
  settings: FsrsSettings;
}

export type ComparisonSeverity = "positive" | "neutral" | "warning" | "danger";
export type ComparisonPeriod = "yesterday" | "avg7" | "avg30" | "week";

export interface DailyStats {
  date: string;
  label: string;
  reviews: number;
  newCards: number;
  pass: number;
  fail: number;
  hard: number;
  easy: number;
  studySeconds: number;
  studyMinutes: number;
  avgAnswerSeconds: number | null;
  activeDecks: number;
  passRate: number | null;
  failRate: number | null;
}

export interface MetricDelta {
  delta: number | null;
  percentDelta: number | null;
}

export interface RateDelta {
  deltaPp: number | null;
}

export interface ComparisonDelta {
  reviews: MetricDelta;
  newCards: MetricDelta;
  studyMinutes: MetricDelta;
  passRate: RateDelta;
  failRate: RateDelta;
  avgAnswerSeconds: MetricDelta;
  activeDecks: MetricDelta;
}

export interface ComparisonInsight {
  severity: ComparisonSeverity;
  title: string;
  text: string;
  metric?: string;
}

export interface ProgressComparison {
  available: boolean;
  message: string;
  today: DailyStats;
  baselines: {
    yesterday: DailyStats;
    avg7: DailyStats;
    avg30: DailyStats;
    sameWeekdayLastWeek: DailyStats;
    currentWeek: DailyStats;
    previousWeek: DailyStats;
    currentMonth: DailyStats;
    previousMonth: DailyStats;
  };
  comparisons: {
    yesterday: ComparisonDelta;
    avg7: ComparisonDelta;
    avg30: ComparisonDelta;
    sameWeekdayLastWeek: ComparisonDelta;
    week: ComparisonDelta;
    month: ComparisonDelta;
  };
  insights: ComparisonInsight[];
}

export interface CalendarDayStats {
  date: string;
  reviews: number;
  newCards: number;
  learning?: number;
  relearning?: number;
  mature?: number;
  pass?: number;
  fail?: number;
  passRate?: number | null;
  studySeconds?: number;
  avgAnswerSeconds?: number | null;
  activeDecks?: number;
  isToday?: boolean;
  isFuture?: boolean;
  dueForecast?: number | null;
}

export interface CalendarInsight {
  tone: "positive" | "neutral" | "warning" | "danger";
  title: string;
  text: string;
}

export interface StreakInfo {
  currentStreak: number;
  bestStreak: number;
  activeDays: number;
  totalDays: number;
}

export interface RecommendationPanel {
  mainAction: string;
  why: string;
  avoid: string;
  checklist: string[];
}

export type StatsCacheStatus = "ready" | "scheduled" | "building" | "stale" | "empty" | "error";

export interface StatsCacheSummary {
  status: StatsCacheStatus;
  dataSource?: ReportDataSource;
  usedFor?: string[];
  version?: number;
  createdAt?: number;
  updatedAt: number;
  lastRevlogId?: number;
  cachedDays: number;
  cachedDeckDays: number;
  isBuilding?: boolean;
  error?: string | null;
  lastError?: string | null;
  lastBuildDurationMs?: number;
  lastRefreshDurationMs?: number;
  lastRefreshAddedRows?: number;
  fallbackReason?: string | null;
  limitations?: string[];
  cachePath?: string;
  deckHistoryNote?: string;
  useStatsCacheForReport?: boolean;
  reportSourceMode?: string;
  periodSummary?: {
    total_reviews: number;
    new_cards: number;
    again: number;
    hard: number;
    good: number;
    easy: number;
    pass: number;
    fail: number;
    pass_rate: number | null;
    fail_rate: number | null;
    study_seconds: number;
    active_days: number;
    average_reviews_per_active_day: number;
    average_study_seconds_per_active_day: number;
    average_answer_seconds: number | null;
  };
  cacheDeckSummary?: {
    available: boolean;
    limitation: string;
  };
  performance?: {
    cacheReadMs?: number;
    cacheAdaptMs?: number;
  };
}

export interface StudyReport {
  dataSource?: ReportDataSource;
  metadata: ReportMetadata;
  summary: {
    verdict: string;
    riskLevel: Status;
    mainAction: string;
    warning: string;
    newCardsAdvice: string;
  };
  kpis: KpiMetric[];
  answerDistribution: AnswerDistributionItem[];
  activity: {
    available: boolean;
    activeDays: number;
    missedDays: number;
    currentStreak: number;
    bestStreak: number;
    bestDay: string;
    weekdayAverage: WeekdayActivity[];
    days: ActivityDay[];
  };
  comparison?: ProgressComparison;
  decks: DeckPerformance[];
  attentionCards?: RawCardAttentionPayload[];
  attentionCardsStatus?: AttentionCardsStatus;
  noteTypeCatalog?: NoteTypeCatalogItem[];
  forecast: {
    available: boolean;
    tomorrow: number;
    next7Days: number;
    next30Days: number;
    activeDayBaseline: number;
    overloadRisk: Status;
    daily: ForecastDay[];
    recommendation: string;
  };
  fsrs: FsrsSummary;
  recommendations: RecommendationPanel;
  cache?: StatsCacheSummary;
  cacheDebug?: {
    parityChecked: boolean;
    reason?: string | null;
    mismatches: Array<{
      metric: string;
      legacy: number;
      cache: number;
      delta: number;
    }>;
  };
  performance?: {
    reportBuildMs?: number;
    cacheReadMs?: number;
    legacyBuildMs?: number;
  };
  today?: TodayStudyReport;
}

export type TodayStudyReport = Pick<
  StudyReport,
  "metadata" | "summary" | "kpis" | "answerDistribution" | "activity" | "comparison" | "decks" | "recommendations"
>;
