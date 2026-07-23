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
const root = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts";
const reportsDir = path.join(root, "reports");
const screenshotsDir = path.join(root, "screenshots");
const readyPath = process.env.ANKI_STUDY_REPORT_E2E_READY_FILE || path.join(root, "runtime", "dashboard-ready.json");
const ready = JSON.parse(await fs.readFile(readyPath, "utf8"));
const telemetryE2eEndpoint = process.env.ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT || "";
const anchors = (JSON.parse(await fs.readFile(path.join(reportsDir, "anchor-resolution-report.json"), "utf8"))).anchors;
const scenarios = JSON.parse(await fs.readFile(path.join(reportsDir, "scenario-application-report.json"), "utf8"));
const previewAnchorIds = ["words-preview", "grammar-preview", "java-preview"];
const consoleEvents = [];
const pageErrors = [];
const failedRequests = [];
const externalRequests = [];
const screenshots = [];
const startedAt = Date.now();

console.log(`[real-decks] browser smoke: loading ${previewAnchorIds.length} preview anchors`);
const browser = await chromium.launch({ headless: true });
try {
  const dashboardPage = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  attachDiagnostics(dashboardPage);
  await installThemeBootstrap(dashboardPage);
  await captureDashboardRoutes(dashboardPage);
  const telemetryClientProof = telemetryE2eEndpoint ? await assertTelemetryClient(dashboardPage) : null;

  const previewProofs = [];
  for (const anchorId of previewAnchorIds) {
    const anchor = anchors[anchorId];
    const card = await inspectCard(dashboardPage, anchorId, anchor);
    previewProofs.push(await captureNativePreview(anchorId, anchor, card));
  }

  const stateProof = await assertScenarioCards(dashboardPage);
  const cardsRouteProof = await inspectCardsRoute(dashboardPage);

  const actionableFailures = failedRequests.filter((item) => !item.url.includes("favicon"));
  assert(pageErrors.length === 0, `Browser page errors: ${pageErrors.join("\n")}`);
  assert(actionableFailures.length === 0, `Browser request failures: ${JSON.stringify(actionableFailures)}`);
  assert(externalRequests.length === 0, `Unexpected external requests: ${JSON.stringify(externalRequests)}`);
  const consoleErrors = consoleEvents.filter((event) => event.type === "error");
  assert(consoleErrors.length === 0, `Browser console errors: ${JSON.stringify(consoleErrors)}`);

  const performance = {
    schemaVersion: 1,
    label,
    durationMs: Date.now() - startedAt,
    screenshotCount: screenshots.length,
    configuredWorkers: Number(process.env.ANKI_E2E_SCREENSHOT_WORKERS || 1),
    mode: process.env.E2E_MODE || "standard",
    scope: process.env.ANKI_E2E_SCOPE || "full",
  };
  await writeJson(path.join(reportsDir, `browser-smoke-${label}.json`), {
    ok: true,
    label,
    anchors: previewProofs,
    scenarioCards: stateProof,
    cardsRoute: cardsRouteProof,
    telemetryClient: telemetryClientProof,
    screenshots,
    consoleEvents,
    pageErrors,
    failedRequests: actionableFailures,
    unexpectedExternalRequests: externalRequests,
    screenshotPerformance: performance,
  });
  await writeJson(path.join(reportsDir, "screenshot-performance.json"), performance);
  await fs.writeFile(
    path.join(reportsDir, "screenshot-performance.md"),
    `# Screenshot performance\n\n- Status: PASS\n- Screenshots: ${screenshots.length}\n- Duration: ${performance.durationMs} ms\n- Workers: ${performance.configuredWorkers}\n`,
    "utf8",
  );
  console.log(`[real-decks] browser smoke PASS: screenshots=${screenshots.length} external=0`);
} catch (error) {
  await writeJson(path.join(reportsDir, `browser-smoke-${label}.json`), {
    ok: false,
    label,
    error: String(error?.stack || error?.message || error),
    screenshots,
    consoleEvents,
    pageErrors,
    failedRequests,
    unexpectedExternalRequests: externalRequests,
  });
  throw error;
} finally {
  await browser.close();
}

function attachDiagnostics(page) {
  page.on("console", (message) => {
    consoleEvents.push({ type: message.type(), text: message.text(), location: message.location() });
  });
  page.on("pageerror", (error) => pageErrors.push(String(error?.stack || error?.message || error)));
  page.on("requestfailed", (request) => {
    failedRequests.push({ url: redactUrl(request.url()), method: request.method(), error: request.failure()?.errorText || "" });
  });
  page.on("request", (request) => {
    const url = new URL(request.url());
    const base = new URL(ready.baseUrl);
    if (!["data:", "blob:", "about:"].includes(url.protocol) && url.origin !== base.origin) {
      externalRequests.push({ url: `${url.origin}${url.pathname}`, method: request.method() });
    }
  });
}

async function installThemeBootstrap(page) {
  await page.addInitScript(() => {
    const selectedTheme = new URLSearchParams(window.location.search).get("e2eTheme");
    if (!selectedTheme) return;
    localStorage.setItem("anki-study-report-theme", selectedTheme);
    const applyTheme = () => {
      const root = document.documentElement;
      if (!root) return false;
      root.dataset.theme = selectedTheme;
      root.style.colorScheme = selectedTheme;
      return true;
    };
    if (!applyTheme()) {
      document.addEventListener("DOMContentLoaded", applyTheme, { once: true });
    }
  });
}


async function assertTelemetryClient(page) {
  const fakeState = async () => {
    const response = await fetch(`${telemetryE2eEndpoint}/__e2e/state`);
    assert(response.ok, "Telemetry fake state endpoint is reachable");
    return response.json();
  };
  const controlFake = async (offline) => {
    const response = await fetch(`${telemetryE2eEndpoint}/__e2e/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offline }),
    });
    assert(response.ok, "Telemetry fake control endpoint accepted the bounded state change");
    return response.json();
  };
  const dashboardPost = (requestPath, payload) => page.evaluate(async ({ requestPath, payload }) => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const response = await fetch(`${requestPath}?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    return { status: response.status, body: await response.json() };
  }, { requestPath, payload });
  const waitFor = async (predicate, description) => {
    const deadline = Date.now() + 15000;
    let state;
    do {
      state = await fakeState();
      if (predicate(state)) return state;
      await new Promise((resolve) => setTimeout(resolve, 100));
    } while (Date.now() < deadline);
    throw new Error(`Timed out waiting for ${description}: ${JSON.stringify(state)}`);
  };
  const emitMany = async (event, count) => {
    const started = Date.now();
    for (let index = 0; index < count; index += 1) {
      const result = await dashboardPost("/api/telemetry/events", event);
      assert(result.status === 200 && result.body?.ok === true, "Local telemety bridge accepts a bounded semantic event");
    }
    return Date.now() - started;
  };
  const privacy = (reliabilityDiagnostics, featureUsage) => dashboardPost("/api/privacy", {
    purposes: { reliabilityDiagnostics, featureUsage },
  });

  const declined = await fakeState();
  assert(declined.enrollments === 0 && declined.eventCount === 0, "Declined consent produces zero outbound telemetry requests");

  const reliabilityChoice = await privacy(true, false);
  assert(reliabilityChoice.status === 200, "Reliability-only consent is persisted through the local API");
  const disabledFeature = await dashboardPost("/api/telemetry/events", {
    eventCode: "dashboard.opened",
    occurredAt: new Date().toISOString(),
  });
  assert(disabledFeature.body?.queued === false, "Feature event is a quiet no-op when only reliability is enabled");
  const reliabilityDurationMs = await emitMany({
    eventCode: "api_operation.failed",
    featureCode: "dashboard_start",
    errorCode: "internal_error",
    occurredAt: new Date().toISOString(),
  }, 25);
  const afterReliability = await waitFor(
    (state) => state.eventPurposes?.reliabilityDiagnostics >= 25,
    "reliability-only batch delivery",
  );
  assert(afterReliability.eventPurposes.featureUsage === 0, "Reliability-only consent sends no feature-usage event");

  const featureChoice = await privacy(false, true);
  assert(featureChoice.status === 200, "Feature-only consent is persisted through the local API");
  const disabledReliability = await dashboardPost("/api/telemetry/events", {
    eventCode: "addon.started",
    occurredAt: new Date().toISOString(),
  });
  assert(disabledReliability.body?.queued === false, "Reliability event is a quiet no-op when only feature usage is enabled");
  const featureDurationMs = await emitMany({
    eventCode: "page.opened",
    pageCode: "settings_privacy",
    occurredAt: new Date().toISOString(),
  }, 25);
  const afterFeature = await waitFor(
    (state) => state.eventPurposes?.featureUsage >= 25,
    "feature-only batch delivery",
  );
  assert(afterFeature.eventBatches >= 2, "Telemetry events are delivered in bounded batches");
  assert(reliabilityDurationMs < 5000 && featureDurationMs < 5000, "Telemetry queueing does not freeze the dashboard UI");

  await controlFake(true);
  const beforeOffline = await fakeState();
  await emitMany({
    eventCode: "dashboard.opened",
    occurredAt: new Date().toISOString(),
  }, 25);
  await new Promise((resolve) => setTimeout(resolve, 300));
  const localStatus = await page.evaluate(async () => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const response = await fetch(`/api/telemetry/status?token=${encodeURIComponent(token)}`, { cache: "no-store" });
    return response.json();
  });
  const afterOffline = await fakeState();
  assert(afterOffline.eventCount === beforeOffline.eventCount, "Offline fake ingestion accepts no event batch");
  assert(localStatus.telemetryClient?.pendingEventCount >= 25, "Offline telemety remains in the persistent local queue");

  return {
    declinedZeroOutbound: true,
    reliabilityOnly: true,
    featureOnly: true,
    eventBatchesBeforeOffline: afterFeature.eventBatches,
    pendingBeforeRestart: localStatus.telemetryClient.pendingEventCount,
    queueDurationsMs: { reliability: reliabilityDurationMs, feature: featureDurationMs },
    fakeSummary: afterOffline,
  };
}

async function captureDashboardRoutes(page) {
  const cases = [
    ["home", "/home"],
    ["cards", "/cards"],
    ["decks", "/decks"],
    ["profile", "/profile"],
    ["settings", "/settings"],
  ];
  for (const [name, route] of cases) {
    for (const theme of ["light", "dark"]) {
      await openDashboardRoute(page, route, theme);
      await assertDashboardRoute(page, route);
      await dismissDialogs(page);
      const filePath = path.join(screenshotsDir, "pages", name, `${theme}.png`);
      await saveScreenshot(page, filePath, { fullPage: true, kind: "page", route: `#${route}`, theme });
    }
  }
}

async function openDashboardRoute(page, route, theme) {
  const query = new URLSearchParams({ token: ready.token, e2eTheme: theme });
  await page.goto(`${ready.baseUrl}/?${query.toString()}#${route}`, { waitUntil: "networkidle", timeout: 60000 });
}

async function assertDashboardRoute(page, route) {
  await page.locator("main").waitFor({ state: "visible", timeout: 60000 });
  const expectedHash = `#${route}`;
  await page.waitForFunction((hash) => window.location.hash === hash, expectedHash, { timeout: 60000 });
  assert(await page.evaluate((hash) => window.location.hash === hash, expectedHash), `Dashboard route mismatch: expected ${expectedHash}`);
}

async function dismissDialogs(page) {
  for (let index = 0; index < 4; index += 1) {
    const dialog = page.locator('[role="dialog"]:visible').first();
    if (!(await dialog.count())) return;
    const understood = dialog.getByRole("button", { name: /Понятно|Закрыть|Сохранить выбранное/ }).first();
    if (await understood.count()) {
      if (!(await understood.isDisabled().catch(() => true))) await understood.click();
      else await page.keyboard.press("Escape");
    } else {
      await page.keyboard.press("Escape");
    }
    await page.waitForTimeout(200);
  }
}

async function inspectCard(page, anchorId, anchor) {
  return page.evaluate(async ({ token, selectedAnchorId, selectedAnchor }) => {
    const response = await fetch(`/api/search/inspect?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schemaVersion: 2,
        mode: "cards",
        cardId: String(selectedAnchor.cardId),
        requestId: `browser-real-deck-${selectedAnchorId}`,
      }),
    });
    const body = await response.json();
    if (!response.ok || body?.ok !== true || body?.response?.schemaVersion !== 2 || body?.response?.mode !== "cards") {
      throw new Error(`/api/search/inspect failed for ${selectedAnchorId}: ${response.status}`);
    }
    const details = body.response.details;
    if (!details || String(details.cardId) !== String(selectedAnchor.cardId)) {
      throw new Error(`/api/search/inspect returned the wrong card for ${selectedAnchorId}`);
    }
    return details;
  }, { token: ready.token, selectedAnchorId: anchorId, selectedAnchor: anchor });
}

async function captureNativePreview(anchorId, anchor, card) {
  const rendered = card.renderedPreview;
  assert(rendered && rendered.renderSource === "anki_native", `${anchorId} uses native Anki rendering`);
  assert(String(rendered.frontHtml || "").trim() && String(rendered.backHtml || "").trim(), `${anchorId} has front/back HTML`);
  const combined = `${rendered.frontHtml || ""}\n${rendered.backHtml || ""}\n${rendered.css || ""}`;
  assert(!combined.toLowerCase().includes("[sound:"), `${anchorId} has no raw sound marker`);
  assert(!combined.toLowerCase().includes("[anki:play:"), `${anchorId} has no raw Anki play marker`);
  for (const className of anchor.htmlClasses || []) assert(combined.includes(className), `${anchorId} includes ${className}`);

  const proof = { anchorId, cardId: anchor.cardId, noteId: anchor.noteId, noteTypeId: anchor.noteTypeId, renderSource: rendered.renderSource, screenshots: [] };
  for (const theme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
    attachDiagnostics(page);
    await page.setContent(`<!doctype html><html data-theme="${theme}"><head><meta charset="utf-8"><style>
      html{color-scheme:${theme};font-family:system-ui,sans-serif;background:${theme === "dark" ? "#111827" : "#f8fafc"};color:${theme === "dark" ? "#f8fafc" : "#0f172a"}}
      body{margin:0;padding:32px}.frame{max-width:1120px;margin:auto;border:1px solid ${theme === "dark" ? "#374151" : "#cbd5e1"};border-radius:16px;padding:24px;background:${theme === "dark" ? "#1f2937" : "#fff"}}
      h1{font-size:22px;margin:0 0 20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{min-width:0;border:1px solid ${theme === "dark" ? "#4b5563" : "#dbeafe"};border-radius:12px;padding:16px;overflow:auto}.label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;opacity:.65;margin-bottom:12px}.host{min-height:260px;overflow:auto}
      @media(max-width:900px){.grid{grid-template-columns:1fr}}
    </style></head><body><main class="frame"><h1>Real deck native preview — ${escapeHtml(anchorId)}</h1><div class="grid"><section class="panel"><div class="label">Front</div><div id="front" class="host"></div></section><section class="panel"><div class="label">Back</div><div id="back" class="host"></div></section></div></main></body></html>`);
    await page.evaluate(({ frontHtml, backHtml, css }) => {
      for (const [id, html] of [["front", frontHtml], ["back", backHtml]]) {
        const host = document.getElementById(id);
        const shadow = host.attachShadow({ mode: "open" });
        const style = document.createElement("style");
        style.textContent = css || "";
        const content = document.createElement("div");
        content.innerHTML = html || "";
        shadow.append(style, content);
      }
    }, { frontHtml: rendered.frontHtml, backHtml: rendered.backHtml, css: rendered.css });
    await page.waitForTimeout(500);
    const metrics = await page.evaluate(() => [...document.querySelectorAll(".host")].map((host) => ({
      scrollHeight: host.shadowRoot?.documentElement?.scrollHeight || host.scrollHeight,
      clientHeight: host.clientHeight,
      scriptCount: host.shadowRoot?.querySelectorAll("script").length || 0,
    })));
    assert(metrics.every((item) => item.scriptCount === 0), `${anchorId} preview contains no scripts`);
    const filePath = path.join(screenshotsDir, "cards", "real-decks", anchorId, `${theme}.png`);
    await saveScreenshot(page, filePath, { fullPage: true, kind: "cards", anchorId, theme, mode: "expanded-front-back" });
    proof.screenshots.push(relative(filePath));
    await page.close();
  }
  return proof;
}

async function assertScenarioCards(page) {
  const anchorIds = ["cards-action-recheck", "cards-low-success", "cards-suspended", "cards-buried"];
  const values = await page.evaluate(async ({ token, selected }) => {
    const response = await fetch(`/api/triage/query?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schemaVersion: 4,
        dataset: "search_workset",
        cardIds: selected.map((item) => String(item.cardId)),
        scope: { periodStartMs: 0, periodEndMs: 9007199254740991, deckIds: [] },
        limit: selected.length,
      }),
    });
    const body = await response.json();
    if (!response.ok || body?.ok !== true) throw new Error(`triage query failed: ${response.status}`);
    return body.response.items || [];
  }, { token: ready.token, selected: anchorIds.map((id) => anchors[id]) });
  const ids = new Set(values.map((item) => String(item.cardId)));
  assert(ids.has(String(anchors["cards-action-recheck"].cardId)), "action/recheck state is visible to triage");
  assert(ids.has(String(anchors["cards-low-success"].cardId)), "low-success state is visible to triage");
  const scenarioById = new Map((scenarios.scenarios || []).map((item) => [item.id, item]));
  assert(scenarioById.get("cards-suspended")?.after?.queue === -1, "suspended state applied to imported card");
  assert(scenarioById.get("cards-buried")?.after?.queue === -2, "buried state applied to imported card");
  assert(scenarios.contentMutation?.notesCreated === 0 && scenarios.contentMutation?.cardsCreated === 0, "scenario proof contains no cloned content");
  return { triageItemCount: values.length, anchorIds, suspendedQueue: -1, buriedQueue: -2, clonedCards: 0 };
}

async function inspectCardsRoute(page) {
  const result = {};
  for (const theme of ["light", "dark"]) {
    await openDashboardRoute(page, "/cards", theme);
    await assertDashboardRoute(page, "/cards");
    await dismissDialogs(page);
    await page.waitForTimeout(1000);
    const metrics = await page.evaluate(() => ({
      shadowHosts: document.querySelectorAll(".anki-card-shadow-preview").length,
      rawSoundMarkers: (document.body.innerText.match(/\[sound:/gi) || []).length,
      rawPlayMarkers: (document.body.innerText.match(/\[anki:play:/gi) || []).length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    }));
    assert(metrics.rawSoundMarkers === 0 && metrics.rawPlayMarkers === 0, `Cards ${theme} has no raw AV markers`);
    assert(!metrics.horizontalOverflow, `Cards ${theme} has no horizontal overflow`);
    const filePath = path.join(screenshotsDir, "states", "cards", "real-deck-inbox", `${theme}.png`);
    await saveScreenshot(page, filePath, { fullPage: true, kind: "state", route: "#/cards", state: "real-deck-inbox", theme });
    result[theme] = metrics;
  }
  return result;
}

async function saveScreenshot(page, filePath, metadata) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await page.screenshot({ path: filePath, fullPage: metadata.fullPage !== false });
  screenshots.push({ path: relative(filePath), ...metadata });
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function relative(filePath) {
  return path.relative(root, filePath).split(path.sep).join("/");
}

function redactUrl(value) {
  try {
    const url = new URL(value);
    url.searchParams.delete("token");
    return `${url.origin}${url.pathname}${url.search}`;
  } catch {
    return String(value).replace(/([?&]token=)[^&]+/gi, "$1<redacted>");
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
