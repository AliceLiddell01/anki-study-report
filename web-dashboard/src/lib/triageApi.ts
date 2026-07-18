import type {
  TriageCardState,
  TriageDataset,
  TriageEvidence,
  TriageItem,
  TriagePriority,
  TriageQueryRequest,
  TriageQueryResponse,
  TriageReason,
  TriageSource,
  TriageSourceStatus,
} from "../types/triage";

const SOURCES: TriageSource[] = ["attention", "signals", "search_workset"];
const PRIORITIES: TriagePriority[] = ["high", "medium", "low"];
const CARD_STATES: TriageCardState[] = ["new", "learning", "review", "due", "suspended", "buried"];
const REASON_CODES = ["learning.leech", "learning.repeated_again", "learning.low_pass_rate", "learning.slow_answer"];
const MAX_SAFE_TIMESTAMP = Number.MAX_SAFE_INTEGER;

export class TriageApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fieldErrors?: Record<string, string>;

  constructor(message: string, options: { code: string; status: number; fieldErrors?: Record<string, string> }) {
    super(message);
    this.name = "TriageApiError";
    this.code = options.code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors;
  }
}

export async function fetchTriageQuery(
  request: TriageQueryRequest,
  signal?: AbortSignal,
): Promise<TriageQueryResponse> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/triage/query?token=${encodeURIComponent(token)}`, {
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
  if (!isRecord(payload)) {
    throw new TriageApiError("Triage request failed.", { code: "triage_failed", status: response.status });
  }
  if (!response.ok || payload.ok !== true || !("response" in payload)) {
    throw new TriageApiError(
      typeof payload.message === "string" ? payload.message : "Triage request failed.",
      {
        code: typeof payload.error === "string" ? payload.error : "triage_failed",
        status: response.status,
        fieldErrors: stringRecord(payload.fieldErrors),
      },
    );
  }
  if (!exactKeys(payload, ["ok", "response"])) {
    throw invalidResponseError();
  }
  return parseTriageQueryResponse(payload.response);
}

export function parseTriageQueryResponse(value: unknown): TriageQueryResponse {
  if (!isTriageQueryResponse(value)) {
    throw invalidResponseError();
  }
  return value;
}

function isTriageQueryResponse(value: unknown): value is TriageQueryResponse {
  if (!isRecord(value) || !exactKeys(value, [
    "schemaVersion", "dataset", "status", "generatedAtMs", "totalCount", "returnedCount",
    "limit", "truncated", "sourceStatus", "contentChecks", "items",
  ])) return false;
  const dataset = value.dataset;
  if (value.schemaVersion !== 1 || !isDataset(dataset)) return false;
  if (!new Set(["available", "partial", "unavailable"]).has(String(value.status))) return false;
  if (!safeTimestamp(value.generatedAtMs) || !count(value.totalCount) || !count(value.returnedCount)) return false;
  const maxLimit = dataset === "automatic" ? 100 : 200;
  if (!positiveInteger(value.limit) || value.limit > maxLimit || !Array.isArray(value.items)) return false;
  if (value.returnedCount !== value.items.length || value.returnedCount > value.limit || value.totalCount < value.returnedCount) return false;
  if (typeof value.truncated !== "boolean" || value.truncated !== (value.totalCount > value.returnedCount)) return false;
  if (!isSourceStatusMap(value.sourceStatus) || !isContentChecks(value.contentChecks)) return false;
  return value.items.every((item) => isTriageItem(item, dataset));
}

function isTriageItem(value: unknown, dataset: TriageDataset): value is TriageItem {
  if (!isRecord(value) || !exactKeys(value, [
    "itemId", "availability", "cardId", "noteId", "deck", "noteType", "template", "primaryText",
    "priority", "primaryReasonCode", "reasons", "sources", "cardState", "inspect",
  ])) return false;
  if (!decimalId(value.cardId) || value.itemId !== `card:${value.cardId}`) return false;
  if (value.availability !== "available" && value.availability !== "missing") return false;
  if (value.noteId !== null && !decimalId(value.noteId)) return false;
  if (!isDeck(value.deck) || !isNoteType(value.noteType) || !isTemplate(value.template)) return false;
  if (typeof value.primaryText !== "string" || value.primaryText.length > 240) return false;
  if (!Array.isArray(value.reasons) || value.reasons.length > 4 || !value.reasons.every(isTriageReason)) return false;
  if (!sourceArray(value.sources) || !isCardStateSummary(value.cardState)) return false;
  if (dataset === "automatic" && (value.reasons.length === 0 || value.sources.includes("search_workset"))) return false;
  if (dataset === "search_workset" && !value.sources.includes("search_workset")) return false;
  if (value.reasons.length === 0) {
    if (value.priority !== null || value.primaryReasonCode !== null) return false;
  } else if (value.priority !== value.reasons[0]?.priority || value.primaryReasonCode !== value.reasons[0]?.code) {
    return false;
  }
  if (value.availability === "missing") return value.inspect === null;
  return isInspect(value.inspect, value.cardId);
}

function isTriageReason(value: unknown): value is TriageReason {
  if (!isRecord(value) || !exactKeys(value, ["code", "family", "scope", "priority", "sources", "evidence", "detectedAtMs"])) return false;
  if (!REASON_CODES.includes(String(value.code)) || value.family !== "learning" || value.scope !== "card") return false;
  if (!isPriority(value.priority) || !sourceArray(value.sources) || value.sources.includes("search_workset")) return false;
  if (!Array.isArray(value.evidence) || value.evidence.length > 4 || !value.evidence.every(isTriageEvidence)) return false;
  return value.detectedAtMs === null || safeTimestamp(value.detectedAtMs);
}

function isTriageEvidence(value: unknown): value is TriageEvidence {
  if (!isRecord(value) || typeof value.kind !== "string") return false;
  if (value.kind === "leech_state") {
    return exactKeys(value, ["kind", "lapses"]) && count(value.lapses);
  }
  if (value.kind === "review_counts") {
    return exactKeys(value, ["kind", "againCount", "periodStartMs", "periodEndMs"])
      && count(value.againCount) && period(value.periodStartMs, value.periodEndMs);
  }
  if (value.kind === "pass_rate") {
    return exactKeys(value, ["kind", "passRate", "periodStartMs", "periodEndMs"])
      && finite(value.passRate) && value.passRate >= 0 && value.passRate <= 1
      && period(value.periodStartMs, value.periodEndMs);
  }
  if (value.kind === "answer_time") {
    return exactKeys(value, ["kind", "averageAnswerSeconds", "periodStartMs", "periodEndMs"])
      && finite(value.averageAnswerSeconds) && value.averageAnswerSeconds >= 0
      && period(value.periodStartMs, value.periodEndMs);
  }
  if (value.kind === "signal_evidence") {
    return exactKeys(value, ["kind", "severity", "againCount", "reviewCount", "windowDays", "detectorVersion"])
      && (value.severity === "warning" || value.severity === "critical")
      && count(value.againCount) && count(value.reviewCount) && positiveInteger(value.windowDays)
      && typeof value.detectorVersion === "string" && value.detectorVersion.length > 0 && value.detectorVersion.length <= 40;
  }
  return false;
}

function isSourceStatusMap(value: unknown): boolean {
  return isRecord(value)
    && exactKeys(value, ["attention", "signals", "searchResolver"])
    && isSourceStatus(value.attention)
    && isSourceStatus(value.signals)
    && isSourceStatus(value.searchResolver);
}

function isSourceStatus(value: unknown): value is TriageSourceStatus {
  return isRecord(value)
    && exactKeys(value, ["status", "itemCount", "skippedCount", "truncated", "errorCode"])
    && new Set(["available", "empty", "unavailable", "error"]).has(String(value.status))
    && count(value.itemCount) && value.itemCount <= 200
    && count(value.skippedCount) && value.skippedCount <= 200
    && typeof value.truncated === "boolean"
    && (value.errorCode === null || (typeof value.errorCode === "string" && /^[a-z0-9_]{1,80}$/.test(value.errorCode)));
}

function isDeck(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["deckId", "name"])
    && (value.deckId === null || decimalId(value.deckId))
    && typeof value.name === "string" && value.name.length <= 200;
}

function isNoteType(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["noteTypeId", "name"])
    && (value.noteTypeId === null || decimalId(value.noteTypeId))
    && typeof value.name === "string" && value.name.length <= 160;
}

function isTemplate(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["ordinal", "name"])
    && (value.ordinal === null || count(value.ordinal))
    && typeof value.name === "string" && value.name.length <= 160;
}

function isCardStateSummary(value: unknown): boolean {
  if (!isRecord(value) || !exactKeys(value, ["state", "suspended", "buried", "flag"])) return false;
  if (value.flag !== null && (!count(value.flag) || value.flag > 7)) return false;
  if (value.state === null) return value.suspended === null && value.buried === null;
  if (!CARD_STATES.includes(value.state as TriageCardState)) return false;
  return typeof value.suspended === "boolean" && value.suspended === (value.state === "suspended")
    && typeof value.buried === "boolean" && value.buried === (value.state === "buried");
}

function isInspect(value: unknown, cardId: string): boolean {
  return isRecord(value) && exactKeys(value, ["mode", "cardId"]) && value.mode === "cards" && value.cardId === cardId;
}

function isContentChecks(value: unknown): boolean {
  return isRecord(value) && exactKeys(value, ["status"]) && value.status === "profiles_not_available";
}

function sourceArray(value: unknown): value is TriageSource[] {
  return Array.isArray(value) && value.length <= SOURCES.length
    && value.every((item) => SOURCES.includes(item))
    && new Set(value).size === value.length;
}

function isDataset(value: unknown): value is TriageDataset {
  return value === "automatic" || value === "search_workset";
}

function isPriority(value: unknown): value is TriagePriority {
  return PRIORITIES.includes(value as TriagePriority);
}

function period(start: unknown, end: unknown): boolean {
  return safeTimestamp(start) && safeTimestamp(end) && Number(end) > Number(start);
}

function safeTimestamp(value: unknown): value is number {
  return count(value) && value <= MAX_SAFE_TIMESTAMP;
}

function decimalId(value: unknown): value is string {
  return typeof value === "string"
    && /^[1-9]\d{0,18}$/.test(value)
    && (value.length < 19 || value <= "9223372036854775807");
}

function positiveInteger(value: unknown): value is number {
  return count(value) && value > 0;
}

function count(value: unknown): value is number {
  return finite(value) && Number.isInteger(value) && value >= 0;
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const expected = [...keys].sort();
  const actual = Object.keys(value).sort();
  return expected.length === actual.length && expected.every((key, index) => actual[index] === key);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function stringRecord(value: unknown): Record<string, string> | undefined {
  if (!isRecord(value) || !Object.values(value).every((item) => typeof item === "string")) return undefined;
  return value as Record<string, string>;
}

function invalidResponseError(): TriageApiError {
  return new TriageApiError("Triage returned an invalid response.", { code: "invalid_triage_response", status: 200 });
}
