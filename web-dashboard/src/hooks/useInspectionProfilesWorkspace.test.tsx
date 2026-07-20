// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { InspectionProfilesWorkspace } from "./useInspectionProfilesWorkspace";
import { useInspectionProfilesWorkspace } from "./useInspectionProfilesWorkspace";
import type { InspectionProfilesQueryResponse } from "../types/inspectionProfiles";
import { InspectionProfilesApiError } from "../lib/inspectionProfilesApi";

const mocks = vi.hoisted(() => ({ query: vi.fn(), validate: vi.fn(), update: vi.fn() }));
vi.mock("../lib/inspectionProfilesApi", async () => ({
  ...(await vi.importActual<typeof import("../lib/inspectionProfilesApi")>("../lib/inspectionProfilesApi")),
  fetchInspectionProfiles: mocks.query,
  validateInspectionProfile: mocks.validate,
  updateInspectionProfile: mocks.update,
}));

const fingerprint = { algorithm: "sha256" as const, value: "b".repeat(64) };
const field = { ordinal: 0, name: "Front" };
const check = { checkId: "front-required", kind: "non_empty" as const, roles: ["question"], mode: "any" as const, priority: "high" as const };
const response: InspectionProfilesQueryResponse = {
  schemaVersion: 1,
  status: "available",
  store: { status: "empty", revision: 0, profileCount: 0, errorCode: null, quarantined: false },
  totalCount: 2,
  returnedCount: 2,
  limit: 500,
  truncated: false,
  skippedCount: 0,
  items: ["1", "2"].map((noteTypeId) => ({
    structure: { noteTypeId, name: `Type ${noteTypeId}`, kind: "standard", fields: [field], templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Front"], backFields: ["Front"] }], fingerprint },
    effectiveState: "not_configured",
    stateReason: null,
    authoritative: false,
    storedProfile: null,
    suggestion: { detectedKind: "generic", confidence: 0.9, fieldMappings: [{ role: "question", fields: [field], confidence: 0.9 }], checks: [check], warnings: [], unresolvedFields: [] },
  })),
};

describe("useInspectionProfilesWorkspace", () => {
  let root: Root;
  let container: HTMLDivElement;
  let latest: InspectionProfilesWorkspace;

  function Harness() {
    latest = useInspectionProfilesWorkspace();
    return <div data-origin={latest.draftOrigin} data-dirty={latest.dirty ? "yes" : "no"} />;
  }

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    mocks.query.mockReset().mockResolvedValue(response);
    mocks.validate.mockReset().mockResolvedValue({ schemaVersion: 2, valid: true, effectiveState: "confirmed", stateReason: null, fieldErrors: {}, preview: { status: "unavailable", requestedCount: 10, evaluatedCount: 0, missingCardIds: [], failureCount: 0, truncated: false, items: [] } });
    mocks.update.mockReset().mockResolvedValue({ schemaVersion: 1, action: "save", store: { ...response.store, status: "available", revision: 1 }, profile: null });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });

  it("creates a reproducible generated draft without marking user work dirty", async () => {
    await render();
    await act(async () => { expect(latest.select("1")).toBe(true); });
    expect(latest.draftOrigin).toBe("generated");
    expect(latest.generatedDraft).toBe(true);
    expect(latest.hasUserEdits).toBe(false);
    expect(latest.dirty).toBe(false);
    expect(latest.draft?.checks[0]?.checkId).toBe("front-required");
    expect(mocks.update).not.toHaveBeenCalled();
    await act(async () => { expect(latest.select("2")).toBe(true); });
    expect(latest.selectedNoteTypeId).toBe("2");
  });

  it("marks only actual edits dirty and protects selection", async () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    await render();
    await act(async () => { latest.select("1"); });
    await act(async () => latest.setDraftFromUser({ ...latest.draft!, displayName: "Edited" }));
    expect(latest.hasUserEdits).toBe(true);
    expect(latest.dirty).toBe(true);
    expect(latest.select("2")).toBe(false);
    expect(addSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
    await act(async () => { expect(latest.select("2", true)).toBe(true); });
    expect(latest.dirty).toBe(false);
  });

  it("rebuilds a clean generated draft on reload but preserves a dirty draft", async () => {
    await render();
    await act(async () => { latest.select("1"); });
    const changed = structuredClone(response);
    changed.items[0]!.suggestion.checks = [{ ...check, checkId: "fresh-required" }];
    mocks.query.mockResolvedValueOnce(changed);
    await act(async () => latest.reload());
    expect(latest.draft?.checks[0]?.checkId).toBe("fresh-required");

    await act(async () => latest.setDraftFromUser({ ...latest.draft!, displayName: "Protected" }));
    mocks.query.mockResolvedValueOnce(response);
    await act(async () => latest.reload());
    expect(latest.draft?.displayName).toBe("Protected");
  });

  it("tracks imported and empty drafts as user-owned and non-authoritative", async () => {
    await render();
    await act(async () => { latest.select("1"); });
    await act(async () => latest.setImportedDraft({ ...latest.draft!, displayName: "Imported" }));
    expect(latest.draftOrigin).toBe("imported");
    expect(latest.dirty).toBe(true);
    await act(async () => latest.startEmpty());
    expect(latest.draftOrigin).toBe("empty");
    expect(latest.draft?.fieldMappings).toEqual([]);
    expect(latest.dirty).toBe(true);
  });

  it("uses validate v2 and update v1 only after explicit save", async () => {
    await render();
    await act(async () => { latest.select("1"); });
    expect(mocks.validate).not.toHaveBeenCalled();
    expect(mocks.update).not.toHaveBeenCalled();
    await act(async () => { expect(await latest.save("confirmed")).toBe(true); });
    expect(mocks.validate).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 2, preview: { mode: "sample", limit: 10 } }), expect.any(AbortSignal));
    expect(mocks.update).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 1, action: "save", targetState: "confirmed", expectedRevision: 0 }));
  });

  it("preserves the user draft on a revision conflict", async () => {
    await render();
    await act(async () => { latest.select("1"); });
    await act(async () => latest.setDraftFromUser({ ...latest.draft!, displayName: "My work" }));
    mocks.update.mockRejectedValueOnce(new InspectionProfilesApiError("conflict", { code: "inspection_profile_revision_conflict", status: 409, currentRevision: 7 }));
    await act(async () => { expect(await latest.save("confirmed")).toBe(false); });
    expect(latest.conflictRevision).toBe(7);
    expect(latest.draft?.displayName).toBe("My work");
    expect(latest.dirty).toBe(true);
  });

  async function render() {
    await act(async () => root.render(<Harness />));
    await settle();
  }
  async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
});
