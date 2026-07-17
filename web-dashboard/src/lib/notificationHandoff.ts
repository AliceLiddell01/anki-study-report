import type { NotificationCategory } from "./notificationsApi";

const KEY = "anki-study-report:notification-handoff";
const MAX_AGE_MS = 10 * 60 * 1000;

export type NotificationHandoff = {
  category: NotificationCategory;
  entityType: "deck" | "card";
  entityId: string;
  createdAt: string;
};

export function writeNotificationHandoff(value: NotificationHandoff): void {
  if (!valid(value, Date.now())) return;
  sessionStorage.setItem(KEY, JSON.stringify(value));
}

export function consumeNotificationHandoff(category: "deck_health" | "card_problems", now = Date.now()): NotificationHandoff | null {
  const raw = sessionStorage.getItem(KEY);
  sessionStorage.removeItem(KEY);
  if (!raw || raw.length > 512) return null;
  try {
    const value = JSON.parse(raw) as unknown;
    if (!valid(value, now) || value.category !== category) return null;
    return value;
  } catch {
    return null;
  }
}

function valid(value: unknown, now: number): value is NotificationHandoff {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const source = value as Record<string, unknown>;
  if (Object.keys(source).sort().join(",") !== "category,createdAt,entityId,entityType") return false;
  if (!new Set(["deck_health", "card_problems"]).has(String(source.category))) return false;
  if (!new Set(["deck", "card"]).has(String(source.entityType))) return false;
  if (typeof source.entityId !== "string" || !/^\d{1,40}$/.test(source.entityId)) return false;
  if (typeof source.createdAt !== "string" || source.createdAt.length > 40) return false;
  const created = Date.parse(source.createdAt);
  return Number.isFinite(created) && created <= now + 60_000 && now - created <= MAX_AGE_MS;
}
