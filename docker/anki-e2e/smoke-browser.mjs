#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const value = process.argv[index];
  if (value.startsWith("--")) {
    args.set(value.slice(2), process.argv[index + 1] && !process.argv[index + 1].startsWith("--") ? process.argv[++index] : "1");
  }
}

const label = args.get("label") || "run";
const artifacts = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts";
const readyFile = process.env.ANKI_STUDY_REPORT_E2E_READY_FILE || path.join(artifacts, "dashboard-ready.json");
const ready = JSON.parse(await fs.readFile(readyFile, "utf8"));
const cardsUrl = `${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/cards`;
const consoleEvents = [];
const networkEvents = [];
const pageErrors = [];

const browser = await chromium.launch({ headless: true });
let page;
try {
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    consoleEvents.push({
      type: message.type(),
      text: message.text(),
      location: message.location(),
    });
  });
  page.on("pageerror", (error) => {
    pageErrors.push(String(error?.stack || error?.message || error));
  });
  page.on("requestfailed", (request) => {
    networkEvents.push({
      kind: "requestfailed",
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || null,
    });
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      networkEvents.push({
        kind: "response",
        status: response.status(),
        url: response.url(),
      });
    }
  });

  await capture(page, "table", "light", `cards-table-light-${label}.png`);
  const shadowDetails = await inspectShadowPreview(page);
  if (!shadowDetails.exists) {
    throw new Error("Shadow DOM preview host for fixture card was not found.");
  }
  if (
    !shadowDetails.hasOpenShadowRoot ||
    !shadowDetails.hasStyle ||
    !shadowDetails.hasCard ||
    shadowDetails.imgCount < 2 ||
    shadowDetails.audioCount < 1 ||
    shadowDetails.renderSource !== "anki_native" ||
    shadowDetails.hasRawAnkiPlayMarker ||
    shadowDetails.hasRawSoundMarker ||
    !shadowDetails.audioBeforeExample ||
    (!shadowDetails.hasWordFocus && !shadowDetails.hasInlineColor)
  ) {
    throw new Error(`Shadow DOM preview incomplete: ${JSON.stringify(shadowDetails)}`);
  }

  await fs.writeFile(path.join(artifacts, `cards-shadow-dom-dump-${label}.html`), redactArtifact(shadowDetails.html), "utf8");
  await capture(page, "table", "dark", `cards-table-dark-${label}.png`);
  await capture(page, "tiles", "dark", `cards-tile-${label}.png`);
  await capture(page, "ankiPreview", "dark", `cards-anki-preview-${label}.png`);

  await writeJson(`browser-smoke-${label}.json`, {
    ok: true,
    consoleEvents: relevantConsoleEvents(),
    networkEvents,
    pageErrors,
    shadowDetails,
  });

  if (pageErrors.length > 0) {
    throw new Error(`Browser page errors: ${pageErrors.join("\n")}`);
  }
  console.log(`Browser smoke passed for ${cardsUrl}`);
} catch (error) {
  if (page) {
    await writeBrowserFailureArtifacts(page, error);
  } else {
    await writeJson(`browser-smoke-${label}.json`, {
      ok: false,
      error: String(error?.stack || error?.message || error),
      consoleEvents: relevantConsoleEvents(),
      networkEvents,
      pageErrors,
    });
  }
  throw error;
} finally {
  await browser.close();
}

async function capture(page, mode, theme, fileName) {
  await prepareCardsPage(page, mode, theme);
  if (mode === "table" || mode === "tiles") {
    await waitForShadowFixture(page, mode === "tiles" ? "tile" : "table");
  } else {
    await waitForAnkiPreview(page);
  }
  await page.screenshot({ path: path.join(artifacts, fileName), fullPage: true });
}

async function prepareCardsPage(page, mode, theme) {
  await page.goto(cardsUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(
    ({ mode: selectedMode, theme: selectedTheme }) => {
      window.localStorage.setItem("anki-study-report.cards.displayMode", selectedMode);
      window.localStorage.setItem("anki-study-report-theme", selectedTheme);
      document.documentElement.dataset.theme = selectedTheme;
    },
    { mode, theme },
  );
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await waitForCardsPageReady(page);
}

async function waitForCardsPageReady(page) {
  await page.getByRole("heading", { name: "Карточки" }).waitFor({ timeout: 60000 });
  await page.waitForFunction(
    () => !/Проверяю локальный API дашборда|Отчёт ещё не построен|Локальный API дашборда не вернул отчёт/.test(document.body.innerText),
    undefined,
    { timeout: 60000 },
  );
  await page.waitForFunction(
    () =>
      document.body.innerText.includes("要望") ||
      document.documentElement.innerHTML.includes("要望") ||
      document.documentElement.innerHTML.includes("%E8%A6%81"),
    undefined,
    { timeout: 60000 },
  );
  const errorText = await visibleErrorText(page);
  if (errorText) {
    throw new Error(`Cards page shows visible error: ${errorText}`);
  }
}

async function waitForShadowFixture(page, mode) {
  const host = page.locator(`[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="${mode}"]`).first();
  await host.waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    ({ expectedMode }) => {
      const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"]')];
      return hosts.some((host) => {
        if (host.getAttribute("data-shadow-preview-mode") !== expectedMode) {
          return false;
        }
        const shadowRoot = host.shadowRoot;
        const html = shadowRoot?.innerHTML || "";
        const template = host.querySelector("template")?.innerHTML || "";
        const searchable = `${host.getAttribute("title") || ""}\n${template}\n${html}`;
        return Boolean(shadowRoot && (searchable.includes("要望") || searchable.includes("%E8%A6%81")));
      });
    },
    { expectedMode: mode },
    { timeout: 60000 },
  );
}

async function waitForAnkiPreview(page) {
  await page.locator(".asr-front-preview-html").first().waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    () => {
      const previews = [...document.querySelectorAll(".asr-front-preview-html")];
      return previews.some((preview) => {
        const html = preview.innerHTML;
        const text = preview.textContent || "";
        return text.includes("要望") || html.includes("要望") || html.includes("%E8%A6%81");
      });
    },
    undefined,
    { timeout: 60000 },
  );
}

async function inspectShadowPreview(page) {
  return page.evaluate(() => {
    const hosts = [
      ...document.querySelectorAll('[data-testid="anki-card-shadow-preview"], [data-shadow-preview="true"]'),
    ];
    for (const host of hosts) {
      const shadowRoot = host.shadowRoot;
      const html = shadowRoot?.innerHTML || "";
      const template = host.querySelector("template")?.innerHTML || "";
      const searchable = `${host.getAttribute("title") || ""}\n${template}\n${html}`;
      const cardHtml = shadowRoot?.querySelector(".card")?.innerHTML || html;
      const audioIndex = Math.max(cardHtml.indexOf("asr-card-audio"), cardHtml.indexOf("<audio"));
      const replayIndex = cardHtml.indexOf("asr-card-replay");
      const controlIndex = audioIndex >= 0 ? audioIndex : replayIndex;
      const exampleIndex = cardHtml.indexOf("word-focus");
      if (!searchable.includes("要望") && !searchable.includes("%E8%A6%81")) {
        continue;
      }
      return {
        exists: true,
        mode: host.getAttribute("data-shadow-preview-mode") || "",
        renderSource: host.getAttribute("data-render-source") || "",
        hasOpenShadowRoot: Boolean(shadowRoot),
        hasStyle: Boolean(shadowRoot?.querySelector("style")),
        hasCard: Boolean(shadowRoot?.querySelector(".card")),
        imgCount: shadowRoot?.querySelectorAll("img").length || 0,
        audioCount: shadowRoot?.querySelectorAll("audio, .asr-card-audio").length || 0,
        hasWordFocus: Boolean(shadowRoot?.querySelector(".word-focus")),
        hasInlineColor: Boolean(shadowRoot?.querySelector('[style*="color"]')),
        hasRawAnkiPlayMarker: html.includes("[anki:play:"),
        hasRawSoundMarker: html.toLowerCase().includes("[sound:"),
        audioBeforeExample: controlIndex >= 0 && exampleIndex >= 0 && controlIndex < exampleIndex,
        hasScrollbarMarker: Boolean(shadowRoot?.querySelector(".inner-scrollbar, .scrollbar")),
        html,
      };
    }
    return {
      exists: false,
      mode: "",
      renderSource: "",
      hasOpenShadowRoot: false,
      hasStyle: false,
      hasCard: false,
      imgCount: 0,
      audioCount: 0,
      hasWordFocus: false,
      hasInlineColor: false,
      hasRawAnkiPlayMarker: false,
      hasRawSoundMarker: false,
      audioBeforeExample: false,
      hasScrollbarMarker: false,
      html: "",
    };
  });
}

async function visibleErrorText(page) {
  return page.evaluate(() => {
    const text = document.body.innerText || "";
    const markers = [
      "Локальный API дашборда не вернул отчёт",
      "Откройте дашборд из Anki Study Report",
      "Не удалось собрать данные по карточкам",
    ];
    return markers.find((marker) => text.includes(marker)) || "";
  });
}

async function writeBrowserFailureArtifacts(page, error) {
  await fs.mkdir(artifacts, { recursive: true });
  const errorText = String(error?.stack || error?.message || error);
  await saveBestEffort(() => page.screenshot({ path: path.join(artifacts, `browser-failure-${label}.png`), fullPage: true }));
  await saveBestEffort(async () => fs.writeFile(path.join(artifacts, `browser-failure-${label}.html`), redactArtifact(await page.content()), "utf8"));
  await saveBestEffort(() => writeConsoleLog(`browser-console-${label}.log`));
  await saveBestEffort(() => writeJson(`browser-network-${label}.json`, networkEvents));
  await saveBestEffort(async () => writeJson(`browser-dom-summary-${label}.json`, await buildDomSummary(page)));
  await saveBestEffort(() =>
    writeJson(`browser-smoke-${label}.json`, {
      ok: false,
      error: errorText,
      consoleEvents: relevantConsoleEvents(),
      networkEvents,
      pageErrors,
    }),
  );
}

async function buildDomSummary(page) {
  return page.evaluate(() => {
    const all = [...document.querySelectorAll("*")];
    const interestingElements = all.filter((element) =>
      [...element.attributes].some((attribute) => /shadow|preview|card/i.test(`${attribute.name}=${attribute.value}`)),
    );
    const dataAttributes = [];
    for (const element of all) {
      for (const attribute of element.attributes) {
        if (attribute.name.startsWith("data-")) {
          dataAttributes.push({
            tag: element.tagName.toLowerCase(),
            name: attribute.name,
            value: attribute.value,
          });
        }
        if (dataAttributes.length >= 100) {
          break;
        }
      }
      if (dataAttributes.length >= 100) {
        break;
      }
    }
    return {
      url: window.location.href,
      title: document.title,
      bodyTextStart: (document.body.innerText || "").slice(0, 5000),
      interestingAttributeElementCount: interestingElements.length,
      interestingAttributes: interestingElements.slice(0, 100).map((element) => ({
        tag: element.tagName.toLowerCase(),
        attributes: [...element.attributes]
          .filter((attribute) => /shadow|preview|card/i.test(`${attribute.name}=${attribute.value}`))
          .map((attribute) => [attribute.name, attribute.value]),
      })),
      dataAttributes,
      cardTableRows: document.querySelectorAll(".cards-risk-table tbody tr").length,
      cardTiles: document.querySelectorAll(".status-border-danger, .status-border-warning, .status-border-neutral").length,
      shadowPreviewHosts: document.querySelectorAll('[data-testid="anki-card-shadow-preview"], [data-shadow-preview="true"]').length,
      ankiPreviewSections: document.querySelectorAll(".asr-front-preview-html").length,
      images: document.querySelectorAll("img").length,
      audio: document.querySelectorAll("audio").length,
      buttons: document.querySelectorAll("button").length,
      hasFixtureText: (document.body.innerText || "").includes("要望") || document.documentElement.innerHTML.includes("要望"),
    };
  });
}

function relevantConsoleEvents() {
  return consoleEvents.filter((event) => ["error", "warning"].includes(event.type));
}

async function writeConsoleLog(fileName) {
  const lines = relevantConsoleEvents().map((event) => {
    const location = event.location?.url ? ` ${event.location.url}:${event.location.lineNumber || 0}` : "";
    return `[${event.type}]${location} ${event.text}`;
  });
  await fs.writeFile(path.join(artifacts, fileName), `${lines.join("\n")}\n`, "utf8");
}

async function writeJson(fileName, value) {
  await fs.writeFile(path.join(artifacts, fileName), JSON.stringify(redactArtifact(value), null, 2), "utf8");
}

async function saveBestEffort(action) {
  try {
    await action();
  } catch {
    // Failure artifacts should never hide the original browser smoke error.
  }
}

function redactArtifact(value) {
  if (typeof value === "string") {
    const tokenEscaped = ready.token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return value
      .replace(new RegExp(tokenEscaped, "g"), "<redacted-token>")
      .replace(/token=([^&"'<>\\\s]+)/gi, "token=<redacted>");
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactArtifact(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, redactArtifact(item)]));
  }
  return value;
}
