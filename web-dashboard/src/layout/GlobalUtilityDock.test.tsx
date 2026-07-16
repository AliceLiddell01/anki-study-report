// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { LANGUAGE_STORAGE_KEY } from "../i18n/language";
import GlobalUtilityDock from "./GlobalUtilityDock";

describe("GlobalUtilityDock language control", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("switches language immediately, persists it, and leaves theme unchanged", async () => {
    const onThemeChange = vi.fn();
    await act(async () => root.render(<GlobalUtilityDock resolvedTheme="dark" onThemeChange={onThemeChange} />));

    const trigger = container.querySelector<HTMLButtonElement>('[data-testid="language-selector"]')!;
    expect(trigger.textContent).toContain("RU");
    act(() => trigger.click());
    const english = container.querySelector<HTMLButtonElement>('[data-language="en"]')!;
    expect(english.getAttribute("aria-checked")).toBe("false");

    await act(async () => english.click());
    expect(i18n.language).toBe("en");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(container.querySelector('[data-testid="language-selector"]')?.textContent).toContain("EN");
    expect(onThemeChange).not.toHaveBeenCalled();
  });

  it("removes the language tooltip while the menu is open and restores it after Escape", async () => {
    await act(async () => root.render(<GlobalUtilityDock resolvedTheme="dark" onThemeChange={() => undefined} />));
    const trigger = container.querySelector<HTMLButtonElement>('[data-testid="language-selector"]')!;
    expect(container.querySelector('[role="tooltip"]#language-selector-tooltip')).not.toBeNull();
    expect(trigger.getAttribute("aria-describedby")).toBe("language-selector-tooltip");

    act(() => trigger.click());
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(container.querySelector('[role="tooltip"]#language-selector-tooltip')).toBeNull();
    expect(trigger.hasAttribute("aria-describedby")).toBe(false);
    expect(container.querySelectorAll('[role="menuitemradio"]')).toHaveLength(2);

    act(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(trigger);
    expect(container.querySelector('[role="tooltip"]#language-selector-tooltip')).not.toBeNull();
  });

  it("keeps Arrow, Home/End and outside-click keyboard behavior", async () => {
    await act(async () => root.render(<GlobalUtilityDock resolvedTheme="light" onThemeChange={() => undefined} />));
    const trigger = container.querySelector<HTMLButtonElement>('[data-testid="language-selector"]')!;
    act(() => trigger.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })));
    const items = [...container.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]')];
    expect(document.activeElement).toBe(items[0]);
    act(() => items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true })));
    expect(document.activeElement).toBe(items[1]);
    act(() => items[1].dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
    expect(document.activeElement).toBe(items[0]);
    act(() => document.body.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true })));
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("keeps the language selection unchanged when toggling theme", async () => {
    await act(async () => i18n.changeLanguage("en"));
    const onThemeChange = vi.fn();
    await act(async () => root.render(<GlobalUtilityDock resolvedTheme="dark" onThemeChange={onThemeChange} />));
    act(() => container.querySelector<HTMLButtonElement>('[data-testid="theme-toggle"]')!.click());
    expect(onThemeChange).toHaveBeenCalledWith("light");
    expect(i18n.language).toBe("en");
  });
});
