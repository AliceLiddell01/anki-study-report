// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import { runReportAction } from "../lib/actionsApi";
import type { StudyReport } from "../types/report";
import DecksPage from "./DecksPage";

vi.mock("../lib/actionsApi", () => ({ runReportAction: vi.fn() }));
const actionMock = vi.mocked(runReportAction);

describe("Decks v2", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    actionMock.mockReset();
    actionMock.mockResolvedValue({ ok: true, action: "open-deck-browser", message: "Opened deck." });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders the agreed header, four compact metrics and controls", () => {
    const markup = renderToStaticMarkup(<DecksPage report={mockReport} loadState="ready" />);
    expect(markup).toContain(">Колоды</h1>");
    expect(markup).toContain("Состояние структуры колод и области, требующие внимания.");
    for (const label of ["Всего колод", "Требуют внимания", "Опасные", "Средняя успешность"]) expect(markup).toContain(label);
    expect(markup).toContain("Найти колоду…");
    expect(markup).toContain("Все статусы");
    expect(markup).toContain("По имени");
    expect(markup).toContain("Развернуть группы");
    expect(markup).toContain("1 фильтрованная колода не участвует в оценке");
    expect(markup).not.toContain("Фильтрованные колоды не входят в оценку состояния");
    expect(markup).not.toContain("Хорошие колоды");
    expect(markup).not.toContain("Средний ответ</p><p class=\"mt-1 text-xl");
  });

  it("shows roots collapsed, selects the first alphabetical root, and separates disclosure from selection", async () => {
    await renderPage();
    expect(text()).toContain("Grammar");
    expect(text()).toContain("Words");
    expect(text()).not.toContain("Grammar::N2");
    expect(button("Grammar").getAttribute("aria-pressed")).toBe("true");
    const disclosure = container.querySelector('button[aria-label="Развернуть Words"]') as HTMLButtonElement;
    expect(disclosure.getAttribute("aria-expanded")).toBe("false");
    await act(async () => disclosure.click());
    expect(disclosure.getAttribute("aria-expanded")).toBe("true");
    expect(text()).toContain("N3");
    expect(button("Grammar").getAttribute("aria-pressed")).toBe("true");
  });

  it("search reveals ancestor context and clearing restores manual expansion", async () => {
    await renderPage();
    await act(async () => button("Развернуть группы").click());
    expect(button("Свернуть все")).not.toBeNull();
    const search = container.querySelector('input[placeholder="Найти колоду…"]') as HTMLInputElement;
    await input(search, "Урок с очень длинным названием");
    expect(button("Группы раскрыты фильтром").disabled).toBe(true);
    expect(text()).toContain("Words");
    expect(text()).toContain("N3");
    expect(text()).toContain("Урок с очень длинным названием");
    expect(text()).not.toContain("Grammar::N2");
    expect(button("Урок с очень длинным названием", true).getAttribute("aria-pressed")).toBe("true");
    expect(button("Урок с очень длинным названием", true).getAttribute("aria-pressed")).toBe("true");
    await input(search, "");
    expect(container.querySelector('button[title="Words::N3"]')).not.toBeNull();
    expect(container.querySelector('button[title="Words::N3::Урок с очень длинным названием"]')).toBeNull();
  });

  it("expands only root groups, collapses manual branches, and keeps selection valid", async () => {
    await renderPage();
    await act(async () => button("Развернуть группы").click());
    expect(container.querySelector('button[title="Grammar::N2"]')).not.toBeNull();
    expect(container.querySelector('button[title="Words::N3"]')).not.toBeNull();
    expect(text()).not.toContain("Урок с очень длинным названием");
    await act(async () => container.querySelector<HTMLButtonElement>('button[title="Words::N3"]')!.click());
    await act(async () => button("Свернуть все").click());
    expect(text()).not.toContain("Words::N3");
    expect(container.querySelector('button[aria-pressed="true"]')).not.toBeNull();
    expect(button("Развернуть группы")).not.toBeNull();
  });

  it("filters attention/danger/insufficient while retaining ancestors and falls selection back", async () => {
    await renderPage();
    const selects = container.querySelectorAll("select");
    await select(selects[0] as HTMLSelectElement, "danger");
    expect(text()).toContain("Words");
    expect(text()).toContain("N3");
    expect(text()).toContain("Урок с очень длинным названием");
    expect(text()).not.toContain("Grammar::N2");
    await select(selects[0] as HTMLSelectElement, "insufficient");
    expect(text()).toContain("予備");
    expect(text()).toContain("Предварительная оценка");
  });

  it("renders direct/subtree distinction, descendant issue navigation and unavailable values honestly", async () => {
    await renderPage();
    await act(async () => button("Words").click());
    expect(text()).toContain("Прямые и иерархические данные");
    expect(text()).toContain("С дочерними:");
    expect(text()).toContain("В самой колоде:");
    expect(text()).toContain("Проблемы внутри");
    expect(container.querySelector('[data-detail-section="identity"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="reasons"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="metrics"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="direct-subtree"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="issues"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="recommendations"]')).not.toBeNull();
    expect(container.querySelector('[data-detail-section="actions"]')).not.toBeNull();
    await act(async () => button("Урок с очень длинным названием", true).click());
    expect(container.querySelector("h2")?.textContent).toContain("Урок с очень длинным названием");

    const report = structuredClone(mockReport) as StudyReport;
    report.deckHub!.nodes["301"].subtreeMetrics.averageAnswerSeconds = null;
    report.deckHub!.nodes["301"].subtreeMetrics.activeDays = null;
    await renderPage(report);
    await act(async () => button("初級", true).click());
    expect(text()).toContain("Нет данных");
  });

  it("sends only deck ID and mode for subtree/direct Browser actions and reports errors", async () => {
    await renderPage();
    await act(async () => button("Words").click());
    await act(async () => button("Открыть с дочерними").click());
    expect(actionMock).toHaveBeenCalledWith("open-deck-browser", { deckId: 101, mode: "subtree" });
    await act(async () => button("Только эта колода").click());
    expect(actionMock).toHaveBeenLastCalledWith("open-deck-browser", { deckId: 101, mode: "direct" });

    actionMock.mockResolvedValueOnce({ ok: false, action: "open-deck-browser", error: "Deck is unavailable." });
    await act(async () => button("Только эта колода").click());
    expect(text()).toContain("Deck is unavailable.");
  });

  it("handles no decks and legacy payload fallback without changing the route contract", () => {
    const empty = structuredClone(mockReport) as StudyReport;
    empty.deckHub = { ...empty.deckHub!, summary: { ...empty.deckHub!.summary, totalDecks: 0 }, nodes: {}, rootIds: [] };
    expect(renderToStaticMarkup(<DecksPage report={empty} loadState="ready" />)).toContain("Колоды пока не найдены");

    const legacy = { ...mockReport, deckHub: undefined };
    const markup = renderToStaticMarkup(<DecksPage report={legacy} loadState="ready" />);
    expect(markup).toContain("Words::N1::Lesson 18");
    expect(markup).not.toContain('role="treegrid"');
    expect(markup).not.toMatch(/min-h-\[[^\]]+\]/);
  });

  it("hides filtered information when no filtered decks were excluded", () => {
    const report = structuredClone(mockReport) as StudyReport;
    report.deckHub!.summary.filteredDecksExcluded = 0;
    const markup = renderToStaticMarkup(<DecksPage report={report} loadState="ready" />);
    expect(markup).not.toContain('data-testid="filtered-decks-info"');
  });

  async function renderPage(report: StudyReport = mockReport) {
    await act(async () => root.render(<DecksPage report={report} loadState="ready" />));
  }

  function text() { return container.textContent || ""; }
  function button(label: string, contains = false) {
    const matches = [...container.querySelectorAll("button")].filter((item) => contains ? item.textContent?.includes(label) : item.getAttribute("title") === label || item.textContent?.trim() === label);
    const result = matches[0] as HTMLButtonElement | undefined;
    if (!result) throw new Error(`Button not found: ${label}`);
    return result;
  }
});

async function input(element: HTMLInputElement, value: string) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    setter.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function select(element: HTMLSelectElement, value: string) {
  await act(async () => {
    element.value = value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
