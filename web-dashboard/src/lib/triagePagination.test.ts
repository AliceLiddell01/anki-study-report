import { describe, expect, it } from "vitest";
import type { TriageItem, TriageQueryResponse, TriageReason } from "../types/triage";
import { MAX_ACCUMULATED_ITEMS, mergeTriagePages } from "./triagePagination";

function reason(id: string, code: string, priority: "high" | "medium" | "low"): TriageReason {
  return {
    reasonId: id,
    code,
    family: code.startsWith("content.") ? "content" : "learning",
    scope: code.startsWith("content.") ? "note" : "card",
    priority,
    sources: [code.startsWith("content.") ? "profile_checks" : "attention"],
    evidence: [],
    detectedAtMs: 10,
  };
}

function item(cardId: string, reasons: TriageReason[]): TriageItem {
  return {
    itemId: `card:${cardId}`,
    availability: "available",
    cardId,
    noteId: `2${cardId}`,
    deck: { deckId: "1", name: "Deck" },
    noteType: { noteTypeId: "2", name: "Basic" },
    template: { ordinal: 0, name: "Card 1" },
    displayText: `Card ${cardId}`,
    displaySource: "reviewer_front",
    displayStatus: "available",
    displayTruncated: false,
    priority: reasons[0]?.priority ?? null,
    primaryReasonCode: reasons[0]?.code ?? null,
    reasons,
    sources: [...new Set(reasons.flatMap((value) => value.sources))],
    cardState: { state: "review", suspended: false, buried: false, flag: 0 },
    inspect: { mode: "cards", cardId },
  };
}

function response(items: TriageItem[], scanned: number, cursor: string | null): TriageQueryResponse {
  const truncated = cursor !== null;
  return {
    schemaVersion: 4,
    dataset: "automatic",
    status: "available",
    generatedAtMs: 10,
    totalCount: items.length,
    returnedCount: items.length,
    limit: 100,
    truncated: false,
    sourceStatus: {
      learningCandidates: source("available", 1),
      contentCandidates: { ...source(items.length ? "available" : "empty", items.length), scannedNoteCount: scanned, truncated, nextCursor: cursor },
      signals: source("empty", 0),
      searchResolver: source("available", items.length),
      profileChecks: source(items.length ? "available" : "empty", items.length),
    },
    contentChecks: {
      status: "available",
      confirmedProfileCount: 1,
      needsReviewProfileCount: 0,
      disabledProfileCount: 0,
      suggestedProfileCount: 0,
      scannedNoteCount: scanned,
      evaluatedNoteCount: scanned,
      failedCheckCount: items.length,
      skippedCount: 0,
      truncated,
      nextCursor: cursor,
      errorCode: null,
    },
    items,
  };
}

function source(status: "available" | "empty", itemCount: number) {
  return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null } as const;
}

describe("mergeTriagePages", () => {
  it("dedupes items, reasons, and sources while retaining the strongest reason", () => {
    const learning = reason("learning:1", "learning.repeated_again", "high");
    const content = reason("content:1", "content.audio_missing", "medium");
    const base = response([item("10", [learning])], 500, "500");
    const next = response([item("10", [learning, content]), item("11", [content])], 400, "900");
    const merged = mergeTriagePages(base, next);

    expect(merged.addedItemCount).toBe(1);
    expect(merged.response.items.map((value) => value.cardId)).toEqual(["10", "11"]);
    expect(merged.response.items[0]!.reasons.map((value) => value.reasonId)).toEqual(["learning:1", "content:1"]);
    expect(merged.response.items[0]!.sources).toEqual(["attention", "profile_checks"]);
    expect(merged.response.sourceStatus.contentCandidates.scannedNoteCount).toBe(900);
    expect(merged.response.contentChecks.nextCursor).toBe("900");
  });

  it("advances progress after an empty continuation page without dropping prior issues", () => {
    const base = response([item("10", [reason("learning:1", "learning.leech", "high")])], 500, "500");
    const next = response([], 500, null);
    const merged = mergeTriagePages(base, next);
    expect(merged.addedItemCount).toBe(0);
    expect(merged.response.items).toHaveLength(1);
    expect(merged.response.sourceStatus.contentCandidates.scannedNoteCount).toBe(1000);
    expect(merged.response.sourceStatus.contentCandidates.nextCursor).toBeNull();
  });

  it("caps accumulated unique items without an unbounded client list", () => {
    const baseItems = Array.from({ length: MAX_ACCUMULATED_ITEMS }, (_, index) => item(String(index + 1), [reason(`r:${index}`, "learning.leech", "high")]));
    const merged = mergeTriagePages(response(baseItems, 500, "500"), response([item("9999", [reason("r:new", "content.audio_missing", "medium")])], 500, "1000"));
    expect(merged.capped).toBe(true);
    expect(merged.response.items).toHaveLength(MAX_ACCUMULATED_ITEMS);
    expect(merged.response.truncated).toBe(true);
  });
});
