import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { mockReport } from "../data/mockReport";
import HomePage from "./HomePage";

describe("Today page contract", () => {
  it("uses the dedicated today slice and removes the old period/scope cards", () => {
    const report = {
      ...mockReport,
      today: {
        metadata: { ...mockReport.metadata, period: "Сегодня", periodId: "today", todayDate: "2026-07-10", selectedDecks: [] },
        summary: { ...mockReport.summary, verdict: "TODAY_ONLY_VERDICT" },
        kpis: mockReport.kpis,
        answerDistribution: mockReport.answerDistribution,
        activity: mockReport.activity,
        comparison: mockReport.comparison,
        decks: mockReport.decks,
        recommendations: mockReport.recommendations,
      },
    };

    const markup = renderToStaticMarkup(<HomePage report={report} loadState="ready" />);

    expect(markup).toContain(">Сегодня</h1>");
    expect(markup).toContain("TODAY_ONLY_VERDICT");
    expect(markup).not.toContain("Период статистики");
    expect(markup).not.toContain("Статистика по");
    expect(markup).not.toContain('href="#/settings"');
  });

  it("shows a compact settings link only for a non-default deck scope", () => {
    const report = {
      ...mockReport,
      today: {
        metadata: { ...mockReport.metadata, period: "Сегодня", periodId: "today", selectedDecks: ["Core", "Mining"] },
        summary: mockReport.summary,
        kpis: mockReport.kpis,
        answerDistribution: mockReport.answerDistribution,
        activity: mockReport.activity,
        comparison: mockReport.comparison,
        decks: mockReport.decks,
        recommendations: mockReport.recommendations,
      },
    };

    const markup = renderToStaticMarkup(<HomePage report={report} loadState="ready" />);

    expect(markup).toContain("2 колоды: Core, Mining");
    expect(markup).toContain('href="#/settings"');
  });
});
