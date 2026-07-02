import { describe, expect, it } from "vitest";

import { buildCalendarModel, calculateStreakInfo, heatmapIntensity, maxMetricValue } from "./calendarStats";
import type { CalendarDayStats, StudyReport } from "../types/report";

describe("calendarStats", () => {
  it("builds a stable calendar model from sparse report days", () => {
    const report = {
      activity: {
        days: [
          { date: "2026-06-29", reviews: 4, newCards: 1, again: 1, studySeconds: 40 },
          { date: "2026-07-01", reviews: 6, newCards: 2, again: 0, studySeconds: 60 },
        ],
      },
      forecast: {
        daily: [{ date: "2026-07-02", due: 8, learningDue: 1 }],
      },
      comparison: {
        today: { date: "2026-07-01", reviews: 6, newCards: 2, pass: 6, fail: 0, passRate: 1, studySeconds: 60 },
        comparisons: { week: { reviews: { percentDelta: 15 } } },
      },
    } as StudyReport;

    const model = buildCalendarModel(report, "30", "2026-07-01");

    expect(model.today).toBe("2026-07-01");
    expect(model.historicalDays.map((day) => day.date)).toEqual(["2026-06-29", "2026-06-30", "2026-07-01"]);
    expect(model.futureDays[0]?.date).toBe("2026-07-02");
    expect(model.summary.reviewsThisMonth).toBe(6);
    expect(model.metricAvailability.forecast).toBe(true);
  });

  it("calculates streaks and heatmap intensity", () => {
    const days = [
      day("2026-06-28", 1),
      day("2026-06-29", 0),
      day("2026-06-30", 3),
      day("2026-07-01", 2),
    ];

    expect(calculateStreakInfo(days, "2026-07-01")).toEqual({
      currentStreak: 2,
      bestStreak: 2,
      activeDays: 3,
      totalDays: 4,
    });
    expect(maxMetricValue(days, "reviews")).toBe(3);
    expect(heatmapIntensity(days[0], "reviews", 3)).toBeGreaterThan(0);
  });
});

function day(date: string, reviews: number): CalendarDayStats {
  return {
    date,
    reviews,
    newCards: 0,
    pass: reviews,
    fail: 0,
    passRate: reviews ? 1 : null,
    studySeconds: reviews * 10,
    avgAnswerSeconds: reviews ? 10 : null,
    isToday: false,
    isFuture: false,
    dueForecast: null,
  };
}
