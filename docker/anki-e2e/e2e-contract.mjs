export const E2E_SCOPES = Object.freeze(["full", "global", "stats", "decks", "activity", "cards", "settings"]);

const PAGE_SCOPE = Object.freeze({
  today: "global",
  calendar: "activity",
  "stats-overview": "stats",
  "stats-quality": "stats",
  "stats-load": "stats",
  "stats-progress": "stats",
  "stats-decks": "stats",
  "fsrs-overview": "stats",
  "fsrs-memory": "stats",
  "fsrs-calibration": "stats",
  "fsrs-steps": "stats",
  "fsrs-simulator": "stats",
  decks: "decks",
  search: "global",
  profile: "global",
  tools: "global",
  "settings/report": "settings",
  "settings/data": "settings",
  "settings/privacy": "settings",
  "settings/server": "settings",
  "settings/sources": "settings",
  "settings/logs": "settings",
});

export function resolveScope(value = "full") {
  const scope = String(value || "full").trim().toLowerCase();
  if (!E2E_SCOPES.includes(scope)) throw new Error(`Unsupported E2E scope: ${value}`);
  return scope;
}

export function resolveWorkerCount(value = "auto", cpuCount = 4) {
  const normalized = String(value || "auto").trim().toLowerCase();
  const count = normalized === "auto" ? Math.min(3, Math.max(1, Number(cpuCount) - 1)) : Number(normalized);
  if (!Number.isInteger(count) || count < 1 || count > 4) {
    throw new Error(`Screenshot workers must be auto or an integer from 1 to 4: ${value}`);
  }
  return count;
}

export function shouldRunScope(selectedScope, candidateScope) {
  return selectedScope === "full" || selectedScope === candidateScope;
}

export function filterPageCases(pageCases, scope) {
  const selected = resolveScope(scope);
  return pageCases.filter((item) => selected === "full" || PAGE_SCOPE[item.pageName] === selected);
}

export function buildPageCaptureTasks(pageCases, scope) {
  const tasks = [];
  for (const theme of ["light", "dark"]) {
    for (const pageCase of filterPageCases(pageCases, scope)) {
      tasks.push({
        id: `page:${pageCase.pageName}:${theme}`,
        scope: PAGE_SCOPE[pageCase.pageName],
        route: pageCase.route,
        pageName: pageCase.pageName,
        heading: pageCase.heading,
        primaryHref: pageCase.primaryHref || null,
        settingsHref: pageCase.settingsHref || null,
        theme,
        zoom: 1,
        state: "default",
        artifactPath: `screenshots/pages/${pageCase.pageName}/${theme}.png`,
        serialGroup: null,
      });
    }
  }
  assertUniqueTasks(tasks);
  return tasks;
}

export function assertUniqueTasks(tasks) {
  for (const field of ["id", "artifactPath"]) {
    const values = tasks.map((task) => task[field]);
    const duplicate = values.find((value, index) => values.indexOf(value) !== index);
    if (duplicate) throw new Error(`Duplicate capture task ${field}: ${duplicate}`);
  }
}

export async function runBoundedTaskQueue(tasks, workerCount, workerFactory, executeTask) {
  const count = Math.min(resolveWorkerCount(workerCount), Math.max(1, tasks.length));
  const results = new Array(tasks.length);
  const errors = [];
  let cursor = 0;
  const startedAt = Date.now();
  const workers = [];
  try {
    for (let index = 0; index < count; index += 1) workers.push(await workerFactory(index + 1));
    await Promise.all(workers.map(async (worker, workerIndex) => {
      while (true) {
        const taskIndex = cursor++;
        if (taskIndex >= tasks.length) break;
        const task = tasks[taskIndex];
        const taskStartedAt = Date.now();
        try {
          const value = await executeTask(worker, task, workerIndex + 1);
          results[taskIndex] = { ...task, workerId: workerIndex + 1, startedAt: new Date(taskStartedAt).toISOString(), finishedAt: new Date().toISOString(), durationMs: Date.now() - taskStartedAt, result: "success", retryCount: 0, value };
        } catch (error) {
          const failure = { ...task, workerId: workerIndex + 1, startedAt: new Date(taskStartedAt).toISOString(), finishedAt: new Date().toISOString(), durationMs: Date.now() - taskStartedAt, result: "failed", retryCount: 0, error: String(error?.stack || error) };
          results[taskIndex] = failure;
          errors.push(failure);
        }
      }
    }));
  } finally {
    await Promise.allSettled(workers.map((worker) => worker.close()));
  }
  if (errors.length) {
    const error = new Error(`Parallel capture failed for ${errors.map((item) => item.id).join(", ")}`);
    error.taskResults = results.filter(Boolean);
    throw error;
  }
  return { startedAt, finishedAt: Date.now(), workerCount: count, tasks: results };
}

function percentile(values, percentileValue) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.max(0, Math.ceil((percentileValue / 100) * sorted.length) - 1)];
}

export function summarizeCapturePerformance(run) {
  const tasks = run.tasks || [];
  const durations = tasks.map((task) => task.durationMs).filter(Number.isFinite);
  const wallMs = Math.max(0, Number(run.finishedAt) - Number(run.startedAt));
  const summedTaskMs = durations.reduce((sum, value) => sum + value, 0);
  const workerBusyMs = Object.fromEntries(Array.from({ length: run.workerCount }, (_, index) => {
    const workerId = index + 1;
    return [String(workerId), tasks.filter((task) => task.workerId === workerId).reduce((sum, task) => sum + task.durationMs, 0)];
  }));
  const speedup = wallMs ? summedTaskMs / wallMs : null;
  const sumBy = (key) => Object.fromEntries([...new Set(tasks.map((task) => String(task[key] ?? "none")))].sort().map((value) => [value, tasks.filter((task) => String(task[key] ?? "none") === value).reduce((sum, task) => sum + task.durationMs, 0)]));
  return {
    schemaVersion: 1,
    totalTasks: tasks.length,
    successfulTasks: tasks.filter((task) => task.result === "success").length,
    failedTasks: tasks.filter((task) => task.result === "failed").length,
    retries: tasks.reduce((sum, task) => sum + (task.retryCount || 0), 0),
    workerCount: run.workerCount,
    captureWallMs: wallMs,
    summedTaskMs,
    savedMs: Math.max(0, summedTaskMs - wallMs),
    averageTaskMs: durations.length ? summedTaskMs / durations.length : null,
    p50TaskMs: percentile(durations, 50),
    medianTaskMs: percentile(durations, 50),
    p90TaskMs: percentile(durations, 90),
    p95TaskMs: percentile(durations, 95),
    maxTaskMs: durations.length ? Math.max(...durations) : null,
    screenshotsPerSecond: wallMs ? (tasks.length * 1000) / wallMs : null,
    parallelSpeedup: speedup,
    parallelEfficiency: speedup === null ? null : speedup / run.workerCount,
    workerBusyMs,
    workerIdleMs: Object.fromEntries(Object.entries(workerBusyMs).map(([id, busy]) => [id, Math.max(0, wallMs - busy)])),
    workerUtilization: Object.fromEntries(Object.entries(workerBusyMs).map(([id, busy]) => [id, wallMs ? busy / wallMs : null])),
    durationByScope: sumBy("scope"),
    durationByTheme: sumBy("theme"),
    durationByZoom: sumBy("zoom"),
    durationByState: sumBy("state"),
    slowestTasks: [...tasks].sort((a, b) => b.durationMs - a.durationMs).slice(0, 10),
    tasks,
  };
}
