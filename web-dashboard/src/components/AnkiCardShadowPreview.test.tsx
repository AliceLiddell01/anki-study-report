// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AnkiCardShadowPreview, buildShadowPreviewDocument, calculateAdaptivePreviewLayout } from "./AnkiCardShadowPreview";

describe("AnkiCardShadowPreview layout", () => {
  it("never lets scaled content exceed a narrow host width", () => {
    const layout = calculateAdaptivePreviewLayout({ mode: "preview", availableWidth: 180, contentWidth: 900, contentHeight: 2400 });
    expect(layout.contentWidth * layout.scale).toBeLessThanOrEqual(layout.targetWidth + 0.001);
    expect(layout.scale).toBeCloseTo(0.2, 6);
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
});
