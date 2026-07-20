// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import type { InspectionProfile, InspectionProfileSummary } from "../../types/inspectionProfiles";
import AdvancedProfileDisclosure from "./AdvancedProfileDisclosure";

const fingerprint = { algorithm: "sha256" as const, value: "e".repeat(64) };
const field = { ordinal: 0, name: "Front" };
const draft: InspectionProfile = { profileId: "note-type-1", noteTypeId: "1", noteTypeName: "Basic", storedState: "suggested", displayName: "Basic", expectedFingerprint: fingerprint, appliesTo: { templateOrdinals: [] }, fieldMappings: [{ role: "question", fields: [field] }], checks: [{ checkId: "question-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" }], confirmedAt: null, updatedAt: "2026-07-20T12:00:00Z" };
const item: InspectionProfileSummary = { structure: { noteTypeId: "1", name: "Basic", kind: "standard", fields: [field], templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Front"], backFields: ["Front"] }], fingerprint }, effectiveState: "not_configured", stateReason: null, authoritative: false, storedProfile: null, suggestion: { detectedKind: "generic", confidence: .9, fieldMappings: [{ role: "question", fields: [field], confidence: .9 }], checks: draft.checks, warnings: [], unresolvedFields: [] } };

describe("AdvancedProfileDisclosure", () => {
  let root: Root;
  let container: HTMLDivElement;
  beforeEach(async () => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; await i18n.changeLanguage("en"); container = document.createElement("div"); document.body.append(container); root = createRoot(container); });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

  it("is collapsed by default and advertises hidden errors in its summary", async () => {
    const onOpenChange = vi.fn();
    await act(async () => root.render(<AdvancedProfileDisclosure item={item} draft={draft} errors={{ "profile.checks.0.roles": "select_role" }} open={false} onOpenChange={onOpenChange} onChange={() => undefined} />));
    const details = container.querySelector("details")!;
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")?.textContent).toContain("1 errors");
    expect(details.textContent).toContain("question-required");
    await act(async () => details.querySelector<HTMLElement>("summary")!.click());
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });
});
