// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import NotificationCenterPage from "./NotificationCenterPage";

const mocks = vi.hoisted(() => ({ list: vi.fn(), summary: vi.fn(), mark: vi.fn(), markAll: vi.fn() }));
vi.mock("../lib/notificationsApi", async () => ({ ...(await vi.importActual<typeof import("../lib/notificationsApi")>("../lib/notificationsApi")), fetchNotifications: mocks.list, fetchNotificationSummary: mocks.summary, markNotificationsRead: mocks.mark, markAllNotificationsRead: mocks.markAll }));
const workload = { notificationId: "n1", signalId: "s1", kind: "signal_created", code: "workload.review_pressure", category: "workload", severity: "warning", createdAt: "2026-07-17T00:00:00Z", readAt: null, toastDeliveredAt: null, signalStatus: "active", entity: { type: "all_collection", id: null }, evidence: { currentLoad: 120, baselineMedian: 50 }, sourceRevision: "r1" };
const release = { notificationId: "n2", signalId: null, kind: "release", code: "release.1.1.0", category: "product_updates", severity: "info", createdAt: "2026-07-16T00:00:00Z", readAt: "2026-07-17T00:00:00Z", toastDeliveredAt: null, signalStatus: null, entity: null, evidence: {}, sourceRevision: "release:1.1.0" };

describe("notification center", () => {
  let container: HTMLDivElement; let root: Root;
  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; await i18n.changeLanguage("en");
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    mocks.list.mockReset().mockResolvedValue({ schemaVersion: 1, page: 1, pageLimit: 20, pageCount: 1, total: 2, items: [workload, release] });
    mocks.summary.mockReset().mockResolvedValue({ schemaVersion: 1, unreadCount: 1, activeSignalCount: 1, items: [workload] });
    mocks.mark.mockReset().mockResolvedValue({}); mocks.markAll.mockReset().mockResolvedValue({});
  });
  afterEach(() => { act(() => root.unmount()); container.remove(); vi.clearAllMocks(); });

  it("renders tabs, categories, active/resolved history, and contextual actions", async () => {
    const openRelease = vi.fn(); await act(async () => root.render(<NotificationCenterPage onOpenWhatsNew={openRelease} />));
    expect(container.textContent).toContain("Notification Center"); expect(container.textContent).toContain("Active"); expect(container.textContent).toContain("Product updates");
    expect(container.querySelectorAll('[data-testid="notification-item"]')).toHaveLength(2);
    const releaseButton = [...container.querySelectorAll("button")].find((button) => button.textContent?.includes("What's New"))!;
    await act(async () => releaseButton.click()); expect(openRelease).toHaveBeenCalledOnce();
  });

  it("requests unread/category filters without putting entity IDs in the URL", async () => {
    await act(async () => root.render(<NotificationCenterPage onOpenWhatsNew={() => undefined} />));
    const unread = [...container.querySelectorAll<HTMLButtonElement>('[role="tab"]')].find((button) => button.textContent === "Unread")!;
    await act(async () => unread.click());
    const select = container.querySelector<HTMLSelectElement>("#notification-category")!;
    await act(async () => { select.value = "card_problems"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(mocks.list).toHaveBeenLastCalledWith(expect.objectContaining({ tab: "unread", category: "card_problems" }));
    expect(window.location.hash).not.toContain("n1");
  });
});
