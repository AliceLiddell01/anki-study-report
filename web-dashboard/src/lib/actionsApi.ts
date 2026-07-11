export type ReportAction =
  | "copy-markdown"
  | "save-markdown"
  | "open-browser"
  | "open-browser-search"
  | "open-deck-browser"
  | "open-problematic"
  | "open-again"
  | "open-new"
  | "open-dashboard"
  | "open-native-stats";

export type BrowserActionKind = "problematic-decks" | "again" | "new";

export type ServerAction = "restart" | "stop" | "open-dashboard" | "copy-url";

export type ActionResponse = {
  ok: boolean;
  action: string;
  message?: string;
  error?: string;
};

export async function runReportAction(
  action: ReportAction,
  body: { kind?: BrowserActionKind; query?: string; deckId?: number; mode?: "subtree" | "direct" } = {},
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

export async function runServerAction(action: ServerAction): Promise<ActionResponse> {
  const token = dashboardToken();
  const response = await fetch(`/api/server/${action}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
  });
  const data = await safeJson(response);
  if (!response.ok && !data) {
    return {
      ok: false,
      action,
      error: response.status === 403 ? "Invalid dashboard token." : "Server action failed.",
    };
  }
  return normalizeActionResponse(data, action);
}

export function dashboardToken(): string {
  return dashboardTokenFromSearch(window.location.search);
}

export function dashboardTokenFromSearch(search: string): string {
  return new URLSearchParams(search).get("token") || "";
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function normalizeActionResponse(value: unknown, fallbackAction: ReportAction | ServerAction): ActionResponse {
  const data = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const ok = data.ok === true;
  return {
    ok,
    action: typeof data.action === "string" && data.action.trim() ? data.action : fallbackAction,
    message: cleanText(data.message),
    error: ok ? undefined : cleanText(data.error) || cleanText(data.message),
  };
}

function cleanText(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const text = value.replace(/\b(Traceback|undefined|null|NaN|Infinity|Invalid Date)\b/g, "Dashboard action failed.").trim();
  return text || undefined;
}
