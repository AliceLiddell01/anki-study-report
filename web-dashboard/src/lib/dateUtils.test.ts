import { describe, expect, it } from "vitest";

import i18n from "../i18n";
import { addDays, daysBetween, enumerateDateKeys, formatLongDate, formatShortDate, isDateKey, localizedWeekdayLabels, monthKey } from "./dateUtils";

describe("dateUtils", () => {
  it("validates calendar date keys strictly", () => {
    expect(isDateKey("2026-07-01")).toBe(true);
    expect(isDateKey("2026-02-29")).toBe(false);
    expect(isDateKey("2026-7-1")).toBe(false);
  });

  it("handles date arithmetic without timezone drift", () => {
    expect(addDays("2026-07-01", 2)).toBe("2026-07-03");
    expect(addDays("2026-07-01", -1)).toBe("2026-06-30");
    expect(daysBetween("2026-06-30", "2026-07-02")).toBe(2);
    expect(enumerateDateKeys("2026-06-30", "2026-07-02")).toEqual([
      "2026-06-30",
      "2026-07-01",
      "2026-07-02",
    ]);
  });

  it("formats compact Russian date labels", () => {
    expect(formatShortDate("2026-07-01")).toBe("1 июл.");
    expect(formatShortDate("bad")).toBe("Нет данных");
    expect(monthKey("2026-07-01")).toBe("2026-07");
  });

  it("formats dates and weekdays for the active locale", async () => {
    await i18n.changeLanguage("ru");
    expect(formatLongDate("2026-07-01")).toBe("1 июля 2026 г.");
    expect(localizedWeekdayLabels()[0]).toMatch(/^пн/i);
    await i18n.changeLanguage("en");
    expect(formatLongDate("2026-07-01")).toBe("July 1, 2026");
    expect(localizedWeekdayLabels()[0]).toMatch(/^Mon/i);
  });
});
