export type NotificationCategory = "workload" | "retention" | "deck_health" | "card_problems" | "product_updates";
export type NotificationSeverity = "info" | "warning" | "critical";
export type NotificationKind = "signal_created" | "signal_reactivated" | "severity_escalated" | "release" | "system";
export type NotificationTab = "all" | "unread" | "active";

export type NotificationItem = {
  notificationId: string;
  signalId: string | null;
  kind: NotificationKind;
  code: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  createdAt: string;
  readAt: string | null;
  toastDeliveredAt: string | null;
  signalStatus: "active" | "resolved" | null;
  entity: { type: "all_collection" | "deck" | "card" | "note"; id: string | null } | null;
  evidence: Record<string, string | number | null>;
  sourceRevision: string;
};

export type NotificationPreferences = {
  notificationCenterEnabled: true;
  showUnreadBadge: boolean;
  showInAppToasts: boolean;
  minimumToastSeverity: NotificationSeverity;
  sound: "none";
  osNotifications: "none";
  toastCategories: Record<NotificationCategory, boolean>;
};

export type NotificationSummary = {
  schemaVersion: number;
  unreadCount: number;
  activeSignalCount: number;
  items: NotificationItem[];
};

export type NotificationList = {
  schemaVersion: number;
  page: number;
  pageLimit: number;
  pageCount: number;
  total: number;
  items: NotificationItem[];
};

const categories = new Set<NotificationCategory>(["workload", "retention", "deck_health", "card_problems", "product_updates"]);
const severities = new Set<NotificationSeverity>(["info", "warning", "critical"]);
const kinds = new Set<NotificationKind>(["signal_created", "signal_reactivated", "severity_escalated", "release", "system"]);

function dashboardToken(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const separator = path.includes("?") ? "&" : "?";
  const response = await fetch(`${path}${separator}token=${encodeURIComponent(dashboardToken())}`, {
    cache: "no-store",
    ...init,
  });
  const payload = await response.json().catch(() => null) as unknown;
  if (!response.ok) throw new Error(errorCode(payload));
  return payload;
}

export async function fetchNotificationSummary(): Promise<NotificationSummary> {
  return parseSummary(await request("/api/notifications/summary"));
}

export async function fetchNotifications(query: { page?: number; pageLimit?: number; tab?: NotificationTab; category?: NotificationCategory | "all" } = {}): Promise<NotificationList> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    pageLimit: String(query.pageLimit ?? 20),
    tab: query.tab ?? "all",
    category: query.category ?? "all",
  });
  return parseList(await request(`/api/notifications?${params.toString()}`));
}

export async function markNotificationsRead(notificationIds: string[]): Promise<NotificationSummary> {
  return parseMutationSummary(await request("/api/notifications/read", jsonRequest("POST", { notificationIds })));
}

export async function markAllNotificationsRead(): Promise<NotificationSummary> {
  return parseMutationSummary(await request("/api/notifications/read-all", jsonRequest("POST", {})));
}

export async function fetchNotificationPreferences(): Promise<NotificationPreferences> {
  return parsePreferencesResponse(await request("/api/settings/notifications"));
}

export async function saveNotificationPreferences(patch: Partial<Pick<NotificationPreferences, "showUnreadBadge" | "showInAppToasts" | "minimumToastSeverity">> & { toastCategories?: Partial<Record<NotificationCategory, boolean>> }): Promise<NotificationPreferences> {
  return parsePreferencesResponse(await request("/api/settings/notifications", jsonRequest("PUT", patch)));
}

export async function fetchToastCandidates(sessionStartedAt: string): Promise<NotificationItem[]> {
  const payload = assertRecord(await request(`/api/notifications/toasts?sessionStartedAt=${encodeURIComponent(sessionStartedAt)}`));
  assertExactKeys(payload, ["ok", "schemaVersion", "items"]);
  if (payload.ok !== true || payload.schemaVersion !== 1 || !Array.isArray(payload.items)) throw new Error("invalid_notification_response");
  return payload.items.map(parseItem);
}

export async function acknowledgeToastDelivery(notificationIds: string[]): Promise<void> {
  const payload = assertRecord(await request("/api/notifications/toast-delivered", jsonRequest("POST", { notificationIds })));
  assertExactKeys(payload, ["ok", "updated"]);
  if (payload.ok !== true || !isCount(payload.updated)) throw new Error("invalid_notification_response");
}

function jsonRequest(method: "POST" | "PUT", value: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) };
}

function parseSummary(value: unknown): NotificationSummary {
  const payload = assertRecord(value);
  assertExactKeys(payload, ["ok", "schemaVersion", "unreadCount", "activeSignalCount", "items"]);
  if (payload.ok !== true || payload.schemaVersion !== 1 || !isCount(payload.unreadCount) || !isCount(payload.activeSignalCount) || !Array.isArray(payload.items)) throw new Error("invalid_notification_response");
  return { schemaVersion: 1, unreadCount: payload.unreadCount, activeSignalCount: payload.activeSignalCount, items: payload.items.map(parseItem) };
}

function parseMutationSummary(value: unknown): NotificationSummary {
  const payload = assertRecord(value);
  assertExactKeys(payload, ["ok", "updated", "schemaVersion", "unreadCount", "activeSignalCount", "items"]);
  if (!isCount(payload.updated)) throw new Error("invalid_notification_response");
  return parseSummary(Object.fromEntries(Object.entries(payload).filter(([key]) => key !== "updated")));
}

function parseList(value: unknown): NotificationList {
  const payload = assertRecord(value);
  assertExactKeys(payload, ["ok", "schemaVersion", "page", "pageLimit", "pageCount", "total", "items"]);
  if (payload.ok !== true || payload.schemaVersion !== 1 || !isPositive(payload.page) || !isPositive(payload.pageLimit) || payload.pageLimit > 50 || !isCount(payload.pageCount) || !isCount(payload.total) || !Array.isArray(payload.items)) throw new Error("invalid_notification_response");
  return { schemaVersion: 1, page: payload.page, pageLimit: payload.pageLimit, pageCount: payload.pageCount, total: payload.total, items: payload.items.map(parseItem) };
}

function parsePreferencesResponse(value: unknown): NotificationPreferences {
  const payload = assertRecord(value);
  assertExactKeys(payload, ["ok", "schemaVersion", "preferences"]);
  if (payload.ok !== true || payload.schemaVersion !== 1) throw new Error("invalid_notification_response");
  const preferences = assertRecord(payload.preferences);
  assertExactKeys(preferences, ["notificationCenterEnabled", "showUnreadBadge", "showInAppToasts", "minimumToastSeverity", "sound", "osNotifications", "toastCategories"]);
  const toastCategories = assertRecord(preferences.toastCategories);
  assertExactKeys(toastCategories, [...categories]);
  if (preferences.notificationCenterEnabled !== true || typeof preferences.showUnreadBadge !== "boolean" || typeof preferences.showInAppToasts !== "boolean" || !severities.has(preferences.minimumToastSeverity as NotificationSeverity) || preferences.sound !== "none" || preferences.osNotifications !== "none" || Object.values(toastCategories).some((item) => typeof item !== "boolean")) throw new Error("invalid_notification_response");
  return { ...preferences, toastCategories } as NotificationPreferences;
}

function parseItem(value: unknown): NotificationItem {
  const item = assertRecord(value);
  assertExactKeys(item, ["notificationId", "signalId", "kind", "code", "category", "severity", "createdAt", "readAt", "toastDeliveredAt", "signalStatus", "entity", "evidence", "sourceRevision"]);
  const entity = item.entity === null ? null : assertRecord(item.entity);
  if (entity) assertExactKeys(entity, ["type", "id"]);
  const evidence = assertRecord(item.evidence);
  if (!isBoundedString(item.notificationId, 64) || !(item.signalId === null || isBoundedString(item.signalId, 64)) || !kinds.has(item.kind as NotificationKind) || !isBoundedString(item.code, 100) || !categories.has(item.category as NotificationCategory) || !severities.has(item.severity as NotificationSeverity) || !isBoundedString(item.createdAt, 40) || !(item.readAt === null || isBoundedString(item.readAt, 40)) || !(item.toastDeliveredAt === null || isBoundedString(item.toastDeliveredAt, 40)) || !(item.signalStatus === null || item.signalStatus === "active" || item.signalStatus === "resolved") || !isBoundedString(item.sourceRevision, 160)) throw new Error("invalid_notification_response");
  if (entity && (!new Set(["all_collection", "deck", "card", "note"]).has(String(entity.type)) || !(entity.id === null || isBoundedString(entity.id, 40)))) throw new Error("invalid_notification_response");
  if (Object.keys(evidence).length > 8 || Object.values(evidence).some((entry) => !(entry === null || typeof entry === "string" || typeof entry === "number"))) throw new Error("invalid_notification_response");
  return item as NotificationItem;
}

function assertRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid_notification_response");
  return value as Record<string, unknown>;
}

function assertExactKeys(value: Record<string, unknown>, keys: string[]): void {
  const expected = [...keys].sort();
  const actual = Object.keys(value).sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) throw new Error("invalid_notification_response");
}

function isCount(value: unknown): value is number { return Number.isInteger(value) && (value as number) >= 0; }
function isPositive(value: unknown): value is number { return Number.isInteger(value) && (value as number) >= 1; }
function isBoundedString(value: unknown, limit: number): value is string { return typeof value === "string" && value.length > 0 && value.length <= limit && !/[\r\n]/.test(value); }
function errorCode(value: unknown): string { return value && typeof value === "object" && "error" in value && typeof value.error === "string" ? value.error : "notification_request_failed"; }
