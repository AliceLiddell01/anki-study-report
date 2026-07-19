// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchTriageQuery, parseTriageQueryResponse, TriageApiError } from "./triageApi";

const availableSource = {
  status: "available",
  itemCount: 1,
  skippedCount: 0,
  truncated: false,
  errorCode: null,
};

const item = {
  itemId: "card:1001",
  availability: "available",
  cardId: "1001",
  noteId: "2001",
  deck: { deckId: "3", name: "Languages::Japanese" },
  noteType: { noteTypeId: "7", name: "Basic" },
  template: { ordinal: 0, name: "Card 1" },
  displayText: "日本語",
  displaySource: "browser_question",
  displayStatus: "available",
  displayTruncated: false,
  priority: "high",
  primaryReasonCode: "learning.leech",
  reasons: [{
    reasonId: "learning:learning.leech",
    code: "learning.leech",
    family: "learning",
    scope: "card",
    priority: "high",
    sources: ["attention"],
    evidence: [{ kind: "leech_state", lapses: 8 }],
    detectedAtMs: 1_721_000_000_000,
  }],
  sources: ["attention"],
  cardState: { state: "review", suspended: false, buried: false, flag: 2 },
  inspect: { mode: "cards", cardId: "1001" },
};

const automaticResponse = {
  schemaVersion: 4,
  dataset: "automatic",
  status: "available",
  generatedAtMs: 1_721_000_000_000,
  totalCount: 1,
  returnedCount: 1,
  limit: 100,
  truncated: false,
  sourceStatus: {
    learningCandidates: availableSource,
    contentCandidates: {
      ...availableSource,
      status: "empty",
      itemCount: 0,
      scannedNoteCount: 0,
      nextCursor: null,
    },
    signals: { ...availableSource, status: "empty", itemCount: 0 },
    searchResolver: availableSource,
    profileChecks: { ...availableSource, status: "empty", itemCount: 0 },
  },
  contentChecks: {
    status: "no_confirmed_profiles",
    confirmedProfileCount: 0,
    needsReviewProfileCount: 0,
    disabledProfileCount: 0,
    suggestedProfileCount: 0,
    scannedNoteCount: 0,
    evaluatedNoteCount: 0,
    failedCheckCount: 0,
    skippedCount: 0,
    truncated: false,
    nextCursor: null,
    errorCode: null,
  },
  items: [item],
};

const missingItem = {
  itemId: "card:1002",
  availability: "missing",
  cardId: "1002",
  noteId: null,
  deck: { deckId: null, name: "" },
  noteType: { noteTypeId: null, name: "" },
  template: { ordinal: null, name: "" },
  displayText: "",
  displaySource: "none",
  displayStatus: "unavailable",
  displayTruncated: false,
  priority: null,
  primaryReasonCode: null,
  reasons: [],
  sources: ["search_workset"],
  cardState: { state: null, suspended: null, buried: null, flag: null },
  inspect: null,
};

const worksetResponse = {
  ...automaticResponse,
  dataset: "search_workset",
  totalCount: 1,
  returnedCount: 1,
  limit: 200,
  sourceStatus: {
    learningCandidates: { ...availableSource, status: "not_applicable", itemCount: 0 },
    contentCandidates: {
      ...availableSource,
      status: "not_applicable",
      itemCount: 0,
      scannedNoteCount: 0,
      nextCursor: null,
    },
    signals: { ...availableSource, status: "empty", itemCount: 0 },
    searchResolver: { ...availableSource, status: "empty", itemCount: 0, skippedCount: 1, errorCode: "card_resolution_missing" },
    profileChecks: { ...availableSource, status: "empty", itemCount: 0 },
  },
  items: [missingItem],
};

afterEach(() => vi.unstubAllGlobals());

describe("Triage v4 read API contract", () => {
  it("parses canonical display identity and structured evidence", () => {
    expect(parseTriageQueryResponse(automaticResponse)).toEqual(automaticResponse);
  });

  it("accepts coherent unavailable identity only for missing workset items", () => {
    expect(parseTriageQueryResponse(worksetResponse)).toEqual(worksetResponse);
  });

  it.each([
    ["v3 schema", { ...automaticResponse, schemaVersion: 3 }],
    ["unknown response key", { ...automaticResponse, future: true }],
    ["old primaryText alias", { ...automaticResponse, items: [{ ...item, primaryText: "legacy" }] }],
    ["unknown item key", { ...automaticResponse, items: [{ ...item, future: true }] }],
    ["available without text", { ...automaticResponse, items: [{ ...item, displayText: "" }] }],
    ["media-only with none source", { ...automaticResponse, items: [{ ...item, displayText: "", displayStatus: "media_only", displaySource: "none" }] }],
    ["missing with available identity", { ...worksetResponse, items: [{ ...missingItem, displayText: "legacy", displayStatus: "available", displaySource: "reviewer_front" }] }],
    ["count drift", { ...automaticResponse, returnedCount: 0 }],
    ["invalid enum", { ...automaticResponse, items: [{ ...item, displaySource: "formatter" }] }],
  ])("fails closed for malformed v4 payloads: %s", (_label, value) => {
    expect(() => parseTriageQueryResponse(value)).toThrowError(TriageApiError);
  });

  it("posts schemaVersion 4 in JSON and keeps card IDs out of the URL", async () => {
    window.history.replaceState(null, "", "/?token=secret-token#/cards");
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ ok: true, response: worksetResponse }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const request = {
      schemaVersion: 4 as const,
      dataset: "search_workset" as const,
      cardIds: ["1002"],
      scope: { periodStartMs: 1, periodEndMs: 2, deckIds: [] },
      limit: 200,
    };

    await expect(fetchTriageQuery(request)).resolves.toEqual(worksetResponse);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/triage/query?token=secret-token");
    expect(String(url)).not.toContain("1002");
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });

  it("returns controlled API errors and rejects extra success-envelope fields", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "invalid_triage_request",
      message: "Check request.",
      fieldErrors: { schemaVersion: "Expected schemaVersion 4." },
    }), { status: 400 })));
    await expect(fetchTriageQuery({
      schemaVersion: 4,
      dataset: "automatic",
      contentCursor: null,
      scope: { periodStartMs: 1, periodEndMs: 2, deckIds: [] },
      limit: 100,
    })).rejects.toMatchObject({ code: "invalid_triage_request", status: 400 });

    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response: automaticResponse, extra: true }), { status: 200 })));
    await expect(fetchTriageQuery({
      schemaVersion: 4,
      dataset: "automatic",
      contentCursor: null,
      scope: { periodStartMs: 1, periodEndMs: 2, deckIds: [] },
      limit: 100,
    })).rejects.toMatchObject({ code: "invalid_triage_response" });
  });
});
