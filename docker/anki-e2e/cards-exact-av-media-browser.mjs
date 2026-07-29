#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const value = process.argv[index];
  if (value.startsWith("--")) {
    args.set(value.slice(2), process.argv[index + 1]);
    index += 1;
  }
}

const readyPath = args.get("ready");
const reportsDir = args.get("reports");
const screenshotsDir = args.get("screenshots");
const diagnosticsDir = args.get("diagnostics");
if (!readyPath || !reportsDir || !screenshotsDir || !diagnosticsDir) {
  throw new Error("Required arguments: --ready --reports --screenshots --diagnostics");
}

const requiredEnv = (name) => {
  const value = String(process.env[name] || "").trim();
  if (!value) throw new Error(`Required environment variable is missing: ${name}`);
  return value;
};

const config = {
  cardId: requiredEnv("ANKI_E2E_EXACT_CARD_ID"),
  word: requiredEnv("ANKI_E2E_EXACT_WORD"),
  gif: { name: requiredEnv("ANKI_E2E_EXACT_GIF_NAME"), sha256: requiredEnv("ANKI_E2E_EXACT_GIF_SHA256") },
  mp3: { name: requiredEnv("ANKI_E2E_EXACT_MP3_NAME"), sha256: requiredEnv("ANKI_E2E_EXACT_MP3_SHA256") },
  png: { name: requiredEnv("ANKI_E2E_EXACT_PNG_NAME"), sha256: requiredEnv("ANKI_E2E_EXACT_PNG_SHA256") },
  themes: parseThemes(requiredEnv("ANKI_E2E_EXACT_THEMES")),
  viewports: parseViewports(requiredEnv("ANKI_E2E_EXACT_VIEWPORTS_JSON")),
};
const responsiveMatrixViewports = Object.freeze([
  Object.freeze({ name: "full-hd", width: 1920, height: 1080 }),
  Object.freeze({ name: "qhd", width: 2560, height: 1440 }),
  Object.freeze({ name: "4k-uhd", width: 3840, height: 2160 }),
]);
const primaryEvidenceViewport = responsiveMatrixViewports[0];

const ready = JSON.parse(await fs.readFile(readyPath, "utf8"));
const base = new URL(ready.baseUrl);
const token = String(ready.token);
const artifactRoot = path.dirname(reportsDir);
const exactScreenshotsRoot = path.join(screenshotsDir, "cards", "exact-av-media");
const responsiveMatrixRoot = path.join(exactScreenshotsRoot, "responsive-matrix");
const interactionGalleryRoot = path.join(exactScreenshotsRoot, "interaction-gallery", "1920x1080");
const failureScreenshots = path.join(diagnosticsDir, "screenshots-before-failure");
const traceDir = path.join(diagnosticsDir, "browser-trace");
const exactBrowserPath = path.join(reportsDir, "exact-browser.json");
const pageConsolePath = path.join(reportsDir, "page-console-summary.json");
const requestLedgerPath = path.join(reportsDir, "request-ledger.json");
const geometryPath = path.join(reportsDir, "geometry-metrics.json");
const contactSheetPath = path.join(reportsDir, "cards-exact-contact-sheet.png");

await Promise.all([
  fs.mkdir(reportsDir, { recursive: true }),
  fs.mkdir(exactScreenshotsRoot, { recursive: true }),
  fs.mkdir(responsiveMatrixRoot, { recursive: true }),
  fs.mkdir(interactionGalleryRoot, { recursive: true }),
  fs.mkdir(failureScreenshots, { recursive: true }),
  fs.mkdir(traceDir, { recursive: true }),
]);

const consoleEvents = [];
const pageErrors = [];
const failedRequests = [];
const requestLedger = [];
const externalRequests = [];
const inspectionProfileRequests = [];
const mediaResponses = [];
const screenshots = [];
const scenarios = [];
const geometry = [];
const gifScenarioFrames = [];
const replayFocusProofs = [];
let responsiveMatrix = [];
let interactionGallery = [];
let replayProof = null;
let gifProof = null;
let fixedFrameProof = null;
let activeContext = null;
let activePage = null;
let activeScenario = null;
let lastScenario = null;
let status = "FAIL";
let failure = null;

const browser = await chromium.launch({
  headless: true,
  args: ["--autoplay-policy=no-user-gesture-required"],
});

try {
  for (const scenario of buildScenarios(config)) {
    activeScenario = scenario.name;
    lastScenario = scenario.name;
    activeContext = await browser.newContext({
      viewport: { width: scenario.width, height: scenario.height },
      deviceScaleFactor: 1,
      locale: "en-US",
      timezoneId: "UTC",
      colorScheme: scenario.theme,
    });
    await activeContext.tracing.start({ screenshots: true, snapshots: true, sources: true });
    activePage = await activeContext.newPage();
    attachDiagnostics(activePage, scenario.name);
    await installThemeBootstrap(activePage);

    try {
      await openCards(activePage, scenario.theme);
      const item = activePage.locator(`[data-testid="cards-inbox-item"][data-card-id="${config.cardId}"]`);
      await item.waitFor({ state: "visible", timeout: 60000 });
      await item.click();

      if (scenario.kind === "drawer") {
        await activePage.locator('[data-testid="cards-detail-drawer"]').waitFor({ state: "visible", timeout: 30000 });
      } else {
        await activePage.locator('[data-testid="cards-detail-content"]').waitFor({ state: "visible", timeout: 30000 });
      }

      await waitForExactShadow(activePage, "preview", "front");
      const frontMetrics = await shadowMetrics(activePage, "preview");
      assertExactMetrics(frontMetrics, `${scenario.name} front`);
      geometry.push({ scenario: scenario.name, state: "front", ...geometryProjection(frontMetrics) });

      let displayedMetrics = frontMetrics;
      let backMetrics = null;
      if (scenario.kind === "expanded") {
        await activePage.locator(".cards-detail-expand").click();
        await activePage.locator('[data-testid="cards-preview-modal"]').waitFor({ state: "visible", timeout: 30000 });
        await waitForExactShadow(activePage, "expanded", "back");
        backMetrics = await shadowMetrics(activePage, "expanded");
        assertExactMetrics(backMetrics, `${scenario.name} back`);
        geometry.push({ scenario: scenario.name, state: "back", ...geometryProjection(backMetrics) });
        displayedMetrics = backMetrics;
      }

      const fullPath = path.join(exactScreenshotsRoot, `${scenario.name}.png`);
      await activePage.screenshot({ path: fullPath, fullPage: true, animations: "allow", caret: "hide" });
      screenshots.push(recordScreenshot(fullPath, { kind: "full-page", scenario: scenario.name, theme: scenario.theme }));

      const target = scenario.kind === "drawer"
        ? activePage.locator('[data-testid="cards-detail-drawer"]')
        : scenario.kind === "expanded"
          ? activePage.locator('[data-testid="cards-preview-modal"]')
          : activePage.locator('[data-testid="cards-inspector"]');
      const contourPath = path.join(exactScreenshotsRoot, `${scenario.name}-contour.png`);
      await capturePageClip(activePage, target, contourPath);
      screenshots.push(recordScreenshot(contourPath, { kind: "contour", scenario: scenario.name, theme: scenario.theme }));

      const host = exactHost(activePage, scenario.kind === "expanded" ? "expanded" : "preview", scenario.kind);
      const framePath = path.join(exactScreenshotsRoot, `${scenario.name}-card-frame.png`);
      await capturePageClip(activePage, host, framePath);
      screenshots.push(recordScreenshot(framePath, { kind: "card-frame", scenario: scenario.name, theme: scenario.theme }));

      if (scenario.kind === "wide") {
        const groupPath = path.join(exactScreenshotsRoot, `${scenario.name}-media-block.png`);
        await captureRect(activePage, displayedMetrics.compositionGroup, groupPath);
        screenshots.push(recordScreenshot(groupPath, { kind: "media-block", scenario: scenario.name, theme: scenario.theme }));

        const focusProof = await proveReplayFocus(
          activePage,
          exactScreenshotsRoot,
          scenario.theme,
        );
        replayFocusProofs.push(focusProof);
        screenshots.push(...focusProof.screenshots);
      }

      const gifCaptureMode = scenario.kind === "expanded"
        ? "expanded"
        : "preview";
      const gifCaptureMetrics = await shadowMetrics(
        activePage,
        gifCaptureMode,
      );
      const gifScenarioPath = path.join(
        exactScreenshotsRoot,
        `${scenario.name}-gif-frame.png`,
      );
      const gifScenarioBytes = await captureRect(
        activePage,
        gifCaptureMetrics.gif.rect,
        gifScenarioPath,
      );
      const gifScenarioFrame = {
        scenario: scenario.name,
        theme: scenario.theme,
        side: gifCaptureMetrics.side,
        complete: gifCaptureMetrics.gif.complete,
        naturalWidth: gifCaptureMetrics.gif.naturalWidth,
        naturalHeight: gifCaptureMetrics.gif.naturalHeight,
        renderedWidth: gifCaptureMetrics.gif.rect.width,
        renderedHeight: gifCaptureMetrics.gif.rect.height,
        capturedAtEpochMs: Date.now(),
        path: gifScenarioPath,
        sha256: crypto
          .createHash("sha256")
          .update(gifScenarioBytes)
          .digest("hex"),
      };
      gifScenarioFrames.push(gifScenarioFrame);
      screenshots.push(recordScreenshot(gifScenarioPath, {
        kind: "gif-browser-frame",
        scenario: scenario.name,
        theme: scenario.theme,
        side: gifCaptureMetrics.side,
        capturedAtEpochMs: gifScenarioFrame.capturedAtEpochMs,
      }));

      if (scenario.name === "wide-light") {
        replayProof = await proveReplayLifecycle(activePage, exactScreenshotsRoot);
        screenshots.push(...replayProof.screenshots);
        fixedFrameProof = await extractDeterministicGifFrame(activePage, exactScreenshotsRoot);
        screenshots.push(recordScreenshot(fixedFrameProof.path, {
          kind: "gif-fixed-frame",
          scenario: scenario.name,
          theme: scenario.theme,
          frameIndex: fixedFrameProof.frameIndex,
        }));
      }

      scenarios.push({
        name: scenario.name,
        theme: scenario.theme,
        viewport: { width: scenario.width, height: scenario.height },
        kind: scenario.kind,
        frontMetrics,
        backMetrics,
        displayedSide: displayedMetrics.side,
        screenshots: screenshots.filter((item) => item.scenario === scenario.name).map((item) => item.path),
      });
      await activeContext.tracing.stop();
    } finally {
      await activePage.close().catch(() => {});
      await activeContext.close().catch(() => {});
      activePage = null;
      activeContext = null;
      activeScenario = null;
    }
  }

  const visualEvidence = await captureCardsVisualEvidence(browser);
  responsiveMatrix = visualEvidence.matrix;
  interactionGallery = visualEvidence.interactions;
  screenshots.push(...visualEvidence.screenshots);
  gifProof = proveGifAnimation(gifScenarioFrames);

  assert(
    replayFocusProofs.length === config.themes.length,
    `replay focus proof count mismatch: ${
      JSON.stringify(replayFocusProofs)
    }`,
  );
  assert(
    replayFocusProofs.every(
      (item) => (
        item.keyboardFocused
        && item.screenshotDiffers
        && item.focusStyle.outlineWidthPx >= 2
        && item.focusStyle.outlineStyle !== "none"
        && item.focusStyle.boxShadow !== "none"
      ),
    ),
    `replay focus evidence is incomplete: ${
      JSON.stringify(replayFocusProofs)
    }`,
  );

  assert(replayProof?.first?.playEvent && replayProof?.first?.playingEvent, "first replay did not reach play/playing");
  assert(replayProof?.playCalls >= 2, "second replay did not invoke play()");
  assert(replayProof?.second?.resetObserved === true, "second replay did not reset currentTime");
  assert(replayProof?.rejectedPromiseHandled === true, "rejected play() promise escaped the production handler");
  assert(gifProof?.browserFramesDiffer === true, "animated GIF browser frames did not differ");
  assert(fixedFrameProof?.frameIndex === 0 && fixedFrameProof?.frameCount > 1, "deterministic GIF frame proof is incomplete");
  assert(mediaResponses.some((item) => item.name === config.gif.name && item.status === 200), "GIF HTTP 200 was not observed");
  assert(mediaResponses.some((item) => item.name === config.mp3.name && item.status === 200), "MP3 HTTP 200 was not observed");
  assert(mediaResponses.some((item) => item.name === config.png.name && item.status === 200), "PNG HTTP 200 was not observed");
  assert(externalRequests.length === 0, `unexpected external requests: ${JSON.stringify(externalRequests)}`);
  assert(inspectionProfileRequests.length === 0, `Inspection Profiles requests occurred: ${JSON.stringify(inspectionProfileRequests)}`);
  assert(pageErrors.length === 0, `page errors: ${JSON.stringify(pageErrors)}`);
  assert(consoleEvents.filter((item) => item.type === "error").length === 0, "unexpected console errors");
  assert(failedRequests.length === 0, `failed requests: ${JSON.stringify(failedRequests)}`);

  await createContactSheet(browser, contactSheetPath, screenshots);
  status = "PASS";
} catch (error) {
  const failureScenario = activeScenario || lastScenario;
  failure = {
    errorType: String(error?.name || "Error"),
    message: safeText(error?.message || error),
    activeScenario: failureScenario,
  };
  if (activePage) {
    const failurePath = path.join(failureScreenshots, `exact-${safeName(failureScenario || "unknown")}.png`);
    await activePage.screenshot({ path: failurePath, fullPage: true, animations: "allow", caret: "hide" }).catch(() => {});
  }
  if (activeContext) {
    const tracePath = path.join(traceDir, `exact-${safeName(failureScenario || "unknown")}.zip`);
    await activeContext.tracing.stop({ path: tracePath }).catch(() => {});
  }
} finally {
  await browser.close().catch(() => {});
  await writeReports();
}

if (failure) {
  throw new Error(`Cards exact AV/media browser gate failed: ${failure.message}`);
}

console.log(
  `[cards-exact] browser PASS scenarios=${scenarios.length} screenshots=${screenshots.length} external=0 profiles=0`,
);

function parseThemes(value) {
  const result = value.split(",").map((item) => item.trim()).filter(Boolean);
  if (!result.length || result.some((item) => !["light", "dark"].includes(item))) {
    throw new Error(`Invalid exact theme matrix: ${value}`);
  }
  return [...new Set(result)];
}

function parseViewports(value) {
  const parsed = JSON.parse(value);
  for (const key of ["wide", "drawer", "expanded"]) {
    const item = parsed?.[key];
    if (!item || !Number.isInteger(item.width) || !Number.isInteger(item.height) || item.width < 800 || item.height < 600) {
      throw new Error(`Invalid exact viewport ${key}: ${JSON.stringify(item)}`);
    }
  }
  return parsed;
}

function buildScenarios(value) {
  const result = [];
  for (const theme of value.themes) {
    for (const kind of ["wide", "drawer", "expanded"]) {
      const viewport = value.viewports[kind];
      result.push({
        name: kind === "drawer" ? `drawer-${viewport.width}-${theme}` : `${kind}-${theme}`,
        theme,
        kind,
        width: viewport.width,
        height: viewport.height,
      });
    }
  }
  return result;
}

async function captureCardsVisualEvidence(browserInstance) {
  const matrix = [];
  const interactions = [];
  const captured = [];

  for (const viewport of responsiveMatrixViewports) {
    const scenario = `responsive-matrix-${viewport.name}-light`;
    activeScenario = scenario;
    lastScenario = scenario;
    activeContext = await browserInstance.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
      locale: "en-US",
      timezoneId: "UTC",
      colorScheme: "light",
      reducedMotion: "reduce",
    });
    activePage = await activeContext.newPage();
    attachDiagnostics(activePage, scenario);
    await installThemeBootstrap(activePage);

    await openCards(activePage, "light");
    const item = activePage.locator(`[data-testid="cards-inbox-item"][data-card-id="${config.cardId}"]`);
    await item.waitFor({ state: "visible", timeout: 60000 });
    await item.click();
    await activePage.locator('[data-testid="cards-detail-content"]').waitFor({ state: "visible", timeout: 30000 });
    await waitForExactShadow(activePage, "preview", "front");

    if (viewport === primaryEvidenceViewport) {
      const warningCount = await activePage.locator(".cards-inbox-warning").count();
      if (warningCount > 0) {
        const warningPath = path.join(interactionGalleryRoot, "01-dismissible-warnings-1920x1080-light.png");
        await activePage.screenshot({ path: warningPath, fullPage: false, animations: "disabled", caret: "hide" });
        const warningScreenshot = recordScreenshot(warningPath, {
          kind: "interaction-state",
          scenario,
          state: "dismissible-warnings",
          theme: "light",
          viewport: { width: viewport.width, height: viewport.height },
        });
        captured.push(warningScreenshot);
        interactions.push({ state: "dismissible-warnings", screenshot: warningScreenshot.path });
      }
    }

    await dismissCardsNotices(activePage);
    await assertCleanMatrixState(activePage);
    const layout = await cardsPageGeometry(activePage);
    assertResponsiveMatrixGeometry(layout, viewport);
    const matrixPath = path.join(
      responsiveMatrixRoot,
      `cards-page-${viewport.name}-${viewport.width}x${viewport.height}-light.png`,
    );
    await activePage.screenshot({ path: matrixPath, fullPage: false, animations: "disabled", caret: "hide" });
    const matrixScreenshot = recordScreenshot(matrixPath, {
      kind: "responsive-matrix",
      scenario,
      theme: "light",
      viewport: { width: viewport.width, height: viewport.height },
    });
    captured.push(matrixScreenshot);
    matrix.push({
      name: viewport.name,
      viewport: { width: viewport.width, height: viewport.height },
      theme: "light",
      deviceScaleFactor: 1,
      fullPage: false,
      animations: "disabled",
      screenshot: matrixScreenshot.path,
      geometry: layout,
    });

    if (viewport === primaryEvidenceViewport) {
      const filterToggle = activePage.locator(".cards-inbox-filter-toggle");
      await filterToggle.click();
      await activePage.locator("#cards-inbox-filter-panel").waitFor({ state: "visible", timeout: 10000 });
      const filtersPath = path.join(interactionGalleryRoot, "02-filters-open-1920x1080-light.png");
      await activePage.screenshot({ path: filtersPath, fullPage: false, animations: "disabled", caret: "hide" });
      const filtersScreenshot = recordScreenshot(filtersPath, {
        kind: "interaction-state",
        scenario,
        state: "filters-open",
        theme: "light",
        viewport: { width: viewport.width, height: viewport.height },
      });
      captured.push(filtersScreenshot);
      interactions.push({ state: "filters-open", screenshot: filtersScreenshot.path });
      await filterToggle.click();
      await activePage.locator("#cards-inbox-filter-panel").waitFor({ state: "detached", timeout: 10000 });

      const coverage = activePage.locator(".cards-inbox-coverage > summary");
      await coverage.click();
      await activePage.locator(".cards-inbox-coverage[open]").waitFor({ state: "visible", timeout: 10000 });
      const coveragePath = path.join(interactionGalleryRoot, "03-coverage-open-1920x1080-light.png");
      await activePage.screenshot({ path: coveragePath, fullPage: false, animations: "disabled", caret: "hide" });
      const coverageScreenshot = recordScreenshot(coveragePath, {
        kind: "interaction-state",
        scenario,
        state: "coverage-open",
        theme: "light",
        viewport: { width: viewport.width, height: viewport.height },
      });
      captured.push(coverageScreenshot);
      interactions.push({ state: "coverage-open", screenshot: coverageScreenshot.path });
      await coverage.click();

      await activePage.locator(".cards-detail-expand").click();
      const expanded = activePage.locator('[data-testid="cards-preview-modal"]');
      await expanded.waitFor({ state: "visible", timeout: 30000 });
      await waitForExactShadow(activePage, "expanded", "back");
      const expandedPath = path.join(interactionGalleryRoot, "04-expanded-answer-close-up-1920x1080-light.png");
      await capturePageClip(activePage, expanded, expandedPath);
      const expandedScreenshot = recordScreenshot(expandedPath, {
        kind: "expanded-answer-close-up",
        scenario,
        state: "expanded-answer",
        theme: "light",
        viewport: { width: viewport.width, height: viewport.height },
      });
      captured.push(expandedScreenshot);
      interactions.push({ state: "expanded-answer", screenshot: expandedScreenshot.path });
      await expanded.locator(".product-modal-close").click();
      await expanded.waitFor({ state: "detached", timeout: 10000 });

      await activePage.locator(".shared-refresh-button").click();
      const refreshNotice = activePage.locator(".cards-refresh-status.is-success:not(:empty)");
      await refreshNotice.waitFor({ state: "visible", timeout: 30000 });
      const refreshPath = path.join(interactionGalleryRoot, "05-refresh-notification-close-up-1920x1080-light.png");
      await capturePageClip(activePage, refreshNotice, refreshPath);
      const refreshScreenshot = recordScreenshot(refreshPath, {
        kind: "refresh-notification-close-up",
        scenario,
        state: "refresh-success",
        theme: "light",
        viewport: { width: viewport.width, height: viewport.height },
      });
      captured.push(refreshScreenshot);
      interactions.push({ state: "refresh-success", screenshot: refreshScreenshot.path });
      await refreshNotice.locator(".cards-notice-close").click();
      await activePage.waitForFunction(
        () => !document.querySelector(".cards-refresh-status:not(:empty)"),
        null,
        { timeout: 10000 },
      );

      await activePage.locator('[data-testid="theme-toggle"]').click();
      await activePage.waitForFunction(
        () => document.documentElement.dataset.theme === "dark"
          && document.querySelector('[data-shadow-preview="true"]')?.getAttribute("data-preview-night-mode") === "true",
        null,
        { timeout: 10000 },
      );
      const darkLayout = await cardsPageGeometry(activePage);
      assertNativeCardFillsFrame(darkLayout);
      const darkPath = path.join(interactionGalleryRoot, "06-native-card-fill-1920x1080-dark.png");
      await activePage.screenshot({ path: darkPath, fullPage: false, animations: "disabled", caret: "hide" });
      const darkScreenshot = recordScreenshot(darkPath, {
        kind: "interaction-state",
        scenario,
        state: "native-card-fill-dark",
        theme: "dark",
        viewport: { width: viewport.width, height: viewport.height },
      });
      captured.push(darkScreenshot);
      interactions.push({
        state: "native-card-fill-dark",
        screenshot: darkScreenshot.path,
        geometry: {
          nativeCard: darkLayout.nativeCard,
          nativeCardFrame: darkLayout.nativeCardFrame,
          nativeCardBackground: darkLayout.nativeCardBackground,
        },
      });
    }

    await activePage.close();
    await activeContext.close();
    activePage = null;
    activeContext = null;
    activeScenario = null;
  }

  assert(matrix.length === responsiveMatrixViewports.length, `responsive matrix is incomplete: ${JSON.stringify(matrix)}`);
  assert(
    matrix.every((item) => item.fullPage === false && item.deviceScaleFactor === 1),
    `responsive matrix contains full-page or scaled captures: ${JSON.stringify(matrix)}`,
  );
  return { matrix, interactions, screenshots: captured };
}

async function dismissCardsNotices(page) {
  const warningClose = page.locator(".cards-inbox-warning .cards-notice-close");
  while (await warningClose.count()) {
    await warningClose.first().click();
  }
  await page.locator(".cards-inbox-warning").waitFor({ state: "detached", timeout: 10000 }).catch(async () => {
    assert(await page.locator(".cards-inbox-warning").count() === 0, "Cards warnings did not close");
  });
}

async function assertCleanMatrixState(page) {
  const state = await page.evaluate(() => ({
    notices: document.querySelectorAll(".cards-inbox-warning, .cards-refresh-status:not(:empty)").length,
    filtersOpen: Boolean(document.querySelector("#cards-inbox-filter-panel")),
    coverageOpen: Boolean(document.querySelector(".cards-inbox-coverage[open]")),
    modalOpen: Boolean(document.querySelector('[data-testid="cards-preview-modal"]')),
  }));
  assert(
    state.notices === 0 && !state.filtersOpen && !state.coverageOpen && !state.modalOpen,
    `responsive matrix contains transient UI: ${JSON.stringify(state)}`,
  );
}

async function cardsPageGeometry(page) {
  return page.evaluate(() => {
    const elementRect = (element) => {
      if (!(element instanceof HTMLElement)) return null;
      const value = element.getBoundingClientRect();
      return { x: value.x, y: value.y, width: value.width, height: value.height, right: value.right, bottom: value.bottom };
    };
    const rect = (selector) => {
      const element = document.querySelector(selector);
      return elementRect(element);
    };
    const previewHost = document.querySelector('[data-testid="cards-inspector"] [data-shadow-preview="true"]');
    const nativeRoot = previewHost?.shadowRoot ?? null;
    const nativeCard = nativeRoot?.querySelector('[data-testid="asr-shadow-card"]') ?? null;
    const nativeCardFrame = nativeRoot?.querySelector('[data-testid="asr-shadow-card-frame"]') ?? null;
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      document: {
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
      },
      workspace: rect(".cards-inbox-workspace"),
      queue: rect(".cards-inbox-queue"),
      inspector: rect('[data-testid="cards-inspector"]'),
      previewFrame: rect(".cards-detail-preview-frame"),
      previewHost: rect('[data-testid="cards-inspector"] [data-shadow-preview="true"]'),
      nativeCard: elementRect(nativeCard),
      nativeCardFrame: elementRect(nativeCardFrame),
      nativeCardBackground: nativeCard instanceof HTMLElement ? getComputedStyle(nativeCard).backgroundColor : null,
    };
  });
}

function assertResponsiveMatrixGeometry(layout, viewport) {
  assert(
    layout.viewport.width === viewport.width && layout.viewport.height === viewport.height,
    `responsive viewport mismatch: expected=${viewport.width}x${viewport.height} actual=${JSON.stringify(layout.viewport)}`,
  );
  assert(layout.document.scrollWidth <= viewport.width, `responsive matrix has horizontal overflow: ${JSON.stringify(layout)}`);
  assert(layout.document.scrollHeight <= viewport.height, `responsive matrix stretches below the viewport: ${JSON.stringify(layout)}`);
  assert(layout.workspace && layout.workspace.height >= 680 && layout.workspace.height <= 842, `workspace height is unbounded: ${JSON.stringify(layout)}`);
  assert(layout.workspace.width <= 2304, `workspace width exceeds the Cards contract: ${JSON.stringify(layout)}`);
  assert(layout.queue && layout.inspector && Math.abs(layout.queue.height - layout.inspector.height) <= 1, `queue/inspector heights diverge: ${JSON.stringify(layout)}`);
  assert(layout.previewFrame && layout.previewHost, `preview geometry is missing: ${JSON.stringify(layout)}`);
  assert(layout.previewHost.height <= layout.previewFrame.height, `native preview exceeds its frame: ${JSON.stringify(layout)}`);
  assert(layout.previewFrame.bottom <= layout.inspector.bottom + 1, `preview frame escapes the inspector: ${JSON.stringify(layout)}`);
  assertNativeCardFillsFrame(layout);
}

function assertNativeCardFillsFrame(layout) {
  assert(layout.nativeCard && layout.nativeCardFrame, `native card canvas geometry is missing: ${JSON.stringify(layout)}`);
  assert(
    Math.abs(layout.nativeCard.width - layout.nativeCardFrame.width) <= 1,
    `native card background does not fill the preview width: ${JSON.stringify(layout)}`,
  );
  assert(
    Math.abs(layout.nativeCard.height - layout.nativeCardFrame.height) <= 1,
    `native card background does not fill the preview height: ${JSON.stringify(layout)}`,
  );
}

function attachDiagnostics(page, scenario) {
  page.on("pageerror", (error) => pageErrors.push({
    scenario,
    errorType: String(error?.name || "Error"),
    message: safeText(error?.message || error),
  }));
  page.on("console", (message) => {
    consoleEvents.push({
      scenario,
      type: message.type(),
      text: safeText(message.text()),
      location: sanitizeLocation(message.location()),
    });
  });
  page.on("requestfailed", (request) => {
    if (!request.url().includes("favicon")) {
      failedRequests.push({
        scenario,
        path: safeUrlPath(request.url()),
        method: request.method(),
        error: safeText(request.failure()?.errorText || ""),
      });
    }
  });
  page.on("request", (request) => {
    const url = new URL(request.url());
    const item = { scenario, path: url.pathname, method: request.method(), resourceType: request.resourceType() };
    requestLedger.push(item);
    if (!["data:", "blob:", "about:"].includes(url.protocol) && url.origin !== base.origin) {
      externalRequests.push({ scenario, origin: url.origin, path: url.pathname, method: request.method() });
    }
    if (url.pathname.startsWith("/api/inspection-profiles")) {
      inspectionProfileRequests.push({ scenario, path: url.pathname, method: request.method() });
    }
  });
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname === "/api/media") {
      mediaResponses.push({
        scenario,
        name: url.searchParams.get("name") || "",
        status: response.status(),
        contentType: response.headers()["content-type"] || "",
      });
    }
  });
}

async function installThemeBootstrap(page) {
  await page.addInitScript(() => {
    const theme = new URLSearchParams(window.location.search).get("e2eTheme");
    if (!theme) return;
    localStorage.setItem("anki-study-report-theme", theme);
    const apply = () => {
      if (!document.documentElement) return false;
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
      return true;
    };
    if (!apply()) document.addEventListener("DOMContentLoaded", apply, { once: true });
  });
}

async function openCards(page, theme) {
  const query = new URLSearchParams({ token, e2eTheme: theme });
  await page.goto(`${ready.baseUrl}/?${query.toString()}#/cards`, { waitUntil: "networkidle", timeout: 60000 });
  await page.locator("main").waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(() => window.location.hash === "#/cards", null, { timeout: 60000 });
  await dismissDialogs(page);
}

async function dismissDialogs(page) {
  for (let index = 0; index < 5; index += 1) {
    const dialog = page.locator('[role="dialog"]:visible').first();
    if (!(await dialog.count())) return;
    const button = dialog.getByRole("button", {
      name: /Понятно|Закрыть|Сохранить выбранное|Got it|Close|Save selected/i,
    }).first();
    if (await button.count()) {
      if (!(await button.isDisabled().catch(() => true))) await button.click();
      else await page.keyboard.press("Escape");
    } else {
      await page.keyboard.press("Escape");
    }
    await page.waitForTimeout(200);
  }
}

function exactHost(page, mode, kind = "") {
  if (mode === "expanded") {
    return page.locator('[data-testid="cards-preview-modal"] [data-testid="anki-card-shadow-preview"]').first();
  }
  const prefix = kind === "drawer"
    ? '[data-testid="cards-detail-drawer"] '
    : '[data-testid="cards-inspector"] ';
  return page.locator(`${prefix}[data-testid="anki-card-shadow-preview"]`).first();
}

async function waitForExactShadow(page, mode, expectedSide) {
  await page.waitForFunction(({ mode, expectedSide, config }) => {
    const scope = mode === "expanded"
      ? document.querySelector('[data-testid="cards-preview-modal"]')
      : document.querySelector('[data-testid="cards-detail-content"]');
    const host = scope?.querySelector(`[data-testid="anki-card-shadow-preview"][data-preview-mode="${mode}"]`);
    const root = host?.shadowRoot;
    if (!host || !root || host.dataset.previewSide !== expectedSide) return false;
    const mediaName = (src) => {
      try {
        const url = new URL(src, window.location.href);
        return url.searchParams.get("name") || decodeURIComponent(url.pathname.split("/").pop() || "");
      } catch {
        return "";
      }
    };
    const audio = root.querySelector("audio.asr-card-audio");
    const imageNames = [...root.querySelectorAll("img")].map((image) => mediaName(image.src));
    if (!audio || mediaName(audio.src) !== config.mp3 || !imageNames.includes(config.gif)) return false;
    if (expectedSide === "front") return !imageNames.includes(config.png);
    return imageNames.includes(config.png);
  }, {
    mode,
    expectedSide,
    config: { gif: config.gif.name, mp3: config.mp3.name, png: config.png.name },
  }, { timeout: 30000 });
}

async function shadowMetrics(page, mode) {
  return page.evaluate(({ mode, config }) => {
    const scope = mode === "expanded"
      ? document.querySelector('[data-testid="cards-preview-modal"]')
      : document.querySelector('[data-testid="cards-detail-content"]');
    const host = scope?.querySelector(`[data-testid="anki-card-shadow-preview"][data-preview-mode="${mode}"]`);
    const root = host?.shadowRoot;
    if (!host || !root) throw new Error(`Exact shadow host is missing for mode=${mode}`);
    const card = root.querySelector('[data-testid="asr-shadow-card"]');
    const shell = root.querySelector('[data-testid="asr-shadow-card-shell"]');
    const frame = root.querySelector('[data-testid="asr-shadow-card-frame"]');
    const viewport = root.querySelector('[data-testid="asr-shadow-card-viewport"]');
    const button = root.querySelector(".asr-card-replay-button");
    const wrapper = root.querySelector(".asr-card-replay");
    const audio = root.querySelector("audio.asr-card-audio");

    const mediaName = (src) => {
      const url = new URL(src, window.location.href);
      return url.searchParams.get("name") || decodeURIComponent(url.pathname.split("/").pop() || "");
    };
    const rect = (element) => {
      if (!element) return null;
      const value = element.getBoundingClientRect();
      return {
        x: value.x,
        y: value.y,
        width: value.width,
        height: value.height,
        top: value.top,
        right: value.right,
        bottom: value.bottom,
        left: value.left,
      };
    };
    const style = (element) => {
      if (!element) return null;
      const value = getComputedStyle(element);
      return {
        width: value.width,
        height: value.height,
        display: value.display,
        margin: value.margin,
        verticalAlign: value.verticalAlign,
        objectFit: value.objectFit,
        fontFamily: value.fontFamily,
        fontSize: value.fontSize,
        lineHeight: value.lineHeight,
      };
    };
    const visible = (element) => {
      if (!element) return false;
      const value = element.getBoundingClientRect();
      const computed = getComputedStyle(element);
      return value.width > 0 && value.height > 0 && computed.visibility !== "hidden" && computed.display !== "none";
    };
    const mediaMetric = (name) => {
      const element = [...root.querySelectorAll("img")].find((image) => mediaName(image.src) === name);
      if (!element) return null;
      return {
        name,
        complete: element.complete,
        naturalWidth: element.naturalWidth,
        naturalHeight: element.naturalHeight,
        rect: rect(element),
        style: style(element),
      };
    };
    const leafElements = [...root.querySelectorAll("*")].filter((element) => element.children.length === 0 && visible(element));
    const normalized = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const wordFocusCandidates = [...root.querySelectorAll(".word-focus")]
      .filter((element) => visible(element) && normalized(element.textContent) === config.word);
    const wordFocus = wordFocusCandidates[0] || null;
    const exampleCandidates = [...root.querySelectorAll(".example-item, .examples, .jp, .ru, .example-focus")]
      .filter((element) => visible(element) && normalized(element.textContent).length >= 4);
    const example = host.dataset.previewSide === "back"
      ? (exampleCandidates[0] || leafElements.find((element) => normalized(element.textContent).length >= 12) || null)
      : null;
    const gifElement = [...root.querySelectorAll("img")]
      .find((image) => mediaName(image.src) === config.gif);
    const pngElement = [...root.querySelectorAll("img")]
      .find((image) => mediaName(image.src) === config.png);
    const parts = [
      wrapper,
      button,
      gifElement,
      host.dataset.previewSide === "back" ? pngElement : null,
      wordFocus,
      example,
    ]
      .filter(Boolean)
      .map(rect)
      .filter(Boolean);
    const union = parts.length
      ? {
          x: Math.min(...parts.map((item) => item.left)),
          y: Math.min(...parts.map((item) => item.top)),
          left: Math.min(...parts.map((item) => item.left)),
          top: Math.min(...parts.map((item) => item.top)),
          right: Math.max(...parts.map((item) => item.right)),
          bottom: Math.max(...parts.map((item) => item.bottom)),
        }
      : null;
    if (union) {
      union.width = union.right - union.left;
      union.height = union.bottom - union.top;
    }

    const gif = mediaMetric(config.gif);
    const png = mediaMetric(config.png);
    const replayRect = rect(wrapper || button);
    const wordFocusRect = rect(wordFocus);
    const exampleRect = rect(example);
    return {
      mode,
      side: host.dataset.previewSide || "",
      host: rect(host),
      shell: rect(shell),
      frame: rect(frame),
      viewport: rect(viewport),
      card: rect(card),
      replay: {
        wrapperCount: root.querySelectorAll(".asr-card-replay").length,
        buttonCount: root.querySelectorAll(".asr-card-replay-button").length,
        replayClassCount: root.querySelectorAll(".replay-button").length,
        audioCount: root.querySelectorAll("audio.asr-card-audio").length,
        svgCount: root.querySelectorAll(".asr-card-replay-button svg").length,
        circleCount: root.querySelectorAll(".asr-card-replay-button svg circle").length,
        pathCount: root.querySelectorAll(".asr-card-replay-button svg path").length,
        wrapperRect: replayRect,
        buttonRect: rect(button),
        buttonStyle: style(button),
        audioName: audio ? mediaName(audio.src) : "",
        ariaLabel: button?.getAttribute("aria-label") || "",
        documentLanguage: document.documentElement.lang || "",
      },
      gif,
      png,
      wordFocus: {
        count: wordFocusCandidates.length,
        text: normalized(wordFocus?.textContent),
        rect: wordFocusRect,
        style: style(wordFocus),
      },
      example: { textLength: normalized(example?.textContent).length, rect: exampleRect, style: style(example) },
      compositionGroup: union,
      gaps: {
        audioToImage: replayRect && gif?.rect ? gif.rect.top - replayRect.bottom : null,
        imageToWordFocus: gif?.rect && wordFocusRect ? wordFocusRect.top - gif.rect.bottom : null,
        wordFocusToExample: wordFocusRect && exampleRect ? exampleRect.top - wordFocusRect.bottom : null,
        imageRowToExample: gif?.rect && exampleRect
          ? exampleRect.top - Math.max(gif.rect.bottom, wordFocusRect?.bottom || gif.rect.bottom)
          : null,
      },
      rawSoundMarkers: (card?.textContent?.match(/\[sound:/gi) || []).length,
      rawPlayMarkers: (card?.textContent?.match(/\[anki:play:/gi) || []).length,
      scripts: root.querySelectorAll("script").length,
      externalMedia: [...root.querySelectorAll("img,audio,video")].filter((element) => {
        const url = new URL(element.currentSrc || element.src, window.location.href);
        return !["data:", "blob:"].includes(url.protocol) && url.origin !== window.location.origin;
      }).length,
    };
  }, {
    mode,
    config: { word: config.word, gif: config.gif.name, mp3: config.mp3.name, png: config.png.name },
  });
}

function assertMediaGeometry(
  media,
  label,
  { expectedNatural = null, expectedComputed = null } = {},
) {
  assert(media, `${label}: media is missing`);
  assert(media.complete === true, `${label}: image is not complete`);

  const naturalWidth = Number(media.naturalWidth);
  const naturalHeight = Number(media.naturalHeight);
  assert(
    Number.isFinite(naturalWidth) && naturalWidth > 0
      && Number.isFinite(naturalHeight) && naturalHeight > 0,
    `${label}: intrinsic geometry is unavailable ${JSON.stringify(media)}`,
  );

  if (expectedNatural) {
    assert(
      naturalWidth === expectedNatural.width
        && naturalHeight === expectedNatural.height,
      `${label}: intrinsic geometry mismatch ${JSON.stringify({
        actual: { width: naturalWidth, height: naturalHeight },
        expected: expectedNatural,
      })}`,
    );
  }

  const computedWidth = Number.parseFloat(media.style?.width || "");
  const computedHeight = Number.parseFloat(media.style?.height || "");
  assert(
    Number.isFinite(computedWidth) && computedWidth > 0
      && Number.isFinite(computedHeight) && computedHeight > 0,
    `${label}: computed geometry is unavailable ${JSON.stringify(media.style)}`,
  );

  if (expectedComputed) {
    assert(
      Math.abs(computedWidth - expectedComputed.width) <= 1
        && Math.abs(computedHeight - expectedComputed.height) <= 1,
      `${label}: template geometry mismatch ${JSON.stringify({
        actual: { width: computedWidth, height: computedHeight },
        expected: expectedComputed,
      })}`,
    );
  }

  const naturalAspect = naturalWidth / naturalHeight;
  const computedAspect = computedWidth / computedHeight;
  assert(
    Math.abs(naturalAspect - computedAspect) <= 0.02,
    `${label}: aspect ratio was not preserved ${JSON.stringify({
      naturalAspect,
      computedAspect,
      naturalWidth,
      naturalHeight,
      computedWidth,
      computedHeight,
    })}`,
  );

  assert(
    media.rect && media.rect.width > 0 && media.rect.height > 0,
    `${label}: rendered rectangle is unavailable ${JSON.stringify(media.rect)}`,
  );
}

function assertExactMetrics(metrics, label) {
  const replay = metrics.replay;
  assert(
    replay.wrapperCount === 1 && replay.buttonCount === 1 && replay.replayClassCount === 1
      && replay.audioCount === 1 && replay.svgCount === 1 && replay.circleCount === 1 && replay.pathCount === 1,
    `${label}: replay structure mismatch ${JSON.stringify(replay)}`,
  );
  assert(replay.audioName === config.mp3.name, `${label}: wrong audio ${replay.audioName}`);
  const language = replay.documentLanguage.toLowerCase().startsWith("en")
    ? "en"
    : "ru";
  const expectedReplayLabel = language === "en"
    ? "Play audio"
    : "Воспроизвести аудио";
  assert(
    replay.ariaLabel === expectedReplayLabel,
    `${label}: localized replay label mismatch ${
      JSON.stringify({
        language: replay.documentLanguage,
        actual: replay.ariaLabel,
        expected: expectedReplayLabel,
      })
    }`,
  );
  assertMediaGeometry(metrics.gif, `${label} GIF`, {
    expectedNatural: { width: 160, height: 120 },
    expectedComputed: { width: 160, height: 120 },
  });
  if (metrics.side === "front") {
    assert(metrics.png === null, `${label}: answer-only PNG leaked into front preview`);
  } else if (metrics.side === "back") {
    assertMediaGeometry(metrics.png, `${label} PNG`);
  } else {
    throw new Error(`${label}: unexpected preview side ${metrics.side}`);
  }
  assert(
    metrics.wordFocus.count === 1 && metrics.wordFocus.text === config.word && metrics.wordFocus.rect,
    `${label}: exact word-focus geometry mismatch ${JSON.stringify(metrics.wordFocus)}`,
  );
  if (metrics.side === "back") {
    assert(metrics.example.rect, `${label}: back-side example geometry is unavailable`);
  } else {
    assert(metrics.example.rect === null, `${label}: front-side example geometry must be absent`);
  }
  assert(metrics.compositionGroup, `${label}: composition group geometry is unavailable`);
  assert(!metrics.rawSoundMarkers && !metrics.rawPlayMarkers && !metrics.scripts && !metrics.externalMedia, `${label}: safety metric failed`);
}

function geometryProjection(metrics) {
  const group = metrics.compositionGroup;
  const card = metrics.card;
  return {
    cardId: config.cardId,
    side: metrics.side,
    previewScale: 1,
    cardRect: card,
    audioButtonRect: metrics.replay.buttonRect,
    replayWrapperRect: metrics.replay.wrapperRect,
    imageRect: metrics.gif?.rect || metrics.png?.rect,
    gifRect: metrics.gif?.rect,
    pngRect: metrics.png?.rect,
    wordFocusRect: metrics.wordFocus.rect,
    exampleRect: metrics.example.rect,
    groupRect: group,
    audioToImageGap: metrics.gaps.audioToImage,
    imageToWordFocusGap: metrics.gaps.imageToWordFocus,
    wordFocusToExampleGap: metrics.gaps.wordFocusToExample,
    imageRowToExampleGap: metrics.gaps.imageRowToExample,
    groupCenterX: group ? group.left + group.width / 2 : null,
    groupCenterY: group ? group.top + group.height / 2 : null,
    cardCenterX: card ? card.left + card.width / 2 : null,
    cardCenterY: card ? card.top + card.height / 2 : null,
  };
}

async function proveReplayFocus(page, outputRoot, theme) {
  const host = exactHost(page, "preview", "wide");
  const button = host.locator(".asr-card-replay-button");
  const paddingPx = 8;

  await button.evaluate((element) => element.blur());
  const defaultPath = path.join(
    outputRoot,
    `replay-default-${theme}.png`,
  );
  const defaultBytes = await capturePageClip(
    page,
    button,
    defaultPath,
    paddingPx,
  );

  await button.focus();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");

  const keyboardFocused = await host.evaluate(
    (element) => (
      element.shadowRoot?.activeElement?.classList
        .contains("asr-card-replay-button") === true
    ),
  );
  assert(
    keyboardFocused,
    `${theme}: keyboard focus did not return to the replay button`,
  );

  const focusStyle = await host.evaluate((element) => {
    const replayButton = element.shadowRoot
      ?.querySelector(".asr-card-replay-button");
    if (!(replayButton instanceof HTMLButtonElement)) {
      throw new Error("replay button is unavailable for focus proof");
    }
    const computed = getComputedStyle(replayButton);
    return {
      outlineStyle: computed.outlineStyle,
      outlineWidth: computed.outlineWidth,
      outlineWidthPx: Number.parseFloat(computed.outlineWidth),
      outlineColor: computed.outlineColor,
      outlineOffset: computed.outlineOffset,
      boxShadow: computed.boxShadow,
    };
  });

  assert(
    Number.isFinite(focusStyle.outlineWidthPx)
      && focusStyle.outlineWidthPx >= 2
      && focusStyle.outlineStyle !== "none"
      && focusStyle.boxShadow !== "none",
    `${theme}: computed focus indicator is not strong enough: ${
      JSON.stringify(focusStyle)
    }`,
  );

  const focusPath = path.join(
    outputRoot,
    `replay-keyboard-focus-${theme}.png`,
  );
  const focusBytes = await capturePageClip(
    page,
    button,
    focusPath,
    paddingPx,
  );

  const defaultSha256 = crypto
    .createHash("sha256")
    .update(defaultBytes)
    .digest("hex");
  const focusSha256 = crypto
    .createHash("sha256")
    .update(focusBytes)
    .digest("hex");
  const screenshotDiffers = defaultSha256 !== focusSha256;

  assert(
    screenshotDiffers,
    `${theme}: replay focus screenshot matches the default capture`,
  );

  return {
    theme,
    keyboardFocused,
    paddingPx,
    focusStyle,
    defaultSha256,
    focusSha256,
    screenshotDiffers,
    screenshots: [
      recordScreenshot(defaultPath, {
        kind: "replay-default",
        scenario: `wide-${theme}`,
        theme,
        paddingPx,
      }),
      recordScreenshot(focusPath, {
        kind: "replay-keyboard-focus",
        scenario: `wide-${theme}`,
        theme,
        paddingPx,
      }),
    ],
  };
}

async function proveReplayLifecycle(page, outputRoot) {
  const host = exactHost(page, "preview", "wide");
  const button = host.locator(".asr-card-replay-button");

  await host.evaluate((element) => {
    const audio = element.shadowRoot.querySelector("audio.asr-card-audio");
    audio.pause();
    if (Number.isFinite(audio.duration) && audio.duration > 0.1) {
      audio.currentTime = 0.08;
    }
    const originalPlay = audio.play.bind(audio);
    window.__asrReplayProof = {
      playCalls: 0,
      playEvent: false,
      playingEvent: false,
      timeUpdateEvent: false,
      playEventCurrentTime: null,
      playingEventCurrentTime: null,
      promiseResolved: false,
      promiseRejected: false,
    };
    audio.play = () => {
      window.__asrReplayProof.playCalls += 1;
      const promise = originalPlay();
      Promise.resolve(promise).then(
        () => { window.__asrReplayProof.promiseResolved = true; },
        () => { window.__asrReplayProof.promiseRejected = true; },
      );
      return promise;
    };
    audio.addEventListener("play", () => {
      window.__asrReplayProof.playEvent = true;
      window.__asrReplayProof.playEventCurrentTime = audio.currentTime;
    }, { once: true });
    audio.addEventListener("playing", () => {
      window.__asrReplayProof.playingEvent = true;
      window.__asrReplayProof.playingEventCurrentTime = audio.currentTime;
    }, { once: true });
    audio.addEventListener("timeupdate", () => {
      window.__asrReplayProof.timeUpdateEvent = true;
    }, { once: true });
  });

  await button.click();
  await page.waitForFunction(() => {
    const proof = window.__asrReplayProof;
    return proof?.playEvent
      && proof?.playingEvent
      && proof?.promiseResolved;
  }, null, { timeout: 15000 });

  const playingPath = path.join(outputRoot, "replay-playing.png");
  await capturePageClip(page, button, playingPath, 8);
  await page.waitForTimeout(250);

  const first = await host.evaluate((element) => {
    const audio = element.shadowRoot.querySelector("audio.asr-card-audio");
    return {
      ...window.__asrReplayProof,
      currentTimeAfterWait: audio.currentTime,
      pausedAfterWait: audio.paused,
      readyState: audio.readyState,
      networkState: audio.networkState,
      duration: audio.duration,
      playedRanges: [...Array(audio.played.length)].map(
        (_, index) => [
          audio.played.start(index),
          audio.played.end(index),
        ],
      ),
    };
  });
  assert(
    first.playEventCurrentTime <= 0.03,
    `audio was not reset before first play event: ${
      JSON.stringify(first)
    }`,
  );

  const secondSetup = await host.evaluate(async (element) => {
    const audio = element.shadowRoot.querySelector(
      "audio.asr-card-audio",
    );

    const duration = Number(audio.duration);
    const minimumProgress = Number.isFinite(duration) && duration > 0
      ? Math.min(0.08, Math.max(0.03, duration * 0.15))
      : 0.05;
    const deadline = performance.now() + 5000;

    while (
      audio.currentTime < minimumProgress
      && !audio.ended
      && performance.now() < deadline
    ) {
      await new Promise((resolve) => setTimeout(resolve, 25));
    }

    audio.pause();

    const beforeClickCurrentTime = audio.currentTime;
    const timeRanges = (ranges) => (
      [...Array(ranges.length)].map((_, index) => [
        ranges.start(index),
        ranges.end(index),
      ])
    );

    window.__asrReplayProof.second = {
      minimumProgress,
      beforeClickCurrentTime,
      playEvent: false,
      playingEvent: false,
      playEventCurrentTime: null,
      playingEventCurrentTime: null,
    };

    audio.addEventListener("play", () => {
      window.__asrReplayProof.second.playEvent = true;
      window.__asrReplayProof.second.playEventCurrentTime =
        audio.currentTime;
    }, { once: true });

    audio.addEventListener("playing", () => {
      window.__asrReplayProof.second.playingEvent = true;
      window.__asrReplayProof.second.playingEventCurrentTime =
        audio.currentTime;
    }, { once: true });

    return {
      minimumProgress,
      beforeClickCurrentTime,
      duration,
      ended: audio.ended,
      paused: audio.paused,
      seeking: audio.seeking,
      readyState: audio.readyState,
      networkState: audio.networkState,
      seekableRanges: timeRanges(audio.seekable),
      playedRanges: timeRanges(audio.played),
    };
  });

  assert(
    secondSetup.paused === true
      && secondSetup.seeking === false
      && secondSetup.beforeClickCurrentTime
        >= secondSetup.minimumProgress,
    `first playback did not advance before second replay: ${
      JSON.stringify(secondSetup)
    }`,
  );

  await button.click();

  await page.waitForFunction(() => {
    const proof = window.__asrReplayProof;
    return proof?.playCalls >= 2
      && proof?.second?.playEvent
      && proof?.second?.playingEvent;
  }, null, { timeout: 10000 });

  const second = await host.evaluate(
    (element, setup) => {
      const audio = element.shadowRoot.querySelector(
        "audio.asr-card-audio",
      );
      const proof = window.__asrReplayProof;
      const value = proof.second;

      return {
        ...setup,
        ...value,
        playCalls: proof.playCalls,
        currentTimeAfterPlay: audio.currentTime,
        resetObserved:
          value.beforeClickCurrentTime
            >= value.minimumProgress
          && value.playEventCurrentTime !== null
          && value.playEventCurrentTime <= 0.03,
      };
    },
    secondSetup,
  );

  assert(
    second.resetObserved === true,
    `second replay was not reset before play: ${
      JSON.stringify(second)
    }`,
  );

  const pageErrorsBeforeRejection = pageErrors.length;
  await host.evaluate((element) => {
    const audio = element.shadowRoot.querySelector("audio.asr-card-audio");
    audio.play = () => Promise.reject(
      new DOMException(
        "intentional E2E rejection",
        "NotAllowedError",
      ),
    );
  });
  await button.click();
  await page.waitForTimeout(250);
  const rejectedPromiseHandled =
    pageErrors.length === pageErrorsBeforeRejection;

  const response = [...mediaResponses]
    .reverse()
    .find((item) => item.name === config.mp3.name);
  return {
    first,
    second,
    playCalls: second.playCalls,
    mediaHttp200: response?.status === 200,
    rejectedPromiseHandled,
    screenshots: [
      recordScreenshot(playingPath, {
        kind: "replay-playing",
        scenario: "wide-light",
        theme: "light",
        paddingPx: 8,
      }),
    ],
  };
}

function proveGifAnimation(frameRows) {
  const expectedCount = buildScenarios(config).length;
  assert(
    frameRows.length === expectedCount,
    `GIF scenario capture count mismatch: ${
      JSON.stringify({
        actual: frameRows.length,
        expected: expectedCount,
      })
    }`,
  );

  for (const frame of frameRows) {
    assert(
      frame.complete === true
        && frame.naturalWidth === 160
        && frame.naturalHeight === 120,
      `GIF scenario readiness mismatch: ${JSON.stringify(frame)}`,
    );
  }

  const grouped = new Map();
  for (const frame of frameRows) {
    const width = Math.round(frame.renderedWidth);
    const height = Math.round(frame.renderedHeight);
    const key = `${frame.theme}:${width}x${height}`;
    const rows = grouped.get(key) || [];
    rows.push(frame);
    grouped.set(key, rows);
  }

  const comparisonGroups = [...grouped.entries()]
    .filter(([, rows]) => rows.length >= 2)
    .map(([key, rows]) => {
      const uniqueHashes = new Set(rows.map((item) => item.sha256));
      const timestamps = rows
        .map((item) => item.capturedAtEpochMs)
        .sort((left, right) => left - right);
      return {
        key,
        captureCount: rows.length,
        uniqueFrameCount: uniqueHashes.size,
        firstCaptureEpochMs: timestamps[0],
        lastCaptureEpochMs: timestamps.at(-1),
        elapsedMs: timestamps.at(-1) - timestamps[0],
        scenarios: rows.map((item) => item.scenario),
        hashes: [...uniqueHashes],
      };
    });

  const proofGroup = comparisonGroups.find(
    (group) => (
      group.captureCount >= 2
      && group.uniqueFrameCount >= 2
      && group.elapsedMs > 0
    ),
  );

  assert(
    proofGroup,
    `animated GIF cross-scenario captures did not differ: ${
      JSON.stringify(comparisonGroups)
    }`,
  );

  return {
    readiness: {
      captureCount: frameRows.length,
      complete: frameRows.every((item) => item.complete === true),
      naturalWidth: 160,
      naturalHeight: 120,
    },
    sourceGifSha256: config.gif.sha256,
    samplingMethod:
      "cross-scenario Playwright page.screenshot clip (animations=allow)",
    comparisonRule:
      "same theme and rounded rendered dimensions; at least two timestamps and two hashes",
    comparisonGroup: proofGroup.key,
    comparisonGroups,
    browserFramesDiffer: true,
    uniqueFrameCount: proofGroup.uniqueFrameCount,
    frames: frameRows.map((item) => ({
      ...item,
      path: relative(item.path),
    })),
    screenshots: frameRows.map((item) => ({
      path: relative(item.path),
      kind: "gif-browser-frame",
      scenario: item.scenario,
      theme: item.theme,
      side: item.side,
      capturedAtEpochMs: item.capturedAtEpochMs,
    })),
  };
}

async function extractDeterministicGifFrame(page, outputRoot) {
  const host = exactHost(page, "preview", "wide");
  const payload = await host.evaluate(async (element, gifName) => {
    const image = [...element.shadowRoot.querySelectorAll("img")].find((candidate) => {
      const url = new URL(candidate.src, window.location.href);
      const name = url.searchParams.get("name") || decodeURIComponent(url.pathname.split("/").pop() || "");
      return name === gifName;
    });
    if (!image) throw new Error(`GIF image not found: ${gifName}`);
    if (!("ImageDecoder" in window)) throw new Error("Chromium ImageDecoder is unavailable");
    if (!(await ImageDecoder.isTypeSupported("image/gif"))) throw new Error("Chromium ImageDecoder does not support image/gif");
    const response = await fetch(image.src, { cache: "no-store" });
    if (!response.ok) throw new Error(`GIF fetch failed: ${response.status}`);
    const data = new Uint8Array(await response.arrayBuffer());
    const decoder = new ImageDecoder({ data, type: "image/gif", preferAnimation: true });
    await decoder.tracks.ready;
    const track = decoder.tracks.selectedTrack;
    const decoded = await decoder.decode({ frameIndex: 0, completeFramesOnly: true });
    const frame = decoded.image;
    const canvas = document.createElement("canvas");
    canvas.width = frame.displayWidth;
    canvas.height = frame.displayHeight;
    const context = canvas.getContext("2d");
    context.drawImage(frame, 0, 0);
    const dataUrl = canvas.toDataURL("image/png");
    const result = {
      frameIndex: 0,
      frameCount: track.frameCount,
      repetitionCount: track.repetitionCount,
      width: frame.displayWidth,
      height: frame.displayHeight,
      durationMicroseconds: frame.duration,
      pngBase64: dataUrl.split(",", 2)[1],
    };
    frame.close();
    decoder.close();
    return result;
  }, config.gif.name);

  assert(payload.width === 160 && payload.height === 120, `fixed GIF frame geometry mismatch: ${JSON.stringify(payload)}`);
  assert(payload.frameCount > 1, `GIF is not animated: frameCount=${payload.frameCount}`);
  const bytes = Buffer.from(payload.pngBase64, "base64");
  const outputPath = path.join(outputRoot, "gif-fixed-frame-0.png");
  await fs.writeFile(outputPath, bytes);
  return {
    frameIndex: payload.frameIndex,
    frameCount: payload.frameCount,
    repetitionCount: payload.repetitionCount,
    durationMicroseconds: payload.durationMicroseconds,
    width: payload.width,
    height: payload.height,
    sourceGifSha256: config.gif.sha256,
    pngSha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    path: outputPath,
    relativePath: relative(outputPath),
    decoder: "Chromium ImageDecoder",
  };
}

async function capturePageClip(
  page,
  locator,
  outputPath,
  padding = 0,
) {
  await locator.evaluate(
    (element) => element.scrollIntoView({
      block: "center",
      inline: "center",
      behavior: "auto",
    }),
  );
  await page.waitForTimeout(100);
  const clip = await locator.evaluate((element, paddingValue) => {
    const rect = element.getBoundingClientRect();
    const documentElement = document.documentElement;
    const body = document.body;
    const documentWidth = Math.max(
      documentElement.scrollWidth,
      documentElement.clientWidth,
      body?.scrollWidth || 0,
      body?.clientWidth || 0,
    );
    const documentHeight = Math.max(
      documentElement.scrollHeight,
      documentElement.clientHeight,
      body?.scrollHeight || 0,
      body?.clientHeight || 0,
    );
    const resolvedPadding = Math.max(
      0,
      Number(paddingValue) || 0,
    );
    const left = Number(rect.left) + window.scrollX;
    const top = Number(rect.top) + window.scrollY;
    const right = left + Number(rect.width);
    const bottom = top + Number(rect.height);
    const x = Math.max(0, left - resolvedPadding);
    const y = Math.max(0, top - resolvedPadding);
    const clippedRight = Math.min(
      documentWidth,
      right + resolvedPadding,
    );
    const clippedBottom = Math.min(
      documentHeight,
      bottom + resolvedPadding,
    );
    const width = clippedRight - x;
    const height = clippedBottom - y;
    if (!(width > 0 && height > 0)) {
      throw new Error(
        `screenshot clip is unavailable: ${
          JSON.stringify({
            x,
            y,
            width,
            height,
            padding: resolvedPadding,
          })
        }`,
      );
    }
    return { x, y, width, height };
  }, padding);
  return page.screenshot({
    path: outputPath,
    animations: "allow",
    caret: "hide",
    clip,
  });
}

async function captureRect(page, value, outputPath) {
  assert(value && value.width > 0 && value.height > 0, `capture rect is unavailable: ${JSON.stringify(value)}`);
  const clip = await page.evaluate((rect) => {
    const documentElement = document.documentElement;
    const body = document.body;
    const documentWidth = Math.max(
      documentElement.scrollWidth,
      documentElement.clientWidth,
      body?.scrollWidth || 0,
      body?.clientWidth || 0,
    );
    const documentHeight = Math.max(
      documentElement.scrollHeight,
      documentElement.clientHeight,
      body?.scrollHeight || 0,
      body?.clientHeight || 0,
    );
    const left = Number(rect.left ?? rect.x);
    const top = Number(rect.top ?? rect.y);
    const x = Math.max(0, left + window.scrollX);
    const y = Math.max(0, top + window.scrollY);
    const width = Math.min(Number(rect.width), Math.max(1, documentWidth - x));
    const height = Math.min(Number(rect.height), Math.max(1, documentHeight - y));
    if (!(width > 0 && height > 0)) {
      throw new Error(`screenshot clip is unavailable: ${JSON.stringify({ x, y, width, height })}`);
    }
    return { x, y, width, height };
  }, value);
  return page.screenshot({ path: outputPath, animations: "allow", caret: "hide", clip });
}

async function createContactSheet(browserInstance, outputPath, allScreenshots) {
  const selectedKinds = new Set([
    "full-page",
    "media-block",
    "replay-default",
    "replay-keyboard-focus",
    "replay-playing",
    "gif-browser-frame",
    "gif-fixed-frame",
    "responsive-matrix",
    "interaction-state",
    "expanded-answer-close-up",
    "refresh-notification-close-up",
  ]);
  const selected = allScreenshots.filter((item) => selectedKinds.has(item.kind));
  const cards = [];
  for (const item of selected) {
    const absolute = path.join(artifactRoot, item.path);
    const bytes = await fs.readFile(absolute);
    cards.push({
      label: [item.kind, item.scenario, item.theme].filter(Boolean).join(" · "),
      data: `data:image/png;base64,${bytes.toString("base64")}`,
    });
  }
  const page = await browserInstance.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  try {
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
      body{font-family:system-ui,sans-serif;margin:0;padding:24px;background:#f5f5f5;color:#111}
      h1{margin:0 0 20px;font-size:28px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
      figure{margin:0;background:#fff;border:1px solid #ccc;border-radius:12px;padding:12px;break-inside:avoid}
      img{display:block;width:100%;height:auto;max-height:720px;object-fit:contain;background:#eee}
      figcaption{font-size:13px;font-weight:600;margin-top:8px;overflow-wrap:anywhere}
    </style></head><body><h1>Cards exact AV/media — production contact sheet</h1><div class="grid">${
      cards.map((item) => `<figure><img src="${item.data}" alt=""><figcaption>${escapeHtml(item.label)}</figcaption></figure>`).join("")
    }</div></body></html>`, { waitUntil: "load" });
    await page.screenshot({ path: outputPath, fullPage: true, animations: "allow", caret: "hide" });
  } finally {
    await page.close();
  }
}

async function writeReports() {
  const report = {
    schemaVersion: 1,
    status,
    cardId: Number(config.cardId),
    word: config.word,
    config: {
      themes: config.themes,
      viewports: config.viewports,
      media: { gif: config.gif, mp3: config.mp3, png: config.png },
      browser: { headless: true, deviceScaleFactor: 1, locale: "en-US", timezone: "UTC" },
    },
    scenarios,
    responsiveMatrix,
    interactionGallery,
    replay: replayProof
      ? { ...replayProof, focus: replayFocusProofs }
      : null,
    animation: gifProof,
    deterministicFrame: fixedFrameProof ? { ...fixedFrameProof, path: fixedFrameProof.relativePath, relativePath: undefined } : null,
    mediaResponses,
    screenshots,
    externalRequests: externalRequests.length,
    inspectionProfilesRequests: inspectionProfileRequests.length,
    pageErrors: pageErrors.length,
    consoleErrors: consoleEvents.filter((item) => item.type === "error").length,
    failedRequests: failedRequests.length,
    failure,
  };
  const pageConsole = {
    schemaVersion: 1,
    status,
    pageErrors,
    consoleEvents,
    unexpectedConsoleErrors: consoleEvents.filter((item) => item.type === "error"),
  };
  const requests = {
    schemaVersion: 1,
    status,
    requests: requestLedger,
    mediaResponses,
    failedRequests,
    externalRequests,
    inspectionProfileRequests,
  };
  const geometryReport = {
    schemaVersion: 1,
    status,
    cardId: Number(config.cardId),
    tolerancePx: 4,
    metrics: geometry,
  };
  for (const [target, value] of [
    [exactBrowserPath, report],
    [pageConsolePath, pageConsole],
    [requestLedgerPath, requests],
    [geometryPath, geometryReport],
  ]) {
    const serialized = JSON.stringify(value, null, 2) + "\n";
    assert(!serialized.includes(token) && !/[?&](?:access_)?token=/.test(serialized), `token leaked into ${path.basename(target)}`);
    await fs.writeFile(target, serialized, "utf8");
  }
}

function recordScreenshot(absolutePath, metadata) {
  return { path: relative(absolutePath), ...metadata };
}

function relative(value) {
  return path.relative(artifactRoot, value).split(path.sep).join("/");
}

function safeUrlPath(value) {
  try {
    const url = new URL(value);
    return url.pathname;
  } catch {
    return "[invalid-url]";
  }
}

function sanitizeLocation(value) {
  if (!value || typeof value !== "object") return {};
  return { lineNumber: value.lineNumber ?? null, columnNumber: value.columnNumber ?? null };
}

function safeText(value) {
  return String(value || "")
    .replace(/[\r\n\t\0]+/g, " ")
    .replace(/https?:\/\/\S+/gi, "[URL]")
    .replace(/(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/])\S*/g, "[PRIVATE_PATH]")
    .replace(/\/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:\/\S*)?/g, "[PRIVATE_PATH]")
    .replace(/([?&](?:access_)?token=)[^&\s]+/gi, "$1[REDACTED]")
    .trim()
    .replace(/\s+/g, " ")
    .slice(0, 500);
}

function safeName(value) {
  return String(value || "unknown").replace(/[^A-Za-z0-9_.-]/g, "-").slice(0, 80);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
