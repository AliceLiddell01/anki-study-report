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

describe("Statistics visual system", () => {
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

  it("renders five route destinations with active state and the four-layer overview hierarchy", async () => {
    await render("overview");
    expect(Array.from(container.querySelectorAll('nav[aria-label="Разделы статистики"] a'), (link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Обзор", "#/stats"], ["Качество", "#/stats/quality"], ["Нагрузка", "#/stats/load"], ["Прогресс", "#/stats/progress"], ["Колоды", "#/stats/decks"],
    ]);
    expect(container.querySelector('nav[aria-label="Разделы статистики"] [aria-current="page"]')?.textContent).toBe("Обзор");
    expect(container.querySelector('[data-testid="statistics-header"] h1')?.textContent).toBe("Статистика");
    expect(container.querySelector('[data-testid="statistics-query-bar"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="statistics-insight"]')).not.toBeNull();
    expect(container.querySelectorAll('[data-testid="statistics-kpi-card"]')).toHaveLength(6);
    expect(container.querySelectorAll(".statistics-chart-panel").length).toBeGreaterThanOrEqual(5);
    expect(queryMock).not.toHaveBeenCalled();
  });

  it("keeps known mixed units in separate panels and starts every bar scale at zero", () => {
    const markup = pageMarkup("overview");
    const reviews = extractTestId(markup, "stats-overview-reviews");
    const time = extractTestId(markup, "stats-overview-time");
    const success = extractTestId(markup, "stats-overview-success");
    expect(reviews).toContain("Повторения");
    expect(reviews).not.toContain("Время, мин");
    expect(time).toContain("Время, мин");
    expect(time).not.toContain("Повторения</span>");
    expect(success).toContain("Успешность");
    expect(success).not.toContain("Средний ответ</span>");
    expect(markup).toContain('data-axis-origin="zero"');
    expect(markup).not.toContain('data-chart-kind="grouped"');
  });

  it("shows six KPI deltas with percentage points, neutral non-color comparison styling and no-baseline state", () => {
    const markup = pageMarkup("overview");
    expect(markup).toContain("+2,4 п.п. к прошлому периоду");
    expect(markup).toContain('data-comparison-style="outline-dashed"');
    const withoutBaseline = reportWith((result) => { result.overview.comparison = { status: "unavailable", reason: "no_previous_data" }; });
    const noBaselineMarkup = renderToStaticMarkup(<StatisticsPage report={withoutBaseline} loadState="ready" section="overview" />);
    expect(noBaselineMarkup).toContain("Нет сопоставимых данных");
    expect(noBaselineMarkup).not.toContain("0% к прошлому периоду");
  });

  it("renders sparse and missing data explicitly without interpolation", () => {
    const sparse = reportWith((result) => {
      result.overview.series = [{ ...result.overview.series[0], successRate: null }];
    });
    const markup = renderToStaticMarkup(<StatisticsPage report={sparse} loadState="ready" section="overview" />);
    expect(markup).toContain("Мало точек: график показывает только доступные значения без интерполяции");
    expect(markup).toContain("Пропуски не заменены нулями");
    expect(markup).toContain("Нет данных");
  });

  it("separates quality percentage trend from Pass/Fail volume and uses Russian user labels", () => {
    const markup = pageMarkup("quality");
    expect(extractTestId(markup, "stats-quality-success")).toContain("Успешность по времени");
    expect(extractTestId(markup, "stats-quality-success")).not.toContain("Успешно</span>");
    expect(extractTestId(markup, "stats-quality-volume")).toContain("Успешно");
    expect(markup).toContain("Снова");
    expect(markup).toContain("Трудно");
    expect(markup).toContain("Хорошо");
    expect(markup).toContain("Легко");
    expect(markup).toContain("Истинное удержание");
    expect(markup).toContain("Зрелые");
    expect(visibleText(markup)).not.toMatch(/STATISTICS V1|True Retention|\bMature\b|\bAgain\b|\bHard\b|\bGood\b|\bEasy\b/i);
  });

  it("renders load summary, unit-separated past charts, stacked future due and assumptions", () => {
    const markup = pageMarkup("load");
    for (const label of ["Просрочено сейчас", "Следующие 7 дней", "Следующие 30 дней", "Средняя нагрузка активного дня"]) expect(markup).toContain(label);
    expect(extractTestId(markup, "stats-load-reviews")).not.toContain("Время, мин");
    expect(extractTestId(markup, "stats-load-time")).not.toContain("Повторения</span>");
    expect(extractTestId(markup, "stats-load-future-due")).toContain('data-chart-kind="stacked"');
    expect(markup).toContain("Изучение");
    expect(markup).toContain("Повторение");
    expect(markup).toContain("Переучивание");
    expect(markup).toContain("Будущие новые карточки и будущие ошибки не учитываются");
    expect(markup).not.toMatch(/Daily load|Σ 1 \/ max|>Learning<|>Review<|>Relearning</);
  });

  it("keeps cards and notes separate and presents current states as a snapshot part-to-whole", () => {
    const markup = pageMarkup("progress");
    expect(markup).toContain("Всего карточек");
    expect(markup).toContain("Всего заметок");
    expect(extractTestId(markup, "stats-progress-current-state")).toContain("Снимок сейчас, а не реконструкция прошлого");
    expect(extractTestId(markup, "stats-progress-current-state")).toContain("statistics-stacked-strip is-state");
    expect(markup).toContain("исторический ряд не восстанавливается");
    expect(extractTestId(markup, "stats-progress-introduced")).toContain("Введённые карточки");
    expect(extractTestId(markup, "stats-progress-introduced")).not.toContain("Молодые</span>");
  });

  it("selects useful decks deterministically, shows comparison initially and marks selected rows beyond color", async () => {
    await render("decks");
    const checked = [...container.querySelectorAll('.statistics-deck-table input[type="checkbox"]:checked')] as HTMLInputElement[];
    expect(checked).toHaveLength(3);
    expect(container.querySelector('[data-testid="stats-deck-comparison-chart"]')?.textContent).toContain("Japanese");
    expect(container.querySelector('[data-testid="stats-deck-comparison-chart"]')?.textContent).toContain("Очень длинная колода 日本語");
    expect(container.querySelectorAll('.statistics-deck-table tr[data-selected="true"]')).toHaveLength(3);
    expect(container.querySelector('.statistics-deck-table tr[data-selected="true"] svg')).not.toBeNull();
    await act(async () => checked[0].click());
    expect(container.querySelectorAll('.statistics-deck-table input[type="checkbox"]:checked')).toHaveLength(2);
    expect(container.querySelector('[data-testid="stats-deck-comparison-chart"]')?.textContent).not.toContain("Japanese1 320");
    expect(text()).not.toMatch(/health|опасная колода|хорошая колода|максимум 12/i);
  });

  it("associates visible chart summaries and structured tables with panel headings", () => {
    const markup = pageMarkup("quality");
    expect(markup).toContain("statistics-chart-summary");
    expect(markup).toContain("Таблица данных");
    expect(markup).toMatch(/<table class="statistics-table" aria-labelledby="statistics-chart-title-/);
    expect(markup).toContain('aria-label="Обозначения графика"');
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain('aria-label="Параметры статистики"');
  });

  it("changes period, explains disabled all-time comparison and sends a typed request", async () => {
    await render("overview");
    await change(selectByLabel("Период"), "all");
    const comparison = inputByLabel("Сравнить периоды");
    expect(comparison.disabled).toBe(true);
    expect(comparison.checked).toBe(false);
    expect(text()).toContain("Для всего времени нет предыдущего периода");
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ period: "all", comparison: false }), expect.any(AbortSignal));
  });

  it("supports dashboard, collection and deck direct/subtree scopes without persistence", async () => {
    await render("overview");
    const scope = selectByLabel("Область");
    await change(scope, "all_collection");
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ scope: { kind: "all_collection" } }), expect.any(AbortSignal));
    await change(scope, "single_deck");
    expect(text()).toContain("С подколодами");
    await act(async () => inputByLabel("Только напрямую").click());
    expect(queryMock).toHaveBeenLastCalledWith(expect.objectContaining({ scope: expect.objectContaining({ kind: "single_deck", mode: "direct" }) }), expect.any(AbortSignal));
    expect(window.localStorage.length).toBe(0);
  });

  it("keeps current content while loading and retries errors", async () => {
    await render("overview");
    queryMock.mockRejectedValueOnce(new Error("Сервер временно недоступен"));
    await change(selectByLabel("Период"), "30d");
    expect(text()).toContain("Сервер временно недоступен");
    queryMock.mockResolvedValueOnce(resultFor("30d"));
    await act(async () => button("Повторить").click());
    expect(text()).not.toContain("Сервер временно недоступен");

  });

  it("does not apply a stale response after a newer query", async () => {
    let resolveOld!: (value: StatisticsResult) => void;
    let resolveNew!: (value: StatisticsResult) => void;
    queryMock.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; })).mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve; }));
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

  it("opens native Anki statistics through the narrow action", async () => {
    await render("overview");
    await act(async () => button("Открыть статистику Anki").click());
    expect(actionMock).toHaveBeenCalledWith("open-native-stats", {});
  });

  async function render(section: StatisticsSection) {
    await act(async () => root.render(<StatisticsPage report={mockReport} loadState="ready" section={section} />));
  }
  function text() { return container.textContent || ""; }
  function button(label: string) { return [...container.querySelectorAll("button")].find((item) => item.textContent?.includes(label)) as HTMLButtonElement; }
  function selectByLabel(label: string) { return [...container.querySelectorAll("label")].find((item) => item.firstChild?.textContent?.trim() === label)?.querySelector("select") as HTMLSelectElement; }
  function inputByLabel(label: string) { return [...container.querySelectorAll("label")].find((item) => item.textContent?.includes(label))?.querySelector("input") as HTMLInputElement; }
});

function pageMarkup(section: StatisticsSection, report = mockReport) {
  return renderToStaticMarkup(<StatisticsPage report={report} loadState="ready" section={section} />);
}

function extractTestId(markup: string, testId: string): string {
  const start = markup.indexOf(`data-testid="${testId}"`);
  if (start < 0) return "";
  const end = markup.indexOf("</section>", start);
  return markup.slice(start, end < 0 ? undefined : end + 10);
}

function visibleText(markup: string): string {
  return markup.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
}

function reportWith(change: (result: StatisticsResult) => void): StudyReport {
  const report = structuredClone(mockReport);
  change(report.statisticsHub!.initialResult);
  return report;
}

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
