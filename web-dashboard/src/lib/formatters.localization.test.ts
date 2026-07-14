import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { formatInteger, formatPercent } from "./formatters";

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
});
