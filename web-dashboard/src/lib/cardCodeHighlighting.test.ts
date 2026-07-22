// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import { highlightJavaBlocks, highlightJavaElement, tokenizeJavaSource } from "./cardCodeHighlighting";

describe("bounded Java card highlighting", () => {
  it("tokenizes Java without changing source text", () => {
    const source = "public record User(String name) { // immutable\n  return null;\n}";
    const tokens = tokenizeJavaSource(source);
    expect(tokens.map((token) => token.value).join("")).toBe(source);
    expect(tokens.some((token) => token.kind === "keyword" && token.value === "record")).toBe(true);
    expect(tokens.some((token) => token.kind === "comment")).toBe(true);
  });

  it("highlights only explicit Java blocks and preserves textContent", () => {
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<pre><code class="language-java">public class Demo { int n = 42; }</code></pre><pre><code class="language-python">print(42)</code></pre>`;
    const java = root.querySelector<HTMLElement>(".language-java")!;
    const python = root.querySelector<HTMLElement>(".language-python")!;
    const source = java.textContent;

    expect(highlightJavaBlocks(root)).toBe(1);
    expect(java.textContent).toBe(source);
    expect(java.dataset.asrCodeHighlighted).toBe("java");
    expect(java.querySelector(".asr-code-token--keyword")?.textContent).toBe("public");
    expect(python.dataset.asrCodeHighlighted).toBeUndefined();
    expect(root.querySelector("style[data-asr-java-highlighting]")).toBeTruthy();
  });

  it("supports lang-java and leaves oversized source plain", () => {
    const alias = document.createElement("code");
    alias.className = "lang-java";
    alias.textContent = "final int value = 1;";
    expect(highlightJavaElement(alias)).toBe(true);
    expect(alias.textContent).toBe("final int value = 1;");

    const oversized = document.createElement("code");
    oversized.className = "language-java";
    oversized.textContent = "x".repeat(20_001);
    expect(highlightJavaElement(oversized)).toBe(false);
    expect(oversized.childElementCount).toBe(0);
  });
});
