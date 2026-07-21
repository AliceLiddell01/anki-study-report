import { describe, expect, it } from "vitest";
import {
  canApplyOperationCompletion,
  inspectCacheKey,
  MAX_INSPECT_CACHE_ENTRIES,
  putBoundedInspectCache,
} from "./cardsWorkspacePolicy";

describe("cards workspace generation policy", () => {
  it("isolates operation completion from a later query generation", () => {
    const operation = { operationId: 1, itemId: "card:1", cardId: "1", queryGeneration: 7 };
    expect(canApplyOperationCompletion(operation, 7)).toBe(true);
    expect(canApplyOperationCompletion(operation, 8)).toBe(false);
  });

  it("keys inspect values by generation and keeps the cache bounded", () => {
    expect(inspectCacheKey(7, "1")).not.toBe(inspectCacheKey(8, "1"));
    const cache = new Map<string, number>();
    for (let index = 0; index <= MAX_INSPECT_CACHE_ENTRIES; index += 1) {
      putBoundedInspectCache(cache, inspectCacheKey(7, String(index)), index);
    }
    expect(cache).toHaveLength(MAX_INSPECT_CACHE_ENTRIES);
    expect(cache.has(inspectCacheKey(7, "0"))).toBe(false);
  });
});
