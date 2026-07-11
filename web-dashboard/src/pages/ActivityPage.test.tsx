// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mockReport } from "../data/mockReport";
import type { ActivityHubModel, StudyReport } from "../types/report";
import CalendarPage from "./CalendarPage";

describe("Activity / Calendar v2", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    window.requestAnimationFrame = (callback) => { callback(0); return 1; };
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders Activity heading, default 90 days and the four real metrics without Forecast", () => {
    const markup = renderToStaticMarkup(<CalendarPage report={mockReport} loadState="ready" />);
    expect(markup).toContain(">Активность</h1>");
    expect(markup).toContain("История занятий, серий и учебного ритма.");
    for (const metric of ["Повторения", "Время", "Новые", "Успешность"]) expect(markup).toContain(metric);
    expect(markup).not.toContain("Прогноз");
    expect(markup).toMatch(/id="activity-period"[^>]*>.*value="90d" selected/);
    expect(markup).toContain('data-testid="activity-calendar"');
    expect(markup).toContain('data-testid="activity-feed"');
  });

  it("selects today by default and distinguishes active, inactive and unavailable details", async () => {
    await renderPage();
    expect(dayButton(mockReport.activityHub!.today).getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector('[data-testid="activity-day-detail"]')?.textContent).toContain("1 319");

    await clickDay("2026-06-25");
    expect(container.querySelector('[data-testid="activity-day-detail"]')?.textContent).toContain("Занятий не было");

    await changeSelect("#activity-period", "1y");
    await clickDay("2025-07-01");
    expect(container.querySelector('[data-testid="activity-day-detail"]')?.textContent).toContain("Статистика для этой даты недоступна");
  });

  it("supports click, arrows, Home/End and Enter/Space selection with accessible labels", async () => {
    await renderPage();
    const today = dayButton("2026-06-29");
    await act(async () => today.focus());
    await act(async () => today.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true })));
    expect((document.activeElement as HTMLElement)?.dataset.date).toBe("2026-06-28");
    await act(async () => document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })));
    expect(dayButton("2026-06-28").getAttribute("aria-pressed")).toBe("true");
    expect(dayButton("2026-06-28").getAttribute("aria-label")).toMatch(/Есть занятия|Занятий не было/);

    await act(async () => dayButton("2026-06-28").dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
    expect((document.activeElement as HTMLElement)?.dataset.date).toBe("2026-06-22");
    await act(async () => document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true })));
    expect((document.activeElement as HTMLElement)?.dataset.date).toBe("2026-06-28");
    await act(async () => document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true })));
    expect(dayButton("2026-06-28").getAttribute("aria-pressed")).toBe("true");
  });

  it("switches metric and period while keeping today selected", async () => {
    await renderPage();
    for (const label of ["Время", "Новые", "Успешность", "Повторения"]) {
      await act(async () => button(label).click());
      expect(button(label).getAttribute("aria-pressed")).toBe("true");
    }
    await changeSelect("#activity-period", "30d");
    expect((container.querySelector("#activity-period") as HTMLSelectElement).value).toBe("30d");
    expect(dayButton(mockReport.activityHub!.today).getAttribute("aria-pressed")).toBe("true");
  });

  it("shows five decks first and expands/collapses the complete selected-day list", async () => {
    await renderPage();
    const detail = container.querySelector('[data-testid="activity-day-detail"]')!;
    expect(detail.querySelectorAll('[data-testid="activity-day-deck-row"]')).toHaveLength(5);
    expect(detail.querySelector('[data-testid="activity-day-deck-row"]')?.textContent).toMatch(/повторений · (\d+%|Нет данных)/);
    expect(detail.textContent).not.toMatch(/Хорошо|Норма|Внимание|Опасно/);
    expect(button("Показать ещё 2").getAttribute("aria-expanded")).toBe("false");
    await act(async () => button("Показать ещё 2").click());
    expect(detail.querySelectorAll('[data-testid="activity-day-deck-row"]')).toHaveLength(7);
    expect(button("Свернуть").getAttribute("aria-expanded")).toBe("true");
    await act(async () => button("Свернуть").click());
    expect(detail.querySelectorAll('[data-testid="activity-day-deck-row"]')).toHaveLength(5);
  });

  it("renders every visible active day, derived highlights and 14 + 14 pagination", async () => {
    await renderPage();
    expect(container.querySelectorAll('[data-feed-type="daily_summary"]').length).toBe(14);
    expect(container.textContent).not.toContain("дневная сводка");
    expect(container.textContent).toContain("серия");
    expect(container.textContent).toContain("рекорд");
    expect(container.querySelectorAll("[data-activity-month]").length).toBeGreaterThan(0);
    expect(uniqueMonthHeadings()).toBe(true);
    expect(container.textContent).toContain("Серия достигла 3 дня");
    expect(container.textContent).toContain("Новый максимум");
    expect(container.textContent).toContain("Итоги завершённой недели");
    expect(container.textContent).toContain("На 12% больше повторений, чем неделей ранее");
    await act(async () => button("Показать более раннюю активность").click());
    expect(container.querySelectorAll('[data-feed-type="daily_summary"]').length).toBe(28);
    expect(uniqueMonthHeadings()).toBe(true);
    expect(container.textContent).toContain("Возвращение после 2 дней без занятий");
    expect(container.textContent).not.toMatch(/leech|deck_improved|deck_declined|лучше|хуже|эффективнее/i);
  });

  it("renders the date as primary calendar text and the selected metric as secondary accessible content", async () => {
    await renderPage();
    const today = dayButton(mockReport.activityHub!.today);
    expect(today.querySelector(".activity-calendar-date")?.textContent).toBe(String(Number(mockReport.activityHub!.today.slice(-2))));
    expect(today.querySelector(".activity-calendar-value")?.textContent).toMatch(/\d|—|н\/д/);
    expect(today.getAttribute("aria-label")).toMatch(/Повторения:/);
  });

  it("renders complete empty and one-day states without fake weekly trends", () => {
    const empty = withHub({ ...mockReport.activityHub!, bounds: { ...mockReport.activityHub!.bounds, availableFrom: null }, days: [], feed: { days: [], weeks: [], pageSize: 14 } });
    const emptyMarkup = renderToStaticMarkup(<CalendarPage report={empty} loadState="ready" />);
    expect(emptyMarkup).toContain("История активности пока пуста");

    const oneDayHub: ActivityHubModel = {
      ...mockReport.activityHub!,
      today: "2026-07-01",
      bounds: { start: "2025-07-02", end: "2026-07-01", availableFrom: "2026-07-01", maxDays: 365 },
      periods: Object.fromEntries(Object.entries(mockReport.activityHub!.periods).map(([key, value]) => [key, { ...value, start: "2026-07-01", end: "2026-07-01" }])) as ActivityHubModel["periods"],
      days: [{ date: "2026-07-01", availability: "active", reviews: 1, newCards: 0, pass: 0, fail: 0, successRate: null, studySeconds: null, activeDeckCount: 1, decks: [{ id: 1, name: "日本語", reviews: 1, pass: 0, fail: 0, successRate: null }] }],
      feed: { days: [{ id: "2026-07-01:daily-summary", type: "daily_summary", date: "2026-07-01", highlights: [] }], weeks: [], pageSize: 14 },
    };
    const oneDayMarkup = renderToStaticMarkup(<CalendarPage report={withHub(oneDayHub)} loadState="ready" />);
    expect((oneDayMarkup.match(/data-feed-type="daily_summary"/g) ?? []).length).toBe(1);
    expect(oneDayMarkup).toContain("Нет данных");
    expect(oneDayMarkup).not.toContain("неделей ранее");
  });

  async function renderPage(report = mockReport) {
    await act(async () => root.render(<CalendarPage report={report} loadState="ready" />));
  }

  function dayButton(date: string) {
    const found = container.querySelector<HTMLButtonElement>(`button[data-date="${date}"]`);
    if (!found) throw new Error(`Day not found: ${date}`);
    return found;
  }

  async function clickDay(date: string) {
    await act(async () => dayButton(date).click());
  }

  function button(text: string) {
    const found = Array.from(container.querySelectorAll("button")).find((item) => item.textContent?.includes(text));
    if (!found) throw new Error(`Button not found: ${text}`);
    return found;
  }

  async function changeSelect(selector: string, value: string) {
    const select = container.querySelector<HTMLSelectElement>(selector)!;
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
    await act(async () => {
      setter?.call(select, value);
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  function uniqueMonthHeadings() {
    const keys = Array.from(container.querySelectorAll<HTMLElement>("[data-activity-month]"), (item) => item.dataset.activityMonth);
    return new Set(keys).size === keys.length;
  }
});

function withHub(activityHub: ActivityHubModel): StudyReport {
  return { ...mockReport, activityHub };
}
