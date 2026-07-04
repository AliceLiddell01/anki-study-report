import { useEffect, useMemo, useRef, useState } from "react";

export type AnkiCardShadowPreviewMode = "table" | "tile";

export interface AnkiCardShadowPreviewProps {
  html: string;
  css?: string;
  title?: string;
  cardOrd?: number;
  renderSource?: string;
  nightMode?: boolean;
  mode: AnkiCardShadowPreviewMode;
  className?: string;
}

interface ShadowPreviewDocument {
  cardClassName: string;
  html: string;
  styleText: string;
  viewportClassName: string;
}

const SHADOW_BASE_CSS = `
:host {
  all: initial;
  display: block;
  width: 100%;
  height: 100%;
  contain: content;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

.asr-shadow-card-viewport {
  width: 640px;
  transform-origin: top left;
}

.asr-shadow-card-viewport--table {
  transform: scale(0.36);
}

.asr-shadow-card-viewport--tile {
  transform: scale(0.5);
}

.card {
  width: 640px;
  min-height: 480px;
  overflow: visible;
  padding: 24px;
  background: #ffffff;
  color: #111827;
  font-family: Arial, sans-serif;
  font-size: 28px;
  line-height: 1.45;
  text-align: center;
}

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
  display: block;
  width: min(100%, 260px);
  height: 32px;
  margin: 0 0 16px;
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
}: AnkiCardShadowPreviewProps): ShadowPreviewDocument {
  const normalizedOrd = Number.isFinite(cardOrd) ? Math.max(0, Math.floor(cardOrd)) : 0;
  const cardClasses = ["card", `card${normalizedOrd + 1}`, nightMode ? "nightMode" : ""].filter(Boolean);
  return {
    cardClassName: cardClasses.join(" "),
    html: html || "",
    styleText: [SHADOW_BASE_CSS, css || "", SHADOW_SAFETY_CSS].join("\n"),
    viewportClassName: `asr-shadow-card-viewport asr-shadow-card-viewport--${mode}`,
  };
}

export function AnkiCardShadowPreview({
  html,
  css = "",
  title = "",
  cardOrd = 0,
  renderSource = "",
  nightMode,
  mode,
  className = "",
}: AnkiCardShadowPreviewProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [autoNightMode, setAutoNightMode] = useState(false);
  const resolvedNightMode = nightMode ?? autoNightMode;
  const shadowDocument = useMemo(
    () => buildShadowPreviewDocument({ html, css, title, cardOrd, nightMode: resolvedNightMode, mode, className }),
    [cardOrd, className, css, html, mode, resolvedNightMode, title],
  );

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

    const viewport = document.createElement("div");
    viewport.className = shadowDocument.viewportClassName;

    const card = document.createElement("div");
    card.className = shadowDocument.cardClassName;
    card.innerHTML = shadowDocument.html;

    viewport.appendChild(card);
    shadowRoot.append(style, viewport);
  }, [shadowDocument]);

  return (
    <div
      ref={hostRef}
      className={`anki-card-shadow-preview anki-card-shadow-preview--${mode} ${className}`.trim()}
      title={title}
      aria-label={title}
      data-testid="anki-card-shadow-preview"
      data-shadow-preview="true"
      data-shadow-preview-mode={mode}
      data-render-source={renderSource}
    >
      <template data-shadow-preview-template dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
