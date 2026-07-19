// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import i18n from "../i18n";
import { runReportAction } from "../lib/actionsApi";
import SearchPage from "./SearchPage";

vi.mock("../lib/actionsApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/actionsApi")>();
  return { ...actual, runReportAction: vi.fn() };
});
vi.mock("../lib/telemetryApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/telemetryApi")>();
  return { ...actual, emitTelemetryEvent: vi.fn().mockResolvedValue({ ok: true, code: "telemetry.disabled", queued: false }) };
});

const actionMock = vi.mocked(runReportAction);
const card = {
  cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese", noteTypeId: "7", noteTypeName: "Basic",
  templateOrdinal: 0, templateName: "Card 1", displayText: "【に】（する）", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false,
  state: "review", due: 1, interval: 10, repetitions: 5, lapses: 0, flag: 0, tagSummary: ["jp"],
};
const note = {
  noteId: "2001", noteTypeId: "7", noteTypeName: "Basic", primaryText: "日本語", tagSummary: ["jp"], cardCount: 1,
  deckSummary: [{ deckId: "3", deckName: "Japanese" }],
};

describe("Search workspace", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    window.history.replaceState(null, "", "/?token=test-token#/search");
    window.sessionStorage.clear();
    await i18n.changeLanguage("ru");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    actionMock.mockReset();
    actionMock.mockResolvedValue({ ok: true, action: "open-search-selection", resultCode: "search.browser_opened", requestedCount: 1 });
  });

  afterEach(async () => {
    vi.unstubAllGlobals();
    await act(async () => root.unmount());
    container.remove();
  });

  it("runs only on explicit submit and sends schemaVersion 2", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => success(queryResponse("cards", [card])));
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await change(queryInput(), "deck:Private tag:secret");
    expect(fetchMock).not.toHaveBeenCalled();
    await click(button("Найти"));
    await settle();
    const [url, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse(String(init?.body));
    expect(url).toBe("/api/search/query?token=test-token");
    expect(body.schemaVersion).toBe(2);
    expect(body.query).toBe("deck:Private tag:secret");
    expect(String(url)).not.toContain("Private");
  });

  it("renders canonical card identity in the row and matching Inspector heading", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).includes("/inspect")) return success(cardInspect(card));
      return success(queryResponse("cards", [card]));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    expect(container.textContent?.match(/【に】（する）/g)).toHaveLength(1);
    await click(container.querySelector<HTMLButtonElement>(".search-row-button")!);
    await settle();
    expect(container.textContent?.match(/【に】（する）/g)?.length).toBeGreaterThanOrEqual(2);
    const inspectBody = JSON.parse(String(fetchMock.mock.calls.find(([url]) => String(url).includes("/inspect"))![1]?.body));
    expect(inspectBody.schemaVersion).toBe(2);
  });

  it("keeps note-mode primaryText and clears card-only filters", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => success(queryResponse("notes", [note])));
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    const selects = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-controls-row select"));
    await change(selects.find((item) => item.textContent?.includes("Любое состояние"))!, "suspended");
    await click(container.querySelector<HTMLInputElement>('input[name="search-mode"][value="notes"]')!);
    expect(container.textContent).not.toContain("Любое состояние");
    await click(button("Найти"));
    await settle();
    expect(container.textContent).toContain("日本語");
    const body = JSON.parse(String(fetchMock.mock.calls[0]![1]?.body));
    expect(body.schemaVersion).toBe(2);
    expect(body.mode).toBe("notes");
  });

  it("localizes media-only and unavailable card identities in RU and EN", async () => {
    const fallbackRows = [
      { ...card, cardId: "1001", displayText: "", displayStatus: "media_only", displaySource: "reviewer_front" },
      { ...card, cardId: "1002", noteId: "2002", displayText: "", displayStatus: "unavailable", displaySource: "none" },
    ];
    vi.stubGlobal("fetch", vi.fn(async () => success(queryResponse("cards", fallbackRows))));
    await renderPage();
    await click(button("Найти"));
    await settle();
    expect(container.textContent).toContain("Карточка только с медиа");
    expect(container.textContent).toContain("Текст карточки недоступен");
    await act(async () => { await i18n.changeLanguage("en"); });
    expect(container.textContent).toContain("Card with media only");
    expect(container.textContent).toContain("Card text unavailable");
  });

  it("keeps page selection and Browser handoff exact-ID based", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => success(queryResponse("cards", [card]))));
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('thead input[type="checkbox"]')!);
    expect(container.textContent).toContain("Выбрано: 1");
    await click(button("Открыть в Anki Browser"));
    await settle();
    expect(actionMock).toHaveBeenCalledWith("open-search-selection", { mode: "cards", entityIds: ["1001"] });
  });

  it("aborts the previous query and applies only the latest v2 response", async () => {
    const pending: Array<{ signal?: AbortSignal; resolve: (response: Response) => void }> = [];
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((resolve) => pending.push({ signal: init?.signal as AbortSignal, resolve }))));
    await renderPage();
    await change(queryInput(), "first");
    await click(button("Найти"));
    await change(queryInput(), "second");
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(pending[0]!.signal?.aborted).toBe(true);
    pending[1]!.resolve(success(queryResponse("cards", [{ ...card, displayText: "latest" }])));
    await settle();
    pending[0]!.resolve(success(queryResponse("cards", [{ ...card, displayText: "stale" }])));
    await settle();
    expect(container.textContent).toContain("latest");
    expect(container.textContent).not.toContain("stale");
  });

  it("refreshes active v2 inspect details after an entity action", async () => {
    let inspectCalls = 0;
    let queryCalls = 0;
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).includes("/api/search/inspect")) { inspectCalls += 1; return success(cardInspect(card, `inspect-${inspectCalls}`)); }
      if (String(input).includes("/api/entities/cards/actions")) return entitySuccess();
      queryCalls += 1;
      return success(queryResponse("cards", [card]));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLButtonElement>(".search-row-button")!);
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    await click(button("Приостановить"));
    await settleMany();
    expect(queryCalls).toBe(2);
    expect(inspectCalls).toBe(2);
  });

  async function renderPage() { await act(async () => root.render(<SearchPage report={mockReport} loadState="ready" />)); }
  function queryInput() { return container.querySelector<HTMLInputElement>(".search-query-field input")!; }
  function button(text: string) { return Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find((item) => item.textContent === text)!; }
});

async function change(element: HTMLInputElement | HTMLSelectElement, value: string) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype, "value")!.set!;
    setter.call(element, value);
    element.dispatchEvent(new Event(element instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
  });
}
async function click(element: HTMLElement) { await act(async () => element.click()); }
async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
async function settleMany() { await act(async () => { for (let index = 0; index < 8; index += 1) await Promise.resolve(); }); }
function success(response: unknown) { return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } }); }
function entitySuccess() { return success({ schemaVersion: 1, entityType: "cards", action: "suspend", requestedCount: 1, affectedCount: 1, unchangedCount: 0, undoable: true, resultCode: "cards.suspended", args: {}, requestId: "entity-action-1" }); }
function queryResponse(mode: "cards" | "notes", items: unknown[], overrides: Record<string, unknown> = {}) {
  const pageSize = 50; const boundedTotal = items.length;
  return { schemaVersion: 2, mode, items, page: 1, pageSize, pageCount: Math.ceil(boundedTotal / pageSize), pageLimit: 40, returnedCount: items.length, boundedTotal, hasNext: false, truncated: false, sort: { key: "entity_id", direction: "asc" }, requestId: "search-1", ...overrides };
}
function cardInspect(value: typeof card, requestId = "inspect-1") {
  return { schemaVersion: 2, mode: "cards", requestId, details: { ...value, deck: { deckId: value.deckId, deckName: value.deckName }, noteType: { noteTypeId: value.noteTypeId, noteTypeName: value.noteTypeName }, template: { ordinal: value.templateOrdinal, name: value.templateName }, queue: 2, tags: value.tagSummary, renderedPreview: { renderStatus: "sanitized", frontHtml: `<div>${value.displayText}</div>`, frontPlainText: value.displayText, mediaRefs: [] } } };
}
