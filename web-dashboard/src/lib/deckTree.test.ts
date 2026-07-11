import { describe, expect, it } from "vitest";
import type { DeckHubModel, DeckHubNode } from "../types/report";
import { exactDeckMatch, nearestVisibleSelection, visibleDeckRows } from "./deckTree";

const metric = (reviews: number, passRate: number | null) => ({ reviews, newCards: 0, passCount: passRate === null ? 0 : Math.round(reviews * passRate), failCount: passRate === null ? 0 : reviews - Math.round(reviews * passRate), hardCount: 0, easyCount: 0, passRate, failRate: passRate === null ? null : 1 - passRate, averageAnswerSeconds: reviews ? 10 : null, studySeconds: 0, activeDays: reviews ? 1 : 0, directCardCount: reviews ? 1 : 0 });

function node(deckId: number, fullName: string, parentId: number | null, childIds: number[], status: DeckHubNode["aggregateHealth"] = "neutral", confidence: DeckHubNode["dataConfidence"] = "sufficient", reviews = 10): DeckHubNode {
  return { deckId, fullName, shortName: fullName.split("::").slice(-1)[0]!, parentId, depth: fullName.split("::").length - 1, childIds, filtered: false, structuralOnly: false, directMetrics: metric(reviews, reviews ? 0.8 : null), subtreeMetrics: metric(reviews, reviews ? 0.8 : null), aggregateHealth: status, dataConfidence: confidence, descendantIssueCount: 0, descendantIssues: [], reasons: [], recommendations: [], actions: { includeDescendants: true, directOnly: childIds.length > 0 } };
}

function hub(): DeckHubModel {
  const nodes = [
    node(1, "Words", null, [2, 3], "neutral", "sufficient", 100),
    node(2, "Words::N10", 1, [4], "good", "sufficient", 30),
    node(3, "Words::N2", 1, [], "danger", "sufficient", 20),
    node(4, "Words::N10::Урок", 2, [], "warning", "preliminary", 5),
    node(5, "Grammar", null, [6], "neutral", "sufficient", 40),
    node(6, "Grammar::N2", 5, [], "good", "sufficient", 20),
  ];
  return { schemaVersion: 1, scope: { kind: "all", selectedDeckIds: [], includeChildDecks: true }, summary: { totalDecks: nodes.length, attentionDecks: 2, dangerDecks: 1, groupsWithDescendantIssues: 1, aggregatePassRate: 0.8, filteredDecksExcluded: 0 }, nodes: Object.fromEntries(nodes.map((item) => [String(item.deckId), item])), rootIds: [1, 5] };
}

describe("deckTree", () => {
  it("shows roots and expands only manual branches by default", () => {
    expect(visibleDeckRows(hub(), new Set(), "", "all", "name").map((row) => row.node.deckId)).toEqual([5, 1]);
    expect(visibleDeckRows(hub(), new Set([1]), "", "all", "name").map((row) => row.node.deckId)).toEqual([5, 1, 2, 3]);
  });

  it("searches full/short/non-Latin names and preserves ancestor context", () => {
    const rows = visibleDeckRows(hub(), new Set(), "урок", "all", "name");
    expect(rows.map((row) => row.node.deckId)).toEqual([1, 2, 4]);
    expect(rows.map((row) => row.contextOnly)).toEqual([true, true, false]);
    expect(exactDeckMatch(hub(), "N2")).toBe(6);
    expect(exactDeckMatch(hub(), "Words::N2")).toBe(3);
  });

  it("implements attention, danger and insufficient filters with ancestors", () => {
    expect(visibleDeckRows(hub(), new Set(), "", "attention", "name").map((row) => row.node.deckId)).toEqual([1, 2, 4, 3]);
    expect(visibleDeckRows(hub(), new Set(), "", "danger", "name").map((row) => row.node.deckId)).toEqual([1, 3]);
    expect(visibleDeckRows(hub(), new Set(), "", "insufficient", "name").map((row) => row.node.deckId)).toEqual([1, 2, 4]);
  });

  it("sorts siblings without flattening hierarchy and handles unavailable success deterministically", () => {
    const byStatus = visibleDeckRows(hub(), new Set([1, 5]), "", "all", "status").map((row) => row.node.deckId);
    expect(byStatus).toEqual([5, 6, 1, 3, 2]);
    const byReviews = visibleDeckRows(hub(), new Set([1]), "", "all", "reviews").map((row) => row.node.deckId);
    expect(byReviews).toEqual([1, 2, 3, 5]);
  });

  it("falls selection back to nearest visible ancestor then first visible row", () => {
    expect(nearestVisibleSelection(hub(), new Set([1, 2]), 4)).toBe(2);
    expect(nearestVisibleSelection(hub(), new Set([5]), 4)).toBe(5);
  });
});
