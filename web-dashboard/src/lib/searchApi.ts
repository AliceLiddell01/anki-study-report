import type {
  SearchCardRow,
  SearchInspectRequest,
  SearchInspectResponse,
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
  if (!positiveInteger(value.page) || ![25, 50, 100].includes(Number(value.pageSize))) return false;
  if (!nonNegativeInteger(value.returnedCount) || !nonNegativeInteger(value.boundedTotal)) return false;
  if (value.returnedCount !== value.items.length || value.items.length > Number(value.pageSize)) return false;
  if (typeof value.hasNext !== "boolean" || typeof value.truncated !== "boolean") return false;
  return value.items.every((item) => mode === "cards" ? isCardRow(item) : isNoteRow(item));
}

function isSearchInspectResponse(value: unknown, mode: SearchMode): value is SearchInspectResponse {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.mode !== mode || !isRecord(value.details)) return false;
  return mode === "cards" ? isCardRow(value.details) : isNoteRow(value.details);
}

function isCardRow(value: unknown): value is SearchCardRow {
  return isRecord(value)
    && decimalId(value.cardId)
    && decimalId(value.noteId)
    && decimalId(value.deckId)
    && decimalId(value.noteTypeId)
    && typeof value.primaryText === "string"
    && typeof value.deckName === "string"
    && typeof value.noteTypeName === "string"
    && Array.isArray(value.tagSummary)
    && value.tagSummary.every((tag) => typeof tag === "string");
}

function isNoteRow(value: unknown): value is SearchNoteRow {
  return isRecord(value)
    && decimalId(value.noteId)
    && decimalId(value.noteTypeId)
    && typeof value.primaryText === "string"
    && typeof value.noteTypeName === "string"
    && nonNegativeInteger(value.cardCount)
    && Array.isArray(value.tagSummary)
    && value.tagSummary.every((tag) => typeof tag === "string")
    && Array.isArray(value.deckSummary);
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
  return typeof value === "string" && /^[1-9]\d{0,18}$/.test(value);
}

function positiveInteger(value: unknown): boolean {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

function nonNegativeInteger(value: unknown): boolean {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}
