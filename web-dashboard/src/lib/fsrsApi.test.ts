// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchFsrs, fsrsQueryKey } from "./fsrsApi";

describe("FSRS API", () => {
  beforeEach(() => { window.history.replaceState({}, "", "/?token=safe"); vi.restoreAllMocks(); });
  it("sends only the typed operation contract", async () => {
    const query = { operation: "memory", scope: { kind: "all_collection" }, period: "90d" } as const;
    const response = { schemaVersion: 1, operation: "memory", query, result: {}, calculationVersion: "v1" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, response }), { status: 200, headers: { "Content-Type": "application/json" } }));
    await expect(fetchFsrs(query)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith("/api/statistics/fsrs/query?token=safe", expect.objectContaining({ method: "POST", body: fsrsQueryKey(query) }));
    expect(fsrsQueryKey(query)).not.toContain("search");
  });
});
