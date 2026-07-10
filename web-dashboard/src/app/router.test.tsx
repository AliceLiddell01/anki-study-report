import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getRouteFromHash, primaryNavItems, renderRoute } from "./router";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard router", () => {
  it("advertises only supported product destinations", () => {
    expect(primaryNavItems).toEqual([
      { path: "/home", label: "Сегодня" },
      { path: "/calendar", label: "Календарь" },
      { path: "/decks", label: "Колоды" },
      { path: "/cards", label: "Карточки" },
    ]);
    const primaryPaths: string[] = primaryNavItems.map((item) => item.path);
    for (const hiddenPath of [
      "/profile",
      "/actions",
      "/integrations",
      "/logs",
      "/settings",
      "/settings/server",
      "/stats",
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
      "/actions",
      "/settings",
      "/settings/server",
      "/integrations",
      "/logs",
    ].map((path) => getRouteFromHash(`#${path}`))).toEqual([
      "/home",
      "/profile",
      "/decks",
      "/cards",
      "/calendar",
      "/actions",
      "/settings",
      "/settings/server",
      "/integrations",
      "/logs",
    ]);
    expect(getRouteFromHash("#/stats")).toBe("/home");
    expect(getRouteFromHash("#/fsrs")).toBe("/home");
    expect(getRouteFromHash("#/browse")).toBe("/home");
    expect(getRouteFromHash("#/unknown")).toBe("/home");
    expect(getRouteFromHash("")).toBe("/home");
  });

  it("keeps the settings shell, source diagnostics, and real Anki Browser tools available", () => {
    vi.stubGlobal("window", { location: { search: "?token=test-token" } });
    const integrations = renderToStaticMarkup(renderRoute("/integrations", null, "error"));
    const actions = renderToStaticMarkup(renderRoute("/actions", null, "error"));

    expect(integrations).toContain("Разделы настроек");
    expect(integrations).toContain('href="#/settings"');
    expect(integrations).toContain('href="#/settings/server"');
    expect(integrations).toContain('href="#/integrations"');
    expect(integrations).toContain('href="#/logs"');
    expect(integrations).toContain("Источники данных");
    expect(integrations).toContain("Диагностика");
    expect(actions).toContain("Инструменты");
    expect(actions).toContain("Открыть проблемные колоды");
    expect(actions).toContain("Открыть Again за период");
    expect(actions).toContain("Открыть New за период");
  });
});
