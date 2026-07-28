import { readFile, writeFile, mkdir } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..", "..");
const baseUrl = requiredEnv("BASE_URL");
const evidenceRoot = requiredEnv("EVIDENCE_ROOT");
const prototypeRoot = requiredEnv("PROTOTYPE_ROOT");
const axeSource = readFileSync(requiredEnv("AXE_PATH"), "utf8");

const directories = {
  full: path.join(evidenceRoot, "production", "full-page"),
  regions: path.join(evidenceRoot, "production", "regions"),
  aria: path.join(evidenceRoot, "accessibility", "aria"),
  accessibility: path.join(evidenceRoot, "accessibility"),
  metrics: path.join(evidenceRoot, "metrics"),
  diagnostics: path.join(evidenceRoot, "diagnostics"),
  comparisons: path.join(evidenceRoot, "comparisons"),
};
await Promise.all(Object.values(directories).map((directory) => mkdir(directory, { recursive: true })));

const fingerprint = { algorithm: "sha256", value: "a".repeat(64) };
const checks = {
  japanese: [
    { checkId: "meaning-required", kind: "non_empty", roles: ["meaning"], mode: "any", priority: "high" },
    { checkId: "audio-required", kind: "contains_audio", roles: ["audio"], mode: "any", priority: "medium" },
  ],
  programming: [
    { checkId: "answer-required", kind: "non_empty", roles: ["answer"], mode: "any", priority: "high" },
    { checkId: "code-present", kind: "contains_image", roles: ["code"], mode: "any", priority: "low" },
  ],
  generic: [{ checkId: "front-required", kind: "non_empty", roles: ["question"], mode: "any", priority: "high" }],
};

function noteType({
  id,
  name,
  displayName = name,
  detectedKind,
  fields,
  mappings,
  profileChecks,
  state = "not_configured",
  templates = ["Card 1"],
}) {
  const refs = fields.map((field, ordinal) => ({ ordinal, name: field }));
  const storedProfile = state === "not_configured" ? null : {
    profileId: `note-type-${id}`,
    noteTypeId: id,
    noteTypeName: name,
    storedState: state === "disabled" ? "disabled" : state === "confirmed" || state === "needs_review" ? "confirmed" : "suggested",
    displayName,
    expectedFingerprint: fingerprint,
    appliesTo: { templateOrdinals: [] },
    fieldMappings: mappings.map(([role, field]) => ({ role, fields: [refs.find((ref) => ref.name === field)] })),
    checks: profileChecks,
    confirmedAt: state === "confirmed" || state === "needs_review" ? "2026-07-28T12:00:00Z" : null,
    updatedAt: "2026-07-28T12:00:00Z",
  };
  return {
    structure: {
      noteTypeId: id,
      name,
      kind: "standard",
      fields: refs,
      templates: templates.map((templateName, ordinal) => ({
        ordinal,
        name: templateName,
        frontFields: fields.slice(0, 1),
        backFields: fields.slice(1),
      })),
      fingerprint,
    },
    effectiveState: state,
    stateReason: state === "needs_review" ? "field_changed" : null,
    authoritative: state === "confirmed",
    storedProfile,
    suggestion: {
      detectedKind,
      confidence: 0.92,
      fieldMappings: mappings.map(([role, field]) => ({
        role,
        fields: [refs.find((ref) => ref.name === field)],
        confidence: 0.94,
      })),
      checks: profileChecks,
      warnings: [],
      unresolvedFields: [],
    },
  };
}

const japanese = noteType({
  id: "1",
  name: "Слова",
  displayName: "E2E Japanese Vocabulary",
  detectedKind: "japanese_vocab",
  fields: ["Слово", "Чтение", "Значение", "Аудио"],
  mappings: [["term", "Слово"], ["reading", "Чтение"], ["meaning", "Значение"], ["audio", "Аудио"]],
  profileChecks: checks.japanese,
  state: "confirmed",
  templates: ["Card 1", "Card 2"],
});
const java = noteType({
  id: "2",
  name: "Java",
  displayName: "E2E Programming",
  detectedKind: "programming",
  fields: ["Вопрос", "Ответ", "Код", "Пояснение"],
  mappings: [["question", "Вопрос"], ["answer", "Ответ"], ["code", "Код"], ["explanation", "Пояснение"]],
  profileChecks: checks.programming,
});
const longEnglish = noteType({
  id: "3",
  name: "Extremely long customer-facing note type name for overflow verification",
  displayName: "A deliberately long local inspection profile display name",
  detectedKind: "generic",
  fields: ["Front", "Back"],
  mappings: [["question", "Front"], ["answer", "Back"]],
  profileChecks: checks.generic,
  state: "suggested",
});
const fixtureItems = [
  japanese,
  java,
  longEnglish,
  noteType({ id: "4", name: "Грамматика", detectedKind: "japanese_grammar", fields: ["Правило", "Пример"], mappings: [["question", "Правило"], ["answer", "Пример"]], profileChecks: checks.generic, state: "needs_review" }),
  noteType({ id: "5", name: "Копия Грамматика", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic }),
  noteType({ id: "6", name: "Основная", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic, state: "disabled" }),
  noteType({ id: "7", name: "Basic", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic }),
  noteType({ id: "8", name: "Basic (and reversed card)", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic }),
  noteType({ id: "9", name: "Basic (optional reversed card)", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic }),
  noteType({ id: "10", name: "Cloze", detectedKind: "generic", fields: ["Text", "Extra"], mappings: [["question", "Text"], ["answer", "Extra"]], profileChecks: checks.generic }),
  noteType({ id: "11", name: "E2E Custom CSS", detectedKind: "generic", fields: ["Front", "Back"], mappings: [["question", "Front"], ["answer", "Back"]], profileChecks: checks.generic }),
];

function profilesResponse(fixture) {
  const items = fixture === "empty" ? [] : fixtureItems;
  const storeStatus = fixture === "store-unavailable" ? "unavailable" : items.some((item) => item.storedProfile) ? "available" : "empty";
  return {
    schemaVersion: 1,
    status: storeStatus === "unavailable" ? "unavailable" : "available",
    store: {
      status: storeStatus,
      revision: 4,
      profileCount: items.filter((item) => item.storedProfile).length,
      errorCode: storeStatus === "unavailable" ? "inspection_profiles_unavailable" : null,
      quarantined: false,
    },
    totalCount: items.length,
    returnedCount: items.length,
    limit: 500,
    truncated: false,
    skippedCount: 0,
    items,
  };
}

const preferences = {
  notificationCenterEnabled: true,
  showUnreadBadge: true,
  showInAppToasts: true,
  minimumToastSeverity: "critical",
  sound: "none",
  osNotifications: "none",
  toastCategories: { workload: true, retention: true, deck_health: true, card_problems: true, product_updates: true },
};
const productNotices = {
  ok: true,
  currentVersion: "0.0.0",
  notice: { schemaVersion: 1, firstObservedVersion: "0.0.0", lastStartedVersion: "0.0.0", lastSeenReleaseVersion: "0.0.0" },
  privacy: {
    schemaVersion: 1,
    requiresConsent: false,
    telemetry: {
      status: "declined",
      consentSchemaVersion: 1,
      privacyNoticeVersion: "2026-07-15",
      purposes: { reliabilityDiagnostics: false, featureUsage: false },
      effectivePurposes: { reliabilityDiagnostics: false, featureUsage: false },
      decidedAt: "2026-07-28T12:00:00Z",
      deletionPending: false,
      requiresConsent: false,
    },
  },
  requiresConsent: false,
  showWhatsNew: false,
  unseenReleaseVersions: [],
  changelog: { schemaVersion: 1, unreleased: { sections: [] }, releases: [] },
};

const report = {
  schemaVersion: 1,
  source: { repoRoot, harness: path.relative(repoRoot, fileURLToPath(import.meta.url)) },
  captures: [],
  regions: [],
  geometry: {},
  interactions: {},
  ariaSnapshots: [],
  axe: [],
  requests: [],
  responses: [],
  unexpectedRequests: [],
  requestFailures: [],
  expectedRequestAborts: [],
  consoleErrors: [],
  pageErrors: [],
  externalRequests: [],
};

function response(route, status, body) {
  return route.fulfill({ status, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
}

async function configureContext(context, scenario) {
  await context.addInitScript(({ theme, language }) => {
    localStorage.setItem("anki-study-report-theme", theme);
    localStorage.setItem("anki-study-report-language", language);
  }, scenario);
  await context.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname !== "127.0.0.1") {
      report.externalRequests.push({ scenario: scenario.id, method: request.method(), url: request.url() });
      return route.abort("blockedbyclient");
    }
    if (!url.pathname.startsWith("/api/")) return route.continue();
    const key = `${request.method()} ${url.pathname}`;
    report.requests.push({ scenario: scenario.id, key, query: [...url.searchParams.keys()].filter((name) => name !== "token").sort() });
    if (key === "GET /api/report") return response(route, 200, { metadata: {}, summary: {}, kpis: [] });
    if (key === "POST /api/telemetry/events") return response(route, 200, { ok: true, code: "telemetry.disabled", queued: false });
    if (key === "GET /api/product-notices") return response(route, 200, productNotices);
    if (key === "GET /api/notifications/summary") return response(route, 200, { ok: true, schemaVersion: 1, unreadCount: 0, activeSignalCount: 0, items: [] });
    if (key === "GET /api/notifications/toasts") return response(route, 200, { ok: true, schemaVersion: 1, items: [] });
    if (key === "GET /api/settings/notifications") return response(route, 200, { ok: true, schemaVersion: 1, preferences });
    if (key === "POST /api/inspection-profiles/query") {
      if (scenario.fixture === "loading") await new Promise((resolve) => setTimeout(resolve, 900));
      if (scenario.fixture === "load-error") return response(route, 200, { ok: false, error: "inspection_profiles_unavailable" });
      return response(route, 200, { ok: true, response: profilesResponse(scenario.fixture) });
    }
    report.unexpectedRequests.push({ scenario: scenario.id, key });
    return response(route, 599, { ok: false, error: "unexpected_visual_fixture_request" });
  });
}

async function openScenario(browser, scenario) {
  const context = await browser.newContext({
    viewport: { width: scenario.width, height: scenario.height },
    colorScheme: scenario.theme,
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
    locale: scenario.language === "ru" ? "ru-RU" : "en-US",
  });
  await configureContext(context, scenario);
  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") report.consoleErrors.push({ scenario: scenario.id, text: message.text() });
  });
  page.on("pageerror", (error) => report.pageErrors.push({ scenario: scenario.id, text: error.message }));
  page.on("requestfailed", (request) => {
    const failure = {
      scenario: scenario.id,
      method: request.method(),
      url: request.url().replace(/token=[^&]*/g, "token=<redacted>"),
      error: request.failure()?.errorText ?? "unknown",
    };
    if (scenario.fixture === "loading" && failure.error === "net::ERR_ABORTED") {
      report.expectedRequestAborts.push({ ...failure, reason: "Context closed after the loading-state capture." });
      return;
    }
    report.requestFailures.push(failure);
  });
  page.on("response", (browserResponse) => {
    const url = new URL(browserResponse.url());
    if (url.pathname.startsWith("/api/")) {
      report.responses.push({
        scenario: scenario.id,
        method: browserResponse.request().method(),
        path: url.pathname,
        status: browserResponse.status(),
      });
    }
  });
  await page.goto(`${baseUrl}/?token=visual-test#/settings/inspection-profiles`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-testid="settings-layout-shell"]').waitFor({ state: "visible" });
  await page.locator('[data-testid="settings-route-header-slot"] h1').waitFor({ state: "visible" });
  return { context, page };
}

async function prepareScenario(page, scenario) {
  if (scenario.fixture === "loading") {
    await page.getByText(scenario.language === "ru" ? "Загружаем типы записей…" : "Loading note types…").waitFor();
    return;
  }
  if (scenario.fixture === "load-error") {
    await page.getByRole("alert").filter({ hasText: scenario.language === "ru" ? "Не удалось загрузить профили" : "Inspection Profiles could not be loaded" }).waitFor();
    return;
  }
  if (scenario.fixture === "empty") {
    await page.getByText(scenario.language === "ru" ? "В коллекции нет доступных типов записей." : "No available note types were found in the collection.").waitFor();
    return;
  }
  await page.locator(".inspection-note-button").first().waitFor({ state: "visible" });
  if (scenario.fixture === "no-matches") {
    await page.locator("#inspection-profile-search").fill("no-such-note-type");
    await page.getByText(scenario.language === "ru" ? "По фильтрам ничего не найдено." : "No note types match these filters.").waitFor();
    return;
  }
  const noteName = scenario.select === "long" ? "Extremely long customer-facing" : scenario.select === "words" ? "Слова" : "Java";
  await page.locator(".inspection-note-button").filter({ hasText: noteName }).click();
  await page.locator("[data-testid='inspection-basic-editor']").waitFor({ state: "visible" });
  if (scenario.advanced || scenario.fixture === "dirty") {
    await page.getByRole("tab", { name: scenario.language === "ru" ? "Расширенное" : "Advanced" }).click();
    await page.locator("#inspection-advanced-panel").waitFor({ state: "visible" });
  }
  if (scenario.fixture === "dirty") {
    await page.locator("#inspection-profile-display-name").fill("Локально изменённый профиль");
    await page.getByText(scenario.language === "ru" ? "Несохранённые изменения" : "Unsaved changes").waitFor();
  }
  await page.locator(".inspection-note-button:focus").evaluate((element) => element.blur()).catch(() => undefined);
  await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });
  await page.waitForTimeout(60);
}

function rectangle(page, selector) {
  return page.locator(selector).evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {
      x: round(rect.x),
      y: round(rect.y),
      width: round(rect.width),
      height: round(rect.height),
      display: style.display,
      gridTemplateColumns: style.gridTemplateColumns,
      fontFamily: style.fontFamily,
    };
    function round(value) { return Math.round(value * 100) / 100; }
  }).catch(() => null);
}

async function geometry(page) {
  const selectors = {
    shell: ".settings-layout-shell",
    header: ".settings-route-header-slot",
    navigation: ".settings-nav-shell",
    content: ".settings-route-content",
    workspace: ".inspection-workspace",
    catalog: ".inspection-catalog",
    catalogControls: ".inspection-catalog-controls",
    selected: ".inspection-note-button.is-selected",
    editor: ".inspection-editor",
    identity: ".inspection-editor-identity",
    tabs: ".inspection-mode-switch",
  };
  const entries = await Promise.all(Object.entries(selectors).map(async ([name, selector]) => [name, await rectangle(page, selector)]));
  const font = await page.evaluate(() => {
    const measure = (text) => {
      const span = document.createElement("span");
      span.textContent = text;
      span.style.cssText = "position:fixed;left:-10000px;top:-10000px;font-size:16px;line-height:1;white-space:pre";
      span.style.fontFamily = getComputedStyle(document.body).fontFamily;
      document.body.append(span);
      const width = span.getBoundingClientRect().width;
      span.remove();
      return Math.round(width * 100) / 100;
    };
    const narrow = measure("iiiiiiiiii");
    const wide = measure("mmmmmmmmmm");
    return {
      body: getComputedStyle(document.body).fontFamily,
      narrowWidth: narrow,
      wideWidth: wide,
      monospaceDetected: Math.abs(wide - narrow) < 1,
    };
  });
  return {
    viewport: await page.evaluate(() => ({ width: innerWidth, height: innerHeight })),
    ...Object.fromEntries(entries),
    font,
    h1Count: await page.locator(".settings-layout-shell h1").count(),
    horizontalOverflow: await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth),
  };
}

async function capture(page, scenario) {
  const fullName = `${scenario.id}.png`;
  await page.screenshot({ path: path.join(directories.full, fullName), fullPage: false, animations: "disabled" });
  report.captures.push({ scenario: scenario.id, filename: fullName, width: scenario.width, height: scenario.height, theme: scenario.theme, language: scenario.language, fixture: scenario.fixture ?? "default" });
  if (scenario.fixture && scenario.fixture !== "dirty") {
    const ariaFilename = `${scenario.id}.aria.yml`;
    const aria = await page.locator('[data-testid="settings-layout-shell"]').ariaSnapshot();
    await writeFile(path.join(directories.aria, ariaFilename), `${aria}\n`, "utf8");
    report.ariaSnapshots.push(ariaFilename);
    return;
  }
  const regionSelectors = {
    header: ".settings-route-header-slot",
    workspace: ".inspection-workspace",
    catalog: ".inspection-catalog",
    controls: ".inspection-catalog-controls",
    selected: ".inspection-note-button.is-selected",
    editor: ".inspection-editor",
    identity: ".inspection-editor-identity",
    tabs: ".inspection-mode-switch",
  };
  for (const [region, selector] of Object.entries(regionSelectors)) {
    const locator = page.locator(selector);
    if (!await locator.count() || !await locator.first().isVisible()) continue;
    const filename = `${scenario.id}-${region}.png`;
    await locator.first().screenshot({ path: path.join(directories.regions, filename), animations: "disabled" });
    report.regions.push({ scenario: scenario.id, region, filename, box: await locator.first().boundingBox() });
  }
  const ariaFilename = `${scenario.id}.aria.yml`;
  const aria = await page.locator('[data-testid="settings-layout-shell"]').ariaSnapshot();
  await writeFile(path.join(directories.aria, ariaFilename), `${aria}\n`, "utf8");
  report.ariaSnapshots.push(ariaFilename);
}

async function runAxe(page, scenario) {
  await page.addScriptTag({ content: axeSource });
  const result = await page.evaluate(async () => {
    const axeResult = await window.axe.run({
      include: [['[data-testid="settings-layout-shell"]']],
      exclude: [[".inspection-note-meta"]],
    }, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] },
    });
    const contrastChecks = [...document.querySelectorAll(".inspection-note-meta")].map((element) => {
      const foreground = rgb(getComputedStyle(element).color);
      const background = rgb(getComputedStyle(element.parentElement).backgroundColor);
      const ratio = contrast(foreground, background);
      return {
        text: element.textContent?.trim() ?? "",
        foreground,
        background,
        ratio: Math.round(ratio * 100) / 100,
      };
    });
    return {
      violations: axeResult.violations,
      incomplete: axeResult.incomplete,
      passes: axeResult.passes.map((item) => item.id),
      inapplicable: axeResult.inapplicable.map((item) => item.id),
      scopeExclusions: [{
        selector: ".inspection-note-meta",
        reason: "Deque reports bgOverlap for grid metadata; every excluded node is checked below with computed foreground/background contrast.",
      }],
      contrastChecks,
    };
    function rgb(value) {
      const values = value.match(/[\d.]+/g)?.slice(0, 3).map(Number) ?? [];
      if (values.length !== 3) throw new Error(`Unsupported computed color: ${value}`);
      return values;
    }
    function luminance(color) {
      return color.map((value) => {
        const channel = value / 255;
        return channel <= .03928 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
      }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
    }
    function contrast(left, right) {
      const values = [luminance(left), luminance(right)].sort((a, b) => b - a);
      return (values[0] + .05) / (values[1] + .05);
    }
  });
  report.axe.push({ scenario: scenario.id, ...result });
  await writeFile(path.join(directories.accessibility, `axe-${scenario.id}.json`), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  if (result.violations.length || result.incomplete.length) {
    throw new Error(`${scenario.id}: axe expected 0 violations and 0 incomplete, got ${result.violations.length}/${result.incomplete.length}`);
  }
  if (result.contrastChecks.some((item) => item.ratio < 4.5)) {
    throw new Error(`${scenario.id}: catalog metadata computed contrast is below 4.5:1`);
  }
}

async function verifyTabs(page, language) {
  const basic = page.getByRole("tab", { name: language === "ru" ? "Основное" : "Basic" });
  await basic.focus();
  await basic.press("ArrowRight");
  const advanced = page.getByRole("tab", { name: language === "ru" ? "Расширенное" : "Advanced" });
  if (!await advanced.evaluate((element) => element === document.activeElement && element.getAttribute("aria-selected") === "true")) {
    throw new Error("ArrowRight did not select and focus Advanced");
  }
  await advanced.press("Home");
  if (!await basic.evaluate((element) => element === document.activeElement && element.getAttribute("aria-selected") === "true")) {
    throw new Error("Home did not select and focus Basic");
  }
  await basic.press("End");
  if (!await advanced.evaluate((element) => element === document.activeElement && element.getAttribute("aria-selected") === "true")) {
    throw new Error("End did not select and focus Advanced");
  }
  await advanced.press("ArrowLeft");
  if (!await basic.evaluate((element) => element === document.activeElement && element.getAttribute("aria-selected") === "true")) {
    throw new Error("ArrowLeft did not select and focus Basic");
  }
  report.interactions.tabs = { arrowRight: true, home: true, end: true, arrowLeft: true };
}

const scenarios = [
  { id: "1440-ru-light-java-basic", width: 1440, height: 900, theme: "light", language: "ru" },
  { id: "1440-ru-light-identity", width: 1440, height: 900, theme: "light", language: "ru", select: "words" },
  { id: "1440-ru-dark-java-advanced", width: 1440, height: 900, theme: "dark", language: "ru", advanced: true },
  { id: "1440-en-light-long-labels", width: 1440, height: 900, theme: "light", language: "en", select: "long" },
  { id: "1024-ru-light-compact", width: 1024, height: 768, theme: "light", language: "ru" },
  { id: "1024-en-dark-compact", width: 1024, height: 768, theme: "dark", language: "en" },
  { id: "2560-ru-light-advanced", width: 2560, height: 1440, theme: "light", language: "ru", advanced: true },
  { id: "1440-ru-light-loading", width: 1440, height: 900, theme: "light", language: "ru", fixture: "loading" },
  { id: "1440-ru-light-load-error", width: 1440, height: 900, theme: "light", language: "ru", fixture: "load-error" },
  { id: "1440-ru-light-store-unavailable", width: 1440, height: 900, theme: "light", language: "ru", fixture: "store-unavailable" },
  { id: "1440-ru-light-empty", width: 1440, height: 900, theme: "light", language: "ru", fixture: "empty" },
  { id: "1440-ru-light-no-matches", width: 1440, height: 900, theme: "light", language: "ru", fixture: "no-matches" },
  { id: "1440-ru-light-dirty", width: 1440, height: 900, theme: "light", language: "ru", fixture: "dirty" },
];

const browser = await chromium.launch({ headless: true });
for (const scenario of scenarios) {
  const { context, page } = await openScenario(browser, scenario);
  if (scenario.id === "1440-ru-light-java-basic" || scenario.id === "1024-en-dark-compact") {
    await page.locator(".inspection-note-button").first().waitFor({ state: "visible" });
    await runAxe(page, scenario);
  }
  await prepareScenario(page, scenario);
  const state = await geometry(page);
  report.geometry[scenario.id] = state;
  if (state.h1Count !== 1) throw new Error(`${scenario.id}: expected one H1, found ${state.h1Count}`);
  if (state.horizontalOverflow) throw new Error(`${scenario.id}: horizontal page overflow`);
  if (state.font.monospaceDetected) throw new Error(`${scenario.id}: computed body font behaves as monospace`);
  if (scenario.width === 1024 && state.catalog && state.editor && state.catalog.y !== state.editor.y) {
    throw new Error(`${scenario.id}: catalog and editor are not side by side`);
  }
  if (scenario.width === 2560 && state.editor?.width < 1500) throw new Error(`${scenario.id}: editor did not expand at QHD`);
  if (scenario.id === "1440-ru-light-java-basic") {
    await verifyTabs(page, scenario.language);
  }
  await capture(page, scenario);
  await context.close();
}

{
  const scenario = { id: "1024-ru-light-overflow", width: 1024, height: 768, theme: "light", language: "ru" };
  const { context, page } = await openScenario(browser, scenario);
  await prepareScenario(page, scenario);
  const trigger = page.locator('[data-testid="settings-overflow-trigger"]');
  await trigger.focus();
  await trigger.press("ArrowDown");
  const menu = page.locator('[data-testid="settings-overflow-menu"]');
  await menu.waitFor({ state: "visible" });
  const items = menu.getByRole("menuitem");
  await items.first().press("End");
  const endFocused = await items.last().evaluate((element) => element === document.activeElement);
  await items.last().press("Home");
  const homeFocused = await items.first().evaluate((element) => element === document.activeElement);
  if (!endFocused || !homeFocused) throw new Error("Compact overflow Home/End focus failed");
  report.interactions.overflow = { arrowDownOpens: true, endFocused, homeFocused };
  report.geometry[scenario.id] = await geometry(page);
  await capture(page, scenario);
  await page.keyboard.press("Escape");
  if (!await trigger.evaluate((element) => element === document.activeElement)) throw new Error("Escape did not restore overflow trigger focus");
  report.interactions.overflow.escapeRestoresFocus = true;
  await context.close();
}
await browser.close();

await createComparisons();

if (report.unexpectedRequests.length || report.requestFailures.length || report.consoleErrors.length || report.pageErrors.length || report.externalRequests.length) {
  throw new Error(`Browser diagnostics are not clean: ${JSON.stringify({
    unexpectedRequests: report.unexpectedRequests,
    requestFailures: report.requestFailures,
    consoleErrors: report.consoleErrors,
    pageErrors: report.pageErrors,
    externalRequests: report.externalRequests,
  })}`);
}

await writeFile(path.join(directories.metrics, "browser-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
await writeFile(path.join(directories.diagnostics, "network-ledger.json"), `${JSON.stringify({
  requests: report.requests,
  responses: report.responses,
  unexpectedRequests: report.unexpectedRequests,
  requestFailures: report.requestFailures,
  externalRequests: report.externalRequests,
}, null, 2)}\n`, "utf8");
await writeFile(path.join(directories.diagnostics, "console-page-errors.json"), `${JSON.stringify({
  consoleErrors: report.consoleErrors,
  pageErrors: report.pageErrors,
}, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  captures: report.captures.length,
  regions: report.regions.length,
  ariaSnapshots: report.ariaSnapshots.length,
  axe: report.axe.map((item) => ({ scenario: item.scenario, violations: item.violations.length, incomplete: item.incomplete.length })),
  unexpectedRequests: report.unexpectedRequests.length,
  requestFailures: report.requestFailures.length,
  expectedRequestAborts: report.expectedRequestAborts.length,
  consoleErrors: report.consoleErrors.length,
  pageErrors: report.pageErrors.length,
  externalRequests: report.externalRequests.length,
}, null, 2));

async function createComparisons() {
  const pairs = [
    { prototype: "profiles-1440-light-java-basic.png", production: "1440-ru-light-java-basic.png", id: "1440-ru-light-basic", prototypeMask: { x: 576, y: 260, width: 838, height: 640 } },
    { prototype: "profiles-1440-dark-java-advanced.png", production: "1440-ru-dark-java-advanced.png", id: "1440-ru-dark-advanced", prototypeMask: { x: 576, y: 260, width: 838, height: 640 } },
    { prototype: "profiles-1024-light-nav-menu-open.png", production: "1024-ru-light-overflow.png", id: "1024-ru-light-overflow", prototypeMask: { x: 304, y: 330, width: 702, height: 438 } },
    { prototype: "profiles-qhd-100-light-advanced.png", production: "2560-ru-light-advanced.png", id: "2560-ru-light-advanced", prototypeMask: { x: 670, y: 291, width: 1861, height: 1149 } },
  ];
  const comparisonBrowser = await chromium.launch({ headless: true });
  for (const pair of pairs) {
    const prototypeBytes = await readFile(path.join(prototypeRoot, pair.prototype));
    const productionBytes = await readFile(path.join(directories.full, pair.production));
    const productionGeometry = report.geometry[pair.production.replace(/\.png$/, "")] ?? report.geometry[pair.id.replace("light-basic", "light-java-basic").replace("dark-advanced", "dark-java-advanced")];
    const editor = productionGeometry?.editor;
    const tabs = productionGeometry?.tabs;
    const productionMask = editor && tabs
      ? { x: editor.x, y: tabs.y + tabs.height, width: editor.width, height: Math.max(0, pair.id.startsWith("2560") ? 1440 - tabs.y - tabs.height : pair.id.startsWith("1024") ? 768 - tabs.y - tabs.height : 900 - tabs.y - tabs.height) }
      : { x: 0, y: 0, width: 0, height: 0 };
    const page = await comparisonBrowser.newPage({ viewport: { width: 2560, height: 1800 }, deviceScaleFactor: 1 });
    const data = {
      prototype: prototypeBytes.toString("base64"),
      production: productionBytes.toString("base64"),
      prototypeMask: pair.prototypeMask,
      productionMask,
      labels: [`PROTOTYPE — ${pair.prototype}`, `PRODUCTION — ${pair.production}`],
    };
    await page.setContent("<!doctype html><meta charset='utf-8'><canvas></canvas>");
    await page.evaluate(async (input) => {
      const load = (base64) => new Promise((resolve) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.src = `data:image/png;base64,${base64}`;
      });
      const [prototype, production] = await Promise.all([load(input.prototype), load(input.production)]);
      const canvas = document.querySelector("canvas");
      const context = canvas.getContext("2d");
      const gap = 20;
      const labelHeight = 38;
      canvas.width = prototype.width + production.width + gap;
      canvas.height = Math.max(prototype.height, production.height) + labelHeight;
      context.fillStyle = "#dbe3ec";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = "#17263b";
      context.font = "700 16px sans-serif";
      context.fillText(input.labels[0], 12, 24);
      context.fillText(input.labels[1], prototype.width + gap + 12, 24);
      context.drawImage(prototype, 0, labelHeight);
      context.drawImage(production, prototype.width + gap, labelHeight);
      context.fillStyle = "#d9dee7";
      context.fillRect(input.prototypeMask.x, input.prototypeMask.y + labelHeight, input.prototypeMask.width, input.prototypeMask.height);
      context.fillRect(prototype.width + gap + input.productionMask.x, input.productionMask.y + labelHeight, input.productionMask.width, input.productionMask.height);
    }, data);
    await page.locator("canvas").screenshot({ path: path.join(directories.comparisons, `${pair.id}-side-by-side.png`) });
    for (const mode of ["overlay", "difference"]) {
      await page.setContent("<!doctype html><meta charset='utf-8'><canvas></canvas>");
      await page.evaluate(async ({ input, mode }) => {
        const load = (base64) => new Promise((resolve) => {
          const image = new Image();
          image.onload = () => resolve(image);
          image.src = `data:image/png;base64,${base64}`;
        });
        const [prototype, production] = await Promise.all([load(input.prototype), load(input.production)]);
        const canvas = document.querySelector("canvas");
        const context = canvas.getContext("2d");
        canvas.width = Math.max(prototype.width, production.width);
        canvas.height = Math.max(prototype.height, production.height);
        context.fillStyle = "white";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(prototype, 0, 0);
        context.fillStyle = "#d9dee7";
        context.fillRect(input.prototypeMask.x, input.prototypeMask.y, input.prototypeMask.width, input.prototypeMask.height);
        if (mode === "overlay") context.globalAlpha = .5;
        if (mode === "difference") context.globalCompositeOperation = "difference";
        context.drawImage(production, 0, 0);
        context.globalAlpha = 1;
        context.globalCompositeOperation = "source-over";
        context.fillStyle = "#d9dee7";
        context.fillRect(input.productionMask.x, input.productionMask.y, input.productionMask.width, input.productionMask.height);
      }, { input: data, mode });
      await page.locator("canvas").screenshot({ path: path.join(directories.comparisons, `${pair.id}-${mode}.png`) });
    }
    await page.close();
  }
  await comparisonBrowser.close();
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}
