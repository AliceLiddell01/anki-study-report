import { beforeAll, describe, expect, it } from "vitest";

let cardsCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  cardsCss = readFileSync("src/styles/cardsInbox.css", "utf8");
});

describe("Cards responsive visual contract", () => {
  it("uses the exact 1199/1200 Inspector boundary", () => {
    expect(cardsCss).toContain("@media (min-width: 1200px)");
    expect(cardsCss).toContain("@media (max-width: 1199px)");
    expect(cardsCss).toMatch(/@media \(min-width: 1200px\)[\s\S]*?\.cards-inbox-workspace\s*\{[\s\S]*?grid-template-columns:/);
  });

  it("keeps the narrow drawer opaque, non-modal, and clear of the utility dock", () => {
    expect(cardsCss).toMatch(/\.cards-detail-drawer\s*\{[^}]*width:\s*min\(640px, calc\(100vw - 32px\)\)[^}]*border-left:\s*2px solid[^}]*background:\s*var\(--surface-2\)/s);
    expect(cardsCss).toMatch(/body:has\(\.cards-detail-drawer\) \.global-utility-dock\s*\{[^}]*right:\s*calc\(min\(640px, 100vw - 32px\) \+ 1rem\)/s);
    expect(cardsCss).not.toContain(".cards-detail-drawer-backdrop");
  });

  it("keeps answer modal chrome compact and respects reduced motion", () => {
    expect(cardsCss).toMatch(/\.product-modal\.cards-answer-modal\s*\{[^}]*width:\s*min\(900px, 100%\)/s);
    expect(cardsCss).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.cards-detail-drawer\s*\{[^}]*animation:\s*none/s);
  });
});
