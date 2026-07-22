import hljs from "highlight.js/lib/core";
import java from "highlight.js/lib/languages/java";

const MAX_JAVA_BLOCKS = 8;
const MAX_JAVA_BLOCK_CHARS = 20_000;
const MAX_JAVA_TOTAL_CHARS = 60_000;

const JAVA_SELECTOR = [
  "code.language-java",
  "code.lang-java",
  "pre.language-java > code",
  "pre.lang-java > code",
].join(",");

hljs.registerLanguage("java", java);

export interface CardCodeHighlightingResult {
  highlighted: number;
  skippedOversized: number;
  skippedLimit: number;
  failed: number;
}

export function highlightJavaBlocks(root: ParentNode): CardCodeHighlightingResult {
  const candidates = [...root.querySelectorAll<HTMLElement>(JAVA_SELECTOR)];
  let highlighted = 0;
  let skippedOversized = 0;
  let skippedLimit = 0;
  let failed = 0;
  let totalChars = 0;

  for (let index = 0; index < candidates.length; index += 1) {
    if (index >= MAX_JAVA_BLOCKS) {
      skippedLimit += candidates.length - index;
      break;
    }

    const element = candidates[index]!;
    if (element.dataset.asrCodeHighlighted === "java") {
      continue;
    }

    const source = element.textContent ?? "";
    if (!source || source.length > MAX_JAVA_BLOCK_CHARS) {
      skippedOversized += 1;
      continue;
    }
    if (totalChars + source.length > MAX_JAVA_TOTAL_CHARS) {
      skippedLimit += candidates.length - index;
      break;
    }
    totalChars += source.length;

    const originalClassName = element.className;
    const originalHighlighted = element.getAttribute("data-highlighted");
    element.replaceChildren(element.ownerDocument.createTextNode(source));
    element.classList.add("language-java");
    element.removeAttribute("data-highlighted");

    try {
      hljs.highlightElement(element);
    } catch {
      restorePlainCode(element, source, originalClassName, originalHighlighted);
      failed += 1;
      continue;
    }

    if (element.textContent !== source) {
      restorePlainCode(element, source, originalClassName, originalHighlighted);
      failed += 1;
      continue;
    }

    element.dataset.asrCodeHighlighted = "java";
    highlighted += 1;
  }

  if (highlighted > 0 && isShadowRoot(root)) {
    ensureHighlightStyle(root);
  }

  return { highlighted, skippedOversized, skippedLimit, failed };
}

function restorePlainCode(
  element: HTMLElement,
  source: string,
  originalClassName: string,
  originalHighlighted: string | null,
): void {
  element.className = originalClassName;
  element.replaceChildren(element.ownerDocument.createTextNode(source));
  element.removeAttribute("data-asr-code-highlighted");
  if (originalHighlighted === null) {
    element.removeAttribute("data-highlighted");
  } else {
    element.setAttribute("data-highlighted", originalHighlighted);
  }
}

function isShadowRoot(value: ParentNode): value is ShadowRoot {
  return typeof ShadowRoot !== "undefined" && value instanceof ShadowRoot;
}

function ensureHighlightStyle(root: ShadowRoot): void {
  if (root.querySelector("style[data-asr-java-highlighting]")) {
    return;
  }

  const style = root.ownerDocument.createElement("style");
  style.dataset.asrJavaHighlighting = "true";
  style.textContent = `
.hljs-keyword,
.hljs-type,
.hljs-title.class_,
.hljs-built_in,
.hljs-literal {
  color: color-mix(in srgb, currentColor 38%, #2563eb 62%);
}

.hljs-string,
.hljs-char {
  color: color-mix(in srgb, currentColor 42%, #16803c 58%);
}

.hljs-comment,
.hljs-quote {
  color: currentColor;
  opacity: .68;
  font-style: italic;
}

.hljs-number {
  color: color-mix(in srgb, currentColor 42%, #7c3aed 58%);
}

.hljs-meta,
.hljs-annotation {
  color: color-mix(in srgb, currentColor 40%, #b45309 60%);
}

.hljs-variable,
.hljs-params {
  color: color-mix(in srgb, currentColor 70%, #0f766e 30%);
}
`;
  root.prepend(style);
}
