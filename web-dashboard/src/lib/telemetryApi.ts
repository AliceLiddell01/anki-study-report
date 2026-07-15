export type DurationBucket = "under_100_ms" | "100_500_ms" | "500_2000_ms" | "over_2000_ms";
export type ResultCountBucket = "0" | "1_10" | "11_100" | "101_1000" | "over_1000";

export type SemanticTelemetryEvent =
  | { eventCode: "addon.started"; occurredAt: string }
  | { eventCode: "dashboard.opened"; occurredAt: string }
  | { eventCode: "page.opened"; pageCode: string; occurredAt: string }
  | { eventCode: "search.completed"; resultCode: "success" | "no_results" | "failed"; durationBucket: DurationBucket; resultCountBucket: ResultCountBucket; occurredAt: string }
  | { eventCode: "entity_action.completed"; actionCode: string; resultCode: "success" | "no_change" | "failed"; durationBucket: DurationBucket; occurredAt: string }
  | { eventCode: "api_operation.failed"; featureCode: string; errorCode: "timeout" | "unavailable" | "invalid_response" | "http_error" | "internal_error"; occurredAt: string }
  | { eventCode: "dashboard_startup.completed"; resultCode: "success" | "failed"; durationBucket: DurationBucket; occurredAt: string };

export type TelemetryEventResponse = {
  ok: boolean;
  code?: "telemetry.disabled" | "telemetry.queued" | "telemetry.queue_unavailable";
  queued?: boolean;
  purpose?: "reliabilityDiagnostics" | "featureUsage";
  error?: string;
  fieldErrors?: Record<string, string>;
};

function dashboardToken(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

export async function emitTelemetryEvent(event: SemanticTelemetryEvent): Promise<TelemetryEventResponse> {
  try {
    const response = await fetch(`/api/telemetry/events?token=${encodeURIComponent(dashboardToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(event),
      cache: "no-store",
    });
    const payload = await response.json() as TelemetryEventResponse;
    return payload && typeof payload === "object" ? payload : { ok: false, error: "invalid_response" };
  } catch {
    return { ok: false, error: "local_telemetry_unavailable" };
  }
}

export async function deleteTelemetryData(): Promise<{ ok: boolean; code?: string; deletionPending?: boolean; confirmed?: boolean; error?: string }> {
  try {
    const response = await fetch(`/api/telemetry/delete?token=${encodeURIComponent(dashboardToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      cache: "no-store",
    });
    return await response.json();
  } catch {
    return { ok: false, error: "local_telemetry_unavailable" };
  }
}

export function telemetryOccurredAt(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

export function durationBucket(durationMs: number): DurationBucket {
  if (durationMs < 100) return "under_100_ms";
  if (durationMs < 500) return "100_500_ms";
  if (durationMs < 2000) return "500_2000_ms";
  return "over_2000_ms";
}

export function resultCountBucket(count: number): ResultCountBucket {
  if (count <= 0) return "0";
  if (count <= 10) return "1_10";
  if (count <= 100) return "11_100";
  if (count <= 1000) return "101_1000";
  return "over_1000";
}
