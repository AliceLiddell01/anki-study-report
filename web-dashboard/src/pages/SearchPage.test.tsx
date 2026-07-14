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

const actionMock = vi.mocked(runReportAction);
const card = {
  cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese", noteTypeId: "7", noteTypeName: "Basic",
  templateOrdinal: 0, templateName: "Card 1", primaryText: "日本語", state: "review", due: 1, interval: 10,
  repetitions: 5, lapses: 0, flag: 0, tagSummary: ["jp"],
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
    document.documentElement.dataset.theme = "dark";
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

  it("runs only on explicit submit and keeps the native query out of URL and title", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => success(queryResponse("cards", [card])));
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    const title = document.title;
    await change(queryInput(), "deck:Private tag:secret");
    expect(fetchMock).not.toHaveBeenCalled();
    await click(button("Найти"));
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/search/query?token=test-token");
    expect(String(url)).not.toContain("Private");
    expect(JSON.parse(String(init?.body)).query).toBe("deck:Private tag:secret");
    expect(window.location.href).not.toContain("Private");
    expect(document.title).toBe(title);
  });

  it("clears card-only filters when switching to Notes and restores controls from session without auto-query", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    const selects = Array.from(container.querySelectorAll<HTMLSelectElement>(".search-controls-row select"));
    await change(selects.find((item) => item.textContent?.includes("Любое состояние"))!, "suspended");
    await change(selects.find((item) => item.textContent?.includes("Любой флаг"))!, "3");
    await change(queryInput(), "tag:kept");
    await click(container.querySelector<HTMLInputElement>('input[name="search-mode"][value="notes"]')!);
    expect(container.textContent).not.toContain("Любое состояние");
    const stored = JSON.parse(window.sessionStorage.getItem("anki-study-report.search.v1")!);
    expect(stored.query).toBe("tag:kept");
    expect(stored.filters.state).toBe("");
    expect(stored.filters.flag).toBe("");
    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => root.unmount());
    root = createRoot(container);
    await renderPage();
    expect(queryInput().value).toBe("tag:kept");
    expect(container.querySelector<HTMLInputElement>('input[name="search-mode"][value="notes"]')?.checked).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders fixed Card columns, pageCount pagination, page-only selection, and Browser integration", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => success(queryResponse("cards", [card], { boundedTotal: 51, pageCount: 2, hasNext: true }))));
    await renderPage();
    await click(button("Найти"));
    await settle();
    for (const heading of ["Основной текст", "Колода", "Тип записи", "Шаблон", "Состояние", "Срок", "Интервал", "Повторы", "Ошибки", "Флаг"]) {
      expect(tableHeadings()).toContain(heading);
    }
    expect(container.textContent).toContain("Страница 1 из 2");
    await click(container.querySelector<HTMLInputElement>('thead input[type="checkbox"]')!);
    expect(container.textContent).toContain("Выбрано: 1");
    await click(button("Открыть в Anki Browser"));
    await settle();
    expect(actionMock).toHaveBeenCalledWith("open-search-selection", { mode: "cards", entityIds: ["1001"] });
    expect(container.textContent).toContain("В Anki Browser открыто: 1");
  });

  it("renders distinct Note columns and loads compact inspect lazily with a recoverable stale state", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/inspect")) return new Response(JSON.stringify({ ok: false, error: "search_entity_not_found", message: "gone" }), { status: 404 });
      return success(queryResponse("notes", [note]));
    });
    vi.stubGlobal("fetch", fetchMock);
    await renderPage();
    await click(container.querySelector<HTMLInputElement>('input[name="search-mode"][value="notes"]')!);
    await click(button("Найти"));
    await settle();
    expect(tableHeadings()).toEqual(expect.arrayContaining(["Основной текст", "Тип записи", "Теги", "Карточки", "Колоды"]));
    expect(tableHeadings()).not.toContain("Состояние");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await click(container.querySelector<HTMLButtonElement>(".search-row-button")!);
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Элемент удалён или больше недоступен.");
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

  it("aborts the previous query and applies only the latest response", async () => {
    const pending: Array<{ signal?: AbortSignal; resolve: (response: Response) => void }> = [];
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((resolve) => pending.push({ signal: init?.signal as AbortSignal, resolve }))));
    await renderPage();
    await change(queryInput(), "first");
    await click(button("Найти"));
    await change(queryInput(), "second");
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(pending).toHaveLength(2);
    expect(pending[0]!.signal?.aborted).toBe(true);
    pending[1]!.resolve(success(queryResponse("cards", [{ ...card, primaryText: "latest" }])));
    await settle();
    pending[0]!.resolve(success(queryResponse("cards", [{ ...card, primaryText: "stale" }])));
    await settle();
    expect(container.textContent).toContain("latest");
    expect(container.textContent).not.toContain("stale");
  });

  it("renders localized Search in representative light and dark states", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => success(queryResponse("cards", []))));
    document.documentElement.dataset.theme = "light";
    await i18n.changeLanguage("en");
    await renderPage();
    expect(container.querySelector("h1")?.textContent).toBe("Search");
    expect(container.textContent).toContain("Native Anki query");
    document.documentElement.dataset.theme = "dark";
    await act(async () => { await i18n.changeLanguage("ru"); });
    expect(container.querySelector("h1")?.textContent).toBe("Поиск");
  });

  async function renderPage() {
    await act(async () => root.render(<SearchPage report={mockReport} loadState="ready" />));
  }

  function queryInput() { return container.querySelector<HTMLInputElement>(".search-query-field input")!; }
  function button(text: string) { return Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find((item) => item.textContent === text)!; }
  function tableHeadings() { return Array.from(container.querySelectorAll("thead th"), (item) => item.textContent?.trim() ?? ""); }
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
function success(response: unknown) { return new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } }); }
function queryResponse(mode: "cards" | "notes", items: unknown[], overrides: Record<string, unknown> = {}) {
  const pageSize = 50;
  const boundedTotal = items.length;
  return { schemaVersion: 1, mode, items, page: 1, pageSize, pageCount: Math.ceil(boundedTotal / pageSize), pageLimit: 40, returnedCount: items.length, boundedTotal, hasNext: false, truncated: false, sort: { key: "entity_id", direction: "asc" }, requestId: "search-1", ...overrides };
}
