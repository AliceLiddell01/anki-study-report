import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { runReportAction, type ActionResponse } from "../lib/actionsApi";
import { runCardEntityAction, EntityActionApiError } from "../lib/entityActionsApi";
import { fetchSearchInspect, SearchApiError } from "../lib/searchApi";
import { fetchTriageQuery, fetchTriageRecheck, TriageApiError } from "../lib/triageApi";
import {
  canApplyOperationCompletion,
  inspectCacheKey,
  putBoundedInspectCache,
  type GenerationBoundOperation,
} from "../lib/cardsWorkspacePolicy";
import {
  MAX_ACCUMULATED_ITEMS,
  MAX_CONTENT_PAGES,
  mergeTriagePages,
} from "../lib/triagePagination";
import type { SearchInspectResponse } from "../types/search";
import type { CardEntityAction, EntityActionResponse } from "../types/entityActions";
import type { TriageItem, TriageQueryResponse, TriageReason, TriageScope } from "../types/triage";

export type CardsQueryStatus = "loading" | "ready" | "error";
export type CardsInspectStatus = "idle" | "loading" | "ready" | "error";
export type CardsContinuationStatus = "idle" | "loading" | "error" | "exhausted" | "capped";
export type LearningPeriodDays = 7 | 30 | 90;
export type CardsResolutionPhase =
  | "idle"
  | "action_pending"
  | "action_failed"
  | "awaiting_recheck"
  | "rechecking"
  | "still_active"
  | "partially_resolved"
  | "resolved"
  | "recheck_failed"
  | "evidence_stale"
  | "entity_missing"
  | "entity_changed";

export interface CardsReasonReconciliation {
  removed: TriageReason[];
  remaining: TriageReason[];
  added: TriageReason[];
}

export interface CardsResolutionState {
  itemId: string;
  phase: CardsResolutionPhase;
  actionResult: EntityActionResponse | ActionResponse | null;
  actionError: EntityActionApiError | null;
  recheckError: TriageApiError | null;
  reconciliation: CardsReasonReconciliation | null;
}

export interface CardsFocusRequest {
  itemId: string | null;
  version: number;
}

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
  resolution: CardsResolutionState | null;
  lastOutcome: CardsResolutionState | null;
  focusRequest: CardsFocusRequest;
  mutationPending: boolean;
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
  runSafeAction: (action: CardEntityAction) => Promise<void>;
  recheckActive: () => Promise<void>;
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
  const [resolutionById, setResolutionById] = useState<Record<string, CardsResolutionState>>({});
  const [mutationOperation, setMutationOperation] = useState<GenerationBoundOperation | null>(null);
  const [lastOutcome, setLastOutcome] = useState<CardsResolutionState | null>(null);
  const [focusRequest, setFocusRequest] = useState<CardsFocusRequest>({ itemId: null, version: 0 });

  const querySequence = useRef(0);
  const inspectSequence = useRef(0);
  const continuationSequence = useRef(0);
  const continuationController = useRef<AbortController | null>(null);
  const continuationInFlight = useRef(false);
  const actionSequence = useRef(0);
  const actionInFlight = useRef(false);
  const mutationOperationRef = useRef<GenerationBoundOperation | null>(null);
  const openSequence = useRef(0);
  const recheckSequence = useRef(0);
  const recheckController = useRef<AbortController | null>(null);
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
    recheckController.current?.abort();
    recheckController.current = null;
    recheckSequence.current += 1;
    openSequence.current += 1;
    setContinuationStatus("idle");
    setContinuationError(null);
    setLoadedContentPages(0);
    setLastContinuationAddedCount(null);
    setOpenPending(false);
    setOpenResult(null);
    setResolutionById({});
    setLastOutcome(null);
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
    inspectCache.current.clear();

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

  useEffect(() => () => {
    continuationController.current?.abort();
    recheckController.current?.abort();
  }, []);

  const activeItem = useMemo(
    () => response?.items.find((item) => item.itemId === activeId) ?? null,
    [activeId, response],
  );
  const resolution = activeId ? resolutionById[activeId] ?? null : null;
  const mutationPending = mutationOperation !== null;

  const writeResolution = useCallback((itemId: string, value: CardsResolutionState) => {
    setResolutionById((current) => ({ ...current, [itemId]: value }));
  }, []);

  useEffect(() => {
    const cardId = activeItem?.inspect?.cardId;
    if (!cardId) {
      setInspectStatus("idle");
      setInspectResponse(null);
      setInspectError(null);
      return;
    }
    const generation = querySequence.current;
    const cacheKey = inspectCacheKey(generation, cardId);
    const cached = inspectCache.current.get(cacheKey);
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
        if (
          controller.signal.aborted
          || sequence !== inspectSequence.current
          || generation !== querySequence.current
        ) return;
        putBoundedInspectCache(inspectCache.current, cacheKey, value);
        setInspectResponse(value);
        setInspectStatus("ready");
      })
      .catch((error: unknown) => {
        if (
          controller.signal.aborted
          || sequence !== inspectSequence.current
          || generation !== querySequence.current
        ) return;
        setInspectError(asSearchError(error));
        setInspectResponse(null);
        setInspectStatus("error");
      });
    return () => controller.abort();
  }, [activeItem?.itemId, activeItem?.inspect?.cardId, inspectVersion]);

  const activate = useCallback((item: TriageItem) => {
    openSequence.current += 1;
    recheckController.current?.abort();
    recheckSequence.current += 1;
    setOpenPending(false);
    setOpenResult(null);
    const nextId = item.inspect ? item.itemId : null;
    setActiveId(nextId);
    activeIdRef.current = nextId;
  }, []);

  const clearActive = useCallback(() => {
    openSequence.current += 1;
    recheckController.current?.abort();
    recheckSequence.current += 1;
    setOpenPending(false);
    setOpenResult(null);
    setActiveId(null);
    activeIdRef.current = null;
    inspectSequence.current += 1;
    setInspectStatus("idle");
    setInspectResponse(null);
    setInspectError(null);
  }, []);

  const refresh = useCallback(() => {
    querySequence.current += 1;
    setOpenResult(null);
    setRefreshVersion((value) => value + 1);
  }, []);

  const setLearningPeriodDays = useCallback((value: LearningPeriodDays) => {
    if (value !== 7 && value !== 30 && value !== 90) return;
    if (value === learningPeriodDays) return;
    querySequence.current += 1;
    setOpenResult(null);
    setLearningPeriodDaysState(value);
  }, [learningPeriodDays]);

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
    if (cardId) inspectCache.current.delete(inspectCacheKey(querySequence.current, cardId));
    setInspectVersion((value) => value + 1);
  }, []);

  const openInAnki = useCallback(async () => {
    if (!activeItem?.inspect || openPending || mutationPending) return;
    const itemId = activeItem.itemId;
    const sequence = ++openSequence.current;
    const queryGeneration = querySequence.current;
    setOpenPending(true);
    try {
      const result = await runReportAction("open-search-selection", {
        mode: "cards",
        entityIds: [activeItem.inspect.cardId],
      });
      if (sequence !== openSequence.current || queryGeneration !== querySequence.current) return;
      setOpenResult(result);
      writeResolution(itemId, {
        itemId,
        phase: result.ok ? "awaiting_recheck" : "action_failed",
        actionResult: result,
        actionError: null,
        recheckError: null,
        reconciliation: null,
      });
    } finally {
      if (sequence === openSequence.current) setOpenPending(false);
    }
  }, [activeItem, mutationPending, openPending, writeResolution]);

  const runSafeAction = useCallback(async (action: CardEntityAction) => {
    if (!activeItem || actionInFlight.current || mutationOperationRef.current || openPending) return;
    if (["action_pending", "awaiting_recheck", "rechecking"].includes(resolutionById[activeItem.itemId]?.phase ?? "idle")) return;
    if (!["suspend", "unsuspend", "bury", "unbury", "clear_flag"].includes(action)) return;
    const item = activeItem;
    const sequence = ++actionSequence.current;
    const operation: GenerationBoundOperation = {
      operationId: sequence,
      itemId: item.itemId,
      cardId: item.cardId,
      queryGeneration: querySequence.current,
    };
    actionInFlight.current = true;
    mutationOperationRef.current = operation;
    setMutationOperation(operation);
    writeResolution(item.itemId, {
      itemId: item.itemId,
      phase: "action_pending",
      actionResult: null,
      actionError: null,
      recheckError: null,
      reconciliation: null,
    });
    try {
      const result = await runCardEntityAction({
        action,
        cardIds: [item.cardId],
        requestId: `cards-resolution-${sequence}`,
      });
      if (
        sequence !== actionSequence.current
        || !canApplyOperationCompletion(operation, querySequence.current)
      ) return;
      writeResolution(item.itemId, {
        itemId: item.itemId,
        phase: "awaiting_recheck",
        actionResult: result,
        actionError: null,
        recheckError: null,
        reconciliation: null,
      });
      inspectCache.current.delete(inspectCacheKey(operation.queryGeneration, item.cardId));
      setInspectVersion((current) => current + 1);
    } catch (error: unknown) {
      if (
        sequence !== actionSequence.current
        || !canApplyOperationCompletion(operation, querySequence.current)
      ) return;
      writeResolution(item.itemId, {
        itemId: item.itemId,
        phase: "action_failed",
        actionResult: null,
        actionError: asEntityActionError(error),
        recheckError: null,
        reconciliation: null,
      });
    } finally {
      actionInFlight.current = false;
      if (mutationOperationRef.current?.operationId === operation.operationId) {
        mutationOperationRef.current = null;
        setMutationOperation(null);
      }
    }
  }, [activeItem, openPending, resolutionById, writeResolution]);

  const recheckActive = useCallback(async () => {
    const item = activeItem;
    const scope = scopeRef.current;
    if (!item?.noteId || !scope || mutationPending) return;
    const controller = new AbortController();
    recheckController.current?.abort();
    recheckController.current = controller;
    const sequence = ++recheckSequence.current;
    const queryGeneration = querySequence.current;
    writeResolution(item.itemId, {
      itemId: item.itemId,
      phase: "rechecking",
      actionResult: resolutionById[item.itemId]?.actionResult ?? null,
      actionError: null,
      recheckError: null,
      reconciliation: null,
    });
    try {
      const value = await fetchTriageRecheck({
        schemaVersion: 1,
        cardId: item.cardId,
        expectedNoteId: item.noteId,
        reasonIds: item.reasons.map((reason) => reason.reasonId),
        scope,
      }, controller.signal);
      if (
        controller.signal.aborted
        || sequence !== recheckSequence.current
        || queryGeneration !== querySequence.current
      ) return;
      if (value.entityStatus !== "available") {
        inspectCache.current.delete(inspectCacheKey(querySequence.current, item.cardId));
        const phase = value.entityStatus === "missing"
          ? "entity_missing"
          : value.entityStatus === "changed"
            ? "entity_changed"
            : "evidence_stale";
        const outcome: CardsResolutionState = {
          itemId: item.itemId,
          phase,
          actionResult: resolutionById[item.itemId]?.actionResult ?? null,
          actionError: null,
          recheckError: null,
          reconciliation: null,
        };
        writeResolution(item.itemId, outcome);
        setLastOutcome(outcome);
        return;
      }
      if (value.status !== "available" || !value.item) {
        inspectCache.current.delete(inspectCacheKey(querySequence.current, item.cardId));
        const outcome: CardsResolutionState = {
          itemId: item.itemId,
          phase: "evidence_stale",
          actionResult: resolutionById[item.itemId]?.actionResult ?? null,
          actionError: null,
          recheckError: null,
          reconciliation: null,
        };
        writeResolution(item.itemId, outcome);
        setLastOutcome(outcome);
        return;
      }

      const reconciliation = reconcileReasons(item.reasons, value.item.reasons);
      if (value.item.reasons.length > 0) {
        const phase = reconciliation.removed.length > 0 ? "partially_resolved" : "still_active";
        const outcome: CardsResolutionState = {
          itemId: item.itemId,
          phase,
          actionResult: resolutionById[item.itemId]?.actionResult ?? null,
          actionError: null,
          recheckError: null,
          reconciliation,
        };
        setResponse((current) => replaceTriageItem(current, value.item!));
        responseRef.current = replaceTriageItem(responseRef.current, value.item);
        inspectCache.current.delete(inspectCacheKey(querySequence.current, item.cardId));
        setInspectVersion((current) => current + 1);
        writeResolution(item.itemId, outcome);
        setLastOutcome(outcome);
        return;
      }

      const current = responseRef.current;
      inspectCache.current.delete(inspectCacheKey(querySequence.current, item.cardId));
      const index = current?.items.findIndex((candidate) => candidate.itemId === item.itemId) ?? -1;
      const nextResponse = removeTriageItem(current, item.itemId);
      const nextItem = nextResponse?.items[Math.min(Math.max(index, 0), Math.max(nextResponse.items.length - 1, 0))] ?? null;
      const outcome: CardsResolutionState = {
        itemId: item.itemId,
        phase: "resolved",
        actionResult: resolutionById[item.itemId]?.actionResult ?? null,
        actionError: null,
        recheckError: null,
        reconciliation,
      };
      setResponse(nextResponse);
      responseRef.current = nextResponse;
      setActiveId(nextItem?.itemId ?? null);
      activeIdRef.current = nextItem?.itemId ?? null;
      setFocusRequest((currentFocus) => ({ itemId: nextItem?.itemId ?? null, version: currentFocus.version + 1 }));
      writeResolution(item.itemId, outcome);
      setLastOutcome(outcome);
    } catch (error: unknown) {
      if (
        controller.signal.aborted
        || sequence !== recheckSequence.current
        || queryGeneration !== querySequence.current
      ) return;
      const outcome: CardsResolutionState = {
        itemId: item.itemId,
        phase: "recheck_failed",
        actionResult: resolutionById[item.itemId]?.actionResult ?? null,
        actionError: null,
        recheckError: asTriageError(error),
        reconciliation: null,
      };
      writeResolution(item.itemId, outcome);
      setLastOutcome(outcome);
    } finally {
      if (sequence === recheckSequence.current) recheckController.current = null;
    }
  }, [activeItem, mutationPending, resolutionById, writeResolution]);

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
    resolution,
    lastOutcome,
    focusRequest,
    mutationPending,
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
    runSafeAction,
    recheckActive,
  };
}

function reconcileReasons(previous: TriageReason[], current: TriageReason[]): CardsReasonReconciliation {
  const previousIds = new Set(previous.map((reason) => reason.reasonId));
  const currentIds = new Set(current.map((reason) => reason.reasonId));
  return {
    removed: previous.filter((reason) => !currentIds.has(reason.reasonId)),
    remaining: current.filter((reason) => previousIds.has(reason.reasonId)),
    added: current.filter((reason) => !previousIds.has(reason.reasonId)),
  };
}

function replaceTriageItem(response: TriageQueryResponse | null, item: TriageItem): TriageQueryResponse | null {
  if (!response) return null;
  return { ...response, items: response.items.map((value) => value.itemId === item.itemId ? item : value) };
}

function removeTriageItem(response: TriageQueryResponse | null, itemId: string): TriageQueryResponse | null {
  if (!response) return null;
  const items = response.items.filter((item) => item.itemId !== itemId);
  const removed = response.items.length - items.length;
  const totalCount = Math.max(items.length, response.totalCount - removed);
  return {
    ...response,
    items,
    totalCount,
    returnedCount: items.length,
    truncated: totalCount > items.length,
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

function asEntityActionError(error: unknown): EntityActionApiError {
  return error instanceof EntityActionApiError
    ? error
    : new EntityActionApiError("The Anki action failed.", { code: "entity_action_failed", status: 0 });
}
