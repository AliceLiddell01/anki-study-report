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

const automaticResponse = {
  schemaVersion: 1,
  dataset: "automatic",
  status: "available",
  generatedAtMs: 1_721_000_000_000,
  totalCount: 1,
  returnedCount: 1,
  limit: 100,
  truncated: false,
  sourceStatus: {
    attention: availableSource,
    signals: availableSource,
    searchResolver: availableSource,
  },
  contentChecks: { status: "profiles_not_available" },
  items: [{
    itemId: "card:1001",
    availability: "available",
    cardId: "1001",
    noteId: "2001",
    deck: { deckId: "3", name: "Languages::Japanese" },
    noteType: { noteTypeId: "7", name: "Basic" },
    template: { ordinal: 0, name: "Card 1" },
    primaryText: "日本語",
    priority: "high",
    primaryReasonCode: "learning.leech",
    reasons: [
      {
        code: "learning.leech",
        family: "learning",
        scope: "card",
        priority: "high",
        sources: ["attention"],
        evidence: [{ kind: "leech_state", lapses: 8 }],
        detectedAtMs: 1_721_000_000_000,
      },
      {
        code: "learning.repeated_again",
        family: "learning",
        scope: "card",
        priority: "medium",
        sources: ["attention", "signals"],
        evidence: [
          { kind: "signal_evidence", severity: "warning", againCount: 4, reviewCount: 7, windowDays: 7, detectorVersion: "signals-v1.0" },
          { kind: "review_counts", againCount: 4, periodStartMs: 1_700_000_000_000, periodEndMs: 1_700_604_800_000 },
        ],
        detectedAtMs: 1_721_000_000_000,
      },
      {
        code: "learning.low_pass_rate",
        family: "learning",
        scope: "card",
        priority: "medium",
        sources: ["attention"],
        evidence: [{ kind: "pass_rate", passRate: 0.42, periodStartMs: 1_700_000_000_000, periodEndMs: 1_700_604_800_000 }],
        detectedAtMs: null,
      },
      {
        code: "learning.slow_answer",
        family: "learning",
        scope: "card",
        priority: "low",
        sources: ["attention"],
        evidence: [{ kind: "answer_time", averageAnswerSeconds: 12.5, periodStartMs: 1_700_000_000_000, periodEndMs: 1_700_604_800_000 }],
        detectedAtMs: null,
      },
    ],
    sources: ["attention", "signals"],
    cardState: { state: "review", suspended: false, buried: false, flag: 2 },
    inspect: { mode: "cards", cardId: "1001" },
  }],
};

const worksetResponse = {
  schemaVersion: 1,
  dataset: "search_workset",
  status: "available",
  generatedAtMs: 1_721_000_000_000,
  totalCount: 1,
  returnedCount: 1,
  limit: 200,
  truncated: false,
  sourceStatus: {
    attention: { ...availableSource, status: "empty", itemCount: 0 },
    signals: { ...availableSource, status: "empty", itemCount: 0 },
    searchResolver: { ...availableSource, status: "empty", itemCount: 0, skippedCount: 1, errorCode: "card_resolution_missing" },
  },
  contentChecks: { status: "profiles_not_available" },
  items: [{
    itemId: "card:1002",
    availability: "missing",
    cardId: "1002",
    noteId: null,
    deck: { deckId: null, name: "" },
    noteType: { noteTypeId: null, name: "" },
    template: { ordinal: null, name: "" },
    primaryText: "",
    priority: null,
    primaryReasonCode: null,
    reasons: [],
    sources: ["search_workset"],
    cardState: { state: null, suspended: null, buried: null, flag: null },
    inspect: null,
  }],
};

afterEach(() => vi.unstubAllGlobals());

describe("triage read API contract", () => {
  it("parses automatic responses and every structured evidence variant", () => {
    expect(parseTriageQueryResponse(automaticResponse)).toEqual(automaticResponse);
  });

  it("parses neutral Search workset items with null priority and typed missing state", () => {
    expect(parseTriageQueryResponse(worksetResponse)).toEqual(worksetResponse);
  });

  it("fails closed for schema, enum, ID, finite-number, nested-status, and count drift", () => {
    const invalid = [
      { ...automaticResponse, schemaVersion: 2 },
      { ...automaticResponse, status: "future" },
      { ...automaticResponse, items: [{ ...automaticResponse.items[0], cardId: "01" }] },
      { ...automaticResponse, generatedAtMs: Number.NaN },
      {
        ...automaticResponse,
        sourceStatus: { ...automaticResponse.sourceStatus, signals: { ...availableSource, status: "future" } },
      },
      { ...automaticResponse, returnedCount: 0 },
      { ...automaticResponse, truncated: true },
      { ...automaticResponse, unexpected: true },
      {
        ...automaticResponse,
        items: [{ ...automaticResponse.items[0], priority: null }],
      },
    ];
    for (const value of invalid) {
      expect(() => parseTriageQueryResponse(value)).toThrowError(TriageApiError);
    }
  });

  it("posts IDs in JSON, uses the dashboard token, and validates the success envelope", async () => {
    window.history.replaceState(null, "", "/?token=secret-token#/cards");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ ok: true, response: worksetResponse }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const request = {
      schemaVersion: 1 as const,
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
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("returns controlled API errors and rejects extra success-envelope fields", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "invalid_triage_request",
      message: "Check request.",
      fieldErrors: { limit: "invalid" },
    }), { status: 400 })));
    await expect(fetchTriageQuery({
      schemaVersion: 1,
      dataset: "automatic",
      scope: { periodStartMs: 1, periodEndMs: 2, deckIds: [] },
      limit: 100,
    })).rejects.toMatchObject({ code: "invalid_triage_request", status: 400, fieldErrors: { limit: "invalid" } });

    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response: automaticResponse, extra: true }), { status: 200 })));
    await expect(fetchTriageQuery({
      schemaVersion: 1,
      dataset: "automatic",
      scope: { periodStartMs: 1, periodEndMs: 2, deckIds: [] },
      limit: 100,
    })).rejects.toMatchObject({ code: "invalid_triage_response" });
  });
});
