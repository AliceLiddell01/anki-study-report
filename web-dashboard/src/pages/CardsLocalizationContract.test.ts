import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

const mainSource = readFileSync("src/main.tsx", "utf8");
const typographyCss = readFileSync("src/styles/cardsTypography.css", "utf8");

describe("Cards localization typography contract", () => {
  it("loads the Cards typography correction after the workspace stylesheet", () => {
    const workspaceImport = mainSource.indexOf('import "./styles/cardsInbox.css";');
    const typographyImport = mainSource.indexOf('import "./styles/cardsTypography.css";');

    expect(workspaceImport).toBeGreaterThanOrEqual(0);
    expect(typographyImport).toBeGreaterThan(workspaceImport);
  });

  it("inherits the locale-aware application font stack for Cards chrome", () => {
    expect(typographyCss).toMatch(
      /\.cards-inbox-page\s*\{[^}]*font-family:\s*inherit\s*;/s,
    );
    expect(typographyCss).not.toMatch(/Yu Gothic|Hiragino|Noto Sans JP|Meiryo/i);
  });
});
