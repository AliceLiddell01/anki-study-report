// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import InspectionProfilesSettingsPage from "./InspectionProfilesSettingsPage";

const mocks = vi.hoisted(() => ({ query: vi.fn(), validate: vi.fn(), update: vi.fn() }));
vi.mock("../lib/inspectionProfilesApi", async () => ({
  ...(await vi.importActual<typeof import("../lib/inspectionProfilesApi")>("../lib/inspectionProfilesApi")),
  fetchInspectionProfiles: mocks.query,
  validateInspectionProfile: mocks.validate,
  updateInspectionProfile: mocks.update,
}));

const fingerprint = { algorithm: "sha256" as const, value: "a".repeat(64) };
const field = { ordinal: 0, name: "Front" };
const check = { checkId: "question-required", kind: "non_empty" as const, roles: ["question"], mode: "any" as const, priority: "high" as const };
const suggestion = { detectedKind: "generic", confidence: 0.8, fieldMappings: [{ role: "question", fields: [field], confidence: 0.9 }], checks: [check], warnings: [], unresolvedFields: [] };
const store = { status: "empty" as const, revision: 0, profileCount: 0, errorCode: null, quarantined: false };
const queryResponse = {
  schemaVersion: 1 as const, status: "available" as const, store, totalCount: 2, returnedCount: 2, limit: 500, truncated: false, skippedCount: 0,
  items: ["Basic", "Cloze"].map((name, index) => ({
    structure: { noteTypeId: String(index + 1), name, kind: index ? "cloze" as const : "standard" as const, fields: [field], templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Front"], backFields: ["Front"] }], fingerprint },
    effectiveState: "not_configured" as const, stateReason: null, authoritative: false, storedProfile: null, suggestion,
  })),
};

describe("Inspection Profiles settings workspace", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("ru");
    container = document.createElement("div");
    container.id = "dashboard-app-shell";
    document.body.append(container);
    root = createRoot(container);
    mocks.query.mockReset().mockResolvedValue(queryResponse);
    mocks.validate.mockReset().mockResolvedValue({ schemaVersion: 2, valid: true, effectiveState: "confirmed", stateReason: null, fieldErrors: {}, preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] } });
    mocks.update.mockReset().mockResolvedValue({ schemaVersion: 1, action: "save", store: { ...store, revision: 1, status: "available" }, profile: null });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it("loads the catalog, creates only a dirty suggestion draft, and confirms through validate v2", async () => {
    await renderPage();
    expect(container.textContent).toContain("Профили проверки");
    expect(container.textContent).toContain("Basic");
    await click(noteButton("Basic"));
    await settle();
    await click(button("Использовать подсказку"));
    expect(container.textContent).toContain("Есть несохранённые изменения");
    expect(mocks.update).not.toHaveBeenCalled();
    await click(button("Подтвердить и включить"));
    await settle();
    expect(mocks.validate).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 2, preview: { mode: "sample", limit: 10 } }), expect.any(AbortSignal));
    expect(mocks.update).toHaveBeenCalledWith(expect.objectContaining({ action: "save", targetState: "confirmed", expectedRevision: 0 }));
  });

  it("protects a dirty draft when switching note types", async () => {
    await renderPage();
    await click(noteButton("Basic"));
    await settle();
    await click(button("Начать с пустого"));
    await click(noteButton("Cloze"));
    expect(document.querySelector('[role="dialog"]')?.textContent).toContain("Отбросить несохранённые изменения");
    expect(container.textContent).toContain("Basic");
  });

  it("renders complete English route copy", async () => {
    await i18n.changeLanguage("en");
    await renderPage();
    expect(container.textContent).toContain("Inspection Profiles");
    expect(container.textContent).toContain("Note types");
    expect(container.textContent).toContain("Not configured");
  });

  async function renderPage() { await act(async () => root.render(<InspectionProfilesSettingsPage />)); await settle(); }
  async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
  async function click(element: HTMLElement) { await act(async () => element.click()); }
  function button(text: string) { const match = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text); if (!match) throw new Error(`missing button ${text}`); return match; }
  function noteButton(text: string) { const match = [...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].find((item) => item.textContent?.includes(text)); if (!match) throw new Error(`missing note ${text}`); return match; }
});
