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
    expect(container.textContent).toContain("снимок текущего состояния");
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
    expect(container.textContent).toContain("Цель меняется с 90% на 93%");
    expect(container.textContent).toContain("Симулятор работает только для чтения");
  });

  it("renders an overview verdict, actual-target comparison, configurations, and deeper links", async () => {
    fetchMock.mockResolvedValue({ schemaVersion: 1, operation: "overview", query: { operation: "overview", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" }, period: "90d" }, calculationVersion: "v1", result: {
      configurations: mockReport.statisticsHub!.fsrs.configurations,
      mixedConfiguration: true,
      targetRetentionRange: { min: .88, max: .93 },
      estimatedRemembered: 643.2,
      studiedCards: 700,
      averageRetrievability: .919,
      medianStabilityDays: 28,
      actualRetention: .89,
      dataSufficiency: "sufficient",
      insight: "Фактическое удержание находится внутри диапазона целей.",
    } });

    await render("overview");

    expect(container.textContent).toContain("Главный вывод");
    expect(container.textContent).toContain("Фактическое и целевое удержание");
    expect(container.textContent).toContain("Факт внутри целевого диапазона");
    expect(container.textContent).toContain("Совместимые наборы настроек");
    expect(container.querySelector('a[href="#/stats/fsrs/calibration"]')).not.toBeNull();
  });

  it("shows calibration loading and a sparse-safe calculated result", async () => {
    let resolveRequest!: (value: Awaited<ReturnType<typeof fetchFsrs>>) => void;
    fetchMock.mockImplementation(() => new Promise((resolve) => { resolveRequest = resolve; }));
    await render("calibration");
    const button = [...container.querySelectorAll("button")].find((item) => item.textContent?.includes("Рассчитать точность"))!;
    await act(async () => button.click());
    expect(container.textContent).toContain("Сопоставляем прогнозы и ответы");
    await act(async () => resolveRequest({ schemaVersion: 1, operation: "calibration", query: { operation: "calibration", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" }, period: "90d" }, calculationVersion: "v1", result: {
      configuration: mockReport.statisticsHub!.fsrs.configurations[0], sampleSize: 12, sufficiency: "insufficient", rmseBins: .08, hardIsRecall: true,
      bins: [{ label: "80–90%", predicted: .85, actual: 1, sampleSize: 1, sufficiency: "insufficient" }],
    } }));
    expect(container.textContent).toContain("Пока рано оценивать точность модели");
    expect(container.textContent).toContain("Малая выборка");
    expect(container.textContent).toContain("Таблица данных и методика");
  });

  it("renders insufficient learning steps without overstating one-observation retention", async () => {
    fetchMock.mockResolvedValue({ schemaVersion: 1, operation: "steps", query: { operation: "steps", scope: { kind: "configuration", configurationId: "cfg-10-demo-a1" }, period: "90d" }, calculationVersion: "v1", result: {
      availability: "available", configuration: mockReport.statisticsHub!.fsrs.configurations[0], scopeExpandedToPreset: true,
      learningStepsSeconds: [60, 600], relearningStepsSeconds: [600], shortTermMode: "configured_steps",
      scenarios: [{ id: "first_good", sampleSize: 1, retention: 1, observedSuccessfulRangeSeconds: [600, 600], sufficiency: "insufficient" }], recommendation: null,
    } });

    await render("steps");

    expect(container.textContent).toContain("Для рекомендации пока мало наблюдений");
    expect(container.textContent).toContain("Область расширена до пресета");
    expect(container.textContent).toContain("Мало данных");
    expect(container.textContent).not.toContain("100% — надёжно");
  });

  it("blocks invalid simulator values before a request", async () => {
    await render("simulator");
    const input = container.querySelector('input[aria-label="Целевое удержание"]') as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(input, "1");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const button = [...container.querySelectorAll("button")].find((item) => item.textContent?.includes("Рассчитать сценарий")) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(container.textContent).toContain("От 75% до 99%");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a first-class no-configuration state without starting a query", async () => {
    const report = structuredClone(mockReport);
    report.statisticsHub!.fsrs = { ...report.statisticsHub!.fsrs, configurationCount: 0, configurations: [], defaultConfigurationId: null };
    await act(async () => { root.render(<FsrsStatisticsPage report={report} loadState="ready" section="overview" />); });
    expect(container.querySelector('[data-testid="fsrs-no-configuration"]')).not.toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

async function render(section: FsrsSection) {
  await act(async () => { root.render(<FsrsStatisticsPage report={mockReport} loadState="ready" section={section} />); await Promise.resolve(); });
  await act(async () => { await Promise.resolve(); });
}
