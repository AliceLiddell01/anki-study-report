import { readFile, writeFile, mkdir } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
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
  overlays: path.join(evidenceRoot, "overlays"),
  pixelDiffs: path.join(evidenceRoot, "pixel-diffs"),
  prototype: path.join(evidenceRoot, "prototype-references"),
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
  let items = fixture === "empty" ? [] : fixtureItems;
  if (fixture === "basic-review") {
    items = fixtureItems.map((item) => item.structure.noteTypeId === "2" ? {
      ...item,
      suggestion: {
        ...item.suggestion,
        confidence: 0.62,
        unresolvedFields: [item.structure.fields[3]],
        warnings: ["review_mappings"],
      },
    } : item);
  }
  if (fixture === "basic-zero") {
    items = fixtureItems.map((item) => item.structure.noteTypeId === "2" ? {
      ...item,
      suggestion: { ...item.suggestion, checks: [] },
    } : item);
  }
  if (fixture === "basic-custom") {
    items = fixtureItems.map((item) => item.structure.noteTypeId === "2" ? {
      ...item,
      suggestion: {
        ...item.suggestion,
        fieldMappings: item.suggestion.fieldMappings.map((mapping, index) => index === 3 ? { ...mapping, role: "custom_explanation" } : mapping),
      },
    } : item);
  }
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
  prototypeGeometry: {},
  geometryComparison: {},
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
  const targetUrl = new URL(baseUrl);
  targetUrl.searchParams.set("token", ["visual", "test"].join("-"));
  targetUrl.hash = "/settings/inspection-profiles";
  await page.goto(targetUrl.toString(), { waitUntil: "domcontentloaded" });
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
  const noteSelector = {
    long: '.inspection-note-button[title^="Extremely long customer-facing"]',
    words: '.inspection-note-button[title="Слова"]',
    needs_review: '.inspection-note-button[title="Грамматика"]',
    disabled: '.inspection-note-button[title="Основная"]',
    no_name: '.inspection-note-button[title="Basic"]',
  }[scenario.select] ?? '.inspection-note-button[title="Java"]';
  await page.locator(noteSelector).evaluate((element) => element.click());
  await page.locator("[data-testid='inspection-basic-editor']").waitFor({ state: "visible" });
  if (scenario.selectedTemplates) {
    await page.getByLabel(scenario.language === "ru" ? "Только выбранные шаблоны" : "Selected templates only").click();
  }
  if (scenario.advanced || scenario.fixture === "dirty") {
    await page.getByRole("tab", { name: scenario.language === "ru" ? "Расширенное" : "Advanced" }).click();
    await page.locator("#inspection-advanced-panel").waitFor({ state: "visible" });
  }
  if (scenario.fixture === "dirty") {
    await page.locator("#inspection-profile-display-name").fill("Локально изменённый профиль");
    await page.getByText(scenario.language === "ru" ? "Несохранённые изменения" : "Unsaved changes").waitFor();
    await page.getByRole("tab", { name: scenario.language === "ru" ? "Основное" : "Basic" }).click();
    await page.locator("#inspection-basic-mode-panel").waitFor({ state: "visible" });
    await page.getByRole("tab", { name: scenario.language === "ru" ? "Расширенное" : "Advanced" }).click();
    await page.locator("#inspection-advanced-panel").waitFor({ state: "visible" });
    const preservedValue = await page.locator("#inspection-profile-display-name").inputValue();
    if (preservedValue !== "Локально изменённый профиль") throw new Error("Dirty draft was not preserved across Basic and Advanced tabs");
    report.interactions.dirtyDraft = { basicAdvancedRoundTrip: true, preservedValue };
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
    identityInner: ".inspection-editor-identity-inner",
    lifecycle: ".inspection-lifecycle",
    tabs: ".inspection-mode-switch",
    editorBodyStart: "#inspection-basic-mode-panel, #inspection-advanced-panel",
    basic: ".inspection-basic",
    basicFields: ".inspection-basic-fields",
    basicRequirements: ".inspection-basic-requirements",
    basicScope: ".inspection-basic-scope",
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
  await resetScrollPositions(page);
  await page.screenshot({ path: path.join(directories.full, fullName), fullPage: false, animations: "disabled" });
  report.captures.push({ scenario: scenario.id, filename: fullName, width: scenario.width, height: scenario.height, theme: scenario.theme, language: scenario.language, fixture: scenario.fixture ?? "default" });
  if (["loading", "load-error", "empty", "no-matches", "store-unavailable"].includes(scenario.fixture)) {
    const ariaFilename = `${scenario.id}.aria.yml`;
    const aria = await page.locator('[data-testid="settings-layout-shell"]').ariaSnapshot();
    await writeFile(path.join(directories.aria, ariaFilename), `${aria}\n`, "utf8");
    report.ariaSnapshots.push(ariaFilename);
    return;
  }
  const topbar = page.locator(".topbar-surface");
  const topbarVisibility = await topbar.count() ? await topbar.evaluate((element) => element.style.visibility) : "";
  if (await topbar.count()) await topbar.evaluate((element) => { element.style.visibility = "hidden"; });
  const regionSelectors = {
    "profiles-route-header": ".settings-route-header-slot",
    "profiles-workspace": ".inspection-workspace",
    "profiles-catalog": ".inspection-catalog",
    "profiles-catalog-controls": ".inspection-catalog-controls",
    "profiles-selected-row": ".inspection-note-button.is-selected",
    "profiles-editor-frame": ".inspection-editor",
    "profiles-editor-identity": ".inspection-editor-identity",
    "profiles-editor-tabs": ".inspection-mode-switch",
    "profiles-editor-body-start": "#inspection-basic-mode-panel, #inspection-advanced-panel",
    "basic-full-panel": ".inspection-basic",
    "basic-setup-summary": ".inspection-guided-summary",
    "basic-field-mappings": ".inspection-basic-fields",
    "basic-field-row": ".inspection-basic-row",
    "basic-requirements": ".inspection-basic-requirements",
    "basic-requirement-row": ".inspection-requirement-row",
    "basic-add-requirement": ".inspection-add-requirement",
    "basic-template-scope": ".inspection-basic-scope",
    "basic-inline-error": ".inspection-inline-error",
    "basic-body-to-action-boundary": ".inspection-primary-actions",
  };
  try {
    for (const [region, selector] of Object.entries(regionSelectors)) {
      const locator = page.locator(selector);
      if (!await locator.count() || !await locator.first().isVisible()) continue;
      await locator.first().evaluate((element, block) => element.scrollIntoView({ block, inline: "nearest" }), region === "profiles-editor-body-start" ? "start" : "center");
      await page.waitForTimeout(50);
      const filename = `${scenario.id}-${region}.png`;
      const box = await locator.first().boundingBox();
      if (region === "profiles-editor-body-start" && box) {
        const viewport = page.viewportSize();
        const clipX = Math.max(0, box.x);
        const clipY = Math.max(0, box.y);
        await page.screenshot({
          path: path.join(directories.regions, filename),
          animations: "disabled",
          clip: {
            x: clipX,
            y: clipY,
            width: Math.min(box.width, (viewport?.width ?? box.x + box.width) - clipX),
            height: Math.min(48, box.height, (viewport?.height ?? box.y + box.height) - clipY),
          },
        });
      } else {
        await locator.first().screenshot({ path: path.join(directories.regions, filename), animations: "disabled" });
      }
      report.regions.push({ scenario: scenario.id, region, filename, box });
    }
  } finally {
    if (await topbar.count()) await topbar.evaluate((element, visibility) => { element.style.visibility = visibility; }, topbarVisibility);
  }
  const ariaFilename = `${scenario.id}.aria.yml`;
  const aria = await page.locator('[data-testid="settings-layout-shell"]').ariaSnapshot();
  await writeFile(path.join(directories.aria, ariaFilename), `${aria}\n`, "utf8");
  report.ariaSnapshots.push(ariaFilename);
}

async function resetScrollPositions(page) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    for (const element of document.querySelectorAll("*")) {
      if (!(element instanceof HTMLElement)) continue;
      if (element.scrollTop) element.scrollTop = 0;
      if (element.scrollLeft) element.scrollLeft = 0;
    }
  });
  await page.waitForTimeout(50);
}

async function runAxe(page, scenario) {
  await page.addScriptTag({ content: axeSource });
  const result = await page.evaluate(async () => {
    const axeResult = await window.axe.run({
      include: [['[data-testid="settings-layout-shell"]']],
    }, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] },
    });
    return {
      violations: axeResult.violations,
      incomplete: axeResult.incomplete,
      passes: axeResult.passes.map((item) => item.id),
      inapplicable: axeResult.inapplicable.map((item) => item.id),
      scopeExclusions: [],
    };
  });
  report.axe.push({ scenario: scenario.id, ...result });
  await writeFile(path.join(directories.accessibility, `axe-${scenario.id}.json`), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  if (result.violations.length || result.incomplete.length) {
    throw new Error(`${scenario.id}: axe expected 0 violations and 0 incomplete, got ${result.violations.length}/${result.incomplete.length}`);
  }
}

async function verifyTabs(page, language) {
  const basic = page.getByRole("tab", { name: language === "ru" ? "Основное" : "Basic" });
  await basic.focus();
  await basic.press("ArrowRight");
  const advanced = page.getByRole("tab", { name: language === "ru" ? "Расширенное" : "Advanced" });
  if (!await waitForSelectedTab(advanced)) {
    throw new Error("ArrowRight did not select and focus Advanced");
  }
  await advanced.press("Home");
  if (!await waitForSelectedTab(basic)) {
    throw new Error("Home did not select and focus Basic");
  }
  await basic.press("End");
  if (!await waitForSelectedTab(advanced)) {
    throw new Error("End did not select and focus Advanced");
  }
  await advanced.press("ArrowLeft");
  if (!await waitForSelectedTab(basic)) {
    throw new Error("ArrowLeft did not select and focus Basic");
  }
  await basic.press("Tab");
  const tabExit = await page.evaluate(() => document.activeElement?.getAttribute("role") !== "tab"
    && Boolean(document.activeElement?.closest("#inspection-basic-mode-panel")));
  if (!tabExit) throw new Error("Tab did not exit the tablist into the active panel");
  report.interactions.tabs = { arrowRight: true, home: true, end: true, arrowLeft: true, tabExit };
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
}

async function verifyLongLabelLayout(page) {
  const row = page.locator('.inspection-note-button[title^="Extremely long customer-facing"]');
  const name = await row.locator(".inspection-note-name").boundingBox();
  const hint = await row.locator("small").boundingBox();
  if (!name || !hint) throw new Error("Long label geometry is unavailable");
  const separation = Math.round((hint.y - (name.y + name.height)) * 100) / 100;
  if (separation < 0) throw new Error(`Long catalog name overlaps its hint by ${Math.abs(separation)}px`);
  report.interactions.longLabel = { noOverlap: true, separation };
}

async function waitForSelectedTab(tab) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    if (await tab.evaluate((element) => element === document.activeElement && element.getAttribute("aria-selected") === "true")) return true;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  return false;
}

async function verifyVisualStates(page) {
  const selected = page.locator(".inspection-note-button.is-selected");
  const focusTarget = page.locator('.inspection-note-button[title="Грамматика"]');
  const activeTab = page.locator(".inspection-mode-switch [aria-selected='true']");
  const selectedStyle = await visualStyle(selected);
  await reachByKeyboard(page, focusTarget);
  await page.waitForTimeout(250);
  const focusStyle = await visualStyle(focusTarget);
  await focusTarget.hover();
  await page.waitForTimeout(250);
  const hoverStyle = await visualStyle(focusTarget);
  const activeTabStyle = await visualStyle(activeTab);
  await reachByKeyboard(page, activeTab);
  await page.waitForTimeout(250);
  const tabFocusStyle = await visualStyle(activeTab);
  if (selectedStyle.backgroundColor === hoverStyle.backgroundColor) throw new Error("Selected and hover catalog states are indistinguishable");
  if (!focusStyle.focusVisible || (
    (focusStyle.outlineStyle === "none" || focusStyle.outlineWidth === "0px")
    && focusStyle.boxShadow === "none"
  )) {
    throw new Error(`Catalog keyboard focus is not visible: ${JSON.stringify(focusStyle)}`);
  }
  if (
    activeTabStyle.backgroundColor === tabFocusStyle.backgroundColor
    && activeTabStyle.borderBottomColor === tabFocusStyle.borderBottomColor
    && activeTabStyle.boxShadow === tabFocusStyle.boxShadow
    && activeTabStyle.outlineWidth === tabFocusStyle.outlineWidth
  ) {
    throw new Error("Active and keyboard-focused tab states are indistinguishable");
  }
  report.interactions.visualStates = {
    selected: selectedStyle,
    focus: focusStyle,
    hover: hoverStyle,
    activeTab: activeTabStyle,
    tabFocus: tabFocusStyle,
  };
  await focusTarget.focus();
}

async function verifyBasicInteractions(page, language) {
  const rows = page.locator(".inspection-requirement-row");
  const initialCount = await rows.count();
  const priority = page.locator("#inspection-basic-priority-0");
  await priority.selectOption("low");
  if (await priority.inputValue() !== "low") throw new Error("Basic priority did not update");
  await page.locator("#inspection-basic-new-requirement").selectOption("min_text_length");
  const add = page.getByRole("button", { name: language === "ru" ? "Добавить" : "Add", exact: true });
  await add.click();
  await rows.nth(initialCount).waitFor({ state: "visible" });
  await page.waitForFunction((id) => document.activeElement?.id === id, `inspection-basic-requirement-${initialCount}`);
  const addFocusId = await page.evaluate(() => document.activeElement?.id ?? "");
  if (addFocusId !== `inspection-basic-requirement-${initialCount}`) {
    throw new Error(`Add requirement focus moved to ${addFocusId || "no element"}`);
  }
  const minLength = page.locator(`#inspection-basic-min-length-${initialCount}`);
  await minLength.fill("12");
  if (await minLength.inputValue() !== "12") throw new Error("Basic minimum length did not update");
  await rows.nth(initialCount).getByRole("button", { name: new RegExp(language === "ru" ? "^Удалить требование:" : "^Remove requirement:") }).click();
  await rows.nth(initialCount).waitFor({ state: "detached" });
  await page.waitForFunction((id) => document.activeElement?.id === id, `inspection-basic-requirement-${initialCount - 1}`);
  const removeFocusId = await page.evaluate(() => document.activeElement?.id ?? "");
  if (removeFocusId !== `inspection-basic-requirement-${initialCount - 1}`) {
    throw new Error(`Remove requirement focus moved to ${removeFocusId || "no element"}`);
  }

  await page.locator("#inspection-basic-new-requirement").selectOption("one_of_roles_non_empty");
  await add.click();
  await rows.nth(initialCount).waitFor({ state: "visible" });
  const multiRoleChoices = rows.nth(initialCount).locator(".inspection-basic-role-choices input");
  await multiRoleChoices.nth(2).check();
  if (!await multiRoleChoices.nth(2).isChecked()) throw new Error("Basic multi-role checkbox did not update");
  await rows.nth(initialCount).getByRole("button", { name: new RegExp(language === "ru" ? "^Удалить требование:" : "^Remove requirement:") }).click();
  await rows.nth(initialCount).waitFor({ state: "detached" });

  const selectedScope = page.getByLabel(language === "ru" ? "Только выбранные шаблоны" : "Selected templates only");
  await selectedScope.click();
  const templateChoices = page.locator(".inspection-basic-template-list input");
  await templateChoices.nth(1).check();
  if (!await templateChoices.nth(1).isChecked()) throw new Error("Basic template checkbox did not update");
  await templateChoices.nth(1).uncheck();
  if (await templateChoices.nth(1).isChecked()) throw new Error("Basic template checkbox did not clear");

  const requiredMapping = page.locator("#inspection-basic-role-1");
  await requiredMapping.selectOption("");
  if (await requiredMapping.inputValue() !== "") throw new Error("Cleared Basic mapping restored a stale controlled value");
  await page.getByRole("button", { name: language === "ru" ? "Проверить настройку" : "Check setup", exact: true }).click();
  await page.locator("#inspection-errors-title").waitFor({ state: "visible" });
  await page.waitForFunction(() => document.activeElement?.id === "inspection-errors-title");
  const summaryFocusId = await page.evaluate(() => document.activeElement?.id ?? "");
  if (summaryFocusId !== "inspection-errors-title") throw new Error(`Validation error summary focus moved to ${summaryFocusId || "no element"}`);
  await page.locator(".inspection-error-summary button").first().click();
  await page.waitForFunction(() => document.activeElement?.id === "inspection-basic-role-1");
  const controlFocusId = await page.evaluate(() => document.activeElement?.id ?? "");
  if (controlFocusId !== "inspection-basic-role-1") throw new Error(`Error link focus moved to ${controlFocusId || "no element"}`);
  const basicSelected = await page.locator("#inspection-mode-basic").getAttribute("aria-selected");
  if (basicSelected !== "true") throw new Error("Error link did not keep the Basic tab selected");
  report.interactions.basic = {
    initialRequirementCount: initialCount,
    addFocusId,
    removeFocusId,
    priorityChanged: true,
    minLengthChanged: true,
    multiRoleChecked: true,
    selectedTemplateScope: true,
    templateToggled: true,
    clearedMappingRemainedEmpty: true,
    validationStayedClientSide: true,
    summaryFocusId,
    controlFocusId,
    basicTabSelected: true,
  };
}

async function reachByKeyboard(page, target) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
  for (let index = 0; index < 60; index += 1) {
    await page.keyboard.press("Tab");
    if (await target.evaluate((element) => element === document.activeElement)) return;
  }
  throw new Error("Keyboard traversal did not reach the expected target");
}

async function visualStyle(locator) {
  return locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      focusVisible: element.matches(":focus-visible"),
      focusRing: style.getPropertyValue("--inspection-focus-ring"),
      workspacePage: Boolean(element.closest(".inspection-workspace-page")),
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
      borderBottomColor: style.borderBottomColor,
      boxShadow: style.boxShadow,
      outlineColor: style.outlineColor,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
    };
  });
}

const scenarios = [
  { id: "1440-ru-light-java-basic", width: 1440, height: 900, theme: "light", language: "ru" },
  { id: "1440-ru-light-identity", width: 1440, height: 900, theme: "light", language: "ru", select: "words" },
  { id: "1440-en-light-java-basic", width: 1440, height: 900, theme: "light", language: "en" },
  { id: "1440-ru-dark-java-basic", width: 1440, height: 900, theme: "dark", language: "ru" },
  { id: "1440-ru-light-review-basic", width: 1440, height: 900, theme: "light", language: "ru", fixture: "basic-review" },
  { id: "1440-ru-light-zero-requirements", width: 1440, height: 900, theme: "light", language: "ru", fixture: "basic-zero" },
  { id: "1440-en-light-custom-role", width: 1440, height: 900, theme: "light", language: "en", fixture: "basic-custom" },
  { id: "1440-ru-light-multi-template-selected", width: 1440, height: 900, theme: "light", language: "ru", select: "words", selectedTemplates: true },
  { id: "1440-ru-dark-java-advanced", width: 1440, height: 900, theme: "dark", language: "ru", advanced: true },
  { id: "1440-en-light-long-labels", width: 1440, height: 900, theme: "light", language: "en", select: "long" },
  { id: "1024-ru-light-compact", width: 1024, height: 768, theme: "light", language: "ru" },
  { id: "1024-ru-light-selected-focus", width: 1024, height: 768, theme: "light", language: "ru", visualStates: true },
  { id: "1024-en-dark-compact", width: 1024, height: 768, theme: "dark", language: "en" },
  { id: "2560-ru-light-basic", width: 2560, height: 1440, theme: "light", language: "ru" },
  { id: "2560-ru-light-advanced", width: 2560, height: 1440, theme: "light", language: "ru", advanced: true },
  { id: "1440-ru-light-needs-review", width: 1440, height: 900, theme: "light", language: "ru", select: "needs_review" },
  { id: "1440-ru-light-disabled", width: 1440, height: 900, theme: "light", language: "ru", select: "disabled" },
  { id: "1440-ru-light-generated-no-name", width: 1440, height: 900, theme: "light", language: "ru", select: "no_name" },
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
  if (scenario.width === 1024 && state.catalog && state.editor && Math.abs(state.catalog.y - state.editor.y) > 1) {
    throw new Error(`${scenario.id}: catalog and editor differ by ${Math.abs(state.catalog.y - state.editor.y)}px on the block axis`);
  }
  if (scenario.width === 2560 && state.editor?.width < 1500) throw new Error(`${scenario.id}: editor did not expand at QHD`);
  if (scenario.width === 2560 && state.identityInner?.width > 1320) throw new Error(`${scenario.id}: identity inner layout is not bounded`);
  if (scenario.width === 2560 && state.lifecycle?.width > 400) throw new Error(`${scenario.id}: lifecycle content is too wide`);
  if (scenario.id === "2560-ru-light-basic" && (state.basic?.width < 1000 || state.basic?.width > 1280)) {
    throw new Error(`${scenario.id}: Basic inner layout width ${state.basic?.width ?? "missing"} is not bounded`);
  }
  if (scenario.id === "1440-ru-light-java-basic") {
    await verifyTabs(page, scenario.language);
  }
  if (scenario.id === "1024-ru-light-compact") await verifyLongLabelLayout(page);
  if (scenario.visualStates) await verifyVisualStates(page);
  await capture(page, scenario);
  await context.close();
}

{
  const scenario = { id: "1024-ru-light-cleared-mapping-error", width: 1024, height: 768, theme: "light", language: "ru", select: "words" };
  const { context, page } = await openScenario(browser, scenario);
  await prepareScenario(page, scenario);
  await verifyBasicInteractions(page, scenario.language);
  report.geometry[scenario.id] = await geometry(page);
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
await measurePrototypeGeometry(browser);
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

async function measurePrototypeGeometry(browserInstance) {
  const targets = [
    { id: "1440-ru-light-basic", productionId: "1440-ru-light-java-basic", width: 1440, height: 900, state: "main" },
    { id: "1024-ru-light-basic", productionId: "1024-ru-light-compact", width: 1024, height: 768, state: "main" },
    { id: "2560-ru-light-basic", productionId: "2560-ru-light-basic", width: 2560, height: 1440, state: "main" },
    { id: "2560-ru-light-advanced", productionId: "2560-ru-light-advanced", width: 2560, height: 1440, state: "advanced" },
  ];
  const prototypeUrl = pathToFileURL(path.join(prototypeRoot, "prototype.html")).href;
  for (const target of targets) {
    const context = await browserInstance.newContext({
      viewport: { width: target.width, height: target.height },
      colorScheme: "light",
      reducedMotion: "reduce",
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await page.goto(`${prototypeUrl}?view=profiles&state=${target.state}&theme=light`, { waitUntil: "load" });
    const java = page.locator(".catalog-item").filter({ hasText: /^Java/ });
    if (await java.count()) await java.click();
    if (target.state === "advanced") await page.getByRole("tab", { name: "Расширенные" }).click();
    await page.locator(".editor").waitFor({ state: "visible" });
    const prototype = {
      viewport: { width: target.width, height: target.height },
      editor: await rectangle(page, ".editor"),
      identity: await rectangle(page, ".editor-title-row"),
      identityHeader: await rectangle(page, ".editor-head"),
      catalogControls: await rectangle(page, ".catalog-controls"),
      selectedRow: await rectangle(page, ".catalog-item.active"),
      tabs: await rectangle(page, ".profile-tabs"),
      editorBodyStart: await rectangle(page, "[role='tabpanel']"),
    };
    report.prototypeGeometry[target.id] = prototype;
    const prototypeCapture = `prototype-${target.id}-live.png`;
    await page.screenshot({ path: path.join(directories.prototype, prototypeCapture), fullPage: false, animations: "disabled" });
    report.prototypeGeometry[target.id].capture = prototypeCapture;
    const production = report.geometry[target.productionId];
    const prototypeIdentityTitleRowHeight = prototype.identity?.height ?? null;
    const prototypeEditorHeaderHeight = prototype.identityHeader?.height ?? null;
    const productionIdentityHeight = production?.identity?.height ?? null;
    const productionIdentityAndTabsHeight = productionIdentityHeight === null || production?.tabs?.height == null
      ? null
      : Math.round((productionIdentityHeight + production.tabs.height) * 100) / 100;
    const editorHeaderAbsoluteDelta = prototypeEditorHeaderHeight === null || productionIdentityAndTabsHeight === null
      ? null
      : Math.round((productionIdentityAndTabsHeight - prototypeEditorHeaderHeight) * 100) / 100;
    report.geometryComparison[target.id] = {
      prototypeIdentityTitleRowHeight,
      prototypeEditorHeaderHeight,
      productionIdentityHeight,
      productionIdentityAndTabsHeight,
      editorHeaderAbsoluteDelta,
      prototypeEditorBodyStartY: prototype.editorBodyStart?.y ?? null,
      productionEditorBodyStartY: production?.editorBodyStart?.y ?? null,
      prototypeCatalogControlsHeight: prototype.catalogControls?.height ?? null,
      productionCatalogControlsHeight: production?.catalogControls?.height ?? null,
      prototypeRowHeight: prototype.selectedRow?.height ?? null,
      productionRowHeight: production?.selected?.height ?? null,
      qhdIdentityInnerWidth: production?.identityInner?.width ?? null,
      qhdLifecycleWidth: production?.lifecycle?.width ?? null,
    };
    await context.close();
  }
}

async function createComparisons() {
  const pairs = [
    { prototype: "profiles-1440-light-java-basic.png", production: "1440-ru-light-java-basic.png", id: "1440-ru-light-basic", prototypeMask: { x: 576, y: 260, width: 838, height: 640 } },
    { prototype: "prototype-1024-ru-light-basic-live.png", production: "1024-ru-light-compact.png", id: "1024-ru-light-basic", prototypeMask: { x: 304, y: 332, width: 702, height: 436 }, evidencePrototype: true },
    { prototype: "prototype-2560-ru-light-basic-live.png", production: "2560-ru-light-basic.png", id: "2560-ru-light-basic", prototypeMask: { x: 670, y: 291, width: 1861, height: 1149 }, evidencePrototype: true },
    { prototype: "profiles-1440-dark-java-advanced.png", production: "1440-ru-dark-java-advanced.png", id: "1440-ru-dark-advanced", prototypeMask: { x: 576, y: 260, width: 838, height: 640 } },
    { prototype: "profiles-1024-light-nav-menu-open.png", production: "1024-ru-light-overflow.png", id: "1024-ru-light-overflow", prototypeMask: { x: 304, y: 330, width: 702, height: 438 } },
    { prototype: "profiles-qhd-100-light-advanced.png", production: "2560-ru-light-advanced.png", id: "2560-ru-light-advanced", prototypeMask: { x: 670, y: 291, width: 1861, height: 1149 } },
  ];
  const comparisonBrowser = await chromium.launch({ headless: true });
  for (const pair of pairs) {
    const prototypeBytes = await readFile(path.join(pair.evidencePrototype ? directories.prototype : prototypeRoot, pair.prototype));
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
      const outputDirectory = mode === "overlay" ? directories.overlays : directories.pixelDiffs;
      await page.locator("canvas").screenshot({ path: path.join(outputDirectory, `${pair.id}-${mode}.png`) });
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
