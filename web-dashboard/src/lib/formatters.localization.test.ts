import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { formatDurationSeconds, formatInteger, formatPercent, formatSeconds } from "./formatters";
import { formatDateTime, isValidDateTime } from "./localizedDateTime";

describe("locale-aware formatters and plurals", () => {
  it("uses Russian plural categories", async () => {
    await i18n.changeLanguage("ru");
    expect(i18n.t("units.card", { ns: "common", count: 1 })).toBe("1 карточка");
    expect(i18n.t("units.card", { ns: "common", count: 2 })).toBe("2 карточки");
    expect(i18n.t("units.card", { ns: "common", count: 5 })).toBe("5 карточек");
  });

  it("changes number formatting with the active language", async () => {
    await i18n.changeLanguage("ru");
    expect(formatInteger(12_345)).toContain("12");
    expect(formatPercent(0.815).replace(/\s/g, "")).toBe("81,5%");
    await i18n.changeLanguage("en");
    expect(formatInteger(12_345)).toBe("12,345");
    expect(formatPercent(0.815)).toBe("81.5%");
  });

  it("localizes units without hard-coded locale output", async () => {
    await i18n.changeLanguage("ru");
    expect(formatSeconds(1.5)).toBe("1,5 с");
    expect(formatDurationSeconds(3660)).toBe("1 ч 1 мин");
    await i18n.changeLanguage("en");
    expect(formatSeconds(1.5)).toBe("1.5 sec");
    expect(formatDurationSeconds(3660)).toBe("1 hr 1 min");
  });

  it("formats local date-times in Russian and English with safe invalid fallback", async () => {
    const raw = "2026-07-15T11:46:49.771921Z";
    expect(isValidDateTime(raw)).toBe(true);
    await i18n.changeLanguage("ru");
    const russian = formatDateTime(raw, "—");
    await i18n.changeLanguage("en");
    const english = formatDateTime(raw, "—");
    expect(russian).toContain("2026");
    expect(english).toContain("2026");
    expect(russian).not.toBe(english);
    expect(formatDateTime("not-a-date", "Unknown")).toBe("Unknown");
    expect(isValidDateTime(null)).toBe(false);
  });
});
