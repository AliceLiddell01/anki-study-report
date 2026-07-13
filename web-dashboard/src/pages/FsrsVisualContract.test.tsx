// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { mockReport } from "../data/mockReport";
import FsrsStatisticsPage, { type FsrsSection } from "./FsrsStatisticsPage";

const sections: FsrsSection[] = ["overview", "memory", "calibration", "steps", "simulator"];
let finalCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: URL, encoding: "utf8"): string;
  };
  finalCss = readFileSync(new URL("../styles.fsrs-final.css", import.meta.url), "utf8");
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
    expect(finalCss).toMatch(/\.statistics-sidebar\s*\{[^}]*box-sizing:\s*border-box/s);
    expect(finalCss).toMatch(/\.statistics-sidebar-heading\s*\{[^}]*padding-inline:/s);
    expect(finalCss).toMatch(/\.statistics-sidebar-icon\s*\{[^}]*margin:\s*0;[^}]*transform:\s*none;/s);
    expect(finalCss).not.toMatch(/\.statistics-sidebar\s*\{[^}]*overflow:\s*hidden/s);
  });

  it("removes the FSRS-only decorative pseudo-element while retaining the shared header surface", () => {
    expect(finalCss).toMatch(/\.fsrs-hero::after\s*\{[^}]*content:\s*none;[^}]*display:\s*none;/s);
    expect(finalCss).toMatch(/\.fsrs-hero\s*\{[^}]*overflow:\s*visible;/s);
    expect(finalCss).not.toMatch(/radial-gradient|border-radius:\s*50%|filter:\s*blur/i);
  });
});
