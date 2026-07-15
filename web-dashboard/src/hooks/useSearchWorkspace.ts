import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { runReportAction, type ActionResponse } from "../lib/actionsApi";
import { EntityActionApiError, runCardEntityAction, runNoteEntityAction } from "../lib/entityActionsApi";
import { fetchSearchInspect, fetchSearchQuery, SearchApiError } from "../lib/searchApi";
import { durationBucket, emitTelemetryEvent, resultCountBucket, telemetryOccurredAt } from "../lib/telemetryApi";
import type { CardEntityAction, EntityActionResponse, NoteEntityAction } from "../types/entityActions";
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
  const [actionPending, setActionPending] = useState(false);
  const [actionResponse, setActionResponse] = useState<EntityActionResponse | null>(null);
  const [actionError, setActionError] = useState<EntityActionApiError | null>(null);
  const queryAbort = useRef<AbortController | null>(null);
  const inspectAbort = useRef<AbortController | null>(null);
  const actionAbort = useRef<AbortController | null>(null);
  const actionInFlight = useRef(false);
  const querySequence = useRef(0);
  const inspectSequence = useRef(0);
  const requestSequence = useRef(0);

  useEffect(() => {
    persistSessionState({ mode, query, filters, sortDirection, pageSize });
  }, [filters, mode, pageSize, query, sortDirection]);

  useEffect(() => () => {
    queryAbort.current?.abort();
    inspectAbort.current?.abort();
    actionAbort.current?.abort();
  }, []);

  const executeQuery = useCallback(async (request: SearchQueryRequest) => {
    const startedAt = performance.now();
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
      void emitTelemetryEvent({
        eventCode: "search.completed",
        resultCode: value.boundedTotal === 0 ? "no_results" : "success",
        durationBucket: durationBucket(performance.now() - startedAt),
        resultCountBucket: resultCountBucket(value.boundedTotal),
        occurredAt: telemetryOccurredAt(),
      });
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
      const searchError = asSearchError(error);
      setQueryError(searchError);
      void emitTelemetryEvent({
        eventCode: "search.completed",
        resultCode: "failed",
        durationBucket: durationBucket(performance.now() - startedAt),
        resultCountBucket: "0",
        occurredAt: telemetryOccurredAt(),
      });
      void emitTelemetryEvent({
        eventCode: "api_operation.failed",
        featureCode: "search_query",
        errorCode: String(searchError.code).includes("timeout") ? "timeout" : "unavailable",
        occurredAt: telemetryOccurredAt(),
      });
      return null;
    }
  }, [activeId, response]);

  const submit = useCallback(() => {
    if (actionInFlight.current) return;
    setActionResponse(null);
    setActionError(null);
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
    if (actionInFlight.current) return;
    const request = submittedRequest ?? buildRequest({ mode, query, filters, sortDirection, pageSize, page: 1, requestId: nextRequestId(requestSequence) });
    void executeQuery({ ...request, requestId: nextRequestId(requestSequence) });
  }, [executeQuery, filters, mode, pageSize, query, sortDirection, submittedRequest]);

  const goToPage = useCallback((page: number) => {
    if (actionInFlight.current) return;
    if (!submittedRequest) return;
    void executeQuery({ ...submittedRequest, page, requestId: nextRequestId(requestSequence) });
  }, [executeQuery, submittedRequest]);

  const setPageSize = useCallback((value: 25 | 50 | 100) => {
    if (actionInFlight.current) return;
    setPageSizeState(value);
    if (submittedRequest) {
      void executeQuery({ ...submittedRequest, page: 1, pageSize: value, requestId: nextRequestId(requestSequence) });
    }
  }, [executeQuery, submittedRequest]);

  const setMode = useCallback((value: SearchMode) => {
    if (actionInFlight.current) return;
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
    setActionResponse(null);
    setActionError(null);
  }, [mode]);

  const clear = useCallback(() => {
    if (actionInFlight.current) return;
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
    setActionResponse(null);
    setActionError(null);
  }, []);

  const inspect = useCallback(async (id: string, allowDuringAction = false) => {
    if (actionInFlight.current && !allowDuringAction) return;
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

  const refreshAfterAction = useCallback(async (request: SearchQueryRequest, inspectedId: string | null) => {
    let refreshed = await executeQuery({ ...request, requestId: nextRequestId(requestSequence) });
    if (refreshed && refreshed.pageCount > 0 && refreshed.page > refreshed.pageCount) {
      refreshed = await executeQuery({
        ...request,
        page: refreshed.pageCount,
        requestId: nextRequestId(requestSequence),
      });
    }
    setSelectedIds(new Set());
    setSelectionCapHit(false);
    if (inspectedId && refreshed && entityIds(refreshed).includes(inspectedId)) {
      await inspect(inspectedId, true);
    }
  }, [executeQuery, inspect]);

  const runEntityAction = useCallback(async (
    entityAction: CardEntityAction | NoteEntityAction,
    options: { flag?: number; tags?: string[]; deckId?: string } = {},
  ) => {
    if (actionInFlight.current || selectedIds.size === 0 || !submittedRequest) return;
    actionInFlight.current = true;
    setActionPending(true);
    setActionResponse(null);
    setActionError(null);
    queryAbort.current?.abort();
    querySequence.current += 1;
    const controller = new AbortController();
    actionAbort.current = controller;
    const ids = [...selectedIds];
    const startedAt = performance.now();
    const inspectedId = activeId;
    try {
      const requestId = `entity-action-${nextRequestId(requestSequence)}`;
      const value = mode === "cards"
        ? await runCardEntityAction({
            action: entityAction as CardEntityAction,
            cardIds: ids,
            ...(entityAction === "set_flag" ? { flag: options.flag } : {}),
            ...(entityAction === "move_to_deck" ? { deckId: options.deckId } : {}),
            requestId,
          }, controller.signal)
        : await runNoteEntityAction({
            action: entityAction as NoteEntityAction,
            noteIds: ids,
            tags: options.tags ?? [],
            requestId,
          }, controller.signal);
      if (controller.signal.aborted) return;
      setActionResponse(value);
      void emitTelemetryEvent({
        eventCode: "entity_action.completed",
        actionCode: entityAction,
        resultCode: value.resultCode === "action.no_changes" ? "no_change" : "success",
        durationBucket: durationBucket(performance.now() - startedAt),
        occurredAt: telemetryOccurredAt(),
      });
      await refreshAfterAction(submittedRequest, inspectedId);
    } catch (error) {
      if (!controller.signal.aborted) {
        setActionError(error instanceof EntityActionApiError
          ? error
          : new EntityActionApiError("The Anki action failed.", { code: "entity_action_failed", status: 0 }));
        void emitTelemetryEvent({
          eventCode: "entity_action.completed",
          actionCode: entityAction,
          resultCode: "failed",
          durationBucket: durationBucket(performance.now() - startedAt),
          occurredAt: telemetryOccurredAt(),
        });
        void emitTelemetryEvent({
          eventCode: "api_operation.failed",
          featureCode: "entity_action",
          errorCode: "unavailable",
          occurredAt: telemetryOccurredAt(),
        });
      }
    } finally {
      if (!controller.signal.aborted) setActionPending(false);
      actionInFlight.current = false;
    }
  }, [activeId, mode, refreshAfterAction, selectedIds, submittedRequest]);

  return {
    mode, setMode, query, setQuery, filters, setFilters, sortDirection, setSortDirection,
    pageSize, setPageSize, response, queryStatus, queryError, submit, retry, goToPage, clear,
    selectedIds, selectionCapHit, toggleSelection, togglePageSelection,
    activeId, inspect, inspectStatus, inspectResponse, inspectError,
    browserStatus, browserPending, openInBrowser,
    actionPending, actionResponse, actionError, runEntityAction,
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
