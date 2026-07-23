import test from "node:test";
import assert from "node:assert/strict";
import {
  BROWSER_PLAN_SCHEMA_VERSION,
  BROWSER_REPORT_SCHEMA_VERSION,
  BrowserProgress,
  PREVIEW_ANCHOR_IDS,
  ROUTE_CASES,
  THEMES,
  buildBrowserPlan,
  safeErrorSummary,
  validateBrowserPlan,
} from "../docker/anki-e2e/browser-progress.mjs";

function plan(telemetryEnabled = true) {
  return buildBrowserPlan({ label: "first", mode: "standard", scope: "cards", telemetryEnabled });
}

function harness(customPlan = plan(false)) {
  const screenshots = [];
  const logs = [];
  const events = [];
  const snapshots = [];
  let clock = 0;
  const progress = new BrowserProgress({
    plan: customPlan,
    screenshots,
    log: (line) => logs.push(line),
    emitRunEvent: async (event) => events.push(event),
    persist: async (snapshot) => snapshots.push(snapshot),
    now: () => (clock += 10),
  });
  return { progress, screenshots, logs, events, snapshots };
}

test("plan is deterministic, bounded, and preserves 18 screenshots", () => {
  const first = plan(true);
  const second = plan(true);
  assert.deepEqual(first, second);
  assert.equal(first.schemaVersion, BROWSER_PLAN_SCHEMA_VERSION);
  assert.equal(BROWSER_REPORT_SCHEMA_VERSION, 2);
  assert.equal(first.expectedScreenshotCount, 18);
  assert.equal(new Set(first.items.map((item) => item.id)).size, first.itemCount);
  assert.deepEqual(ROUTE_CASES.map((item) => item.name), ["home", "cards", "decks", "profile", "settings"]);
  assert.deepEqual(THEMES, ["light", "dark"]);
  assert.deepEqual(PREVIEW_ANCHOR_IDS, ["words-preview", "grammar-preview", "java-preview"]);
  assert.equal(first.countsByKind["route-capture"], 10);
  assert.equal(first.countsByKind["native-preview"], 3);
  assert.equal(first.countsByKind["cards-route"], 2);
  assert.equal(first.countsByKind.telemetry, 4);
  assert.equal(first.items.filter((item) => item.kind === "native-preview").every((item) => item.expectedScreenshots === 2), true);
  assert.equal(first.items.reduce((sum, item) => sum + item.expectedScreenshots, 0), 18);
  validateBrowserPlan(first);
});

test("telemetry items are absent when endpoint is disabled", () => {
  const disabled = plan(false);
  assert.equal(disabled.telemetryEnabled, false);
  assert.equal(disabled.items.some((item) => item.kind === "telemetry"), false);
  assert.equal(disabled.expectedScreenshotCount, 18);
});

test("START precedes operation and PASS records duration and screenshot delta", async () => {
  const custom = { ...plan(false), items: [Object.freeze({ id: "route.home.light", kind: "route-capture", label: "route=#/home theme=light", route: "#/home", theme: "light", expectedScreenshots: 1, order: 1 })], itemCount: 1, countsByKind: { "route-capture": 1 }, expectedScreenshotCount: 1 };
  const { progress, screenshots, logs, events } = harness(custom);
  const order = [];
  progress.log = (line) => { logs.push(line); order.push(line.includes("START") ? "start" : "pass"); };
  await progress.run("route.home.light", async () => { order.push("operation"); screenshots.push({ path: "screenshots/pages/home/light.png" }); });
  const snapshot = progress.finalize();
  assert.deepEqual(order, ["start", "operation", "pass"]);
  assert.equal(snapshot.items[0].status, "pass");
  assert.equal(snapshot.items[0].durationMs, 10);
  assert.equal(snapshot.items[0].actualScreenshots, 1);
  assert.deepEqual(snapshot.items[0].screenshotPaths, ["screenshots/pages/home/light.png"]);
  assert.deepEqual(events.map((event) => [event.current, event.total]), [[1, 1], [1, 1]]);
});

test("FAIL records exact item and rethrows the original exception", async () => {
  const custom = { ...plan(false), items: [Object.freeze({ id: "preview.words-preview", kind: "native-preview", label: "anchor=words-preview", anchorId: "words-preview", expectedScreenshots: 2, order: 1 })], itemCount: 1, countsByKind: { "native-preview": 1 }, expectedScreenshotCount: 2 };
  const { progress, logs, events, snapshots } = harness(custom);
  const original = new TypeError("failed at https://127.0.0.1/?token=secret /home/owner/private");
  await assert.rejects(progress.run("preview.words-preview", async () => { throw original; }), (error) => error === original);
  const snapshot = progress.snapshot();
  assert.equal(snapshot.progress.failedItemId, "preview.words-preview");
  assert.equal(snapshot.progress.activeItemId, null);
  assert.equal(snapshot.items[0].status, "fail");
  assert.equal(snapshot.items[0].errorType, "TypeError");
  assert.equal(snapshot.items[0].safeErrorSummary.includes("secret"), false);
  assert.equal(snapshot.items[0].safeErrorSummary.includes("/home/"), false);
  assert.equal(logs.some((line) => line.includes("FAIL native-preview item=preview.words-preview")), true);
  assert.equal(events.at(-1).message.includes("errorType=TypeError"), true);
  assert.equal(snapshots.at(-1).progress.failedItemId, "preview.words-preview");
});

test("run-event producer failure hard-fails the item and preserves the original error", async () => {
  const custom = { ...plan(false), items: [Object.freeze({ id: "diagnostics.final", kind: "diagnostics", label: "final", expectedScreenshots: 0, order: 1 })], itemCount: 1, countsByKind: { diagnostics: 1 }, expectedScreenshotCount: 0 };
  const original = new Error("producer unavailable");
  const progress = new BrowserProgress({
    plan: custom,
    screenshots: [],
    log: () => {},
    emitRunEvent: async () => { throw original; },
    persist: async () => {},
    now: () => 10,
  });
  await assert.rejects(progress.run("diagnostics.final", async () => {}), (error) => error === original);
  const snapshot = progress.snapshot();
  assert.equal(snapshot.progress.failedItemId, "diagnostics.final");
  assert.equal(snapshot.progress.activeItemId, null);
  assert.equal(snapshot.items.length, 1);
  assert.equal(snapshot.items[0].status, "fail");
});

test("unknown and duplicate completion are rejected", async () => {
  const custom = { ...plan(false), items: [Object.freeze({ id: "diagnostics.final", kind: "diagnostics", label: "final", expectedScreenshots: 0, order: 1 })], itemCount: 1, countsByKind: { diagnostics: 1 }, expectedScreenshotCount: 0 };
  const { progress } = harness(custom);
  await assert.rejects(progress.run("unknown.item", async () => {}), /Unknown or unplanned/);
  await progress.run("diagnostics.final", async () => {});
  await assert.rejects(progress.run("diagnostics.final", async () => {}), /already completed/);
});

test("screenshot accounting fails closed", async () => {
  const custom = { ...plan(false), items: [Object.freeze({ id: "route.home.light", kind: "route-capture", label: "route", expectedScreenshots: 1, order: 1 })], itemCount: 1, countsByKind: { "route-capture": 1 }, expectedScreenshotCount: 1 };
  const { progress } = harness(custom);
  await assert.rejects(progress.run("route.home.light", async () => {}), /Screenshot contribution mismatch/);
  assert.equal(progress.snapshot().items[0].status, "fail");
});

test("slowest items are deterministic and bounded", async () => {
  const items = [
    Object.freeze({ id: "a.one", kind: "diagnostics", label: "a", expectedScreenshots: 0, order: 1 }),
    Object.freeze({ id: "b.two", kind: "diagnostics", label: "b", expectedScreenshots: 0, order: 2 }),
  ];
  const custom = { ...plan(false), items, itemCount: 2, countsByKind: { diagnostics: 2 }, expectedScreenshotCount: 0 };
  let clock = 0;
  const progress = new BrowserProgress({ plan: custom, screenshots: [], now: () => (clock += 5), log: () => {}, emitRunEvent: async () => {} });
  await progress.run("a.one", async () => {});
  await progress.run("b.two", async () => {});
  const snapshot = progress.finalize();
  assert.deepEqual(snapshot.slowestItems.map((item) => item.id), ["a.one", "b.two"]);
  assert.equal(snapshot.items.every((item) => Number.isInteger(item.durationMs) && item.durationMs >= 0), true);
});

test("safe error summary removes URLs, tokens, and private paths", () => {
  const value = safeErrorSummary(new Error("boom https://localhost/a?token=secret C:\\Users\\owner\\x /tmp/private"));
  assert.equal(value.includes("secret"), false);
  assert.equal(value.includes("C:\\"), false);
  assert.equal(value.includes("/tmp/"), false);
  assert.equal(value.includes("\n"), false);
});
