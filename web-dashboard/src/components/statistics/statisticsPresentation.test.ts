import { describe, expect, it } from "vitest";
import { mockReport } from "../../data/mockReport";
import {
  deltaModel,
  describeSeries,
  selectDefaultDeckIds,
  statisticsColorClass,
} from "./statisticsPresentation";

describe("statistics presentation helpers", () => {
  it("maps semantic concepts to stable palette classes", () => {
    expect(statisticsColorClass.reviews).toBe("stats-color-reviews");
    expect(statisticsColorClass["study-time"]).toBe("stats-color-study-time");
    expect(statisticsColorClass.previous).toBe("stats-color-previous");
    expect(statisticsColorClass.again).not.toBe(statisticsColorClass.good);
  });

  it("formats rate changes in percentage points and distinguishes previous periods beyond color", () => {
    const comparison = mockReport.statisticsHub!.initialResult.overview.comparison;
    expect(deltaModel(comparison, "successRate", "percentage-points")).toEqual({ text: "+2,4 п.п. к прошлому периоду", direction: "increase", comparisonStyle: "outline-dashed" });
  });

  it("does not convert missing comparison into zero", () => {
    expect(deltaModel({ status: "unavailable" }, "reviews")).toEqual({ text: "Нет сопоставимых данных", direction: "unavailable", comparisonStyle: "unavailable" });
  });

  it("chooses up to three useful decks deterministically and excludes insufficient or empty rows", () => {
    const rows = structuredClone(mockReport.statisticsHub!.initialResult.deckComparison.rows);
    rows.push({ ...rows[0], deckId: 999, fullName: "Empty", reviews: 0, confidence: "insufficient" });
    expect(selectDefaultDeckIds(rows)).toEqual([101, 201, 301]);
    expect(selectDefaultDeckIds([...rows].reverse())).toEqual([101, 201, 301]);
  });

  it("describes sparse and missing series without invented interpolation", () => {
    expect(describeSeries([], "Успешность")).toContain("данных");
    expect(describeSeries([null, 42, undefined], "Повторения")).toContain("одно значение");
  });
});
