import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSearchMetadata, SearchApiError } from "../lib/searchApi";
import type { SearchMetadataResponse } from "../types/search";

export type SearchMetadataState = ReturnType<typeof useSearchMetadata>;

export function useSearchMetadata() {
  const [response, setResponse] = useState<SearchMetadataResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<SearchApiError | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestSequence = useRef(0);

  useEffect(() => () => abortRef.current?.abort(), []);

  const load = useCallback(async () => {
    if (status === "loading" || status === "ready") return response;
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    requestSequence.current += 1;
    const requestId = `search-metadata-${requestSequence.current}`;
    setStatus("loading");
    setError(null);
    try {
      const value = await fetchSearchMetadata({ kind: "metadata", requestId }, controller.signal);
      if (controller.signal.aborted) return null;
      setResponse(value);
      setStatus("ready");
      return value;
    } catch (value) {
      if (controller.signal.aborted) return null;
      setError(value instanceof SearchApiError
        ? value
        : new SearchApiError("Search metadata failed.", { code: "search_failed", status: 0 }));
      setStatus("error");
      return null;
    }
  }, [response, status]);

  const retry = useCallback(() => {
    setStatus("idle");
    setError(null);
  }, []);

  return { response, status, error, load, retry };
}
