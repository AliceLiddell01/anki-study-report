#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { ensureArtifactParent, relativeArtifactPath, resolveArtifactPaths } from "./artifact-paths.mjs";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const value = process.argv[index];
  if (value.startsWith("--")) {
    args.set(value.slice(2), process.argv[index + 1] && !process.argv[index + 1].startsWith("--") ? process.argv[++index] : "1");
  }
}

const label = args.get("label") || "run";
const artifacts = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts";
const artifactPaths = resolveArtifactPaths(artifacts);
const readyFile = process.env.ANKI_STUDY_REPORT_E2E_READY_FILE || path.join(artifactPaths.runtime, "dashboard-ready.json");
const ready = JSON.parse(await fs.readFile(readyFile, "utf8"));
const cardsUrl = `${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/cards`;
const baseViewport = { name: "desktop-1440", width: 1440, height: 1000 };
const responsiveViewports = [
  baseViewport,
  { name: "narrow-1280", width: 1280, height: 900 },
];
const dashboardPageCases = [
  { route: "/home", pageName: "today", heading: "Сегодня", primaryHref: "#/home" },
  { route: "/calendar", pageName: "calendar", heading: "Календарь", primaryHref: "#/calendar" },
  { route: "/decks", pageName: "decks", heading: "Колоды", primaryHref: "#/decks" },
  { route: "/profile", pageName: "profile", heading: "E2E" },
  { route: "/actions", pageName: "tools", heading: "Инструменты" },
  { route: "/settings", pageName: "settings/report", heading: "Отчёт", settingsHref: "#/settings" },
  { route: "/settings/data", pageName: "settings/data", heading: "Данные", settingsHref: "#/settings/data" },
  { route: "/settings/server", pageName: "settings/server", heading: "Сервер", settingsHref: "#/settings/server" },
  { route: "/settings/sources", pageName: "settings/sources", heading: "Источники данных", settingsHref: "#/settings/sources" },
  { route: "/settings/logs", pageName: "settings/logs", heading: "Логи", settingsHref: "#/settings/logs" },
];
const consoleEvents = [];
const networkEvents = [];
const pageErrors = [];
const assetResponses = [];

const browser = await chromium.launch({ headless: true });
let page;
try {
  await deleteStaleFailureArtifacts();
  page = await browser.newPage({ viewport: { width: baseViewport.width, height: baseViewport.height }, deviceScaleFactor: 1 });
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
    if (/\/assets\/.*\.(css|js)(?:[?#]|$)/.test(response.url())) {
      assetResponses.push({
        status: response.status(),
        url: response.url(),
        contentType: response.headers()["content-type"] || "",
      });
    }
    if (response.status() >= 400) {
      networkEvents.push({
        kind: "response",
        status: response.status(),
        url: response.url(),
      });
    }
  });

  const visualStates = [];
  const perf100Enabled = await isPerformance100Enabled();
  const tableLightScreenshot = artifactPaths.cardsScreenshot("synthetic", "table", "light");
  await capture(page, "table", "light", tableLightScreenshot);
  const shadowDetails = await inspectShadowPreview(page, "table");
  if (!shadowDetails.exists) {
    throw new Error("Shadow DOM preview host for fixture card was not found.");
  }
  const strictSyntheticFixtureIncomplete =
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
    !shadowDetails.hasInlineColor;
  if (!perf100Enabled && strictSyntheticFixtureIncomplete) {
    throw new Error(`Shadow DOM preview incomplete: ${JSON.stringify(shadowDetails)}`);
  }
  if (perf100Enabled) {
    assertBrowser(shadowDetails.hasOpenShadowRoot, "Perf100 table preview has an open shadow root.");
    assertBrowser(shadowDetails.hasCard, "Perf100 table preview has a rendered card.");
    assertBrowser(shadowDetails.renderSource === "anki_native", "Perf100 table preview uses native render.");
    assertBrowser(!shadowDetails.hasRawAnkiPlayMarker && !shadowDetails.hasRawSoundMarker, "Perf100 table preview has no raw media markers.");
  }
  assertFrontOnlyMode(shadowDetails, "table");
  visualStates.push({ mode: "table", theme: "light", screenshot: relativeArtifactPath(artifactPaths, tableLightScreenshot), details: shadowDetails });

  const shadowDumpPath = artifactPaths.htmlFile("cards", `synthetic-shadow-dom-${label}.html`);
  await ensureArtifactParent(shadowDumpPath);
  await fs.writeFile(shadowDumpPath, redactArtifact(shadowDetails.html), "utf8");
  const tableDarkScreenshot = artifactPaths.cardsScreenshot("synthetic", "table", "dark");
  await capture(page, "table", "dark", tableDarkScreenshot);
  const tableDarkDetails = await inspectShadowPreview(page, "table");
  assertFrontOnlyMode(tableDarkDetails, "table");
  visualStates.push({ mode: "table", theme: "dark", screenshot: relativeArtifactPath(artifactPaths, tableDarkScreenshot), details: tableDarkDetails });

  const tilesLightScreenshot = artifactPaths.cardsScreenshot("synthetic", "tiles", "light");
  await capture(page, "tiles", "light", tilesLightScreenshot);
  const tilesLightDetails = await inspectShadowPreview(page, "tile");
  assertFrontOnlyMode(tilesLightDetails, "tile");
  visualStates.push({ mode: "tiles", theme: "light", screenshot: relativeArtifactPath(artifactPaths, tilesLightScreenshot), details: tilesLightDetails });

  const tilesDarkScreenshot = artifactPaths.cardsScreenshot("synthetic", "tiles", "dark");
  await capture(page, "tiles", "dark", tilesDarkScreenshot);
  const tilesDarkDetails = await inspectShadowPreview(page, "tile");
  assertFrontOnlyMode(tilesDarkDetails, "tile");
  visualStates.push({ mode: "tiles", theme: "dark", screenshot: relativeArtifactPath(artifactPaths, tilesDarkScreenshot), details: tilesDarkDetails });

  const previewLightScreenshot = artifactPaths.cardsScreenshot("synthetic", "ankiPreview", "light");
  await capture(page, "ankiPreview", "light", previewLightScreenshot);
  const ankiPreviewLightDetails = await inspectAnkiPreview(page);
  assertAnkiPreviewAnswerOnly(ankiPreviewLightDetails, "light");
  visualStates.push({ mode: "ankiPreview", theme: "light", screenshot: relativeArtifactPath(artifactPaths, previewLightScreenshot), details: ankiPreviewLightDetails });

  const previewDarkScreenshot = artifactPaths.cardsScreenshot("synthetic", "ankiPreview", "dark");
  await capture(page, "ankiPreview", "dark", previewDarkScreenshot);
  const ankiPreviewDarkDetails = await inspectAnkiPreview(page);
  assertAnkiPreviewAnswerOnly(ankiPreviewDarkDetails, "dark");
  visualStates.push({ mode: "ankiPreview", theme: "dark", screenshot: relativeArtifactPath(artifactPaths, previewDarkScreenshot), details: ankiPreviewDarkDetails });

  const apkgDetails = await assertApkgBrowserIfEnabled(page);
  const profileDetails = await assertProfileMvp(page);
  const pageScreenshots = await captureDashboardPages(page);
  const navigationScreenshots = await captureAvatarMenu(page);
  const cssDiagnostics = await assertCssDiagnostics(page);

  await writeJson(`browser-smoke-${label}.json`, {
    ok: true,
    consoleEvents: relevantConsoleEvents(),
    networkEvents,
    pageErrors,
    shadowDetails,
    visualStates,
    cssDiagnostics,
    apkg: apkgDetails,
    profile: profileDetails,
    pageScreenshots,
    navigationScreenshots,
  });

  if (pageErrors.length > 0) {
    throw new Error(`Browser page errors: ${pageErrors.join("\n")}`);
  }
  console.log(`Browser smoke passed for ${ready.baseUrl}`);
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

async function capture(page, mode, theme, filePath) {
  await prepareCardsPage(page, mode, theme);
  if (mode === "table" || mode === "tiles") {
    await waitForShadowFixture(page, mode === "tiles" ? "tile" : "table");
  } else {
    await waitForAnkiPreview(page);
  }
  await waitForLayoutStabilization(page);
  await ensureArtifactParent(filePath);
  await page.screenshot({ path: filePath, fullPage: true });
}

async function captureDashboardPages(page) {
  const screenshots = [];
  for (const theme of ["light", "dark"]) {
    for (const pageCase of dashboardPageCases) {
      await prepareDashboardRoute(page, pageCase.route, theme, pageCase.heading);
      await waitForLayoutStabilization(page);
      const activeState = await inspectActiveNavigation(page);
      assertBrowser(
        activeState.primaryHref === (pageCase.primaryHref || null),
        `${pageCase.route} ${theme} primary active state is correct: ${activeState.primaryHref}`,
      );
      assertBrowser(
        activeState.settingsHref === (pageCase.settingsHref || null),
        `${pageCase.route} ${theme} settings active state is correct: ${activeState.settingsHref}`,
      );
      const filePath = artifactPaths.pageScreenshot(pageCase.pageName, theme);
      await ensureArtifactParent(filePath);
      await page.screenshot({ path: filePath, fullPage: true });
      screenshots.push({
        route: `#${pageCase.route}`,
        page: pageCase.pageName,
        theme,
        screenshot: relativeArtifactPath(artifactPaths, filePath),
        activeState,
      });
    }
  }
  return screenshots;
}

async function assertProfileMvp(page) {
  await prepareDashboardRoute(page, "/profile", "light", "E2E");
  await page.getByTestId("profile-hero").waitFor({ state: "visible", timeout: 15000 });
  await page.getByTestId("profile-banner").waitFor({ state: "visible", timeout: 15000 });
  await page.getByTestId("profile-avatar").waitFor({ state: "visible", timeout: 15000 });
  for (const label of ["Всего повторений", "Активных дней", "Текущая серия", "Лучшая серия", "Время учёбы", "Средняя успешность"]) {
    await page.getByText(label, { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  }
  const heatmapVisible = await page.getByTestId("profile-heatmap").isVisible().catch(() => false);
  const heatmapEmptyVisible = await page.getByText("История активности появится после первых повторений.", { exact: true }).isVisible().catch(() => false);
  assertBrowser(heatmapVisible || heatmapEmptyVisible, "Profile activity heatmap or explicit empty state is visible.");
  await page.getByRole("heading", { name: "Последние занятия", exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await page.getByRole("heading", { name: "Колоды", exact: true }).waitFor({ state: "visible", timeout: 15000 });

  const sort = page.locator("#profile-deck-sort");
  await sort.selectOption("reviews");
  await page.getByText("Порядок колод сохранён.", { exact: true }).waitFor({ state: "attached", timeout: 15000 });

  await page.getByRole("button", { name: "Изменить дату начала", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Дата начала обучения", exact: true });
  await dialog.waitFor({ state: "visible", timeout: 15000 });
  await dialog.locator("#profile-study-start").fill("2020-01-01");
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  await dialog.waitFor({ state: "hidden", timeout: 15000 });

  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "E2E", exact: true }).waitFor({ timeout: 60000 });
  const persistedSort = await page.locator("#profile-deck-sort").inputValue();
  const profileApi = await page.evaluate(async () => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const response = await fetch(`/api/profile?token=${encodeURIComponent(token)}`, { cache: "no-store" });
    return { status: response.status, body: await response.json() };
  });
  assertBrowser(profileApi.status === 200 && profileApi.body?.ok === true, "Profile API remains available after reload.");
  assertBrowser(persistedSort === "reviews", `Profile deck sort persists after reload: ${persistedSort}`);
  assertBrowser(profileApi.body?.profile?.preferences?.customStudyStartedOn === "2020-01-01", "Profile study start persists after reload.");
  assertBrowser(profileApi.body?.profile?.studyHistory?.statsAvailableFrom !== "2020-01-01", "Profile override does not fabricate stats availability.");
  const domText = await page.locator("body").innerText();
  assertBrowser(!domText.includes(ready.token), "Profile DOM does not expose the dashboard token.");
  return {
    identity: profileApi.body?.profile?.identity?.displayName || null,
    persistedSort,
    persistedStudyStart: profileApi.body?.profile?.preferences?.customStudyStartedOn || null,
    statsAvailableFrom: profileApi.body?.profile?.studyHistory?.statsAvailableFrom || null,
    heatmapVisible,
    heatmapEmptyVisible,
  };
}

async function captureAvatarMenu(page) {
  const screenshots = [];
  for (const theme of ["light", "dark"]) {
    await prepareDashboardRoute(page, "/home", theme, "Сегодня");
    const trigger = page.getByRole("button", { name: "Открыть меню профиля", exact: true });
    await trigger.click();
    const menu = page.getByRole("menu", { name: "Меню профиля", exact: true });
    await menu.waitFor({ state: "visible", timeout: 15000 });
    const support = menu.getByRole("menuitem", { name: "Поддержать проект", exact: true });
    await support.waitFor({ state: "visible", timeout: 15000 });
    const linkContract = await support.evaluate((element) => ({
      href: element.getAttribute("href"),
      target: element.getAttribute("target"),
      rel: element.getAttribute("rel"),
      referrerPolicy: element.getAttribute("referrerpolicy"),
    }));
    assertBrowser(linkContract.href === "https://boosty.to/ankistudyreport", "Boosty support URL is exact.");
    assertBrowser(linkContract.target === "_blank", "Boosty support link opens a new tab.");
    assertBrowser(String(linkContract.rel || "").split(/\s+/).includes("noopener"), "Boosty support link uses noopener.");
    assertBrowser(String(linkContract.rel || "").split(/\s+/).includes("noreferrer"), "Boosty support link uses noreferrer.");
    assertBrowser(linkContract.referrerPolicy === "no-referrer", "Boosty support link uses no-referrer policy.");
    const menuItems = await menu.getByRole("menuitem").allTextContents();
    assertBrowser(
      JSON.stringify(menuItems.map((item) => item.trim())) === JSON.stringify(["Профиль", "Настройки", "Инструменты", "Поддержать проект"]),
      `Avatar menu items are complete: ${menuItems.join(", ")}`,
    );
    await waitForLayoutStabilization(page);
    const filePath = artifactPaths.navigationScreenshot(theme);
    await ensureArtifactParent(filePath);
    await page.screenshot({ path: filePath, fullPage: false });
    screenshots.push({
      route: "#/home",
      theme,
      screenshot: relativeArtifactPath(artifactPaths, filePath),
      items: menuItems.map((item) => item.trim()),
      support: linkContract,
    });
  }
  return screenshots;
}

async function inspectActiveNavigation(page) {
  return page.evaluate(() => ({
    primaryHref:
      document.querySelector('nav[aria-label="Основная навигация"] [aria-current="page"]')?.getAttribute("href") || null,
    settingsHref:
      document.querySelector('nav[aria-label="Настройки"] [aria-current="page"]')?.getAttribute("href") || null,
  }));
}

async function assertApkgBrowserIfEnabled(page) {
  const importSummary = await readJsonIfExists(path.join(artifactPaths.reports, "apkg-import-summary.json"));
  if (!importSummary.enabled) {
    const summary = {
      enabled: false,
      skipReason: importSummary.skipReason || "APKG fixture mode disabled.",
    };
    await writeJson(`browser-smoke-apkg-${label}.json`, { apkg: summary });
    return summary;
  }
  assertBrowser(importSummary.imported === true, "APKG import summary reports imported.");
  const problemSummary = await readJsonIfExists(path.join(artifactPaths.reports, "apkg-problematic-summary.json"));
  assertBrowser(problemSummary.enabled === true, "APKG problematic summary enabled.");
  const report = await fetchReport();
  const apkgCards = findApkgCards(report, importSummary);
  const importedCardCount = Number(importSummary.cardCount || 0);
  const importedNoteCount = Number(importSummary.noteCount || 0);
  const importedNoteTypeCount = (importSummary.noteTypeNames || []).length;
  const importedMediaFileCount = (importSummary.mediaFilesFound || []).length;
  assertBrowser(importedNoteCount === 10, `APKG fixture imported 10 notes: ${importedNoteCount}`);
  assertBrowser(importedCardCount === 10, `APKG fixture imported 10 cards: ${importedCardCount}`);
  assertBrowser(importedNoteTypeCount === 4, `APKG fixture imported 4 note types: ${importedNoteTypeCount}`);
  assertBrowser(importedMediaFileCount === 13, `APKG fixture imported 13 media files: ${importedMediaFileCount}`);
  assertBrowser(apkgCards.length >= Math.min(3, importedCardCount), "APKG cards are present in browser report data.");
  if (importedCardCount <= 100) {
    assertBrowser(apkgCards.length >= importedCardCount, "All imported APKG cards are visible in browser report data.");
  }
  const distinctNoteTypes = unique(apkgCards.map(cardNoteType).filter(Boolean));
  assertBrowser(distinctNoteTypes.length >= Math.min(3, (importSummary.noteTypeNames || []).length || 3), "APKG browser data has at least 3 note types.");
  assertRepresentativeApkgCards(apkgCards, importSummary);
  const renderSourceNativeCount = apkgCards.filter((card) => card?.renderedPreview?.renderSource === "anki_native").length;
  assertBrowser(renderSourceNativeCount >= importedCardCount, `APKG browser cards use native render source: ${renderSourceNativeCount}`);

  const deckName = (importSummary.deckNames || [])[0] || "asr-e2e-render-fixtures";
  await captureApkg(page, "table", "light", artifactPaths.cardsScreenshot("apkg", "table", "light"), deckName);
  const tableLightDetails = await inspectApkgShadowPreviews(page, "table");
  const tableLightLayout = await inspectTableLayout(page);
  assertBrowser(tableLightDetails.hostCount >= Math.min(3, apkgCards.length), `APKG light table previews found: ${tableLightDetails.hostCount}`);
  assertShadowSummary(tableLightDetails, "table light");
  assertTableLayoutSummary(tableLightLayout, "APKG light table");

  await captureApkg(page, "table", "dark", artifactPaths.cardsScreenshot("apkg", "table", "dark"), deckName);
  const tableDetails = await inspectApkgShadowPreviews(page, "table");
  const tableLayout = await inspectTableLayout(page);
  assertBrowser(tableDetails.hostCount >= Math.min(3, apkgCards.length), `APKG table previews found: ${tableDetails.hostCount}`);
  assertShadowSummary(tableDetails, "table");
  assertTableLayoutSummary(tableLayout, "APKG dark table");

  await captureApkg(page, "tiles", "light", artifactPaths.cardsScreenshot("apkg", "tiles", "light"), deckName);
  const tileLightDetails = await inspectApkgShadowPreviews(page, "tile");
  const tileLightLayout = await inspectTileLayout(page);
  assertBrowser(tileLightDetails.hostCount >= Math.min(3, apkgCards.length), `APKG light tile previews found: ${tileLightDetails.hostCount}`);
  assertShadowSummary(tileLightDetails, "tile light");
  assertTileLayoutSummary(tileLightLayout, "APKG light tiles");

  await captureApkg(page, "tiles", "dark", artifactPaths.cardsScreenshot("apkg", "tiles", "dark"), deckName);
  const tileDetails = await inspectApkgShadowPreviews(page, "tile");
  const tileLayout = await inspectTileLayout(page);
  assertBrowser(tileDetails.hostCount >= Math.min(3, apkgCards.length), `APKG tile previews found: ${tileDetails.hostCount}`);
  assertShadowSummary(tileDetails, "tile");
  assertTileLayoutSummary(tileLayout, "APKG dark tiles");

  await captureApkg(page, "ankiPreview", "light", artifactPaths.cardsScreenshot("apkg", "ankiPreview", "light"), deckName);
  const previewLightDetails = await inspectApkgAnkiPreview(page);
  assertBrowser(previewLightDetails.previewCount >= Math.min(3, apkgCards.length), `APKG light Anki answer previews found: ${previewLightDetails.previewCount}`);
  assertBrowser(previewLightDetails.frontHostCount === 0, "APKG light Anki preview has no separate front preview host.");
  assertBrowser(previewLightDetails.unmeasuredHostCount === 0, "APKG light Anki preview answer hosts completed adaptive measurement.");
  assertBrowser(previewLightDetails.clippedHostCount === 0, "APKG light Anki preview answer hosts are not clipped at the bottom.");
  assertBrowser(!previewLightDetails.hasRawSoundMarker, "APKG light Anki preview has no raw sound marker.");
  assertBrowser(!previewLightDetails.hasRawAnkiPlayMarker, "APKG light Anki preview has no raw Anki AV marker.");
  assertBrowser(!previewLightDetails.hasScriptTag, "APKG light Anki preview has no script tag.");
  assertBrowser(!previewLightDetails.hasExternalCdnLink, "APKG light Anki preview has no external CDN link.");

  await captureApkg(page, "ankiPreview", "dark", artifactPaths.cardsScreenshot("apkg", "ankiPreview", "dark"), deckName);
  const previewDetails = await inspectApkgAnkiPreview(page);
  assertBrowser(previewDetails.previewCount >= Math.min(3, apkgCards.length), `APKG Anki answer previews found: ${previewDetails.previewCount}`);
  assertBrowser(previewDetails.frontHostCount === 0, "APKG Anki preview has no separate front preview host.");
  assertBrowser(previewDetails.unmeasuredHostCount === 0, "APKG Anki preview answer hosts completed adaptive measurement.");
  assertBrowser(previewDetails.clippedHostCount === 0, "APKG Anki preview answer hosts are not clipped at the bottom.");
  assertBrowser(!previewDetails.hasRawSoundMarker, "APKG Anki preview has no raw sound marker.");
  assertBrowser(!previewDetails.hasRawAnkiPlayMarker, "APKG Anki preview has no raw Anki AV marker.");
  assertBrowser(!previewDetails.hasScriptTag, "APKG Anki preview has no script tag.");
  assertBrowser(!previewDetails.hasExternalCdnLink, "APKG Anki preview has no external CDN link.");
  const documentNoteCssLeak = await inspectDocumentNoteCssLeak(page);
  assertBrowser(documentNoteCssLeak.count === 0, "APKG note CSS did not leak into document-level style tags.");
  const responsiveLayouts = await inspectApkgResponsiveLayouts(page, deckName);
  const performance100 = await inspectCardsPerformance100IfEnabled(page, report, importSummary, problemSummary, deckName);

  const summary = {
    enabled: true,
    fixturePath: "docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg",
    noteCount: importedNoteCount,
    cardCount: importedCardCount,
    noteTypeCount: importedNoteTypeCount,
    mediaFileCount: importedMediaFileCount,
    renderSourceNativeCount,
    attentionCardsFromApkg: apkgCards.length,
    distinctNoteTypes,
    deckName,
    viewport: baseViewport,
    tableLightDetails,
    tableLightLayout,
    tableDetails,
    tableLayout,
    tileLightDetails,
    tileDetails,
    tileLightLayout,
    tileLayout,
    previewLightDetails,
    previewDetails,
    responsiveLayouts,
    performance100,
    modes: {
      table: {
        light: tableLightLayout,
        dark: tableLayout,
      },
      tiles: {
        light: tileLightLayout,
        dark: tileLayout,
      },
      ankiPreview: {
        light: {
          answerPreviewBottomClippedCount: previewLightDetails.clippedHostCount,
          frontDuplicateSectionCount: previewLightDetails.frontHostCount,
          unmeasuredHostCount: previewLightDetails.unmeasuredHostCount,
          clippedHostCount: previewLightDetails.clippedHostCount,
        },
        dark: {
          answerPreviewBottomClippedCount: previewDetails.clippedHostCount,
          frontDuplicateSectionCount: previewDetails.frontHostCount,
          unmeasuredHostCount: previewDetails.unmeasuredHostCount,
          clippedHostCount: previewDetails.clippedHostCount,
        },
      },
    },
    media: {
      rawSoundMarkerCount:
        tableLightDetails.rawSoundMarkersFound + tableDetails.rawSoundMarkersFound + tileLightDetails.rawSoundMarkersFound + tileDetails.rawSoundMarkersFound,
      rawAnkiPlayMarkerCount:
        tableLightDetails.rawAnkiPlayMarkersFound +
        tableDetails.rawAnkiPlayMarkersFound +
        tileLightDetails.rawAnkiPlayMarkersFound +
        tileDetails.rawAnkiPlayMarkersFound,
    },
    documentNoteCssLeak,
    representatives: summarizeRepresentatives(apkgCards),
  };
  await writeJson(`browser-smoke-apkg-${label}.json`, { apkg: summary });
  return summary;
}

async function assertCssDiagnostics(page) {
  const diagnostics = {};

  await prepareDashboardRoute(page, "/cards", "light", "Карточки");
  await waitForCardsPageReady(page);
  diagnostics.cardsLight = await inspectDashboardCss(page, "cards-light");
  assertDashboardCss(diagnostics.cardsLight, { theme: "light", page: "Cards" });

  await prepareDashboardRoute(page, "/settings/server", "light", "Сервер");
  diagnostics.settingsLight = await inspectDashboardCss(page, "settings-light");
  assertDashboardCss(diagnostics.settingsLight, { theme: "light", page: "Settings" });

  await prepareDashboardRoute(page, "/settings/server", "dark", "Сервер");
  diagnostics.settingsDark = await inspectDashboardCss(page, "settings-dark");
  assertDashboardCss(diagnostics.settingsDark, { theme: "dark", page: "Settings" });

  await prepareDashboardRoute(page, "/cards", "light", "Карточки");
  await waitForCardsPageReady(page);
  diagnostics.cardsAfterSettingsLight = await inspectDashboardCss(page, "cards-after-settings-light");
  assertDashboardCss(diagnostics.cardsAfterSettingsLight, { theme: "light", page: "Cards after Settings" });

  await writeJson(`browser-css-diagnostics-${label}.json`, diagnostics);
  return diagnostics;
}

async function prepareDashboardRoute(page, route, theme, headingName) {
  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#${route}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.evaluate((selectedTheme) => {
    window.localStorage.setItem("anki-study-report-theme", selectedTheme);
    document.documentElement.dataset.theme = selectedTheme;
    document.documentElement.style.colorScheme = selectedTheme;
  }, theme);
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: headingName, exact: true }).waitFor({ timeout: 60000 });
}

async function inspectDashboardCss(page, pageName) {
  const assetResponseSnapshot = [...assetResponses];
  return page.evaluate(
    ({ currentPageName, responses }) => {
      const noteCssMarkers = [".word-focus", ".main-word", ".main-grammar", ".meaning-box"];
      const linkedStylesheets = [...document.querySelectorAll('link[rel~="stylesheet"]')].map((link) => {
        let ruleCount = 0;
        let readable = false;
        try {
          ruleCount = link.sheet?.cssRules?.length || 0;
          readable = Boolean(link.sheet);
        } catch {
          readable = false;
        }
        const response = responses.find((item) => stripQuery(item.url) === stripQuery(link.href));
        return {
          href: link.href,
          loaded: Boolean(link.sheet),
          readable,
          ruleCount,
          status: response?.status || null,
          contentType: response?.contentType || "",
        };
      });
      const loadedStylesheets = [...document.styleSheets].map((sheet) => {
        let ruleCount = 0;
        let readable = false;
        try {
          ruleCount = sheet.cssRules?.length || 0;
          readable = true;
        } catch {
          readable = false;
        }
        const href = sheet.href || "";
        const response = responses.find((item) => href && stripQuery(item.url) === stripQuery(href));
        return {
          href,
          readable,
          ruleCount,
          status: response?.status || null,
          contentType: response?.contentType || "",
        };
      });
      const styleTagsWithNoteMarkers = [...document.querySelectorAll("style")]
        .map((style, index) => ({ index, text: style.textContent || "" }))
        .filter((style) => noteCssMarkers.some((marker) => style.text.includes(marker)))
        .map((style) => ({
          index: style.index,
          markers: noteCssMarkers.filter((marker) => style.text.includes(marker)),
          excerpt: style.text.slice(0, 500),
        }));
      const appRoot = document.querySelector("#root > div") || document.querySelector("#root") || document.body;
      const main = document.querySelector("main") || appRoot;
      const pageRoot = document.querySelector("main > div") || main;
      return {
        pageName: currentPageName,
        url: window.location.href,
        loadedStylesheets,
        linkedStylesheets,
        documentThemeAttribute: document.documentElement.getAttribute("data-theme") || "",
        bodyClassName: document.body.className || "",
        rootClassName: document.documentElement.className || "",
        appRoot: computedSnapshot(appRoot),
        main: computedSnapshot(main),
        pageRoot: computedSnapshot(pageRoot),
        settingsPageRoot: document.body.innerText.includes("Настройки") ? computedSnapshot(pageRoot) : null,
        cardsPageRoot: document.body.innerText.includes("Карточки") ? computedSnapshot(pageRoot) : null,
        documentStyleTagsWithNoteCssMarkers: styleTagsWithNoteMarkers,
        documentStyleTagsWithNoteCssMarkerCount: styleTagsWithNoteMarkers.length,
      };

      function stripQuery(value) {
        return String(value || "").split("#", 1)[0].split("?", 1)[0];
      }

      function computedSnapshot(element) {
        const style = getComputedStyle(element);
        return {
          tag: element.tagName.toLowerCase(),
          className: element.className || "",
          backgroundColor: style.backgroundColor,
          effectiveBackgroundColor: effectiveBackgroundColor(element),
          color: style.color,
        };
      }

      function effectiveBackgroundColor(element) {
        let current = element;
        while (current && current instanceof Element) {
          const color = getComputedStyle(current).backgroundColor;
          if (color && color !== "transparent" && !/^rgba\(\s*0,\s*0,\s*0,\s*0\s*\)$/i.test(color)) {
            return color;
          }
          current = current.parentElement;
        }
        return getComputedStyle(document.body).backgroundColor;
      }
    },
    { currentPageName: pageName, responses: assetResponseSnapshot },
  );
}

async function inspectDocumentNoteCssLeak(page) {
  return page.evaluate(() => {
    const markers = [".word-focus", ".main-word", ".main-grammar", ".meaning-box"];
    const matches = [...document.querySelectorAll("style")]
      .map((style, index) => ({ index, text: style.textContent || "" }))
      .filter((style) => markers.some((marker) => style.text.includes(marker)))
      .map((style) => ({
        index: style.index,
        markers: markers.filter((marker) => style.text.includes(marker)),
        excerpt: style.text.slice(0, 500),
      }));
    return { count: matches.length, matches };
  });
}

function assertDashboardCss(diagnostics, { theme, page }) {
  assertBrowser(diagnostics.documentThemeAttribute === theme, `${page} document theme is ${theme}.`);
  assertBrowser(diagnostics.linkedStylesheets.length > 0, `${page} has linked stylesheets.`);
  assertBrowser(
    diagnostics.linkedStylesheets.every((sheet) => sheet.loaded && sheet.ruleCount > 0 && (sheet.status === null || sheet.status === 200)),
    `${page} linked stylesheets loaded with CSS rules.`,
  );
  assertBrowser(
    diagnostics.documentStyleTagsWithNoteCssMarkerCount === 0,
    `${page} has no document-level note CSS markers.`,
  );
  const luminance = colorLuminance(diagnostics.appRoot.effectiveBackgroundColor);
  if (theme === "light") {
    assertBrowser(luminance > 180, `${page} light theme background is light: ${diagnostics.appRoot.effectiveBackgroundColor}.`);
  } else {
    assertBrowser(luminance < 90, `${page} dark theme background is dark: ${diagnostics.appRoot.effectiveBackgroundColor}.`);
  }
}

function colorLuminance(value) {
  const match = String(value || "").match(/rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/i);
  if (!match) {
    return 0;
  }
  const [, red, green, blue] = match.map(Number);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

async function captureApkg(page, mode, theme, filePath, deckName) {
  await prepareCardsPage(page, mode, theme);
  await applyDeckFilter(page, deckName);
  if (mode === "table" || mode === "tiles") {
    await waitForApkgShadowPreviews(page, mode === "tiles" ? "tile" : "table");
  } else {
    await waitForApkgAnkiPreview(page);
  }
  await waitForLayoutStabilization(page);
  await ensureArtifactParent(filePath);
  await page.screenshot({ path: filePath, fullPage: true });
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
        return Boolean(
          shadowRoot &&
            host.getAttribute("data-preview-measured") === "true" &&
            (searchable.includes("要望") || searchable.includes("%E8%A6%81")),
        );
      });
    },
    { expectedMode: mode },
    { timeout: 60000 },
  );
}

async function waitForAnkiPreview(page) {
  await page.locator('[data-testid="anki-preview-answer"]').first().waitFor({ state: "visible", timeout: 60000 });
  await page.locator('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="answer"]').first().waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    () => {
      const answerHosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="answer"]')];
      return answerHosts.some((host) => {
        const html = `${host.getAttribute("title") || ""}\n${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`;
        return (
          host.getAttribute("data-preview-measured") === "true" &&
          (html.includes("要望") || html.includes("%E8%A6%81")) &&
          (host.shadowRoot?.textContent || "").trim().length > 0
        );
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
      return hosts.length > 0 && hosts.every((host) => host.getAttribute("data-preview-measured") === "true") && hosts.some((host) => {
        const searchable = `${host.getAttribute("title") || ""}\n${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`;
        return /要望|遺伝子型|なくて|WebSocket|%E8%A6%81/.test(searchable);
      });
    },
    { expectedMode: mode },
    { timeout: 60000 },
  );
}

async function waitForLayoutStabilization(page) {
  await page.evaluate(async () => {
    await document.fonts?.ready?.catch(() => undefined);
    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(resolve);
        });
      });
    });
  });
}

async function waitForApkgAnkiPreview(page) {
  await page.locator('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"]').first().waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    () => {
      const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"]')];
      return hosts.some((host) => {
        const searchable = `${host.getAttribute("title") || ""}\n${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`;
        return host.getAttribute("data-preview-measured") === "true" && /要望|遺伝子型|なくて|WebSocket|%E8%A6%81/.test(searchable);
      });
    },
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

async function inspectTileLayout(page) {
  return page.evaluate(() => {
    const tolerance = 2;
    const tiles = [...document.querySelectorAll('[data-testid="cards-tile"]')].filter((tile) => {
      const rect = tile.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    const rectOf = (element) => {
      if (!element) {
        return null;
      }
      const rect = element.getBoundingClientRect();
      return {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      };
    };
    const intersects = (first, second) =>
      Boolean(
        first &&
          second &&
          first.left < second.right - tolerance &&
          first.right > second.left + tolerance &&
          first.top < second.bottom - tolerance &&
          first.bottom > second.top + tolerance,
      );
    const outside = (inner, outer) =>
      Boolean(
        inner &&
          outer &&
          (inner.left < outer.left - tolerance ||
            inner.right > outer.right + tolerance ||
            inner.top < outer.top - tolerance ||
            inner.bottom > outer.bottom + tolerance)
      );
    const zeroSized = (rect) => !rect || rect.width <= tolerance || rect.height <= tolerance;
    const actionCovered = (button) => {
      const rect = button.getBoundingClientRect();
      if (rect.width <= tolerance || rect.height <= tolerance) {
        return true;
      }
      if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) {
        return false;
      }
      const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return !(target === button || button.contains(target) || target?.closest("button") === button);
    };

    const tileDetails = tiles.map((tile, index) => {
      const tileRect = rectOf(tile);
      const previewSlot = tile.querySelector('[data-testid="cards-tile-preview-slot"]');
      const previewHost = tile.querySelector('[data-testid="anki-card-shadow-preview"]');
      const metrics = tile.querySelector('[data-testid="cards-tile-metrics"]');
      const issues = tile.querySelector('[data-testid="cards-tile-issues"]');
      const actions = tile.querySelector('[data-testid="cards-tile-actions"]');
      const previewRect = rectOf(previewSlot || previewHost);
      const hostRect = rectOf(previewHost);
      const metricsRect = rectOf(metrics);
      const issuesRect = rectOf(issues);
      const actionsRect = rectOf(actions);
      const issueBadges = [...(issues?.querySelectorAll(".status-pill") || [])].map(rectOf);
      const buttons = [...(actions?.querySelectorAll("button") || [])];
      const previewOverlapsMetrics = intersects(previewRect, metricsRect);
      const previewOverlapsIssues = intersects(previewRect, issuesRect);
      const previewOverlapsActions = intersects(previewRect, actionsRect);
      const hostOutsidePreviewSlot = Boolean(hostRect && previewRect && outside(hostRect, previewRect));
      return {
        index,
        cardId: tile.getAttribute("data-card-id") || "",
        measured: previewHost?.getAttribute("data-preview-measured") === "true",
        previewOverflow: previewHost?.getAttribute("data-preview-overflow") || "",
        tileRect,
        previewRect,
        hostRect,
        metricsRect,
        issuesRect,
        actionsRect,
        previewOverlapsMetrics,
        previewOverlapsIssues,
        previewOverlapsActions,
        hostOutsidePreviewSlot,
        metricsClipped: zeroSized(metricsRect) || outside(metricsRect, tileRect),
        actionsClipped: zeroSized(actionsRect) || outside(actionsRect, tileRect),
        badgesClipped: issueBadges.some((rect) => zeroSized(rect) || outside(rect, tileRect)),
        coveredActions: buttons.filter(actionCovered).length,
        buttonCount: buttons.length,
      };
    });

    let tileOverlapCount = 0;
    for (let outerIndex = 0; outerIndex < tileDetails.length; outerIndex += 1) {
      for (let innerIndex = outerIndex + 1; innerIndex < tileDetails.length; innerIndex += 1) {
        if (intersects(tileDetails[outerIndex].tileRect, tileDetails[innerIndex].tileRect)) {
          tileOverlapCount += 1;
        }
      }
    }
    const pageText = document.body.innerText || "";
    return {
      tileCount: tileDetails.length,
      tileOverlapCount,
      tilePreviewOverlapCount: tileDetails.filter(
        (detail) => detail.previewOverlapsMetrics || detail.previewOverlapsIssues || detail.previewOverlapsActions,
      ).length,
      tileMetricsClippedCount: tileDetails.filter((detail) => detail.metricsClipped).length,
      tileActionsClippedCount: tileDetails.filter((detail) => detail.actionsClipped).length,
      tileBadgesClippedCount: tileDetails.filter((detail) => detail.badgesClipped).length,
      tileCoveredActionsCount: tileDetails.reduce((sum, detail) => sum + detail.coveredActions, 0),
      tilePreviewHostOutsideSlotCount: tileDetails.filter((detail) => detail.hostOutsidePreviewSlot).length,
      unmeasuredHostCount: tileDetails.filter((detail) => !detail.measured).length,
      rawSoundCount: (pageText.match(/\[sound:/gi) || []).length,
      rawAnkiPlayCount: (pageText.match(/\[anki:play:/gi) || []).length,
      details: tileDetails.slice(0, 12),
    };
  });
}

async function inspectTableLayout(page) {
  return page.evaluate(() => {
    const tolerance = 2;
    const verticalScrollTolerance = 32;
    const wrapper = document.querySelector('[data-testid="cards-table-wrap"]') || document.querySelector(".cards-table-wrap");
    const rows = [...document.querySelectorAll('[data-testid="cards-table-row"]')].filter((row) => {
      const rect = row.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    const rectOf = (element) => {
      if (!element) {
        return null;
      }
      const rect = element.getBoundingClientRect();
      return {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      };
    };
    const zeroSized = (rect) => !rect || rect.width <= tolerance || rect.height <= tolerance;
    const bottomClippedBy = (inner, outer) =>
      Boolean(inner && outer && inner.top < outer.bottom - tolerance && inner.bottom > outer.bottom + tolerance);
    const outside = (inner, outer) =>
      Boolean(
        inner &&
          outer &&
          (inner.left < outer.left - tolerance ||
            inner.right > outer.right + tolerance ||
            inner.top < outer.top - tolerance ||
            inner.bottom > outer.bottom + tolerance)
      );
    const actionCovered = (button) => {
      const rect = button.getBoundingClientRect();
      if (rect.width <= tolerance || rect.height <= tolerance) {
        return true;
      }
      if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) {
        return false;
      }
      const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return !(target === button || button.contains(target) || target?.closest("button") === button);
    };
    const wrapperRect = rectOf(wrapper);
    const wrapperStyle = wrapper ? getComputedStyle(wrapper) : null;
    const wrapperHasVerticalScroll =
      Boolean(wrapper) &&
      /(auto|scroll|overlay)/.test(wrapperStyle?.overflowY || "") &&
      wrapper.scrollHeight > wrapper.clientHeight + verticalScrollTolerance;
    const rowDetails = rows.map((row, index) => {
      const rowRect = rectOf(row);
      const previewCell = row.querySelector('[data-testid="cards-table-preview-cell"]');
      const previewHost = row.querySelector('[data-testid="anki-card-shadow-preview"]');
      const issues = row.querySelector('[data-testid="cards-table-issues"]');
      const actions = row.querySelector('[data-testid="cards-table-actions"]');
      const previewRect = rectOf(previewHost || previewCell);
      const actionsRect = rectOf(actions);
      const issuesRect = rectOf(issues);
      const issueBadges = [...(issues?.querySelectorAll(".status-pill") || [])].map(rectOf);
      const buttons = [...(actions?.querySelectorAll("button") || [])];
      return {
        index,
        cardId: row.getAttribute("data-card-id") || "",
        measured: previewHost?.getAttribute("data-preview-measured") === "true",
        previewOverflow: previewHost?.getAttribute("data-preview-overflow") || "",
        rowRect,
        previewRect,
        actionsRect,
        issuesRect,
        rowBottomClipped: wrapperHasVerticalScroll && bottomClippedBy(rowRect, wrapperRect),
        previewBottomClipped: wrapperHasVerticalScroll && bottomClippedBy(previewRect, wrapperRect),
        actionsBottomClipped: wrapperHasVerticalScroll && bottomClippedBy(actionsRect, wrapperRect),
        badgesBottomClipped: wrapperHasVerticalScroll && issueBadges.some((rect) => bottomClippedBy(rect, wrapperRect)),
        actionsClippedByRow: zeroSized(actionsRect) || outside(actionsRect, rowRect),
        badgesClippedByRow: issueBadges.some((rect) => zeroSized(rect) || outside(rect, rowRect)),
        coveredActions: buttons.filter(actionCovered).length,
        buttonCount: buttons.length,
      };
    });
    const pageText = document.body.innerText || "";
    return {
      tableRowCount: rowDetails.length,
      tableInternalScrollCount: wrapperHasVerticalScroll ? 1 : 0,
      tableWrapperOverflowY: wrapperStyle?.overflowY || "",
      tableWrapperClientHeight: wrapper?.clientHeight || 0,
      tableWrapperScrollHeight: wrapper?.scrollHeight || 0,
      tableRowBottomClippedCount: rowDetails.filter((detail) => detail.rowBottomClipped).length,
      tablePreviewBottomClippedCount: rowDetails.filter((detail) => detail.previewBottomClipped).length,
      tableActionsBottomClippedCount: rowDetails.filter((detail) => detail.actionsBottomClipped || detail.actionsClippedByRow).length,
      tableBadgesBottomClippedCount: rowDetails.filter((detail) => detail.badgesBottomClipped || detail.badgesClippedByRow).length,
      tableCoveredActionsCount: rowDetails.reduce((sum, detail) => sum + detail.coveredActions, 0),
      unmeasuredHostCount: rowDetails.filter((detail) => !detail.measured).length,
      rawSoundCount: (pageText.match(/\[sound:/gi) || []).length,
      rawAnkiPlayCount: (pageText.match(/\[anki:play:/gi) || []).length,
      details: rowDetails.slice(0, 12),
    };
  });
}

async function inspectApkgResponsiveLayouts(page, deckName) {
  const result = [];
  for (const viewport of responsiveViewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    await prepareCardsPage(page, "table", "dark");
    await applyDeckFilter(page, deckName);
    await waitForApkgShadowPreviews(page, "table");
    await waitForLayoutStabilization(page);
    const table = await inspectTableLayout(page);
    assertTableLayoutSummary(table, `APKG ${viewport.name} table`);

    await prepareCardsPage(page, "tiles", "dark");
    await applyDeckFilter(page, deckName);
    await waitForApkgShadowPreviews(page, "tile");
    await waitForLayoutStabilization(page);
    const tiles = await inspectTileLayout(page);
    assertTileLayoutSummary(tiles, `APKG ${viewport.name} tiles`);

    await prepareCardsPage(page, "ankiPreview", "dark");
    await applyDeckFilter(page, deckName);
    await waitForApkgAnkiPreview(page);
    await waitForLayoutStabilization(page);
    const ankiPreview = await inspectApkgAnkiPreview(page);
    assertApkgAnkiPreviewSummary(ankiPreview, `APKG ${viewport.name} Anki preview`);

    result.push({ viewport, table, tiles, ankiPreview });
  }
  await page.setViewportSize({ width: baseViewport.width, height: baseViewport.height });
  return result;
}

async function inspectCardsPerformance100IfEnabled(page, report, importSummary, problemSummary, deckName) {
  const scenario = problemSummary.performanceScenario || {};
  if (!scenario.enabled) {
    return {
      enabled: false,
      scenario: "cards-performance-100",
      skipReason: scenario.skipReason || "ANKI_E2E_PERF100 is not enabled.",
    };
  }

  const apkgCards = findApkgCards(report, importSummary);
  const targetCardCount = Number(scenario.targetCardCount || 100);
  const renderSourceCounts = countRenderSources(apkgCards);
  assertBrowser(targetCardCount === 100, `Performance scenario target is 100 cards: ${targetCardCount}`);
  assertBrowser(apkgCards.length >= targetCardCount, `Performance scenario cards reached dashboard: ${apkgCards.length}`);
  assertBrowser((renderSourceCounts.anki_native || 0) >= targetCardCount, `Performance scenario cards use native render: ${renderSourceCounts.anki_native || 0}`);

  const modes = [];
  for (const viewport of responsiveViewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const mode of ["table", "tiles", "ankiPreview"]) {
      const initialStart = Date.now();
      await prepareCardsPage(page, mode, "dark");
      await applyDeckFilter(page, deckName);
      if (mode === "table") {
        await waitForApkgShadowPreviews(page, "table");
      } else if (mode === "tiles") {
        await waitForApkgShadowPreviews(page, "tile");
      } else {
        await waitForApkgAnkiPreview(page);
      }
      await waitForLayoutStabilization(page);
      const initialStableMs = Date.now() - initialStart;
      const layout = mode === "table" ? await inspectTableLayout(page) : mode === "tiles" ? await inspectTileLayout(page) : await inspectApkgAnkiPreview(page);
      if (mode === "table") {
        assertTableLayoutSummary(layout, `Performance 100 ${viewport.name} table`);
      } else if (mode === "tiles") {
        assertTileLayoutSummary(layout, `Performance 100 ${viewport.name} tiles`);
      } else {
        assertApkgAnkiPreviewSummary(layout, `Performance 100 ${viewport.name} Anki preview`);
      }
      const hostSummary = await inspectPerformanceHostSummary(page, mode);
      const scrollStart = Date.now();
      const scrollSamples = await samplePerformanceScroll(page, mode);
      const scrollSampleMs = Date.now() - scrollStart;
      assertPerformanceModeSummary({
        mode,
        viewport,
        targetCardCount,
        layout,
        hostSummary,
        scrollSamples,
      });
      modes.push({
        scenario: "cards-performance-100",
        cardCount: targetCardCount,
        mode,
        theme: "dark",
        viewport: `${viewport.width}x${viewport.height}`,
        shadowHostCount: hostSummary.shadowHostCount,
        frontHostCount: hostSummary.frontHostCount,
        answerHostCount: hostSummary.answerHostCount,
        measuredHostCount: hostSummary.measuredHostCount,
        unmeasuredHostCount: hostSummary.unmeasuredHostCount,
        clippedHostCount: hostSummary.clippedHostCount,
        overflowHostCount: hostSummary.overflowHostCount,
        coveredActionsCount: hostSummary.coveredActionsCount,
        consoleErrorCount: consoleEvents.filter((event) => event.type === "error").length,
        pageErrorCount: pageErrors.length,
        initialStableMs,
        modeSwitchStableMs: initialStableMs,
        scrollSampleMs,
        renderSourceCounts: hostSummary.renderSourceCounts,
        rawSoundMarkerCount: hostSummary.rawSoundMarkerCount,
        rawAnkiPlayMarkerCount: hostSummary.rawAnkiPlayMarkerCount,
        layout,
        scrollSamples,
      });
    }
  }
  await page.setViewportSize({ width: baseViewport.width, height: baseViewport.height });

  const summary = {
    enabled: true,
    scenario: "cards-performance-100",
    targetCardCount,
    sourceImportedCardCount: Number(importSummary.cardCount || 0),
    dashboardCardCount: apkgCards.length,
    clonedCardCount: Number(scenario.clonedCardCount || 0),
    clonedNoteCount: Number(scenario.clonedNoteCount || 0),
    renderSourceCounts,
    modes,
  };
  await writeJson(`browser-smoke-performance-100-${label}.json`, { performance100: summary });
  return summary;
}

async function inspectPerformanceHostSummary(page, mode) {
  return page.evaluate((selectedMode) => {
    const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"]')];
    const frontHosts = hosts.filter((host) => host.getAttribute("data-preview-side") === "front");
    const answerHosts = hosts.filter((host) => host.getAttribute("data-preview-side") === "answer");
    const clipChecks = hosts.map((host) => {
      const viewport = host.shadowRoot?.querySelector('[data-testid="asr-shadow-card-viewport"]') || host.shadowRoot?.querySelector(".asr-shadow-card-viewport");
      const hostRect = host.getBoundingClientRect();
      const viewportRect = viewport?.getBoundingClientRect();
      return {
        measured: host.getAttribute("data-preview-measured") === "true",
        overflow: host.getAttribute("data-preview-overflow") === "true",
        clipped: selectedMode === "ankiPreview" && (!viewportRect || viewportRect.bottom > hostRect.bottom + 3),
        renderSource: host.getAttribute("data-render-source") || "other",
      };
    });
    const renderSourceCounts = {};
    for (const check of clipChecks) {
      renderSourceCounts[check.renderSource] = (renderSourceCounts[check.renderSource] || 0) + 1;
    }
    const buttons = [...document.querySelectorAll('[data-testid="cards-table-actions"] button, [data-testid="cards-tile-actions"] button, .cards-anki-preview-actions button')];
    const coveredActionsCount = buttons.filter((button) => {
      const rect = button.getBoundingClientRect();
      if (rect.width <= 2 || rect.height <= 2) {
        return true;
      }
      if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) {
        return false;
      }
      const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return !(target === button || button.contains(target) || target?.closest("button") === button);
    }).length;
    const pageText = document.body.innerText || "";
    return {
      mode: selectedMode,
      tableRowCount: document.querySelectorAll('[data-testid="cards-table-row"]').length,
      tileCount: document.querySelectorAll('[data-testid="cards-tile"]').length,
      ankiPreviewCardCount: document.querySelectorAll(".cards-anki-preview-card").length,
      shadowHostCount: hosts.length,
      frontHostCount: frontHosts.length,
      answerHostCount: answerHosts.length,
      measuredHostCount: clipChecks.filter((check) => check.measured).length,
      unmeasuredHostCount: clipChecks.filter((check) => !check.measured).length,
      clippedHostCount: clipChecks.filter((check) => check.clipped).length,
      overflowHostCount: clipChecks.filter((check) => check.overflow).length,
      coveredActionsCount,
      rawSoundMarkerCount: (pageText.match(/\[sound:/gi) || []).length,
      rawAnkiPlayMarkerCount: (pageText.match(/\[anki:play:/gi) || []).length,
      renderSourceCounts,
    };
  }, mode);
}

async function samplePerformanceScroll(page, mode) {
  const positions = await page.evaluate(() => {
    const scrolling = document.scrollingElement || document.documentElement;
    const maxScroll = Math.max(0, scrolling.scrollHeight - window.innerHeight);
    return [...new Set([0, Math.round(maxScroll / 2), maxScroll])];
  });
  const samples = [];
  for (const position of positions) {
    const started = Date.now();
    await page.evaluate((scrollTop) => window.scrollTo(0, scrollTop), position);
    await waitForLayoutStabilization(page);
    const sample = await page.evaluate((selectedMode) => {
      const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"]')];
      const visibleHosts = hosts.filter((host) => {
        const rect = host.getBoundingClientRect();
        return rect.bottom > 0 && rect.top < window.innerHeight && rect.width > 0 && rect.height > 0;
      });
      const visibleClipChecks = visibleHosts.map((host) => {
        const viewport = host.shadowRoot?.querySelector('[data-testid="asr-shadow-card-viewport"]') || host.shadowRoot?.querySelector(".asr-shadow-card-viewport");
        const hostRect = host.getBoundingClientRect();
        const viewportRect = viewport?.getBoundingClientRect();
        return {
          measured: host.getAttribute("data-preview-measured") === "true",
          clipped: selectedMode === "ankiPreview" && (!viewportRect || viewportRect.bottom > hostRect.bottom + 3),
        };
      });
      return {
        scrollY: Math.round(window.scrollY),
        visibleHostCount: visibleHosts.length,
        visibleMeasuredHostCount: visibleClipChecks.filter((check) => check.measured).length,
        visibleUnmeasuredHostCount: visibleClipChecks.filter((check) => !check.measured).length,
        visibleClippedHostCount: visibleClipChecks.filter((check) => check.clipped).length,
      };
    }, mode);
    samples.push({ ...sample, stableMs: Date.now() - started });
  }
  return samples;
}

function assertPerformanceModeSummary({ mode, targetCardCount, layout, hostSummary, scrollSamples }) {
  assertBrowser(pageErrors.length === 0, `Performance 100 ${mode} has no page errors.`);
  assertBrowser(consoleEvents.filter((event) => event.type === "error").length === 0, `Performance 100 ${mode} has no console errors.`);
  assertBrowser(hostSummary.rawSoundMarkerCount === 0, `Performance 100 ${mode} has no visible raw sound markers.`);
  assertBrowser(hostSummary.rawAnkiPlayMarkerCount === 0, `Performance 100 ${mode} has no visible raw Anki play markers.`);
  assertBrowser(hostSummary.coveredActionsCount === 0, `Performance 100 ${mode} action buttons are not covered.`);
  assertBrowser(scrollSamples.every((sample) => sample.visibleUnmeasuredHostCount === 0), `Performance 100 ${mode} visible hosts stay measured while scrolling.`);
  assertBrowser(scrollSamples.every((sample) => sample.visibleClippedHostCount === 0), `Performance 100 ${mode} visible answer hosts are not clipped while scrolling.`);
  if (mode === "table") {
    assertBrowser(layout.tableRowCount >= targetCardCount, `Performance 100 table rendered ${targetCardCount} rows.`);
    assertBrowser(hostSummary.frontHostCount >= targetCardCount, `Performance 100 table rendered front hosts.`);
    assertBrowser(hostSummary.answerHostCount === 0, "Performance 100 table did not mount answer hosts.");
  } else if (mode === "tiles") {
    assertBrowser(layout.tileCount >= targetCardCount, `Performance 100 tiles rendered ${targetCardCount} tiles.`);
    assertBrowser(hostSummary.frontHostCount >= targetCardCount, `Performance 100 tiles rendered front hosts.`);
    assertBrowser(hostSummary.answerHostCount === 0, "Performance 100 tiles did not mount answer hosts.");
  } else {
    assertBrowser(hostSummary.ankiPreviewCardCount >= targetCardCount, `Performance 100 Anki preview rendered ${targetCardCount} cards.`);
    assertBrowser(hostSummary.answerHostCount >= targetCardCount, `Performance 100 Anki preview rendered answer hosts.`);
    assertBrowser(hostSummary.frontHostCount === 0, "Performance 100 Anki preview did not mount front hosts.");
    assertBrowser(hostSummary.clippedHostCount === 0, "Performance 100 Anki preview answer hosts are not clipped.");
  }
}

async function inspectApkgAnkiPreview(page) {
  return page.evaluate(() => {
    const hosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="answer"]')];
    const frontHosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="front"]')];
    const html = hosts.map((host) => `${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`).join("\n");
    const shadowRoots = hosts.map((host) => host.shadowRoot).filter(Boolean);
    const images = shadowRoots.flatMap((shadowRoot) => [...shadowRoot.querySelectorAll("img")]);
    const audioElements = shadowRoots.flatMap((shadowRoot) => [...shadowRoot.querySelectorAll("audio")]);
    const clipChecks = hosts.map((host) => {
      const root = host.shadowRoot;
      const viewport = root?.querySelector('[data-testid="asr-shadow-card-viewport"]') || root?.querySelector(".asr-shadow-card-viewport");
      const hostRect = host.getBoundingClientRect();
      const viewportRect = viewport?.getBoundingClientRect();
      return {
        hasHost: Boolean(host),
        hasViewport: Boolean(viewport),
        measured: host.getAttribute("data-preview-measured") === "true",
        overflow: host.getAttribute("data-preview-overflow") === "true",
        scale: Number(host.getAttribute("data-preview-scale") || 0),
        hostHeight: hostRect.height,
        hostBottom: hostRect.bottom,
        viewportHeight: viewportRect?.height || 0,
        viewportBottom: viewportRect?.bottom || 0,
        clipped: !viewportRect || viewportRect.bottom > hostRect.bottom + 3,
      };
    });
    return {
      previewCount: hosts.length,
      frontHostCount: frontHosts.length,
      imgCount: images.length,
      audioElementCount: audioElements.length,
      replayButtonCount: shadowRoots.reduce((sum, shadowRoot) => sum + shadowRoot.querySelectorAll(".asr-card-replay-button").length, 0),
      hasRawSoundMarker: html.toLowerCase().includes("[sound:"),
      hasRawAnkiPlayMarker: html.includes("[anki:play:"),
      hasScriptTag: /<script/i.test(html),
      hasExternalCdnLink: /cdnjs|<link\b/i.test(html),
      hasWordFocus: html.includes("word-focus"),
      hasGrammarFocus: /grammar-focus|grammar-pattern|main-grammar/.test(html),
      clipChecks,
      clippedHostCount: clipChecks.filter((check) => check.clipped).length,
      unmeasuredHostCount: clipChecks.filter((check) => !check.measured).length,
      textSample: shadowRoots.map((shadowRoot) => shadowRoot.textContent || "").join("\n").slice(0, 500),
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

function assertTileLayoutSummary(details, labelText) {
  assertBrowser(details.tileCount > 0, `${labelText} rendered tile cards.`);
  assertBrowser(details.tileOverlapCount === 0, `${labelText} cards do not overlap each other.`);
  assertBrowser(details.tilePreviewOverlapCount === 0, `${labelText} previews do not overlap metrics, badges, or actions.`);
  assertBrowser(details.tileMetricsClippedCount === 0, `${labelText} metrics remain inside tile bounds.`);
  assertBrowser(details.tileActionsClippedCount === 0, `${labelText} actions remain inside tile bounds.`);
  assertBrowser(details.tileBadgesClippedCount === 0, `${labelText} issue badges remain inside tile bounds.`);
  assertBrowser(details.tileCoveredActionsCount === 0, `${labelText} action buttons are not covered by overlays.`);
  assertBrowser(details.tilePreviewHostOutsideSlotCount === 0, `${labelText} preview hosts remain inside preview slots.`);
  assertBrowser(details.unmeasuredHostCount === 0, `${labelText} preview hosts completed adaptive measurement.`);
  assertBrowser(details.rawSoundCount === 0, `${labelText} has no visible raw sound macro.`);
  assertBrowser(details.rawAnkiPlayCount === 0, `${labelText} has no visible raw Anki play macro.`);
}

function assertTableLayoutSummary(details, labelText) {
  assertBrowser(details.tableRowCount > 0, `${labelText} rendered table rows.`);
  assertBrowser(details.tableInternalScrollCount === 0, `${labelText} has no nested vertical table scroll.`);
  assertBrowser(details.tableRowBottomClippedCount === 0, `${labelText} rows are not clipped by the table wrapper.`);
  assertBrowser(details.tablePreviewBottomClippedCount === 0, `${labelText} preview hosts are not clipped by the table wrapper.`);
  assertBrowser(details.tableActionsBottomClippedCount === 0, `${labelText} action cells remain visible inside rows.`);
  assertBrowser(details.tableBadgesBottomClippedCount === 0, `${labelText} issue badges remain visible inside rows.`);
  assertBrowser(details.tableCoveredActionsCount === 0, `${labelText} action buttons are not covered by overlays.`);
  assertBrowser(details.unmeasuredHostCount === 0, `${labelText} preview hosts completed adaptive measurement.`);
  assertBrowser(details.rawSoundCount === 0, `${labelText} has no visible raw sound macro.`);
  assertBrowser(details.rawAnkiPlayCount === 0, `${labelText} has no visible raw Anki play macro.`);
}

function assertApkgAnkiPreviewSummary(details, labelText) {
  assertBrowser(details.previewCount > 0, `${labelText} rendered answer previews.`);
  assertBrowser(details.frontHostCount === 0, `${labelText} has no separate front preview host.`);
  assertBrowser(details.unmeasuredHostCount === 0, `${labelText} answer hosts completed adaptive measurement.`);
  assertBrowser(details.clippedHostCount === 0, `${labelText} answer hosts are not clipped at the bottom.`);
  assertBrowser(!details.hasRawSoundMarker, `${labelText} has no raw sound marker.`);
  assertBrowser(!details.hasRawAnkiPlayMarker, `${labelText} has no raw Anki AV marker.`);
  assertBrowser(!details.hasScriptTag, `${labelText} has no script tag.`);
  assertBrowser(!details.hasExternalCdnLink, `${labelText} has no external CDN link.`);
}

async function inspectShadowPreview(page, expectedMode = "") {
  return page.evaluate((mode) => {
    const hosts = [
      ...document.querySelectorAll('[data-testid="anki-card-shadow-preview"], [data-shadow-preview="true"]'),
    ];
    let fallback = null;
    for (const host of hosts) {
      if (mode && host.getAttribute("data-shadow-preview-mode") !== mode) {
        continue;
      }
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
      const details = {
        exists: true,
        mode: host.getAttribute("data-shadow-preview-mode") || "",
        side: host.getAttribute("data-preview-side") || host.getAttribute("data-shadow-preview-side") || "",
        renderSource: host.getAttribute("data-render-source") || "",
        frontSectionCount: document.querySelectorAll('[data-testid="anki-preview-front"]').length,
        backSectionCount: document.querySelectorAll('[data-testid="anki-preview-back"]').length,
        answerSectionCount: document.querySelectorAll('[data-testid="anki-preview-answer"]').length,
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
      if (details.hasCardContent) {
        return details;
      }
      fallback ||= details;
    }
    if (fallback) {
      return fallback;
    }
    return {
      exists: false,
      mode: "",
      side: "",
      renderSource: "",
      frontSectionCount: 0,
      backSectionCount: 0,
      answerSectionCount: 0,
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
  }, expectedMode);
}

async function inspectAnkiPreview(page) {
  return page.evaluate(() => {
    const frontHosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="front"]')];
    const backHosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="back"]')];
    const answerHosts = [...document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"][data-preview-side="answer"]')];
    const hosts = [...answerHosts];
    const html = hosts.map((host) => `${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`).join("\n");
    const answerHtml = answerHosts.map((host) => `${host.querySelector("template")?.innerHTML || ""}\n${host.shadowRoot?.innerHTML || ""}`).join("\n");
    const shadowRoots = hosts.map((host) => host.shadowRoot).filter(Boolean);
    const images = shadowRoots.flatMap((shadowRoot) => [...shadowRoot.querySelectorAll("img")]);
    const audioElements = shadowRoots.flatMap((shadowRoot) => [...shadowRoot.querySelectorAll("audio")]);
    const visibleNativeAudioControls = audioElements.some((audio) => {
      const rect = audio.getBoundingClientRect();
      return audio.hasAttribute("controls") && rect.width > 0 && rect.height > 0;
    });
    const clipChecks = hosts.map((host) => {
      const root = host.shadowRoot;
      const viewport = root?.querySelector('[data-testid="asr-shadow-card-viewport"]') || root?.querySelector(".asr-shadow-card-viewport");
      const hostRect = host.getBoundingClientRect();
      const viewportRect = viewport?.getBoundingClientRect();
      return {
        hasHost: Boolean(host),
        hasViewport: Boolean(viewport),
        measured: host.getAttribute("data-preview-measured") === "true",
        overflow: host.getAttribute("data-preview-overflow") === "true",
        scale: Number(host.getAttribute("data-preview-scale") || 0),
        hostHeight: hostRect.height,
        hostBottom: hostRect.bottom,
        viewportHeight: viewportRect?.height || 0,
        viewportBottom: viewportRect?.bottom || 0,
        clipped: !viewportRect || viewportRect.bottom > hostRect.bottom + 3,
      };
    });
    return {
      frontSectionCount: document.querySelectorAll('[data-testid="anki-preview-front"]').length,
      backSectionCount: document.querySelectorAll('[data-testid="anki-preview-back"]').length,
      answerSectionCount: document.querySelectorAll('[data-testid="anki-preview-answer"]').length,
      frontHostCount: frontHosts.length,
      backHostCount: backHosts.length,
      answerHostCount: answerHosts.length,
      renderSources: [...new Set(hosts.map((host) => host.getAttribute("data-render-source") || "").filter(Boolean))],
      imgCount: images.length,
      audioElementCount: audioElements.length,
      replayButtonCount: shadowRoots.reduce((sum, shadowRoot) => sum + shadowRoot.querySelectorAll(".asr-card-replay-button").length, 0),
      hasVisibleNativeAudioControls: visibleNativeAudioControls,
      hasRawSoundMarker: html.toLowerCase().includes("[sound:"),
      hasRawAnkiPlayMarker: html.includes("[anki:play:"),
      hasScriptTag: Boolean(shadowRoots.some((shadowRoot) => shadowRoot.querySelector("script"))) || /<script/i.test(html),
      hasExternalCdnLink: /cdnjs|<link\b/i.test(html),
      hasWordFocus: answerHtml.includes("word-focus"),
      hasAnswerContent: answerHtml.trim().length > 0,
      hasAnswerFallback: document.body.innerText.includes("Ответ недоступен, показана лицевая сторона"),
      hasAnswerText: /обрат|ответ|meaning|translation|改善|要望|back|answer|request|demand/i.test(answerHtml),
      hasAnswerSeparator: /id=["']answer["']|<hr\b/i.test(answerHtml),
      clipChecks,
      clippedHostCount: clipChecks.filter((check) => check.clipped).length,
      unmeasuredHostCount: clipChecks.filter((check) => !check.measured).length,
      textSample: shadowRoots.map((shadowRoot) => shadowRoot.textContent || "").join("\n").slice(0, 500),
    };
  });
}

function assertFrontOnlyMode(details, mode) {
  assertBrowser(details.exists, `${mode} preview exists.`);
  assertBrowser(details.mode === mode, `${mode} preview mode marker is present.`);
  assertBrowser(details.side === "front", `${mode} preview is front-only.`);
  assertBrowser(details.frontSectionCount === 0, `${mode} has no Anki Preview front section.`);
  assertBrowser(details.backSectionCount === 0, `${mode} has no Anki Preview back section.`);
  assertBrowser(details.answerSectionCount === 0, `${mode} has no Anki Preview answer section.`);
  assertBrowser(!details.hasRawSoundMarker, `${mode} has no raw sound marker.`);
  assertBrowser(!details.hasRawAnkiPlayMarker, `${mode} has no raw Anki AV marker.`);
}

function assertAnkiPreviewAnswerOnly(details, theme) {
  assertBrowser(details.answerSectionCount > 0, `Anki Preview ${theme} has answer section.`);
  assertBrowser(details.frontSectionCount === 0, `Anki Preview ${theme} has no separate front section.`);
  assertBrowser(details.backSectionCount === 0, `Anki Preview ${theme} has no separate back section.`);
  assertBrowser(details.answerHostCount > 0, `Anki Preview ${theme} has answer Shadow preview.`);
  assertBrowser(details.frontHostCount === 0, `Anki Preview ${theme} has no separate front Shadow preview.`);
  assertBrowser(details.backHostCount === 0, `Anki Preview ${theme} has no separate back Shadow preview.`);
  assertBrowser(details.unmeasuredHostCount === 0, `Anki Preview ${theme} answer hosts completed adaptive measurement.`);
  assertBrowser(details.clippedHostCount === 0, `Anki Preview ${theme} answer hosts are not clipped at the bottom.`);
  assertBrowser(details.hasAnswerContent, `Anki Preview ${theme} has rendered answer content.`);
  assertBrowser(!details.hasAnswerFallback, `Anki Preview ${theme} did not fall back for fixture card.`);
  assertBrowser(!details.hasVisibleNativeAudioControls, `Anki Preview ${theme} has no visible native audio controls.`);
  assertBrowser(!details.hasRawSoundMarker, `Anki Preview ${theme} has no raw sound marker.`);
  assertBrowser(!details.hasRawAnkiPlayMarker, `Anki Preview ${theme} has no raw Anki AV marker.`);
  assertBrowser(!details.hasScriptTag, `Anki Preview ${theme} has no script tag.`);
  assertBrowser(!details.hasExternalCdnLink, `Anki Preview ${theme} has no external CDN refs.`);
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
  const errorText = String(error?.stack || error?.message || error);
  const failureScreenshot = artifactPaths.failureScreenshot(`browser-${label}-failure.png`);
  const failureHtml = artifactPaths.htmlFile("failures", `browser-${label}-failure.html`);
  await saveBestEffort(async () => {
    await ensureArtifactParent(failureScreenshot);
    await page.screenshot({ path: failureScreenshot, fullPage: true });
  });
  await saveBestEffort(async () => {
    await ensureArtifactParent(failureHtml);
    await fs.writeFile(failureHtml, redactArtifact(await page.content()), "utf8");
  });
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

async function deleteStaleFailureArtifacts() {
  const stalePaths = [
    artifactPaths.failureScreenshot(`browser-${label}-failure.png`),
    artifactPaths.htmlFile("failures", `browser-${label}-failure.html`),
    path.join(artifactPaths.diagnostics, `browser-console-${label}.log`),
    artifactPaths.report(`browser-network-${label}.json`),
    artifactPaths.report(`browser-dom-summary-${label}.json`),
  ];
  await Promise.all(stalePaths.map((filePath) => fs.rm(filePath, { force: true })));
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
      ankiPreviewSections: document.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-shadow-preview-mode="preview"]').length,
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

function countRenderSources(cards) {
  const result = { anki_native: 0, fallback: 0, sanitized: 0, other: 0 };
  for (const card of cards) {
    const source = String(card?.renderedPreview?.renderSource || "");
    if (source === "anki_native") {
      result.anki_native += 1;
    } else if (source === "fallback") {
      result.fallback += 1;
    } else if (source === "sanitized") {
      result.sanitized += 1;
    } else {
      result.other += 1;
    }
  }
  return result;
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

async function isPerformance100Enabled() {
  const problemSummary = await readJsonIfExists(path.join(artifactPaths.reports, "apkg-problematic-summary.json"));
  return Boolean(problemSummary?.performanceScenario?.enabled);
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
  const filePath = path.join(artifactPaths.diagnostics, fileName);
  await ensureArtifactParent(filePath);
  await fs.writeFile(filePath, `${redactArtifact(lines.join("\n"))}\n`, "utf8");
}

async function writeJson(fileName, value) {
  const filePath = artifactPaths.report(fileName);
  await ensureArtifactParent(filePath);
  await fs.writeFile(filePath, JSON.stringify(redactArtifact(value), null, 2), "utf8");
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
