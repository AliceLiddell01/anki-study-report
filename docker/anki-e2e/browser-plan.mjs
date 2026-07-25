export const BROWSER_PLAN_SCHEMA_VERSION = 1;
export const BROWSER_REPORT_SCHEMA_VERSION = 3;
export const THEMES = Object.freeze(["light", "dark"]);
export const ROUTE_CASES = Object.freeze([
  Object.freeze({ name: "home", route: "/home" }),
  Object.freeze({ name: "cards", route: "/cards" }),
  Object.freeze({ name: "decks", route: "/decks" }),
  Object.freeze({ name: "profile", route: "/profile" }),
  Object.freeze({ name: "settings", route: "/settings" }),
]);
export const PREVIEW_ANCHOR_IDS = Object.freeze(["words-preview", "grammar-preview", "java-preview"]);
export const KNOWN_ITEM_KINDS = Object.freeze([
  "browser-launch",
  "dashboard-setup",
  "route-capture",
  "telemetry",
  "native-preview",
  "scenario-cards",
  "cards-route",
  "diagnostics",
]);

const ITEM_ID_RE = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/;

export function buildBrowserPlan({ label, mode, scope, telemetryEnabled }) {
  const items = [];
  const add = (item) => items.push(Object.freeze({ ...item, order: items.length + 1 }));
  add({ id: "browser.launch", kind: "browser-launch", label: "launch Chromium", expectedScreenshots: 0 });
  add({ id: "dashboard.setup", kind: "dashboard-setup", label: "create dashboard page", expectedScreenshots: 0 });
  for (const { name, route } of ROUTE_CASES) {
    for (const theme of THEMES) {
      add({
        id: `route.${name}.${theme}`,
        kind: "route-capture",
        label: `route=#${route} theme=${theme}`,
        route: `#${route}`,
        theme,
        expectedScreenshots: 1,
      });
    }
  }
  if (telemetryEnabled) {
    add({ id: "telemetry.declined", kind: "telemetry", label: "declined baseline", step: "declined", expectedScreenshots: 0 });
    add({ id: "telemetry.reliability", kind: "telemetry", label: "reliability-only delivery", step: "reliability", expectedScreenshots: 0 });
    add({ id: "telemetry.feature", kind: "telemetry", label: "feature-only delivery", step: "feature", expectedScreenshots: 0 });
    add({ id: "telemetry.offline", kind: "telemetry", label: "offline queue proof", step: "offline", expectedScreenshots: 0 });
  }
  for (const anchorId of PREVIEW_ANCHOR_IDS) {
    add({
      id: `preview.${anchorId}`,
      kind: "native-preview",
      label: `anchor=${anchorId}`,
      anchorId,
      expectedScreenshots: 2,
    });
  }
  add({ id: "scenario.cards", kind: "scenario-cards", label: "scenario card checks", expectedScreenshots: 0 });
  for (const theme of THEMES) {
    add({
      id: `cards-route.${theme}`,
      kind: "cards-route",
      label: `route=#/cards theme=${theme}`,
      route: "#/cards",
      theme,
      expectedScreenshots: 1,
    });
  }
  add({ id: "diagnostics.final", kind: "diagnostics", label: "final browser diagnostics", expectedScreenshots: 0 });
  const countsByKind = {};
  for (const item of items) countsByKind[item.kind] = (countsByKind[item.kind] || 0) + 1;
  const expectedScreenshotCount = items.reduce((total, item) => total + item.expectedScreenshots, 0);
  const plan = Object.freeze({
    schemaVersion: BROWSER_PLAN_SCHEMA_VERSION,
    label: safeIdentifier(label, "label"),
    mode: safeIdentifier(mode, "mode"),
    scope: safeIdentifier(scope, "scope"),
    telemetryEnabled: Boolean(telemetryEnabled),
    expectedScreenshotCount,
    itemCount: items.length,
    countsByKind: Object.freeze(countsByKind),
    items: Object.freeze(items),
  });
  validateBrowserPlan(plan);
  return plan;
}

export function validateBrowserPlan(plan) {
  if (!plan || plan.schemaVersion !== BROWSER_PLAN_SCHEMA_VERSION) throw new Error("Browser plan schemaVersion must be 1");
  if (!Array.isArray(plan.items) || plan.items.length === 0) throw new Error("Browser plan items must be a non-empty array");
  if (plan.itemCount !== plan.items.length) throw new Error("Browser plan itemCount differs from items length");
  const knownKinds = new Set(KNOWN_ITEM_KINDS);
  const ids = new Set();
  const counts = {};
  let screenshotTotal = 0;
  for (const [index, item] of plan.items.entries()) {
    if (!ITEM_ID_RE.test(item.id)) throw new Error(`Invalid browser item id: ${item.id}`);
    if (ids.has(item.id)) throw new Error(`Duplicate browser item id: ${item.id}`);
    ids.add(item.id);
    if (!knownKinds.has(item.kind)) throw new Error(`Unknown browser item kind: ${item.kind}`);
    if (item.order !== index + 1) throw new Error(`Browser item order mismatch: ${item.id}`);
    if (!Number.isInteger(item.expectedScreenshots) || item.expectedScreenshots < 0) {
      throw new Error(`Invalid expectedScreenshots for ${item.id}`);
    }
    screenshotTotal += item.expectedScreenshots;
    counts[item.kind] = (counts[item.kind] || 0) + 1;
    validatePublicItemFields(item);
  }
  if (screenshotTotal !== plan.expectedScreenshotCount) throw new Error("Browser plan screenshot total mismatch");
  if (JSON.stringify(counts) !== JSON.stringify(plan.countsByKind)) throw new Error("Browser plan countsByKind mismatch");
  return plan;
}

export function safeIdentifier(value, label) {
  const normalized = String(value || "").trim();
  if (!/^[A-Za-z0-9_.-]+$/.test(normalized)) throw new Error(`${label} contains unsafe characters`);
  return normalized;
}

function validatePublicItemFields(item) {
  for (const [key, value] of Object.entries(item)) {
    if (typeof value !== "string") continue;
    if (/[\r\n\0]/.test(value) || /[?&](?:access_)?token=/i.test(value)) throw new Error(`Unsafe browser item field: ${key}`);
    if (/(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s'"(])\/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:\/|$))/i.test(value)) {
      throw new Error(`Private path in browser item field: ${key}`);
    }
  }
}
