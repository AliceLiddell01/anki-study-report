import { describe, expect, it } from "vitest";
import { privacyTelemetryStatusCopy } from "./privacyTelemetryStatusCopy";

function keys(value: unknown, prefix = ""): string[] {
  if (!value || typeof value !== "object") return [prefix];
  return Object.entries(value).flatMap(([key, child]) => keys(child, prefix ? `${prefix}.${key}` : key));
}

function values(value: unknown): string[] {
  if (!value || typeof value !== "object") return [String(value)];
  return Object.values(value).flatMap(values);
}

describe("privacy telemetry status copy", () => {
  it("keeps RU and EN key parity with non-empty bundled text", () => {
    expect(keys(privacyTelemetryStatusCopy.ru)).toEqual(keys(privacyTelemetryStatusCopy.en));
    expect([...values(privacyTelemetryStatusCopy.ru), ...values(privacyTelemetryStatusCopy.en)]
      .every((value) => value.trim().length > 0)).toBe(true);
  });
});
