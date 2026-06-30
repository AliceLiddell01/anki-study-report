export type ReportAction =
  | "copy-markdown"
  | "save-markdown"
  | "open-browser"
  | "open-problematic"
  | "open-again"
  | "open-new"
  | "open-dashboard";

export type BrowserActionKind = "problematic-decks" | "again" | "new";

export type ActionResponse = {
  ok: boolean;
  action: string;
  message?: string;
  error?: string;
};

export async function runReportAction(
  action: ReportAction,
  body: { kind?: BrowserActionKind } = {},
): Promise<ActionResponse> {
  const token = dashboardToken();
  const response = await fetch(`/api/actions/${action}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const data = await safeJson(response);
  if (!response.ok && !data) {
    return {
      ok: false,
      action,
      error: response.status === 403 ? "Invalid dashboard token." : "Dashboard action failed.",
    };
  }
  return normalizeActionResponse(data, action);
}

export function dashboardToken(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function normalizeActionResponse(value: unknown, fallbackAction: ReportAction): ActionResponse {
  const data = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    ok: data.ok === true,
    action: typeof data.action === "string" && data.action.trim() ? data.action : fallbackAction,
    message: cleanText(data.message),
    error: cleanText(data.error) || cleanText(data.message),
  };
}

function cleanText(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const text = value.replace(/\b(Traceback|undefined|null|NaN|Infinity|Invalid Date)\b/g, "Dashboard action failed.").trim();
  return text || undefined;
}
