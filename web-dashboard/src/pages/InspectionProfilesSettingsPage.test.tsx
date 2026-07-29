// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resolveInspectionProfileDisplayIdentity } from "../components/inspection-profiles/InspectionProfileEditorIdentity";
import { filterAndSortInspectionProfileItems } from "../components/inspection-profiles/InspectionProfilesCatalog";
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
confirmed.storedProfile!.displayName = "Stored profile identity";
const needsReview = noteType("4", "Changed Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "needs_review");
const disabled = noteType("5", "Disabled Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "disabled");
const suggested = noteType("6", "Draft Basic", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
], "suggested");
const longRussian = noteType("7", "Очень длинное название пользовательского типа записи для проверки переноса без потери текста", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
]);
const longEnglish = noteType("8", "Extremely long customer-facing note type name for stable duplicate-like ordering", "generic", ["Front", "Back"], [["question", "Front"], ["answer", "Back"]], [
  { checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
]);

const queryResponse: InspectionProfilesQueryResponse = {
  schemaVersion: 1,
  status: "available",
  store,
  totalCount: 8,
  returnedCount: 8,
  limit: 500,
  truncated: false,
  skippedCount: 0,
  items: [japanese, programming, confirmed, needsReview, disabled, suggested, longRussian, longEnglish],
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
    expect([...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].map((item) => item.getAttribute("aria-pressed"))).toEqual([
      "false", "false", "false", "false", "false", "false", "false", "false",
    ]);
    expect([...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].map((item) => item.title).slice(0, 3)).toEqual([
      "Changed Basic",
      "Confirmed Basic",
      "Draft Basic",
    ]);
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
    expect(milestones()).toEqual(["2", "3", "4", "5", "6", "7"]);
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
    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-advanced")!);
    expect(container.querySelector("[data-testid='inspection-basic-editor']")).toBeNull();
    expect(container.querySelector<HTMLInputElement>("#inspection-check-id-0")?.value).toBe("meaning-required");
    expect(mocks.update).not.toHaveBeenCalled();
  });

  it("round-trips Basic and Advanced edits through one unsaved strict draft", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    await change(container.querySelector<HTMLSelectElement>("#inspection-basic-priority-0")!, "low");

    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-advanced")!);
    expect(container.querySelector<HTMLSelectElement>("#inspection-check-priority-0")?.value).toBe("low");
    await change(container.querySelector<HTMLInputElement>("#inspection-role-1")!, "definition");

    await click(container.querySelector<HTMLButtonElement>("#inspection-mode-basic")!);
    expect(container.querySelector<HTMLSelectElement>("#inspection-basic-check-role-0")?.value).toBe("definition");
    expect(container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")?.value).toBe("1");
    expect(mocks.validate).not.toHaveBeenCalled();
    expect(mocks.update).not.toHaveBeenCalled();
  });

  it("supports Arrow, Home, and End navigation across editor tabs", async () => {
    await renderPage();
    await click(noteButton("Japanese Vocabulary"));
    const basic = container.querySelector<HTMLButtonElement>("#inspection-mode-basic")!;
    basic.focus();
    await keyDown(basic, "ArrowRight");
    expect(document.activeElement?.id).toBe("inspection-mode-advanced");
    expect(container.querySelector("#inspection-advanced-panel")).toBeTruthy();
    const advanced = container.querySelector<HTMLButtonElement>("#inspection-mode-advanced")!;
    await keyDown(advanced, "Home");
    expect(document.activeElement?.id).toBe("inspection-mode-basic");
    expect(container.querySelector("#inspection-basic-mode-panel")).toBeTruthy();
    await keyDown(container.querySelector<HTMLButtonElement>("#inspection-mode-basic")!, "End");
    expect(document.activeElement?.id).toBe("inspection-mode-advanced");
  });

  it("does not require reconfirmation for an unchanged confirmed profile", async () => {
    await renderPage();
    await click(noteButton("Confirmed Basic"));
    expect(container.querySelector(".inspection-profile-identity")?.textContent).toContain("Stored profile identity");
    expect(container.textContent).toContain("Включено");
    expect(exactButton("Подтвердить и включить")).toBeUndefined();
    expect(exactButton("Проверить настройку")).toBeDefined();
  });

  it("integrates state into the compact catalog and exposes one lifecycle primary action", async () => {
    await renderPage();
    expect(container.querySelector(".inspection-summary")).toBeNull();
    expect(container.querySelector(".inspection-catalog-header")?.textContent).toContain("8/8");
    expect(container.querySelector(".inspection-empty-editor")?.textContent).toContain("не сохранится и не включит проверки автоматически");

    await click(noteButton("Japanese Vocabulary"));
    expect(primaryButtons().map((item) => item.textContent?.trim())).toEqual(["Подтвердить и включить"]);
    expect(milestones()).toEqual(["2", "3", "4", "5", "7"]);
    expect(container.querySelector(".inspection-lifecycle")?.textContent).toContain("Безопасный вариант уже подготовлен");

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
    expect(container.querySelector(".inspection-profile-identity")?.textContent).toContain("Proposed profile: Programming question/answer");
    expect(container.querySelector(".inspection-profile-identity")?.textContent).not.toContain("Profile: Programming Q&A");
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
    expect(container.querySelector(".inspection-lifecycle")).toBeTruthy();
    expect(container.querySelector(".inspection-editor.workspace-safe-area")).toBeNull();
    expect(document.activeElement?.classList.contains("workspace-selected")).toBe(false);
  });

  it("sorts filtered catalog items by lifecycle priority without mutating the source array", () => {
    const source = [disabled, longEnglish, confirmed, japanese, suggested, needsReview, programming];
    const originalIds = source.map((item) => item.structure.noteTypeId);
    const result = filterAndSortInspectionProfileItems(source, "all", "", "en");
    expect(result.map((item) => item.effectiveState)).toEqual([
      "needs_review",
      "confirmed",
      "suggested",
      "not_configured",
      "not_configured",
      "not_configured",
      "disabled",
    ]);
    const notConfiguredNames = result
      .filter((item) => item.effectiveState === "not_configured")
      .map((item) => item.structure.name);
    expect(notConfiguredNames).toEqual([...notConfiguredNames].sort((left, right) => left.localeCompare(right, "en", { sensitivity: "base", numeric: true })));
    expect(source.map((item) => item.structure.noteTypeId)).toEqual(originalIds);

    const filtered = filterAndSortInspectionProfileItems(source, "all", "basic", "en");
    expect(filtered.map((item) => item.effectiveState)).toEqual(["needs_review", "confirmed", "suggested", "disabled"]);
  });

  it("keeps search, state filtering, clear filters, long names, and selected state coherent", async () => {
    await renderPage();
    await click(noteButton(longRussian.structure.name));
    expect(noteButton(longRussian.structure.name).getAttribute("aria-pressed")).toBe("true");

    const state = container.querySelector<HTMLSelectElement>("#inspection-profile-state-filter")!;
    await change(state, "not_configured");
    expect(noteButton(longRussian.structure.name).getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector(".inspection-clear-filters")).toBeTruthy();

    const search = container.querySelector<HTMLInputElement>("#inspection-profile-search")!;
    await change(search, "Extremely long");
    expect(noteButton(longEnglish.structure.name).title).toBe(longEnglish.structure.name);
    expect(container.querySelector(".inspection-note-list")?.textContent).not.toContain(longRussian.structure.name);

    await click(container.querySelector<HTMLButtonElement>(".inspection-clear-filters")!);
    expect(container.querySelector(".inspection-clear-filters")).toBeNull();
    expect(noteButton(longRussian.structure.name).getAttribute("aria-pressed")).toBe("true");
  });

  it("uses truthful generated identities and an explicit no-name fallback in RU and EN", async () => {
    await renderPage();
    await click(noteButton("Programming Q&A"));
    const ruIdentity = container.querySelector(".inspection-profile-identity")!;
    expect(ruIdentity.textContent).toContain("Предлагаемый профиль: Вопрос по программированию");
    expect(ruIdentity.getAttribute("data-identity-source")).toBe("suggestion");
    expect((container.querySelector(".inspection-editor-identity")?.textContent?.match(/Вопрос по программированию/g) ?? [])).toHaveLength(1);

    await click(noteButton(longEnglish.structure.name));
    expect(container.querySelector(".inspection-profile-identity")?.textContent).toContain("Предлагаемый профиль: Пока без отдельного имени");
    expect(container.querySelector(".inspection-profile-identity")?.getAttribute("data-identity-source")).toBe("explicit-fallback");

    await act(async () => {
      await i18n.changeLanguage("en");
    });
    await settle();
    await click(noteButton("Programming Q&A"));
    expect(container.querySelector(".inspection-profile-identity")?.textContent).toContain("Proposed profile: Programming question/answer");

    const resolved = resolveInspectionProfileDisplayIdentity({
      item: longEnglish,
      draft: { ...longEnglish.storedProfile!, displayName: longEnglish.structure.name },
      generatedDraft: true,
      detectedKindLabel: "General front/back",
      detectedKindMeaningful: false,
      noIndependentName: "No separate name yet",
    });
    expect(resolved).toEqual({ value: "No separate name yet", source: "explicit-fallback" });
  });

  async function renderPage() { await act(async () => root.render(<InspectionProfilesSettingsPage />)); await settle(); }
  async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
  async function click(element: HTMLElement) { await act(async () => element.click()); await settle(); }
  async function keyDown(element: HTMLElement, key: string) {
    await act(async () => {
      element.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
      await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
    });
    await settle();
  }
  async function change(element: HTMLSelectElement | HTMLInputElement, value: string) {
    await act(async () => {
      const prototype = element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLSelectElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(element, value);
      element.dispatchEvent(new Event(element instanceof HTMLInputElement ? "input" : "change", { bubbles: true }));
    });
    await settle();
  }
  function button(text: string) { const match = exactButton(text); if (!match) throw new Error(`missing button ${text}`); return match; }
  function exactButton(text: string) { return [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text); }
  function primaryButtons() { return [...container.querySelectorAll<HTMLButtonElement>(".inspection-primary-actions .primary-button")]; }
  function milestones() { return [...container.querySelectorAll(".inspection-editor-stack .inspection-milestone")].map((node) => node.textContent); }
  function noteButton(text: string) { const match = [...container.querySelectorAll<HTMLButtonElement>(".inspection-note-button")].find((item) => item.textContent?.includes(text)); if (!match) throw new Error(`missing note ${text}`); return match; }
});
