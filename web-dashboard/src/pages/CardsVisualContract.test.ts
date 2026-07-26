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
  it("keeps the exact 1199/1200 Inspector boundary with wide mode as the default composition", () => {
    expect(cardsCss).toContain("@media (max-width: 1199px)");
    expect(cardsCss).toMatch(/\.cards-inbox-workspace\s*\{[^}]*grid-template-columns:\s*var\(--cards-queue-width\) minmax\(0, 1fr\)/s);
    expect(cardsCss).toMatch(/@media \(max-width: 1199px\)[\s\S]*?\.cards-inbox-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/s);
  });

  it("keeps the narrow drawer opaque, non-modal, labelled, and clear of the utility dock", () => {
    expect(cardsCss).toMatch(/\.cards-detail-drawer\s*\{(?=[^}]*width:\s*min\(72vw, 760px\))(?=[^}]*border-left:\s*1px solid)(?=[^}]*background:\s*var\(--surface-2\))[^}]*\}/s);
    expect(cardsCss).toMatch(/body:has\(\.cards-detail-drawer\) \.global-utility-dock\s*\{[^}]*right:\s*calc\(min\(72vw, 760px\) \+ 1rem\)/s);
    expect(cardsCss).toMatch(/\.cards-detail-drawer-close\s*\{[^}]*display:\s*inline-flex/s);
    expect(cardsCss).toMatch(/\.cards-detail-drawer-close\s*\{[^}]*min-width:\s*6\.1rem/s);
    expect(cardsCss).not.toContain(".cards-detail-drawer-backdrop");
  });

  it("keeps answer modal chrome compact and respects reduced motion", () => {
    expect(cardsCss).toMatch(/\.product-modal\.cards-answer-modal\s*\{[^}]*width:\s*min\(980px, 100%\)/s);
    expect(cardsCss).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.cards-detail-drawer\s*\{[^}]*animation:\s*none/s);
  });
});
