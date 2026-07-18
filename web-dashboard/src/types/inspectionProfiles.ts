export type InspectionProfileState = "not_configured" | "suggested" | "confirmed" | "needs_review" | "disabled";
export type InspectionProfileStoredState = "suggested" | "confirmed" | "disabled";
export type InspectionProfilePriority = "high" | "medium" | "low";
export type InspectionProfileCheckKind =
  | "non_empty"
  | "contains_audio"
  | "contains_image"
  | "min_text_length"
  | "one_of_roles_non_empty"
  | "all_roles_non_empty";

export interface InspectionFieldRef { ordinal: number; name: string }
export interface InspectionFieldMapping { role: string; fields: InspectionFieldRef[] }

interface InspectionCheckBase {
  checkId: string;
  roles: string[];
  priority: InspectionProfilePriority;
}

export type InspectionCheck =
  | (InspectionCheckBase & { kind: "non_empty" | "contains_audio" | "contains_image"; mode: "any" | "all" })
  | (InspectionCheckBase & { kind: "min_text_length"; mode: "any" | "all"; minLength: number })
  | (InspectionCheckBase & { kind: "one_of_roles_non_empty" | "all_roles_non_empty" });

export interface InspectionFingerprint { algorithm: "sha256"; value: string }

export interface InspectionProfile {
  profileId: string;
  noteTypeId: string;
  noteTypeName: string;
  storedState: InspectionProfileStoredState;
  displayName: string;
  expectedFingerprint: InspectionFingerprint;
  appliesTo: { templateOrdinals: number[] };
  fieldMappings: InspectionFieldMapping[];
  checks: InspectionCheck[];
  confirmedAt: string | null;
  updatedAt: string;
}

export interface InspectionNoteTypeStructure {
  noteTypeId: string;
  name: string;
  kind: "standard" | "cloze";
  fields: InspectionFieldRef[];
  templates: { ordinal: number; name: string; frontFields: string[]; backFields: string[] }[];
  fingerprint: InspectionFingerprint;
}

export interface InspectionSuggestion {
  detectedKind: string;
  confidence: number;
  fieldMappings: { role: string; fields: InspectionFieldRef[]; confidence: number }[];
  checks: InspectionCheck[];
  warnings: string[];
  unresolvedFields: InspectionFieldRef[];
}

export interface InspectionProfileSummary {
  structure: InspectionNoteTypeStructure;
  effectiveState: InspectionProfileState;
  stateReason: string | null;
  authoritative: boolean;
  storedProfile: InspectionProfile | null;
  suggestion: InspectionSuggestion;
}

export interface InspectionStoreStatus {
  status: "empty" | "available" | "corrupt" | "future_schema" | "unavailable";
  revision: number;
  profileCount: number;
  errorCode: string | null;
  quarantined: boolean;
}

export interface InspectionProfilesQueryRequest {
  schemaVersion: 1;
  noteTypeIds: string[];
  limit: number;
}

export interface InspectionProfilesQueryResponse {
  schemaVersion: 1;
  status: "available" | "partial" | "unavailable";
  store: InspectionStoreStatus;
  totalCount: number;
  returnedCount: number;
  limit: number;
  truncated: boolean;
  skippedCount: number;
  items: InspectionProfileSummary[];
}

export interface InspectionProfileFailure {
  profileId: string;
  noteTypeId: string;
  checkId: string;
  checkKind: InspectionProfileCheckKind;
  scope: "note";
  priority: InspectionProfilePriority;
  targetRoles: string[];
  mappedFields: InspectionFieldRef[];
  evidence: {
    expectedCondition: string;
    actualTextLength: number | null;
    expectedTextLength: number | null;
    marker: "audio" | "image" | null;
    markerPresent: false | null;
  };
  profileRevision: number;
  fingerprint: string;
  affectedSiblingCount: number;
  templateOrdinals: number[];
}

export interface InspectionPreviewResult {
  status: "available" | "unavailable";
  requestedCount: number;
  evaluatedCount: number;
  missingCardIds: string[];
  failureCount: number;
  truncated: boolean;
  items: { cardId: string; noteId: string; failureCount: number; failures: InspectionProfileFailure[] }[];
}

export type InspectionValidateRequest =
  | { schemaVersion: 1; profile: InspectionProfile; cardIds: string[] }
  | { schemaVersion: 2; profile: InspectionProfile; preview: { mode: "sample"; limit: number } };
export interface InspectionValidateResponse {
  schemaVersion: 1 | 2;
  valid: boolean;
  effectiveState: InspectionProfileState;
  stateReason: string | null;
  fieldErrors: Record<string, string>;
  preview: InspectionPreviewResult;
}

export interface InspectionProfileDocument {
  schemaVersion: 1;
  revision: number;
  profiles: [InspectionProfile];
}

export type InspectionUpdateRequest =
  | { schemaVersion: 1; action: "save"; expectedRevision: number; targetState: "suggested" | "confirmed"; profile: InspectionProfile }
  | { schemaVersion: 1; action: "disable" | "delete"; expectedRevision: number; noteTypeId: string };

export interface InspectionUpdateResponse {
  schemaVersion: 1;
  action: "save" | "disable" | "delete";
  store: InspectionStoreStatus;
  profile: InspectionProfile | null;
}
