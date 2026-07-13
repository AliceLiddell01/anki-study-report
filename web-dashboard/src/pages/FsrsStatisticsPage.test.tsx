// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, beforeAll, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import { fetchFsrs } from "../lib/fsrsApi";
import FsrsStatisticsPage, { type FsrsSection } from "./FsrsStatisticsPage";

vi.mock("../lib/fsrsApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/fsrsApi")>();
  return { ...actual, fetchFsrs: vi.fn() };
});

const fetchMock = vi.mocked(fetchFsrs);
let container: HTMLDivElement;
let root: Root;

beforeAll(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; });

describe("FSRS Statistics", () => {
  beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); fetchMock.mockReset(); });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

  it("renders Statistics and local FSRS navigation with active states", () => {
    const markup = renderToStaticMarkup(<FsrsStatisticsPage report={mockReport} loadState="ready" section="memory" />);
    expect(markup).toContain('href="#/stats/fsrs"');
    expect(markup).toContain('href="#/stats/fsrs/memory" aria-current="page"');
    expect(markup).toContain("Точность модели");
    expect(markup).toContain("Симулятор");
    expect(markup).not.toContain('href="#/fsrs"');
  });

  it("shows disabled state without pretending SM-2 is FSRS", () => {
    const report = structuredClone(mockReport);
    report.statisticsHub!.fsrs = { ...report.statisticsHub!.fsrs, enabled: false, availability: "disabled", supportedFeatures: [] };
    const markup = renderToStaticMarkup(<FsrsStatisticsPage report={report} loadState="ready" section="overview" />);
    expect(markup).toContain("FSRS не включён");
    expect(markup).not.toContain("SM-2");
  });

  it("loads memory lazily and renders distributions with table alternatives", async () => {
    fetchMock.mockResolvedValue({ schemaVersion: 1, operation: "memory", query: { operation: "memory", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" }, period: "90d" }, calculationVersion: "v1", result: {
      availability: "available", studiedCards: 700, estimatedRemembered: 643.2, averageRetrievability: .919, medianRetrievability: .93, medianStabilityDays: 28, medianDifficulty: 5.2, cardsBelowOwnTarget: 120, overdueCards: 14,
      retrievabilityDistribution: [{ label: "80–90%", count: 120, percentage: .171 }], stabilityDistribution: [{ label: "1–3 месяца", count: 240, percentage: .343 }], difficultyDistribution: [{ label: "5–7", count: 300, percentage: .429 }], limitations: ["snapshot_not_history"],
    } });
    await render("memory");
    expect(container.textContent).toContain("Вероятно помните сейчас 643,2 карточек");
    expect(container.textContent).toContain("Стабильность памяти");
    expect(container.querySelectorAll("table").length).toBeGreaterThanOrEqual(3);
    expect(container.textContent).toContain("Снимок текущего состояния");
  });

  it("does not auto-run calibration or simulator and exposes no apply action", async () => {
    await render("calibration");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Рассчитать точность");
    await render("simulator");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Рассчитать");
    expect(container.textContent).not.toMatch(/Применить|Перепланировать|Оптимизировать/);
  });

  it("does not render a previous operation response during a route change", async () => {
    fetchMock.mockResolvedValue({ schemaVersion: 1, operation: "memory", query: { operation: "memory", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" }, period: "90d" }, calculationVersion: "v1", result: {
      availability: "available", studiedCards: 1, estimatedRemembered: .9, averageRetrievability: .9, medianRetrievability: .9, medianStabilityDays: 10, medianDifficulty: 5, cardsBelowOwnTarget: 0, overdueCards: 0,
      retrievabilityDistribution: [], stabilityDistribution: [], difficultyDistribution: [], limitations: [],
    } });
    await render("memory");
    expect(container.querySelector('[data-testid="fsrs-memory"]')).not.toBeNull();
    await act(async () => { root.render(<FsrsStatisticsPage report={mockReport} loadState="ready" section="calibration" />); });
    expect(container.querySelector('[data-testid="fsrs-memory"]')).toBeNull();
    expect(container.textContent).toContain("Рассчитать точность");
  });

  it("sends bounded typed simulator inputs after an explicit click", async () => {
    fetchMock.mockResolvedValue({ schemaVersion: 1, operation: "simulate", query: { operation: "simulate", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" } }, calculationVersion: "v1", result: {
      configuration: mockReport.statisticsHub!.fsrs.configurations[0], current: { desiredRetention: .9, averageReviewsPerDay: 80, averageMinutesPerDay: 20, peakReviews: 120, backlog: 0, daily: [{ day: 1, reviews: 80, minutes: 20 }] }, hypothetical: { desiredRetention: .93, averageReviewsPerDay: 110, averageMinutesPerDay: 28, peakReviews: 150, backlog: 4, daily: [{ day: 1, reviews: 110, minutes: 28 }] }, delta: { reviewsPerDay: 30, minutesPerDay: 8 }, native: true, readOnly: true,
    } });
    await render("simulator");
    const button = [...container.querySelectorAll("button")].find((item) => item.textContent?.includes("Рассчитать"))!;
    await act(async () => button.click());
    expect(fetchMock).toHaveBeenCalledWith(expect.objectContaining({ operation: "simulate", scope: { kind: "deck", deckId: 101 }, simulation: expect.objectContaining({ desiredRetention: .93, horizonDays: 180, maximumReviewsPerDay: 500 }) }), expect.any(AbortSignal));
    expect(container.textContent).toContain("Переход с 90% на 93%");
    expect(container.textContent).toContain("Нативная read-only симуляция Anki");
  });
});

async function render(section: FsrsSection) {
  await act(async () => { root.render(<FsrsStatisticsPage report={mockReport} loadState="ready" section={section} />); await Promise.resolve(); });
  await act(async () => { await Promise.resolve(); });
}
