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
    shadowDetails.imgCount !== 2 ||
    shadowDetails.audioElementCount < 1 ||
    !shadowDetails.hasReplayButton ||
    shadowDetails.hasVisibleNativeAudioControls ||
    !shadowDetails.imagesLoaded ||
    shadowDetails.renderSource !== "anki_native" ||
    shadowDetails.hasRawAnkiPlayMarker ||
    shadowDetails.hasRawSoundMarker ||
    !shadowDetails.audioBeforeExample ||
    !shadowDetails.hasWordFocus ||
    !shadowDetails.hasMainWord ||
    !shadowDetails.hasCardContent ||
    !shadowDetails.wordFocusColorMatchesExpected ||
    shadowDetails.wordFocusColorIsOldBlue ||
    !shadowDetails.hasInlineColor
  ) {
    throw new Error(`Shadow DOM preview incomplete: ${JSON.stringify(shadowDetails)}`);
  }

  await fs.writeFile(path.join(artifacts, `cards-shadow-dom-dump-${label}.html`), redactArtifact(shadowDetails.html), "utf8");
  await capture(page, "table", "dark", `cards-table-dark-${label}.png`);
  await capture(page, "tiles", "dark", `cards-tile-${label}.png`);
  await capture(page, "ankiPreview", "dark", `cards-anki-preview-${label}.png`);
  const apkgDetails = await assertApkgBrowserIfEnabled(page);

  await writeJson(`browser-smoke-${label}.json`, {
    ok: true,
    consoleEvents: relevantConsoleEvents(),
    networkEvents,
    pageErrors,
    shadowDetails,
    apkg: apkgDetails,
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

async function assertApkgBrowserIfEnabled(page) {
  const importSummary = await readJsonIfExists(path.join(artifacts, "apkg-import-summary.json"));
  if (!importSummary.enabled) {
    const summary = {
      enabled: false,
      skipReason: importSummary.skipReason || "APKG fixture mode disabled.",
    };
    await writeJson(`browser-smoke-apkg-${label}.json`, { apkg: summary });
    return summary;
  }
  assertBrowser(importSummary.imported === true, "APKG import summary reports imported.");
  const problemSummary = await readJsonIfExists(path.join(artifacts, "apkg-problematic-summary.json"));
  assertBrowser(problemSummary.enabled === true, "APKG problematic summary enabled.");
  const report = await fetchReport();
  const apkgCards = findApkgCards(report, importSummary);
  const importedCardCount = Number(importSummary.cardCount || 0);
  assertBrowser(apkgCards.length >= Math.min(3, importedCardCount), "APKG cards are present in browser report data.");
  if (importedCardCount <= 100) {
    assertBrowser(apkgCards.length >= importedCardCount, "All imported APKG cards are visible in browser report data.");
  }
  const distinctNoteTypes = unique(apkgCards.map(cardNoteType).filter(Boolean));
  assertBrowser(distinctNoteTypes.length >= Math.min(3, (importSummary.noteTypeNames || []).length || 3), "APKG browser data has at least 3 note types.");
  assertRepresentativeApkgCards(apkgCards, importSummary);

  const deckName = (importSummary.deckNames || [])[0] || "asr-e2e-render-fixtures";
  await captureApkg(page, "table", "dark", `cards-apkg-table-dark-${label}.png`, deckName);
  const tableDetails = await inspectApkgShadowPreviews(page, "table");
  assertBrowser(tableDetails.hostCount >= Math.min(3, apkgCards.length), `APKG table previews found: ${tableDetails.hostCount}`);
  assertShadowSummary(tableDetails, "table");

  await captureApkg(page, "tiles", "dark", `cards-apkg-tile-${label}.png`, deckName);
  const tileDetails = await inspectApkgShadowPreviews(page, "tile");
  assertBrowser(tileDetails.hostCount >= Math.min(3, apkgCards.length), `APKG tile previews found: ${tileDetails.hostCount}`);
  assertShadowSummary(tileDetails, "tile");

  await captureApkg(page, "ankiPreview", "dark", `cards-apkg-anki-preview-${label}.png`, deckName);
  const previewDetails = await inspectApkgAnkiPreview(page);
  assertBrowser(previewDetails.previewCount >= Math.min(3, apkgCards.length), `APKG Anki previews found: ${previewDetails.previewCount}`);
  assertBrowser(!previewDetails.hasRawSoundMarker, "APKG Anki preview has no raw sound marker.");
  assertBrowser(!previewDetails.hasRawAnkiPlayMarker, "APKG Anki preview has no raw Anki AV marker.");
  assertBrowser(!previewDetails.hasScriptTag, "APKG Anki preview has no script tag.");
  assertBrowser(!previewDetails.hasExternalCdnLink, "APKG Anki preview has no external CDN link.");

  const summary = {
    enabled: true,
    cardCount: importedCardCount,
    attentionCardsFromApkg: apkgCards.length,
    distinctNoteTypes,
    deckName,
    tableDetails,
    tileDetails,
    previewDetails,
    representatives: summarizeRepresentatives(apkgCards),
  };
  await writeJson(`browser-smoke-apkg-${label}.json`, { apkg: summary });
  return summary;
}

async function captureApkg(page, mode, theme, fileName, deckName) {
  await prepareCardsPage(page, mode, theme);
  await applyDeckFilter(page, deckName);
  if (mode === "table" || mode === "tiles") {
    await waitForApkgShadowPreviews(page, mode === "tiles" ? "tile" : "table");
  } else {
    await waitForApkgAnkiPreview(page);
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

async function applyDeckFilter(page, deckName) {
  await page.evaluate((wantedDeck) => {
    const selects = [...document.querySelectorAll("select")];
    const deckSelect = selects.find((select) => [...select.options].some((option) => option.value === wantedDeck));
    if (!(deckSelect instanceof HTMLSelectElement)) {
      throw new Error(`Deck filter option not found: ${wantedDeck}`);
    }
    deckSelect.value = wantedDeck;
    deckSelect.dispatchEvent(new Event("change", { bubbles: true }));
  }, deckName);
  await page.waitForFunction(
    (wantedDeck) => document.body.innerText.includes(wantedDeck),
    deckName,
    { timeout: 15000 },
  );
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

async function waitForApkgShadowPreviews(page, mode) {
  await page.waitForFunction(
    ({ expectedMode }) => {
      const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"]')].filter(
        (host) => host.getAttribute("data-shadow-preview-mode") === expectedMode,
      );
      return hosts.some((host) => {
        const searchable = `${host.getAttribute("title") || ""}\n${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`;
        return /要望|遺伝子型|なくて|WebSocket|%E8%A6%81/.test(searchable);
      });
    },
    { expectedMode: mode },
    { timeout: 60000 },
  );
}

async function waitForApkgAnkiPreview(page) {
  await page.locator(".asr-front-preview-html").first().waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    () => /要望|遺伝子型|なくて|WebSocket|%E8%A6%81/.test(document.documentElement.innerHTML),
    undefined,
    { timeout: 60000 },
  );
}

async function inspectApkgShadowPreviews(page, mode) {
  return page.evaluate((expectedMode) => {
    const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"]')].filter(
      (host) => host.getAttribute("data-shadow-preview-mode") === expectedMode,
    );
    const details = hosts.map((host) => {
      const shadowRoot = host.shadowRoot;
      const html = shadowRoot?.innerHTML || "";
      const template = host.querySelector("template")?.innerHTML || "";
      const searchable = `${host.getAttribute("title") || ""}\n${template}\n${html}`;
      const images = [...(shadowRoot?.querySelectorAll("img") || [])].map((image) => {
        const rect = image.getBoundingClientRect();
        return {
          src: image.getAttribute("src") || "",
          complete: image.complete,
          naturalWidth: image.naturalWidth,
          naturalHeight: image.naturalHeight,
          renderedWidth: rect.width,
          renderedHeight: rect.height,
        };
      });
      const audioElements = [...(shadowRoot?.querySelectorAll("audio") || [])];
      const visibleNativeAudioControls = audioElements.some((audio) => {
        const rect = audio.getBoundingClientRect();
        return audio.hasAttribute("controls") && rect.width > 0 && rect.height > 0;
      });
      const wordFocus = shadowRoot?.querySelector(".word-focus");
      const grammarFocus = shadowRoot?.querySelector(".grammar-focus, .grammar-pattern, .main-grammar");
      return {
        title: host.getAttribute("title") || "",
        renderSource: host.getAttribute("data-render-source") || "",
        hasOpenShadowRoot: Boolean(shadowRoot),
        imgCount: shadowRoot?.querySelectorAll("img").length || 0,
        audioElementCount: audioElements.length,
        hasReplayButton: Boolean(shadowRoot?.querySelector(".asr-card-replay-button")),
        hasVisibleNativeAudioControls: visibleNativeAudioControls,
        imagesLoaded: images.every(
          (image) =>
            image.complete &&
            image.naturalWidth > 0 &&
            image.naturalHeight > 0 &&
            image.renderedWidth > 0 &&
            image.renderedHeight > 0,
        ),
        imageDetails: images,
        hasRawSoundMarker: searchable.toLowerCase().includes("[sound:"),
        hasRawAnkiPlayMarker: searchable.includes("[anki:play:"),
        hasScriptTag: Boolean(shadowRoot?.querySelector("script")) || /<script/i.test(template),
        hasExternalCdnLink: /cdnjs|<link\b/i.test(searchable),
        hasWordFocus: Boolean(wordFocus),
        hasGrammarFocus: Boolean(grammarFocus),
        wordFocusColor: wordFocus ? getComputedStyle(wordFocus).color : "",
        grammarFocusColor: grammarFocus ? getComputedStyle(grammarFocus).color : "",
        hasCardContent: Boolean(shadowRoot?.querySelector(".card-content")),
        hasMainWord: Boolean(shadowRoot?.querySelector(".main-word")),
        hasMainGrammar: Boolean(shadowRoot?.querySelector(".main-grammar")),
        textSample: (shadowRoot?.textContent || host.getAttribute("title") || "").slice(0, 300),
      };
    });
    const apkgDetails = details.filter((detail) => /要望|遺伝子型|なくて|WebSocket|要|遺/.test(detail.textSample) || detail.imgCount > 0 || detail.hasReplayButton);
    return {
      mode: expectedMode,
      hostCount: hosts.length,
      apkgLikeHostCount: apkgDetails.length,
      details: apkgDetails.length ? apkgDetails.slice(0, 12) : details.slice(0, 12),
      rawSoundMarkersFound: details.filter((detail) => detail.hasRawSoundMarker).length,
      rawAnkiPlayMarkersFound: details.filter((detail) => detail.hasRawAnkiPlayMarker).length,
      scriptTagsFound: details.filter((detail) => detail.hasScriptTag).length,
      externalCdnLinksFound: details.filter((detail) => detail.hasExternalCdnLink).length,
      replayButtonCount: details.filter((detail) => detail.hasReplayButton).length,
      mediaHostCount: details.filter((detail) => detail.imgCount > 0 || detail.audioElementCount > 0).length,
      wordFocusCount: details.filter((detail) => detail.hasWordFocus).length,
      grammarFocusCount: details.filter((detail) => detail.hasGrammarFocus).length,
    };
  }, mode);
}

async function inspectApkgAnkiPreview(page) {
  return page.evaluate(() => {
    const previews = [...document.querySelectorAll(".asr-front-preview-html")];
    const html = previews.map((preview) => preview.innerHTML).join("\n");
    return {
      previewCount: previews.length,
      imgCount: previews.reduce((sum, preview) => sum + preview.querySelectorAll("img").length, 0),
      audioElementCount: previews.reduce((sum, preview) => sum + preview.querySelectorAll("audio").length, 0),
      replayButtonCount: previews.reduce((sum, preview) => sum + preview.querySelectorAll(".asr-card-replay-button").length, 0),
      hasRawSoundMarker: html.toLowerCase().includes("[sound:"),
      hasRawAnkiPlayMarker: html.includes("[anki:play:"),
      hasScriptTag: /<script/i.test(html),
      hasExternalCdnLink: /cdnjs|<link\b/i.test(html),
      hasWordFocus: html.includes("word-focus"),
      hasGrammarFocus: /grammar-focus|grammar-pattern|main-grammar/.test(html),
      textSample: previews.map((preview) => preview.textContent || "").join("\n").slice(0, 500),
    };
  });
}

function assertShadowSummary(details, mode) {
  assertBrowser(details.rawSoundMarkersFound === 0, `APKG ${mode} previews have no raw sound markers.`);
  assertBrowser(details.rawAnkiPlayMarkersFound === 0, `APKG ${mode} previews have no raw Anki AV markers.`);
  assertBrowser(details.scriptTagsFound === 0, `APKG ${mode} previews have no script tags.`);
  assertBrowser(details.externalCdnLinksFound === 0, `APKG ${mode} previews have no external CDN refs.`);
  assertBrowser(details.details.every((detail) => detail.renderSource === "anki_native"), `APKG ${mode} previews use native render.`);
  assertBrowser(details.details.every((detail) => detail.hasOpenShadowRoot), `APKG ${mode} previews have open shadow roots.`);
  if (details.mediaHostCount > 0) {
    assertBrowser(details.details.filter((detail) => detail.imgCount > 0).every((detail) => detail.imagesLoaded), `APKG ${mode} images loaded.`);
  }
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
      const replayIndex = cardHtml.indexOf("asr-card-replay-button");
      const audioIndex = Math.max(cardHtml.indexOf("asr-card-audio"), cardHtml.indexOf("<audio"));
      const controlIndex = replayIndex >= 0 ? replayIndex : audioIndex;
      const exampleIndex = cardHtml.indexOf("word-focus");
      if (!searchable.includes("要望") && !searchable.includes("%E8%A6%81")) {
        continue;
      }
      const imageDetails = [...(shadowRoot?.querySelectorAll("img") || [])].map((image) => {
        const rect = image.getBoundingClientRect();
        return {
          src: image.getAttribute("src") || "",
          complete: image.complete,
          naturalWidth: image.naturalWidth,
          naturalHeight: image.naturalHeight,
          renderedWidth: rect.width,
          renderedHeight: rect.height,
        };
      });
      const audioElements = [...(shadowRoot?.querySelectorAll("audio") || [])];
      const hasVisibleNativeAudioControls = audioElements.some((audio) => {
        const rect = audio.getBoundingClientRect();
        return audio.hasAttribute("controls") && rect.width > 0 && rect.height > 0;
      });
      const normalizeRgb = (value) => {
        const match = String(value || "").match(/rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/i);
        return match ? `rgb(${Number(match[1])}, ${Number(match[2])}, ${Number(match[3])})` : String(value || "").trim().toLowerCase();
      };
      const wordFocus = shadowRoot?.querySelector(".word-focus");
      const wordFocusColor = wordFocus ? getComputedStyle(wordFocus).color : "";
      const normalizedWordFocusColor = normalizeRgb(wordFocusColor);
      const imagesLoaded =
        imageDetails.length === 2 &&
        imageDetails.every(
          (image) =>
            image.complete &&
            image.naturalWidth > 20 &&
            image.naturalHeight > 20 &&
            image.renderedWidth > 20 &&
            image.renderedHeight > 20,
        );
      return {
        exists: true,
        mode: host.getAttribute("data-shadow-preview-mode") || "",
        renderSource: host.getAttribute("data-render-source") || "",
        hasOpenShadowRoot: Boolean(shadowRoot),
        hasStyle: Boolean(shadowRoot?.querySelector("style")),
        hasCard: Boolean(shadowRoot?.querySelector(".card")),
        imgCount: shadowRoot?.querySelectorAll("img").length || 0,
        audioCount: audioElements.length,
        audioElementCount: audioElements.length,
        hasReplayButton: Boolean(shadowRoot?.querySelector(".asr-card-replay-button")),
        hasVisibleNativeAudioControls,
        imagesLoaded,
        imageDetails,
        hasWordFocus: Boolean(shadowRoot?.querySelector(".word-focus")),
        hasMainWord: Boolean(shadowRoot?.querySelector(".main-word")),
        hasCardContent: Boolean(shadowRoot?.querySelector(".card-content")),
        hasInlineColor: Boolean(shadowRoot?.querySelector('[style*="color"]')),
        wordFocusColor,
        normalizedWordFocusColor,
        wordFocusColorMatchesExpected: normalizedWordFocusColor === "rgb(255, 170, 0)",
        wordFocusColorIsOldBlue: normalizedWordFocusColor === "rgb(37, 99, 235)",
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
      audioElementCount: 0,
      hasReplayButton: false,
      hasVisibleNativeAudioControls: false,
      imagesLoaded: false,
      imageDetails: [],
      hasWordFocus: false,
      hasMainWord: false,
      hasCardContent: false,
      hasInlineColor: false,
      wordFocusColor: "",
      normalizedWordFocusColor: "",
      wordFocusColorMatchesExpected: false,
      wordFocusColorIsOldBlue: false,
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

async function fetchReport() {
  const response = await fetch(`${ready.baseUrl}/api/report?token=${encodeURIComponent(ready.token)}`);
  if (!response.ok) {
    throw new Error(`/api/report returned ${response.status}`);
  }
  return response.json();
}

function findApkgCards(report, importSummary) {
  const cards = Array.isArray(report?.attentionCards)
    ? report.attentionCards
    : Array.isArray(report?.cards)
      ? report.cards
      : [];
  const deckNames = new Set((importSummary.deckNames || []).map(String));
  const noteTypeNames = new Set((importSummary.noteTypeNames || []).map(String));
  const cardIds = new Set((importSummary.cardIds || []).map((value) => Number(value)).filter(Number.isFinite));
  return cards.filter((card) => {
    const cardId = Number(card?.cardId || card?.card_id || 0);
    return (
      cardIds.has(cardId) ||
      deckNames.has(String(card?.deckName || card?.deck_name || "")) ||
      noteTypeNames.has(cardNoteType(card))
    );
  });
}

function cardNoteType(card) {
  return String(card?.preview?.noteTypeName || card?.preview?.note_type_name || card?.noteTypeName || card?.note_type_name || "");
}

function assertRepresentativeApkgCards(cards, importSummary) {
  const renderedDumps = cards.map((card) => JSON.stringify(card?.renderedPreview || {}, null, 0)).join("\n");
  const textDump = cards.map((card) => JSON.stringify(card, null, 0)).join("\n");
  const noteTypes = new Set(cards.map(cardNoteType));
  for (const expected of ["Основная", "Грамматика", "Слова", "Копия Грамматика"]) {
    if ((importSummary.noteTypeNames || []).includes(expected)) {
      assertBrowser(noteTypes.has(expected), `APKG browser card represented note type: ${expected}`);
    }
  }
  assertBrowser(cards.every((card) => card?.renderedPreview?.renderSource === "anki_native"), "APKG browser cards use native render.");
  assertBrowser(cards.every((card) => !card?.renderedPreview?.fallbackReason), "APKG browser cards have no fallback reason.");
  assertBrowser(!renderedDumps.toLowerCase().includes("[sound:"), "APKG browser rendered data has no raw sound markers.");
  assertBrowser(!renderedDumps.includes("[anki:play:"), "APKG browser rendered data has no raw Anki AV markers.");
  assertBrowser(!/<script/i.test(renderedDumps), "APKG browser rendered data has no script tag.");
  assertBrowser(!/cdnjs|<link\b/i.test(renderedDumps), "APKG browser rendered data has no external CDN refs.");
  if (textDump.includes("要望")) {
    assertBrowser(renderedDumps.includes("word-focus"), "APKG 要望 card preserves word-focus class.");
    assertBrowser(renderedDumps.includes("asr-card-replay-button"), "APKG 要望 card has replay button.");
  }
  if (textDump.includes("遺伝子型")) {
    assertBrowser(renderedDumps.includes("asr-card-replay-button"), "APKG 遺伝子型 card has replay button.");
  }
  if (textDump.includes("なくて")) {
    assertBrowser(/grammar-focus|grammar-pattern|main-grammar/.test(renderedDumps), "APKG なくて card preserves grammar classes.");
  }
  if (textDump.includes("WebSocket")) {
    assertBrowser(/<b>|font-weight|span/i.test(renderedDumps), "APKG WebSocket card preserves safe static HTML.");
  }
}

function summarizeRepresentatives(cards) {
  const result = {};
  for (const [key, pattern] of Object.entries({
    youbou: /要望/,
    idenshigata: /遺伝子型/,
    nakute: /なくて/,
    websocket: /WebSocket/i,
  })) {
    const card = cards.find((item) => pattern.test(JSON.stringify(item)));
    if (card) {
      result[key] = {
        cardId: card.cardId,
        noteTypeName: cardNoteType(card),
        cardTemplateName: card.preview?.cardTemplateName || "",
        renderSource: card.renderedPreview?.renderSource || "",
        mediaRefs: (card.renderedPreview?.mediaRefs || []).map((item) => item.name),
      };
    }
  }
  return result;
}

function unique(values) {
  return [...new Set(values)];
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") {
      return {};
    }
    throw error;
  }
}

function assertBrowser(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
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
