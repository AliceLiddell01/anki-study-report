// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TriageItem, TriageQueryResponse, TriageReason } from "../types/triage";
import { useCardsTriageWorkspace } from "./useCardsTriageWorkspace";

const first = item("1001", "First", reason("learning:1", "learning.leech", "high"));
const second = item("1002", "Second", reason("content:2", "content.audio_missing", "medium"));

let latestWorkspace: ReturnType<typeof useCardsTriageWorkspace> | null = null;
let harnessDeckIds = ["3"];

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  latestWorkspace = null;
  harnessDeckIds = ["3"];
});

describe("useCardsTriageWorkspace", () => {
  it("uses an explicit period and performs exactly one bounded continuation request per activation", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const calls: Array<{ url: string; body: Record<string, unknown> }> = [];
    let triageCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}")); calls.push({ url, body });
      if (url.includes("/api/triage/query")) {
        triageCount += 1;
        if (triageCount === 1) return ok(response([first], 500, "500"));
        if (triageCount === 2) return ok(response([first, second], 250, null));
        return ok(response([first], 0, null));
      }
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();

    const initial = calls.find((call) => call.url.includes("/api/triage/query"))!;
    expect(initial.body.schemaVersion).toBe(4);
    expect(initial.body.contentCursor).toBeNull();
    const initialScope = initial.body.scope as { periodStartMs: number; periodEndMs: number; deckIds: string[] };
    expect(initialScope.deckIds).toEqual(["3"]);
    expect(initialScope.periodEndMs - initialScope.periodStartMs).toBe(7 * 86400000);
    expect(latestWorkspace!.activeItem).toBeNull();

    await act(async () => latestWorkspace!.activate(first));
    await flush();
    expect(calls.filter((call) => call.url.includes("/api/search/inspect")).map((call) => call.body.cardId)).toEqual(["1001"]);

    await act(async () => {
      const firstRequest = latestWorkspace!.continueContentScan();
      const ignoredDoubleClick = latestWorkspace!.continueContentScan();
      await Promise.all([firstRequest, ignoredDoubleClick]);
    });
    await waitUntil(() => latestWorkspace?.loadedContentPages === 1);
    const triageCalls = calls.filter((call) => call.url.includes("/api/triage/query"));
    expect(triageCalls).toHaveLength(2);
    expect(triageCalls[1]!.body.contentCursor).toBe("500");
    expect(latestWorkspace!.response!.items.map((value) => value.cardId)).toEqual(["1001", "1002"]);
    expect(latestWorkspace!.scannedNoteCount).toBe(750);
    expect(latestWorkspace!.loadedContentPages).toBe(1);
    expect(latestWorkspace!.continuationStatus).toBe("exhausted");
    expect(latestWorkspace!.activeItem?.cardId).toBe("1001");

    await act(async () => latestWorkspace!.setLearningPeriodDays(30));
    await flush();
    const periodCalls = calls.filter((call) => call.url.includes("/api/triage/query"));
    const periodCall = periodCalls[periodCalls.length - 1]!;
    const periodScope = periodCall.body.scope as { periodStartMs: number; periodEndMs: number };
    expect(periodCall.body.contentCursor).toBeNull();
    expect(periodScope.periodEndMs - periodScope.periodStartMs).toBe(30 * 86400000);
    expect(latestWorkspace!.loadedContentPages).toBe(0);
    expect(latestWorkspace!.scannedNoteCount).toBe(0);
    await act(async () => root.unmount());
  });

  it("preserves usable items and the same cursor after a continuation failure", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const calls: Array<Record<string, unknown>> = [];
    let count = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (!url.includes("/api/triage/query")) return ok(searchDetails(String(body.cardId)));
      calls.push(body); count += 1;
      if (count === 1) return ok(response([first], 500, "500"));
      if (count === 2) return new Response(JSON.stringify({ ok: false, error: "triage_failed", message: "failed" }), { status: 500, headers: { "Content-Type": "application/json" } });
      return ok(response([], 500, null));
    }));
    const root = await mount();
    await act(async () => { await latestWorkspace!.continueContentScan(); });
    expect(latestWorkspace!.continuationStatus).toBe("error");
    expect(latestWorkspace!.response!.items).toHaveLength(1);
    await act(async () => { await latestWorkspace!.continueContentScan(); });
    expect(calls[1]!.contentCursor).toBe("500");
    expect(calls[2]!.contentCursor).toBe("500");
    expect(latestWorkspace!.lastContinuationAddedCount).toBe(0);
    expect(latestWorkspace!.scannedNoteCount).toBe(1000);
    await act(async () => root.unmount());
  });

  it("preserves the current inbox and active item while an explicit refresh is pending", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let queryCount = 0;
    let resolveRefresh: ((value: Response) => void) | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) {
        queryCount += 1;
        if (queryCount === 1) return ok(response([first], 0, null));
        return new Promise<Response>((resolve) => { resolveRefresh = resolve; });
      }
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await waitUntil(() => latestWorkspace?.inspectStatus === "ready");

    await act(async () => latestWorkspace!.refresh());
    await waitUntil(() => latestWorkspace?.refreshStatus === "pending");
    expect(latestWorkspace!.response?.items).toEqual([first]);
    expect(latestWorkspace!.activeItem?.itemId).toBe(first.itemId);

    await act(async () => resolveRefresh?.(ok(response([first, second], 0, null))));
    await waitUntil(() => latestWorkspace?.refreshStatus === "success");
    expect(latestWorkspace!.response?.items).toEqual([first, second]);
    expect(latestWorkspace!.activeItem?.itemId).toBe(first.itemId);
    await act(async () => root.unmount());
  });

  it("prevents stale inspect responses and reuses cached exact-card details", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const inspectCalls: string[] = [];
    let resolveFirst: ((value: Response) => void) | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first, second], 0, null));
      const cardId = String(body.cardId); inspectCalls.push(cardId);
      if (cardId === "1001" && inspectCalls.length === 1) return new Promise<Response>((resolve) => { resolveFirst = resolve; });
      return ok(searchDetails(cardId));
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await act(async () => latestWorkspace!.activate(second));
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.cardId === "1002");
    expect(latestWorkspace!.inspectResponse?.details.cardId).toBe("1002");
    await act(async () => resolveFirst?.(ok(searchDetails("1001"))));
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.cardId === "1002");
    expect(latestWorkspace!.inspectResponse?.details.cardId).toBe("1002");
    await act(async () => latestWorkspace!.activate(first));
    await flush();
    await act(async () => latestWorkspace!.activate(second));
    await flush();
    expect(inspectCalls.filter((value) => value === "1002")).toHaveLength(1);
    await act(async () => root.unmount());
  });

  it("loads a fresh inspect payload for the same active card after explicit refresh", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let inspectCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/search/inspect")) {
        inspectCount += 1;
        const value = searchDetails(String(body.cardId));
        value.details.displayText = inspectCount === 1 ? "stale inspect" : "fresh inspect";
        return ok(value);
      }
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.displayText === "stale inspect");

    await act(async () => latestWorkspace!.refresh());
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.displayText === "fresh inspect");

    expect(inspectCount).toBe(2);
    expect(latestWorkspace!.activeItem?.cardId).toBe("1001");
    await act(async () => root.unmount());
  });

  it("ignores an inspect response from before a refresh generation", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let resolveStale: ((value: Response) => void) | null = null;
    let inspectCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/search/inspect")) {
        inspectCount += 1;
        if (inspectCount === 1) return new Promise<Response>((resolve) => { resolveStale = resolve; });
        const fresh = searchDetails(String(body.cardId));
        fresh.details.displayText = "fresh generation";
        return ok(fresh);
      }
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await act(async () => latestWorkspace!.refresh());
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.displayText === "fresh generation");

    const stale = searchDetails("1001");
    stale.details.displayText = "stale generation";
    await act(async () => resolveStale?.(ok(stale)));
    await flush();

    expect(latestWorkspace!.inspectResponse?.details.displayText).toBe("fresh generation");
    expect(inspectCount).toBe(2);
    await act(async () => root.unmount());
  });

  it("invalidates inspect data when the selected deck context changes", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let inspectCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/search/inspect")) {
        inspectCount += 1;
        const value = searchDetails(String(body.cardId));
        value.details.displayText = `deck generation ${inspectCount}`;
        return ok(value);
      }
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.displayText === "deck generation 1");

    harnessDeckIds = ["4"];
    await act(async () => root.render(<Harness />));
    await waitUntil(() => latestWorkspace?.inspectResponse?.details.displayText === "deck generation 2");

    expect(inspectCount).toBe(2);
    await act(async () => root.unmount());
  });

  it("keeps a deferred mutation globally busy across refresh and isolates its stale completion", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let resolveAction: ((value: Response) => void) | null = null;
    let actionCalls = 0;
    let openCalls = 0;
    let recheckCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/entities/cards/actions")) {
        actionCalls += 1;
        return new Promise<Response>((resolve) => { resolveAction = resolve; });
      }
      if (url.includes("/api/actions")) {
        openCalls += 1;
        return ok({ ok: true, code: "browser_opened", message: "opened" });
      }
      if (url.includes("/api/triage/recheck")) {
        recheckCalls += 1;
        return ok(recheck(first));
      }
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await flush();
    let pending!: Promise<void>;
    await act(async () => { pending = latestWorkspace!.runSafeAction("suspend"); await Promise.resolve(); });
    expect(latestWorkspace!.mutationPending).toBe(true);

    await act(async () => latestWorkspace!.refresh());
    await waitUntil(() => latestWorkspace?.queryStatus === "ready" && latestWorkspace?.activeItem?.cardId === "1001");
    expect(latestWorkspace!.mutationPending).toBe(true);
    expect(latestWorkspace!.resolution).toBeNull();
    await act(async () => {
      await latestWorkspace!.runSafeAction("bury");
      await latestWorkspace!.openInAnki();
      await latestWorkspace!.recheckActive();
    });
    expect(actionCalls).toBe(1);
    expect(openCalls).toBe(0);
    expect(recheckCalls).toBe(0);

    await act(async () => {
      resolveAction?.(ok({
        schemaVersion: 1,
        entityType: "cards",
        action: "suspend",
        requestedCount: 1,
        affectedCount: 1,
        unchangedCount: 0,
        undoable: true,
        resultCode: "action.cards_suspended",
        args: {},
        requestId: "old-generation",
      }));
      await pending;
    });
    expect(latestWorkspace!.mutationPending).toBe(false);
    expect(latestWorkspace!.resolution).toBeNull();
    expect(latestWorkspace!.lastOutcome).toBeNull();
    expect(latestWorkspace!.response?.items.map((value) => value.cardId)).toEqual(["1001"]);
    await act(async () => root.unmount());
  });

  it("keeps a deferred mutation busy across a period transition", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let resolveAction: ((value: Response) => void) | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/entities/cards/actions")) return new Promise<Response>((resolve) => { resolveAction = resolve; });
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    let pending!: Promise<void>;
    await act(async () => { pending = latestWorkspace!.runSafeAction("suspend"); await Promise.resolve(); });
    await act(async () => latestWorkspace!.setLearningPeriodDays(30));
    await waitUntil(() => latestWorkspace?.learningPeriodDays === 30 && latestWorkspace?.queryStatus === "ready");
    expect(latestWorkspace!.mutationPending).toBe(true);
    await act(async () => {
      resolveAction?.(ok({
        schemaVersion: 1, entityType: "cards", action: "suspend", requestedCount: 1,
        affectedCount: 1, unchangedCount: 0, undoable: true,
        resultCode: "action.cards_suspended", args: {}, requestId: "period-transition",
      }));
      await pending;
    });
    expect(latestWorkspace!.mutationPending).toBe(false);
    expect(latestWorkspace!.resolution).toBeNull();
    await act(async () => root.unmount());
  });

  it("keeps action success separate from recheck and removes only a canonically resolved card", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const calls: string[] = [];
    const resolved = { ...first, priority: null, primaryReasonCode: null, reasons: [], sources: [], cardState: { ...first.cardState, state: "suspended" as const, suspended: true } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}")); calls.push(url);
      if (url.includes("/api/triage/query")) return ok(response([first, second], 0, null));
      if (url.includes("/api/entities/cards/actions")) return ok({ schemaVersion: 1, entityType: "cards", action: "suspend", requestedCount: 1, affectedCount: 0, unchangedCount: 1, undoable: false, resultCode: "action.no_changes", args: {}, requestId: body.requestId });
      if (url.includes("/api/triage/recheck")) return ok(recheck(resolved));
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await flush();
    await act(async () => { await latestWorkspace!.runSafeAction("suspend"); });
    expect(latestWorkspace!.resolution?.phase).toBe("awaiting_recheck");
    expect(latestWorkspace!.response!.items).toHaveLength(2);
    expect(calls.filter((url) => url.includes("/api/triage/recheck"))).toHaveLength(0);
    await act(async () => { await latestWorkspace!.recheckActive(); });
    expect(latestWorkspace!.lastOutcome?.phase).toBe("resolved");
    expect(latestWorkspace!.lastOutcome?.reconciliation?.removed.map((value) => value.reasonId)).toEqual(["learning:1"]);
    expect(latestWorkspace!.response!.items.map((value) => value.cardId)).toEqual(["1002"]);
    expect(latestWorkspace!.activeItem?.cardId).toBe("1002");
    expect(latestWorkspace!.focusRequest.itemId).toBe("card:1002");
    await act(async () => root.unmount());
  });

  it("reconciles removed, remaining, and new reasons but fails closed on partial evidence", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const oldContent = reason("profile:old", "content.audio_missing", "medium");
    const newContent = reason("profile:new", "content.image_missing", "low");
    const combined: TriageItem = { ...first, reasons: [first.reasons[0]!, oldContent], sources: ["attention", "profile_checks"] };
    let recheckCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([combined], 0, null));
      if (url.includes("/api/triage/recheck")) {
        recheckCount += 1;
        if (recheckCount === 1) return ok(recheck({ ...combined, priority: "medium", primaryReasonCode: oldContent.code, reasons: [oldContent, newContent], sources: ["profile_checks"] }));
        return ok(recheck({ ...combined, priority: null, primaryReasonCode: null, reasons: [], sources: [] }, "partial"));
      }
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(combined));
    await flush();
    await act(async () => { await latestWorkspace!.recheckActive(); });
    expect(latestWorkspace!.resolution?.phase).toBe("partially_resolved");
    expect(latestWorkspace!.resolution?.reconciliation?.removed.map((value) => value.reasonId)).toEqual(["learning:1"]);
    expect(latestWorkspace!.resolution?.reconciliation?.remaining.map((value) => value.reasonId)).toEqual(["profile:old"]);
    expect(latestWorkspace!.resolution?.reconciliation?.added.map((value) => value.reasonId)).toEqual(["profile:new"]);
    expect(latestWorkspace!.activeItem?.primaryReasonCode).toBe("content.audio_missing");
    await act(async () => { await latestWorkspace!.recheckActive(); });
    expect(latestWorkspace!.resolution?.phase).toBe("evidence_stale");
    expect(latestWorkspace!.response!.items).toHaveLength(1);
    await act(async () => root.unmount());
  });

  it("reports action failure without rechecking or removing the item", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}")); calls.push(url);
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/entities/cards/actions")) return new Response(JSON.stringify({ ok: false, error: "entity_action_stale", message: "stale" }), { status: 409, headers: { "Content-Type": "application/json" } });
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await flush();
    await act(async () => { await latestWorkspace!.runSafeAction("suspend"); });
    expect(latestWorkspace!.resolution?.phase).toBe("action_failed");
    expect(latestWorkspace!.resolution?.actionError?.code).toBe("entity_action_stale");
    expect(latestWorkspace!.response!.items).toHaveLength(1);
    expect(calls.some((url) => url.includes("/api/triage/recheck"))).toBe(false);
    await act(async () => root.unmount());
  });

  it("prevents an older recheck response from overwriting the latest result", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    let resolveOld: ((value: Response) => void) | null = null;
    let count = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = JSON.parse(String(init?.body || "{}"));
      if (url.includes("/api/triage/query")) return ok(response([first], 0, null));
      if (url.includes("/api/triage/recheck")) {
        count += 1;
        if (count === 1) return new Promise<Response>((resolve) => { resolveOld = resolve; });
        return ok(recheck(first));
      }
      if (url.includes("/api/search/inspect")) return ok(searchDetails(String(body.cardId)));
      throw new Error(`unexpected ${url}`);
    }));
    const root = await mount();
    await act(async () => latestWorkspace!.activate(first));
    await flush();
    let oldRequest!: Promise<void>;
    await act(async () => { oldRequest = latestWorkspace!.recheckActive(); await Promise.resolve(); });
    await act(async () => { await latestWorkspace!.recheckActive(); });
    expect(latestWorkspace!.resolution?.phase).toBe("still_active");
    const empty = { ...first, priority: null, primaryReasonCode: null, reasons: [], sources: [] };
    await act(async () => { resolveOld?.(ok(recheck(empty))); await oldRequest; });
    expect(latestWorkspace!.resolution?.phase).toBe("still_active");
    expect(latestWorkspace!.response!.items).toHaveLength(1);
    await act(async () => root.unmount());
  });
});

async function mount() {
  document.body.innerHTML = '<div id="root"></div>';
  const root = createRoot(document.getElementById("root")!);
  await act(async () => root.render(<Harness />));
  await flush();
  return root;
}

function Harness() {
  latestWorkspace = useCardsTriageWorkspace(harnessDeckIds);
  return <div>{latestWorkspace.queryStatus}:{latestWorkspace.response?.items.length ?? 0}:{latestWorkspace.continuationStatus}</div>;
}

async function flush() {
  await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
}

async function waitUntil(predicate: () => boolean, attempts = 50) {
  for (let index = 0; index < attempts; index += 1) {
    if (predicate()) return;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)); });
  }
  throw new Error("condition did not become true");
}

function reason(id: string, code: string, priority: "high" | "medium" | "low"): TriageReason {
  return { reasonId: id, code, family: code.startsWith("content.") ? "content" : "learning", scope: code.startsWith("content.") ? "note" : "card", priority, sources: [code.startsWith("content.") ? "profile_checks" : "attention"], evidence: code.startsWith("content.") ? [{ kind: "profile_check", profileId: "note-type-7", checkId: "c", checkKind: "contains_audio", roles: ["audio"], fields: [], expectedCondition: "contains_audio", actualTextLength: null, expectedTextLength: null, marker: "audio", markerPresent: false, profileRevision: 1, fingerprint: "a".repeat(64), affectedSiblingCount: 1, templateOrdinals: [] }] : [{ kind: "leech_state", lapses: 8 }], detectedAtMs: 2 };
}
function item(cardId: string, displayText: string, itemReason: TriageReason): TriageItem {
  return { itemId: `card:${cardId}`, availability: "available", cardId, noteId: `2${cardId}`, deck: { deckId: "3", name: "Deck" }, noteType: { noteTypeId: "7", name: "Basic" }, template: { ordinal: 0, name: "Card 1" }, displayText, displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, priority: itemReason.priority, primaryReasonCode: itemReason.code, reasons: [itemReason], sources: itemReason.sources, cardState: { state: "review", suspended: false, buried: false, flag: 0 }, inspect: { mode: "cards", cardId } };
}
function response(values: TriageItem[], scanned: number, cursor: string | null): TriageQueryResponse {
  const truncated = cursor !== null;
  return { schemaVersion: 4, dataset: "automatic", status: "available", generatedAtMs: Date.now(), totalCount: values.length, returnedCount: values.length, limit: 100, truncated: false, sourceStatus: { learningCandidates: source("available", values.length), contentCandidates: { ...source(values.length ? "available" : "empty", values.length), scannedNoteCount: scanned, truncated, nextCursor: cursor }, signals: source("empty", 0), searchResolver: source("available", values.length), profileChecks: source(values.length ? "available" : "empty", values.length) }, contentChecks: { status: "available", confirmedProfileCount: 1, needsReviewProfileCount: 0, disabledProfileCount: 0, suggestedProfileCount: 0, scannedNoteCount: scanned, evaluatedNoteCount: scanned, failedCheckCount: values.length, skippedCount: 0, truncated, nextCursor: cursor, errorCode: null }, items: values };
}
function source(status: "available" | "empty", itemCount: number) { return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null } as const; }
function ok(responseValue: unknown) { return new Response(JSON.stringify({ ok: true, response: responseValue }), { status: 200, headers: { "Content-Type": "application/json" } }); }
function searchDetails(cardId: string) { return { schemaVersion: 2, mode: "cards", requestId: `cards-${cardId}`, details: { cardId, noteId: `2${cardId}`, deckId: "3", deckName: "Deck", noteTypeId: "7", noteTypeName: "Basic", templateOrdinal: 0, templateName: "Card 1", displayText: cardId, displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, state: "review", due: 1, interval: 1, repetitions: 1, lapses: 0, flag: 0, tagSummary: [], deck: { deckId: "3", deckName: "Deck" }, noteType: { noteTypeId: "7", noteTypeName: "Basic" }, template: { ordinal: 0, name: "Card 1" }, queue: 2, tags: [], renderedPreview: { renderStatus: "sanitized", frontHtml: `<b>${cardId}</b>`, backHtml: `<i>${cardId}</i>`, frontPlainText: cardId, backPlainText: cardId, css: "", mediaRefs: [], cardOrd: 0, cardId: Number(cardId), renderSource: "anki_native" } } }; }
function recheck(recheckItem: TriageItem, status: "available" | "partial" = "available") { return { schemaVersion: 1, cardId: recheckItem.cardId, expectedNoteId: recheckItem.noteId, status, entityStatus: "available", generatedAtMs: Date.now(), sourceStatus: { learningCandidates: source("empty", 0), signals: source("empty", 0), searchResolver: source("available", 1), profileChecks: status === "partial" ? { ...source("empty", 0), status: "partial", errorCode: "profile_structures_partial" } : source(recheckItem.reasons.length ? "available" : "empty", recheckItem.reasons.length) }, contentChecks: { status: status === "partial" ? "partial" : "available", confirmedProfileCount: 1, needsReviewProfileCount: status === "partial" ? 1 : 0, disabledProfileCount: 0, suggestedProfileCount: 0, scannedNoteCount: 0, evaluatedNoteCount: 1, failedCheckCount: recheckItem.reasons.length, skippedCount: 0, truncated: false, nextCursor: null, errorCode: status === "partial" ? "profile_structures_partial" : null }, item: recheckItem }; }
