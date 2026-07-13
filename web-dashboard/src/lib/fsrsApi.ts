import type { FsrsQuery, FsrsResponse } from "../types/report";

export class FsrsApiError extends Error {
  fieldErrors?: Record<string, string>;
  constructor(message: string, fieldErrors?: Record<string, string>) {
    super(message);
    this.name = "FsrsApiError";
    this.fieldErrors = fieldErrors;
  }
}

export function fsrsQueryKey(query: FsrsQuery): string {
  return JSON.stringify(query);
}

export async function fetchFsrs<T = Record<string, unknown>>(query: FsrsQuery, signal?: AbortSignal): Promise<FsrsResponse<T>> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/statistics/fsrs/query?token=${encodeURIComponent(token)}`, {
    method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" }, body: fsrsQueryKey(query), signal,
  });
  let payload: unknown;
  try { payload = await response.json(); } catch { payload = null; }
  const body = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  if (!response.ok || body.ok !== true || !body.response) {
    throw new FsrsApiError(typeof body.message === "string" ? body.message : response.status === 403 ? "Недействительная ссылка dashboard." : "Не удалось получить FSRS-аналитику.", body.fieldErrors as Record<string, string> | undefined);
  }
  return body.response as FsrsResponse<T>;
}
