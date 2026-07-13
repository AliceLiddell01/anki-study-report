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
const reportsDir = process.env.ANKI_STUDY_REPORT_E2E_REPORTS_DIR || path.join(artifacts, "reports");
const readyFile = process.env.ANKI_STUDY_REPORT_E2E_READY_FILE || path.join(artifacts, "runtime", "dashboard-ready.json");
const ready = JSON.parse(await fs.readFile(readyFile, "utf8"));
const token = encodeURIComponent(ready.token);

const routes = [
  ["/stats", "Статистика", false],
  ["/stats/quality", "Качество", false],
  ["/stats/load", "Нагрузка", false],
  ["/stats/progress", "Прогресс", false],
  ["/stats/decks", "Колоды", false],
  ["/stats/fsrs", "FSRS", true],
  ["/stats/fsrs/memory", "Состояние памяти", true],
  ["/stats/fsrs/calibration", "Точность модели", true],
  ["/stats/fsrs/steps", "Шаги обучения", true],
  ["/stats/fsrs/simulator", "Симулятор", true],
];

const desktopProfiles = [
  { name: "width-1265-zoom-100", width: 1265, height: 900, deviceScaleFactor: 1 },
  { name: "width-989-zoom-100", width: 989, height: 900, deviceScaleFactor: 1 },
  { name: "width-1265-zoom-125", width: 1265, height: 900, deviceScaleFactor: 1.25 },
  { name: "width-989-zoom-125", width: 989, height: 900, deviceScaleFactor: 1.25 },
];

const browser = await chromium.launch({ headless: true });
const results = [];
const consoleErrors = [];
const pageErrors = [];
const requestFailures = [];

try {
  for (const profile of desktopProfiles) {
    const context = await browser.newContext({
      viewport: { width: profile.width, height: profile.height },
      deviceScaleFactor: profile.deviceScaleFactor,
    });
    const page = await context.newPage();
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push({ profile: profile.name, text: message.text(), location: message.location() });
    });
    page.on("pageerror", (error) => pageErrors.push({ profile: profile.name, error: String(error?.stack || error?.message || error) }));
    page.on("requestfailed", (request) => {
      const failure = request.failure()?.errorText || "unknown";
      if (!/ERR_ABORTED/i.test(failure)) {
        requestFailures.push({ profile: profile.name, method: request.method(), url: request.url(), failure });
      }
    });

    for (const theme of ["light", "dark"]) {
      let themeStored = false;
      for (const [route, heading, fsrsRoute] of routes) {
        const url = `${ready.baseUrl}/?token=${token}#${route}`;
        await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
        if (!themeStored) {
          await page.evaluate((selectedTheme) => {
            localStorage.setItem("anki-study-report-theme", selectedTheme);
            document.documentElement.dataset.theme = selectedTheme;
            document.documentElement.style.colorScheme = selectedTheme;
          }, theme);
          await page.reload({ waitUntil: "networkidle", timeout: 60000 });
          themeStored = true;
        }
        await page.getByRole("heading", { name: heading, exact: true }).waitFor({ state: "visible", timeout: 60000 });
        await page.getByTestId("statistics-sidebar").waitFor({ state: "visible", timeout: 15000 });
        await page.evaluate(async () => {
          await document.fonts?.ready?.catch(() => undefined);
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        });

        const geometry = await page.evaluate(({ expectFsrs }) => {
          const sidebar = document.querySelector('[data-testid="statistics-sidebar"]');
          const headingElement = sidebar?.querySelector(".statistics-sidebar-heading");
          const icon = sidebar?.querySelector(".statistics-sidebar-icon");
          const hero = document.querySelector(".statistics-header");
          if (!sidebar || !headingElement || !icon || !hero) return null;
          const toRect = (element) => {
            const rect = element.getBoundingClientRect();
            return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
          };
          const sidebarStyle = getComputedStyle(sidebar);
          const heroStyle = getComputedStyle(hero);
          const pseudo = expectFsrs ? getComputedStyle(hero, "::after") : null;
          return {
            viewport: { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight, devicePixelRatio: window.devicePixelRatio },
            sidebar: toRect(sidebar),
            heading: toRect(headingElement),
            icon: toRect(icon),
            sidebarOverflow: sidebarStyle.overflow,
            sidebarBorderRadius: Number.parseFloat(sidebarStyle.borderTopLeftRadius),
            heroBorderWidth: Number.parseFloat(heroStyle.borderTopWidth),
            heroBackgroundImage: heroStyle.backgroundImage,
            fsrsPseudo: pseudo ? {
              content: pseudo.content,
              display: pseudo.display,
              backgroundImage: pseudo.backgroundImage,
              backgroundColor: pseudo.backgroundColor,
              borderRadius: pseudo.borderRadius,
              filter: pseudo.filter,
            } : null,
          };
        }, { expectFsrs: fsrsRoute });

        assert(geometry, `${profile.name} ${theme} ${route}: Statistics geometry nodes are present.`);
        const tolerance = 0.75;
        const safeInset = 4;
        assert(geometry.icon.left >= geometry.sidebar.left + safeInset - tolerance, `${profile.name} ${theme} ${route}: sidebar icon left edge stays inside the rounded card.`);
        assert(geometry.icon.top >= geometry.sidebar.top + safeInset - tolerance, `${profile.name} ${theme} ${route}: sidebar icon top edge stays inside the rounded card.`);
        assert(geometry.icon.right <= geometry.sidebar.right - safeInset + tolerance, `${profile.name} ${theme} ${route}: sidebar icon right edge stays inside the rounded card.`);
        assert(geometry.icon.bottom <= geometry.sidebar.bottom - safeInset + tolerance, `${profile.name} ${theme} ${route}: sidebar icon bottom edge stays inside the rounded card.`);
        assert(geometry.heading.left >= geometry.sidebar.left - tolerance && geometry.heading.right <= geometry.sidebar.right + tolerance, `${profile.name} ${theme} ${route}: sidebar heading remains horizontally contained.`);
        assert(geometry.sidebarBorderRadius >= 8, `${profile.name} ${theme} ${route}: sidebar retains a rounded container.`);
        assert(geometry.sidebarOverflow !== "hidden" && geometry.sidebarOverflow !== "clip", `${profile.name} ${theme} ${route}: sidebar does not clip focus outlines.`);
        assert(geometry.heroBorderWidth >= 1 && geometry.heroBackgroundImage !== "none", `${profile.name} ${theme} ${route}: shared Statistics header surface remains intact.`);

        if (fsrsRoute) {
          const pseudo = geometry.fsrsPseudo;
          assert(pseudo && (pseudo.content === "none" || pseudo.display === "none"), `${profile.name} ${theme} ${route}: FSRS-only decorative pseudo-element is disabled.`);
          assert(!/radial-gradient/i.test(pseudo.backgroundImage), `${profile.name} ${theme} ${route}: FSRS header has no radial decorative spot.`);
        }

        results.push({ profile, theme, route, heading, fsrsRoute, geometry });
      }
    }
    await context.close();
  }

  assert(consoleErrors.length === 0, `Geometry pass has browser console errors: ${JSON.stringify(consoleErrors)}`);
  assert(pageErrors.length === 0, `Geometry pass has page errors: ${JSON.stringify(pageErrors)}`);
  assert(requestFailures.length === 0, `Geometry pass has request failures: ${JSON.stringify(requestFailures)}`);

  await fs.mkdir(reportsDir, { recursive: true });
  await fs.writeFile(path.join(reportsDir, `fsrs-visual-contract-${label}.json`), JSON.stringify({
    ok: true,
    schemaVersion: 1,
    profiles: desktopProfiles,
    routes: routes.map(([route, heading, fsrsRoute]) => ({ route, heading, fsrsRoute })),
    checks: results,
    consoleErrors,
    pageErrors,
    requestFailures,
  }, null, 2), "utf8");
  console.log(`FSRS visual contract passed: ${results.length} route/theme/profile combinations.`);
} catch (error) {
  await fs.mkdir(reportsDir, { recursive: true });
  await fs.writeFile(path.join(reportsDir, `fsrs-visual-contract-${label}.json`), JSON.stringify({
    ok: false,
    schemaVersion: 1,
    error: String(error?.stack || error?.message || error),
    checks: results,
    consoleErrors,
    pageErrors,
    requestFailures,
  }, null, 2), "utf8");
  throw error;
} finally {
  await browser.close();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
