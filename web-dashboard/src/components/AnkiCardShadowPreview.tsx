import { memo, type CSSProperties, useEffect, useMemo, useRef, useState } from "react";

export type AnkiCardShadowPreviewMode = "table" | "tile" | "preview" | "expanded";
export type AnkiCardShadowPreviewSide = "front" | "back" | "answer";

export interface AnkiPreviewModeConfig {
  baseWidth: number;
  baseHeight: number;
  targetWidth: number;
  targetHeight: number;
  scale: number;
  maxScale: number;
  minHeight: number;
  maxHeight?: number;
  allowAutoHeight: boolean;
  verticalPadding: number;
  audioButtonSize: number;
}

export const ANKI_PREVIEW_MODE_CONFIG: Record<AnkiCardShadowPreviewMode, AnkiPreviewModeConfig> = {
  table: {
    baseWidth: 640,
    baseHeight: 340,
    targetWidth: 320,
    targetHeight: 170,
    scale: 0.5,
    maxScale: 0.5,
    minHeight: 118,
    maxHeight: 190,
    allowAutoHeight: false,
    verticalPadding: 18,
    audioButtonSize: 30,
  },
  tile: {
    baseWidth: 600,
    baseHeight: 330,
    targetWidth: 500,
    targetHeight: 268,
    scale: 0.78,
    maxScale: 0.82,
    minHeight: 190,
    maxHeight: 340,
    allowAutoHeight: false,
    verticalPadding: 24,
    audioButtonSize: 36,
  },
  preview: {
    baseWidth: 720,
    baseHeight: 420,
    targetWidth: 720,
    targetHeight: 390,
    scale: 0.88,
    maxScale: 1,
    minHeight: 220,
    maxHeight: 440,
    allowAutoHeight: false,
    verticalPadding: 24,
    audioButtonSize: 40,
  },
  expanded: {
    baseWidth: 900,
    baseHeight: 1,
    targetWidth: 980,
    targetHeight: 1,
    scale: 1,
    maxScale: 1,
    minHeight: 1,
    allowAutoHeight: true,
    verticalPadding: 0,
    audioButtonSize: 40,
  },
};

export interface AnkiCardShadowPreviewProps {
  html: string;
  css?: string;
  title?: string;
  cardOrd?: number;
  renderSource?: string;
  nightMode?: boolean;
  mode: AnkiCardShadowPreviewMode;
  side?: AnkiCardShadowPreviewSide;
  className?: string;
}

interface ShadowPreviewDocument {
  cardClassName: string;
  html: string;
  shellClassName: string;
  styleText: string;
  viewportClassName: string;
}

export interface AdaptivePreviewLayoutInput {
  mode: AnkiCardShadowPreviewMode;
  availableWidth: number;
  contentWidth: number;
  contentHeight: number;
}

export interface AdaptivePreviewLayout {
  scale: number;
  hostHeight: number;
  targetWidth: number;
  contentWidth: number;
  contentHeight: number;
  measured: boolean;
  overflow: boolean;
}

const SHADOW_BASE_CSS = `
:host {
  all: initial;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 100%;
  contain: content;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

.asr-shadow-card-shell {
  display: flex;
  width: var(--asr-preview-target-width);
  height: var(--asr-preview-target-height);
  max-width: 100%;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.asr-shadow-card-shell--preview {
  align-items: flex-start;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px;
}

.asr-shadow-card-shell--expanded {
  align-items: flex-start;
  height: auto;
  overflow: visible;
  padding: 0;
}

.asr-shadow-card-frame {
  position: relative;
  flex: 0 0 auto;
  width: var(--asr-preview-scaled-width);
  height: var(--asr-preview-scaled-height);
}

.asr-shadow-card-viewport {
  position: absolute;
  inset: 0 auto auto 0;
  width: var(--asr-preview-content-width);
  min-height: var(--asr-preview-content-height);
  transform: scale(var(--asr-preview-scale));
  transform-origin: top left;
}

.card {
  width: var(--asr-preview-base-width);
  min-height: var(--asr-preview-base-height);
  overflow: visible;
  padding: 24px;
  background: #ffffff;
  color: #111827;
  font-family: Arial, sans-serif;
  font-size: 28px;
  line-height: 1.45;
  text-align: center;
}

.asr-shadow-card-viewport--table .card {
  padding: 18px;
  font-size: 30px;
  line-height: 1.35;
}

.asr-shadow-card-viewport--tile .card {
  padding: 22px;
  font-size: 30px;
  line-height: 1.4;
}

.asr-shadow-card-viewport--preview .card,
.asr-shadow-card-viewport--expanded .card {
  padding: 28px;
  font-size: 28px;
  line-height: 1.5;
}

.card pre {
  max-width: 100%;
  overflow: auto;
  white-space: pre;
}

.nightMode .card,
.card.nightMode {
  background: #111827;
  color: #f8fafc;
}
`;

function measuredNumber(value: number, fallback: number): number {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function calculateAdaptivePreviewLayout({
  mode,
  availableWidth,
  contentWidth,
  contentHeight,
}: AdaptivePreviewLayoutInput): AdaptivePreviewLayout {
  const config = ANKI_PREVIEW_MODE_CONFIG[mode];
  const measuredContentWidth = Math.max(config.baseWidth, measuredNumber(contentWidth, config.baseWidth));
  const measuredContentHeight = Math.max(config.baseHeight, measuredNumber(contentHeight, config.baseHeight));
  const measuredAvailableWidth = measuredNumber(availableWidth, config.targetWidth);
  const targetWidth = Math.max(1, Math.min(measuredAvailableWidth, config.targetWidth));
  const widthScale = targetWidth / measuredContentWidth;
  let scale = Math.max(Number.EPSILON, Math.min(widthScale, config.maxScale));

  if (mode !== "preview" && !config.allowAutoHeight && config.maxHeight) {
    const heightScale = Math.max(Number.EPSILON, (config.maxHeight - config.verticalPadding) / measuredContentHeight);
    scale = Math.max(Number.EPSILON, Math.min(scale, heightScale, config.maxScale));
  }

  const scaledHeight = Math.ceil(measuredContentHeight * scale + config.verticalPadding);
  const unclampedHeight = Math.max(config.minHeight, scaledHeight);
  const hostHeight = config.allowAutoHeight || !config.maxHeight ? unclampedHeight : Math.min(config.maxHeight, unclampedHeight);
  const overflow = !config.allowAutoHeight && scaledHeight > hostHeight + 1;

  return {
    scale,
    hostHeight,
    targetWidth,
    contentWidth: measuredContentWidth,
    contentHeight: measuredContentHeight,
    measured: true,
    overflow,
  };
}

function initialAdaptiveLayout(mode: AnkiCardShadowPreviewMode): AdaptivePreviewLayout {
  const config = ANKI_PREVIEW_MODE_CONFIG[mode];
  return {
    scale: config.scale,
    hostHeight: config.targetHeight,
    targetWidth: config.targetWidth,
    contentWidth: config.baseWidth,
    contentHeight: config.baseHeight,
    measured: false,
    overflow: false,
  };
}

const SHADOW_SAFETY_CSS = `
.card img {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
  object-fit: contain;
}

.card audio,
.card .asr-card-audio {
  display: none;
}

.card .asr-card-replay {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  margin: 0 0 12px;
}

.card .asr-card-replay-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--asr-card-audio-size);
  height: var(--asr-card-audio-size);
  border: 1px solid rgba(37, 99, 235, 0.42);
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.72);
  cursor: pointer;
  padding: 0;
}

.card .asr-card-replay-button:hover {
  background: rgba(37, 99, 235, 0.16);
  border-color: rgba(37, 99, 235, 0.62);
}

.card .asr-card-replay-button:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.28);
  outline-offset: 2px;
}

.card .asr-card-replay-icon {
  display: block;
  font-size: 16px;
  line-height: 1;
  transform: translateX(1px);
}

.card .asr-card-media-missing {
  display: inline-block;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 6px;
  padding: 2px 8px;
  color: #94a3b8;
  font-size: 18px;
}
`;

export function buildShadowPreviewDocument({
  html,
  css = "",
  cardOrd = 0,
  nightMode = false,
  mode,
  side = "front",
}: AnkiCardShadowPreviewProps): ShadowPreviewDocument {
  const normalizedOrd = Number.isFinite(cardOrd) ? Math.max(0, Math.floor(cardOrd)) : 0;
  const cardClasses = ["card", `card${normalizedOrd + 1}`, nightMode ? "nightMode" : ""].filter(Boolean);
  return {
    cardClassName: cardClasses.join(" "),
    html: html || "",
    shellClassName: ["asr-shadow-card-shell", `asr-shadow-card-shell--${mode}`, `asr-shadow-card-shell--${side}`, nightMode ? "nightMode" : ""]
      .filter(Boolean)
      .join(" "),
    styleText: [SHADOW_BASE_CSS, css || "", SHADOW_SAFETY_CSS].join("\n"),
    viewportClassName: `asr-shadow-card-viewport asr-shadow-card-viewport--${mode}`,
  };
}

function previewModeStyle(mode: AnkiCardShadowPreviewMode, layout: AdaptivePreviewLayout): CSSProperties {
  const config = ANKI_PREVIEW_MODE_CONFIG[mode];
  return {
    "--asr-preview-base-width": `${config.baseWidth}px`,
    "--asr-preview-base-height": `${config.baseHeight}px`,
    "--asr-preview-content-width": `${layout.contentWidth}px`,
    "--asr-preview-content-height": `${layout.contentHeight}px`,
    "--asr-preview-scaled-width": `${Math.max(1, Math.ceil(layout.contentWidth * layout.scale))}px`,
    "--asr-preview-scaled-height": `${Math.max(1, Math.ceil(layout.contentHeight * layout.scale))}px`,
    "--asr-preview-target-width": `${layout.targetWidth}px`,
    "--asr-preview-target-height": `${layout.hostHeight}px`,
    "--asr-preview-scale": layout.scale,
    "--asr-shadow-host-height": `${layout.hostHeight}px`,
    "--asr-card-audio-size": `${config.audioButtonSize}px`,
  } as CSSProperties;
}

function AnkiCardShadowPreviewComponent({
  html,
  css = "",
  title = "",
  cardOrd = 0,
  renderSource = "",
  nightMode,
  mode,
  side = "front",
  className = "",
}: AnkiCardShadowPreviewProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [autoNightMode, setAutoNightMode] = useState(false);
  const [layout, setLayout] = useState<AdaptivePreviewLayout>(() => initialAdaptiveLayout(mode));
  const resolvedNightMode = nightMode ?? autoNightMode;
  const shadowDocument = useMemo(
    () => buildShadowPreviewDocument({ html, css, title, cardOrd, nightMode: resolvedNightMode, mode, side, className }),
    [cardOrd, className, css, html, mode, resolvedNightMode, side, title],
  );
  const hostStyle = useMemo(() => previewModeStyle(mode, layout), [layout, mode]);

  useEffect(() => {
    setLayout(initialAdaptiveLayout(mode));
  }, [mode]);

  useEffect(() => {
    if (nightMode !== undefined || typeof document === "undefined") {
      return;
    }
    const readTheme = () => {
      const theme = document.documentElement.getAttribute("data-theme");
      if (theme) {
        setAutoNightMode(theme !== "light");
        return;
      }
      setAutoNightMode(Boolean(window.matchMedia?.("(prefers-color-scheme: dark)").matches));
    };
    readTheme();
    const observer = new MutationObserver(readTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, [nightMode]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host?.attachShadow || typeof document === "undefined") {
      return;
    }
    const shadowRoot = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    shadowRoot.replaceChildren();

    const style = document.createElement("style");
    style.textContent = shadowDocument.styleText;

    const shell = document.createElement("div");
    shell.className = shadowDocument.shellClassName;
    shell.setAttribute("data-testid", "asr-shadow-card-shell");

    const viewport = document.createElement("div");
    viewport.className = shadowDocument.viewportClassName;
    viewport.setAttribute("data-testid", "asr-shadow-card-viewport");

    const card = document.createElement("div");
    card.className = shadowDocument.cardClassName;
    card.setAttribute("data-testid", "asr-shadow-card");
    card.innerHTML = shadowDocument.html;

    const frame = document.createElement("div");
    frame.className = "asr-shadow-card-frame";
    frame.setAttribute("data-testid", "asr-shadow-card-frame");

    viewport.appendChild(card);
    frame.appendChild(viewport);
    shell.appendChild(frame);
    shadowRoot.append(style, shell);

    const handleReplayClick = (event: Event) => {
      const target = event.target instanceof Element ? event.target : null;
      const button = target?.closest(".asr-card-replay-button");
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }
      const wrapper = button.closest(".asr-card-replay");
      const audio = wrapper?.querySelector("audio.asr-card-audio");
      if (!(audio instanceof HTMLAudioElement)) {
        return;
      }
      try {
        audio.currentTime = 0;
        const playResult = audio.play();
        if (playResult && typeof playResult.catch === "function") {
          playResult.catch(() => undefined);
        }
      } catch {
        // Browser playback restrictions should not break the preview.
      }
    };
    shadowRoot.addEventListener("click", handleReplayClick);

    let measureFrame = 0;
    let disposed = false;
    const scheduleMeasure = () => {
      if (disposed || measureFrame) {
        return;
      }
      measureFrame = window.requestAnimationFrame(() => {
        measureFrame = 0;
        if (disposed) {
          return;
        }
        const hostRect = host.getBoundingClientRect();
        const cardRect = card.getBoundingClientRect();
        const nextLayout = calculateAdaptivePreviewLayout({
          mode,
          availableWidth: hostRect.width || host.clientWidth || ANKI_PREVIEW_MODE_CONFIG[mode].targetWidth,
          contentWidth: Math.max(card.scrollWidth, viewport.scrollWidth, cardRect.width, ANKI_PREVIEW_MODE_CONFIG[mode].baseWidth),
          contentHeight: Math.max(card.scrollHeight, viewport.scrollHeight, cardRect.height, ANKI_PREVIEW_MODE_CONFIG[mode].baseHeight),
        });
        setLayout((current) => {
          const heightChanged = Math.abs(current.hostHeight - nextLayout.hostHeight) > 1;
          const scaleChanged = Math.abs(current.scale - nextLayout.scale) > 0.005;
          const widthChanged = Math.abs(current.targetWidth - nextLayout.targetWidth) > 1;
          if (
            current.measured === nextLayout.measured &&
            current.overflow === nextLayout.overflow &&
            !heightChanged &&
            !scaleChanged &&
            !widthChanged
          ) {
            return current;
          }
          return nextLayout;
        });
      });
    };

    scheduleMeasure();

    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(scheduleMeasure) : null;
    resizeObserver?.observe(host);
    resizeObserver?.observe(card);

    const media = [...shadowRoot.querySelectorAll("img, video")];
    media.forEach((element) => {
      element.addEventListener("load", scheduleMeasure);
      element.addEventListener("loadedmetadata", scheduleMeasure);
      element.addEventListener("error", scheduleMeasure);
    });

    document.fonts?.ready?.then(scheduleMeasure).catch(() => undefined);

    return () => {
      disposed = true;
      if (measureFrame) {
        window.cancelAnimationFrame(measureFrame);
      }
      resizeObserver?.disconnect();
      media.forEach((element) => {
        element.removeEventListener("load", scheduleMeasure);
        element.removeEventListener("loadedmetadata", scheduleMeasure);
        element.removeEventListener("error", scheduleMeasure);
      });
      shadowRoot.removeEventListener("click", handleReplayClick);
    };
  }, [mode, shadowDocument]);

  return (
    <div
      ref={hostRef}
      className={`anki-card-shadow-preview anki-card-shadow-preview--${mode} ${className}`.trim()}
      title={title}
      aria-label={title}
      style={hostStyle}
      data-testid="anki-card-shadow-preview"
      data-shadow-preview="true"
      data-preview-mode={mode}
      data-preview-side={side}
      data-shadow-preview-mode={mode}
      data-shadow-preview-side={side}
      data-render-source={renderSource}
      data-preview-measured={layout.measured ? "true" : "false"}
      data-preview-overflow={layout.overflow ? "true" : "false"}
      data-preview-scale={layout.scale.toFixed(3)}
    >
      <template data-shadow-preview-template dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}

export const AnkiCardShadowPreview = memo(AnkiCardShadowPreviewComponent, arePreviewPropsEqual);

function arePreviewPropsEqual(previous: AnkiCardShadowPreviewProps, next: AnkiCardShadowPreviewProps): boolean {
  return (
    previous.html === next.html &&
    (previous.css || "") === (next.css || "") &&
    (previous.title || "") === (next.title || "") &&
    (previous.cardOrd || 0) === (next.cardOrd || 0) &&
    (previous.renderSource || "") === (next.renderSource || "") &&
    previous.nightMode === next.nightMode &&
    previous.mode === next.mode &&
    (previous.side || "front") === (next.side || "front") &&
    (previous.className || "") === (next.className || "")
  );
}
