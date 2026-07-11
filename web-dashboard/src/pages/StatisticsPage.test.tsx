// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import { runReportAction } from "../lib/actionsApi";
import { fetchStatistics } from "../lib/statisticsApi";
import type { StatisticsPeriod, StatisticsResult, StudyReport } from "../types/report";
import StatisticsPage, { type StatisticsSection } from "./StatisticsPage";

vi.mock("../lib/actionsApi", () => ({ runReportAction: vi.fn() }));
vi.mock("../lib/statisticsApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/statisticsApi")>();
  return { ...actual, fetchStatistics: vi.fn() };
});

const queryMock = vi.mocked(fetchStatistics);
const actionMock = vi.mocked(runReportAction);

describe("Statistics v1", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    queryMock.mockReset();
    queryMock.mockImplementation(async (query) => resultFor(query.period));
    actionMock.mockReset();
    actionMock.mockResolvedValue({ ok: true, action: "open-native-stats", message: "Opened." });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders five route-based sidebar destinations and the default 90d overview without a query", async () => {
    await render("overview");
    expect(Array.from(container.querySelectorAll('nav[aria-label="Разделы статистики"] a'), (link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Обзор", "#/stats"], ["Качество", "#/stats/quality"], ["Нагрузка", "#/stats/load"], ["Прогресс", "#/stats/progress"], ["Колоды", "#/stats/decks"],
    ]);
    expect(container.querySelector('nav[aria-label="Разделы статистики"] [aria-current="page"]')?.textContent).toBe("Обзор");
    expect(text()).toContain("Повторения");
    expect(text()).toContain("Время учёбы");
    expect(text()).toContain("Новые карточки и повторения");
    expect(queryMock).not.toHaveBeenCalled();
  });

  it("renders complete Quality, Load, Progress and Deck comparison sections", () => {
    const expected: Record<StatisticsSection, string[]> = {
      overview: ["Повторения и время"],
      quality: ["True Retention", "Кнопки ответа", "Истинное удержание"],
      load: ["Просрочено сейчас", "Daily load", "Будущая нагрузка"],
      progress: ["Всего карточек", "Всего заметок", "Текущее состояние коллекции"],
      decks: ["Сравнение колод", "Непересекающиеся корневые группы", "Очень длинная колода 日本語"],
    };
    for (const section of Object.keys(expected) as StatisticsSection[]) {
      const markup = renderToStaticMarkup(<StatisticsPage report={mockReport} loadState="ready" section={section} />);
      for (const value of expected[section]) expect(markup).toContain(value);
      expect(markup).not.toMatch(/health|опасная колода|хорошая колода/i);
    }
  });

  it("changes period, disables comparison for all-time and sends a typed request", async () => {
    await render("overview");
    const period = selectByLabel("Период");
    await change(period, "all");
    const comparison = inputByLabel("Сравнить с предыдущим периодом") as HTMLInputElement;
    expect(comparison.disabled).toBe(true);
    expect(comparison.checked).toBe(false);
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ period: "all", comparison: false }), expect.any(AbortSignal));
  });

  it("supports dashboard, collection and deck direct/subtree scopes without changing Settings", async () => {
    await render("overview");
    const scope = selectByLabel("Область");
    await change(scope, "all_collection");
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ scope: { kind: "all_collection" } }), expect.any(AbortSignal));
    await change(scope, "single_deck");
    expect(text()).toContain("С подколодами");
    const direct = inputByLabel("Только напрямую") as HTMLInputElement;
    await act(async () => direct.click());
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ scope: expect.objectContaining({ kind: "single_deck", mode: "direct" }) }), expect.any(AbortSignal));
    expect(window.localStorage.length).toBe(0);
  });

  it("keeps current content while loading and offers retry after a query error", async () => {
    await render("overview");
    queryMock.mockRejectedValueOnce(new Error("Сервер временно недоступен"));
    await change(selectByLabel("Период"), "30d");
    expect(text()).toContain("Сервер временно недоступен");
    expect(button("Повторить")).not.toBeNull();
    queryMock.mockResolvedValueOnce(resultFor("30d"));
    await act(async () => button("Повторить").click());
    expect(text()).not.toContain("Сервер временно недоступен");
  });

  it("does not apply a stale response after a newer request", async () => {
    let resolveOld!: (value: StatisticsResult) => void;
    let resolveNew!: (value: StatisticsResult) => void;
    queryMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve; }));
    await render("overview");
    const period = selectByLabel("Период");
    await act(async () => {
      setSelect(period, "30d");
      setSelect(period, "7d");
    });
    await act(async () => resolveNew(resultFor("7d", 707)));
    await act(async () => resolveOld(resultFor("30d", 3030)));
    expect(text()).toContain("707");
    expect(text()).not.toContain("3 030");
  });

  it("opens native Anki Stats through the narrow action", async () => {
    await render("overview");
    await act(async () => button("Открыть статистику Anki").click());
    expect(actionMock).toHaveBeenCalledWith("open-native-stats", {});
  });

  it("provides accessible chart summaries, data tables, labels and no color-only legend", () => {
    const markup = renderToStaticMarkup(<StatisticsPage report={mockReport} loadState="ready" section="quality" />);
    expect(markup).toContain('aria-label="Параметры статистики"');
    expect(markup).toContain('role="img"');
    expect(markup).toContain("Таблица данных");
    expect(markup).toContain("Успешность");
    expect(markup).toContain('aria-current="page"');
  });

  async function render(section: StatisticsSection) {
    await act(async () => root.render(<StatisticsPage report={mockReport} loadState="ready" section={section} />));
  }
  function text() { return container.textContent || ""; }
  function button(label: string) { return [...container.querySelectorAll("button")].find((item) => item.textContent?.includes(label)) as HTMLButtonElement; }
  function selectByLabel(label: string) { return [...container.querySelectorAll("label")].find((item) => item.firstChild?.textContent?.trim() === label)?.querySelector("select") as HTMLSelectElement; }
  function inputByLabel(label: string) { return [...container.querySelectorAll("label")].find((item) => item.textContent?.includes(label))?.querySelector("input") as HTMLInputElement; }
});

function resultFor(period: StatisticsPeriod, reviews?: number): StatisticsResult {
  const result = structuredClone(mockReport.statisticsHub!.initialResult);
  result.query.period = period;
  if (reviews != null) result.overview.kpis.reviews = reviews;
  return result;
}

async function change(element: HTMLSelectElement, value: string) {
  await act(async () => setSelect(element, value));
}

function setSelect(element: HTMLSelectElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
  setter.call(element, value);
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

