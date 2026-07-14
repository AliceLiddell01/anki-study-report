import type {
  SearchCardRow,
  SearchInspectRequest,
  SearchInspectResponse,
  SearchMetadataRequest,
  SearchMetadataResponse,
  SearchMode,
  SearchNoteRow,
  SearchQueryRequest,
  SearchQueryResponse,
} from "../types/search";

export class SearchApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fieldErrors?: Record<string, string>;
  readonly requestId?: string;

  constructor(message: string, options: { code: string; status: number; fieldErrors?: Record<string, string>; requestId?: string }) {
    super(message);
    this.name = "SearchApiError";
    this.code = options.code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors;
    this.requestId = options.requestId;
  }
}

export async function fetchSearchQuery<M extends SearchMode>(
  request: SearchQueryRequest & { mode: M },
  signal?: AbortSignal,
): Promise<SearchQueryResponse<M>> {
  const value = await postSearch("/api/search/query", request, signal);
  if (!isSearchQueryResponse(value, request.mode)) {
    throw malformedResponseError();
  }
  return value as SearchQueryResponse<M>;
}

export async function fetchSearchMetadata(
  request: SearchMetadataRequest,
  signal?: AbortSignal,
): Promise<SearchMetadataResponse> {
  const value = await postSearch("/api/search/query", request, signal);
  if (!isSearchMetadataResponse(value)) {
    throw malformedResponseError();
  }
  return value;
}

export async function fetchSearchInspect<M extends SearchMode>(
  request: SearchInspectRequest & { mode: M },
  signal?: AbortSignal,
): Promise<SearchInspectResponse<M>> {
  const value = await postSearch("/api/search/inspect", request, signal);
  if (!isSearchInspectResponse(value, request.mode)) {
    throw malformedResponseError();
  }
  return value as SearchInspectResponse<M>;
}

async function postSearch(path: string, request: object, signal?: AbortSignal): Promise<unknown> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`${path}?token=${encodeURIComponent(token)}`, {
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
  const body = isRecord(payload) ? payload : {};
  if (!response.ok || body.ok !== true || !("response" in body)) {
    throw new SearchApiError(
      typeof body.message === "string" ? body.message : "Search request failed.",
      {
        code: typeof body.error === "string" ? body.error : "search_failed",
        status: response.status,
        fieldErrors: stringRecord(body.fieldErrors),
        requestId: typeof body.requestId === "string" ? body.requestId : undefined,
      },
    );
  }
  return body.response;
}

function isSearchQueryResponse(value: unknown, mode: SearchMode): value is SearchQueryResponse {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.mode !== mode || !Array.isArray(value.items)) return false;
  if (!positiveInteger(value.page) || !isPageSize(value.pageSize)) return false;
  if (!nonNegativeInteger(value.pageCount) || !positiveInteger(value.pageLimit)) return false;
  if (!nonNegativeInteger(value.returnedCount) || !nonNegativeInteger(value.boundedTotal)) return false;
  if (value.boundedTotal > 2000 || value.pageCount !== Math.ceil(value.boundedTotal / value.pageSize)) return false;
  if (value.pageLimit !== Math.ceil(2000 / value.pageSize) || value.page > value.pageLimit) return false;
  if (value.returnedCount !== value.items.length || value.items.length > Number(value.pageSize)) return false;
  if (value.page > value.pageCount && value.items.length !== 0) return false;
  if (typeof value.hasNext !== "boolean" || value.hasNext !== (value.page < value.pageCount) || typeof value.truncated !== "boolean") return false;
  if (!isSearchSort(value.sort) || !optionalRequestId(value.requestId)) return false;
  return value.items.every((item) => mode === "cards" ? isSearchCardRow(item) : isSearchNoteRow(item));
}

function isSearchMetadataResponse(value: unknown): value is SearchMetadataResponse {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.kind !== "metadata") return false;
  if (!Array.isArray(value.decks) || !value.decks.every(isSearchMetadataDeck)) return false;
  if (!Array.isArray(value.noteTypes) || !value.noteTypes.every(isSearchMetadataNoteType)) return false;
  if (value.decks.length > 5000 || value.noteTypes.length > 1000) return false;
  if (typeof value.decksTruncated !== "boolean" || typeof value.noteTypesTruncated !== "boolean") return false;
  return optionalRequestId(value.requestId);
}

function isSearchInspectResponse(value: unknown, mode: SearchMode): value is SearchInspectResponse {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.mode !== mode || !isRecord(value.details)) return false;
  if (!optionalRequestId(value.requestId)) return false;
  return mode === "cards" ? isSearchCardDetails(value.details) : isSearchNoteDetails(value.details);
}

function isSearchMetadataDeck(value: unknown): boolean {
  return isRecord(value)
    && decimalId(value.deckId)
    && typeof value.deckName === "string"
    && value.deckName.length <= 500
    && typeof value.filtered === "boolean";
}

function isSearchMetadataNoteType(value: unknown): boolean {
  return isRecord(value)
    && decimalId(value.noteTypeId)
    && typeof value.noteTypeName === "string"
    && value.noteTypeName.length <= 500;
}

function isSearchCardRow(value: unknown): value is SearchCardRow {
  return isRecord(value)
    && decimalId(value.cardId)
    && decimalId(value.noteId)
    && decimalId(value.deckId)
    && decimalId(value.noteTypeId)
    && typeof value.deckName === "string"
    && typeof value.noteTypeName === "string"
    && integer(value.templateOrdinal)
    && typeof value.templateName === "string"
    && typeof value.primaryText === "string"
    && isCardState(value.state)
    && integer(value.due)
    && integer(value.interval)
    && integer(value.repetitions)
    && integer(value.lapses)
    && integer(value.flag)
    && value.flag >= 0
    && value.flag <= 7
    && stringArray(value.tagSummary);
}

function isSearchNoteRow(value: unknown): value is SearchNoteRow {
  return isRecord(value)
    && decimalId(value.noteId)
    && decimalId(value.noteTypeId)
    && typeof value.primaryText === "string"
    && typeof value.noteTypeName === "string"
    && nonNegativeInteger(value.cardCount)
    && stringArray(value.tagSummary)
    && Array.isArray(value.deckSummary)
    && value.deckSummary.every(isSearchDeckSummary);
}

function isSearchCardDetails(value: unknown): boolean {
  return isSearchCardRow(value)
    && isRecord(value)
    && isSearchDeckSummary(value.deck)
    && isNoteTypeSummary(value.noteType)
    && isRecord(value.template)
    && integer(value.template.ordinal)
    && typeof value.template.name === "string"
    && integer(value.queue)
    && stringArray(value.tags);
}

function isSearchNoteDetails(value: unknown): boolean {
  return isSearchNoteRow(value)
    && isRecord(value)
    && isNoteTypeSummary(value.noteType)
    && Array.isArray(value.fields)
    && value.fields.every((field) => isRecord(field) && typeof field.name === "string" && typeof field.value === "string")
    && stringArray(value.tags)
    && Array.isArray(value.cardReferences)
    && value.cardReferences.every(isCardReference)
    && typeof value.cardsTruncated === "boolean"
    && typeof value.fieldsTruncated === "boolean"
    && Array.isArray(value.deckSummaries)
    && value.deckSummaries.every(isSearchDeckSummary);
}

function isSearchDeckSummary(value: unknown): boolean {
  return isRecord(value) && decimalId(value.deckId) && typeof value.deckName === "string";
}

function isNoteTypeSummary(value: unknown): boolean {
  return isRecord(value) && decimalId(value.noteTypeId) && typeof value.noteTypeName === "string";
}

function isCardReference(value: unknown): boolean {
  return isRecord(value) && decimalId(value.cardId) && decimalId(value.deckId) && integer(value.templateOrdinal);
}

function isSearchSort(value: unknown): boolean {
  return isRecord(value) && value.key === "entity_id" && (value.direction === "asc" || value.direction === "desc");
}

function isCardState(value: unknown): boolean {
  return ["new", "learning", "review", "due", "suspended", "buried"].includes(String(value));
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function optionalRequestId(value: unknown): boolean {
  return value === undefined || (typeof value === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(value));
}

function isPageSize(value: unknown): value is 25 | 50 | 100 {
  return value === 25 || value === 50 || value === 100;
}

function malformedResponseError(): SearchApiError {
  return new SearchApiError("Search returned an invalid response.", { code: "invalid_search_response", status: 200 });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function stringRecord(value: unknown): Record<string, string> | undefined {
  if (!isRecord(value) || !Object.values(value).every((item) => typeof item === "string")) return undefined;
  return value as Record<string, string>;
}

function decimalId(value: unknown): value is string {
  return typeof value === "string"
    && /^[1-9]\d{0,18}$/.test(value)
    && (value.length < 19 || value <= "9223372036854775807");
}

function positiveInteger(value: unknown): value is number {
  return integer(value) && value > 0;
}

function nonNegativeInteger(value: unknown): value is number {
  return integer(value) && value >= 0;
}

function integer(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && Number.isInteger(value);
}
