// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchNotificationPreferences, fetchNotificationSummary, fetchNotifications, saveNotificationPreferences } from "./notificationsApi";

const item = {
  notificationId: "n1", signalId: "s1", kind: "signal_created", code: "workload.review_pressure",
  category: "workload", severity: "warning", createdAt: "2026-07-17T00:00:00Z", readAt: null,
  toastDeliveredAt: null, signalStatus: "active", entity: { type: "all_collection", id: null },
  evidence: { currentLoad: 120, baselineMedian: 50 }, sourceRevision: "cache:1",
};

afterEach(() => vi.unstubAllGlobals());

describe("notifications API validators", () => {
  it("validates summary/list payloads and keeps the dashboard token local", async () => {
    window.history.replaceState(null, "", "/?token=secret-value#/notifications");
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ ok: true, schemaVersion: 1, unreadCount: 1, activeSignalCount: 1, items: [item] }))
      .mockResolvedValueOnce(response({ ok: true, schemaVersion: 1, page: 1, pageLimit: 20, pageCount: 1, total: 1, items: [item] }));
    vi.stubGlobal("fetch", fetchMock);

    expect((await fetchNotificationSummary()).items[0].code).toBe("workload.review_pressure");
    expect((await fetchNotifications({ tab: "active" })).total).toBe(1);
    expect(fetchMock.mock.calls[0][0]).toContain("token=secret-value");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: "no-store" });
  });

  it("rejects unknown response fields", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ ok: true, schemaVersion: 1, unreadCount: 0, activeSignalCount: 0, items: [], unexpected: true })));
    await expect(fetchNotificationSummary()).rejects.toThrow("invalid_notification_response");
  });

  it("round-trips strict preferences without sound or OS controls", async () => {
    const preferences = { notificationCenterEnabled: true, showUnreadBadge: true, showInAppToasts: true, minimumToastSeverity: "critical", sound: "none", osNotifications: "none", toastCategories: { workload: true, retention: true, deck_health: true, card_problems: true, product_updates: true } };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ ok: true, schemaVersion: 1, preferences }))
      .mockResolvedValueOnce(response({ ok: true, schemaVersion: 1, preferences: { ...preferences, showUnreadBadge: false } }));
    vi.stubGlobal("fetch", fetchMock);

    expect((await fetchNotificationPreferences()).minimumToastSeverity).toBe("critical");
    expect((await saveNotificationPreferences({ showUnreadBadge: false })).showUnreadBadge).toBe(false);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ showUnreadBadge: false });
  });
});

function response(value: unknown): Response { return { ok: true, json: async () => value } as Response; }
