// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnkiCardShadowPreview } from "./AnkiCardShadowPreview";

describe("AnkiCardShadowPreview Java highlighting order", () => {
  let callbacks: FrameRequestCallback[];

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    callbacks = [];
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callbacks.push(callback);
      return callbacks.length;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("highlights sanitized Java code before the first measurement frame", async () => {
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    const source = "public class Demo { private int value = 7; }";

    await act(async () => {
      root.render(
        <AnkiCardShadowPreview
          html={`<pre><code class="language-java">${source}</code></pre>`}
          mode="preview"
          side="front"
        />,
      );
      await Promise.resolve();
    });

    const host = container.querySelector<HTMLElement>("[data-shadow-preview='true']")!;
    const code = host.shadowRoot?.querySelector<HTMLElement>("code.language-java");

    expect(code?.textContent).toBe(source);
    expect(code?.dataset.asrCodeHighlighted).toBe("java");
    expect(code?.querySelector(".hljs-keyword")).toBeTruthy();
    expect(host.dataset.previewMeasured).toBe("false");
    expect(callbacks).toHaveLength(1);

    await act(async () => {
      callbacks.shift()?.(0);
      await Promise.resolve();
    });

    expect(host.dataset.previewMeasured).toBe("true");
    await act(async () => root.unmount());
  });
});
