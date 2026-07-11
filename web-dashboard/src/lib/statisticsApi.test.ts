// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import { fetchStatistics, StatisticsApiError, statisticsQueryKey } from "./statisticsApi";

afterEach(() => vi.unstubAllGlobals());

describe("statistics API", () => {
  it("posts only the normalized typed query with the dashboard token", async () => {
    window.history.replaceState(null, "", "/?token=secret-token#/stats");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ ok: true, result: mockReport.statisticsHub!.initialResult }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const query = { scope: { kind: "dashboard" as const }, period: "90d" as const, granularity: "auto" as const, comparison: true };
    await fetchStatistics(query);
    expect(fetchMock).toHaveBeenCalledWith("/api/statistics/query?token=secret-token", expect.objectContaining({ method: "POST", body: statisticsQueryKey(query) }));
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]?.body))).toEqual(query);
  });

  it("normalizes all-time comparison off in the request key", () => {
    expect(JSON.parse(statisticsQueryKey({ scope: { kind: "all_collection" }, period: "all", granularity: "day", comparison: true })).comparison).toBe(false);
  });

  it("surfaces typed validation errors without leaking technical data", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: false, error: "invalid_statistics_query", message: "Проверьте параметры.", fieldErrors: { period: "Unsupported period." } }), { status: 400, headers: { "Content-Type": "application/json" } })));
    await expect(fetchStatistics({ scope: { kind: "dashboard" }, period: "90d", granularity: "auto", comparison: true })).rejects.toMatchObject({ message: "Проверьте параметры.", fieldErrors: { period: "Unsupported period." } } satisfies Partial<StatisticsApiError>);
  });
});
