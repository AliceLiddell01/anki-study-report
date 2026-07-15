import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";

function parsedDateTime(value: unknown): Date | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const normalized = value.replace(/\.(\d{3})\d+(?=Z|[+-]\d{2}:?\d{2}$)/, ".$1");
  const parsed = new Date(normalized);
  return Number.isFinite(parsed.getTime()) ? parsed : null;
}

export function isValidDateTime(value: unknown): value is string {
  return parsedDateTime(value) !== null;
}

export function formatDateTime(value: unknown, fallback = i18n.t("state.noData", { ns: "common" })): string {
  const parsed = parsedDateTime(value);
  if (!parsed) return fallback;
  return new Intl.DateTimeFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(parsed);
}
