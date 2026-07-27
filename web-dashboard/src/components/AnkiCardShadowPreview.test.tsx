// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  AnkiCardShadowPreview,
  buildShadowPreviewDocument,
  calculateAdaptivePreviewLayout,
  enhanceReplayControls,
} from "./AnkiCardShadowPreview";
import { cssWithMediaToken } from "./cards/CardsDetail";

function replayCard(): HTMLDivElement {
  const card = document.createElement("div");
  card.innerHTML = `
    <span class="asr-card-replay">
      <button
        type="button"
        class="asr-card-replay-button"
        aria-label="stale label"
      ></button>
      <audio
        class="asr-card-audio"
        src="/api/media?name=%E5%BD%B1.mp3&token=redacted"
      ></audio>
    </span>
  `;
  return card;
}

describe("AnkiCardShadowPreview layout", () => {
  it("never lets scaled content exceed a narrow host width", () => {
    const layout = calculateAdaptivePreviewLayout({ mode: "preview", availableWidth: 180, contentWidth: 900, contentHeight: 2400 });
    expect(layout.contentWidth * layout.scale).toBeLessThanOrEqual(layout.targetWidth - 20 + 0.001);
    expect(layout.scale).toBeCloseTo(160 / 900, 6);
    expect(layout.overflow).toBe(true);
  });



  it("keeps native card scale at 1 when the compact host can fit the accepted 660px canvas", () => {
    const layout = calculateAdaptivePreviewLayout({
      mode: "preview",
      availableWidth: 720,
      availableHeight: 600,
      contentWidth: 660,
      contentHeight: 420,
    });
    expect(layout.scale).toBe(1);
    expect(layout.contentWidth).toBe(660);
    expect(layout.hostHeight).toBe(600);
  });

  it("fills a short compact card canvas to the available preview height without scaling glyphs", () => {
    const layout = calculateAdaptivePreviewLayout({
      mode: "preview",
      availableWidth: 720,
      availableHeight: 600,
      contentWidth: 720,
      contentHeight: 180,
    });
    expect(layout.scale).toBeCloseTo(700 / 720, 6);
    expect(layout.hostHeight).toBe(600);
    expect(layout.contentHeight).toBeCloseTo(580 / (700 / 720), 6);
    expect(layout.overflow).toBe(false);
  });

  it("keeps long compact content width-fitted and clipped inside the same host", () => {
    const layout = calculateAdaptivePreviewLayout({
      mode: "preview",
      availableWidth: 720,
      availableHeight: 600,
      contentWidth: 720,
      contentHeight: 1200,
    });
    expect(layout.scale).toBeCloseTo(700 / 720, 6);
    expect(layout.hostHeight).toBe(600);
    expect(layout.contentHeight).toBe(1200);
    expect(layout.overflow).toBe(true);
  });

  it("uses width fit but not height fit for expanded answers", () => {
    const layout = calculateAdaptivePreviewLayout({ mode: "expanded", availableWidth: 720, contentWidth: 900, contentHeight: 3200 });
    expect(layout.scale).toBeCloseTo(0.8, 6);
    expect(layout.hostHeight).toBe(2560);
    expect(layout.overflow).toBe(false);
  });

  it("normalizes invalid measurements without NaN or zero scale", () => {
    const layout = calculateAdaptivePreviewLayout({ mode: "preview", availableWidth: Number.NaN, contentWidth: -1, contentHeight: 0 });
    expect(Number.isFinite(layout.scale)).toBe(true);
    expect(layout.scale).toBeGreaterThan(0);
    expect(layout.hostHeight).toBeGreaterThan(0);
  });

  it("keeps explicit front and back side metadata", () => {
    const front = buildShadowPreviewDocument({ html: "<b>front</b>", mode: "preview", side: "front" });
    const back = buildShadowPreviewDocument({ html: "<b>back</b>", mode: "expanded", side: "back" });
    expect(front.shellClassName).toContain("asr-shadow-card-shell--front");
    expect(back.shellClassName).toContain("asr-shadow-card-shell--back");
    expect(back.shellClassName).toContain("asr-shadow-card-shell--expanded");
    const html = renderToStaticMarkup(<AnkiCardShadowPreview html="<b>answer</b>" mode="expanded" side="back" />);
    expect(html).toContain('data-preview-side="back"');
    expect(html).toContain('data-preview-mode="expanded"');
  });

  it("keeps compact preview clipped while applying an explicit Anki day/night context", () => {
    const lightCard = buildShadowPreviewDocument({
      html: '<span class="term">front</span>',
      css: '@scope (.card){:scope{background-color:rgb(250,240,220);color:rgb(20,30,40)}:scope.card1{text-align:center}:scope .term{font-weight:700}}',
      cardOrd: 0,
      nightMode: false,
      mode: "preview",
    });

    const darkCard = buildShadowPreviewDocument({
      html: '<span class="term">front</span>',
      css: '.card.nightMode{background-color:rgb(47,47,49)}.nightMode .term{color:rgb(245,245,245)}',
      cardOrd: 0,
      nightMode: true,
      mode: "preview",
    });

    expect(lightCard.cardClassName).toBe("card card1");
    expect(lightCard.shellClassName).not.toContain("nightMode");
    expect(darkCard.cardClassName).toBe("card card1 nightMode");
    expect(darkCard.shellClassName).toContain("nightMode");
    expect(darkCard.styleText).toContain(".card.nightMode{background-color:rgb(47,47,49)}");
    expect(darkCard.styleText).toContain(".nightMode .term{color:rgb(245,245,245)}");
    expect(darkCard.styleText).toContain(":where(.card).nightMode");
    expect(darkCard.styleText).toContain("background: #111827");
    expect(darkCard.styleText).toContain('font-family: Arial, "Noto Sans JP", sans-serif');
    expect(darkCard.styleText).toContain(".asr-shadow-card-viewport--preview > .card");
    expect(lightCard.styleText).toContain(".asr-shadow-card-shell--preview");
    expect(lightCard.styleText).toContain("overflow: hidden");
    expect(lightCard.styleText).not.toContain("overflow-y: auto");
    expect(lightCard.styleText).not.toContain("overscroll-behavior: contain");
    expect(lightCard.styleText).toContain("background-color:rgb(250,240,220)");
    expect(lightCard.styleText).toContain(":where(.card)");
    expect(lightCard.styleText).toContain(":where(.asr-shadow-card-viewport--preview) > :where(.card)");
    expect(lightCard.styleText).not.toContain(".asr-shadow-card-viewport--preview .card");
  });

  it("keeps mode fallbacks weaker than exact native template typography and spacing", () => {
    const document = buildShadowPreviewDocument({
      html: '<div class="main-word"><span class="word-focus">影</span></div>',
      css: '@scope (.card){:scope{font-size:20px;line-height:1.6;padding:7px}:scope .main-word{font-size:36px}:scope .word-focus{color:rgb(255,170,0)}}',
      cardOrd: 0,
      nightMode: false,
      mode: "preview",
    });
    const templateIndex = document.styleText.indexOf('@scope (.card)');
    expect(templateIndex).toBeGreaterThan(document.styleText.indexOf(':where(.card)'));
    expect(document.styleText).toContain(':where(.asr-shadow-card-viewport--preview) > :where(.card)');
    expect(document.styleText).toContain('font-size:20px;line-height:1.6;padding:7px');
    expect(document.styleText).not.toContain('.asr-shadow-card-viewport--preview .card');
  });

  it("updates shell and card nightMode classes without replacing the preview payload", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    const css = '.card{background-color:rgb(250,250,250)}.card.nightMode{background-color:rgb(47,47,49)}.nightMode .target{color:rgb(245,245,245)}';
    const html = '<span class="target">same payload</span>';

    await act(async () => root.render(<AnkiCardShadowPreview html={html} css={css} nightMode={false} mode="preview" side="front" />));
    let host = container.querySelector<HTMLElement>('[data-testid="anki-card-shadow-preview"]')!;
    expect(host.dataset.previewNightMode).toBe("false");
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card-shell"]')?.classList.contains("nightMode")).toBe(false);
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card"]')?.classList.contains("nightMode")).toBe(false);
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card"]')?.innerHTML).toContain("same payload");

    await act(async () => root.render(<AnkiCardShadowPreview html={html} css={css} nightMode mode="preview" side="front" />));
    host = container.querySelector<HTMLElement>('[data-testid="anki-card-shadow-preview"]')!;
    expect(host.dataset.previewNightMode).toBe("true");
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card-shell"]')?.classList.contains("nightMode")).toBe(true);
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card"]')?.classList.contains("nightMode")).toBe(true);
    expect(host.shadowRoot?.querySelector('[data-testid="asr-shadow-card"]')?.innerHTML).toContain("same payload");

    await act(async () => root.unmount());
    container.remove();
  });

  it("adds the dashboard token only to parser-approved local CSS media URLs", () => {
    window.history.replaceState(null, "", "/?token=local-token#/cards");
    const css = '@scope (.card){.card{background:url("/api/media?name=safe.png")}}';

    expect(cssWithMediaToken(css)).toContain('/api/media?name=safe.png&token=local-token');
    expect(cssWithMediaToken('.card{background:url("https://evil.invalid/a.png")}')).toBe(
      '.card{background:url("https://evil.invalid/a.png")}',
    );
  });

  it("uses the supplied localized accessible name for the icon-only replay control", () => {
    const card = replayCard();

    enhanceReplayControls(card, "Воспроизвести аудио");
    expect(
      card.querySelector("button")?.getAttribute("aria-label"),
    ).toBe("Воспроизвести аудио");

    enhanceReplayControls(card, "Play audio");
    expect(
      card.querySelector("button")?.getAttribute("aria-label"),
    ).toBe("Play audio");
  });

  it("overrides a stale card-provided replay label", () => {
    const card = replayCard();

    enhanceReplayControls(card, "Play audio");

    expect(
      card.querySelector("button")?.getAttribute("aria-label"),
    ).not.toBe("stale label");
  });

  it("keeps a strong two-color focus fallback without overriding template specificity", () => {
    const document = buildShadowPreviewDocument({
      html: "",
      mode: "preview",
    });

    expect(document.styleText).toContain(
      "outline: 2px solid #f9f9f9",
    );
    expect(document.styleText).toContain("outline-offset: 0");
    expect(document.styleText).toContain(
      "box-shadow: 0 0 0 4px #193146",
    );
    expect(document.styleText).not.toContain("!important");
  });
});
