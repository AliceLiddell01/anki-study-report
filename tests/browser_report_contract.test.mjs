import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {
  itemTiming,
  normalizeBrowserArtifacts,
  normalizePerformanceEvidence,
  validateProgressCounters,
} from "../docker/anki-e2e/browser-report-contract.mjs";

test("schema v3 uses operation-only timing and explicit counters", () => {
  const report = {
    schemaVersion: 3,
    progress: { terminalItems: 2, passedItems: 1, failedItems: 1, skippedItems: 0, remainingItems: 0, totalItems: 2 },
    producerMetrics: { runEventProducerCalls: 5, runEventProducerDurationMs: 44, runEventProducerFailures: 1 },
    items: [
      { id: "a", kind: "route-capture", status: "pass", order: 1, operationDurationMs: 7 },
      { id: "b", kind: "telemetry", status: "fail", order: 2, operationDurationMs: 9 },
    ],
  };
  const result = normalizePerformanceEvidence(report, { schemaVersion: 2, status: "fail" });
  assert.equal(result.schemaVersion, 3);
  assert.equal(result.itemTimingSemantics, "operation-only");
  assert.equal(result.slowestItems[0].id, "b");
  assert.equal(result.producerMetrics.runEventProducerCalls, 5);
  assert.equal(Object.hasOwn(result.progress, "completed"), false);
});

test("legacy schema v2 remains readable but is labeled non-comparable", () => {
  assert.deepEqual(itemTiming({ durationMs: 12 }, 2), { value: 12, semantics: "legacy-lifecycle-mixed" });
  const result = normalizePerformanceEvidence({
    schemaVersion: 2,
    progress: { completed: 1, total: 1 },
    items: [{ id: "legacy", kind: "route-capture", status: "pass", order: 1, durationMs: 12 }],
  }, { schemaVersion: 2 });
  assert.equal(result.itemTimingSemantics, "legacy-lifecycle-mixed");
  assert.equal(result.slowestItems[0].timingSemantics, "legacy-lifecycle-mixed");
});

test("counter invariants reject completed and arithmetic mismatches", () => {
  assert.throws(() => validateProgressCounters({ completed: 1, terminalItems: 1, passedItems: 1, failedItems: 0, skippedItems: 0, remainingItems: 0, totalItems: 1 }), /completed/);
  assert.throws(() => validateProgressCounters({ terminalItems: 2, passedItems: 1, failedItems: 0, skippedItems: 0, remainingItems: 0, totalItems: 2 }), /terminalItems differs/);
});

test("artifact normalizer rewrites nested report and Markdown", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "asr-browser-contract-"));
  const reports = path.join(root, "reports");
  await fs.mkdir(reports, { recursive: true });
  const report = {
    schemaVersion: 3,
    progress: { terminalItems: 1, passedItems: 1, failedItems: 0, skippedItems: 0, remainingItems: 0, totalItems: 1 },
    producerMetrics: { runEventProducerCalls: 2, runEventProducerDurationMs: 10, runEventProducerFailures: 0 },
    items: [{ id: "a", kind: "diagnostics", status: "pass", order: 1, operationDurationMs: 4 }],
  };
  await fs.writeFile(path.join(reports, "browser-smoke-first.json"), JSON.stringify(report));
  await fs.writeFile(path.join(reports, "screenshot-performance.json"), JSON.stringify({ schemaVersion: 2, status: "pass", screenshotCount: 0, durationMs: 100, plan: { expectedScreenshotCount: 0 } }));
  assert.equal(await normalizeBrowserArtifacts({ root, label: "first" }), true);
  const normalized = JSON.parse(await fs.readFile(path.join(reports, "screenshot-performance.json"), "utf8"));
  const browser = JSON.parse(await fs.readFile(path.join(reports, "browser-smoke-first.json"), "utf8"));
  const markdown = await fs.readFile(path.join(reports, "screenshot-performance.md"), "utf8");
  assert.equal(normalized.schemaVersion, 3);
  assert.equal(browser.screenshotPerformance.schemaVersion, 3);
  assert.match(markdown, /Item timing semantics: operation-only/);
  assert.doesNotMatch(markdown, /undefined/);
});
