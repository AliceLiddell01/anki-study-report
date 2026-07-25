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

function oneItem(item) {
  return {
    ...plan(false),
    items: [Object.freeze({ ...item, order: 1 })],
    itemCount: 1,
    countsByKind: { [item.kind]: 1 },
    expectedScreenshotCount: item.expectedScreenshots,
  };
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
    emitRunEvent: async (event) => { events.push(event); clock += 100; },
    persist: async (snapshot) => { snapshots.push(snapshot); clock += 50; },
    now: () => clock,
  });
  return { progress, screenshots, logs, events, snapshots, advance: (ms) => { clock += ms; } };
}

test("plan is deterministic, bounded, and preserves 18 screenshots", () => {
  const first = plan(true);
  const second = plan(true);
  assert.deepEqual(first, second);
  assert.equal(first.schemaVersion, BROWSER_PLAN_SCHEMA_VERSION);
  assert.equal(BROWSER_REPORT_SCHEMA_VERSION, 3);
  assert.equal(first.expectedScreenshotCount, 18);
  assert.equal(new Set(first.items.map((item) => item.id)).size, first.itemCount);
  assert.deepEqual(ROUTE_CASES.map((item) => item.name), ["home", "cards", "decks", "profile", "settings"]);
  assert.deepEqual(THEMES, ["light", "dark"]);
  assert.deepEqual(PREVIEW_ANCHOR_IDS, ["words-preview", "grammar-preview", "java-preview"]);
  assert.equal(first.countsByKind["route-capture"], 10);
  assert.equal(first.countsByKind["native-preview"], 3);
  assert.equal(first.countsByKind["cards-route"], 2);
  assert.equal(first.countsByKind.telemetry, 4);
  assert.equal(first.items.reduce((sum, item) => sum + item.expectedScreenshots, 0), 18);
  validateBrowserPlan(first);
});

test("telemetry items are absent when endpoint is disabled", () => {
  const disabled = plan(false);
  assert.equal(disabled.telemetryEnabled, false);
  assert.equal(disabled.items.some((item) => item.kind === "telemetry"), false);
  assert.equal(disabled.expectedScreenshotCount, 18);
});

test("operationDurationMs excludes START/PASS producer and persist overhead", async () => {
  const custom = oneItem({
    id: "route.home.light",
    kind: "route-capture",
    label: "route=#/home theme=light",
    route: "#/home",
    theme: "light",
    expectedScreenshots: 1,
  });
  const { progress, screenshots, events, advance } = harness(custom);
  await progress.run("route.home.light", async () => {
    advance(20);
    screenshots.push({ path: "screenshots/pages/home/light.png" });
  });
  const snapshot = progress.finalize();
  assert.equal(snapshot.items[0].operationDurationMs, 20);
  assert.equal(snapshot.items[0].durationMs, undefined);
  assert.equal(snapshot.items[0].actualScreenshots, 1);
  assert.deepEqual(snapshot.items[0].screenshotPaths, ["screenshots/pages/home/light.png"]);
  assert.equal(snapshot.producerMetrics.runEventProducerCalls, 2);
  assert.equal(snapshot.producerMetrics.runEventProducerDurationMs, 200);
  assert.equal(snapshot.producerMetrics.runEventProducerFailures, 0);
  assert.deepEqual(events.map((event) => [event.current, event.total]), [[1, 1], [1, 1]]);
});

test("progress counters distinguish terminal pass fail skip and remaining", async () => {
  const custom = oneItem({ id: "diagnostics.final", kind: "diagnostics", label: "final", expectedScreenshots: 0 });
  const { progress, advance } = harness(custom);
  let snapshot = progress.snapshot();
  assert.deepEqual(
    {
      terminalItems: snapshot.progress.terminalItems,
      passedItems: snapshot.progress.passedItems,
      failedItems: snapshot.progress.failedItems,
      skippedItems: snapshot.progress.skippedItems,
      remainingItems: snapshot.progress.remainingItems,
      totalItems: snapshot.progress.totalItems,
    },
    { terminalItems: 0, passedItems: 0, failedItems: 0, skippedItems: 0, remainingItems: 1, totalItems: 1 },
  );
  assert.equal(snapshot.progress.completed, 0);
  assert.equal(Object.keys(snapshot.progress).includes("completed"), false);
  assert.equal(JSON.stringify(snapshot.progress).includes("completed"), false);
  await progress.run("diagnostics.final", async () => advance(7));
  snapshot = progress.finalize();
  assert.deepEqual(
    {
      terminalItems: snapshot.progress.terminalItems,
      passedItems: snapshot.progress.passedItems,
      failedItems: snapshot.progress.failedItems,
      skippedItems: snapshot.progress.skippedItems,
      remainingItems: snapshot.progress.remainingItems,
      totalItems: snapshot.progress.totalItems,
    },
    { terminalItems: 1, passedItems: 1, failedItems: 0, skippedItems: 0, remainingItems: 0, totalItems: 1 },
  );
});

test("FAIL records exact item and rethrows the original operation exception", async () => {
  const custom = oneItem({
    id: "preview.words-preview",
    kind: "native-preview",
    label: "anchor=words-preview",
    anchorId: "words-preview",
    expectedScreenshots: 2,
  });
  const { progress, logs, snapshots, advance } = harness(custom);
  const original = new TypeError("failed at https://127.0.0.1/?token=secret /home/owner/private");
  await assert.rejects(progress.run("preview.words-preview", async () => { advance(33); throw original; }), (error) => error === original);
  const snapshot = progress.snapshot();
  assert.equal(snapshot.progress.failedItemId, "preview.words-preview");
  assert.equal(snapshot.progress.activeItemId, null);
  assert.equal(snapshot.progress.terminalItems, 1);
  assert.equal(snapshot.progress.passedItems, 0);
  assert.equal(snapshot.progress.failedItems, 1);
  assert.equal(snapshot.items[0].status, "fail");
  assert.equal(snapshot.items[0].failureStage, "operation");
  assert.equal(snapshot.items[0].operationDurationMs, 33);
  assert.equal(snapshot.items[0].errorType, "TypeError");
  assert.equal(snapshot.items[0].safeErrorSummary.includes("secret"), false);
  assert.equal(snapshot.items[0].safeErrorSummary.includes("/home/"), false);
  assert.equal(logs.some((line) => line.includes("FAIL native-preview item=preview.words-preview")), true);
  assert.equal(snapshots.at(-1).progress.failedItemId, "preview.words-preview");
});

test("run-event producer failure is measured and operation is not mis-timed", async () => {
  const custom = oneItem({ id: "diagnostics.final", kind: "diagnostics", label: "final", expectedScreenshots: 0 });
  const original = new Error("producer unavailable");
  let clock = 0;
  const progress = new BrowserProgress({
    plan: custom,
    screenshots: [],
    log: () => {},
    emitRunEvent: async () => { clock += 25; throw original; },
    persist: async () => {},
    now: () => clock,
  });
  await assert.rejects(progress.run("diagnostics.final", async () => { clock += 100; }), (error) => error === original);
  const snapshot = progress.snapshot();
  assert.equal(snapshot.items[0].failureStage, "start-run-event");
  assert.equal(snapshot.items[0].operationDurationMs, null);
  assert.equal(snapshot.producerMetrics.runEventProducerCalls, 2);
  assert.equal(snapshot.producerMetrics.runEventProducerFailures, 2);
  assert.equal(snapshot.producerMetrics.runEventProducerDurationMs, 50);
});

test("producer calls are bounded by lifecycle and milestones, not HTTP events or screenshots", async () => {
  const custom = oneItem({
    id: "route.home.light",
    kind: "route-capture",
    label: "route",
    expectedScreenshots: 1,
  });
  const { progress, screenshots, advance } = harness(custom);
  await progress.run("route.home.light", async () => {
    for (let index = 0; index < 100; index += 1) advance(1); // observational stand-in for HTTP activity
    screenshots.push({ path: "screenshots/pages/home/light.png" });
  });
  const snapshot = progress.finalize();
  assert.equal(snapshot.producerMetrics.runEventProducerCalls, 2);
  assert.equal(snapshot.items[0].operationDurationMs, 100);
});

test("telemetry milestones add bounded producer calls", async () => {
  const custom = oneItem({
    id: "telemetry.offline",
    kind: "telemetry",
    label: "offline",
    step: "offline",
    expectedScreenshots: 0,
  });
  const { progress, advance } = harness(custom);
  await progress.run("telemetry.offline", async () => {
    advance(5);
    await progress.milestone("telemetry.offline", "queue-persisted");
  });
  const snapshot = progress.finalize();
  assert.equal(snapshot.producerMetrics.runEventProducerCalls, 3);
});

test("unknown and duplicate terminal item are rejected", async () => {
  const custom = oneItem({ id: "diagnostics.final", kind: "diagnostics", label: "final", expectedScreenshots: 0 });
  const { progress } = harness(custom);
  await assert.rejects(progress.run("unknown.item", async () => {}), /Unknown or unplanned/);
  await progress.run("diagnostics.final", async () => {});
  await assert.rejects(progress.run("diagnostics.final", async () => {}), /already terminal/);
});

test("screenshot accounting fails closed while preserving operation timing", async () => {
  const custom = oneItem({ id: "route.home.light", kind: "route-capture", label: "route", expectedScreenshots: 1 });
  const { progress, advance } = harness(custom);
  await assert.rejects(progress.run("route.home.light", async () => advance(9)), /Screenshot contribution mismatch/);
  const item = progress.snapshot().items[0];
  assert.equal(item.status, "fail");
  assert.equal(item.operationDurationMs, 9);
  assert.equal(item.failureStage, "operation");
});

test("slowest items use operation-only timing and remain deterministic", async () => {
  const items = [
    Object.freeze({ id: "a.one", kind: "diagnostics", label: "a", expectedScreenshots: 0, order: 1 }),
    Object.freeze({ id: "b.two", kind: "diagnostics", label: "b", expectedScreenshots: 0, order: 2 }),
  ];
  const custom = { ...plan(false), items, itemCount: 2, countsByKind: { diagnostics: 2 }, expectedScreenshotCount: 0 };
  const { progress, advance } = harness(custom);
  await progress.run("a.one", async () => advance(5));
  await progress.run("b.two", async () => advance(10));
  const snapshot = progress.finalize();
  assert.deepEqual(snapshot.slowestItems.map((item) => item.id), ["b.two", "a.one"]);
  assert.deepEqual(snapshot.slowestItems.map((item) => item.operationDurationMs), [10, 5]);
});

test("safe error summary removes URLs, tokens, and private paths", () => {
  const value = safeErrorSummary(new Error("boom https://localhost/a?token=secret C:\\Users\\owner\\x /tmp/private"));
  assert.equal(value.includes("secret"), false);
  assert.equal(value.includes("C:\\"), false);
  assert.equal(value.includes("/tmp/"), false);
  assert.equal(value.includes("\n"), false);
});
