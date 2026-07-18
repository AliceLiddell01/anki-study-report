import { afterEach, describe, expect, it } from "vitest";
import i18n from "../i18n";
import { cardDisplayText } from "./cardDisplayText";

const base = { displayText: "", displaySource: "none" as const, displayStatus: "unavailable" as const, displayTruncated: false };

afterEach(async () => { await i18n.changeLanguage("ru"); });

describe("cardDisplayText", () => {
  it("returns backend text for available identity", () => {
    expect(cardDisplayText({ ...base, displayText: "【に】（する）", displaySource: "reviewer_front", displayStatus: "available" })).toBe("【に】（する）");
  });

  it("localizes media-only and unavailable states in Russian and English", async () => {
    expect(cardDisplayText({ ...base, displaySource: "reviewer_front", displayStatus: "media_only" })).toBe("Карточка только с медиа");
    expect(cardDisplayText(base)).toBe("Текст карточки недоступен");
    await i18n.changeLanguage("en");
    expect(cardDisplayText({ ...base, displaySource: "browser_question", displayStatus: "media_only" })).toBe("Card with media only");
    expect(cardDisplayText(base)).toBe("Card text unavailable");
  });
});
