import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

export const BROWSER_PLAN_SCHEMA_VERSION = 1;
export const BROWSER_REPORT_SCHEMA_VERSION = 2;
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
const SAFE_ERROR_MAX = 240;
const SLOWEST_ITEM_COUNT = 5;

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

export class BrowserProgress {
  constructor({ plan, screenshots, emitRunEvent, persist, log = console.log, now = () => performance.now() }) {
    validateBrowserPlan(plan);
    if (!Array.isArray(screenshots)) throw new Error("screenshots must be an array");
    this.plan = plan;
    this.screenshots = screenshots;
    this.emitRunEvent = emitRunEvent;
    this.persist = persist;
    this.log = log;
    this.now = now;
    this.items = [];
    this.itemById = new Map(plan.items.map((item) => [item.id, item]));
    this.completedIds = new Set();
    this.activeItemId = null;
    this.failedItemId = null;
  }

  printPlan() {
    this.log(`[BROWSER] PLAN items=${this.plan.itemCount} screenshots=${this.plan.expectedScreenshotCount} telemetry=${this.plan.telemetryEnabled}`);
  }

  async run(itemId, operation) {
    const item = this.itemById.get(itemId);
    if (!item) throw new Error(`Unknown or unplanned browser item: ${itemId}`);
    if (this.activeItemId) throw new Error(`Browser item is already active: ${this.activeItemId}`);
    if (this.completedIds.has(itemId)) throw new Error(`Browser item already completed: ${itemId}`);
    if (typeof operation !== "function") throw new Error(`Browser item operation must be callable: ${itemId}`);

    const current = item.order;
    const total = this.plan.itemCount;
    const screenshotStart = this.screenshots.length;
    const started = this.now();
    this.activeItemId = itemId;
    this.log(`[BROWSER] [${current}/${total}] START ${item.kind} item=${item.id}${formatItemContext(item)}`);

    try {
      await this.#emit(current, total, `item=start id=${item.id} kind=${item.kind}`);
      await this.#persist();
      const value = await operation();
      const durationMs = nonNegativeDuration(this.now() - started);
      const actualScreenshots = this.screenshots.length - screenshotStart;
      if (actualScreenshots !== item.expectedScreenshots) {
        throw new Error(`Screenshot contribution mismatch for ${item.id}: expected ${item.expectedScreenshots}, actual ${actualScreenshots}`);
      }
      await this.#emit(current, total, `item=pass id=${item.id} kind=${item.kind} durationMs=${durationMs} screenshots=${actualScreenshots}`);
      this.#record(item, "pass", durationMs, screenshotStart, actualScreenshots, null);
      this.log(`[BROWSER] [${current}/${total}] PASS ${item.kind} item=${item.id} duration=${durationMs}ms screenshots=${actualScreenshots}`);
      await this.#persist();
      return value;
    } catch (error) {
      const durationMs = nonNegativeDuration(this.now() - started);
      const actualScreenshots = this.screenshots.length - screenshotStart;
      this.failedItemId = item.id;
      if (!this.completedIds.has(item.id)) {
        this.#record(item, "fail", durationMs, screenshotStart, actualScreenshots, {
          errorType: safeErrorType(error),
          safeErrorSummary: safeErrorSummary(error),
        });
      } else {
        const record = this.items.find((candidate) => candidate.id === item.id);
        if (record) {
          record.status = "fail";
          record.errorType = safeErrorType(error);
          record.safeErrorSummary = safeErrorSummary(error);
        }
      }
      this.log(`[BROWSER] [${current}/${total}] FAIL ${item.kind} item=${item.id} duration=${durationMs}ms screenshots=${actualScreenshots} errorType=${safeErrorType(error)}`);
      try {
        await this.#emit(current, total, `item=fail id=${item.id} kind=${item.kind} durationMs=${durationMs} errorType=${safeErrorType(error)}`);
      } catch (secondary) {
        this.log(`[BROWSER] [${current}/${total}] INFO ${item.kind} item=${item.id} secondary=run-event-producer`);
      }
      try {
        await this.#persist();
      } catch (secondary) {
        this.log(`[BROWSER] [${current}/${total}] INFO ${item.kind} item=${item.id} secondary=progress-persist`);
      }
      throw error;
    } finally {
      this.activeItemId = null;
    }
  }

  async milestone(itemId, marker) {
    const item = this.itemById.get(itemId);
    if (!item || this.activeItemId !== itemId) throw new Error(`Milestone requires the active planned item: ${itemId}`);
    const safeMarker = safeIdentifier(marker, "milestone");
    this.log(`[BROWSER] [${item.order}/${this.plan.itemCount}] INFO ${item.kind} item=${item.id} milestone=${safeMarker}`);
    await this.#emit(item.order, this.plan.itemCount, `item=info id=${item.id} milestone=${safeMarker}`);
  }

  finalize() {
    if (this.activeItemId) throw new Error(`Browser item remains active: ${this.activeItemId}`);
    if (this.failedItemId) throw new Error(`Browser progress contains failed item: ${this.failedItemId}`);
    if (this.completedIds.size !== this.plan.itemCount) {
      throw new Error(`Browser progress incomplete: ${this.completedIds.size}/${this.plan.itemCount}`);
    }
    if (this.screenshots.length !== this.plan.expectedScreenshotCount) {
      throw new Error(`Browser screenshot total mismatch: expected ${this.plan.expectedScreenshotCount}, actual ${this.screenshots.length}`);
    }
    return this.snapshot();
  }

  snapshot() {
    return {
      plan: {
        schemaVersion: this.plan.schemaVersion,
        label: this.plan.label,
        mode: this.plan.mode,
        scope: this.plan.scope,
        telemetryEnabled: this.plan.telemetryEnabled,
        itemCount: this.plan.itemCount,
        expectedScreenshotCount: this.plan.expectedScreenshotCount,
        countsByKind: this.plan.countsByKind,
        items: this.plan.items,
      },
      progress: {
        completed: this.items.length,
        total: this.plan.itemCount,
        failedItemId: this.failedItemId,
        activeItemId: this.activeItemId,
        expectedScreenshotCount: this.plan.expectedScreenshotCount,
        actualScreenshotCount: this.screenshots.length,
      },
      items: this.items.map((item) => ({ ...item, screenshotPaths: [...item.screenshotPaths] })),
      slowestItems: slowestItems(this.items),
    };
  }

  #record(item, status, durationMs, screenshotStart, actualScreenshots, error) {
    const screenshotPaths = this.screenshots.slice(screenshotStart).map((entry) => entry.path);
    const record = {
      id: item.id,
      kind: item.kind,
      status,
      order: item.order,
      durationMs,
      expectedScreenshots: item.expectedScreenshots,
      actualScreenshots,
      screenshotPaths,
      ...(item.route ? { route: item.route } : {}),
      ...(item.theme ? { theme: item.theme } : {}),
      ...(item.anchorId ? { anchorId: item.anchorId } : {}),
      ...(item.step ? { step: item.step } : {}),
      ...(error || {}),
    };
    this.items.push(record);
    this.completedIds.add(item.id);
    return record;
  }

  async #emit(current, total, message) {
    if (typeof this.emitRunEvent === "function") await this.emitRunEvent({ current, total, message });
  }

  async #persist() {
    if (typeof this.persist === "function") await this.persist(this.snapshot());
  }
}

export function createRunEventEmitter({ outputPath, producerPath } = {}) {
  const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
  const resolvedProducer = producerPath || process.env.ANKI_E2E_RUN_EVENT_PROTOCOL || path.join(moduleDirectory, "run_event_protocol.py");
  const resolvedOutput = outputPath || process.env.ANKI_E2E_RUN_EVENTS_PATH;
  if (!resolvedOutput) throw new Error("ANKI_E2E_RUN_EVENTS_PATH is required for browser progress events");
  return ({ current, total, message }) => new Promise((resolve, reject) => {
    const child = execFile(
      resolvedProducer,
      [
        "emit",
        "--output", resolvedOutput,
        "--producer", "docker-e2e",
        "--phase-id", "browser-smoke-first",
        "--event-kind", "message",
        "--status", "info",
        "--current", String(current),
        "--total", String(total),
        "--message", message,
      ],
      { shell: false, windowsHide: true },
      (error, stdout, stderr) => {
        if (stdout) process.stdout.write(stdout);
        if (stderr) process.stderr.write(stderr);
        if (error) reject(new Error(`Run-event producer failed for browser progress: ${error.message}`));
        else resolve();
      },
    );
    child.stdin?.end();
  });
}

export function safeErrorSummary(error) {
  let value = String(error?.message || error || "Error");
  value = value.replace(/[\r\n\t\0]+/g, " ");
  value = value.replace(/https?:\/\/\S+/gi, "[URL]");
  value = value.replace(/(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/])\S*/g, "[PRIVATE_PATH]");
  value = value.replace(/\/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:\/\S*)?/g, "[PRIVATE_PATH]");
  value = value.replace(/([?&](?:access_)?token=)[^&\s]+/gi, "$1[REDACTED]");
  value = value.trim().replace(/\s+/g, " ");
  if (!value) value = "Error";
  return value.slice(0, SAFE_ERROR_MAX);
}

function safeErrorType(error) {
  const value = String(error?.name || "Error").replace(/[^A-Za-z0-9_.-]/g, "");
  return value.slice(0, 80) || "Error";
}

function safeIdentifier(value, label) {
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

function formatItemContext(item) {
  const parts = [];
  if (item.route) parts.push(`route=${item.route}`);
  if (item.theme) parts.push(`theme=${item.theme}`);
  if (item.anchorId) parts.push(`anchor=${item.anchorId}`);
  if (item.step) parts.push(`step=${item.step}`);
  return parts.length ? ` ${parts.join(" ")}` : "";
}

function nonNegativeDuration(value) {
  if (!Number.isFinite(value)) throw new Error("Browser item duration is not finite");
  return Math.max(0, Math.round(value));
}

function slowestItems(items) {
  return [...items]
    .sort((left, right) => right.durationMs - left.durationMs || left.order - right.order || left.id.localeCompare(right.id))
    .slice(0, SLOWEST_ITEM_COUNT)
    .map(({ id, kind, status, order, durationMs }) => ({ id, kind, status, order, durationMs }));
}
