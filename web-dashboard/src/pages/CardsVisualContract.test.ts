import { beforeAll, describe, expect, it } from "vitest";

let cardsCss = "";
let globalCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  cardsCss = readFileSync("src/styles/cardsInbox.css", "utf8");
  globalCss = readFileSync("src/styles.css", "utf8");

  it("keeps preview frame ownership outside the native card while filling the compact host", () => {
    expect(cardsCss).toMatch(/\.cards-detail-preview-frame\s*\{[^}]*place-items:\s*stretch[^}]*overflow:\s*hidden[^}]*background:\s*transparent/s);
    expect(globalCss).toMatch(/\.anki-card-shadow-preview--preview\s*\{[^}]*height:\s*100%[^}]*border-radius:\s*0\.82rem[^}]*box-shadow:/s);
    expect(cardsCss).not.toMatch(/\.cards-detail-preview-frame\s*\{[^}]*background:\s*#(?:2f2f31|111827)/is);
  });

  it("separates selected, busy, and focus-visible queue states", () => {
    expect(cardsCss).toMatch(/\.cards-inbox-item\.is-active\s*\{[^}]*background:\s*color-mix\(in srgb, var\(--accent-primary\) 4%, var\(--surface-2\)\)[^}]*box-shadow:\s*inset 3px 0 var\(--accent-primary\)/s);
    expect(cardsCss).toMatch(/\.cards-inbox-item\.is-active\.is-busy\s*\{[^}]*background:\s*color-mix\(in srgb, var\(--accent-primary\) 2\.5%, var\(--surface-2\)\)[^}]*cursor:\s*progress/s);
    expect(globalCss).toMatch(/\.workspace-interactive:focus-visible\s*\{[^}]*outline:\s*3px solid/s);
    expect(cardsCss).not.toMatch(/\.cards-inbox-item\.is-active\s*\{[^}]*opacity:\s*\.[0-9]+/s);
  });

  it("keeps queue controls aligned and makes available primary actions visually distinct from disabled ones", () => {
    expect(cardsCss).toMatch(/\.cards-inbox-queue-controls input\s*\{[^}]*height:\s*36px/s);
    expect(cardsCss).toMatch(/\.cards-inbox-filter-toggle\s*\{[^}]*height:\s*36px/s);
    expect(cardsCss).toMatch(/\.cards-inbox-active-filters > span\s*\{[^}]*border-radius:\s*999px[^}]*min-height:\s*24px/s);
    expect(cardsCss).toMatch(/\.cards-detail-actions > \.primary-button\s*\{[^}]*background:\s*var\(--accent-primary\)[^}]*color:\s*#ffffff/s);
    expect(cardsCss).toMatch(/\.cards-detail-actions > \.primary-button:disabled\s*\{[^}]*background:[^}]*box-shadow:\s*none[^}]*opacity:\s*\.68/s);
  });

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

  it("keeps preview frame ownership outside the native card while filling the compact host", () => {
    expect(cardsCss).toMatch(/\.cards-detail-preview-frame\s*\{[^}]*place-items:\s*stretch[^}]*overflow:\s*hidden[^}]*background:\s*transparent/s);
    expect(globalCss).toMatch(/\.anki-card-shadow-preview--preview\s*\{[^}]*height:\s*100%[^}]*border-radius:\s*0\.82rem[^}]*box-shadow:/s);
    expect(cardsCss).not.toMatch(/\.cards-detail-preview-frame\s*\{[^}]*background:\s*#(?:2f2f31|111827)/is);
  });

  it("separates selected, busy, and focus-visible queue states", () => {
    expect(cardsCss).toMatch(/\.cards-inbox-item\.is-active\s*\{[^}]*background:\s*color-mix\(in srgb, var\(--accent-primary\) 4%, var\(--surface-2\)\)[^}]*box-shadow:\s*inset 3px 0 var\(--accent-primary\)/s);
    expect(cardsCss).toMatch(/\.cards-inbox-item\.is-active\.is-busy\s*\{[^}]*background:\s*color-mix\(in srgb, var\(--accent-primary\) 2\.5%, var\(--surface-2\)\)[^}]*cursor:\s*progress/s);
    expect(globalCss).toMatch(/\.workspace-interactive:focus-visible\s*\{[^}]*outline:\s*3px solid/s);
    expect(cardsCss).not.toMatch(/\.cards-inbox-item\.is-active\s*\{[^}]*opacity:\s*\.[0-9]+/s);
  });

  it("keeps queue controls aligned and makes available primary actions visually distinct from disabled ones", () => {
    expect(cardsCss).toMatch(/\.cards-inbox-queue-controls input\s*\{[^}]*height:\s*36px/s);
    expect(cardsCss).toMatch(/\.cards-inbox-filter-toggle\s*\{[^}]*height:\s*36px/s);
    expect(cardsCss).toMatch(/\.cards-inbox-active-filters > span\s*\{[^}]*border-radius:\s*999px[^}]*min-height:\s*24px/s);
    expect(cardsCss).toMatch(/\.cards-detail-actions > \.primary-button\s*\{[^}]*background:\s*var\(--accent-primary\)[^}]*color:\s*#ffffff/s);
    expect(cardsCss).toMatch(/\.cards-detail-actions > \.primary-button:disabled\s*\{[^}]*background:[^}]*box-shadow:\s*none[^}]*opacity:\s*\.68/s);
  });

});
