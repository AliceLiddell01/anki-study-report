// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchInspectionProfiles,
  InspectionProfilesApiError,
  parseInspectionProfilesQueryResponse,
  parseInspectionUpdateResponse,
  parseInspectionValidateResponse,
} from "./inspectionProfilesApi";


const fingerprint = { algorithm: "sha256", value: "a".repeat(64) };
const field = { ordinal: 1, name: "Meaning" };
const check = { checkId: "meaning-required", kind: "non_empty", roles: ["meaning"], mode: "any", priority: "high" };
const profile = {
  profileId: "note-type-123",
  noteTypeId: "123",
  noteTypeName: "Basic",
  storedState: "confirmed",
  displayName: "Basic",
  expectedFingerprint: fingerprint,
  appliesTo: { templateOrdinals: [] },
  fieldMappings: [{ role: "meaning", fields: [field] }],
  checks: [check],
  confirmedAt: "2026-07-18T00:00:00Z",
  updatedAt: "2026-07-18T00:00:00Z",
};
const store = { status: "available", revision: 1, profileCount: 1, errorCode: null, quarantined: false };
const queryResponse = {
  schemaVersion: 1,
  status: "available",
  store,
  totalCount: 1,
  returnedCount: 1,
  limit: 500,
  truncated: false,
  skippedCount: 0,
  items: [{
    structure: {
      noteTypeId: "123",
      name: "Basic",
      kind: "standard",
      fields: [{ ordinal: 0, name: "Front" }, field],
      templates: [{ ordinal: 0, name: "Card 1", frontFields: ["Front"], backFields: ["Meaning"] }],
      fingerprint,
    },
    effectiveState: "confirmed",
    stateReason: null,
    authoritative: true,
    storedProfile: profile,
    suggestion: {
      detectedKind: "generic",
      confidence: 0.8,
      fieldMappings: [{ role: "meaning", fields: [field], confidence: 0.9 }],
      checks: [check],
      warnings: [],
      unresolvedFields: [{ ordinal: 0, name: "Front" }],
    },
  }],
};

afterEach(() => vi.unstubAllGlobals());

describe("Inspection Profiles API contract", () => {
  it("parses a strict catalog and confirmed profile", () => {
    expect(parseInspectionProfilesQueryResponse(queryResponse)).toEqual(queryResponse);
  });

  it("fails closed on future schema, unknown checks, unknown fields, and non-finite values", () => {
    const invalid = [
      { ...queryResponse, schemaVersion: 2 },
      { ...queryResponse, extra: true },
      { ...queryResponse, totalCount: Number.NaN },
      {
        ...queryResponse,
        items: [{ ...queryResponse.items[0], storedProfile: { ...profile, checks: [{ ...check, kind: "regex", pattern: ".*" }] } }],
      },
    ];
    for (const value of invalid) {
      expect(() => parseInspectionProfilesQueryResponse(value)).toThrowError(InspectionProfilesApiError);
    }
  });

  it("parses bounded preview failures without raw note content", () => {
    const response = {
      schemaVersion: 1,
      valid: true,
      effectiveState: "confirmed",
      stateReason: null,
      fieldErrors: {},
      preview: {
        status: "available",
        requestedCount: 1,
        evaluatedCount: 1,
        missingCardIds: [],
        failureCount: 1,
        truncated: false,
        items: [{
          cardId: "9",
          noteId: "8",
          failureCount: 1,
          failures: [{
            profileId: "note-type-123",
            noteTypeId: "123",
            checkId: "meaning-required",
            checkKind: "non_empty",
            scope: "note",
            priority: "high",
            targetRoles: ["meaning"],
            mappedFields: [field],
            evidence: { expectedCondition: "any_non_empty", actualTextLength: 0, expectedTextLength: null, marker: null, markerPresent: null },
            profileRevision: 1,
            fingerprint: "a".repeat(64),
            affectedSiblingCount: 2,
            templateOrdinals: [],
          }],
        }],
      },
    };
    expect(parseInspectionValidateResponse(response)).toEqual(response);
    expect(JSON.stringify(response)).not.toContain("rawFields");
  });

  it("parses revision-bearing update results", () => {
    expect(parseInspectionUpdateResponse({ schemaVersion: 1, action: "save", store, profile })).toEqual({
      schemaVersion: 1, action: "save", store, profile,
    });
  });

  it("posts JSON with token and rejects extra envelope fields", async () => {
    window.history.replaceState(null, "", "/?token=secret#/settings");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(
      JSON.stringify({ ok: true, response: queryResponse }), { status: 200 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    const request = { schemaVersion: 1 as const, noteTypeIds: ["123"], limit: 500 };
    await expect(fetchInspectionProfiles(request)).resolves.toEqual(queryResponse);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/inspection-profiles/query?token=secret");
    expect(String(url)).not.toContain("123");
    expect(JSON.parse(String(init?.body))).toEqual(request);

    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true, response: queryResponse, extra: true }), { status: 200 })));
    await expect(fetchInspectionProfiles(request)).rejects.toMatchObject({ code: "inspection_profiles_failed" });
  });
});
