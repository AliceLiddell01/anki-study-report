import type { CardDisplayIdentity } from "./search";

export type TriageDataset = "automatic" | "search_workset";
export type TriagePriority = "high" | "medium" | "low";
export type TriageReasonFamily = "learning" | "content" | "system" | "manual";
export type TriageReasonScope = "card" | "note";
export type TriageSource = "attention" | "signals" | "search_workset" | "profile_checks";
export type TriageAvailability = "available" | "missing";
export type TriageResponseStatus = "available" | "partial" | "unavailable";
export type TriageSourceAvailability = "available" | "empty" | "partial" | "unavailable" | "error" | "not_applicable";
export type TriageCardState = "new" | "learning" | "review" | "due" | "suspended" | "buried";

export type TriageEvidence =
  | { kind: "leech_state"; lapses: number }
  | { kind: "review_counts"; againCount: number; periodStartMs: number; periodEndMs: number }
  | { kind: "pass_rate"; passRate: number; periodStartMs: number; periodEndMs: number }
  | { kind: "answer_time"; averageAnswerSeconds: number; periodStartMs: number; periodEndMs: number }
  | { kind: "signal_evidence"; severity: "warning" | "critical"; againCount: number; reviewCount: number; windowDays: number; detectorVersion: string }
  | {
      kind: "profile_check";
      profileId: string;
      checkId: string;
      checkKind: "non_empty" | "contains_audio" | "contains_image" | "min_text_length" | "one_of_roles_non_empty" | "all_roles_non_empty";
      roles: string[];
      fields: { ordinal: number; name: string }[];
      expectedCondition: string;
      actualTextLength: number | null;
      expectedTextLength: number | null;
      marker: "audio" | "image" | null;
      markerPresent: false | null;
      profileRevision: number;
      fingerprint: string;
      affectedSiblingCount: number;
      templateOrdinals: number[];
    };

export interface TriageReason {
  reasonId: string;
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

export interface TriageContentSourceStatus extends TriageSourceStatus {
  scannedNoteCount: number;
  nextCursor: string | null;
}

export interface TriageItem extends CardDisplayIdentity {
  itemId: string;
  availability: TriageAvailability;
  cardId: string;
  noteId: string | null;
  deck: { deckId: string | null; name: string };
  noteType: { noteTypeId: string | null; name: string };
  template: { ordinal: number | null; name: string };
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
  | { schemaVersion: 4; dataset: "automatic"; scope: TriageScope; limit: number; contentCursor: string | null; cardIds?: never }
  | { schemaVersion: 4; dataset: "search_workset"; cardIds: string[]; scope: TriageScope; limit: number; contentCursor?: never };

export interface TriageQueryResponse {
  schemaVersion: 4;
  dataset: TriageDataset;
  status: TriageResponseStatus;
  generatedAtMs: number;
  totalCount: number;
  returnedCount: number;
  limit: number;
  truncated: boolean;
  sourceStatus: {
    learningCandidates: TriageSourceStatus;
    contentCandidates: TriageContentSourceStatus;
    signals: TriageSourceStatus;
    searchResolver: TriageSourceStatus;
    profileChecks: TriageSourceStatus;
  };
  contentChecks: {
    status: "available" | "no_confirmed_profiles" | "profiles_need_review" | "disabled" | "partial" | "unavailable";
    confirmedProfileCount: number;
    needsReviewProfileCount: number;
    disabledProfileCount: number;
    suggestedProfileCount: number;
    scannedNoteCount: number;
    evaluatedNoteCount: number;
    failedCheckCount: number;
    skippedCount: number;
    truncated: boolean;
    nextCursor: string | null;
    errorCode: string | null;
  };
  items: TriageItem[];
}
