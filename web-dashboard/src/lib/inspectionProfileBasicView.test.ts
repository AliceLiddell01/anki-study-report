import { describe, expect, it } from "vitest";
import { createCheck, createStableCheckId, friendlyDetectedKind, friendlyRole, projectBasicProfile } from "./inspectionProfileBasicView";
import type { InspectionCheck, InspectionProfile, InspectionProfileSummary } from "../types/inspectionProfiles";

const fingerprint = { algorithm: "sha256" as const, value: "c".repeat(64) };
const fields = [
  { ordinal: 0, name: "Question" },
  { ordinal: 1, name: "Answer" },
  { ordinal: 2, name: "Audio" },
];
const checks: InspectionCheck[] = [
  { checkId: "required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" },
  { checkId: "audio", kind: "contains_audio", roles: ["audio"], mode: "any", priority: "medium" },
  { checkId: "image", kind: "contains_image", roles: ["answer"], mode: "any", priority: "low" },
  { checkId: "length", kind: "min_text_length", roles: ["answer"], mode: "any", priority: "medium", minLength: 5 },
  { checkId: "one", kind: "one_of_roles_non_empty", roles: ["question", "answer"], priority: "medium" },
  { checkId: "all", kind: "all_roles_non_empty", roles: ["question", "answer"], priority: "high" },
];
const profile: InspectionProfile = {
  profileId: "note-type-1",
  noteTypeId: "1",
  noteTypeName: "Anything",
  storedState: "suggested",
  displayName: "Anything",
  expectedFingerprint: fingerprint,
  appliesTo: { templateOrdinals: [] },
  fieldMappings: [
    { role: "question", fields: [fields[0]!] },
    { role: "answer", fields: [fields[1]!] },
    { role: "audio", fields: [fields[2]!] },
  ],
  checks,
  confirmedAt: null,
  updatedAt: "2026-07-20T12:00:00Z",
};
const item: InspectionProfileSummary = {
  structure: { noteTypeId: "1", name: "Anything", kind: "standard", fields, templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Question"], backFields: ["Answer"] }], fingerprint },
  effectiveState: "not_configured",
  stateReason: null,
  authoritative: false,
  storedProfile: null,
  suggestion: { detectedKind: "programming", confidence: 0.91, fieldMappings: profile.fieldMappings.map((mapping) => ({ ...mapping, confidence: 0.9 })), checks, warnings: [], unresolvedFields: [] },
};

describe("inspectionProfileBasicView", () => {
  it("projects every strict check kind without exposing IDs as titles", () => {
    const view = projectBasicProfile(item, profile, "en");
    expect(view.requirements).toHaveLength(6);
    expect(view.requirements.map((requirement) => requirement.check.kind)).toEqual([
      "non_empty", "contains_audio", "contains_image", "min_text_length", "one_of_roles_non_empty", "all_roles_non_empty",
    ]);
    expect(view.requirements.map((requirement) => requirement.title)).not.toContain("required");
    expect(view.requirements[0]?.title).toBe("Question is required");
    expect(view.requirements[1]?.title).toBe("Audio must contain audio");
  });

  it("uses backend detectedKind rather than the note type display name", () => {
    expect(friendlyDetectedKind(item.suggestion.detectedKind, "en").label).toBe("Programming question/answer");
    expect(projectBasicProfile({ ...item, structure: { ...item.structure, name: "Japanese Audio Programming" } }, profile, "en").detectedKind.label).toBe("Programming question/answer");
  });

  it("recognizes the backend canonical basic kind", () => {
    expect(friendlyDetectedKind("basic", "en")).toEqual(expect.objectContaining({ label: "General front/back", known: true }));
    expect(friendlyDetectedKind("basic", "ru")).toEqual(expect.objectContaining({ label: "Общий front/back", known: true }));
  });

  it("provides a safe custom-role fallback", () => {
    expect(friendlyRole("my_custom_role", "ru")).toEqual(expect.objectContaining({ label: "My custom role", known: false }));
  });

  it("generates bounded collision-safe stable check IDs", () => {
    const occupied = { ...profile, checks: [{ ...checks[0]!, checkId: "non-empty-1" }] };
    expect(createStableCheckId(occupied, "non_empty")).toBe("non-empty-2");
    const created = createCheck(occupied, "min_text_length");
    expect(created.checkId).toBe("min-text-length-1");
    expect(created.kind).toBe("min_text_length");
  });
});
