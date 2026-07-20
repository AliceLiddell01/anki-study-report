// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../../i18n";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";
import BasicProfileEditor from "./BasicProfileEditor";

const fingerprint = { algorithm: "sha256" as const, value: "d".repeat(64) };
const fields = [{ ordinal: 0, name: "Question" }, { ordinal: 1, name: "Answer" }, { ordinal: 2, name: "Code" }];
const draft: InspectionProfile = {
  profileId: "note-type-1", noteTypeId: "1", noteTypeName: "Programming", storedState: "suggested", displayName: "Programming",
  expectedFingerprint: fingerprint, appliesTo: { templateOrdinals: [] }, confirmedAt: null, updatedAt: "2026-07-20T12:00:00Z",
  fieldMappings: [{ role: "question", fields: [fields[0]!] }, { role: "answer", fields: [fields[1]!] }],
  checks: [{ checkId: "question-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" }],
};
const item: InspectionProfileSummary = {
  structure: { noteTypeId: "1", name: "Programming", kind: "standard", fields, templates: [{ ordinal: 0, name: "Recognition", frontFields: ["Question"], backFields: ["Answer"] }, { ordinal: 1, name: "Production", frontFields: ["Answer"], backFields: ["Question"] }], fingerprint },
  effectiveState: "not_configured", stateReason: null, authoritative: false, storedProfile: null,
  suggestion: { detectedKind: "programming", confidence: 0.9, fieldMappings: draft.fieldMappings.map((mapping) => ({ ...mapping, confidence: 0.9 })), checks: draft.checks, warnings: [], unresolvedFields: [] },
};

describe("BasicProfileEditor", () => {
  let root: Root;
  let container: HTMLDivElement;
  let current = structuredClone(draft);

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("en");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    current = structuredClone(draft);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("edits the exact v1 draft and prevents duplicate field claims", async () => {
    await render();
    const answerSelect = container.querySelector<HTMLSelectElement>("#inspection-basic-role-1")!;
    expect([...answerSelect.options].find((option) => option.value === "0")?.disabled).toBe(true);
    await change(answerSelect, "2");
    expect(current.fieldMappings[1]?.fields).toEqual([{ ordinal: 2, name: "Code" }]);
  });

  it("adds and removes a strict built-in requirement with a stable internal ID", async () => {
    await render();
    await change(container.querySelector<HTMLSelectElement>("#inspection-basic-new-requirement")!, "min_text_length");
    await click(button("Add"));
    expect(current.checks.at(-1)).toEqual(expect.objectContaining({ checkId: "min-text-length-1", kind: "min_text_length", minLength: 1 }));
    await render();
    expect(container.querySelector("[data-testid='inspection-basic-editor']")?.textContent).not.toContain("min-text-length-1");
    const remove = [...container.querySelectorAll<HTMLButtonElement>(".inspection-icon-button")].at(-1)!;
    await click(remove);
    expect(current.checks).toHaveLength(1);
  });

  it("shows friendly template names without ordinal copy", async () => {
    await render();
    const selectedScope = [...container.querySelectorAll<HTMLInputElement>("input[type='radio']")][1]!;
    await act(async () => selectedScope.click());
    await render();
    expect(container.textContent).toContain("Recognition");
    expect(container.textContent).toContain("Production");
    expect(container.textContent).not.toContain("Ordinal");
  });

  async function render() {
    await act(async () => root.render(<BasicProfileEditor item={item} draft={current} errors={{}} onChange={(next) => { current = structuredClone(next); }} />));
    await settle();
  }
  async function settle() { await act(async () => { await Promise.resolve(); }); }
  async function click(element: HTMLElement) { await act(async () => element.click()); await render(); }
  async function change(element: HTMLSelectElement, value: string) { await act(async () => { element.value = value; element.dispatchEvent(new Event("change", { bubbles: true })); }); await render(); }
  function button(text: string) { const match = [...container.querySelectorAll<HTMLButtonElement>("button")].find((element) => element.textContent?.trim() === text); if (!match) throw new Error(`Missing ${text}`); return match; }
});
