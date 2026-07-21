#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { ensureArtifactParent, relativeArtifactPath, resolveArtifactPaths } from "./artifact-paths.mjs";
import {
  buildPageCaptureTasks,
  resolveScope,
  resolveWorkerCount,
  runBoundedTaskQueue,
  shouldRunScope,
  summarizeCapturePerformance,
} from "./e2e-contract.mjs";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const value = process.argv[index];
  if (value.startsWith("--")) {
    args.set(value.slice(2), process.argv[index + 1] && !process.argv[index + 1].startsWith("--") ? process.argv[++index] : "1");
  }
}

const label = args.get("label") || "run";
const scope = resolveScope(process.env.ANKI_E2E_SCOPE || "full");
const screenshotWorkers = resolveWorkerCount(process.env.ANKI_E2E_SCREENSHOT_WORKERS || "3");
const artifacts = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts";
const artifactPaths = resolveArtifactPaths(artifacts);
const readyFile = process.env.ANKI_STUDY_REPORT_E2E_READY_FILE || path.join(artifactPaths.runtime, "dashboard-ready.json");
const ready = JSON.parse(await fs.readFile(readyFile, "utf8"));
const telemetryE2eEndpoint = process.env.ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT || "";
const cardsUrl = `${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/cards`;
const baseViewport = { name: "desktop-1440", width: 1440, height: 1000 };
const responsiveViewports = [
  baseViewport,
  { name: "narrow-1280", width: 1280, height: 900 },
];
const dashboardPageCases = [
  { route: "/home", pageName: "today", heading: "Сегодня", primaryHref: "#/home" },
  { route: "/calendar", pageName: "calendar", heading: "Активность", primaryHref: "#/calendar" },
  { route: "/stats", pageName: "stats-overview", heading: "Статистика", primaryHref: "#/stats" },
  { route: "/stats/quality", pageName: "stats-quality", heading: "Качество", primaryHref: "#/stats" },
  { route: "/stats/load", pageName: "stats-load", heading: "Нагрузка", primaryHref: "#/stats" },
  { route: "/stats/progress", pageName: "stats-progress", heading: "Прогресс", primaryHref: "#/stats" },
  { route: "/stats/decks", pageName: "stats-decks", heading: "Колоды", primaryHref: "#/stats" },
  { route: "/stats/fsrs", pageName: "fsrs-overview", heading: "FSRS", primaryHref: "#/stats" },
  { route: "/stats/fsrs/memory", pageName: "fsrs-memory", heading: "Состояние памяти", primaryHref: "#/stats" },
  { route: "/stats/fsrs/calibration", pageName: "fsrs-calibration", heading: "Точность модели", primaryHref: "#/stats" },
  { route: "/stats/fsrs/steps", pageName: "fsrs-steps", heading: "Шаги обучения", primaryHref: "#/stats" },
  { route: "/stats/fsrs/simulator", pageName: "fsrs-simulator", heading: "Симулятор", primaryHref: "#/stats" },
  { route: "/decks", pageName: "decks", heading: "Колоды", primaryHref: "#/decks" },
  { route: "/search", pageName: "search", heading: "Поиск", primaryHref: "#/search" },
  { route: "/profile", pageName: "profile", heading: "E2E" },
  { route: "/actions", pageName: "tools", heading: "Инструменты" },
  { route: "/settings", pageName: "settings/report", heading: "Отчёт", settingsHref: "#/settings" },
  { route: "/settings/data", pageName: "settings/data", heading: "Данные", settingsHref: "#/settings/data" },
  { route: "/settings/inspection-profiles", pageName: "settings/inspection-profiles", heading: "Профили проверки", settingsHref: "#/settings/inspection-profiles" },
  { route: "/settings/privacy", pageName: "settings/privacy", heading: "Приватность", settingsHref: "#/settings/privacy" },
  { route: "/settings/server", pageName: "settings/server", heading: "Сервер", settingsHref: "#/settings/server" },
  { route: "/settings/sources", pageName: "settings/sources", heading: "Источники данных", settingsHref: "#/settings/sources" },
  { route: "/settings/logs", pageName: "settings/logs", heading: "Логи", settingsHref: "#/settings/logs" },
  { route: "/notifications", pageName: "notifications", heading: "Центр уведомлений" },
  { route: "/settings/notifications", pageName: "settings/notifications", heading: "Уведомления", settingsHref: "#/settings/notifications" },
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
  const productNoticesDetails = await assertProductNotices(page);
  const notificationDetails = shouldRunScope(scope, "notifications") ? await assertNotificationCenter(page) : null;
  const telemetryClientDetails = telemetryE2eEndpoint ? await assertTelemetryClient(page) : null;
  const searchQueryContract = shouldRunScope(scope, "global") ? await assertSearchQueryContract() : null;
  let shadowDetails = null;
  let apkgDetails = null;
  if (shouldRunScope(scope, "cards")) {
    const cardsV2Details = await assertCardsV2Workspace(page, perf100Enabled);
    shadowDetails = cardsV2Details.preview;
    apkgDetails = cardsV2Details.apkg;
    visualStates.push(...cardsV2Details.visualStates);
  }
  const profileDetails = shouldRunScope(scope, "global") ? await assertProfileMvp(page) : null;
  const themeDetails = await assertGlobalThemeDock(page);
  const localizationDetails = await assertLocalizationDock(page);
  const activityDetails = shouldRunScope(scope, "activity") ? await assertActivityHub(page) : null;
  const deckDetails = shouldRunScope(scope, "decks") ? await assertDeckHub(page) : null;
  const statisticsDetails = shouldRunScope(scope, "stats") ? await assertStatisticsHub(page) : null;
  const inspectionProfilesDetails = shouldRunScope(scope, "cards") ? await assertInspectionProfilesWorkspace(page) : null;
  const polishStateScreenshots = await capturePolishStates(page, scope);
  const zoomDetails = await captureZoomProof(scope);
  const pageCapture = await captureDashboardPages();
  const pageScreenshots = pageCapture.screenshots;
  const navigationScreenshots = shouldRunScope(scope, "global") ? await captureAvatarMenu(page) : [];
  const cssDiagnostics = shouldRunScope(scope, "cards") ? await assertCssDiagnostics(page) : null;
  const requestFailures = actionableNetworkEvents();
  const consoleErrors = relevantConsoleEvents().filter((event) => event.type === "error");

  await writeJson(`browser-smoke-${label}.json`, {
    ok: true,
    consoleEvents: relevantConsoleEvents(),
    networkEvents,
    requestFailures,
    consoleErrors,
    pageErrors,
    shadowDetails,
    visualStates,
    cssDiagnostics,
    apkg: apkgDetails,
    profile: profileDetails,
    productNotices: productNoticesDetails,
    notifications: notificationDetails,
    telemetryClient: telemetryClientDetails,
    theme: themeDetails,
    localization: localizationDetails,
    activity: activityDetails,
    decks: deckDetails,
    statistics: statisticsDetails,
    inspectionProfiles: inspectionProfilesDetails,
    polishStateScreenshots,
    zoom125: zoomDetails,
    pageScreenshots,
    navigationScreenshots,
    scope,
    searchQueryContract,
    screenshotWorkers,
    screenshotPerformance: pageCapture.performance,
  });

  if (pageErrors.length > 0) {
    throw new Error(`Browser page errors: ${pageErrors.join("\n")}`);
  }
  if (requestFailures.length > 0) {
    throw new Error(`Browser request failures: ${JSON.stringify(requestFailures)}`);
  }
  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${JSON.stringify(consoleErrors)}`);
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

async function assertProductNotices(page) {
  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/home`, { waitUntil: "networkidle", timeout: 60000 });
  const consent = page.getByTestId("telemetry-consent-dialog");
  const whatsNew = page.getByTestId("whats-new-dialog");
  const firstRunObserved = await consent.isVisible().catch(() => false);
  const screenshots = [];

  if (firstRunObserved) {
    assertBrowser(await consent.getAttribute("role") === "dialog", "First-run consent uses a dialog role.");
    assertBrowser(await consent.getAttribute("aria-modal") === "true", "First-run consent is modal.");
    const checked = await consent.locator('input[type="checkbox"]:checked').count();
    assertBrowser(checked === 0, "First-run consent has no preselected purpose.");
    assertBrowser(
      await consent.getByRole("button", { name: "Сохранить выбранное", exact: true }).isDisabled(),
      "First-run consent cannot affirm an empty purpose selection.",
    );
    const inert = await page.locator("#dashboard-app-shell").evaluate((element) => element.inert && element.getAttribute("aria-hidden") === "true");
    assertBrowser(inert, "First-run consent makes the dashboard shell inert.");
    for (const theme of ["light", "dark"]) {
      screenshots.push(await captureProductNoticeState(page, consent, "consent-first-run", theme));
    }
    await page.keyboard.press("Escape");
    await whatsNew.waitFor({ state: "visible", timeout: 15000 });
  }

  if (!await whatsNew.isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Открыть меню профиля", exact: true }).click();
    await page.getByRole("menuitem", { name: "Что нового", exact: true }).click();
    await whatsNew.waitFor({ state: "visible", timeout: 15000 });
  }
  assertBrowser(await whatsNew.getAttribute("role") === "dialog", "What's New uses a dialog role.");
  assertBrowser((await whatsNew.getByRole("button", { expanded: true }).count()) >= 1, "What's New expands at least the current release.");
  for (const theme of ["light", "dark"]) {
    screenshots.push(await captureProductNoticeState(page, whatsNew, "whats-new", theme));
  }
  await whatsNew.getByRole("button", { name: "Понятно", exact: true }).click();
  await whatsNew.waitFor({ state: "hidden", timeout: 15000 });

  const state = await page.evaluate(async () => {
    const token = new URLSearchParams(location.search).get("token") || "";
    const [privacyResponse, noticesResponse] = await Promise.all([
      fetch(`/api/privacy?token=${encodeURIComponent(token)}`, { cache: "no-store" }),
      fetch(`/api/product-notices?token=${encodeURIComponent(token)}`, { cache: "no-store" }),
    ]);
    return { privacy: await privacyResponse.json(), notices: await noticesResponse.json() };
  });
  if (firstRunObserved) {
    assertBrowser(state.privacy?.privacy?.telemetry?.status === "declined", "Escape persists a declined first-run choice.");
  }
  assertBrowser(state.notices?.showWhatsNew === false, "Closing What's New marks the current release seen.");
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  assertBrowser(await page.locator('[role="dialog"]').count() === 0, "Product notices do not repeat after persisted close.");

  await page.getByRole("button", { name: "Открыть меню профиля", exact: true }).click();
  await page.getByRole("menuitem", { name: "Что нового", exact: true }).click();
  await whatsNew.waitFor({ state: "visible", timeout: 15000 });
  await whatsNew.getByRole("button", { name: "Закрыть историю изменений", exact: true }).click();
  await whatsNew.waitFor({ state: "hidden", timeout: 15000 });

  await prepareDashboardRoute(page, "/settings/privacy", "light", "Приватность");
  const privacyInvoker = page.getByRole("button", { name: "Открыть «Что нового»", exact: true });
  for (const closeMode of ["x", "escape", "got-it"]) {
    await privacyInvoker.click();
    await whatsNew.waitFor({ state: "visible", timeout: 15000 });
    if (closeMode === "x") {
      await whatsNew.getByRole("button", { name: "Закрыть историю изменений", exact: true }).click();
    } else if (closeMode === "escape") {
      await page.keyboard.press("Escape");
    } else {
      await whatsNew.getByRole("button", { name: "Понятно", exact: true }).click();
    }
    await whatsNew.waitFor({ state: "hidden", timeout: 15000 });
    await page.waitForTimeout(250);
    assertBrowser(!await whatsNew.isVisible().catch(() => false), `Manual What's New remains closed after ${closeMode} and async mark-seen response.`);
    assertBrowser(await privacyInvoker.evaluate((element) => document.activeElement === element), `Focus returns to the Privacy invoker after ${closeMode}.`);
  }

  for (const theme of ["light", "dark"]) {
    await prepareDashboardRoute(page, "/settings/privacy", theme, "Приватность");
    assertBrowser(await page.locator('input[type="checkbox"]').count() === 2, `Privacy settings exposes both granular purposes in ${theme} theme.`);
    assertBrowser(
      (await page.locator("main").innerText()).includes("Уведомление о конфиденциальности"),
      `Privacy settings exposes the localized notice and exact data controls in ${theme} theme.`,
    );
    const privacyShot = artifactPaths.stateScreenshot("product-notices", "privacy-settings", theme);
    await ensureArtifactParent(privacyShot);
    await page.screenshot({ path: privacyShot, fullPage: true });
    screenshots.push(relativeArtifactPath(artifactPaths, privacyShot));
  }
  const telemetryStatusScreenshots = await captureTelemetryStatusEvidence(page);
  screenshots.push(...telemetryStatusScreenshots);
  return {
    firstRunObserved,
    persistedStatus: state.privacy?.privacy?.telemetry?.status || null,
    currentVersion: state.notices?.currentVersion || null,
    noRepeatAfterClose: true,
    manualReopen: true,
    manualCloseModes: ["x", "escape", "got-it"],
    focusRestored: true,
    telemetryStatusScreenshots,
    screenshots,
  };
}

async function captureTelemetryStatusEvidence(page) {
  const token = new URLSearchParams(new URL(page.url()).search).get("token") || "";
  const baselineResponse = await page.request.get(`${ready.baseUrl}/api/privacy?token=${encodeURIComponent(token)}`);
  assertBrowser(baselineResponse.ok(), "Privacy baseline is available for sanitized status evidence.");
  const baseline = await baselineResponse.json();
  const timestamps = {
    attempt: "2026-07-15T11:45:00Z",
    retry: "2026-07-15T12:15:00Z",
    delivered: "2026-07-15T12:05:00Z",
  };
  const states = {
    "waiting-retry": {
      enrollmentState: "waiting_retry", pendingEventCount: 3,
      lastEnrollmentAttemptAt: timestamps.attempt, lastEnrollmentErrorCode: "network_error",
      enrollmentNextAttemptAt: timestamps.retry, lastEnrollmentSuccessAt: null,
      lastDeliveryAttemptAt: null, lastDeliveryErrorCode: null, lastSuccessfulDeliveryAt: null,
    },
    "enrollment-failed": {
      enrollmentState: "failed", pendingEventCount: 3,
      lastEnrollmentAttemptAt: timestamps.attempt, lastEnrollmentErrorCode: "unsupported_contract",
      enrollmentNextAttemptAt: null, lastEnrollmentSuccessAt: null,
      lastDeliveryAttemptAt: null, lastDeliveryErrorCode: null, lastSuccessfulDeliveryAt: null,
    },
    "enrolled-pending": {
      enrollmentState: "enrolled", pendingEventCount: 3,
      lastEnrollmentAttemptAt: timestamps.attempt, lastEnrollmentErrorCode: null,
      enrollmentNextAttemptAt: null, lastEnrollmentSuccessAt: timestamps.attempt,
      lastDeliveryAttemptAt: timestamps.delivered, lastDeliveryErrorCode: "network_error", lastSuccessfulDeliveryAt: null,
    },
    delivered: {
      enrollmentState: "enrolled", pendingEventCount: 0,
      lastEnrollmentAttemptAt: timestamps.attempt, lastEnrollmentErrorCode: null,
      enrollmentNextAttemptAt: null, lastEnrollmentSuccessAt: timestamps.attempt,
      lastDeliveryAttemptAt: timestamps.delivered, lastDeliveryErrorCode: null, lastSuccessfulDeliveryAt: timestamps.delivered,
    },
  };
  let activeState = states["waiting-retry"];
  const handler = async (route) => {
    const client = {
      ...(baseline.telemetryClient || {}),
      endpointState: "configured",
      senderState: "idle",
      deletionPending: false,
      deletionErrorCode: null,
      deletionNextAttemptAt: null,
      ...activeState,
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...baseline, telemetryClient: client }) });
  };
  await page.route("**/api/privacy?*", handler);
  const screenshots = [];
  try {
    for (const [stateName, state] of Object.entries(states)) {
      activeState = state;
      for (const theme of ["light", "dark"]) {
        await prepareDashboardRoute(page, "/settings/privacy", theme, "Приватность");
        const filePath = artifactPaths.stateScreenshot("telemetry-status", stateName, theme);
        await ensureArtifactParent(filePath);
        await page.screenshot({ path: filePath, fullPage: true });
        screenshots.push(relativeArtifactPath(artifactPaths, filePath));
      }
    }
  } finally {
    await page.unroute("**/api/privacy?*", handler);
  }
  return screenshots;
}

async function captureProductNoticeState(page, modal, stateName, theme) {
  await page.evaluate((selectedTheme) => {
    window.localStorage.setItem("anki-study-report-theme", selectedTheme);
    document.documentElement.dataset.theme = selectedTheme;
    document.documentElement.style.colorScheme = selectedTheme;
  }, theme);
  await page.waitForFunction((selectedTheme) => document.documentElement.dataset.theme === selectedTheme, theme);
  await waitForLayoutStabilization(page);
  const colors = await modal.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
      color: style.color,
    };
  });
  const luminance = colorLuminance(colors.backgroundColor);
  if (theme === "dark") {
    assertBrowser(luminance < 90, `${stateName} dark modal surface is dark: ${colors.backgroundColor}.`);
  } else {
    assertBrowser(luminance > 180, `${stateName} light modal surface is light: ${colors.backgroundColor}.`);
  }
  assertBrowser(colors.borderColor !== colors.backgroundColor, `${stateName} ${theme} modal keeps a visible border.`);
  assertBrowser(colors.color !== colors.backgroundColor, `${stateName} ${theme} modal keeps contrasting text.`);
  const filePath = artifactPaths.stateScreenshot("product-notices", stateName, theme);
  await ensureArtifactParent(filePath);
  await page.screenshot({ path: filePath, fullPage: true });
  return relativeArtifactPath(artifactPaths, filePath);
}

async function assertNotificationCenter(page) {
  const screenshots = [];
  const settingsResponse = await page.request.put(
    `${ready.baseUrl}/api/settings/notifications?token=${encodeURIComponent(ready.token)}`,
    {
      data: {
        showUnreadBadge: true,
        showInAppToasts: true,
        minimumToastSeverity: "critical",
        toastCategories: { workload: true, retention: true, deck_health: true, card_problems: true, product_updates: true },
      },
    },
  );
  assertBrowser(settingsResponse.ok(), "Notification E2E resets the isolated profile to documented defaults.");
  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/home`, { waitUntil: "networkidle", timeout: 60000 });
  await page.evaluate(() => {
    localStorage.setItem("anki-study-report-language", "ru");
    localStorage.setItem("anki-study-report-theme", "light");
  });
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });

  const criticalToast = page.locator('[data-testid="notification-toast-viewport"] [role="alert"]');
  await criticalToast.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(!await criticalToast.evaluate((element) => element.contains(document.activeElement)), "Critical toast does not steal focus.");
  await page.waitForTimeout(8500);
  assertBrowser(await criticalToast.isVisible(), "Critical toast persists beyond the warning timeout.");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "toast-critical", "light"));
  await criticalToast.getByRole("button", { name: "Закрыть", exact: true }).click();

  const bell = page.getByRole("button", { name: "Уведомления", exact: true }).first();
  const badge = page.getByTestId("notification-badge");
  await badge.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(/^\d+$|^99\+$/.test((await badge.innerText()).trim()), "Notification bell exposes a bounded unread badge.");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "bell-unread", "light"));
  await bell.click();
  const panel = page.locator('#notification-panel[role="dialog"][aria-modal="false"]');
  await panel.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser((await panel.locator('[data-testid="notification-item"]').count()) <= 8, "Compact notification panel is bounded to eight items.");
  assertBrowser(await panel.evaluate((element) => document.activeElement === element), "Focus enters the notification panel.");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "panel", "light"));
  await page.keyboard.press("Escape");
  await panel.waitFor({ state: "hidden", timeout: 15000 });
  await page.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Уведомления");
  assertBrowser(await bell.evaluate((element) => document.activeElement === element), "Escape returns focus to the notification bell.");

  await prepareDashboardRoute(page, "/notifications", "light", "Центр уведомлений");
  const resolvedPage = await page.evaluate(async () => {
    const token = new URLSearchParams(location.search).get("token") || "";
    for (let pageNumber = 1; pageNumber <= 10; pageNumber += 1) {
      const result = await fetch(`/api/notifications?page=${pageNumber}&pageLimit=20&tab=all&category=all&token=${encodeURIComponent(token)}`, { cache: "no-store" }).then((response) => response.json());
      if (result.items?.some((item) => item.signalStatus === "resolved")) return pageNumber;
      if (pageNumber >= (result.pageCount || 1)) break;
    }
    return 0;
  });
  assertBrowser(resolvedPage > 0, "Resolved notifications remain in the bounded durable API history.");
  for (let pageNumber = 1; pageNumber < resolvedPage; pageNumber += 1) {
    await page.getByRole("button", { name: "Следующая страница", exact: true }).click();
  }
  const resolvedCard = page.getByTestId("notification-item").filter({ hasText: "Завершено" }).first();
  await resolvedCard.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(await resolvedCard.isVisible(), "Resolved notifications remain in durable history.");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "resolved-history", "light"));
  for (let pageNumber = resolvedPage; pageNumber > 1; pageNumber -= 1) {
    await page.getByRole("button", { name: "Предыдущая страница", exact: true }).click();
  }
  await page.getByTestId("notification-item").first().waitFor({ state: "visible", timeout: 15000 });
  screenshots.push(await saveStateScreenshot(page, "notification-center", "all", "light"));
  await page.getByRole("tab", { name: "Непрочитанные", exact: true }).click();
  screenshots.push(await saveStateScreenshot(page, "notification-center", "unread", "light"));
  await page.getByRole("tab", { name: "Активные", exact: true }).click();
  screenshots.push(await saveStateScreenshot(page, "notification-center", "active", "light"));

  const independence = await page.evaluate(async () => {
    const token = new URLSearchParams(location.search).get("token") || "";
    const list = await fetch(`/api/notifications?page=1&pageLimit=50&tab=active&category=all&token=${encodeURIComponent(token)}`, { cache: "no-store" }).then((response) => response.json());
    const target = list.items?.find((item) => item.readAt === null && item.signalStatus === "active");
    if (!target) return { checked: false, preserved: false };
    await fetch(`/api/notifications/read?token=${encodeURIComponent(token)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ notificationIds: [target.notificationId] }) });
    const after = await fetch(`/api/notifications?page=1&pageLimit=50&tab=all&category=all&token=${encodeURIComponent(token)}`, { cache: "no-store" }).then((response) => response.json());
    const updated = after.items?.find((item) => item.notificationId === target.notificationId);
    return { checked: true, preserved: updated?.signalStatus === "active" && updated?.readAt !== null };
  });
  assertBrowser(independence.checked && independence.preserved, "Read state changes without resolving the active signal.");

  await prepareDashboardRoute(page, "/settings/notifications", "light", "Уведомления");
  const settingsCheckboxes = page.locator('main input[type="checkbox"]');
  assertBrowser(await settingsCheckboxes.count() === 7, "Notification settings expose two master controls and five categories.");
  assertBrowser(await settingsCheckboxes.evaluateAll((items) => items.every((item) => item.checked)), "Notification settings defaults are enabled.");
  const minimum = page.locator("#minimum-toast-severity");
  assertBrowser(await minimum.inputValue() === "critical", "Minimum toast severity defaults to critical.");
  screenshots.push(await saveStateScreenshot(page, "notification-settings", "defaults-ru", "light"));
  await settingsCheckboxes.nth(0).uncheck();
  await minimum.selectOption("warning");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await page.getByText("Настройки сохранены.", { exact: true }).waitFor({ state: "visible", timeout: 15000 });

  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  const warningToast = page.locator('[data-testid="notification-toast-viewport"] [role="status"]');
  await warningToast.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(!await warningToast.evaluate((element) => element.contains(document.activeElement)), "Warning toast does not steal focus.");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "toast-warning", "light"));
  await warningToast.getByRole("button", { name: "Закрыть", exact: true }).click();
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1000);
  assertBrowser(await page.getByTestId("notification-toast-viewport").count() === 0, "Delivered toast does not repeat after reload.");
  assertBrowser(await page.locator("#minimum-toast-severity").inputValue() === "warning", "Toast severity persists after reload.");
  assertBrowser(!await page.locator('main input[type="checkbox"]').nth(0).isChecked(), "Unread badge preference persists after reload.");

  await prepareDashboardRoute(page, "/notifications", "light", "Центр уведомлений");
  await page.getByRole("button", { name: "Отметить всё прочитанным", exact: true }).click();
  await page.getByText("Непрочитанных: 0", { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await page.getByRole("tab", { name: "Непрочитанные", exact: true }).click();
  await page.getByText("Для выбранного фильтра уведомлений нет.", { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  screenshots.push(await saveStateScreenshot(page, "notification-center", "empty", "light"));

  await page.getByRole("tab", { name: "Все", exact: true }).click();
  await page.getByTestId("language-selector").click();
  await page.getByRole("menuitemradio", { name: "English", exact: true }).click();
  await page.getByRole("heading", { name: "Notification Center", exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await page.getByTestId("theme-toggle").click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
  screenshots.push(await saveStateScreenshot(page, "notification-center", "all-en", "dark"));

  await page.getByTestId("language-selector").click();
  await page.getByRole("menuitemradio", { name: "Русский", exact: true }).click();
  await page.getByTestId("theme-toggle").click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "light" && document.documentElement.lang === "ru");

  const finalState = await page.evaluate(async () => {
    const token = new URLSearchParams(location.search).get("token") || "";
    const [summary, settings] = await Promise.all([
      fetch(`/api/notifications/summary?token=${encodeURIComponent(token)}`, { cache: "no-store" }).then((response) => response.json()),
      fetch(`/api/settings/notifications?token=${encodeURIComponent(token)}`, { cache: "no-store" }).then((response) => response.json()),
    ]);
    return {
      unreadCount: summary.unreadCount,
      activeSignalCount: summary.activeSignalCount,
      showUnreadBadge: settings.preferences?.showUnreadBadge,
      minimumToastSeverity: settings.preferences?.minimumToastSeverity,
    };
  });
  assertBrowser(finalState.unreadCount === 0, "Mark all read leaves zero unread notifications.");
  await writeJson("notification-browser-proof.json", {
    ok: true,
    lifecycleVisible: true,
    readResolutionIndependent: true,
    focusReturned: true,
    toastFocusStolen: false,
    toastRepeatedAfterReload: false,
    preferences: { showUnreadBadge: finalState.showUnreadBadge, minimumToastSeverity: finalState.minimumToastSeverity },
    unreadCount: finalState.unreadCount,
    activeSignalCount: finalState.activeSignalCount,
    screenshotCount: screenshots.length,
  });
  return { ...finalState, readResolutionIndependent: true, focusReturned: true, toastRepeatedAfterReload: false, screenshots };
}

async function assertTelemetryClient(page) {
  const fakeState = async () => {
    const response = await fetch(`${telemetryE2eEndpoint}/__e2e/state`);
    assertBrowser(response.ok, "Telemetry fake state endpoint is reachable.");
    return response.json();
  };
  const controlFake = async (offline) => {
    const response = await fetch(`${telemetryE2eEndpoint}/__e2e/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offline }),
    });
    assertBrowser(response.ok, "Telemetry fake control endpoint accepted the bounded state change.");
    return response.json();
  };
  const dashboardPost = (path, payload) => page.evaluate(async ({ path, payload }) => {
    const token = new URLSearchParams(location.search).get("token") || "";
    const response = await fetch(`${path}?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    return { status: response.status, body: await response.json() };
  }, { path, payload });
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
      assertBrowser(result.status === 200 && result.body?.ok === true, "Local telemetry bridge accepts a bounded semantic event.");
    }
    return Date.now() - started;
  };
  const privacy = (reliabilityDiagnostics, featureUsage) => dashboardPost("/api/privacy", {
    purposes: { reliabilityDiagnostics, featureUsage },
  });

  const declined = await fakeState();
  assertBrowser(declined.enrollments === 0 && declined.eventCount === 0, "Declined consent produces zero outbound telemetry requests.");

  const reliabilityChoice = await privacy(true, false);
  assertBrowser(reliabilityChoice.status === 200, "Reliability-only consent is persisted through the local API.");
  const disabledFeature = await dashboardPost("/api/telemetry/events", {
    eventCode: "dashboard.opened",
    occurredAt: new Date().toISOString(),
  });
  assertBrowser(disabledFeature.body?.queued === false, "Feature event is a quiet no-op when only reliability is enabled.");
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
  assertBrowser(afterReliability.eventPurposes.featureUsage === 0, "Reliability-only consent sends no feature-usage event.");

  const featureChoice = await privacy(false, true);
  assertBrowser(featureChoice.status === 200, "Feature-only consent is persisted through the local API.");
  const disabledReliability = await dashboardPost("/api/telemetry/events", {
    eventCode: "addon.started",
    occurredAt: new Date().toISOString(),
  });
  assertBrowser(disabledReliability.body?.queued === false, "Reliability event is a quiet no-op when only feature usage is enabled.");
  const featureDurationMs = await emitMany({
    eventCode: "page.opened",
    pageCode: "settings_privacy",
    occurredAt: new Date().toISOString(),
  }, 25);
  const afterFeature = await waitFor(
    (state) => state.eventPurposes?.featureUsage >= 25,
    "feature-only batch delivery",
  );
  assertBrowser(afterFeature.eventBatches >= 2, "Telemetry events are delivered in bounded batches.");
  assertBrowser(reliabilityDurationMs < 5000 && featureDurationMs < 5000, "Telemetry queueing does not freeze the dashboard UI.");

  await controlFake(true);
  const beforeOffline = await fakeState();
  await emitMany({
    eventCode: "dashboard.opened",
    occurredAt: new Date().toISOString(),
  }, 25);
  await new Promise((resolve) => setTimeout(resolve, 300));
  const localStatus = await page.evaluate(async () => {
    const token = new URLSearchParams(location.search).get("token") || "";
    const response = await fetch(`/api/telemetry/status?token=${encodeURIComponent(token)}`, { cache: "no-store" });
    return response.json();
  });
  const afterOffline = await fakeState();
  assertBrowser(afterOffline.eventCount === beforeOffline.eventCount, "Offline fake ingestion accepts no event batch.");
  assertBrowser(localStatus.telemetryClient?.pendingEventCount >= 25, "Offline telemetry remains in the persistent local queue.");

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

async function captureDashboardPages() {
  const tasks = buildPageCaptureTasks(dashboardPageCases, scope);
  if (!tasks.length) {
    const empty = summarizeCapturePerformance({ startedAt: Date.now(), finishedAt: Date.now(), workerCount: screenshotWorkers, tasks: [] });
    await writeScreenshotPerformance(empty);
    return { screenshots: [], performance: empty };
  }
  let run;
  try {
    run = await runBoundedTaskQueue(
      tasks,
      screenshotWorkers,
      async (workerId) => {
        const context = await browser.newContext({ viewport: { width: baseViewport.width, height: baseViewport.height }, deviceScaleFactor: 1 });
        const workerPage = await context.newPage();
        attachPageEvents(workerPage, workerId);
        return { page: workerPage, close: () => context.close() };
      },
      async (worker, task) => {
        await prepareDashboardRoute(worker.page, task.route, task.theme, task.heading);
        await waitForLayoutStabilization(worker.page);
        const activeState = await inspectActiveNavigation(worker.page);
        assertBrowser(activeState.primaryHref === task.primaryHref, `${task.id} primary active state is correct: ${activeState.primaryHref}`);
        assertBrowser(activeState.settingsHref === task.settingsHref, `${task.id} settings active state is correct: ${activeState.settingsHref}`);
        const filePath = artifactPaths.pageScreenshot(task.pageName, task.theme);
        assertBrowser(relativeArtifactPath(artifactPaths, filePath) === task.artifactPath, `${task.id} artifact path matches its descriptor.`);
        await ensureArtifactParent(filePath);
        await worker.page.screenshot({ path: filePath, fullPage: true });
        return { route: `#${task.route}`, page: task.pageName, theme: task.theme, screenshot: relativeArtifactPath(artifactPaths, filePath), activeState };
      },
    );
  } catch (error) {
    const failedRun = { startedAt: Date.now(), finishedAt: Date.now(), workerCount: screenshotWorkers, tasks: error.taskResults || [] };
    await writeScreenshotPerformance(summarizeCapturePerformance(failedRun));
    throw error;
  }
  const performance = summarizeCapturePerformance(run);
  await writeScreenshotPerformance(performance);
  return { screenshots: run.tasks.map((task) => task.value), performance };
}

function attachPageEvents(targetPage, workerId = null) {
  targetPage.on("console", (message) => consoleEvents.push({ type: message.type(), text: message.text(), location: message.location(), workerId }));
  targetPage.on("pageerror", (error) => pageErrors.push(String(error?.stack || error?.message || error)));
  targetPage.on("requestfailed", (request) => networkEvents.push({ kind: "requestfailed", method: request.method(), url: request.url(), failure: request.failure()?.errorText || null, workerId }));
  targetPage.on("response", (response) => {
    if (response.status() >= 400) networkEvents.push({ kind: "response", status: response.status(), url: response.url(), workerId });
  });
}

async function writeScreenshotPerformance(performance) {
  await writeJson("screenshot-performance.json", performance);
  const rows = performance.slowestTasks.map((task) => `| ${task.id} | ${task.workerId} | ${task.durationMs} | ${task.result} |`).join("\n");
  const markdown = `# Screenshot performance\n\nScope: \`${scope}\`; workers: ${performance.workerCount}.\n\n` +
    `Tasks: ${performance.successfulTasks}/${performance.totalTasks}; capture wall: ${performance.captureWallMs} ms; summed work: ${performance.summedTaskMs} ms; speedup: ${formatMetric(performance.parallelSpeedup)}; efficiency: ${formatMetric(performance.parallelEfficiency)}.\n\n` +
    `| Task | Worker | Duration ms | Result |\n| --- | ---: | ---: | --- |\n${rows}\n`;
  await fs.writeFile(artifactPaths.report("screenshot-performance.md"), markdown, "utf8");
}

function formatMetric(value) {
  return Number.isFinite(value) ? value.toFixed(2) : "n/a";
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

async function assertGlobalThemeDock(page) {
  await prepareDashboardRoute(page, "/home", "light", "Сегодня");
  const dock = page.getByTestId("global-utility-dock");
  const toggle = page.getByTestId("theme-toggle");
  await dock.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(await dock.count() === 1, "Global utility dock renders exactly once.");
  assertBrowser(await toggle.getAttribute("aria-label") === "Включить тёмную тему", "Light theme exposes the dark-theme action.");
  const tooltip = page.locator("#theme-toggle-tooltip");
  assertBrowser(await tooltip.count() === 1 && (await tooltip.textContent())?.trim() === "Включить тёмную тему", "Theme tooltip matches the available action.");
  await toggle.focus();
  assertBrowser(await toggle.evaluate((element) => document.activeElement === element), "Theme toggle accepts keyboard focus.");
  await toggle.press("Enter");
  await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
  assertBrowser(await toggle.getAttribute("aria-label") === "Включить светлую тему", "Dark theme exposes the light-theme action.");
  assertBrowser(await page.evaluate(() => localStorage.getItem("anki-study-report-theme")) === "dark", "Explicit dark preference is stored.");

  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/calendar`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Активность", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("data-theme") === "dark", "SPA navigation preserves the selected theme.");
  assertBrowser(await page.getByTestId("global-utility-dock").count() === 1, "Navigation does not duplicate the utility dock.");
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("data-theme") === "dark", "Reload restores the stored dark theme.");

  for (const routeCase of [
    ["/decks", "Колоды"],
    ["/cards", "Карточки, требующие внимания"],
    ["/profile", "E2E"],
    ["/actions", "Инструменты"],
    ["/settings", "Отчёт"],
  ]) {
    await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#${routeCase[0]}`, { waitUntil: "networkidle", timeout: 60000 });
    await page.getByRole("heading", { name: routeCase[1], exact: true }).waitFor({ timeout: 60000 });
    assertBrowser(await page.getByTestId("theme-toggle").count() === 1, `Theme toggle is present on ${routeCase[0]}.`);
  }

  await prepareDashboardRoute(page, "/home", "dark", "Сегодня");
  const profileTrigger = page.getByRole("button", { name: "Открыть меню профиля", exact: true });
  await profileTrigger.click();
  const overlap = await page.evaluate(() => {
    const dockRect = document.querySelector('[data-testid="global-utility-dock"]')?.getBoundingClientRect();
    const menuRect = document.querySelector('[role="menu"]')?.getBoundingClientRect();
    if (!dockRect || !menuRect) return true;
    return !(dockRect.right <= menuRect.left || dockRect.left >= menuRect.right || dockRect.bottom <= menuRect.top || dockRect.top >= menuRect.bottom);
  });
  assertBrowser(!overlap, "Global utility dock does not overlap the profile menu.");
  await page.keyboard.press("Escape");
  await page.getByTestId("theme-toggle").press("Enter");
  await page.waitForFunction(() => document.documentElement.dataset.theme === "light");
  assertBrowser(await page.evaluate(() => localStorage.getItem("anki-study-report-theme")) === "light", "Theme toggle returns to and stores light mode.");
  const bodyText = await page.locator("body").innerText();
  assertBrowser(!bodyText.includes(ready.token), "Theme control does not expose the dashboard token.");
  return { routesChecked: 7, persistedAfterReload: true, navigationPreserved: true, duplicateCount: 0, profileMenuOverlap: false };
}

async function assertLocalizationDock(page) {
  const screenshots = [];
  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/home`, { waitUntil: "networkidle", timeout: 60000 });
  await page.evaluate(() => {
    localStorage.removeItem("anki-study-report-language");
    localStorage.setItem("anki-study-report-theme", "light");
  });
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Сегодня", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("lang") === "ru", "Dashboard defaults to html lang=ru.");
  assertBrowser(await page.getByTestId("language-selector").count() === 1, "Language selector renders exactly once.");
  screenshots.push(await captureLocalizationScreenshot(page, "today", "ru", "light"));

  const initialHash = new URL(page.url()).hash;
  await page.getByTestId("language-selector").click();
  assertBrowser(await page.locator("#language-selector-tooltip").count() === 0, "Language tooltip is absent while aria-expanded is true.");
  assertBrowser(await page.getByTestId("language-selector").getAttribute("aria-expanded") === "true", "Language trigger exposes the open menu state.");
  const languageMenuShot = artifactPaths.stateScreenshot("localization", "language-menu-open-ru", "light");
  await ensureArtifactParent(languageMenuShot);
  await page.screenshot({ path: languageMenuShot, fullPage: true });
  screenshots.push(relativeArtifactPath(artifactPaths, languageMenuShot));
  await page.getByRole("menuitemradio", { name: "English", exact: true }).click();
  await page.waitForFunction(() => document.documentElement.lang === "en");
  assertBrowser(new URL(page.url()).hash === initialHash, "Language switch preserves the active route.");
  assertBrowser(await page.evaluate(() => localStorage.getItem("anki-study-report-language")) === "en", "English preference is stored.");
  await page.getByRole("heading", { name: "Today", exact: true }).waitFor({ timeout: 15000 });
  screenshots.push(await captureLocalizationScreenshot(page, "today", "en", "light"));

  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/stats`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Statistics", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("lang") === "en", "SPA navigation preserves English on Statistics.");
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Statistics", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("lang") === "en", "Reload restores English preference.");

  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/stats/fsrs`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "FSRS", exact: true }).waitFor({ timeout: 60000 });
  await page.getByTestId("theme-toggle").click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
  assertBrowser(await page.locator("html").getAttribute("lang") === "en", "Theme switch does not reset English.");
  screenshots.push(await captureLocalizationScreenshot(page, "fsrs-overview", "en", "dark"));

  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/settings`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Report", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(await page.locator("html").getAttribute("lang") === "en", "Settings renders in English.");

  const settingsHash = new URL(page.url()).hash;
  await page.getByTestId("language-selector").click();
  await page.getByRole("menuitemradio", { name: "Русский", exact: true }).click();
  await page.waitForFunction(() => document.documentElement.lang === "ru");
  await page.getByRole("heading", { name: "Отчёт", exact: true }).waitFor({ timeout: 15000 });
  assertBrowser(new URL(page.url()).hash === settingsHash, "Switching back to Russian preserves Settings route.");
  assertBrowser(await page.locator("html").getAttribute("data-theme") === "dark", "Switching language preserves dark theme.");
  screenshots.push(await captureLocalizationScreenshot(page, "settings-report", "ru", "dark"));

  await page.getByTestId("theme-toggle").click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "light");
  return { routesChecked: 4, persistedAfterReload: true, themeIndependent: true, screenshots, screenshotCount: screenshots.length };
}

async function captureLocalizationScreenshot(page, pageName, language, theme) {
  const filePath = artifactPaths.stateScreenshot("localization", `${pageName}-${language}`, theme);
  await ensureArtifactParent(filePath);
  await page.screenshot({ path: filePath, fullPage: true });
  return { page: pageName, language, theme, screenshot: relativeArtifactPath(artifactPaths, filePath) };
}

async function assertActivityHub(page) {
  await prepareDashboardRoute(page, "/calendar", "light", "Активность");
  const period = page.locator("#activity-period");
  assertBrowser(await period.inputValue() === "90d", "Activity defaults to the last 90 days.");
  for (const metric of ["Повторения", "Время", "Новые", "Успешность"]) {
    await page.getByRole("button", { name: metric, exact: true }).waitFor({ state: "visible", timeout: 15000 });
  }
  assertBrowser(await page.getByRole("button", { name: "Прогноз", exact: true }).count() === 0, "Activity has no placeholder forecast metric.");
  await page.getByRole("button", { name: "Время", exact: true }).click();
  assertBrowser(await page.getByRole("button", { name: "Время", exact: true }).getAttribute("aria-pressed") === "true", "Activity metric switch updates selection.");
  await page.getByRole("button", { name: "Повторения", exact: true }).click();

  const selected = page.locator('[data-testid="activity-calendar"] button[aria-pressed="true"]');
  assertBrowser(await selected.count() === 1, "Activity has exactly one selected day.");
  const selectedDate = await selected.getAttribute("data-date");
  const inactive = page.locator('[data-testid="activity-calendar"] button[data-availability="inactive"]').first();
  await inactive.click();
  await page.getByTestId("activity-day-detail").getByRole("heading", { name: "Занятий не было", exact: true }).waitFor({ state: "visible", timeout: 15000 });
  const inactiveDate = await inactive.getAttribute("data-date");

  const todayButton = page.locator(`[data-testid="activity-calendar"] button[data-date="${selectedDate}"]`);
  await todayButton.click();
  const detail = page.getByTestId("activity-day-detail");
  await detail.getByText("Активные колоды", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
  const expand = detail.getByRole("button", { name: /Показать ещё \d+/, exact: false });
  assertBrowser(await expand.count() === 1, "Activity selected day exposes more than five decks.");
  const collapsedDeckRows = await detail.locator("div.mt-2.grid.gap-2 > div").count();
  await expand.click();
  const expandedDeckRows = await detail.locator("div.mt-2.grid.gap-2 > div").count();
  assertBrowser(expandedDeckRows > collapsedDeckRows && collapsedDeckRows === 5, `Activity deck list expands from five rows: ${collapsedDeckRows} -> ${expandedDeckRows}`);
  await detail.getByRole("button", { name: "Свернуть", exact: true }).click();

  const feed = page.getByTestId("activity-feed");
  const initialDaily = await feed.locator('[data-feed-type="daily_summary"]').count();
  assertBrowser(initialDaily === 14, `Activity feed starts with 14 active days: ${initialDaily}`);
  assertBrowser(await feed.locator('[data-feed-type="daily_summary"] .status-pill').count() === 0, "Ordinary Activity entries do not repeat the daily-summary badge.");
  const monthKeysBefore = await feed.locator("[data-activity-month]").evaluateAll((items) => items.map((item) => item.getAttribute("data-activity-month")));
  assertBrowser(new Set(monthKeysBefore).size === monthKeysBefore.length, "Activity month headings are unique before load-more.");
  assertBrowser(await page.locator(".activity-calendar-date").count() > 0 && await page.locator(".activity-calendar-value").count() > 0, "Activity cells expose primary dates and secondary metric values.");
  await page.getByText(/Возвращение после 2 дней без занятий/).first().waitFor({ state: "visible", timeout: 15000 });
  await page.getByText(/Серия достигла 3/).first().waitFor({ state: "visible", timeout: 15000 });
  await page.getByText(/Новый максимум:/).first().waitFor({ state: "visible", timeout: 15000 });
  await page.getByText("Итоги завершённой недели", { exact: true }).first().waitFor({ state: "visible", timeout: 15000 });
  const loadMore = page.getByRole("button", { name: "Показать более раннюю активность", exact: true });
  assertBrowser(await loadMore.count() === 1, "Activity feed exposes deterministic load more.");
  await loadMore.click();
  const expandedDaily = await feed.locator('[data-feed-type="daily_summary"]').count();
  assertBrowser(expandedDaily > initialDaily, `Activity feed loads earlier active days: ${initialDaily} -> ${expandedDaily}`);
  const monthKeysAfter = await feed.locator("[data-activity-month]").evaluateAll((items) => items.map((item) => item.getAttribute("data-activity-month")));
  assertBrowser(new Set(monthKeysAfter).size === monthKeysAfter.length, "Activity load-more merges entries into unique month groups.");
  const bodyText = await page.locator("body").innerText();
  assertBrowser(!bodyText.includes(ready.token), "Activity DOM does not expose the dashboard token.");
  return { selectedDate, inactiveDate, initialDaily, expandedDaily, collapsedDeckRows, expandedDeckRows, monthGroups: monthKeysAfter };
}

async function assertStatisticsHub(page) {
  await prepareDashboardRoute(page, "/stats", "light", "Статистика");
  await page.getByTestId("statistics-page").waitFor({ state: "visible", timeout: 15000 });
  const navLabels = await page.locator('nav[aria-label="Основная навигация"] a').allTextContents();
  assertBrowser(
    JSON.stringify(navLabels.map((value) => value.trim())) === JSON.stringify(["Сегодня", "Активность", "Статистика", "Колоды", "Поиск", "Карточки"]),
    `Statistics primary navigation order is correct: ${JSON.stringify(navLabels)}`,
  );
  const sectionLinks = page.locator('nav[aria-label="Разделы статистики"] a');
  assertBrowser(await sectionLinks.count() === 6, "Statistics exposes six real sections including FSRS.");
  assertBrowser(await page.getByTestId("global-utility-dock").count() === 1, "Statistics keeps the global theme dock.");
  const periodSelect = page
    .locator('section[aria-label="Параметры статистики"] label')
    .filter({ hasText: /^Период/ })
    .locator("select");
  assertBrowser(await periodSelect.inputValue() === "90d", "Statistics defaults to 90 days.");
  for (const label of ["Повторения", "Время учёбы", "Успешность", "Новые карточки", "Активные дни", "Средний ответ"]) {
    await page.getByText(label, { exact: true }).first().waitFor({ state: "visible", timeout: 15000 });
  }

  for (const routeCase of [
    ["/stats/quality", "Качество", "Истинное удержание"],
    ["/stats/load", "Нагрузка", "Будущая нагрузка"],
    ["/stats/progress", "Прогресс", "Текущее состояние коллекции"],
    ["/stats/decks", "Колоды", "Успешность по выбранным колодам"],
  ]) {
    await prepareDashboardRoute(page, routeCase[0], "light", routeCase[1]);
    await page.getByText(routeCase[2], { exact: true }).first().waitFor({ state: "visible", timeout: 15000 });
    const primary = await inspectActiveNavigation(page);
    assertBrowser(primary.primaryHref === "#/stats", `${routeCase[0]} keeps Statistics active in primary navigation.`);
  }

  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Колоды", exact: true }).waitFor({ timeout: 60000 });
  assertBrowser(new URL(page.url()).hash === "#/stats/decks", "Statistics nested direct route survives reload.");

  await prepareDashboardRoute(page, "/stats", "light", "Статистика");
  const queryResponse = page.waitForResponse((response) => response.url().includes("/api/statistics/query") && response.request().method() === "POST");
  await periodSelect.selectOption("30d");
  const response = await queryResponse;
  assertBrowser(response.status() === 200, `Statistics typed query succeeds: ${response.status()}`);
  await periodSelect.selectOption("all");
  assertBrowser(await page.getByLabel("Сравнить периоды").isDisabled(), "All-time disables previous-period comparison.");
  await periodSelect.selectOption("90d");
  await page.getByLabel("Область").selectOption("single_deck");
  await page.getByLabel("Только напрямую").check();
  await page.getByText("Только напрямую", { exact: true }).waitFor({ state: "visible", timeout: 15000 });

  for (const routeCase of [
    ["/stats", "Статистика"],
    ["/stats/quality", "Качество"],
    ["/stats/load", "Нагрузка"],
    ["/stats/progress", "Прогресс"],
    ["/stats/decks", "Колоды"],
  ]) {
    await prepareDashboardRoute(page, routeCase[0], "light", routeCase[1]);
    const layout = await inspectStatisticsLayout(page);
    assertBrowser(!layout.horizontalOverflow, `${routeCase[0]} has no horizontal overflow.`);
    assertBrowser(layout.panelCount > 0 && layout.panelBordersVisible, `${routeCase[0]} analytical panels have visible boundaries.`);
    assertBrowser(!layout.controlsChaotic && layout.sidebarUsable, `${routeCase[0]} controls and sidebar remain usable.`);
    assertBrowser(layout.dockOverlapCount === 0, `${routeCase[0]} global dock does not overlap actionable Statistics content.`);
    assertBrowser(layout.chartClippingCount === 0, `${routeCase[0]} chart labels stay inside their panels.`);
  }

  await prepareDashboardRoute(page, "/stats/decks", "light", "Колоды");
  assertBrowser(await page.locator('.statistics-deck-table input[type="checkbox"]:checked').count() > 0, "Deck comparison has a useful default selection.");
  assertBrowser(await page.getByTestId("stats-deck-comparison-chart").isVisible(), "Deck comparison chart is visible on initial load.");
  const visibleStatisticsText = await page.locator('[data-testid="statistics-page"]').innerText();
  assertBrowser(!/STATISTICS V1|True Retention|Daily load|\bMature\b|Σ 1 \/ max|максимум 12/i.test(visibleStatisticsText), "Statistics hides developer terminology and formulas from primary UI.");

  const nativeResult = await page.evaluate(async () => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const response = await fetch(`/api/actions/open-native-stats?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    return { status: response.status, body: await response.json() };
  });
  assertBrowser(nativeResult.status === 200 && nativeResult.body?.ok === true, "Native Anki Stats action callback succeeds.");
  const bodyText = await page.locator("body").innerText();
  assertBrowser(!bodyText.includes(ready.token), "Statistics DOM does not expose the dashboard token.");
  const fsrs = await assertFsrsHub(page);
  return {
    routesChecked: 10,
    defaultPeriod: "90d",
    typedQueryStatus: response.status(),
    allTimeComparisonDisabled: true,
    singleDeckDirectChecked: true,
    nativeActionOk: true,
    visualLayoutChecked: true,
    defaultDeckSelection: true,
    fsrs,
  };
}

async function assertFsrsHub(page) {
  for (const [route, heading] of [
    ["/stats/fsrs", "FSRS"], ["/stats/fsrs/memory", "Состояние памяти"],
    ["/stats/fsrs/calibration", "Точность модели"], ["/stats/fsrs/steps", "Шаги обучения"],
    ["/stats/fsrs/simulator", "Симулятор"],
  ]) {
    await prepareDashboardRoute(page, route, "light", heading);
    await page.getByTestId("fsrs-page").waitFor({ state: "visible", timeout: 15000 });
    const primary = await inspectActiveNavigation(page);
    assertBrowser(primary.primaryHref === "#/stats", `${route} keeps Statistics active.`);
    assertBrowser(await page.locator('nav[aria-label="Разделы FSRS"] a[aria-current="page"]').count() === 1, `${route} has one active local FSRS item.`);
  }
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  assertBrowser(new URL(page.url()).hash === "#/stats/fsrs/simulator", "FSRS nested direct route survives reload.");
  await prepareDashboardRoute(page, "/stats/fsrs/memory", "light", "Состояние памяти");
  await page.getByTestId("fsrs-memory").waitFor({ state: "visible", timeout: 30000 });
  assertBrowser(await page.getByText("Оценка запомненного", { exact: true }).count() === 0, "Memory route uses expected-estimate wording instead of a guaranteed card list.");
  await prepareDashboardRoute(page, "/stats/fsrs/calibration", "light", "Точность модели");
  await page.getByRole("button", { name: /Рассчитать точность/ }).click();
  await page.getByTestId("fsrs-calibration").waitFor({ state: "visible", timeout: 30000 });
  await prepareDashboardRoute(page, "/stats/fsrs/simulator", "light", "Симулятор");
  await page.getByRole("button", { name: /^Рассчитать сценарий$/ }).click();
  await page.getByTestId("fsrs-simulator-result").waitFor({ state: "visible", timeout: 60000 });
  const loadedChunks = await page.evaluate(() => performance.getEntriesByType("resource")
    .map((entry) => entry.name)
    .filter((name) => /StatisticsPage|FsrsStatisticsPage/.test(name))
    .map((name) => new URL(name).pathname));
  assertBrowser(loadedChunks.some((name) => name.includes("FsrsStatisticsPage")), "Cold FSRS navigation loads its lazy route chunk.");
  await prepareDashboardRoute(page, "/decks", "light", "Колоды");
  await page.getByTestId("deck-tree-panel").waitFor({ state: "visible", timeout: 30000 });
  await prepareDashboardRoute(page, "/stats/fsrs/steps", "light", "Шаги обучения");
  await page.getByTestId("fsrs-steps").waitFor({ state: "visible", timeout: 30000 });
  const text = await page.getByTestId("fsrs-page").innerText();
  assertBrowser(!/Применить|Перепланировать|Оптимизировать/.test(text), "FSRS exposes no mutating action.");
  assertBrowser(!text.includes(ready.token), "FSRS DOM does not expose the dashboard token.");
  return { routes: 5, memory: true, calibration: true, simulator: true, packagedLazyChunkPaths: loadedChunks, nonStatisticsAfterFsrs: true, coldFsrsAfterNonStatistics: true, mutatingActions: 0 };
}

async function inspectStatisticsLayout(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-testid="statistics-page"], [data-testid="fsrs-page"]');
    const dockRect = document.querySelector('[data-testid="global-utility-dock"]')?.getBoundingClientRect();
    const controls = document.querySelector(".statistics-controls");
    const sidebar = document.querySelector(".statistics-sidebar");
    const panels = [...document.querySelectorAll(".statistics-panel")];
    const actionable = [...document.querySelectorAll('[data-testid="statistics-page"] button, [data-testid="statistics-page"] a, [data-testid="statistics-page"] input, [data-testid="statistics-page"] select, [data-testid="fsrs-page"] button, [data-testid="fsrs-page"] a, [data-testid="fsrs-page"] input, [data-testid="fsrs-page"] select')]
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
    const dockOverlapCount = dockRect ? actionable.filter((element) => {
      const rect = element.getBoundingClientRect();
      return !(dockRect.right <= rect.left || dockRect.left >= rect.right || dockRect.bottom <= rect.top || dockRect.top >= rect.bottom);
    }).length : 0;
    const chartClippingCount = [...document.querySelectorAll(".statistics-rechart")].filter((chart) => chart.scrollWidth > chart.clientWidth + 1).length;
    const controlRows = controls ? new Set([...controls.children].map((element) => Math.round(element.getBoundingClientRect().top))).size : 0;
    return {
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      panelCount: panels.length,
      panelBordersVisible: panels.every((panel) => Number.parseFloat(getComputedStyle(panel).borderTopWidth) >= 1),
      controlsChaotic: controlRows > 2,
      sidebarUsable: Boolean(sidebar && sidebar.getBoundingClientRect().width > 160 && sidebar.getBoundingClientRect().height > 100),
      dockOverlapCount,
      chartClippingCount,
      rootVisible: Boolean(root && root.getBoundingClientRect().width > 0),
    };
  });
}

async function assertDeckHub(page) {
  await prepareDashboardRoute(page, "/decks", "light", "Колоды");
  const header = page.locator("header").filter({ has: page.getByRole("heading", { name: "Колоды", exact: true }) });
  for (const label of ["Всего колод", "Требуют внимания", "Опасные", "Средняя успешность"]) {
    await header.getByText(label, { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  }
  const report = await fetchReport();
  const hub = report.deckHub;
  assertBrowser(hub?.schemaVersion === 1, "Decks v2 payload is available.");
  assertBrowser(Array.isArray(hub?.rootIds) && hub.rootIds.length >= 2, "Decks v2 has multiple roots.");
  assertBrowser(!Object.values(hub?.nodes || {}).some((node) => node.fullName === "E2E Filtered Health Excluded"), "Filtered fixture deck is absent from health nodes.");
  assertBrowser(Number(hub?.summary?.filteredDecksExcluded || 0) >= 1, "Filtered fixture deck is counted as excluded.");
  assertBrowser(await page.getByTestId("filtered-decks-info").count() === 1, "Filtered-deck exclusion is shown as one compact information line.");
  const groupsToggle = page.getByTestId("deck-groups-toggle");
  assertBrowser(await groupsToggle.innerText() === "Развернуть группы", "Deck groups control offers an effective expand action initially.");
  await groupsToggle.click();
  assertBrowser(await groupsToggle.innerText() === "Свернуть все", "Deck groups control switches to collapse after root expansion.");
  assertBrowser(await page.locator('button[title="E2E Decks::Danger"]').count() === 1, "Global expand opens root groups.");
  assertBrowser(await page.locator('button[title*="Уровень 6"]').count() === 0, "Global expand does not recursively open deep descendants.");
  await groupsToggle.click();
  assertBrowser(await groupsToggle.innerText() === "Развернуть группы", "Deck groups collapse returns to the initial action.");

  const parentRow = page.locator('button[title="E2E Decks"]');
  await parentRow.waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(await page.locator('button[title="E2E Decks::Danger"]').count() === 0, "Deck children are collapsed initially.");
  const disclosure = page.getByRole("button", { name: "Развернуть E2E Decks", exact: true });
  assertBrowser(await disclosure.getAttribute("aria-expanded") === "false", "Deck disclosure starts collapsed.");
  await disclosure.click();
  await page.locator('button[title="E2E Decks::Danger"]').waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(await page.getByRole("button", { name: "Свернуть E2E Decks", exact: true }).getAttribute("aria-expanded") === "true", "Deck disclosure expands with aria-expanded.");

  const search = page.getByPlaceholder("Найти колоду…", { exact: true });
  await search.fill("Danger");
  assertBrowser(await groupsToggle.isDisabled(), "Deck groups control is disabled honestly during search auto-expansion.");
  assertBrowser(await groupsToggle.innerText() === "Группы раскрыты фильтром", "Deck groups control explains search auto-expansion.");
  await page.locator('button[title="E2E Decks"]').waitFor({ state: "visible", timeout: 15000 });
  await page.locator('button[title="E2E Decks::Danger"]').waitFor({ state: "visible", timeout: 15000 });
  assertBrowser(await page.locator('button[title="E2E Grammar::N3"]').count() === 0, "Deck search removes unrelated branches.");
  await search.fill("");
  assertBrowser(!(await groupsToggle.isDisabled()), "Deck groups control is restored after search.");
  assertBrowser(await page.locator('button[title="E2E Decks::Danger"]').count() === 1, "Clearing search restores manual expansion.");

  const selects = page.locator("select");
  await selects.nth(0).selectOption("danger");
  await search.fill("E2E Decks::Danger");
  await page.getByRole("heading", { name: "Danger", exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await selects.nth(1).selectOption("reviews");
  assertBrowser(await page.locator('button[title="E2E Decks::Danger"]').count() === 1, "Deck sort preserves hierarchy under filter.");
  await search.fill("");
  await selects.nth(0).selectOption("all");
  await parentRow.click();
  await page.getByText("Прямые и иерархические данные", { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await page.getByText(/С дочерними:/).waitFor({ state: "visible", timeout: 15000 });
  await page.getByText(/В самой колоде:/).waitFor({ state: "visible", timeout: 15000 });
  await page.getByRole("heading", { name: "Проблемы внутри", exact: true }).waitFor({ state: "visible", timeout: 15000 });
  for (const section of ["identity", "reasons", "metrics", "direct-subtree", "issues", "recommendations", "actions"]) {
    assertBrowser(await page.locator(`[data-detail-section="${section}"]`).count() === 1, `Deck detail section ${section} is present when applicable.`);
  }
  const treePanelHeight = await page.getByTestId("deck-tree-panel").evaluate((element) => element.getBoundingClientRect().height);
  const detailPanelHeight = await page.getByTestId("deck-detail-panel").evaluate((element) => element.getBoundingClientRect().height);
  assertBrowser(treePanelHeight < detailPanelHeight || Math.abs(treePanelHeight - detailPanelHeight) < 80, "Short deck tree keeps its natural height instead of stretching to the detail panel.");

  await page.getByRole("button", { name: "Открыть с дочерними", exact: true }).click();
  await page.getByText("Opened deck in Anki Browser.", { exact: true }).waitFor({ state: "visible", timeout: 15000 });
  await page.getByRole("button", { name: "Только эта колода", exact: true }).click();
  await page.getByText("Opened deck in Anki Browser.", { exact: true }).waitFor({ state: "visible", timeout: 15000 });

  const bodyText = await page.locator("body").innerText();
  assertBrowser(!bodyText.includes(ready.token), "Decks DOM does not expose the dashboard token.");
  return {
    roots: hub.rootIds.length,
    nodes: Object.keys(hub.nodes || {}).length,
    filteredExcluded: hub.summary.filteredDecksExcluded,
    parent: hub.nodes?.[String(Object.values(hub.nodes || {}).find((node) => node.fullName === "E2E Decks")?.deckId || "")],
    actions: ["subtree", "direct"],
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
      JSON.stringify(menuItems.map((item) => item.trim())) === JSON.stringify(["Профиль", "Настройки", "Инструменты", "Что нового", "Поддержать проект"]),
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

async function capturePolishStates(page, selectedScope) {
  const screenshots = [];
  if (shouldRunScope(selectedScope, "activity")) {
  await prepareDashboardRoute(page, "/calendar", "light", "Активность");
  const loadMore = page.getByRole("button", { name: "Показать более раннюю активность", exact: true });
  if (await loadMore.count()) await loadMore.click();
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "calendar", "history-expanded"));
  }

  if (shouldRunScope(selectedScope, "decks")) {
  await prepareDashboardRoute(page, "/decks", "light", "Колоды");
  await page.getByTestId("deck-groups-toggle").click();
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "decks", "root-groups-expanded"));
  await page.locator('button[title="E2E Decks"]').click();
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "decks", "selected-parent"));
  await page.locator('button[title="E2E Decks::Danger"]').click();
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "decks", "selected-leaf"));
  }

  if (shouldRunScope(selectedScope, "stats")) {
  await prepareDashboardRoute(page, "/stats", "light", "Статистика");
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-overview", "sparse"));
  const statisticsPeriod = page
    .locator('section[aria-label="Параметры статистики"] label')
    .filter({ hasText: /^Период/ })
    .locator("select");
  await statisticsPeriod.selectOption("7d");
  await page.locator('[data-comparison-style="outline-dashed"]').first().waitFor({ state: "visible", timeout: 15000 });
  screenshots.push(await saveStateScreenshot(page, "stats-overview", "comparison"));

  await prepareDashboardRoute(page, "/stats/quality", "light", "Качество");
  await page.getByLabel("Область").selectOption("single_deck");
  const statisticsDeck = page
    .locator('section[aria-label="Параметры статистики"] label')
    .filter({ hasText: /^Колода/ })
    .locator("select");
  await statisticsDeck.selectOption({ label: "E2E Grammar" });
  await page.locator(".statistics-confidence-badge.is-insufficient").first().waitFor({ state: "visible", timeout: 15000 });
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-quality", "low-confidence"));

  await prepareDashboardRoute(page, "/stats/load", "light", "Нагрузка");
  await page.getByTestId("stats-load-future-due").waitFor({ state: "visible", timeout: 15000 });
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-load", "future-due"));

  await prepareDashboardRoute(page, "/stats/progress", "light", "Прогресс");
  await page.getByTestId("stats-progress-current-state").waitFor({ state: "visible", timeout: 15000 });
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-progress", "current-state"));

  await prepareDashboardRoute(page, "/stats/decks", "light", "Колоды");
  await page.getByTestId("stats-deck-comparison-chart").waitFor({ state: "visible", timeout: 15000 });
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-decks", "default-selection"));
  const selectedDeck = page.locator('.statistics-deck-table input[type="checkbox"]:checked').first();
  if (await selectedDeck.count()) await selectedDeck.uncheck();
  const availableDeck = page.locator('.statistics-deck-table input[type="checkbox"]:not(:checked):not(:disabled)').last();
  if (await availableDeck.count()) await availableDeck.check();
  await waitForLayoutStabilization(page);
  screenshots.push(await saveStateScreenshot(page, "stats-decks", "custom-selection"));

  await prepareDashboardRoute(page, "/stats/fsrs", "light", "FSRS");
  await page.getByTestId("fsrs-overview").waitFor({ state: "visible", timeout: 30000 });
  screenshots.push(await saveStateScreenshot(page, "fsrs-overview", "mixed-config"));
  await prepareDashboardRoute(page, "/stats/fsrs/memory", "light", "Состояние памяти");
  await page.getByTestId("fsrs-memory").waitFor({ state: "visible", timeout: 30000 });
  screenshots.push(await saveStateScreenshot(page, "fsrs-memory", "snapshot"));
  await prepareDashboardRoute(page, "/stats/fsrs/calibration", "light", "Точность модели");
  screenshots.push(await saveStateScreenshot(page, "fsrs-calibration", "idle", "light"));
  screenshots.push(await saveStateScreenshot(page, "fsrs-calibration", "idle", "dark"));
  await page.getByRole("button", { name: /Рассчитать точность/ }).click();
  await page.getByTestId("fsrs-calibration").waitFor({ state: "visible", timeout: 30000 });
  screenshots.push(await saveStateScreenshot(page, "fsrs-calibration", "ready-sparse", "light"));
  screenshots.push(await saveStateScreenshot(page, "fsrs-calibration", "ready-sparse", "dark"));
  await prepareDashboardRoute(page, "/stats/fsrs/steps", "light", "Шаги обучения");
  await page.getByTestId("fsrs-steps").waitFor({ state: "visible", timeout: 30000 });
  screenshots.push(await saveStateScreenshot(page, "fsrs-steps", "insufficient"));
  await prepareDashboardRoute(page, "/stats/fsrs/simulator", "light", "Симулятор");
  screenshots.push(await saveStateScreenshot(page, "fsrs-simulator", "idle-form", "light"));
  screenshots.push(await saveStateScreenshot(page, "fsrs-simulator", "idle-form", "dark"));
  await page.getByRole("button", { name: /^Рассчитать сценарий$/ }).click();
  await page.getByTestId("fsrs-simulator-result").waitFor({ state: "visible", timeout: 60000 });
  screenshots.push(await saveStateScreenshot(page, "fsrs-simulator", "ready", "light"));
  screenshots.push(await saveStateScreenshot(page, "fsrs-simulator", "ready", "dark"));
  }
  return screenshots;
}

async function saveStateScreenshot(page, pageName, stateName, theme = "light") {
  await page.evaluate((selectedTheme) => {
    window.localStorage.setItem("anki-study-report-theme", selectedTheme);
    document.documentElement.dataset.theme = selectedTheme;
    document.documentElement.style.colorScheme = selectedTheme;
  }, theme);
  await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "instant" }));
  await waitForLayoutStabilization(page);
  const filePath = artifactPaths.stateScreenshot(pageName, stateName, theme);
  await ensureArtifactParent(filePath);
  await page.screenshot({ path: filePath, fullPage: true });
  return { page: pageName, state: stateName, theme, screenshot: relativeArtifactPath(artifactPaths, filePath) };
}

async function assertInspectionProfilesWorkspace(page) {
  await prepareDashboardRoute(page, "/settings/inspection-profiles", "light", "Профили проверки");
  const japanese = page.getByRole("button", { name: /E2E Japanese Vocabulary/ });
  const programming = page.getByRole("button", { name: /E2E Programming/ });
  const suggestionSource = page.getByRole("button", { name: /E2E Generic Basic/ });
  await japanese.waitFor({ state: "visible", timeout: 30000 });
  await programming.waitFor({ state: "visible", timeout: 30000 });
  await suggestionSource.waitFor({ state: "visible", timeout: 30000 });
  const listScreenshot = await saveStateScreenshot(page, "inspection-profiles", "list", "light");

  await japanese.click();
  await page.getByRole("heading", { name: "E2E Japanese Vocabulary" }).waitFor({ state: "visible", timeout: 30000 });
  const lifecycleText = await page.locator(".inspection-editor-header").innerText();
  const expectedState = label === "first" ? "Подтверждён" : "Нужна проверка";
  assertBrowser(lifecycleText.includes(expectedState), `Inspection Profiles editor shows ${expectedState}.`);
  const editorScreenshot = await saveStateScreenshot(page, "inspection-profiles", label === "first" ? "confirmed-editor" : "needs-review", "light");

  await suggestionSource.click();
  await page.getByRole("heading", { name: "E2E Generic Basic" }).waitFor({ state: "visible", timeout: 30000 });
  const sourceLifecycleText = await page.locator(".inspection-editor-header").innerText();
  assertBrowser(sourceLifecycleText.includes("Не настроен"), "Suggestion flow starts from a stable unconfigured fixture profile.");
  await page.getByRole("button", { name: "Использовать подсказку", exact: true }).click();
  await page.getByText("Есть несохранённые изменения").waitFor({ state: "visible", timeout: 10000 });
  const dirtyScreenshot = await saveStateScreenshot(page, "inspection-profiles", "dirty-suggestion", "dark");
  await page.getByRole("button", { name: "Проверить профиль", exact: true }).click();
  await page.getByRole("heading", { name: "Проверка и ограниченный пример" }).waitFor({ state: "visible", timeout: 30000 });
  const previewScreenshot = await saveStateScreenshot(page, "inspection-profiles", "validated-preview", "light");

  await programming.evaluate((element) => element.click());
  const unsavedDialog = page.getByTestId("inspection-unsaved-dialog");
  await unsavedDialog.waitFor({ state: "visible", timeout: 10000 });
  assertBrowser((await unsavedDialog.innerText()).includes("Отбросить несохранённые изменения?"), "Unsaved navigation dialog has the expected accessible title.");
  await unsavedDialog.getByRole("button", { name: "Продолжить редактирование", exact: true }).click();
  assertBrowser(await page.getByText("Есть несохранённые изменения").isVisible(), "Unsaved draft remains after cancelling note-type navigation.");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assertBrowser(overflow <= 2, "Inspection Profiles workspace has no horizontal page overflow.");
  return {
    expectedState,
    suggestionSourceName: "E2E Generic Basic",
    suggestionCreatesDirtyDraft: true,
    validateV2PreviewVisible: true,
    unsavedNavigationProtected: true,
    noHorizontalOverflow: true,
    screenshots: [listScreenshot, editorScreenshot, dirtyScreenshot, previewScreenshot],
  };
}

async function captureZoomProof(selectedScope) {
  const zoomPage = await browser.newPage({ viewport: { width: 1152, height: 800 }, deviceScaleFactor: 1.25 });
  const results = [];
  zoomPage.on("console", (message) => consoleEvents.push({ type: message.type(), text: message.text(), location: message.location() }));
  zoomPage.on("pageerror", (error) => pageErrors.push(String(error?.stack || error?.message || error)));
  zoomPage.on("requestfailed", (request) => networkEvents.push({ kind: "requestfailed", method: request.method(), url: request.url(), failure: request.failure()?.errorText || null }));
  zoomPage.on("response", (response) => {
    if (response.status() >= 400) networkEvents.push({ kind: "response", status: response.status(), url: response.url() });
  });
  try {
    for (const routeCase of [
      { route: "/calendar", pageName: "calendar", heading: "Активность", scope: "activity" },
      { route: "/stats", pageName: "stats-overview", heading: "Статистика", scope: "stats" },
      { route: "/stats/quality", pageName: "stats-quality", heading: "Качество", scope: "stats" },
      { route: "/stats/load", pageName: "stats-load", heading: "Нагрузка", scope: "stats" },
      { route: "/stats/decks", pageName: "stats-decks", heading: "Колоды", scope: "stats" },
      { route: "/stats/fsrs", pageName: "fsrs-overview", heading: "FSRS", scope: "stats" },
      { route: "/stats/fsrs/calibration", pageName: "fsrs-calibration", heading: "Точность модели", scope: "stats" },
      { route: "/stats/fsrs/simulator", pageName: "fsrs-simulator", heading: "Симулятор", scope: "stats" },
      { route: "/decks", pageName: "decks", heading: "Колоды", scope: "decks" },
      { route: "/settings", pageName: "settings/report", heading: "Отчёт", scope: "settings" },
    ].filter((item) => shouldRunScope(selectedScope, item.scope))) {
      await prepareDashboardRoute(zoomPage, routeCase.route, "light", routeCase.heading);
      await zoomPage.waitForFunction(() => document.documentElement.clientWidth === 1152 && window.devicePixelRatio === 1.25);
      const layout = await inspectZoomLayout(zoomPage);
      assertBrowser(!layout.horizontalOverflow, `${routeCase.route} has no horizontal clipping at emulated 125% scale.`);
      assertBrowser(layout.dockVisible && layout.dockOverlapCount === 0 && layout.mainPaddingRight >= 78, `${routeCase.route} utility dock stays visible inside the App Shell safe inset at emulated 125% scale: ${JSON.stringify(layout)}`);
      const filePath = artifactPaths.zoomScreenshot(routeCase.pageName);
      await ensureArtifactParent(filePath);
      await zoomPage.screenshot({ path: filePath, fullPage: true });
      results.push({ ...routeCase, screenshot: relativeArtifactPath(artifactPaths, filePath), layout });
    }
  } finally {
    await zoomPage.close();
  }
  return {
    method: "Playwright isolated browser context with 1152x800 CSS viewport and deviceScaleFactor 1.25 (1440x1000 physical target)",
    pages: results,
  };
}

async function inspectZoomLayout(page) {
  return page.evaluate(() => {
    const dock = document.querySelector('[data-testid="global-utility-dock"]');
    const dockRect = dock?.getBoundingClientRect();
    const actionable = [...document.querySelectorAll("main button, main a, main input, main select")]
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      });
    const overlaps = dockRect ? actionable.filter((element) => {
      const rect = element.getBoundingClientRect();
      return !(dockRect.right <= rect.left || dockRect.left >= rect.right || dockRect.bottom <= rect.top || dockRect.top >= rect.bottom);
    }) : [];
    return {
      cssViewport: { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight },
      devicePixelRatio: window.devicePixelRatio,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      dockVisible: Boolean(dockRect && dockRect.width > 0 && dockRect.height > 0),
      dockOverlapCount: overlaps.length,
      mainPaddingRight: Number.parseFloat(getComputedStyle(document.querySelector("main")).paddingRight) || 0,
    };
  });
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
  const deckFilterExpectation = buildApkgDeckFilterExpectation(report, importSummary, deckName);
  await captureApkg(page, "table", "light", artifactPaths.cardsScreenshot("apkg", "table", "light"), deckName, deckFilterExpectation);
  const tableLightDetails = await inspectApkgShadowPreviews(page, "table");
  const tableLightLayout = await inspectTableLayout(page);
  assertBrowser(tableLightDetails.hostCount >= Math.min(3, apkgCards.length), `APKG light table previews found: ${tableLightDetails.hostCount}`);
  assertShadowSummary(tableLightDetails, "table light");
  assertTableLayoutSummary(tableLightLayout, "APKG light table");

  await captureApkg(page, "table", "dark", artifactPaths.cardsScreenshot("apkg", "table", "dark"), deckName, deckFilterExpectation);
  const tableDetails = await inspectApkgShadowPreviews(page, "table");
  const tableLayout = await inspectTableLayout(page);
  assertBrowser(tableDetails.hostCount >= Math.min(3, apkgCards.length), `APKG table previews found: ${tableDetails.hostCount}`);
  assertShadowSummary(tableDetails, "table");
  assertTableLayoutSummary(tableLayout, "APKG dark table");

  await captureApkg(page, "tiles", "light", artifactPaths.cardsScreenshot("apkg", "tiles", "light"), deckName, deckFilterExpectation);
  const tileLightDetails = await inspectApkgShadowPreviews(page, "tile");
  const tileLightLayout = await inspectTileLayout(page);
  assertBrowser(tileLightDetails.hostCount >= Math.min(3, apkgCards.length), `APKG light tile previews found: ${tileLightDetails.hostCount}`);
  assertShadowSummary(tileLightDetails, "tile light");
  assertTileLayoutSummary(tileLightLayout, "APKG light tiles");

  await captureApkg(page, "tiles", "dark", artifactPaths.cardsScreenshot("apkg", "tiles", "dark"), deckName, deckFilterExpectation);
  const tileDetails = await inspectApkgShadowPreviews(page, "tile");
  const tileLayout = await inspectTileLayout(page);
  assertBrowser(tileDetails.hostCount >= Math.min(3, apkgCards.length), `APKG tile previews found: ${tileDetails.hostCount}`);
  assertShadowSummary(tileDetails, "tile");
  assertTileLayoutSummary(tileLayout, "APKG dark tiles");

  await captureApkg(page, "ankiPreview", "light", artifactPaths.cardsScreenshot("apkg", "ankiPreview", "light"), deckName, deckFilterExpectation);
  const previewLightDetails = await inspectApkgAnkiPreview(page);
  assertBrowser(previewLightDetails.previewCount >= Math.min(3, apkgCards.length), `APKG light Anki answer previews found: ${previewLightDetails.previewCount}`);
  assertBrowser(previewLightDetails.frontHostCount === 0, "APKG light Anki preview has no separate front preview host.");
  assertBrowser(previewLightDetails.unmeasuredHostCount === 0, "APKG light Anki preview answer hosts completed adaptive measurement.");
  assertBrowser(previewLightDetails.clippedHostCount === 0, "APKG light Anki preview answer hosts are not clipped at the bottom.");
  assertBrowser(!previewLightDetails.hasRawSoundMarker, "APKG light Anki preview has no raw sound marker.");
  assertBrowser(!previewLightDetails.hasRawAnkiPlayMarker, "APKG light Anki preview has no raw Anki AV marker.");
  assertBrowser(!previewLightDetails.hasScriptTag, "APKG light Anki preview has no script tag.");
  assertBrowser(!previewLightDetails.hasExternalCdnLink, "APKG light Anki preview has no external CDN link.");

  await captureApkg(page, "ankiPreview", "dark", artifactPaths.cardsScreenshot("apkg", "ankiPreview", "dark"), deckName, deckFilterExpectation);
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
  const responsiveLayouts = await inspectApkgResponsiveLayouts(page, deckName, deckFilterExpectation);
  const performance100 = await inspectCardsPerformance100IfEnabled(page, report, importSummary, problemSummary, deckName, deckFilterExpectation);

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

  await prepareDashboardRoute(page, "/cards", "light", "Карточки, требующие внимания");
  await waitForCardsPageReady(page);
  diagnostics.cardsLight = await inspectDashboardCss(page, "cards-light");
  assertDashboardCss(diagnostics.cardsLight, { theme: "light", page: "Cards" });

  await prepareDashboardRoute(page, "/settings/server", "light", "Сервер");
  diagnostics.settingsLight = await inspectDashboardCss(page, "settings-light");
  assertDashboardCss(diagnostics.settingsLight, { theme: "light", page: "Settings" });

  await prepareDashboardRoute(page, "/settings/server", "dark", "Сервер");
  diagnostics.settingsDark = await inspectDashboardCss(page, "settings-dark");
  assertDashboardCss(diagnostics.settingsDark, { theme: "dark", page: "Settings" });

  await prepareDashboardRoute(page, "/cards", "light", "Карточки, требующие внимания");
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

async function assertCardsV2Workspace(page, perf100Enabled) {
  const inspectRequests = [];
  const onInspectRequest = (request) => {
    if (request.url().includes("/api/search/inspect")) {
      let cardId = "";
      try { cardId = JSON.parse(request.postData() || "{}").cardId || ""; } catch {}
      inspectRequests.push(cardId);
    }
  };
  page.on("request", onInspectRequest);
  try {
    await page.setViewportSize({ width: 1440, height: 1000 });
    const beforeInitial = inspectRequests.length;
    await prepareCardsPage(page, "workspace", "light");
    await page.locator('[data-testid="anki-card-shadow-preview"]').waitFor({ state: "visible", timeout: 60000 });
    await page.waitForFunction(() => document.querySelector('[data-testid="anki-card-shadow-preview"]')?.getAttribute("data-preview-measured") === "true", undefined, { timeout: 60000 });
    const initial = await inspectCardsV2Layout(page);
    assertBrowser(initial.inboxCount === 1, "Cards attention inbox renders one semantic list.");
    assertBrowser(initial.itemCount > 0 && initial.listItemCount === initial.itemCount, "Cards attention inbox renders one list item per actionable card.");
    assertBrowser(initial.invalidItemButtonCount === 0, "Each Cards attention item exposes exactly one native button.");
    assertBrowser(initial.tableCount === 0 && initial.gridRoleCount === 0 && initial.listboxRoleCount === 0, "Cards attention inbox does not regress to table, grid, or listbox semantics.");
    assertBrowser(initial.previewHostCount === 1, "Cards attention inbox renders one active-card preview only.");
    assertBrowser(initial.inspectorCount === 1 && initial.drawerCount === 0, "Wide Cards workspace renders one persistent Inspector and no drawer.");
    assertBrowser(initial.activeItemCount === 1, "Wide Cards workspace exposes exactly one current inbox item.");
    assertBrowser(initial.legacyModeControlCount === 0, "Cards attention inbox removes legacy table, tiles, and Anki-preview modes.");
    assertBrowser(initial.checkboxCount === 0, "Cards attention inbox does not render a dead bulk checkbox.");
    assertBrowser(initial.riskScoreTextCount === 0, "Cards attention inbox does not expose legacy numeric risk scores.");
    assertBrowser(inspectRequests.length - beforeInitial === 1, "Cards attention inbox requests Search inspect only for the initial active card.");
    if (perf100Enabled) assertBrowser(initial.itemCount === 100, `Cards bounded performance queue renders 100 items: ${initial.itemCount}`);

    const lightPath = artifactPaths.cardsScreenshot("synthetic", "workspace", "light");
    await ensureArtifactParent(lightPath);
    await page.screenshot({ path: lightPath, fullPage: true });
    const visualStates = [{ mode: "workspace", theme: "light", screenshot: relativeArtifactPath(artifactPaths, lightPath), details: initial }];

    if (initial.itemCount > 1) {
      const second = page.locator('[data-testid="cards-inbox-item"]').nth(1);
      const beforeSecond = inspectRequests.length;
      await second.focus();
      await Promise.all([
        page.waitForResponse((response) => response.url().includes("/api/search/inspect") && response.request().method() === "POST", { timeout: 60000 }),
        second.press("Enter"),
      ]);
      await page.waitForFunction(() => document.querySelectorAll('[data-testid="cards-inbox-item"][aria-current="true"]').length === 1, undefined, { timeout: 15000 });
      await page.waitForFunction(() => document.querySelector('[data-testid="anki-card-shadow-preview"]')?.getAttribute("data-preview-measured") === "true", undefined, { timeout: 60000 });
      assertBrowser(inspectRequests.length - beforeSecond === 1, "Keyboard inbox activation requests exactly one new active-card inspect.");
    }

    const expand = page.getByRole("button", { name: "Развернуть ответ", exact: true });
    await expand.click();
    await page.locator('[data-testid="cards-preview-modal"]').waitFor({ state: "visible", timeout: 15000 });
    await page.locator('[data-testid="cards-preview-modal"] [data-testid="anki-card-shadow-preview"][data-preview-side="back"]').waitFor({ state: "visible", timeout: 15000 });
    const modalState = await page.evaluate(() => {
      const shell = document.getElementById("dashboard-app-shell");
      const modal = document.querySelector('[data-testid="cards-preview-modal"]');
      return {
        shellInert: Boolean(shell?.inert),
        shellAriaHidden: shell?.getAttribute("aria-hidden") === "true",
        modalOutsideShell: Boolean(modal && shell && !shell.contains(modal)),
        dialogCount: document.querySelectorAll('[role="dialog"]').length,
        backPreviewCount: modal?.querySelectorAll('[data-testid="anki-card-shadow-preview"][data-preview-side="back"]').length || 0,
      };
    });
    assertBrowser((modalState.shellInert || modalState.shellAriaHidden) && modalState.modalOutsideShell && modalState.dialogCount === 1 && modalState.backPreviewCount === 1, "Expanded answer is one true modal outside the inert app shell.");
    const expandedPath = artifactPaths.cardsScreenshot("synthetic", "expanded", "light");
    await ensureArtifactParent(expandedPath);
    await page.screenshot({ path: expandedPath, fullPage: true });
    visualStates.push({ mode: "expanded", theme: "light", screenshot: relativeArtifactPath(artifactPaths, expandedPath), details: modalState });
    await page.keyboard.press("Escape");
    await page.locator('[data-testid="cards-preview-modal"]').waitFor({ state: "hidden", timeout: 15000 });

    const open = page.getByRole("button", { name: "Открыть в Anki", exact: true });
    await open.focus();
    await page.keyboard.press("Enter");
    await page.getByText("Запрос на открытие Anki Browser принят. Проблема остаётся активной.").waitFor({ state: "visible", timeout: 15000 });

    await prepareCardsPage(page, "workspace", "dark");
    await page.locator('[data-testid="anki-card-shadow-preview"]').waitFor({ state: "visible", timeout: 60000 });
    const darkPath = artifactPaths.cardsScreenshot("synthetic", "workspace", "dark");
    await ensureArtifactParent(darkPath);
    await page.screenshot({ path: darkPath, fullPage: true });
    const dark = await inspectCardsV2Layout(page);
    assertBrowser(dark.inspectorCount === 1 && dark.drawerCount === 0 && dark.previewHostCount === 1, "Dark wide Cards workspace preserves the attention inbox and Inspector contract.");
    visualStates.push({ mode: "workspace", theme: "dark", screenshot: relativeArtifactPath(artifactPaths, darkPath), details: dark });

    await page.setViewportSize({ width: 1024, height: 900 });
    await prepareCardsPage(page, "workspace-1024", "light");
    await page.waitForFunction(() => document.querySelectorAll('[data-testid="cards-inbox-item"][aria-current="true"]').length === 0 && !document.querySelector('[data-testid="cards-detail-drawer"]'), undefined, { timeout: 15000 });
    const narrowClosed = await inspectCardsV2Layout(page);
    assertBrowser(narrowClosed.documentOverflow <= 1, `Cards 1024 layout has no horizontal document overflow: ${narrowClosed.documentOverflow}`);
    assertBrowser(narrowClosed.itemCount > 0 && narrowClosed.queueWidthRatio >= 0.95, `Cards 1024 queue remains full width before activation: ${JSON.stringify(narrowClosed)}`);
    assertBrowser(narrowClosed.inspectorCount === 0 && narrowClosed.drawerCount === 0 && narrowClosed.previewHostCount === 0 && narrowClosed.activeItemCount === 0, "Cards 1024 starts with a full-width queue and no implicit detail surface.");

    const first = page.locator('[data-testid="cards-inbox-item"]').first();
    const firstCardId = await first.getAttribute("data-card-id");
    await first.focus();
    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/api/search/inspect") && response.request().method() === "POST", { timeout: 60000 }),
      first.press("Enter"),
    ]);
    await page.locator('[data-testid="cards-detail-drawer"]').waitFor({ state: "visible", timeout: 15000 });
    await page.waitForFunction(() => document.querySelector('[data-testid="cards-detail-drawer"] [data-testid="anki-card-shadow-preview"]')?.getAttribute("data-preview-measured") === "true", undefined, { timeout: 60000 });
    const narrowOpen = await inspectCardsV2Layout(page);
    assertBrowser(narrowOpen.drawerCount === 1 && narrowOpen.drawerRoleRegionCount === 1 && narrowOpen.drawerAriaModal === null, "Cards 1024 opens one non-modal detail region.");
    assertBrowser(!narrowOpen.shellInert && !narrowOpen.shellAriaHidden, "Cards 1024 drawer does not inert the dashboard shell.");
    assertBrowser(narrowOpen.inspectorCount === 0 && narrowOpen.previewHostCount === 1 && narrowOpen.activeItemCount === 1, "Cards 1024 drawer renders one active detail preview without a wide Inspector.");
    assertBrowser(narrowOpen.itemCount === narrowClosed.itemCount && narrowOpen.disabledItemCount === 0, "Cards 1024 queue remains operable while the drawer is open.");
    const narrowPath = artifactPaths.cardsScreenshot("synthetic", "workspace-1024", "light");
    await ensureArtifactParent(narrowPath);
    await page.screenshot({ path: narrowPath, fullPage: true });
    visualStates.push({ mode: "workspace-1024", theme: "light", screenshot: relativeArtifactPath(artifactPaths, narrowPath), details: narrowOpen });

    await page.getByRole("button", { name: "Развернуть ответ", exact: true }).click();
    await page.locator('[data-testid="cards-preview-modal"]').waitFor({ state: "visible", timeout: 15000 });
    assertBrowser(await page.locator('[data-testid="cards-detail-drawer"]').count() === 1, "Opening the answer modal preserves the underlying non-modal drawer.");
    await page.keyboard.press("Escape");
    await page.locator('[data-testid="cards-preview-modal"]').waitFor({ state: "hidden", timeout: 15000 });
    assertBrowser(await page.locator('[data-testid="cards-detail-drawer"]').count() === 1, "The first Escape closes only the answer modal.");
    await page.keyboard.press("Escape");
    await page.locator('[data-testid="cards-detail-drawer"]').waitFor({ state: "hidden", timeout: 15000 });
    await page.waitForFunction((cardId) => document.activeElement?.getAttribute("data-card-id") === cardId, firstCardId, { timeout: 15000 });

    const importSummary = await readJsonIfExists(path.join(artifactPaths.reports, "apkg-import-summary.json"));
    const apkg = { enabled: Boolean(importSummary.enabled), imported: Boolean(importSummary.imported), cardCount: Number(importSummary.cardCount || 0), activePreviewOnly: false };
    if (apkg.enabled) {
      assertBrowser(apkg.imported && apkg.cardCount > 0, "Cards APKG fixture was imported.");
      const apkgDeckName = (importSummary.deckNames || [])[0];
      assertBrowser(Boolean(apkgDeckName), "Cards APKG fixture exposes a deck name.");
      await page.setViewportSize({ width: baseViewport.width, height: baseViewport.height });
      await prepareCardsPage(page, "workspace", "light");
      await applyDeckFilter(page, apkgDeckName);
      await page.waitForFunction((deckName) => {
        const items = [...document.querySelectorAll('[data-testid="cards-inbox-item"]')];
        return items.length > 0 && items.every((item) => (item.textContent || "").includes(deckName));
      }, apkgDeckName, { timeout: 60000 });
      await page.locator('[data-testid="anki-card-shadow-preview"]').waitFor({ state: "visible", timeout: 60000 });
      await page.waitForFunction(() => document.querySelector('[data-testid="anki-card-shadow-preview"]')?.getAttribute("data-preview-measured") === "true", undefined, { timeout: 60000 });
      const apkgLayout = await inspectCardsV2Layout(page);
      assertBrowser(apkgLayout.previewHostCount === 1 && apkgLayout.activeItemCount === 1 && apkgLayout.inspectorCount === 1, "Cards APKG deck keeps one active preview in the wide Inspector.");
      apkg.activePreviewOnly = true;
      const apkgPath = artifactPaths.cardsScreenshot("apkg", "workspace", "light");
      await ensureArtifactParent(apkgPath);
      await page.screenshot({ path: apkgPath, fullPage: true });
      visualStates.push({ mode: "workspace", theme: "light", fixture: "apkg", deckName: apkgDeckName, screenshot: relativeArtifactPath(artifactPaths, apkgPath), details: apkgLayout });
    }

    await page.setViewportSize({ width: baseViewport.width, height: baseViewport.height });
    return { preview: { ...initial, activePreviewOnly: true, inspectRequestCount: inspectRequests.length }, apkg, visualStates };
  } finally {
    page.off("request", onInspectRequest);
  }
}

async function inspectCardsV2Layout(page) {
  return page.evaluate(() => {
    const pageRoot = document.querySelector('[data-testid="cards-inbox-page"]');
    const workspace = pageRoot?.querySelector(".cards-inbox-workspace")?.getBoundingClientRect();
    const queue = pageRoot?.querySelector(".cards-inbox-queue")?.getBoundingClientRect();
    const inspector = pageRoot?.querySelector(".cards-inbox-inspector")?.getBoundingClientRect();
    const drawer = document.querySelector('[data-testid="cards-detail-drawer"]');
    const shell = document.getElementById("dashboard-app-shell");
    const items = [...(pageRoot?.querySelectorAll('[data-testid="cards-inbox-item"]') || [])];
    const listItems = [...(pageRoot?.querySelectorAll('[data-testid="cards-inbox-list-item"]') || [])];
    const bodyText = pageRoot?.textContent || "";
    return {
      inboxCount: pageRoot?.querySelectorAll('[data-testid="cards-inbox"]').length || 0,
      itemCount: items.length,
      listItemCount: listItems.length,
      invalidItemButtonCount: listItems.filter((item) => item.querySelectorAll("button").length !== 1 || item.querySelectorAll(":scope > button").length !== 1).length,
      activeItemCount: pageRoot?.querySelectorAll('[data-testid="cards-inbox-item"][aria-current="true"]').length || 0,
      disabledItemCount: items.filter((item) => item.disabled).length,
      tableCount: pageRoot?.querySelectorAll("table").length || 0,
      gridRoleCount: pageRoot?.querySelectorAll('[role="grid"]').length || 0,
      listboxRoleCount: pageRoot?.querySelectorAll('[role="listbox"]').length || 0,
      inspectorCount: pageRoot?.querySelectorAll('[data-testid="cards-inspector"]').length || 0,
      drawerCount: drawer ? 1 : 0,
      drawerRoleRegionCount: drawer?.getAttribute("role") === "region" ? 1 : 0,
      drawerAriaModal: drawer?.getAttribute("aria-modal") ?? null,
      previewHostCount: document.querySelectorAll('[data-testid="anki-card-shadow-preview"]').length,
      checkboxCount: pageRoot?.querySelectorAll('input[type="checkbox"]').length || 0,
      legacyModeControlCount: [...(pageRoot?.querySelectorAll("button") || [])].filter((button) => ["Таблица", "Плитки", "Превью Anki"].includes((button.textContent || "").trim())).length,
      riskScoreTextCount: (bodyText.match(/Риск\s+\d+|risk\s+\d+/gi) || []).length,
      workspaceWidth: Math.round(workspace?.width || 0),
      queueWidth: Math.round(queue?.width || 0),
      queueWidthRatio: workspace?.width ? Number(((queue?.width || 0) / workspace.width).toFixed(3)) : 0,
      inspectorWidth: Math.round(inspector?.width || 0),
      documentOverflow: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
      pageHeight: document.documentElement.scrollHeight,
      shellInert: Boolean(shell?.inert),
      shellAriaHidden: shell?.getAttribute("aria-hidden") === "true",
    };
  });
}

async function captureApkg(page, mode, theme, filePath, deckName, deckFilterExpectation) {
  await prepareCardsPage(page, mode, theme);
  await applyApkgDeckFilter(page, deckName, deckFilterExpectation);
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
    ({ theme: selectedTheme }) => {
      window.localStorage.setItem("anki-study-report-theme", selectedTheme);
      document.documentElement.dataset.theme = selectedTheme;
    },
    { theme },
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

async function applyApkgDeckFilter(page, deckName, expectation) {
  assertBrowser(expectation.deckCardCount > 0, expectation.deckDiagnostic);
  assertBrowser(expectation.futureCards.length === 0, expectation.dateDiagnostic);
  assertBrowser(expectation.filteredCardCount > 0, expectation.filteredDiagnostic);
  await applyDeckFilter(page, deckName);
  const filterSummary = page.locator("p").filter({ hasText: /^Показано\s/ }).first();
  await filterSummary.waitFor({ state: "visible", timeout: 15000 });
  const summaryText = (await filterSummary.innerText()).replace(/\s+/g, " ").trim();
  assertBrowser(
    summaryText.startsWith(`Показано ${expectation.filteredCardCount} из `),
    `APKG deck filter count mismatch before preview wait: deck=${deckName}, expected=${expectation.filteredCardCount}, actual=${summaryText}`,
  );
}

async function waitForCardsPageReady(page) {
  await page.getByRole("heading", { name: "Карточки, требующие внимания", exact: true }).waitFor({ timeout: 60000 });
  await page.waitForFunction(
    () => !/Загружаем очередь внимания|Не удалось загрузить карточки|Карточки недоступны/.test(document.body.innerText),
    undefined,
    { timeout: 60000 },
  );
  await page.locator('[data-testid="cards-inbox-page"]').waitFor({ state: "visible", timeout: 60000 });
  await page.locator('[data-testid="cards-inbox"]').waitFor({ state: "visible", timeout: 60000 });
  await page.locator('[data-testid="cards-inbox-item"]').first().waitFor({ state: "visible", timeout: 60000 });
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

async function inspectApkgResponsiveLayouts(page, deckName, deckFilterExpectation) {
  const result = [];
  for (const viewport of responsiveViewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    await prepareCardsPage(page, "table", "dark");
    await applyApkgDeckFilter(page, deckName, deckFilterExpectation);
    await waitForApkgShadowPreviews(page, "table");
    await waitForLayoutStabilization(page);
    const table = await inspectTableLayout(page);
    assertTableLayoutSummary(table, `APKG ${viewport.name} table`);

    await prepareCardsPage(page, "tiles", "dark");
    await applyApkgDeckFilter(page, deckName, deckFilterExpectation);
    await waitForApkgShadowPreviews(page, "tile");
    await waitForLayoutStabilization(page);
    const tiles = await inspectTileLayout(page);
    assertTileLayoutSummary(tiles, `APKG ${viewport.name} tiles`);

    await prepareCardsPage(page, "ankiPreview", "dark");
    await applyApkgDeckFilter(page, deckName, deckFilterExpectation);
    await waitForApkgAnkiPreview(page);
    await waitForLayoutStabilization(page);
    const ankiPreview = await inspectApkgAnkiPreview(page);
    assertApkgAnkiPreviewSummary(ankiPreview, `APKG ${viewport.name} Anki preview`);

    result.push({ viewport, table, tiles, ankiPreview });
  }
  await page.setViewportSize({ width: baseViewport.width, height: baseViewport.height });
  return result;
}

async function inspectCardsPerformance100IfEnabled(page, report, importSummary, problemSummary, deckName, deckFilterExpectation) {
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
      await applyApkgDeckFilter(page, deckName, deckFilterExpectation);
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

async function assertSearchQueryContract() {
  const nativeQuery = 'deck:"E2E Fixtures"';
  const cardRequest = {
    mode: "cards",
    query: nativeQuery,
    filters: [],
    sort: { key: "entity_id", direction: "asc" },
    page: 1,
    pageSize: 25,
    requestId: "e2e-cards",
  };
  const noteRequest = { ...cardRequest, mode: "notes", requestId: "e2e-notes" };

  const invalidToken = await postSearchContract("/api/search/query", cardRequest, "invalid-token");
  assertBrowser(invalidToken.status === 403, "Search query rejects an invalid token.");

  const invalidQuery = await postSearchContract("/api/search/query", {
    ...cardRequest,
    query: 'deck:"unterminated',
    requestId: "e2e-invalid-query",
  });
  assertBrowser(invalidQuery.status === 400, "Malformed native query returns HTTP 400.");
  assertBrowser(invalidQuery.body?.error === "invalid_search_request", "Malformed native query returns a typed validation error.");

  const cards = await postSearchContract("/api/search/query", cardRequest);
  const notes = await postSearchContract("/api/search/query", noteRequest);
  assertBrowser(cards.status === 200 && cards.body?.ok === true, "Native Cards query succeeds with a valid token.");
  assertBrowser(notes.status === 200 && notes.body?.ok === true, "Native Notes query succeeds with a valid token.");
  const cardResult = cards.body.response;
  const noteResult = notes.body.response;
  assertBoundedSearchResult(cardResult, "cards");
  assertBoundedSearchResult(noteResult, "notes");
  assertBrowser(cardResult.items.length > 0, "Native Cards query returns the deterministic E2E fixture.");
  assertBrowser(noteResult.items.length > 0, "Native Notes query returns the deterministic E2E fixture.");

  const cardId = String(cardResult.items[0].cardId || "");
  const noteId = String(noteResult.items[0].noteId || "");
  const cardInspect = await postSearchContract("/api/search/inspect", {
    mode: "cards",
    cardId,
    requestId: "e2e-card-inspect",
  });
  const noteInspect = await postSearchContract("/api/search/inspect", {
    mode: "notes",
    noteId,
    requestId: "e2e-note-inspect",
  });
  assertBrowser(cardInspect.status === 200 && cardInspect.body?.response?.details?.cardId === cardId, "Card inspect returns the selected fixture card.");
  assertBrowser(noteInspect.status === 200 && noteInspect.body?.response?.details?.noteId === noteId, "Note inspect returns the selected fixture note.");
  assertCompleteCardDetails(cardInspect.body?.response?.details);
  assertCompleteNoteDetails(noteInspect.body?.response?.details);

  const structured = await postSearchContract("/api/search/query", {
    ...cardRequest,
    query: "",
    filters: [
      { type: "deck", deckId: String(cardInspect.body.response.details.deckId) },
      { type: "tag", tag: "e2e" },
    ],
    requestId: "e2e-structured",
  });
  assertBrowser(structured.status === 200 && structured.body?.response?.items?.length > 0, "Structured deck and tag filters return fixture cards.");

  const cardBrowser = await postSearchContract("/api/actions/open-search-selection", { mode: "cards", entityIds: [cardId] });
  const noteBrowser = await postSearchContract("/api/actions/open-search-selection", { mode: "notes", entityIds: [noteId] });
  assertBrowser(cardBrowser.status === 200 && cardBrowser.body?.resultCode === "search.browser_opened", "Selected card IDs open native Browser.");
  assertBrowser(noteBrowser.status === 200 && noteBrowser.body?.resultCode === "search.browser_opened", "Selected note IDs open native Browser.");

  const actionEvidence = await assertSafeEntityActions({
    cardId,
    noteId,
    cardBefore: cardInspect.body.response.details,
    noteBefore: noteInspect.body.response.details,
  });

  await assertSearchWorkspaceUi(nativeQuery);

  const emptyPage = await postSearchContract("/api/search/query", { ...cardRequest, page: 2, requestId: "e2e-empty-page" });
  assertBrowser(emptyPage.status === 200, "A page within pageLimit but beyond pageCount remains valid.");
  assertBrowser(emptyPage.body?.response?.items?.length === 0, "A page beyond pageCount is explicitly empty.");

  const cardsAfter = await postSearchContract("/api/search/query", cardRequest);
  const notesAfter = await postSearchContract("/api/search/query", noteRequest);
  const stableCards = JSON.stringify(cardsAfter.body?.response?.items?.map((item) => item.cardId)) === JSON.stringify(cardResult.items.map((item) => item.cardId));
  const stableNotes = JSON.stringify(notesAfter.body?.response?.items?.map((item) => item.noteId)) === JSON.stringify(noteResult.items.map((item) => item.noteId));
  assertBrowser(stableCards && stableNotes, "Read-only search and inspect calls leave the result set unchanged.");

  const artifact = {
    validTokenStatus: cards.status,
    invalidTokenStatus: invalidToken.status,
    invalidQuery: { status: invalidQuery.status, error: invalidQuery.body?.error || null },
    cards: summarizeSearchResult(cardResult, cardId),
    notes: summarizeSearchResult(noteResult, noteId),
    inspect: { cardStatus: cardInspect.status, noteStatus: noteInspect.status },
    collectionStable: stableCards && stableNotes,
    browserIntegration: { cards: cardBrowser.status === 200, notes: noteBrowser.status === 200 },
    structuredFilters: structured.status === 200,
    actions: actionEvidence,
    mutationEndpointsUsed: true,
    rawQueryExported: false,
    tokenExported: false,
  };
  const serialized = JSON.stringify(artifact);
  assertBrowser(!serialized.includes(nativeQuery) && !serialized.includes(ready.token), "Search contract artifact excludes the raw query and dashboard token.");
  await writeJson("search-query-contract.json", artifact);
  return artifact;
}

async function assertSafeEntityActions({ cardId, noteId, cardBefore, noteBefore }) {
  const fixture = JSON.parse(await fs.readFile(artifactPaths.report("fixture-summary.json"), "utf8"));
  const targetDeckId = Number(fixture.actionDeckIds?.target || 0);
  const filteredDeckId = Number(fixture.actionDeckIds?.filtered || 0);
  const sourceDeckId = Number(cardBefore.deckId || 0);
  assertBrowser(targetDeckId > 0 && filteredDeckId > 0 && sourceDeckId > 0 && targetDeckId !== sourceDeckId, "Action fixture decks are deterministic and distinct.");

  const invalidToken = await postSearchContract("/api/entities/cards/actions", {
    action: "suspend", cardIds: [cardId], requestId: "e2e-action-invalid-token",
  }, "invalid-token");
  assertBrowser(invalidToken.status === 403, "Mutation endpoint rejects an invalid token.");

  const action = async (entityType, payload, expectedCode) => {
    const result = await postSearchContract(`/api/entities/${entityType}/actions`, payload);
    assertBrowser(result.status === 200 && result.body?.ok === true, `${expectedCode} succeeds.`);
    assertBrowser(result.body?.response?.resultCode === expectedCode, `${expectedCode} returns its stable result code.`);
    assertBrowser(result.body?.response?.undoable === true, `${expectedCode} reports native undo support.`);
    return result.body.response;
  };
  const inspectCard = async (requestId) => (await postSearchContract("/api/search/inspect", { mode: "cards", cardId, requestId })).body?.response?.details;
  const inspectNote = async (requestId) => (await postSearchContract("/api/search/inspect", { mode: "notes", noteId, requestId })).body?.response?.details;

  const suspend = await action("cards", { action: "suspend", cardIds: [cardId], requestId: "e2e-suspend" }, "cards.suspended");
  assertBrowser((await inspectCard("e2e-suspended"))?.queue === -1, "Suspend refresh exposes the suspended queue.");
  await action("cards", { action: "unsuspend", cardIds: [cardId], requestId: "e2e-unsuspend" }, "cards.unsuspended");
  assertBrowser((await inspectCard("e2e-unsuspended"))?.queue === cardBefore.queue, "Unsuspend restores the fixture queue.");

  await action("cards", { action: "set_flag", cardIds: [cardId], flag: 3, requestId: "e2e-flag" }, "cards.flag_set");
  assertBrowser((await inspectCard("e2e-flagged"))?.flag === 3, "Set flag refresh exposes the native flag.");
  await action("cards", { action: "clear_flag", cardIds: [cardId], requestId: "e2e-clear-flag" }, "cards.flag_cleared");
  assertBrowser((await inspectCard("e2e-flag-cleared"))?.flag === cardBefore.flag, "Clear flag restores the fixture flag.");

  const actionTag = "asr-e2e-safe-action";
  await action("notes", { action: "add_tags", noteIds: [noteId], tags: [actionTag], requestId: "e2e-add-tag" }, "notes.tags_added");
  assertBrowser((await inspectNote("e2e-tag-added"))?.tags?.includes(actionTag), "Add tags refresh exposes the native note tag.");
  await action("notes", { action: "remove_tags", noteIds: [noteId], tags: [actionTag], requestId: "e2e-remove-tag" }, "notes.tags_removed");
  assertBrowser(!(await inspectNote("e2e-tag-removed"))?.tags?.includes(actionTag), "Remove tags restores the fixture tags.");

  await action("cards", { action: "bury", cardIds: [cardId], requestId: "e2e-bury" }, "cards.buried");
  assertBrowser([-2, -3].includes((await inspectCard("e2e-buried"))?.queue), "Bury refresh exposes a temporary buried queue.");
  await action("cards", { action: "unbury", cardIds: [cardId], requestId: "e2e-unbury" }, "cards.unburied");
  assertBrowser((await inspectCard("e2e-unburied"))?.queue === cardBefore.queue, "Unbury restores the fixture queue.");

  const filtered = await postSearchContract("/api/entities/cards/actions", {
    action: "move_to_deck", cardIds: [cardId], deckId: String(filteredDeckId), requestId: "e2e-filtered-destination",
  });
  assertBrowser(filtered.status === 400 && filtered.body?.error === "cards.destination_filtered", "Filtered destination is rejected with a typed error.");
  await action("cards", { action: "move_to_deck", cardIds: [cardId], deckId: String(targetDeckId), requestId: "e2e-move" }, "cards.moved");
  assertBrowser(Number((await inspectCard("e2e-moved"))?.deckId) === targetDeckId, "Move refresh exposes the destination deck.");
  const movedQuery = await postSearchContract("/api/search/query", {
    mode: "cards", query: "", filters: [{ type: "deck", deckId: String(targetDeckId) }],
    sort: { key: "entity_id", direction: "asc" }, page: 1, pageSize: 25, requestId: "e2e-moved-query",
  });
  assertBrowser(movedQuery.body?.response?.items?.some((item) => String(item.cardId) === cardId), "Deck-filtered query refresh finds the moved card.");
  await action("cards", { action: "move_to_deck", cardIds: [cardId], deckId: String(sourceDeckId), requestId: "e2e-move-restore" }, "cards.moved");

  const cardAfter = await inspectCard("e2e-card-restored");
  const noteAfter = await inspectNote("e2e-note-restored");
  const cardStable = cardAfter?.queue === cardBefore.queue && cardAfter?.flag === cardBefore.flag && Number(cardAfter?.deckId) === sourceDeckId;
  const noteStable = JSON.stringify(noteAfter?.tags || []) === JSON.stringify(noteBefore.tags || []);
  assertBrowser(cardStable && noteStable, "Safe action cycles restore the deterministic collection baseline.");
  return {
    invalidTokenStatus: invalidToken.status,
    changedBatches: 10,
    requestedPerBatch: suspend.requestedCount,
    filteredDestinationRejected: filtered.body?.error === "cards.destination_filtered",
    undoableEvidence: true,
    queryRefresh: true,
    inspectRefresh: true,
    collectionStable: cardStable && noteStable,
  };
}

async function assertSearchWorkspaceUi(nativeQuery) {
  await page.goto(`${ready.baseUrl}/?token=${encodeURIComponent(ready.token)}#/search`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Поиск", exact: true }).waitFor({ state: "visible", timeout: 30000 });
  const primaryHrefs = await page.locator('nav[aria-label] a').evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  assertBrowser(JSON.stringify(primaryHrefs.slice(0, 6)) === JSON.stringify(["#/home", "#/calendar", "#/stats", "#/decks", "#/search", "#/cards"]), "Primary navigation keeps Search between Decks and Cards.");
  const queryInput = page.locator(".search-query-field input");
  await queryInput.fill(nativeQuery);
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await page.locator(".search-table tbody tr").first().waitFor({ state: "visible", timeout: 30000 });
  const cardRows = await page.locator(".search-table tbody tr").count();
  assertBrowser(cardRows > 0, "Search workspace renders bounded Card rows.");
  await page.locator(".search-row-button").first().click();
  await page.locator(".search-inspector-content").waitFor({ state: "visible", timeout: 30000 });
  await page.locator('input[name="search-mode"][value="notes"]').check();
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await page.locator(".search-table tbody tr").first().waitFor({ state: "visible", timeout: 30000 });
  assertBrowser(await page.locator(".search-table thead").getByText("Карточки", { exact: true }).count() === 1, "Notes mode renders distinct columns.");
  assertBrowser(!page.url().includes(encodeURIComponent(nativeQuery)) && !page.url().includes(nativeQuery), "Raw native query stays out of the URL.");
  assertBrowser(!String(await page.title()).includes(nativeQuery), "Raw native query stays out of the page title.");
}

async function postSearchContract(endpoint, payload, token = ready.token) {
  const response = await fetch(`${ready.baseUrl}${endpoint}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { status: response.status, body };
}

function assertBoundedSearchResult(result, mode) {
  assertBrowser(result?.mode === mode, `Search response preserves ${mode} discrimination.`);
  assertBrowser(Array.isArray(result?.items), `${mode} search response contains items.`);
  assertBrowser(result.page === 1 && result.pageSize === 25, `${mode} search response preserves paging.`);
  assertBrowser(result.items.length <= result.pageSize, `${mode} search page is bounded.`);
  assertBrowser(result.boundedTotal <= 2000, `${mode} search total respects the hard cap.`);
  assertBrowser(result.pageCount === Math.ceil(result.boundedTotal / result.pageSize), `${mode} search pageCount reflects bounded results.`);
  assertBrowser(result.pageLimit === Math.ceil(2000 / result.pageSize), `${mode} search pageLimit reflects the hard cap.`);
  assertBrowser(!Object.hasOwn(result, "maxPage"), `${mode} search omits the retired maxPage field.`);
  assertBrowser(typeof result.hasNext === "boolean" && typeof result.truncated === "boolean", `${mode} search exposes bounded result metadata.`);
}

function assertCompleteCardDetails(details) {
  const required = ["cardId", "noteId", "deckId", "deckName", "noteTypeId", "noteTypeName", "templateOrdinal", "templateName", "primaryText", "state", "due", "interval", "repetitions", "lapses", "flag", "tagSummary", "deck", "noteType", "template", "queue", "tags", "renderedPreview"];
  assertBrowser(required.every((key) => Object.hasOwn(details || {}, key)), "Card inspect returns every declared detail field.");
  assertBrowser(details?.deck?.deckId === details?.deckId && details?.noteType?.noteTypeId === details?.noteTypeId, "Card inspect nested identities match the row projection.");
  assertBrowser(["available", "sanitized", "unavailable", "fallback", "error"].includes(details?.renderedPreview?.renderStatus), "Card inspect returns a bounded safe preview status.");
}

function assertCompleteNoteDetails(details) {
  const required = ["noteId", "noteTypeId", "noteTypeName", "primaryText", "tagSummary", "cardCount", "deckSummary", "noteType", "fields", "tags", "cardReferences", "cardsTruncated", "fieldsTruncated", "deckSummaries"];
  assertBrowser(required.every((key) => Object.hasOwn(details || {}, key)), "Note inspect returns every declared detail field.");
  assertBrowser(Array.isArray(details?.fields) && Array.isArray(details?.cardReferences) && Array.isArray(details?.deckSummaries), "Note inspect nested collections are complete.");
}

function summarizeSearchResult(result, selectedId) {
  return {
    mode: result.mode,
    page: result.page,
    pageSize: result.pageSize,
    pageCount: result.pageCount,
    pageLimit: result.pageLimit,
    returnedCount: result.returnedCount,
    boundedTotal: result.boundedTotal,
    hasNext: result.hasNext,
    truncated: result.truncated,
    selectedId,
  };
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

function buildApkgDeckFilterExpectation(report, importSummary, deckName) {
  const todayDate = String(report?.metadata?.todayDate || "");
  const deckCards = findApkgCards(report, importSummary).filter(
    (card) => String(card?.deckName || card?.deck_name || "") === deckName,
  );
  const todayMs = Date.parse(`${todayDate}T00:00:00Z`);
  const periodStartMs = todayMs - 6 * 24 * 60 * 60 * 1000;
  const datedCards = deckCards.map((card) => ({
    cardId: Number(card?.cardId || card?.card_id || 0),
    lastReviewedAt: String(card?.lastReviewedAt || card?.last_reviewed_at || ""),
  }));
  const parsedCards = datedCards.map((card) => ({
    ...card,
    reviewedMs: Date.parse(`${card.lastReviewedAt}T00:00:00Z`),
  }));
  const futureCards = parsedCards.filter((card) => Number.isFinite(card.reviewedMs) && card.reviewedMs > todayMs);
  const filteredCardCount = parsedCards.filter(
    (card) => Number.isFinite(card.reviewedMs) && card.reviewedMs >= periodStartMs && card.reviewedMs <= todayMs,
  ).length;
  const dateDetails = datedCards.map((card) => `${card.cardId}:${card.lastReviewedAt || "missing"}`).join(", ");
  return {
    deckCardCount: deckCards.length,
    filteredCardCount,
    futureCards,
    deckDiagnostic: `APKG selected deck has no report cards before preview wait: deck=${deckName}`,
    dateDiagnostic: `APKG current-day fixture is after report metadata.todayDate before preview wait: deck=${deckName}, todayDate=${todayDate || "missing"}, cards=[${dateDetails}]`,
    filteredDiagnostic: `APKG selected deck has zero cards in the 7-day UI period before preview wait: deck=${deckName}, todayDate=${todayDate || "missing"}, cards=[${dateDetails}]`,
  };
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

function actionableNetworkEvents() {
  return networkEvents.filter((event) => {
    if (event.kind !== "requestfailed") return true;
    return !String(event.failure || "").includes("ERR_ABORTED");
  });
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
