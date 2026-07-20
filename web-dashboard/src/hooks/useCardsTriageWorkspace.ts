import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { runReportAction, type ActionResponse } from "../lib/actionsApi";
import { fetchSearchInspect, SearchApiError } from "../lib/searchApi";
import { fetchTriageQuery, TriageApiError } from "../lib/triageApi";
import {
  MAX_ACCUMULATED_ITEMS,
  MAX_CONTENT_PAGES,
  mergeTriagePages,
} from "../lib/triagePagination";
import type { SearchInspectResponse } from "../types/search";
import type { TriageItem, TriageQueryResponse, TriageScope } from "../types/triage";

export type CardsQueryStatus = "loading" | "ready" | "error";
export type CardsInspectStatus = "idle" | "loading" | "ready" | "error";
export type CardsContinuationStatus = "idle" | "loading" | "error" | "exhausted" | "capped";
export type LearningPeriodDays = 7 | 30 | 90;

export interface CardsTriageWorkspace {
  queryStatus: CardsQueryStatus;
  queryError: TriageApiError | null;
  response: TriageQueryResponse | null;
  learningPeriodDays: LearningPeriodDays;
  setLearningPeriodDays: (value: LearningPeriodDays) => void;
  activeId: string | null;
  activeItem: TriageItem | null;
  inspectStatus: CardsInspectStatus;
  inspectError: SearchApiError | null;
  inspectResponse: SearchInspectResponse<"cards"> | null;
  openPending: boolean;
  openResult: ActionResponse | null;
  continuationStatus: CardsContinuationStatus;
  continuationError: TriageApiError | null;
  loadedContentPages: number;
  scannedNoteCount: number;
  hasMoreContent: boolean;
  lastContinuationAddedCount: number | null;
  activate: (item: TriageItem) => void;
  clearActive: () => void;
  refresh: () => void;
  continueContentScan: () => Promise<void>;
  retryInspect: () => void;
  openInAnki: () => Promise<void>;
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function useCardsTriageWorkspace(deckIds: string[]): CardsTriageWorkspace {
  const deckKey = deckIds.join(",");
  const stableDeckIds = useMemo(() => deckKey ? deckKey.split(",") : [], [deckKey]);
  const [learningPeriodDays, setLearningPeriodDaysState] = useState<LearningPeriodDays>(7);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [queryStatus, setQueryStatus] = useState<CardsQueryStatus>("loading");
  const [queryError, setQueryError] = useState<TriageApiError | null>(null);
  const [response, setResponse] = useState<TriageQueryResponse | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [inspectStatus, setInspectStatus] = useState<CardsInspectStatus>("idle");
  const [inspectError, setInspectError] = useState<SearchApiError | null>(null);
  const [inspectResponse, setInspectResponse] = useState<SearchInspectResponse<"cards"> | null>(null);
  const [inspectVersion, setInspectVersion] = useState(0);
  const [openPending, setOpenPending] = useState(false);
  const [openResult, setOpenResult] = useState<ActionResponse | null>(null);
  const [continuationStatus, setContinuationStatus] = useState<CardsContinuationStatus>("idle");
  const [continuationError, setContinuationError] = useState<TriageApiError | null>(null);
  const [loadedContentPages, setLoadedContentPages] = useState(0);
  const [lastContinuationAddedCount, setLastContinuationAddedCount] = useState<number | null>(null);

  const querySequence = useRef(0);
  const inspectSequence = useRef(0);
  const continuationSequence = useRef(0);
  const continuationController = useRef<AbortController | null>(null);
  const continuationInFlight = useRef(false);
  const activeIdRef = useRef<string | null>(null);
  const responseRef = useRef<TriageQueryResponse | null>(null);
  const scopeRef = useRef<TriageScope | null>(null);
  const inspectCache = useRef(new Map<string, SearchInspectResponse<"cards">>());

  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);
  useEffect(() => { responseRef.current = response; }, [response]);

  useEffect(() => {
    const controller = new AbortController();
    const sequence = ++querySequence.current;
    const previousActive = activeIdRef.current;
    const periodEndMs = Date.now();
    const scope: TriageScope = {
      periodStartMs: periodEndMs - learningPeriodDays * DAY_MS,
      periodEndMs,
      deckIds: stableDeckIds,
    };
    scopeRef.current = scope;

    continuationController.current?.abort();
    continuationController.current = null;
    continuationInFlight.current = false;
    continuationSequence.current += 1;
    setContinuationStatus("idle");
    setContinuationError(null);
    setLoadedContentPages(0);
    setLastContinuationAddedCount(null);
    setQueryStatus("loading");
    setQueryError(null);
    setResponse(null);
    responseRef.current = null;
    setActiveId(null);
    activeIdRef.current = null;
    setInspectStatus("idle");
    setInspectResponse(null);
    setInspectError(null);
    inspectSequence.current += 1;

    void fetchTriageQuery({
      schemaVersion: 4,
      dataset: "automatic",
      scope,
      limit: 100,
      contentCursor: null,
    }, controller.signal).then((value) => {
      if (controller.signal.aborted || sequence !== querySequence.current) return;
      setResponse(value);
      responseRef.current = value;
      setQueryStatus("ready");
      const restored = previousActive && value.items.some((item) => item.itemId === previousActive && item.inspect)
        ? previousActive
        : null;
      setActiveId(restored);
      activeIdRef.current = restored;
      setContinuationStatus(coherentNextCursor(value) ? "idle" : "exhausted");
    }).catch((error: unknown) => {
      if (controller.signal.aborted || sequence !== querySequence.current) return;
      setQueryError(asTriageError(error));
      setQueryStatus("error");
      setResponse(null);
      responseRef.current = null;
      setActiveId(null);
      activeIdRef.current = null;
    });
    return () => controller.abort();
  }, [learningPeriodDays, refreshVersion, stableDeckIds]);

  useEffect(() => () => continuationController.current?.abort(), []);

  const activeItem = useMemo(
    () => response?.items.find((item) => item.itemId === activeId) ?? null,
    [activeId, response],
  );

  useEffect(() => {
    const cardId = activeItem?.inspect?.cardId;
    if (!cardId) {
      setInspectStatus("idle");
      setInspectResponse(null);
      setInspectError(null);
      return;
    }
    const cached = inspectCache.current.get(cardId);
    if (cached) {
      setInspectResponse(cached);
      setInspectStatus("ready");
      setInspectError(null);
      return;
    }
    const controller = new AbortController();
    const sequence = ++inspectSequence.current;
    setInspectStatus("loading");
    setInspectResponse(null);
    setInspectError(null);
    void fetchSearchInspect({ schemaVersion: 2, mode: "cards", cardId, requestId: `cards-${sequence}` }, controller.signal)
      .then((value) => {
        if (controller.signal.aborted || sequence !== inspectSequence.current) return;
        inspectCache.current.set(cardId, value);
        setInspectResponse(value);
        setInspectStatus("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || sequence !== inspectSequence.current) return;
        setInspectError(asSearchError(error));
        setInspectResponse(null);
        setInspectStatus("error");
      });
    return () => controller.abort();
  }, [activeItem?.itemId, activeItem?.inspect?.cardId, inspectVersion]);

  const activate = useCallback((item: TriageItem) => {
    setOpenResult(null);
    const nextId = item.inspect ? item.itemId : null;
    setActiveId(nextId);
    activeIdRef.current = nextId;
  }, []);

  const clearActive = useCallback(() => {
    setOpenResult(null);
    setActiveId(null);
    activeIdRef.current = null;
    inspectSequence.current += 1;
    setInspectStatus("idle");
    setInspectResponse(null);
    setInspectError(null);
  }, []);

  const refresh = useCallback(() => {
    setOpenResult(null);
    setRefreshVersion((value) => value + 1);
  }, []);

  const setLearningPeriodDays = useCallback((value: LearningPeriodDays) => {
    if (value !== 7 && value !== 30 && value !== 90) return;
    setOpenResult(null);
    setLearningPeriodDaysState(value);
  }, []);

  const continueContentScan = useCallback(async () => {
    const base = responseRef.current;
    const scope = scopeRef.current;
    const cursor = coherentNextCursor(base);
    if (!base || !scope || !cursor || continuationInFlight.current) return;
    if (loadedContentPages >= MAX_CONTENT_PAGES || base.items.length >= MAX_ACCUMULATED_ITEMS) {
      setContinuationStatus("capped");
      return;
    }

    const controller = new AbortController();
    continuationController.current?.abort();
    continuationController.current = controller;
    continuationInFlight.current = true;
    const sequence = ++continuationSequence.current;
    setContinuationStatus("loading");
    setContinuationError(null);
    setLastContinuationAddedCount(null);
    try {
      const page = await fetchTriageQuery({
        schemaVersion: 4,
        dataset: "automatic",
        scope,
        limit: 100,
        contentCursor: cursor,
      }, controller.signal);
      if (controller.signal.aborted || sequence !== continuationSequence.current) return;
      const current = responseRef.current;
      if (!current) return;
      const merged = mergeTriagePages(current, page);
      const nextPageCount = loadedContentPages + 1;
      setResponse(merged.response);
      responseRef.current = merged.response;
      setLoadedContentPages(nextPageCount);
      setLastContinuationAddedCount(merged.addedItemCount);
      const capReached = merged.capped
        || merged.response.items.length >= MAX_ACCUMULATED_ITEMS
        || nextPageCount >= MAX_CONTENT_PAGES;
      setContinuationStatus(capReached ? "capped" : coherentNextCursor(merged.response) ? "idle" : "exhausted");
      const currentActive = activeIdRef.current;
      if (currentActive && !merged.response.items.some((item) => item.itemId === currentActive && item.inspect)) {
        setActiveId(null);
        activeIdRef.current = null;
      }
    } catch (error: unknown) {
      if (controller.signal.aborted || sequence !== continuationSequence.current) return;
      setContinuationError(asTriageError(error));
      setContinuationStatus("error");
    } finally {
      if (sequence === continuationSequence.current) {
        continuationInFlight.current = false;
        continuationController.current = null;
      }
    }
  }, [loadedContentPages]);

  const retryInspect = useCallback(() => {
    const cardId = activeIdRef.current
      ? responseRef.current?.items.find((item) => item.itemId === activeIdRef.current)?.inspect?.cardId
      : null;
    if (cardId) inspectCache.current.delete(cardId);
    setInspectVersion((value) => value + 1);
  }, []);

  const openInAnki = useCallback(async () => {
    if (!activeItem?.inspect || openPending) return;
    setOpenPending(true);
    const result = await runReportAction("open-search-selection", {
      mode: "cards",
      entityIds: [activeItem.inspect.cardId],
    });
    setOpenResult(result);
    setOpenPending(false);
  }, [activeItem, openPending]);

  const scannedNoteCount = response?.sourceStatus.contentCandidates.scannedNoteCount ?? 0;
  const hasMoreContent = continuationStatus !== "capped" && !!coherentNextCursor(response);

  return {
    queryStatus,
    queryError,
    response,
    learningPeriodDays,
    setLearningPeriodDays,
    activeId,
    activeItem,
    inspectStatus,
    inspectError,
    inspectResponse,
    openPending,
    openResult,
    continuationStatus,
    continuationError,
    loadedContentPages,
    scannedNoteCount,
    hasMoreContent,
    lastContinuationAddedCount,
    activate,
    clearActive,
    refresh,
    continueContentScan,
    retryInspect,
    openInAnki,
  };
}

function coherentNextCursor(response: TriageQueryResponse | null): string | null {
  if (!response) return null;
  const source = response.sourceStatus.contentCandidates;
  const checks = response.contentChecks;
  if (!source.truncated || !checks.truncated) return null;
  if (!source.nextCursor || source.nextCursor !== checks.nextCursor) return null;
  return source.nextCursor;
}

function asTriageError(error: unknown): TriageApiError {
  return error instanceof TriageApiError
    ? error
    : new TriageApiError("Triage request failed.", { code: "triage_failed", status: 0 });
}

function asSearchError(error: unknown): SearchApiError {
  return error instanceof SearchApiError
    ? error
    : new SearchApiError("Card details are unavailable.", { code: "search_failed", status: 0 });
}
