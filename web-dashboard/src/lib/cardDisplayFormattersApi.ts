import type {
  CardDisplayFormatter,
  CardDisplayFormatterQueryRequest,
  CardDisplayFormatterStoreSnapshot,
  CardDisplayFormatterUpdateRequest,
  CardDisplayFormatterUpdateResponse,
  CardDisplayFormatterValidateRequest,
  CardDisplayFormatterValidateResponse,
} from "../types/cardDisplayFormatters";

const STORE_STATUSES = ["empty", "available", "corrupt", "future_schema", "unavailable"] as const;
const STORED_STATES = ["enabled", "disabled"] as const;
const INPUT_SOURCES = ["browser_question", "reviewer_front"] as const;
const TEXT_MODES = ["preserve", "omit"] as const;
const MEDIA_MODES = ["omit", "filename", "stem", "marker"] as const;

export class CardDisplayFormattersApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fieldErrors?: Record<string, string>;
  readonly currentRevision?: number;

  constructor(message: string, options: { code: string; status: number; fieldErrors?: Record<string, string>; currentRevision?: number }) {
    super(message);
    this.name = "CardDisplayFormattersApiError";
    this.code = options.code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors;
    this.currentRevision = options.currentRevision;
  }
}

export async function fetchCardDisplayFormatters(
  request: CardDisplayFormatterQueryRequest,
  signal?: AbortSignal,
): Promise<CardDisplayFormatterStoreSnapshot> {
  return parseCardDisplayFormatterStoreSnapshot(await post("query", request, signal));
}

export async function validateCardDisplayFormatter(
  request: CardDisplayFormatterValidateRequest,
  signal?: AbortSignal,
): Promise<CardDisplayFormatterValidateResponse> {
  return parseCardDisplayFormatterValidateResponse(await post("validate", request, signal));
}

export async function updateCardDisplayFormatter(
  request: CardDisplayFormatterUpdateRequest,
  signal?: AbortSignal,
): Promise<CardDisplayFormatterUpdateResponse> {
  return parseCardDisplayFormatterUpdateResponse(await post("update", request, signal));
}

async function post(operation: "query" | "validate" | "update", request: object, signal?: AbortSignal): Promise<unknown> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/card-display-formatters/${operation}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  let payload: unknown;
  try { payload = await response.json(); } catch { payload = null; }
  if (!isRecord(payload) || !response.ok || payload.ok !== true || !exactKeys(payload, ["ok", "response"])) {
    const error = parseErrorEnvelope(payload);
    throw new CardDisplayFormattersApiError("Card display formatter request failed.", {
      code: error?.code ?? "card_display_formatters_failed",
      status: response.status,
      fieldErrors: error?.fieldErrors,
      currentRevision: error?.currentRevision,
    });
  }
  return payload.response;
}

export function parseCardDisplayFormatterStoreSnapshot(value: unknown): CardDisplayFormatterStoreSnapshot {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "status", "revision", "formatters", "errorCode", "quarantined"])) throw invalidResponse();
  if (value.schemaVersion !== 1 || !STORE_STATUSES.includes(value.status as never) || !safeInteger(value.revision)) throw invalidResponse();
  if (!Array.isArray(value.formatters) || value.formatters.length > 1000 || !value.formatters.every(isFormatter)) throw invalidResponse();
  if ((value.status === "empty" || value.status === "available") === false && value.formatters.length !== 0) throw invalidResponse();
  if (value.status === "empty" && value.formatters.length !== 0) throw invalidResponse();
  if (value.status === "available" && value.formatters.length === 0) throw invalidResponse();
  if (value.errorCode !== null && !boundedCode(value.errorCode)) throw invalidResponse();
  if (typeof value.quarantined !== "boolean") throw invalidResponse();
  const keys = value.formatters.map((item) => `${item.noteTypeId}:${item.templateOrdinal === null ? "default" : item.templateOrdinal}`);
  if (new Set(keys).size !== keys.length) throw invalidResponse();
  const counts = new Map<string, number>();
  for (const formatter of value.formatters) counts.set(formatter.noteTypeId, (counts.get(formatter.noteTypeId) || 0) + 1);
  if ([...counts.values()].some((count) => count > 33)) throw invalidResponse();
  return value as unknown as CardDisplayFormatterStoreSnapshot;
}

export function parseCardDisplayFormatterValidateResponse(value: unknown): CardDisplayFormatterValidateResponse {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "valid", "formatter", "fieldErrors"])) throw invalidResponse();
  if (value.schemaVersion !== 1 || value.valid !== true || !isFormatter(value.formatter) || !isStringRecord(value.fieldErrors) || Object.keys(value.fieldErrors).length !== 0) throw invalidResponse();
  return value as unknown as CardDisplayFormatterValidateResponse;
}

export function parseCardDisplayFormatterUpdateResponse(value: unknown): CardDisplayFormatterUpdateResponse {
  if (!isRecord(value) || !exactKeys(value, ["schemaVersion", "action", "store", "formatter"])) throw invalidResponse();
  if (value.schemaVersion !== 1 || (value.action !== "save" && value.action !== "delete")) throw invalidResponse();
  const store = parseCardDisplayFormatterStoreSnapshot(value.store);
  if (value.formatter !== null && !isFormatter(value.formatter)) throw invalidResponse();
  if ((value.action === "save") !== (value.formatter !== null)) throw invalidResponse();
  if (value.action === "save") {
    if (store.status !== "available") throw invalidResponse();
    const formatter = value.formatter as CardDisplayFormatter;
    const stored = store.formatters.find((item) => formatterKey(item) === formatterKey(formatter));
    if (!stored || JSON.stringify(stored) !== JSON.stringify(formatter)) throw invalidResponse();
  }
  return { schemaVersion: 1, action: value.action, store, formatter: value.formatter as CardDisplayFormatter | null };
}


type ParsedErrorEnvelope = {
  code: string;
  fieldErrors?: Record<string, string>;
  currentRevision?: number;
};

function parseErrorEnvelope(value: unknown): ParsedErrorEnvelope | null {
  if (!isRecord(value) || value.ok !== false || !boundedCode(value.error)) return null;
  if (exactKeys(value, ["ok", "error"])) return { code: value.error };
  if (exactKeys(value, ["ok", "error", "fieldErrors"]) && isStringRecord(value.fieldErrors)) {
    return { code: value.error, fieldErrors: value.fieldErrors };
  }
  if (exactKeys(value, ["ok", "error", "currentRevision"]) && safeInteger(value.currentRevision)) {
    return { code: value.error, currentRevision: value.currentRevision };
  }
  return null;
}

function formatterKey(value: CardDisplayFormatter): string {
  return `${value.noteTypeId}:${value.templateOrdinal === null ? "default" : value.templateOrdinal}`;
}

function isFormatter(value: unknown): value is CardDisplayFormatter {
  if (!isRecord(value) || !exactKeys(value, [
    "noteTypeId", "noteTypeName", "templateOrdinal", "templateName", "storedState",
    "inputSource", "textMode", "imageMode", "audioMode", "maxLines", "lineSeparator",
    "maxCharacters", "updatedAt",
  ])) return false;
  if (!decimalId(value.noteTypeId) || !boundedText(value.noteTypeName, 160)) return false;
  if (value.templateOrdinal !== null && !ordinal(value.templateOrdinal)) return false;
  if (value.templateOrdinal === null ? value.templateName !== null : !boundedText(value.templateName, 160)) return false;
  return STORED_STATES.includes(value.storedState as never)
    && INPUT_SOURCES.includes(value.inputSource as never)
    && TEXT_MODES.includes(value.textMode as never)
    && MEDIA_MODES.includes(value.imageMode as never)
    && MEDIA_MODES.includes(value.audioMode as never)
    && integerRange(value.maxLines, 1, 4)
    && typeof value.lineSeparator === "string" && [...value.lineSeparator].length <= 8 && !/[\u0000-\u001f\u007f]/.test(value.lineSeparator)
    && integerRange(value.maxCharacters, 1, 240)
    && timestamp(value.updatedAt);
}

function decimalId(value: unknown): value is string {
  return typeof value === "string" && /^[1-9]\d{0,18}$/.test(value)
    && (value.length < 19 || value <= "9223372036854775807");
}
function ordinal(value: unknown): value is number { return integerRange(value, 0, 31); }
function integerRange(value: unknown, min: number, max: number): value is number { return safeInteger(value) && value >= min && value <= max; }
function safeInteger(value: unknown): value is number { return typeof value === "number" && Number.isSafeInteger(value) && value >= 0; }
function boundedText(value: unknown, max: number): value is string { return typeof value === "string" && value.trim().length > 0 && [...value].length <= max && !/[\u0000-\u001f\u007f]/.test(value); }
function timestamp(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 40) return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?Z$/.exec(value);
  if (!match || Number(match[1]) < 1) return false;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return false;
  return new Date(parsed).toISOString().slice(0, 19) === value.slice(0, 19);
}
function boundedCode(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9_]{0,79}$/.test(value); }
function isStringRecord(value: unknown): value is Record<string, string> { return isRecord(value) && Object.values(value).every((item) => typeof item === "string" && item.length <= 240); }
function isRecord(value: unknown): value is Record<string, unknown> { return !!value && typeof value === "object" && !Array.isArray(value); }
function exactKeys(value: Record<string, unknown>, keys: string[]): boolean { const actual = Object.keys(value).sort(); const expected = [...keys].sort(); return actual.length === expected.length && expected.every((key, index) => actual[index] === key); }
function invalidResponse(): CardDisplayFormattersApiError { return new CardDisplayFormattersApiError("Card display formatters returned an invalid response.", { code: "invalid_card_display_formatters_response", status: 200 }); }
