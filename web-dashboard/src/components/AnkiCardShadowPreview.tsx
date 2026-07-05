import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";

export type AnkiCardShadowPreviewMode = "table" | "tile" | "preview";
export type AnkiCardShadowPreviewSide = "front" | "back" | "answer";

export interface AnkiPreviewModeConfig {
  baseWidth: number;
  baseHeight: number;
  targetWidth: number;
  targetHeight: number;
  scale: number;
  audioButtonSize: number;
}

export const ANKI_PREVIEW_MODE_CONFIG: Record<AnkiCardShadowPreviewMode, AnkiPreviewModeConfig> = {
  table: {
    baseWidth: 640,
    baseHeight: 392,
    targetWidth: 292,
    targetHeight: 174,
    scale: 0.43,
    audioButtonSize: 32,
  },
  tile: {
    baseWidth: 640,
    baseHeight: 380,
    targetWidth: 520,
    targetHeight: 292,
    scale: 0.72,
    audioButtonSize: 38,
  },
  preview: {
    baseWidth: 640,
    baseHeight: 420,
    targetWidth: 640,
    targetHeight: 420,
    scale: 0.94,
    audioButtonSize: 42,
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

const SHADOW_BASE_CSS = `
:host {
  all: initial;
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
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
  max-height: 100%;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.asr-shadow-card-viewport {
  flex: 0 0 var(--asr-preview-base-width);
  width: var(--asr-preview-base-width);
  min-height: var(--asr-preview-base-height);
  transform: scale(var(--asr-preview-scale));
  transform-origin: center center;
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

.nightMode .card,
.card.nightMode {
  background: #111827;
  color: #f8fafc;
}
`;

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

function previewModeStyle(mode: AnkiCardShadowPreviewMode): CSSProperties {
  const config = ANKI_PREVIEW_MODE_CONFIG[mode];
  return {
    "--asr-preview-base-width": `${config.baseWidth}px`,
    "--asr-preview-base-height": `${config.baseHeight}px`,
    "--asr-preview-target-width": `${config.targetWidth}px`,
    "--asr-preview-target-height": `${config.targetHeight}px`,
    "--asr-preview-scale": config.scale,
    "--asr-card-audio-size": `${config.audioButtonSize}px`,
  } as CSSProperties;
}

export function AnkiCardShadowPreview({
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
  const resolvedNightMode = nightMode ?? autoNightMode;
  const shadowDocument = useMemo(
    () => buildShadowPreviewDocument({ html, css, title, cardOrd, nightMode: resolvedNightMode, mode, side, className }),
    [cardOrd, className, css, html, mode, resolvedNightMode, side, title],
  );
  const hostStyle = useMemo(() => previewModeStyle(mode), [mode]);

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

    const viewport = document.createElement("div");
    viewport.className = shadowDocument.viewportClassName;

    const card = document.createElement("div");
    card.className = shadowDocument.cardClassName;
    card.innerHTML = shadowDocument.html;

    viewport.appendChild(card);
    shell.appendChild(viewport);
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
    return () => shadowRoot.removeEventListener("click", handleReplayClick);
  }, [shadowDocument]);

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
    >
      <template data-shadow-preview-template dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
