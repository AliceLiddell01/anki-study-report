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

const fingerprint = { algorithm: "sha256" as const, value: "a".repeat(64) };
const store = { status: "empty" as const, revision: 0, profileCount: 0, errorCode: null, quarantined: false };

function noteType(
  noteTypeId: string,
  name: string,
  detectedKind: string,
  fields: string[],
  mappings: Array<[string, string]>,
  checks: InspectionProfileSummary["suggestion"]["checks"],
  state: InspectionProfileSummary["effectiveState"] = "not_configured",
): InspectionProfileSummary {
  const refs = fields.map((field, ordinal) => ({ ordinal, name: field }));
  const storedProfile = state === "not_configured" ? null : {
    profileId: `note-type-${noteTypeId}`,
    noteTypeId,
    noteTypeName: name,
    storedState: state === "disabled" ? "disabled" as const : state === "confirmed" || state === "needs_review" ? "confirmed" as const : "suggested" as const,
    displayName: name,
    expectedFingerprint: fingerprint,
    appliesTo: { templateOrdinals: [] },
    fieldMappings: mappings.map(([role, field]) => ({ role, fields: [refs.find((ref) => ref.name === field)!] })),
    checks,
    confirmedAt: state === "confirmed" || state === "needs_review" ? "2026-07-20T12:00:00Z" : null,
    updatedAt: "2026-07-20T12:00:00Z",
  };
  return {
    structure: {
      noteTypeId,
      name,
      kind: "standard",
      fields: refs,
      templates: [{ ordinal: 0, name: "Card 1", frontFields: fields.slice(0, 1), backFields: fields.slice(1) }],
      fingerprint,
    },
    effectiveState: state,
    stateReason: state === "needs_review" ? "field_changed" : null,
    authoritative: state === "confirmed",
    storedProfile,
    suggestion: {
      detectedKind,
      confidence: 0.92,
      fieldMappings: mappings.map(([role, field]) => ({ role, fields: [refs.find((ref) => ref.name === field)!], confidence: 0.94 })),
      checks,
      warnings: [],
      unresolvedFields: [],
    },
  };
}

const japanese = noteType("1", "Japanese Vocabulary", "japanese_vocab", ["Word", "Meaning", "Audio"], [
  ["term", "Word"], ["meaning", "Meaning"], ["audio", "Audio"],
], [
  { checkId: "meaning-required", kind: "non_empty", roles: ["meaning"], mode: "any", priority: "high" },
  { checkId: "audio-required", kind: "contains_audio", roles: ["audio"], mode: "any", priority: "medium" },
]);
const programming = noteType("2", "Programming Q&A", "programming", ["Question", "Answer", "Code"], [
  ["question", "Question"], ["answer", "Answer"], ["code", "Code"],
], [
  { checkId: "question-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
  { checkId: "answer-required", kind: "non_empty", roles: ["answer"], mode: "any", priority: "high" },
]);
const confirmed = noteType("3", "Confirmed Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "confirmed");
const needsReview = noteType("4", "Changed Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "needs_review");
const disabled = noteType("5", "Disabled Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "disabled");

const queryResponse: InspectionProfilesQueryResponse = {
  schemaVersion: 1,
  status: "available",
  store,
  totalCount: 5,
  returnedCount: 5,
  limit: 500,
  truncated: false,
  skippedCount: 0,
  items: [japanese, programming, confirmed, needsReview, disabled],
};

describe("Inspection Profiles guided settings workspace", () => {
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

  it("materializes a clean generated Japanese draft immediately and switches without a discard dialog", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    const basic = container.querySelector<HTMLElement>("[data-testid='inspection-basic-editor']")!;
    expect(basic.textContent).toContain("Японская лексика");
    expect(basic.textContent).toContain("Аудио: требуется аудио");
    expect(basic.textContent).toContain("Audio");
    expect(basic.textContent).not.toContain("audio-required");
    expect(container.textContent).not.toContain("Использовать подсказку");
    expect(container.textContent).not.toContain("Есть несохранённые изменения");
    expect(mocks.update).not.toHaveBeenCalled();
    expect([...basic.querySelectorAll(".inspection-milestone")].map((node) => node.textContent)).toEqual(["2", "3", "4", "5"]);

    await click(noteButton("Programming Q&A"));
    expect(document.querySelector("[role='dialog']")).toBeNull();
    const programmingBasic = container.querySelector<HTMLElement>("[data-testid='inspection-basic-editor']")!;
    expect(programmingBasic.textContent).toContain("Вопрос: обязательно");
    expect(programmingBasic.textContent).toContain("Ответ: обязательно");
    expect(programmingBasic.textContent).not.toContain("требуется аудио");
  });

  it("protects the draft only after an actual user edit", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    const priority = container.querySelector<HTMLSelectElement>("#inspection-basic-priority-0")!;
    await change(priority, "low");
    expect(container.textContent).toContain("Есть несохранённые изменения");
    await click(noteButton("Programming Q&A"));
    const dialog = document.querySelector<HTMLElement>("[role='dialog']");
    expect(dialog?.textContent).toContain("Отбросить несохранённые изменения");
  });

  it("validates with schema v2 and confirms with update schema v1", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    await click(button("Проверить настройку"));
    expect(milestones()).toEqual(["1", "2", "3", "4", "5", "6", "7"]);
    await click(button("Подтвердить и включить"));
    await settle();
    expect(mocks.validate).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 2, preview: { mode: "sample", limit: 10 } }), expect.any(AbortSignal));
    expect(mocks.update).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 1, action: "save", targetState: "confirmed", expectedRevision: 0 }));
  });

  it("keeps Basic and Advanced mutually exclusive without mutating the draft", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    expect(container.querySelector("[role='tab'][aria-selected='true']")?.textContent).toContain("Основное");
    expect(container.querySelector("[data-testid='inspection-basic-editor']")?.textContent).not.toContain("meaning-required");
    expect(container.querySelector("#inspection-advanced-panel")).toBeNull();
    await click(button("Расширенное"));
    expect(container.querySelector("[data-testid='inspection-basic-editor']")).toBeNull();
    expect(container.querySelector("#inspection-advanced-panel")?.textContent).toContain("meaning-required");
    expect(mocks.update).not.toHaveBeenCalled();
  });

  it("does not require reconfirmation for an unchanged confirmed profile", async () => {
    await renderPage();
    await click(noteButton("Confirmed Basic"));
    expect(container.textContent).toContain("Включено");
    expect(exactButton("Подтвердить и включить")).toBeUndefined();
    expect(exactButton("Проверить настройку")).toBeDefined();
  });

  it("keeps the summary informational and exposes one lifecycle primary action", async () => {
    await renderPage();
    expect(container.querySelector(".inspection-summary button")).toBeNull();
    expect(container.querySelector(".inspection-summary")?.textContent).toContain("Всего типов5");
    expect(container.querySelector(".inspection-empty-editor")?.textContent).toContain("не сохранится и не включит проверки автоматически");

    await click(noteButton("Japanese Vocabulary"));
    expect(primaryButtons().map((item) => item.textContent?.trim())).toEqual(["Подтвердить и включить"]);
    expect(milestones()).toEqual(["1", "2", "3", "4", "5", "7"]);

    await click(noteButton("Changed Basic"));
    expect(primaryButtons().map((item) => item.textContent?.trim())).toEqual(["Проверить и подтвердить снова"]);

    await click(noteButton("Disabled Basic"));
    expect(primaryButtons().map((item) => item.textContent?.trim())).toEqual(["Проверить и включить"]);

    await click(noteButton("Confirmed Basic"));
    expect(primaryButtons()).toHaveLength(0);
  });

  it("separates destructive tools and keeps changed state visible on the Advanced tab", async () => {
    await renderPage();
    await click(noteButton("Confirmed Basic"));
    const priority = container.querySelector<HTMLSelectElement>("#inspection-basic-priority-0")!;
    await change(priority, "low");
    expect(container.querySelector("#inspection-mode-advanced")?.textContent).toContain("Изменено");
    expect(primaryButtons().map((item) => item.textContent?.trim())).toEqual(["Проверить и подтвердить изменения"]);
    const tools = container.querySelector(".inspection-profile-tools")!;
    expect(tools.querySelector(".inspection-profile-tool-group:not(.is-destructive)")?.textContent).toContain("Экспорт JSON");
    expect(tools.querySelector(".inspection-profile-tool-group.is-destructive")?.textContent).toContain("Удалить профиль");
  });

  it("renders the guided workflow in English", async () => {
    await i18n.changeLanguage("en");
    await renderPage();
    await click(noteButton("Programming Q&A"));
    expect(container.textContent).toContain("Suggested setup");
    expect(container.textContent).toContain("Question is required");
    expect(container.textContent).toContain("Confirm and enable");
    expect(container.textContent).toContain("Advanced");
  });

  it("uses the shared workspace roles without turning selection into focus", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    expect(container.querySelector(".inspection-workspace-page.workspace-page")).toBeTruthy();
    expect(container.querySelectorAll(".workspace-region").length).toBe(2);
    expect(container.querySelector(".inspection-note-button.workspace-interactive.workspace-selected")).toBeTruthy();
    expect(container.querySelector(".inspection-state-guidance.workspace-state")).toBeTruthy();
    expect(container.querySelector(".inspection-editor.workspace-safe-area")).toBeNull();
    expect(document.activeElement?.classList.contains("workspace-selected")).toBe(false);
  });

  async function renderPage() { await act(async () => root.render(<InspectionProfilesSettingsPage />)); await settle(); }
  async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
  async function click(element: HTMLElement) { await act(async () => element.click()); await settle(); }
  async function change(element: HTMLSelectElement | HTMLInputElement, value: string) { await act(async () => { element.value = value; element.dispatchEvent(new Event("change", { bubbles: true })); }); await settle(); }
  function button(text: string) { const match = exactButton(text); if (!match) throw new Error(`missing button ${text}`); return match; }
  function exactButton(text: string) { return [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text); }
  function primaryButtons() { return [...container.querySelectorAll<HTMLButtonElement>(".inspection-primary-actions .primary-button")]; }
  function milestones() { return [...container.querySelectorAll(".inspection-editor-stack .inspection-milestone")].map((node) => node.textContent); }
  function noteButton(text: string) { const match = [...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].find((item) => item.textContent?.includes(text)); if (!match) throw new Error(`missing note ${text}`); return match; }
});
