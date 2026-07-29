import fs from "node:fs/promises";
import path from "node:path";

export const SCREENSHOT_PERFORMANCE_SCHEMA_VERSION = 3;

export function itemTiming(item, reportSchemaVersion) {
  if (reportSchemaVersion >= 3) {
    return {
      value: Number.isInteger(item?.operationDurationMs) ? item.operationDurationMs : null,
      semantics: "operation-only",
    };
  }
  return {
    value: Number.isInteger(item?.durationMs) ? item.durationMs : null,
    semantics: "legacy-lifecycle-mixed",
  };
}

export function validateProgressCounters(progress) {
  const names = ["terminalItems", "passedItems", "failedItems", "skippedItems", "remainingItems", "totalItems"];
  for (const name of names) {
    if (!Number.isInteger(progress?.[name]) || progress[name] < 0) throw new Error(`Invalid browser progress counter: ${name}`);
  }
  if (Object.hasOwn(progress, "completed")) throw new Error("Browser report schema v3 must not serialize progress.completed");
  if (progress.terminalItems !== progress.passedItems + progress.failedItems + progress.skippedItems) {
    throw new Error("terminalItems differs from pass/fail/skip counters");
  }
  if (progress.terminalItems + progress.remainingItems !== progress.totalItems) {
    throw new Error("terminalItems + remainingItems differs from totalItems");
  }
  return progress;
}

export function normalizePerformanceEvidence(report, performance) {
  if (![2, 3].includes(report?.schemaVersion)) throw new Error("Unsupported browser report schema");
  if (report.schemaVersion === 3) validateProgressCounters(report.progress);
  const items = Array.isArray(report.items) ? report.items : [];
  const slowestItems = [...items]
    .map((item) => ({ ...item, timing: itemTiming(item, report.schemaVersion) }))
    .filter((entry) => entry.timing.value !== null)
    .sort((left, right) => right.timing.value - left.timing.value || left.order - right.order || left.id.localeCompare(right.id))
    .slice(0, 5)
    .map((entry) => ({
      id: entry.id,
      kind: entry.kind,
      status: entry.status,
      order: entry.order,
      operationDurationMs: entry.timing.value,
      timingSemantics: entry.timing.semantics,
    }));
  const normalized = {
    ...performance,
    schemaVersion: SCREENSHOT_PERFORMANCE_SCHEMA_VERSION,
    itemTimingSemantics: report.schemaVersion >= 3 ? "operation-only" : "legacy-lifecycle-mixed",
    progress: report.progress,
    producerMetrics: report.producerMetrics || {
      runEventProducerCalls: report.progress?.runEventProducerCalls ?? 0,
      runEventProducerDurationMs: report.progress?.runEventProducerDurationMs ?? 0,
      runEventProducerFailures: report.progress?.runEventProducerFailures ?? 0,
    },
    items,
    slowestItems,
  };
  if (report.schemaVersion >= 3) {
    for (const item of normalized.items) {
      if (Object.hasOwn(item, "durationMs")) throw new Error(`Schema v3 item retains ambiguous durationMs: ${item.id}`);
    }
  }
  return normalized;
}

export async function normalizeBrowserArtifacts({ root, label = "first" }) {
  const reports = path.join(root, "reports");
  const reportPath = path.join(reports, `browser-smoke-${label}.json`);
  const performancePath = path.join(reports, "screenshot-performance.json");
  let report;
  let performance;
  try {
    report = JSON.parse(await fs.readFile(reportPath, "utf8"));
    performance = JSON.parse(await fs.readFile(performancePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") return false;
    throw error;
  }
  const normalized = normalizePerformanceEvidence(report, performance);
  report.screenshotPerformance = normalized;
  await atomicJson(reportPath, report);
  await atomicJson(performancePath, normalized);
  const slowest = normalized.slowestItems.length
    ? normalized.slowestItems.map((item) => `- ${item.id}: ${item.operationDurationMs} ms (${item.status}, ${item.timingSemantics})`).join("\n")
    : "- no terminal operation timings";
  const progress = normalized.progress || {};
  const markdown = [
    "# Screenshot performance",
    "",
    `- Status: ${String(normalized.status || "unknown").toUpperCase()}`,
    `- Browser terminal items: ${progress.terminalItems ?? "n/a"}/${progress.totalItems ?? "n/a"}`,
    `- Browser passed/failed/skipped: ${progress.passedItems ?? "n/a"}/${progress.failedItems ?? "n/a"}/${progress.skippedItems ?? "n/a"}`,
    `- Screenshots: ${normalized.screenshotCount ?? "n/a"}/${normalized.plan?.expectedScreenshotCount ?? "n/a"}`,
    `- Browser wall duration: ${normalized.durationMs ?? "n/a"} ms`,
    `- Item timing semantics: ${normalized.itemTimingSemantics}`,
    `- Run-event producer calls: ${normalized.producerMetrics.runEventProducerCalls}`,
    `- Run-event producer duration: ${normalized.producerMetrics.runEventProducerDurationMs} ms`,
    `- Run-event producer failures: ${normalized.producerMetrics.runEventProducerFailures}`,
    "",
    "## Slowest item operations",
    "",
    slowest,
    "",
  ].join("\n");
  await atomicText(path.join(reports, "screenshot-performance.md"), markdown);
  return true;
}

async function atomicJson(filePath, value) {
  await atomicText(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

async function atomicText(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temp = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  try {
    await fs.writeFile(temp, value, "utf8");
    await fs.rename(temp, filePath);
  } finally {
    await fs.rm(temp, { force: true });
  }
}
