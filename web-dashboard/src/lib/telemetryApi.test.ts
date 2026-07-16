// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  checkConnectionAndSendNow,
  deleteTelemetryData,
  durationBucket,
  emitTelemetryEvent,
  resultCountBucket,
} from "./telemetryApi";

describe("telemetry API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("sends semantic events only to the token-protected local bridge", async () => {
    window.history.replaceState({}, "", "/?token=local-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, code: "telemetry.queued", queued: true }),
    } as Response);
    const event = { eventCode: "dashboard.opened" as const, occurredAt: "2026-07-15T00:00:00Z" };

    const result = await emitTelemetryEvent(event);
    await deleteTelemetryData();
    await checkConnectionAndSendNow();

    expect(result.queued).toBe(true);
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      "/api/telemetry/events?token=local-token",
      "/api/telemetry/delete?token=local-token",
      "/api/telemetry/check-send?token=local-token",
    ]);
    expect(fetchMock.mock.calls.every(([url]) => !/^https?:/i.test(String(url)))).toBe(true);
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(expect.objectContaining({
      method: "POST",
      body: JSON.stringify(event),
    }));
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(expect.objectContaining({ method: "POST", body: "{}" }));
    expect(fetchMock.mock.calls[2]?.[1]).toEqual(expect.objectContaining({ method: "POST", body: "{}" }));
  });

  it("fails quietly when the local bridge is unavailable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));

    await expect(emitTelemetryEvent({
      eventCode: "dashboard.opened",
      occurredAt: "2026-07-15T00:00:00Z",
    })).resolves.toEqual({ ok: false, error: "local_telemetry_unavailable" });
    await expect(deleteTelemetryData()).resolves.toEqual({ ok: false, error: "local_telemetry_unavailable" });
    await expect(checkConnectionAndSendNow()).resolves.toEqual({ ok: false, error: "local_telemetry_unavailable" });
  });

  it("maps raw measurements into bounded buckets", () => {
    expect([durationBucket(0), durationBucket(100), durationBucket(500), durationBucket(2000)]).toEqual([
      "under_100_ms", "100_500_ms", "500_2000_ms", "over_2000_ms",
    ]);
    expect([resultCountBucket(0), resultCountBucket(1), resultCountBucket(11), resultCountBucket(101), resultCountBucket(1001)]).toEqual([
      "0", "1_10", "11_100", "101_1000", "over_1000",
    ]);
  });
});
