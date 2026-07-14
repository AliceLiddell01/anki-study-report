import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { runReportAction, type ActionResponse } from "../lib/actionsApi";
import { fetchSearchInspect, fetchSearchQuery, SearchApiError } from "../lib/searchApi";
import type {
  SearchCardDetails,
  SearchCardRow,
  SearchCardState,
  SearchFilter,
  SearchInspectResponse,
  SearchMode,
  SearchNoteDetails,
  SearchNoteRow,
  SearchQueryRequest,
  SearchQueryResponse,
  SearchSortDirection,
} from "../types/search";

export const SEARCH_SELECTION_LIMIT = 200;
export const SEARCH_SESSION_KEY = "anki-study-report.search.v1";

export type SearchFiltersState = {
  deckId: string;
  noteTypeId: string;
  tag: string;
  state: "" | SearchCardState;
  flag: "" | "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7";
};

export type SearchWorkspaceState = ReturnType<typeof useSearchWorkspace>;

const EMPTY_FILTERS: SearchFiltersState = { deckId: "", noteTypeId: "", tag: "", state: "", flag: "" };

export function useSearchWorkspace() {
  const initial = useMemo(readSessionState, []);
  const [mode, setModeState] = useState<SearchMode>(initial.mode);
  const [query, setQuery] = useState(initial.query);
  const [filters, setFilters] = useState<SearchFiltersState>(initial.filters);
  const [sortDirection, setSortDirection] = useState<SearchSortDirection>(initial.sortDirection);
  const [pageSize, setPageSizeState] = useState<25 | 50 | 100>(initial.pageSize);
  const [response, setResponse] = useState<SearchQueryResponse | null>(null);
  const [queryStatus, setQueryStatus] = useState<"initial" | "loading" | "ready" | "error">("initial");
  const [queryError, setQueryError] = useState<SearchApiError | null>(null);
  const [submittedRequest, setSubmittedRequest] = useState<SearchQueryRequest | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [selectionCapHit, setSelectionCapHit] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [inspectStatus, setInspectStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [inspectResponse, setInspectResponse] = useState<SearchInspectResponse | null>(null);
  const [inspectError, setInspectError] = useState<SearchApiError | null>(null);
  const [browserStatus, setBrowserStatus] = useState<ActionResponse | null>(null);
  const [browserPending, setBrowserPending] = useState(false);
  const queryAbort = useRef<AbortController | null>(null);
  const inspectAbort = useRef<AbortController | null>(null);
  const querySequence = useRef(0);
  const inspectSequence = useRef(0);
  const requestSequence = useRef(0);

  useEffect(() => {
    persistSessionState({ mode, query, filters, sortDirection, pageSize });
  }, [filters, mode, pageSize, query, sortDirection]);

  useEffect(() => () => {
    queryAbort.current?.abort();
    inspectAbort.current?.abort();
  }, []);

  const executeQuery = useCallback(async (request: SearchQueryRequest) => {
    queryAbort.current?.abort();
    const controller = new AbortController();
    queryAbort.current = controller;
    const sequence = ++querySequence.current;
    setQueryStatus("loading");
    setQueryError(null);
    setBrowserStatus(null);
    try {
      const value = await fetchSearchQuery(request, controller.signal);
      if (sequence !== querySequence.current) return null;
      setResponse(value);
      setQueryStatus("ready");
      setSubmittedRequest(request);
      const returnedIds = new Set(entityIds(value));
      setSelectedIds((current) => {
        if (!response || response.mode !== value.mode || response.page !== value.page) return current;
        const oldPageIds = new Set(entityIds(response));
        return new Set([...current].filter((id) => !oldPageIds.has(id) || returnedIds.has(id)));
      });
      if (activeId && !returnedIds.has(activeId) && value.page === request.page) {
        setActiveId(null);
        setInspectStatus("idle");
        setInspectResponse(null);
      }
      return value;
    } catch (error) {
      if (controller.signal.aborted || sequence !== querySequence.current) return null;
      setQueryStatus("error");
      setQueryError(asSearchError(error));
      return null;
    }
  }, [activeId, response]);

  const submit = useCallback(() => {
    const request = buildRequest({ mode, query, filters, sortDirection, pageSize, page: 1, requestId: nextRequestId(requestSequence) });
    const fingerprintChanged = !submittedRequest || searchFingerprint(request) !== searchFingerprint(submittedRequest);
    if (fingerprintChanged) {
      setSelectedIds(new Set());
      setSelectionCapHit(false);
      setActiveId(null);
      setInspectStatus("idle");
      setInspectResponse(null);
      inspectAbort.current?.abort();
    }
    void executeQuery(request);
  }, [executeQuery, filters, mode, pageSize, query, sortDirection, submittedRequest]);

  const retry = useCallback(() => {
    const request = submittedRequest ?? buildRequest({ mode, query, filters, sortDirection, pageSize, page: 1, requestId: nextRequestId(requestSequence) });
    void executeQuery({ ...request, requestId: nextRequestId(requestSequence) });
  }, [executeQuery, filters, mode, pageSize, query, sortDirection, submittedRequest]);

  const goToPage = useCallback((page: number) => {
    if (!submittedRequest) return;
    void executeQuery({ ...submittedRequest, page, requestId: nextRequestId(requestSequence) });
  }, [executeQuery, submittedRequest]);

  const setPageSize = useCallback((value: 25 | 50 | 100) => {
    setPageSizeState(value);
    if (submittedRequest) {
      void executeQuery({ ...submittedRequest, page: 1, pageSize: value, requestId: nextRequestId(requestSequence) });
    }
  }, [executeQuery, submittedRequest]);

  const setMode = useCallback((value: SearchMode) => {
    if (value === mode) return;
    queryAbort.current?.abort();
    inspectAbort.current?.abort();
    setModeState(value);
    setFilters((current) => value === "notes" ? { ...current, state: "", flag: "" } : current);
    setResponse(null);
    setQueryStatus("initial");
    setQueryError(null);
    setSubmittedRequest(null);
    setSelectedIds(new Set());
    setSelectionCapHit(false);
    setActiveId(null);
    setInspectStatus("idle");
    setInspectResponse(null);
    setInspectError(null);
  }, [mode]);

  const clear = useCallback(() => {
    queryAbort.current?.abort();
    inspectAbort.current?.abort();
    setQuery("");
    setFilters(EMPTY_FILTERS);
    setSortDirection("asc");
    setPageSizeState(50);
    setResponse(null);
    setQueryStatus("initial");
    setQueryError(null);
    setSubmittedRequest(null);
    setSelectedIds(new Set());
    setSelectionCapHit(false);
    setActiveId(null);
    setInspectStatus("idle");
    setInspectResponse(null);
    setInspectError(null);
  }, []);

  const inspect = useCallback(async (id: string) => {
    setActiveId(id);
    inspectAbort.current?.abort();
    const controller = new AbortController();
    inspectAbort.current = controller;
    const sequence = ++inspectSequence.current;
    setInspectStatus("loading");
    setInspectError(null);
    const requestId = `inspect-${sequence}`;
    try {
      const value = mode === "cards"
        ? await fetchSearchInspect({ mode, cardId: id, requestId }, controller.signal)
        : await fetchSearchInspect({ mode, noteId: id, requestId }, controller.signal);
      if (sequence !== inspectSequence.current) return;
      setInspectResponse(value);
      setInspectStatus("ready");
    } catch (error) {
      if (controller.signal.aborted || sequence !== inspectSequence.current) return;
      setInspectError(asSearchError(error));
      setInspectResponse(null);
      setInspectStatus("error");
    }
  }, [mode]);

  const toggleSelection = useCallback((id: string, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (!checked) {
        next.delete(id);
        setSelectionCapHit(false);
      } else if (next.size < SEARCH_SELECTION_LIMIT) {
        next.add(id);
      } else {
        setSelectionCapHit(true);
      }
      return next;
    });
  }, []);

  const togglePageSelection = useCallback((checked: boolean) => {
    const ids = response ? entityIds(response) : [];
    setSelectedIds((current) => {
      const next = new Set(current);
      if (!checked) {
        ids.forEach((id) => next.delete(id));
        setSelectionCapHit(false);
        return next;
      }
      for (const id of ids) {
        if (next.size >= SEARCH_SELECTION_LIMIT) {
          setSelectionCapHit(true);
          break;
        }
        next.add(id);
      }
      return next;
    });
  }, [response]);

  const openInBrowser = useCallback(async () => {
    if (!selectedIds.size || browserPending) return;
    setBrowserPending(true);
    setBrowserStatus(null);
    try {
      const result = await runReportAction("open-search-selection", { mode, entityIds: [...selectedIds] });
      setBrowserStatus(result);
    } finally {
      setBrowserPending(false);
    }
  }, [browserPending, mode, selectedIds]);

  return {
    mode, setMode, query, setQuery, filters, setFilters, sortDirection, setSortDirection,
    pageSize, setPageSize, response, queryStatus, queryError, submit, retry, goToPage, clear,
    selectedIds, selectionCapHit, toggleSelection, togglePageSelection,
    activeId, inspect, inspectStatus, inspectResponse, inspectError,
    browserStatus, browserPending, openInBrowser,
  };
}

function buildRequest(input: {
  mode: SearchMode; query: string; filters: SearchFiltersState; sortDirection: SearchSortDirection;
  pageSize: 25 | 50 | 100; page: number; requestId: string;
}): SearchQueryRequest {
  const filters: SearchFilter[] = [];
  if (input.filters.deckId) filters.push({ type: "deck", deckId: input.filters.deckId });
  if (input.filters.noteTypeId) filters.push({ type: "note_type", noteTypeId: input.filters.noteTypeId });
  if (input.filters.tag.trim()) filters.push({ type: "tag", tag: input.filters.tag.trim() });
  if (input.mode === "cards" && input.filters.state) filters.push({ type: "state", state: input.filters.state });
  if (input.mode === "cards" && input.filters.flag !== "") filters.push({ type: "flag", flag: Number(input.filters.flag) as 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 });
  return {
    mode: input.mode,
    query: input.query,
    filters,
    sort: { key: "entity_id", direction: input.sortDirection },
    page: input.page,
    pageSize: input.pageSize,
    requestId: input.requestId,
  };
}

function nextRequestId(sequence: React.MutableRefObject<number>): string {
  sequence.current += 1;
  return `search-${sequence.current}`;
}

function entityIds(response: SearchQueryResponse): string[] {
  return response.mode === "cards"
    ? (response.items as SearchCardRow[]).map((item) => item.cardId)
    : (response.items as SearchNoteRow[]).map((item) => item.noteId);
}

function searchFingerprint(request: SearchQueryRequest): string {
  return JSON.stringify({ mode: request.mode, query: request.query, filters: request.filters, sort: request.sort, pageSize: request.pageSize });
}

function asSearchError(value: unknown): SearchApiError {
  return value instanceof SearchApiError
    ? value
    : new SearchApiError("Search request failed.", { code: "search_failed", status: 0 });
}

function readSessionState(): {
  mode: SearchMode; query: string; filters: SearchFiltersState; sortDirection: SearchSortDirection; pageSize: 25 | 50 | 100;
} {
  const fallback = { mode: "cards" as const, query: "", filters: EMPTY_FILTERS, sortDirection: "asc" as const, pageSize: 50 as const };
  try {
    const raw = window.sessionStorage.getItem(SEARCH_SESSION_KEY);
    if (!raw) return fallback;
    const value = JSON.parse(raw) as Record<string, unknown>;
    const rawFilters = value.filters && typeof value.filters === "object" ? value.filters as Record<string, unknown> : {};
    return {
      mode: value.mode === "notes" ? "notes" : "cards",
      query: typeof value.query === "string" ? value.query.slice(0, 4096) : "",
      filters: {
        deckId: typeof rawFilters.deckId === "string" ? rawFilters.deckId : "",
        noteTypeId: typeof rawFilters.noteTypeId === "string" ? rawFilters.noteTypeId : "",
        tag: typeof rawFilters.tag === "string" ? rawFilters.tag.slice(0, 100) : "",
        state: ["new", "learning", "review", "due", "suspended", "buried"].includes(String(rawFilters.state)) ? rawFilters.state as SearchCardState : "",
        flag: ["0", "1", "2", "3", "4", "5", "6", "7"].includes(String(rawFilters.flag)) ? rawFilters.flag as SearchFiltersState["flag"] : "",
      },
      sortDirection: value.sortDirection === "desc" ? "desc" : "asc",
      pageSize: value.pageSize === 25 || value.pageSize === 100 ? value.pageSize : 50,
    };
  } catch {
    return fallback;
  }
}

function persistSessionState(value: object): void {
  try {
    window.sessionStorage.setItem(SEARCH_SESSION_KEY, JSON.stringify({ version: 1, ...value }));
  } catch {
    // Search remains usable for this render when session storage is unavailable.
  }
}

export type SearchDetails = SearchCardDetails | SearchNoteDetails;
