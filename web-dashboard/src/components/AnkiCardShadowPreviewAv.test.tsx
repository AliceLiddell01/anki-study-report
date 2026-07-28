// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AnkiCardShadowPreview,
  buildShadowPreviewDocument,
  enhanceReplayControls,
} from "./AnkiCardShadowPreview";

function replayMarkup(name = "影.mp3"): string {
  const encoded = encodeURIComponent(name);
  return (
    '<span class="asr-card-replay">' +
    `<button class="asr-card-replay-button" type="button" aria-label="Play audio ${name}" data-audio-name="${name}">` +
    '<span class="asr-card-replay-icon" aria-hidden="true">▶</span>' +
    "</button>" +
    `<audio class="asr-card-audio" preload="none" src="/api/media?name=${encoded}"></audio>` +
    "</span>"
  );
}

function mountFragment(html: string): HTMLDivElement {
  const root = document.createElement("div");
  root.innerHTML = html;
  return root;
}

afterEach(() => {
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe("AnkiCardShadowPreview AV fidelity", () => {
  it("adds Anki-compatible replay hooks and a safe SVG after sanitization", () => {
    const root = mountFragment(replayMarkup());

    enhanceReplayControls(root);

    const wrapper = root.querySelector(".asr-card-replay");
    const button = root.querySelector<HTMLButtonElement>("button.asr-card-replay-button");
    const audio = root.querySelector<HTMLAudioElement>("audio.asr-card-audio");
    expect(wrapper).not.toBeNull();
    expect(button?.classList.contains("replay-button")).toBe(true);
    expect(button?.dataset.asrReplayEnhanced).toBe("true");
    expect(button?.getAttribute("aria-label")).toBe("Play audio");
    expect(button?.getAttribute("aria-label")).not.toContain("影.mp3");
    expect(button?.querySelectorAll("svg")).toHaveLength(1);
    expect(button?.querySelectorAll("svg circle")).toHaveLength(1);
    expect(button?.querySelectorAll("svg path")).toHaveLength(1);
    expect(root.querySelector(".asr-card-replay-icon")).toBeNull();
    expect(audio?.getAttribute("src")).toBe("/api/media?name=%E5%BD%B1.mp3");
  });

  it("is idempotent and never duplicates replay controls", () => {
    const root = mountFragment(replayMarkup());

    enhanceReplayControls(root);
    enhanceReplayControls(root);

    expect(root.querySelectorAll("button.asr-card-replay-button")).toHaveLength(1);
    expect(root.querySelectorAll("audio.asr-card-audio")).toHaveLength(1);
    expect(root.querySelectorAll("svg")).toHaveLength(1);
  });

  it("does not synthesize audio metadata when no safe audio element exists", () => {
    const root = mountFragment('<span class="asr-card-replay"></span>');

    enhanceReplayControls(root);

    expect(root.querySelector("button")).toBeNull();
    expect(root.querySelector("audio")).toBeNull();
  });

  it("keeps replay and image presentation fallbacks before template CSS", () => {
    const templateCss = [
      ".replay-button { margin: 11px; }",
      ".replay-button svg { width: 52px; height: 52px; }",
      ".replay-button svg circle { fill: rgb(1, 2, 3); }",
      ".replay-button svg path { fill: rgb(4, 5, 6); }",
      "img { width: 160px; height: 120px; vertical-align: baseline; object-fit: fill; }",
    ].join("\n");
    const documentModel = buildShadowPreviewDocument({
      html: `${replayMarkup()}<img src="/api/media?name=%E5%BD%B1.gif" alt="">`,
      css: templateCss,
      mode: "preview",
    });

    const templateIndex = documentModel.styleText.indexOf(templateCss);
    const replayFallbackIndex = documentModel.styleText.indexOf(":where(.replay-button, .asr-card-replay-button)");
    const safetyIndex = documentModel.styleText.indexOf("Raw media stays inert");
    expect(replayFallbackIndex).toBeGreaterThanOrEqual(0);
    expect(replayFallbackIndex).toBeLessThan(templateIndex);
    expect(templateIndex).toBeLessThan(safetyIndex);
    expect(documentModel.styleText).toContain(":where(.card) :where(img)");
    expect(documentModel.styleText).not.toContain(".card img {\n  max-width: 100%;\n  height: auto;");
    expect(documentModel.styleText).not.toContain("object-fit: contain");
    expect(documentModel.styleText).not.toContain("vertical-align: middle;\n  object-fit");
  });

  it("uses the same AV payload for light/dark and preview/expanded contours", () => {
    const html = `${replayMarkup()}<img src="/api/media?name=%E5%BD%B1.gif" alt="">（する）<br>（影が伸びる。）`;
    const css = ".replay-button svg circle { fill: #fff; } img { width: 160px; height: 120px; }";
    const light = buildShadowPreviewDocument({ html, css, mode: "preview", nightMode: false });
    const dark = buildShadowPreviewDocument({ html, css, mode: "preview", nightMode: true });
    const expanded = buildShadowPreviewDocument({ html, css, mode: "expanded", nightMode: true, side: "back" });

    expect(light.html).toBe(html);
    expect(dark.html).toBe(html);
    expect(expanded.html).toBe(html);
    expect(light.styleText).toBe(dark.styleText);
    expect(dark.styleText).toBe(expanded.styleText);
    expect(dark.cardClassName).toContain("nightMode");
    expect(expanded.shellClassName).toContain("asr-shadow-card-shell--expanded");
  });

  it("resets currentTime and invokes play once from the safe ShadowRoot handler", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(() => Promise.resolve());
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<AnkiCardShadowPreview html={replayMarkup()} mode="preview" side="front" />);
    });

    const host = container.querySelector<HTMLElement>('[data-testid="anki-card-shadow-preview"]')!;
    const button = host.shadowRoot?.querySelector<HTMLButtonElement>("button.asr-card-replay-button");
    const audio = host.shadowRoot?.querySelector<HTMLAudioElement>("audio.asr-card-audio");
    expect(button?.classList.contains("replay-button")).toBe(true);
    expect(audio).not.toBeNull();
    if (!button || !audio) {
      throw new Error("Expected enhanced replay control");
    }
    audio.currentTime = 7;

    await act(async () => {
      button.click();
      await Promise.resolve();
    });

    expect(audio.currentTime).toBe(0);
    expect(play).toHaveBeenCalledTimes(1);

    await act(async () => root.unmount());
  });

  it("contains a rejected play promise without breaking the preview", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(() => Promise.reject(new Error("blocked")));
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<AnkiCardShadowPreview html={replayMarkup()} mode="expanded" side="back" nightMode />);
    });

    const host = container.querySelector<HTMLElement>('[data-testid="anki-card-shadow-preview"]')!;
    const button = host.shadowRoot?.querySelector<HTMLButtonElement>("button.asr-card-replay-button");
    expect(button).not.toBeNull();

    await act(async () => {
      button?.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(play).toHaveBeenCalledTimes(1);
    expect(host.shadowRoot?.querySelector(".asr-shadow-card-shell")).not.toBeNull();

    await act(async () => root.unmount());
  });
});
