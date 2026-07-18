// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCardsTriageWorkspace } from "./useCardsTriageWorkspace";

const triageItems = [item("1001", "First"), item("1002", "Second")];

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ""; });

describe("useCardsTriageWorkspace", () => {
  it("queries automatic v3 once and inspects only the active item through Search v2", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const calls: Array<{ url: string; body: Record<string, unknown> }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}")); calls.push({ url, body });
      if (url.includes("/api/triage/query")) return ok({ schemaVersion: 3, dataset: "automatic", status: "available", generatedAtMs: Date.now(), totalCount: 2, returnedCount: 2, limit: 100, truncated: false, sourceStatus: { attention: source("available", 2), signals: source("empty", 0), searchResolver: source("empty", 0), profileChecks: source("empty", 0) }, contentChecks: { status: "no_confirmed_profiles", confirmedProfileCount: 0, needsReviewProfileCount: 0, disabledProfileCount: 0, suggestedProfileCount: 0, evaluatedNoteCount: 0, failedCheckCount: 0, skippedCount: 0, truncated: false, errorCode: null }, items: triageItems });
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    document.body.innerHTML = '<div id="root"></div>';
    const root = createRoot(document.getElementById("root")!);
    await act(async () => root.render(<Harness />));
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    const triageCall = calls.find((call) => call.url.includes("/api/triage/query"))!;
    expect(triageCall.body.schemaVersion).toBe(3);
    expect(triageCall.body.dataset).toBe("automatic");
    const scope = triageCall.body.scope as { deckIds: string[]; periodStartMs: number; periodEndMs: number };
    expect(scope.deckIds).toEqual(["3"]);
    expect(scope.periodEndMs - scope.periodStartMs).toBe(7 * 24 * 60 * 60 * 1000);
    const inspectCalls = calls.filter((call) => call.url.includes("/api/search/inspect"));
    expect(inspectCalls.map((call) => call.body.cardId)).toEqual(["1001"]);
    expect(inspectCalls[0]!.body.schemaVersion).toBe(2);
    const second = document.querySelector('button[data-card-id="1002"]') as HTMLButtonElement;
    await act(async () => second.click());
    await act(async () => { await Promise.resolve(); });
    expect(calls.filter((call) => call.url.includes("/api/search/inspect")).map((call) => call.body.cardId)).toEqual(["1001", "1002"]);
    await act(async () => root.unmount());
  });
});

function Harness() { const workspace = useCardsTriageWorkspace(["3"]); return <div>{workspace.response?.items.map((value) => <button key={value.cardId} data-card-id={value.cardId} onClick={() => workspace.activate(value)}>{value.displayText}</button>)}</div>; }
function item(cardId: string, displayText: string) { const reason = { reasonId: `learning:${cardId}`, code: "learning.leech", family: "learning", scope: "card", priority: "high", sources: ["attention"], evidence: [{ kind: "leech_state", lapses: 2 }], detectedAtMs: 2 }; return { itemId: `card:${cardId}`, availability: "available", cardId, noteId: `2${cardId}`, deck: { deckId: "3", name: "Deck" }, noteType: { noteTypeId: "7", name: "Basic" }, template: { ordinal: 0, name: "Card 1" }, displayText, displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, priority: "high", primaryReasonCode: "learning.leech", reasons: [reason], sources: ["attention"], cardState: { state: "review", suspended: false, buried: false, flag: 0 }, inspect: { mode: "cards", cardId } }; }
function source(status: string, itemCount: number) { return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null }; }
function ok(response: unknown) { return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } }); }
function searchDetails(cardId: string) { return { schemaVersion: 2, mode: "cards", details: { cardId, noteId: `2${cardId}`, deckId: "3", deckName: "Deck", noteTypeId: "7", noteTypeName: "Basic", templateOrdinal: 0, templateName: "Card 1", displayText: cardId, displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, state: "review", due: 1, interval: 1, repetitions: 1, lapses: 0, flag: 0, tagSummary: [], deck: { deckId: "3", deckName: "Deck" }, noteType: { noteTypeId: "7", noteTypeName: "Basic" }, template: { ordinal: 0, name: "Card 1" }, queue: 2, tags: [], renderedPreview: { renderStatus: "sanitized", frontHtml: `<b>${cardId}</b>`, mediaRefs: [] } } }; }
