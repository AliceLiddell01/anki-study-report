import { beforeAll, describe, expect, it } from "vitest";

describe("Profile visual contract", () => {
  let source = "";
  let css = "";

  beforeAll(async () => {
    const nodeFsSpecifier = "node:fs";
    const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
      readFileSync(path: string, encoding: "utf8"): string;
    };
    source = readFileSync("src/pages/ProfilePage.tsx", "utf8");
    css = readFileSync("src/styles/profile.css", "utf8");
  });

  it("keeps the production section order explicit", () => {
    const composition = source.slice(source.indexOf("return ("), source.indexOf("function ProfileHero"));
    const order = ["<ProfileHero", "<MainDecks", "<ProfileStatus", "<ActivityHeatmap", "<RecentHistory"]
      .map((marker) => composition.indexOf(marker));
    expect(order.every((position) => position >= 0)).toBe(true);
    expect(order).toEqual([...order].sort((left, right) => left - right));
  });

  it("uses only existing routes and the current profile preference contract", () => {
    expect(source).toContain('href="#/decks"');
    expect(source).toContain('href="#/calendar"');
    expect(source).toContain("customStudyStartedOn");
    expect(source).toContain("deckOverviewSort");
    expect(source).not.toMatch(/href="#\/(skills|achievements|levels|rewards)"/);
    expect(source).toContain("createPortal(");
    expect(source).toContain("document.body");
    expect(source).not.toMatch(/localStorage|collection\./);
  });

  it("defines bounded responsive behavior and fail-open reduced motion", () => {
    expect(css).toContain("@media (max-width: 1180px)");
    expect(css).toContain("@media (max-width: 760px)");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toMatch(/\.profile-page\s*\{[\s\S]*?min-width:\s*0/);
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*?transition:\s*none/);
    expect(css).not.toMatch(/\.profile-page\s*\{[^}]*transform:/);
    expect(css).not.toMatch(/\.profile-page\s*\{[^}]*animation:/);
    expect(css).not.toContain("opacity: 0");
    expect(css).not.toMatch(/animation:\s*[^;]*(infinite|forwards)/);
    expect(css).toMatch(/\.profile-button:focus-visible[\s\S]*?outline:\s*3px/);
  });

  it("keeps visible cards factual and free of deferred gamification systems", () => {
    expect(source).not.toMatch(/\b(XP|achievement|mastery|level|reward|skill tree)\b/i);
    expect(source).toContain("profile.decks.overview");
    expect(source).toContain("profile.studyHistory");
    expect(source).toContain("profile.activity.recentActiveDays");
    expect(source).not.toMatch(/LearningAreas|learningAreas|moreLearningAreas/);
  });

  it("enforces readable Profile typography and semantic theme surfaces", () => {
    expect(css).not.toMatch(/font-size:\s*\.6\drem/);
    expect(css).not.toMatch(/font-size:\s*\.7(?:0)?rem/);
    expect(css).toMatch(/\.profile-deck-card dt\s*\{[\s\S]*?font-size:\s*\.75rem/);
    expect(css).toMatch(/\.profile-status-card p,[\s\S]*?\.profile-status-card span\s*\{[\s\S]*?font-size:\s*\.72rem/);
    expect(css).toMatch(/\.profile-heatmap-legend\s*\{[\s\S]*?font-size:\s*\.72rem/);
    expect(css).toContain("var(--surface-2)");
    expect(css).toContain("var(--text-primary)");
    expect(css).not.toMatch(/url\(/);
  });

  it("defines deterministic hierarchy and short-range Activity presentation", () => {
    expect(source).toContain('data-canonical-name={name}');
    expect(source).toContain('aria-label={name}');
    expect(source).toContain("COMPACT_ACTIVITY_DAYS_LIMIT");
    expect(source).toContain('data-activity-presentation={presentation}');
    expect(css).toContain(".profile-status-primary");
    expect(css).toContain(".profile-status-secondary");
    expect(css).toContain(".profile-activity--compact .profile-activity__content");
    expect(css).toContain(".profile-activity--compact .profile-heatmap");
  });
});
