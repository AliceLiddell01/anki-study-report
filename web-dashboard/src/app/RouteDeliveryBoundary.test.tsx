// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { RouteDeliveryBoundary, RouteLoading } from "./RouteDeliveryBoundary";

beforeAll(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

afterEach(() => vi.restoreAllMocks());

describe("lazy route delivery", () => {
  it("shows a branded non-blank Suspense fallback", () => {
    const markup = renderToStaticMarkup(<RouteLoading />);
    expect(markup).toContain('data-testid="route-loading"');
    expect(markup).toContain("Anki Study Report");
    expect(markup).toContain("Открываем раздел");
  });

  it("turns a chunk failure into a visible reload action without logging a URL", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    function BrokenRoute(): never { throw new Error("chunk unavailable"); }

    await act(async () => root.render(<RouteDeliveryBoundary><BrokenRoute /></RouteDeliveryBoundary>));

    expect(container.querySelector('[data-testid="route-load-error"]')).not.toBeNull();
    expect(container.textContent).toContain("Перезагрузить dashboard");
    const diagnostic = consoleError.mock.calls.find((call) => call[0] === "Dashboard route chunk failed to load");
    expect(diagnostic).toBeTruthy();
    expect(JSON.stringify(diagnostic)).not.toContain("token=");
    await act(async () => root.unmount());
    container.remove();
  });
});
