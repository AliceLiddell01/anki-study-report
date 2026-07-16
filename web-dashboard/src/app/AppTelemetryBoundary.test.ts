import { describe, expect, it } from "vitest";
import { telemetryPageCode } from "./App";

describe("notification telemetry boundary", () => {
  it("does not map local notification routes to remote page events", () => {
    expect(telemetryPageCode("/notifications")).toBeNull();
    expect(telemetryPageCode("/home")).toBe("home");
  });
});
