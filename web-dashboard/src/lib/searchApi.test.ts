// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import type { SearchQueryRequest } from "../types/search";
import { fetchSearchInspect, fetchSearchMetadata, fetchSearchQuery, SearchApiError } from "./searchApi";

const card = {
  cardId: "1001",
  noteId: "2001",
  deckId: "3",
  deckName: "Languages::Japanese",
  noteTypeId: "7",
  noteTypeName: "Basic",
  templateOrdinal: 0,
  templateName: "Card 1",
  displayText: "日本語",
  displaySource: "browser_question",
  displayStatus: "available",
  displayTruncated: false,
  state: "review",
  due: 1,
  interval: 10,
  repetitions: 5,
  lapses: 0,
  flag: 0,
  tagSummary: ["jp"],
} as const;

const query = {
  schemaVersion: 2,
  mode: "cards",
  query: "deck:Japanese tag:jp",
  filters: [{ type: "deck", deckId: "3" }],
  sort: { key: "entity_id", direction: "asc" },
  page: 1,
  pageSize: 25,
  requestId: "client-1",
} satisfies SearchQueryRequest;

const queryResponse = {
  schemaVersion: 2,
  mode: "cards",
  items: [card],
  page: 1,
  pageSize: 25,
  pageCount: 1,
  pageLimit: 80,
  returnedCount: 1,
  boundedTotal: 1,
  hasNext: false,
  truncated: false,
  sort: { key: "entity_id", direction: "asc" },
  requestId: "client-1",
};

const cardDetails = {
  ...card,
  deck: { deckId: "3", deckName: "Languages::Japanese" },
  noteType: { noteTypeId: "7", noteTypeName: "Basic" },
  template: { ordinal: 0, name: "Card 1" },
  queue: 2,
  tags: ["jp"],
  renderedPreview: {
    renderStatus: "sanitized",
    frontHtml: "<b>日本語</b>",
    backHtml: "<b>Japanese</b>",
    frontPlainText: "日本語",
    backPlainText: "Japanese",
    css: "b { font-weight: 700; }",
    mediaRefs: [],
    cardOrd: 0,
    cardId: 1001,
    renderSource: "anki_native",
    fallbackReason: null,
  },
};

const note = {
  noteId: "2001",
  noteTypeId: "7",
  noteTypeName: "Basic",
  primaryText: "日本語",
  tagSummary: ["jp"],
  cardCount: 1,
  deckSummary: [{ deckId: "3", deckName: "Languages::Japanese" }],
};

const noteDetails = {
  ...note,
  noteType: { noteTypeId: "7", noteTypeName: "Basic" },
  fields: [{ name: "Front", value: "日本語" }],
  tags: ["jp"],
  cardReferences: [{ cardId: "1001", deckId: "3", templateOrdinal: 0 }],
  cardsTruncated: false,
  fieldsTruncated: false,
  deckSummaries: [{ deckId: "3", deckName: "Languages::Japanese" }],
};

afterEach(() => vi.unstubAllGlobals());

describe("Search v2 API contract", () => {
  it("posts the versioned native query in JSON and keeps it out of the URL", async () => {
    window.history.replaceState(null, "", "/?token=secret-token#/search");
    const fetchMock = vi.fn(async () => success(queryResponse));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchSearchQuery(query)).resolves.toEqual(queryResponse);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/search/query?token=secret-token");
    expect(String(url)).not.toContain("Japanese");
    expect(JSON.parse(String(init?.body))).toEqual(query);
  });

  it("keeps Search metadata on its independent v1 contract", async () => {
    const metadata = {
      schemaVersion: 1,
      kind: "metadata",
      decks: [{ deckId: "3", deckName: "Japanese", filtered: false }],
      noteTypes: [{ noteTypeId: "7", noteTypeName: "Basic" }],
      decksTruncated: false,
      noteTypesTruncated: false,
      requestId: "metadata-1",
    };
    vi.stubGlobal("fetch", vi.fn(async () => success(metadata)));
    await expect(fetchSearchMetadata({ kind: "metadata", requestId: "metadata-1" })).resolves.toEqual(metadata);
  });

  it("uses Search inspect v2 and accepts the same card display identity", async () => {
    const response = { schemaVersion: 2, mode: "cards", details: cardDetails, requestId: "inspect-1" };
    const fetchMock = vi.fn(async () => success(response));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchSearchInspect({ schemaVersion: 2, mode: "cards", cardId: "1001", requestId: "inspect-1" })).resolves.toEqual(response);
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]?.body))).toMatchObject({ schemaVersion: 2, cardId: "1001" });
  });

  it("keeps note-mode primaryText distinct from card display identity", async () => {
    const response = { ...queryResponse, mode: "notes", items: [note] };
    vi.stubGlobal("fetch", vi.fn(async () => success(response)));
    const result = await fetchSearchQuery({ ...query, mode: "notes" });
    expect(result.items[0]).toMatchObject({ primaryText: "日本語" });
    expect(result.items[0]).not.toHaveProperty("displayText");

    vi.stubGlobal("fetch", vi.fn(async () => success({ schemaVersion: 2, mode: "notes", details: noteDetails })));
    await expect(fetchSearchInspect({ schemaVersion: 2, mode: "notes", noteId: "2001" })).resolves.toMatchObject({ details: noteDetails });
  });

  it.each([
    ["old schema", { ...queryResponse, schemaVersion: 1 }],
    ["unknown response key", { ...queryResponse, future: true }],
    ["old card primaryText alias", { ...queryResponse, items: [{ ...card, primaryText: "legacy" }] }],
    ["unknown card key", { ...queryResponse, items: [{ ...card, future: true }] }],
    ["invalid display source", { ...queryResponse, items: [{ ...card, displaySource: "formatter" }] }],
    ["available without text", { ...queryResponse, items: [{ ...card, displayText: "" }] }],
    ["media-only with text", { ...queryResponse, items: [{ ...card, displayStatus: "media_only", displayText: "x" }] }],
    ["unavailable with rendered source", { ...queryResponse, items: [{ ...card, displayStatus: "unavailable", displayText: "", displaySource: "reviewer_front" }] }],
    ["truncated unavailable", { ...queryResponse, items: [{ ...card, displayStatus: "unavailable", displayText: "", displaySource: "none", displayTruncated: true }] }],
  ])("rejects malformed v2 payloads: %s", async (_label, response) => {
    vi.stubGlobal("fetch", vi.fn(async () => success(response)));
    await expect(fetchSearchQuery(query)).rejects.toMatchObject({ code: "invalid_search_response" });
  });

  it.each([
    ["unknown details key", { ...cardDetails, future: true }],
    ["missing display field", { ...cardDetails, displayStatus: undefined }],
    ["old primaryText alias", { ...cardDetails, primaryText: "legacy" }],
    ["unknown nested deck key", { ...cardDetails, deck: { ...cardDetails.deck, future: true } }],
  ])("rejects malformed card details: %s", async (_label, details) => {
    vi.stubGlobal("fetch", vi.fn(async () => success({ schemaVersion: 2, mode: "cards", details })));
    await expect(fetchSearchInspect({ schemaVersion: 2, mode: "cards", cardId: "1001" })).rejects.toMatchObject({ code: "invalid_search_response" });
  });

  it("preserves decimal IDs beyond JavaScript safe integer precision", async () => {
    const precise = "9223372036854775807";
    const response = { ...queryResponse, items: [{ ...card, cardId: precise }] };
    vi.stubGlobal("fetch", vi.fn(async () => success(response)));
    const result = await fetchSearchQuery(query);
    expect(result.items[0]!.cardId).toBe(precise);
  });

  it("returns typed errors with field errors and request correlation", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "invalid_search_request",
      message: "Check parameters.",
      fieldErrors: { schemaVersion: "Expected schemaVersion 2." },
      requestId: "client-1",
    }), { status: 400 })));
    await expect(fetchSearchQuery(query)).rejects.toMatchObject({
      name: "SearchApiError",
      code: "invalid_search_request",
      status: 400,
      fieldErrors: { schemaVersion: "Expected schemaVersion 2." },
      requestId: "client-1",
    } satisfies Partial<SearchApiError>);
  });
});

function success(response: unknown) {
  return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } });
}
