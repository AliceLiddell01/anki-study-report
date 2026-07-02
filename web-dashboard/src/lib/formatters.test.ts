import { describe, expect, it } from "vitest";

import {
  finiteNullableNumber,
  finiteNumber,
  formatCompactSeconds,
  formatDurationSeconds,
  formatInteger,
  formatPercent,
  safeText,
} from "./formatters";

describe("formatters", () => {
  it("normalizes finite numbers", () => {
    expect(finiteNumber(12)).toBe(12);
    expect(finiteNumber(Number.NaN, 5)).toBe(5);
    expect(finiteNullableNumber(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("formats report numbers consistently", () => {
    expect(formatInteger(1234.4)).toBe("1 234");
    expect(formatPercent(0.9)).toBe("90%");
    expect(formatPercent(null)).toBe("Нет данных");
    expect(formatCompactSeconds(2.5)).toBe("2.5s");
    expect(formatDurationSeconds(3661)).toBe("1 ч 1 мин");
  });

  it("keeps text fallbacks safe", () => {
    expect(safeText("  ready  ")).toBe("  ready  ");
    expect(safeText("")).toBe("Нет данных");
  });
});
