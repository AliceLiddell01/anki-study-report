import { describe, expect, it } from "vitest";
import type { TriageItem, TriageReason } from "../types/triage";
import { compareTriageItems, compareTriageReasons, strongestPriority } from "./triageOrdering";

function reason(code: string, priority: "high" | "medium" | "low", detectedAtMs: number): TriageReason {
  return {
    reasonId: `${code}:${detectedAtMs}`,
    code,
    family: code.startsWith("content.") ? "content" : "learning",
    scope: "card",
    priority,
    sources: [code.startsWith("content.") ? "profile_checks" : "attention"],
    evidence: [],
    detectedAtMs,
  };
}

function item(cardId: string, value: TriageReason): TriageItem {
  return {
    itemId: `card:${cardId}`,
    availability: "available",
    cardId,
    noteId: `2${cardId}`,
    deck: { deckId: "1", name: "Deck" },
    noteType: { noteTypeId: "2", name: "Basic" },
    template: { ordinal: 0, name: "Card 1" },
    displayText: cardId,
    displaySource: "reviewer_front",
    displayStatus: "available",
    displayTruncated: false,
    priority: value.priority,
    primaryReasonCode: value.code,
    reasons: [value],
    sources: value.sources,
    cardState: { state: "review", suspended: false, buried: false, flag: 0 },
    inspect: { mode: "cards", cardId },
  };
}

describe("canonical Cards ordering", () => {
  it("mirrors backend priority, reason, recency, and card-id order", () => {
    const values = [
      item("5", reason("content.audio_missing", "medium", 30)),
      item("3", reason("learning.repeated_again", "high", 10)),
      item("2", reason("learning.leech", "high", 20)),
      item("1", reason("learning.leech", "high", 40)),
    ].sort(compareTriageItems);
    expect(values.map((value) => value.cardId)).toEqual(["1", "2", "3", "5"]);
  });

  it("orders reasons without inventing a numeric risk score", () => {
    const values = [
      reason("content.audio_missing", "medium", 1),
      reason("learning.slow_answer", "high", 1),
      reason("learning.leech", "high", 1),
    ].sort(compareTriageReasons);
    expect(values.map((value) => value.code)).toEqual([
      "learning.leech",
      "learning.slow_answer",
      "content.audio_missing",
    ]);
    expect(strongestPriority("medium", "high")).toBe("high");
  });
});
