// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { InspectionProfileSummary, InspectionProfilesQueryResponse } from "../types/inspectionProfiles";
import InspectionProfilesSettingsPage from "./InspectionProfilesSettingsPage";

const mocks = vi.hoisted(() => ({ query: vi.fn(), validate: vi.fn(), update: vi.fn() }));
vi.mock("../lib/inspectionProfilesApi", async () => ({
  ...(await vi.importActual<typeof import("../lib/inspectionProfilesApi")>("../lib/inspectionProfilesApi")),
  fetchInspectionProfiles: mocks.query,
  validateInspectionProfile: mocks.validate,
  updateInspectionProfile: mocks.update,
}));

const fingerprint = { algorithm: "sha256" as const, value: "b".repeat(64) };
const refs = ["Word", "Meaning", "Audio"].map((name, ordinal) => ({ ordinal, name }));
const japanese: InspectionProfileSummary = {
  structure: {
    noteTypeId: "1",
    name: "Japanese Vocabulary",
    kind: "standard",
    fields: refs,
    templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Word"], backFields: ["Meaning", "Audio"] }],
    fingerprint,
  },
  effectiveState: "not_configured",
  stateReason: null,
  authoritative: false,
  storedProfile: null,
  suggestion: {
    detectedKind: "japanese_vocab",
    confidence: 0.95,
    fieldMappings: [
      { role: "term", fields: [refs[0]], confidence: 0.98 },
      { role: "meaning", fields: [refs[1]], confidence: 0.98 },
      { role: "audio", fields: [refs[2]], confidence: 0.98 },
    ],
    checks: [
      { checkId: "meaning-required", kind: "non_empty", roles: ["meaning"], mode: "any", priority: "high" },
    ],
    warnings: [],
    unresolvedFields: [],
  },
};

const response: InspectionProfilesQueryResponse = {
  schemaVersion: 1,
  status: "available",
  store: { status: "empty", revision: 0, profileCount: 0, errorCode: null, quarantined: false },
  totalCount: 1,
  returnedCount: 1,
  limit: 500,
  truncated: false,
  skippedCount: 0,
  items: [japanese],
};

describe("Inspection Profiles controlled validation regression", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("ru");
    container = document.createElement("div");
    container.id = "dashboard-app-shell";
    document.body.append(container);
    root = createRoot(container);
    mocks.query.mockReset().mockResolvedValue(response);
    mocks.validate.mockReset().mockResolvedValue({
      schemaVersion: 2,
      valid: true,
      effectiveState: "confirmed",
      stateReason: null,
      fieldErrors: {},
      preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] },
    });
    mocks.update.mockReset();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it("keeps an explicitly cleared mapping empty, reports a client error, then validates after repair", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));

    let meaning = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    await change(meaning, "");
    meaning = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    expect(meaning.value).toBe("");
    expect(meaning.selectedOptions[0]?.value).toBe("");

    const firstCheck = button("Проверить настройку");
    firstCheck.focus();
    await click(firstCheck);

    expect(mocks.validate).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Исправьте профиль");
    expect(container.textContent).not.toContain("Черновик проверен");
    meaning = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    expect(meaning.getAttribute("aria-invalid")).toBe("true");
    expect(document.activeElement?.id).toBe("inspection-errors-title");
    expect(document.activeElement).not.toBe(document.body);

    const mappingError = container.querySelector<HTMLButtonElement>(".inspection-error-summary button")!;
    await click(mappingError);
    expect(document.activeElement?.id).toBe("inspection-basic-role-1");
    expect(container.querySelector("#inspection-mode-basic")?.getAttribute("aria-selected")).toBe("true");

    meaning = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    await change(meaning, "1");
    meaning = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    expect(meaning.getAttribute("aria-invalid")).toBeNull();
    expect(container.querySelector("#inspection-errors-title")).toBeNull();

    const secondCheck = button("Проверить настройку");
    secondCheck.focus();
    await click(secondCheck);
    expect(mocks.validate).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(secondCheck);
    expect(document.activeElement).not.toBe(document.body);
  });

  it("routes aggregate mappings and checks errors to Basic groups without an Advanced count", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-advanced")!);

    const meaningRole = container.querySelector<HTMLInputElement>("#inspection-role-1")!;
    await changeInput(meaningRole, "term");
    await click(button("Проверить настройку"));

    expect(container.querySelector("#inspection-mode-advanced .inspection-mode-error-count")).toBeNull();
    const mappingsError = container.querySelector<HTMLButtonElement>(".inspection-error-summary button")!;
    await click(mappingsError);
    expect(container.querySelector("#inspection-mode-basic")?.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement?.id).toBe("inspection-basic-fields");

    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-advanced")!);
    await changeInput(container.querySelector<HTMLInputElement>("#inspection-role-1")!, "meaning");
    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-basic")!);
    mocks.validate.mockResolvedValueOnce({
      schemaVersion: 2,
      valid: false,
      effectiveState: "suggested",
      stateReason: null,
      fieldErrors: { "profile.checks": "duplicate_check_ids" },
      preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] },
    });
    await click(button("Проверить настройку"));
    expect(container.querySelector("#inspection-mode-advanced .inspection-mode-error-count")).toBeNull();
    const checksError = container.querySelector<HTMLButtonElement>(".inspection-error-summary button")!;
    await click(checksError);
    expect(document.activeElement?.id).toBe("inspection-basic-requirements");
  });

  it("routes Advanced-only errors to the exact control and reports the exact badge count", async () => {
    mocks.validate.mockResolvedValueOnce({
      schemaVersion: 2,
      valid: false,
      effectiveState: "suggested",
      stateReason: null,
      fieldErrors: { "profile.checks.0.checkId": "invalid_check_id" },
      preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] },
    });
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    await click(button("Проверить настройку"));

    expect(container.querySelector("#inspection-mode-advanced .inspection-mode-error-count")?.textContent).toBe("1");
    await click(container.querySelector<HTMLButtonElement>(".inspection-error-summary button")!);
    expect(container.querySelector("#inspection-mode-advanced")?.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement?.id).toBe("inspection-check-id-0");
    expect(document.activeElement).not.toBe(document.body);
  });

  async function renderPage() {
    await act(async () => root.render(<InspectionProfilesSettingsPage />));
    await settle();
  }

  async function settle() {
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  async function click(element: HTMLElement) {
    await act(async () => element.click());
    await settle();
  }

  async function change(element: HTMLSelectElement, value: string) {
    await act(async () => {
      element.value = value;
      element.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await settle();
  }

  async function changeInput(element: HTMLInputElement, value: string) {
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(element, value);
      element.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await settle();
  }

  function button(text: string) {
    const match = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text);
    if (!match) throw new Error(`missing button ${text}`);
    return match;
  }

  function noteButton(text: string) {
    const match = [...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].find((item) => item.textContent?.includes(text));
    if (!match) throw new Error(`missing note ${text}`);
    return match;
  }
});
