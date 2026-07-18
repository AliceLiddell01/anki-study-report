export type TriageDataset = "automatic" | "search_workset";
export type TriagePriority = "high" | "medium" | "low";
export type TriageReasonFamily = "learning" | "content" | "system" | "manual";
export type TriageReasonScope = "card" | "note";
export type TriageSource = "attention" | "signals" | "search_workset";
export type TriageAvailability = "available" | "missing";
export type TriageResponseStatus = "available" | "partial" | "unavailable";
export type TriageSourceAvailability = "available" | "empty" | "unavailable" | "error";
export type TriageCardState = "new" | "learning" | "review" | "due" | "suspended" | "buried";

export type TriageEvidence =
  | { kind: "leech_state"; lapses: number }
  | { kind: "review_counts"; againCount: number; periodStartMs: number; periodEndMs: number }
  | { kind: "pass_rate"; passRate: number; periodStartMs: number; periodEndMs: number }
  | { kind: "answer_time"; averageAnswerSeconds: number; periodStartMs: number; periodEndMs: number }
  | {
      kind: "signal_evidence";
      severity: "warning" | "critical";
      againCount: number;
      reviewCount: number;
      windowDays: number;
      detectorVersion: string;
    };

export interface TriageReason {
  code: string;
  family: TriageReasonFamily;
  scope: TriageReasonScope;
  priority: TriagePriority;
  sources: TriageSource[];
  evidence: TriageEvidence[];
  detectedAtMs: number | null;
}

export interface TriageSourceStatus {
  status: TriageSourceAvailability;
  itemCount: number;
  skippedCount: number;
  truncated: boolean;
  errorCode: string | null;
}

export interface TriageItem {
  itemId: string;
  availability: TriageAvailability;
  cardId: string;
  noteId: string | null;
  deck: { deckId: string | null; name: string };
  noteType: { noteTypeId: string | null; name: string };
  template: { ordinal: number | null; name: string };
  primaryText: string;
  priority: TriagePriority | null;
  primaryReasonCode: string | null;
  reasons: TriageReason[];
  sources: TriageSource[];
  cardState: {
    state: TriageCardState | null;
    suspended: boolean | null;
    buried: boolean | null;
    flag: number | null;
  };
  inspect: { mode: "cards"; cardId: string } | null;
}

export interface TriageScope {
  periodStartMs: number;
  periodEndMs: number;
  deckIds: string[];
}

export type TriageQueryRequest =
  | { schemaVersion: 1; dataset: "automatic"; scope: TriageScope; limit: number; cardIds?: never }
  | { schemaVersion: 1; dataset: "search_workset"; cardIds: string[]; scope: TriageScope; limit: number };

export interface TriageQueryResponse {
  schemaVersion: 1;
  dataset: TriageDataset;
  status: TriageResponseStatus;
  generatedAtMs: number;
  totalCount: number;
  returnedCount: number;
  limit: number;
  truncated: boolean;
  sourceStatus: {
    attention: TriageSourceStatus;
    signals: TriageSourceStatus;
    searchResolver: TriageSourceStatus;
  };
  contentChecks: { status: "profiles_not_available" };
  items: TriageItem[];
}
