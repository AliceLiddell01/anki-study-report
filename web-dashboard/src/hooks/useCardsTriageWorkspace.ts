import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { runReportAction, type ActionResponse } from "../lib/actionsApi";
import { fetchSearchInspect, SearchApiError } from "../lib/searchApi";
import { fetchTriageQuery, TriageApiError } from "../lib/triageApi";
import type { SearchInspectResponse } from "../types/search";
import type { TriageItem, TriageQueryResponse } from "../types/triage";

export type CardsQueryStatus = "loading" | "ready" | "error";
export type CardsInspectStatus = "idle" | "loading" | "ready" | "error";

export interface CardsTriageWorkspace {
  queryStatus: CardsQueryStatus;
  queryError: TriageApiError | null;
  response: TriageQueryResponse | null;
  activeId: string | null;
  activeItem: TriageItem | null;
  inspectStatus: CardsInspectStatus;
  inspectError: SearchApiError | null;
  inspectResponse: SearchInspectResponse<"cards"> | null;
  openPending: boolean;
  openResult: ActionResponse | null;
  activate: (item: TriageItem) => void;
  clearActive: () => void;
  refresh: () => void;
  retryInspect: () => void;
  openInAnki: () => Promise<void>;
}

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export function useCardsTriageWorkspace(deckIds: string[]): CardsTriageWorkspace {
  const deckKey = deckIds.join(",");
  const stableDeckIds = useMemo(() => deckKey ? deckKey.split(",") : [], [deckKey]);
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
  const querySequence = useRef(0);
  const inspectSequence = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const sequence = ++querySequence.current;
    const periodEndMs = Date.now();
    setQueryStatus("loading");
    setQueryError(null);
    void fetchTriageQuery({
      schemaVersion: 2,
      dataset: "automatic",
      scope: { periodStartMs: periodEndMs - SEVEN_DAYS_MS, periodEndMs, deckIds: stableDeckIds },
      limit: 100,
    }, controller.signal).then((value) => {
      if (controller.signal.aborted || sequence !== querySequence.current) return;
      setResponse(value);
      setQueryStatus("ready");
      setActiveId((current) => {
        const currentStillExists = current && value.items.some((item) => item.itemId === current && item.inspect);
        return currentStillExists ? current : value.items.find((item) => item.inspect)?.itemId ?? null;
      });
    }).catch((error: unknown) => {
      if (controller.signal.aborted || sequence !== querySequence.current) return;
      setQueryError(asTriageError(error));
      setQueryStatus("error");
      setResponse(null);
      setActiveId(null);
    });
    return () => controller.abort();
  }, [refreshVersion, stableDeckIds]);

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
    const controller = new AbortController();
    const sequence = ++inspectSequence.current;
    setInspectStatus("loading");
    setInspectResponse(null);
    setInspectError(null);
    void fetchSearchInspect({ mode: "cards", cardId, requestId: `cards-${sequence}` }, controller.signal)
      .then((value) => {
        if (controller.signal.aborted || sequence !== inspectSequence.current) return;
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
    setActiveId(item.inspect ? item.itemId : null);
  }, []);
  const clearActive = useCallback(() => {
    setOpenResult(null);
    setActiveId(null);
  }, []);

  const refresh = useCallback(() => {
    setOpenResult(null);
    setRefreshVersion((value) => value + 1);
  }, []);

  const retryInspect = useCallback(() => setInspectVersion((value) => value + 1), []);

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

  return {
    queryStatus, queryError, response, activeId, activeItem, inspectStatus, inspectError,
    inspectResponse, openPending, openResult, activate, clearActive, refresh, retryInspect, openInAnki,
  };
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
