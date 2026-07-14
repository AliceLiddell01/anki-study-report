import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { compatibilityRedirectForHash, getRouteFromHash, primaryNavItems, renderRoute } from "./router";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard router", () => {
  it("advertises only supported product destinations", () => {
    expect(primaryNavItems).toEqual([
      { path: "/home", labelKey: "primary.today" },
      { path: "/calendar", labelKey: "primary.activity" },
      { path: "/stats", labelKey: "primary.statistics" },
      { path: "/decks", labelKey: "primary.decks" },
      { path: "/cards", labelKey: "primary.cards" },
    ]);
    const primaryPaths: string[] = primaryNavItems.map((item) => item.path);
    for (const hiddenPath of [
      "/profile",
      "/actions",
      "/integrations",
      "/logs",
      "/settings",
      "/settings/data",
      "/settings/server",
      "/settings/sources",
      "/settings/logs",
      "/fsrs",
      "/browse",
    ]) {
      expect(primaryPaths).not.toContain(hiddenPath);
    }
  });

  it("keeps every current route reachable while removed and unknown hashes fall back home", () => {
    expect([
      "/home",
      "/profile",
      "/decks",
      "/cards",
      "/calendar",
      "/stats",
      "/stats/quality",
      "/stats/load",
      "/stats/progress",
      "/stats/decks",
      "/stats/fsrs",
      "/stats/fsrs/memory",
      "/stats/fsrs/calibration",
      "/stats/fsrs/steps",
      "/stats/fsrs/simulator",
      "/actions",
      "/settings",
      "/settings/data",
      "/settings/server",
      "/settings/sources",
      "/settings/logs",
    ].map((path) => getRouteFromHash(`#${path}`))).toEqual([
      "/home",
      "/profile",
      "/decks",
      "/cards",
      "/calendar",
      "/stats",
      "/stats/quality",
      "/stats/load",
      "/stats/progress",
      "/stats/decks",
      "/stats/fsrs",
      "/stats/fsrs/memory",
      "/stats/fsrs/calibration",
      "/stats/fsrs/steps",
      "/stats/fsrs/simulator",
      "/actions",
      "/settings",
      "/settings/data",
      "/settings/server",
      "/settings/sources",
      "/settings/logs",
    ]);
    expect(getRouteFromHash("#/integrations")).toBe("/settings/sources");
    expect(getRouteFromHash("#/logs")).toBe("/settings/logs");
    expect(compatibilityRedirectForHash("#/integrations")).toBe("/settings/sources");
    expect(compatibilityRedirectForHash("#/logs")).toBe("/settings/logs");
    expect(compatibilityRedirectForHash("#/settings/logs")).toBeNull();
    expect(getRouteFromHash("#/stats")).toBe("/stats");
    expect(getRouteFromHash("#/stats/quality")).toBe("/stats/quality");
    expect(getRouteFromHash("#/stats/fsrs/simulator")).toBe("/stats/fsrs/simulator");
    expect(getRouteFromHash("#/stats/fsrs/unknown")).toBe("/home");
    expect(getRouteFromHash("#/fsrs")).toBe("/home");
    expect(getRouteFromHash("#/browse")).toBe("/home");
    expect(getRouteFromHash("#/unknown")).toBe("/home");
    expect(getRouteFromHash("")).toBe("/home");
  });

  it("keeps the settings shell, source diagnostics, and real Anki Browser tools available", () => {
    vi.stubGlobal("window", { location: { search: "?token=test-token" } });
    const integrations = renderToStaticMarkup(renderRoute("/settings/sources", null, "error"));
    const actions = renderToStaticMarkup(renderRoute("/actions", null, "error"));

    expect(integrations).toContain('aria-label="Настройки"');
    expect(integrations).toContain('href="#/settings"');
    expect(integrations).toContain('href="#/settings/data"');
    expect(integrations).toContain('href="#/settings/server"');
    expect(integrations).toContain('href="#/settings/sources"');
    expect(integrations).toContain('href="#/settings/logs"');
    expect(integrations).toContain("Источники данных");
    expect(integrations).toContain("Диагностика");
    expect(actions).toContain("Инструменты");
    expect(actions).toContain("Открыть проблемные колоды");
    expect(actions).toContain("Открыть Again за период");
    expect(actions).toContain("Открыть New за период");
  });
});
