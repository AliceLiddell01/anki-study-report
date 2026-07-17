// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { NotificationItem } from "../lib/notificationsApi";
import NotificationToasts, { buildNotificationToastQueue } from "./NotificationToasts";

const mocks = vi.hoisted(() => ({ fetch: vi.fn(), acknowledge: vi.fn() }));
vi.mock("../lib/notificationsApi", async () => ({ ...(await vi.importActual<typeof import("../lib/notificationsApi")>("../lib/notificationsApi")), fetchToastCandidates: mocks.fetch, acknowledgeToastDelivery: mocks.acknowledge }));
function item(id: string, severity: "info" | "warning" | "critical" = "warning"): NotificationItem { return { notificationId: id, signalId: `s-${id}`, kind: "signal_created", code: "workload.review_pressure", category: "workload", severity, createdAt: "2026-07-17T00:00:00Z", readAt: null, toastDeliveredAt: null, signalStatus: "active", entity: { type: "all_collection", id: null }, evidence: { currentLoad: 120, baselineMedian: 50 }, sourceRevision: "r1" }; }

describe("notification toasts", () => {
  let container: HTMLDivElement; let root: Root;
  beforeEach(async () => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; await i18n.changeLanguage("en"); container = document.createElement("div"); document.body.append(container); root = createRoot(container); mocks.fetch.mockReset(); mocks.acknowledge.mockReset().mockResolvedValue(undefined); });
  afterEach(() => { act(() => root.unmount()); container.remove(); vi.useRealTimers(); vi.clearAllMocks(); });

  it("collapses overflow to a bounded three-item queue", () => {
    const queue = buildNotificationToastQueue([item("1"), item("2"), item("3"), item("4")], (key, values) => key === "summaryToast" ? `${values?.count} more` : key);
    expect(queue).toHaveLength(3); expect(queue[2].notificationIds).toEqual(["3", "4"]); expect(queue[2].evidence).toBe("2 more");
  });

  it("acknowledges only after accepting a warning and auto-dismisses after eight seconds", async () => {
    vi.useFakeTimers(); mocks.fetch.mockResolvedValue([item("1")]);
    await act(async () => root.render(<NotificationToasts />)); await act(async () => Promise.resolve());
    expect(container.querySelector('[role="status"]')).not.toBeNull(); expect(mocks.acknowledge).toHaveBeenCalledWith(["1"]);
    await act(async () => vi.advanceTimersByTime(8000)); expect(container.querySelector('[role="status"]')).toBeNull();
  });

  it("keeps a critical alert until the accessible close button is used", async () => {
    vi.useFakeTimers(); mocks.fetch.mockResolvedValue([item("1", "critical")]);
    await act(async () => root.render(<NotificationToasts />)); await act(async () => Promise.resolve());
    await act(async () => vi.advanceTimersByTime(60000)); expect(container.querySelector('[role="alert"]')).not.toBeNull();
    act(() => container.querySelector<HTMLButtonElement>('button[aria-label="Close"]')!.click()); expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("pauses an auto-dismiss toast while hovered and honors reduced-motion styling", async () => {
    vi.useFakeTimers(); mocks.fetch.mockResolvedValue([item("1")]);
    await act(async () => root.render(<NotificationToasts />)); await act(async () => Promise.resolve());
    const toast = container.querySelector<HTMLElement>('[role="status"]')!;
    expect(toast.className).toContain("motion-reduce:transition-none");
    act(() => toast.dispatchEvent(new MouseEvent("mouseover", { bubbles: true })));
    await act(async () => vi.advanceTimersByTime(20000));
    expect(container.querySelector('[role="status"]')).not.toBeNull();
    act(() => toast.dispatchEvent(new MouseEvent("mouseout", { bubbles: true, relatedTarget: document.body })));
    await act(async () => vi.advanceTimersByTime(8000));
    expect(container.querySelector('[role="status"]')).toBeNull();
  });
});
