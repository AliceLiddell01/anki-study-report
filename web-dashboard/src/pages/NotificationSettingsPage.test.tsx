// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import NotificationSettingsPage from "./NotificationSettingsPage";

const mocks = vi.hoisted(() => ({ fetch: vi.fn(), save: vi.fn() }));
vi.mock("../lib/notificationsApi", async () => ({
  ...(await vi.importActual<typeof import("../lib/notificationsApi")>("../lib/notificationsApi")),
  fetchNotificationPreferences: mocks.fetch,
  saveNotificationPreferences: mocks.save,
}));

const defaults = {
  notificationCenterEnabled: true,
  showUnreadBadge: true,
  showInAppToasts: true,
  minimumToastSeverity: "critical",
  sound: "none",
  osNotifications: "none",
  toastCategories: {
    workload: true,
    retention: true,
    deck_health: true,
    card_problems: true,
    product_updates: true,
  },
} as const;

describe("notification preferences", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("en");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    mocks.fetch.mockReset().mockResolvedValue(defaults);
    mocks.save.mockReset().mockImplementation(async (value) => ({ ...defaults, ...value }));
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it("shows conservative defaults and persists badge, severity, and category controls", async () => {
    await renderPage();
    await settle();

    expect(container.querySelector<HTMLSelectElement>("#minimum-toast-severity")?.value).toBe("critical");
    const checkboxes = [...container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
    expect(checkboxes.every((box) => box.checked)).toBe(true);

    await act(async () => checkboxes[0].click());
    const select = container.querySelector<HTMLSelectElement>("#minimum-toast-severity")!;
    await act(async () => {
      select.value = "warning";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });

    const save = [...container.querySelectorAll("button")].find((button) => button.textContent === "Save")!;
    await act(async () => save.click());

    expect(mocks.save).toHaveBeenCalledWith(expect.objectContaining({
      showUnreadBadge: false,
      minimumToastSeverity: "warning",
    }));
    expect(container.textContent).toContain("Sound and OS notifications are not used");
  });

  it("keeps one route heading and its focus through loading-to-error transition", async () => {
    let rejectFetch: ((reason?: unknown) => void) | undefined;
    mocks.fetch.mockImplementation(() => new Promise((_, reject) => {
      rejectFetch = reject;
    }));

    await renderPage();

    const heading = container.querySelector<HTMLHeadingElement>("h1")!;
    expect(heading.textContent).toBe("Notifications");
    heading.tabIndex = -1;
    heading.focus();
    expect(document.activeElement).toBe(heading);

    await act(async () => {
      rejectFetch?.(new Error("unavailable"));
      await Promise.resolve();
    });
    await settle();

    expect(container.querySelector("h1")).toBe(heading);
    expect(document.activeElement).toBe(heading);
    expect(container.querySelector("#minimum-toast-severity")).toBeNull();
  });

  async function renderPage() {
    await act(async () => {
      root.render(<NotificationSettingsPage />);
    });
  }

  async function settle() {
    await act(async () => {
      await Promise.resolve();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });
  }
});
