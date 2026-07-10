import { afterEach, describe, expect, it, vi } from "vitest";
import { saveProfilePreferences } from "./profileApi";

describe("profile API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends only the supplied editable patch with dashboard token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, profile: { preferences: { deckOverviewSort: "reviews" } } }),
    });
    vi.stubGlobal("window", { location: { search: "?token=safe-token" } });
    vi.stubGlobal("fetch", fetchMock);
    const result = await saveProfilePreferences({ deckOverviewSort: "reviews" });
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("/api/profile?token=safe-token", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ deckOverviewSort: "reviews" }),
    }));
  });

  it("preserves typed field errors", async () => {
    vi.stubGlobal("window", { location: { search: "?token=t" } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ ok: false, fieldErrors: { customStudyStartedOn: "future" } }),
    }));
    const result = await saveProfilePreferences({ customStudyStartedOn: "2099-01-01" });
    expect(result.fieldErrors).toEqual({ customStudyStartedOn: "future" });
  });
});
