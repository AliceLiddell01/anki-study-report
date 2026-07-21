// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CardsDetailDrawer } from "./CardsDetailDrawer";

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("CardsDetailDrawer", () => {
  it("is a labelled non-modal region without inert background or focus trap", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    document.body.innerHTML = '<div id="dashboard-app-shell"><button id="activator">Card</button><div id="root"></div></div>';
    const activator = document.getElementById("activator") as HTMLButtonElement;
    const close = vi.fn();
    const root = createRoot(document.getElementById("root")!);
    await act(async () => root.render(
      <CardsDetailDrawer open labelledBy="detail-title" regionId="detail-region" closeLabel="Close" contextLabel="Card details" restoreFocusTo={activator} fallbackFocusTo={null} onRequestClose={close}>
        <h2 id="detail-title">Details</h2><button type="button">Inner action</button>
      </CardsDetailDrawer>,
    ));

    const drawer = document.querySelector('[data-testid="cards-detail-drawer"]')!;
    expect(drawer.getAttribute("role")).toBe("region");
    expect(drawer.getAttribute("aria-modal")).toBeNull();
    expect(drawer.textContent).toContain("Card details");
    expect(document.getElementById("dashboard-app-shell")!.hasAttribute("inert")).toBe(false);
    expect(drawer.querySelectorAll("button")).toHaveLength(2);

    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(close).toHaveBeenCalledTimes(1);
    await act(async () => { await Promise.resolve(); });
    expect(document.activeElement).toBe(activator);
    await act(async () => root.unmount());
  });

  it("lets the nested answer modal own Escape first", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    document.body.innerHTML = '<div id="root"></div><div role="dialog" aria-modal="true"></div>';
    const close = vi.fn();
    const root = createRoot(document.getElementById("root")!);
    await act(async () => root.render(
      <CardsDetailDrawer open labelledBy="detail-title" regionId="detail-region" closeLabel="Close" restoreFocusTo={null} fallbackFocusTo={null} onRequestClose={close}>
        <h2 id="detail-title">Details</h2>
      </CardsDetailDrawer>,
    ));
    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(close).not.toHaveBeenCalled();
    await act(async () => root.unmount());
  });
});
