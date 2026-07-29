import { beforeAll, describe, expect, it } from "vitest";

let inspectionCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  inspectionCss = readFileSync("src/styles/inspectionProfiles.css", "utf8");
});

describe("Inspection Profiles visual contract", () => {
  it("keeps a bounded catalog beside the editor through 1024px", () => {
    expect(inspectionCss).toMatch(/\.inspection-workspace\s*\{[^}]*grid-template-columns:\s*clamp\(288px, 20vw, 320px\) minmax\(0, 1fr\)/s);
    expect(inspectionCss).toMatch(/@media \(max-width: 1024px\)[\s\S]*?\.inspection-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(248px, 270px\) minmax\(0, 1fr\)/s);
    expect(inspectionCss).toMatch(/@media \(max-width: 720px\)[\s\S]*?\.inspection-workspace\s*\{[^}]*grid-template-columns:\s*1fr/s);
    expect(inspectionCss).toMatch(/\.inspection-workspace\s*\{[^}]*gap:\s*0;[^}]*border:\s*1px solid/s);
    expect(inspectionCss).toMatch(/\.inspection-catalog-controls\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) minmax\(5\.8rem, \.5fr\) auto/s);
  });

  it("bounds identity content and keeps selected, focus, hover, active, and dirty semantics separate", () => {
    expect(inspectionCss).toMatch(/\.inspection-editor-identity-inner\s*\{[^}]*width:\s*min\(100%, 82rem\)[^}]*grid-template-columns:\s*minmax\(18rem, 42rem\) minmax\(15rem, 24rem\)/s);
    expect(inspectionCss).toMatch(/\.inspection-note-button:hover\s*\{[^}]*inspection-hover-surface/s);
    expect(inspectionCss).toMatch(/\.inspection-note-button:focus-visible\s*\{[^}]*inspection-focus-ring/s);
    expect(inspectionCss).toMatch(/\.inspection-note-button\.is-selected\s*\{[^}]*inspection-selected-surface/s);
    expect(inspectionCss).toMatch(/\.inspection-mode-switch button\.is-active\s*\{[^}]*border-bottom-color:\s*var\(--accent-primary\)/s);
    expect(inspectionCss).toMatch(/\.inspection-mode-dirty\s*\{[^}]*status-warning/s);
    expect(inspectionCss).toContain("@media (forced-colors: active)");
    expect(inspectionCss).not.toMatch(/\.inspection-note-button:hover,[\s\S]*?status-warning/s);
  });

  it("flattens Basic sections while preserving bordered interactive rows", () => {
    expect(inspectionCss).toMatch(/\.inspection-basic-section\s*\{[^}]*border:\s*0;[^}]*border-bottom:/s);
    expect(inspectionCss).toMatch(/\.inspection-basic-row,[\s\S]*?\.inspection-requirement-row\s*\{[^}]*border:\s*1px solid/s);
    expect(inspectionCss).toMatch(/\.inspection-validation-result\s*\{[^}]*border:\s*0;[^}]*border-left:\s*3px solid/s);
  });

  it("keeps status inline and removes the overlapping sticky toast", () => {
    expect(inspectionCss).toMatch(/\.inspection-operation-status\s*\{[^}]*grid-column:\s*1 \/ -1/s);
    expect(inspectionCss).not.toMatch(/\.inspection-operation-status\s*\{[^}]*position:\s*(fixed|sticky)/s);
  });

  it("uses editor container width for dense internal grids", () => {
    expect(inspectionCss).toMatch(/\.inspection-editor\s*\{[^}]*container:\s*inspection-editor \/ inline-size/s);
    expect(inspectionCss).toMatch(/\.inspection-basic\s*\{[^}]*width:\s*100%[^}]*grid-template-columns:\s*minmax\(24rem, 1\.45fr\) minmax\(17rem, 1fr\)/s);
    expect(inspectionCss).not.toContain("width: min(100%, 78rem)");
    expect(inspectionCss).toMatch(/\.inspection-advanced-grid\s*\{[^}]*grid-template-columns:\s*minmax\(15\.625rem, 1\.15fr\) minmax\(15\.625rem, 1fr\) minmax\(16\.875rem, 1fr\)/s);
    expect(inspectionCss).toContain("@container inspection-editor (max-width: 900px)");
    expect(inspectionCss).toContain("@container inspection-editor (max-width: 620px)");
    expect(inspectionCss).toContain("@container inspection-editor (max-width: 640px)");
  });
});
