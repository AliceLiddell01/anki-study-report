// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import type { SearchQueryRequest } from "../types/search";
import { fetchSearchInspect, fetchSearchQuery, SearchApiError } from "./searchApi";


const card = {
  cardId: "1001",
  noteId: "2001",
  deckId: "3",
  deckName: "Languages::Japanese",
  noteTypeId: "7",
  noteTypeName: "Basic",
  templateOrdinal: 0,
  templateName: "Card 1",
  primaryText: "日本語",
  state: "review",
  due: 1,
  interval: 10,
  repetitions: 5,
  lapses: 0,
  flag: 0,
  tagSummary: ["jp"],
};

const query = {
  mode: "cards",
  query: "deck:Japanese tag:jp",
  filters: [{ type: "deck", deckId: "3" }],
  sort: { key: "entity_id", direction: "asc" },
  page: 1,
  pageSize: 25,
  requestId: "client-1",
} satisfies SearchQueryRequest;

const queryResponse = {
  schemaVersion: 1,
  mode: "cards",
  items: [card],
  page: 1,
  pageSize: 25,
  maxPage: 80,
  returnedCount: 1,
  boundedTotal: 1,
  hasNext: false,
  truncated: false,
  sort: { key: "entity_id", direction: "asc" },
  requestId: "client-1",
};

afterEach(() => vi.unstubAllGlobals());

describe("search API foundation", () => {
  it("posts the native query in JSON and never puts it in the URL", async () => {
    window.history.replaceState(null, "", "/?token=secret-token#/home");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ ok: true, response: queryResponse }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchSearchQuery(query)).resolves.toEqual(queryResponse);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/search/query?token=secret-token");
    expect(String(url)).not.toContain("Japanese");
    expect(init).toMatchObject({ method: "POST", cache: "no-store" });
    expect(JSON.parse(String(init?.body))).toEqual(query);
  });

  it("forwards AbortSignal to fetch", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ ok: true, response: queryResponse }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchSearchQuery(query, controller.signal);
    expect(fetchMock.mock.calls[0]![1]?.signal).toBe(controller.signal);
  });

  it("returns typed errors with field errors and request correlation", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "invalid_search_request",
      message: "Check parameters.",
      fieldErrors: { query: "Invalid native query." },
      requestId: "client-1",
    }), { status: 400 })));
    await expect(fetchSearchQuery(query)).rejects.toMatchObject({
      name: "SearchApiError",
      code: "invalid_search_request",
      status: 400,
      fieldErrors: { query: "Invalid native query." },
      requestId: "client-1",
    } satisfies Partial<SearchApiError>);
  });

  it("rejects malformed success payloads and numeric IDs", async () => {
    const malformed = { ...queryResponse, items: [{ ...card, cardId: 1001 }] };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response: malformed }), { status: 200 })));
    await expect(fetchSearchQuery(query)).rejects.toMatchObject({ code: "invalid_search_response" });
  });

  it("preserves decimal IDs beyond JavaScript safe integer precision", async () => {
    const precise = "9223372036854775807";
    const response = { ...queryResponse, items: [{ ...card, cardId: precise }] };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response }), { status: 200 })));
    const result = await fetchSearchQuery(query);
    expect(result.items[0]!.cardId).toBe(precise);
  });

  it("discriminates Notes rows from Cards rows", async () => {
    const noteResponse = {
      ...queryResponse,
      mode: "notes",
      items: [{
        noteId: "2001",
        noteTypeId: "7",
        noteTypeName: "Basic",
        primaryText: "日本語",
        tagSummary: ["jp"],
        cardCount: 1,
        deckSummary: [{ deckId: "3", deckName: "Languages::Japanese" }],
      }],
    };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response: noteResponse }), { status: 200 })));
    const result = await fetchSearchQuery({ ...query, mode: "notes" });
    expect(result.mode).toBe("notes");
    expect(result.items[0]!.noteId).toBe("2001");
  });

  it("normalizes runtime failures separately from validation errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "search_timeout",
      message: "The search request did not finish in time.",
      requestId: "client-1",
    }), { status: 504 })));
    await expect(fetchSearchQuery(query)).rejects.toMatchObject({
      code: "search_timeout",
      status: 504,
      requestId: "client-1",
    });
  });

  it("uses the separate inspect endpoint and validates mode-specific details", async () => {
    const response = { schemaVersion: 1, mode: "cards", details: { ...card, tags: ["jp"] } };
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ ok: true, response }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchSearchInspect({ mode: "cards", cardId: "1001" })).resolves.toEqual(response);
    expect(fetchMock.mock.calls[0]![0]).toContain("/api/search/inspect?token=");
  });
});
