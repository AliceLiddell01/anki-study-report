// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RoutePath } from "../app/router";
import { THEME_STORAGE_KEY } from "../lib/theme";
import AppLayout from "./AppLayout";

const routes: RoutePath[] = [
  "/home", "/calendar", "/decks", "/cards", "/profile", "/actions",
  "/settings", "/settings/data", "/settings/server", "/settings/sources", "/settings/logs",
];

describe("AppLayout global utilities", () => {
  let container: HTMLDivElement;
  let root: Root;
  let systemDark = false;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    systemDark = false;
    vi.stubGlobal("matchMedia", vi.fn(() => ({
      get matches() { return systemDark; },
      media: "(prefers-color-scheme: dark)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })));
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it.each(routes)("renders one persistent utility dock on %s", async (route) => {
    await render(route);
    expect(container.querySelectorAll('[data-testid="global-utility-dock"]')).toHaveLength(1);
    expect(container.querySelector('[data-testid="theme-toggle"]')).not.toBeNull();
    const dock = container.querySelector('[data-testid="global-utility-dock"]')!;
    expect(dock.querySelectorAll('[data-testid="language-selector"]')).toHaveLength(1);
    expect(dock.querySelector('[data-testid="language-selector"]')?.textContent).toContain("RU");
  });

  it("toggles light and dark, stores the existing explicit values, and updates action labels", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    await render("/home");
    const toggle = themeToggle();
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(toggle.getAttribute("aria-label")).toBe("Включить тёмную тему");
    expect(container.querySelector('#theme-toggle-tooltip')?.textContent).toBe("Включить тёмную тему");

    await act(async () => toggle.click());
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(themeToggle().getAttribute("aria-label")).toBe("Включить светлую тему");

    await act(async () => themeToggle().click());
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("keeps system-mode compatibility and preserves the theme and single dock across navigation", async () => {
    systemDark = true;
    window.localStorage.setItem(THEME_STORAGE_KEY, "system");
    await render("/home");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("system");

    await act(async () => themeToggle().click());
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    await render("/settings/server");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(container.querySelectorAll('[data-testid="theme-toggle"]')).toHaveLength(1);
  });

  async function render(route: RoutePath) {
    await act(async () => root.render(<AppLayout activeRoute={route}><p>{route}</p></AppLayout>));
  }

  function themeToggle() {
    return container.querySelector<HTMLButtonElement>('[data-testid="theme-toggle"]')!;
  }
});
