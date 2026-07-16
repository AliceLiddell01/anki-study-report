// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { NotificationSummary } from "../lib/notificationsApi";
import NotificationBell from "./NotificationBell";

const mocks = vi.hoisted(() => ({ summary: vi.fn(), preferences: vi.fn(), markAll: vi.fn(), mark: vi.fn() }));
vi.mock("../lib/notificationsApi", async () => ({
  ...(await vi.importActual<typeof import("../lib/notificationsApi")>("../lib/notificationsApi")),
  fetchNotificationSummary: mocks.summary, fetchNotificationPreferences: mocks.preferences,
  markAllNotificationsRead: mocks.markAll, markNotificationsRead: mocks.mark,
}));

const entry = { notificationId: "n1", signalId: "s1", kind: "signal_created", code: "workload.review_pressure", category: "workload", severity: "warning", createdAt: "2026-07-17T00:00:00Z", readAt: null, toastDeliveredAt: null, signalStatus: "active", entity: { type: "all_collection", id: null }, evidence: { currentLoad: 120, baselineMedian: 50 }, sourceRevision: "r1" } as const;
function summary(unreadCount = 1): NotificationSummary { return { schemaVersion: 1, unreadCount, activeSignalCount: 1, items: unreadCount ? [entry] : [] }; }

describe("notification bell", () => {
  let container: HTMLDivElement; let root: Root;
  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("en");
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    mocks.summary.mockReset().mockResolvedValue(summary(120));
    mocks.preferences.mockReset().mockResolvedValue({ showUnreadBadge: true });
    mocks.markAll.mockReset().mockResolvedValue(summary(0)); mocks.mark.mockReset().mockResolvedValue(summary(0));
  });
  afterEach(() => { act(() => root.unmount()); container.remove(); vi.clearAllMocks(); });

  it("caps the badge and supports dialog focus, Escape, and outside close", async () => {
    await act(async () => root.render(<NotificationBell onOpenWhatsNew={() => undefined} />));
    expect(container.querySelector('[data-testid="notification-badge"]')?.textContent).toBe("99+");
    const trigger = container.querySelector<HTMLButtonElement>('button[aria-label="Notifications"]')!;
    act(() => trigger.click());
    const panel = container.querySelector<HTMLElement>('[role="dialog"]')!;
    expect(trigger.getAttribute("aria-expanded")).toBe("true"); expect(document.activeElement).toBe(panel);
    await act(async () => { document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); await new Promise((resolve) => window.setTimeout(resolve, 20)); });
    expect(container.querySelector('[role="dialog"]')).toBeNull(); expect(document.activeElement).toBe(trigger);
    act(() => trigger.click());
    act(() => document.body.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true })));
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it("shows the empty state when badge display is disabled", async () => {
    mocks.summary.mockResolvedValue(summary(0)); mocks.preferences.mockResolvedValue({ showUnreadBadge: false });
    await act(async () => root.render(<NotificationBell onOpenWhatsNew={() => undefined} />));
    const trigger = container.querySelector<HTMLButtonElement>('button[aria-label="Notifications"]')!;
    act(() => trigger.click());
    expect(container.textContent).toContain("No new notifications"); expect(container.querySelector('[data-testid="notification-badge"]')).toBeNull();
  });
});
