// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { mockReport } from "../data/mockReport";
import FsrsStatisticsPage, { type FsrsSection } from "./FsrsStatisticsPage";

const sections: FsrsSection[] = ["overview", "memory", "calibration", "steps", "simulator"];
let stylesCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  stylesCss = readFileSync("src/styles.css", "utf8");
});

describe("FSRS shared visual contract", () => {
  it("uses the same Statistics sidebar and header surface on every FSRS route", () => {
    for (const section of sections) {
      const markup = renderToStaticMarkup(
        <FsrsStatisticsPage report={mockReport} loadState="ready" section={section} />,
      );

      expect(markup).toContain('data-testid="statistics-sidebar"');
      expect(markup).toContain('class="statistics-sidebar-icon"');
      expect(markup).toContain('class="statistics-header statistics-page-surface fsrs-hero"');
      expect(markup).toContain(`data-fsrs-section="${section}"`);
    }
  });

  it("keeps the sidebar icon inside the shared card without clipping focus outlines", () => {
    expect(stylesCss).toMatch(/\.statistics-sidebar\s*\{[^}]*box-sizing:\s*border-box/s);
    expect(stylesCss).toMatch(/\.statistics-sidebar-heading\s*\{[^}]*padding:/s);
    expect(stylesCss).toMatch(/\.statistics-sidebar-icon\s*\{[^}]*margin:\s*0;/s);
    expect(stylesCss).not.toMatch(/\.statistics-sidebar\s*\{[^}]*overflow:\s*hidden/s);
  });

  it("keeps both icon badges on one shared optical-alignment contract", () => {
    expect(stylesCss).toMatch(/\.brand-icon-badge,\s*\.statistics-sidebar-icon\s*\{[^}]*line-height:\s*0/s);
    expect(stylesCss).toMatch(/\.brand-icon-badge\s*>\s*svg,\s*\.statistics-sidebar-icon\s*>\s*svg\s*\{[^}]*display:\s*block;[^}]*transform:\s*translateY\(\.5px\)/s);
  });

  it("removes the FSRS-only decorative pseudo-element instead of overriding it later", () => {
    expect(stylesCss).not.toMatch(/\.fsrs-hero::after/);
    expect(stylesCss).not.toMatch(/\.fsrs-hero[^}]*radial-gradient|\.fsrs-hero[^}]*filter:\s*blur/is);
  });
});
