// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";
import { consumeNotificationHandoff, writeNotificationHandoff } from "./notificationHandoff";

describe("notification contextual handoff", () => {
  beforeEach(() => sessionStorage.clear());

  it("passes one bounded local entity without a URL", () => {
    const createdAt = new Date().toISOString();
    writeNotificationHandoff({ category: "deck_health", entityType: "deck", entityId: "123", createdAt });
    const value = consumeNotificationHandoff("deck_health", Date.parse(createdAt) + 1000);
    expect(value?.entityId).toBe("123");
    expect(sessionStorage.length).toBe(0);
    expect(window.location.href).not.toContain("123");
  });

  it("rejects stale, mismatched, and unbounded values", () => {
    sessionStorage.setItem("anki-study-report:notification-handoff", JSON.stringify({ category: "card_problems", entityType: "card", entityId: "1 OR 1=1", createdAt: "2026-07-17T10:00:00Z" }));
    expect(consumeNotificationHandoff("card_problems", Date.parse("2026-07-17T10:01:00Z"))).toBeNull();
    expect(consumeNotificationHandoff("card_problems")).toBeNull();
  });
});
