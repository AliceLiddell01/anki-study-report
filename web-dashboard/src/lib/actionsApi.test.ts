import { afterEach, describe, expect, it, vi } from "vitest";

import { dashboardTokenFromSearch, runServerAction } from "./actionsApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("actionsApi", () => {
  it("reads dashboard token from a URL search string", () => {
    expect(dashboardTokenFromSearch("?token=abc%20123")).toBe("abc 123");
  });

  it("falls back to an empty token", () => {
    expect(dashboardTokenFromSearch("")).toBe("");
    expect(dashboardTokenFromSearch("?view=stats")).toBe("");
  });

  it("posts server actions with the dashboard token", async () => {
    vi.stubGlobal("window", { location: { search: "?token=abc%20123" } });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, action: "copy-url", message: "Copied dashboard URL." }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(runServerAction("copy-url")).resolves.toEqual({
      ok: true,
      action: "copy-url",
      message: "Copied dashboard URL.",
      error: undefined,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/server/copy-url?token=abc%20123", {
      method: "POST",
      cache: "no-store",
    });
  });
});
