// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { RoutePath } from "../app/router";
import SettingsLayout, { settingsSections } from "./SettingsLayout";
import { SettingsRouteHeader } from "./SettingsRouteHeader";

let stylesCss = "";

beforeAll(async () => {
  const nodeFsSpecifier = "node:fs";
  const { readFileSync } = await import(/* @vite-ignore */ nodeFsSpecifier) as {
    readFileSync(path: string, encoding: "utf8"): string;
  };
  stylesCss = readFileSync("src/styles.css", "utf8");
});

describe("SettingsLayout responsive navigation", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("ru");
    window.location.hash = "#/settings/inspection-profiles";
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => window.setTimeout(() => callback(0), 0));
    vi.stubGlobal("cancelAnimationFrame", (handle: number) => window.clearTimeout(handle));
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  it("uses one canonical route model and exposes every Settings route with active semantics", async () => {
    await render("/settings/inspection-profiles");

    const expectedPaths = settingsSections.flatMap((section) => section.items.map((item) => item.path));
    const links = [...container.querySelectorAll<HTMLAnchorElement>("[data-settings-nav-link]")];
    expect(links.map((link) => link.dataset.settingsNavLink)).toEqual(expectedPaths);
    expect(links).toHaveLength(8);
    expect(container.querySelector('[data-settings-nav-link="/settings/inspection-profiles"]')?.getAttribute("aria-current")).toBe("page");
    expect(container.querySelectorAll('[data-settings-nav-link][aria-current="page"]')).toHaveLength(1);
    expect(container.querySelector('nav[aria-label="Настройки"]')).not.toBeNull();
  });

  it("renders one page H1 in semantic header-navigation-content order", async () => {
    await render("/settings/inspection-profiles");

    const shell = container.querySelector<HTMLElement>('[data-testid="settings-layout-shell"]')!;
    const header = container.querySelector<HTMLElement>('[data-testid="settings-route-header-slot"]')!;
    const navigation = container.querySelector<HTMLElement>('[data-testid="settings-navigation-shell"]')!;
    const content = container.querySelector<HTMLElement>('[data-testid="settings-route-content"]')!;
    const order = Node.DOCUMENT_POSITION_FOLLOWING;

    expect(shell.children[0]).toBe(header);
    expect(header.compareDocumentPosition(navigation) & order).toBeTruthy();
    expect(navigation.compareDocumentPosition(content) & order).toBeTruthy();
    expect(header.querySelector("h1")?.textContent).toBe("Профили проверки");
    expect(content.querySelector("h1")).toBeNull();
    expect(container.querySelectorAll("h1")).toHaveLength(1);
  });

  it("supports menu keyboard boundaries, Escape focus return, and outside close", async () => {
    await render("/settings/inspection-profiles");
    const trigger = overflowTrigger();
    expect(trigger.hasAttribute("aria-controls")).toBe(false);

    await act(async () => trigger.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })));
    await flush();
    const menu = overflowMenu();
    expect(trigger.getAttribute("aria-controls")).toBe(menu.id);
    const items = [...menu.querySelectorAll<HTMLAnchorElement>('[role="menuitem"]')];
    expect(items.map((item) => item.getAttribute("href"))).toEqual([
      "#/settings/notifications",
      "#/settings/server",
      "#/settings/sources",
      "#/settings/logs",
    ]);
    expect(document.activeElement).toBe(items[0]);

    await act(async () => items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true })));
    expect(document.activeElement).toBe(items[3]);
    await act(async () => items[3].dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
    expect(document.activeElement).toBe(items[0]);

    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    await flush();
    expect(container.querySelector('[data-testid="settings-overflow-menu"]')).toBeNull();
    expect(document.activeElement).toBe(trigger);

    await act(async () => trigger.click());
    await flush();
    await act(async () => document.body.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true })));
    expect(container.querySelector('[data-testid="settings-overflow-menu"]')).toBeNull();
  });

  it("focuses the shared real H1 for every overflow route", async () => {
    const cases: Array<[RoutePath, string]> = [
      ["/settings/notifications", "Уведомления"],
      ["/settings/server", "Сервер"],
      ["/settings/sources", "Источники данных"],
      ["/settings/logs", "Логи"],
    ];

    for (const [route, heading] of cases) {
      await render("/settings/inspection-profiles");
      await act(async () => overflowTrigger().click());
      await flush();
      const link = overflowMenu().querySelector<HTMLAnchorElement>(`a[href="#${route}"]`)!;
      await act(async () => link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, detail: 0 })));
      await render(route, heading);
      await flush();

      const target = container.querySelector<HTMLHeadingElement>('[data-testid="settings-route-header-slot"] h1')!;
      expect(target.dataset.focusKey).toBe("route-target");
      expect(target.getAttribute("tabindex")).toBe("-1");
      expect(document.activeElement).toBe(target);
      expect(document.activeElement).not.toBe(document.body);
    }
  });

  it("waits for a lazy route heading before moving keyboard focus", async () => {
    await render("/settings/inspection-profiles");
    await act(async () => overflowTrigger().click());
    await flush();
    const link = overflowMenu().querySelector<HTMLAnchorElement>('a[href="#/settings/notifications"]')!;
    await act(async () => link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, detail: 0 })));

    await act(async () => {
      root.render(
        <SettingsLayout activeRoute="/settings/notifications">
          <section data-testid="lazy-route-fallback">Loading</section>
        </SettingsLayout>,
      );
    });
    expect(document.activeElement?.getAttribute("data-focus-key")).not.toBe("route-target");

    await render("/settings/notifications", "Уведомления");

    const target = container.querySelector<HTMLHeadingElement>('[data-testid="settings-route-header-slot"] h1')!;
    expect(target.dataset.focusKey).toBe("route-target");
    expect(document.activeElement).toBe(target);
  });

  it("marks an overflow route active and renders English compact labels", async () => {
    await i18n.changeLanguage("en");
    await render("/settings/server", "Server");

    expect(container.textContent).toContain("Settings");
    expect(overflowTrigger().textContent).toContain("More");
    expect(overflowTrigger().dataset.activeRoute).toBe("true");

    await act(async () => overflowTrigger().click());
    await flush();
    expect(overflowMenu().querySelector('a[href="#/settings/server"]')?.getAttribute("aria-current")).toBe("page");
  });

  it("defines header-spanning desktop and header-navigation-content compact grids", () => {
    expect(stylesCss).toContain("main.app-content-safe-inset:has(.settings-layout-shell)");
    expect(stylesCss).toMatch(/grid-template-areas:\s*"header header"\s*"nav content"/);
    expect(stylesCss).toMatch(/@media \(max-width: 1120px\)[\s\S]*grid-template-areas:\s*"header"\s*"nav"\s*"content"/);
    expect(stylesCss).toContain(".settings-route-header-slot");
    expect(stylesCss).toContain('.settings-nav-overflow-trigger[aria-expanded="true"]');
    expect(stylesCss).not.toContain("main.app-content-safe-inset {\n  max-width: none;");
  });

  async function render(route: RoutePath, heading = "Профили проверки") {
    await act(async () => {
      root.render(
        <SettingsLayout activeRoute={route}>
          <>
            <SettingsRouteHeader>
              <header className="settings-page-header"><h1>{heading}</h1><p>Route description</p></header>
            </SettingsRouteHeader>
            <section data-testid="route-body"><h2>Route body</h2></section>
          </>
        </SettingsLayout>,
      );
    });
    await flush();
  }

  function overflowTrigger() {
    return container.querySelector<HTMLButtonElement>('[data-testid="settings-overflow-trigger"]')!;
  }

  function overflowMenu() {
    return container.querySelector<HTMLElement>('[data-testid="settings-overflow-menu"]')!;
  }

  async function flush() {
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    });
  }
});
