import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getRouteFromHash, navItems, renderRoute } from "./router";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard router", () => {
  it("advertises only supported product destinations", () => {
    expect(navItems.map((item) => item.path)).toEqual([
      "/home",
      "/profile",
      "/decks",
      "/cards",
      "/calendar",
      "/actions",
      "/integrations",
      "/logs",
      "/settings/server",
    ]);
  });

  it("keeps supported routes reachable and sends removed or unknown hashes home", () => {
    expect(getRouteFromHash("#/integrations")).toBe("/integrations");
    expect(getRouteFromHash("#/actions")).toBe("/actions");
    expect(getRouteFromHash("#/stats")).toBe("/home");
    expect(getRouteFromHash("#/fsrs")).toBe("/home");
    expect(getRouteFromHash("#/browse")).toBe("/home");
    expect(getRouteFromHash("#/unknown")).toBe("/home");
  });

  it("keeps integrations diagnostics and real Anki Browser actions available", () => {
    vi.stubGlobal("window", { location: { search: "?token=test-token" } });
    const integrations = renderToStaticMarkup(renderRoute("/integrations", null, "error"));
    const actions = renderToStaticMarkup(renderRoute("/actions", null, "error"));

    expect(integrations).toContain("Интеграции");
    expect(integrations).toContain("Диагностика");
    expect(actions).toContain("Открыть проблемные колоды");
    expect(actions).toContain("Открыть Again за период");
    expect(actions).toContain("Открыть New за период");
  });
});
