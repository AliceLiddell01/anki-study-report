// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPrivacy, fetchProductNotices, markCurrentReleaseSeen, savePrivacyChoices } from "./productNoticesApi";

describe("product notices API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("uses only token-protected local dashboard endpoints", async () => {
    window.history.replaceState({}, "", "/?token=local-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    } as Response);

    await fetchProductNotices();
    await fetchPrivacy();
    await savePrivacyChoices({ reliabilityDiagnostics: true, featureUsage: false });
    await markCurrentReleaseSeen();

    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      "/api/product-notices?token=local-token",
      "/api/privacy?token=local-token",
      "/api/privacy?token=local-token",
      "/api/product-notices/seen?token=local-token",
    ]);
    expect(fetchMock.mock.calls.every(([url]) => !/^https?:/i.test(String(url)))).toBe(true);
    expect(fetchMock.mock.calls[2]?.[1]).toEqual(expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ purposes: { reliabilityDiagnostics: true, featureUsage: false } }),
    }));
    expect(fetchMock.mock.calls[3]?.[1]).toEqual(expect.objectContaining({ method: "POST", body: "{}" }));
  });

  it("falls back to bundled release history with telemetry effectively disabled", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));

    const result = await fetchProductNotices();

    expect(result.ok).toBe(true);
    expect(result.error).toBe("product_notices_state_unavailable");
    expect(result.showWhatsNew).toBe(true);
    expect(result.requiresConsent).toBe(false);
    expect(Object.values(result.privacy.telemetry.effectivePurposes)).toEqual([false, false]);
    expect(result.changelog.releases.length).toBeGreaterThan(0);
  });
});
