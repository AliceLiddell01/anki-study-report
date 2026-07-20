// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../../i18n";
import type { InspectionProfile, InspectionProfileSummary, InspectionValidateResponse } from "../../types/inspectionProfiles";
import ProfileValidationResult from "./ProfileValidationResult";

const fingerprint = { algorithm: "sha256" as const, value: "f".repeat(64) };
const field = { ordinal: 0, name: "Audio" };
const draft: InspectionProfile = { profileId: "note-type-1", noteTypeId: "1", noteTypeName: "Japanese", storedState: "suggested", displayName: "Japanese", expectedFingerprint: fingerprint, appliesTo: { templateOrdinals: [] }, fieldMappings: [{ role: "audio", fields: [field] }], checks: [{ checkId: "audio-required", kind: "contains_audio", roles: ["audio"], mode: "any", priority: "high" }], confirmedAt: null, updatedAt: "2026-07-20T12:00:00Z" };
const item: InspectionProfileSummary = { structure: { noteTypeId: "1", name: "Japanese", kind: "standard", fields: [field], templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Audio"], backFields: ["Audio"] }], fingerprint }, effectiveState: "not_configured", stateReason: null, authoritative: false, storedProfile: null, suggestion: { detectedKind: "japanese_vocab", confidence: .9, fieldMappings: [{ role: "audio", fields: [field], confidence: .9 }], checks: draft.checks, warnings: [], unresolvedFields: [] } };
const validation: InspectionValidateResponse = { schemaVersion: 2, valid: true, effectiveState: "suggested", stateReason: null, fieldErrors: {}, preview: { status: "available", requestedCount: 10, evaluatedCount: 1, missingCardIds: [], failureCount: 1, truncated: false, items: [{ cardId: "10", noteId: "20", failureCount: 1, failures: [{ profileId: "note-type-1", noteTypeId: "1", checkId: "audio-required", checkKind: "contains_audio", scope: "note", priority: "high", targetRoles: ["audio"], mappedFields: [field], evidence: { expectedCondition: "contains_audio", actualTextLength: null, expectedTextLength: null, marker: "audio", markerPresent: false }, profileRevision: 0, fingerprint: fingerprint.value, affectedSiblingCount: 1, templateOrdinals: [0] }] }] } };

describe("ProfileValidationResult", () => {
  let root: Root;
  let container: HTMLDivElement;
  beforeEach(async () => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; await i18n.changeLanguage("en"); container = document.createElement("div"); document.body.append(container); root = createRoot(container); });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

  it("groups failures by friendly requirement without exposing check or card IDs", async () => {
    await act(async () => root.render(<ProfileValidationResult item={item} draft={draft} validation={validation} />));
    expect(container.textContent).toContain("Audio must contain audio");
    expect(container.textContent).toContain("The required audio marker was not found");
    expect(container.textContent).not.toContain("audio-required");
    expect(container.textContent).not.toContain("10");
    expect(container.textContent).not.toContain("20");
  });

  it("states honestly when no content sample is available", async () => {
    await act(async () => root.render(<ProfileValidationResult item={item} draft={draft} validation={{ ...validation, preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] } }} />));
    expect(container.textContent).toContain("there are no cards available for a content sample");
  });
});
