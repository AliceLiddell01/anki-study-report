// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { ProductNoticesResponse } from "../lib/productNoticesApi";
import ProductNoticeCoordinator from "./ProductNoticeCoordinator";
import WhatsNewDialog from "./WhatsNewDialog";

const releases = [
  { version: "1.2.0", date: "2026-07-15", sections: [{ type: "added" as const, items: [{ id: "current", text: { ru: "Текущая версия", en: "Current release" } }] }] },
  { version: "1.1.0", date: "2026-07-10", sections: [{ type: "changed" as const, items: [{ id: "middle", text: { ru: "Промежуточная версия", en: "Middle release" } }] }] },
  { version: "1.0.0", date: "2026-07-01", sections: [{ type: "fixed" as const, items: [{ id: "old", text: { ru: "Первая версия", en: "First release" } }] }] },
];

function response(overrides: Partial<ProductNoticesResponse> = {}): ProductNoticesResponse {
  return {
    ok: true,
    currentVersion: "1.2.0",
    notice: { schemaVersion: 1, firstObservedVersion: "1.2.0", lastStartedVersion: "1.2.0", lastSeenReleaseVersion: null },
    privacy: {
      schemaVersion: 1,
      requiresConsent: true,
      telemetry: {
        status: "undecided",
        consentSchemaVersion: 1,
        privacyNoticeVersion: "2026-07-15",
        purposes: { reliabilityDiagnostics: false, featureUsage: false },
        effectivePurposes: { reliabilityDiagnostics: false, featureUsage: false },
        decidedAt: null,
        deletionPending: false,
        requiresConsent: true,
      },
    },
    requiresConsent: true,
    showWhatsNew: true,
    unseenReleaseVersions: ["1.2.0", "1.1.0"],
    changelog: { schemaVersion: 1, unreleased: { sections: [] }, releases },
    ...overrides,
  };
}

describe("product notice coordinator", () => {
  let container: HTMLDivElement;
  let shell: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("ru");
    window.history.replaceState({}, "", "/?token=dashboard-token");
    shell = document.createElement("div");
    shell.id = "dashboard-app-shell";
    document.body.append(shell);
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    shell.remove();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("shows unselected consent first and treats Escape as a persisted granular decline before What's New", async () => {
    const initial = response();
    const afterConsent = response({
      requiresConsent: false,
      privacy: {
        schemaVersion: 1,
        requiresConsent: false,
        telemetry: {
          ...initial.privacy.telemetry,
          status: "declined",
          decidedAt: "2026-07-15T00:00:00Z",
          requiresConsent: false,
        },
      },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(initial))
      .mockResolvedValueOnce(jsonResponse({ ok: true, privacy: afterConsent.privacy }))
      .mockResolvedValueOnce(jsonResponse(afterConsent));

    await act(async () => root.render(<ProductNoticeCoordinator manualOpenSignal={0} />));
    await settle();

    expect(container.querySelector('[data-testid="telemetry-consent-dialog"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="whats-new-dialog"]')).toBeNull();
    expect(Array.from(container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')).every((input) => !input.checked)).toBe(true);
    expect(shell.inert).toBe(true);

    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    await settle();

    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/privacy?token=dashboard-token");
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      purposes: { reliabilityDiagnostics: false, featureUsage: false },
    });
    expect(container.querySelector('[data-testid="telemetry-consent-dialog"]')).toBeNull();
    expect(container.querySelector('[data-testid="whats-new-dialog"]')).not.toBeNull();
  });

  it("preserves skipped-version expansion across language changes and restores focus after Escape", async () => {
    const invoker = document.createElement("button");
    document.body.append(invoker);
    invoker.focus();
    const update = response({
      requiresConsent: false,
      notice: { schemaVersion: 1, firstObservedVersion: "1.0.0", lastStartedVersion: "1.2.0", lastSeenReleaseVersion: "1.0.0" },
    });

    function Harness() {
      const [open, setOpen] = useState(true);
      return open ? <WhatsNewDialog data={update} onClose={() => setOpen(false)} /> : null;
    }

    await act(async () => root.render(<Harness />));
    expect(document.activeElement?.id).toBe("whats-new-dialog-title");
    expect(container.querySelectorAll('[aria-expanded="true"]')).toHaveLength(2);
    await act(async () => i18n.changeLanguage("en"));
    expect(container.querySelectorAll('[aria-expanded="true"]')).toHaveLength(2);
    expect(container.textContent).toContain("What's new since your last visit");

    const modal = container.querySelector<HTMLElement>('[data-testid="whats-new-dialog"]')!;
    const focusable = modal.querySelectorAll<HTMLElement>('button:not([disabled])');
    focusable[focusable.length - 1]?.focus();
    act(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true })));
    expect(document.activeElement).toBe(focusable[0]);

    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(container.querySelector('[data-testid="whats-new-dialog"]')).toBeNull();
    expect(document.activeElement).toBe(invoker);
    invoker.remove();
  });

  it("shows only the current release expanded on first install", async () => {
    await act(async () => root.render(<WhatsNewDialog data={response()} onClose={() => undefined} />));
    expect(container.querySelectorAll('[aria-expanded="true"]')).toHaveLength(1);
    expect(container.textContent).toContain("Что нового в Anki Study Report");
  });

  it("persists an affirmative granular choice and does not repeat after release notes are marked seen", async () => {
    const initial = response();
    const afterConsent = response({
      requiresConsent: false,
      privacy: {
        schemaVersion: 1,
        requiresConsent: false,
        telemetry: {
          ...initial.privacy.telemetry,
          status: "accepted",
          purposes: { reliabilityDiagnostics: true, featureUsage: false },
          effectivePurposes: { reliabilityDiagnostics: true, featureUsage: false },
          decidedAt: "2026-07-15T00:00:00Z",
          requiresConsent: false,
        },
      },
    });
    const afterSeen = response({
      ...afterConsent,
      showWhatsNew: false,
      unseenReleaseVersions: [],
      notice: { ...afterConsent.notice, lastSeenReleaseVersion: "1.2.0" },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(initial))
      .mockResolvedValueOnce(jsonResponse({ ok: true, privacy: afterConsent.privacy }))
      .mockResolvedValueOnce(jsonResponse(afterConsent))
      .mockResolvedValueOnce(jsonResponse(afterSeen));

    await act(async () => root.render(<ProductNoticeCoordinator manualOpenSignal={0} />));
    await settle();
    const firstPurpose = container.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    act(() => firstPurpose.click());
    const save = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Сохранить выбранное")!;
    await act(async () => save.click());
    await settle();

    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      purposes: { reliabilityDiagnostics: true, featureUsage: false },
    });
    expect(container.querySelector('[data-testid="whats-new-dialog"]')).not.toBeNull();
    const gotIt = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Понятно")!;
    await act(async () => gotIt.click());
    await settle();
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(fetchMock.mock.calls[3]?.[0]).toBe("/api/product-notices/seen?token=dashboard-token");
  });

  it("allows manual What's New reopening without reopening consent", async () => {
    const settled = response({
      requiresConsent: false,
      showWhatsNew: false,
      unseenReleaseVersions: [],
      notice: { schemaVersion: 1, firstObservedVersion: "1.0.0", lastStartedVersion: "1.2.0", lastSeenReleaseVersion: "1.2.0" },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(settled));

    await act(async () => root.render(<ProductNoticeCoordinator manualOpenSignal={0} />));
    await settle();
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    await act(async () => root.render(<ProductNoticeCoordinator manualOpenSignal={1} />));

    expect(container.querySelector('[data-testid="whats-new-dialog"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="telemetry-consent-dialog"]')).toBeNull();
  });
});

function jsonResponse(payload: unknown): Response {
  return { ok: true, status: 200, json: async () => payload } as Response;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}
