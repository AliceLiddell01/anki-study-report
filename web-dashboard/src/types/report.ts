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

export type DeckHealthConfidence = "sufficient" | "preliminary" | "insufficient";

export interface DeckHubMetrics {
  reviews: number;
  newCards: number;
  passCount: number;
  failCount: number;
  hardCount: number;
  easyCount: number;
  passRate: number | null;
  failRate: number | null;
  averageAnswerSeconds: number | null;
  studySeconds: number;
  activeDays: number | null;
  directCardCount: number;
}

export interface DeckHubIssue {
  deckId: number;
  fullName: string;
  shortName: string;
  status: Status;
  reason: string;
}

export interface DeckHubNode {
  deckId: number;
  fullName: string;
  shortName: string;
  parentId: number | null;
  depth: number;
  childIds: number[];
  filtered: false;
  structuralOnly: boolean;
  directMetrics: DeckHubMetrics;
  subtreeMetrics: DeckHubMetrics;
  aggregateHealth: Status;
  dataConfidence: DeckHealthConfidence;
  descendantIssueCount: number;
  descendantIssues: DeckHubIssue[];
  reasons: string[];
  recommendations: string[];
  actions: {
    includeDescendants: boolean;
    directOnly: boolean;
  };
}

export interface DeckHubModel {
  schemaVersion: number;
  scope: {
    kind: "all" | "selected";
    selectedDeckIds: number[];
    includeChildDecks: boolean;
  };
  summary: {
    totalDecks: number;
    attentionDecks: number;
    dangerDecks: number;
    groupsWithDescendantIssues: number;
    aggregatePassRate: number | null;
    filteredDecksExcluded: number;
  };
  nodes: Record<string, DeckHubNode>;
  rootIds: number[];
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
  fallbackReason?: string | null;
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
  deckHub?: DeckHubModel;
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
  profile?: ProfileModel;
  activityHub?: ActivityHubModel;
  statisticsHub?: StatisticsHubModel;
}

export type StatisticsPeriod = "7d" | "30d" | "90d" | "1y" | "all";
export type StatisticsGranularity = "auto" | "day" | "week" | "month";
export type StatisticsConfidence = "insufficient" | "preliminary" | "sufficient";
export type StatisticsScope =
  | { kind: "dashboard" }
  | { kind: "all_collection" }
  | { kind: "single_deck"; deckId: number; mode: "subtree" | "direct" };

export interface StatisticsQuery {
  scope: StatisticsScope;
  period: StatisticsPeriod;
  granularity: StatisticsGranularity;
  comparison: boolean;
  resolvedGranularity?: Exclude<StatisticsGranularity, "auto">;
}

export interface StatisticsRetention {
  overall: number | null;
  young: number | null;
  mature: number | null;
  youngPass: number;
  youngFail: number;
  maturePass: number;
  matureFail: number;
  sampleSize: number;
}

export interface StatisticsSeriesPoint {
  key: string;
  label: string;
  reviews: number;
  studySeconds?: number | null;
  introducedCards?: number;
  activeDays?: number;
  successRate?: number | null;
  averageAnswerSeconds?: number | null;
  pass?: number;
  fail?: number;
  ratings?: { again: number; hard: number; good: number; easy: number };
  trueRetention?: StatisticsRetention;
}

export interface StatisticsResult {
  schemaVersion: number;
  query: StatisticsQuery & { resolvedGranularity: Exclude<StatisticsGranularity, "auto"> };
  scope: { kind: StatisticsScope["kind"]; deckIds: number[]; label: string; deckId?: number; mode?: "subtree" | "direct" };
  coverage: {
    dataFrom: string | null;
    dataTo: string | null;
    requestedFrom: string | null;
    requestedTo: string;
    coverage: "full" | "partial" | "unavailable";
    sampleSize: number;
    activeDays: number;
    studyTimeSource: "revlog_estimate" | null;
    limitations: string[];
    calculationVersion: string;
  };
  confidencePolicy: { insufficientBelow: number; preliminaryBelow: number; deckRowMinimum: number; trendMinimumActiveDays: number };
  overview: {
    kpis: { reviews: number; studySeconds: number | null; successRate: number | null; introducedCards: number; activeDays: number; averageAnswerSeconds: number | null };
    comparison: Record<string, unknown> & { status: "available" | "partial" | "unavailable"; reason?: string | null };
    series: StatisticsSeriesPoint[];
    insights: Array<{ type: string; direction: "increase" | "decrease" | "same"; value: number; unit: string }>;
    confidence: StatisticsConfidence;
  };
  quality: {
    series: StatisticsSeriesPoint[];
    ratings: { again: number; hard: number; good: number; easy: number };
    pass: number;
    fail: number;
    successRate: number | null;
    trueRetention: StatisticsRetention;
    confidence: StatisticsConfidence;
  };
  load: {
    past: StatisticsSeriesPoint[];
    averageActiveDayReviews: number | null;
    dailyLoad: number;
    overdue: number;
    futureDue: Array<{ dayOffset: number; learning: number; review: number; relearning: number; total: number }>;
    assumptionCode: string;
  };
  progress: {
    currentStates: Record<"unseen" | "learning" | "young" | "mature" | "suspended" | "buried", number>;
    totalCards: number;
    totalNotes: number;
    introducedSeries: StatisticsSeriesPoint[];
    introducedCards: number;
    historicalStateSeriesAvailable: false;
  };
  deckComparison: {
    mode: "non_overlapping_roots";
    limit: number;
    rows: Array<{
      deckId: number;
      fullName: string;
      mode: "subtree";
      reviews: number;
      successRate: number | null;
      averageAnswerSeconds: number | null;
      studySeconds: number;
      introducedCards: number;
      confidence: StatisticsConfidence;
      periodDelta: {
        reviews: { current: number; previous: number; delta: number | null; direction: string };
        successRate: { current: number | null; previous: number | null; delta: number | null; direction: string };
      } | null;
    }>;
  };
  limitations: string[];
  calculationVersion: string;
  bounds: { current: { start: string | null; end: string }; previous: { start: string | null; end: string } | null };
}

export interface StatisticsHubModel {
  schemaVersion: number;
  generatedAt: string;
  availability: "available" | "building" | "partial" | "unavailable";
  coverage: StatisticsResult["coverage"];
  capabilities: { core: "available"; fsrs: "available" | "unavailable"; advanced: "future_not_exposed"; providers: []; nativeStatsAction: boolean };
  fsrs: FsrsCapability;
  metricDefinitionsVersion: string;
  defaultQuery: StatisticsQuery;
  initialResult: StatisticsResult;
  scope: StatisticsResult["scope"];
  deckOptions: Array<{ deckId: number; fullName: string; parentId: number | null }>;
}

export type FsrsAvailability = "enabled" | "disabled" | "insufficient_data" | "partial_coverage" | "mixed_configuration" | "unavailable" | "error";
export type FsrsOperation = "overview" | "memory" | "calibration" | "steps" | "simulate";
export type FsrsScope =
  | { kind: "dashboard" | "all_collection" }
  | { kind: "configuration"; configurationId: string }
  | { kind: "deck"; deckId: number };

export interface FsrsConfigurationGroup {
  id: string;
  presetId: number;
  presetName: string;
  parameterFingerprint: string;
  parameterVersion: string;
  defaultDesiredRetention: number | null;
  deckDesiredRetentionOverrides: Array<{ deckId: number; desiredRetention: number }>;
  learningStepsSeconds: number[];
  relearningStepsSeconds: number[];
  shortTermMode: "fsrs" | "configured_steps";
  deckIds: number[];
  deckNames: string[];
  cardCount: number;
  reviewedCardCount: number;
  qualifyingReviewCount: number;
  coverage: string;
  dataSufficiency: "insufficient" | "preliminary" | "sufficient";
}

export interface FsrsCapability {
  schemaVersion: number;
  enabled: boolean;
  availability: FsrsAvailability;
  configurationCount: number;
  reviewedCardCount: number;
  qualifyingReviewCount: number;
  mixedConfiguration: boolean;
  defaultConfigurationId: string | null;
  supportedFeatures: string[];
  limitations: string[];
  configurations: FsrsConfigurationGroup[];
}

export interface FsrsQuery {
  operation: FsrsOperation;
  scope: FsrsScope;
  period?: "30d" | "90d" | "180d" | "1y";
  simulation?: { desiredRetention: number; horizonDays: 90 | 180 | 365; additionalNewCards: number; newCardsPerDay: number; maximumReviewsPerDay: number };
}

export interface FsrsResponse<T = Record<string, unknown>> {
  schemaVersion: number;
  operation: FsrsOperation;
  query: FsrsQuery;
  result: T;
  calculationVersion: string;
}

export type ActivityAvailability = "active" | "inactive" | "unavailable";
export type ActivityPeriod = "30d" | "90d" | "6m" | "1y";
export type ActivityMetric = "reviews" | "study_time" | "new_cards" | "success_rate";

export interface ActivityDeckDay {
  id: number;
  name: string;
  reviews: number;
  pass: number;
  fail: number;
  successRate: number | null;
}

export interface ActivityHubDay {
  date: string;
  availability: ActivityAvailability;
  reviews?: number;
  newCards?: number;
  pass?: number;
  fail?: number;
  successRate?: number | null;
  studySeconds?: number | null;
  activeDeckCount?: number;
  decks?: ActivityDeckDay[];
}

export interface ActivityHighlight {
  id: string;
  type: "return_after_break" | "streak_milestone" | "new_activity_record";
  inactiveDays?: number;
  days?: number;
  reviews?: number;
  previousMax?: number;
}

export interface ActivityFeedDay {
  id: string;
  type: "daily_summary";
  date: string;
  highlights: ActivityHighlight[];
}

export interface ActivityWeekSummary {
  id: string;
  type: "weekly_summary";
  weekStart: string;
  weekEnd: string;
  activeDays: number;
  reviews: number;
  studySeconds: number | null;
  successRate: number | null;
  comparison: {
    reviewsPercentChange: number;
    direction: "more" | "less" | "same";
  } | null;
}

export interface ActivityHubModel {
  schemaVersion: number;
  today: string;
  scope: {
    kind: "all" | "selected";
    selectedDeckIds: number[];
    includeChildDecks: boolean;
  };
  bounds: {
    start: string;
    end: string;
    availableFrom: string | null;
    maxDays: number;
  };
  periods: Record<ActivityPeriod, { start: string; end: string; label: string }>;
  metrics: { studyTimeSource: "revlog_estimate" | "session_tracker" | "study_time_stats" | null };
  overview: { currentStreak: number; bestStreak: number };
  days: ActivityHubDay[];
  feed: {
    days: ActivityFeedDay[];
    weeks: ActivityWeekSummary[];
    pageSize: number;
  };
}

export type ProfileDeckSort = "name" | "reviews" | "active_days";

export interface ProfileActivityDay {
  date: string;
  reviews: number;
  studySeconds: number | null;
  passRate: number | null;
}

export interface ProfileDeckOverview {
  id: number;
  name: string;
  totalReviews: number;
  activeDays: number;
}

export interface ProfileModel {
  identity: {
    ankiProfileName: string | null;
    displayName: string;
    initials: string;
    label: "Локальный профиль" | string;
  };
  studyHistory: {
    detectedStartedOn: string | null;
    customStartedOn: string | null;
    displayedStartedOn: string | null;
    statsAvailableFrom: string | null;
    totalReviews: number;
    activeDays: number;
    currentStreak: number;
    bestStreak: number;
    studyTimeSeconds: number | null;
    studyTimeSource: "revlog_estimate" | "session_tracker" | "study_time_stats" | null;
    averagePassRate: number | null;
  };
  activity: {
    days: ProfileActivityDay[];
    recentActiveDays: ProfileActivityDay[];
    rangeStart: string | null;
    rangeEnd: string | null;
  };
  decks: {
    overview: ProfileDeckOverview[];
    total: number;
    limit: number;
    aggregation: "canonical_current_deck" | string;
  };
  preferences: {
    customStudyStartedOn: string | null;
    deckOverviewSort: ProfileDeckSort;
  };
}

export type TodayStudyReport = Pick<
  StudyReport,
  "metadata" | "summary" | "kpis" | "answerDistribution" | "activity" | "comparison" | "decks" | "recommendations"
>;
