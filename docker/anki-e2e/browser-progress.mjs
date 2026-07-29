import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

import {
  BROWSER_PLAN_SCHEMA_VERSION,
  BROWSER_REPORT_SCHEMA_VERSION,
  KNOWN_ITEM_KINDS,
  PREVIEW_ANCHOR_IDS,
  ROUTE_CASES,
  THEMES,
  buildBrowserPlan,
  validateBrowserPlan,
  safeIdentifier,
} from "./browser-plan.mjs";

export {
  BROWSER_PLAN_SCHEMA_VERSION,
  BROWSER_REPORT_SCHEMA_VERSION,
  KNOWN_ITEM_KINDS,
  PREVIEW_ANCHOR_IDS,
  ROUTE_CASES,
  THEMES,
  buildBrowserPlan,
  validateBrowserPlan,
};


const SAFE_ERROR_MAX = 240;
const SLOWEST_ITEM_COUNT = 5;

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
    this.terminalIds = new Set();
    this.activeItemId = null;
    this.failedItemId = null;
    this.producerMetrics = {
      runEventProducerCalls: 0,
      runEventProducerDurationMs: 0,
      runEventProducerFailures: 0,
    };
  }

  printPlan() {
    this.log(`[BROWSER] PLAN items=${this.plan.itemCount} screenshots=${this.plan.expectedScreenshotCount} telemetry=${this.plan.telemetryEnabled}`);
  }

  async run(itemId, operation) {
    const item = this.itemById.get(itemId);
    if (!item) throw new Error(`Unknown or unplanned browser item: ${itemId}`);
    if (this.activeItemId) throw new Error(`Browser item is already active: ${this.activeItemId}`);
    if (this.terminalIds.has(itemId)) throw new Error(`Browser item already terminal: ${itemId}`);
    if (typeof operation !== "function") throw new Error(`Browser item operation must be callable: ${itemId}`);

    const current = item.order;
    const total = this.plan.itemCount;
    const screenshotStart = this.screenshots.length;
    let operationStarted = null;
    let operationDurationMs = null;
    let failureStage = "start-run-event";
    this.activeItemId = itemId;
    this.log(`[BROWSER] [${current}/${total}] START ${item.kind} item=${item.id}${formatItemContext(item)}`);

    try {
      await this.#emit(current, total, `item=start id=${item.id} kind=${item.kind}`);
      failureStage = "start-persist";
      await this.#persist();
      failureStage = "operation";
      operationStarted = this.now();
      const value = await operation();
      operationDurationMs = nonNegativeDuration(this.now() - operationStarted);
      const actualScreenshots = this.screenshots.length - screenshotStart;
      if (actualScreenshots !== item.expectedScreenshots) {
        throw new Error(`Screenshot contribution mismatch for ${item.id}: expected ${item.expectedScreenshots}, actual ${actualScreenshots}`);
      }
      failureStage = "pass-run-event";
      await this.#emit(current, total, `item=pass id=${item.id} kind=${item.kind} operationDurationMs=${operationDurationMs} screenshots=${actualScreenshots}`);
      this.#record(item, "pass", operationDurationMs, screenshotStart, actualScreenshots, null, null);
      this.log(`[BROWSER] [${current}/${total}] PASS ${item.kind} item=${item.id} operation=${operationDurationMs}ms screenshots=${actualScreenshots}`);
      failureStage = "pass-persist";
      await this.#persist();
      return value;
    } catch (error) {
      if (operationStarted !== null && operationDurationMs === null) {
        operationDurationMs = nonNegativeDuration(this.now() - operationStarted);
      }
      const actualScreenshots = this.screenshots.length - screenshotStart;
      this.failedItemId = item.id;
      if (!this.terminalIds.has(item.id)) {
        this.#record(item, "fail", operationDurationMs, screenshotStart, actualScreenshots, {
          errorType: safeErrorType(error),
          safeErrorSummary: safeErrorSummary(error),
        }, failureStage);
      } else {
        const record = this.items.find((candidate) => candidate.id === item.id);
        if (record) {
          record.status = "fail";
          record.failureStage = failureStage;
          record.errorType = safeErrorType(error);
          record.safeErrorSummary = safeErrorSummary(error);
        }
      }
      const durationText = operationDurationMs === null ? "n/a" : `${operationDurationMs}ms`;
      this.log(`[BROWSER] [${current}/${total}] FAIL ${item.kind} item=${item.id} operation=${durationText} screenshots=${actualScreenshots} stage=${failureStage} errorType=${safeErrorType(error)}`);
      try {
        await this.#emit(current, total, `item=fail id=${item.id} kind=${item.kind} stage=${failureStage} errorType=${safeErrorType(error)}`);
      } catch {
        this.log(`[BROWSER] [${current}/${total}] INFO ${item.kind} item=${item.id} secondary=run-event-producer`);
      }
      try {
        await this.#persist();
      } catch {
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
    if (this.terminalIds.size !== this.plan.itemCount) {
      throw new Error(`Browser progress incomplete: ${this.terminalIds.size}/${this.plan.itemCount}`);
    }
    if (this.screenshots.length !== this.plan.expectedScreenshotCount) {
      throw new Error(`Browser screenshot total mismatch: expected ${this.plan.expectedScreenshotCount}, actual ${this.screenshots.length}`);
    }
    return this.snapshot();
  }

  snapshot() {
    const passedItems = this.items.filter((item) => item.status === "pass").length;
    const failedItems = this.items.filter((item) => item.status === "fail").length;
    const skippedItems = this.items.filter((item) => item.status === "skip").length;
    const terminalItems = passedItems + failedItems + skippedItems;
    const progress = {
      terminalItems,
      passedItems,
      failedItems,
      skippedItems,
      remainingItems: this.plan.itemCount - terminalItems,
      totalItems: this.plan.itemCount,
      failedItemId: this.failedItemId,
      activeItemId: this.activeItemId,
      expectedScreenshotCount: this.plan.expectedScreenshotCount,
      actualScreenshotCount: this.screenshots.length,
      runEventProducerCalls: this.producerMetrics.runEventProducerCalls,
      runEventProducerDurationMs: this.producerMetrics.runEventProducerDurationMs,
      runEventProducerFailures: this.producerMetrics.runEventProducerFailures,
    };
    // Non-enumerable runtime aliases keep the unchanged smoke orchestrator readable
    // while schema v3 JSON deliberately omits the ambiguous legacy fields.
    Object.defineProperties(progress, {
      completed: { value: terminalItems, enumerable: false },
      total: { value: this.plan.itemCount, enumerable: false },
    });
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
      progress,
      producerMetrics: { ...this.producerMetrics },
      items: this.items.map((item) => ({ ...item, screenshotPaths: [...item.screenshotPaths] })),
      slowestItems: slowestItems(this.items),
    };
  }

  #record(item, status, operationDurationMs, screenshotStart, actualScreenshots, error, failureStage) {
    const screenshotPaths = this.screenshots.slice(screenshotStart).map((entry) => entry.path);
    const record = {
      id: item.id,
      kind: item.kind,
      status,
      order: item.order,
      operationDurationMs,
      expectedScreenshots: item.expectedScreenshots,
      actualScreenshots,
      screenshotPaths,
      ...(failureStage ? { failureStage } : {}),
      ...(item.route ? { route: item.route } : {}),
      ...(item.theme ? { theme: item.theme } : {}),
      ...(item.anchorId ? { anchorId: item.anchorId } : {}),
      ...(item.step ? { step: item.step } : {}),
      ...(error || {}),
    };
    this.items.push(record);
    this.terminalIds.add(item.id);
    return record;
  }

  async #emit(current, total, message) {
    if (typeof this.emitRunEvent !== "function") return;
    const started = this.now();
    this.producerMetrics.runEventProducerCalls += 1;
    try {
      await this.emitRunEvent({ current, total, message });
    } catch (error) {
      this.producerMetrics.runEventProducerFailures += 1;
      throw error;
    } finally {
      this.producerMetrics.runEventProducerDurationMs += nonNegativeDuration(this.now() - started);
    }
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
        if (error) {
          const wrapped = new Error(`Run-event producer failed for browser progress: ${error.message}`, { cause: error });
          wrapped.code = error.code ?? null;
          wrapped.signal = error.signal ?? null;
          reject(wrapped);
        } else {
          resolve();
        }
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

export function safeErrorType(error) {
  const value = String(error?.name || "Error").replace(/[^A-Za-z0-9_.-]/g, "");
  return value.slice(0, 80) || "Error";
}

export function formatItemContext(item) {
  const parts = [];
  if (item.route) parts.push(`route=${item.route}`);
  if (item.theme) parts.push(`theme=${item.theme}`);
  if (item.anchorId) parts.push(`anchor=${item.anchorId}`);
  if (item.step) parts.push(`step=${item.step}`);
  return parts.length ? ` ${parts.join(" ")}` : "";
}

export function nonNegativeDuration(value) {
  if (!Number.isFinite(value)) throw new Error("Browser item duration is not finite");
  return Math.max(0, Math.round(value));
}

export function slowestItems(items) {
  return items
    .filter((item) => Number.isInteger(item.operationDurationMs))
    .sort((left, right) => right.operationDurationMs - left.operationDurationMs || left.order - right.order || left.id.localeCompare(right.id))
    .slice(0, SLOWEST_ITEM_COUNT)
    .map(({ id, kind, status, order, operationDurationMs }) => {
      const item = { id, kind, status, order, operationDurationMs };
      Object.defineProperty(item, "durationMs", { value: operationDurationMs, enumerable: false });
      return item;
    });
}
