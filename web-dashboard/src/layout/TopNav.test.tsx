// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { RoutePath } from "../app/router";
import TopNav from "./TopNav";

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function renderNav(activeRoute: RoutePath = "/home") {
  act(() => root.render(<TopNav activeRoute={activeRoute} />));
}

function profileTrigger() {
  return container.querySelector<HTMLButtonElement>('button[aria-label="Открыть меню профиля"]')!;
}

function openProfileMenu() {
  act(() => profileTrigger().click());
  return container.querySelector<HTMLElement>('[role="menu"]')!;
}

describe("TopNav", () => {
  it("shows only the agreed primary navigation in the product order", () => {
    renderNav("/calendar");

    const nav = container.querySelector<HTMLElement>('nav[aria-label="Основная навигация"]')!;
    expect(Array.from(nav.querySelectorAll("a"), (link) => link.textContent)).toEqual([
      "Сегодня",
      "Активность",
      "Колоды",
      "Карточки",
    ]);
    expect(nav.textContent).not.toMatch(/Профиль|Инструменты|Источники данных|Логи|Настройки|Сервер|Stats|FSRS|Browse/);
    expect(nav.querySelector('[aria-current="page"]')?.textContent).toBe("Активность");
  });

  it("opens an accessible profile dropdown with current account and utility routes", () => {
    renderNav();
    const trigger = profileTrigger();

    expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    const menu = openProfileMenu();
    const items = Array.from(menu.querySelectorAll<HTMLAnchorElement>('[role="menuitem"]'));

    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(items.map((item) => [item.textContent?.trim(), item.getAttribute("href")])).toEqual([
      ["Профиль", "#/profile"],
      ["Настройки", "#/settings"],
      ["Инструменты", "#/actions"],
      ["Поддержать проект", "https://boosty.to/ankistudyreport"],
    ]);
    expect(document.activeElement).toBe(items[0]);
  });

  it("exposes Boosty as a no-referrer external utility without changing the SPA hash", () => {
    window.location.hash = "#/home";
    renderNav();
    const menu = openProfileMenu();
    const utilityGroup = menu.querySelector<HTMLElement>('[role="group"][aria-label="Утилиты"]')!;
    const utilityItems = Array.from(utilityGroup.querySelectorAll<HTMLAnchorElement>('[role="menuitem"]'));
    const support = utilityItems[1];

    expect(utilityItems.map((item) => item.textContent?.trim())).toEqual(["Инструменты", "Поддержать проект"]);
    expect(support.getAttribute("href")).toBe("https://boosty.to/ankistudyreport");
    expect(support.getAttribute("target")).toBe("_blank");
    expect(support.getAttribute("rel")?.split(/\s+/)).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
    expect(support.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(support.hasAttribute("aria-current")).toBe(false);

    act(() => support.click());
    expect(window.location.hash).toBe("#/home");
    expect(container.querySelector('[role="menu"]')).toBeNull();
  });

  it("supports arrow keys and returns focus to the trigger after Escape", () => {
    renderNav();
    const trigger = profileTrigger();
    const menu = openProfileMenu();
    const items = menu.querySelectorAll<HTMLElement>('[role="menuitem"]');

    act(() => items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })));
    expect(document.activeElement).toBe(items[1]);

    act(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(container.querySelector('[role="menu"]')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("closes on outside pointer input, menu navigation, and route changes", () => {
    renderNav();
    openProfileMenu();
    act(() => document.body.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true })));
    expect(container.querySelector('[role="menu"]')).toBeNull();

    const menu = openProfileMenu();
    act(() => menu.querySelector<HTMLAnchorElement>('a[href="#/settings"]')!.click());
    expect(container.querySelector('[role="menu"]')).toBeNull();

    openProfileMenu();
    renderNav("/profile");
    expect(container.querySelector('[role="menu"]')).toBeNull();
  });
});
