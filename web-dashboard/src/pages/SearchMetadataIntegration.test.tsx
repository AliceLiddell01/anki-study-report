// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import i18n from "../i18n";
import SearchPage from "./SearchPage";

const card = {
  cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese", noteTypeId: "7", noteTypeName: "Basic",
  templateOrdinal: 0, templateName: "Card 1", displayText: "日本語", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false,
  state: "review", due: 1, interval: 10, repetitions: 5, lapses: 0, flag: 0, tagSummary: ["jp"],
};

describe("Search live metadata", () => {
  let container: HTMLDivElement;
  let root: ReturnType<typeof createRoot>;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    window.history.replaceState(null, "", "/?token=test-token#/search");
    window.sessionStorage.clear();
    await i18n.changeLanguage("ru");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    vi.unstubAllGlobals();
    await act(async () => root.unmount());
    container.remove();
  });

  it("loads v1 metadata choices and uses a v2 card query", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body || "{}"));
      if (body.kind === "metadata") {
        return success({
          schemaVersion: 1,
          kind: "metadata",
          decks: [
            { deckId: "999", deckName: "Outside Scope", filtered: false },
            { deckId: "998", deckName: "Filtered Search Deck", filtered: true },
          ],
          noteTypes: [{ noteTypeId: "77", noteTypeName: "Outside Type" }],
          decksTruncated: false,
          noteTypesTruncated: false,
          requestId: body.requestId,
        });
      }
      expect(body.schemaVersion).toBe(2);
      return success({
        schemaVersion: 2, mode: "cards", items: [card], page: 1, pageSize: 50, pageCount: 1, pageLimit: 40,
        returnedCount: 1, boundedTotal: 1, hasNext: false, truncated: false,
        sort: { key: "entity_id", direction: "asc" }, requestId: body.requestId,
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    await act(async () => root.render(<SearchPage report={mockReport} loadState="ready" />));

    const filterSelects = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-controls-row select"));
    const deckFilter = filterSelects.find((select) => select.textContent?.includes("Все колоды"))!;
    await act(async () => deckFilter.focus());
    await settle();
    expect(deckFilter.textContent).toContain("Outside Scope");
    expect(deckFilter.textContent).toContain("Filtered Search Deck");
    const noteTypeFilter = filterSelects.find((select) => select.textContent?.includes("Все типы"))!;
    expect(noteTypeFilter.textContent).toContain("Outside Type");

    await act(async () => Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find((button) => button.textContent === "Найти")!.click());
    await settle();
    expect(container.textContent).toContain("日本語");
    await act(async () => container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!.click());
    const destination = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-action-bar select"))
      .find((select) => select.textContent?.includes("Outside Scope"))!;
    expect(destination.textContent).toContain("Outside Scope");
    expect(destination.textContent).not.toContain("Filtered Search Deck");
  });
});

async function settle() {
  await act(async () => {
    for (let index = 0; index < 8; index += 1) await Promise.resolve();
  });
}

function success(response: unknown) {
  return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } });
}
