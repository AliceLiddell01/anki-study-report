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
  it("keeps the catalog at 280-320px and stacks it at 1024px", () => {
    expect(inspectionCss).toMatch(/\.inspection-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(280px, 320px\) minmax\(0, 1fr\)/s);
    expect(inspectionCss).toMatch(/@media \(max-width: 1024px\)[\s\S]*?\.inspection-workspace\s*\{[^}]*grid-template-columns:\s*1fr/s);
    expect(inspectionCss).toMatch(/\.inspection-search input\s*\{[^}]*grid-column:\s*1 \/ -1/s);
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
    expect(inspectionCss).toContain("@container inspection-editor (max-width: 900px)");
    expect(inspectionCss).toContain("@container inspection-editor (max-width: 640px)");
  });
});
