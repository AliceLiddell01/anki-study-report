export type DashboardScope = "all" | "selected";
export type ReportPeriod =
  | "today"
  | "yesterday"
  | "since_last_report"
  | "last_7_days"
  | "last_30_days"
  | "custom"
  | "all_time";
export type ReportScope = "all" | "current" | "selected";
export type ReportDetailLevel = "compact" | "normal" | "full";
export type AnswerMode = "auto" | "standard" | "pass_fail";

export interface DeckOption {
  id: number;
  name: string;
}

export interface PublicSettings {
  dashboard: {
    scope: DashboardScope;
    selectedDeckIds: number[];
    selectedDeckNames: string[];
    includeChildDecks: boolean;
  };
  report: {
    defaultPeriod: ReportPeriod;
    customStartDate: string;
    customEndDate: string;
    scope: ReportScope;
    selectedDeckIds: number[];
    includeChildDecks: boolean;
    detailLevel: ReportDetailLevel;
    answerMode: AnswerMode;
  };
  data: {
    trackReviewerSessions: boolean;
    sessionIdleTimeoutSeconds: number;
    sessionGapCapSeconds: number;
    useStudyTimeStats: boolean;
    useStatsCacheForReport: boolean;
  };
  server: {
    autoStart: boolean;
    port: number;
    idleTimeoutSeconds: number;
  };
}

export type SettingsSectionName = keyof PublicSettings;

export interface SettingsResponse {
  ok: boolean;
  settings: PublicSettings;
  deckOptions: DeckOption[];
  message?: string;
  fieldErrors?: Record<string, string>;
  restartRequired?: boolean;
  report?: unknown;
  reportRefreshError?: string;
}
