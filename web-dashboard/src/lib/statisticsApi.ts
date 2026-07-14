import type { StatisticsQuery, StatisticsResult } from "../types/report";
import i18n from "../i18n";

export class StatisticsApiError extends Error {
  fieldErrors?: Record<string, string>;

  constructor(message: string, fieldErrors?: Record<string, string>) {
    super(message);
    this.name = "StatisticsApiError";
    this.fieldErrors = fieldErrors;
  }
}

export function statisticsQueryKey(query: StatisticsQuery): string {
  return JSON.stringify({
    scope: query.scope,
    period: query.period,
    granularity: query.granularity,
    comparison: query.period === "all" ? false : query.comparison,
  });
}

export async function fetchStatistics(query: StatisticsQuery, signal?: AbortSignal): Promise<StatisticsResult> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/statistics/query?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: statisticsQueryKey(query),
    signal,
  });
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const body = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  if (!response.ok || body.ok !== true || !body.result || typeof body.result !== "object") {
    const fieldErrors = body.fieldErrors && typeof body.fieldErrors === "object"
      ? body.fieldErrors as Record<string, string>
      : undefined;
    throw new StatisticsApiError(
      typeof body.message === "string" ? body.message : response.status === 403 ? i18n.t("unavailable.forbidden", { ns: "statistics" }) : i18n.t("shell.refreshFailed", { ns: "statistics" }),
      fieldErrors,
    );
  }
  return body.result as StatisticsResult;
}

