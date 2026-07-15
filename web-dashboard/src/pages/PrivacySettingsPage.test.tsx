// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { PrivacyResponse } from "../lib/productNoticesApi";
import PrivacySettingsPage from "./PrivacySettingsPage";

const mocks = vi.hoisted(() => ({
  fetchPrivacy: vi.fn(),
  savePrivacyChoices: vi.fn(),
  deleteTelemetryData: vi.fn(),
}));

vi.mock("../lib/productNoticesApi", async () => {
  const actual = await vi.importActual<typeof import("../lib/productNoticesApi")>("../lib/productNoticesApi");
  return { ...actual, fetchPrivacy: mocks.fetchPrivacy, savePrivacyChoices: mocks.savePrivacyChoices };
});
vi.mock("../lib/telemetryApi", async () => {
  const actual = await vi.importActual<typeof import("../lib/telemetryApi")>("../lib/telemetryApi");
  return { ...actual, deleteTelemetryData: mocks.deleteTelemetryData };
});

function response(overrides: Partial<PrivacyResponse> = {}): PrivacyResponse {
  return {
    ok: true,
    privacy: {
      schemaVersion: 1,
      requiresConsent: false,
      telemetry: {
        status: "accepted",
        consentSchemaVersion: 1,
        privacyNoticeVersion: "2026-07-15",
        purposes: { reliabilityDiagnostics: true, featureUsage: false },
        effectivePurposes: { reliabilityDiagnostics: true, featureUsage: false },
        decidedAt: "2026-07-15T00:00:00Z",
        deletionPending: false,
        requiresConsent: false,
      },
    },
    telemetryClient: {
      storeSchemaVersion: 1,
      telemetrySchemaVersion: 1,
      endpointState: "configured",
      enrollmentState: "enrolled",
      senderState: "idle",
      pendingEventCount: 2,
      pendingByPurpose: { reliabilityDiagnostics: 2, featureUsage: 0 },
      lastSuccessfulDeliveryAt: null,
      lastDeliveryAttemptAt: null,
      lastDeliveryErrorCode: null,
      deletionPending: false,
      deletionErrorCode: null,
      deletionNextAttemptAt: null,
    },
    ...overrides,
  };
}

describe("privacy settings", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("en");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    mocks.fetchPrivacy.mockReset().mockResolvedValue(response());
    mocks.savePrivacyChoices.mockReset().mockResolvedValue(response());
    mocks.deleteTelemetryData.mockReset();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it("shows accepted granular choices and bounded client status without credentials", async () => {
    await act(async () => root.render(<PrivacySettingsPage onOpenWhatsNew={() => undefined} />));

    expect(container.textContent).toContain("Allowed for selected purposes");
    expect(container.textContent).toContain("2");
    const checkboxes = [...container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
    expect(checkboxes.map((item) => item.checked)).toEqual([true, false]);
    expect(container.textContent).not.toContain("installationId");
    expect(container.textContent).not.toContain("writeToken");
  });

  it("reports offline deletion as pending after disabling effective telemetry", async () => {
    const pending = response({
      privacy: {
        ...response().privacy!,
        telemetry: {
          ...response().privacy!.telemetry,
          status: "declined",
          purposes: { reliabilityDiagnostics: false, featureUsage: false },
          effectivePurposes: { reliabilityDiagnostics: false, featureUsage: false },
          deletionPending: true,
        },
      },
      telemetryClient: {
        ...response().telemetryClient!,
        deletionPending: true,
        deletionErrorCode: "network_error",
        deletionNextAttemptAt: "2026-07-15T00:15:00Z",
      },
    });
    mocks.deleteTelemetryData.mockResolvedValue({ ok: true, deletionPending: true, confirmed: false });
    mocks.fetchPrivacy.mockResolvedValueOnce(response()).mockResolvedValueOnce(pending);
    await act(async () => root.render(<PrivacySettingsPage onOpenWhatsNew={() => undefined} />));
    const deleteButton = [...container.querySelectorAll("button")].find((item) => item.textContent === "Delete already collected data");
    expect(deleteButton).toBeDefined();

    await act(async () => deleteButton?.click());

    expect(mocks.deleteTelemetryData).toHaveBeenCalledOnce();
    expect(container.textContent).toContain("Deletion is pending");
    expect(container.textContent).not.toContain("2026-07-15T00:15:00Z");
    expect(container.querySelector('[title="2026-07-15T00:15:00Z"]')).not.toBeNull();
  });

  it("disables remote no-op actions and explains why they are unavailable", async () => {
    mocks.fetchPrivacy.mockResolvedValue(response({
      privacy: {
        ...response().privacy!,
        telemetry: {
          ...response().privacy!.telemetry,
          status: "declined",
          purposes: { reliabilityDiagnostics: false, featureUsage: false },
          effectivePurposes: { reliabilityDiagnostics: false, featureUsage: false },
          deletionPending: false,
        },
      },
      telemetryClient: {
        ...response().telemetryClient!,
        enrollmentState: "not_enrolled",
        pendingEventCount: 0,
        pendingByPurpose: { reliabilityDiagnostics: 0, featureUsage: 0 },
        lastSuccessfulDeliveryAt: null,
        deletionPending: false,
      },
    }));

    await act(async () => root.render(<PrivacySettingsPage onOpenWhatsNew={() => undefined} />));

    const disable = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Disable all telemetry");
    const remove = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Delete already collected data");
    expect(disable?.disabled).toBe(true);
    expect(remove?.disabled).toBe(true);
    expect(container.textContent).toContain("All purposes are disabled");
    expect(container.textContent).toContain("Nothing can be deleted");
    expect(mocks.savePrivacyChoices).not.toHaveBeenCalled();
    expect(mocks.deleteTelemetryData).not.toHaveBeenCalled();
  });

  it("shows localized timestamps while retaining the raw ISO value for diagnostics", async () => {
    await i18n.changeLanguage("ru");
    mocks.fetchPrivacy.mockResolvedValue(response({
      privacy: {
        ...response().privacy!,
        telemetry: { ...response().privacy!.telemetry, decidedAt: "2026-07-15T11:46:49.771921Z" },
      },
      telemetryClient: {
        ...response().telemetryClient!,
        lastSuccessfulDeliveryAt: "2026-07-15T11:47:00Z",
      },
    }));

    await act(async () => root.render(<PrivacySettingsPage onOpenWhatsNew={() => undefined} />));

    const decision = container.querySelector('time[datetime="2026-07-15T11:46:49.771921Z"]');
    expect(decision).not.toBeNull();
    expect(decision?.textContent).not.toContain("T11:46:49");
    expect(decision?.getAttribute("title")).toBe("2026-07-15T11:46:49.771921Z");
  });
});
