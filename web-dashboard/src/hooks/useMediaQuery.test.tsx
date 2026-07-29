// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { useMediaQuery } from "./useMediaQuery";

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

it("subscribes to matchMedia changes and cleans up the listener", async () => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  let matches = false;
  let listener: (() => void) | null = null;
  const addEventListener = vi.fn((_event: string, value: () => void) => { listener = value; });
  const removeEventListener = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn(() => ({
    get matches() { return matches; },
    media: "(min-width: 1200px)",
    onchange: null,
    addEventListener,
    removeEventListener,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })));
  document.body.innerHTML = '<div id="root"></div>';
  const root = createRoot(document.getElementById("root")!);

  await act(async () => root.render(<Harness />));
  expect(document.body.textContent).toContain("drawer");
  matches = true;
  await act(async () => listener?.());
  expect(document.body.textContent).toContain("wide");

  await act(async () => root.unmount());
  expect(removeEventListener).toHaveBeenCalledWith("change", expect.any(Function));
});

function Harness() {
  const wide = useMediaQuery("(min-width: 1200px)");
  return <span>{wide ? "wide" : "drawer"}</span>;
}
