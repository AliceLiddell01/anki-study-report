import { beforeAll, describe, expect, it } from "vitest";

let sharedCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  sharedCss = readFileSync("src/styles.css", "utf8");
});

describe("shared workspace motion and shape contract", () => {
  it("defines the bounded motion, radius, and surface scales", () => {
    for (const token of ["--motion-instant", "--motion-fast", "--motion-normal", "--motion-panel", "--ease-exit", "--radius-control", "--radius-item", "--radius-region", "--radius-panel", "--radius-pill", "--surface-primary-region", "--surface-status-result"]) {
      expect(sharedCss).toContain(token);
    }
    expect(sharedCss).not.toMatch(/transition\s*:\s*all\b/);
  });

  it("keeps refresh content visible and makes reduced motion static", () => {
    expect(sharedCss).toMatch(/\.shared-refresh-region\.is-refreshing\s*\{[^}]*opacity:/s);
    expect(sharedCss).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.shared-refresh-icon\.is-pending\s*\{[^}]*animation:\s*none/s);
  });
});
