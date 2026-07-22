const MAX_JAVA_BLOCKS = 12;
const MAX_JAVA_BLOCK_CHARS = 20_000;
const MAX_JAVA_TOTAL_CHARS = 60_000;

const JAVA_SELECTOR = [
  "code.language-java",
  "code.lang-java",
  "pre.language-java > code",
  "pre.lang-java > code",
].join(",");

const JAVA_TOKEN_PATTERN = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|@[A-Za-z_$][\w$]*|\b(?:abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|exports|extends|final|finally|float|for|goto|if|implements|import|instanceof|int|interface|long|module|native|new|non-sealed|open|opens|package|permits|private|protected|provides|public|record|requires|return|sealed|short|static|strictfp|super|switch|synchronized|this|throw|throws|to|transient|transitive|try|uses|var|void|volatile|while|with|yield|null|true|false)\b|\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?[fFdDlL]?)\b)/g;

export type JavaTokenKind = "plain" | "comment" | "string" | "annotation" | "keyword" | "number";

export interface JavaToken {
  kind: JavaTokenKind;
  value: string;
}

export function tokenizeJavaSource(source: string): JavaToken[] {
  const tokens: JavaToken[] = [];
  let cursor = 0;
  JAVA_TOKEN_PATTERN.lastIndex = 0;
  for (let match = JAVA_TOKEN_PATTERN.exec(source); match; match = JAVA_TOKEN_PATTERN.exec(source)) {
    if (match.index > cursor) tokens.push({ kind: "plain", value: source.slice(cursor, match.index) });
    const value = match[0];
    const kind: JavaTokenKind = value.startsWith("//") || value.startsWith("/*")
      ? "comment"
      : value.startsWith("\"") || value.startsWith("'")
        ? "string"
        : value.startsWith("@")
          ? "annotation"
          : /^\d|^0[xXbB]/.test(value)
            ? "number"
            : "keyword";
    tokens.push({ kind, value });
    cursor = match.index + value.length;
  }
  if (cursor < source.length) tokens.push({ kind: "plain", value: source.slice(cursor) });
  return tokens;
}

export function highlightJavaElement(element: HTMLElement): boolean {
  if (!element.matches(JAVA_SELECTOR) || element.dataset.asrCodeHighlighted === "java") return false;
  const source = element.textContent ?? "";
  if (!source || source.length > MAX_JAVA_BLOCK_CHARS) return false;

  const fragment = element.ownerDocument.createDocumentFragment();
  for (const token of tokenizeJavaSource(source)) {
    if (token.kind === "plain") {
      fragment.append(element.ownerDocument.createTextNode(token.value));
      continue;
    }
    const span = element.ownerDocument.createElement("span");
    span.className = `asr-code-token asr-code-token--${token.kind}`;
    span.textContent = token.value;
    fragment.append(span);
  }
  element.replaceChildren(fragment);
  element.dataset.asrCodeHighlighted = "java";
  return element.textContent === source;
}

export function highlightJavaBlocks(root: ParentNode): number {
  const candidates = [...root.querySelectorAll<HTMLElement>(JAVA_SELECTOR)].slice(0, MAX_JAVA_BLOCKS);
  let totalChars = 0;
  let highlighted = 0;
  for (const element of candidates) {
    const length = element.textContent?.length ?? 0;
    if (totalChars + length > MAX_JAVA_TOTAL_CHARS) break;
    totalChars += length;
    if (highlightJavaElement(element)) highlighted += 1;
  }
  if (highlighted > 0 && isShadowRoot(root)) ensureHighlightStyle(root);
  return highlighted;
}

export function installCardCodeHighlighting(doc: Document = document): () => void {
  let frame = 0;
  let retries = 0;
  const scan = () => {
    frame = 0;
    for (const host of doc.querySelectorAll<HTMLElement>("[data-shadow-preview='true']")) {
      if (host.shadowRoot) highlightJavaBlocks(host.shadowRoot);
    }
    if (retries > 0) {
      retries -= 1;
      schedule();
    }
  };
  const schedule = () => {
    if (!frame) frame = window.requestAnimationFrame(scan);
  };
  const observer = new MutationObserver(() => {
    retries = 2;
    schedule();
  });
  observer.observe(doc.documentElement, { childList: true, subtree: true, characterData: true });
  retries = 2;
  schedule();
  return () => {
    observer.disconnect();
    if (frame) window.cancelAnimationFrame(frame);
  };
}

function isShadowRoot(value: ParentNode): value is ShadowRoot {
  return typeof ShadowRoot !== "undefined" && value instanceof ShadowRoot;
}

function ensureHighlightStyle(root: ShadowRoot): void {
  if (root.querySelector("style[data-asr-java-highlighting]")) return;
  const style = root.ownerDocument.createElement("style");
  style.dataset.asrJavaHighlighting = "true";
  style.textContent = `
.card code.language-java,
.card code.lang-java,
.card pre.language-java > code,
.card pre.lang-java > code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-variant-ligatures: none;
  tab-size: 4;
}
.asr-code-token--keyword { color: #0550ae; font-weight: 650; }
.asr-code-token--string { color: #a31515; }
.asr-code-token--comment { color: #527a5a; font-style: italic; }
.asr-code-token--annotation { color: #7a3e9d; }
.asr-code-token--number { color: #0b6b67; }
.nightMode .asr-code-token--keyword,
.card.nightMode .asr-code-token--keyword { color: #7ab7ff; }
.nightMode .asr-code-token--string,
.card.nightMode .asr-code-token--string { color: #ffb4a8; }
.nightMode .asr-code-token--comment,
.card.nightMode .asr-code-token--comment { color: #8fd19e; }
.nightMode .asr-code-token--annotation,
.card.nightMode .asr-code-token--annotation { color: #d9a8ff; }
.nightMode .asr-code-token--number,
.card.nightMode .asr-code-token--number { color: #83d9d2; }
`;
  root.prepend(style);
}
