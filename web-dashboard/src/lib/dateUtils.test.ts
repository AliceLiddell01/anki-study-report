import { describe, expect, it } from "vitest";

import { addDays, daysBetween, enumerateDateKeys, formatShortDate, isDateKey, monthKey } from "./dateUtils";

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
});
