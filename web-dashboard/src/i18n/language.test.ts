// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest";
import {
  LANGUAGE_STORAGE_KEY,
  applyDocumentLanguage,
  normalizeLanguage,
  persistLanguagePreference,
  readLanguagePreference,
} from "./language";

describe("language preference", () => {
  it("uses Russian by default and repairs a corrupt stored value", () => {
    expect(readLanguagePreference()).toBe("ru");
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "de");
    expect(readLanguagePreference()).toBe("ru");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("ru");
    expect(normalizeLanguage(undefined)).toBe("ru");
  });

  it("persists supported languages and tolerates blocked storage", () => {
    persistLanguagePreference("en");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(() => persistLanguagePreference("ru")).not.toThrow();
    spy.mockRestore();
  });

  it("synchronizes the document language, direction, and title", () => {
    applyDocumentLanguage("en", "Learning Dashboard");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.title).toBe("Learning Dashboard");
  });
});
