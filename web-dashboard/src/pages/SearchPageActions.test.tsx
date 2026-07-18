// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import i18n from "../i18n";
import SearchPage from "./SearchPage";

vi.mock("../lib/telemetryApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/telemetryApi")>();
  return { ...actual, emitTelemetryEvent: vi.fn().mockResolvedValue({ ok: true, code: "telemetry.disabled", queued: false }) };
});

const card = {
  cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese", noteTypeId: "7", noteTypeName: "Basic",
  templateOrdinal: 0, templateName: "Card 1", displayText: "日本語", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false,
  state: "review", due: 1, interval: 10, repetitions: 5, lapses: 0, flag: 0, tagSummary: ["jp"],
};
const note = {
  noteId: "2001", noteTypeId: "7", noteTypeName: "Basic", primaryText: "日本語", tagSummary: ["jp"], cardCount: 1,
  deckSummary: [{ deckId: "3", deckName: "Japanese" }],
};

describe("Search v2 action regressions", () => {
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
  });

  afterEach(async () => {
    vi.unstubAllGlobals();
    await act(async () => root.unmount());
    container.remove();
  });

  it("keeps explicit selection across pages and enforces the 200 item cap", async () => {
    vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const request = JSON.parse(String(init?.body));
      const start = (request.page - 1) * 50 + 1;
      const count = request.page <= 4 ? 50 : 1;
      const items = Array.from({ length: count }, (_, index) => ({ ...card, cardId: String(start + index), noteId: String(10_000 + start + index) }));
      return success({ ...queryResponse("cards", items), page: request.page, pageCount: 5, boundedTotal: 201, hasNext: request.page < 5, requestId: request.requestId });
    }));
    await renderPage();
    await click(button("Найти"));
    await settle();
    for (let page = 1; page <= 4; page += 1) {
      await click(container.querySelector<HTMLInputElement>('thead input[type="checkbox"]')!);
      if (page < 4) {
        await click(button("Далее"));
        await settle();
      }
    }
    expect(container.textContent).toContain("Выбрано: 200");
    await click(button("Далее"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('thead input[type="checkbox"]')!);
    expect(container.textContent).toContain("Можно выбрать не больше 200 явных элементов.");
    expect(container.textContent).toContain("Выбрано: 200");
  });

  it("shows card-only actions, prevents duplicate submission, and refreshes after success", async () => {
    let resolveAction!: (value: Response) => void;
    const pendingAction = new Promise<Response>((resolve) => { resolveAction = resolve; });
    let queryCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/api/entities/cards/actions")) return pendingAction;
      queryCalls += 1;
      return success(queryResponse("cards", queryCalls === 1 ? [card] : []));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    expect(button("Приостановить")).toBeTruthy();
    expect(button("Добавить теги")).toBeFalsy();
    expect(button("Отложить")).toBeTruthy();
    await act(async () => {
      button("Приостановить").click();
      button("Приостановить").click();
    });
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/entities/"))).toHaveLength(1);
    expect(button("Приостановить").disabled).toBe(true);
    resolveAction(entitySuccess({ resultCode: "cards.suspended", action: "suspend" }));
    await settleMany();
    expect(queryCalls).toBe(2);
    expect(container.textContent).toContain("Приостановлено карточек: 1");
    expect(container.textContent).toContain("можно отменить в Anki");
    expect(container.textContent).not.toContain("Выбрано: 1");
  });

  it("shows note tag actions only in Notes mode and preserves native tag text", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).includes("/api/entities/notes/actions")) {
        return entitySuccess({ entityType: "notes", action: "add_tags", resultCode: "notes.tags_added" });
      }
      return success(queryResponse("notes", [note]));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(container.querySelector<HTMLInputElement>('input[name="search-mode"][value="notes"]')!);
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    expect(button("Приостановить")).toBeFalsy();
    expect(button("Отложить")).toBeFalsy();
    const addButton = button("Добавить теги");
    expect(addButton.disabled).toBe(true);
    const input = container.querySelector<HTMLInputElement>(".search-tag-action input")!;
    await change(input, "Japanese::Grammar important");
    expect(addButton.disabled).toBe(false);
    await click(addButton);
    await settleMany();
    const actionCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/api/entities/notes/actions"))!;
    expect(JSON.parse(String(actionCall[1]?.body))).toMatchObject({
      action: "add_tags", noteIds: ["2001"], tags: ["Japanese::Grammar important"],
    });
    expect(container.textContent).toContain("Теги добавлены записям: 1");
  });

  it("corrects the page after an action removes the last result", async () => {
    const pages: number[] = [];
    let afterAction = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).includes("/api/entities/cards/actions")) {
        afterAction = true;
        return entitySuccess({ resultCode: "cards.suspended", action: "suspend" });
      }
      const request = JSON.parse(String(init?.body));
      pages.push(request.page);
      if (!afterAction && request.page === 1) return success(queryResponse("cards", [card], { boundedTotal: 51, pageCount: 2, hasNext: true }));
      if (!afterAction && request.page === 2) return success(queryResponse("cards", [{ ...card, cardId: "1051" }], { page: 2, boundedTotal: 51, pageCount: 2 }));
      if (afterAction && request.page === 2) return success(queryResponse("cards", [], { page: 2, boundedTotal: 50, pageCount: 1 }));
      return success(queryResponse("cards", [{ ...card, cardId: "1000" }], { boundedTotal: 50, pageCount: 1 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(button("Далее"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    await click(button("Приостановить"));
    await settleMany();
    expect(pages).toEqual([1, 2, 2, 1]);
    expect(container.textContent).toContain("Страница 1 из 1");
  });

  it("moves cards with the live deck catalog and preserves a deck-filtered query", async () => {
    const queryBodies: Array<Record<string, unknown>> = [];
    let actionBody: Record<string, unknown> | null = null;
    const sourceCard = { ...card, deckId: "201", deckName: "Japanese" };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body || "{}"));
      if (String(input).includes("/api/entities/cards/actions")) {
        actionBody = body;
        return entitySuccess({ action: "move_to_deck", resultCode: "cards.moved", args: { deckId: 101 } });
      }
      if (body.kind === "metadata") return success(metadataResponse(body.requestId));
      queryBodies.push(body);
      return success(queryResponse("cards", [sourceCard], { requestId: body.requestId }));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    const deckFilter = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-controls-row select"))
      .find((select) => Array.from(select.options).some((option) => option.value === "201"))!;
    await change(deckFilter, "201");
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    const destination = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-action-bar select"))
      .find((select) => Array.from(select.options).some((option) => option.value === "101"))!;
    await change(destination, "101");
    await click(button("Переместить"));
    await settleMany();
    expect(actionBody).toMatchObject({ action: "move_to_deck", cardIds: ["1001"], deckId: "101" });
    expect(queryBodies).toHaveLength(2);
    expect(queryBodies[1]?.filters).toEqual(queryBodies[0]?.filters);
    expect(container.textContent).toContain("Перемещено карточек: 1");
  });

  it("localizes a filtered-source move rejection", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body || "{}"));
      if (String(input).includes("/api/entities/cards/actions")) return new Response(JSON.stringify({
        ok: false, error: "cards.filtered_source_unsupported", message: "safe",
      }), { status: 409 });
      if (body.kind === "metadata") return success(metadataResponse(body.requestId));
      return success(queryResponse("cards", [card], { requestId: body.requestId }));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    const destination = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-action-bar select"))
      .find((select) => Array.from(select.options).some((option) => option.value === "101"))!;
    await change(destination, "101");
    await click(button("Переместить"));
    await settleMany();
    expect(container.textContent).toContain("Сначала верните её в домашнюю колоду через Anki");
  });

  it("localizes malformed action responses and aborts the action on unmount", async () => {
    let actionSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).includes("/api/entities/cards/actions")) {
        actionSignal = init?.signal as AbortSignal;
        return Promise.resolve(new Response(JSON.stringify({ ok: true, response: { schemaVersion: 1 } }), { status: 200 }));
      }
      return Promise.resolve(success(queryResponse("cards", [card])));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(button("Найти"));
    await settle();
    await click(container.querySelector<HTMLInputElement>('tbody input[type="checkbox"]')!);
    await click(button("Приостановить"));
    await settleMany();
    expect(container.textContent).toContain("Dashboard получил некорректный ответ действия.");

    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      actionSignal = init?.signal as AbortSignal;
      return new Promise<Response>(() => undefined);
    }));
    await click(button("Приостановить"));
    await act(async () => root.unmount());
    expect(actionSignal?.aborted).toBe(true);
    root = createRoot(container);
  });

  async function renderPage() { await act(async () => root.render(<SearchPage report={mockReport} loadState="ready" />)); }
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
async function settleMany() { await act(async () => { for (let index = 0; index < 10; index += 1) await Promise.resolve(); }); }
function success(response: unknown) { return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } }); }
function entitySuccess(overrides: Record<string, unknown> = {}) {
  return success({ schemaVersion: 1, entityType: "cards", action: "suspend", requestedCount: 1, affectedCount: 1, unchangedCount: 0, undoable: true, resultCode: "cards.suspended", args: {}, requestId: "entity-action-1", ...overrides });
}
function queryResponse(mode: "cards" | "notes", items: unknown[], overrides: Record<string, unknown> = {}) {
  const pageSize = 50; const boundedTotal = items.length;
  return { schemaVersion: 2, mode, items, page: 1, pageSize, pageCount: Math.ceil(boundedTotal / pageSize), pageLimit: 40, returnedCount: items.length, boundedTotal, hasNext: false, truncated: false, sort: { key: "entity_id", direction: "asc" }, requestId: "search-1", ...overrides };
}
function metadataResponse(requestId: unknown) {
  return { schemaVersion: 1, kind: "metadata", decks: [{ deckId: "201", deckName: "Japanese", filtered: false }, { deckId: "101", deckName: "Destination", filtered: false }], noteTypes: [{ noteTypeId: "7", noteTypeName: "Basic" }], decksTruncated: false, noteTypesTruncated: false, requestId };
}
