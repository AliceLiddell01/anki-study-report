import type {
  InspectionCheck,
  InspectionFieldRef,
  InspectionFieldMapping,
  InspectionNoteTypeStructure,
  InspectionProfile,
  InspectionProfileFailure,
  InspectionProfileDocument,
  InspectionProfileSummary,
  InspectionProfilesQueryRequest,
  InspectionProfilesQueryResponse,
  InspectionProfileState,
  InspectionPreviewResult,
  InspectionStoreStatus,
  InspectionSuggestion,
  InspectionUpdateRequest,
  InspectionUpdateResponse,
  InspectionValidateRequest,
  InspectionValidateResponse,
} from "../types/inspectionProfiles";

const STATES: InspectionProfileState[] = ["not_configured", "suggested", "confirmed", "needs_review", "disabled"];
const PRIORITIES = ["high", "medium", "low"];
const CHECK_KINDS = ["non_empty", "contains_audio", "contains_image", "min_text_length", "one_of_roles_non_empty", "all_roles_non_empty"];

export class InspectionProfilesApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fieldErrors?: Record<string, string>;
  readonly currentRevision?: number;

  constructor(message: string, options: { code: string; status: number; fieldErrors?: Record<string, string>; currentRevision?: number }) {
    super(message);
    this.name = "InspectionProfilesApiError";
    this.code = options.code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors;
    this.currentRevision = options.currentRevision;
  }
}

export async function fetchInspectionProfiles(
  request: InspectionProfilesQueryRequest,
  signal?: AbortSignal,
): Promise<InspectionProfilesQueryResponse> {
  return parseInspectionProfilesQueryResponse(await post("query", request, signal));
}

export async function validateInspectionProfile(
  request: InspectionValidateRequest,
  signal?: AbortSignal,
): Promise<InspectionValidateResponse> {
  return parseInspectionValidateResponse(await post("validate", request, signal));
}

export async function updateInspectionProfile(
  request: InspectionUpdateRequest,
  signal?: AbortSignal,
): Promise<InspectionUpdateResponse> {
  return parseInspectionUpdateResponse(await post("update", request, signal));
}

async function post(operation: string, request: object, signal?: AbortSignal): Promise<unknown> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/inspection-profiles/${operation}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!isRecord(payload) || !response.ok || payload.ok !== true || !exactKeys(payload, ["ok", "response"])) {
    const body = isRecord(payload) ? payload : {};
    throw new InspectionProfilesApiError("Inspection Profile request failed.", {
      code: typeof body.error === "string" ? body.error : "inspection_profiles_failed",
      status: response.status,
      fieldErrors: stringRecord(body.fieldErrors),
      currentRevision: count(body.currentRevision) ? body.currentRevision : undefined,
    });
  }
  return payload.response;
}

export function parseInspectionProfilesQueryResponse(value: unknown): InspectionProfilesQueryResponse {
  if (!isRecord(value) || !exactKeys(value, [
    "schemaVersion", "status", "store", "totalCount", "returnedCount", "limit",
    "truncated", "skippedCount", "items",
  ])) throw invalidResponse();
  if (value.schemaVersion !== 1 || (value.status !== "available" && value.status !== "partial" && value.status !== "unavailable")) throw invalidResponse();
  if (!isStoreStatus(value.store) || !count(value.totalCount) || !count(value.returnedCount) || !positive(value.limit) || value.limit > 500) throw invalidResponse();
  if (!count(value.skippedCount) || typeof value.truncated !== "boolean" || !Array.isArray(value.items)) throw invalidResponse();
  if (value.items.length !== value.returnedCount || value.returnedCount > value.limit || value.totalCount < value.returnedCount) throw invalidResponse();
  if (value.truncated !== (value.totalCount > value.returnedCount) || !value.items.every(isProfileSummary)) throw invalidResponse();
  return {
    schemaVersion: value.schemaVersion,
    status: value.status,
    store: value.store,
    totalCount: value.totalCount,
    returnedCount: value.returnedCount,
    limit: value.limit,
    truncated: value.truncated,
    skippedCount: value.skippedCount,
    items: value.items,
  };
}

export function parseInspectionValidateResponse(value: unknown): InspectionValidateResponse {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "valid", "effectiveState", "stateReason", "fieldErrors", "preview"])) throw invalidResponse();
  if ((value.schemaVersion !== 1 && value.schemaVersion !== 2) || typeof value.valid !== "boolean" || !isState(value.effectiveState)) throw invalidResponse();
  if (!isNullableReason(value.stateReason) || !isStringRecord(value.fieldErrors) || !isPreview(value.preview)) throw invalidResponse();
  if (value.valid !== (Object.keys(value.fieldErrors).length === 0)) throw invalidResponse();
  return {
    schemaVersion: value.schemaVersion,
    valid: value.valid,
    effectiveState: value.effectiveState,
    stateReason: value.stateReason,
    fieldErrors: value.fieldErrors,
    preview: value.preview,
  };
}

export function parseInspectionProfileDocument(value: unknown): InspectionProfileDocument {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "revision", "profiles"])) throw invalidResponse();
  if (value.schemaVersion !== 1 || !count(value.revision) || !Array.isArray(value.profiles) || value.profiles.length !== 1) throw invalidResponse();
  if (!isProfile(value.profiles[0])) throw invalidResponse();
  return { schemaVersion: 1, revision: value.revision, profiles: [value.profiles[0]] };
}

export function parseInspectionUpdateResponse(value: unknown): InspectionUpdateResponse {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "action", "store", "profile"])) throw invalidResponse();
  if (value.schemaVersion !== 1 || (value.action !== "save" && value.action !== "disable" && value.action !== "delete")) throw invalidResponse();
  if (!isStoreStatus(value.store) || (value.profile !== null && !isProfile(value.profile))) throw invalidResponse();
  if ((value.action === "delete") !== (value.profile === null)) throw invalidResponse();
  return { schemaVersion: value.schemaVersion, action: value.action, store: value.store, profile: value.profile };
}

function isProfileSummary(value: unknown): value is InspectionProfileSummary {
  if (!isRecord(value) || !exactKeys(value, ["structure", "effectiveState", "stateReason", "authoritative", "storedProfile", "suggestion"])) return false;
  if (!isStructure(value.structure) || !isState(value.effectiveState)) return false;
  if (!isNullableReason(value.stateReason) || typeof value.authoritative !== "boolean") return false;
  if (value.authoritative !== (value.effectiveState === "confirmed")) return false;
  return (value.storedProfile === null || isProfile(value.storedProfile)) && isSuggestion(value.suggestion);
}

function isStructure(value: unknown): value is InspectionNoteTypeStructure {
  return isRecord(value) && exactKeys(value, ["noteTypeId", "name", "kind", "fields", "templates", "fingerprint"])
    && decimalId(value.noteTypeId) && text(value.name, 160)
    && (value.kind === "standard" || value.kind === "cloze")
    && Array.isArray(value.fields) && value.fields.length <= 64 && value.fields.every(isFieldRef)
    && Array.isArray(value.templates) && value.templates.length <= 32 && value.templates.every(isTemplate)
    && isFingerprint(value.fingerprint);
}

function isTemplate(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["ordinal", "name", "frontFields", "backFields"])
    && ordinal(value.ordinal, 31) && text(value.name, 160)
    && stringArray(value.frontFields, 64, 160) && stringArray(value.backFields, 64, 160);
}

function isProfile(value: unknown): value is InspectionProfile {
  if (!isRecord(value) || !exactKeys(value, [
    "profileId", "noteTypeId", "noteTypeName", "storedState", "displayName", "expectedFingerprint",
    "appliesTo", "fieldMappings", "checks", "confirmedAt", "updatedAt",
  ])) return false;
  if (!decimalId(value.noteTypeId) || value.profileId !== `note-type-${value.noteTypeId}`) return false;
  if (!text(value.noteTypeName, 160) || !text(value.displayName, 160)) return false;
  if (!["suggested", "confirmed", "disabled"].includes(String(value.storedState)) || !isFingerprint(value.expectedFingerprint)) return false;
  if (!isRecord(value.appliesTo) || !exactKeys(value.appliesTo, ["templateOrdinals"]) || !ordinalArray(value.appliesTo.templateOrdinals, 16, 31)) return false;
  if (!Array.isArray(value.fieldMappings) || value.fieldMappings.length > 32 || !value.fieldMappings.every(isMapping)) return false;
  if (!Array.isArray(value.checks) || value.checks.length > 32 || !value.checks.every(isCheck)) return false;
  const roles = value.fieldMappings.map((item) => item.role);
  const refs = value.fieldMappings.flatMap((item) => item.fields.map((field) => `${field.ordinal}:${field.name}`));
  const checkIds = value.checks.map((item) => item.checkId);
  if (new Set(roles).size !== roles.length || new Set(refs).size !== refs.length || new Set(checkIds).size !== checkIds.length) return false;
  if (value.checks.some((item) => item.roles.some((role) => !roles.includes(role)))) return false;
  if (!timestamp(value.updatedAt) || (value.confirmedAt !== null && !timestamp(value.confirmedAt))) return false;
  return value.storedState !== "confirmed" || value.confirmedAt !== null;
}

function isMapping(value: unknown): value is InspectionFieldMapping {
  return isRecord(value) && exactKeys(value, ["role", "fields"])
    && slug(value.role) && Array.isArray(value.fields) && value.fields.length > 0
    && value.fields.length <= 16 && value.fields.every(isFieldRef);
}

function isCheck(value: unknown): value is InspectionCheck {
  if (!isRecord(value) || typeof value.kind !== "string" || !CHECK_KINDS.includes(value.kind)) return false;
  const common = slugId(value.checkId, 80) && slugArray(value.roles, 16) && PRIORITIES.includes(String(value.priority));
  if (!common) return false;
  if (["non_empty", "contains_audio", "contains_image"].includes(value.kind)) {
    return exactKeys(value, ["checkId", "kind", "roles", "mode", "priority"])
      && (value.mode === "any" || value.mode === "all");
  }
  if (value.kind === "min_text_length") {
    return exactKeys(value, ["checkId", "kind", "roles", "mode", "priority", "minLength"])
      && (value.mode === "any" || value.mode === "all")
      && positive(value.minLength) && value.minLength <= 10_000;
  }
  return exactKeys(value, ["checkId", "kind", "roles", "priority"]);
}

function isSuggestion(value: unknown): value is InspectionSuggestion {
  return isRecord(value) && exactKeys(value, ["detectedKind", "confidence", "fieldMappings", "checks", "warnings", "unresolvedFields"])
    && text(value.detectedKind, 40) && confidence(value.confidence)
    && Array.isArray(value.fieldMappings) && value.fieldMappings.length <= 32 && value.fieldMappings.every(isSuggestedMapping)
    && Array.isArray(value.checks) && value.checks.length <= 32 && value.checks.every(isCheck)
    && stringArray(value.warnings, 32, 80)
    && Array.isArray(value.unresolvedFields) && value.unresolvedFields.length <= 64 && value.unresolvedFields.every(isFieldRef);
}

function isSuggestedMapping(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["role", "fields", "confidence"])
    && slug(value.role) && Array.isArray(value.fields) && value.fields.length > 0
    && value.fields.length <= 16 && value.fields.every(isFieldRef) && confidence(value.confidence);
}

function isPreview(value: unknown): value is InspectionPreviewResult {
  if (!isRecord(value) || !exactKeys(value, [
    "status", "requestedCount", "evaluatedCount", "missingCardIds", "failureCount", "truncated", "items",
  ])) return false;
  if (value.status !== "available" && value.status !== "unavailable") return false;
  if (!count(value.requestedCount) || value.requestedCount > 20 || !count(value.evaluatedCount) || value.evaluatedCount > 20) return false;
  if (!decimalIdArray(value.missingCardIds, 20) || !count(value.failureCount) || typeof value.truncated !== "boolean" || !Array.isArray(value.items)) return false;
  return value.items.length === value.evaluatedCount && value.items.length <= 20 && value.items.every(isPreviewItem)
    && value.failureCount === value.items.reduce((sum, item) => sum + Number(isRecord(item) ? item.failureCount : 0), 0);
}

function isPreviewItem(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["cardId", "noteId", "failureCount", "failures"])
    && decimalId(value.cardId) && decimalId(value.noteId) && count(value.failureCount)
    && Array.isArray(value.failures) && value.failures.length <= 32
    && value.failures.length === value.failureCount && value.failures.every(isFailure);
}

function isFailure(value: unknown): value is InspectionProfileFailure {
  if (!isRecord(value) || !exactKeys(value, [
    "profileId", "noteTypeId", "checkId", "checkKind", "scope", "priority", "targetRoles",
    "mappedFields", "evidence", "profileRevision", "fingerprint", "affectedSiblingCount", "templateOrdinals",
  ])) return false;
  return /^note-type-[1-9]\d{0,18}$/.test(String(value.profileId)) && decimalId(value.noteTypeId)
    && slugId(value.checkId, 80) && CHECK_KINDS.includes(String(value.checkKind)) && value.scope === "note"
    && PRIORITIES.includes(String(value.priority)) && slugArray(value.targetRoles, 16)
    && Array.isArray(value.mappedFields) && value.mappedFields.length <= 16 && value.mappedFields.every(isFieldRef)
    && isFailureEvidence(value.evidence) && count(value.profileRevision)
    && typeof value.fingerprint === "string" && /^[a-f0-9]{64}$/.test(value.fingerprint)
    && positive(value.affectedSiblingCount) && ordinalArray(value.templateOrdinals, 16, 31);
}

function isFailureEvidence(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["expectedCondition", "actualTextLength", "expectedTextLength", "marker", "markerPresent"])
    && text(value.expectedCondition, 80)
    && nullableCount(value.actualTextLength) && nullableCount(value.expectedTextLength)
    && (value.marker === null || value.marker === "audio" || value.marker === "image")
    && (value.markerPresent === null || value.markerPresent === false);
}

function isStoreStatus(value: unknown): value is InspectionStoreStatus {
  return isRecord(value) && exactKeys(value, ["status", "revision", "profileCount", "errorCode", "quarantined"])
    && ["empty", "available", "corrupt", "future_schema", "unavailable"].includes(String(value.status))
    && count(value.revision) && count(value.profileCount) && value.profileCount <= 500
    && (value.errorCode === null || slugId(value.errorCode, 80)) && typeof value.quarantined === "boolean";
}

function isFingerprint(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["algorithm", "value"])
    && value.algorithm === "sha256" && typeof value.value === "string" && /^[a-f0-9]{64}$/.test(value.value);
}

function isFieldRef(value: unknown): value is InspectionFieldRef {
  return isRecord(value) && exactKeys(value, ["ordinal", "name"])
    && ordinal(value.ordinal, 63) && text(value.name, 160);
}

function timestamp(value: unknown): value is string {
  return typeof value === "string" && value.length <= 40
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(value)
    && Number.isFinite(Date.parse(value));
}

function decimalId(value: unknown): value is string {
  return typeof value === "string" && /^[1-9]\d{0,18}$/.test(value)
    && (value.length < 19 || value <= "9223372036854775807");
}

function decimalIdArray(value: unknown, maximum: number): boolean {
  return Array.isArray(value) && value.length <= maximum && value.every(decimalId) && new Set(value).size === value.length;
}

function ordinalArray(value: unknown, maximum: number, maxOrdinal: number): boolean {
  return Array.isArray(value) && value.length <= maximum
    && value.every((item) => ordinal(item, maxOrdinal)) && new Set(value).size === value.length;
}

function ordinal(value: unknown, maximum: number): value is number {
  return count(value) && value <= maximum;
}

function nullableCount(value: unknown): boolean { return value === null || count(value); }
function confidence(value: unknown): boolean { return finite(value) && value >= 0 && value <= 1; }
function positive(value: unknown): value is number { return count(value) && value > 0; }
function count(value: unknown): value is number { return finite(value) && Number.isInteger(value) && value >= 0 && value <= Number.MAX_SAFE_INTEGER; }
function finite(value: unknown): value is number { return typeof value === "number" && Number.isFinite(value); }
function text(value: unknown, maximum: number): value is string { return typeof value === "string" && value.trim().length > 0 && value.length <= maximum; }
function slug(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9_]{0,39}$/.test(value); }
function slugId(value: unknown, maximum: number): value is string { return typeof value === "string" && value.length <= maximum && /^[a-z][a-z0-9_-]*$/.test(value); }
function slugArray(value: unknown, maximum: number): boolean { return Array.isArray(value) && value.length > 0 && value.length <= maximum && value.every(slug) && new Set(value).size === value.length; }
function stringArray(value: unknown, maximum: number, maxText: number): boolean { return Array.isArray(value) && value.length <= maximum && value.every((item) => typeof item === "string" && item.length <= maxText); }
function isState(value: unknown): value is InspectionProfileState { return STATES.includes(value as InspectionProfileState); }
function isNullableReason(value: unknown): value is string | null { return value === null || slugId(value, 80); }
function isStringRecord(value: unknown): value is Record<string, string> { return isRecord(value) && Object.values(value).every((item) => typeof item === "string" && item.length <= 240); }
function stringRecord(value: unknown): Record<string, string> | undefined { return isStringRecord(value) ? value : undefined; }

function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const expected = [...keys].sort();
  const actual = Object.keys(value).sort();
  return expected.length === actual.length && expected.every((key, index) => actual[index] === key);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function invalidResponse(): InspectionProfilesApiError {
  return new InspectionProfilesApiError("Inspection Profiles returned an invalid response.", {
    code: "invalid_inspection_profiles_response",
    status: 200,
  });
}
