// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchSearchMetadata } from "./searchApi";

const metadataResponse = {
  schemaVersion: 1,
  kind: "metadata",
  decks: [
    { deckId: "10", deckName: "Languages::Japanese", filtered: false },
    { deckId: "20", deckName: "Filtered", filtered: true },
  ],
  noteTypes: [{ noteTypeId: "7", noteTypeName: "Basic" }],
  decksTruncated: false,
  noteTypesTruncated: false,
  requestId: "metadata-1",
};

afterEach(() => vi.unstubAllGlobals());

describe("Search metadata API", () => {
  it("posts a strict metadata request without a raw query", async () => {
    window.history.replaceState(null, "", "/?token=metadata-token#/search");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true, response: metadataResponse }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchSearchMetadata({ kind: "metadata", requestId: "metadata-1" })).resolves.toEqual(metadataResponse);
    expect(fetchMock).toHaveBeenCalledWith("/api/search/query?token=metadata-token", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ kind: "metadata", requestId: "metadata-1" }),
    }));
  });

  it.each([
    ["numeric deck ID", { ...metadataResponse, decks: [{ deckId: 10, deckName: "Deck", filtered: false }] }],
    ["missing filtered marker", { ...metadataResponse, decks: [{ deckId: "10", deckName: "Deck" }] }],
    ["numeric note type ID", { ...metadataResponse, noteTypes: [{ noteTypeId: 7, noteTypeName: "Basic" }] }],
    ["malformed truncation marker", { ...metadataResponse, decksTruncated: 0 }],
    ["malformed request ID", { ...metadataResponse, requestId: "secret value" }],
  ])("rejects malformed metadata: %s", async (_label, response) => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response }), { status: 200 })));
    await expect(fetchSearchMetadata({ kind: "metadata" })).rejects.toMatchObject({ code: "invalid_search_response" });
  });
});
