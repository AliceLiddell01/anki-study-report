// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../../i18n";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";
import AdvancedProfileDisclosure from "./AdvancedProfileDisclosure";

const fingerprint = { algorithm: "sha256" as const, value: "e".repeat(64) };
const fields = [{ ordinal: 0, name: "Front" }, { ordinal: 1, name: "Back" }];
const draft: InspectionProfile = {
  profileId: "note-type-1",
  noteTypeId: "1",
  noteTypeName: "Basic",
  storedState: "suggested",
  displayName: "Basic",
  expectedFingerprint: fingerprint,
  appliesTo: { templateOrdinals: [] },
  fieldMappings: [{ role: "question", fields: [fields[0]!] }],
  checks: [{ checkId: "question-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" }],
  confirmedAt: null,
  updatedAt: "2026-07-20T12:00:00Z",
};
const item: InspectionProfileSummary = {
  structure: {
    noteTypeId: "1",
    name: "Basic",
    kind: "standard",
    fields,
    templates: [
      { ordinal: 0, name: "Card 1", frontFields: ["Front"], backFields: ["Back"] },
      { ordinal: 1, name: "Card 2", frontFields: ["Back"], backFields: ["Front"] },
    ],
    fingerprint,
  },
  effectiveState: "not_configured",
  stateReason: null,
  authoritative: false,
  storedProfile: null,
  suggestion: {
    detectedKind: "generic",
    confidence: .9,
    fieldMappings: [{ role: "question", fields: [fields[0]!], confidence: .9 }],
    checks: draft.checks,
    warnings: [],
    unresolvedFields: [],
  },
};

describe("AdvancedProfileDisclosure", () => {
  let root: Root;
  let container: HTMLDivElement;
  let current: InspectionProfile;

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

  it("renders the authored mappings, checks, and templates columns as one exact editor", async () => {
    await render({ "profile.checks.0.roles": "select_role" });
    const panel = container.querySelector<HTMLElement>("#inspection-advanced-panel")!;
    expect(panel.getAttribute("role")).toBe("tabpanel");
    expect(panel.getAttribute("aria-labelledby")).toBe("inspection-mode-advanced");
    expect(container.querySelector(".inspection-advanced-grid")?.children).toHaveLength(3);
    expect(container.querySelector<HTMLInputElement>("#inspection-check-id-0")?.value).toBe("question-required");
    expect(container.querySelector("#inspection-check-roles-0")?.getAttribute("aria-invalid")).toBe("true");
  });

  it("keeps one strict draft while roles and check kinds change", async () => {
    await render();
    await change(container.querySelector<HTMLInputElement>("#inspection-role-0")!, "prompt");
    expect(current.fieldMappings[0]?.role).toBe("prompt");
    expect(current.checks[0]?.roles).toEqual(["prompt"]);

    await change(container.querySelector<HTMLInputElement>("#inspection-check-id-0")!, "prompt-custom");
    await change(container.querySelector<HTMLSelectElement>("#inspection-check-kind-0")!, "min_text_length");
    expect(current.checks[0]).toEqual(expect.objectContaining({
      checkId: "prompt-custom",
      kind: "min_text_length",
      minLength: 1,
      mode: "any",
    }));

    await change(container.querySelector<HTMLSelectElement>("#inspection-check-kind-0")!, "all_roles_non_empty");
    expect(current.checks[0]).toEqual({
      checkId: "prompt-custom",
      kind: "all_roles_non_empty",
      roles: ["prompt"],
      priority: "high",
    });
  });

  it("preserves unresolved check references when a role is removed", async () => {
    await render();
    await click(container.querySelector<HTMLButtonElement>(".is-mappings .inspection-icon-button")!);
    expect(current.fieldMappings).toEqual([]);
    expect(current.checks).toHaveLength(1);
    expect(current.checks[0]?.roles).toEqual(["question"]);
    await render({ "profile.checks.0.roles": "select_role" });
    expect(container.textContent).toContain("missing role");
  });

  it("prevents an implicit all-template collapse and exposes missing ordinals", async () => {
    current.appliesTo.templateOrdinals = [0];
    await render();
    const selected = container.querySelector<HTMLInputElement>(".is-templates input[type='checkbox']:checked")!;
    expect(selected.disabled).toBe(true);
    expect(selected.getAttribute("aria-describedby")).toBe("inspection-template-scope-keep-one");

    current.appliesTo.templateOrdinals = [99];
    await render({ "profile.appliesTo.templateOrdinals": "unresolved_template" });
    expect(container.textContent).toContain("Saved template ordinals are missing: 99");
    expect(container.querySelector("#inspection-template-scope")?.getAttribute("aria-invalid")).toBe("true");
  });

  it("moves focus deterministically after add and remove actions", async () => {
    await render();
    await click(container.querySelector<HTMLButtonElement>("#inspection-add-mapping")!);
    await renderAndFrame();
    expect(document.activeElement?.id).toBe("inspection-role-1");

    const removeMappings = container.querySelectorAll<HTMLButtonElement>(".is-mappings .inspection-icon-button");
    await click(removeMappings[1]!);
    await renderAndFrame();
    expect(document.activeElement?.id).toBe("inspection-mapping-0");

    await click(container.querySelector<HTMLButtonElement>("#inspection-add-check")!);
    await renderAndFrame();
    expect(document.activeElement?.id).toBe("inspection-check-id-1");
  });

  async function render(errors: Record<string, string> = {}) {
    await act(async () => root.render(<AdvancedProfileDisclosure item={item} draft={current} errors={errors} onChange={(next) => { current = structuredClone(next); }} />));
    await act(async () => { await Promise.resolve(); });
  }

  async function click(element: HTMLElement) {
    await act(async () => element.click());
  }

  async function renderAndFrame() {
    await render();
    await act(async () => { await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve())); });
  }

  async function change(element: HTMLInputElement | HTMLSelectElement, value: string) {
    await act(async () => {
      const prototype = element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLSelectElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(element, value);
      element.dispatchEvent(new Event(element instanceof HTMLInputElement ? "input" : "change", { bubbles: true }));
    });
    await render();
  }
});
