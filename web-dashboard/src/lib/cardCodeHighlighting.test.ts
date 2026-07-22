// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { highlightJavaBlocks } from "./cardCodeHighlighting";

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("bounded Java card highlighting", () => {
  it("highlights only explicitly marked Java blocks and preserves source text", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const host = document.createElement("div");
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <div class="card">
        <pre><code class="language-java">public class Demo { private int value = 7; }</code></pre>
        <pre><code class="lang-java">record Item(String name) {}</code></pre>
        <pre class="language-java"><code>interface Worker { void run(); }</code></pre>
        <pre><code class="language-python">print("plain")</code></pre>
        <pre><code>public class Unmarked {}</code></pre>
      </div>
    `;

    const expected = [
      "public class Demo { private int value = 7; }",
      "record Item(String name) {}",
      "interface Worker { void run(); }",
    ];
    const result = highlightJavaBlocks(shadow);
    const highlighted = [...shadow.querySelectorAll<HTMLElement>("[data-asr-code-highlighted='java']")];

    expect(result).toEqual({ highlighted: 3, skippedOversized: 0, skippedLimit: 0, failed: 0 });
    expect(highlighted.map((element) => element.textContent)).toEqual(expected);
    expect(highlighted.every((element) => element.classList.contains("hljs"))).toBe(true);
    expect(highlighted[0]?.querySelector(".hljs-keyword")).toBeTruthy();
    expect(shadow.querySelector(".language-python")?.innerHTML).toBe('print("plain")');
    expect(shadow.querySelector("pre:last-child code")?.innerHTML).toBe("public class Unmarked {}");
    expect(shadow.querySelector("style[data-asr-java-highlighting]")?.textContent).not.toMatch(/background|font-family|text-align/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("leaves oversized and unknown-language blocks plain", () => {
    const host = document.createElement("div");
    const shadow = host.attachShadow({ mode: "open" });
    const oversized = "x".repeat(20_001);
    shadow.innerHTML = `
      <pre><code class="language-java"></code></pre>
      <pre><code class="language-kotlin">class Plain</code></pre>
    `;
    const java = shadow.querySelector<HTMLElement>(".language-java")!;
    java.textContent = oversized;

    const result = highlightJavaBlocks(shadow);

    expect(result.highlighted).toBe(0);
    expect(result.skippedOversized).toBe(1);
    expect(java.textContent).toBe(oversized);
    expect(java.querySelector("span")).toBeNull();
    expect(shadow.querySelector(".language-kotlin")?.innerHTML).toBe("class Plain");
    expect(shadow.querySelector("style[data-asr-java-highlighting]")).toBeNull();
  });

  it("enforces the bounded block limit without autodetection", () => {
    const host = document.createElement("div");
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = Array.from(
      { length: 9 },
      (_, index) => `<pre><code class="language-java">class Demo${index} {}</code></pre>`,
    ).join("");

    const result = highlightJavaBlocks(shadow);

    expect(result.highlighted).toBe(8);
    expect(result.skippedLimit).toBe(1);
    expect(shadow.querySelectorAll("[data-asr-code-highlighted='java']")).toHaveLength(8);
    expect(shadow.querySelectorAll("code")[8]?.querySelector("span")).toBeNull();
  });
});
