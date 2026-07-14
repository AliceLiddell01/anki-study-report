import { afterEach, describe, expect, it, vi } from "vitest";

import { dashboardTokenFromSearch, runReportAction, runServerAction } from "./actionsApi";

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

  it("posts only the typed deck Browser request shape", async () => {
    vi.stubGlobal("window", { location: { search: "?token=deck-token" } });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, action: "open-deck-browser", message: "Opened deck." }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await runReportAction("open-deck-browser", { deckId: 42, mode: "direct" });
    expect(fetchMock).toHaveBeenCalledWith("/api/actions/open-deck-browser?token=deck-token", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ deckId: 42, mode: "direct" }),
    }));
  });

  it("posts an explicit mode-specific Search selection and preserves semantic result metadata", async () => {
    vi.stubGlobal("window", { location: { search: "?token=search-token" } });
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ok: true,
      action: "open-search-selection",
      resultCode: "search.browser_opened",
      requestedCount: 2,
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(runReportAction("open-search-selection", { mode: "notes", entityIds: ["1", "2"] })).resolves.toMatchObject({
      ok: true,
      resultCode: "search.browser_opened",
      requestedCount: 2,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/actions/open-search-selection?token=search-token", expect.objectContaining({
      body: JSON.stringify({ mode: "notes", entityIds: ["1", "2"] }),
    }));
  });
});
